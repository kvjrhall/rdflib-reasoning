# Store Event Ownership and BatchDispatcher Source Decoupling

## Status

Accepted

## Context

The `BatchDispatcher` introduced as part of the engine's update contract
([DR-004](DR-004%20RETE%20Store%20Persistence%20and%20Engine%20Update%20Contract.md))
batches `TripleAddedEvent` and `TripleRemovedEvent` from a backing
`rdflib.store.Store` into per-context fixed-point batch events that
`RETEStore` consumes. Until now, `BatchDispatcher` subscribed directly to
the backing store's own `Dispatcher`:

```python
backing_store.dispatcher.subscribe(TripleAddedEvent, self._on_triple_added)
backing_store.dispatcher.subscribe(TripleRemovedEvent, self._on_triple_removed)
```

This bound the engine to a contract that the validated backing store
(`rdflib.plugins.stores.memory.Memory`) honors only by accident on the add
path and violates outright on the remove path:

- `Memory.add` calls `Store.add(self, triple, context, quoted=quoted)` as
  its first line, which dispatches `TripleAddedEvent` pre-mutation. The
  contract is satisfied incidentally, not because `Memory` was authored
  against it.
- `Memory.remove` does NOT call `Store.remove(self, ...)` on the base
  class, so it never dispatches `TripleRemovedEvent`. PR B
  ([DR-025](DR-025%20RETE%20Store%20Removal%20Wiring%20and%20Re-Materialization%20Policy.md))
  worked around this by having `RETEStore.remove` snapshot pattern matches
  and emit `TripleRemovedEvent` itself before delegating to
  `self.store.remove`.

The PR B workaround established the right pattern for one half of the
contract while leaving the add path implicitly coupled to a quirk of the
validated backing store. The two halves should follow a single explicit
policy: `RETEStore` owns the engine-visible event lifecycle for every
mutation, and the backing store is treated as opaque persistence whose
own dispatcher is irrelevant to the engine.

## Decision

`RETEStore` owns the raw `TripleAddedEvent` and `TripleRemovedEvent`
emission for every mutation it performs. `BatchDispatcher` subscribes to
a caller-provided source `Dispatcher` rather than the backing store's
dispatcher. The backing store's dispatcher is no longer consumed by the
engine.

### BatchDispatcher contract

`BatchDispatcher.__init__` accepts two keyword-only arguments:

```python
def __init__(
    self,
    *,
    source_dispatcher: Dispatcher,
    backing_store: Store,
) -> None: ...
```

- `source_dispatcher` is the dispatcher on which raw `TripleAddedEvent`
  and `TripleRemovedEvent` are emitted by the caller (in this codebase,
  always `RETEStore._raw_dispatcher`). `BatchDispatcher` subscribes its
  `_on_triple_added` / `_on_triple_removed` handlers to this dispatcher.
- `backing_store` is retained solely for the read-only `_exists_in_store`
  dedup check, which uses the standard `Store.contexts(triple)` API. The
  backing store's own dispatcher is never read.

The pre-mutation event semantic is preserved: callers MUST emit one
`TripleAddedEvent` (resp. `TripleRemovedEvent`) per mutation BEFORE the
mutation reaches the backing store, so that `_exists_in_store(triple,
context_id)` correctly reports "already present" for adds and "still
present" for removes.

### RETEStore wiring

`RETEStore.__init__` instantiates a private `Dispatcher` and threads it
through to `BatchDispatcher`:

```python
self._raw_dispatcher = Dispatcher()
self.dispatcher = BatchDispatcher(
    source_dispatcher=self._raw_dispatcher,
    backing_store=store,
)
```

The public `RETEStore.dispatcher` continues to be the `BatchDispatcher`,
preserving the existing batch-event subscription surface
(`TripleAddedBatchEvent`, `TripleRemovedBatchEvent`). The `_raw_dispatcher`
is private and not part of the public API.

`RETEStore.add`, `RETEStore.addN`, and `RETEStore.remove` each emit raw
events on `self._raw_dispatcher` BEFORE delegating to the backing store:

- `add(triple, context, quoted=False)` emits one `TripleAddedEvent` then
  delegates to `self.store.add`.
- `addN(quads)` materializes the iterable into a list, emits one
  `TripleAddedEvent` per quad, then delegates to `self.store.addN`.
- `remove(triple_pattern, context)` keeps the snapshot/emit/delegate
  shape from PR B, emitting on `self._raw_dispatcher` instead of
  `self.store.dispatcher`.

The pattern-based remove path continues to use
`self.store.triples(pattern, context)` to enumerate concrete matches
before any mutation, so each emitted event names a fully ground triple.

### Idempotence and dedup

DR-004's add-side idempotence (`engine.add_triples` is a no-op for
already-known triples) and DR-025's remove-side idempotence
(`engine.retract_triples` returns the empty set for already-absent
triples) are unaffected. `BatchDispatcher`'s `_exists_in_store` check
remains the single dedup point: events whose triples are already in the
backing store at the requested context are filtered before reaching any
batch subscriber.

### Non-goals

- This decision does not formalize a new `Store` API surface. The
  `Store.add`, `Store.addN`, `Store.remove`, `Store.triples`, and
  `Store.contexts` methods remain the only backing-store entry points
  the engine relies on.
- `RETEStore.update` and `RETEStore.remove_graph` remain
  `NotImplementedError`. SPARQL Update and graph-lifecycle removal are
  out of scope.
- Filing an upstream rdflib bug for `Memory.remove` not dispatching
  `TripleRemovedEvent` is a possible follow-up but is not blocking. The
  engine no longer depends on either backing-store dispatcher behavior.

## Consequences

The engine becomes incidentally compatible with any context-aware
`Store` implementation, including stores that do not dispatch
`TripleAddedEvent` / `TripleRemovedEvent` on their own dispatchers, as
long as their mutation methods perform the requested mutation and
their `triples` / `contexts` queries are consistent. The PR B workaround
for `Memory.remove` becomes the general policy.

The backing store's dispatcher is no longer subscribed by the engine.
Stores that DO dispatch their own events (such as `Memory.add` via
`Store.add(self, ...)`) continue to do so; those events fall on the
floor as far as the engine is concerned. External consumers that
previously subscribed to `backing_store.dispatcher` for raw events
remain free to do so independently of the engine, but they will only
observe events that the backing store itself emits, which is now a
backing-store-specific behavior and not a contract the engine relies on.

DR-004's add-side update contract and DR-025's removal wiring and
re-materialization-with-warning policy continue to apply unchanged.
DR-025's "Store wiring" section is updated with a back-reference to this
decision so that the manual emission described there is understood as
an instance of the general policy rather than a special-case workaround.
