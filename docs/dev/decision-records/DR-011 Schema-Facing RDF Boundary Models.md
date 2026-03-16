# DR-011 Schema-Facing RDF Boundary Models

## Status

Accepted

## Date

2026-03-15

## Context

The `rdflib-reasoning-middleware` package now exposes RDF-facing dataset models directly across the runtime boundary to a Research Agent through Pydantic-generated JSON Schema.
Those boundary models are consumed differently from ordinary developer-only Python classes:

- The serialized form becomes part of the Research Agent's working contract.
- The generated schema influences how a Research Agent chooses and validates values.
- Development Agents may edit the module directly without first reading the broader architecture guidance.

The repository already establishes that middleware-visible data should avoid heavy graph/session objects and use explicit schema-driven surfaces.
However, the repository did not yet define a consistent rule set for how schema-facing RDF term models should balance:

- Python-native convenience versus wire-format simplicity
- reusable type-level validation versus per-field duplication
- concise operational descriptions versus formal specification references
- schema-visible boundary fields versus Python-only helper properties

## Decision

Schema-facing RDF boundary models MUST follow these rules:

1. Serialized wire forms
   - Runtime-visible serialized forms SHOULD use lexical RDF representations such as N3 strings when those are the natural boundary contract.
   - Boundary models SHOULD prefer simple JSON-native shapes that a Research Agent can inspect and emit directly.

2. Reusable validation and schema metadata
   - RDF term constraints SHOULD be attached to reusable schema aliases or equivalent shared model components rather than copied into every field validator.
   - Reusable aliases SHOULD carry the generated schema description, examples, and validation behavior needed across multiple models.

3. Descriptions and examples
   - Schema-facing descriptions SHOULD be operational, concise, and directly useful for tool usage.
   - Descriptions MAY cite formal standards when that helps a Research Agent recover from errors, but they SHOULD NOT reproduce long stretches of normative prose.
   - Examples SHOULD use high-fidelity lexical forms matching the exact serialized interface.

4. Python-only helper values
   - Heavy runtime helper objects such as `rdflib.Graph` MAY exist as computed Python-only conveniences.
   - Such helper objects MUST NOT be required serialized inputs or outputs across the Research Agent boundary.

5. Local discoverability for Development Agents
   - Modules defining schema-facing RDF boundary models SHOULD include a module-level docstring that points to the governing architecture section and this decision record.
   - Package-local Development Agent guidance MAY additionally reference these documents when the package is likely to be edited in isolation.

## Consequences

- Middleware schema becomes more consistent across tools and state payloads.
- Research Agents receive more actionable schema guidance at the exact point of use.
- Development Agents have a clearer repository-level rule set for future schema additions.
- Some boundary models may require explicit `arbitrary_types_allowed` or other Pydantic configuration in order to preserve rich Python-side values while keeping a simple serialized surface.

## Related

- [DR-002 Structural Elements and Middleware Integration](DR-002%20Structural%20Elements%20and%20Middleware%20Integration.md)
- [architecture.md](../architecture.md)
