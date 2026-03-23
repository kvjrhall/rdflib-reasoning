try:
    from IPython.display import Markdown, display
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    raise ImportError(
        "Notebook tracing requires optional dependency support. "
        "Install `rdflib-reasoning-middleware[notebook]` to use "
        "`rdflib_reasoning.middleware.tracing_notebook`."
    ) from exc

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from threading import Event, Thread
from typing import Any, Self

from .tracing import TraceEvent, TraceRecorder, TraceSink


@dataclass(slots=True)
class _ToolInvocation:
    """Normalized lifecycle view of one tool invocation."""

    name: str
    started_arguments: Any = None
    result: Any = None
    tool_message: Mapping[str, Any] | None = None
    result_call_id: str | None = None


class NotebookTraceRenderer:
    """Render trace sink snapshots in a notebook cell."""

    def __init__(self, sink: TraceSink, *, heading: str = "Trace") -> None:
        self.sink = sink
        self.heading = heading
        self._handle = display(
            Markdown(f"### {heading}\n\n_No trace events yet._"),
            display_id=True,
        )

    def refresh(self) -> None:
        """Render the current sink snapshot into the notebook output."""
        self._handle.update(Markdown(self._render_markdown(self.sink.snapshot())))

    def _render_markdown(self, events: Iterable[TraceEvent]) -> str:
        lines = [f"# {self.heading}", ""]
        for turn_index, turn in enumerate(self._group_events(events), start=1):
            lines.append(f"## Turn {turn_index}")
            lines.append("")
            lines.extend(self._render_turn(turn))
        if len(lines) == 2:
            lines.append("_No trace events yet._")
        return "\n".join(lines)

    def _group_events(self, events: Iterable[TraceEvent]) -> list[list[TraceEvent]]:
        turns: list[list[TraceEvent]] = []
        current_turn: list[TraceEvent] = []

        for event in events:
            if event.kind == "chat_model_start" and current_turn:
                turns.append(current_turn)
                current_turn = []
            current_turn.append(event)
            if event.kind == "llm_end":
                payload = dict(event.payload)
                tool_calls = payload.get("tool_calls", ())
                finish_reason = dict(payload.get("response_metadata", {})).get(
                    "finish_reason"
                )
                if not tool_calls and finish_reason != "tool_calls":
                    turns.append(current_turn)
                    current_turn = []

        if current_turn:
            turns.append(current_turn)

        return turns

    def _render_turn(self, turn: list[TraceEvent]) -> list[str]:
        lines: list[str] = []
        token_buffer: list[str] = []
        tool_events: list[TraceEvent] = []

        for event in turn:
            if event.kind == "llm_new_token":
                payload = dict(event.payload)
                content = payload.get("content") or payload.get("token")
                if content:
                    token_buffer.append(str(content))
                continue

            if event.kind in {"tool_start", "tool_end", "tool_message"}:
                tool_events.append(event)
                continue

            if token_buffer:
                lines.extend(
                    [
                        "### Agent Output",
                        "",
                        *self._quote_block("".join(token_buffer)),
                        "",
                    ]
                )
                token_buffer.clear()

            lines.extend(self._render_event(event))

        if token_buffer:
            lines.extend(
                [
                    "### Agent Output",
                    "",
                    *self._quote_block("".join(token_buffer)),
                    "",
                ]
            )

        lines.extend(self._render_tool_events(tool_events))
        return lines

    def _render_event(self, event: TraceEvent) -> list[str]:
        payload = dict(event.payload)
        if event.kind == "chat_model_start":
            return []
        if event.kind == "tool_start":
            return []
        if event.kind == "tool_end":
            return []
        if event.kind == "tool_message":
            return []
        if event.kind == "llm_end":
            metadata = payload.get("response_metadata", {})
            finish_reason = metadata.get("finish_reason")
            tool_calls = payload.get("tool_calls", ())
            invalid_tool_calls = payload.get("invalid_tool_calls", ())
            content = payload.get("content")
            if tool_calls:
                if len(tool_calls) == 1 and not invalid_tool_calls:
                    return []
                lines = [
                    "### Model Decision",
                    "",
                    f"- Finish reason: `{finish_reason}`",
                    f"- Tool calls: `{len(tool_calls)}`",
                    "",
                ]
                if len(tool_calls) > 1 or invalid_tool_calls:
                    lines.extend(self._render_tool_calls(tool_calls))
                if invalid_tool_calls:
                    lines.extend(
                        [
                            "#### Invalid Tool Calls",
                            "",
                            "```json",
                            self._pretty_json(invalid_tool_calls),
                            "```",
                            "",
                        ]
                    )
                return lines
            if content:
                return [
                    "### Final Response",
                    "",
                    *self._quote_block(str(content)),
                    "",
                ]
            return [
                "### Model Decision",
                "",
                f"- Finish reason: `{finish_reason}`",
                "",
            ]
        return [
            f"### Event: {event.kind}",
            "",
            "```json",
            self._pretty_json(payload),
            "```",
            "",
        ]

    def _pretty_json(self, value: Any) -> str:
        normalized = self._normalize(value)
        if isinstance(normalized, str):
            return normalized
        return json.dumps(normalized, indent=2, sort_keys=True)

    def _normalize(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(key): self._normalize(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [self._normalize(item) for item in value]
        if isinstance(value, list):
            return [self._normalize(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _render_tool_calls(self, tool_calls: Any) -> list[str]:
        lines = ["#### Requested Tool Calls", ""]
        for index, tool_call in enumerate(tool_calls, start=1):
            normalized = self._normalize(tool_call)
            if isinstance(normalized, Mapping):
                name = normalized.get("name", "unknown")
                arguments = normalized.get("args")
                if arguments is None:
                    function = normalized.get("function")
                    if isinstance(function, Mapping):
                        name = function.get("name", name)
                        arguments = function.get("arguments")
                lines.append(f"{index}. `{name}`")
                if arguments is not None:
                    lines.extend(
                        [
                            "",
                            "```json",
                            self._pretty_json(arguments),
                            "```",
                            "",
                        ]
                    )
                else:
                    lines.append("")
                continue
            lines.extend(
                [
                    f"{index}.",
                    "",
                    "```json",
                    self._pretty_json(normalized),
                    "```",
                    "",
                ]
            )
        return lines

    def _render_tool_events(self, events: list[TraceEvent]) -> list[str]:
        if not events:
            return []

        lines: list[str] = []
        for invocation in self._collect_tool_invocations(events):
            lines.extend(self._render_tool_invocation(invocation))
        return lines

    def _collect_tool_invocations(
        self, events: list[TraceEvent]
    ) -> list[_ToolInvocation]:
        invocations: list[_ToolInvocation] = []

        for event in events:
            payload = dict(event.payload)

            if event.kind == "tool_start":
                tool_input = payload.get("inputs") or payload.get("input_str")
                invocations.append(
                    _ToolInvocation(
                        name=event.name or "unknown",
                        started_arguments=tool_input,
                    )
                )
                continue

            if event.kind == "tool_end":
                invocation = self._match_open_invocation(
                    invocations,
                    name=event.name,
                    tool_call_id=payload.get("tool_call_id"),
                )
                if invocation is None:
                    invocation = _ToolInvocation(name=event.name or "unknown")
                    invocations.append(invocation)
                invocation.result = payload.get("output")
                invocation.result_call_id = payload.get("tool_call_id")
                continue

            if event.kind == "tool_message":
                invocation = self._match_open_invocation(
                    invocations,
                    name=event.name,
                    tool_call_id=payload.get("tool_call_id"),
                )
                if invocation is None:
                    invocation = _ToolInvocation(name=event.name or "unknown")
                    invocations.append(invocation)
                invocation.tool_message = {
                    "status": payload.get("status"),
                    "tool_call_id": payload.get("tool_call_id"),
                    "content": payload.get("content"),
                }

        return invocations

    def _match_open_invocation(
        self,
        invocations: list[_ToolInvocation],
        *,
        name: str | None,
        tool_call_id: str | None,
    ) -> _ToolInvocation | None:
        del tool_call_id
        for invocation in reversed(invocations):
            if invocation.result is not None or invocation.tool_message is not None:
                continue
            if name and invocation.name == name:
                return invocation
        return None

    def _render_tool_invocation(self, invocation: _ToolInvocation) -> list[str]:
        lines = [f"### Tool: {invocation.name}", ""]

        if invocation.started_arguments is not None:
            lines.extend(
                [
                    "#### Arguments",
                    "",
                    "```json",
                    self._pretty_json(invocation.started_arguments),
                    "```",
                    "",
                ]
            )

        if invocation.result is not None:
            lines.extend(
                [
                    "#### Result",
                    "",
                    "```json",
                    self._pretty_json(invocation.result),
                    "```",
                    "",
                ]
            )

        if invocation.tool_message is not None:
            status = invocation.tool_message.get("status")
            heading = "#### Rejection" if status == "error" else "#### Message"
            lines.extend(
                [
                    heading,
                    "",
                    "```json",
                    self._pretty_json(invocation.tool_message),
                    "```",
                    "",
                ]
            )

        return lines

    def _quote_block(self, content: str) -> list[str]:
        return [f"> {line}" if line else ">" for line in content.splitlines()]


class LiveNotebookTrace:
    """Own a recorder and live-render notebook trace updates."""

    def __init__(
        self,
        *,
        heading: str = "Trace",
        max_events: int = 500,
        refresh_interval_seconds: float = 0.25,
    ) -> None:
        self.sink = TraceSink(max_events=max_events)
        self.recorder = TraceRecorder(self.sink)
        self.renderer = NotebookTraceRenderer(self.sink, heading=heading)
        self.refresh_interval_seconds = refresh_interval_seconds
        self._stop_event = Event()
        self._thread: Thread | None = None

    @property
    def callbacks(self) -> tuple[TraceRecorder, ...]:
        """Return callback handlers suitable for LangChain config injection."""
        return (self.recorder,)

    def start(self) -> None:
        """Begin periodic notebook refreshes until stopped."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop periodic refreshes and flush any remaining trace events."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(self.refresh_interval_seconds * 2, 0.1))
            self._thread = None
        self.renderer.refresh()

    def attach(self, runnable: Any) -> Any:
        """Return a runnable configured with this trace recorder."""
        return runnable.with_config({"callbacks": list(self.callbacks)})

    def refresh(self) -> None:
        """Force a notebook refresh immediately."""
        self.renderer.refresh()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        del exc_type, exc, tb
        self.stop()

    def _refresh_loop(self) -> None:
        while not self._stop_event.wait(timeout=self.refresh_interval_seconds):
            self.renderer.refresh()


__all__ = ["LiveNotebookTrace", "NotebookTraceRenderer"]
