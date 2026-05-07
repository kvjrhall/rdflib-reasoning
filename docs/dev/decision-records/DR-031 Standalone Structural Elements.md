# Standalone Structural Elements

## Status

Accepted

## Context

The repository supports research into agents and their interoperability with formal logic. Structural elements (OWL 2 and other graph-scoped constructs) need to be consumable by LangChain [Custom Middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom) and by Research Agents (runtime agents) as tool arguments/responses and state payloads. To achieve that, their schema must be exposed via Pydantic, remain terse and guidance-optimized for Research Agents, and avoid embedding complex third-party structures. A single, required graph context per element simplifies reasoning and equality; validation errors must support correction by Research Agents and humans.

RDF graphs are often **partial** and **open-world**: an OWL construct may reference IRIs or blank nodes whose defining triples (for example class declarations) are not present in the same graph. **Embedding** one `StructuralElement` inside another as a composed field suggests a **closed subtree** of fully interpreted axiom objects and can imply that the graph is more complete than it is. That conflicts with **partitioning** goals: a chunk's shape and meaning MUST NOT depend on having carved sibling axioms for every node an axiom mentions, and removing one partition MUST NOT leave a parent object that still "contains" children whose triples are absent or were never asserted.

This record **supersedes** [DR-002 Structural Elements and Middleware Integration](DR-002%20Structural%20Elements%20and%20Middleware%20Integration.md), which allowed related structural elements to be embedded in fields with a shared `context`. The rules below replace that embedding posture with **standalone** `StructuralElement` instances whose cross-element references stop at **RDF node identifiers**, while preserving DR-002's other middleware and schema constraints.

## Decision

- **Pydantic hierarchy.** All domain data models at the interface of `rdflib-reasoning-middleware` MUST be Pydantic models. Strong reasons to deviate MUST be documented. `GraphBacked` is the universal base for graph-scoped Pydantic models; `StructuralElement` is the universal base for all OWL 2 structural elements. Non-OWL constructs (e.g. RDF-star triple-statements per RDF 1.2) MAY be `GraphBacked` without subclassing `StructuralElement`.

- **No embedded graphs or heavy third-party types.** Structural elements and other `GraphBacked` models MUST NOT contain `rdflib.Graph`, `ConjunctiveGraph`, SPARQL result objects, or other container/session/handle types. Schema-facing model fields MUST use package-defined annotated aliases for RDF terms (for example `N3IRIRef`, `N3Resource`, `N3Node`, `N3ContextIdentifier`) so generated JSON Schema and lexical serialization remain boundary-safe. Raw rdflib node-level classes (`URIRef`, `BNode`, `Literal`, `IdentifiedNode`, etc.) MAY still be used internally in helpers, computed properties, and local logic that does not define schema-facing fields.

- **Standalone structural elements (no axiom-level composition).** A `StructuralElement` instance MUST NOT compose or aggregate other `StructuralElement` or `GraphBacked` instances as Pydantic fields. Cross-element structure in the object model MUST be expressed only through **RDF node references** (and literals where the mapping permits). Cross-axiom traversal and interpretation of referenced nodes are **graph-level** concerns, implemented by explicit helpers or traversal over triples, not by nesting axiom instances.

- **Context.** Each instance has a single, required `context` (graph identifier). Cross-context relationships are expressed only at the triple or quad level. Provide `as_quads` so that triples from `as_triples` are converted to quads by appending `context`.

- **OWL 2 alignment.** Each concrete `StructuralElement` subclass MUST correspond to a well-identified OWL 2 structural element (or clearly documented extension). `as_triples` and `as_quads` MUST conform to `owl2-mapping-to-rdf` and transitive specs (e.g. `rdf11-semantics`).

- **Shallow `as_triples`.** `as_triples` MUST NOT recurse into related elements: it emits only the triple multiset for **this** structural element's OWL mapping, with operands appearing as **object positions** that reference other nodes by identity. The no-composition rule makes recursion structurally unnecessary for new code; the shallow rule remains an explicit invariant and defense-in-depth against regressions.

- **JSON Schema: terse and guidance-optimized.** Descriptions assume only the "joint documentation" (Pydantic-generated JSON Schema for the model and its fields). They MUST NOT assume module/repo docs, decision records, or internal artifacts; they MAY reference official specification identifiers (e.g. RFC numbers, W3C spec URIs). Field descriptions MUST complement, not duplicate, other docs; complex interaction at enclosing class level. Examples SHOULD be used sparingly when they materially reduce misuse. Constrained types SHOULD be used wherever possible; unconstrained types MUST NOT be used without explicit user approval.

- **Validation errors.** Errors MUST specify illegal values; SHOULD describe valid ranges in human- and Research Agent–friendly terms; SHOULD recommend a concrete fix. Spec violations MUST reference the governing spec and section using official identifiers. Where feasible, errors SHOULD follow: short summary, illegal value(s), valid range hint, spec reference if applicable. Exact error shape may be refined in a future decision.

- **LangChain middleware.** `GraphBacked`/`StructuralElement` instances MUST be usable as tool argument/response models and as values in middleware state. They MUST be stateless and immutable. They MUST NOT subclass LangGraph `AgentState`; middleware MAY map them into `AgentState` fields.

- **Axiom artifact and graph correspondence.** An axiom artifact in Python SHOULD correspond 1:1 to a defined multiset (or set) of triples or quads **actually present** in the graph for that axiom's mapping, not to a closed tree of fully interpreted OWL objects whose supporting triples may be missing elsewhere.

## Consequences

- Research Agents and tools retain a stable, schema-driven interface to axioms and graph-scoped data; JSON Schema stays small and guidance-oriented.
- Partial ontologies and incremental authoring are modeled honestly: operands are nodes unless and until traversal materializes separate axiom objects from the graph.
- Partitioning and deletion semantics improve: chunk shape does not depend on sibling axioms being present; parents do not retain nested axiom objects for absent subgraphs.
- **Tradeoff:** JSON Schema loses discriminated-union strength for operands when those operands are bare node identifiers instead of nested axiom types; reusable schema aliases and field descriptions SHOULD mitigate misuse.
- **Known follow-up (design drift):** `Seq[T: StructuralElement]` in `rdflib-reasoning-axioms` and its use in `DataIntersectionOf`, `DataUnionOf`, `DataComplementOf`, and `DatatypeRestriction` violate the no-composition rule. A follow-up redesign SHOULD preserve RDF list scaffolding (list cell identifiers, `rdf:first` / `rdf:rest`) while representing sequence members as **node-level** operands, not nested `StructuralElement` instances.
- Stricter OWL alignment and shallow serialization remain required for new structural elements; error message conventions remain as in DR-002; a future DR may standardize machine-readable error shape.
- `rdflib-reasoning-axioms` and `rdflib-reasoning-middleware` documentation SHOULD remain aligned with these rules as the code is brought into compliance.

## Supersedes

- [DR-002 Structural Elements and Middleware Integration](DR-002%20Structural%20Elements%20and%20Middleware%20Integration.md)
