# mypy: disable-error-code="import-not-found"

try:
    from IPython.display import Markdown, display  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    raise ImportError(
        "Notebook tracing requires optional dependency support. "
        "Install `rdflib-reasoning-middleware[notebook]` to use "
        "`rdflib_reasoning.middleware.tracing_notebook`."
    ) from exc

import json
import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from threading import Event, Thread
from typing import Any, Self

from .tracing import (
    TraceRecorder,
    TraceSink,
    TurnTrace,
    TurnTracer,
    TurnTraceToolCall,
    normalize_trace_json_value,
    turn_traces_to_json_document,
)


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

    def _render_markdown(self, events: Iterable[Any]) -> str:
        turns = TurnTracer().snapshot(events)
        lines = [f"# {self.heading}", ""]
        for turn_index, turn in enumerate(turns, start=1):
            lines.append(f"## Turn {turn_index}")
            lines.append("")
            lines.extend(self._render_turn(turn))
        if len(lines) == 2:
            lines.append("_No trace events yet._")
        return "\n".join(lines)

    def _render_turn(self, turn: TurnTrace) -> list[str]:
        lines: list[str] = []
        if turn.input_summary:
            lines.extend(
                [
                    "### Model Input Summary",
                    "",
                    *self._render_input_summary(turn.input_summary),
                    "",
                ]
            )

        if turn.agent_output:
            lines.extend(
                [
                    "### Agent Output",
                    "",
                    *self._quote_block(turn.agent_output),
                    "",
                ]
            )

        lines.extend(self._render_turn_decision(turn))
        lines.extend(self._render_tool_events(turn.tool_invocations))
        return lines

    def _render_turn_decision(self, turn: TurnTrace) -> list[str]:
        lines: list[str] = []
        finish_reason = turn.response_metadata.get("finish_reason")
        if turn.requested_tool_calls:
            if len(turn.requested_tool_calls) == 1 and not turn.invalid_tool_calls:
                return lines
            lines.extend(
                [
                    "### Model Decision",
                    "",
                    f"- Finish reason: `{finish_reason}`",
                    f"- Tool calls: `{len(turn.requested_tool_calls)}`",
                    "",
                ]
            )
            if len(turn.requested_tool_calls) > 1 or turn.invalid_tool_calls:
                lines.extend(self._render_tool_calls(turn.requested_tool_calls))
            if turn.invalid_tool_calls:
                lines.extend(
                    [
                        "#### Invalid Tool Calls",
                        "",
                        "```json",
                        self._pretty_json(turn.invalid_tool_calls),
                        "```",
                        "",
                    ]
                )
            return lines
        if turn.final_content:
            return [
                "### Final Response",
                "",
                *self._quote_block(str(turn.final_content)),
                "",
            ]
        return [
            "### Model Decision",
            "",
            f"- Finish reason: `{finish_reason}`",
            "",
        ]

    def _pretty_json(self, value: Any) -> str:
        normalized = self._normalize(value)
        if isinstance(normalized, str):
            return normalized
        return json.dumps(normalized, indent=2, sort_keys=True)

    def _normalize(self, value: Any) -> Any:
        return normalize_trace_json_value(value)

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

    def _render_tool_events(self, events: Iterable[TurnTraceToolCall]) -> list[str]:
        if not events:
            return []

        lines: list[str] = []
        for invocation in events:
            lines.extend(self._render_tool_invocation(invocation))
        return lines

    def _render_tool_invocation(self, invocation: TurnTraceToolCall) -> list[str]:
        lines = [f"### Tool: {invocation.name}", ""]

        if invocation.requested_arguments is not None:
            lines.extend(
                [
                    "#### Arguments",
                    "",
                    "```json",
                    self._pretty_json(invocation.requested_arguments),
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

    def _render_input_summary(self, summary: Iterable[Mapping[str, Any]]) -> list[str]:
        lines: list[str] = []
        for message in summary:
            normalized = self._normalize(message)
            if not isinstance(normalized, Mapping):
                lines.append(f"- `{normalized}`")
                continue
            message_type = normalized.get("type", "message")
            content_preview = normalized.get("content_preview")
            if content_preview:
                lines.append(f"- `{message_type}`: {content_preview}")
            else:
                lines.append(f"- `{message_type}`")
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

    def dump(
        self,
        path: str | Path | os.PathLike[str] | None = None,
        *,
        indent: int | None = 2,
    ) -> str:
        """Persist correlated :class:`~.tracing.TurnTrace` rows as JSON.

        When ``path`` is ``None``, returns the transcript as a string and does
        not write to disk. Otherwise writes UTF-8 JSON and returns the path as
        a string.
        """
        turns = TurnTracer().snapshot(self.sink.snapshot())
        document = turn_traces_to_json_document(turns)
        text = json.dumps(document, indent=indent, sort_keys=True)
        if path is None:
            return text
        out = Path(path)
        out.write_text(text, encoding="utf-8")
        return str(out)

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
