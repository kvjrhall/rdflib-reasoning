from collections.abc import Iterable
from typing import Any

import pytest
from rdflib import Dataset, Graph, Namespace
from rdflib.plugins.stores.memory import Memory
from rdflib.store import VALID_STORE, Store
from rdflib.term import BNode
from rdflibr.engine.batch_dispatcher import TripleAddedBatchEvent
from rdflibr.engine.rete_engine import RETEEngine, RETEEngineFactory, Rule
from rdflibr.engine.rete_store import RETEStore

_NS = Namespace("https://example.org/")


class DummyRule(Rule):
    pass


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
