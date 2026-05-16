# OWL 2 Crosswalks

- This directory contains repository-authored crosswalks built from spec-local `index-data.json` artifacts.
- `INDEX.md` is the primary Development Agent-facing artifact. It explains how to use each crosswalk and includes the current markdown tables directly.
- `crosswalk-data.json` is the machine-readable sidecar for joins, downstream tooling, and future refinement of the crosswalk model.
- `create-crosswalks.py` regenerates `INDEX.md` and `crosswalk-data.json`.
- `master-table-seed.json` is a tracked, hand-maintained authoring input. It is not generated output. Use it to record curated construct-level associations that cannot yet be derived mechanically, including `StructuralElement` subtype targets, row-completeness status, and reconstruction notes.
- The `StructuralElement` names recorded in `master-table-seed.json` should stay aligned with the `## Feature Matrix` in [rdflib-reasoning-axioms/README.md](../../../rdflib-reasoning-axioms/README.md#feature-matrix). The crosswalk `status` field is different: it describes the completeness of the crosswalk row itself, not the implementation maturity of any software component.
- Treat the crosswalks as curated repository guidance layered over the source specifications, not as normative specification text.
