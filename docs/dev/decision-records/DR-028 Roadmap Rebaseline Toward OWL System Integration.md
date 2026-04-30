# Roadmap Rebaseline Toward OWL System Integration

## Status

Accepted

## Context

The repository roadmap originally treated retrieval and experiment expansion as
the next major post-vocabulary milestone, with advanced engine behavior,
proof-evaluation infrastructure, and citation work following as separate later
releases.

Subsequent implementation and planning changed the dependency picture:

- The deductive RDFLib substrate has become valuable as a standalone package
  capability for Python users independently of Research Agent middleware.
- Research Agent-facing inference should be exposed through explicit middleware
  after the RDFLib substrate is stable, rather than being conflated with store
  and engine behavior.
- Prospective use cases such as agent knowledge exploration, graph embeddings,
  knowledge exchange, deductive memory, and proof authoring depend on a
  structural traversal and representation layer that can lift RDF graph content
  into `StructuralElement` and `GraphBacked` objects.
- OWL 2 RDF mapping and OWL 2 RL inference need to remain adjacent in planning
  so inferred OWL-level facts can be traversed, rendered, explained, and
  exchanged by the structural layer.
- Remote retrieval, graph embeddings, learned inference layers, backward
  chaining, LangGraph skill packaging, and subagent packaging are important
  future tracks, but they are enhancements or adoption experiments once the core
  system works end-to-end.

This means the roadmap needs to prioritize the coherent OWL system story before
provider-specific retrieval or experimental packaging work.

## Decision

We rebaseline the pre-`1.0.0` roadmap around core OWL system integration.

The intended release sequence is:

1. `0.4.0`: Deductive RDFLib dataset behavior.
   Complete the reusable engine/store substrate: `RETEStore`, complete RDFS
   materialization, JTMS support bookkeeping, recursive retraction, proof
   reconstruction and rendering, and contradiction diagnostics.
2. `0.5.0`: Inference middleware.
   Expose the deductive substrate to Research Agents through explicit
   middleware composition, typed tool surfaces, explanations, and diagnostics.
3. `0.6.0`: OWL structural traversal and representation baseline.
   Lift supported RDF graph content into structural objects, provide stable
   ordering, and render deterministic prose/text over asserted and inferred
   graph content.
4. `0.7.0`: Complete OWL 2 RL materialization profile.
   Implement complete OWL 2 RL materialization coverage for the repository's
   forward-chaining profile, complete contradiction diagnostics, and verify
   compatibility with structural traversal.
5. `0.8.0`: OWL system integration baseline.
   Demonstrate that asserted and inferred OWL structures can flow through
   inference, traversal, proof/explanation, rendering, evaluation, and stable
   text representation.
6. `0.9.0`: Graph import and provenance baseline.
   Add controlled graph import and provenance infrastructure without committing
   to remote provider-specific retrieval.
7. `0.10.0`: Knowledge exchange and axiom-authoring tools.
   Allow Research Agents and downstream systems to author, validate, exchange,
   and serialize structured knowledge through RDF, structural objects, prose,
   proof payloads, and schema-driven outputs.
8. `1.0.0`: Stable core infrastructure release.
   Mark the point where the core system works end-to-end and is ready for
   stable public documentation, citation metadata, and release hardening.

Remote service retrieval, LangGraph skill packaging, subagent packaging, graph
embeddings, Graph Inference Layers, learned inference layers, backward chaining,
and hybrid query-time inference remain post-`1.0.0` enhancements or
experimental adoption tracks unless a concrete experiment pulls one forward.

`docs/dev/prospective-use-cases.md` is formalized as non-authoritative planning
input. It may motivate roadmap sequencing and architecture additions, but it
does not override `architecture.md`, `roadmap.md`, decision records, or source
code.

## Consequences

The roadmap now tells a staged core-infrastructure story:

- RDFLib-level deduction works first.
- Research Agents can then use deduction through middleware.
- RDF graphs can then be lifted into OWL structural representations.
- Complete OWL 2 RL inference can then produce structurally meaningful outputs.
- The OWL-facing pieces can then be demonstrated as one integrated system.
- Graph import, provenance, and knowledge exchange build on that core rather
  than preceding it.

This defers provider-specific retrieval and packaging experiments, but it
reduces integration risk by ensuring that retrieval, skills, subagents, graph
embeddings, and learned inference layers build on stable graph, proof,
provenance, and structural representation contracts.

The rebaseline also creates a clearer `1.0.0` boundary: `1.0.0` means the core
system is coherent and usable end-to-end, not that every long-horizon research
or deployment enhancement has been implemented.

## Supersedes

None.
