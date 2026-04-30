# Packaging Experiments as Post-Core Adoption Tracks

## Status

Accepted

## Context

The roadmap rebaseline toward OWL system integration separates core semantic
capabilities from later adoption and deployment experiments. During that
rebaseline, LangGraph skill packaging and subagent packaging emerged as useful
possibilities for repeated workflows such as retrieval, axiom authoring, proof
critique, and structural summarization.

Those packaging strategies are not monotonic feature milestones. Adopting them
too early could create premature abstractions, add latency or token overhead,
fragment the runtime surface, or make it harder to evaluate the underlying
semantic capabilities directly. Conversely, rejecting them categorically would
ignore a plausible way to improve ergonomics once workflows become stable.

The repository therefore needs a planning rule that keeps skill and subagent
packaging available for concrete experiments without treating them as required
pre-`1.0.0` infrastructure.

## Decision

LangGraph skill packaging and subagent packaging are post-core adoption tracks,
not guaranteed core milestones.

They MAY be evaluated when a repeated workflow has stable inputs, outputs,
success criteria, and enough usage evidence to measure the packaging decision
itself. Candidate workflows include retrieval, axiom authoring, proof critique,
structural summarization, and other bounded capabilities that can be evaluated
against an unpackaged implementation.

Packaging evaluations MUST remain outcome-driven. They SHOULD compare
reliability, latency, token cost, ergonomics, implementation complexity, and
debuggability against the baseline middleware or library implementation.

The result of a packaging evaluation MAY be adoption, partial adoption,
deferral, or rejection. Any of those outcomes is compatible with the core
semantic architecture.

Skill and subagent packaging SHOULD NOT be treated as required pre-`1.0.0`
infrastructure unless a specific milestone exposes a measurable need that cannot
be satisfied cleanly by the existing middleware, library, or documentation
surfaces.

## Consequences

The pre-`1.0.0` roadmap can focus on deductive RDFLib datasets, inference
middleware, OWL structural traversal, complete OWL 2 RL materialization, OWL
system integration, graph provenance, and knowledge exchange without reserving a
milestone for packaging mechanics.

Packaging remains available when it makes a concrete workflow better, but it
does not become architecture by default. This keeps the system easier to
evaluate while the semantic substrate is still changing.

Future Development Agents should avoid interpreting the absence of a skill or
subagent package as missing core functionality. They should instead ask whether
the underlying capability exists and whether packaging has been justified by a
measured use case.

## Supersedes

None.
