---
name: structural-elements-middleware-design
overview: Apply and formalize the structural element design for rdflib-reasoning, including Pydantic-based GraphBacked/StructuralElement rules, JSON Schema guidance conventions, and LangChain middleware alignment, and record it as a new decision record.
todos:
  - id: tighten-structural-element-core
    content: Refine `GraphBacked` and `StructuralElement` docs/signatures and add `as_quads` implementation
    status: completed
  - id: document-type-boundaries-and-context
    content: Document allowed rdflib/third-party types and `context`/related semantics in structural elements and axioms docs
    status: completed
  - id: json-schema-guidance-rules
    content: Codify terse, guidance-optimized JSON Schema and error conventions in AGENTS/docs
    status: completed
  - id: middleware-alignment-docs
    content: Clarify LangChain middleware relationship for GraphBacked/StructuralElement in middleware and root docs
    status: completed
  - id: new-decision-record-structural-elements
    content: Create and index a new decision record capturing this structural-elements-and-middleware design
    status: completed
isProject: false
---

# Structural elements & middleware design

## Goals

- **Align structural elements** (`GraphBacked`, `StructuralElement`, and concrete subclasses) with the clarified principles for Pydantic modeling, graph context semantics, and LangChain middleware usage.
- **Codify JSON Schema and error-message conventions** so they are actionable for authors and consumable by runtime agents.
- **Introduce `as_quads`** to make the `context` semantics operational.
- **Capture the design as a formal DR** under `docs/dev/decision-records/` using the existing DR template and indexing rules.

## Steps

- **1. Tighten core structural element docs and signatures**
  - Update class and method docstrings in `[rdflib-reasoning-axioms/src/rdflibr/axiom/structural_element.py](rdflib-reasoning-axioms/src/rdflibr/axiom/structural_element.py)` to:
    - Make `GraphBacked` the universal base for graph-scoped Pydantic models.
    - Make `StructuralElement` the universal base for OWL 2 structural elements.
    - Clearly state that `as_triples` MUST NOT recurse into related elements and that generated triples are spec-aligned.
  - Add a concrete `as_quads` method (likely on `GraphBacked` or `StructuralElement`) that converts `as_triples` to quads by appending `context`.
- **2. Clarify allowed rdflib and third‑party types**
  - In `structural_element.py` (and, if helpful, `[rdflib-reasoning-axioms/AGENTS.md](rdflib-reasoning-axioms/AGENTS.md)`), document that:
    - Structural elements MAY use rdflib node types (`URIRef`, `BNode`, `Literal`, `IdentifiedNode`, etc.).
    - Structural elements and other `GraphBacked` models MUST NOT embed `rdflib.Graph`, `ConjunctiveGraph`, SPARQL result objects, or similar container/session/handle types.
- **3. Define `context` and “related” semantics**
  - In `GraphBacked` docs, define `context` as a single, required context identifier for all facts represented by the instance.
  - Clarify that:
    - Any field whose type is another `GraphBacked` (or `StructuralElement`) instance MUST share the same `context`.
    - Cross-context relationships, if any, are expressed only at the triple/quad level, not by embedding foreign-context `GraphBacked` instances.
  - If appropriate, add a lightweight validator enforcing context equality for embedded `GraphBacked` fields.
- **4. Codify JSON Schema “terse, guidance-optimized” rules**
  - In a central doc for contributors (e.g., `[rdflib-reasoning-axioms/AGENTS.md](rdflib-reasoning-axioms/AGENTS.md)` or a short section in `[AGENTS.md](AGENTS.md)`), write explicit bullets capturing:
    - The definition of **joint documentation** as only what appears in Pydantic’s JSON Schema for the model and its fields.
    - Field descriptions MUST complement, not duplicate, class/other-field docs, and complex interactions SHOULD be documented at the enclosing class.
    - Schema descriptions MUST NOT assume module/repo docs; they MAY reference official specification identifiers (e.g., RFC numbers) but MUST NOT reference DRs or internal `optimized.html` artifacts.
    - Examples SHOULD be used sparingly and only when they materially reduce misuse.
- **5. Codify “optimized for guidance” constraints and error conventions**
  - Document JSON Schema / Pydantic type rules:
    - Constrained types SHOULD be used wherever possible to reduce search space; unconstrained types MUST NOT be used without explicit approval from a user.
  - Document error message conventions (future-proofed):
    - Errors MUST call out illegal values and SHOULD describe valid ranges in human/agent-friendly terms (omitting overly complex regexes where they add cognitive load).
    - Errors SHOULD recommend a concrete fix and, when they reflect spec violations, MUST reference the governing spec + section using official identifiers.
    - Where feasible, errors SHOULD follow a consistent pattern (short summary, illegal value(s), valid range hint, spec reference if applicable), while allowing future DRs to refine structure.
- **6. Clarify LangChain middleware relationship**
  - In `[rdflib-reasoning-middleware/README.md](rdflib-reasoning-middleware/README.md)` and/or `[AGENTS.md](AGENTS.md)`, state that:
    - `GraphBacked` / `StructuralElement` instances MUST be usable as tool argument/response models and as values carried inside middleware state.
    - `GraphBacked` elements are stateless and immutable domain snapshots.
    - `GraphBacked` and `StructuralElement` MUST NOT subclass LangGraph `AgentState`; middleware MAY map them into `AgentState` fields.
- **7. Align package-level docs with the new rules**
  - Update `[rdflib-reasoning-axioms/AGENTS.md](rdflib-reasoning-axioms/AGENTS.md)` to:
    - Explicitly state that each concrete `StructuralElement` corresponds to a well-identified OWL 2 structural element (or clearly documented extension).
    - Note that `as_triples` / `as_quads` MUST conform to `owl2-mapping-to-rdf` and transitive specs (e.g., `rdf11-semantics`).
    - Mention RDF-star-like triple-statements as potential `GraphBacked` but non-`StructuralElement` models, tied to RDF 1.2/RDF-star semantics.
- **8. Create a new decision record**
  - Follow the `new-decision-record` skill and `[docs/dev/decision-records/AGENTS.md](docs/dev/decision-records/AGENTS.md)` to:
    - Determine the next `DR-XXX` number based on existing files in `[docs/dev/decision-records/](docs/dev/decision-records/)`.
    - Draft a DR using `[docs/dev/decision-records/template.md](docs/dev/decision-records/template.md)` capturing:
      - Title: structural elements & middleware integration (shortened appropriately).
      - Status: likely `Proposed` or `Accepted` depending on your intent.
      - Context: motivations (agent-first design, LangChain middleware, OWL2 alignment).
      - Decision: the rules for `GraphBacked`/`StructuralElement`, JSON Schema terseness/guidance, error conventions, LangChain boundary, and context semantics.
      - Consequences: benefits (agent guidance, interoperability, testability) and trade-offs (stricter schemas, more disciplined error messages).
      - Supersedes: reference any prior DRs if applicable.
    - Update `[docs/dev/decision-records/INDEX.md](docs/dev/decision-records/INDEX.md)` with a new row for this DR, wiring any Supersedes/Superseded By links as appropriate.
- **9. Sanity-check with example models**
  - Optionally, pick one or two existing or planned structural elements and:
    - Ensure they follow the new inheritance, context, and type constraints.
    - Inspect their generated JSON Schema to confirm terseness and guidance quality.
    - Verify that validation errors match the new conventions and are suitable for use in LangChain middleware and tools.
