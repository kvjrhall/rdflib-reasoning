# Middleware Guidance

This package contains schema-facing RDF boundary models and middleware surfaces used across the runtime boundary to a Research Agent.

- Treat [`docs/dev/architecture.md`](../docs/dev/architecture.md) as the authoritative architecture, especially:
  - `Structural elements and middleware`
  - `Schema-facing RDF boundary models`
- Treat [`docs/dev/decision-records/DR-011 Schema-Facing RDF Boundary Models.md`](../docs/dev/decision-records/DR-011%20Schema-Facing%20RDF%20Boundary%20Models.md) as the authoritative rationale of schema-facing RDF term models in this package.
- Serialized boundary models SHOULD prefer lexical RDF forms such as N3 strings.
- Heavy Python helper objects (for example `rdflib.Graph`) MUST NOT be required serialized inputs or outputs across the Research Agent boundary.
- When editing schema-facing descriptions, optimize for concise operational guidance, explicit constraints, and high-fidelity examples rather than long theoretical prose.
