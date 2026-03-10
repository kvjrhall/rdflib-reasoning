# Research Agent and Development Agent Terminology

## Status

Accepted

## Context

When "agent" appears in markdown, docstrings, or field descriptors, it can refer to two mutually exclusive types: (1) a deployed/runtime agent that is the subject of research and sees only tools, system prompts, and generated schema; (2) a code agent (e.g. Cursor, Claude Code) that reads repository documentation, modifies code and docs, and develops for the former. This ambiguity makes it unclear who consumes which documentation and who must follow which rules. We need unambiguous terms and a single place for canonical definitions.

## Decision

- **Research Agent**: A deployed or runtime agent that is the subject of or participant in research. It is implemented in code, sees tools and supplied system prompts, and may see generated schema of data classes exposed through middleware or MCP. It MUST NOT see repository content (design docs, AGENTS.md, decision records, or source). Framework and product names such as LangGraph `AgentState` and "DeepAgents" refer to this runtime (Research Agent) side.

- **Development Agent**: A code agent (e.g. Claude Code, Cursor) that accesses design documentation, module documentation, and repository content; modifies code and documentation; and develops code to support the Research Agent and documentation to support itself. It MUST be aware of the distinction between the two agent types.

- **Canonical definitions** live in the root [AGENTS.md](../../AGENTS.md), optimized for Development Agent consumption. Non-normative definitions and how the repository interacts with each type appear in the root [README.md](../../README.md).

- **Documentation and docstrings** MUST use "Research Agent" or "Development Agent" (or explicit "runtime agent" where this DR allows) when referring to one of these types; unqualified "agent" is avoided for those referents. Framework and product names (e.g. `AgentState`, "DeepAgents") remain unchanged.

## Consequences

- Documentation can be read consistently; readers know which agent type is addressed.
- The Development Agent can rely on root AGENTS.md for canonical definitions.
- Follow-up edits replace ambiguous "agent" across the repository with the chosen terms.
- Future Pydantic field descriptions and docstrings use "Research Agent" (or "runtime agent") when the consumer is the deployed agent.

## Supersedes

None.
