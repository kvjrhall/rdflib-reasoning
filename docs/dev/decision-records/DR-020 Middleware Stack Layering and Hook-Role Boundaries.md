# Middleware Stack Layering and Hook-Role Boundaries

## Status

Accepted

## Context

The middleware stack in `rdflib-reasoning-middleware` has grown to include
capability middleware (`DatasetMiddleware`, `RDFVocabularyMiddleware`),
orchestration middleware (`ContinuationGuardMiddleware`), and framework-provided
middleware from Deep Agents and LangChain.

Recent failures showed that stability is most fragile where middleware
responsibilities overlap, especially when transcript-shape repair and reducer
updates are split across incompatible hook boundaries.
In particular:

- message-shape canonicalization performed via reducer updates can conflict with
  `add_messages` semantics (for example stale delete ids)
- continuation and policy concerns can drift into capability middleware when
  stack layering is not explicit
- custom middleware can duplicate framework defaults when boundaries are not
  documented

The repository needs a clear intended architecture that:

- defines one standard middleware layering order
- assigns strict responsibilities to node hooks versus wrap hooks
- treats reducer behavior as an architectural constraint rather than an
  implementation detail
- preserves a practical process for a one-developer plus Development-Agent
  workflow by keeping process gates advisory for now

## Decision

The middleware architecture SHALL adopt an explicit layered stack and hook-role
contract.

For normative interpretation of the current intended architecture, Development
Agents MUST treat [`../architecture.md`](../architecture.md) as authoritative;
this record captures rationale and adoption history for that architecture.

### Layering policy

Middleware composition for Research Agent harnesses SHOULD follow this order
(outer to inner):

1. Deep Agents default middleware, unless deliberately replaced for a specific
   experiment
2. LangChain prebuilt generic resilience middleware (retry/fallback/context
   editing/limits), when needed
3. RDF capability middleware (`DatasetMiddleware`, `RDFVocabularyMiddleware`)
4. RDF orchestration and policy middleware (`ContinuationGuardMiddleware`)
5. Provider-specific adapter middleware only when model-specific behavior
   requires it

### Hook-role policy

- `before_model` / `after_model` hooks MUST be used for state transitions,
  routing, and non-conflicting state updates.
- `wrap_model_call` / `awrap_model_call` hooks MUST own provider-bound
  request/response canonicalization, including transcript-shape normalization.
- Middleware MUST avoid node-hook transcript surgery via `RemoveMessage` when an
  equivalent provider-bound request repair path exists.
- Middleware design MUST treat `add_messages` reducer semantics as a
  first-class constraint and MUST avoid stale-delete patterns.

### State and evolution policy

- Shared service injection remains explicit and capability-scoped.
- Middleware state namespaces SHOULD remain concern-scoped (`rdf_*`,
  `continuation_*`, `memory_*`, `skills_*`).
- `MemoryMiddleware` and `SkillsMiddleware` adoption SHOULD be staged after
  stack layering and hook-role boundaries are stable.

### Process policy

- Middleware PR review gates (checklists/rubric scoring) are accepted as a
  future direction and SHOULD be treated as advisory internal guidance for now.
- These gates SHALL NOT be treated as hard mandatory enforcement criteria in the
  current one-developer plus Development-Agent workflow.

## Consequences

Benefits:

- middleware behavior becomes easier to reason about because ownership is
  explicit by stack layer and hook type
- reducer-safety failures become less likely because transcript-shape repair is
  centralized at provider-bound boundaries
- framework defaults and built-ins can be leveraged with less custom
  duplication
- the architecture is better positioned for later memory/skills integration and
  subagent packaging

Costs and follow-up considerations:

- some existing architecture wording and decision-record references must be
  updated to this unified policy
- tests must continue to include graph-level regression coverage for reducer and
  transcript-shape behaviors
- advisory review gates still require disciplined use by maintainers since they
  are not enforced mechanically

## Supersedes

- [DR-018 State-Machine Continuation Control for Single-Run Harnesses](DR-018%20State-Machine%20Continuation%20Control%20for%20Single-Run%20Harnesses.md)
- [DR-019 Shared Middleware Services and Unified Vocabulary Configuration](DR-019%20Shared%20Middleware%20Services%20and%20Unified%20Vocabulary%20Configuration.md)
