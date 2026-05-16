import pytest
from rdflib import (
    OWL,
    RDF,
    RDFS,
    XSD,
    BNode,
    Graph,
    IdentifiedNode,
    Literal,
    Node,
    URIRef,
)
from rdflib_reasoning.axiom.axiomatize import (
    MalformedGraphError,
    UnsupportedGraphError,
    axiomatize,
)
from rdflib_reasoning.axiom.class_axiom import DeclarationClass, SubClassOf
from rdflib_reasoning.axiom.datatype import (
    DataAllValuesFromNary,
    DataComplementOf,
    DataIntersectionOf,
    DataOneOf,
    DataSomeValuesFrom,
    DataSomeValuesFromNary,
    DatatypeRestriction,
    DataUnionOf,
    DeclarationDatatype,
    FacetEntry,
    FacetList,
)
from rdflib_reasoning.axiom.structural_element import Seq, SeqEntry, StructuralElement

EX = "http://example.com/"
CTX = URIRef(f"{EX}g")


def _uri(name: str) -> URIRef:
    return URIRef(f"{EX}{name}")


def _graph_from_triples(
    triples: tuple[tuple[IdentifiedNode, URIRef, Node], ...],
) -> Graph:
    graph = Graph(identifier=CTX)
    for triple in triples:
        graph.add(triple)
    return graph


def _graph_from_element(element: StructuralElement) -> Graph:
    graph = Graph(identifier=element.context)
    for triple in element.as_triples:
        graph.add(triple)
    return graph


def _binary_seq(head_name: str, mid_name: str, first: Node, second: Node) -> Seq:
    return Seq(
        context=CTX,
        entries=(
            SeqEntry(cell=_uri(head_name), value=first),
            SeqEntry(cell=_uri(mid_name), value=second),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )


def _current_datatype_elements() -> tuple[StructuralElement, ...]:
    facet_list = FacetList(
        context=CTX,
        entries=(
            FacetEntry(
                cell=_uri("facet-list"),
                anchor=_uri("facet-anchor"),
                facet=XSD.minInclusive,
                value=Literal(1, datatype=XSD.integer),
            ),
            FacetEntry(cell=RDF.nil, anchor=None, facet=None, value=None),
        ),
    )
    property_seq = _binary_seq(
        "prop-list",
        "prop-list-tail",
        _uri("p1"),
        _uri("p2"),
    )
    return (
        DeclarationDatatype(context=CTX, name_value=_uri("declared-datatype")),
        DataIntersectionOf(
            context=CTX,
            name_value=_uri("data-intersection"),
            intersection_of=_binary_seq(
                "intersection-list",
                "intersection-list-tail",
                _uri("dt-a"),
                _uri("dt-b"),
            ),
        ),
        DataUnionOf(
            context=CTX,
            name_value=_uri("data-union"),
            union_of=_binary_seq(
                "union-list",
                "union-list-tail",
                _uri("dt-c"),
                _uri("dt-d"),
            ),
        ),
        DataComplementOf(
            context=CTX,
            name_value=_uri("data-complement"),
            complement_of=_uri("dt-inner"),
        ),
        DataOneOf(
            context=CTX,
            name_value=_uri("data-one-of"),
            one_of=_binary_seq(
                "one-of-list",
                "one-of-list-tail",
                Literal("red"),
                Literal(7, datatype=XSD.integer),
            ),
        ),
        DatatypeRestriction(
            context=CTX,
            name_value=_uri("datatype-restriction"),
            on_datatype=XSD.integer,
            with_restrictions=facet_list,
        ),
        DataSomeValuesFrom(
            context=CTX,
            name_value=_uri("some-values-from"),
            on_property=_uri("p"),
            some_values_from=_uri("range"),
        ),
        DataSomeValuesFromNary(
            context=CTX,
            name_value=_uri("some-values-from-nary"),
            on_properties=property_seq,
            some_values_from=_uri("range-nary"),
        ),
        DataAllValuesFromNary(
            context=CTX,
            name_value=_uri("all-values-from-nary"),
            on_properties=property_seq,
            all_values_from=_uri("range-nary"),
        ),
    )


def _current_class_elements() -> tuple[StructuralElement, ...]:
    return (
        DeclarationClass(context=CTX, name_value=_uri("DeclaredClass")),
        SubClassOf(
            context=CTX,
            sub_class_expression=_uri("ChildClass"),
            super_class_expression=_uri("ParentClass"),
        ),
    )


@pytest.mark.parametrize("element", _current_datatype_elements())
def test_axiomatize_round_trips_current_datatype_elements(
    element: StructuralElement,
) -> None:
    actual = axiomatize(_graph_from_element(element))

    assert len(actual) == 1
    assert type(actual[0]) is type(element)
    assert actual[0] == element


@pytest.mark.parametrize("element", _current_class_elements())
def test_axiomatize_round_trips_current_class_elements(
    element: StructuralElement,
) -> None:
    actual = axiomatize(_graph_from_element(element))

    assert len(actual) == 1
    assert type(actual[0]) is type(element)
    assert actual[0] == element


def test_axiomatize_orders_elements_and_falls_back_to_declaration() -> None:
    declaration_b = DeclarationDatatype(context=CTX, name_value=_uri("b-datatype"))
    declaration_a = DeclarationDatatype(context=CTX, name_value=_uri("a-datatype"))
    complement = DataComplementOf(
        context=CTX,
        name_value=_uri("c-complement"),
        complement_of=declaration_a.name,
    )
    graph = Graph(identifier=CTX)
    for element in (complement, declaration_b, declaration_a):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)

    assert tuple(element.name for element in actual) == (
        declaration_a.name,
        declaration_b.name,
        complement.name,
    )
    assert isinstance(actual[0], DeclarationDatatype)
    assert isinstance(actual[1], DeclarationDatatype)
    assert isinstance(actual[2], DataComplementOf)


