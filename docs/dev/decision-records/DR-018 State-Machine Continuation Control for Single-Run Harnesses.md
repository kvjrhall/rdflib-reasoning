# State-Machine Continuation Control for Single-Run Harnesses

## Status

Superseded by [DR-020 Middleware Stack Layering and Hook-Role Boundaries](DR-020%20Middleware%20Stack%20Layering%20and%20Hook-Role%20Boundaries.md)

## Context

[DR-016 Continuation Guard Middleware for Single-Run Execution
Discipline](DR-016%20Continuation%20Guard%20Middleware%20for%20Single-Run%20Execution%20Discipline.md)
separated continuation control from model-specific prompt middleware and
established `ContinuationGuardMiddleware` as an optional orchestration-control
layer for single-run harnesses.

Subsequent notebook and demo runs exposed a stronger requirement: run stability
MUST NOT depend on the Research Agent choosing the "right" continuation branch.
In particular, repeated unchanged `serialize_dataset` retries can lead to a
provider-incompatible assistant-final continuation pattern even when the
Research Agent has already been told to finish. A best-effort reminder-only
guard is therefore insufficient.

The repository needs a principled continuation-control design that:

- gives single-run harnesses deterministic stopping behavior once a valid final
  Turtle answer is present
- uses provider-safe continuation when more model work is still required
- provides a stable foundation for future continuation criteria without adding
  ad hoc prompt exceptions

## Decision

Single-run continuation control will be modeled as an explicit private runtime
state machine.

- Continuation control uses three conceptual modes:
  - `normal`: ordinary single-run behavior
  - `finalize_only`: the next acceptable step is finalization or a specific
    corrective dataset change
  - `stop_now`: the run should terminate deterministically
- This continuation mode is middleware-private state. It MUST NOT be exposed to
  the Research Agent as a tool argument, tool result field, or ordinary state
  payload.
- `ContinuationGuardMiddleware` owns the continuation-control state machine and
  MUST use provider-safe continuation prompts (`HumanMessage`-based prompting)
  only when that role transition is valid for the current transcript shape,
  rather than relying on implicit continuation from an assistant-final
  transcript. In particular, tool-result turns SHOULD continue through the
  ordinary `tool -> assistant` path rather than forcing a `tool -> user`
  transition.
- `ContinuationGuardMiddleware` MUST deterministically end the run once the
  latest assistant output contains a valid completed Turtle answer.
- The first transition into `finalize_only` is driven by repeated unchanged
  `serialize_dataset` rejection. `DatasetMiddleware` emits that transition as an
  explicit state update alongside the rejecting `ToolMessage`.
- If a subsequent dataset mutation actually changes the dataset, continuation
  control returns to `normal`.

This design keeps provider-specific prompt adaptation middleware separate from
continuation control while making continuation safety a runtime control policy
rather than a best-effort prompt nudge.

## Consequences

Benefits:

- single-run notebook and demo harnesses become stable even when the Research
  Agent keeps trying to continue
- continuation behavior becomes extensible through explicit states and
  transitions rather than prompt-only special cases
- provider-safe continuation is available without making continuation control
  model-specific

Costs and follow-up considerations:

- continuation control now spans both `ContinuationGuardMiddleware` and the
  dataset/continuation boundary
- tests must cover `Command(update=...)` state transitions in addition to plain
  `ToolMessage` and `HumanMessage` behavior
- future continuation triggers SHOULD be integrated by adding principled state
  transitions, not by introducing isolated prompt exceptions

## Supersedes

- [DR-016 Continuation Guard Middleware for Single-Run Execution
  Discipline](DR-016%20Continuation%20Guard%20Middleware%20for%20Single-Run%20Execution%20Discipline.md)
