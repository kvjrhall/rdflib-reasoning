# EXAMPLE-004 Architecture document

_Exported on 3/10/2026 at 08:39:27 EDT from Cursor (2.6.14)_

---

**User**

Consider the following proposal: `architecture.md` MUST be a standalone document representing the cumulative understanding of the system after "applying" all of the decision-records in sequence. In practice, this means that an agent need only to consume `architecture.md` to understand the system as-it-is / as-it-should-be.

MY SPECULATION: If we implicitly require an agent to understand the culminated design, then we risk it only reeading a subset of the records and for it to become confused while attempting to validate the compliance of the system with our architecture secification.

---

**Cursor**

Reading the architecture doc and decision-records structure to ground the response.

Here’s a concise take on the proposal and your concern.

**Proposal (as I understand it)**

- `architecture.md` is the **single, standalone** statement of the system: “apply” all decision records in sequence and you get the content that should be in `architecture.md`.
- For “as-it-is / as-it-should-be,” an agent **only needs** `architecture.md`; it doesn’t need to re-derive the design from the DRs.

**Your concern**
If we only _implicitly_ assume “the agent understands the culminated design,” we don’t actually tell it _where_ that culminated design lives. So in practice an agent might:

- Follow links from `architecture.md` into individual DRs, or
- Discover `INDEX.md` / `decision-records/` and read a **subset** of DRs,

and then try to validate compliance using that **partial** view. Because DRs are rationale and context (and may overlap, or refer to each other), a subset can be inconsistent or incomplete, so the agent gets a wrong or confused picture of what “compliant” means.

So the risk isn’t that “architecture is cumulative” is wrong—it’s that **we never make the consumption contract explicit**, so agents (and tooling) aren’t steered to treat `architecture.md` as the sole source for compliance and “current design.”

**What would mitigate the risk**
Making the contract **explicit** in the same place(s) agents are told how to use `docs/dev/`:

1. **In `docs/dev/AGENTS.md` (or equivalent)**
   State clearly:
   - For understanding the **current** system and validating **compliance** with the architecture, use **only** `architecture.md`.
   - Decision records are **rationale and history**; they must stay consistent with `architecture.md`, but they are not the specification for “as-it-should-be.”

2. **In `architecture.md` itself**
   A short “How to use this document” (or similar) that says:
   - This file is the **standalone** specification of the current architecture.
   - For compliance checks and “as-it-should-be” reasoning, use this document; do not rely on a subset of decision records.

3. **Optional: in `decision-records/AGENTS.md`**
   Reinforce that DRs are **inputs** that have been folded into `architecture.md`; the **output** for “what the system is” is `architecture.md`. So when validating the system, read `architecture.md`, not the DR set.

**Summary**
Your speculation is about **agent behavior under ambiguity**: without an explicit “read this one doc for compliance,” agents may reasonably follow links or explore the DR folder and then reason from an incomplete set of DRs. The fix is to make the rule **explicit** (“architecture.md is the single source for current design and compliance; DRs are supporting rationale”) in the docs that define how agents should use `docs/dev/`, so the “implicit” requirement becomes a clear, machine- and human-actionable instruction.

---

**User**

Let's make the necesary updates to mitigate the risk. Some subtle notes:

> Decision records are rationale and history; they must stay consistent with architecture.md, but they are not the specification for “as-it-should-be.”

It is not the case that **they** (the DRs) must stay consistent with `architecture.md` (in that they require updates). Instead, the architecture must be consistent with the current decision records. For example, If a new decision supercedes an old one, then the architecture should reflect the newer DR's changes to the superseded DR rather than updating the older DR to match the architecture.

Your optional change to `decision-records/AGENTS.md` is a good suggestion. I think that we want the agent to know that it should consider `architecture.md` as its baseline when it is drafting decision records, too. "When validating the system" may imply that the agent does not need to consider it for other tasks.

We should be cautious that we might update `architecture.md` _without_ an associated decision record, so it should always be the authoritative reference for the system's "as it should be" state. The actual code, of course, being the authority on "as it is". I do not know if we should make that association (code: as it is) explicit, as that's pretty strongly embedded in task/domain understanding for Development Agents, no?

---

**Cursor**

We’re aligned on the intent; I’ll sketch **exact wording** you can paste into the docs to mitigate the risk while respecting your subtleties.

### 1. Update `docs/dev/architecture.md`

Add a usage section near the top (after the intro paragraph, before `## Agent roles`):

