from pydantic import BaseModel
from rdflib import OWL, RDF, RDFS, URIRef
from rdflib_reasoning.axiom.class_axiom import DeclarationClass, SubClassOf


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


def test_declaration_class_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    name = URIRef("http://example.com/Person")
    declaration = DeclarationClass(context=ctx, name_value=name)

    assert declaration.name == name
    assert declaration.rdf_type == OWL.Class
    assert declaration.as_triples == ((name, RDF.type, OWL.Class),)


def test_declaration_class_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    declaration = DeclarationClass(
        context=ctx,
        name_value=URIRef("http://example.com/Person"),
    )

    assert declaration.as_quads == tuple((*t, ctx) for t in declaration.as_triples)


def test_declaration_class_python_json_round_trip_and_schema() -> None:
    declaration = DeclarationClass(
        context=URIRef("http://example.com/g"),
        name_value=URIRef("http://example.com/Person"),
    )

    _assert_python_json_round_trip(DeclarationClass, declaration)
    _assert_model_json_schema_smoke(DeclarationClass, "DeclarationClass")


def test_subclass_of_as_triples() -> None:
    ctx = URIRef("http://example.com/g")
    child = URIRef("http://example.com/Child")
    parent = URIRef("http://example.com/Parent")
    axiom = SubClassOf(
        context=ctx,
        sub_class_expression=child,
        super_class_expression=parent,
    )

    assert axiom.name == child
    assert axiom.as_triples == ((child, RDFS.subClassOf, parent),)


def test_subclass_of_as_quads() -> None:
    ctx = URIRef("http://example.com/g")
    axiom = SubClassOf(
        context=ctx,
        sub_class_expression=URIRef("http://example.com/Child"),
        super_class_expression=URIRef("http://example.com/Parent"),
    )

    assert axiom.as_quads == tuple((*t, ctx) for t in axiom.as_triples)


def test_subclass_of_python_json_round_trip_and_schema() -> None:
    axiom = SubClassOf(
        context=URIRef("http://example.com/g"),
        sub_class_expression=URIRef("http://example.com/Child"),
        super_class_expression=URIRef("http://example.com/Parent"),
    )

    _assert_python_json_round_trip(SubClassOf, axiom)
    _assert_model_json_schema_smoke(SubClassOf, "SubClassOf")
