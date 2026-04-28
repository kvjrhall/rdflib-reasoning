# RETE Store Removal Wiring and Re-Materialization Policy

## Status

Accepted

## Context

The staged truth-maintenance plan in
[`docs/dev/architecture.md`](../architecture.md) sequences support recording
(stage 1), support verification ([DR-023](DR-023%20JTMS%20Support%20Verification%20API%20Surface.md)),
recursive Mark-Verify-Sweep retraction at the TMS-controller layer
([DR-024](DR-024%20TMSController%20Recursive%20Retraction.md)), and removal
wiring through the supported store integration path (stage 4).

This decision specifies stage (4): `RETEEngine.retract_triples`,
`RETEStore.remove`, and the `TripleRemovedBatchEvent` subscription that ties
DR-024's TMS primitive to the `Store` event contract used by `BatchDispatcher`,
`RETEStore`, and `RETEEngine` in
[DR-004](DR-004%20RETE%20Store%20Persistence%20and%20Engine%20Update%20Contract.md).

When a removal arrives via the store/graph API, two cases produce a divergence
between the engine's logical closure and the backing store:

- **Stated-and-derived:** a triple `T` is asserted by the user and also has at
  least one valid `Justification`. `TMSController.retract_triple` clears the
  `stated` flag, leaves `T` in working memory as derived, and reports `T` in
  `unstated_fact_ids`. The dispatcher event is pre-mutation, so the backing
  store is about to drop `T` regardless.
- **Derived-only:** the user removes a previously materialized inference
  whose working-memory fact is derived only. `TMSController.retract_triple`
  raises `ValueError` because direct retraction of a derived fact violates
  the JTMS invariant in `architecture.md` (derived facts are removed if and
  only if their justification set becomes empty).

A coherent policy must specify what `RETEStore` does in both cases without
violating the JTMS support invariants and without producing an unbounded
event loop through `BatchDispatcher`.

## Decision

### Engine API

`RETEEngine.retract_triples` is implemented as a batch entry point with the
signature:

```python
def retract_triples(self, triples: Iterable[Triple]) -> set[Triple]:
    """Retract triples; return all triples that left the logical closure."""
```

For each input triple, the engine looks up the working-memory `Fact`. If the
fact is absent, the input is skipped. If `fact.stated` is True, the engine
calls `TMSController.retract_triple(triple)` and consumes the resulting
`RetractionOutcome`. If the fact is derived only, the engine applies the
re-materialization policy below without invoking the TMS primitive.

After all TMS calls finish, the engine evicts stale partial matches from the
RETE network, updates `known_triples` and `materialized_triples`, and returns
the union of (a) input triples whose working-memory fact was actually removed
and (b) cascade consequents removed by Mark-Verify-Sweep. Triples reported in
`unstated_fact_ids`, and derived-only triples handled by the re-materialization
policy, MUST NOT appear in the returned set; the engine still believes them.

`retract_triples` MUST be idempotent for already-absent triples. A second call
with the same input MUST be a no-op and MUST return an empty set. This is the
symmetric counterpart of DR-004's requirement that `add_triples` is idempotent
for already-known triples; `BatchDispatcher` relies on this symmetry to
converge cascade events without an explicit reentrancy guard.

### Re-materialization with warning

When a removal would leave the engine and the backing store in disagreement
about a triple `T` that the engine still believes, the engine's belief wins:

- For a stated-and-derived `T`, `TMSController.retract_triple` clears the
  `stated` flag; `T` remains in working memory as derived.
- For a derived-only `T`, the engine leaves working memory unchanged.

In both cases `RETEEngine.retract_triples` omits `T` from its returned set.
`RETEStore._on_triples_removed` re-adds each such `T` to the engine's context
graph after the original `BatchDispatcher` removal pass completes, restoring
agreement between the store and working memory.

When this re-materialization occurs, `RETEStore` MUST emit a `UserWarning`
that names the triple and explains that the store-side removal was logically
ineffective because the engine still derives the triple. Callers that want
the triple to actually disappear MUST retract a supporting stated fact
instead.

This branch is preferred over a "user remove wins" branch (which would
require a derived-only TMS withdrawal primitive) and over a silent
re-materialization branch (which would hide a logically meaningful event
from the caller). Re-materialization preserves DR-024's JTMS invariants and
is symmetric with the add-side responsibility of the engine driving the
store. The warning preserves observability so callers are not surprised by a
silent no-op.

### RETE network pruning

`NetworkMatcher.match_terminals` merges new alpha/beta matches into
**persistent** `NodeRegistry.alpha_memory` and `NodeRegistry.beta_memory`
through `_store_matches`. `_join_beta` reads from those persisted memories,
so a `PartialMatch` whose `facts` tuple references a removed `Fact` will
continue to participate in joins until evicted.

`NodeRegistry` therefore exposes:

```python
def evict_partial_matches_referencing(self, fact_ids: frozenset[str]) -> None:
    ...
```

