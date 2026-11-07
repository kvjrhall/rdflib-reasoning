"""Unit tests for property, key, and individual-difference structural axioms."""

import pytest
from pydantic import BaseModel, ValidationError
from rdflib import OWL, RDF, RDFS, BNode, URIRef
from rdflib_reasoning.axiom.property_axiom import (
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
    ObjectPropertyDomain,
    ObjectPropertyRange,
    SameIndividual,
    SubDataPropertyOf,
    SubObjectPropertyOf,
    SubObjectPropertyOfChain,
)
from rdflib_reasoning.axiom.structural_element import Seq, SeqEntry, StructuralElement


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


def _assert_round_trips_preserve_as_triples(
    model_cls: type[BaseModel],
    instance: StructuralElement,
) -> None:
    """Round-trip Seq-backed axioms preserving RDF projection (entries may retype)."""
    from_py = model_cls.model_validate(instance.model_dump())
    assert isinstance(from_py, StructuralElement)
    assert from_py.as_triples == instance.as_triples
    from_js = model_cls.model_validate_json(instance.model_dump_json())
    assert isinstance(from_js, StructuralElement)
    assert from_js.as_triples == instance.as_triples


def _binary_seq(ctx: URIRef, first: URIRef, second: URIRef) -> Seq:
    return Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=URIRef("http://example.com/list"), value=first),
            SeqEntry(cell=URIRef("http://example.com/list-tail"), value=second),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )


def _ternary_seq(ctx: URIRef, first: URIRef, second: URIRef, third: URIRef) -> Seq:
    return Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=URIRef("http://example.com/list"), value=first),
            SeqEntry(cell=URIRef("http://example.com/list-mid"), value=second),
            SeqEntry(cell=URIRef("http://example.com/list-tail"), value=third),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )


def test_sub_object_property_of_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    child = URIRef("http://example.com/childProp")
    parent = URIRef("http://example.com/parentProp")
    axiom = SubObjectPropertyOf(
        context=ctx,
        sub_object_property_expression=child,
        super_object_property_expression=parent,
    )

    assert axiom.name == child
    assert axiom.as_triples == ((child, RDFS.subPropertyOf, parent),)
    assert axiom.as_quads == tuple((*t, ctx) for t in axiom.as_triples)
    _assert_python_json_round_trip(SubObjectPropertyOf, axiom)
    _assert_model_json_schema_smoke(SubObjectPropertyOf, "SubObjectPropertyOf")


def test_sub_data_property_of_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    child = URIRef("http://example.com/childData")
    parent = URIRef("http://example.com/parentData")
    axiom = SubDataPropertyOf(
        context=ctx,
        sub_data_property_expression=child,
        super_data_property_expression=parent,
    )

    assert axiom.as_triples == ((child, RDFS.subPropertyOf, parent),)
    _assert_python_json_round_trip(SubDataPropertyOf, axiom)
    _assert_model_json_schema_smoke(SubDataPropertyOf, "SubDataPropertyOf")


def test_sub_object_property_of_chain_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    ope = URIRef("http://example.com/hasUncle")
    chain = _binary_seq(
        ctx,
        URIRef("http://example.com/hasParent"),
        URIRef("http://example.com/hasBrother"),
    )
    axiom = SubObjectPropertyOfChain(
        context=ctx,
        object_property_expression=ope,
        property_chain=chain,
    )

    assert axiom.name == ope
    assert (ope, OWL.propertyChainAxiom, chain.name) in axiom.as_triples
    assert set(chain.as_triples).issubset(set(axiom.as_triples))
    _assert_round_trips_preserve_as_triples(SubObjectPropertyOfChain, axiom)
    _assert_model_json_schema_smoke(
        SubObjectPropertyOfChain, "SubObjectPropertyOfChain"
    )


def test_sub_object_property_of_chain_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    with pytest.raises(ValidationError, match="n >= 2"):
        SubObjectPropertyOfChain(
            context=ctx,
            object_property_expression=URIRef("http://example.com/p"),
            property_chain=Seq(
                context=ctx,
                entries=(
                    SeqEntry(
                        cell=URIRef("http://example.com/list"),
                        value=URIRef("http://example.com/only"),
                    ),
                    SeqEntry(cell=RDF.nil, value=None),
                ),
            ),
        )


