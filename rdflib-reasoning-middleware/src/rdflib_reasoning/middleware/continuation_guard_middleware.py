import logging
import re
from ast import literal_eval
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Final, cast, override

from deepagents.middleware._utils import append_to_system_message
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import (
    ContextT,
    ExtendedModelResponse,
    ModelRequest,
    ModelResponse,
    ResponseT,
    hook_config,
)
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    ToolMessage,
)
from langgraph.types import Command

from ._message_heuristics import (
    find_tool_transcript_issue,
    has_recent_guard_reminder,
    latest_ai_message,
    looks_like_completed_answer,
    looks_like_plan_intent,
    looks_like_recovery_intent,
    summarize_message_tail,
)
from .continuation_state import ContinuationGuardState, ContinuationMode

logger = logging.getLogger(__name__)

_PENDING_TOOL_TRANSCRIPT_REMINDER_KEY: Final[str] = (
    "pending_tool_transcript_system_reminder"
)

_RECOVERY_REMINDER_PREFIX: Final[str] = (
    "[rdflib_reasoning-recovery] A tool call just failed. Do not narrate that you will fix it."
)
_RECOVERY_REMINDER: Final[str] = (
    f"{_RECOVERY_REMINDER_PREFIX} Instead, either emit the corrected tool call now or, "
    "if the task is actually complete, provide a short completed answer. Keep tool "
    "arguments explicit and fully corrected before retrying."
)
_PLAN_REMINDER_PREFIX: Final[str] = (
    "[rdflib_reasoning-continuation] Do not stop at an unfinished plan."
)
_PLAN_REMINDER: Final[str] = (
    f"{_PLAN_REMINDER_PREFIX} Either emit the next tool call now or return the "
    "completed final answer immediately."
)
_FINALIZE_REMINDER_PREFIX: Final[str] = (
    "[rdflib_reasoning-finalize] Return the completed final answer now."
)
_FINALIZE_REMINDER: Final[str] = (
    f"{_FINALIZE_REMINDER_PREFIX} Do not keep deliberating or re-inspecting the "
    "dataset. If your last successful `serialize_dataset` already reflects the "
    "graph you intend to present, reuse that Turtle directly as your final answer "
    "instead of calling `serialize_dataset` again. Do not try a different "
    "serialization format for an unchanged dataset; it will not improve the graph "
    "or add data. Return the final answer immediately unless you have identified "
    "one or more specific missing triples that require exactly one corrective "
    "tool call."
)
_TOOL_TRANSCRIPT_REMINDER_PREFIX: Final[str] = (
    "[rdflib_reasoning-tool-transcript] The previous tool-call turn was not executed."
)
_TOOL_TRANSCRIPT_REMINDER: Final[str] = (
    f"{_TOOL_TRANSCRIPT_REMINDER_PREFIX} Do not treat that tool call as completed. "
    "Either emit one corrected tool call now or, if the task is complete, provide "
    "the completed final answer immediately."
)
_REPEATED_SERIALIZE_REJECTION_MARKER: Final[str] = (
    "The dataset has not changed since the previous `serialize_dataset` call in this format."
)
_SERIALIZE_REUSE_INTENT_MARKERS: Final[tuple[str, ...]] = (
    "previous successful serialization",
    "return the previous successful serialization",
    "reuse the previous successful serialization",
)
_SERIALIZE_FINAL_ANSWER_TOKENS: Final[tuple[str, ...]] = (
    "turtle",
    "trig",
    "n3",
    "nt",
    "serialization",
    "representation",
)
_SERIALIZE_RESULT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"format=(?P<format>'[^']+'|\"[^\"]+\")\s+content=(?P<content>'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\")\s+default_graph_triple_count=",
    re.DOTALL,
)

# Circuit breaker: repeated tool calls in finalize-only (e.g. stuck on serialize_dataset)
# would otherwise loop until LangGraph hits recursion_limit.
_MAX_FINALIZE_ONLY_FORBIDDEN_TOOL_ROUNDS: Final[int] = 5


