import asyncio
from collections.abc import Sequence
from typing import cast

import pytest
from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.types import Command
from rdflib_reasoning.middleware._message_heuristics import find_tool_transcript_issue
from rdflib_reasoning.middleware.continuation_guard_middleware import (
    ContinuationGuardMiddleware,
)


def _openai_user_role_after_tool_violation(messages: Sequence[BaseMessage]) -> bool:
    """True when a HumanMessage (``user``) immediately follows a ToolMessage (``tool``).

    OpenAI Chat Completions reject this ordering with
    ``BadRequestError: Unexpected role 'user' after role 'tool'``.
    """
    for index, message in enumerate(messages[:-1]):
        if isinstance(message, ToolMessage) and isinstance(
            messages[index + 1], HumanMessage
        ):
            return True
    return False


def _messages_after_normal_mode_tool_transcript_repair_scenario() -> tuple[
    list[BaseMessage], str | None
]:
    """Build the notebook-like tail; return inner handler messages and system prompt text."""
    middleware = ContinuationGuardMiddleware()
    request = ModelRequest(
        model=None,
        messages=[
            AIMessage(
                id="ai-plan",
                content="Planning the RDF extraction.",
                tool_calls=[],
            ),
            HumanMessage(
                content=(
                    "[rdflib_reasoning-continuation] Do not stop at an unfinished plan. "
                    "Either emit the next tool call now or return the completed final answer "
                    "immediately."
                )
            ),
            AIMessage(
                id="ai-first-tool",
                content="Calling add_triples.",
                tool_calls=[
                    {
                        "name": "add_triples",
                        "args": {"triples": []},
                        "id": "call-add-1",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(
                id="tool-err-1",
                content="Whitelist violation for rdf:type.",
                tool_call_id="call-add-1",
                status="error",
            ),
            AIMessage(
                id="ai-retry-tools",
                content="Retrying with corrected triples.",
                tool_calls=[
                    {
                        "name": "add_triples",
                        "args": {"triples": []},
                        "id": "call-add-2",
                        "type": "tool_call",
                    }
                ],
            ),
        ],
        system_message=SystemMessage(content="Base system prompt"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"continuation_mode": "normal"},
        runtime=None,
        model_settings={},
    )
    captured: dict[str, object] = {}

    def handler(next_request: ModelRequest) -> str:
        captured["messages"] = list(next_request.messages)
        sm = next_request.system_message
        captured["system_text"] = sm.text if sm is not None else None
        return "ok"

    middleware.wrap_model_call(request, handler)
    return cast(list[BaseMessage], captured["messages"]), cast(
        str | None, captured.get("system_text")
    )


_REPEATED_SERIALIZE_TOOL_MESSAGE = ToolMessage(
    content=(
        "The dataset has not changed since the previous `serialize_dataset` "
        "call in this format. Re-serializing will not reformat or improve "
        "the graph. Use the previous successful serialization as your final "
        "answer if it already reflects the graph you intend to present. Do "
        "not call `serialize_dataset` again until you have changed the "
        "dataset. Return your final answer now, or make one or more "
        "specific dataset changes before any further serialization."
    ),
    tool_call_id="call-serialize",
    status="error",
)
_SERIALIZE_TOOL_CALL_MESSAGE = AIMessage(
    id="ai-serialize-call",
    content="Let me serialize the dataset now.",
    tool_calls=[
        {
            "name": "serialize_dataset",
            "args": {"format": "turtle"},
            "id": "call-serialize",
            "type": "tool_call",
        }
    ],
)
_LIST_TRIPLES_TOOL_CALL_MESSAGE = AIMessage(
    id="ai-list-call",
    content="Let me inspect the current graph.",
    tool_calls=[
        {
            "name": "list_triples",
            "args": {},
            "id": "call-1",
            "type": "tool_call",
        }
    ],
)
_ERROR_TOOL_CALL_MESSAGE = AIMessage(
    id="ai-error-call",
    content="Let me inspect the graph again.",
    tool_calls=[
        {
            "name": "list_triples",
            "args": {},
            "id": "call-x",
            "type": "tool_call",
        }
    ],
)


def test_after_model_reprompts_on_unfinished_recovery_after_tool_error() -> None:
    middleware = ContinuationGuardMiddleware()
    state = {
        "messages": [
            ToolMessage(
                content="Validation failed",
                tool_call_id="call-1",
                status="error",
            ),
            AIMessage(
                content=(
                    "I intended to add the missing triples. Let me correct this by "
                    "adding the remaining relationships."
                )
            ),
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, Command)
    assert result.goto == "model"
    reminder = result.update["messages"][0]
    assert isinstance(reminder, HumanMessage)
    assert "Do not narrate that you will fix it" in str(reminder.content)


def test_after_model_does_not_interrupt_normal_final_content() -> None:
    middleware = ContinuationGuardMiddleware()
    state = {
        "messages": [
            ToolMessage(
                content="Triples added",
                tool_call_id="call-1",
                status="success",
            ),
            AIMessage(content="The RDF graph has been updated successfully."),
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert result is None


def test_before_model_injects_provider_safe_finalize_message_in_finalize_only_mode() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [
            AIMessage(content="I will inspect once more before returning the answer."),
        ],
    }

    result = middleware.before_model(state, runtime=None)

    assert result is not None
    reminder = result["messages"][0]
    assert isinstance(reminder, HumanMessage)
    assert "Return the completed final answer now" in str(reminder.content)


def test_before_model_does_not_inject_finalize_message_immediately_after_tool_result() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [
            _LIST_TRIPLES_TOOL_CALL_MESSAGE,
            ToolMessage(
                content="Triples removed from the default graph.",
                tool_call_id="call-1",
                status="success",
            ),
        ],
    }

    result = middleware.before_model(state, runtime=None)

    assert result is None


def test_before_model_does_not_inject_human_message_after_repeated_serialize_rejection() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [_SERIALIZE_TOOL_CALL_MESSAGE, _REPEATED_SERIALIZE_TOOL_MESSAGE],
    }

    result = middleware.before_model(state, runtime=None)

    assert result is None


def test_wrap_model_call_appends_finalize_system_prompt_after_repeated_serialize_rejection() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    request = ModelRequest(
        model=None,
        messages=[_SERIALIZE_TOOL_CALL_MESSAGE, _REPEATED_SERIALIZE_TOOL_MESSAGE],
        system_message=SystemMessage(content="Base system prompt"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"continuation_mode": "finalize_only"},
        runtime=None,
        model_settings={},
    )
    captured: dict = {}

    def handler(next_request: ModelRequest) -> str:
        captured["system_message"] = next_request.system_message
        return "ok"

    result = middleware.wrap_model_call(request, handler)

    assert result == "ok"
    assert captured["system_message"] is not None
    assert "reuse that Turtle directly as your final answer" in str(
        captured["system_message"].content
    )
    assert "Do not try a different serialization format" in str(
        captured["system_message"].content
    )


def test_awrap_model_call_appends_finalize_system_prompt_after_repeated_serialize_rejection_async() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    request = ModelRequest(
        model=None,
        messages=[_SERIALIZE_TOOL_CALL_MESSAGE, _REPEATED_SERIALIZE_TOOL_MESSAGE],
        system_message=SystemMessage(content="Base system prompt"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"continuation_mode": "finalize_only"},
        runtime=None,
        model_settings={},
    )
    captured: dict = {}

    async def handler(next_request: ModelRequest) -> str:
        captured["system_message"] = next_request.system_message
        return "ok"

    result = asyncio.run(middleware.awrap_model_call(request, handler))

    assert result == "ok"
    assert "reuse that Turtle directly as your final answer" in str(
        captured["system_message"].content
    )
    assert "Do not try a different serialization format" in str(
        captured["system_message"].content
    )


def test_wrap_model_call_does_not_append_finalize_when_continuation_mode_is_normal() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    request = ModelRequest(
        model=None,
        messages=[_SERIALIZE_TOOL_CALL_MESSAGE, _REPEATED_SERIALIZE_TOOL_MESSAGE],
        system_message=SystemMessage(content="Base system prompt"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"continuation_mode": "normal"},
        runtime=None,
        model_settings={},
    )
    captured: dict = {}

    def handler(next_request: ModelRequest) -> str:
        captured["system_message"] = next_request.system_message
        return "ok"

    middleware.wrap_model_call(request, handler)

    assert "reuse that Turtle directly as your final answer" not in str(
        captured["system_message"].content
    )


def test_wrap_model_call_appends_finalize_for_any_tool_result_in_finalize_only_mode() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    request = ModelRequest(
        model=None,
        messages=[
            _ERROR_TOOL_CALL_MESSAGE,
            ToolMessage(
                content="Some other tool error",
                tool_call_id="call-x",
                status="error",
            ),
        ],
        system_message=SystemMessage(content="Base system prompt"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"continuation_mode": "finalize_only"},
        runtime=None,
        model_settings={},
    )
    captured: dict = {}

    def handler(next_request: ModelRequest) -> str:
        captured["system_message"] = next_request.system_message
        return "ok"

    middleware.wrap_model_call(request, handler)

    assert "reuse that Turtle directly as your final answer" in str(
        captured["system_message"].content
    )


def test_before_model_does_not_duplicate_finalize_message_when_already_last_message() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [
            HumanMessage(
                content=(
                    "[rdflib_reasoning-finalize] Return the completed final answer now."
                )
            )
        ],
    }

    result = middleware.before_model(state, runtime=None)

    assert result is None


def test_after_model_does_not_reprompt_when_tool_calls_already_present() -> None:
    middleware = ContinuationGuardMiddleware()
    state = {
        "messages": [
            ToolMessage(
                content="Validation failed",
                tool_call_id="call-1",
                status="error",
            ),
            AIMessage(
                content="Let me correct this now.",
                tool_calls=[
                    {
                        "name": "add_triples",
                        "args": {"triples": []},
                        "id": "tool-1",
                        "type": "tool_call",
                    }
                ],
            ),
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert result is None


def test_after_model_does_not_reprompt_when_invalid_tool_calls_are_present() -> None:
    middleware = ContinuationGuardMiddleware()
    state = {
        "messages": [
            AIMessage(
                content="Let me add the remaining triples now.",
                invalid_tool_calls=[
                    {
                        "name": "add_triples",
                        "args": '{"triples": [{"subject": "<urn:ex:John>"}',
                        "id": "tool-1",
                        "type": "invalid_tool_call",
                        "error": "JSONDecodeError",
                    }
                ],
            ),
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert result is None


def test_after_model_only_injects_recovery_reminder_once() -> None:
    middleware = ContinuationGuardMiddleware()
    state = {
        "messages": [
            ToolMessage(
                content="Validation failed",
                tool_call_id="call-1",
                status="error",
            ),
            HumanMessage(
                content=(
                    "[rdflib_reasoning-recovery] A tool call just failed. Do not narrate that "
                    "you will fix it."
                )
            ),
            AIMessage(content="I will fix the triples and retry."),
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert result is None


def test_after_model_reprompts_on_plan_only_response() -> None:
    middleware = ContinuationGuardMiddleware()
    state = {
        "messages": [
            AIMessage(
                content=(
                    "I will help you represent the subject matter as RDF. "
                    "Here's how I will proceed:\nStep-by-step plan:\n1. Define classes."
                )
            )
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, Command)
    assert result.goto == "model"
    reminder = result.update["messages"][0]
    assert isinstance(reminder, HumanMessage)
    assert "Do not stop at an unfinished plan" in str(reminder.content)


def test_after_model_ends_deterministically_when_valid_completed_turtle_answer_present_in_finalize_only_mode() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [
            AIMessage(
                content="```text/turtle\n@prefix ex: <urn:ex:> .\nex:John a ex:Person .\n```"
            )
        ],
    }

    result = middleware.after_model(state, runtime=None)

    assert result == {
        "continuation_mode": "stop_now",
        "jump_to": "end",
        "finalize_only_forbidden_tool_rounds": 0,
    }


def test_after_model_recovers_previous_successful_serialization_in_finalize_only_mode() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [
            ToolMessage(
                content=(
                    "format='turtle' content='@prefix ex: <urn:ex:> .\\n\\nex:John a ex:Person .\\n' "
                    "default_graph_triple_count=1 is_empty=False "
                    "message='Serialized the current default graph containing 1 triples.'"
                ),
                name="serialize_dataset",
                tool_call_id="tool-serialize-success",
                status="success",
            ),
            ToolMessage(
                content=(
                    "The dataset has not changed since the previous `serialize_dataset` "
                    "call in this format. Re-serializing will not reformat or improve "
                    "the graph. Use the previous successful serialization as your final "
                    "answer if it already reflects the graph you intend to present."
                ),
                name="serialize_dataset",
                tool_call_id="tool-serialize-repeat",
                status="error",
            ),
            AIMessage(
                content=(
                    "I will now return the previous successful serialization as the "
                    "final answer. The dataset accurately represents all the explicit "
                    "claims from the source text:"
                )
            ),
        ],
    }

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, dict)
    assert result["continuation_mode"] == "stop_now"
    assert result["jump_to"] == "end"
    assert result["finalize_only_forbidden_tool_rounds"] == 0
    recovered = result["messages"][0]
    assert isinstance(recovered, AIMessage)
    assert "```text/turtle" in str(recovered.content)
    assert "ex:John a ex:Person ." in str(recovered.content)


def test_after_model_recovers_immediately_preceding_successful_serialization_in_normal_mode() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "messages": [
            ToolMessage(
                content=(
                    "format='turtle' content='@prefix ex: <urn:ex:> .\\n\\nex:John a ex:Person .\\n' "
                    "default_graph_triple_count=1 is_empty=False "
                    "message='Serialized the current default graph containing 1 triples.'"
                ),
                name="serialize_dataset",
                tool_call_id="tool-serialize-success",
                status="success",
            ),
            AIMessage(
                content=(
                    "I will now return the Turtle representation as the final answer. "
                    "The representation accurately captures all the explicit claims in "
                    "the source text:"
                )
            ),
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, dict)
    assert result["continuation_mode"] == "stop_now"
    assert result["jump_to"] == "end"
    assert result["finalize_only_forbidden_tool_rounds"] == 0
    recovered = result["messages"][0]
    assert isinstance(recovered, AIMessage)
    assert "```text/turtle" in str(recovered.content)
    assert "ex:John a ex:Person ." in str(recovered.content)


def test_after_model_only_injects_planning_reminder_once() -> None:
    middleware = ContinuationGuardMiddleware()
    state = {
        "messages": [
            HumanMessage(
                content=(
                    "[rdflib_reasoning-continuation] Do not stop at an unfinished plan."
                )
            ),
            AIMessage(
                content=(
                    "Here's how I will proceed next. Step-by-step plan:\n"
                    "1. Add the remaining triples."
                )
            ),
        ]
    }

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, Command)
    assert result.goto == "model"
    reminder = result.update["messages"][0]
    assert isinstance(reminder, HumanMessage)
    assert "Return the completed final answer now" in str(reminder.content)


def test_after_model_reprompts_with_finalize_guidance_for_nonfinal_output_in_finalize_only_mode() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [
            AIMessage(content="Next I will inspect the dataset one more time."),
        ],
    }

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, Command)
    assert result.goto == "model"
    reminder = result.update["messages"][0]
    assert isinstance(reminder, HumanMessage)
    assert "Return the completed final answer now" in str(reminder.content)


def test_after_model_reprompts_when_serialize_tool_call_appears_in_finalize_only_mode() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [
            AIMessage(
                id="ai-serialize",
                content="Let me serialize in TriG instead.",
                tool_calls=[
                    {
                        "name": "serialize_dataset",
                        "args": {"format": "trig"},
                        "id": "tool-serialize",
                        "type": "tool_call",
                    }
                ],
            ),
        ],
    }

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, Command)
    assert result.goto == "model"
    assert isinstance(result.update["messages"][0], RemoveMessage)
    reminder = result.update["messages"][1]
    assert isinstance(reminder, HumanMessage)
    assert "Do not try a different serialization format" in str(reminder.content)


def test_after_model_reprompts_when_invalid_serialize_tool_call_appears_in_finalize_only_mode() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [
            AIMessage(
                id="ai-invalid-serialize",
                content="Let me serialize one more time.",
                invalid_tool_calls=[
                    {
                        "name": "serialize_dataset",
                        "args": '{"format": "turtle"',
                        "id": "tool-serialize",
                        "type": "invalid_tool_call",
                        "error": "JSONDecodeError",
                    }
                ],
            ),
        ],
    }

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, Command)
    assert result.goto == "model"
    assert isinstance(result.update["messages"][0], RemoveMessage)
    reminder = result.update["messages"][1]
    assert isinstance(reminder, HumanMessage)
    assert "Do not try a different serialization format" in str(reminder.content)