def test_object_property_domain_and_range() -> None:
    ctx = URIRef("http://example.com/g")
    prop = URIRef("http://example.com/worksFor")
    domain = ObjectPropertyDomain(
        context=ctx,
        object_property_expression=prop,
        class_expression=URIRef("http://example.com/Person"),
    )
    range_ = ObjectPropertyRange(
        context=ctx,
        object_property_expression=prop,
        class_expression=URIRef("http://example.com/Organization"),
    )

    assert domain.as_triples == (
        (prop, RDFS.domain, URIRef("http://example.com/Person")),
    )
    assert range_.as_triples == (
        (prop, RDFS.range, URIRef("http://example.com/Organization")),
    )
    _assert_python_json_round_trip(ObjectPropertyDomain, domain)
    _assert_python_json_round_trip(ObjectPropertyRange, range_)


def test_data_property_domain_and_range() -> None:
    ctx = URIRef("http://example.com/g")
    prop = URIRef("http://example.com/age")
    domain = DataPropertyDomain(
        context=ctx,
        data_property_expression=prop,
        class_expression=URIRef("http://example.com/Person"),
    )
    range_ = DataPropertyRange(
        context=ctx,
        data_property_expression=prop,
        data_range=URIRef("http://www.w3.org/2001/XMLSchema#integer"),
    )

    assert domain.as_triples == (
        (prop, RDFS.domain, URIRef("http://example.com/Person")),
    )
    assert range_.as_triples == (
        (
            prop,
            RDFS.range,
            URIRef("http://www.w3.org/2001/XMLSchema#integer"),
        ),
    )
    _assert_python_json_round_trip(DataPropertyDomain, domain)
    _assert_python_json_round_trip(DataPropertyRange, range_)


def test_inverse_object_properties_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    p = URIRef("http://example.com/hasParent")
    q = URIRef("http://example.com/hasChild")
    axiom = InverseObjectProperties(
        context=ctx,
        object_property_expression_1=p,
        object_property_expression_2=q,
    )

    assert axiom.as_triples == ((p, OWL.inverseOf, q),)
    _assert_python_json_round_trip(InverseObjectProperties, axiom)
    _assert_model_json_schema_smoke(InverseObjectProperties, "InverseObjectProperties")


def test_datatype_definition_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    dt = URIRef("http://example.com/AdultAge")
    dr = BNode("dr")
    axiom = DatatypeDefinition(context=ctx, datatype=dt, data_range=dr)

    assert axiom.as_triples == ((dt, OWL.equivalentClass, dr),)
    _assert_python_json_round_trip(DatatypeDefinition, axiom)
    _assert_model_json_schema_smoke(DatatypeDefinition, "DatatypeDefinition")


def test_equivalent_object_and_data_properties_binary() -> None:
    ctx = URIRef("http://example.com/g")
    p1 = URIRef("http://example.com/p1")
    p2 = URIRef("http://example.com/p2")
    obj = EquivalentObjectProperties(
        context=ctx,
        object_property_expression_1=p1,
        object_property_expression_2=p2,
    )
    data = EquivalentDataProperties(
        context=ctx,
        data_property_expression_1=p1,
        data_property_expression_2=p2,
    )

    assert obj.as_triples == ((p1, OWL.equivalentProperty, p2),)
    assert data.as_triples == ((p1, OWL.equivalentProperty, p2),)
    _assert_python_json_round_trip(EquivalentObjectProperties, obj)
    _assert_python_json_round_trip(EquivalentDataProperties, data)
    _assert_model_json_schema_smoke(
        EquivalentObjectProperties,
        "EquivalentObjectProperties",
    )
    _assert_model_json_schema_smoke(
        EquivalentDataProperties, "EquivalentDataProperties"
    )


def test_same_individual_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    a = URIRef("http://example.com/alice")
    b = URIRef("http://example.com/bob")
    axiom = SameIndividual(context=ctx, individual_1=a, individual_2=b)

    assert axiom.name == a
    assert axiom.as_triples == ((a, OWL.sameAs, b),)
    _assert_python_json_round_trip(SameIndividual, axiom)
    _assert_model_json_schema_smoke(SameIndividual, "SameIndividual")


