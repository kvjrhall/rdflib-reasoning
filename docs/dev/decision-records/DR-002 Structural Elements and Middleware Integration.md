# Structural Elements and Middleware Integration

## Status

Accepted

## Context

The repository supports research into agents and their interoperability with formal logic. Structural elements (OWL 2 and other graph-scoped constructs) need to be consumable by LangChain [Custom Middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom) and by Research Agents (runtime agents) as tool arguments/responses and state payloads. To achieve that, their schema must be exposed via Pydantic, remain terse and guidance-optimized for Research Agents, and avoid embedding complex third-party structures. A single, required graph context per element simplifies reasoning and equality; validation errors must support correction by Research Agents and humans.

## Decision

- **Pydantic hierarchy.** All domain data models at the interface of `rdflib-reasoning-middleware` MUST be Pydantic models. Strong reasons to deviate MUST be documented. `GraphBacked` is the universal base for graph-scoped Pydantic models; `StructuralElement` is the universal base for all OWL 2 structural elements. Non-OWL constructs (e.g. RDF-star triple-statements per RDF 1.2) MAY be `GraphBacked` without subclassing `StructuralElement`.

- **No embedded graphs or heavy third-party types.** Structural elements and other `GraphBacked` models MUST NOT contain `rdflib.Graph`, `ConjunctiveGraph`, SPARQL result objects, or other container/session/handle types. They MAY use rdflib node-level types (`URIRef`, `BNode`, `Literal`, `IdentifiedNode`, etc.).

- **Context and related elements.** Each instance has a single, required `context` (graph identifier). Related structural elements (e.g. those embedded in a field) MUST share the same `context`; enforce via validators. Cross-context relationships are expressed only at the triple/quad level. Provide `as_quads` so that triples from `as_triples` are converted to quads by appending `context`.

- **OWL 2 alignment.** Each concrete `StructuralElement` subclass MUST correspond to a well-identified OWL 2 structural element (or clearly documented extension). `as_triples` and `as_quads` MUST conform to `owl2-mapping-to-rdf` and transitive specs (e.g. `rdf11-semantics`).

- **JSON Schema: terse and guidance-optimized.** Descriptions assume only the "joint documentation" (Pydantic-generated JSON Schema for the model and its fields). They MUST NOT assume module/repo docs, decision records, or internal artifacts; they MAY reference official specification identifiers (e.g. RFC numbers, W3C spec URIs). Field descriptions MUST complement, not duplicate, other docs; complex interaction at enclosing class level. Examples SHOULD be used sparingly when they materially reduce misuse. Constrained types SHOULD be used wherever possible; unconstrained types MUST NOT be used without explicit user approval.

- **Validation errors.** Errors MUST specify illegal values; SHOULD describe valid ranges in human- and Research Agent–friendly terms; SHOULD recommend a concrete fix. Spec violations MUST reference the governing spec and section using official identifiers. Where feasible, errors SHOULD follow: short summary, illegal value(s), valid range hint, spec reference if applicable. Exact error shape may be refined in a future decision.

- **LangChain middleware.** `GraphBacked`/`StructuralElement` instances MUST be usable as tool argument/response models and as values in middleware state. They MUST be stateless and immutable. They MUST NOT subclass LangGraph `AgentState`; middleware MAY map them into `AgentState` fields.

## Consequences

- Research Agents and tools get a stable, schema-driven interface to axioms and graph-scoped data; JSON Schema stays small and guidance-oriented.
- Stricter type and context rules improve consistency and testability; new structural elements require explicit OWL 2 (or spec) alignment.
- Error message conventions improve debuggability and Research Agent self-correction; a future DR may standardize machine-readable error shape.
- `rdflib-reasoning-axioms` and `rdflib-reasoning-middleware` documentation (AGENTS.md, README, code docstrings) have been updated to reflect these rules.

## Supersedes

None.
