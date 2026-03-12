# RDF 1.1 Semantics

- This directory is the primary source for RDFS entailment rules and their normalized anchors.
- `INDEX.md` is the primary Development Agent-facing artifact. Use it to locate the RDFS entailment section, the patterns subsection, and the individual `rdfs1` to `rdfs13` rules.
- `index-data.json` is the machine-readable sidecar for rule-level joins and optional RDFS support crosswalks.
- `create-index.py` regenerates `INDEX.md` and `index-data.json`.
- Use this spec when you need background RDFS entailment support that is adjacent to, but not fully included in, OWL 2 RL/RDF rules.