def test_after_model_reprompts_when_non_serialize_tool_call_appears_in_finalize_only_mode() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [
            AIMessage(
                id="ai-list",
                content="Let me inspect the dataset one more time.",
                tool_calls=[
                    {
                        "name": "list_triples",
                        "args": {},
                        "id": "tool-list",
                        "type": "tool_call",
                    }
                ],
            ),
        ],
    }

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, Command)
    assert result.goto == "model"
    assert isinstance(result.update["messages"][0], RemoveMessage)
    reminder = result.update["messages"][1]
    assert isinstance(reminder, HumanMessage)
    assert "Return the completed final answer now" in str(reminder.content)


def test_after_model_removes_forbidden_tool_call_without_human_message_when_prior_message_is_tool() -> (
    None
):
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [
            _SERIALIZE_TOOL_CALL_MESSAGE,
            _REPEATED_SERIALIZE_TOOL_MESSAGE,
            AIMessage(
                id="ai-list-after-tool",
                content="Let me inspect the dataset one more time.",
                tool_calls=[
                    {
                        "name": "list_triples",
                        "args": {},
                        "id": "tool-list",
                        "type": "tool_call",
                    }
                ],
            ),
        ],
    }

    result = middleware.after_model(state, runtime=None)

    assert isinstance(result, Command)
    assert result.goto == "model"
    assert len(result.update["messages"]) == 1
    assert isinstance(result.update["messages"][0], RemoveMessage)
    assert result.update["messages"][0].id == "ai-list-after-tool"


