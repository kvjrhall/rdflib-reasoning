---
name: verify-project-documentation
description: Assess the compliance of Markdown documents against the project's documentation policy, fixing compliance issues if asked to.
---

# Verify Project Documentation

- You (the Development Agent) MUST ascertain if the repository follows the repository documentation policy.
- You SHOULD correct compliance issues UNLESS the user has requested that you not do so.
- You MAY widen your criteria to adhere to modern best practices.
- You SHOULD adjust your criteria if the user has requested that you do so

## 1. General Documentation Policy

The checklist for policy adherence follows:

- [ ] CRITICAL: Documentation passes linting: `make check`
- [ ] CRITICAL: Documentation tone/style/content adheres to modern standards for technical documentation

- [ ] References to `docs/example-chats` MUST NOT exist outside that directory
- [ ] References to an `Agent` MUST use [the agent role controlled vocabulary](../../../AGENTS.md#agent-roles)
- [ ] Docstrings within any distribution source folders (i.e., `src/` or `rdflib-reasoning-*/src`) MUST NOT refer to any local development documents or references.
- [ ] All document cross references (read: markdown links in the repository) MUST be valid and resolvable
- [ ] If a path exists within documentation for the Development Agent, its surface form SHOULD be relative to the repository root (e.g., `rdflib-reasoning-engine/README.md`)
- [ ] All external documentation references (read: hyperlinks outside the repository) MUST be dereferencable (syntactically valid and normally reachable)
- [ ] References to agents MUST NOT place emphasis on any specific model (e.g., Claude, GPT, Grok, etc)
- [ ] References to agentic code environments SHOULD NOT place emphasis on any single tool (e.g., Claude Code, Codex, Cursor, etc)

## 2. Specific File Documentation Policies

Each of the following sections extends the [General Documentation Policy](#1-general-documentation-policy) for a document or set of documents.

### 2.1. Policy for `architecture.md` and `decision-records`

- [ ] [The quality gates for `docs/dev/architecture.md`](../../../docs/dev/AGENTS.md) are given by its local `AGENTS.md`
- [ ] [The quality gates for `docs/dev/decision-records`](../../../docs/dev/decision-records/AGENTS.md) also include their local `AGENTS.md`

### 2.2. Policy for sub-project `rdflib-reasoning-*/README.md` files

- [ ] Feature matrices in the documents are up-to-date and match the current system state
- [ ] Feature matrices are complete with respect to documented roadmapped functionality
- [ ] The project overview is accurate and describes the purpose of the subproject
- [ ] Distinguishing and key system features are briefly described and surface early in the documentation (i.e., not buried in a feature matrix)
- [ ] Installation and setup procedures are clearly documented
- [ ] A short tutorial/onboarding experience is provided in the way of small "Quick Start" examples
- [ ] All code examples / listings / names match the current state of the system

### 2.3. Policy for the root `README.md` file

- [ ] The document accurately communicates the repository's purpose, intended audience, and research focus near the top of the file
- [ ] The document presents the repository structure and major sub-projects in a way that matches the current filesystem and project boundaries
- [ ] The document acts as a reliable entry point for a new Development Agent or contributor by linking to the key orientation documents (e.g., `AGENTS.md`, `docs/dev/architecture.md`, and major sub-project READMEs or directories)
- [ ] Installation and environment guidance is accurate, internally consistent, and aligned with the repository's required development workflow
- [ ] Any claims about capabilities, current scope, or repository status are consistent with the present codebase and sub-project documentation
- [ ] The document provides enough navigational structure that a reviewer can quickly determine where architecture, implementation, specifications, and research artifacts live
- [ ] Examples, commands, and package names shown in the document match the current repository state
- [ ] The document avoids duplicating volatile low-level detail that is better maintained in sub-project documentation, unless the duplication is intentional and kept in sync

### 2.4. Policy for `AGENTS.md` files

- [ ] Each `AGENTS.md` clearly states the scope of the instructions it introduces and does not silently conflict with higher-level `AGENTS.md` files
- [ ] Instructions are written for the Development Agent, unless a distinction between Development Agent and Research Agent is explicitly required
- [ ] References to agents consistently use the repository's controlled vocabulary from the root `AGENTS.md`, with `Development Agent` remaining the default audience unless another role is explicitly assigned
- [ ] The document clearly distinguishes normative instructions from explanatory/background material so that repository policy is easy to follow
- [ ] File- or directory-specific quality gates are concrete, testable, and scoped to the subtree governed by that `AGENTS.md`
- [ ] Cross references to templates, indexes, decision records, architecture documents, or sibling guidance are accurate and resolvable
- [ ] Instructions do not require impossible repository knowledge from a Research Agent or otherwise blur the boundary between runtime-agent behavior and repository-development behavior
- [ ] Local `AGENTS.md` files extend parent instructions additively where possible, and any override or specialization is made explicit enough to avoid ambiguity during validation
- [ ] Reusable terminology, naming, and path conventions in the document match the current repository and adjacent documentation
