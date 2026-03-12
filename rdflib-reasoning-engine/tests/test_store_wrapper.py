from collections.abc import Iterable
from typing import Any

from rdflib import Dataset, Namespace
from rdflib.plugins.stores.memory import Memory
from rdflib.term import BNode
from rdflibr.engine.api import RETEEngine, RETEEngineFactory
from rdflibr.engine.batch_dispatcher import TripleAddedBatchEvent
from rdflibr.engine.store_wrapper import StoreWrapper

_NS = Namespace("https://example.org/")


class DummyEngine(RETEEngine):
    def __init__(self) -> None:
        super().__init__(context_data={}, rules=[])
        self.add_triples_calls: list[list[tuple[int, int, int]]] = []

    def add_triples(
        self, triples: Iterable[tuple[int, int, int]]
    ) -> set[tuple[int, int, int]]:  # type: ignore[override]
        materialized = list(triples)
        self.add_triples_calls.append(materialized)
        return set(materialized)


class DummyFactory(RETEEngineFactory):
    def __init__(self) -> None:
        super().__init__()
        self.engines: dict[Any, DummyEngine] = {}

    def new_engine(self, context: Any) -> DummyEngine:  # type: ignore[override]
        engine = DummyEngine()
        self.engines[context] = engine
        return engine


def test_store_wrapper_initialization_matches_backing_store() -> None:
    backing = Memory()
    factory = DummyFactory()

    wrapper = StoreWrapper(backing, factory)

    assert wrapper.store is backing
    assert wrapper.factory is factory
    assert wrapper.context_aware == backing.context_aware
    assert wrapper.graph_aware == backing.graph_aware
    assert wrapper.transaction_aware == backing.transaction_aware


def test_store_wrapper_get_engine_caches_per_context() -> None:
    backing = Memory()
    factory = DummyFactory()
    wrapper = StoreWrapper(backing, factory)

    context_id = BNode()

    engine1 = wrapper._get_engine(context_id)
    engine2 = wrapper._get_engine(context_id)

    assert engine1 is engine2
    # Factory should only be asked to create one engine for this context.
    assert factory.engines[context_id] is engine1


def test_store_wrapper_on_triples_added_is_subscribed() -> None:
    backing = Memory()
    factory = DummyFactory()
    wrapper = StoreWrapper(backing, factory)

    context_id = BNode()
    events = {(_NS.s, _NS.p, _NS.o)}
    batch = TripleAddedBatchEvent(events=events, context_id=context_id)

    # The current implementation is intentionally minimal; the callback must be callable.
    wrapper._on_triples_added(batch)


def test_store_wrapper_delegates_to_backing_store() -> None:
    backing = Memory()
    factory = DummyFactory()
    wrapper = StoreWrapper(backing, factory)
    ds = Dataset(store=wrapper)

    s, p, o = _NS.s, _NS.p, _NS.o
    ds.add((s, p, o))

    triples = list(wrapper.triples((s, p, o)))
    assert len(triples) == 1
