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
from rdflib_reasoning.axiom.class_axiom import (
    ClassAssertion,
    DeclarationClass,
    SubClassOf,
)
from rdflib_reasoning.axiom.datatype import (
    DataAllValuesFrom,
    DataAllValuesFromNary,
    DataComplementOf,
    DataHasValue,
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
from rdflib_reasoning.axiom.declaration import (
    DeclarationDataProperty,
    DeclarationObjectProperty,
)
from rdflib_reasoning.axiom.object_expression import (
    DisjointClasses,
    DisjointClassesNary,
    DisjointUnion,
    EquivalentClasses,
    ObjectComplementOf,
    ObjectIntersectionOf,
    ObjectInverseOf,
    ObjectOneOf,
    ObjectUnionOf,
)
from rdflib_reasoning.axiom.property_axiom import (
    DataPropertyAssertion,
    DataPropertyDomain,
    DataPropertyRange,
    DatatypeDefinition,
    DifferentIndividuals,
    DifferentIndividualsNary,
    DisjointDataProperties,
    DisjointDataPropertiesNary,
    DisjointObjectProperties,
    DisjointObjectPropertiesNary,
    EquivalentDataProperties,
    EquivalentObjectProperties,
    HasKey,
    InverseObjectProperties,
    ObjectPropertyAssertion,
    ObjectPropertyDomain,
    ObjectPropertyRange,
    SameIndividual,
    SubDataPropertyOf,
    SubObjectPropertyOf,
    SubObjectPropertyOfChain,
)
from rdflib_reasoning.axiom.restriction import ObjectSomeValuesFrom
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
        DataAllValuesFrom(
            context=CTX,
            name_value=_uri("all-values-from-unary"),
            on_property=_uri("p-all"),
            all_values_from=_uri("range-all"),
        ),
        DataHasValue(
            context=CTX,
            name_value=_uri("data-has-value"),
            on_property=_uri("p-hv"),
            has_value=Literal("Ada"),
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


def _ternary_seq(
    head_name: str,
    mid_name: str,
    tail_name: str,
    first: Node,
    second: Node,
    third: Node,
) -> Seq:
    return Seq(
        context=CTX,
        entries=(
            SeqEntry(cell=_uri(head_name), value=first),
            SeqEntry(cell=_uri(mid_name), value=second),
            SeqEntry(cell=_uri(tail_name), value=third),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )


def _current_object_expression_elements() -> tuple[StructuralElement, ...]:
    return (
        ObjectIntersectionOf(
            context=CTX,
            name_value=_uri("object-intersection"),
            intersection_of=_binary_seq(
                "obj-intersection-list",
                "obj-intersection-list-tail",
                _uri("CE-a"),
                _uri("CE-b"),
            ),
        ),
        ObjectUnionOf(
            context=CTX,
            name_value=_uri("object-union"),
            union_of=_binary_seq(
                "obj-union-list",
                "obj-union-list-tail",
                _uri("CE-c"),
                _uri("CE-d"),
            ),
        ),
        ObjectComplementOf(
            context=CTX,
            name_value=_uri("object-complement"),
            complement_of=_uri("CE-inner"),
        ),
        ObjectOneOf(
            context=CTX,
            name_value=_uri("object-one-of"),
            one_of=_binary_seq(
                "obj-one-of-list",
                "obj-one-of-list-tail",
                _uri("alice"),
                _uri("bob"),
            ),
        ),
        ObjectInverseOf(
            context=CTX,
            # Blank-node subject distinguishes ObjectInverseOf from
            # InverseObjectProperties (IRI-subject owl:inverseOf).
            name_value=BNode(),
            inverse_of=_uri("parentOf"),
        ),
        DisjointClasses(
            context=CTX,
            class_expression_1=_uri("Boy"),
            class_expression_2=_uri("Girl"),
        ),
        EquivalentClasses(
            context=CTX,
            class_expression_1=_uri("BoyEq"),
            class_expression_2=_uri("MaleChild"),
        ),
        DisjointClassesNary(
            context=CTX,
            name_value=_uri("all-disjoint-classes"),
            members=_ternary_seq(
                "adc-list",
                "adc-list-mid",
                "adc-list-tail",
                _uri("CE-x"),
                _uri("CE-y"),
                _uri("CE-z"),
            ),
        ),
        DisjointUnion(
            context=CTX,
            union_class=_uri("Child"),
            disjoint_union_of=_binary_seq(
                "du-list",
                "du-list-tail",
                _uri("Boy"),
                _uri("Girl"),
            ),
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


@pytest.mark.parametrize("element", _current_object_expression_elements())
def test_axiomatize_round_trips_current_object_expression_elements(
    element: StructuralElement,
) -> None:
    actual = axiomatize(_graph_from_element(element))

    assert len(actual) == 1
    assert type(actual[0]) is type(element)
    assert actual[0] == element


def _current_property_axiom_elements() -> tuple[StructuralElement, ...]:
    return (
        SubObjectPropertyOf(
            context=CTX,
            sub_object_property_expression=_uri("childProp"),
            super_object_property_expression=_uri("parentProp"),
        ),
        SubObjectPropertyOfChain(
            context=CTX,
            object_property_expression=_uri("hasUncle"),
            property_chain=_binary_seq(
                "chain-list",
                "chain-list-tail",
                _uri("hasParent"),
                _uri("hasBrother"),
            ),
        ),
        ObjectPropertyDomain(
            context=CTX,
            object_property_expression=_uri("worksFor"),
            class_expression=_uri("Person"),
        ),
        ObjectPropertyRange(
            context=CTX,
            object_property_expression=_uri("worksForRange"),
            class_expression=_uri("Organization"),
        ),
        InverseObjectProperties(
            context=CTX,
            object_property_expression_1=_uri("hasParent"),
            object_property_expression_2=_uri("hasChild"),
        ),
        EquivalentObjectProperties(
            context=CTX,
            object_property_expression_1=_uri("eqPropA"),
            object_property_expression_2=_uri("eqPropB"),
        ),
        DisjointObjectProperties(
            context=CTX,
            object_property_expression_1=_uri("disjointP1"),
            object_property_expression_2=_uri("disjointP2"),
        ),
        DisjointObjectPropertiesNary(
            context=CTX,
            name_value=_uri("all-disjoint-object-props"),
            members=_ternary_seq(
                "adop-list",
                "adop-list-mid",
                "adop-list-tail",
                _uri("op-a"),
                _uri("op-b"),
                _uri("op-c"),
            ),
        ),
        HasKey(
            context=CTX,
            class_expression=_uri("KeyedPerson"),
            key_properties=_binary_seq(
                "key-list",
                "key-list-tail",
                _uri("hasSSN"),
                _uri("nationalId"),
            ),
        ),
        DifferentIndividuals(
            context=CTX,
            individual_1=_uri("alice"),
            individual_2=_uri("bob"),
        ),
        SameIndividual(
            context=CTX,
            individual_1=_uri("meg"),
            individual_2=_uri("megan"),
        ),
        DifferentIndividualsNary(
            context=CTX,
            name_value=_uri("all-different"),
            members=_ternary_seq(
                "diff-list",
                "diff-list-mid",
                "diff-list-tail",
                _uri("aliceN"),
                _uri("bobN"),
                _uri("carolN"),
            ),
        ),
    )


@pytest.mark.parametrize("element", _current_property_axiom_elements())
def test_axiomatize_round_trips_current_property_axiom_elements(
    element: StructuralElement,
) -> None:
    actual = axiomatize(_graph_from_element(element))

    assert len(actual) == 1
    assert type(actual[0]) is type(element)
    assert actual[0] == element


def test_axiomatize_lifts_data_property_axioms_with_declarations() -> None:
    """Data forms share RDF with object forms; DatatypeProperty tips the scale."""
    decl_a = DeclarationDataProperty(context=CTX, name_value=_uri("age"))
    decl_b = DeclarationDataProperty(context=CTX, name_value=_uri("weight"))
    sub = SubDataPropertyOf(
        context=CTX,
        sub_data_property_expression=decl_a.name,
        super_data_property_expression=_uri("measure"),
    )
    domain = DataPropertyDomain(
        context=CTX,
        data_property_expression=decl_a.name,
        class_expression=_uri("Person"),
    )
    range_ = DataPropertyRange(
        context=CTX,
        data_property_expression=decl_a.name,
        data_range=_uri("nonNegInt"),
    )
    disjoint = DisjointDataProperties(
        context=CTX,
        data_property_expression_1=decl_a.name,
        data_property_expression_2=decl_b.name,
    )
    equivalent = EquivalentDataProperties(
        context=CTX,
        data_property_expression_1=decl_a.name,
        data_property_expression_2=decl_b.name,
    )
    disjoint_nary = DisjointDataPropertiesNary(
        context=CTX,
        name_value=_uri("all-disjoint-data-props"),
        members=_ternary_seq(
            "addp-list",
            "addp-list-mid",
            "addp-list-tail",
            decl_a.name,
            decl_b.name,
            _uri("height"),
        ),
    )
    height_decl = DeclarationDataProperty(context=CTX, name_value=_uri("height"))
    graph = Graph(identifier=CTX)
    for element in (
        decl_a,
        decl_b,
        height_decl,
        sub,
        domain,
        range_,
        disjoint,
        equivalent,
        disjoint_nary,
    ):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)
    kinds = {type(element) for element in actual}
    assert SubDataPropertyOf in kinds
    assert DataPropertyDomain in kinds
    assert DataPropertyRange in kinds
    assert DisjointDataProperties in kinds
    assert EquivalentDataProperties in kinds
    assert DisjointDataPropertiesNary in kinds
    assert DeclarationDataProperty in kinds


def test_axiomatize_datatype_definition_with_datatype_tip() -> None:
    """``owl:equivalentClass`` with ``rdfs:Datatype`` tip lifts as DatatypeDefinition."""
    decl = DeclarationDatatype(context=CTX, name_value=_uri("AdultAge"))
    definition = DatatypeDefinition(
        context=CTX,
        datatype=decl.name,
        data_range=_uri("adultAgeRange"),
    )
    graph = Graph(identifier=CTX)
    for element in (decl, definition):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)
    kinds = {type(element) for element in actual}
    assert DatatypeDefinition in kinds
    assert DeclarationDatatype in kinds
    found = next(e for e in actual if isinstance(e, DatatypeDefinition))
    assert found == definition


def test_axiomatize_equivalent_class_chain_yields_binary_axioms() -> None:
    """A chain of ``owl:equivalentClass`` triples lifts as one binary axiom each."""
    ce1 = _uri("CE1")
    ce2 = _uri("CE2")
    ce3 = _uri("CE3")
    graph = _graph_from_triples(
        (
            (ce1, OWL.equivalentClass, ce2),
            (ce2, OWL.equivalentClass, ce3),
        )
    )

    actual = axiomatize(graph)

    assert len(actual) == 2
    assert all(isinstance(element, EquivalentClasses) for element in actual)
    pairs = {
        (element.class_expression_1, element.class_expression_2) for element in actual
    }
    assert pairs == {(ce1, ce2), (ce2, ce3)}


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
            # Annotation assertions are outside current axiomatization coverage.
            (_uri("subject"), _uri("comment"), Literal("note")),
        ),
        (
            # ClassAssertion requires a known CE; undeclared type objects remain
            # unconsumed under the strict CE gate.
            (_uri("alice"), RDF.type, _uri("Person")),
        ),
        (
            # Negative property assertions are outside current coverage.
            (_uri("npa"), RDF.type, OWL.NegativePropertyAssertion),
        ),
    ),
)
def test_axiomatize_fails_for_unsupported_structures(
    triples: tuple[tuple[IdentifiedNode, URIRef, Node], ...],
) -> None:
    with pytest.raises(UnsupportedGraphError):
        axiomatize(_graph_from_triples(triples))


