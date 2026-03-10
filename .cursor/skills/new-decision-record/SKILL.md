---
name: new-decision-record
description: Infer a decision record from the current chat and write it as a new DR under docs/dev/decision-records using the template. Use when the user asks to create or record a decision from the conversation, or to write a DR/ADR.
---

# New Decision Record

Create a new decision record from the current conversation. Follow [docs/dev/decision-records/AGENTS.md](docs/dev/decision-records/AGENTS.md) for all DR rules (location, naming, INDEX, architecture, supersedes).

## Workflow

1. **Infer** – From the conversation, extract: title/topic, context (why), decision (what), consequences (outcomes).

2. **Next number** – List `DR-*.md` in `docs/dev/decision-records/`; take the maximum number + 1, zero-pad to three digits (e.g. 001, 002).

3. **Write** – Create `docs/dev/decision-records/DR-XXX Short Title.md` using [docs/dev/decision-records/template.md](docs/dev/decision-records/template.md). Use the section headings: Title, Status, Context, Decision, Consequences, Supersedes (if applicable). Filename pattern: `DR-XXX` followed by a space and a short title.

4. **Index** – Append a row to [docs/dev/decision-records/INDEX.md](docs/dev/decision-records/INDEX.md): Record Date (YYYY-MM-DD), link to the new record, Supercedes (link) if any, Superceded By (leave empty), Comment (optional).

5. **Supersedes** – If this DR supersedes any document: list and link them in the new DR’s Supersedes section; add “Superseded by [DR-XXX](DR-XXX Title.md)” to those documents’ Status; update their INDEX row “Superceded By” with a link to the new DR; set the new DR’s INDEX row “Supercedes” to link to them.

6. **Architecture** – Before finalizing the record, read [docs/dev/architecture.md](docs/dev/architecture.md) and treat it as the current "as it should be" baseline. If the decision changes the intended architecture or design (not just describing current behavior), you MUST update `architecture.md` so that it reflects the new decision. Minor clarifications MAY update `architecture.md` directly without a DR, but substantive architectural changes SHOULD be accompanied by a decision record.

## Mental model

- `docs/dev/architecture.md` – authoritative description of the current intended architecture and design.
- `docs/dev/decision-records/` – rationale and history explaining *why* and *when* the architecture changed.
- The codebase – actual behavior of the system; discrepancies between code and `architecture.md` indicate design drift to be resolved via code changes, documentation changes, and/or new decision records.

## Template reference

Sections to fill: **Title** (one line), **Status** (Proposed | Accepted | Deprecated | Superseded by …), **Context**, **Decision**, **Consequences**, **Supersedes** (optional).
