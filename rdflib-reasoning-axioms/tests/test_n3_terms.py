"""Unit tests for schema-facing N3 type aliases in ``rdflib_reasoning.axiom.n3_terms``."""

import json

import pytest
import regex as re
from pydantic import ConfigDict, TypeAdapter
from rdflib import BNode, IdentifiedNode, Node, URIRef
from rdflib_reasoning.axiom.common import (
    N3ContextIdentifier,
    N3IRIRef,
    N3Node,
    N3Resource,
)
from rdflib_reasoning.axiom.n3_terms import TURTLE_ECMA_BLANK_NODE_PATTERN

turtle_regex = re.compile(TURTLE_ECMA_BLANK_NODE_PATTERN)

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


def test_subject_schema_is_valid() -> None:
    schema = subject_adapter.json_schema()
    assert schema is not None
    pretty_schema = json.dumps(schema, indent=2, sort_keys=True)

    assert schema.get("type") == "string", (
        f"Schema 'type' field should be present and set to 'string': {pretty_schema}"
    )


def test_graph_context_adapter_serializes_and_deserializes_python(
    valid_graph_context: N3ContextIdentifier,
) -> None:
    python = graph_context_adapter.dump_python(valid_graph_context)
    assert graph_context_adapter.validate_python(python) == valid_graph_context


def test_graph_context_adapter_serializes_and_deserializes_json(
    valid_graph_context: N3ContextIdentifier,
) -> None:
    json_text = graph_context_adapter.dump_json(valid_graph_context).decode("utf-8")
    assert graph_context_adapter.validate_json(json_text) == valid_graph_context, (
        f"Unexpected JSON dumped: {json_text}"
    )


def test_subject_adapter_serializes_and_deserializes_python(
    valid_subject: IdentifiedNode,
) -> None:
    python = subject_adapter.dump_python(valid_subject)
    assert subject_adapter.validate_python(python) == valid_subject


def test_subject_adapter_serializes_and_deserializes_json(
    valid_subject: IdentifiedNode,
) -> None:
    json_text = subject_adapter.dump_json(valid_subject).decode("utf-8")
    assert subject_adapter.validate_json(json_text) == valid_subject, (
        f"Unexpected JSON dumped: {json_text}"
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
    json_text = predicate_adapter.dump_json(valid_predicate).decode("utf-8")
    assert predicate_adapter.validate_json(json_text) == valid_predicate, (
        f"Unexpected JSON dumped: {json_text}"
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
    json_text = object_adapter.dump_json(valid_object).decode("utf-8")
    assert object_adapter.validate_json(json_text) == valid_object, (
        f"Unexpected JSON dumped: {json_text}"
    )


def test_object_adapter_accepts_bare_iri_input_and_serializes_canonically() -> None:
    obj = object_adapter.validate_python("urn:example:object")

    assert obj == URIRef("urn:example:object")
    assert object_adapter.dump_python(obj) == "<urn:example:object>"


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


def test_single_token_plain_text_error_mentions_literal_recovery_hint() -> None:
    with pytest.raises(ValueError, match="plain text") as exc_info:
        object_adapter.validate_python("Person")

    assert 'literal like "\\"Person\\""' in str(exc_info.value)
    assert "bare RFC 3987 IRI" in str(exc_info.value)
