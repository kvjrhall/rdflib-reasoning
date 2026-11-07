"""Tests for property and named-individual declaration structural elements."""

from collections.abc import Sequence

import pytest
from pydantic import BaseModel
from rdflib import OWL, RDF, Graph, IdentifiedNode, URIRef
from rdflib_reasoning.axiom.axiomatize import axiomatize
from rdflib_reasoning.axiom.declaration import (
    DeclarationAnnotationProperty,
    DeclarationDataProperty,
    DeclarationObjectProperty,
    NamedIndividual,
)
from rdflib_reasoning.axiom.structural_element import (
    DeclarationElement,
    StructuralElement,
)

CTX = URIRef("http://example.com/g")
EX = "http://example.com/"


def _uri(name: str) -> URIRef:
    return URIRef(f"{EX}{name}")


def _assert_model_json_schema_smoke(model_cls: type[BaseModel], title: str) -> None:
    schema = model_cls.model_json_schema()
    assert schema.get("title") == title
    assert "context" in schema["properties"]


def _assert_python_json_round_trip[T: BaseModel](
    model_cls: type[T],
    instance: T,
) -> None:
    dumped = instance.model_dump()
    assert model_cls.model_validate(dumped) == instance
    json_text = instance.model_dump_json()
    assert model_cls.model_validate_json(json_text) == instance


def _graph_from_element(element: StructuralElement) -> Graph:
    graph = Graph(identifier=element.context)
    for triple in element.as_triples:
        graph.add(triple)
    return graph


_DECLARATION_CASES: Sequence[tuple[type[DeclarationElement], IdentifiedNode, str]] = (
    (DeclarationObjectProperty, OWL.ObjectProperty, "DeclarationObjectProperty"),
    (DeclarationDataProperty, OWL.DatatypeProperty, "DeclarationDataProperty"),
    (
        DeclarationAnnotationProperty,
        OWL.AnnotationProperty,
        "DeclarationAnnotationProperty",
    ),
    (NamedIndividual, OWL.NamedIndividual, "NamedIndividual"),
)


@pytest.mark.parametrize(("cls", "rdf_type", "kind"), _DECLARATION_CASES)
def test_declaration_as_triples(
    cls: type[DeclarationElement],
    rdf_type: IdentifiedNode,
    kind: str,
) -> None:
    name = _uri("entity")
    declaration = cls(context=CTX, name_value=name)

    assert declaration.kind == kind
    assert declaration.name == name
    assert declaration.rdf_type == rdf_type
    assert declaration.as_triples == ((name, RDF.type, rdf_type),)
    assert declaration.as_quads == tuple((*t, CTX) for t in declaration.as_triples)


@pytest.mark.parametrize(("cls", "_rdf_type", "kind"), _DECLARATION_CASES)
def test_declaration_python_json_round_trip_and_schema(
    cls: type[DeclarationElement],
    _rdf_type: IdentifiedNode,
    kind: str,
) -> None:
    declaration = cls(context=CTX, name_value=_uri("entity"))
    _assert_python_json_round_trip(cls, declaration)
    _assert_model_json_schema_smoke(cls, kind)


@pytest.mark.parametrize(("cls", "_rdf_type", "_kind"), _DECLARATION_CASES)
def test_axiomatize_round_trips_declarations(
    cls: type[DeclarationElement],
    _rdf_type: IdentifiedNode,
    _kind: str,
) -> None:
    element = cls(context=CTX, name_value=_uri(f"{cls.__name__}-entity"))
    actual = axiomatize(_graph_from_element(element))

    assert len(actual) == 1
    assert type(actual[0]) is cls
    assert actual[0] == element
