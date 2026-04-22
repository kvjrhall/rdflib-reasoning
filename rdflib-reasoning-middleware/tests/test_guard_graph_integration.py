import sys
from collections.abc import Callable
from json import loads as json_loads
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.errors import GraphRecursionError
from rdflib import Namespace
from rdflib_reasoning.middleware import (
    DatasetMiddleware,
    DatasetMiddlewareConfig,
    RDFVocabularyMiddleware,
    RDFVocabularyMiddlewareConfig,
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


def _vocabulary_only_middleware() -> list[Any]:
    vocabulary_context = VocabularyConfiguration.bundled_plus(
        VocabularyDeclaration(prefix="ex", namespace=EX_NS)
    ).build_context()
    return [
        RDFVocabularyMiddleware(
            RDFVocabularyMiddlewareConfig(vocabulary_context=vocabulary_context)
        )
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


def _ai_messages(chunks: list[dict[str, Any]]) -> list[AIMessage]:
    messages: list[AIMessage] = []
    for chunk in chunks:
        for update in chunk.values():
            if not isinstance(update, dict):
                continue
            chunk_messages = update.get("messages")
            if not isinstance(chunk_messages, list):
                continue
            messages.extend(
                message for message in chunk_messages if isinstance(message, AIMessage)
            )
    return messages


def _values_chunks(
    agent: Any,
    *,
    messages: list[BaseMessage | dict[str, str]],
    recursion_limit: int = 20,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for chunk in agent.stream(
        {"messages": list(messages)},
        config={"recursion_limit": recursion_limit},
        stream_mode="values",
    ):
        if isinstance(chunk, dict):
            chunks.append(chunk)
    return chunks


def _values_chunks_allowing_recursion_limit(
    agent: Any,
    *,
    messages: list[BaseMessage | dict[str, str]],
    recursion_limit: int = 20,
) -> tuple[list[dict[str, Any]], GraphRecursionError | None]:
    chunks: list[dict[str, Any]] = []
    try:
        for chunk in agent.stream(
            {"messages": list(messages)},
            config={"recursion_limit": recursion_limit},
            stream_mode="values",
        ):
            if isinstance(chunk, dict):
                chunks.append(chunk)
    except GraphRecursionError as exc:
        return chunks, exc
    return chunks, None


def _has_user_after_tool_in_messages(messages: list[Any]) -> bool:
    for index, message in enumerate(messages[:-1]):
        if isinstance(message, ToolMessage) and isinstance(
            messages[index + 1], HumanMessage
        ):
            return True
    return False


@tool
def _fake_write_file(file_path: str, content: str) -> str:
    """Test-only fake file writer that must never execute in finalize-only recovery."""
    del file_path, content
    raise AssertionError(
        "write_file should not execute once finalize-only can recover the last successful serialization"
    )


@pytest.mark.parametrize(("factory_name", "graph_factory"), GRAPH_FACTORIES)
def test_search_terms_tool_result_is_stringified_in_agent_tool_message(
    factory_name: str, graph_factory: GraphFactory
) -> None:
    del factory_name
    model = ToolFriendlyFakeMessagesListChatModel(
        responses=[
            AIMessage(
                id="ai-list-vocabularies",
                content="First I should inspect the available vocabularies.",
                tool_calls=[
                    {
                        "name": "list_vocabularies",
                        "args": {},
                        "id": "call-list-vocabularies",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                id="ai-search",
                content="Searching for the right property.",
                tool_calls=[
                    {
                        "name": "search_terms",
                        "args": {
                            "query": "maker",
                            "vocabularies": ["http://xmlns.com/foaf/0.1/"],
                            "term_types": ["property"],
                            "limit": 5,
                        },
                        "id": "call-search",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Done."),
        ]
    )
    agent = graph_factory(model=model, middleware=_vocabulary_only_middleware())

    chunks = collect_update_chunks(
        agent,
        messages=[{"role": "user", "content": "Find a fitting vocabulary term."}],
        recursion_limit=20,
    )

    tool_messages = _tool_messages(chunks)
    search_message = next(
        message for message in tool_messages if message.name == "search_terms"
    )

    assert isinstance(search_message.content, str)
    parsed = json_loads(search_message.content)
    assert parsed["query"] == "maker"
    assert isinstance(parsed["hits"], list)
    assert len(parsed["hits"]) > 0
    assert isinstance(parsed["hits"][0]["uri"], str)
    assert isinstance(parsed["hits"][0]["why_matched"], list)


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
def test_graph_recovers_from_invalid_add_triples_payload_in_empty_dataset(
    factory_name: str, graph_factory: GraphFactory
) -> None:
    del factory_name
    model = ToolFriendlyFakeMessagesListChatModel(
        responses=[
            AIMessage(
                id="ai-invalid-add",
                content=(
                    "I will now call add_triples with the class definition and then "
                    "continue modeling."
                ),
                invalid_tool_calls=[
                    {
                        "id": "invalid-add-1",
                        "name": "add_triples",
                        "args": (
                            '{"triples":[{"subject":"<urn:test:s>",'
                            '"predicate":"<http://www.w3.org/2000/01/rdf-schema#label>",'
                            '"object":""Broken""}]}'
                        ),
                        "error": "JSONDecodeError",
                        "type": "invalid_tool_call",
                    }
                ],
            ),
            AIMessage(
                id="ai-valid-add",
                content="Calling add_triples with corrected JSON now.",
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
                        "id": "call-add-valid",
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
    ai_messages = _ai_messages(chunks)
    assert any(len(message.invalid_tool_calls) > 0 for message in ai_messages), (
        "Expected the malformed add_triples attempt to surface in the run transcript."
    )
    assert any("```text/turtle" in str(message.content) for message in ai_messages)


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
def test_graph_reuses_last_successful_serialization_after_repeated_serialize_rejection(
    factory_name: str, graph_factory: GraphFactory
) -> None:
    """Regression: finalize-only should not accept prose that promises to reuse Turtle.

    This mirrors the notebook failure where the model:
    1. serializes successfully,
    2. narrates instead of finishing,
    3. gets a repeated-serialize rejection,
    4. says it will return the previous serialization,
    5. but never actually emits the Turtle block.
    """
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
                id="ai-narrate-after-serialize",
                content=(
                    "Let me analyze the current RDF representation to ensure it "
                    "accurately captures the explicit claims from the text."
                ),
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
                id="ai-prose-reuse-only",
                content=(
                    "I will now return the previous successful serialization as the "
                    "final answer. The dataset accurately represents all the explicit "
                    "claims from the source text:"
                ),
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

    ai_messages = _ai_messages(chunks)
    assert any(
        "I will now return the previous successful serialization as the final answer."
        in str(message.content)
        for message in ai_messages
    )
    assert any("```text/turtle" in str(message.content) for message in ai_messages), (
        "Expected the run to surface the last successful Turtle serialization as the final answer."
    )


@pytest.mark.parametrize(("factory_name", "graph_factory"), GRAPH_FACTORIES)
def test_graph_short_circuits_finalize_only_before_forbidden_write_file_executes(
    factory_name: str, graph_factory: GraphFactory
) -> None:
    """Regression: finalize-only should recover Turtle before a write_file loop can start."""
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
                id="ai-write-file",
                content="I will write the serialized Turtle to a file now.",
                tool_calls=[
                    {
                        "name": "write_file",
                        "args": {
                            "file_path": "/large_tool_results/demo/output.ttl",
                            "content": (
                                "@prefix ex: <urn:test:> .\n"
                                "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
                                "ex:s a rdfs:Class .\n"
                            ),
                        },
                        "id": "call-write-file",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(id="ai-should-not-be-called", content="SHOULD_NOT_BE_CALLED"),
        ]
    )
    agent = graph_factory(
        model=model,
        middleware=_combined_guard_middleware(),
        tools=[_fake_write_file],
    )

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
    assert not any(message.name == "write_file" for message in tool_messages)

    ai_messages = _ai_messages(chunks)
    assert any("```text/turtle" in str(message.content) for message in ai_messages), (
        "Expected finalize-only to recover the last successful Turtle serialization."
    )
    assert not any(
        "SHOULD_NOT_BE_CALLED" in str(message.content) for message in ai_messages
    )


@pytest.mark.parametrize(("factory_name", "graph_factory"), GRAPH_FACTORIES)
def test_graph_stops_without_another_model_call_after_serialize_final_answer_preamble(
    factory_name: str, graph_factory: GraphFactory
) -> None:
    """Regression: do not re-enter the model after an assistant final-answer preamble.

    This mirrors the current notebook failure where the agent:
    1. serializes the dataset successfully,
    2. says it will now return the Turtle as the final answer,
    3. but the framework calls the model again anyway.
    """
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
                content="Let me serialize the current RDF dataset to ensure it accurately reflects the representation and return it as the final answer.",
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
                id="ai-final-answer-preamble",
                content=(
                    "I will now return the Turtle representation as the final answer. "
                    "The representation accurately captures all the explicit claims in "
                    "the source text:"
                ),
            ),
            AIMessage(
                id="ai-should-not-be-called",
                content="SHOULD_NOT_BE_CALLED",
            ),
        ]
    )
    agent = graph_factory(model=model, middleware=_combined_guard_middleware())

    chunks = collect_update_chunks(
        agent,
        messages=[{"role": "user", "content": "Represent the source text as RDF."}],
        recursion_limit=30,
    )

    ai_messages = _ai_messages(chunks)
    assert any(
        "I will now return the Turtle representation as the final answer."
        in str(message.content)
        for message in ai_messages
    )
    assert not any(
        "SHOULD_NOT_BE_CALLED" in str(message.content) for message in ai_messages
    ), (
        "The framework should have terminated locally instead of calling the model again."
    )
    assert any("```text/turtle" in str(message.content) for message in ai_messages), (
        "Expected the run to surface the serialized Turtle as the final answer."
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


@pytest.mark.parametrize(("factory_name", "graph_factory"), GRAPH_FACTORIES)
def test_graph_reprompt_after_rejected_tool_retry_keeps_provider_safe_message_order(
    factory_name: str, graph_factory: GraphFactory
) -> None:
    """Regression: normal-mode retry guidance must not create tool -> user ordering."""
    model = ToolFriendlyFakeMessagesListChatModel(
        responses=[
            AIMessage(
                id="ai-repeat-search",
                content="Retry the same search.",
                tool_calls=[
                    {
                        "name": "search_terms",
                        "args": {
                            "query": "person",
                            "vocabularies": [
                                "http://www.w3.org/ns/prov#",
                                "http://xmlns.com/foaf/0.1/",
                            ],
                        },
                        "id": "call-repeat-search",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="I will inspect one of the returned candidates instead."),
        ]
    )
    agent = graph_factory(model=model, middleware=[ContinuationGuardMiddleware()])

    chunks, recursion_exc = _values_chunks_allowing_recursion_limit(
        agent,
        messages=[
            HumanMessage(content="Please continue from the tool failure."),
            AIMessage(
                id="ai-original-search",
                content="Search for person candidates.",
                tool_calls=[
                    {
                        "name": "search_terms",
                        "args": {
                            "query": "person",
                            "vocabularies": [
                                "http://www.w3.org/ns/prov#",
                                "http://xmlns.com/foaf/0.1/",
                            ],
                        },
                        "id": "call-original-search",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(
                content=(
                    "Misuse: repeated `search_terms` query was rejected. "
                    "Do not retry it unchanged."
                ),
                name="search_terms",
                tool_call_id="call-original-search",
                status="error",
            ),
        ],
        recursion_limit=10,
    )

    assert chunks
    # Deep Agents may continue beyond this tiny fake-model script because additional
    # framework middleware still nudges the run; provider-safe ordering must hold either way.
    if factory_name == "deep_agent":
        assert recursion_exc is not None or chunks
    else:
        assert recursion_exc is None
    assert not any(
        _has_user_after_tool_in_messages(chunk.get("messages", [])) for chunk in chunks
    )


def test_deep_agent_graph_stops_infinite_normal_mode_rejected_tool_retry_loop() -> None:
    """Regression: repeated identical retries after a tool error must stop in normal mode."""
    model = ToolFriendlyFakeMessagesListChatModel(
        responses=[
            AIMessage(
                id=f"ai-static-retry-{i}",
                content=f"Retry the same static lookup ({i}).",
                tool_calls=[
                    {
                        "name": "static_lookup",
                        "args": {"term": "Mammal", "include_source_rdf": True},
                        "id": f"call-static-retry-{i}",
                        "type": "tool_call",
                    }
                ],
            )
            for i in range(6)
        ]
    )
    agent = create_deep_agent_graph(
        model=model, middleware=[ContinuationGuardMiddleware()]
    )

    chunks = collect_update_chunks(
        agent,
        messages=[
            HumanMessage(content="Please continue from the previous tool failure."),
            AIMessage(
                id="ai-static-original",
                content="Inspect the term.",
                tool_calls=[
                    {
                        "name": "static_lookup",
                        "args": {"term": "Mammal", "include_source_rdf": True},
                        "id": "call-static-original",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(
                content="Static lookup already answered that exact question.",
                name="static_lookup",
                tool_call_id="call-static-original",
                status="error",
            ),
        ],
        recursion_limit=20,
    )

    assert len(chunks) < 40
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
