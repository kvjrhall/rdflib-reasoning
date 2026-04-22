# Bootstrap-Phase Effective Visibility and Derivation Metadata

## Status

Accepted

## Context

[DR-021 Silent Rules and Bootstrap Axiom Execution](DR-021%20Silent%20Rules%20and%20Bootstrap%20Axiom%20Execution.md)
established immutable rule-level `silent` semantics and once-per-context
bootstrap execution before warmup.

Implementation of that decision exposed an additional case: a silent bootstrap
axiom can stimulate a non-silent rule during bootstrap and produce background
closure that is useful inside the engine but undesirable to materialize into the
backing graph on empty-graph startup.

Treating bootstrap suppression by mutating or overloading `Rule.silent` would
blur two separate concerns:

- the rule's default visibility policy during normal operation; and
- the effective visibility of one specific rule firing during bootstrap.

The engine's derivation records and proof reconstruction also need a stable way
to preserve that distinction so callers can inspect either the effective policy
for a firing or the originating rule's default policy.

## Decision

- `Rule.silent` MUST remain an immutable rule-definition property and MUST
  define the default visibility policy for firings of that rule during normal
  operation.
- `DerivationRecord.silent` MUST represent the effective visibility policy of
  the recorded rule firing for materialization and explanation purposes.
- `DerivationRecord.bootstrap` MUST indicate whether the recorded rule firing
  occurred during the bootstrap phase before warmup over existing graph content.
- Bootstrap rules MUST still execute once per engine-context initialization
  before warmup over existing graph content, preserving the ordering introduced
  by DR-021.
- Triples produced solely during bootstrap and its bootstrap-only closure MUST
  seed engine state and MAY appear in engine-native derivation logs, but MUST
  NOT be materialized back into the backing graph/store unless later
  source-graph input independently causes a visible non-silent derivation.
- During bootstrap, derivation records for bootstrap-phase firings MUST set
  `bootstrap=True`.
- During bootstrap, derivation records for bootstrap-phase firings MUST record
  `silent=True` as the effective visibility state, even when the originating
  rule has `Rule.silent=False`.
- User-facing proof reconstruction MUST continue to exclude derivation records
  whose effective `silent` value is true.
- Callers that need rule-definition policy rather than effective firing policy
  SHOULD resolve the recorded `rule_id` back to the rule definition and inspect
  `Rule.silent`.

## Consequences

- The design preserves the original meaning of `Rule.silent` as a rule-level
  policy instead of repurposing it as a phase-specific override.
- Derivation logs gain enough metadata to distinguish bootstrap-phase
  suppression from normal-operation silent rules.
- Bootstrap can continue to seed useful internal closure without polluting the
  backing graph with background vocabulary triples.
- Proof reconstruction remains driven by effective visibility policy rather
  than by inference about execution phase.
- Documentation and architecture can describe bootstrap suppression without
  modifying previously accepted decision records in place.

## Supersedes

[DR-021 Silent Rules and Bootstrap Axiom Execution](DR-021%20Silent%20Rules%20and%20Bootstrap%20Axiom%20Execution.md)
