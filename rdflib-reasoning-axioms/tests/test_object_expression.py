import pytest
from pydantic import BaseModel, ValidationError
from rdflib import OWL, RDF, BNode, URIRef
from rdflib_reasoning.axiom.object_expression import (
    ClassExpression,
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
    """Round-trip through ``model_dump`` / ``model_validate`` and JSON, preserving RDF projection."""
    from_py = model_cls.model_validate(instance.model_dump())
    assert isinstance(from_py, StructuralElement)
    assert from_py.as_triples == instance.as_triples
    from_js = model_cls.model_validate_json(instance.model_dump_json())
    assert isinstance(from_js, StructuralElement)
    assert from_js.as_triples == instance.as_triples


def _build_binary_class_seq(
    ctx: URIRef | BNode,
    *,
    list_head: URIRef | BNode,
    list_mid: URIRef | BNode,
) -> Seq:
    return Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=URIRef("http://example.com/ClassA")),
            SeqEntry(cell=list_mid, value=URIRef("http://example.com/ClassB")),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )


def _build_ternary_class_seq(
    ctx: URIRef | BNode,
    *,
    list_head: URIRef | BNode,
    list_mid: URIRef | BNode,
    list_tail: URIRef | BNode,
) -> Seq:
    return Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=URIRef("http://example.com/ClassA")),
            SeqEntry(cell=list_mid, value=URIRef("http://example.com/ClassB")),
            SeqEntry(cell=list_tail, value=URIRef("http://example.com/ClassC")),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )


def test_cannot_instantiate_abc_class_expression() -> None:
    with pytest.raises(TypeError):
        ClassExpression(  # type: ignore[abstract] # pyright: ignore[reportAbstractUsage]
            context=BNode(),
            name_value=URIRef("http://example.com/SomeClass"),
        )


def test_object_intersection_of_as_triples() -> None:
    ctx = BNode()
    head, mid, x = BNode(), BNode(), BNode()
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=head, value=URIRef("http://example.com/ClassA")),
            SeqEntry(cell=mid, value=URIRef("http://example.com/ClassB")),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    intersection = ObjectIntersectionOf(context=ctx, name_value=x, intersection_of=seq)

    assert intersection.as_triples == (
        *seq.as_triples,
        (x, RDF.type, OWL.Class),
        (x, OWL.intersectionOf, head),
    )


def test_object_union_of_as_triples() -> None:
    ctx = BNode()
    head, mid, x = BNode(), BNode(), BNode()
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=head, value=URIRef("http://example.com/ClassA")),
            SeqEntry(cell=mid, value=URIRef("http://example.com/ClassB")),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    union = ObjectUnionOf(context=ctx, name_value=x, union_of=seq)

    assert union.as_triples == (
        *seq.as_triples,
        (x, RDF.type, OWL.Class),
        (x, OWL.unionOf, head),
    )


def test_object_complement_of_as_triples() -> None:
    ctx = BNode()
    x = BNode()
    inner = URIRef("http://example.com/InnerClass")
    comp = ObjectComplementOf(context=ctx, name_value=x, complement_of=inner)

    assert comp.as_triples == (
        (x, RDF.type, OWL.Class),
        (x, OWL.complementOf, inner),
    )


def test_object_one_of_as_triples() -> None:
    ctx = BNode()
    head, mid, x = BNode(), BNode(), BNode()
    ind_a = URIRef("http://example.com/alice")
    ind_b = URIRef("http://example.com/bob")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=head, value=ind_a),
            SeqEntry(cell=mid, value=ind_b),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    one_of = ObjectOneOf(context=ctx, name_value=x, one_of=seq)

    assert one_of.as_triples == (
        *seq.as_triples,
        (x, RDF.type, OWL.Class),
        (x, OWL.oneOf, head),
    )


def test_object_inverse_of_as_triples() -> None:
    ctx = BNode()
    x = BNode()
    prop = URIRef("http://example.com/parentOf")
    inv = ObjectInverseOf(context=ctx, name_value=x, inverse_of=prop)

    assert inv.as_triples == ((x, OWL.inverseOf, prop),)
    assert (x, RDF.type, OWL.Class) not in inv.as_triples
    assert (x, RDF.type, OWL.ObjectProperty) not in inv.as_triples


def test_disjoint_classes_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    ce1 = URIRef("http://example.com/Boy")
    ce2 = URIRef("http://example.com/Girl")
    axiom = DisjointClasses(
        context=ctx,
        class_expression_1=ce1,
        class_expression_2=ce2,
    )

    assert axiom.name == ce1
    assert axiom.as_triples == ((ce1, OWL.disjointWith, ce2),)


