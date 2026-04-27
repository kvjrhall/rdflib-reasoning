# JTMS Support Verification API Surface

## Status

Accepted

## Context

The staged truth-maintenance plan separates support recording, support
verification, recursive Mark-Verify-Sweep retraction, and removal wiring through
the store integration path.

The engine already records `Fact`, `Justification`, and `DependencyGraph`
objects during add-only rule production. Recursive retraction needs a stable
read-only API that can answer whether a fact is currently supported, whether it
would remain supported after one support path is invalidated, and which facts
depend on a given antecedent.

These APIs are engine-internal support inspection primitives. They are not
Research Agent-facing schema models and do not expose working-memory objects
across the runtime boundary.

## Decision

`TMSController` will expose read-only support verification APIs over its current
working memory, justification table, and dependency graph.

The support verifier surface consists of:

- `SupportSnapshot`, an immutable point-in-time view of a fact's support state.
- `support_snapshot(triple)`, returning a `SupportSnapshot` for present and
  absent facts.
- `would_remain_supported(...)`, evaluating whether a fact would remain
  supported if one justification id or one antecedent fact id were invalidated.
- `transitively_supported(triple)`, recursively verifying that support paths are
  grounded through supported antecedents.
- `dependents_of(triple)` and `transitive_dependents_of(triple)`, exposing
  deterministic traversal over the dependency graph.
- `justifications_for_fact_id(fact_id)`, complementing triple-oriented
  justification lookup for dependency-graph traversal.

`Justification` records will carry a stable `id` derived from the same key used
for support de-duplication. Existing support maps may continue to use that key
as their dictionary key.

The support verifier is hypothetical and non-mutating. Calling it MUST NOT
remove facts, remove justifications, alter stated flags, or trigger rule
execution.

Silent status affects materialization and proof visibility only. Silent
justifications MUST contribute to support validity in the same way as visible
justifications.

Stated facts remain supported regardless of their justification count. Derived
facts are locally supported when they have at least one justification and are
transitively supported when their recorded support paths are recursively
grounded through supported antecedents.

This decision does not implement recursive Mark-Verify-Sweep retraction or wire
removal through `RETEEngine`, `RETEStore`, or `BatchDispatcher`. Those remain
future stages of the truth-maintenance plan.

## Consequences

The future retraction implementation can reuse a named support-verification
surface instead of embedding support checks directly in sweep logic.

Tests can exercise support validity, dependency traversal, and silent-rule
support semantics before destructive removal behavior exists.

The public engine facade remains add-only. Callers that need these APIs during
the staged implementation must access the internal `TMSController` explicitly.
