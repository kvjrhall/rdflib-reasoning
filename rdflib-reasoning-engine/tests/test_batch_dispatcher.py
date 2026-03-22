"""Tests for BatchDispatcher: store event behavior and inference entrypoint.

These tests clarify when and how store events are emitted during various
addition operations, and document the entrypoint for the inference engine
(store events → BatchDispatcher → batch events → fixed point). The suite is
validated only against rdflib.plugins.stores.memory.Memory; other stores
are not asserted. See BatchDispatcher docstring and docs/dev/architecture.md
(Engine event contract and entrypoint) for the store event contract.
"""

import unittest.mock as mock
from collections.abc import Generator
from typing import Any

import pytest
from rdflib import Dataset, Graph, Namespace
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID
from rdflib.plugins.stores.memory import Memory
from rdflib.store import Store, TripleAddedEvent, TripleRemovedEvent
from rdflib_reasoning.engine.batch_dispatcher import (
    BatchDispatcher,
    TripleAddedBatchEvent,
    TripleRemovedBatchEvent,
)

type TestData[T] = Generator[T, Any, Any]


_NS = Namespace("https://example.org/")

POPULATED_TURTLE_DATA = f"""
    PREFIX : <{_NS}>

    :a :b :c .
    :d :e :f .
    :d :g :h .
    """


@pytest.fixture
def empty_store() -> TestData[Store]:
    yield Memory()


@pytest.fixture
def store() -> TestData[Store]:
    s = Memory()
    ds = Dataset(store=s)
    ds.parse(data=POPULATED_TURTLE_DATA, format="ttl")
    yield s


def create_dispatcher(store: Store) -> BatchDispatcher:
    dispatcher = BatchDispatcher(backing_store=store)
    return dispatcher


class BatchCollector:
    added_batches: list[TripleAddedBatchEvent]
    removed_batches: list[TripleRemovedBatchEvent]

    def __init__(self, dispatcher: BatchDispatcher) -> None:
        self.added_batches = []
        self.removed_batches = []
        dispatcher.subscribe(TripleAddedBatchEvent, self.on_added_batch)
        dispatcher.subscribe(TripleRemovedBatchEvent, self.on_removed_batch)

    def on_added_batch(self, batch: TripleAddedBatchEvent) -> None:
        self.added_batches.append(batch)

    def on_removed_batch(self, batch: TripleRemovedBatchEvent) -> None:
        self.removed_batches.append(batch)


def test_add_to_default_graph_by_dataset(empty_store: Store) -> None:
    dispatcher = create_dispatcher(empty_store)
    listener = BatchCollector(dispatcher)
    dataset = Dataset(store=empty_store)

    s, p, o = _NS.s, _NS.p, _NS.o

    dataset.add((s, p, o))  # Added to default graph through dataset

    assert len(listener.added_batches) == 1
    assert listener.added_batches[0].context_id == DATASET_DEFAULT_GRAPH_ID
    assert listener.added_batches[0].events == {(s, p, o)}


def test_reentrant_add_to_default_graph_by_dataset(empty_store: Store) -> None:
    dispatcher = create_dispatcher(empty_store)
    listener = BatchCollector(dispatcher)
    dataset = Dataset(store=empty_store)

    g = dataset.default_graph
    quads = [
        (_NS.s, _NS.p, _NS.o, g),
        (_NS.d, _NS.e, _NS.f, g),
        (_NS.d, _NS.g, _NS.h, g),
    ]

    called = False

    def on_batch(_: TripleAddedBatchEvent) -> None:
        nonlocal called
        if not called:
            called = True
            empty_store.add(quads[1][:3], quads[1][3])
            empty_store.add(quads[2][:3], quads[2][3])

    dispatcher.subscribe(TripleAddedBatchEvent, on_batch)

    dataset.add(quads[0][:3])  # Add a single triple to the default graph

    assert len(listener.added_batches) == 2
    assert listener.added_batches[0].context_id == g.identifier
    assert listener.added_batches[0].events == {quads[0][:3]}

    # The update taking place mid-batch should be added to the next batch and then processed before returning
    assert listener.added_batches[1].context_id == g.identifier
    assert listener.added_batches[1].events == {quads[1][:3], quads[2][:3]}


