from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import ToolMessage


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """Normalized trace event captured from LangChain callbacks."""

    kind: str
    run_id: UUID
    name: str | None = None
    parent_run_id: UUID | None = None
    tags: tuple[str, ...] = ()
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TurnTraceToolCall:
    """Correlated view of one tool invocation within a model turn."""

    name: str
    requested_arguments: Any = None
    tool_call_id: str | None = None
    result: Any = None
    tool_message: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class TurnTrace:
    """Correlated trace artifact for one Research Agent turn."""

    run_id: UUID
    name: str | None = None
    parent_run_id: UUID | None = None
    tags: tuple[str, ...] = ()
    input_summary: tuple[Mapping[str, Any], ...] = ()
    agent_output: str = ""
    final_content: Any = None
    requested_tool_calls: tuple[Mapping[str, Any], ...] = ()
    invalid_tool_calls: tuple[Mapping[str, Any], ...] = ()
    tool_invocations: tuple[TurnTraceToolCall, ...] = ()
    response_metadata: Mapping[str, Any] = field(default_factory=dict)


class TraceSink:
    """Append-only bounded trace buffer."""

    def __init__(self, max_events: int = 500) -> None:
        self._events: deque[TraceEvent] = deque(maxlen=max_events)
        self._lock = Lock()

    def append(self, event: TraceEvent) -> None:
        with self._lock:
            self._events.append(event)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def snapshot(self) -> tuple[TraceEvent, ...]:
        with self._lock:
            return tuple(self._events)


def _tool_call_chunk_field(chunk: Any, field: str) -> Any:
    if isinstance(chunk, Mapping):
        return chunk.get(field)
    return getattr(chunk, field, None)


def _tool_call_field(tool_call: Any, field: str) -> Any:
    if isinstance(tool_call, Mapping):
        value = tool_call.get(field)
        if value is not None:
            return value
        function = tool_call.get("function")
        if isinstance(function, Mapping):
            return function.get(field)
        return None
    value = getattr(tool_call, field, None)
    if value is not None:
        return value
    function = getattr(tool_call, "function", None)
    return getattr(function, field, None) if function is not None else None


def _truncate_preview(text: str, limit: int = 240) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


def _content_preview(content: Any) -> str:
    if isinstance(content, str):
        return _truncate_preview(content)
    if isinstance(content, Mapping):
        if content.get("type") == "text" and isinstance(content.get("text"), str):
            return _truncate_preview(content["text"])
        return _truncate_preview(
            str({str(k): _content_preview(v) for k, v in content.items()})
        )
    if isinstance(content, Sequence) and not isinstance(content, str):
        parts: list[str] = []
        for item in content:
            preview = _content_preview(item)
            if preview:
                parts.append(preview)
        return _truncate_preview(" ".join(parts))
    if content is None:
        return ""
    return _truncate_preview(str(content))


def _message_type(message: Any) -> str:
    if hasattr(message, "type") and isinstance(message.type, str):
        return message.type
    return type(message).__name__


def _summarize_message(
    message: Any, *, batch_index: int, message_index: int
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "batch_index": batch_index,
        "message_index": message_index,
        "type": _message_type(message),
    }
    name = getattr(message, "name", None)
    if name is not None:
        summary["name"] = name
    content_preview = _content_preview(getattr(message, "content", None))
    if content_preview:
        summary["content_preview"] = content_preview
    tool_call_id = getattr(message, "tool_call_id", None)
    if tool_call_id is not None:
        summary["tool_call_id"] = tool_call_id
    status = getattr(message, "status", None)
    if status is not None:
        summary["status"] = status
    return summary


def _summarize_message_batches(
    messages: Sequence[Sequence[Any]],
) -> tuple[Mapping[str, Any], ...]:
    summaries: list[Mapping[str, Any]] = []
    for batch_index, batch in enumerate(messages):
        for message_index, message in enumerate(batch):
            summaries.append(
                _summarize_message(
                    message,
                    batch_index=batch_index,
                    message_index=message_index,
                )
            )
    return tuple(summaries)