def test_equivalent_classes_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    ce1 = URIRef("http://example.com/Boy")
    ce2 = URIRef("http://example.com/MaleChild")
    axiom = EquivalentClasses(
        context=ctx,
        class_expression_1=ce1,
        class_expression_2=ce2,
    )

    assert axiom.name == ce1
    assert axiom.as_triples == ((ce1, OWL.equivalentClass, ce2),)
    _assert_python_json_round_trip(EquivalentClasses, axiom)
    _assert_model_json_schema_smoke(EquivalentClasses, "EquivalentClasses")
    assert axiom.as_quads == tuple((*t, axiom.context) for t in axiom.as_triples)


def test_disjoint_classes_nary_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    main = URIRef("http://example.com/all-disjoint")
    list_head = URIRef("http://example.com/membersHead")
    list_mid = URIRef("http://example.com/membersMid")
    list_tail = URIRef("http://example.com/membersTail")
    seq = _build_ternary_class_seq(
        ctx,
        list_head=list_head,
        list_mid=list_mid,
        list_tail=list_tail,
    )
    axiom = DisjointClassesNary(context=ctx, name_value=main, members=seq)

    assert axiom.as_triples == (
        *seq.as_triples,
        (main, RDF.type, OWL.AllDisjointClasses),
        (main, OWL.members, list_head),
    )


def test_disjoint_union_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    named = URIRef("http://example.com/Child")
    list_head = URIRef("http://example.com/duHead")
    list_mid = URIRef("http://example.com/duMid")
    seq = _build_binary_class_seq(ctx, list_head=list_head, list_mid=list_mid)
    axiom = DisjointUnion(
        context=ctx,
        union_class=named,
        disjoint_union_of=seq,
    )

    assert axiom.name == named
    assert axiom.as_triples == (
        *seq.as_triples,
        (named, OWL.disjointUnionOf, list_head),
    )
    assert (named, RDF.type, OWL.Class) not in axiom.as_triples


def test_object_intersection_of_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_binary_class_seq(
        ctx,
        list_head=URIRef("http://example.com/listHead"),
        list_mid=URIRef("http://example.com/listMid"),
    )
    inst = ObjectIntersectionOf(
        context=ctx,
        name_value=URIRef("http://example.com/intersectionCE"),
        intersection_of=seq,
    )
    _assert_round_trips_preserve_as_triples(ObjectIntersectionOf, inst)
    _assert_model_json_schema_smoke(ObjectIntersectionOf, "ObjectIntersectionOf")


def test_object_intersection_of_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_binary_class_seq(
        ctx,
        list_head=URIRef("http://example.com/listHead"),
        list_mid=URIRef("http://example.com/listMid"),
    )
    inst = ObjectIntersectionOf(
        context=ctx,
        name_value=URIRef("http://example.com/intersectionCE"),
        intersection_of=seq,
    )
    assert inst.as_quads == tuple((*t, ctx) for t in inst.as_triples)


def test_object_intersection_of_rejects_mismatched_fragment_context() -> None:
    owner_ctx = URIRef("http://example.com/g-owner")
    fragment_ctx = URIRef("http://example.com/g-other")
    seq = _build_binary_class_seq(
        fragment_ctx,
        list_head=URIRef("http://example.com/listHead"),
        list_mid=URIRef("http://example.com/listMid"),
    )
    with pytest.raises(ValidationError, match="StructuralFragment"):
        ObjectIntersectionOf(
            context=owner_ctx,
            name_value=URIRef("http://example.com/intersectionCE"),
            intersection_of=seq,
        )


def test_object_intersection_of_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(
                cell=URIRef("http://example.com/c1"),
                value=URIRef("http://example.com/ClassA"),
            ),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    with pytest.raises(ValidationError, match="n >= 2"):
        ObjectIntersectionOf(
            context=ctx,
            name_value=URIRef("http://example.com/intersectionCE"),
            intersection_of=seq,
        )


def test_object_union_of_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_binary_class_seq(
        ctx,
        list_head=URIRef("http://example.com/listHeadU"),
        list_mid=URIRef("http://example.com/listMidU"),
    )
    inst = ObjectUnionOf(
        context=ctx,
        name_value=URIRef("http://example.com/unionCE"),
        union_of=seq,
    )
    _assert_round_trips_preserve_as_triples(ObjectUnionOf, inst)
    _assert_model_json_schema_smoke(ObjectUnionOf, "ObjectUnionOf")


def test_object_union_of_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(
                cell=URIRef("http://example.com/c1"),
                value=URIRef("http://example.com/ClassA"),
            ),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    with pytest.raises(ValidationError, match="n >= 2"):
        ObjectUnionOf(
            context=ctx,
            name_value=URIRef("http://example.com/unionCE"),
            union_of=seq,
        )


def test_object_complement_of_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    inst = ObjectComplementOf(
        context=ctx,
        name_value=URIRef("http://example.com/complementCE"),
        complement_of=URIRef("http://example.com/InnerClass"),
    )
    _assert_round_trips_preserve_as_triples(ObjectComplementOf, inst)
    _assert_model_json_schema_smoke(ObjectComplementOf, "ObjectComplementOf")
    _assert_python_json_round_trip(ObjectComplementOf, inst)


