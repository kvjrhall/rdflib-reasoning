from typing import Annotated, Final, Literal

from langchain.agents.middleware import AgentState
from langchain.agents.middleware.types import PrivateStateAttr
from langgraph.channels.ephemeral_value import EphemeralValue
from typing_extensions import NotRequired

ContinuationMode = Literal["normal", "finalize_only", "stop_now"]

# ``before_model`` may set this and ``wrap_model_call`` may clear it in the same graph
# step; ``guard=False`` lets LangGraph coalesce multiple writes (last value wins).
_PENDING_TOOL_TRANSCRIPT_CHANNEL: Final[EphemeralValue[str | None]] = EphemeralValue(
    str | None,
    guard=False,
)


class ContinuationGuardState(AgentState):
    """Private orchestration state for continuation control."""

    continuation_mode: NotRequired[Annotated[ContinuationMode, PrivateStateAttr]]
    finalize_only_forbidden_tool_rounds: NotRequired[Annotated[int, PrivateStateAttr]]
    """Count of consecutive finalize-only model turns that still emitted tool calls."""

    pending_tool_transcript_system_reminder: NotRequired[
        Annotated[str | None, _PENDING_TOOL_TRANSCRIPT_CHANNEL, PrivateStateAttr]
    ]
    """Tool-transcript repair nudge deferred from ``before_model`` for ``wrap_model_call``."""