def test_axiomatize_does_not_mutate_caller_graph() -> None:
    element = DataComplementOf(
        context=CTX,
        name_value=_uri("immutable-complement"),
        complement_of=_uri("immutable-inner"),
    )
    graph = _graph_from_element(element)
    before = set(graph)

    assert axiomatize(graph) == (element,)
    assert set(graph) == before


@pytest.mark.parametrize(
    "triples",
    (
        (
            (_uri("restriction"), RDF.type, OWL.Restriction),
            (_uri("restriction"), OWL.onProperty, _uri("object-property")),
            (_uri("restriction"), OWL.someValuesFrom, _uri("ObjectClass")),
            (_uri("object-property"), RDF.type, OWL.ObjectProperty),
        ),
        (
            (_uri("unary-all"), RDF.type, OWL.Restriction),
            (_uri("unary-all"), OWL.onProperty, _uri("p")),
            (_uri("unary-all"), OWL.allValuesFrom, _uri("range")),
        ),
    ),
)
def test_axiomatize_fails_for_unsupported_structures(
    triples: tuple[tuple[IdentifiedNode, URIRef, Node], ...],
) -> None:
    with pytest.raises(UnsupportedGraphError):
        axiomatize(_graph_from_triples(triples))


def test_axiomatize_lifts_multiple_subclass_axioms_with_same_subject() -> None:
    subclass_a = SubClassOf(
        context=CTX,
        sub_class_expression=_uri("ChildClass"),
        super_class_expression=_uri("ParentA"),
    )
    subclass_b = SubClassOf(
        context=CTX,
        sub_class_expression=_uri("ChildClass"),
        super_class_expression=_uri("ParentB"),
    )
    graph = Graph(identifier=CTX)
    for element in (subclass_b, subclass_a):
        for triple in element.as_triples:
            graph.add(triple)

    assert axiomatize(graph) == (subclass_a, subclass_b)


