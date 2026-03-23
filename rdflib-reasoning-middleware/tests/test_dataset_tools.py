from deepagents import create_deep_agent
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from rdflib import Literal, URIRef
from rdflib_reasoning.middleware import (
    DatasetMiddleware,
    N3Triple,
    NewResourceNodeResponse,
    SerializationResponse,
    SerializeRequest,
    TripleBatchRequest,
)

EX = "urn:test:"


def test_tool_models_validate_n3_shapes() -> None:
    triple = N3Triple(
        subject=f"<{EX}s>",
        predicate=f"<{EX}p>",
        object='"value"',
    )

    assert (triple.subject, triple.predicate, triple.object) == (
        URIRef(f"{EX}s"),
        URIRef(f"{EX}p"),
        Literal("value"),
    )


def test_tool_models_accept_bare_iris_and_serialize_canonically() -> None:
    triple = N3Triple(
        subject=f"{EX}s",
        predicate=f"{EX}p",
        object=f"{EX}o",
    )

    assert (triple.subject, triple.predicate, triple.object) == (
        URIRef(f"{EX}s"),
        URIRef(f"{EX}p"),
        URIRef(f"{EX}o"),
    )
    assert triple.model_dump(mode="json") == {
        "subject": f"<{EX}s>",
        "predicate": f"<{EX}p>",
        "object": f"<{EX}o>",
    }


def test_request_models_are_tuple_backed_and_validate_expected_shapes() -> None:
    triple_request = TripleBatchRequest(
        triples=(
            N3Triple(
                subject=f"<{EX}s>",
                predicate=f"<{EX}p>",
                object='"value"',
            ),
        )
    )
    serialize_request = SerializeRequest(format="turtle")

    assert isinstance(triple_request.triples, tuple)
    assert serialize_request.format == "turtle"


def test_tool_input_schemas_match_request_models() -> None:
    middleware = DatasetMiddleware()
    tools = {tool.name: tool for tool in middleware.tools}

    assert {tool.name for tool in middleware.tools} == {
        "list_triples",
        "add_triples",
        "remove_triples",
        "serialize_dataset",
        "reset_dataset",
        "new_blank_node",
    }
    assert tools["add_triples"].get_input_schema() is TripleBatchRequest
    assert tools["serialize_dataset"].get_input_schema() is SerializeRequest

    serialized = tools["serialize_dataset"].invoke({"format": "turtle"})
    assert isinstance(serialized, SerializationResponse)
    assert serialized.format == "turtle"
    assert serialized.model_dump(mode="json")["format"] == "turtle"

    blank_node = tools["new_blank_node"].invoke({})
    assert isinstance(blank_node, NewResourceNodeResponse)
    assert blank_node.resource.startswith("_:")


def test_dataset_tool_descriptions_and_examples_are_agent_facing() -> None:
    middleware = DatasetMiddleware()
    tools = {tool.name: tool for tool in middleware.tools}
    triple_batch_schema = TripleBatchRequest.model_json_schema()
    serialize_schema = SerializeRequest.model_json_schema()

    assert "top-level argument" in tools["add_triples"].description
    assert "top-level argument" in tools["remove_triples"].description
    assert "IRI inputs MAY be given either" in tools["add_triples"].description
    assert (
        "Literal text MUST be encoded as RDF literals"
        in tools["add_triples"].description
    )
    assert "one subject per call" in tools["add_triples"].description
    assert len(triple_batch_schema["properties"]["triples"]["examples"]) >= 2
    assert len(serialize_schema["properties"]["format"]["examples"]) >= 2


def test_dataset_middleware_crud_surface_supports_default_graph_triples() -> None:
    middleware = DatasetMiddleware()
    triple = N3Triple(
        subject=f"<{EX}s1>",
        predicate=f"<{EX}p>",
        object='"default"',
    )

    add_response = middleware.add_triples(
        [(triple.subject, triple.predicate, triple.object)]
    )
    remove_response = middleware.remove_triples(
        [(triple.subject, triple.predicate, triple.object)]
    )

    assert add_response.updated == 1
    assert remove_response.updated == 1
    assert middleware.list_triples() == ()


def test_dataset_middleware_serializes_default_graph_only() -> None:
    middleware = DatasetMiddleware()
    middleware.add_triples(
        [(URIRef(f"{EX}s1"), URIRef(f"{EX}p"), Literal("default"))],
    )

    response = middleware.serialize(format="turtle")

    assert "default" in response


def test_dataset_middleware_reset_replaces_state() -> None:
    middleware = DatasetMiddleware()
    middleware.add_triples(
        [(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("value"))],
    )

    response = middleware.reset_dataset()

    assert response.updated == 1
    assert middleware.list_triples() == ()


def test_dataset_middleware_registers_langchain_tools() -> None:
    middleware = DatasetMiddleware()

    assert {tool.name for tool in middleware.tools} == {
        "list_triples",
        "add_triples",
        "remove_triples",
        "serialize_dataset",
        "reset_dataset",
        "new_blank_node",
    }


def test_dataset_middleware_can_be_registered_as_agent_middleware() -> None:
    model = FakeListChatModel(responses=["ok"])

    agent = create_agent(model=model, middleware=[DatasetMiddleware()])
    deep_agent = create_deep_agent(
        model=model,
        system_prompt="You are a research assistant specialized in technical documentation.",
        middleware=[DatasetMiddleware()],
    )

    assert agent is not None
    assert deep_agent is not None
