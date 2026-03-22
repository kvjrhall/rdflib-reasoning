import logging
from collections.abc import Awaitable, Callable
from typing import Any, Final, override

from deepagents.middleware._utils import append_to_system_message
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import (
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.types import Command

logger = logging.getLogger(__name__)

_MINISTRAL_PROMPT_SUFFIX: Final[str] = """
# HOW YOU SHOULD THINK AND ANSWER

First draft your thinking process (inner monologue) until you arrive at a response. Format your response using Markdown, and use LaTeX for any mathematical equations. Write both your thoughts and the response in the same language as the input.

Your thinking process must follow the template below:[THINK]Your thoughts or/and draft, like working through an exercise on scratch paper. Be as casual and as long as you want until you are confident to generate the response to the user.[/THINK]Here, provide a self-contained response.
"""

_RECOVERY_REMINDER_PREFIX: Final[str] = (
    "[rdflibr-recovery] A tool call just failed. Do not narrate that you will fix it."
)
_RECOVERY_REMINDER: Final[str] = (
    f"{_RECOVERY_REMINDER_PREFIX} Instead, either emit the corrected tool call now or, "
    "if the task is actually complete, provide a short completed answer. Keep tool "
    "arguments explicit and fully corrected before retrying."
)
_CONTINUATION_INTENT_MARKERS: Final[tuple[str, ...]] = (
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


def _latest_ai_message(messages: list[BaseMessage]) -> AIMessage | None:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def _has_recent_error_tool_message(messages: list[BaseMessage]) -> bool:
    seen_latest_ai = False
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            if seen_latest_ai:
                return False
            seen_latest_ai = True
            continue
        if not seen_latest_ai:
            continue
        if (
            isinstance(message, ToolMessage)
            and getattr(message, "status", None) == "error"
        ):
            return True
    return False


def _has_recent_recovery_reminder(messages: list[BaseMessage]) -> bool:
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
            _RECOVERY_REMINDER_PREFIX
        ):
            return True
    return False


def _looks_like_unfinished_recovery(content: str) -> bool:
    normalized = content.casefold()
    return any(marker in normalized for marker in _CONTINUATION_INTENT_MARKERS)


class MinistralPromptSuffixMiddleware(AgentMiddleware[Any, ContextT, ResponseT]):
    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        """Append Ministral prompt suffix to the system prompt before model execution."""
        logger.debug("Wrapping model call for Ministral Prompt Suffix Middleware")
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                _MINISTRAL_PROMPT_SUFFIX,
            )
        )
        return handler(request)

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[
            [ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]
        ],
    ) -> ModelResponse[ResponseT]:
        """Append Ministral prompt suffix to the system prompt before async model execution."""
        logger.debug(
            "Async wrapping model call for Ministral Prompt Suffix Middleware (async)"
        )
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                _MINISTRAL_PROMPT_SUFFIX,
            )
        )
        return await handler(request)

    @override
    def after_model(  # type: ignore[override]  # after_model's type hints are dated
        self, state: Any, runtime: Any
    ) -> dict[str, Any] | Command[Any] | None:
        del runtime
        messages = state.get("messages")
        if not isinstance(messages, list) or not messages:
            return None

        last_ai_message = _latest_ai_message(messages)
        if last_ai_message is None or last_ai_message.tool_calls:
            return None

        content = (
            last_ai_message.text
            if isinstance(last_ai_message.text, str)
            else str(last_ai_message.content)
        )
        if not content or not _looks_like_unfinished_recovery(content):
            return None
        if not _has_recent_error_tool_message(messages):
            return None
        if _has_recent_recovery_reminder(messages):
            return None

        logger.debug(
            "Detected unfinished recovery narration after tool rejection; re-prompting model"
        )
        return Command(
            update={"messages": [HumanMessage(content=_RECOVERY_REMINDER)]},
            goto="model",
        )