def test_reentrant_add_to_different_context_is_not_stranded(empty_store: Store) -> None:
    """Reentrant additions in another context must also drain before returning."""
    dispatcher = create_dispatcher(empty_store)
    listener = BatchCollector(dispatcher)
    dataset = Dataset(store=empty_store)

    default_graph = dataset.default_graph
    other_graph = dataset.graph(_NS.g)
    initial = (_NS.s, _NS.p, _NS.o)
    inferred = (_NS.d, _NS.e, _NS.f)
    called = False

    def on_batch(_: TripleAddedBatchEvent) -> None:
        nonlocal called
        if called:
            return
        called = True
        other_graph.add(inferred)

    dispatcher.subscribe(TripleAddedBatchEvent, on_batch)

    default_graph.add(initial)

    assert len(listener.added_batches) == 2
    assert listener.added_batches[0].context_id == default_graph.identifier
    assert listener.added_batches[0].events == {initial}
    assert listener.added_batches[1].context_id == other_graph.identifier
    assert listener.added_batches[1].events == {inferred}


def test_add_to_default_graph_by_graph(empty_store: Store) -> None:
    dispatcher = create_dispatcher(empty_store)
    listener = BatchCollector(dispatcher)
    dataset = Dataset(store=empty_store)

    s, p, o = _NS.s, _NS.p, _NS.o

    dataset.default_graph.add((s, p, o))

    assert len(listener.added_batches) == 1
    assert listener.added_batches[0].context_id == DATASET_DEFAULT_GRAPH_ID
    assert listener.added_batches[0].events == {(s, p, o)}


def test_add_to_default_graph_by_quad(empty_store: Store) -> None:
    dispatcher = create_dispatcher(empty_store)
    listener = BatchCollector(dispatcher)
    dataset = Dataset(store=empty_store)

    s, p, o, g = _NS.s, _NS.p, _NS.o, dataset.default_graph

    dataset.add((s, p, o, g))

    assert len(listener.added_batches) == 1
    assert listener.added_batches[0].context_id == g.identifier
    assert listener.added_batches[0].events == {(s, p, o)}


def test_addN_to_default_graph_by_quad(empty_store: Store) -> None:
    """Memory emits one TripleAddedEvent per triple in addN; we get one batch per triple."""
    dispatcher = create_dispatcher(empty_store)
    listener = BatchCollector(dispatcher)
    dataset = Dataset(store=empty_store)

    g = dataset.default_graph
    quads = set(
        [
            (_NS.s, _NS.p, _NS.o, g),
            (_NS.d, _NS.e, _NS.f, g),
            (_NS.d, _NS.g, _NS.h, g),
        ]
    )
    triples = {q[:3] for q in quads}

    dataset.addN(quads)

    # Memory emits per triple, so we get one batch per triple. A store that batched
    # events for addN would yield a single batch; the inference entrypoint supports both.
    assert len(listener.added_batches) == 3
    assert listener.added_batches[0].context_id == g.identifier
    assert set().union(*(b.events for b in listener.added_batches)) == triples


def test_addN_to_new_graph_by_quad(empty_store: Store) -> None:
    """addN to a new context creates the graph implicitly; Memory emits per triple."""
    with mock.patch.object(
        empty_store,
        "add_graph",
        wraps=empty_store.add_graph,
    ) as wrapped_add_graph:
        dispatcher = create_dispatcher(empty_store)
        listener = BatchCollector(dispatcher)
        dataset = Dataset(store=empty_store)

        g = Graph(identifier="https://example.org/g")
        quads = set(
            [
                (_NS.s, _NS.p, _NS.o, g),
                (_NS.d, _NS.e, _NS.f, g),
                (_NS.d, _NS.g, _NS.h, g),
            ]
        )
        triples = {q[:3] for q in quads}

        dataset.addN(quads)

        assert not wrapped_add_graph.called

    # The graph was created just by adding the quads to the dataset.
    # We MUST NOT assume that add_graph is part of the lifecycle of the graph.
    for q in quads:
        assert (gid := dataset.get_graph(g.identifier)) is not None
        assert (q[0], q[1], q[2]) in gid

    # The original graph g is not stored by the dataset; the dataset creates its own.
    # We MUST NOT treat the context of a quad as the materialization destination.
    for q in quads:
        assert (q[0], q[1], q[2]) not in g

    assert len(listener.added_batches) == 3
    assert listener.added_batches[0].context_id == g.identifier
    assert set().union(*(b.events for b in listener.added_batches)) == triples


