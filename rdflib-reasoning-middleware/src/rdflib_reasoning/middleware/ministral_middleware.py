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

logger = logging.getLogger(__name__)

_MINISTRAL_PROMPT_SUFFIX: Final[str] = """
# HOW YOU SHOULD THINK AND ANSWER

First draft your thinking process (inner monologue) until you arrive at a response. Format your response using Markdown, and use LaTeX for any mathematical equations. Write both your thoughts and the response in the same language as the input.

Your thinking process must follow the template below:[THINK]Your thoughts or/and draft, like working through an exercise on scratch paper. Be as casual and as long as you want until you are confident to generate the response to the user.[/THINK]Here, provide a self-contained response.
"""


class MinistralPromptSuffixMiddleware(AgentMiddleware[Any, ContextT, ResponseT]):
    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        """Append Ministral prompt suffix to the system prompt before model execution."""
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
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                _MINISTRAL_PROMPT_SUFFIX,
            )
        )
        return await handler(request)
