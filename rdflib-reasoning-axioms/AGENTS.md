# The `rdflib-reasoning-axioms` Sub-Package

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

- The REQUIRED purpose of this package is round-trip `graph -> axiomatization -> graph` transformations. Transformation inputs MUST be treated as immutable and produce new instances for outputs.
- You MUST use the `owl2-mapping-to-rdf` specification as the authoritative reference for the RDF consumed/produced by this package.
- You MUST use transitive references to specifications made by `owl2-mapping-to-rdf`. I.e., `rdf11-semantics`.
- You MAY support backwards compatibility with OWL 1 DL.
- You SHOULD remember that other packages (i.e., `rdflib-reasoning-engine`) MAY interoperate with this package and be affected by this package's design.

## Structural elements and GraphBacked

- `GraphBacked` is the universal base for graph-scoped Pydantic models in this package. `StructuralElement` is the universal base for all OWL 2 structural elements; every concrete OWL 2 structural element MUST subclass `StructuralElement`.
- Each concrete `StructuralElement` subclass MUST correspond to a well-identified OWL 2 structural element (or a clearly documented extension). `as_triples` and `as_quads` MUST conform to `owl2-mapping-to-rdf` and transitive specs (e.g. `rdf11-semantics`). Non-OWL constructs (e.g. RDF-star triple-statements per RDF 1.2) MAY be modeled as `GraphBacked` without subclassing `StructuralElement`; document the governing spec (e.g. RDF 1.2 / RDF-star) for such models.
- GraphBacked and StructuralElement models MAY use rdflib node-level types (`URIRef`, `BNode`, `Literal`, `IdentifiedNode`, etc.). They MUST NOT contain `rdflib.Graph`, `ConjunctiveGraph`, SPARQL result objects, or other container/session/handle types.
- Each instance has a single, required `context` (graph identifier). Any field whose type is another `GraphBacked` or `StructuralElement` MUST share the same `context`; enforce this via validators where such nesting exists. Cross-context relationships are expressed only at the triple/quad level, not by embedding instances with a different context.

## JSON Schema: terse and optimized for guidance

Schema and field descriptions are consumed by Research Agents (runtime); they MUST assume only the "joint documentation" (the generated Pydantic JSON Schema for the enclosing class and its fields). They MUST NOT assume module or repository documentation, decision records, or internal artifacts (e.g. `optimized.html`) are available.

- **Terse.** Descriptions SHOULD optimize context usage by complementing the joint documentation. They SHOULD NOT explain other fields except to capture relationship to those fields; complex interaction MUST be documented at the enclosing class level. They MUST NOT reference decision records or repository-local spec content; they MAY reference official specification identifiers (e.g. RFC numbers, W3C spec URIs and section identifiers).
- **Examples.** Examples in schema SHOULD be used sparingly and only when they materially reduce misuse.
- **Constrained types.** Constrained types (enums, constrained strings, etc.) SHOULD be used wherever possible to reduce cognitive load and assist Research Agents and developers. Unconstrained types MUST NOT be used without explicit approval from a user.

## Validation errors

All domain-level checks SHOULD be performed as a consequence of Pydantic validation. Error messages are guidance for correction by a Research Agent or human.

- Errors MUST explicitly specify illegal values. They SHOULD explicitly define valid ranges in human- and Research Agent–friendly terms (e.g. "a nonzero positive integer", "an RFC 3987 IRI", "one of {'a','b'}"). Valid ranges MAY be omitted when they would increase cognitive load (e.g. a long regex for IRIs).
- Errors SHOULD recommend a concrete fix (e.g. "validate the derivation of the value and try again", "use function_y instead").
- If an error represents violation of a specification constraint, the error MUST indicate the specification and section using official identifiers.
- Where feasible, errors SHOULD follow a consistent pattern: short summary, illegal value(s), valid range hint, and spec reference if applicable. Exact error shape may be refined in a future decision.