def test_axiomatize_lifts_subclass_of_data_restriction_as_separate_partition() -> None:
    restriction_node = BNode("ageRestriction")
    declaration = DeclarationClass(context=CTX, name_value=_uri("Adult"))
    restriction = DataSomeValuesFrom(
        context=CTX,
        name_value=restriction_node,
        on_property=_uri("age"),
        some_values_from=_uri("adultAgeDatatype"),
    )
    subclass = SubClassOf(
        context=CTX,
        sub_class_expression=declaration.name,
        super_class_expression=restriction.name,
    )
    graph = Graph(identifier=CTX)
    for element in (declaration, restriction, subclass):
        for triple in element.as_triples:
            graph.add(triple)

    assert axiomatize(graph) == (subclass, declaration, restriction)


def test_axiomatize_fails_for_literal_subclass_target() -> None:
    graph = _graph_from_triples(
        ((_uri("ChildClass"), RDFS.subClassOf, Literal("not-a-class-node")),)
    )

    with pytest.raises(MalformedGraphError, match="super class expression"):
        axiomatize(graph)


def test_axiomatize_fails_for_broken_rdf_list() -> None:
    graph = _graph_from_triples(
        (
            (_uri("broken-one-of"), RDF.type, RDFS.Datatype),
            (_uri("broken-one-of"), OWL.oneOf, _uri("broken-list")),
            (_uri("broken-list"), RDF.first, Literal("x")),
        )
    )

    with pytest.raises(MalformedGraphError, match="rdf:rest"):
        axiomatize(graph)


def test_axiomatize_fails_for_shared_list_head() -> None:
    graph = _graph_from_triples(
        (
            (_uri("one-of-a"), RDF.type, RDFS.Datatype),
            (_uri("one-of-a"), OWL.oneOf, _uri("shared-list")),
            (_uri("one-of-b"), RDF.type, RDFS.Datatype),
            (_uri("one-of-b"), OWL.oneOf, _uri("shared-list")),
            (_uri("shared-list"), RDF.first, Literal("x")),
            (_uri("shared-list"), RDF.rest, RDF.nil),
        )
    )

    with pytest.raises(MalformedGraphError, match="already owned"):
        axiomatize(graph)


def test_axiomatize_fails_for_under_arity_data_intersection() -> None:
    graph = _graph_from_triples(
        (
            (_uri("small-intersection"), RDF.type, RDFS.Datatype),
            (_uri("small-intersection"), OWL.intersectionOf, _uri("one-cell-list")),
            (_uri("one-cell-list"), RDF.first, _uri("dt")),
            (_uri("one-cell-list"), RDF.rest, RDF.nil),
        )
    )

    with pytest.raises(MalformedGraphError, match="n >= 2"):
        axiomatize(graph)


def test_axiomatize_fails_for_malformed_facet_anchor() -> None:
    graph = _graph_from_triples(
        (
            (_uri("restricted"), RDF.type, RDFS.Datatype),
            (_uri("restricted"), OWL.onDatatype, XSD.integer),
            (_uri("restricted"), OWL.withRestrictions, _uri("facet-list")),
            (_uri("facet-list"), RDF.first, _uri("facet-anchor")),
            (_uri("facet-list"), RDF.rest, RDF.nil),
        )
    )

    with pytest.raises(MalformedGraphError, match="facet predicate/value"):
        axiomatize(graph)


def test_axiomatize_fails_for_nonliteral_data_one_of_member() -> None:
    graph = _graph_from_triples(
        (
            (_uri("bad-one-of"), RDF.type, RDFS.Datatype),
            (_uri("bad-one-of"), OWL.oneOf, _uri("bad-one-of-list")),
            (_uri("bad-one-of-list"), RDF.first, _uri("not-a-literal")),
            (_uri("bad-one-of-list"), RDF.rest, RDF.nil),
        )
    )

    with pytest.raises(MalformedGraphError, match="MUST be literals"):
        axiomatize(graph)
