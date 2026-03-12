from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from rdflib.term import Node
from rdflibr.axiom.common import Triple

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

    rule_id: RuleId
    consequent_id: str
    antecedent_ids: tuple[str, ...]
    metadata: dict[str, Any]


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
    def _justification_key(justification: Justification) -> str:
        metadata_key = "|".join(
            f"{key}={repr(value)}"
            for key, value in sorted(justification.metadata.items())
        )
        antecedents_key = ",".join(justification.antecedent_ids)
        return (
            f"{justification.rule_id.ruleset}:{justification.rule_id.rule_id}"
            f"|{antecedents_key}|{metadata_key}"
        )

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
        justification = Justification(
            rule_id=rule_id,
            consequent_id=consequent.id,
            antecedent_ids=antecedent_ids,
            metadata={
                "depth": depth,
                "bindings": self._bindings_metadata(bindings),
            },
        )
        support_key = self._justification_key(justification)
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
        return tuple(self.justifications_by_consequent.get(fact.id, {}).values())

    def support_count(self, triple: Triple) -> int:
        return len(self.justifications_for(triple))

    def is_supported(self, triple: Triple) -> bool:
        fact = self.working_memory.get_fact(triple)
        if fact is None:
            return False
        return fact.stated or self.support_count(triple) > 0

    def clear(self) -> None:
        self.working_memory.clear()
        self.dependency_graph.clear()
        self.justifications_by_consequent.clear()
