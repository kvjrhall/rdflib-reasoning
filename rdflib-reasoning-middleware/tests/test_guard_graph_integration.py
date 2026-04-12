import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from rdflib import Namespace
from rdflib_reasoning.middleware import (
    DatasetMiddleware,
    DatasetMiddlewareConfig,
    VocabularyConfiguration,
    VocabularyDeclaration,
)
from rdflib_reasoning.middleware.continuation_guard_middleware import (
    ContinuationGuardMiddleware,
)
from rdflib_reasoning.middleware.ministral_middleware import (
    MinistralPromptSuffixMiddleware,
)

sys.path.append(str(Path(__file__).resolve().parent))

from _agent_test_utils import (  # type: ignore[import-not-found]
    ToolFriendlyFakeMessagesListChatModel,
    collect_update_chunks,
    create_agent_graph,
    create_deep_agent_graph,
)

GraphFactory = Callable[..., Any]

EX_NS = Namespace("urn:test:")
GRAPH_FACTORIES: tuple[tuple[str, GraphFactory], ...] = (
    ("agent", create_agent_graph),
    ("deep_agent", create_deep_agent_graph),
)


def _combined_guard_middleware() -> list[Any]:
    vocabulary_context = VocabularyConfiguration.bundled_plus(
        VocabularyDeclaration(prefix="ex", namespace=EX_NS)
    ).build_context()
    return [
        DatasetMiddleware(
            DatasetMiddlewareConfig(vocabulary_context=vocabulary_context)
        ),
        MinistralPromptSuffixMiddleware(),
        ContinuationGuardMiddleware(),
    ]


def _tool_messages(chunks: list[dict[str, Any]]) -> list[ToolMessage]:
    messages: list[ToolMessage] = []
    for chunk in chunks:
        for update in chunk.values():
            if not isinstance(update, dict):
                continue
            chunk_messages = update.get("messages")
            if not isinstance(chunk_messages, list):
                continue
            messages.extend(
                message
                for message in chunk_messages
                if isinstance(message, ToolMessage)
            )
    return messages


