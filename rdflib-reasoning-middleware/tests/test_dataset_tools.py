from rdflib import Literal, URIRef
from rdflibr.middleware import (
    CreateGraphRequest,
    DatasetToolLayer,
    QuadBatchRequest,
    RDFQuadModel,
    RDFTripleModel,
    SerializeRequest,
    TripleBatchRequest,
)

EX = "urn:test:"


def test_tool_layer_adds_and_lists_triples() -> None:
    tools = DatasetToolLayer()
    triple = RDFTripleModel(
        subject=f"<{EX}s>",
        predicate=f"<{EX}p>",
        object='"value"',
    )

    response = tools.add_triples(TripleBatchRequest(triples=[triple]))

    assert response.updated == 1
    assert tools.list_triples().triples == [triple]


def test_tool_layer_adds_and_lists_quads() -> None:
    tools = DatasetToolLayer()
    quad = RDFQuadModel(
        subject=f"<{EX}s>",
        predicate=f"<{EX}p>",
        object='"value"',
        graph=f"<{EX}g>",
    )

    response = tools.add_quads(QuadBatchRequest(quads=[quad]))

    assert response.updated == 1
    assert tools.list_quads().quads == [quad]


def test_tool_layer_lists_and_removes_graphs() -> None:
    tools = DatasetToolLayer()
    graph = CreateGraphRequest(graph=f"<{EX}g>")

    tools.create_graph(graph)

    assert graph.graph in tools.list_graphs().graphs

    tools.remove_graph(graph)

    assert graph.graph not in tools.list_graphs().graphs


def test_tool_layer_serializes_selected_graph_only() -> None:
    tools = DatasetToolLayer()
    tools.add_triples(
        TripleBatchRequest(
            triples=[
                RDFTripleModel(
                    subject=f"<{EX}s1>",
                    predicate=f"<{EX}p>",
                    object='"default"',
                )
            ]
        )
    )
    tools.add_quads(
        QuadBatchRequest(
            quads=[
                RDFQuadModel(
                    subject=f"<{EX}s2>",
                    predicate=f"<{EX}p>",
                    object='"named"',
                    graph=f"<{EX}g>",
                )
            ]
        )
    )

    response = tools.serialize(SerializeRequest(format="turtle", graph=f"<{EX}g>"))

    assert "named" in response.content
    assert "default" not in response.content


def test_tool_layer_reset_replaces_shared_state() -> None:
    tools = DatasetToolLayer()
    tools.add_triples(
        TripleBatchRequest(
            triples=[
                RDFTripleModel(
                    subject=f"<{EX}s>",
                    predicate=f"<{EX}p>",
                    object='"value"',
                )
            ]
        )
    )

    tools.reset_dataset()

    assert tools.list_triples().triples == []


def test_tool_models_validate_n3_shapes() -> None:
    triple = RDFTripleModel(
        subject=f"<{EX}s>",
        predicate=f"<{EX}p>",
        object='"value"',
    )
    quad = RDFQuadModel(
        subject=f"<{EX}s>",
        predicate=f"<{EX}p>",
        object='"value"',
        graph=f"<{EX}g>",
    )

    assert triple.to_rdflib() == (
        URIRef(f"{EX}s"),
        URIRef(f"{EX}p"),
        Literal("value"),
    )
    assert quad.to_rdflib() == (
        URIRef(f"{EX}s"),
        URIRef(f"{EX}p"),
        Literal("value"),
        URIRef(f"{EX}g"),
    )
