"""Focused tests for object/data restriction and cardinality structural elements."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError
from rdflib import OWL, RDF, XSD, BNode, Graph, Literal, URIRef
from rdflib_reasoning.axiom.axiomatize import axiomatize
from rdflib_reasoning.axiom.datatype import (
    DataAllValuesFrom,
    DataExactCardinality,
    DataExactCardinalityQualified,
    DataHasValue,
    DataMaxCardinality,
    DataMaxCardinalityQualified,
    DataMinCardinality,
    DataMinCardinalityQualified,
)
from rdflib_reasoning.axiom.declaration import (
    DeclarationDataProperty,
    DeclarationObjectProperty,
)
from rdflib_reasoning.axiom.restriction import (
    ObjectAllValuesFrom,
    ObjectExactCardinality,
    ObjectExactCardinalityQualified,
    ObjectHasSelf,
    ObjectHasValue,
    ObjectMaxCardinality,
    ObjectMaxCardinalityQualified,
    ObjectMinCardinality,
    ObjectMinCardinalityQualified,
    ObjectRestriction,
    ObjectSomeValuesFrom,
)
from rdflib_reasoning.axiom.structural_element import StructuralElement

EX = "http://example.com/"
CTX = URIRef(f"{EX}g")


def _uri(name: str) -> URIRef:
    return URIRef(f"{EX}{name}")


def _nn(n: int) -> Literal:
    return Literal(n, datatype=XSD.nonNegativeInteger)


def _assert_model_json_schema_smoke(model_cls: type[BaseModel], title: str) -> None:
    schema = model_cls.model_json_schema()
    assert schema.get("title") == title
    assert "context" in schema["properties"]


def _assert_python_json_round_trip[T: BaseModel](
    model_cls: type[T], instance: T
) -> None:
    assert model_cls.model_validate(instance.model_dump()) == instance
    assert model_cls.model_validate_json(instance.model_dump_json()) == instance


def _graph_from_elements(*elements: StructuralElement) -> Graph:
    graph = Graph(identifier=CTX)
    for element in elements:
        for triple in element.as_triples:
            graph.add(triple)
    return graph


def test_cannot_instantiate_abc_object_restriction() -> None:
    with pytest.raises(TypeError):
        ObjectRestriction(  # type: ignore[abstract] # pyright: ignore[reportAbstractUsage]
            context=BNode(),
            name_value=BNode(),
        )


def test_object_some_values_from_as_triples() -> None:
    main = _uri("restriction-node")
    prop = _uri("op")
    filler = _uri("CE")
    inst = ObjectSomeValuesFrom(
        context=CTX,
        name_value=main,
        on_property=prop,
        some_values_from=filler,
    )
    assert inst.as_triples == (
        (main, RDF.type, OWL.Restriction),
        (main, OWL.onProperty, prop),
        (main, OWL.someValuesFrom, filler),
    )


def test_object_has_self_as_triples() -> None:
    main = _uri("self-restriction")
    prop = _uri("knows")
    inst = ObjectHasSelf(context=CTX, name_value=main, on_property=prop)
    assert inst.as_triples == (
        (main, RDF.type, OWL.Restriction),
        (main, OWL.onProperty, prop),
        (main, OWL.hasSelf, Literal(True, datatype=XSD.boolean)),
    )


def test_object_min_cardinality_qualified_as_triples() -> None:
    main = _uri("min-q")
    prop = _uri("hasPart")
    ce = _uri("Wheel")
    n = _nn(4)
    inst = ObjectMinCardinalityQualified(
        context=CTX,
        name_value=main,
        on_property=prop,
        min_qualified_cardinality=n,
        on_class=ce,
    )
    assert inst.as_triples == (
        (main, RDF.type, OWL.Restriction),
        (main, OWL.onProperty, prop),
        (main, OWL.minQualifiedCardinality, n),
        (main, OWL.onClass, ce),
    )


def test_data_all_values_from_as_triples() -> None:
    main = _uri("data-all")
    prop = _uri("age")
    rng = _uri("NonNegativeInteger")
    inst = DataAllValuesFrom(
        context=CTX,
        name_value=main,
        on_property=prop,
        all_values_from=rng,
    )
    assert inst.as_triples == (
        (main, RDF.type, OWL.Restriction),
        (main, OWL.onProperty, prop),
        (main, OWL.allValuesFrom, rng),
    )


def test_data_has_value_as_triples() -> None:
    main = _uri("data-has-value")
    prop = _uri("name")
    lit = Literal("Ada")
    inst = DataHasValue(
        context=CTX,
        name_value=main,
        on_property=prop,
        has_value=lit,
    )
    assert inst.as_triples == (
        (main, RDF.type, OWL.Restriction),
        (main, OWL.onProperty, prop),
        (main, OWL.hasValue, lit),
    )


def test_data_has_value_rejects_non_literal() -> None:
    with pytest.raises(ValidationError, match="literal"):
        DataHasValue(
            context=CTX,
            name_value=_uri("bad"),
            on_property=_uri("p"),
            has_value=_uri("not-a-literal"),
        )


def test_cardinality_rejects_wrong_datatype() -> None:
    with pytest.raises(ValidationError, match="nonNegativeInteger"):
        ObjectMinCardinality(
            context=CTX,
            name_value=_uri("bad"),
            on_property=_uri("p"),
            min_cardinality=Literal(1, datatype=XSD.integer),
        )


def test_object_some_values_from_round_trips_and_schema() -> None:
    inst = ObjectSomeValuesFrom(
        context=CTX,
        name_value=_uri("r"),
        on_property=_uri("op"),
        some_values_from=_uri("CE"),
    )
    _assert_python_json_round_trip(ObjectSomeValuesFrom, inst)
    _assert_model_json_schema_smoke(ObjectSomeValuesFrom, "ObjectSomeValuesFrom")
    assert inst.as_quads == tuple((*t, CTX) for t in inst.as_triples)


def _nn_card(n: int = 2) -> Literal:
    return _nn(n)


def _restriction_elements_solo() -> tuple[StructuralElement, ...]:
    """Restrictions whose RDF shape is unambiguous without property typing."""
    return (
        ObjectHasSelf(
            context=CTX,
            name_value=_uri("object-has-self"),
            on_property=_uri("knows"),
        ),
        ObjectHasValue(
            context=CTX,
            name_value=_uri("object-has-value"),
            on_property=_uri("hasFriend"),
            has_value=_uri("bob"),
        ),
        DataHasValue(
            context=CTX,
            name_value=_uri("data-has-value"),
            on_property=_uri("hasName"),
            has_value=Literal("Ada"),
        ),
        DataAllValuesFrom(
            context=CTX,
            name_value=_uri("data-all-values-from"),
            on_property=_uri("age"),
            all_values_from=_uri("AdultAge"),
        ),
        ObjectMinCardinalityQualified(
            context=CTX,
            name_value=_uri("object-min-q"),
            on_property=_uri("hasPart"),
            min_qualified_cardinality=_nn_card(1),
            on_class=_uri("Wheel"),
        ),
        ObjectMaxCardinalityQualified(
            context=CTX,
            name_value=_uri("object-max-q"),
            on_property=_uri("hasPart"),
            max_qualified_cardinality=_nn_card(4),
            on_class=_uri("Door"),
        ),
        ObjectExactCardinalityQualified(
            context=CTX,
            name_value=_uri("object-exact-q"),
            on_property=_uri("hasPart"),
            qualified_cardinality=_nn_card(2),
            on_class=_uri("Engine"),
        ),
        DataMinCardinalityQualified(
            context=CTX,
            name_value=_uri("data-min-q"),
            on_property=_uri("hasScore"),
            min_qualified_cardinality=_nn_card(1),
            on_data_range=_uri("ScoreRange"),
        ),
        DataMaxCardinalityQualified(
            context=CTX,
            name_value=_uri("data-max-q"),
            on_property=_uri("hasScore"),
            max_qualified_cardinality=_nn_card(3),
            on_data_range=_uri("ScoreRange"),
        ),
        DataExactCardinalityQualified(
            context=CTX,
            name_value=_uri("data-exact-q"),
            on_property=_uri("hasScore"),
            qualified_cardinality=_nn_card(2),
            on_data_range=_uri("ScoreRange"),
        ),
        DataMinCardinality(
            context=CTX,
            name_value=_uri("data-min"),
            on_property=_uri("hasScore"),
            min_cardinality=_nn_card(1),
        ),
        DataMaxCardinality(
            context=CTX,
            name_value=_uri("data-max"),
            on_property=_uri("hasScore"),
            max_cardinality=_nn_card(5),
        ),
        DataExactCardinality(
            context=CTX,
            name_value=_uri("data-exact"),
            on_property=_uri("hasScore"),
            cardinality=_nn_card(2),
        ),
    )


def _object_typed_restriction_pairs() -> tuple[
    tuple[StructuralElement, DeclarationObjectProperty],
    ...,
]:
    """Ambiguous object restrictions paired with an object-property declaration."""
    pairs: list[tuple[StructuralElement, DeclarationObjectProperty]] = []
    for name, ctor, kwargs in (
        (
            "object-some",
            ObjectSomeValuesFrom,
            {"some_values_from": _uri("Person")},
        ),
        (
            "object-all",
            ObjectAllValuesFrom,
            {"all_values_from": _uri("Person")},
        ),
        (
            "object-min",
            ObjectMinCardinality,
            {"min_cardinality": _nn_card(1)},
        ),
        (
            "object-max",
            ObjectMaxCardinality,
            {"max_cardinality": _nn_card(3)},
        ),
        (
            "object-exact",
            ObjectExactCardinality,
            {"cardinality": _nn_card(2)},
        ),
    ):
        prop = _uri(f"{name}-prop")
        restriction = ctor(
            context=CTX,
            name_value=_uri(name),
            on_property=prop,
            **kwargs,
        )
        declaration = DeclarationObjectProperty(context=CTX, name_value=prop)
        pairs.append((restriction, declaration))
    return tuple(pairs)


@pytest.mark.parametrize("element", _restriction_elements_solo())
def test_axiomatize_round_trips_unambiguous_restrictions(
    element: StructuralElement,
) -> None:
    actual = axiomatize(_graph_from_elements(element))
    assert len(actual) == 1
    assert type(actual[0]) is type(element)
    assert actual[0] == element


@pytest.mark.parametrize("pair", _object_typed_restriction_pairs())
def test_axiomatize_round_trips_object_restrictions_with_property_typing(
    pair: tuple[StructuralElement, DeclarationObjectProperty],
) -> None:
    restriction, declaration = pair
    actual = axiomatize(_graph_from_elements(restriction, declaration))
    assert len(actual) == 2
    by_type = {type(el): el for el in actual}
    assert by_type[type(restriction)] == restriction
    assert by_type[DeclarationObjectProperty] == declaration


def test_axiomatize_object_some_values_from_requires_object_property_typing() -> None:
    """Without property typing, unary someValuesFrom lifts as the data form."""
    restriction = ObjectSomeValuesFrom(
        context=CTX,
        name_value=_uri("ambiguous-some"),
        on_property=_uri("p"),
        some_values_from=_uri("CE"),
    )
    actual = axiomatize(_graph_from_elements(restriction))
    assert len(actual) == 1
    lifted = actual[0]
    assert lifted.as_triples == restriction.as_triples
    assert type(lifted).__name__ == "DataSomeValuesFrom"


def test_axiomatize_data_restriction_with_datatype_property_typing() -> None:
    restriction = DataMinCardinality(
        context=CTX,
        name_value=_uri("typed-data-min"),
        on_property=_uri("score"),
        min_cardinality=_nn_card(1),
    )
    declaration = DeclarationDataProperty(context=CTX, name_value=_uri("score"))
    actual = axiomatize(_graph_from_elements(restriction, declaration))
    by_type = {type(el): el for el in actual}
    assert by_type[DataMinCardinality] == restriction
    assert by_type[DeclarationDataProperty] == declaration
