import re
from collections.abc import Sequence
from typing import Literal, NamedTuple

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from rdflib import Graph


class ToolTranscriptIssue(NamedTuple):
    """Provider-visible tool transcript issue detected in message history."""

    kind: Literal["orphan_tool_response", "unresolved_tool_call"]
    message: BaseMessage


_RECOVERY_INTENT_MARKERS: tuple[str, ...] = (
    "let me correct",
    "i will correct",
    "i'll correct",
    "let me fix",
    "i will fix",
    "i'll fix",
    "i intended to",
    "i missed it",
    "i will also ensure",
    "i need to add",
    "i will add",
    "i'll add",
)
_PLAN_INTENT_MARKERS: tuple[str, ...] = (
    "here's how i will proceed",
    "here is how i will proceed",
    "step-by-step plan",
    "step by step plan",
    "let me",
    "i will now",
    "next i will",
    "i will help you",
    "i will model",
    "i will define",
    "i will mint",
)


def _extract_completed_turtle_block(content: str) -> str | None:
    match = re.search(
        r"```text/turtle\s*\n(.*?)```", content, re.IGNORECASE | re.DOTALL
    )
    if match is None:
        return None
    return match.group(1)


def looks_like_completed_answer(content: str) -> bool:
    turtle = _extract_completed_turtle_block(content)
    if turtle is None:
        return False

    try:
        Graph().parse(data=turtle, format="turtle")
    except Exception:
        return False
    return True


def completed_turtle_answer_represents_empty_graph(content: str) -> bool:
    turtle = _extract_completed_turtle_block(content)
    if turtle is None:
        return False

    try:
        graph = Graph().parse(data=turtle, format="turtle")
    except Exception:
        return False
    return len(graph) == 0


def latest_ai_message(messages: Sequence[AnyMessage]) -> AIMessage | None:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def looks_like_recovery_intent(content: str) -> bool:
    normalized = content.casefold()
    return any(marker in normalized for marker in _RECOVERY_INTENT_MARKERS)


def looks_like_plan_intent(content: str) -> bool:
    normalized = content.casefold()
    return any(marker in normalized for marker in _PLAN_INTENT_MARKERS)


def summarize_message_tail(messages: Sequence[AnyMessage], *, limit: int = 5) -> str:
    tail = messages[-limit:]
    if not tail:
        return "<empty>"

    def summarize(message: BaseMessage) -> str:
        message_id = getattr(message, "id", None)
        if isinstance(message, AIMessage):
            return (
                f"ai(id={message_id!r}, tool_calls={len(message.tool_calls)}, "
                f"invalid_tool_calls={len(message.invalid_tool_calls)})"
            )
        if isinstance(message, ToolMessage):
            return (
                f"tool(id={message_id!r}, tool_call_id={message.tool_call_id!r}, "
                f"status={getattr(message, 'status', None)!r})"
            )
        if isinstance(message, HumanMessage):
            return f"user(id={message_id!r})"
        return f"{type(message).__name__}(id={message_id!r})"

    return " -> ".join(summarize(message) for message in tail)


def has_recent_guard_reminder(messages: Sequence[AnyMessage], prefix: str) -> bool:
    seen_latest_ai = False
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            if seen_latest_ai:
                return False
            seen_latest_ai = True
            continue
        if not seen_latest_ai:
            continue
        if isinstance(message, HumanMessage) and str(message.content).startswith(
            prefix
        ):
            return True
    return False


def find_tool_transcript_issue(
    messages: Sequence[AnyMessage],
) -> ToolTranscriptIssue | None:
    """Detect unresolved tool-call turns before they reach the model provider.

    OpenAI-compatible providers expect each assistant tool-call turn to be followed
    by matching tool-response messages before any subsequent non-tool message.
    Detecting malformed history locally lets middleware repair or reject it in a
    model-agnostic way instead of surfacing provider-specific ``BadRequestError``
    responses.
    """

    pending_tool_call_ids: set[str] = set()
    pending_ai_message: AIMessage | None = None

    for message in messages:
        if pending_tool_call_ids:
            if isinstance(message, ToolMessage):
                tool_call_id = getattr(message, "tool_call_id", None)
                if (
                    isinstance(tool_call_id, str)
                    and tool_call_id in pending_tool_call_ids
                ):
                    pending_tool_call_ids.remove(tool_call_id)
                    if not pending_tool_call_ids:
                        pending_ai_message = None
                    continue
                return ToolTranscriptIssue("orphan_tool_response", message)
            if pending_ai_message is not None:
                return ToolTranscriptIssue("unresolved_tool_call", pending_ai_message)
            return ToolTranscriptIssue("unresolved_tool_call", message)

        if isinstance(message, ToolMessage):
            return ToolTranscriptIssue("orphan_tool_response", message)

        if not isinstance(message, AIMessage):
            continue

        tool_call_ids = {
            str(tool_call.get("id"))
            for tool_call in message.tool_calls
            if isinstance(tool_call, dict) and tool_call.get("id")
        }
        if tool_call_ids:
            pending_tool_call_ids = tool_call_ids
            pending_ai_message = message

    if pending_ai_message is not None and pending_tool_call_ids:
        return ToolTranscriptIssue("unresolved_tool_call", pending_ai_message)

    return None
