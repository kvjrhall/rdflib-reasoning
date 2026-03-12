from collections.abc import Iterable

import pytest
from rdflib.namespace import RDF, RDFS
from rdflib.term import BNode, URIRef, Variable
from rdflibr.engine.api import RETEEngine, RETEEngineFactory
from rdflibr.engine.proof import RuleId
from rdflibr.engine.rules import (
    ContextData,
    PredicateCondition,
    PredicateHook,
    Rule,
    RuleContext,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)

_X = Variable("x")


class DummyRule(Rule):
    """Concrete Rule subclass for type-checking purposes."""

    id: RuleId = RuleId(ruleset="test", rule_id="dummy-rule")
    body: tuple[TripleCondition, ...] = (
        TripleCondition(
            pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_X)
        ),
    )
    head: tuple[TripleConsequent, ...] = (
        TripleConsequent(
            pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_X)
        ),
    )


class WarmupEngine(RETEEngine):
    """Concrete RETEEngine that implements add_triples for testing warmup."""

    def __init__(self, context_data: ContextData, rules: Iterable[Rule]) -> None:
        super().__init__(context_data=context_data, rules=rules)
        self.add_triples_called_with: list[list[tuple[int, int, int]]] = []

    def add_triples(  # type: ignore[override]
        self, triples: Iterable[tuple[int, int, int]]
    ) -> set[tuple[int, int, int]]:  # type: ignore[override]
        materialized = list(triples)
        self.add_triples_called_with.append(materialized)
        # Echo the input triples back as "inferred" for easy assertions.
        return set(materialized)


class SameTermPredicate(PredicateHook):
    def test(self, context: RuleContext, *args: URIRef) -> bool:  # type: ignore[override]
        _ = context
        return len(args) == 2 and args[0] == args[1]


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

    inferred = engine.warmup(existing_triples)  # type: ignore[arg-type]

    # warmup must delegate to add_triples and return its results.
    assert inferred == set(existing_triples)
    assert engine.add_triples_called_with == [existing_triples]


def test_rete_engine_factory_rejects_context_keyword() -> None:
    with pytest.raises(ValueError, match="context is a reserved keyword"):
        RETEEngineFactory(context="not-allowed")


def test_rete_engine_factory_context_template_is_preserved() -> None:
    factory = RETEEngineFactory(foo="bar", answer=42)

    assert factory.context_template == {"foo": "bar", "answer": 42}


def test_rete_engine_add_triples_materializes_inference_to_fixed_point() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    rules: list[Rule] = [
        Rule(
            id=RuleId(ruleset="test", rule_id="subclass"),
            description=None,
            body=(
                TripleCondition(
                    pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
                ),
                TripleCondition(
                    pattern=TriplePattern(
                        subject=y, predicate=RDFS.subClassOf, object=z
                    )
                ),
            ),
            head=(
                TripleConsequent(
                    pattern=TriplePattern(subject=x, predicate=RDF.type, object=z)
                ),
            ),
        )
    ]
    engine = RETEEngine(context_data={"context": BNode()}, rules=rules)
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    animal = URIRef("urn:test:Animal")
    alice = URIRef("urn:test:alice")

    inferred = engine.add_triples(
        [
            (alice, RDF.type, human),
            (human, RDFS.subClassOf, mammal),
            (mammal, RDFS.subClassOf, animal),
        ]
    )

    assert inferred == {
        (alice, RDF.type, mammal),
        (alice, RDF.type, animal),
    }


def test_rete_engine_add_triples_is_idempotent_for_known_triples() -> None:
    x = Variable("x")
    y = Variable("y")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="copy-type"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
        ),
    )
    engine = RETEEngine(context_data={"context": BNode()}, rules=[rule])
    triple = (URIRef("urn:test:a"), RDF.type, URIRef("urn:test:A"))

    assert engine.add_triples([triple]) == set()
    assert engine.add_triples([triple]) == set()


def test_rete_engine_add_triples_supports_builtin_predicates() -> None:
    x = Variable("x")
    y = Variable("y")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="same-term"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
            PredicateCondition(predicate="same_term", arguments=(x, x)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDFS.subClassOf, object=y)
            ),
        ),
    )
    context_data: ContextData = {
        "context": BNode(),
        "builtins": {"predicates": {"same_term": SameTermPredicate()}},
    }
    engine = RETEEngine(context_data=context_data, rules=[rule])
    triple = (URIRef("urn:test:a"), RDF.type, URIRef("urn:test:A"))

    inferred = engine.add_triples([triple])

    assert inferred == {(URIRef("urn:test:a"), RDFS.subClassOf, URIRef("urn:test:A"))}
