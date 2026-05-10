# Standalone Structural Elements

## Status

Accepted

## Context

The repository supports research into agents and their interoperability with formal logic. Structural elements (OWL 2 and other graph-scoped constructs) need to be consumable by LangChain [Custom Middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom) and by Research Agents (runtime agents) as tool arguments/responses and state payloads. To achieve that, their schema must be exposed via Pydantic, remain terse and guidance-optimized for Research Agents, and avoid embedding complex third-party structures. A single, required graph context per element simplifies reasoning and equality; validation errors must support correction by Research Agents and humans.

RDF graphs are often **partial** and **open-world**: an OWL construct may reference IRIs or blank nodes whose defining triples (for example class declarations) are not present in the same graph. Treating one axiom head as if it _composed_ another implies a **closed subtree** of fully interpreted axiom objects and can pretend that the graph is more complete than it is. That conflicts with **partitioning** goals: a chunk's shape and meaning MUST NOT depend on having carved sibling axioms for every node an axiom mentions, and removing one partition MUST NOT leave a parent object that still "contains" children whose triples are absent or were never asserted.

At the same time, several OWL 2 RDF mappings introduce graph fragments that are **co-essential** to a single axiom's serialization (e.g. the `rdf:List` carrying `owl:intersectionOf` members). Those fragments are not separate axioms and have no meaning outside the owning axiom; pushing them down to bare nodes erases scaffolding that the owner is responsible for materializing into the graph. The model therefore needs a way to distinguish:

- **Operand references to other potentially-axiomatized nodes** (cross-axiom links that MUST stay open-world honest), from
- **Owned scaffolding fragments** that MUST be embedded in the owning axiom because they belong to that axiom's mapping and to no other.

This record **supersedes** [DR-002 Structural Elements and Middleware Integration](DR-002%20Structural%20Elements%20and%20Middleware%20Integration.md), which allowed related structural elements to be embedded as fields with a shared `context` and did not separate "owned scaffolding" from "operand reference." The framing below replaces that single-bucket posture with an explicit three-role model.

## Decision

The Pydantic class hierarchy under `GraphBacked` partitions models into three roles. Every non-trivial reference inside a `StructuralElement` MUST be one of:

1. **`StructuralElement` (axiom heads).** One OWL 2 structural element per partition. A `StructuralElement` MUST NOT compose or aggregate other `StructuralElement` instances as fields. Cross-axiom references MUST be expressed only through **RDF node-level identity** (see role 3); cross-axiom traversal and interpretation are graph-level concerns implemented by helpers, not by nesting axiom instances.
2. **`StructuralFragment` (owned scaffolding).** Sibling of `StructuralElement` under `GraphBacked`. A `StructuralFragment` models a graph fragment co-essential to one axiom's RDF mapping (canonical example: `Seq` for `rdf:List` operand lists). Fragments MAY be embedded as Pydantic fields on a single owning `StructuralElement`. A fragment's `as_triples` belongs to the owner's partition, not to a separate one. A fragment MUST share its owner's `context`; this is enforced by a centralized validator on `StructuralElement`. Fragments are not partition units on their own and are not OWL axioms.
3. **Node references via package-defined annotated aliases (`N3Resource`, `N3IRIRef`, `N3Node`, `N3ContextIdentifier`).** Used for cross-axiom links by identity. Schema-facing fields MUST use these aliases rather than raw rdflib node classes; raw rdflib node-level classes (`URIRef`, `BNode`, `Literal`, `IdentifiedNode`, etc.) MAY still be used internally in helpers, computed properties, and local logic that does not define schema-facing fields.

The remaining DR-002 constraints carry forward, refined to this framing:

