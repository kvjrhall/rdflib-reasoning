from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """Normalized trace event captured from LangChain callbacks."""

    kind: str
    run_id: UUID
    name: str | None = None
    parent_run_id: UUID | None = None
    tags: tuple[str, ...] = ()
    payload: Mapping[str, Any] = field(default_factory=dict)


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


__all__ = [
    "TraceEvent",
    "TraceRecorder",
    "TraceSink",
]
