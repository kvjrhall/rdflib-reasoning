# RETE Store Persistence and Engine Update Contract

## Status

Accepted

## Context

The `rdflib-reasoning-engine` package introduces a `RETEStore` that composes RDFLib store events, `BatchDispatcher`, and a RETE-style inference engine.
This raises several architectural questions that need stable answers before the engine implementation proceeds.

When a store is opened from persisted RDF content, the RETE network state is not available as a serialized artifact.
Only RDF graph contents are persisted.
The system therefore needs a defined contract for how engine state is reconstructed on startup and how persisted triples are interpreted.

The store and engine integration also depends on specific behavior from the engine.
`RETEStore` warms an engine from the current contents of a context and then materializes any deductions back into the store.
During normal operation, `BatchDispatcher` provides store-level fixed-point iteration across reentrant materialization.
However, `BatchDispatcher` cannot compensate for an engine that returns only a partial consequence set for a single update.
The engine therefore needs explicit requirements for idempotence and per-update fixed-point generation.

## Decision

- Persisted RDF store contents MUST be treated as authoritative facts when a `RETEStore` opens or attaches to an existing backing store. The system MUST seed the engine from the fully materialized contents of each context; it MUST NOT attempt to distinguish asserted triples from previously derived triples across reloads.
- `RETEStore` warm-start behavior MUST be defined as:
  1. create or obtain the engine for a context;
  2. read the current triples for that context from the backing store;
  3. warm the engine from those triples;
  4. materialize any non-silent warmup deductions back into the store.
- This repository explicitly accepts that a persisted RDF document does not preserve engine-internal state. Reopening a store under the same ruleset means trusting the persisted graph contents as ground truth for subsequent reasoning.
- `RETEEngine.add_triples()` MUST be idempotent for triples that are already known to the engine when derivation logging is disabled. Re-adding an already-known triple MUST NOT produce new deductions solely because the triple was presented again.
- `RETEEngine.add_triples()` MUST compute a fixed point for the update it is given. `RETEEngine.warmup()` MUST compute a fixed point for the warm-start input it is given.
- `BatchDispatcher` provides store-level fixed-point iteration across reentrant materialization events. It MUST NOT be relied upon to compensate for a partially saturating engine update step.
- The coupling between `RETEStore` and `RETEEngine` is intentional. `RETEStore` MAY rely on the engine contracts above, and `RETEEngine` MAY assume that `RETEStore`/`BatchDispatcher` will handle store-event batching and reentrant materialization sequencing.

## Consequences

- Store reopen semantics are simple and explicit: persisted graph contents are the authoritative input facts for engine reconstruction.
- The system does not preserve an asserted-versus-derived boundary across reloads. Previously materialized inferences are treated as ordinary facts after reopening.
- If the active ruleset changes between persistence and reload, stale previously derived triples are still trusted unless some later design introduces validation or rebuild behavior.
- `RETEStore` can materialize warmup deductions by sending them through normal store addition paths, but this is only correct because `RETEEngine.add_triples()` is required to be idempotent for already-known facts.
- Engine implementations now have stronger obligations: each update step and warmup step must saturate to a fixed point for their given inputs.
- Architecture and implementation discussions can distinguish clearly between engine-level fixed-point generation and store-level fixed-point iteration.

## Supersedes

None.
