# Examples of Effective Agent Participation

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

This directory is invisible to Cursor, and MUST be ignored by any other software agents.
This directory is a non-normative reference for humans that MUST NOT be used by agents for any purpose.

## 1. Overview

This directory contains select transcripts of chats with Cursor where it was used collaboratively to design / implement code.
It's effectively a portfolio of best practices that attempt to safely use software agents for system design.
In these chats, we demonstrate what it means to establish clear boundaries for agents so that we can afford them creativity without abandoning safety.

## 2. Examples

As a general approach, we treat the agent (Claude/Cursor) as a junior engineer who is extremely good at finding references, rapidly drafting documentation, and following established patterns within a codebase.
We MUST NOT explicitly tell the agent that, because we SHOULD NOT encourage the agent to be too deferential or to doubt itself.
We _want_ the agent to give harsh and honest analysis so that it is a contributing participant in the process.

### 2.1. Establish a Design (Pydantic Axiom Classes)

In [EXAMPLE-001 pydantic-axiom-classes](./EXAMPLE-001%20pydantic-axiom-classes.md) we start off in a repository where I've established the project scopes through `README.md` & `AGENTS.md` files.

I've already drafted some data classes, their class documentation, and their fields' documentation.
Before I push further into the design, I have a few goals:

1. Identify possible oversights
2. Identify any misalignment with design principles or deviation from the proposed design
3. Understand how the agent understands that code given the absence of any relevent existing DRs; this is greenfield for the agent.
4. Learn about my design and its flaws as if pair programming

There are some subtleties in my prompt's questions:

> 1. Are there clear principles that are being established?
> 2. Is this proposal consistent with the rest of the documentation in the repository (development docs and `README.md`'s)?
> 3. Are there significant oversights or ambiguities that we should clarify before this can be converted into a decision record?

Question (2) reminds the agent to consider the other design materials and comment on the core theme.
_A priori_ I believe that it **is** consistent and that there is an established core theme; I want the agent to populate its context _inspired by its goal_ so that the agent is intrinsically focuses on _how_ to use the content.
If there are no inconsistencies to address, then the agent's output for question (2) is meaningless.

Question (1) captures something more subtle: As a greybeard engineer, a _lot_ of experience is implicit in how I do my job.
I don't want to teach it all to an agent.
I'm not currently being paid to write a book on this.
I _do_ however, want the agent to recognize what those principles are and to begin reinforcing them on the documentation side.
If the agent captures good stuff in Question (1)'s answer, then we can translate it into content for the decision record and reinforce those principles bi-directionally.
This helps the agent, any engineers that follow, and helps me to hold myself accountable for adherence to this design.

Finally, Question (3) is where we plan for iteration.
I have _certainly_ missed things, left things ambiguous, or could apply some fixes.
Let's try to catch them, correct them, and generally clean things up.
Once I'm happy with the "shared" understanding between me and the agent, we can tell the agent to draft a decision record.

An essential theme of this whole process is that I am guiding an agent towards safe development.
I am treating iteration on documentation and code as **iteration on its understanding** first-and-foremost.
This is where we circle back to the Junior Engineer analogy.
We are setting the agent onto a task, but that task has two purposes: solve a problem; teach our colleague.

### 2.2. Restrict File Access

[EXAMPLE-002 Exclude example chats](./EXAMPLE-002%20Exclude%20example%20chats.md) is a meta-discussion about the content of this folder.
In it, I ask Cursor to list the content it can see so that I can iterate on `.cursorignore` (note: Claud Code tests pending).
The primary outcome: In this directory an agent can only see [AGENTS.md](./AGENTS.md), and the instructions therein have been clarified from my original wording.

### 2.3. Disambiguation of `Agent`

This repository has a subtle set of behaviors that make it challenging for a Development Agent to assist as a design participant: we have two agents that we create specifications for.
First, we have the **Development Agent** that assists us in maintaining code / documentation (such as Claude Code or Cursor).
Second, we have the agent that is the subject of our research (the **Research Agent**).
If we fail to be clear in our documentation, then we will certainly confuse human and agent developers.

So, let's vet what the development agent currently assumes and use an unambiguous term for each type of agent _everywhere_ that we want to use the word "agent".
We go through this process and make corrections in [EXAMPLE-003 Agent type ambiguity and naming conventions.md](./EXAMPLE-003%20Agent%20type%20ambiguity%20and%20naming%20conventions.md)

### 2.4. Architecture Document

I noticed that `architecture.md` simply cited some decision records.
I don't want the development agent to have to read all decision records to understand the intended system design, as that would waste context and risks the agent operating with a partial understanding.
In [Example-004 Architecture Document](./EXAMPLE-004%20Architecture%20Document.md), I propose the standalone document and vet my rationale.
Interestingly, the agent not only validates the rationale, but identifies several places that we could/should redundantly reinforce the roles of various documents.

Now, one note that is somewhat ironic.
The agent's reccomendations are solid, but it never thinks to check the compliance of `architecture.md` against our new standards.
If I just charged ahead without reviewing the architecture, then the agent would get conflicting definitions:

- "The architecture document is a standalone description of the system as it is intended"
- Reading the document, it contains references to DRs. Should I assume that all relevent content already exists in this document and that these are optional references?
