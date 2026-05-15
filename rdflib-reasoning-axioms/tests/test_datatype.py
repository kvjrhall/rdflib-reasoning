import pytest
from pydantic import BaseModel, ValidationError
from rdflib import OWL, RDF, RDFS, XSD, BNode, Literal, URIRef
from rdflib_reasoning.axiom.datatype import (
    DataAllValuesFromNary,
    DataComplementOf,
    DataIntersectionOf,
    DataOneOf,
    DataRange,
    DataRestriction,
    DataSomeValuesFrom,
    DataSomeValuesFromNary,
    DatatypeRestriction,
    DataUnionOf,
    DeclarationDatatype,
    FacetEntry,
    FacetList,
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


def test_cannot_instantiate_abc_data_range() -> None:
    with pytest.raises(TypeError):
        DataRange(  # type: ignore[abstract] # pyright: ignore[reportAbstractUsage]
            context=BNode(),
            name_value=URIRef("http://example.com/SomeDatatype"),
        )


def test_cannot_instantiate_abc_data_restriction() -> None:
    with pytest.raises(TypeError):
        DataRestriction(context=BNode(), name_value=BNode())  # type: ignore[abstract] # pyright: ignore[reportAbstractUsage]


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
    head, mid, x = BNode(), BNode(), BNode()
    dr_a = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/InnerDatatypeA")
    )
    dr_b = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/InnerDatatypeB")
    )
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=head, value=dr_a.name),
            SeqEntry(cell=mid, value=dr_b.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    intersection = DataIntersectionOf(context=ctx, name_value=x, intersection_of=seq)

    assert seq.as_triples == (
        (head, RDF.first, dr_a.name),
        (mid, RDF.first, dr_b.name),
        (head, RDF.rest, mid),
        (mid, RDF.rest, RDF.nil),
    )
    assert intersection.as_triples == (
        *seq.as_triples,
        (x, RDF.type, RDFS.Datatype),
        (x, OWL.intersectionOf, head),
    )


def test_data_union_of_as_triples() -> None:
    ctx = BNode()
    head, mid, x = BNode(), BNode(), BNode()
    dr_a = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/InnerDatatypeA")
    )
    dr_b = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/InnerDatatypeB")
    )
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=head, value=dr_a.name),
            SeqEntry(cell=mid, value=dr_b.name),
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
    cell = BNode()
    anchor = BNode()
    facets = FacetList(
        context=ctx,
        entries=(
            FacetEntry(
                cell=cell,
                anchor=anchor,
                facet=URIRef("http://www.w3.org/2001/XMLSchema#minInclusive"),
                value=Literal(1, datatype=XSD.integer),
            ),
            FacetEntry(cell=RDF.nil, anchor=None, facet=None, value=None),
        ),
    )
    dr = DatatypeRestriction(
        context=ctx,
        name_value=main,
        on_datatype=URIRef("http://www.w3.org/2001/XMLSchema#integer"),
        with_restrictions=facets,
    )

    assert (main, RDF.type, RDFS.Datatype) in dr.as_triples


def test_datatype_restriction_as_triples_matches_owl_mapping_spec() -> None:
    """OWL 2 RDF mapping for ``DatatypeRestriction`` (onDatatype, withRestrictions, facets)."""
    ctx = URIRef("http://example.com/graph")
    main = URIRef("http://example.com/dtRestriction")
    cell = URIRef("http://example.com/facetListHead")
    anchor = URIRef("http://example.com/facet1")
    on_dt = URIRef("http://www.w3.org/2001/XMLSchema#integer")
    min_inclusive = URIRef("http://www.w3.org/2001/XMLSchema#minInclusive")
    lit = Literal(1, datatype=XSD.integer)
    facets = FacetList(
        context=ctx,
        entries=(
            FacetEntry(cell=cell, anchor=anchor, facet=min_inclusive, value=lit),
            FacetEntry(cell=RDF.nil, anchor=None, facet=None, value=None),
        ),
    )
    dr = DatatypeRestriction(
        context=ctx,
        name_value=main,
        on_datatype=on_dt,
        with_restrictions=facets,
    )

    assert dr.as_triples == (
        (cell, RDF.first, anchor),
        (anchor, min_inclusive, lit),
        (cell, RDF.rest, RDF.nil),
        (main, RDF.type, RDFS.Datatype),
        (main, OWL.onDatatype, on_dt),
        (main, OWL.withRestrictions, cell),
    )


