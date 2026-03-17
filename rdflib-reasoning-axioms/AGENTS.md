# Axioms Guidance

The `rdflib-reasoning-axioms` package defines graph-scoped domain models that SHOULD remain friendly to future runtime boundaries even when the immediate caller is a Development Agent or an internal package.

That rationale is accurate: keeping axioms boundary-friendly preserves many later design options for proof models, Research Agent tools, retrieval surfaces, and other structured interactions without forcing a large redesign of the domain layer.

## Authoritative references

- Treat [`docs/dev/architecture.md`](../docs/dev/architecture.md) as the authoritative architecture, especially:
  - `Structural elements and middleware`
  - `Schema-facing RDF boundary models`
- Treat [`docs/dev/decision-records/DR-002 Structural Elements and Middleware Integration.md`](../docs/dev/decision-records/DR-002%20Structural%20Elements%20and%20Middleware%20Integration.md) as the authoritative rationale for `GraphBacked` and `StructuralElement`.
- Treat [`docs/dev/decision-records/DR-011 Schema-Facing RDF Boundary Models.md`](../docs/dev/decision-records/DR-011%20Schema-Facing%20RDF%20Boundary%20Models.md) as the authoritative rule set for schema-facing RDF boundary models.

## Core package purpose

- The primary purpose of this package is round-trip `graph -> axiomatization -> graph` transformation through stable graph-scoped domain models.
- Transformation inputs MUST be treated as immutable and MUST produce new instances or outputs rather than mutating caller-owned graph structures in place.
- The OWL 2 Mapping to RDF Graphs specification MUST be treated as the authoritative mapping reference, together with the transitive specifications it relies upon.

## Boundary-friendly model rules

- `GraphBacked` is the universal base for graph-scoped Pydantic models in this package.
- `StructuralElement` is the universal base for OWL 2 structural elements; each concrete OWL 2 structural element MUST subclass `StructuralElement`.
- Schema-facing models MAY use RDFLib node-level terms such as `URIRef`, `BNode`, `Literal`, and `IdentifiedNode`.
- Schema-facing models MUST NOT embed heavy container or session objects such as `rdflib.Graph`, `ConjunctiveGraph`, SPARQL result objects, or similar handles.
- Each instance MUST have a single required `context` graph identifier.
- Any embedded `GraphBacked` or `StructuralElement` field MUST share the same `context`; cross-context relationships MUST be expressed only at the triple or quad level.

## Schema and validation guidance

- Schema-visible descriptions SHOULD be concise, operational, and useful to a Research Agent that only sees generated JSON Schema.
- Descriptions MAY cite official specification identifiers, but they SHOULD NOT depend on repository-local documents being visible at runtime.
- Examples SHOULD be high-fidelity and sparse: include them when they materially reduce misuse.
- Constrained types SHOULD be preferred wherever feasible so schema itself communicates useful limits.
- Domain constraints SHOULD be enforced through Pydantic validation with error messages that identify the illegal value, the valid range or form when helpful, and the relevant specification when a normative constraint is violated.
