# Continuation Guard Middleware for Single-Run Execution Discipline

## Status

Superseded by [DR-018 State-Machine Continuation Control for Single-Run Harnesses](DR-018%20State-Machine%20Continuation%20Control%20for%20Single-Run%20Harnesses.md)

## Context

`rdflib-reasoning-middleware` includes model-specific prompt-adaptation
middleware such as `MinistralPromptSuffixMiddleware`. That middleware also
accumulated `after_model` logic for recovering from unfinished recovery
narration after tool failures. As the repository's notebook and demo harnesses
exposed additional failure modes such as plan-only exits, that logic drifted
away from model-specific prompt adaptation and toward a general post-model
execution-discipline role.

That coupling created two problems:

- a model-specific middleware appeared to own repository-wide continuation
  behavior
- the intervention logic was harder to reuse in non-Ministral configurations
  where the same single-run failure modes still apply

The repository also needs a clear architectural distinction between optional
single-run orchestration controls and deliberately multi-round or memory-backed
agent setups. A continuation guard is useful when a Research Agent is expected
to keep acting until completion, but it SHOULD NOT be assumed for every runtime
profile.

## Decision

Continuation and termination discipline will be modeled as a distinct middleware
capability.

- `MinistralPromptSuffixMiddleware` remains model-specific and is responsible
  only for appending the Ministral prompt suffix.
- A new `ContinuationGuardMiddleware` owns post-model continuation controls.

`ContinuationGuardMiddleware` is an optional middleware intended primarily for
single-run, completion-oriented Research Agent harnesses such as notebooks and
demo workflows.

Its responsibilities are:

- detect unfinished recovery narration after recent tool rejections
- detect unfinished planning or continuation-intent responses that stop before
  the next tool call or completed answer
- inject a short `HumanMessage` reminder and continue the run when the latest
  `AIMessage` clearly stopped in an unfinished mode

Continuation guards are optional by design. They SHOULD NOT be implied by
default for multi-round conversational agents using persistent threads or
memory-backed sessions, because those setups may legitimately stop after a plan
or partial conversational turn.

## Consequences

Benefits:

- model-specific prompt middleware stays narrow and easier to reason about
- continuation control becomes reusable across model configurations
- notebook and demo harnesses can opt into a clear single-run execution
  discipline layer
- future continuation safeguards can be added to one dedicated middleware

Costs and follow-up considerations:

- the middleware stack gains another optional orchestration-control component
- tests and docs must distinguish model-specific prompt adaptation from
  continuation discipline
- Development Agents must be explicit about whether a given harness should use
  `ContinuationGuardMiddleware`

## Supersedes

None.

## Superseded By

- [DR-018 State-Machine Continuation Control for Single-Run Harnesses](DR-018%20State-Machine%20Continuation%20Control%20for%20Single-Run%20Harnesses.md)
