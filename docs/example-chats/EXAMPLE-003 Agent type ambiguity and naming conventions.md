# Agent type ambiguity and naming conventions

_Exported on 3/9/2026 at 22:45:28 EDT from Cursor (2.6.14)_

---

**User**

I want to check for a possible ambiguity, search for where it is found, and then plan some corrective actions to address it. There may exist ambiguity when referencing "agent" in markdown documentation, python docstrings, or pydantic field descriptors. Specifically, there are two MUTUALLY EXCLUSIVE agent classes/types:

1. A deployed / runtime agent that is the subject of or participant in a research activity - Implemented in code, can see tools and supplied system prompts, canot see any of the repository (except for the generated schema of data classes exposed through middleware / MCP).
2. A code agent like Claude Code or Cursor - Accesses design documentation, module documentation, modifies code, can see repository content, etc. This agent MUST be aware of the distinction, as it develops code to support the **Research Agent**, yet develops documentation to support itself.

The presence of this potential ambiguity leads me to question:

1. Suggest a clear & unambiguous pair of names allowing us to standardize references to the two agent types. Use this pair of names when answering the remaining questions.
2. Is it clear in all usages of `agent` as to which type/class of agent is being referenced?

What is your overall assessment?

---

**Cursor**

Searching the repo for "agent" in docs, Python docstrings, and Pydantic fields to locate ambiguous usages. Proposing a naming pair, then assessing each occurrence.

Checking AGENTS.md files and Pydantic field descriptors for "agent":

Checking a few more key files to complete the picture:

Checking Python docstrings and the README for "agent":

Here’s a concise report using your two agent types and a single naming proposal.

---

## 1. Suggested unambiguous names

Use these two terms everywhere:

| Your type | Suggested term | Short definition |
|-----------|----------------|-------------------|
| Deployed / runtime agent (research subject; sees tools, schema, system prompts; no repo access) | **Research Agent** | Runtime agent that uses middleware, tools, and schema; subject of research. |
| Code agent (Cursor, Claude Code; reads docs, edits code, maintains DRs) | **Development Agent** | Agent that reads AGENTS.md and design docs, modifies code and docs, and develops for the Research Agent. |

Use **Research Agent** and **Development Agent** in all docs, docstrings, and any future Pydantic field text that refers to “agent.” Where the framework name is required (e.g. LangGraph), keep **AgentState** as-is.

---

## 2. Where “agent” appears and whether it’s clear

Search covered: all `.md` under the repo, and all `.py` (docstrings, comments, `Field(..., description=...)`). Pydantic `Field` descriptions in `rdflib-reasoning-axioms` do **not** use the word “agent”; only markdown and one Python docstring do.

### Clear or acceptable

- **approach.md**
  - “coding agent,” “agents (e.g., Claude Code),” “cursor uses AGENTS.md” → clearly **Development Agent**.
  - “Clarify the distinct agent roles” (item 7) → refers to both; good place to introduce the two terms.
- **docs/example-chats/README.md**
  - “the agent (Claude/Cursor)” → **Development Agent**.
  - “software agents” in the exclusion rule → intentionally broad (both types should not use example-chats content); could be made explicit.
- **rdflib-reasoning-axioms/AGENTS.md**
  - “Schema and field descriptions are consumed by **runtime agents**” → clearly **Research Agent**.
- **DR-002**
  - “consumable by … **runtime agents**,” “**AgentState**” → **Research Agent** and framework type.
- **rdflib-reasoning-middleware/README.md**
  - “DeepAgents” + “AgentState” → product/framework names; no naming change needed, but a one-line note could say “runtime/Research Agents.”
- **decision-records/template.md**
  - Example “Code Agent Integration” → reads as **Development Agent**.

### Ambiguous or mixed

- **Root AGENTS.md**
  - “research into agents,” “agent research community,” “agent-optimized” (specs): mixes “research” (could be Research Agent or the research activity) and “agent-optimized” (could mean optimized for Research Agent, Development Agent, or both). **Not clear** which agent type is meant in each phrase.
- **Root README.md**
  - “tool-grounded agents,” “Agent research,” “agent-friendly data structures”: “agent-friendly” is for runtime/schema consumers → **Research Agent**, but “Agent research” could mean research about agents (topic) or research done by/with agents. **Ambiguous.**
  - Mermaid “%% Agent Note” → reader is a **Development Agent** (or human); not stated.