def test_before_model_repairs_unresolved_tool_call_transcript_before_provider_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "finalize_only",
        "messages": [
            AIMessage(
                id="ai-serialize",
                content="Let me serialize in TriG instead.",
                tool_calls=[
                    {
                        "name": "serialize_dataset",
                        "args": {"format": "trig"},
                        "id": "tool-serialize",
                        "type": "tool_call",
                    }
                ],
            ),
            HumanMessage(
                content=(
                    "[rdflib_reasoning-finalize] Return the completed final answer now."
                )
            ),
        ],
    }

    result = middleware.before_model(state, runtime=None)

    assert result is None
    assert "unresolved_tool_call" in caplog.text
    assert "continuation_mode=finalize_only" in caplog.text
    assert "remove_message_ids=" in caplog.text
    assert "ai-serialize" in caplog.text
    assert "action=repair" in caplog.text


def test_wrap_model_call_repairs_malformed_tool_transcript(
    caplog: pytest.LogCaptureFixture,
) -> None:
    middleware = ContinuationGuardMiddleware()
    request = ModelRequest(
        model=None,
        messages=[
            AIMessage(
                id="ai-list",
                content="Let me inspect the dataset one more time.",
                tool_calls=[
                    {
                        "name": "list_triples",
                        "args": {},
                        "id": "tool-list",
                        "type": "tool_call",
                    }
                ],
            ),
            HumanMessage(content="Please continue."),
        ],
        system_message=SystemMessage(content="Base system prompt"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"continuation_mode": "normal"},
        runtime=None,
        model_settings={},
    )
    captured: dict[str, object] = {}

    def handler(next_request: ModelRequest) -> str:
        captured["messages"] = list(next_request.messages)
        return "ok"

    result = middleware.wrap_model_call(request, handler)

    assert result == "ok"
    assert "messages" in captured
    assert find_tool_transcript_issue(cast(list, captured["messages"])) is None
    assert "action=repair" in caplog.text
    assert "continuation_mode=normal" in caplog.text