def _build_binary_data_range_seq(
    ctx: URIRef | BNode,
    *,
    list_head: URIRef | BNode,
    list_mid: URIRef | BNode,
) -> Seq:
    return Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=URIRef("http://example.com/innerDTA")),
            SeqEntry(cell=list_mid, value=URIRef("http://example.com/innerDTB")),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )


def test_data_intersection_of_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_binary_data_range_seq(
        ctx,
        list_head=URIRef("http://example.com/listHead"),
        list_mid=URIRef("http://example.com/listMid"),
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
    seq = _build_binary_data_range_seq(
        ctx,
        list_head=URIRef("http://example.com/listHead"),
        list_mid=URIRef("http://example.com/listMid"),
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
    seq = _build_binary_data_range_seq(
        fragment_ctx,
        list_head=URIRef("http://example.com/listHead"),
        list_mid=URIRef("http://example.com/listMid"),
    )
    with pytest.raises(ValidationError, match="StructuralFragment"):
        DataIntersectionOf(
            context=owner_ctx,
            name_value=URIRef("http://example.com/intersectionDT"),
            intersection_of=seq,
        )


def test_data_union_of_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_binary_data_range_seq(
        ctx,
        list_head=URIRef("http://example.com/listHeadU"),
        list_mid=URIRef("http://example.com/listMidU"),
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
    seq = _build_binary_data_range_seq(
        ctx,
        list_head=URIRef("http://example.com/listHeadU"),
        list_mid=URIRef("http://example.com/listMidU"),
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


def _build_facet_list(
    ctx: URIRef | BNode,
    *,
    cell: URIRef | BNode,
    anchor: URIRef | BNode,
) -> FacetList:
    return FacetList(
        context=ctx,
        entries=(
            FacetEntry(
                cell=cell,
                anchor=anchor,
                facet=URIRef("http://www.w3.org/2001/XMLSchema#minInclusive"),
                value=Literal(1, datatype=XSD.integer),
            ),
            FacetEntry(cell=RDF.nil, anchor=None, facet=None, value=None),
        ),
    )


def test_datatype_restriction_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    facets = _build_facet_list(
        ctx,
        cell=URIRef("http://example.com/facetListHead"),
        anchor=URIRef("http://example.com/facetAnchor"),
    )
    inst = DatatypeRestriction(
        context=ctx,
        name_value=URIRef("http://example.com/dtRestriction"),
        on_datatype=URIRef("http://www.w3.org/2001/XMLSchema#integer"),
        with_restrictions=facets,
    )
    _assert_round_trips_preserve_as_triples(DatatypeRestriction, inst)
    _assert_model_json_schema_smoke(DatatypeRestriction, "DatatypeRestriction")


def test_datatype_restriction_rejects_mismatched_fragment_context() -> None:
    owner_ctx = URIRef("http://example.com/g-owner")
    fragment_ctx = URIRef("http://example.com/g-other")
    facets = _build_facet_list(
        fragment_ctx,
        cell=URIRef("http://example.com/facetListHead"),
        anchor=URIRef("http://example.com/facetAnchor"),
    )
    with pytest.raises(ValidationError, match="StructuralFragment"):
        DatatypeRestriction(
            context=owner_ctx,
            name_value=URIRef("http://example.com/dtRestriction"),
            on_datatype=URIRef("http://www.w3.org/2001/XMLSchema#integer"),
            with_restrictions=facets,
        )


def test_datatype_restriction_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    facets = _build_facet_list(
        ctx,
        cell=URIRef("http://example.com/facetListHead"),
        anchor=URIRef("http://example.com/facetAnchor"),
    )
    inst = DatatypeRestriction(
        context=ctx,
        name_value=URIRef("http://example.com/dtRestriction"),
        on_datatype=URIRef("http://www.w3.org/2001/XMLSchema#integer"),
        with_restrictions=facets,
    )
    assert inst.as_quads == tuple((*t, ctx) for t in inst.as_triples)


def test_facet_list_python_json_round_trip_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    facets = _build_facet_list(
        ctx,
        cell=URIRef("http://example.com/facetListHead"),
        anchor=URIRef("http://example.com/facetAnchor"),
    )
    dumped = facets.model_dump()
    assert FacetList.model_validate(dumped).as_triples == facets.as_triples
    json_text = facets.model_dump_json()
    assert FacetList.model_validate_json(json_text).as_triples == facets.as_triples
    schema = FacetList.model_json_schema()
    assert schema.get("title") == "FacetList"
    assert "context" in schema["properties"]
    assert "entries" in schema["properties"]


def test_facet_list_rejects_missing_terminal_sentinel() -> None:
    ctx = BNode()
    with pytest.raises(ValidationError, match="last entry"):
        FacetList(
            context=ctx,
            entries=(
                FacetEntry(
                    cell=BNode(),
                    anchor=BNode(),
                    facet=URIRef("http://www.w3.org/2001/XMLSchema#minInclusive"),
                    value=Literal(1, datatype=XSD.integer),
                ),
            ),
        )


def test_facet_list_rejects_duplicate_list_cells() -> None:
    ctx = BNode()
    shared = BNode()
    with pytest.raises(ValidationError, match="duplicates"):
        FacetList(
            context=ctx,
            entries=(
                FacetEntry(
                    cell=shared,
                    anchor=BNode(),
                    facet=URIRef("http://www.w3.org/2001/XMLSchema#minInclusive"),
                    value=Literal(1, datatype=XSD.integer),
                ),
                FacetEntry(
                    cell=shared,
                    anchor=BNode(),
                    facet=URIRef("http://www.w3.org/2001/XMLSchema#maxInclusive"),
                    value=Literal(10, datatype=XSD.integer),
                ),
                FacetEntry(cell=RDF.nil, anchor=None, facet=None, value=None),
            ),
        )


def test_facet_entry_rejects_partial_non_sentinel() -> None:
    with pytest.raises(ValidationError, match="MUST supply all of"):
        FacetEntry(
            cell=BNode(),
            anchor=BNode(),
            facet=URIRef("http://www.w3.org/2001/XMLSchema#minInclusive"),
            value=None,
        )


def test_facet_entry_rejects_sentinel_with_payload() -> None:
    with pytest.raises(ValidationError, match="rdf:nil"):
        FacetEntry(
            cell=RDF.nil,
            anchor=None,
            facet=URIRef("http://www.w3.org/2001/XMLSchema#minInclusive"),
            value=None,
        )


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


def _build_binary_property_seq(
    ctx: URIRef | BNode,
    *,
    list_head: URIRef | BNode,
    list_mid: URIRef | BNode,
) -> Seq:
    return Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=URIRef("http://example.com/p1")),
            SeqEntry(cell=list_mid, value=URIRef("http://example.com/p2")),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )


def test_data_some_values_from_nary_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    main = URIRef("http://example.com/restriction-node")
    list_head = URIRef("http://example.com/propsListHead")
    list_mid = URIRef("http://example.com/propsListMid")
    rng = URIRef("http://example.com/range")
    seq = _build_binary_property_seq(ctx, list_head=list_head, list_mid=list_mid)
    inst = DataSomeValuesFromNary(
        context=ctx,
        name_value=main,
        on_properties=seq,
        some_values_from=rng,
    )

    assert inst.as_triples == (
        (list_head, RDF.first, URIRef("http://example.com/p1")),
        (list_mid, RDF.first, URIRef("http://example.com/p2")),
        (list_head, RDF.rest, list_mid),
        (list_mid, RDF.rest, RDF.nil),
        (main, RDF.type, OWL.Restriction),
        (main, OWL.onProperties, list_head),
        (main, OWL.someValuesFrom, rng),
    )


def test_data_some_values_from_nary_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_binary_property_seq(
        ctx,
        list_head=URIRef("http://example.com/propsListHead"),
        list_mid=URIRef("http://example.com/propsListMid"),
    )
    inst = DataSomeValuesFromNary(
        context=ctx,
        name_value=URIRef("http://example.com/restriction-node"),
        on_properties=seq,
        some_values_from=URIRef("http://example.com/range"),
    )
    assert inst.as_quads == tuple((*t, ctx) for t in inst.as_triples)


def test_data_some_values_from_nary_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_binary_property_seq(
        ctx,
        list_head=URIRef("http://example.com/propsListHead"),
        list_mid=URIRef("http://example.com/propsListMid"),
    )
    inst = DataSomeValuesFromNary(
        context=ctx,
        name_value=URIRef("http://example.com/restriction-node"),
        on_properties=seq,
        some_values_from=URIRef("http://example.com/range"),
    )
    _assert_round_trips_preserve_as_triples(DataSomeValuesFromNary, inst)
    _assert_model_json_schema_smoke(DataSomeValuesFromNary, "DataSomeValuesFromNary")


def test_data_some_values_from_nary_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(
                cell=URIRef("http://example.com/c1"),
                value=URIRef("http://example.com/p1"),
            ),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    with pytest.raises(ValidationError, match="n >= 2"):
        DataSomeValuesFromNary(
            context=ctx,
            name_value=URIRef("http://example.com/restriction-node"),
            on_properties=seq,
            some_values_from=URIRef("http://example.com/range"),
        )


def test_data_some_values_from_nary_rejects_mismatched_fragment_context() -> None:
    owner_ctx = URIRef("http://example.com/g-owner")
    fragment_ctx = URIRef("http://example.com/g-other")
    seq = _build_binary_property_seq(
        fragment_ctx,
        list_head=URIRef("http://example.com/propsListHead"),
        list_mid=URIRef("http://example.com/propsListMid"),
    )
    with pytest.raises(ValidationError, match="StructuralFragment"):
        DataSomeValuesFromNary(
            context=owner_ctx,
            name_value=URIRef("http://example.com/restriction-node"),
            on_properties=seq,
            some_values_from=URIRef("http://example.com/range"),
        )


def test_data_all_values_from_nary_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    main = URIRef("http://example.com/restriction-node")
    list_head = URIRef("http://example.com/propsListHead")
    list_mid = URIRef("http://example.com/propsListMid")
    rng = URIRef("http://example.com/range")
    seq = _build_binary_property_seq(ctx, list_head=list_head, list_mid=list_mid)
    inst = DataAllValuesFromNary(
        context=ctx,
        name_value=main,
        on_properties=seq,
        all_values_from=rng,
    )

    assert inst.as_triples == (
        (list_head, RDF.first, URIRef("http://example.com/p1")),
        (list_mid, RDF.first, URIRef("http://example.com/p2")),
        (list_head, RDF.rest, list_mid),
        (list_mid, RDF.rest, RDF.nil),
        (main, RDF.type, OWL.Restriction),
        (main, OWL.onProperties, list_head),
        (main, OWL.allValuesFrom, rng),
    )


def test_data_all_values_from_nary_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_binary_property_seq(
        ctx,
        list_head=URIRef("http://example.com/propsListHead"),
        list_mid=URIRef("http://example.com/propsListMid"),
    )
    inst = DataAllValuesFromNary(
        context=ctx,
        name_value=URIRef("http://example.com/restriction-node"),
        on_properties=seq,
        all_values_from=URIRef("http://example.com/range"),
    )
    assert inst.as_quads == tuple((*t, ctx) for t in inst.as_triples)


def test_data_all_values_from_nary_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_binary_property_seq(
        ctx,
        list_head=URIRef("http://example.com/propsListHead"),
        list_mid=URIRef("http://example.com/propsListMid"),
    )
    inst = DataAllValuesFromNary(
        context=ctx,
        name_value=URIRef("http://example.com/restriction-node"),
        on_properties=seq,
        all_values_from=URIRef("http://example.com/range"),
    )
    _assert_round_trips_preserve_as_triples(DataAllValuesFromNary, inst)
    _assert_model_json_schema_smoke(DataAllValuesFromNary, "DataAllValuesFromNary")


def test_data_all_values_from_nary_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(
                cell=URIRef("http://example.com/c1"),
                value=URIRef("http://example.com/p1"),
            ),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    with pytest.raises(ValidationError, match="n >= 2"):
        DataAllValuesFromNary(
            context=ctx,
            name_value=URIRef("http://example.com/restriction-node"),
            on_properties=seq,
            all_values_from=URIRef("http://example.com/range"),
        )


def test_data_all_values_from_nary_rejects_mismatched_fragment_context() -> None:
    owner_ctx = URIRef("http://example.com/g-owner")
    fragment_ctx = URIRef("http://example.com/g-other")
    seq = _build_binary_property_seq(
        fragment_ctx,
        list_head=URIRef("http://example.com/propsListHead"),
        list_mid=URIRef("http://example.com/propsListMid"),
    )
    with pytest.raises(ValidationError, match="StructuralFragment"):
        DataAllValuesFromNary(
            context=owner_ctx,
            name_value=URIRef("http://example.com/restriction-node"),
            on_properties=seq,
            all_values_from=URIRef("http://example.com/range"),
        )


def test_data_one_of_python_round_trip() -> None:
    ctx = URIRef("http://example.com/g")
    list_head = URIRef("http://example.com/oneOfListHead")
    cell_b = URIRef("http://example.com/oneOfListCellB")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=Literal("a")),
            SeqEntry(cell=cell_b, value=Literal(1, datatype=XSD.integer)),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    inst = DataOneOf(
        context=ctx,
        name_value=URIRef("http://example.com/dataOneOfDT"),
        one_of=seq,
    )
    _assert_round_trips_preserve_as_triples(DataOneOf, inst)


def test_data_one_of_model_json_schema_smoke() -> None:
    _assert_model_json_schema_smoke(DataOneOf, "DataOneOf")


def test_data_one_of_json_round_trip() -> None:
    ctx = URIRef("http://example.com/g")
    list_head = URIRef("http://example.com/oneOfListHead")
    cell_b = URIRef("http://example.com/oneOfListCellB")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=Literal("a")),
            SeqEntry(cell=cell_b, value=Literal(1, datatype=XSD.integer)),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    inst = DataOneOf(
        context=ctx,
        name_value=URIRef("http://example.com/dataOneOfDT"),
        one_of=seq,
    )
    json_text = inst.model_dump_json()
    restored = DataOneOf.model_validate_json(json_text)
    assert restored.as_triples == inst.as_triples