@pytest.mark.parametrize(("factory_name", "graph_factory"), GRAPH_FACTORIES)
def test_graph_guards_allow_plan_reprompt_then_valid_tool_call(
    factory_name: str, graph_factory: GraphFactory
) -> None:
    del factory_name
    model = ToolFriendlyFakeMessagesListChatModel(
        responses=[
            AIMessage(content="I will now construct the RDF graph."),
            AIMessage(
                id="ai-add",
                content="Adding triples now.",
                tool_calls=[
                    {
                        "name": "add_triples",
                        "args": {
                            "triples": [
                                {
                                    "subject": "<urn:test:s>",
                                    "predicate": "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>",
                                    "object": "<http://www.w3.org/2000/01/rdf-schema#Class>",
                                }
                            ]
                        },
                        "id": "call-add",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                content=(
                    "```text/turtle\n"
                    "@prefix ex: <urn:test:> .\n"
                    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
                    "ex:s a rdfs:Class .\n"
                    "```"
                )
            ),
        ]
    )
    agent = graph_factory(model=model, middleware=_combined_guard_middleware())

    chunks = collect_update_chunks(
        agent,
        messages=[{"role": "user", "content": "Represent the source text as RDF."}],
        recursion_limit=30,
    )

    tool_messages = _tool_messages(chunks)
    assert any(message.name == "add_triples" for message in tool_messages)
    assert any("ContinuationGuardMiddleware.after_model" in chunk for chunk in chunks)
    assert not any(
        isinstance(message, ToolMessage) and message.name == "list_triples"
        for message in tool_messages
    )


@pytest.mark.parametrize(("factory_name", "graph_factory"), GRAPH_FACTORIES)
def test_graph_guards_handle_repeated_serialize_finalize_only_flow(
    factory_name: str, graph_factory: GraphFactory
) -> None:
    del factory_name
    model = ToolFriendlyFakeMessagesListChatModel(
        responses=[
            AIMessage(
                id="ai-add",
                content="Adding triples now.",
                tool_calls=[
                    {
                        "name": "add_triples",
                        "args": {
                            "triples": [
                                {
                                    "subject": "<urn:test:s>",
                                    "predicate": "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>",
                                    "object": "<http://www.w3.org/2000/01/rdf-schema#Class>",
                                }
                            ]
                        },
                        "id": "call-add",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                id="ai-serialize-1",
                content="Serialize the dataset.",
                tool_calls=[
                    {
                        "name": "serialize_dataset",
                        "args": {"format": "turtle"},
                        "id": "call-serialize-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                id="ai-serialize-2",
                content="Serialize the dataset again.",
                tool_calls=[
                    {
                        "name": "serialize_dataset",
                        "args": {"format": "turtle"},
                        "id": "call-serialize-2",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                id="ai-list-after-rejection",
                content="Let me inspect the dataset one more time.",
                tool_calls=[
                    {
                        "name": "list_triples",
                        "args": {},
                        "id": "call-list",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                content=(
                    "```text/turtle\n"
                    "@prefix ex: <urn:test:> .\n"
                    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
                    "ex:s a rdfs:Class .\n"
                    "```"
                )
            ),
        ]
    )
    agent = graph_factory(model=model, middleware=_combined_guard_middleware())

    chunks = collect_update_chunks(
        agent,
        messages=[{"role": "user", "content": "Represent the source text as RDF."}],
        recursion_limit=40,
    )

    tool_messages = _tool_messages(chunks)
    assert any(
        message.name == "serialize_dataset"
        and getattr(message, "status", None) == "error"
        and "The dataset has not changed since the previous `serialize_dataset` call in this format."
        in str(message.content)
        for message in tool_messages
    )
    assert not any(message.name == "list_triples" for message in tool_messages)
    assert any(
        isinstance(chunk.get("ContinuationGuardMiddleware.after_model"), dict)
        and chunk["ContinuationGuardMiddleware.after_model"].get("jump_to") == "end"
        for chunk in chunks
        if "ContinuationGuardMiddleware.after_model" in chunk
    )


@pytest.mark.parametrize(("factory_name", "graph_factory"), GRAPH_FACTORIES)
def test_graph_repairs_malformed_unresolved_tool_transcript_before_provider_call(
    factory_name: str,
    graph_factory: GraphFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    model = ToolFriendlyFakeMessagesListChatModel(
        responses=[AIMessage(content="Repaired path reached a normal final answer.")]
    )
    agent = graph_factory(model=model, middleware=[ContinuationGuardMiddleware()])

    chunks = collect_update_chunks(
        agent,
        messages=[
            AIMessage(
                content="Let me inspect the dataset one more time.",
                tool_calls=[
                    {
                        "name": "list_triples",
                        "args": {},
                        "id": "call-list",
                        "type": "tool_call",
                    }
                ],
            ),
            HumanMessage(content="Please continue."),
        ],
        recursion_limit=10,
    )

    assert chunks
    if factory_name == "agent":
        assert "continuation_mode=normal" in caplog.text
        assert "action=repair" in caplog.text
    else:
        # create_deep_agent runs PatchToolCallsMiddleware, which cancels dangling tool
        # calls before ContinuationGuardMiddleware.before_model, so caplog may not
        # record a transcript repair even though the run reaches the model successfully.
        assert any(
            "Repaired path reached a normal final answer." in str(chunk)
            for chunk in chunks
        )


def test_deep_agent_graph_stops_infinite_finalize_only_serialize_loop() -> None:
    """Regression: finalize_only + repeated forbidden tool calls must not recurse to graph limit.

    When the model ignores finalize-only discipline and keeps emitting ``serialize_dataset``,
    ``ContinuationGuardMiddleware`` previously removed the assistant turn and re-prompted
    indefinitely until ``recursion_limit`` (notebook: apparent hang / KeyboardInterrupt).
    """
    pre = [
        AIMessage(
            id="ai-add",
            content="Adding triples now.",
            tool_calls=[
                {
                    "name": "add_triples",
                    "args": {
                        "triples": [
                            {
                                "subject": "<urn:test:s>",
                                "predicate": "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>",
                                "object": "<http://www.w3.org/2000/01/rdf-schema#Class>",
                            }
                        ]
                    },
                    "id": "call-add",
                    "type": "tool_call",
                }
            ],
        ),
        AIMessage(
            id="ai-serialize-1",
            content="Serialize the dataset.",
            tool_calls=[
                {
                    "name": "serialize_dataset",
                    "args": {"format": "turtle"},
                    "id": "call-serialize-1",
                    "type": "tool_call",
                }
            ],
        ),
        AIMessage(
            id="ai-serialize-2",
            content="Serialize the dataset again.",
            tool_calls=[
                {
                    "name": "serialize_dataset",
                    "args": {"format": "turtle"},
                    "id": "call-serialize-2",
                    "type": "tool_call",
                }
            ],
        ),
    ]
    stuck = [
        AIMessage(
            id=f"ai-serialize-stuck-{i}",
            content=f"Serialize again ({i}).",
            tool_calls=[
                {
                    "name": "serialize_dataset",
                    "args": {"format": "turtle"},
                    "id": f"call-stuck-{i}",
                    "type": "tool_call",
                }
            ],
        )
        for i in range(40)
    ]
    model = ToolFriendlyFakeMessagesListChatModel(responses=pre + stuck)
    agent = create_deep_agent_graph(
        model=model, middleware=_combined_guard_middleware()
    )

    chunks = collect_update_chunks(
        agent,
        messages=[{"role": "user", "content": "Represent the source text as RDF."}],
        recursion_limit=45,
    )

    # Deep Agents emits many update chunks per step; the important property is that we
    # terminate via stop_now (not GraphRecursionError) before hitting recursion_limit.
    assert len(chunks) < 120

    assert any(
        (
            isinstance(chunk.get("ContinuationGuardMiddleware.after_model"), dict)
            and chunk["ContinuationGuardMiddleware.after_model"].get(
                "continuation_mode"
            )
            == "stop_now"
        )
        or (
            isinstance(chunk.get("ContinuationGuardMiddleware.before_model"), dict)
            and chunk["ContinuationGuardMiddleware.before_model"].get("jump_to")
            == "end"
        )
        for chunk in chunks
    )


def test_deep_agent_graph_does_not_emit_stale_remove_message_ids_during_repair() -> (
    None
):
    """Regression: avoid reducer-time ValueError for stale RemoveMessage ids.

    This notebook-like sequence intentionally drives repeated serialize retries and
    finalize-only transitions where transcript repair may run multiple times.
    """
    model = ToolFriendlyFakeMessagesListChatModel(
        responses=[
            AIMessage(
                id="ai-add",
                content="Adding triples now.",
                tool_calls=[
                    {
                        "name": "add_triples",
                        "args": {
                            "triples": [
                                {
                                    "subject": "<urn:test:s>",
                                    "predicate": "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>",
                                    "object": "<http://www.w3.org/2000/01/rdf-schema#Class>",
                                }
                            ]
                        },
                        "id": "call-add",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                id="ai-serialize-1",
                content="Serialize.",
                tool_calls=[
                    {
                        "name": "serialize_dataset",
                        "args": {"format": "turtle"},
                        "id": "call-serialize-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                id="ai-serialize-2",
                content="Serialize again.",
                tool_calls=[
                    {
                        "name": "serialize_dataset",
                        "args": {"format": "turtle"},
                        "id": "call-serialize-2",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                id="ai-list-1",
                content="Inspect one more time.",
                tool_calls=[
                    {
                        "name": "list_triples",
                        "args": {},
                        "id": "call-list-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                id="ai-list-2",
                content="Inspect again.",
                tool_calls=[
                    {
                        "name": "list_triples",
                        "args": {},
                        "id": "call-list-2",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                id="ai-serialize-3",
                content="Serialize once more.",
                tool_calls=[
                    {
                        "name": "serialize_dataset",
                        "args": {"format": "turtle"},
                        "id": "call-serialize-3",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                content=(
                    "```text/turtle\n"
                    "@prefix ex: <urn:test:> .\n"
                    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
                    "ex:s a rdfs:Class .\n"
                    "```"
                )
            ),
        ]
    )
    agent = create_deep_agent_graph(
        model=model, middleware=_combined_guard_middleware()
    )

    try:
        _ = collect_update_chunks(
            agent,
            messages=[{"role": "user", "content": "Represent the source text as RDF."}],
            recursion_limit=60,
        )
    except ValueError as exc:
        if "Attempting to delete a message with an ID that doesn't exist" in str(exc):
            pytest.fail(
                "Regression: stale RemoveMessage id reached LangGraph add_messages reducer: "
                f"{exc}"
            )
        raise
