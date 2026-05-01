# Project Overview

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

## Agent roles

Two primary agent types are distinguished in this repository's design, and one additional review-only agent role is defined for repository assessment. Documentation and docstrings MUST use these terms when referring to one of them; see [DR-003](docs/dev/decision-records/DR-003%20Research%20Agent%20and%20Development%20Agent%20Terminology.md).

- **Research Agent**: Deployed or runtime agent; subject of research. Sees tools, system prompts, and generated schema (e.g. from middleware/MCP); does NOT see repository, design docs, or AGENTS.md. Framework names such as LangGraph `AgentState` and "DeepAgents" refer to this side.
- **Development Agent**: Code agent (e.g. Cursor, Claude Code). Reads AGENTS.md and design docs; modifies code and documentation; develops code for the Research Agent and documentation for itself. MUST be aware of the distinction between the two types.
- **Critique Agent**: Repository-wide review agent used for technical due diligence, portfolio review, or holistic critique. It MAY inspect any repository content when that inspection is relevant to the review, including content that local `AGENTS.md` files ask Development Agents to ignore. It MUST treat such material as review evidence rather than authoritative implementation guidance.

Most agents interacting with this repository are Development Agents. An agent MUST NOT assume that it is a Critique Agent unless the user, governing prompt, or invoked skill explicitly assigns that role.
Local `AGENTS.md` files SHOULD assume a Development Agent audience unless they explicitly address another role. A local `AGENTS.md` MUST NOT be interpreted to narrow the repository-wide inspection scope of an explicitly designated Critique Agent.

---

This repository MUST support research into agents and their interoperability
with formal logic. It SHOULD support the wider research community studying
agents as the monorepo for the `rdflib-reasoning` Python libraries:

- Development MUST use the `rdflib-reasoning` conda environment.
- All use [src-layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- All use the `rdflib_reasoning` [namespace package](https://packaging.python.org/en/latest/guides/packaging-namespace-packages/) with a shared **PEP 420** implicit namespace at the `rdflib_reasoning` root (no root `__init__.py` in published wheels; subpackages merge at runtime across distributions)

Repository map:

- `docs/`: Reference materials for humans and machines.
- `docs/dev/`: Authoritative architecture, roadmap, decision records, and
  development status.
- `docs/dev/decision-records/`: Rationale and history for architecture and
  planning.
- `docs/specs/`: Cached specifications optimized for Development Agent and
  tooling use.
- `notebooks/`: Research, demonstration, tutorial, and evaluation notebooks.
- `rdflib-reasoning-middleware/`: Research Agent-facing middleware and
  capability gating; see its `AGENTS.md` and
  [README](rdflib-reasoning-middleware/README.md).
- `rdflib-reasoning-axioms/`: Structural RDF/OWL models and graph-backed schema
  contracts; see its `AGENTS.md` for local modeling and schema rules.
- `rdflib-reasoning-engine/`: RDFLib-integrated RETE-based RDFS and OWL 2 RL
  entailment, proof, and contradiction diagnostics; see its `AGENTS.md` for
  engine-specific rules.
- `script-helpers.sh`: Bash helper functions for repository scripts.

## Development Agent Commands

Before first validation in a session, the Development Agent MUST check that
`uv` and `pre-commit` are available in the active environment. If they are not,
the Development Agent SHOULD run validation commands through
`conda run -n rdflib-reasoning make`.

After making significant Python changes, the Development Agent MUST run
`make validate test` and correct any errors.
After making changes to Markdown documents, the Development Agent MUST run
`make check` and correct any markdownlint errors.

- `make` commands may require usage of a conda environment (i.e., `conda run -n rdflib-reasoning make`)
- Use `make test` to run unit tests (should automatically use the virtual environment of `.venv`)
- `make test` outputs coverage details to the console produces artifacts: `.coverage`, `coverage.xml`, `htmlcov/`
- Use `make install-all` when a `.venv` environment does not exist or when dependencies change
- Use `make check` to lint everything **except** type checking
- Use `make validate` to lint everything **including** type checking

## Development Agent use of architecture and roadmap

- The Development Agent SHOULD consult `docs/dev/roadmap.md` before starting substantial feature work, release planning work, or any task where implementation priority or intended scope is unclear.
- The Development Agent MUST treat `docs/dev/architecture.md` as the authoritative intended design and `docs/dev/roadmap.md` as the authoritative release- and priority-oriented scope plan.
- The Development Agent MUST stop and verify that `docs/dev/roadmap.md` remains accurate before concluding substantial Python, middleware, or architecture-affecting work.
- The Development Agent MUST consider reprioritizing tasks and/or changing the intended scope of a release when implementation reveals an under-specified feature, a hidden dependency, a validation failure that changes delivery risk, or a mismatch between `docs/dev/roadmap.md` and `docs/dev/architecture.md`.
