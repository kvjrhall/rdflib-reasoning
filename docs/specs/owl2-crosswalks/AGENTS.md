# OWL 2 Crosswalks

- This directory contains repository-authored crosswalks built from spec-local `index-data.json` artifacts.
- `INDEX.md` is the primary Development Agent-facing artifact. It explains how to use each crosswalk and includes the current markdown tables directly.
- `crosswalk-data.json` is the machine-readable sidecar for joins, downstream tooling, and future refinement of the crosswalk model.
- `create-crosswalks.py` regenerates `INDEX.md` and `crosswalk-data.json`.
- `master-table-seed.json` is a tracked, hand-maintained authoring input. It is not generated output. Use it to record curated construct-level associations that cannot yet be derived mechanically, including `StructuralElement` subtype targets, implementation status, and reconstruction notes.
- The `StructuralElement` names and status values recorded in `master-table-seed.json` should align with the `## Feature Matrix` in [rdflib-reasoning-axioms/README.md](/Users/roberthall/Projects/rdflib-reasoning/rdflib-reasoning-axioms/README.md). Treat that matrix as the repository reference point for feature naming and status vocabulary unless there is an intentional, documented divergence.
- Treat the crosswalks as curated repository guidance layered over the source specifications, not as normative specification text.
