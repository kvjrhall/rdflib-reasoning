# Silent Rules and Bootstrap Axiom Execution

## Status

Accepted

## Context

The engine and proof models already carry a `DerivationRecord.silent` flag, but
the intended semantics and execution contract for silent behavior were not yet
fully specified.

At the same time, practical RDFS usage needs two additional behaviors:

- Some rules (including noisy RDFS entailments) should remain logically active
  without materializing all of their outputs into every graph.
- Axiom-like rules with zero preconditions should execute at context startup so
  each context has a predictable inference baseline, including empty graphs.

Without a single decision covering these points, implementation work risks
drift across rule definitions, derivation logs, proof reconstruction, warm-start
ordering, and release scope planning.

## Decision

- The rule model MUST support an immutable `silent` property as part of each
  rule definition.
- `silent` MUST control both:
  - materialization visibility (whether rule conclusions are written back to the
    graph/store), and
  - proof reconstruction visibility (whether those derivations participate in
    reconstructed user-facing proofs such as `DirectProof`).
- If derivation logging is enabled, silent rule applications MUST still be
  recorded in engine-native derivation logs with `DerivationRecord.silent=True`.
- Explanation reconstruction for user-facing proofs MUST exclude derivation
  records marked silent.
- The rule model MUST permit zero-precondition rules (bootstrap rules).
- Bootstrap rules MUST execute once per engine-context initialization and MUST
  execute before warmup over existing graph content.
- Reopening or recreating an engine for a context MAY re-run bootstrap rules as
  part of initialization; this behavior MUST be idempotent with respect to the
  resulting logical state and materialized output policy.
- The configuration surface for axioms SHOULD remain profile-level inclusion or
  exclusion of the axiom ruleset, rather than per-firing toggles.

## Consequences

- The architecture gains a clear distinction between full engine-native
  derivation provenance and filtered user-facing proof reconstruction.
- Silent rules can remain active for completeness and internal support
  bookkeeping while avoiding graph and proof noise in practical deployments.
- Warm-start behavior must include an explicit bootstrap phase before graph
  content warmup, and tests must validate that ordering.
- Rule IR and compilation paths must be updated to support empty bodies while
  preserving fixed-point and idempotence guarantees.
- Roadmap scope must explicitly include this behavior in release `0.3.0`.

## Supersedes

None.
