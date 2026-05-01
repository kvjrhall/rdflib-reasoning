# Notebook Guidance

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

Notebooks in this directory are research, demonstration, tutorial, and
evaluation artifacts. They are not a separately published package, but they
SHOULD remain executable, readable, and aligned with the repository architecture.

## Task routing

- RDFLib reasoning tutorials SHOULD use the `rdflib-reasoning-engine` package
  directly when demonstrating materialization, retraction, proof reconstruction,
  rendering, or contradiction diagnostics.
- Research Agent middleware demos SHOULD use explicit middleware composition
  rather than hidden prompt changes. Dataset, vocabulary, continuation, and
  inference capabilities MUST be exposed or withheld through middleware choices.
- Middleware demo notebooks SHOULD preserve comparability across conditions by
  using shared task text, shared evaluation helpers, and consistent parseability
  or scoring criteria where such helpers already exist.
- Proof and evaluation notebooks SHOULD keep typed proof/evaluation payloads
  distinct from notebook-only rendering or display conveniences.

## Reference routing

- Use `docs/specs/rdf11-primer/optimized.html` and
  `docs/specs/owl2-overview/optimized.html` for broad orientation.
- Use `docs/specs/rdf11-semantics/AGENTS.md` for RDFS entailment rules and RDF
  model-theory details.
- Use `docs/specs/owl2-reasoning-profiles/AGENTS.md` for OWL 2 RL rule names,
  rule families, and forward-chaining rule tables.
- Use `docs/specs/owl2-mapping-to-rdf/AGENTS.md` and
  `docs/specs/owl2-crosswalks/AGENTS.md` when notebook work touches structural
  OWL elements, RDF mapping, traversal, or inferred OWL content.

## Maintenance

- Notebook prose MUST preserve the distinction between Research Agents and
  Development Agents as defined in the root `AGENTS.md`.
- Notebook edits SHOULD avoid introducing one-off task definitions, prompts,
  metrics, or renderers when an existing shared helper already expresses the
  same concept.
- Notebook outputs MAY be refreshed when needed for clarity, but code and prose
  changes SHOULD remain reviewable and limited to the notebook's purpose.