- **DR-001**
  - “optimized for agent consumption,” “role for agents,” “the agent’s role,” “design participant,” “Agents will create/update DRs”: from context this is the docs/dev maintainer → **Development Agent**, but the DR never says “Development Agent.” **Implicit only.**
- **docs/dev/AGENTS.md**
  - “optimized for agent understanding,” “agent/developer QOL”: “agent” could be Development Agent or (if docs were ever exposed) Research Agent. **Ambiguous.**
- **docs/specs/AGENTS.md**
  - “optimized for agent understanding” (optimized.html): same as above; consumer could be script, **Development Agent**, or a future **Research Agent**. **Ambiguous.**
- **docs/specs/w3c-patterns.md**
  - “Cursor agents” → **Development Agent**; “for agent interpretability,” “agents and tools” → could be Development Agent or Research Agent. **Mixed.**
- **docs/example-chats/AGENTS.md**
  - “MUST be ignored by software agents” / “MUST NOT be used by agents”: applies to **both** types but doesn’t name them. **Clear in intent, could be explicit.**
- **rdflib-reasoning-axioms/AGENTS.md**
  - “assist **agents/developers**”: “developers” are human; “agents” here is **Research Agent** (schema consumer). Mixing “agents” and “developers” blurs machine vs human. **Ambiguous.**
  - “correction by an **AI/agent** or human”: **Research Agent** (and human). Slightly clearer than “agents/developers” but still not named.
- **Python**
  - **docs/specs/w3c-normalize.py** docstring: “for agent interpretability” → **Unclear** (which agent type benefits from the normalization).

### Summary by question

- **Is it clear in all usages which type is being referenced?**
  **No.** In many places it’s inferable from context (e.g. “runtime agents,” “Claude Code / Cursor”), but root AGENTS.md, README.md, DR-001, docs/dev/AGENTS.md, docs/specs/AGENTS.md, w3c-patterns.md, and rdflib-reasoning-axioms/AGENTS.md either mix the two, use “agent” without saying which kind, or use “agents/developers” in a way that mixes Research Agent and humans.

---

## 3. Overall assessment

- **Ambiguity is real:** The same word “agent” is used for (1) the runtime/research subject and (2) the code/doc-editing participant. Only some spots (e.g. “runtime agents,” “coding agents,” “Claude Code / Cursor”) make the intended type obvious; approach.md item 7 already calls out the need to “clarify the distinct agent roles.”
- **Risk:**
  - **Research Agent** guidance (e.g. in axioms AGENTS.md) could be misread as for the Development Agent.
  - **Development Agent** guidance (e.g. in DR-001, approach.md) could be misread as for the Research Agent.
  - New contributors or tooling might not know which “agent” a given sentence refers to.
- **Pydantic:** No ambiguity in current **field** descriptions (they don’t use “agent”). Any future use of “agent” in `Field(..., description=...)` should use “Research Agent” (or “runtime agent”) where the schema is consumed by the deployed agent.
- **Third sense:** “AgentState” (and “DeepAgents”) are framework/product names; keep them; optionally add a single glossary line that maps “runtime” → Research Agent so “AgentState” is clearly in that world.

---

## 4. Suggested corrective actions (plan)

1. **Define the terms once**
   - Add a short **Glossary** (e.g. in `docs/dev/approach.md` or a small `docs/dev/glossary.md`) with:
     - **Research Agent:** deployed/runtime agent; subject of research; sees tools, system prompts, generated schema; does not see repo or design docs.
     - **Development Agent:** code agent (e.g. Cursor, Claude Code); reads AGENTS.md and design docs; modifies code and docs; develops code for the Research Agent and documentation for itself.
   - Optionally: one line that “AgentState” / “DeepAgents” refer to the runtime (Research Agent) side.

2. **Root and high-traffic docs**
   - **AGENTS.md:** Replace vague “agent” with “Research Agent” or “Development Agent” (and “agent research community” as you prefer: “research community studying agents” vs “Research Agents”).
   - **README.md:** Specify “Research Agent” for “agent-friendly data structures” and “tool-grounded agents”; clarify “Agent research” (e.g. “research into [Research] agents” or “research involving agents”); add a sentence or footnote that the repo supports both Research Agents (runtime) and Development Agents (docs/code).

