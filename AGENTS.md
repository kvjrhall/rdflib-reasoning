# Project Overview

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED",  "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

Development MUST use the `rdflib-reasoning` conda environment.

This is a monorepo for the `rdflib-reasoning` python libraries:

- All use [src-layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- All use the `rdflibr` [namespace package](https://packaging.python.org/en/latest/guides/packaging-namespace-packages/)

| Project Path | Description |
| ------------ | ----------- |
| `docs/` | Reference materials for humans and machines |
| `docs/dev/` | Design, Architecture, Decisions, and Development Status |
| `docs/dev/decision-records/` | Rationale driving design & architecture |
| `rdflib-reasoning-agents/` | LangChain middleware for agent/graph interaction |
| `rdflib-reasoning-axioms/` | The project for axiomatizing RDF graphs |
| `rdflib-reasoning-engine/` | Sub-project for RETE-based RDFS and OWL 2 RL Entailment |
| `script-helpers.sh` | A set of bash helper functions to use when writing bash scripts |
