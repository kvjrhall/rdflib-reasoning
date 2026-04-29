# Dual-Channel Contradiction Diagnostics and Explanation Contract

## Status

Accepted

## Context

The architecture currently describes contradiction handling primarily as sensitivity
to a triple-shaped signal of the form `?x rdf:type owl:Nothing`.
This is a useful witness pattern, but it is not the full contradiction surface of
OWL 2 RL/RDF rule semantics.

In OWL 2 RL Section 4.3, contradiction is represented by deriving `false` for
multiple rule families, including but not limited to:

- `cls-nothing2` (`T(?x, rdf:type, owl:Nothing) -> false`)
- `eq-diff*` (same-as and different-from conflicts)
- `prp-irp` / `prp-asyp` (irreflexive and asymmetric conflicts)
- `prp-npa*` (negative property assertion conflicts)
- `dt-not-type` (datatype membership conflicts)

At the same time, engine architecture and DR-005 require that logical mutation
remain triple-oriented and centralized in engine-managed triple production.
Predicates, builtins, callbacks, and similar extensibility points are explicitly
non-mutating and MUST NOT form an alternate graph-mutation channel.

The current explanation stack is strongest for triple goals reconstructed from
derivation records. Contradictions need an explanation path that does not require
materializing contradiction triples into logical working memory.

## Decision

- Contradiction handling is defined as a **dual-channel model**:
  1. **Logical entailment channel**: engine-managed RDF triple production and
     retraction remain unchanged and triple-oriented.
  2. **Contradiction diagnostics channel**: contradiction outcomes are captured
     as non-mutating records, queryable through an engine API surface.

- Contradiction detection targets the full currently modeled OWL 2 RL
  contradiction-producing `false` family, rather than only `owl:Nothing`-witness
  cases.

- Contradiction diagnostics records MUST be represented as structured artifacts
  that include, at minimum:
  - context identifier,
  - originating rule identifier,
  - bound variables (when available),
  - matched premise triples that witness the contradiction,
  - stable ordering metadata suitable for deterministic retrieval.

- Contradiction recording is observational and MUST NOT add or retract RDF triples.
  Contradiction records are NOT working-memory facts and do not participate in TMS
  support bookkeeping.

- Initial contradiction queryability is implemented by selectable recorder sinks
  (default **`RaiseOnContradictionRecorder`**; **`InMemoryContradictionRecorder`**
  with optional warnings; **`DropContradictionRecorder`** for warnings without
  retention), plus read-only engine API methods. Materialization into a dedicated
  diagnostics graph is deferred.

- Contradiction explanation SHOULD be reconstructed from contradiction records and
  premise/derivation context, not by requiring contradiction triple materialization.
  `owl:Nothing` witnesses remain a supported contradiction witness shape but are not
  the sole contradiction trigger.

## Consequences

- Contradiction coverage now aligns better with OWL 2 RL `false` semantics while
  preserving the existing non-mutating extensibility boundary from DR-005.
- The system can provide queryable contradiction causes without polluting logical
  closure with synthetic contradiction triples.
- Triple explanation and contradiction explanation are decoupled in a principled
  way: triple proofs remain triple-derived, while contradiction proofs consume
  contradiction diagnostics records plus supporting premises.
- A future diagnostics graph export path remains possible as an additive feature,
  but is not required for initial contradiction explanation support.

## Supersedes

None.
