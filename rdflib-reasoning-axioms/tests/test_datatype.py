import pytest
from pydantic import BaseModel, ValidationError
from rdflib import OWL, RDF, RDFS, XSD, BNode, Literal, URIRef
from rdflib_reasoning.axiom.datatype import (
    DataComplementOf,
    DataIntersectionOf,
    DataOneOf,
    DataRange,
    DataSomeValuesFrom,
    DatatypeRestriction,
    DataUnionOf,
    DeclarationDatatype,
    RestrictionFacet,
)
from rdflib_reasoning.axiom.structural_element import Seq, SeqEntry, StructuralElement


def _assert_model_json_schema_smoke(model_cls: type[BaseModel], title: str) -> None:
    schema = model_cls.model_json_schema()
    assert schema.get("title") == title
    props = schema["properties"]
    assert "context" in props


def _assert_python_json_round_trip[T: BaseModel](
    model_cls: type[T],
    instance: T,
) -> None:
    """Assert full model equality after Python and JSON round-trips."""
    dumped = instance.model_dump()
    assert model_cls.model_validate(dumped) == instance
    json_text = instance.model_dump_json()
    assert model_cls.model_validate_json(json_text) == instance


def _assert_round_trips_preserve_as_triples(
    model_cls: type[BaseModel],
    instance: StructuralElement,
) -> None:
    """Round-trip through ``model_dump`` / ``model_validate`` and JSON, preserving RDF projection.

    Nested ``DataRange`` / facet discriminators may deserialize to a super-class
    while still producing identical ``as_triples``.
    """
    from_py = model_cls.model_validate(instance.model_dump())
    assert isinstance(from_py, StructuralElement)
    assert from_py.as_triples == instance.as_triples
    from_js = model_cls.model_validate_json(instance.model_dump_json())
    assert isinstance(from_js, StructuralElement)
    assert from_js.as_triples == instance.as_triples


def test_data_range_as_triples() -> None:
    ctx = BNode()
    name = URIRef("http://example.com/SomeDatatype")
    data_range = DataRange(context=ctx, name_value=name)

    assert data_range.as_triples == ((name, RDF.type, RDFS.Datatype),)


def test_cannot_instantiate_abc_restriction_facet() -> None:
    with pytest.raises(TypeError):
        RestrictionFacet(context=BNode())  # type: ignore[abstract] # pyright: ignore[reportAbstractUsage]


def test_declaration_datatype_as_triples() -> None:
    name = URIRef("http://example.com/SomeDatatype")
    declaration_datatype = DeclarationDatatype(context=BNode(), name_value=name)

    assert declaration_datatype.name == name
    assert declaration_datatype.rdf_type == RDFS.Datatype
    assert declaration_datatype.as_triples == ((name, RDF.type, RDFS.Datatype),)


def test_declaration_datatype_as_quads() -> None:
    ctx = BNode()
    name = URIRef("http://example.com/SomeDatatype")
    declaration_datatype = DeclarationDatatype(context=ctx, name_value=name)

    assert declaration_datatype.as_quads == tuple(
        (*t, ctx) for t in declaration_datatype.as_triples
    )


def test_declaration_datatype_json_round_trip() -> None:
    expected = DeclarationDatatype(
        context=BNode(), name_value=URIRef("http://example.com/SomeDatatype")
    )
    json_text = expected.model_dump_json()
    actual = DeclarationDatatype.model_validate_json(json_text)

    assert actual == expected


def test_declaration_datatype_python_round_trip() -> None:
    expected = DeclarationDatatype(
        context=BNode(), name_value=URIRef("http://example.com/SomeDatatype")
    )
    python = expected.model_dump()
    actual = DeclarationDatatype.model_validate(python)

    assert actual == expected


def test_declaration_datatype_json_schema_shape() -> None:
    schema = DeclarationDatatype.model_json_schema()
    assert schema.get("title") == "DeclarationDatatype"
    props = schema["properties"]
    assert "context" in props
    assert "name" in props


def test_seq_list_triples_via_intersection() -> None:
    ctx = BNode()
    head, x = BNode(), BNode()
    dr = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/InnerDatatype")
    )
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=head, value=dr.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    intersection = DataIntersectionOf(context=ctx, name_value=x, intersection_of=seq)

    assert seq.as_triples == (
        (head, RDF.first, dr.name),
        (head, RDF.rest, RDF.nil),
    )
    assert intersection.as_triples == (
        *seq.as_triples,
        (x, RDF.type, RDFS.Datatype),
        (x, OWL.intersectionOf, head),
    )


