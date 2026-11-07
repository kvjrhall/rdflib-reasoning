"""Tests for object and data property characteristic structural elements."""

from collections.abc import Sequence

import pytest
from pydantic import BaseModel
from rdflib import OWL, RDF, Graph, IdentifiedNode, URIRef
from rdflib_reasoning.axiom.axiomatize import axiomatize
from rdflib_reasoning.axiom.declaration import DeclarationDataProperty
from rdflib_reasoning.axiom.property_characteristic import (
    AsymmetricObjectProperty,
    FunctionalDataProperty,
    FunctionalObjectProperty,
    InverseFunctionalObjectProperty,
    IrreflexiveObjectProperty,
    ReflexiveObjectProperty,
    SymmetricObjectProperty,
    TransitiveObjectProperty,
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


_UNAMBIGUOUS_CHARACTERISTIC_CASES: Sequence[
    tuple[type[DeclarationElement], IdentifiedNode, str]
] = (
    (
        InverseFunctionalObjectProperty,
        OWL.InverseFunctionalProperty,
        "InverseFunctionalObjectProperty",
    ),
    (ReflexiveObjectProperty, OWL.ReflexiveProperty, "ReflexiveObjectProperty"),
    (IrreflexiveObjectProperty, OWL.IrreflexiveProperty, "IrreflexiveObjectProperty"),
    (SymmetricObjectProperty, OWL.SymmetricProperty, "SymmetricObjectProperty"),
    (AsymmetricObjectProperty, OWL.AsymmetricProperty, "AsymmetricObjectProperty"),
    (TransitiveObjectProperty, OWL.TransitiveProperty, "TransitiveObjectProperty"),
    (FunctionalObjectProperty, OWL.FunctionalProperty, "FunctionalObjectProperty"),
    (FunctionalDataProperty, OWL.FunctionalProperty, "FunctionalDataProperty"),
)


@pytest.mark.parametrize(
    ("cls", "rdf_type", "kind"),
    _UNAMBIGUOUS_CHARACTERISTIC_CASES,
)
def test_characteristic_as_triples(
    cls: type[DeclarationElement],
    rdf_type: IdentifiedNode,
    kind: str,
) -> None:
    name = _uri("prop")
    axiom = cls(context=CTX, name_value=name)

    assert axiom.kind == kind
    assert axiom.name == name
    assert axiom.rdf_type == rdf_type
    assert axiom.as_triples == ((name, RDF.type, rdf_type),)
    assert axiom.as_quads == tuple((*t, CTX) for t in axiom.as_triples)


@pytest.mark.parametrize(
    ("cls", "_rdf_type", "kind"),
    _UNAMBIGUOUS_CHARACTERISTIC_CASES,
)
def test_characteristic_python_json_round_trip_and_schema(
    cls: type[DeclarationElement],
    _rdf_type: IdentifiedNode,
    kind: str,
) -> None:
    axiom = cls(context=CTX, name_value=_uri("prop"))
    _assert_python_json_round_trip(cls, axiom)
    _assert_model_json_schema_smoke(cls, kind)


@pytest.mark.parametrize(
    ("cls", "_rdf_type", "_kind"),
    (
        case
        for case in _UNAMBIGUOUS_CHARACTERISTIC_CASES
        if case[0] is not FunctionalDataProperty
    ),
)
def test_axiomatize_round_trips_unambiguous_characteristics(
    cls: type[DeclarationElement],
    _rdf_type: IdentifiedNode,
    _kind: str,
) -> None:
    element = cls(context=CTX, name_value=_uri(f"{cls.__name__}-prop"))
    actual = axiomatize(_graph_from_element(element))

    assert len(actual) == 1
    assert type(actual[0]) is cls
    assert actual[0] == element


def test_axiomatize_lifts_lone_functional_property_as_object_form() -> None:
    """Bare ``owl:FunctionalProperty`` defaults to the object characteristic."""
    element = FunctionalDataProperty(context=CTX, name_value=_uri("ambiguous-prop"))
    actual = axiomatize(_graph_from_element(element))

    assert len(actual) == 1
    assert isinstance(actual[0], FunctionalObjectProperty)
    assert actual[0].name == element.name
    assert actual[0].as_triples == element.as_triples


def test_axiomatize_round_trips_functional_data_property_with_declaration() -> None:
    """``FunctionalDataProperty`` is recovered when DatatypeProperty typing is present."""
    name = _uri("functional-data-prop")
    declaration = DeclarationDataProperty(context=CTX, name_value=name)
    characteristic = FunctionalDataProperty(context=CTX, name_value=name)
    graph = Graph(identifier=CTX)
    for element in (declaration, characteristic):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)

    assert actual == (characteristic, declaration)
