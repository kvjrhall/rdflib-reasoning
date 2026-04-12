from collections.abc import Iterable, Sequence
from typing import Any

from deepagents import create_deep_agent
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool


class ToolFriendlyFakeMessagesListChatModel(FakeMessagesListChatModel):
    """Fake chat model that participates in tool-binding agent graphs."""

    def bind_tools(
        self,
        tools: Sequence[BaseTool | dict[str, Any]],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> "ToolFriendlyFakeMessagesListChatModel":
        del tools, tool_choice, kwargs
        return self

    def bind(self, **kwargs: Any) -> "ToolFriendlyFakeMessagesListChatModel":
        del kwargs
        return self


def create_agent_graph(
    model: ToolFriendlyFakeMessagesListChatModel,
    *,
    middleware: Sequence[AgentMiddleware[Any, Any, Any]],
    tools: Sequence[BaseTool] = (),
    system_prompt: str = "You are a research assistant.",
) -> Any:
    return create_agent(
        model=model,
        tools=list(tools),
        system_prompt=system_prompt,
        middleware=list(middleware),
    )


def create_deep_agent_graph(
    model: ToolFriendlyFakeMessagesListChatModel,
    *,
    middleware: Sequence[AgentMiddleware[Any, Any, Any]],
    tools: Sequence[BaseTool] = (),
    system_prompt: str = "You are a research assistant.",
) -> Any:
    return create_deep_agent(
        model=model,
        tools=list(tools),
        system_prompt=system_prompt,
        middleware=list(middleware),
    )


def collect_update_chunks(
    agent: Any,
    *,
    messages: Iterable[BaseMessage | dict[str, str]],
    recursion_limit: int = 20,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for chunk in agent.stream(
        {"messages": list(messages)},
        config={"recursion_limit": recursion_limit},
        stream_mode="updates",
    ):
        chunks.append(chunk)
    return chunks