def _has_recent_error_tool_message(messages: Sequence[BaseMessage]) -> bool:
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


def _is_repeated_serialize_rejection(message: BaseMessage) -> bool:
    return (
        isinstance(message, ToolMessage)
        and getattr(message, "status", None) == "error"
        and _REPEATED_SERIALIZE_REJECTION_MARKER in str(message.content)
    )


def _has_any_tool_call(message: AIMessage) -> bool:
    return bool(message.tool_calls or message.invalid_tool_calls)


def _looks_like_serialization_reuse_intent(content: str) -> bool:
    normalized = content.casefold()
    return any(marker in normalized for marker in _SERIALIZE_REUSE_INTENT_MARKERS)


def _looks_like_serialization_final_answer_preamble(content: str) -> bool:
    normalized = content.casefold()
    return (
        "return" in normalized
        and "final answer" in normalized
        and any(token in normalized for token in _SERIALIZE_FINAL_ANSWER_TOKENS)
    )


def _extract_serialization_result_from_tool_message(
    message: BaseMessage,
) -> tuple[str, str] | None:
    if not (
        isinstance(message, ToolMessage)
        and getattr(message, "status", None) == "success"
        and getattr(message, "name", None) == "serialize_dataset"
    ):
        return None
    match = _SERIALIZE_RESULT_PATTERN.search(str(message.content))
    if match is None:
        return None
    try:
        format_name = literal_eval(match.group("format"))
        serialized_content = literal_eval(match.group("content"))
    except SyntaxError, ValueError:
        return None
    if not isinstance(format_name, str) or not isinstance(serialized_content, str):
        return None
    return format_name, serialized_content


def _completed_answer_from_serialization_result(format_name: str, content: str) -> str:
    stripped = content.rstrip("\n")
    return f"```text/{format_name}\n{stripped}\n```"


def _last_successful_serialization_answer(
    messages: Sequence[BaseMessage],
) -> str | None:
    for message in reversed(messages):
        extracted = _extract_serialization_result_from_tool_message(message)
        if extracted is None:
            continue
        format_name, serialized_content = extracted
        return _completed_answer_from_serialization_result(
            format_name, serialized_content
        )
    return None


def _latest_message_is_successful_serialize_tool_result(
    messages: Sequence[BaseMessage], message: BaseMessage
) -> bool:
    prior_message = _latest_surviving_message_before(messages, message)
    return (
        isinstance(prior_message, ToolMessage)
        and getattr(prior_message, "status", None) == "success"
        and getattr(prior_message, "name", None) == "serialize_dataset"
    )


def _repair_reminder_for_mode(mode: ContinuationMode) -> tuple[str, str]:
    if mode == "finalize_only":
        return _FINALIZE_REMINDER_PREFIX, _FINALIZE_REMINDER
    return _TOOL_TRANSCRIPT_REMINDER_PREFIX, _TOOL_TRANSCRIPT_REMINDER


def _latest_surviving_message_before(
    messages: Sequence[BaseMessage], message: BaseMessage
) -> BaseMessage | None:
    for candidate in reversed(messages):
        if candidate is message:
            continue
        return candidate
    return None


@dataclass
class ToolTranscriptRepairResult:
    """Outcome of normalizing tool-call / tool-result pairing for provider-bound messages."""

    messages: list[AnyMessage]
    removed_message_ids: list[str] = field(default_factory=list)
    reminder: HumanMessage | None = None
    """Human reminder appended to ``messages`` when the tail is not ``ToolMessage``."""

    system_reminder: str | None = None
    """Reminder merged into the system prompt when a human reminder would follow ``ToolMessage``."""

    issue_kinds: list[str] = field(default_factory=list)


