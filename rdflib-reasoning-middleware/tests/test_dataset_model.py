import datetime
import json
from collections.abc import Generator
from typing import Any
from xml.dom.minidom import Document

import pytest
import regex as re
from pydantic import (
    ConfigDict,
    TypeAdapter,
)
from rdflib import RDF, XSD, BNode, IdentifiedNode, Literal, Node, URIRef
from rdflib_reasoning.middleware.dataset_model import (
    _TURTLE_ECMA_BLANK_NODE_PATTERN,
    N3ContextIdentifier,
    N3IRIRef,
    N3Node,
    N3Quad,
    N3Resource,
    N3Triple,
)

type TestData[T] = Generator[T, Any, Any]

# =============================================================================
# Fixtures for RDF Nodes
# =============================================================================

turtle_regex = re.compile(_TURTLE_ECMA_BLANK_NODE_PATTERN)

# Fixtures for RDF Nodes - Valid terms
# -----------------------------------------------------------------------------


@pytest.fixture(
    params=[
        URIRef("http://example.com/valid-graph-context"),
        URIRef("http://example.com/valid-graph-context#fragment"),
        URIRef("urn:example:text:subpart"),
        BNode(value="g"),
        BNode(value="g1"),
        BNode(value="pascalCaseBlankGraph"),
        BNode(value="snake_case_blank_graph"),
    ],
    ids=lambda param: param.n3(),
)
def valid_graph_context(request) -> TestData[N3ContextIdentifier]:
    yield request.param


def _create_html_literal() -> Literal:
    doc = Document()
    frag = doc.createDocumentFragment()  # NOTE: HTML literals are a DocumentFragment

    div = doc.createElement("div")
    frag.appendChild(div)

    span = doc.createElement("span")
    div.appendChild(span)

    text = doc.createTextNode("Hello, World!")
    span.appendChild(text)

    return Literal(frag, datatype=RDF.HTML)


def _create_xml_literal() -> Literal:
    doc = Document()
    root = doc.createElement("root")  # NOTE: XML literals are a Document
    doc.appendChild(root)

    child = doc.createElement("child")
    root.appendChild(child)

    text = doc.createTextNode("Hello, World!")
    child.appendChild(text)

    return Literal(doc, datatype=RDF.XMLLiteral)


