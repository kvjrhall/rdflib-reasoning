from collections.abc import Iterable

import pytest
from rdflib.term import BNode
from rdflibr.engine.api import RETEEngine, RETEEngineFactory
from rdflibr.engine.proof import RuleId
from rdflibr.engine.rules import ContextData, Rule


class DummyRule(Rule):
    """Concrete Rule subclass for type-checking purposes."""

    id: RuleId = RuleId(ruleset="test", rule_id="dummy-rule")


class WarmupEngine(RETEEngine):
    """Concrete RETEEngine that implements add_triples for testing warmup."""

    def __init__(self, context_data: ContextData, rules: Iterable[Rule]) -> None:
        super().__init__(context_data=context_data, rules=rules)
        self.add_triples_called_with: list[list[tuple[int, int, int]]] = []

    def add_triples(
        self, triples: Iterable[tuple[int, int, int]]
    ) -> set[tuple[int, int, int]]:  # type: ignore[override]
        materialized = list(triples)
        self.add_triples_called_with.append(materialized)
        # Echo the input triples back as "inferred" for easy assertions.
        return set(materialized)


def test_rete_engine_init_and_close() -> None:
    context = BNode()
    context_data: ContextData = {"context": context}
    rules: list[Rule] = [
        DummyRule(id=RuleId(ruleset="test", rule_id="dummy-rule-1")),
        DummyRule(id=RuleId(ruleset="test", rule_id="dummy-rule-2")),
    ]

    engine = RETEEngine(context_data=context_data, rules=rules)

    assert engine.context_data is context_data
    assert engine.rules == tuple(rules)

    # close() is currently a no-op but should be callable.
    engine.close()


def test_rete_engine_warmup_uses_add_triples() -> None:
    context = BNode()
    context_data: ContextData = {"context": context}
    rules: list[Rule] = []
    engine = WarmupEngine(context_data=context_data, rules=rules)

    existing_triples = [(1, 2, 3), (4, 5, 6)]

    inferred = engine.warmup(existing_triples)

    # warmup must delegate to add_triples and return its results.
    assert inferred == set(existing_triples)
    assert engine.add_triples_called_with == [existing_triples]


def test_rete_engine_factory_rejects_context_keyword() -> None:
    with pytest.raises(ValueError, match="context is a reserved keyword"):
        RETEEngineFactory(context="not-allowed")


def test_rete_engine_factory_context_template_is_preserved() -> None:
    factory = RETEEngineFactory(foo="bar", answer=42)

    assert factory.context_template == {"foo": "bar", "answer": 42}