def test_object_one_of_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(
                cell=URIRef("http://example.com/oneOfHead"),
                value=URIRef("http://example.com/alice"),
            ),
            SeqEntry(
                cell=URIRef("http://example.com/oneOfMid"),
                value=URIRef("http://example.com/bob"),
            ),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    inst = ObjectOneOf(
        context=ctx,
        name_value=URIRef("http://example.com/oneOfCE"),
        one_of=seq,
    )
    _assert_round_trips_preserve_as_triples(ObjectOneOf, inst)
    _assert_model_json_schema_smoke(ObjectOneOf, "ObjectOneOf")


def test_object_one_of_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    seq = Seq(
        context=ctx,
        entries=(SeqEntry(cell=RDF.nil, value=None),),
    )
    with pytest.raises(ValidationError, match="n >= 1"):
        ObjectOneOf(
            context=ctx,
            name_value=URIRef("http://example.com/oneOfCE"),
            one_of=seq,
        )


def test_object_inverse_of_round_trips_and_schema() -> None:
    inst = ObjectInverseOf(
        context=URIRef("http://example.com/g"),
        name_value=URIRef("http://example.com/inverse-node"),
        inverse_of=URIRef("http://example.com/parentOf"),
    )
    _assert_python_json_round_trip(ObjectInverseOf, inst)
    _assert_model_json_schema_smoke(ObjectInverseOf, "ObjectInverseOf")
    assert inst.as_quads == tuple((*t, inst.context) for t in inst.as_triples)


def test_disjoint_classes_round_trips_and_schema() -> None:
    axiom = DisjointClasses(
        context=URIRef("http://example.com/g"),
        class_expression_1=URIRef("http://example.com/Boy"),
        class_expression_2=URIRef("http://example.com/Girl"),
    )
    _assert_python_json_round_trip(DisjointClasses, axiom)
    _assert_model_json_schema_smoke(DisjointClasses, "DisjointClasses")
    assert axiom.as_quads == tuple((*t, axiom.context) for t in axiom.as_triples)


def test_disjoint_classes_nary_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_ternary_class_seq(
        ctx,
        list_head=URIRef("http://example.com/membersHead"),
        list_mid=URIRef("http://example.com/membersMid"),
        list_tail=URIRef("http://example.com/membersTail"),
    )
    inst = DisjointClassesNary(
        context=ctx,
        name_value=URIRef("http://example.com/all-disjoint"),
        members=seq,
    )
    _assert_round_trips_preserve_as_triples(DisjointClassesNary, inst)
    _assert_model_json_schema_smoke(DisjointClassesNary, "DisjointClassesNary")


def test_disjoint_classes_nary_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_binary_class_seq(
        ctx,
        list_head=URIRef("http://example.com/membersHead"),
        list_mid=URIRef("http://example.com/membersMid"),
    )
    with pytest.raises(ValidationError, match="n > 2"):
        DisjointClassesNary(
            context=ctx,
            name_value=URIRef("http://example.com/all-disjoint"),
            members=seq,
        )


def test_disjoint_classes_nary_rejects_mismatched_fragment_context() -> None:
    owner_ctx = URIRef("http://example.com/g-owner")
    fragment_ctx = URIRef("http://example.com/g-other")
    seq = _build_ternary_class_seq(
        fragment_ctx,
        list_head=URIRef("http://example.com/membersHead"),
        list_mid=URIRef("http://example.com/membersMid"),
        list_tail=URIRef("http://example.com/membersTail"),
    )
    with pytest.raises(ValidationError, match="StructuralFragment"):
        DisjointClassesNary(
            context=owner_ctx,
            name_value=URIRef("http://example.com/all-disjoint"),
            members=seq,
        )


def test_disjoint_union_round_trips_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    seq = _build_binary_class_seq(
        ctx,
        list_head=URIRef("http://example.com/duHead"),
        list_mid=URIRef("http://example.com/duMid"),
    )
    inst = DisjointUnion(
        context=ctx,
        union_class=URIRef("http://example.com/Child"),
        disjoint_union_of=seq,
    )
    _assert_round_trips_preserve_as_triples(DisjointUnion, inst)
    _assert_model_json_schema_smoke(DisjointUnion, "DisjointUnion")


def test_disjoint_union_rejects_under_arity() -> None:
    ctx = URIRef("http://example.com/g")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(
                cell=URIRef("http://example.com/c1"),
                value=URIRef("http://example.com/ClassA"),
            ),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    with pytest.raises(ValidationError, match="n >= 2"):
        DisjointUnion(
            context=ctx,
            union_class=URIRef("http://example.com/Child"),
            disjoint_union_of=seq,
        )