def test_data_union_of_as_triples() -> None:
    ctx = BNode()
    head, x = BNode(), BNode()
    dr = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/InnerDatatype")
    )
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=head, value=dr.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    union = DataUnionOf(context=ctx, name_value=x, union_of=seq)

    assert union.as_triples == (
        *seq.as_triples,
        (x, RDF.type, RDFS.Datatype),
        (x, OWL.unionOf, head),
    )


def test_data_complement_of_as_triples() -> None:
    ctx = BNode()
    x = BNode()
    inner_dt = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/InnerDatatype")
    )
    comp = DataComplementOf(context=ctx, name_value=x, complement_of=inner_dt.name)

    assert comp.as_triples == (
        (x, RDF.type, RDFS.Datatype),
        (x, OWL.complementOf, inner_dt.name),
    )


def test_data_some_values_from_as_triples() -> None:
    ctx = BNode()
    x = BNode()
    prop = URIRef("http://example.com/p")
    rng = URIRef("http://example.com/range")
    dsv = DataSomeValuesFrom(
        context=ctx, name_value=x, on_property=prop, some_values_from=rng
    )

    assert dsv.as_triples == (
        (x, RDF.type, OWL.Restriction),
        (x, OWL.onProperty, prop),
        (x, OWL.someValuesFrom, rng),
    )


def test_data_some_values_from_json_round_trip() -> None:
    # Use an IRI for ``name`` so PlainSerializer/JSON produces parseable N3; ad-hoc
    # ``BNode`` ids are not always roundtrip-able through ``model_dump_json``.
    expected = DataSomeValuesFrom(
        context=BNode(),
        name_value=URIRef("http://example.com/restriction-node"),
        on_property=URIRef("http://example.com/p"),
        some_values_from=URIRef("http://example.com/range"),
    )
    actual = DataSomeValuesFrom.model_validate_json(expected.model_dump_json())
    assert actual == expected


def test_datatype_restriction_emits_datatype_declaration() -> None:
    """Regression: projection always includes the main ``rdfs:Datatype`` declaration."""
    ctx = BNode()
    main = BNode()
    facet_node = BNode()
    list_head = BNode()
    prop = URIRef("http://example.com/p")
    rng = URIRef("http://example.com/range")
    facet = DataSomeValuesFrom(
        context=ctx,
        name_value=facet_node,
        on_property=prop,
        some_values_from=rng,
    )
    facets = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=facet.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    dr = DatatypeRestriction(
        context=ctx,
        name_value=main,
        on_datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"),
        with_restrictions=facets,
    )

    assert (main, RDF.type, RDFS.Datatype) in dr.as_triples


@pytest.mark.xfail(
    strict=True,
    reason="DatatypeRestriction.as_triples does not yet emit full OWL 2 RDF mapping.",
)
def test_datatype_restriction_as_triples_matches_owl_mapping_spec() -> None:
    """Target: OWL 2 RDF mapping for ``DatatypeRestriction`` (onDatatype, withRestrictions, facets)."""
    ctx = URIRef("http://example.com/graph")
    main = URIRef("http://example.com/dtRestriction")
    facet_node = URIRef("http://example.com/facet1")
    list_head = URIRef("http://example.com/facetListHead")
    on_dt = URIRef("http://www.w3.org/2001/XMLSchema#string")
    prop = URIRef("http://example.com/p")
    rng = URIRef("http://example.com/range")
    facet = DataSomeValuesFrom(
        context=ctx,
        name_value=facet_node,
        on_property=prop,
        some_values_from=rng,
    )
    facets = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=facet.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    dr = DatatypeRestriction(
        context=ctx,
        name_value=main,
        on_datatype=on_dt,
        with_restrictions=facets,
    )
    trip = dr.as_triples
    preds = {t[1] for t in trip}
    assert OWL.onDatatype in preds
    assert OWL.withRestrictions in preds
    assert RDF.first in preds and RDF.rest in preds
    assert OWL.onProperty in preds and OWL.someValuesFrom in preds


def test_data_range_python_json_round_trip_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    inst = DataRange(context=ctx, name_value=URIRef("http://example.com/openDataRange"))
    _assert_python_json_round_trip(DataRange, inst)
    _assert_model_json_schema_smoke(DataRange, "DataRange")