def _repair_tool_transcript_messages(
    messages: Sequence[AnyMessage], mode: ContinuationMode
) -> ToolTranscriptRepairResult:
    """Remove offending messages by id until ``find_tool_transcript_issue`` is clean.

    Matches ``before_model`` reminder policy: at most one injected Human reminder per
    repair session, only when the working tail does not already carry that family.
    """
    original = list(messages)
    working = list(messages)
    removed_message_ids: list[str] = []
    issue_kinds: list[str] = []
    reminder: HumanMessage | None = None
    system_reminder: str | None = None
    reminder_prefix, reminder_text = _repair_reminder_for_mode(mode)
    max_iterations = len(working) + 5

    for _ in range(max_iterations):
        issue = find_tool_transcript_issue(working)
        if issue is None:
            break

        issue_kinds.append(issue.kind)
        message_id = getattr(issue.message, "id", None)
        if not isinstance(message_id, str):
            issue_details = (
                "Detected malformed tool-call transcript before model invocation, "
                f"but cannot repair it because the offending {issue.kind} message "
                "has no stable message id."
            )
            logger.error(
                "%s continuation_mode=%s recent_messages=%s action=raise",
                issue_details,
                mode,
                summarize_message_tail(original),
            )
            raise ValueError(issue_details)

        working = [m for m in working if getattr(m, "id", None) != message_id]
        if message_id not in removed_message_ids:
            removed_message_ids.append(message_id)
    else:
        msg = "Tool transcript repair exceeded iteration cap; possible heuristic regression."
        logger.error(
            "%s continuation_mode=%s recent_messages=%s action=raise",
            msg,
            mode,
            summarize_message_tail(original),
        )
        raise RuntimeError(msg)

    if removed_message_ids:
        has_matching_last_reminder = (
            bool(working)
            and isinstance(working[-1], HumanMessage)
            and str(working[-1].content).startswith(reminder_prefix)
        )
        if not has_matching_last_reminder and not has_recent_guard_reminder(
            working, reminder_prefix
        ):
            if working and isinstance(working[-1], ToolMessage):
                logger.debug(
                    "Deferring tool-transcript repair reminder to system prompt because "
                    "the repaired transcript ends with a ToolMessage (OpenAI rejects "
                    "user role immediately after tool role)"
                )
                system_reminder = reminder_text
            else:
                reminder = HumanMessage(content=reminder_text)
                working = [*working, reminder]

    if removed_message_ids:
        logger.warning(
            "Repairing malformed tool-call transcript; issues=%s continuation_mode=%s "
            "remove_message_ids=%s add_reminder=%s reminder_family=%s recent_messages=%s action=repair",
            issue_kinds,
            mode,
            removed_message_ids,
            reminder is not None or system_reminder is not None,
            reminder_prefix,
            summarize_message_tail(original),
        )

    return ToolTranscriptRepairResult(
        messages=working,
        removed_message_ids=removed_message_ids,
        reminder=reminder,
        system_reminder=system_reminder,
        issue_kinds=issue_kinds,
    )


def _model_request_after_tool_transcript_repair(
    request: ModelRequest[ContextT],
    repair: ToolTranscriptRepairResult,
    *,
    mode: ContinuationMode,
) -> ModelRequest[ContextT]:
    """Apply repaired messages and provider-safe reminder delivery for ``wrap_model_call``."""
    messages = repair.messages
    request = request.override(messages=messages)
    if repair.system_reminder:
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                repair.system_reminder,
            ),
        )
    if (
        mode == "finalize_only"
        and messages
        and isinstance(messages[-1], ToolMessage)
        and repair.system_reminder != _FINALIZE_REMINDER
    ):
        if _is_repeated_serialize_rejection(messages[-1]):
            logger.debug(
                "Appending finalize-only reminder to system prompt because the latest tool result "
                "rejected a repeated serialize_dataset request"
            )
        else:
            logger.debug(
                "Appending finalize-only reminder to system prompt because finalize-only mode cannot "
                "continue from a trailing tool result"
            )
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                _FINALIZE_REMINDER,
            ),
        )
    return request


def _coerce_to_model_response(result: Any) -> ModelResponse[Any]:
    if isinstance(result, ModelResponse):
        return result
    if isinstance(result, AIMessage):
        return ModelResponse(result=[result], structured_response=None)
    if isinstance(result, ExtendedModelResponse):
        return result.model_response
    return cast(ModelResponse[Any], result)