def test_axiomatize_class_assertion_with_declaration_tip() -> None:
    declaration = DeclarationClass(context=CTX, name_value=_uri("Person"))
    assertion = ClassAssertion(
        context=CTX,
        individual=_uri("alice"),
        class_expression=declaration.name,
    )
    graph = Graph(identifier=CTX)
    for element in (declaration, assertion):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)
    kinds = {type(element) for element in actual}
    assert DeclarationClass in kinds
    assert ClassAssertion in kinds
    found = next(e for e in actual if isinstance(e, ClassAssertion))
    assert found == assertion


def test_axiomatize_class_assertion_to_object_restriction() -> None:
    restriction = ObjectSomeValuesFrom(
        context=CTX,
        name_value=BNode("parentRestriction"),
        on_property=_uri("hasParent"),
        some_values_from=_uri("Person"),
    )
    assertion = ClassAssertion(
        context=CTX,
        individual=_uri("alice"),
        class_expression=restriction.name,
    )
    # Object-property tip so unary someValuesFrom lifts as Object*, not Data*.
    prop_decl = DeclarationObjectProperty(
        context=CTX,
        name_value=_uri("hasParent"),
    )
    graph = Graph(identifier=CTX)
    for element in (prop_decl, restriction, assertion):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)
    kinds = {type(element) for element in actual}
    assert ObjectSomeValuesFrom in kinds
    assert ClassAssertion in kinds
    found = next(e for e in actual if isinstance(e, ClassAssertion))
    assert found.individual == assertion.individual
    assert found.class_expression == restriction.name