def test_triple_added_event_deduplication(empty_store: Store) -> None:
    """TripleAddedEvent subscribers on BatchDispatcher receive only de-duplicated events.

    The dispatcher forwards TripleAddedEvent to its subscribers (lines 106–108) only
    when the triple is not already in the context. Adding the same triple twice
    must result in exactly one call to the subscriber.
    """
    dispatcher = create_dispatcher(empty_store)
    received: list[TripleAddedEvent] = []

    def on_triple_added(event: TripleAddedEvent) -> None:
        received.append(event)

    dispatcher.subscribe(TripleAddedEvent, on_triple_added)

    dataset = Dataset(store=empty_store)
    s, p, o = _NS.s, _NS.p, _NS.o

    dataset.add((s, p, o))
    dataset.add((s, p, o))  # duplicate add; should not forward second event

    assert len(received) == 1
    assert received[0].triple == (s, p, o)  # type: ignore[attr-defined]
    assert received[0].context.identifier == DATASET_DEFAULT_GRAPH_ID  # type: ignore[attr-defined]


def test_duplicate_add_quad_out_of_store_graph_no_second_batch(
    empty_store: Store,
) -> None:
    """Duplicate add with out-of-store graph: only one batch (second add filtered).

    When the context is an out-of-store Graph (same identifier as the store's
    graph but a different object), the dispatcher must filter using the store's
    view (e.g. backing_store.contexts(triple)), not event.context. We call the
    store directly so g is never populated; the implementation filters the
    second add because the triple is already in the store for that context_id.
    """
    dispatcher = create_dispatcher(empty_store)
    listener = BatchCollector(dispatcher)

    g = Graph(identifier="https://example.org/g")
    triple = (_NS.s, _NS.p, _NS.o)

    empty_store.add(triple, g)
    empty_store.add(triple, g)  # duplicate add; g is never populated by store

    assert len(listener.added_batches) == 1
    assert listener.added_batches[0].context_id == g.identifier
    assert listener.added_batches[0].events == {triple}


def test_reentrant_add_out_of_store_graph_fixed_point(empty_store: Store) -> None:
    """Reentrant adds with out-of-store graph: fixed point after 2 batches.

    Like test_reentrant_add_to_default_graph_by_dataset but using an out-of-store
    graph g as context. We call the store directly so g is never populated. First
    batch triggers the handler which adds two more triples; the second batch
    contains those two; then fixed point (no further batches). Filtering uses the
    store's view, so reentrant adds are correctly deduplicated. We cap times_called
    at 2 so the handler does not add indefinitely.
    """
    dispatcher = create_dispatcher(empty_store)
    listener = BatchCollector(dispatcher)

    g = Graph(identifier="https://example.org/g")
    quads = [
        (_NS.s, _NS.p, _NS.o, g),
        (_NS.d, _NS.e, _NS.f, g),
        (_NS.d, _NS.g, _NS.h, g),
    ]
    times_called: int = 0

    def on_batch(_: TripleAddedBatchEvent) -> None:
        nonlocal times_called
        if times_called >= 2:
            return
        # Re-add the same two triples when times_called < 2 to drive a second batch.
        empty_store.add(quads[1][:3], quads[1][3])
        empty_store.add(quads[2][:3], quads[2][3])
        times_called += 1

    dispatcher.subscribe(TripleAddedBatchEvent, on_batch)

    empty_store.add(
        quads[0][:3], g
    )  # single triple; g is out-of-store and never populated

    assert len(listener.added_batches) == 2
    assert listener.added_batches[0].context_id == g.identifier
    assert listener.added_batches[0].events == {quads[0][:3]}
    assert listener.added_batches[1].context_id == g.identifier
    assert listener.added_batches[1].events == {quads[1][:3], quads[2][:3]}


def test_add_graph(empty_store: Store) -> None:
    """Adding a graph with triples: Memory emits one TripleAddedEvent per triple."""
    dispatcher = create_dispatcher(empty_store)
    listener = BatchCollector(dispatcher)
    dataset = Dataset(store=empty_store)

    g = Graph(identifier="https://example.org/g")
    quads = set(
        [
            (_NS.s, _NS.p, _NS.o, g),
            (_NS.d, _NS.e, _NS.f, g),
            (_NS.d, _NS.g, _NS.h, g),
        ]
    )
    triples = {q[:3] for q in quads}
    g.addN(quads)

    dataset.add_graph(g)

    assert len(listener.added_batches) == 3
    assert listener.added_batches[0].context_id == g.identifier
    assert set().union(*(b.events for b in listener.added_batches)) == triples