class TraceRecorder(BaseCallbackHandler):
    """Collect LangChain lifecycle callbacks into a trace sink."""

    raise_error = False

    def __init__(self, sink: TraceSink) -> None:
        self.sink = sink

    def _append(
        self,
        *,
        kind: str,
        run_id: UUID,
        name: str | None = None,
        parent_run_id: UUID | None = None,
        tags: Sequence[str] | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        self.sink.append(
            TraceEvent(
                kind=kind,
                run_id=run_id,
                name=name,
                parent_run_id=parent_run_id,
                tags=tuple(tags or ()),
                payload=dict(payload or {}),
            )
        )

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        del kwargs
        self._append(
            kind="chat_model_start",
            run_id=run_id,
            name=serialized.get("name"),
            parent_run_id=parent_run_id,
            tags=tags,
            payload={
                "message_batches": len(messages),
                "messages_per_batch": tuple(len(batch) for batch in messages),
                "input_summary": _summarize_message_batches(messages),
                "metadata": metadata or {},
            },
        )

    def on_llm_new_token(
        self,
        token: str,
        *,
        chunk: Any = None,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> Any:
        del kwargs
        tool_call_chunks = []
        if chunk is not None:
            for tool_call_chunk in getattr(chunk, "tool_call_chunks", []) or []:
                tool_call_chunks.append(
                    {
                        "index": _tool_call_chunk_field(tool_call_chunk, "index"),
                        "id": _tool_call_chunk_field(tool_call_chunk, "id"),
                        "name": _tool_call_chunk_field(tool_call_chunk, "name"),
                        "args": _tool_call_chunk_field(tool_call_chunk, "args"),
                    }
                )
        self._append(
            kind="llm_new_token",
            run_id=run_id,
            parent_run_id=parent_run_id,
            tags=tags,
            payload={
                "token": token,
                "content": getattr(chunk, "content", None)
                if chunk is not None
                else None,
                "tool_call_chunks": tuple(tool_call_chunks),
            },
        )

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> Any:
        del kwargs
        generations = getattr(response, "generations", [])
        first_generation = generations[0][0] if generations and generations[0] else None
        message = getattr(first_generation, "message", None)
        payload = {
            "text": getattr(first_generation, "text", None),
            "content": getattr(message, "content", None),
            "tool_calls": getattr(message, "tool_calls", ()),
            "invalid_tool_calls": getattr(message, "invalid_tool_calls", ()),
            "response_metadata": getattr(message, "response_metadata", {}),
        }
        self._append(
            kind="llm_end",
            run_id=run_id,
            parent_run_id=parent_run_id,
            tags=tags,
            payload=payload,
        )

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        del kwargs
        self._append(
            kind="tool_start",
            run_id=run_id,
            name=serialized.get("name"),
            parent_run_id=parent_run_id,
            tags=tags,
            payload={
                "input_str": input_str,
                "inputs": inputs or {},
                "metadata": metadata or {},
            },
        )

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        del kwargs
        tool_name = getattr(output, "name", None)
        tool_call_id = getattr(output, "tool_call_id", None)
        artifact = getattr(output, "artifact", None)
        if artifact is not None:
            content = artifact
        else:
            content = getattr(output, "content", output)
        self._append(
            kind="tool_end",
            run_id=run_id,
            name=tool_name,
            parent_run_id=parent_run_id,
            payload={
                "output": content,
                "tool_call_id": tool_call_id,
            },
        )

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        del kwargs
        for tool_message in _tool_messages(outputs):
            self._append(
                kind="tool_message",
                run_id=run_id,
                name=getattr(tool_message, "name", None),
                parent_run_id=parent_run_id,
                payload={
                    "content": getattr(tool_message, "content", ""),
                    "tool_call_id": getattr(tool_message, "tool_call_id", None),
                    "status": getattr(tool_message, "status", None),
                },
            )


@dataclass(slots=True)
class _TurnTraceToolCallBuilder:
    name: str
    requested_arguments: Any = None
    tool_call_id: str | None = None
    result: Any = None
    tool_message: Mapping[str, Any] | None = None

    @property
    def is_complete(self) -> bool:
        return self.result is not None or self.tool_message is not None

    def build(self) -> TurnTraceToolCall:
        return TurnTraceToolCall(
            name=self.name,
            requested_arguments=self.requested_arguments,
            tool_call_id=self.tool_call_id,
            result=self.result,
            tool_message=self.tool_message,
        )


@dataclass(slots=True)
class _TurnTraceBuilder:
    run_id: UUID
    name: str | None = None
    parent_run_id: UUID | None = None
    tags: tuple[str, ...] = ()
    input_summary: tuple[Mapping[str, Any], ...] = ()
    token_buffer: list[str] = field(default_factory=list)
    final_content: Any = None
    requested_tool_calls: list[Mapping[str, Any]] = field(default_factory=list)
    invalid_tool_calls: list[Mapping[str, Any]] = field(default_factory=list)
    tool_invocations: list[_TurnTraceToolCallBuilder] = field(default_factory=list)
    response_metadata: Mapping[str, Any] = field(default_factory=dict)
    is_open: bool = True

    def build(self) -> TurnTrace:
        return TurnTrace(
            run_id=self.run_id,
            name=self.name,
            parent_run_id=self.parent_run_id,
            tags=self.tags,
            input_summary=self.input_summary,
            agent_output="".join(self.token_buffer),
            final_content=self.final_content,
            requested_tool_calls=tuple(self.requested_tool_calls),
            invalid_tool_calls=tuple(self.invalid_tool_calls),
            tool_invocations=tuple(
                invocation.build() for invocation in self.tool_invocations
            ),
            response_metadata=self.response_metadata,
        )


class TurnTracer:
    """Correlate raw trace events into turn-level trace artifacts."""

    def snapshot(self, events: Iterable[TraceEvent]) -> tuple[TurnTrace, ...]:
        turns: list[TurnTrace] = []
        current_turn: _TurnTraceBuilder | None = None

        for event in events:
            if event.kind == "chat_model_start":
                if current_turn is not None:
                    turns.append(current_turn.build())
                payload = dict(event.payload)
                current_turn = _TurnTraceBuilder(
                    run_id=event.run_id,
                    name=event.name,
                    parent_run_id=event.parent_run_id,
                    tags=event.tags,
                    input_summary=tuple(payload.get("input_summary", ())),
                )
                continue

            if current_turn is None:
                continue

            if event.kind == "llm_new_token":
                payload = dict(event.payload)
                content = payload.get("content") or payload.get("token")
                if content:
                    current_turn.token_buffer.append(str(content))
                continue

            if event.kind == "llm_end":
                payload = dict(event.payload)
                current_turn.final_content = payload.get("content")
                current_turn.response_metadata = dict(
                    payload.get("response_metadata", {})
                )
                current_turn.requested_tool_calls = [
                    dict(_normalize_mapping(tool_call))
                    for tool_call in tuple(payload.get("tool_calls", ()))
                ]
                current_turn.invalid_tool_calls = [
                    dict(_normalize_mapping(tool_call))
                    for tool_call in tuple(payload.get("invalid_tool_calls", ()))
                ]
                current_turn.tool_invocations = [
                    _TurnTraceToolCallBuilder(
                        name=str(normalized.get("name", "unknown")),
                        requested_arguments=normalized.get("args"),
                        tool_call_id=_normalize_tool_call_id(normalized),
                    )
                    for normalized in current_turn.requested_tool_calls
                ]
                finish_reason = current_turn.response_metadata.get("finish_reason")
                if (
                    not current_turn.requested_tool_calls
                    and finish_reason != "tool_calls"
                ):
                    current_turn.is_open = False
                    turns.append(current_turn.build())
                    current_turn = None
                continue

            if event.kind == "tool_start":
                payload = dict(event.payload)
                invocation = self._match_tool_invocation(
                    current_turn.tool_invocations,
                    name=event.name,
                    tool_call_id=None,
                )
                if invocation is None:
                    invocation = _TurnTraceToolCallBuilder(name=event.name or "unknown")
                    current_turn.tool_invocations.append(invocation)
                if invocation.requested_arguments is None:
                    invocation.requested_arguments = payload.get(
                        "inputs"
                    ) or payload.get("input_str")
                continue

            if event.kind == "tool_end":
                payload = dict(event.payload)
                invocation = self._match_tool_invocation(
                    current_turn.tool_invocations,
                    name=event.name,
                    tool_call_id=payload.get("tool_call_id"),
                )
                if invocation is None:
                    invocation = _TurnTraceToolCallBuilder(
                        name=event.name or "unknown",
                        tool_call_id=payload.get("tool_call_id"),
                    )
                    current_turn.tool_invocations.append(invocation)
                if invocation.tool_call_id is None:
                    invocation.tool_call_id = payload.get("tool_call_id")
                invocation.result = payload.get("output")
                continue

            if event.kind == "tool_message":
                payload = dict(event.payload)
                invocation = self._match_tool_invocation(
                    current_turn.tool_invocations,
                    name=event.name,
                    tool_call_id=payload.get("tool_call_id"),
                )
                if invocation is None:
                    invocation = _TurnTraceToolCallBuilder(
                        name=event.name or "unknown",
                        tool_call_id=payload.get("tool_call_id"),
                    )
                    current_turn.tool_invocations.append(invocation)
                if invocation.tool_call_id is None:
                    invocation.tool_call_id = payload.get("tool_call_id")
                invocation.tool_message = {
                    "status": payload.get("status"),
                    "tool_call_id": payload.get("tool_call_id"),
                    "content": payload.get("content"),
                }

        if current_turn is not None:
            turns.append(current_turn.build())

        return tuple(turns)

    def _match_tool_invocation(
        self,
        invocations: list[_TurnTraceToolCallBuilder],
        *,
        name: str | None,
        tool_call_id: str | None,
    ) -> _TurnTraceToolCallBuilder | None:
        if tool_call_id is not None:
            for invocation in invocations:
                if invocation.tool_call_id == tool_call_id:
                    return invocation

        for invocation in reversed(invocations):
            if invocation.is_complete:
                continue
            if name is None or invocation.name == name:
                return invocation

        if tool_call_id is not None:
            for invocation in reversed(invocations):
                if invocation.name == name:
                    return invocation
        return None


def _normalize_tool_call_id(tool_call: Mapping[str, Any]) -> str | None:
    value = tool_call.get("id")
    return str(value) if value is not None else None


def _normalize_mapping(value: Any) -> Mapping[str, Any]:
    normalized: dict[str, Any] = {}
    for field_name in ("id", "name", "args", "error"):
        extracted = _tool_call_field(value, field_name)
        if extracted is not None:
            normalized[field_name] = extracted
    if not normalized and isinstance(value, Mapping):
        return dict(value)
    return normalized


def _tool_messages(outputs: Any) -> tuple[ToolMessage, ...]:
    messages = []
    pending = [outputs]

    while pending:
        current = pending.pop()
        if isinstance(current, ToolMessage):
            messages.append(current)
            continue
        if isinstance(current, Mapping):
            pending.extend(current.values())
            continue
        if isinstance(current, Sequence) and not isinstance(current, str):
            pending.extend(current)

    return tuple(messages)


__all__ = [
    "TraceEvent",
    "TraceRecorder",
    "TraceSink",
    "TurnTrace",
    "TurnTraceToolCall",
    "TurnTracer",
]
