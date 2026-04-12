from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from rdflib_reasoning.middleware._message_heuristics import (
    find_tool_transcript_issue,
)


def test_find_tool_transcript_issue_detects_unresolved_tool_call() -> None:
    unresolved_ai = AIMessage(
        id="ai-call",
        content="Let me inspect the dataset.",
        tool_calls=[
            {
                "name": "list_triples",
                "args": {},
                "id": "call-list",
                "type": "tool_call",
            }
        ],
    )

    issue = find_tool_transcript_issue(
        [unresolved_ai, HumanMessage(content="Please continue.")]
    )

    assert issue is not None
    assert issue.kind == "unresolved_tool_call"
    assert issue.message is unresolved_ai


def test_find_tool_transcript_issue_detects_orphan_tool_response() -> None:
    orphan_tool_message = ToolMessage(
        content="Triples listed.",
        tool_call_id="call-list",
        status="success",
    )

    issue = find_tool_transcript_issue([orphan_tool_message])

    assert issue is not None
    assert issue.kind == "orphan_tool_response"
    assert issue.message is orphan_tool_message
