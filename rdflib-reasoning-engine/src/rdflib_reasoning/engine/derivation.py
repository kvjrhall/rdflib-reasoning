from __future__ import annotations

import warnings
from collections.abc import Iterable, MutableSequence
from dataclasses import dataclass, field
from typing import Literal, Protocol, cast

from rdflib_reasoning.axiom.common import Triple

from .proof import (
    ContradictionClaim,
    ContradictionRecord,
    DerivationRecord,
    DirectProof,
    ProofLeaf,
    ProofNode,
    ProofPayload,
    RuleApplication,
    TripleFact,
)


def format_contradiction_record(record: ContradictionRecord) -> str:
    message = (
        f"[{record.category}] {record.detail} "
        f"(rule={record.rule_id.ruleset}:{record.rule_id.rule_id}, seq={record.sequence_id})"
    )
    message += "\n  premises:\n"
    for premise in record.premises:
        message += f"    {_format_triple(premise.triple)}\n"
    if record.witness is not None:
        message += f"  witness: {_format_triple(record.witness.triple)}\n"
    return message


def _format_triple(triple: Triple) -> tuple[str, str, str]:
    return (triple[0].n3(), triple[1].n3(), triple[2].n3())


class ContradictionWarning(UserWarning):
    """Warning emitted when a contradiction is detected."""


def _warn_contradiction(record: ContradictionRecord, *, stacklevel: int) -> None:
    warnings.warn(
        f"Contradiction [{record.category}] {record.detail} "
        f"(rule={record.rule_id.ruleset}:{record.rule_id.rule_id}, seq={record.sequence_id})",
        ContradictionWarning,
        stacklevel=stacklevel,
    )


class DerivationLogger(Protocol):
    """Interface for sinks of engine-native derivation records.

    These records are engine provenance artifacts, not user-facing proof steps.
    """

    def record(self, record: DerivationRecord) -> None: ...


class ContradictionRecorder(Protocol):
    """Interface for sinks of engine-native contradiction records."""

    def record(self, record: ContradictionRecord) -> None: ...

    def iter_records(self) -> Iterable[ContradictionRecord]: ...

    def clear(self) -> None: ...


@dataclass(slots=True)
class InMemoryDerivationLogger:
    """Simple in-memory sink for engine-native derivation records."""

    records: list[DerivationRecord] = field(default_factory=list)

    def record(self, record: DerivationRecord) -> None:
        """Append one derivation record to the in-memory log."""
        self.records.append(record)


@dataclass(frozen=True, slots=True)
class InMemoryContradictionRecorder:
    """Append-all sink for contradiction diagnostics (unbounded retention).

    When ``warn`` is true (default), each contradiction also emits
    :class:`ContradictionWarning` via :func:`warnings.warn`.
    """

    warn: bool = True
    records: MutableSequence[ContradictionRecord] = field(default_factory=list)

    def record(self, record: ContradictionRecord) -> None:
        """Append one contradiction record to the in-memory log."""
        self.records.append(record)
        if self.warn:
            _warn_contradiction(record, stacklevel=2)

    def iter_records(self) -> Iterable[ContradictionRecord]:
        return tuple(self.records)

    def clear(self) -> None:
        self.records.clear()


class ContradictionDetectedError(RuntimeError):
    """Error raised when a contradiction is detected."""

    record: ContradictionRecord

    def __init__(self, record: ContradictionRecord):
        message = format_contradiction_record(record)
        super().__init__(message)
        self.record = record


@dataclass
class RaiseOnContradictionRecorder:
    """Append each contradiction then raise :class:`ContradictionDetectedError`.

    Retention is unbounded (same list semantics as :class:`InMemoryContradictionRecorder`)
    unless :meth:`clear` is called.
    """

    records: MutableSequence[ContradictionRecord] = field(default_factory=list)

    def record(self, record: ContradictionRecord) -> None:
        self.records.append(record)
        raise ContradictionDetectedError(record)

    def iter_records(self) -> Iterable[ContradictionRecord]:
        return tuple(self.records)

    def clear(self) -> None:
        self.records.clear()