```markdown
## How to use this document

- **Authoritative intended architecture**: This file is the single authoritative description of how the system *should* be structured and behave ("as it should be").
- **Decision records as history**: Decision records in `docs/dev/decision-records/` capture the rationale and history that led to this architecture. Do not infer the current architecture from a subset of decision records; always treat this document as the baseline.
- **Code as implementation**: The source code is the authority on how the system *currently* behaves ("as it is"). Where the code and this document disagree, that discrepancy represents design drift to be resolved by code changes, documentation changes, and/or new decision records.
```

This makes it explicit that:

- `architecture.md` is the **“as it should be”** spec (even if sometimes updated without a DR).
- DRs are **history/rationale**, not the operational spec.
- Code is **“as it is”**, called out explicitly (low-risk clarity for agents).

### 2. Refine `docs/dev/decision-records/AGENTS.md`

You already have:

> - The cumulative interpretation of all decision records MUST be consistent with `docs/dev/architecture.md`
> - `docs/dev/architecture.md` MUST be updated if it conflicts or contradicts the decision record.
> - `docs/dev/architecture.md` SHOULD be updated if the decision record is with respect to the architecture or design...

To reflect your nuance (architecture must be kept consistent with _current_ DRs, DRs themselves aren’t retro-edited except via superseding), I’d tweak and extend as follows.

**Replace the existing three bullets under “Decision Records” with:**

```markdown
- The cumulative interpretation of all decision records MUST be consistent with [`docs/dev/architecture.md`](../architecture.md).
- When a new or updated decision record changes the intended architecture, `docs/dev/architecture.md` MUST be updated to reflect that change (typically by treating the architecture as having been changed as of the new record's date).
- `docs/dev/architecture.md` MAY also be updated directly (e.g., for clarifications or non-substantive adjustments), but for substantive architectural changes a new or updated decision record SHOULD be authored.
```

**Then add an explicit “How agents should use decision records” subsection:**

```markdown
## How agents should use decision records

- **Architecture baseline**: When validating or reasoning about the current intended system design, Development Agents MUST use [`docs/dev/architecture.md`](../architecture.md) as the single source of truth for the "as it should be" architecture. Decision records provide supporting rationale and history only.
- **Avoid partial DR inference**: Development Agents MUST NOT attempt to infer the current architecture by applying only a subset of decision records; this risks inconsistency. Always reason from `architecture.md` when talking about the present intended design.
- **Drafting new decision records**: When drafting a new decision record that affects architecture or design, Development Agents MUST first read [`docs/dev/architecture.md`](../architecture.md) and treat it as the baseline that the decision modifies.
- **Superseding**: When a new decision changes or overturns an older one, it MUST be expressed as a new decision record that explicitly supercedes the older record (see "Superceding" below), and `architecture.md` MUST be updated to reflect the newer decision. Older records generally SHOULD NOT be retroactively rewritten to match the architecture.
```

This:

- Corrects my earlier “DRs must stay consistent with architecture” framing to your intended direction: **architecture must reflect current DRs**, not vice versa.
- Explicitly instructs agents **not** to reason from partial DR sets.
- Tells agents to **use `architecture.md` as the baseline when drafting DRs**, which addresses your concern that “when validating the system” might sound too narrow.

### 3. Small addition to `docs/dev/AGENTS.md` (optional but useful)

To centralize the mental model for Development Agents, you can add a short subsection, for example near the top or after the existing bullet list:

```markdown
## Architecture, decision records, and code

- **Intended architecture ("as it should be")**: `docs/dev/architecture.md` is the authoritative description of the current intended architecture and design.
- **Rationale and history**: `docs/dev/decision-records/` capture why the architecture is the way it is and how it evolved; they are not, by themselves, the operational specification for the current state.
- **Implementation ("as it is")**: The codebase is the authority on the system’s actual behavior. When code and `architecture.md` disagree, treat this as a discrepancy to be resolved via code changes, documentation changes, and/or new decision records.
```

This makes the association “code = as it is” explicit without being heavy‑handed, and sets the triad (architecture / DRs / code) clearly for agents.

---

I’m in Ask mode, so I can’t apply these edits directly, but if you paste these snippets into the respective files (with any local style tweaks you prefer), you’ll have:

- A **clear contract** that `architecture.md` is the single source of truth for “as it should be”.
- Explicit instructions that **partial DR reading is not a valid way** to infer current architecture.
- Guidance that **DRs change architecture by updating `architecture.md` and superseding old DRs**, not by mutating history.

---

**User**

Go ahead and make the reccomended edits.

---

**Cursor**

I’ll update `architecture.md`, `decision-records/AGENTS.md`, and `docs/dev/AGENTS.md` to encode the authoritative role of `architecture.md`, how DRs relate to it, and how agents should use both, then summarize.

Now I’ll patch the three markdown files to add the usage/authority sections and refined guidance for agents.