def _with_pending_tool_transcript_cleared(
    result: ModelResponse[ResponseT]
    | AIMessage
    | ExtendedModelResponse[ResponseT]
    | Any,
) -> ModelResponse[ResponseT] | AIMessage | ExtendedModelResponse[ResponseT] | Any:
    clear: Command[Any] = Command(update={_PENDING_TOOL_TRANSCRIPT_REMINDER_KEY: None})
    if isinstance(result, ExtendedModelResponse):
        prior = (
            dict(result.command.update)
            if result.command is not None and result.command.update
            else {}
        )
        prior.update(clear.update or {})
        return ExtendedModelResponse(
            model_response=result.model_response,
            command=Command(update=prior),
        )
    return ExtendedModelResponse(
        model_response=_coerce_to_model_response(result),
        command=clear,
    )


class ContinuationGuardMiddleware(AgentMiddleware[Any, ContextT, ResponseT]):
    """Optional post-model guard for single-run, completion-oriented agent harnesses."""

    state_schema = ContinuationGuardState

    @staticmethod
    def _merge_clear_finalize_only_tool_rounds(
        state: ContinuationGuardState,
        mode: ContinuationMode,
        out: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Reset the finalize-only tool loop counter when continuation leaves finalize_only."""
        if mode == "finalize_only":
            return out
        rounds_any = state.get("finalize_only_forbidden_tool_rounds", 0)
        if isinstance(rounds_any, int) and rounds_any > 0:
            merged = dict(out) if out else {}
            merged["finalize_only_forbidden_tool_rounds"] = 0
            return merged
        return out

    @override
    @hook_config(can_jump_to=["end"])
    def before_model(  # type: ignore[override]  # before_model's type hints are dated
        self, state: ContinuationGuardState, runtime: Any
    ) -> dict[str, Any] | None:
        del runtime
        mode = self._continuation_mode(state)
        if mode == "stop_now":
            return {"jump_to": "end"}
        messages = state.get("messages")
        if not isinstance(messages, list):
            return self._merge_clear_finalize_only_tool_rounds(state, mode, None)
        repair = _repair_tool_transcript_messages(messages, mode)
        updates_out: dict[str, Any] = {}
        if repair.removed_message_ids:
            # Avoid reducer-level duplicate-delete races when other middleware in
            # the same graph step removes the same transcript ids.
            logger.debug(
                "Suppressing before_model RemoveMessage updates for transcript repair; "
                "provider-bound request repair in wrap_model_call remains authoritative"
            )
            if repair.system_reminder is not None:
                updates_out[_PENDING_TOOL_TRANSCRIPT_REMINDER_KEY] = (
                    repair.system_reminder
                )
            elif repair.reminder is not None:
                updates_out[_PENDING_TOOL_TRANSCRIPT_REMINDER_KEY] = str(
                    repair.reminder.content
                )
        elif repair.reminder is not None:
            updates_out["messages"] = [repair.reminder]
        if repair.system_reminder is not None:
            updates_out[_PENDING_TOOL_TRANSCRIPT_REMINDER_KEY] = repair.system_reminder
        if updates_out:
            return self._merge_clear_finalize_only_tool_rounds(state, mode, updates_out)
        if mode != "finalize_only":
            return self._merge_clear_finalize_only_tool_rounds(state, mode, None)
        if (
            messages
            and isinstance(messages[-1], HumanMessage)
            and str(messages[-1].content).startswith(_FINALIZE_REMINDER_PREFIX)
        ) or has_recent_guard_reminder(messages, _FINALIZE_REMINDER_PREFIX):
            logger.debug(
                "Suppressing duplicate finalize-only reminder before model call"
            )
            return None

        if messages and isinstance(messages[-1], ToolMessage):
            logger.debug(
                "Skipping finalize-only HumanMessage before model call because the latest message is a tool result "
                "(finalize-only nudge for repeated serialize_dataset rejection is applied via system prompt in wrap_model_call)"
            )
            return None

        logger.debug(
            "Injecting finalize-only reminder before model call because continuation_mode=finalize_only"
        )
        return {"messages": [HumanMessage(content=_FINALIZE_REMINDER)]}

    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT] | AIMessage | ExtendedModelResponse[ResponseT] | Any:
        """Append finalize reminder to system prompt when the thread ends with a ToolMessage.

        OpenAI-compatible APIs reject a ``HumanMessage`` immediately after ``ToolMessage``;
        the repeated-``serialize_dataset`` case is handled here instead of ``before_model``.
        """
        mode = self._continuation_mode(request.state)
        pending_any = request.state.get(_PENDING_TOOL_TRANSCRIPT_REMINDER_KEY)
        pending: str | None = pending_any if isinstance(pending_any, str) else None
        repair = _repair_tool_transcript_messages(request.messages, mode)
        request = _model_request_after_tool_transcript_repair(
            request, repair, mode=mode
        )
        if pending is not None and repair.system_reminder is None:
            request = request.override(
                system_message=append_to_system_message(
                    request.system_message,
                    pending,
                ),
            )
        result = handler(request)
        if pending is not None:
            return _with_pending_tool_transcript_cleared(result)
        return result

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[
            [ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]
        ],
    ) -> ModelResponse[ResponseT] | AIMessage | ExtendedModelResponse[ResponseT] | Any:
        """Async variant of `wrap_model_call`."""
        mode = self._continuation_mode(request.state)
        pending_any = request.state.get(_PENDING_TOOL_TRANSCRIPT_REMINDER_KEY)
        pending: str | None = pending_any if isinstance(pending_any, str) else None
        repair = _repair_tool_transcript_messages(request.messages, mode)
        request = _model_request_after_tool_transcript_repair(
            request, repair, mode=mode
        )
        if pending is not None and repair.system_reminder is None:
            request = request.override(
                system_message=append_to_system_message(
                    request.system_message,
                    pending,
                ),
            )
        result = await handler(request)
        if pending is not None:
            return _with_pending_tool_transcript_cleared(result)
        return result

    @staticmethod
    def _continuation_mode(state: Any) -> ContinuationMode:
        mode = state.get("continuation_mode", "normal")
        if mode in {"normal", "finalize_only", "stop_now"}:
            return mode
        return "normal"

    @override
    @hook_config(can_jump_to=["end"])
    def after_model(  # type: ignore[override]  # after_model's type hints are dated
        self, state: ContinuationGuardState, runtime: Any
    ) -> dict[str, Any] | Command[Any] | None:
        del runtime
        messages = state.get("messages")
        if not isinstance(messages, list) or not messages:
            return None

        mode = self._continuation_mode(state)
        last_ai_message = latest_ai_message(messages)
        if last_ai_message is None:
            return None
        if mode == "finalize_only":
            if _has_any_tool_call(last_ai_message):
                rounds_any = state.get("finalize_only_forbidden_tool_rounds", 0)
                rounds = int(rounds_any) if isinstance(rounds_any, int) else 0
                rounds += 1
                updates: list[BaseMessage] = []
                if isinstance(last_ai_message.id, str):
                    updates.append(RemoveMessage(id=last_ai_message.id))
                prior_message = _latest_surviving_message_before(
                    messages, last_ai_message
                )
                if rounds >= _MAX_FINALIZE_ONLY_FORBIDDEN_TOOL_ROUNDS:
                    logger.warning(
                        "Stopping run after %s finalize-only model turns that still "
                        "emitted tool calls (circuit breaker; avoids LangGraph "
                        "recursion exhaustion from repeated serialize_dataset or similar)",
                        rounds,
                    )
                    # Remove the assistant tool-call turn so pending tools are not executed;
                    # otherwise DatasetMiddleware can emit continuation_mode updates that
                    # clobber stop_now in the same graph step.
                    # Use jump_to (not Command.goto) so Deep Agents / LangGraph accept the edge.
                    return {
                        "messages": updates,
                        "continuation_mode": "stop_now",
                        "finalize_only_forbidden_tool_rounds": 0,
                        "jump_to": "end",
                    }
                logger.debug(
                    "Rejecting tool calls in finalize-only mode; removing the offending assistant turn and re-prompting with final-answer-only reminder"
                )
                if isinstance(prior_message, ToolMessage):
                    logger.debug(
                        "Skipping finalize-only HumanMessage after removing forbidden tool call because the repaired transcript would otherwise end with tool -> user; wrap_model_call will supply provider-safe system guidance instead"
                    )
                else:
                    updates.append(HumanMessage(content=_FINALIZE_REMINDER))
                return Command(
                    update={
                        "messages": updates,
                        "finalize_only_forbidden_tool_rounds": rounds,
                    },
                    goto="model",
                )
        if last_ai_message.tool_calls or last_ai_message.invalid_tool_calls:
            return None

        content = (
            last_ai_message.text
            if isinstance(last_ai_message.text, str)
            else str(last_ai_message.content)
        )
        if not content:
            return None

        if mode == "finalize_only":
            if looks_like_completed_answer(content):
                logger.debug(
                    "Detected valid completed Turtle answer in finalize-only mode; ending run deterministically"
                )
                return {
                    "continuation_mode": "stop_now",
                    "jump_to": "end",
                    "finalize_only_forbidden_tool_rounds": 0,
                }
            if _looks_like_serialization_reuse_intent(content):
                recovered_answer = _last_successful_serialization_answer(messages)
                if recovered_answer is not None:
                    logger.debug(
                        "Recovered final answer from the last successful serialize_dataset tool result in finalize-only mode"
                    )
                    return {
                        "messages": [AIMessage(content=recovered_answer)],
                        "continuation_mode": "stop_now",
                        "jump_to": "end",
                        "finalize_only_forbidden_tool_rounds": 0,
                    }
            logger.debug(
                "Detected non-final assistant output in finalize-only mode; re-prompting with final-answer-only reminder"
            )
            return Command(
                update={"messages": [HumanMessage(content=_FINALIZE_REMINDER)]},
                goto="model",
            )

        if _looks_like_serialization_final_answer_preamble(
            content
        ) and _latest_message_is_successful_serialize_tool_result(
            messages, last_ai_message
        ):
            recovered_answer = _last_successful_serialization_answer(messages)
            if recovered_answer is not None:
                logger.debug(
                    "Recovered final answer from the immediately preceding successful serialize_dataset tool result"
                )
                return {
                    "messages": [AIMessage(content=recovered_answer)],
                    "continuation_mode": "stop_now",
                    "jump_to": "end",
                    "finalize_only_forbidden_tool_rounds": 0,
                }

        if looks_like_completed_answer(content):
            return None

        if looks_like_recovery_intent(content):
            if not _has_recent_error_tool_message(messages):
                return None
            if has_recent_guard_reminder(messages, _RECOVERY_REMINDER_PREFIX):
                return None
            logger.debug(
                "Detected unfinished recovery narration after tool rejection; re-prompting model"
            )
            return Command(
                update={"messages": [HumanMessage(content=_RECOVERY_REMINDER)]},
                goto="model",
            )

        if looks_like_plan_intent(content):
            if has_recent_guard_reminder(messages, _FINALIZE_REMINDER_PREFIX):
                return None
            if has_recent_guard_reminder(messages, _PLAN_REMINDER_PREFIX):
                logger.debug(
                    "Detected repeated unfinished planning output after a prior continuation reminder; escalating to final-answer-only reminder"
                )
                return Command(
                    update={"messages": [HumanMessage(content=_FINALIZE_REMINDER)]},
                    goto="model",
                )
            logger.debug(
                "Detected unfinished planning output without tool calls; re-prompting model"
            )
            return Command(
                update={"messages": [HumanMessage(content=_PLAN_REMINDER)]},
                goto="model",
            )

        return None


__all__ = ["ContinuationGuardMiddleware"]