def test_data_one_of_as_triples_matches_owl_mapping_spec() -> None:
    ctx = URIRef("http://example.com/g")
    main = URIRef("http://example.com/dataOneOfDT")
    list_head = URIRef("http://example.com/oneOfListHead")
    cell_b = URIRef("http://example.com/oneOfListCellB")
    lt1 = Literal("a")
    lt2 = Literal(1, datatype=XSD.integer)
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=lt1),
            SeqEntry(cell=cell_b, value=lt2),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    inst = DataOneOf(context=ctx, name_value=main, one_of=seq)

    assert inst.as_triples == (
        (list_head, RDF.first, lt1),
        (cell_b, RDF.first, lt2),
        (list_head, RDF.rest, cell_b),
        (cell_b, RDF.rest, RDF.nil),
        (main, RDF.type, RDFS.Datatype),
        (main, OWL.oneOf, list_head),
    )


def test_data_one_of_as_quads_matches_owl_mapping_spec() -> None:
    ctx = URIRef("http://example.com/g")
    main = URIRef("http://example.com/dataOneOfDT")
    list_head = URIRef("http://example.com/oneOfListHead")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=Literal("a")),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    inst = DataOneOf(context=ctx, name_value=main, one_of=seq)
    assert inst.as_quads == tuple((*t, ctx) for t in inst.as_triples)
    assert len(inst.as_quads) > 1