@dataclass(slots=True)
class DropContradictionRecorder:
    """Discard contradiction diagnostics after optional warning (zero retention).

    :meth:`iter_records` is always empty—there is nothing for
    :meth:`~rdflib_reasoning.engine.api.RETEEngine.contradiction_records` or
    explanation reconstruction to read from this recorder alone.
    """

    warn: bool = True

    def record(self, record: ContradictionRecord) -> None:
        if self.warn:
            _warn_contradiction(record, stacklevel=2)

    def iter_records(self) -> Iterable[ContradictionRecord]:
        return ()

    def clear(self) -> None:
        pass


class ExplanationReconstructor(Protocol):
    """Interface for rebuilding `DirectProof` values from derivation records."""

    def reconstruct(
        self,
        goal: ProofPayload,
        records: Iterable[DerivationRecord | ContradictionRecord],
    ) -> DirectProof: ...


class DerivationProofReconstructor:
    """Rebuild a `DirectProof` tree from engine-native derivation records."""

    @staticmethod
    def _matching_records(
        goal: TripleFact,
        records: tuple[DerivationRecord, ...],
    ) -> tuple[DerivationRecord, ...]:
        return tuple(
            record
            for record in records
            if record.context == goal.context
            and any(conclusion == goal for conclusion in record.conclusions)
            and not record.silent
        )

    @staticmethod
    def _matching_contradictions(
        goal: ContradictionClaim,
        records: tuple[ContradictionRecord, ...],
    ) -> tuple[ContradictionRecord, ...]:
        goal_witness = goal.witness.triple
        return tuple(
            record
            for record in records
            if record.context == goal.context
            and (
                (record.witness is not None and record.witness.triple == goal_witness)
                or any(premise.triple == goal_witness for premise in record.premises)
            )
        )

    @staticmethod
    def _record_priority(record: DerivationRecord) -> tuple[int, int, int]:
        depth = record.depth if record.depth is not None else 10**9
        return (depth, len(record.premises), len(record.conclusions))

    def _build_node(
        self,
        goal: TripleFact,
        records: tuple[DerivationRecord, ...],
        *,
        seen: frozenset[tuple[object, tuple[object, object, object]]],
    ) -> ProofNode:
        goal_key = (goal.context, goal.triple)
        if goal_key in seen:
            return ProofLeaf(claim=goal)

        matches = self._matching_records(goal, records)
        if not matches:
            return ProofLeaf(claim=goal)

        chosen = min(matches, key=self._record_priority)
        next_seen = seen | {goal_key}
        premises = [
            self._build_node(premise, records, seen=next_seen)
            for premise in chosen.premises
        ]
        return RuleApplication(
            conclusions=cast(list[ProofPayload], chosen.conclusions),
            premises=premises,
            rule_id=chosen.rule_id,
            derivation=chosen,
        )

    def reconstruct(
        self,
        goal: ProofPayload,
        records: Iterable[DerivationRecord | ContradictionRecord],
    ) -> DirectProof:
        derivation_records = tuple(
            record for record in records if isinstance(record, DerivationRecord)
        )
        if isinstance(goal, TripleFact):
            proof = self._build_node(goal, derivation_records, seen=frozenset())
            verdict: Literal["proved", "incomplete"] = (
                "proved" if isinstance(proof, RuleApplication) else "incomplete"
            )
            return DirectProof(
                context=goal.context,
                goal=goal,
                proof=proof,
                verdict=verdict,
            )

        if isinstance(goal, ContradictionClaim):
            contradiction_records = tuple(
                record for record in records if isinstance(record, ContradictionRecord)
            )
            matches = self._matching_contradictions(goal, contradiction_records)
            if not matches:
                return DirectProof(
                    context=goal.context,
                    goal=goal,
                    proof=ProofLeaf(claim=goal),
                    verdict="incomplete",
                    notes=(
                        "No contradiction diagnostics record matched the requested "
                        "witness in this context."
                    ),
                )

            chosen = min(matches, key=lambda record: record.sequence_id)
            proof = RuleApplication(
                conclusions=[goal],
                premises=[ProofLeaf(claim=premise) for premise in chosen.premises],
                rule_id=chosen.rule_id,
                rationale=chosen.detail,
            )
            return DirectProof(
                context=goal.context,
                goal=goal,
                proof=proof,
                verdict="contradiction",
            )

        return DirectProof(
            context=goal.context,
            goal=goal,
            proof=ProofLeaf(claim=goal),
            verdict="incomplete",
            notes="Only triple-goal explanation reconstruction is implemented.",
        )
