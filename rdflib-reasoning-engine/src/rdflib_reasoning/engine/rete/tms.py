from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from rdflib.term import Node
from rdflib_reasoning.axiom.common import Triple

from ..proof import RuleId
from .facts import Fact, fact_id_for_triple


class DependencyGraph(BaseModel):
    """
    Bidirectional map tracking logical support relationships among facts.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    antecedents_by_consequent: dict[str, set[str]] = Field(default_factory=dict)
    consequents_by_antecedent: dict[str, set[str]] = Field(default_factory=dict)

    def add_support(self, consequent_id: str, antecedent_ids: tuple[str, ...]) -> None:
        consequent_antecedents = self.antecedents_by_consequent.setdefault(
            consequent_id, set()
        )
        consequent_antecedents.update(antecedent_ids)
        for antecedent_id in antecedent_ids:
            supported = self.consequents_by_antecedent.setdefault(antecedent_id, set())
            supported.add(consequent_id)

    def antecedents_of(self, consequent_id: str) -> tuple[str, ...]:
        return tuple(sorted(self.antecedents_by_consequent.get(consequent_id, set())))

    def consequents_of(self, antecedent_id: str) -> tuple[str, ...]:
        return tuple(sorted(self.consequents_by_antecedent.get(antecedent_id, set())))

    def discard_consequent(self, consequent_id: str) -> None:
        """Remove every edge that involves this fact.

        Used when the fact is being swept from working memory: both the
        consequent-to-antecedent and antecedent-to-consequent directions
        of the dependency graph are cleared.
        """
        antecedents = self.antecedents_by_consequent.pop(consequent_id, None)
        if antecedents:
            for antecedent_id in antecedents:
                supported = self.consequents_by_antecedent.get(antecedent_id)
                if supported is None:
                    continue
                supported.discard(consequent_id)
                if not supported:
                    del self.consequents_by_antecedent[antecedent_id]
        consequents_of = self.consequents_by_antecedent.pop(consequent_id, None)
        if consequents_of:
            for cons_id in consequents_of:
                antecedents_of_cons = self.antecedents_by_consequent.get(cons_id)
                if antecedents_of_cons is None:
                    continue
                antecedents_of_cons.discard(consequent_id)
                if not antecedents_of_cons:
                    del self.antecedents_by_consequent[cons_id]

    def update_consequent_edges(
        self, consequent_id: str, antecedent_ids: Iterable[str]
    ) -> None:
        """Rewrite a consequent's antecedent edges to the given identifiers.

        Used when a fact is kept after a sweep but its justification set has
        been trimmed: the consequent's antecedent edges are set to exactly the
        union of antecedents of its surviving justifications, and reverse
        edges that no longer correspond to any surviving justification are
        discarded.
        """
        new_antecedents = set(antecedent_ids)
        old_antecedents = self.antecedents_by_consequent.get(consequent_id, set())
        removed = old_antecedents - new_antecedents
        if new_antecedents:
            self.antecedents_by_consequent[consequent_id] = new_antecedents
        else:
            self.antecedents_by_consequent.pop(consequent_id, None)
        for antecedent_id in removed:
            supported = self.consequents_by_antecedent.get(antecedent_id)
            if supported is None:
                continue
            supported.discard(consequent_id)
            if not supported:
                del self.consequents_by_antecedent[antecedent_id]

    def clear(self) -> None:
        self.antecedents_by_consequent.clear()
        self.consequents_by_antecedent.clear()


class Justification(BaseModel):
    """
    A single reason for a fact's logical support.

    Justifications are logical support records used for future truth
    maintenance; they are distinct from user-facing proof nodes.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    rule_id: RuleId
    consequent_id: str
    antecedent_ids: tuple[str, ...]
    metadata: dict[str, Any]


class SupportSnapshot(BaseModel):
    """Immutable view of a fact's TMS support state at a moment in time."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    triple: Triple
    fact_id: str | None
    is_present: bool
    is_stated: bool
    justification_ids: tuple[str, ...]

    @property
    def justification_count(self) -> int:
        return len(self.justification_ids)

    @property
    def is_supported(self) -> bool:
        return self.is_present and (self.is_stated or self.justification_count > 0)


class RetractionOutcome(BaseModel):
    """Immutable record of the facts and justifications affected by a retraction.

    Mark-Verify-Sweep retraction may remove facts from working memory, drop
    justification records, and clear the ``stated`` flag from a fact that
    survives because of independent derived support. This outcome surfaces all
    three categories so that engine-side wiring can mirror the changes through
    the supported RDFLib integration path.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    removed_fact_ids: tuple[str, ...] = ()
    removed_triples: tuple[Triple, ...] = ()
    removed_justification_ids: tuple[str, ...] = ()
    unstated_fact_ids: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return (
            not self.removed_fact_ids
            and not self.removed_justification_ids
            and not self.unstated_fact_ids
        )


