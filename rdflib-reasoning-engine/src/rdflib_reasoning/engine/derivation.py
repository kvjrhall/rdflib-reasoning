from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, Protocol, cast

from .proof import (
    DerivationRecord,
    DirectProof,
    ProofLeaf,
    ProofNode,
    ProofPayload,
    RuleApplication,
    TripleFact,
)


class DerivationLogger(Protocol):
    """Interface for sinks of engine-native derivation records.

    These records are engine provenance artifacts, not user-facing proof steps.
    """

    def record(self, record: DerivationRecord) -> None: ...


class ExplanationReconstructor(Protocol):
    """Interface for rebuilding `DirectProof` values from derivation records."""

    def reconstruct(
        self,
        goal: ProofPayload,
        records: Iterable[DerivationRecord],
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
        records: Iterable[DerivationRecord],
    ) -> DirectProof:
        records_tuple = tuple(records)
        if isinstance(goal, TripleFact):
            proof = self._build_node(goal, records_tuple, seen=frozenset())
            verdict: Literal["proved", "incomplete"] = (
                "proved" if isinstance(proof, RuleApplication) else "incomplete"
            )
            return DirectProof(
                context=goal.context,
                goal=goal,
                proof=proof,
                verdict=verdict,
            )

        return DirectProof(
            context=goal.context,
            goal=goal,
            proof=ProofLeaf(claim=goal),
            verdict="incomplete",
            notes="Only triple-goal explanation reconstruction is implemented.",
        )
