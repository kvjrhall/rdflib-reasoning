from rdflib import Literal, URIRef
from rdflibr.middleware import DatasetMiddleware

EX = "urn:test:"


def test_create_state_starts_empty() -> None:
    middleware = DatasetMiddleware()

    state = middleware.create_state()

    assert middleware.list_triples(state) == []
    assert middleware.list_quads(state) == []
    assert list(state["dataset"].graphs()) == [state["dataset"].default_graph]


def test_default_graph_triple_crud() -> None:
    middleware = DatasetMiddleware()
    state = middleware.create_state()
    triple = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))

    middleware.add_triples(state, [triple])

    assert middleware.list_triples(state) == [triple]

    middleware.remove_triples(state, [triple])

    assert middleware.list_triples(state) == []


def test_named_graph_quad_crud_and_listing() -> None:
    middleware = DatasetMiddleware()
    state = middleware.create_state()
    graph_id = URIRef(f"{EX}g")
    quad = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"), graph_id)

    middleware.create_graph(state, graph_id)
    middleware.add_quads(state, [quad])

    graph_ids = {graph.identifier for graph in middleware.list_graphs(state)}

    assert graph_id in graph_ids
    assert quad in middleware.list_quads(state)

    middleware.remove_quads(state, [quad])

    assert quad not in middleware.list_quads(state)


def test_remove_graph_removes_named_graph_contents() -> None:
    middleware = DatasetMiddleware()
    state = middleware.create_state()
    graph_id = URIRef(f"{EX}g")
    quad = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"), graph_id)

    middleware.add_quads(state, [quad])

    middleware.remove_graph(state, graph_id)

    graph_ids = {graph.identifier for graph in middleware.list_graphs(state)}

    assert graph_id not in graph_ids
    assert middleware.list_quads(state) == []


def test_serialize_dataset_and_selected_graph() -> None:
    middleware = DatasetMiddleware()
    state = middleware.create_state()
    default_triple = (URIRef(f"{EX}s1"), URIRef(f"{EX}p"), Literal("default"))
    graph_id = URIRef(f"{EX}g")
    quad = (URIRef(f"{EX}s2"), URIRef(f"{EX}p"), Literal("named"), graph_id)

    middleware.add_triples(state, [default_triple])
    middleware.add_quads(state, [quad])

    dataset_output = middleware.serialize(state)
    graph_output = middleware.serialize(
        state, format="turtle", graph_identifier=graph_id
    )

    assert "default" in dataset_output
    assert "named" in dataset_output
    assert "named" in graph_output
    assert "default" not in graph_output


def test_reset_state_replaces_existing_dataset() -> None:
    middleware = DatasetMiddleware()
    state = middleware.create_state()
    middleware.add_triples(state, [(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])

    reset_state = middleware.reset_state(state)

    assert reset_state is not state
    assert middleware.list_triples(reset_state) == []