def test_wrap_model_call_tool_transcript_repair_defers_nudge_to_system_when_tail_is_tool(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """After repair, transcript is clean, tail is ``ToolMessage``, nudge is not ``HumanMessage``."""
    out, system_text = _messages_after_normal_mode_tool_transcript_repair_scenario()
    assert find_tool_transcript_issue(out) is None
    assert not _openai_user_role_after_tool_violation(out)
    assert isinstance(out[-1], ToolMessage)
    assert system_text is not None
    assert "[rdflib_reasoning-tool-transcript]" in system_text
    assert "action=repair" in caplog.text


def test_wrap_model_call_tool_transcript_repair_must_not_place_user_after_tool_openai_constraint(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Framework regression for provider ordering (matches demo-dataset-middleware failure).

    After a tool error, the model may emit a new assistant turn with tool calls before
    tools run. ``find_tool_transcript_issue`` flags the trailing assistant message;
    repair removes it. When the repaired transcript ends with ``ToolMessage``, the
    reminder must not be a trailing ``HumanMessage`` (OpenAI rejects ``user`` after ``tool``).
    """
    out, _system_text = _messages_after_normal_mode_tool_transcript_repair_scenario()
    assert "action=repair" in caplog.text
    assert not _openai_user_role_after_tool_violation(out), (
        "OpenAI Chat Completions reject HumanMessage (user) immediately after ToolMessage "
        f"(tool); message tail would trigger 400. messages={[type(m).__name__ for m in out]}"
    )


def test_wrap_model_call_tool_transcript_repair_places_reminder_after_final_shape_not_intermediate(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Regression: multi-iteration repair must decide reminder target from final transcript."""
    middleware = ContinuationGuardMiddleware()
    request = ModelRequest(
        model=None,
        messages=[
            ToolMessage(
                id="orphan-first",
                content="orphan tool result before any assistant tool-call turn",
                tool_call_id="orphan-call",
            ),
            AIMessage(
                id="ai-good",
                content="Calling list_triples.",
                tool_calls=[
                    {
                        "name": "list_triples",
                        "args": {},
                        "id": "call-good",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(
                id="tool-good",
                content="ok",
                tool_call_id="call-good",
                status="success",
            ),
            AIMessage(
                id="ai-unresolved-tail",
                content="Calling list_triples again.",
                tool_calls=[
                    {
                        "name": "list_triples",
                        "args": {},
                        "id": "call-unresolved",
                        "type": "tool_call",
                    }
                ],
            ),
        ],
        system_message=SystemMessage(content="Base system prompt"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"continuation_mode": "normal"},
        runtime=None,
        model_settings={},
    )
    captured: dict[str, object] = {}

    def handler(next_request: ModelRequest) -> str:
        captured["messages"] = list(next_request.messages)
        sm = next_request.system_message
        captured["system_text"] = sm.text if sm is not None else None
        return "ok"

    result = middleware.wrap_model_call(request, handler)

    assert result == "ok"
    out = cast(list[BaseMessage], captured["messages"])
    system_text = cast(str | None, captured["system_text"])
    assert find_tool_transcript_issue(out) is None
    assert not _openai_user_role_after_tool_violation(out)
    assert isinstance(out[-1], ToolMessage)
    assert system_text is not None
    assert "[rdflib_reasoning-tool-transcript]" in system_text
    assert "orphan_tool_response" in caplog.text
    assert "unresolved_tool_call" in caplog.text
    assert "action=repair" in caplog.text


def test_wrap_model_call_raises_when_offending_message_lacks_stable_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    middleware = ContinuationGuardMiddleware()
    request = ModelRequest(
        model=None,
        messages=[
            AIMessage(
                content="No stable id on this assistant turn.",
                tool_calls=[
                    {
                        "name": "list_triples",
                        "args": {},
                        "id": "tool-list",
                        "type": "tool_call",
                    }
                ],
            ),
            HumanMessage(content="Please continue."),
        ],
        system_message=SystemMessage(content="Base system prompt"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"continuation_mode": "normal"},
        runtime=None,
        model_settings={},
    )

    def handler(next_request: ModelRequest) -> str:
        raise AssertionError("handler should not be called when repair is impossible")

    with pytest.raises(ValueError, match="no stable message id"):
        middleware.wrap_model_call(request, handler)
    assert "action=raise" in caplog.text


def test_before_model_raises_when_offending_message_lacks_stable_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "normal",
        "messages": [
            AIMessage(
                content="No stable id on this assistant turn.",
                tool_calls=[
                    {
                        "name": "list_triples",
                        "args": {},
                        "id": "tool-list",
                        "type": "tool_call",
                    }
                ],
            ),
            HumanMessage(content="Please continue."),
        ],
    }

    with pytest.raises(ValueError, match="no stable message id"):
        middleware.before_model(state, runtime=None)
    assert "action=raise" in caplog.text


def test_wrap_model_call_repairs_two_orphan_tool_messages_in_one_session(
    caplog: pytest.LogCaptureFixture,
) -> None:
    middleware = ContinuationGuardMiddleware()
    request = ModelRequest(
        model=None,
        messages=[
            ToolMessage(
                id="orphan-a",
                content="orphan",
                tool_call_id="call-a",
            ),
            ToolMessage(
                id="orphan-b",
                content="orphan",
                tool_call_id="call-b",
            ),
        ],
        system_message=SystemMessage(content="Base system prompt"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"continuation_mode": "normal"},
        runtime=None,
        model_settings={},
    )
    captured: dict[str, object] = {}

    def handler(next_request: ModelRequest) -> str:
        captured["messages"] = list(next_request.messages)
        return "ok"

    middleware.wrap_model_call(request, handler)

    out_messages = captured["messages"]
    assert isinstance(out_messages, list)
    assert not any(isinstance(m, ToolMessage) for m in out_messages)
    assert find_tool_transcript_issue(out_messages) is None
    assert "orphan_tool_response" in caplog.text
    assert "remove_message_ids=" in caplog.text
    assert "action=repair" in caplog.text


def test_before_model_ends_immediately_when_continuation_mode_is_stop_now() -> None:
    middleware = ContinuationGuardMiddleware()
    state = {
        "continuation_mode": "stop_now",
        "messages": [
            AIMessage(
                content="```text/turtle\n@prefix ex: <urn:ex:> .\nex:John a ex:Person .\n```"
            )
        ],
    }

    result = middleware.before_model(state, runtime=None)

    assert result == {"jump_to": "end"}
