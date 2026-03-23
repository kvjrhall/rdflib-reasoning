from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from rdflib_reasoning.middleware.ministral_middleware import (
    MinistralPromptSuffixMiddleware,
)


def test_after_model_reprompts_on_unfinished_recovery_after_tool_error() -> None:
    middleware = MinistralPromptSuffixMiddleware()
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
    assert len(result.update["messages"]) == 1
    reminder = result.update["messages"][0]
    assert isinstance(reminder, HumanMessage)
    assert "Do not narrate that you will fix it" in str(reminder.content)


def test_after_model_does_not_interrupt_normal_final_content() -> None:
    middleware = MinistralPromptSuffixMiddleware()
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


def test_after_model_does_not_reprompt_when_tool_calls_already_present() -> None:
    middleware = MinistralPromptSuffixMiddleware()
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


def test_after_model_only_injects_recovery_reminder_once() -> None:
    middleware = MinistralPromptSuffixMiddleware()
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