def test_data_intersection_of_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(
                cell=URIRef("http://example.com/c1"),
                value=URIRef("http://example.com/d1"),
            ),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    with pytest.raises(ValidationError, match="n >= 2"):
        DataIntersectionOf(
            context=ctx,
            name_value=URIRef("http://example.com/intersectionDT"),
            intersection_of=seq,
        )


def test_data_union_of_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(
                cell=URIRef("http://example.com/c1"),
                value=URIRef("http://example.com/d1"),
            ),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    with pytest.raises(ValidationError, match="n >= 2"):
        DataUnionOf(
            context=ctx,
            name_value=URIRef("http://example.com/unionDT"),
            union_of=seq,
        )


def test_data_one_of_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    empty_seq = Seq(
        context=ctx,
        entries=(SeqEntry(cell=RDF.nil, value=None),),
    )
    with pytest.raises(ValidationError, match="n >= 1"):
        DataOneOf(
            context=ctx,
            name_value=URIRef("http://example.com/dataOneOfDT"),
            one_of=empty_seq,
        )


def test_data_one_of_rejects_mismatched_fragment_context() -> None:
    owner_ctx = URIRef("http://example.com/g-owner")
    fragment_ctx = URIRef("http://example.com/g-other")
    list_head = URIRef("http://example.com/oneOfListHead")
    seq = Seq(
        context=fragment_ctx,
        entries=(
            SeqEntry(cell=list_head, value=Literal("a")),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    with pytest.raises(ValidationError, match="StructuralFragment"):
        DataOneOf(
            context=owner_ctx,
            name_value=URIRef("http://example.com/dataOneOfDT"),
            one_of=seq,
        )