def test_triple_removed_event_single_batch_via_dispatcher() -> None:
    """_on_triple_removed emits a single batch for a present triple.

    rdflib's Memory store does not currently emit TripleRemovedEvent, so we
    exercise the removal path by calling _on_triple_removed directly and
    controlling the store-membership check.
    """
    backing = Memory()
    dispatcher = create_dispatcher(backing)
    listener = BatchCollector(dispatcher)

    g = Graph(identifier="https://example.org/g")
    triple = (_NS.s, _NS.p, _NS.o)
    event = TripleRemovedEvent(triple=triple, context=g)

    with mock.patch.object(
        dispatcher, "_exists_in_store", autospec=True, return_value=True
    ):
        dispatcher._on_triple_removed(event)  # type: ignore[attr-defined]

    assert len(listener.removed_batches) == 1
    batch = listener.removed_batches[0]
    assert batch.context_id == g.identifier
    assert batch.events == {triple}


def test_triple_removed_event_deduplicated_via_exists_in_store() -> None:
    """Second removal event is filtered when the triple is already absent."""
    backing = Memory()
    dispatcher = create_dispatcher(backing)
    listener = BatchCollector(dispatcher)

    g = Graph(identifier="https://example.org/g")
    triple = (_NS.s, _NS.p, _NS.o)
    event = TripleRemovedEvent(triple=triple, context=g)

    with mock.patch.object(
        dispatcher,
        "_exists_in_store",
        autospec=True,
        side_effect=[True, False],
    ):
        dispatcher._on_triple_removed(event)  # type: ignore[attr-defined]
        dispatcher._on_triple_removed(event)  # type: ignore[attr-defined]

    assert len(listener.removed_batches) == 1
    batch = listener.removed_batches[0]
    assert batch.context_id == g.identifier
    assert batch.events == {triple}


def test_triple_removed_event_different_context_is_not_stranded() -> None:
    """Reentrant removals in another context must also drain before returning."""
    backing = Memory()
    dispatcher = create_dispatcher(backing)
    listener = BatchCollector(dispatcher)

    g1 = Graph(identifier="https://example.org/g1")
    g2 = Graph(identifier="https://example.org/g2")
    triple_1 = (_NS.s, _NS.p, _NS.o)
    triple_2 = (_NS.d, _NS.e, _NS.f)
    event_1 = TripleRemovedEvent(triple=triple_1, context=g1)
    event_2 = TripleRemovedEvent(triple=triple_2, context=g2)
    called = False

    def on_removed_batch(_: TripleRemovedBatchEvent) -> None:
        nonlocal called
        if called:
            return
        called = True
        dispatcher._on_triple_removed(event_2)  # type: ignore[attr-defined]

    dispatcher.subscribe(TripleRemovedBatchEvent, on_removed_batch)

    with mock.patch.object(
        dispatcher,
        "_exists_in_store",
        autospec=True,
        side_effect=[True, True],
    ):
        dispatcher._on_triple_removed(event_1)  # type: ignore[attr-defined]

    assert len(listener.removed_batches) == 2
    assert listener.removed_batches[0].context_id == g1.identifier
    assert listener.removed_batches[0].events == {triple_1}
    assert listener.removed_batches[1].context_id == g2.identifier
    assert listener.removed_batches[1].events == {triple_2}


def test_batch_dispatcher_resets_handling_flag_after_batch_subscriber_error(
    empty_store: Store,
) -> None:
    """A failing batch subscriber must not leave the dispatcher wedged."""
    dispatcher = create_dispatcher(empty_store)
    dataset = Dataset(store=empty_store)
    failures = 0

    def raising_subscriber(_: TripleAddedBatchEvent) -> None:
        nonlocal failures
        failures += 1
        raise RuntimeError("boom")

    dispatcher.subscribe(TripleAddedBatchEvent, raising_subscriber)

    with pytest.raises(RuntimeError, match="boom"):
        dataset.default_graph.add((_NS.s, _NS.p, _NS.o))

    assert dispatcher._handling_addition is False
    assert dispatcher._dispatch_map is not None
    dispatcher._dispatch_map[TripleAddedBatchEvent].remove(raising_subscriber)
    listener = BatchCollector(dispatcher)

    dataset.default_graph.add((_NS.d, _NS.e, _NS.f))

    assert failures == 1
    assert len(listener.added_batches) == 1
    assert listener.added_batches[0].events == {(_NS.d, _NS.e, _NS.f)}


def test_add_by_SPARQL_update(empty_store: Store) -> None:
    """Reserved for future SPARQL Update event behavior."""
    pytest.skip("Not implemented")
