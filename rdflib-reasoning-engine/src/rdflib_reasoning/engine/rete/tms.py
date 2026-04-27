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

    def clear(self) -> None:
        self.facts_by_id.clear()
        self.fact_ids_by_triple.clear()


class TMSController(BaseModel):
    """
    Controller for truth-maintenance bookkeeping and recursive retraction.

    Retraction remains future work, but the controller scaffold marks the
    boundary that add-only implementations should remain compatible with.
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

    def clear(self) -> None:
        self.working_memory.clear()
        self.dependency_graph.clear()
        self.justifications_by_consequent.clear()