def test_axiomatize_rdf_type_owl_class_is_declaration_not_assertion() -> None:
    declaration = DeclarationClass(context=CTX, name_value=_uri("Person"))
    actual = axiomatize(_graph_from_element(declaration))
    assert actual == (declaration,)
    assert not any(isinstance(element, ClassAssertion) for element in actual)


def test_axiomatize_object_property_assertion_with_declaration_tip() -> None:
    decl = DeclarationObjectProperty(context=CTX, name_value=_uri("knows"))
    assertion = ObjectPropertyAssertion(
        context=CTX,
        object_property_expression=decl.name,
        individual=_uri("alice"),
        value=_uri("bob"),
    )
    graph = Graph(identifier=CTX)
    for element in (decl, assertion):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)
    kinds = {type(element) for element in actual}
    assert DeclarationObjectProperty in kinds
    assert ObjectPropertyAssertion in kinds
    found = next(e for e in actual if isinstance(e, ObjectPropertyAssertion))
    assert found == assertion


def test_axiomatize_object_property_assertion_from_subproperty_operand() -> None:
    decl_child = DeclarationObjectProperty(context=CTX, name_value=_uri("knowsWell"))
    decl_parent = DeclarationObjectProperty(context=CTX, name_value=_uri("knows"))
    sub = SubObjectPropertyOf(
        context=CTX,
        sub_object_property_expression=decl_child.name,
        super_object_property_expression=decl_parent.name,
    )
    assertion = ObjectPropertyAssertion(
        context=CTX,
        object_property_expression=decl_child.name,
        individual=_uri("alice"),
        value=_uri("bob"),
    )
    graph = Graph(identifier=CTX)
    for element in (decl_child, decl_parent, sub, assertion):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)
    found = next(e for e in actual if isinstance(e, ObjectPropertyAssertion))
    assert found == assertion


