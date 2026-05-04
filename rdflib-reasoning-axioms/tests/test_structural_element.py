import pytest
from pydantic import ValidationError
from rdflib import RDF, BNode, URIRef
from rdflib_reasoning.axiom.datatype import DeclarationDatatype
from rdflib_reasoning.axiom.structural_element import (
    DeclarationElement,
    GraphBacked,
    Seq,
    StructuralElement,
)


def test_cannot_instantiate_abc_graph_backed() -> None:
    with pytest.raises(TypeError):
        GraphBacked(context=BNode())


def test_cannot_instantiate_abc_structural_element() -> None:
    with pytest.raises(TypeError):
        StructuralElement(context=BNode())  # type: ignore[abstract]  # pyright: ignore[reportAbstractUsage]


def test_cannot_instantiate_abc_declaration_element() -> None:
    with pytest.raises(TypeError):
        DeclarationElement(  # type: ignore[abstract]  # pyright: ignore[reportAbstractUsage]
            context=BNode(),
            name_value=BNode(),
        )


def test_seq_as_triples_two_element_list() -> None:
    ctx = BNode()
    l1, l2 = BNode(), BNode()
    e1 = DeclarationDatatype(context=ctx, name_value=URIRef("http://example.com/a"))
    e2 = DeclarationDatatype(context=ctx, name_value=URIRef("http://example.com/b"))
    seq = Seq(context=ctx, names=(l1, l2), elements=(e1, e2))

    assert seq.as_triples == (
        (l1, RDF.first, e1.name),
        (l2, RDF.first, e2.name),
        (l1, RDF.rest, l2),
        (l2, RDF.rest, RDF.nil),
    )


def test_seq_as_quads_appends_context() -> None:
    ctx = BNode()
    l1 = BNode()
    e1 = DeclarationDatatype(context=ctx, name_value=URIRef("http://example.com/a"))
    seq = Seq(context=ctx, names=(l1,), elements=(e1,))

    assert seq.as_quads == tuple((*t, ctx) for t in seq.as_triples)


def test_seq_python_json_round_trip_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    e1 = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/cell-a")
    )
    list_head = URIRef("http://example.com/listHead")
    seq = Seq[DeclarationDatatype](context=ctx, names=(list_head,), elements=(e1,))
    dumped = seq.model_dump()
    assert Seq[DeclarationDatatype].model_validate(dumped).as_triples == seq.as_triples
    from_json = Seq[DeclarationDatatype].model_validate_json(seq.model_dump_json())
    assert from_json.as_triples == seq.as_triples
    schema = Seq[DeclarationDatatype].model_json_schema()
    assert schema.get("title") == "Seq[DeclarationDatatype]"
    assert "context" in schema["properties"]
    assert "names" in schema["properties"]
    assert "elements" in schema["properties"]


def test_seq_rejects_mismatched_names_and_elements_length() -> None:
    ctx = BNode()
    with pytest.raises(ValidationError, match="MUST match"):
        Seq(
            context=ctx,
            names=(BNode(), BNode()),
            elements=(
                DeclarationDatatype(
                    context=ctx, name_value=URIRef("http://example.com/a")
                ),
            ),
        )


def test_seq_rejects_duplicate_list_heads() -> None:
    ctx = BNode()
    shared = BNode()
    e1 = DeclarationDatatype(context=ctx, name_value=URIRef("http://example.com/a"))
    e2 = DeclarationDatatype(context=ctx, name_value=URIRef("http://example.com/b"))
    with pytest.raises(ValidationError, match="duplicates"):
        Seq(context=ctx, names=(shared, shared), elements=(e1, e2))


def test_seq_rejects_rdf_nil_as_list_head() -> None:
    ctx = BNode()
    e1 = DeclarationDatatype(context=ctx, name_value=URIRef("http://example.com/a"))
    with pytest.raises(ValidationError, match="rdf:nil"):
        Seq(context=ctx, names=(RDF.nil,), elements=(e1,))


def test_seq_rejects_cross_context_elements() -> None:
    ctx_a = BNode()
    ctx_b = BNode()
    e1 = DeclarationDatatype(context=ctx_b, name_value=URIRef("http://example.com/a"))
    with pytest.raises(ValidationError, match="same context"):
        Seq(
            context=ctx_a,
            names=(BNode(),),
            elements=(e1,),
        )
