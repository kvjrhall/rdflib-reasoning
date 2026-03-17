# DR-013 Dataset Middleware Internal Method and Tool Adapter Pattern

## Status

Accepted

## Date

2026-03-17

## Context

The dataset middleware exposes runtime capabilities to a Research Agent through tool schemas and tool descriptions.
At the same time, higher middleware layers, tests, and Development Agent code need a stable way to interact with the same middleware behavior without going through the schema-facing tool boundary.

If tool functions directly embed the implementation logic, several problems follow:

- Core RDFLib behavior and schema-boundary behavior drift together in the same function.
- Retrieval and inference middleware may be forced to re-enter the tool layer rather than compose with middleware-native operations.
- Tests must choose between awkward tool invocation or duplicated lower-level helpers.
- Changes to request/response schemas risk forcing unrelated rewrites of internal middleware logic.

The repository also now intends to phase dataset capabilities across multiple releases, beginning with a default-graph-only baseline.
That makes it more important to keep the internal implementation boundary distinct from the external Research Agent boundary.

## Decision

Dataset middleware MUST implement core behavior in internal middleware methods and expose Research Agent-facing tools as thin adapters over those methods.

The pattern is:

1. Internal middleware methods
   - Middleware SHOULD expose internal methods that operate on RDFLib-native or otherwise implementation-native values.
   - These methods SHOULD be the source of truth for dataset behavior.
   - These methods MAY be used by tests, retrieval middleware, inference middleware, or other Development Agent-facing integration points.

2. Tool adapters
   - Tool functions MUST remain thin adapters whenever possible.
   - Tool functions SHOULD validate or transform schema-facing request payloads, delegate to internal middleware methods, and transform results into schema-facing response payloads.
   - Tool functions MUST NOT duplicate core business logic already implemented by internal middleware methods except where framework constraints make a tiny amount of glue unavoidable.

3. Boundary discipline
   - Request and response models remain the runtime contract for the Research Agent boundary.
   - Internal middleware methods remain the Development Agent and middleware-composition contract.
   - Changes to one boundary SHOULD minimize unnecessary change to the other.

## Consequences

- Tests can exercise core dataset behavior without depending on tool invocation machinery.
- Retrieval and inference middleware can compose over dataset middleware through internal methods rather than by simulating agent tool calls.
- Tool descriptions and request/response schemas can evolve without forcing equivalent churn in RDFLib-native logic.
- Middleware implementations must be careful to keep the adapter layer thin so the intended separation does not degrade into duplication.

## Related

- [DR-012 Middleware-Owned Dataset Sessions and Coordination](DR-012%20Middleware-Owned%20Dataset%20Sessions%20and%20Coordination.md)
- [architecture.md](../architecture.md)