def test_axiomatize_object_property_assertion_from_object_inverse_of() -> None:
    inv = ObjectInverseOf(
        context=CTX,
        name_value=BNode("invKnows"),
        inverse_of=_uri("knows"),
    )
    assertion = ObjectPropertyAssertion(
        context=CTX,
        object_property_expression=inv.name,
        individual=_uri("alice"),
        value=_uri("bob"),
    )
    graph = Graph(identifier=CTX)
    for element in (inv, assertion):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)
    kinds = {type(element) for element in actual}
    assert ObjectInverseOf in kinds
    assert ObjectPropertyAssertion in kinds
    found = next(e for e in actual if isinstance(e, ObjectPropertyAssertion))
    assert found == assertion


def test_axiomatize_undeclared_resource_predicate_is_unsupported() -> None:
    with pytest.raises(UnsupportedGraphError):
        axiomatize(_graph_from_triples(((_uri("alice"), _uri("knows"), _uri("bob")),)))


def test_axiomatize_known_ope_with_literal_object_not_object_assertion() -> None:
    """Literal objects are not ObjectPropertyAssertion even with a known OPE."""
    decl = DeclarationObjectProperty(context=CTX, name_value=_uri("labelProp"))
    graph = Graph(identifier=CTX)
    for triple in decl.as_triples:
        graph.add(triple)
    graph.add((_uri("alice"), decl.name, Literal("note")))

    with pytest.raises(UnsupportedGraphError):
        axiomatize(graph)


def test_axiomatize_data_property_assertion_with_declaration_tip() -> None:
    decl = DeclarationDataProperty(context=CTX, name_value=_uri("age"))
    assertion = DataPropertyAssertion(
        context=CTX,
        data_property_expression=decl.name,
        individual=_uri("alice"),
        value=Literal(42, datatype=XSD.integer),
    )
    graph = Graph(identifier=CTX)
    for element in (decl, assertion):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)
    kinds = {type(element) for element in actual}
    assert DeclarationDataProperty in kinds
    assert DataPropertyAssertion in kinds
    found = next(e for e in actual if isinstance(e, DataPropertyAssertion))
    assert found == assertion