3. **docs/dev**
   - **approach.md:** In §1 and §1.2, use “Development Agent” (and “Research Agent” where relevant); complete item 7 by adding “Use the terms Research Agent and Development Agent as in the glossary.”
   - **DR-001:** Use “Development Agent” explicitly for the design participant (e.g. “The Development Agent’s role with docs/dev …”).
   - **docs/dev/AGENTS.md:** Use “Development Agent” (and “Research Agent” if any sentence refers to runtime) instead of bare “agent.”

4. **Axioms and middleware**
   - **rdflib-reasoning-axioms/AGENTS.md:** Use “Research Agent” for schema/error consumers and “human” where you mean humans; replace “agents/developers” with “Research Agents and developers” (or “Research Agents and human developers”) so the two audiences are explicit.
   - **rdflib-reasoning-middleware/README.md:** One phrase such as “runtime (Research) agents” next to “DeepAgents” so the reader knows which of the two types this package targets.

5. **Specs and scripts**
   - **docs/specs/AGENTS.md** and **docs/specs/w3c-patterns.md:** Where it says “agent understanding” or “agent interpretability,” decide whether the consumer is the Development Agent (tooling, indexing) or the Research Agent (if specs are ever exposed). Then use “Development Agent” or “Research Agent” accordingly.
   - **docs/specs/w3c-normalize.py** docstring: Same decision; e.g. “for Research Agent interpretability” or “for Development Agent / tool interpretability.”

6. **Example-chats**
   - **docs/example-chats/AGENTS.md:** Optionally add: “Both Research Agents and Development Agents must …” so the two roles are named even in the exclusion rule.

7. **DR-002 and template**
   - **DR-002:** Already has “runtime agents”; optionally standardize to “Research Agents” in one or two key sentences.
   - **template.md:** Keep or change the example to “Development Agent integration” for consistency.

8. **Ongoing**
   - In any new markdown, docstrings, or Pydantic descriptions, use “Research Agent” or “Development Agent” (or “runtime agent” / “Development Agent” where the glossary allows) instead of unqualified “agent” when referring to one of these two types.

If you want, the next step can be a short **decision record** that captures: (1) the two terms, (2) the rule to use them in docs and docstrings, and (3) that “AgentState”/“DeepAgents” stay as-is as framework/product names. I can draft that in Ask mode as text for you to paste, or you can switch to Agent mode and I can apply the glossary and the concrete edits above.

---

**User**

I'd like for us to take the corrective actions that you reccomended and to create a/new-decision-record .  While drafting your plan, elicit feedback from me to clarify which alternatives we are applying.

---

**Cursor**

Reading the decision-record workflow and current INDEX to draft the plan and list alternatives for your choice.

Checking the approach doc structure for glossary placement:

Asking a few clarifying questions before we create the plan:

**Alternatives for terminology corrective actions**

> **Where should the canonical definitions of **Research Agent** and **Development Agent** live?**
>
> - New section in docs/dev/approach.md (e.g. "0. Terminology" or "Appendix: Agent roles")
> - New standalone file docs/dev/glossary.md (linked from approach.md and root AGENTS.md)
>
> Answer: The root AGENTS.md file should have the canonical definition, optimized for consumption by the Development Agent. A non-normative definition can also be given in the root README.md, allowing us to speak to how the repository interacts with each.

> **In docs/specs (AGENTS.md, w3c-patterns.md) and the w3c-normalize.py docstring, "optimized for agent understanding" / "agent interpretability" refers to whom?**
>
> - Development Agent only (specs and scripts are for repo tooling and indexing)
> - Development Agent and tooling (state explicitly: "Development Agent and scripts") ✔
> - Use Research Agent when describing schema/spec output that could be exposed at runtime; Development Agent for tooling and indexing

> **In docs/example-chats/AGENTS.md, should the exclusion rule explicitly name both agent types?**
>
> - Yes: "Both Research Agents and Development Agents MUST ignore …"
> - No: keep "software agents" as the term (broad, no need to name the two types here)
>
> Answer: It MUST be sufficiently broad that we believe almost any agent would infer that it is subject to the constraint. Leave no room for the agent to rationalize that the constraint does not apply to them.