def test_disjoint_object_and_data_properties_binary() -> None:
    ctx = URIRef("http://example.com/g")
    p1 = URIRef("http://example.com/p1")
    p2 = URIRef("http://example.com/p2")
    obj = DisjointObjectProperties(
        context=ctx,
        object_property_expression_1=p1,
        object_property_expression_2=p2,
    )
    data = DisjointDataProperties(
        context=ctx,
        data_property_expression_1=p1,
        data_property_expression_2=p2,
    )

    assert obj.as_triples == ((p1, OWL.propertyDisjointWith, p2),)
    assert data.as_triples == ((p1, OWL.propertyDisjointWith, p2),)
    _assert_python_json_round_trip(DisjointObjectProperties, obj)
    _assert_python_json_round_trip(DisjointDataProperties, data)


def test_disjoint_object_properties_nary_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    name = URIRef("http://example.com/all-disjoint-props")
    members = _ternary_seq(
        ctx,
        URIRef("http://example.com/a"),
        URIRef("http://example.com/b"),
        URIRef("http://example.com/c"),
    )
    axiom = DisjointObjectPropertiesNary(context=ctx, name_value=name, members=members)

    assert (name, RDF.type, OWL.AllDisjointProperties) in axiom.as_triples
    assert (name, OWL.members, members.name) in axiom.as_triples
    _assert_round_trips_preserve_as_triples(DisjointObjectPropertiesNary, axiom)


def test_disjoint_data_properties_nary_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    with pytest.raises(ValidationError, match="n > 2"):
        DisjointDataPropertiesNary(
            context=ctx,
            name_value=URIRef("http://example.com/x"),
            members=_binary_seq(
                ctx,
                URIRef("http://example.com/a"),
                URIRef("http://example.com/b"),
            ),
        )


def test_has_key_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    ce = URIRef("http://example.com/Person")
    keys = _binary_seq(
        ctx,
        URIRef("http://example.com/hasSSN"),
        URIRef("http://example.com/nationalId"),
    )
    axiom = HasKey(context=ctx, class_expression=ce, key_properties=keys)

    assert axiom.name == ce
    assert (ce, OWL.hasKey, keys.name) in axiom.as_triples
    _assert_round_trips_preserve_as_triples(HasKey, axiom)
    _assert_model_json_schema_smoke(HasKey, "HasKey")


def test_has_key_rejects_empty_keys() -> None:
    ctx = URIRef("http://example.com/g")
    with pytest.raises(ValidationError, match="at least one"):
        HasKey(
            context=ctx,
            class_expression=URIRef("http://example.com/Person"),
            key_properties=Seq(
                context=ctx,
                entries=(SeqEntry(cell=RDF.nil, value=None),),
            ),
        )


def test_different_individuals_binary_and_nary() -> None:
    ctx = URIRef("http://example.com/g")
    a = URIRef("http://example.com/alice")
    b = URIRef("http://example.com/bob")
    binary = DifferentIndividuals(context=ctx, individual_1=a, individual_2=b)
    nary = DifferentIndividualsNary(
        context=ctx,
        name_value=URIRef("http://example.com/all-different"),
        members=_ternary_seq(
            ctx,
            a,
            b,
            URIRef("http://example.com/carol"),
        ),
    )

    assert binary.as_triples == ((a, OWL.differentFrom, b),)
    assert (nary.name, RDF.type, OWL.AllDifferent) in nary.as_triples
    assert (nary.name, OWL.members, nary.members.name) in nary.as_triples
    _assert_python_json_round_trip(DifferentIndividuals, binary)
    _assert_round_trips_preserve_as_triples(DifferentIndividualsNary, nary)


def test_seq_owner_rejects_mismatched_context() -> None:
    ctx = URIRef("http://example.com/g")
    other = URIRef("http://example.com/other")
    with pytest.raises(ValidationError, match="share its owner's context"):
        HasKey(
            context=ctx,
            class_expression=URIRef("http://example.com/Person"),
            key_properties=_binary_seq(
                other,
                URIRef("http://example.com/p1"),
                URIRef("http://example.com/p2"),
            ),
        )
