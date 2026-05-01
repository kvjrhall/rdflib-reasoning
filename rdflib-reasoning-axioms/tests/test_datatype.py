import pytest
from rdflib import RDF, RDFS, BNode, URIRef
from rdflib_reasoning.axiom.datatype import (
    DataRange,
    DeclarationDatatype,
    RestrictionFacet,
)


@pytest.mark.xfail(reason="Cannot _enforce_ that DataRange is an abstract base class.")
def test_cannot_instantiate_abc_data_range():
    with pytest.raises(TypeError):
        DataRange(context=BNode(), name_value=BNode())


def test_cannot_instantiate_abc_restriction_facet():
    with pytest.raises(TypeError):
        RestrictionFacet(context=BNode())  # pyright: ignore[reportAbstractUsage]


def test_declaraction_datatype_as_triples():
    name = URIRef("http://example.com/SomeDatatype")
    declaration_datatype = DeclarationDatatype(context=BNode(), name_value=name)

    assert declaration_datatype.name == name
    assert declaration_datatype.rdf_type == RDFS.Datatype
    assert declaration_datatype.as_triples == ((name, RDF.type, RDFS.Datatype),)


def test_declaraction_datatype_json():
    expected = DeclarationDatatype(
        context=BNode(), name_value=URIRef("http://example.com/SomeDatatype")
    )
    json = expected.model_dump_json()
    actual = DeclarationDatatype.model_validate_json(json)

    assert actual == expected


def test_declaraction_datatype_python():
    expected = DeclarationDatatype(
        context=BNode(), name_value=URIRef("http://example.com/SomeDatatype")
    )
    python = expected.model_dump()
    actual = DeclarationDatatype.model_validate(python)

    assert actual == expected


def test_declaration_datatype_schema():
    # Tests that the schema does not raise an exception.
    DeclarationDatatype.model_json_schema()
