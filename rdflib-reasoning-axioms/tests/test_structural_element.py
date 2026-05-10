import pytest
from pydantic import ValidationError
from rdflib import RDF, BNode, URIRef
from rdflib_reasoning.axiom.datatype import DeclarationDatatype
from rdflib_reasoning.axiom.structural_element import (
    DeclarationElement,
    GraphBacked,
    Seq,
    SeqEntry,
    StructuralElement,
    StructuralFragment,
)


def test_cannot_instantiate_abc_graph_backed() -> None:
    with pytest.raises(TypeError):
        GraphBacked(context=BNode())


def test_cannot_instantiate_abc_structural_element() -> None:
    with pytest.raises(TypeError):
        StructuralElement(context=BNode())  # type: ignore[abstract]  # pyright: ignore[reportAbstractUsage]


def test_cannot_instantiate_abc_structural_fragment() -> None:
    with pytest.raises(TypeError):
        StructuralFragment(context=BNode())  # type: ignore[abstract]  # pyright: ignore[reportAbstractUsage]


def test_seq_is_structural_fragment() -> None:
    ctx = BNode()
    seq = Seq(context=ctx, entries=(SeqEntry(cell=RDF.nil, value=None),))
    assert isinstance(seq, StructuralFragment)
    assert isinstance(seq, GraphBacked)
    assert not isinstance(seq, StructuralElement)


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
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=l1, value=e1.name),
            SeqEntry(cell=l2, value=e2.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )

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
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=l1, value=e1.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )

    assert seq.as_quads == tuple((*t, ctx) for t in seq.as_triples)


def test_seq_python_json_round_trip_and_schema() -> None:
    ctx = URIRef("http://example.com/g")
    e1 = DeclarationDatatype(
        context=ctx, name_value=URIRef("http://example.com/cell-a")
    )
    list_head = URIRef("http://example.com/listHead")
    seq = Seq(
        context=ctx,
        entries=(
            SeqEntry(cell=list_head, value=e1.name),
            SeqEntry(cell=RDF.nil, value=None),
        ),
    )
    dumped = seq.model_dump()
    assert Seq.model_validate(dumped).as_triples == seq.as_triples
    from_json = Seq.model_validate_json(seq.model_dump_json())
    assert from_json.as_triples == seq.as_triples
    schema = Seq.model_json_schema()
    assert schema.get("title") == "Seq"
    assert "context" in schema["properties"]
    assert "entries" in schema["properties"]
    assert "names" not in schema["properties"]


def test_seq_rejects_missing_terminal_sentinel() -> None:
    ctx = BNode()
    head = BNode()
    with pytest.raises(ValidationError, match="last entry"):
        Seq(
            context=ctx,
            entries=(
                SeqEntry(
                    cell=head,
                    value=URIRef("http://example.com/a"),
                ),
            ),
        )


def test_seq_rejects_duplicate_list_cells() -> None:
    ctx = BNode()
    shared = BNode()
    with pytest.raises(ValidationError, match="duplicates"):
        Seq(
            context=ctx,
            entries=(
                SeqEntry(cell=shared, value=URIRef("http://example.com/a")),
                SeqEntry(cell=shared, value=URIRef("http://example.com/b")),
                SeqEntry(cell=RDF.nil, value=None),
            ),
        )


def test_seq_rejects_rdf_nil_cell_with_value() -> None:
    ctx = BNode()
    with pytest.raises(ValidationError, match="rdf:nil"):
        Seq(
            context=ctx,
            entries=(SeqEntry(cell=RDF.nil, value=URIRef("http://example.com/a")),),
        )


def test_seq_rejects_empty_entries() -> None:
    ctx = BNode()
    with pytest.raises(ValidationError, match="empty list"):
        Seq(context=ctx, entries=())


def test_seq_empty_list_encoding_emits_no_triples() -> None:
    """OWL empty RDF list: only ``rdf:nil`` sentinel row; no ``rdf:first`` / ``rdf:rest`` triples."""
    ctx = BNode()
    seq = Seq(context=ctx, entries=(SeqEntry(cell=RDF.nil, value=None),))
    assert seq.name == RDF.nil
    assert seq.as_triples == ()