@pytest.fixture(
    params=[
        URIRef("http://example.com/valid-object"),
        BNode(value="o"),
        Literal("Nicholas"),
        Literal(39, datatype=XSD.integer),
        Literal("Nicholas", lang="en"),
        Literal(datetime.date(1987, 1, 1), datatype=XSD.date),
        Literal(datetime.datetime(1987, 1, 1, 12, 0, 0), datatype=XSD.dateTime),
        Literal(
            datetime.datetime(1987, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
            datatype=XSD.dateTimeStamp,
        ),
        Literal(True, datatype=XSD.boolean),
        Literal(False, datatype=XSD.boolean),
        Literal(1.0, datatype=XSD.float),
        Literal(1.0, datatype=XSD.double),
        Literal(1.0, datatype=XSD.decimal),
        Literal(1, datatype=XSD.integer),
        Literal(0, datatype=XSD.nonNegativeInteger),
        Literal(2, datatype=XSD.positiveInteger),
        _create_xml_literal(),
        _create_html_literal(),
    ],
    ids=lambda param: param.n3(),
)
def valid_object(request) -> TestData[Node]:
    yield request.param


@pytest.fixture(
    params=[URIRef("http://example.com/valid-predicate")],
    ids=lambda param: param.n3(),
)
def valid_predicate(request) -> TestData[URIRef]:
    yield request.param


@pytest.fixture(
    params=[
        URIRef("http://example.com/valid-subject"),
        URIRef("http://example.com/valid-subject#fragment"),
        BNode(value="s"),
        BNode(value="b1"),
        BNode(value="pascalCaseBlankSubject"),
        BNode(value="snake_case_blank_subject"),
    ],
    ids=lambda param: param.n3(),
)
def valid_subject(request) -> TestData[IdentifiedNode]:
    yield request.param


# Fixtures for RDF Nodes - Invalid terms (valdation errors)
# -----------------------------------------------------------------------------


@pytest.fixture(
    params=[
        URIRef("relative/iri"),
        URIRef("#auth-1/2"),
        URIRef("../onto/events"),
        URIRef("image.png"),
        URIRef("?type=person"),
        URIRef("http://unescaped/iri characters"),  # Caught by rdflib
        URIRef("http://example.com/disallowed>characters"),  # Caught by rdflib
        BNode(value="_:s"),  # '_:_:s' is not a valid blank node, common mistake
        BNode(value="foo>bar"),  # > is a disallowed character
        BNode(value="endsWith."),  # Cannot end with a period
    ],
    ids=lambda param: str(param),
)
def bad_subject(request) -> TestData[IdentifiedNode]:
    yield request.param


# =============================================================================
# RDF Nodes
# =============================================================================

graph_context_adapter: TypeAdapter[N3ContextIdentifier] = TypeAdapter(
    N3ContextIdentifier, config=ConfigDict(arbitrary_types_allowed=True)
)

object_adapter: TypeAdapter[N3Node] = TypeAdapter(
    N3Node, config=ConfigDict(arbitrary_types_allowed=True)
)

predicate_adapter: TypeAdapter[N3IRIRef] = TypeAdapter(
    N3IRIRef, config=ConfigDict(arbitrary_types_allowed=True)
)

subject_adapter: TypeAdapter[N3Resource] = TypeAdapter(
    N3Resource, config=ConfigDict(arbitrary_types_allowed=True)
)


# RDF Nodes - Generated Schemas
# -----------------------------------------------------------------------------


def test_ecma_blank_node_pattern_is_valid(valid_subject: IdentifiedNode) -> None:
    if not isinstance(valid_subject, BNode):
        pytest.skip("Skipping test for non-blank node")
    assert turtle_regex.match(valid_subject.n3()) is not None


def test_graph_context_schema_is_valid() -> None:
    schema = graph_context_adapter.json_schema()
    assert schema is not None
    pretty_schema = json.dumps(schema, indent=2, sort_keys=True)

    assert schema.get("type") == "string", (
        f"Schema 'type' field should be present and set to 'string': {pretty_schema}"
    )

    # NOTE: Not supported by vLLM backend, yet.
    # assert (one_of := schema.get("oneOf")) is not None and isinstance(
    #     one_of, Sequence
    # ), f"'oneOf' should be present and a JSON array: {pretty_schema}"
    #
    # assert len(one_of) == 2, (
    #     f"Exactly two items alternatives should exist for N3Subject': {pretty_schema}"
    # )
    # assert any(item.get("format") == "iri" for item in one_of), (
    #     f"Exactly one item in 'oneOf' should have 'format' set to 'iri': {pretty_schema}"
    # )
    # assert any(isinstance(item.get("pattern"), str) for item in one_of), (
    #     f"Exactly one item in 'oneOf' should have 'pattern' for blank nodes: {pretty_schema}"
    # )


def test_object_schema_is_valid() -> None:
    schema = object_adapter.json_schema()
    assert schema is not None
    pretty_schema = json.dumps(schema, indent=2, sort_keys=True)

    assert schema.get("type") == "string", (
        f"Schema 'type' field should be present and set to 'string': {pretty_schema}"
    )


def test_predicate_schema_is_valid() -> None:
    schema = predicate_adapter.json_schema()
    assert schema is not None
    assert schema.get("type") == "string"
    # NOTE: Not supported by vLLM backend, yet.
    # assert schema.get("format") == "iri"


def test_subject_schema_is_valid() -> None:
    schema = subject_adapter.json_schema()
    assert schema is not None
    pretty_schema = json.dumps(schema, indent=2, sort_keys=True)

    assert schema.get("type") == "string", (
        f"Schema 'type' field should be present and set to 'string': {pretty_schema}"
    )

    # NOTE: Not supported by vLLM backend, yet.
    # assert (one_of := schema.get("oneOf")) is not None and isinstance(
    #     one_of, Sequence
    # ), f"'oneOf' should be present and a JSON array: {pretty_schema}"
    # assert len(one_of) == 2, (
    #     f"Exactly two items alternatives should exist for N3Subject': {pretty_schema}"
    # )
    # assert any(item.get("format") == "iri" for item in one_of), (
    #     f"Exactly one item in 'oneOf' should have 'format' set to 'iri': {pretty_schema}"
    # )
    # assert any(isinstance(item.get("pattern"), str) for item in one_of), (
    #     f"Exactly one item in 'oneOf' should have 'pattern' for blank nodes: {pretty_schema}"
    # )


# RDF Nodes - TypeAdapters/Serialization
# -----------------------------------------------------------------------------


def test_graph_context_adapter_serializes_and_deserializes_python(
    valid_graph_context: N3ContextIdentifier,
) -> None:
    python = graph_context_adapter.dump_python(valid_graph_context)
    assert graph_context_adapter.validate_python(python) == valid_graph_context


def test_graph_context_adapter_serializes_and_deserializes_json(
    valid_graph_context: N3ContextIdentifier,
) -> None:
    json = graph_context_adapter.dump_json(valid_graph_context).decode("utf-8")
    assert graph_context_adapter.validate_json(json) == valid_graph_context, (
        f"Unexpected JSON dumped: {json}"
    )


def test_subject_adapter_serializes_and_deserializes_python(
    valid_subject: IdentifiedNode,
) -> None:
    python = subject_adapter.dump_python(valid_subject)
    assert subject_adapter.validate_python(python) == valid_subject


def test_subject_adapter_serializes_and_deserializes_json(
    valid_subject: IdentifiedNode,
) -> None:
    json = subject_adapter.dump_json(valid_subject).decode("utf-8")
    assert subject_adapter.validate_json(json) == valid_subject, (
        f"Unexpected JSON dumped: {json}"
    )


def test_subject_adapter_accepts_bare_iri_input_and_serializes_canonically() -> None:
    subject = subject_adapter.validate_python("urn:example:subject")

    assert subject == URIRef("urn:example:subject")
    assert subject_adapter.dump_python(subject) == "<urn:example:subject>"


def test_predicate_adapter_serializes_and_deserializes_python(
    valid_predicate: URIRef,
) -> None:
    python = predicate_adapter.dump_python(valid_predicate)
    assert predicate_adapter.validate_python(python) == valid_predicate


def test_predicate_adapter_serializes_and_deserializes_json(
    valid_predicate: URIRef,
) -> None:
    json = predicate_adapter.dump_json(valid_predicate).decode("utf-8")
    assert predicate_adapter.validate_json(json) == valid_predicate, (
        f"Unexpected JSON dumped: {json}"
    )


def test_predicate_adapter_accepts_bare_iri_input_and_serializes_canonically() -> None:
    predicate = predicate_adapter.validate_python("urn:example:predicate")

    assert predicate == URIRef("urn:example:predicate")
    assert predicate_adapter.dump_python(predicate) == "<urn:example:predicate>"


def test_object_adapter_serializes_and_deserializes_python(
    valid_object: Node,
) -> None:
    python = object_adapter.dump_python(valid_object)
    assert object_adapter.validate_python(python) == valid_object


def test_object_adapter_serializes_and_deserializes_json(
    valid_object: Node,
) -> None:
    json = object_adapter.dump_json(valid_object).decode("utf-8")
    assert object_adapter.validate_json(json) == valid_object, (
        f"Unexpected JSON dumped: {json}"
    )


def test_object_adapter_accepts_bare_iri_input_and_serializes_canonically() -> None:
    obj = object_adapter.validate_python("urn:example:object")

    assert obj == URIRef("urn:example:object")
    assert object_adapter.dump_python(obj) == "<urn:example:object>"


# RDF Nodes - Serialization Failures
# -----------------------------------------------------------------------------


def test_rejects_illegal_subject_python(bad_subject: IdentifiedNode) -> None:
    with pytest.raises(ValueError):
        subject_adapter.validate_python(bad_subject)


def test_invalid_bare_string_error_mentions_iri_recovery_hint() -> None:
    with pytest.raises(ValueError, match="canonical N3 form") as exc_info:
        object_adapter.validate_python(r"not\an\iri")

    assert "bare RFC 3987 IRI" in str(exc_info.value)
    assert "plain text" not in str(exc_info.value)


def test_plain_text_string_error_mentions_literal_recovery_hint() -> None:
    with pytest.raises(ValueError, match="plain text") as exc_info:
        object_adapter.validate_python("A person is an individual.")

    assert 'literal like "\\"A person is an individual.\\""' in str(exc_info.value)
    assert "bare RFC 3987 IRI" in str(exc_info.value)


# =============================================================================
# N3Triple Model
# =============================================================================

# N3Triple Model - Schema
# -----------------------------------------------------------------------------


def test_triple_schema_is_valid() -> None:
    schema = N3Triple.model_json_schema()
    assert schema is not None
    pretty_schema = json.dumps(schema, indent=2, sort_keys=True)

    assert schema.get("type") == "object", pretty_schema
    assert schema.get("required") == ["subject", "predicate", "object"], pretty_schema

    properties = schema.get("properties")
    assert isinstance(properties, dict), pretty_schema
    assert set(properties) == {"subject", "predicate", "object"}, pretty_schema
    assert properties["subject"].get("$ref") == "#/$defs/N3Resource", pretty_schema
    assert properties["predicate"].get("$ref") == "#/$defs/N3IRIRef", pretty_schema
    assert properties["object"].get("$ref") == "#/$defs/N3Node", pretty_schema


# N3Triple Model - Serialization
# -----------------------------------------------------------------------------


def test_triple_serializes_and_deserializes_python(
    valid_subject: IdentifiedNode,
    valid_predicate: URIRef,
    valid_object: Node,
) -> None:
    triple = N3Triple(
        subject=valid_subject,
        predicate=valid_predicate,
        object=valid_object,
    )
    python = triple.model_dump()
    assert triple.model_validate(python) == triple


def test_triple_serializes_and_deserializes_json(
    valid_subject: IdentifiedNode,
    valid_predicate: URIRef,
    valid_object: Node,
) -> None:
    triple = N3Triple(
        subject=valid_subject,
        predicate=valid_predicate,
        object=valid_object,
    )
    json = triple.model_dump_json()
    assert N3Triple.model_validate_json(json) == triple


def test_triple_accepts_bare_iris_and_serializes_to_canonical_n3() -> None:
    triple = N3Triple(
        subject="urn:example:subject",
        predicate="urn:example:predicate",
        object="urn:example:object",
    )

    assert triple.subject == URIRef("urn:example:subject")
    assert triple.predicate == URIRef("urn:example:predicate")
    assert triple.object == URIRef("urn:example:object")
    assert json.loads(triple.model_dump_json()) == {
        "subject": "<urn:example:subject>",
        "predicate": "<urn:example:predicate>",
        "object": "<urn:example:object>",
    }


# N3Triple Model - Serialization Failures
# -----------------------------------------------------------------------------

# TODO create some explicit tests for serialization failures

# =============================================================================
# N3Quad Model
# =============================================================================

# N3Quad Model - Schema
# -----------------------------------------------------------------------------


def test_quad_schema_is_valid() -> None:
    schema = N3Quad.model_json_schema()
    assert schema is not None
    pretty_schema = json.dumps(schema, indent=2, sort_keys=True)

    quad = N3Quad(
        subject=URIRef("http://example.com/valid-subject"),
        predicate=URIRef("http://example.com/valid-predicate"),
        object=URIRef("http://example.com/valid-object"),
        graph_id=URIRef("http://example.com/valid-graph-context"),
    )
    quad_json = quad.model_dump_json(indent=2)

    assert schema.get("type") == "object", pretty_schema
    assert schema.get("required") == ["subject", "predicate", "object", "graph_id"], (
        pretty_schema
    )

    properties = schema.get("properties")
    assert isinstance(properties, dict), pretty_schema
    assert set(properties) == {"subject", "predicate", "object", "graph_id"}, (
        pretty_schema
    )
    assert "graph" not in properties, pretty_schema
    assert properties["subject"].get("$ref") == "#/$defs/N3Resource", pretty_schema
    assert properties["predicate"].get("$ref") == "#/$defs/N3IRIRef", pretty_schema
    assert properties["object"].get("$ref") == "#/$defs/N3Node", pretty_schema
    assert properties["graph_id"].get("$ref") == "#/$defs/N3ContextIdentifier", (
        pretty_schema
    )
    assert '"graph_id": "<http://example.com/valid-graph-context>"' in quad_json


# N3Quad Model - Serialization
# -----------------------------------------------------------------------------


def test_quad_serializes_and_deserializes_python(
    valid_subject: IdentifiedNode,
    valid_predicate: URIRef,
    valid_object: Node,
    valid_graph_context: N3ContextIdentifier,
) -> None:
    quad = N3Quad(
        subject=valid_subject,
        predicate=valid_predicate,
        object=valid_object,
        graph_id=valid_graph_context,
    )
    python = quad.model_dump()
    assert N3Quad.model_validate(python) == quad


def test_quad_serializes_and_deserializes_json(
    valid_subject: IdentifiedNode,
    valid_predicate: URIRef,
    valid_object: Node,
    valid_graph_context: N3ContextIdentifier,
) -> None:
    quad = N3Quad(
        subject=valid_subject,
        predicate=valid_predicate,
        object=valid_object,
        graph_id=valid_graph_context,
    )
    json = quad.model_dump_json()
    assert N3Quad.model_validate_json(json) == quad


# N3Quad Model - Serialization Failures
# -----------------------------------------------------------------------------

# TODO create some explicit tests for serialization failures


regression = {
    "triples": [
        {
            "subject": "urn:ex:Hominidae",
            "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "object": "http://www.w3.org/2002/07/owls#Class",
        },
        {
            "subject": "urn:ex:Hominidae",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "object": "Hominidae",
        },
        {
            "subject": "urn:ex:Hominidae",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#comment",
            "object": '"Hominidae is a subtribe that includes humans and their extinct ancestors."',
        },
        {
            "subject": "urn:ex:Hominina",
            "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "object": "http://www.w3.org/2002/07/owls#Class",
        },
        {
            "subject": "urn:ex:Hominina",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "object": "Hominina",
        },
        {
            "subject": "urn:ex:Hominina",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#comment",
            "object": '"Hominina is a subtribe that includes humans and their closest relatives."',
        },
        {
            "subject": "urn:ex:Haplorhini",
            "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "object": "http://www.w3.org/2002/07/owls#Class",
        },
        {
            "subject": "urn:ex:Haplorhini",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "object": "Haplorhini",
        },
        {
            "subject": "urn:ex:Haplorhini",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#comment",
            "object": '"Haplorhini is a suborder of primates that includes humans and their relatives."',
        },
        {
            "subject": "urn:ex:person",
            "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "object": "http://www.w3.org/2002/07/owls#Class",
        },
        {
            "subject": "urn:ex:person",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "object": "person",
        },
        {
            "subject": "urn:ex:person",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#comment",
            "object": '"A biological classification for humans."',
        },
        {
            "subject": "urn:ex:homo_sapiens",
            "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "object": "http://www.w3.org/2002/07/owls#Class",
        },
        {
            "subject": "urn:ex:homo_sapiens",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "object": '"homo sapiens"',
        },
        {
            "subject": "urn:ex:homo_sapiens",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#comment",
            "object": '"Modern humans, classified under the species homo sapiens."',
        },
        {
            "subject": "urn:ex:primates",
            "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "object": "http://www.w3.org/2002/07/owls#Class",
        },
        {
            "subject": "urn:ex:primates",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "object": "primates",
        },
        {
            "subject": "urn:ex:primates",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#comment",
            "object": '"Primates are a diverse group of mammals that includes humans and their relatives."',
        },
        {
            "subject": "urn:ex:mammals",
            "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "object": "http://www.w3.org/2002/07/owls#Class",
        },
        {
            "subject": "urn:ex:mammals",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "object": "mammals",
        },
        {
            "subject": "urn:ex:mammals",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#comment",
            "object": '"Mammals are a class of vertebrates that includes humans and other animals with hair or fur."',
        },
        {
            "subject": "urn:ex:animals",
            "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "object": "http://www.w3.org/2002/07/owls#Class",
        },
        {
            "subject": "urn:ex:animals",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "object": "animals",
        },
        {
            "subject": "urn:ex:animals",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#comment",
            "object": '"Animals are multicellular organisms that are capable of voluntary movement."',
        },
        {
            "subject": "urn:ex:John",
            "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "object": "urn:ex:person",
        },
        {
            "subject": "urn:ex:John",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "object": "John",
        },
        {
            "subject": "urn:ex:John",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#comment",
            "object": '"An instance of a person."',
        },
    ]
}


@pytest.fixture(params=regression["triples"])
def regression_triple(request) -> TestData[dict[str, str]]:
    yield request.param


def test_regression_triple_deserialize(regression_triple: dict[str, str]) -> None:
    # SHOULD NOT THROW
    N3Triple.model_validate(regression_triple)


def test_regression_triples_deserialize() -> None:
    adapter = TypeAdapter(list[N3Triple])
    # SHOULD NOT THROW
    adapter.validate_python(regression["triples"])