def test_axiomatize_data_property_assertion_from_subproperty_operand() -> None:
    decl_child = DeclarationDataProperty(context=CTX, name_value=_uri("ageYears"))
    decl_parent = DeclarationDataProperty(context=CTX, name_value=_uri("age"))
    sub = SubDataPropertyOf(
        context=CTX,
        sub_data_property_expression=decl_child.name,
        super_data_property_expression=decl_parent.name,
    )
    assertion = DataPropertyAssertion(
        context=CTX,
        data_property_expression=decl_child.name,
        individual=_uri("alice"),
        value=Literal(30, datatype=XSD.integer),
    )
    graph = Graph(identifier=CTX)
    for element in (decl_child, decl_parent, sub, assertion):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)
    found = next(e for e in actual if isinstance(e, DataPropertyAssertion))
    assert found == assertion


def test_axiomatize_undeclared_literal_predicate_is_unsupported() -> None:
    with pytest.raises(UnsupportedGraphError):
        axiomatize(
            _graph_from_triples(
                ((_uri("alice"), _uri("age"), Literal(42, datatype=XSD.integer)),)
            )
        )


def test_axiomatize_known_dpe_with_resource_object_not_data_assertion() -> None:
    """Resource objects are not DataPropertyAssertion even with a known DPE."""
    decl = DeclarationDataProperty(context=CTX, name_value=_uri("friend"))
    graph = Graph(identifier=CTX)
    for triple in decl.as_triples:
        graph.add(triple)
    graph.add((_uri("alice"), decl.name, _uri("bob")))

    with pytest.raises(UnsupportedGraphError):
        axiomatize(graph)


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


def test_axiomatize_fails_for_literal_object_one_of_member() -> None:
    graph = _graph_from_triples(
        (
            (_uri("bad-obj-one-of"), RDF.type, OWL.Class),
            (_uri("bad-obj-one-of"), OWL.oneOf, _uri("bad-obj-one-of-list")),
            (_uri("bad-obj-one-of-list"), RDF.first, Literal("not-an-individual")),
            (_uri("bad-obj-one-of-list"), RDF.rest, RDF.nil),
        )
    )

    with pytest.raises(MalformedGraphError, match="MUST be individuals"):
        axiomatize(graph)


def test_axiomatize_fails_for_under_arity_object_intersection() -> None:
    graph = _graph_from_triples(
        (
            (_uri("small-obj-intersection"), RDF.type, OWL.Class),
            (
                _uri("small-obj-intersection"),
                OWL.intersectionOf,
                _uri("one-cell-obj-list"),
            ),
            (_uri("one-cell-obj-list"), RDF.first, _uri("CE")),
            (_uri("one-cell-obj-list"), RDF.rest, RDF.nil),
        )
    )

    with pytest.raises(MalformedGraphError, match="n >= 2"):
        axiomatize(graph)


def test_axiomatize_fails_for_under_arity_disjoint_classes_nary() -> None:
    graph = _graph_from_triples(
        (
            (_uri("small-adc"), RDF.type, OWL.AllDisjointClasses),
            (_uri("small-adc"), OWL.members, _uri("adc-two-list")),
            (_uri("adc-two-list"), RDF.first, _uri("CE-a")),
            (_uri("adc-two-list"), RDF.rest, _uri("adc-two-list-tail")),
            (_uri("adc-two-list-tail"), RDF.first, _uri("CE-b")),
            (_uri("adc-two-list-tail"), RDF.rest, RDF.nil),
        )
    )

    with pytest.raises(MalformedGraphError, match="n > 2"):
        axiomatize(graph)


def test_axiomatize_object_expression_before_declaration_class_fallback() -> None:
    intersection = ObjectIntersectionOf(
        context=CTX,
        name_value=_uri("rich-class"),
        intersection_of=_binary_seq(
            "rich-list",
            "rich-list-tail",
            _uri("CE-a"),
            _uri("CE-b"),
        ),
    )
    plain = DeclarationClass(context=CTX, name_value=_uri("plain-class"))
    graph = Graph(identifier=CTX)
    for element in (intersection, plain):
        for triple in element.as_triples:
            graph.add(triple)

    actual = axiomatize(graph)

    assert len(actual) == 2
    kinds = {type(element) for element in actual}
    assert kinds == {ObjectIntersectionOf, DeclarationClass}
    richer = next(e for e in actual if isinstance(e, ObjectIntersectionOf))
    assert richer == intersection