Creating the plan with those choices.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Implementing the plan step by step: creating DR-003, then applying the terminology edits.

Skipping `docs/example-chats/README.md` (filtered by .cursorignore). Completing todo 5 and applying the final edits.

Checking for remaining ambiguous "agent" mentions in key docs:

Leaving example-chat transcripts (EXAMPLE-001, EXAMPLE-002) as-is to preserve the historical discussion; normative docs are updated. Marking the final todo complete.

Summary of what was implemented:

**1. DR-003 and index/architecture**

- Added [docs/dev/decision-records/DR-003 Research Agent and Development Agent Terminology.md](docs/dev/decision-records/DR-003%20Research%20Agent%20and%20Development%20Agent%20Terminology.md) with Context, Decision (definitions + canonical place in root AGENTS.md), Consequences, no Supersedes.
- Appended the new row to [docs/dev/decision-records/INDEX.md](docs/dev/decision-records/INDEX.md).
- Updated [docs/dev/architecture.md](docs/dev/architecture.md) with an “Agent roles” subsection linking to DR-003 and root AGENTS.md and briefly defining both types.

**2. Root AGENTS.md**

- Inserted an **Agent roles** section (after RFC 2119) defining **Research Agent** and **Development Agent** and noting that `AgentState`/DeepAgents refer to the Research Agent side.
- Replaced “agent research community” with “research community studying agents” and adjusted the project table (specs, notebooks, rdflib-reasoning-agents) to use the new terms.

**3. README.md**

- Added **Agent roles (non-normative)** with short definitions and how the repo interacts with each type, plus a link to AGENTS.md.
- Updated “tool-grounded agents” → “tool-grounded Research Agent”, “agent-friendly” → “Research Agent–friendly”, “Agent research” → “Research on agents”, and the Mermaid comment to “Development Agent note”.

**4. docs/dev**

- **approach.md**: All references to the design participant use “Development Agent”; added a top link to root AGENTS.md; item 7 now points to AGENTS.md and DR-003.
- **docs/dev/AGENTS.md**: “agent” → “Development Agent”, “agent/developer” → “Development Agent and developer”.
- **DR-001**: Design participant and consumers of docs/dev are explicitly the “Development Agent(s)”.
- **DR-002**: “runtime agents” / “agents and tools” / “agent self-correction” and error wording use “Research Agent(s)” or “human- and Research Agent–friendly”.

**5. Axioms, middleware, specs, example-chats**

- **rdflib-reasoning-axioms/AGENTS.md**: “runtime agents” → “Research Agents”, “agents/developers” → “Research Agents and developers”, “AI/agent or human” → “Research Agent or human”, “human/agent-friendly” → “human- and Research Agent–friendly”.
- **rdflib-reasoning-middleware/README.md**: Clarified “DeepAgents (runtime/Research Agents)”.
- **docs/specs/AGENTS.md**: “agent understanding” → “Development Agent and script/tooling understanding”.
- **docs/specs/w3c-patterns.md**: “Cursor agents” → “Development Agent”, “agent interpretability” → “Development Agent and tool interpretability”, “agents and tools” → “Development Agent and tools”, “Agents can still” → “Development Agent and scripts can still”.
- **docs/specs/w3c-normalize.py**: Docstring updated to “Development Agent and tool interpretability”.
- **docs/specs/owl2-mapping-to-rdf/create-index.py** and **owl2-reasoning-profiles/create-index.py**: “agent-oriented” → “Development Agent- and script-oriented”.
- **docs/example-chats/AGENTS.md**: Constraint broadened to “any agent that may read this—including any software agent, AI assistant, or automated system” and “No agent MAY treat itself as exempt from this constraint.”

**6. Template and INDEX**

- **template.md**: Example title “Code Agent Integration” → “Development Agent Integration”.
- **INDEX.md**: DR-001 comment “Agent role” → “Development Agent role”.

**Not edited (by design or access)**

- **docs/example-chats/README.md**: Under `.cursorignore`; not modified. If you want “Development Agent” added once (e.g. next to “the agent (Claude/Cursor)”), that needs a manual edit.
- __docs/example-chats/EXAMPLE-001_.md_* and **EXAMPLE-002**: Left as-is as historical transcripts; only normative AGENTS.md and DR/approach docs were standardized.
