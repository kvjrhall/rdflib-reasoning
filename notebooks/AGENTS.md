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

## Drift policy

Notebook drift is a correctness issue. When code, documentation, or repository
policy changes affect behavior demonstrated by a checked-in notebook, the
Development Agent MUST update the notebook in the same change or explicitly
confirm that the notebook is unaffected.

The Development Agent MUST check for notebook impact when changing:

- Public package APIs, imports, installation requirements, or package layout.
- Middleware composition, tool behavior, tool descriptions, generated schemas,
  prompts, continuation behavior, or tracing behavior used by notebook demos.
- Shared notebook helpers, task text, target graphs, expected graph shapes,
  scoring metrics, proof rendering, or evaluation payloads.
- The suggested reading order, tutorial path, or notebook descriptions in
  `notebooks/README.md`, the root `README.md`, or Sphinx pages.

Notebook series that compare Research Agent conditions MUST remain comparable.
When a change affects shared task text, baseline prompt guidance, middleware
affordances, model-provider assumptions, target graphs, scoring helpers, or
saved metric interpretation, the Development Agent MUST either update each
affected condition consistently or state in notebook prose that the change is a
deliberate condition difference.

Saved notebook outputs MAY be kept when they are part of the research or
demonstration record. They MUST NOT silently contradict current prose or code.
If a behavior change makes saved output stale, the Development Agent SHOULD do
one of the following:

- Rerun the affected notebook and commit the refreshed output.
- Clear or remove misleading output.
- Mark the output or section as historical and explain why it is retained.

Notebooks that require optional research dependencies, credentials, model
provider access, network access, or long-running execution SHOULD state those
requirements near the setup cells. If a notebook cannot be executed during a
change, the Development Agent SHOULD report the reason and validate any
reusable helpers or extractable code paths that can run locally.

Reusable Python helpers under `notebooks/**/*.py` are reusable source files.
They MUST follow repository Python, typing, linting, and docstring policy.
Notebook cells in `notebooks/**/*.ipynb` are exempt from docstring linting, but
their prose, imports, examples, and saved outputs remain subject to this policy.

## Validation

- Run `make check` after editing notebooks, notebook helpers, or notebook
  guidance.
- Run or audit affected notebooks when execution is feasible in the local
  environment.
- Use `notebooks/audit_demo_series.py` when changing the middleware demo series
  or when reviewing condition comparability across that series.
