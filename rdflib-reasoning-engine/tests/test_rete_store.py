from collections.abc import Iterable
from typing import Any

import pytest
from rdflib import Dataset, Graph, Namespace
from rdflib.namespace import RDF, RDFS
from rdflib.plugins.stores.memory import Memory
from rdflib.store import VALID_STORE, Store
from rdflib.term import BNode, URIRef, Variable
from rdflibr.engine.api import RETEEngine, RETEEngineFactory
from rdflibr.engine.batch_dispatcher import TripleAddedBatchEvent
from rdflibr.engine.proof import RuleId
from rdflibr.engine.rete_store import RETEStore
from rdflibr.engine.rules import Rule, TripleCondition, TripleConsequent, TriplePattern

_NS = Namespace("https://example.org/")
_X = Variable("x")


class DummyRule(Rule):
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


class DummyEngine(RETEEngine):
    def __init__(self) -> None:
        super().__init__(context_data={}, rules=[])
        self.warmup_calls: list[list[tuple[int, int, int]]] = []
        self.add_triples_calls: list[list[tuple[int, int, int]]] = []
        self.add_triples_result: set[tuple[int, int, int]] = set()

    def add_triples(
        self, triples: Iterable[tuple[int, int, int]]
    ) -> set[tuple[int, int, int]]:  # type: ignore[override]
        materialized = list(triples)
        self.add_triples_calls.append(materialized)
        return self.add_triples_result

    def warmup(
        self, existing_triples: Iterable[tuple[int, int, int]]
    ) -> set[tuple[int, int, int]]:  # type: ignore[override]
        materialized = list(existing_triples)
        self.warmup_calls.append(materialized)
        return set(materialized)


class DummyFactory(RETEEngineFactory):
    def __init__(self) -> None:
        super().__init__()
        self.engines: dict[Any, DummyEngine] = {}

    def new_engine(self, context: Any) -> DummyEngine:  # type: ignore[override]
        engine = DummyEngine()
        self.engines[context] = engine
        return engine


class ScriptedEngine(RETEEngine):
    def __init__(
        self,
        *,
        scripted_results: dict[
            frozenset[tuple[Any, Any, Any]], set[tuple[Any, Any, Any]]
        ],
    ) -> None:
        super().__init__(context_data={}, rules=[])
        self.scripted_results = scripted_results
        self.add_triples_calls: list[set[tuple[Any, Any, Any]]] = []

    def add_triples(
        self, triples: Iterable[tuple[Any, Any, Any]]
    ) -> set[tuple[Any, Any, Any]]:  # type: ignore[override]
        materialized = set(triples)
        self.add_triples_calls.append(materialized)
        return self.scripted_results.get(frozenset(materialized), set())


class ScriptedFactory(RETEEngineFactory):
    def __init__(
        self,
        *,
        scripted_results: dict[
            frozenset[tuple[Any, Any, Any]], set[tuple[Any, Any, Any]]
        ],
    ) -> None:
        super().__init__()
        self.scripted_results = scripted_results
        self.engines: dict[Any, ScriptedEngine] = {}

    def new_engine(self, context: Any) -> ScriptedEngine:  # type: ignore[override]
        engine = ScriptedEngine(scripted_results=self.scripted_results)
        self.engines[context] = engine
        return engine


def test_rete_store_requires_context_aware_store() -> None:
    class NonContextAwareStore(Store):
        context_aware = False
        graph_aware = False

    with pytest.raises(ValueError, match="Backing store must be context-aware"):
        RETEStore(NonContextAwareStore(), DummyFactory())


def test_rete_store_initialization_and_open_warmup() -> None:
    backing = Memory()
    ds = Dataset(store=backing)
    # Ensure there is at least one context in the backing store.
    ds.default_graph.add((_NS.s, _NS.p, _NS.o))

    factory = DummyFactory()
    store = RETEStore(backing, factory)

    assert store.context_aware is True
    assert store.graph_aware == backing.graph_aware

    # Backing store.open returns a status; RETEStore.open must delegate without error.
    status = store.open(("id", "configuration"), create=True)
    assert status in (VALID_STORE, None)


