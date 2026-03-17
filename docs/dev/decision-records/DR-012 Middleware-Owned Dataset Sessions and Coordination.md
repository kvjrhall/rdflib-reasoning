# DR-012 Middleware-Owned Dataset Sessions and Coordination

## Status

Accepted

## Date

2026-03-16

## Context

The dataset middleware is intended to provide a shared RDFLib-backed working dataset for Research Agent tool use, retrieval, and inference.
However, the runtime environment imposes constraints that make a live `rdflib.Dataset` a poor fit for `AgentState`:

- LangChain v1 restricts agent state schemas to `TypedDict`-based shapes.
- Runtime state may be deep-copied before concurrent tool invocation and later reduced.
- Deep-copying a live RDFLib dataset is expensive and does not align well with shared mutable state.

At the same time, the project needs coordination for concurrent access to the same dataset.
Different datasets do not inherently conflict with one another, so repository-wide serialization would be unnecessarily coarse.

An exploratory rollback-oriented store wrapper was considered, but that approach expanded the scope toward general transaction support.
That is not required for the current project phase, and it introduces complexity beyond the repository's intended baseline.

## Decision

Dataset middleware MUST treat the live RDFLib dataset as middleware-owned runtime infrastructure, not as copied `AgentState` payload.

The architecture adopts the following rules:

1. Middleware-owned dataset sessions
   - Dataset middleware MUST own a per-dataset session object or equivalent internal container.
   - That session MUST contain the live `rdflib.Dataset` and the coordination primitive used to protect it.
   - Distinct datasets SHOULD use distinct coordination primitives so unrelated datasets can proceed independently.

2. State boundary
   - `AgentState` MUST remain `TypedDict`-compatible and cheap to copy.
   - Live RDFLib graph, dataset, store, lock, or other heavy synchronization objects MUST NOT be stored directly in copied runtime state.
   - State MAY carry lightweight middleware-facing identifiers or metadata needed to resolve the active dataset session.

3. Coordination model
   - Dataset middleware MUST provide multi-reader / single-writer coordination per dataset session.
   - Tool operations that inspect dataset contents SHOULD execute under read coordination.
   - Tool operations that mutate dataset contents MUST execute under write coordination.
   - Retrieval and inference middleware that operate on the same dataset MUST use the same coordination boundary.

4. Non-goals
   - The dataset middleware baseline MUST NOT claim general transaction support.
   - The baseline MUST NOT promise rollback, snapshot isolation, branch-local dataset copies, or conflict-merge semantics for concurrent writes.
   - The baseline MAY assume that supported in-process stores such as RDFLib `Memory` do not fail mid-operation under normal use.
   - Stores or integrations with materially different failure behavior MAY be treated as unsupported or experimental unless explicitly documented otherwise.

## Consequences

- The copied runtime state remains lightweight and compatible with LangChain's state model.
- Shared RDFLib objects and synchronization concerns stay inside middleware-owned infrastructure.
- Concurrent access is coordinated per dataset without serializing unrelated datasets.
- The design avoids scope creep into durable or general-purpose transaction management.
- Middleware implementations must provide explicit lifecycle management for dataset sessions and their associated coordination objects.

## Related

- [architecture.md](../architecture.md)
- [roadmap.md](../roadmap.md)