def test_data_range_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    name = URIRef("http://example.com/SomeDatatype")
    data_range = DataRange(context=ctx, name_value=name)
    assert data_range.as_quads == tuple((*t, ctx) for t in data_range.as_triples)


def test_data_intersection_of_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    inner = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/innerDT")
    )
    list_head = URIRef("http://example.com/listHead")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=inner.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    inst = DataIntersectionOf(
        context=ctx,
        name_value=URIRef("http://example.com/intersectionDT"),
        intersection_of=seq,
    )
    _assert_round_trips_preserve_as_triples(DataIntersectionOf, inst)
    _assert_model_json_schema_smoke(DataIntersectionOf, "DataIntersectionOf")


def test_data_intersection_of_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    inner = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/innerDT")
    )
    list_head = URIRef("http://example.com/listHead")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=inner.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    inst = DataIntersectionOf(
        context=ctx,
        name_value=URIRef("http://example.com/intersectionDT"),
        intersection_of=seq,
    )
    assert inst.as_quads == tuple((*t, ctx) for t in inst.as_triples)


def test_data_intersection_of_rejects_mismatched_fragment_context() -> None:
    owner_ctx = URIRef("http://example.com/g-owner")
    fragment_ctx = URIRef("http://example.com/g-other")
    inner = DeclarationDatatype(
        context=fragment_ctx, name_value=URIRef("http://example.com/innerDT")
    )
    list_head = URIRef("http://example.com/listHead")
    seq = Seq(
        context=fragment_ctx,
        entries=(
            SeqEntry(cell=list_head, value=inner.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    with pytest.raises(ValidationError, match="StructuralFragment"):
        DataIntersectionOf(
            context=owner_ctx,
            name_value=URIRef("http://example.com/intersectionDT"),
            intersection_of=seq,
        )


def test_data_union_of_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    inner = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/innerDT")
    )
    list_head = URIRef("http://example.com/listHeadU")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=inner.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    inst = DataUnionOf(
        context=ctx,
        name_value=URIRef("http://example.com/unionDT"),
        union_of=seq,
    )
    _assert_round_trips_preserve_as_triples(DataUnionOf, inst)
    _assert_model_json_schema_smoke(DataUnionOf, "DataUnionOf")


def test_data_union_of_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    inner = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/innerDT")
    )
    list_head = URIRef("http://example.com/listHeadU")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=inner.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    inst = DataUnionOf(
        context=ctx,
        name_value=URIRef("http://example.com/unionDT"),
        union_of=seq,
    )
    assert inst.as_quads == tuple((*t, ctx) for t in inst.as_triples)


def test_data_complement_of_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    inner = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/innerDT")
    )
    inst = DataComplementOf(
        context=ctx,
        name_value=URIRef("http://example.com/complementDT"),
        complement_of=inner.name,
    )
    _assert_round_trips_preserve_as_triples(DataComplementOf, inst)
    _assert_model_json_schema_smoke(DataComplementOf, "DataComplementOf")


def test_data_complement_of_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    inner = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/innerDT")
    )
    inst = DataComplementOf(
        context=ctx,
        name_value=URIRef("http://example.com/complementDT"),
        complement_of=inner.name,
    )
    assert inst.as_quads == tuple((*t, ctx) for t in inst.as_triples)


def test_datatype_restriction_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    facet = DataSomeValuesFrom(
        context=ctx,
        name_value=URIRef("http://example.com/facetNode"),
        on_property=URIRef("http://example.com/p"),
        some_values_from=URIRef("http://example.com/range"),
    )
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(
                cell=URIRef("http://example.com/facetListHead"),
                value=facet.name,
            ),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    inst = DatatypeRestriction(
        context=ctx,
        name_value=URIRef("http://example.com/dtRestriction"),
        on_datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"),
        with_restrictions=seq,
    )
    _assert_round_trips_preserve_as_triples(DatatypeRestriction, inst)
    _assert_model_json_schema_smoke(DatatypeRestriction, "DatatypeRestriction")


