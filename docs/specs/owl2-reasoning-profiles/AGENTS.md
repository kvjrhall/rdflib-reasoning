# OWL 2 Reasoning Profiles

- This directory is the primary source for OWL 2 RL rule anchors used by the repository.
- `INDEX.md` is the primary Development Agent-facing artifact. Use it in two passes:
  1. Start from the operational OWL 2 RL/RDF rule anchor in Section 4.3.
  2. Follow semantic cross-references only when you need the normative semantic condition or axiomatic-triple basis for the rule.
- `index-data.json` is the machine-readable sidecar for rule-level joins and crosswalk generation.
- `create-index.py` regenerates `INDEX.md` and `index-data.json`.
- Use this spec when you need the operational OWL 2 RL/RDF rule form, not the broader normative semantic theory.
