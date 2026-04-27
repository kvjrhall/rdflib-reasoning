# TMSController Recursive Retraction

## Status

Accepted

## Context

The staged truth-maintenance plan in [`docs/dev/architecture.md`](../architecture.md)
sequences support recording, support verification, recursive Mark-Verify-Sweep
retraction, and removal wiring through the supported store integration path as
distinct stages. Stage (1) records `Fact`, `Justification`, and
`DependencyGraph` data during add-only rule production. Stage (2),
[DR-023](DR-023%20JTMS%20Support%20Verification%20API%20Surface.md), exposes the
read-only support verification surface needed by retraction without committing
to a destructive operation.

This decision specifies stage (3): a recursive Mark-Verify-Sweep retraction
primitive on `TMSController` that consumes the DR-023 verifier surface and
performs the actual mutation of working memory, justifications, and the
dependency graph. Stage (4), wiring `RETEEngine.retract_triples`,
`RETEStore.remove`, and the `TripleRemovedBatchEvent` subscription through the
`Store` event contract, is intentionally deferred so that the retraction
algorithm can be exercised against the JTMS support invariants in isolation
before alpha/beta network and `Agenda` coordination concerns are added.

The retraction primitive is engine-internal. It is not a Research Agent-facing
schema model and does not expose working-memory objects across the runtime
boundary.

## Decision

`TMSController` exposes a single retraction entry point that operates by
triple:

```python
def retract_triple(self, triple: Triple) -> RetractionOutcome: ...
```

The result is reported through an immutable `RetractionOutcome`:

- `removed_fact_ids` and `removed_triples` enumerate facts that were swept from
  working memory.
- `removed_justification_ids` enumerates justifications whose support edges
  were dropped, including justifications that referenced a swept consequent or
  swept antecedent.
- `unstated_fact_ids` enumerates facts whose `stated` flag was cleared but
  whose presence in working memory is preserved by surviving justifications.

`retract_triple` semantics follow the JTMS support invariants in the
architecture document:

- A stated fact with no justifications is removed and triggers Mark-Verify-Sweep
  over its transitive dependents.
- A stated fact that also has at least one justification is treated as a
  derived fact going forward: the `stated` flag is cleared and the fact remains
  present. No cascade is performed; downstream conclusions remain supported.
- Passing a triple whose working-memory fact is non-stated (i.e. derived only)
  raises `ValueError`. Direct retraction of a derived fact would violate the
  invariant that derived facts are removed if and only if their justification
  set becomes empty. PR A only exposes stated retraction at the TMS-controller
  layer.
- Passing a triple that is absent from working memory returns an empty
  `RetractionOutcome` and does not mutate state.
- Silent justifications contribute to support validity in the same way as
  visible justifications, consistent with DR-023 and the silent support
  semantics in `architecture.md`.

The Mark-Verify-Sweep procedure operates over a bounded candidate set rather
than open recursion:

1. Mark: candidates = `{seed_fact_id} ∪ transitive_dependents_of(seed)`.
2. Verify (fixed point): a candidate `c` is promoted to "kept" when at least
   one of its justifications has every antecedent satisfied either by a stated
   fact, a fact outside the candidate set, or a candidate already promoted to
   "kept". The loop continues until a pass produces no new promotions.
3. Sweep: facts that remain candidates after the verify fixed point are
   removed from `WorkingMemory`. Justifications whose consequent or any
   antecedent was swept are dropped from `justifications_by_consequent` and
   their corresponding edges are removed from `DependencyGraph`.

`retract_triple` is atomic in the sense that mutation is performed only after
the verify fixed point has finished. The method either commits the full sweep
or, in the no-cascade and no-op branches, makes no mutations at all.

Three small primitives are added alongside the controller method to keep the
sweep explicit:

- `WorkingMemory.remove_fact(fact_id)` removes the working-memory entry for a
  fact id and returns the removed fact.
- `DependencyGraph.discard_consequent(consequent_id)` removes every edge in
  which the given fact participated, in both the antecedents-of-consequent and
  consequents-of-antecedent directions. It is used when the fact itself is
  swept from working memory.
- `DependencyGraph.update_consequent_edges(consequent_id, antecedent_ids)`
  rewrites the consequent's antecedent edge set to exactly the supplied
  identifiers and discards reverse edges that no surviving justification
  requires. It is used when a fact is kept but its justification set was
  trimmed during the sweep.

These two graph operations cover the two distinct sweep outcomes: swept facts
need bidirectional edge removal, while kept facts need their edge set
recomputed from the union of surviving justifications.

`retract_triple` is intended to be invoked from the engine-side wiring in PR B.
A direct caller that bypasses the engine network and `Agenda` will leave
alpha/beta memory and pending agenda entries holding stale `Fact` references.
The method docstring and tests document this boundary explicitly.

## Consequences

The future engine-level wiring of removal can delegate the support-aware sweep
to a single named primitive instead of re-implementing Mark-Verify-Sweep at the
store boundary.

Tests can exercise stated-fact retraction, multi-parent support survival,
chained derivation cascade, silent-rule support semantics, cycle safety,
dependency-graph consistency after sweep, and idempotence before destructive
behavior is wired through `RETEStore`, `RETEEngine`, and `BatchDispatcher`.

`RETEEngine.retract_triples` and `RETEStore.remove` continue to raise
`NotImplementedError`. The `TripleRemovedBatchEvent` subscription remains
disabled. Callers that need destructive removal during stage (3) must access
`TMSController` explicitly, with the caveat that engine-side network and
agenda state are not yet kept consistent.

`DerivationRecord` retention policy is unchanged: derivation logs remain
lossless across retraction. Reconstructed proofs MAY reference triples that no
longer have a corresponding working-memory fact, which is acceptable because
proof reconstruction is a presentation-layer concern over historical
derivations rather than a live support query.