def test_datatype_restriction_rejects_mismatched_fragment_context() -> None:
    owner_ctx = URIRef("http://example.com/g-owner")
    fragment_ctx = URIRef("http://example.com/g-other")
    facet = DataSomeValuesFrom(
        context=fragment_ctx,
        name_value=URIRef("http://example.com/facetNode"),
        on_property=URIRef("http://example.com/p"),
        some_values_from=URIRef("http://example.com/range"),
    )
    seq = Seq(
        context=fragment_ctx,
        entries=(
            SeqEntry(
                cell=URIRef("http://example.com/facetListHead"),
                value=facet.name,
            ),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    with pytest.raises(ValidationError, match="StructuralFragment"):
        DatatypeRestriction(
            context=owner_ctx,
            name_value=URIRef("http://example.com/dtRestriction"),
            on_datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"),
            with_restrictions=seq,
        )


def test_datatype_restriction_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    facet = DataSomeValuesFrom(
        context=ctx,
        name_value=URIRef("http://example.com/facetNode"),
        on_property=URIRef("http://example.com/p"),
        some_values_from=URIRef("http://example.com/range"),
    )
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(
                cell=URIRef("http://example.com/facetListHead"),
                value=facet.name,
            ),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    inst = DatatypeRestriction(
        context=ctx,
        name_value=URIRef("http://example.com/dtRestriction"),
        on_datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"),
        with_restrictions=seq,
    )
    assert inst.as_quads == tuple((*t, ctx) for t in inst.as_triples)


def test_data_some_values_from_python_round_trip_and_schema() -> None:
    expected = DataSomeValuesFrom(
        context=URIRef("http://example.com/g"),
        name_value=URIRef("http://example.com/restriction-node"),
        on_property=URIRef("http://example.com/p"),
        some_values_from=URIRef("http://example.com/range"),
    )
    _assert_python_json_round_trip(DataSomeValuesFrom, expected)
    _assert_model_json_schema_smoke(DataSomeValuesFrom, "DataSomeValuesFrom")


def test_data_some_values_from_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    inst = DataSomeValuesFrom(
        context=ctx,
        name_value=URIRef("http://example.com/restriction-node"),
        on_property=URIRef("http://example.com/p"),
        some_values_from=URIRef("http://example.com/range"),
    )
    assert inst.as_quads == tuple((*t, ctx) for t in inst.as_triples)


def test_data_one_of_python_round_trip() -> None:
    ctx = URIRef("http://example.com/g")
    inst = DataOneOf(
        context=ctx,
        name_value=URIRef("http://example.com/dataOneOfDT"),
        one_of=(Literal("a"), Literal(1, datatype=XSD.integer)),
    )
    restored = DataOneOf.model_validate(inst.model_dump())
    assert restored.one_of == inst.one_of
    assert restored.context == inst.context


@pytest.mark.xfail(
    strict=True,
    reason="JSON Schema generation for ``one_of`` rdflib literals is not wired yet.",
)
def test_data_one_of_model_json_schema_smoke() -> None:
    _assert_model_json_schema_smoke(DataOneOf, "DataOneOf")


@pytest.mark.xfail(
    strict=True,
    reason="RDF literals in ``one_of`` need JsonOrPython validation for JSON mode.",
)
def test_data_one_of_json_round_trip() -> None:
    ctx = URIRef("http://example.com/g")
    inst = DataOneOf(
        context=ctx,
        name_value=URIRef("http://example.com/dataOneOfDT"),
        one_of=(Literal("a"), Literal(1, datatype=XSD.integer)),
    )
    json_text = inst.model_dump_json()
    assert DataOneOf.model_validate_json(json_text) == inst


@pytest.mark.xfail(
    strict=True,
    reason="DataOneOf.as_triples does not yet emit owl:oneOf and rdf:List literals.",
)
def test_data_one_of_as_triples_matches_owl_mapping_spec() -> None:
    ctx = URIRef("http://example.com/g")
    main = URIRef("http://example.com/dataOneOfDT")
    lt1 = Literal("a")
    lt2 = Literal(1, datatype=XSD.integer)
    inst = DataOneOf(context=ctx, name_value=main, one_of=(lt1, lt2))
    trip = inst.as_triples
    preds = {t[1] for t in trip}
    assert OWL.oneOf in preds
    assert RDF.first in preds and RDF.rest in preds


@pytest.mark.xfail(
    strict=True,
    reason="DataOneOf.as_triples does not yet emit owl:oneOf and rdf:List literals.",
)
def test_data_one_of_as_quads_matches_owl_mapping_spec() -> None:
    ctx = URIRef("http://example.com/g")
    main = URIRef("http://example.com/dataOneOfDT")
    inst = DataOneOf(context=ctx, name_value=main, one_of=(Literal("a"),))
    assert inst.as_quads == tuple((*t, ctx) for t in inst.as_triples)
    assert len(inst.as_quads) > 1
