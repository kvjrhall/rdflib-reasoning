# Engine Guidance

This package contains both engine-internal components and a smaller set of schema-facing proof and derivation models.
Those two categories MUST be kept distinct.

## Authoritative references

- Treat [`docs/dev/architecture.md`](../docs/dev/architecture.md) as the authoritative architecture, especially:
  - `Structural elements and middleware`
  - `Schema-facing RDF boundary models`
  - `Engine event contract and entrypoint`
  - `Proof evaluation harness`
  - `Proof rendering`
  - `RETE Engine Design`
- Treat [`docs/dev/decision-records/DR-007 Proof Model and Derivation Semantics Refinement.md`](../docs/dev/decision-records/DR-007%20Proof%20Model%20and%20Derivation%20Semantics%20Refinement.md) as the authoritative rationale for proof model structure.
- Treat [`docs/dev/decision-records/DR-011 Schema-Facing RDF Boundary Models.md`](../docs/dev/decision-records/DR-011%20Schema-Facing%20RDF%20Boundary%20Models.md) as the authoritative rule set for schema-facing runtime models.

## Boundary rules

- Engine-internal components MUST NOT be required serialized inputs or outputs across the Research Agent boundary.
- Engine-native derivation records, working-memory structures, agenda state, and RETE network objects MUST remain internal unless a separate boundary model explicitly reconstructs them for runtime use.
- Proof or derivation models that do cross the runtime boundary SHOULD expose concise schema guidance, explicit constraints, and high-fidelity lexical examples rather than raw engine internals or extended theory text.
- Heavy runtime helper objects such as stores, graphs, and engine instances MUST NOT be required serialized fields in schema-facing proof models.

## Editing guidance

- When editing proof-facing models, optimize for stable interchange and runtime clarity first, not for mirroring internal engine structures one-to-one.
- When editing engine internals, do not introduce shortcuts that accidentally make Research Agent boundary behavior depend on internal object layouts or debugging representations.
