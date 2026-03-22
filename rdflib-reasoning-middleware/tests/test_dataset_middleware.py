from rdflib import Literal, URIRef
from rdflib_reasoning.middleware import DatasetMiddleware

EX = "urn:test:"


def test_default_graph_starts_empty() -> None:
    middleware = DatasetMiddleware()

    assert middleware.list_triples() == ()


def test_default_graph_triple_crud() -> None:
    middleware = DatasetMiddleware()
    triple = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))

    add_response = middleware.add_triples([triple])

    assert add_response.updated == 1
    assert middleware.list_triples() == (triple,)

    remove_response = middleware.remove_triples([triple])

    assert remove_response.updated == 1
    assert middleware.list_triples() == ()


def test_serialize_default_graph() -> None:
    middleware = DatasetMiddleware()
    triple = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("default"))

    middleware.add_triples([triple])

    output = middleware.serialize(format="turtle")

    assert "default" in output


def test_reset_dataset_replaces_existing_dataset() -> None:
    middleware = DatasetMiddleware()
    middleware.add_triples([(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])

    response = middleware.reset_dataset()

    assert response.updated == 1
    assert middleware.list_triples() == ()
