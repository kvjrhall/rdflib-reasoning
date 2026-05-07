# Axioms Guidance

The `rdflib-reasoning-axioms` package defines graph-scoped domain models for
runtime callers, including Research Agents through package-exposed tools or
middleware and other repository packages. Development Agents maintain this
package, its source documentation, and its docstrings; they are not runtime
callers of this package.

Keeping axioms boundary-friendly preserves later design options for proof
models, Research Agent tools, retrieval surfaces, structural representation, and
other schema-driven interactions without forcing a redesign of the domain layer.

## Authoritative references

- Treat [`docs/dev/architecture.md`](../docs/dev/architecture.md) as the
  authoritative architecture, especially:
  - `Structural elements and middleware`
  - `Structural traversal and representation`
  - `Schema-facing RDF boundary models`
  - `Knowledge exchange and axiom authoring`
- Treat
  [`docs/dev/roadmap.md`](../docs/dev/roadmap.md) as the authoritative release
  and priority plan, especially release `0.6.0` for structural traversal and
  release `0.10.0` for knowledge exchange and axiom authoring.
- Treat
  [`docs/dev/decision-records/DR-031 Standalone Structural Elements.md`](../docs/dev/decision-records/DR-031%20Standalone%20Structural%20Elements.md)
  as the authoritative rationale for `GraphBacked` and `StructuralElement`
  (supersedes DR-002).
- Treat
  [`docs/dev/decision-records/DR-011 Schema-Facing RDF Boundary Models.md`](../docs/dev/decision-records/DR-011%20Schema-Facing%20RDF%20Boundary%20Models.md)
  as the authoritative rule set for schema-facing RDF boundary models.
- Treat
  [`docs/dev/decision-records/DR-003 Research Agent and Development Agent Terminology.md`](../docs/dev/decision-records/DR-003%20Research%20Agent%20and%20Development%20Agent%20Terminology.md)
  as the authoritative rule set for role terminology and visibility boundaries.
- Treat
  [`docs/dev/prospective-use-cases.md`](../docs/dev/prospective-use-cases.md)
  as long-horizon planning input only. It MAY explain motivation, but it MUST
  NOT override architecture, roadmap, decision records, local `AGENTS.md`, or
  source code.

## Documentation and runtime visibility

- `AGENTS.md` and design docs are Development Agent-facing materials. Research
  Agents MUST NOT see them.
- Docstrings are rendered package documentation for client code and package
  consumers. They MUST NOT cite repository-local specs, crosswalks, `AGENTS.md`,
  design docs, or other Development Agent-only materials.
- Source comments that cannot become part of generated documentation MAY cite
  repository-local specs and crosswalks for Development Agents.
- Generated JSON Schema, tool descriptions, serialized model fields, and
  validation errors are the runtime surfaces Research Agents may see when axioms
  are exposed through tools, middleware, or other package boundaries.
- Schema-visible descriptions SHOULD stand alone at runtime and SHOULD prefer
  official specification names, structural forms, field meanings, and compact
  lexical examples over repository-internal documentation references.

## Core package purpose

- Current package work centers on graph-scoped Pydantic structural models and
  RDF projection through `as_triples` and `as_quads`.
- The long-term round-trip goal is `graph -> axiomatization -> graph`, but
  graph-to-structural traversal, stable representation, rendering, and
  Research Agent-facing axiom-authoring surfaces are planned capabilities, not
  assumptions that every current class or test may rely on.
- An axiom artifact SHOULD correspond 1:1 to a defined multiset (or set) of
  triples or quads actually present in the graph for that axiom's mapping, so a
  chunk's shape and meaning do not depend on having carved sibling axioms for
  every node it mentions.
- Transformation inputs MUST be treated as immutable and MUST produce new
  instances or outputs rather than mutating caller-owned graph structures in
  place.

## Structural element cookbook

- Use [`docs/specs/owl2-mapping-to-rdf/INDEX.md`](../docs/specs/owl2-mapping-to-rdf/INDEX.md)
  first when implementing or reviewing `as_triples` and `as_quads`. It is the
  authoritative local lookup for exact OWL structural-element to RDF mapping
  anchors and section spans.
- Use [`docs/specs/owl2-crosswalks/INDEX.md`](../docs/specs/owl2-crosswalks/INDEX.md),
  especially the StructuralElement-oriented master table, for semantic anchors,
  OWL 2 RL rule links, optional RDFS support, proof-reconstruction context, and
  coverage planning.