class WorkingMemory(BaseModel):
    """
    Reactive store of currently asserted facts flowing through the network.

    Working memory is an execution-time structure, not a persisted proof or
    derivation artifact.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    facts_by_id: dict[str, Fact] = Field(default_factory=dict)
    fact_ids_by_triple: dict[Triple, str] = Field(default_factory=dict)

    def add_fact(self, triple: Triple, *, stated: bool) -> Fact:
        fact_id = fact_id_for_triple(triple)
        existing_id = self.fact_ids_by_triple.get(triple)
        if existing_id is not None:
            fact = self.facts_by_id[existing_id]
            if stated:
                fact.stated = True
            return fact

        fact = Fact(id=fact_id, triple=triple, stated=stated)
        self.facts_by_id[fact.id] = fact
        self.fact_ids_by_triple[triple] = fact.id
        return fact

    def get_fact(self, triple: Triple) -> Fact | None:
        fact_id = self.fact_ids_by_triple.get(triple)
        if fact_id is None:
            return None
        return self.facts_by_id[fact_id]

    def has_fact(self, triple: Triple) -> bool:
        return triple in self.fact_ids_by_triple

    def facts(self) -> tuple[Fact, ...]:
        return tuple(self.facts_by_id.values())

    def remove_fact(self, fact_id: str) -> Fact:
        """Remove the working-memory entry for a fact id and return it.

        Raises ``KeyError`` if the fact id is not present.
        """
        fact = self.facts_by_id.pop(fact_id)
        del self.fact_ids_by_triple[fact.triple]
        return fact

    def clear(self) -> None:
        self.facts_by_id.clear()
        self.fact_ids_by_triple.clear()


class TMSController(BaseModel):
    """
    Controller for truth-maintenance bookkeeping and recursive retraction.

    The controller owns fact support state, dependency graph maintenance, and
    Mark-Verify-Sweep retraction. It deliberately does not mutate RETE matcher
    memory or backing RDFLib stores; callers such as ``RETEEngine`` and
    ``RETEStore`` compose those integration responsibilities around the TMS
    primitive.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    working_memory: WorkingMemory = Field(default_factory=WorkingMemory)
    dependency_graph: DependencyGraph = Field(default_factory=DependencyGraph)
    justifications_by_consequent: dict[str, dict[str, Justification]] = Field(
        default_factory=dict
    )

    @staticmethod
    def _bindings_metadata(bindings: Mapping[str, Node]) -> tuple[tuple[str, str], ...]:
        return tuple((name, value.n3()) for name, value in sorted(bindings.items()))

    @staticmethod
    def _justification_key(
        *,
        rule_id: RuleId,
        antecedent_ids: tuple[str, ...],
        metadata: dict[str, Any],
    ) -> str:
        metadata_key = "|".join(
            f"{key}={repr(value)}" for key, value in sorted(metadata.items())
        )
        antecedents_key = ",".join(antecedent_ids)
        return f"{rule_id.ruleset}:{rule_id.rule_id}|{antecedents_key}|{metadata_key}"

    def register_stated(self, triples: Iterable[Triple]) -> tuple[Fact, ...]:
        return tuple(
            self.working_memory.add_fact(triple, stated=True) for triple in triples
        )

    def record_derivation(
        self,
        triple: Triple,
        *,
        rule_id: RuleId,
        premises: tuple[Fact, ...],
        bindings: Mapping[str, Node],
        depth: int,
    ) -> Fact:
        consequent = self.working_memory.add_fact(triple, stated=False)
        antecedent_ids = tuple(fact.id for fact in premises)
        metadata = {
            "depth": depth,
            "bindings": self._bindings_metadata(bindings),
        }
        support_key = self._justification_key(
            rule_id=rule_id, antecedent_ids=antecedent_ids, metadata=metadata
        )
        justification = Justification(
            id=support_key,
            rule_id=rule_id,
            consequent_id=consequent.id,
            antecedent_ids=antecedent_ids,
            metadata=metadata,
        )
        supports = self.justifications_by_consequent.setdefault(consequent.id, {})
        if support_key not in supports:
            supports[support_key] = justification
            self.dependency_graph.add_support(consequent.id, antecedent_ids)
        return consequent

    def fact_for_triple(self, triple: Triple) -> Fact | None:
        return self.working_memory.get_fact(triple)

    def justifications_for(self, triple: Triple) -> tuple[Justification, ...]:
        fact = self.working_memory.get_fact(triple)
        if fact is None:
            return ()
        return self.justifications_for_fact_id(fact.id)

    def justifications_for_fact_id(self, fact_id: str) -> tuple[Justification, ...]:
        return tuple(self.justifications_by_consequent.get(fact_id, {}).values())

    def support_count(self, triple: Triple) -> int:
        return len(self.justifications_for(triple))

    def is_supported(self, triple: Triple) -> bool:
        fact = self.working_memory.get_fact(triple)
        if fact is None:
            return False
        return fact.stated or self.support_count(triple) > 0

    def support_snapshot(self, triple: Triple) -> SupportSnapshot:
        fact = self.working_memory.get_fact(triple)
        if fact is None:
            return SupportSnapshot(
                triple=triple,
                fact_id=None,
                is_present=False,
                is_stated=False,
                justification_ids=(),
            )
        justifications = self.justifications_for_fact_id(fact.id)
        return SupportSnapshot(
            triple=triple,
            fact_id=fact.id,
            is_present=True,
            is_stated=fact.stated,
            justification_ids=tuple(
                justification.id for justification in justifications
            ),
        )

    def would_remain_supported(
        self,
        triple: Triple,
        *,
        without_justification_id: str | None = None,
        without_antecedent_id: str | None = None,
    ) -> bool:
        if (without_justification_id is None) == (without_antecedent_id is None):
            raise ValueError(
                "Provide exactly one of without_justification_id or "
                "without_antecedent_id."
            )

        fact = self.working_memory.get_fact(triple)
        if fact is None:
            return False
        if fact.stated:
            return True

        for justification in self.justifications_for_fact_id(fact.id):
            if without_justification_id is not None:
                if justification.id != without_justification_id:
                    return True
                continue
            if without_antecedent_id not in justification.antecedent_ids:
                return True
        return False

    def transitively_supported(self, triple: Triple) -> bool:
        fact = self.working_memory.get_fact(triple)
        if fact is None:
            return False
        return self._fact_id_transitively_supported(fact.id, set())

    def _fact_id_transitively_supported(self, fact_id: str, visiting: set[str]) -> bool:
        fact = self.working_memory.facts_by_id.get(fact_id)
        if fact is None:
            return False
        if fact.stated:
            return True
        if fact_id in visiting:
            return False

        justifications = self.justifications_for_fact_id(fact_id)
        if not justifications:
            return False

        visiting.add(fact_id)
        try:
            return all(
                all(
                    self._fact_id_transitively_supported(antecedent_id, visiting)
                    for antecedent_id in justification.antecedent_ids
                )
                for justification in justifications
            )
        finally:
            visiting.remove(fact_id)

    def dependents_of(self, triple: Triple) -> tuple[str, ...]:
        fact = self.working_memory.get_fact(triple)
        if fact is None:
            return ()
        return self.dependency_graph.consequents_of(fact.id)

    def transitive_dependents_of(self, triple: Triple) -> tuple[str, ...]:
        fact = self.working_memory.get_fact(triple)
        if fact is None:
            return ()

        seen: set[str] = set()
        pending = list(self.dependency_graph.consequents_of(fact.id))
        while pending:
            dependent_id = pending.pop(0)
            if dependent_id in seen:
                continue
            seen.add(dependent_id)
            pending.extend(self.dependency_graph.consequents_of(dependent_id))
        return tuple(sorted(seen))

    def retract_triple(self, triple: Triple) -> RetractionOutcome:
        """Retract a stated triple using Mark-Verify-Sweep over support paths.

        Behavior follows the usual JTMS support rules for this controller:
        stated facts remain supported regardless of whether they also have
        derived justifications; derived facts are removed only when they have
        no remaining valid justifications; silent justifications count the
        same as visible ones for support.

        - If the triple is unknown, the call is a no-op and an empty outcome
          is returned.
        - If the matching fact is non-stated (derived only), ``ValueError`` is
          raised. Direct retraction of derived facts violates the invariant
          that derived facts are removed iff their justification set becomes
          empty; only stated retraction is exposed at this layer.
        - If the fact is stated and has at least one justification, the
          ``stated`` flag is cleared. The fact remains present, supported by
          its derived justifications, and no cascade is performed.
        - If the fact is stated and has no justifications, the fact is removed
          and Mark-Verify-Sweep removes any transitive dependents whose
          remaining justifications cannot be grounded outside the swept set.

        The method is atomic: the verify fixed point completes before any
        mutation occurs, so the call either commits the full sweep or makes no
        mutations at all.

        This method updates only working memory, the justification table, and
        the dependency graph. It does not update the RETE alpha/beta network,
        the agenda, or any backing RDF store; callers that embed this
        controller in a full engine must apply matching removals there
        separately.
        """
        fact = self.working_memory.get_fact(triple)
        if fact is None:
            return RetractionOutcome()

        if not fact.stated:
            raise ValueError(
                "TMSController.retract_triple only accepts stated facts; "
                f"the fact for triple {triple!r} is derived. Retract one of "
                "its stated antecedents instead."
            )

        if self.justifications_for_fact_id(fact.id):
            fact.stated = False
            return RetractionOutcome(unstated_fact_ids=(fact.id,))

        return self._mark_verify_sweep(fact.id)

    def _mark_verify_sweep(self, seed_fact_id: str) -> RetractionOutcome:
        """Perform Mark-Verify-Sweep starting from a stated, unsupported seed.

        Pre-condition: the seed fact exists in working memory, is stated, and
        has no justifications. The seed is unconditionally added to the
        candidate set and removed by the sweep.
        """
        candidates: set[str] = {seed_fact_id}
        pending = list(self.dependency_graph.consequents_of(seed_fact_id))
        while pending:
            candidate_id = pending.pop()
            if candidate_id in candidates:
                continue
            candidates.add(candidate_id)
            pending.extend(self.dependency_graph.consequents_of(candidate_id))

        kept: set[str] = set()

        def is_supported_outside(fact_id: str) -> bool:
            if fact_id not in candidates:
                return True
            if fact_id in kept:
                return True
            return False

        changed = True
        while changed:
            changed = False
            for candidate_id in candidates:
                if candidate_id == seed_fact_id:
                    continue
                if candidate_id in kept:
                    continue
                candidate_fact = self.working_memory.facts_by_id.get(candidate_id)
                if candidate_fact is None:
                    continue
                if candidate_fact.stated:
                    kept.add(candidate_id)
                    changed = True
                    continue
                for justification in self.justifications_for_fact_id(candidate_id):
                    if all(
                        is_supported_outside(antecedent_id)
                        for antecedent_id in justification.antecedent_ids
                    ):
                        kept.add(candidate_id)
                        changed = True
                        break

        swept = candidates - kept

        removed_pairs: list[tuple[str, Triple]] = []
        removed_justification_ids: list[str] = []

        for swept_id in sorted(swept):
            swept_justifications = self.justifications_by_consequent.pop(swept_id, {})
            removed_justification_ids.extend(swept_justifications.keys())
            self.dependency_graph.discard_consequent(swept_id)
            fact = self.working_memory.facts_by_id.get(swept_id)
            if fact is not None:
                self.working_memory.remove_fact(swept_id)
                removed_pairs.append((swept_id, fact.triple))

        for kept_id in sorted(kept):
            kept_justifications = self.justifications_by_consequent.get(kept_id)
            if kept_justifications is None:
                continue
            surviving_justification_ids = {
                justification_id
                for justification_id, justification in kept_justifications.items()
                if all(
                    antecedent_id not in swept
                    for antecedent_id in justification.antecedent_ids
                )
            }
            for justification_id in list(kept_justifications.keys()):
                if justification_id not in surviving_justification_ids:
                    removed_justification_ids.append(justification_id)
                    del kept_justifications[justification_id]
            if not kept_justifications:
                del self.justifications_by_consequent[kept_id]
            surviving_antecedents: set[str] = set()
            for justification in kept_justifications.values():
                surviving_antecedents.update(justification.antecedent_ids)
            self.dependency_graph.update_consequent_edges(
                kept_id, surviving_antecedents
            )

        return RetractionOutcome(
            removed_fact_ids=tuple(pair[0] for pair in removed_pairs),
            removed_triples=tuple(pair[1] for pair in removed_pairs),
            removed_justification_ids=tuple(sorted(removed_justification_ids)),
        )

    def clear(self) -> None:
        self.working_memory.clear()
        self.dependency_graph.clear()
        self.justifications_by_consequent.clear()
