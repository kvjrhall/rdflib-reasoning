# Approaching This Problem

The two agent types used in this repository are defined in the root [AGENTS.md](../../AGENTS.md): **Research Agent** (runtime, subject of research) and **Development Agent** (code agent that reads docs and develops for the Research Agent).

## 1. Development Agent as Design Participant

### 1.1. Policy Affordances for the Development Agent

We want the Development Agent to clearly understand where and how it can help.
To this end, we use [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt) keywords liberally in [`AGENTS.md`](https://agents.md/) files.
In fact, the first thing greeting the Development Agent [in the root `AGENTS.md`](../../AGENTS.md) file is the familiar RFC 2119 text:

> The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED",  "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

Next we take advantage of how [cursor uses `AGENTS.md`](https://cursor.com/docs/rules#agentsmd), and how Development Agents (e.g. Claude Code) may interpret their contents.
We use multiple `AGENTS.md` files to give guidance for their various subdirectory trees.
For Cursor, it is injected into the Development Agent's context.
Other Development Agents (e.g., Claude Code) can intelligently use these documents and infer their utility from their contents/location.

In terms of design participation, the Development Agent has clear requirements for creating and maintaining development documentation.
When asked to be creative, the Development Agent knows how to play by the rules.

### 1.2. Optimizations for the Development Agent

Development documentation must follow conventions for a project.
Decent LLMs know this, so a Development Agent will typically avoid writing documentation until it has identified the convention from existing documents.
Investigating the existing documents takes time, multiple tool invocations, and most critically, _context_;
however, this risks evicting or compressing the actual subject that we want to produce content with.
Instead, a terse `AGENTS.md` file [like the one for decision records](./decision-records/AGENTS.md) gives the Development Agent dense guidance whenever it interacts with decision records.

You may be wondering about [`INDEX.md`](./decision-records/INDEX.md) and its purpose.
Unlike `AGENTS.md` it is not automatically injected into the context.
Instead, it is a reference that the Development Agent may elect to use based on its task.
`INDEX.md` files are expected to grow without bounds or to have an indefinite size,
which means that the Development Agent may be best served by searching through the file with tools like `grep` or editing them with tools like `sed`.
An `AGENTS.md` file tells the Development Agent that it's there, and what it's there for, but the Development Agent elects to use it intelligently.

## Appendix 1: Step-by Step Methodology for Development Agent Design Participation

What did I explicitly do to set all of this up?

1. Configured monorepo project layout - review of layout and configuration performed by Claude
2. Created documentation guidance for the Development Agent and core `AGENTS.md`
3. Identified key related W3C specifications & create a script to cache them locally
4. Create a script to optimize W3C specifications: maintained by the Development Agent; iterated by giving the Development Agent critique and feedback on the output content.
5. Prototype some `rdflib-reasoning-axioms` data classes and create example-chat transcript [EXAMPLE-001 pydantic-axiom-classes.md](../example-chats/EXAMPLE-001%20pydantic-axiom-classes.md)
6. Iterate on restrictions to prevent Development Agents (i.e., Claude Code / Cursor) from using `example-chats` as content ([EXAMPLE-002 Exclude Example Chats.md](../example-chats/EXAMPLE-002%20Exclude%20example%20chats.md))
7. Clarify the distinct agent roles: use **Research Agent** and **Development Agent** as defined in the root [AGENTS.md](../../AGENTS.md) (see [DR-003](decision-records/DR-003%20Research%20Agent%20and%20Development%20Agent%20Terminology.md)).
8. Performed another pass at ensuring maintenance of `architecture.md` / decision records remain consistent. Humans may review transcript [EXAMPLE-004 Architecture Document](../example-chats/EXAMPLE-004%20Architecture%20Document.md) for details of the process.
