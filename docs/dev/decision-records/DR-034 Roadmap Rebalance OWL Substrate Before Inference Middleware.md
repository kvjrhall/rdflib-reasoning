# Roadmap Rebalance OWL Substrate Before Inference Middleware

## Status

Accepted

## Context

[DR-028 Roadmap Rebaseline Toward OWL System Integration](DR-028%20Roadmap%20Rebaseline%20Toward%20OWL%20System%20Integration.md)
established the pre-`1.0.0` OWL system integration story and sequenced the next
releases as inference middleware (`0.5.0`), structural traversal (`0.6.0`), then
complete OWL 2 RL (`0.7.0`).

Implementation after the released deductive RDFLib substrate (`0.4.0`) changed
that dependency picture:

- Complete OWL 2 RL materialization and contradiction diagnostics landed as an
  engine substrate before Research Agent-facing inference middleware existed.
- The RL-relevant OWL 2 RDF mapping baseline and strict `axiomatize` graph
  lifting landed in the axioms package, so greenfield "structural traversal"
  is no longer the correct description of the next structural milestone.
- Remaining structural work is residual: inferred-content lifting, deterministic
  text representation, and a residue policy for triples that strict V1
  `axiomatize` currently rejects with `UnsupportedGraphError`.
- Ontology headers, `owl:imports`, and the annotation axiom family are not
  required for the RL-oriented substrate; they fit graph import and provenance
  better than the OWL 2 RL / mapping band.
- Reasoner-backed `DatasetRuntime` configuration is a foundation for later
  middleware composition, not a substitute for capability-gated inference
  middleware.

The overall OWL-system-integration rebaseline remains correct. The post-`0.4.0`
ordering and residual scope need to match what the codebase and dependencies
now require.

## Decision

We supersede DR-028's release sequencing while preserving its OWL system
integration rebaseline, post-`1.0.0` deferrals, and the non-authoritative role
of prospective use cases (also captured in
[DR-029](DR-029%20Prospective%20Use%20Cases%20as%20Non-Authoritative%20Planning%20Input.md)).

The intended pre-`1.0.0` release sequence is:

1. `0.4.0`: Deductive RDFLib dataset behavior (released).
   Complete the reusable engine/store substrate: `RETEStore`, complete RDFS
   materialization, JTMS support bookkeeping, recursive retraction, proof
   reconstruction and rendering, and contradiction diagnostics.
2. `0.5.0`: OWL 2 RL inference rules and structural axioms.
   Complete the repository's forward-chaining OWL 2 RL materialization profile
   and contradiction diagnostics, and the RL-relevant OWL 2 RDF mapping /
   `axiomatize` baseline. Ontology headers, `owl:imports`, and annotation
   axioms are out of scope for this release.
3. `0.6.0`: Inferred-content traversal and text representation.
   Complete residual structural work around already-implemented `axiomatize`:
   inferred-content checks, deterministic prose/text representation, OWL 2 RL
   output compatibility, and a drop-and-warn or skip residue policy for
   non-consumed triples. Malformed recognized patterns remain hard failures.
   This is not a greenfield traversal release.
4. `0.7.0`: Inference middleware.
   Expose the deductive substrate to Research Agents through explicit
   middleware composition, typed tool surfaces, explanations, and diagnostics.
   Reasoner-backed `DatasetRuntime` is a prerequisite foundation, not the
   middleware capability boundary itself.
5. `0.8.0`: OWL system integration baseline.
   Demonstrate that asserted and inferred OWL structures can flow through
   inference, traversal, proof/explanation, rendering, evaluation, and stable
   text representation.
6. `0.9.0`: Graph import and provenance baseline.
   Add controlled graph import and provenance infrastructure without committing
   to remote provider-specific retrieval. Include ontology header /
   `owl:imports` handling and annotation axiom coverage deferred from the
   `0.5.0` RL-oriented structural baseline.
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

`docs/dev/roadmap.md` remains the authoritative delivery-scope document for
this sequence. OWL 2 RDF mapping and OWL 2 RL inference MUST remain adjacent in
planning so inferred OWL-level facts can be traversed, rendered, explained, and
exchanged by the structural layer.

## Consequences

- Symbolic OWL 2 RL and structural-axiom substrate work precedes Research
  Agent-facing inference middleware, matching landed implementation and
  reducing middleware scope risk.
- `0.6.0` is framed as residual inferred-content traversal and text
  representation rather than as inventing graph-to-structure lifting from
  scratch.
- Ontology-document metadata (headers, imports, annotations) moves with graph
  import rather than blocking the RL substrate band.
- DR-028 remains historical rationale for the OWL-system-integration
  rebaseline, but it is no longer the authoritative sequencing decision.
- Architecture documentation MUST describe `axiomatize` as the implemented
  traversal baseline and record the intended residue policy for unsupported
  leftovers.

## Supersedes

- [DR-028 Roadmap Rebaseline Toward OWL System Integration](DR-028%20Roadmap%20Rebaseline%20Toward%20OWL%20System%20Integration.md)