def test_rete_store_on_triples_added_materializes_inferred_triples() -> None:
    backing = Memory()
    factory = DummyFactory()
    store = RETEStore(backing, factory)

    context_id = BNode()
    engine, engine_graph = store._ensure_engine(context_id)
    assert isinstance(engine, DummyEngine)

    # Configure the engine to infer a new triple.
    inferred = {(_NS.a, _NS.b, _NS.c)}
    engine.add_triples_result = inferred  # type: ignore[assignment]

    batch = TripleAddedBatchEvent(events=inferred, context_id=context_id)
    store._on_triples_added(batch)

    # The inferred triples must be materialized into the engine's context graph.
    assert all(triple in engine_graph for triple in inferred)


def test_rete_store_add_and_triples_delegate_to_backing_store() -> None:
    backing = Memory()
    factory = DummyFactory()
    store = RETEStore(backing, factory)
    ds = Dataset(store=store)

    s, p, o = _NS.s, _NS.p, _NS.o
    ds.add((s, p, o))

    triples = list(store.triples((s, p, o)))
    assert len(triples) == 1


def test_rete_store_add_graph_ensures_engine_and_delegates() -> None:
    backing = Memory()
    factory = DummyFactory()
    store = RETEStore(backing, factory)

    g = Graph(identifier=_NS.g, store=store)
    g.add((_NS.s, _NS.p, _NS.o))

    store.add_graph(g)

    # Engine must be created for the graph identifier.
    assert _NS.g in factory.engines


def test_rete_store_dataset_add_drives_batch_dispatch_and_materialization() -> None:
    backing = Memory()
    seed = (_NS.s, _NS.p, _NS.o)
    first_inference = (_NS.a, _NS.b, _NS.c)
    second_inference = (_NS.x, _NS.y, _NS.z)
    factory = ScriptedFactory(
        scripted_results={
            frozenset({seed}): {first_inference},
            frozenset({first_inference}): {second_inference},
            frozenset({second_inference}): set(),
        }
    )
    store = RETEStore(backing, factory)
    dataset = Dataset(store=store)

    dataset.default_graph.add(seed)

    engine = factory.engines[dataset.default_graph.identifier]
    assert engine.add_triples_calls == [
        set(),
        {seed},
        {first_inference},
        {second_inference},
    ]
    assert seed in dataset.default_graph
    assert first_inference in dataset.default_graph
    assert second_inference in dataset.default_graph


def test_rete_store_does_not_rematerialize_existing_inferred_triple() -> None:
    backing = Memory()
    seed = (_NS.s, _NS.p, _NS.o)
    inferred = (_NS.a, _NS.b, _NS.c)
    factory = ScriptedFactory(
        scripted_results={
            frozenset({seed}): {inferred},
            frozenset({inferred}): {inferred},
        }
    )
    store = RETEStore(backing, factory)
    dataset = Dataset(store=store)

    dataset.default_graph.add(seed)

    engine = factory.engines[dataset.default_graph.identifier]
    assert engine.add_triples_calls == [set(), {seed}, {inferred}]
    assert list(dataset.default_graph.triples(inferred)) == [inferred]


def test_rete_store_uses_real_factory_engine_to_materialize_inference() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="subclass"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=y, predicate=RDFS.subClassOf, object=z)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=z)
            ),
        ),
    )
    store = RETEStore(Memory(), RETEEngineFactory(rules=[rule]))
    dataset = Dataset(store=store)
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")

    dataset.default_graph.add((alice, RDF.type, human))
    dataset.default_graph.add((human, RDFS.subClassOf, mammal))

    assert (alice, RDF.type, mammal) in dataset.default_graph