- **Pydantic hierarchy.** All domain data models at the interface of `rdflib-reasoning-middleware` MUST be Pydantic models. Strong reasons to deviate MUST be documented. `GraphBacked` is the universal base for graph-scoped Pydantic models; `StructuralElement` and `StructuralFragment` are siblings beneath it. Non-OWL graph-scoped constructs (e.g. RDF-star triple-statements per RDF 1.2) MAY be `GraphBacked` directly without subclassing either.
- **No embedded graphs or heavy third-party types.** `GraphBacked` models MUST NOT contain `rdflib.Graph`, `ConjunctiveGraph`, SPARQL result objects, or other container/session/handle types.
- **Context.** Each `GraphBacked` instance has a single, required `context` (graph identifier). Cross-context relationships are expressed only at the triple or quad level. Provide `as_quads` so that triples from `as_triples` are converted to quads by appending `context`. Owned `StructuralFragment` fields MUST share the owning `StructuralElement`'s `context`.
- **Shallow `as_triples` for axiom heads.** A `StructuralElement.as_triples` MUST NOT recurse into other axiom heads. Owned `StructuralFragment` triples MAY appear in the owner's `as_triples` (the fragment's triples are part of the owner's partition); operand-position references appear only as identity (nodes, not nested axiom instances). The shallow rule is the explicit invariant and defense-in-depth against regressions.
- **OWL 2 alignment.** Each concrete `StructuralElement` subclass MUST correspond to a well-identified OWL 2 structural element (or clearly documented extension). `as_triples` and `as_quads` MUST conform to `owl2-mapping-to-rdf` and transitive specs (e.g. `rdf11-semantics`).
- **JSON Schema: terse and guidance-optimized.** Descriptions assume only the "joint documentation" (Pydantic-generated JSON Schema for the model and its fields). They MUST NOT assume module/repo docs, decision records, or internal artifacts; they MAY reference official specification identifiers (e.g. RFC numbers, W3C spec URIs). Field descriptions MUST complement, not duplicate, other docs; complex interaction at enclosing class level. Examples SHOULD be used sparingly when they materially reduce misuse. Constrained types SHOULD be used wherever possible; unconstrained types MUST NOT be used without explicit user approval.
- **Validation errors.** Errors MUST specify illegal values; SHOULD describe valid ranges in human- and Research Agent–friendly terms; SHOULD recommend a concrete fix. Spec violations MUST reference the governing spec and section using official identifiers. Where feasible, errors SHOULD follow: short summary, illegal value(s), valid range hint, spec reference if applicable. Exact error shape may be refined in a future decision.
- **LangChain middleware.** `GraphBacked` instances (and therefore both roles 1 and 2) MUST be usable as tool argument/response models and as values in middleware state. They MUST be stateless and immutable. They MUST NOT subclass LangGraph `AgentState`; middleware MAY map them into `AgentState` fields.
- **Axiom artifact and graph correspondence.** An axiom artifact in Python (a `StructuralElement` plus any owned `StructuralFragment` fields) SHOULD correspond 1:1 to a defined multiset (or set) of triples or quads **actually present** in the graph for that axiom's mapping. It is not a closed tree of fully interpreted axiom heads whose supporting triples may be missing elsewhere.

## Consequences

- Research Agents and tools retain a stable, schema-driven interface to axioms and graph-scoped data; JSON Schema stays small and guidance-oriented.
- Partial ontologies and incremental authoring are modeled honestly: cross-axiom operands are nodes unless and until traversal materializes separate axiom objects from the graph.
- Partitioning and deletion semantics improve: chunk shape does not depend on sibling axioms being present; parents do not retain nested axiom-head objects for absent subgraphs.
- Owned `rdf:List` and similar scaffolding remain expressible as first-class Pydantic structure (`StructuralFragment`) without violating the no-axiom-composition rule. The shared-context invariant is enforced centrally on `StructuralElement`, not duplicated per axiom class.
- **Tradeoff:** JSON Schema loses discriminated-union strength for cross-axiom operands when those operands are bare node identifiers instead of nested axiom types; reusable schema aliases and field descriptions SHOULD mitigate misuse. Owned-fragment fields keep their typed Pydantic schema, so this tradeoff applies only to operand references.
- Stricter OWL alignment, shallow `as_triples` for axiom heads, and aliases-only schema-facing fields remain required for new structural elements. Error message conventions remain as in DR-002; a future DR may standardize machine-readable error shape.
- `rdflib-reasoning-axioms` and `rdflib-reasoning-middleware` documentation SHOULD remain aligned with these rules as code is brought into compliance.

### Compliance reference

- `Seq` (with `SeqEntry`) is the canonical `StructuralFragment`: it encodes the OWL `rdf:List` operand carrier, embedded as a field on `DataIntersectionOf`, `DataUnionOf`, and `DatatypeRestriction` with shared `context`.
- `DataComplementOf` is the canonical operand-via-node example: its `complement_of` is an `N3Resource` (role 3), and `as_triples` is shallow.

## Supersedes

- [DR-002 Structural Elements and Middleware Integration](DR-002%20Structural%20Elements%20and%20Middleware%20Integration.md)
