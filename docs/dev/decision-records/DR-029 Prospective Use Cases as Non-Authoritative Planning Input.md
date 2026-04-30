# Prospective Use Cases as Non-Authoritative Planning Input

## Status

Accepted

## Context

The repository now has a dedicated prospective-use-cases document that captures
long-horizon research ideas such as agent knowledge exploration, graph
embeddings, Graph Inference Layers, knowledge exchange, deductive memory,
backward chaining, proof authoring, and packaging experiments.

Those use cases are important planning evidence. They reveal shared foundations,
ordering dependencies, and integration risks that may affect the roadmap. For
example, they helped clarify that structural traversal and representation are
core infrastructure, that OWL 2 RDF mapping and OWL 2 RL inference should remain
adjacent, and that provenance is cross-cutting rather than retrieval-only.

At the same time, prospective use cases are intentionally broader than committed
implementation scope. Treating every brainstormed use case as authoritative
architecture would make the roadmap unstable and would blur the distinction
between current intended design, planned release scope, and future research
possibilities.

The repository therefore needs an explicit rule for how Development Agents
should use prospective-use-case material.

## Decision

`docs/dev/prospective-use-cases.md` is a formal planning input, not an
authoritative scope or architecture document.

Development Agents MAY cite it when explaining motivation, identifying shared
foundations, detecting ordering dependencies, evaluating whether roadmap items
should be split or deferred, or proposing future architecture additions.

Development Agents MUST NOT treat it as overriding `architecture.md`,
`roadmap.md`, decision records, local `AGENTS.md` files, or source code.
Authoritative intended architecture remains in `architecture.md`; authoritative
release sequencing and scope remain in `roadmap.md`; rationale and history
remain in decision records.

Prospective use cases MAY justify roadmap reprioritization when they reveal a
common substrate or hidden dependency. They SHOULD NOT, by themselves, commit
the repository to implementing a feature before a milestone explicitly adopts
that scope.

## Consequences

The repository can preserve ambitious research ideas without forcing all of
them into the pre-`1.0.0` core roadmap.

Development Agents get a stable way to use brainstorming material: mine it for
dependencies, risks, examples, and future direction, but resolve present design
questions against the authoritative architecture and roadmap.

This keeps long-horizon ideas visible while protecting the current roadmap from
scope creep. It also makes later decision records cleaner because they can cite
the prospective-use-cases document as motivation without pretending that the
document already made the architectural decision.

## Supersedes

None.