which deletes any `PartialMatch` in alpha or beta memory whose `facts` tuple
contains a removed fact id. `RETEEngine.retract_triples` MUST call this
primitive after applying TMS updates and before returning, with the union of
all fact ids removed from working memory across the batch.

For this stage, a full O(memory size) scan is acceptable. Optimization may
be deferred behind the same primitive without changing the engine contract.

### Store wiring

`rdflib.plugins.stores.memory.Memory.remove` does not call
`Store.remove(self, ...)` on the base class, so the validated backing store
does not emit `TripleRemovedEvent` from its own removal path. This is the
asymmetric counterpart of `Memory.add`, which DOES call `Store.add(self, ...)`
and therefore emits `TripleAddedEvent` on every add. To honor the
`BatchDispatcher` pre-mutation event contract on the removal path,
`RETEStore.remove` performs the event emission itself:

1. Snapshots the concrete triples that match the requested pattern in the
   requested context using `self.store.triples(pattern, context)`.
2. Dispatches one `TripleRemovedEvent` per concrete match through the
   backing store's dispatcher, before any mutation. `BatchDispatcher`
   batches those events and dispatches `TripleRemovedBatchEvent` to
   `_on_triples_removed`.
3. Delegates the actual removal to `self.store.remove(pattern, context)`.

`_on_triples_removed`:

1. Resolves the per-context engine via `_ensure_engine(batch.context_id)`.
2. Calls `engine.retract_triples(batch.events)` to obtain the cascade set.
3. For each cascade triple not already in the original batch, calls
   `context.remove(t)`. `BatchDispatcher`'s `_handling_removal` flag queues
   these into a follow-up batch; the engine no-ops on that pass because each
   triple is already absent from working memory.
4. For each input triple whose working-memory fact survived because the
   engine still believes it (stated-and-derived or derived-only), records
   the triple in `_pending_rematerialize`.

The actual re-materialization is deferred to a `_flush_rematerialize` pass
that runs in the outermost `RETEStore.remove` frame, after the backing
`self.store.remove` mutation has completed. An inline `context.add(t)`
during `_on_triples_removed` would be a no-op because the dispatcher events
are pre-mutation: the triple is still present in the backing store at the
time the handler runs, and `Memory.add` is idempotent for already-present
triples. `RETEStore` therefore tracks a `_remove_depth` counter so that
nested `context.remove` calls (for cascade consequents) do not flush the
re-materialization set prematurely. When the outermost frame returns, the
re-materialized triples are re-added through the normal `Graph.add` path
and a `RetractionRematerializeWarning` (a `UserWarning` subclass) is
emitted per re-added triple.

`RETEStore.remove` does NOT call the engine directly. The dispatcher event
chain remains the single path through which retractions reach the engine;
the manual event emission in step (2) above is part of meeting the
dispatcher contract that the validated backing store does not meet.

`RETEStore.update` and `RETEStore.remove_graph` continue to raise
`NotImplementedError`. SPARQL Update and graph-lifecycle removal are out of
scope for this stage; both can be revisited later without changing the
contracts established here.

`transaction_aware = False` remains accurate because support-aware removal is
not transaction support: there is no rollback, no snapshot isolation, and no
cross-graph atomicity.

### Pattern-based removal

`Store.remove(triple_pattern, context)` accepts wildcards. The validated
backing store, `rdflib.plugins.stores.memory.Memory`, enumerates concrete
matches and emits one `TripleRemovedEvent` per concrete triple before each
mutation, so `BatchDispatcher` already converts patterns into a fully ground
batch before the engine sees it. `RETEEngine.retract_triples` therefore
accepts an iterable of concrete triples and does not need wildcard handling.

### Derivation logs

DR-024 keeps derivation logs lossless across retraction; this decision does
not change that policy. Reconstructed proofs may reference triples that no
longer have a corresponding working-memory fact. That outcome is acceptable
because proof reconstruction is a presentation-layer concern over historical
derivations rather than a live support query.

## Consequences

`RETEStore`, `RETEEngine`, and `TMSController` are wired end-to-end for
removal: a `Dataset.default_graph.remove(triple)` call drives a support-aware
retraction in the engine, removes cascade consequents from the backing
store, and re-materializes triples the engine still derives without leaving
the network or working memory in an inconsistent state.

DR-004's idempotence requirement now has a symmetric counterpart for
removals; both update paths converge through `BatchDispatcher` without
custom reentrancy guards.

Callers who attempt to remove a triple that the engine still derives will
observe a `UserWarning` and the triple will reappear in the backing store.
Removing a stated antecedent of the derivation is the supported way to
actually retract derived knowledge.

`RETEStore.update` and `RETEStore.remove_graph` remain explicit
non-implementations; later work may build on this stage without revisiting
the engine contracts.

Persisted RDF reload semantics are unchanged from DR-004: persisted triples
are re-asserted as stated facts on open, regardless of whether they were
originally stated or derived. Re-materialization at runtime does not affect
this behavior.