- Keep the package [feature matrix](README.md#feature-matrix) aligned with
  implementation coverage. The crosswalk row `status` field describes
  crosswalk-row curation completeness, not the implementation maturity of this
  package.
- When mapping, crosswalk, README, and code disagree, treat the discrepancy as
  design drift to resolve deliberately rather than copying whichever source is
  closest at hand.
- **Design drift:** generic `Seq` over `StructuralElement` operands and several
  datatype models that use it violate the no-composition rule in DR-031; treat
  that as follow-up work (see DR-031 Consequences), not as a pattern for new
  code.

## Boundary-friendly model rules

- `GraphBacked` is the universal base for graph-scoped Pydantic models in this
  package.
- `StructuralElement` is the universal base for OWL 2 structural elements; each
  concrete OWL 2 structural element MUST subclass `StructuralElement`.
- Schema-facing models MUST use package-defined annotated aliases for RDF terms
  (for example `N3IRIRef`, `N3Resource`, `N3Node`, `N3ContextIdentifier`)
  rather than raw RDFLib node classes so generated JSON Schema remains
  boundary-safe.
- Raw RDFLib node-level classes such as `URIRef`, `BNode`, `Literal`, and
  `IdentifiedNode` MAY be used internally (helpers, locals, computed properties)
  when they are not schema-facing fields.
- Schema-facing models MUST NOT embed heavy container or session objects such as
  `rdflib.Graph`, `ConjunctiveGraph`, SPARQL result objects, or similar handles.
- Each instance MUST have a single required `context` graph identifier.
- `StructuralElement` instances MUST NOT compose or aggregate other
  `StructuralElement` or `GraphBacked` instances. Cross-element references MUST
  use RDF node-level types (`IdentifiedNode`, `URIRef`, `BNode`, `Literal`) and
  schema-facing aliases such as `N3IRIRef` or `N3Resource` where appropriate.
- Cross-axiom traversal is the responsibility of explicit graph-level helpers, not
  embedded model fields.
- `as_triples` MUST remain shallow (MUST NOT recurse into related elements).
  The no-composition rule makes this structurally trivial for new code; the
  shallow rule remains an explicit invariant and defense-in-depth.
- Cross-context relationships MUST be expressed only at the triple or quad
  level.
- Schema-boundary alias mapping for Development Agents:
  - `URIRef`-only field -> `N3IRIRef`
  - `IdentifiedNode` field (`URIRef` or `BNode`) -> `N3Resource`
  - Any RDF node (`URIRef`, `BNode`, `Literal`) -> `N3Node`
  - Graph/context identifier (`URIRef` or `BNode`) -> `N3ContextIdentifier`

## Docstring guidance

- Concrete `StructuralElement` docstrings SHOULD name the OWL structural form,
  such as `DataIntersectionOf( DR1 ... DRn )`, when a paired OWL form exists.
- Docstrings SHOULD summarize key RDF node, blank-node, list, or ordering
  assumptions when they affect the mapping or reconstruction story.
- Docstrings SHOULD include a compact mapped-triples block when that block
  materially helps verify `as_triples` or future traversal behavior.
- Docstrings MUST use package-consumer-safe references: official specification
  names, structural forms, and local API names are appropriate; repository-local
  development docs, crosswalks, and `AGENTS.md` files are not.
- Docstrings SHOULD avoid claiming traversal, inference, proof reconstruction,
  Research Agent tool behavior, or full round-trip behavior unless that behavior
  exists for the class being documented.

## Schema and validation guidance

- Schema-visible descriptions SHOULD be concise, operational, and useful to a
  Research Agent that only sees generated JSON Schema.
- Descriptions MAY cite official specification identifiers, but they SHOULD NOT
  depend on repository-local documents being visible at runtime.
- Examples SHOULD be high-fidelity and sparse: include them when they materially
  reduce misuse.
- Constrained types SHOULD be preferred wherever feasible so schema itself
  communicates useful limits.
- Domain constraints SHOULD be enforced through Pydantic validation with error
  messages that identify the illegal value, the valid range or form when
  helpful, and the relevant specification when a normative constraint is
  violated.

## Testing expectations

- Concrete structural elements SHOULD have focused tests for `as_triples`, and
  for `as_quads` when context behavior is relevant to the change.
- Schema-facing models SHOULD have Python round-trip tests using `model_dump`
  and `model_validate`.
- Schema-facing models SHOULD have JSON round-trip tests using `model_dump_json`
  and `model_validate_json`.
- Schema-facing models SHOULD have `model_json_schema()` smoke tests.
- Add stronger schema assertions when field descriptions, aliases, examples,
  lexical RDF forms, required fields, or JSON Schema shape are intended
  Research Agent boundary contracts.
- Tests SHOULD NOT over-specify incidental Pydantic schema layout unless that
  layout is deliberately part of the runtime boundary contract.
- Test functions and helpers under this package's `tests/` tree SHOULD declare a
  return type (typically `-> None` for pytest tests) so local variable
  annotations are type-checked and IDE or Mypy `annotation-unchecked` notes on
  those annotations are avoided.
- Test parameters SHOULD be annotated when the type is not obvious from a
  default or from a single obvious assignment.
- Use `# type: ignore[error-code]` only for deliberate exceptions (for example
  negative tests that instantiate an abstract class); prefer the narrowest
  `error-code` Mypy prints with `--show-error-codes`. Pyright-only suppressions
  (`# pyright: ignore[...]`) do not satisfy Mypy.
- `make validate` runs Mypy on this package's `src/` tree per root
  `pyproject.toml`; the Development Agent SHOULD still keep `tests/` type-clean
  for editors and for any later widening of Mypy `files`.