Got the architecture and decision-records docs updated; now I’ll add the small triad explanation to the top-level dev AGENTS file.

### Summary of changes

- **`docs/dev/architecture.md`**: Added a **“How to use this document”** section that makes it the single authoritative source for the “as it should be” architecture, clarifies DRs as rationale/history only, and explicitly states that code is the “as it is” implementation.
- **`docs/dev/decision-records/AGENTS.md`**: Refined rules so that **architecture is kept consistent with current DRs**, not vice versa; added a **“How agents should use decision records”** section covering architecture as baseline, avoiding partial DR inference, drafting new DRs from `architecture.md`, and superseding behavior.
- **`docs/dev/AGENTS.md`**: Added an **“Architecture, decision records, and code”** section that establishes the triad: `architecture.md` as intended design, DRs as history/rationale, and the codebase as authoritative “as it is,” with drift treated as something to resolve via code/docs/DR updates.

---

**User**

Please review @docs/dev/architecture.md . Is it currently standalone, or does it defer to decision records for definitions or descriptions?

---

**Cursor**

### Short answer

- **It is not fully standalone.**
- It **asserts** that it is the authoritative “as it should be” description (lines 6–10), but:
  - For **agent role terminology**, it defers to `AGENTS.md` and DR‑003.
  - For **structural elements and middleware**, it defers to DR‑002.

Concretely:

```12:21:docs/dev/architecture.md
## Agent roles

This repository distinguishes two agent types; canonical definitions are in the root [AGENTS.md](../../AGENTS.md). See [DR-003 Research Agent and Development Agent Terminology](decision-records/DR-003%20Research%20Agent%20and%20Development%20Agent%20Terminology.md).

- **Research Agent**: Runtime agent (subject of research); consumes middleware, tools, and generated schema; does not see repository or design docs.
- **Development Agent**: Code agent (e.g. Cursor, Claude Code); reads AGENTS.md and design docs; modifies code and documentation.

## Structural elements and middleware

Structural elements and their integration with LangChain middleware are governed by [DR-002 Structural Elements and Middleware Integration](decision-records/DR-002%20Structural%20Elements%20and%20Middleware%20Integration.md): `GraphBacked` and `StructuralElement` in `rdflib-reasoning-axioms` provide the schema-facing interface used by `rdflib-reasoning-middleware` as tool and state payloads.
```

So an agent that only reads `architecture.md` gets:

- The **meta-contract** (“this is the authoritative intended architecture; DRs are history”).
- **Pointers** to DR‑002/DR‑003 and `AGENTS.md` for the normative definitions of some concepts.

If your bar for “standalone” is “no need to follow links for definitions/descriptions,” then it **still defers** and is not self-contained. If your bar is “single source of truth for current intended design, with some definitions factored out,” it behaves as that, but via cross‑references rather than inline repetition.

---

**User**

Please make architecture.md standalone.
I think that we should review and update the @.cursor/skills/new-decision-record/SKILL.md skill so that it guides the Development Agent towards making changes to `architecture.md` as well.

---

**Cursor**

I’ve reviewed `architecture.md` and the DR skill; next I’ll propose a focused plan to (1) inline the needed definitions into `architecture.md` so it’s standalone, and (2) update the skill so it explicitly instructs agents to treat `architecture.md` as the baseline and to update it accordingly when drafting DRs.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I’ve confirmed how “standalone” should work and gathered the DR content; next I’ll inline the necessary definitions into `architecture.md` so agents don’t need to open DRs for core concepts.

I’ve inlined the key agent-role and structural-element definitions into `architecture.md` and reframed the DR links as background, so it now reads as a self-contained spec; next I’ll update the new-decision-record skill to treat `architecture.md` as the baseline and then do a cross-doc consistency pass.

### What I implemented

- **`docs/dev/architecture.md` is now standalone for core concepts.**
  - The **Agent roles** section now contains full, normative definitions of **Research Agent** and **Development Agent**, derived from DR‑003/`AGENTS.md`, plus a brief note that links to those files are for historical/contextual detail, not for basic understanding:

```12:19:docs/dev/architecture.md
## Agent roles

This repository distinguishes two agent types:

- **Research Agent**: A deployed or runtime agent that is the subject of or participant in research. It is implemented in code, sees tools and supplied system prompts, and may see generated schema of data classes exposed through middleware or MCP. It MUST NOT see repository content such as design docs, AGENTS.md, decision records, or source code.
- **Development Agent**: A code agent (e.g. Cursor, Claude Code) that accesses design documentation, module documentation, and repository content; modifies code and documentation; and develops code to support the Research Agent and documentation to support itself.

These definitions are summarized from and kept consistent with the root [AGENTS.md](../../AGENTS.md) and [DR-003 Research Agent and Development Agent Terminology](decision-records/DR-003%20Research%20Agent%20and%20Development%20Agent%20Terminology.md), which provide historical context and additional guidance.
```

