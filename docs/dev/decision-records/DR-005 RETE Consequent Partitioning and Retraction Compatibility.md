# RETE Consequent Partitioning and Retraction Compatibility

## Status

Accepted

## Context

The RETE engine design in `rdflib-reasoning-engine` needs a stable architectural boundary between declarative reasoning and host-extensible Python behavior.
Without that boundary, Python callbacks can become an alternate inference channel that bypasses the RETE network, fixed-point materialization, and future truth-maintenance behavior.

The repository already defines engine and store contracts that assume deterministic, idempotent, triple-oriented fixed-point inference.
At the same time, some implementation techniques inspired by systems such as Jena may still require builtins, predicates, contradiction signaling hooks, or other internal extensibility points.

The first implementation does not need full retraction support.
However, the initial design must not preclude later introduction of a JTMS-backed removal model.

## Decision

- The logical core of the RETE engine MUST remain a pure RDF entailment engine.
- Logical rule consequents MUST be represented only as engine-managed declarative triple production.
- Python predicates or builtins MAY be used during matching or internal engine evaluation, but they MUST be read-only. They MUST NOT add triples, retract triples, or otherwise mutate graph state.
- Python callbacks or hooks MAY be attached for observability, integration, contradiction signaling, tracing, metrics, or similar non-logical behavior, but they MUST NOT add triples, retract triples, or otherwise mutate graph state.
- Python callbacks and hooks MUST NOT serve as an alternate inference channel. All logical graph mutation MUST remain on the engine-managed triple-production path.
- The initial implementation MAY remain add-only. Retraction support is a future design goal that the data model, network structure, and rule representation MUST remain compatible with.
- Because callbacks are non-logical and non-mutating, `RetractionNotImplemented` MUST be interpreted as meaning that no reversal is required for logical consistency.
- Truth-maintenance bookkeeping such as justifications and dependency tracking MUST apply to logical triple production, not to observational callbacks.

## Consequences

- The engine can preserve deterministic fixed-point materialization semantics because all logical consequences remain inside the RETE network and engine-managed production path.
- The architecture remains compatible with the existing `RETEStore` and `BatchDispatcher` contracts, which assume triple-oriented, replay-safe inference.
- Builtins and callbacks remain available for implementation flexibility, but their scope is constrained so they cannot undermine inference correctness.
- Contradiction detection, tracing, metrics, and similar features may still use internal predicates or callbacks, provided those mechanisms do not mutate graph state.
- Retraction is explicitly staged: it is not required for the first implementation, but future JTMS support is preserved as a design constraint.
- API and documentation should distinguish clearly between logical triple productions, read-only predicates, and non-mutating callbacks.

## Supersedes

None.
