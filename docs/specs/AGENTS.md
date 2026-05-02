# External Specifications

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

- Specification directories MAY be generated W3C spec caches, curated
  repository crosswalks, or external inspiration references. Local `AGENTS.md`
  files SHOULD be tailored to the artifact class of their directory.
- Each `docs/specs/<specname>/` directory SHOULD contain a brief, dense,
  hand-maintained `AGENTS.md` that explains when to use the directory and how
  to reach its highest-value local artifacts quickly.
- Local `AGENTS.md` files MUST NOT be dynamically generated and MUST NOT be
  ignored by `.gitignore`.
- Generated W3C spec directories use `optimized.html` as the Development
  Agent- and tooling-oriented copy of the source specification. If present,
  `optimized.html` MUST prune presentational content while preserving or adding
  semantic structure that helps agents and scripts understand the specification.
- Generated W3C spec directories with `create-index.py` MUST contain an
  `AGENTS.md`; `create-index.py` MUST regenerate both `INDEX.md` and
  `index-data.json`. `INDEX.md` is the primary dynamic Development
  Agent-facing lookup artifact, and `index-data.json` is the machine-readable
  sidecar for joins, crosswalks, and other tooling.
- Curated repository crosswalk directories use authored lookup tables and
  sidecar data to connect multiple specifications. Their local `AGENTS.md`
  SHOULD identify generated artifacts, hand-maintained authoring inputs, and
  any non-normative status fields that must not be confused with implementation
  maturity.
- External inspiration reference directories contain fetched documentation or
  source used for comparison and design awareness only. Their local `AGENTS.md`
  MUST explain the no-copy policy and SHOULD point to stable high-value entry
  points rather than static file listings.
- One SHOULD use `make specs-normalize` [Makefile target](../../Makefile) to
  fetch & normalize generated W3C specifications if they are absent.
- Use the **Hint** column to identify which specs are relevant for a task; short-names do not always reflect content (e.g. RL forward rules live in `owl2-reasoning-profiles`, not in `owl2-semantics-rdf`).

| Spec | Hint |
| ---- | ---- |
| `docs/specs/jena-inspiration/AGENTS.md` | Apache Jena docs & source; design inspiration; "how have others achieved this?"; fetch via `fetch-jena.sh`. Not a W3C spec. |
| `docs/specs/owl2-conformance/optimized.html` | Conformance, test types, entailment checker, test case format, input ontologies. |
| `docs/specs/owl2-crosswalks/AGENTS.md` | Relationships / mappings between specifications; RL Rules, RDF-based semantics, RDF mapping, RDFS Semantics |
| `docs/specs/owl2-mapping-to-rdf/AGENTS.md` | OWL structural elements → RDF triples; `as_triples`/`as_quads` conformance; axiom serialization; primary ref for StructuralElement output. |
| `docs/specs/owl2-overview/optimized.html` | OWL 2 high-level overview; introductory. |
| `docs/specs/owl2-reasoning-profiles/AGENTS.md` | OWL 2 RL/EL/QL profiles; **forward-chaining rule tables** (Section 4.3); rule identifiers (e.g. prp-dom, cls-thing, scm-cls, eq-ref). |
| `docs/specs/owl2-semantics-direct/optimized.html` | OWL 2 direct semantics (model-theoretic). |
| `docs/specs/owl2-semantics-rdf/AGENTS.md` | OWL 2 RDF-based semantics (interpreting OWL ontologies in RDF). |
| `docs/specs/owl2-structure-syntax/optimized.html` | OWL 2 structural syntax; BNF; definitions of structural elements (Class, ObjectProperty, etc.). |
| `docs/specs/rdf11-concepts-syntax/optimized.html` | RDF 1.1 concepts and abstract syntax; triples, IRIs, literals, blank nodes. |
| `docs/specs/rdf11-datasets/optimized.html` | RDF 1.1 datasets; named graphs; quads; dataset semantics. |
| `docs/specs/rdf11-primer/optimized.html` | RDF 1.1 primer; introductory; examples. |
| `docs/specs/rdf11-schema/optimized.html` | RDFS vocabulary (rdfs:Class, rdfs:subClassOf, etc.). |
| `docs/specs/rdf11-semantics/AGENTS.md` | RDF 1.1 model theory; **RDFS entailment rules** (rdfs1–rdfs13); formal semantics. |