- The **Structural elements and middleware** section now spells out the architectural behavior and relationships without requiring DR‑002:

```21:33:docs/dev/architecture.md
## Structural elements and middleware

Structural elements describe OWL 2 and related graph-scoped constructs in a way that can be consumed both by middleware and by Research Agents via JSON-schema-driven tools and state.

- The `rdflib-reasoning-axioms` project defines a Pydantic model hierarchy:
  - `GraphBacked` is the universal base for graph-scoped Pydantic models.
  - `StructuralElement` is the universal base for OWL 2 structural elements and closely related extensions.
- Each instance has a single required `context` (graph identifier). Related structural elements embedded in a field share the same `context`; cross-context relationships are expressed only at the triple/quad level.
- Structural elements expose `as_triples` and `as_quads` methods whose output conforms to the OWL 2 mapping to RDF and related RDF semantics specifications.
- Models avoid embedding heavy graph/session types (such as `rdflib.Graph` or SPARQL result objects) and instead rely on node-level terms and Pydantic-generated JSON Schema as the primary interface.
- The `rdflib-reasoning-middleware` project uses `GraphBacked` and `StructuralElement` models as tool argument/response schemas and as values embedded in middleware state for Research Agents.

These rules are aligned with, and further elaborated in, [DR-002 Structural Elements and Middleware Integration](decision-records/DR-002%20Structural%20Elements%20and%20Middleware%20Integration.md).
```

- The top **How to use this document** section already states it is the _single authoritative_ “as it should be” description and clarifies DRs as history and code as “as it is”.

- **`new-decision-record` skill now treats `architecture.md` as the explicit baseline.**
  In `.cursor/skills/new-decision-record/SKILL.md`:

  - Step 6 has been strengthened from “if the decision conflicts with or relates to `architecture.md`, update it” to:

```18:22:.cursor/skills/new-decision-record/SKILL.md
4. **Index** – Append a row to [docs/dev/decision-records/INDEX.md](docs/dev/decision-records/INDEX.md): Record Date (YYYY-MM-DD), link to the new record, Supercedes (link) if any, Superceded By (leave empty), Comment (optional).

5. **Supersedes** – If this DR supersedes any document: list and link them in the new DR’s Supersedes section; add “Superseded by [DR-XXX](DR-XXX Title.md)” to those documents’ Status; update their INDEX row “Superceded By” with a link to the new DR; set the new DR’s INDEX row “Supercedes” to link to them.

6. **Architecture** – Before finalizing the record, read [docs/dev/architecture.md](docs/dev/architecture.md) and treat it as the current "as it should be" baseline. If the decision changes the intended architecture or design (not just describing current behavior), you MUST update `architecture.md` so that it reflects the new decision. Minor clarifications MAY update `architecture.md` directly without a DR, but substantive architectural changes SHOULD be accompanied by a decision record.
```

- A new **Mental model** section makes the triad explicit for the skill:

```24:32:.cursor/skills/new-decision-record/SKILL.md
## Mental model

- `docs/dev/architecture.md` – authoritative description of the current intended architecture and design.
- `docs/dev/decision-records/` – rationale and history explaining *why* and *when* the architecture changed.
- The codebase – actual behavior of the system; discrepancies between code and `architecture.md` indicate design drift to be resolved via code changes, documentation changes, and/or new decision records.

## Template reference

Sections to fill: **Title** (one line), **Status** (Proposed | Accepted | Deprecated | Superseded by …), **Context**, **Decision**, **Consequences**, **Supersedes** (optional).
```

- **Cross-doc story is consistent.**
  - `docs/dev/AGENTS.md` still defines the triad (architecture = “as it should be”, DRs = rationale/history, code = “as it is”).
  - `docs/dev/decision-records/AGENTS.md` requires architecture to be updated when DRs change intended architecture and instructs agents to reason from `architecture.md` rather than from a subset of DRs.
  - `architecture.md` now contains the necessary definitions and structural descriptions directly, while DR‑002/DR‑003 are referenced only for background/rationale.

Together, this means a Development Agent can now:

- Read **only** `docs/dev/architecture.md` to understand the intended architecture.
- Use decision records and `AGENTS.md` as history and nuance, not as required sources for basic definitions.
- Follow the skill to always **read and update `architecture.md`** when making architectural decisions, keeping the architecture doc and DR set aligned.
