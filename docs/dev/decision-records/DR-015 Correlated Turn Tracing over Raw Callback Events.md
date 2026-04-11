# Correlated Turn Tracing over Raw Callback Events

## Status

Accepted

## Context

`rdflib-reasoning-middleware` already captures runtime tracing as append-only
callback events using `TraceEvent`, `TraceRecorder`, and `TraceSink`. This is a
useful low-level debugging substrate, but it leaves downstream consumers to
reconstruct higher-level turn structure for themselves.

The notebook trace renderer currently performs that reconstruction directly. It
groups raw events into turns, correlates tool starts and ends, attaches
`ToolMessage` payloads, and infers rendering boundaries from model finish
reasons. That coupling creates two problems:

- correlation logic lives in a presentation component rather than in a reusable
  tracing layer
- any future consumer beyond the notebook renderer would need to duplicate the
  same event-grouping and tool-correlation behavior

The runtime also needs a clearer observability boundary for Research Agent
experiments. Development Agents should be able to inspect both the raw callback
facts and a correlated view of what happened in one Research Agent turn without
reimplementing that derivation for each consumer.

## Decision

Tracing will use two architectural layers:

- `TraceEvent`, `TraceRecorder`, and `TraceSink` remain the canonical raw
  callback-event capture layer.
- A separate correlated layer produces `TurnTrace` artifacts from raw events.

`TurnTrace` is the primary downstream tracing artifact. A `TurnTrace` represents
one correlated Research Agent turn and includes:

- a concise model-input summary suitable for debugging
- visible streamed agent output for the turn
- requested tool calls and invalid tool calls
- correlated tool invocations, including results and `ToolMessage` payloads
- final response metadata

`TurnTracer` is responsible for deriving `TurnTrace` instances from raw events.
Correlation is therefore a middleware tracing concern rather than a renderer
concern.

The correlation contract is:

- a turn begins at `chat_model_start`
- a turn ends when the model finishes without pending tool-call continuation
- tool calls belong to the current open turn
- tool lifecycle correlation SHOULD use `tool_call_id` when available
- if `tool_call_id` is unavailable, correlation MAY fall back conservatively to
  invocation order and tool name
- partial tool lifecycles MUST remain representable rather than being dropped

Notebook rendering is an important consumer of tracing, but it is only a
consumer. Renderers SHOULD consume `TurnTrace` artifacts rather than owning
turn-grouping and tool-correlation logic themselves.

## Consequences

Benefits:

- downstream consumers gain a stable turn-level tracing interface
- notebook rendering becomes simpler and more focused on presentation
- runtime debugging can surface middleware-injected messages and other
  turn-local context more reliably
- the repository retains low-level callback evidence without forcing every
  consumer to reason from it directly

Costs and follow-up considerations:

- the tracing package now maintains two public layers rather than one
- tests must cover both raw event capture and turn-level correlation
- Development Agents should treat `TurnTrace` as the preferred high-level API
  while retaining raw event tooling for lower-level debugging

## Supersedes

None.
