# External Specifications

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

- `docs/specs/<specname>/` subdirectories are dynamically-retrieved files for some set of specifications
- Each `docs/specs/<specname>/` directory SHOULD contain an `AGENTS.md`.
- If a `docs/specs/<specname>/` directory contains `create-index.py`, it MUST contain an `AGENTS.md`.
- `docs/specs/<specname>/AGENTS.md` is the primary static Development Agent-facing summary artifact for the directory. It MUST be brief, dense, hand-maintained, explain the purpose of the local `INDEX.md`, and refer Development Agents to `INDEX.md` for dynamic references.
- `docs/specs/<specname>/AGENTS.md` MUST NOT be dynamically generated.
- `docs/specs/<specname>/AGENTS.md` MUST NOT be ignored by `.gitignore`.
- If a `docs/specs/<specname>/` directory contains `create-index.py`, then that script MUST generate both `INDEX.md` and `index-data.json`.
- `docs/specs/<specname>/INDEX.md` is the primary dynamic Development Agent-facing index artifact. It SHOULD present the indexed information directly, using markdown structure or tables as appropriate for the content.
- `docs/specs/<specname>/index-data.json` is the machine-readable sidecar intended for joins, crosswalk generation, and other tooling.
- `docs/specs/<specname>/optimized.html` MUST be optimized for Development Agent and script/tooling understanding, if it is present. Elements SHOULD be pruned of presentational content, retaining/adding elements where the semantics of the data become more clear. Element `class` attributes can serve as a way to denote the category of an item.
- One SHOULD use `make specs-normalize` [Makefile target](../../Makefile) to fetch & normalize these specifications if they are absent.
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
