import json
from dataclasses import dataclass
from typing import Final

import pytest
from pydantic import TypeAdapter
from rdflib import IdentifiedNode, Node, URIRef
from rdflib_reasoning.axiom.common import N3ContextIdentifier
from rdflib_reasoning.middleware.dataset_model import N3Quad, N3Triple

from conftest import (
    VALID_GRAPH_CONTEXTS,
    VALID_OBJECTS,
    VALID_PREDICATES,
    VALID_SUBJECTS,
)

# RDF node fixtures (``valid_*``, ``bad_subject``) live in the repository root
# ``conftest.py`` so axioms N3 tests and middleware dataset tests share them.


@dataclass(frozen=True, slots=True)
class TripleRoundTripCase:
    id: str
    subject: IdentifiedNode
    predicate: URIRef
    object_node: Node


@dataclass(frozen=True, slots=True)
class QuadRoundTripCase:
    id: str
    subject: IdentifiedNode
    predicate: URIRef
    object_node: Node
    graph_id: N3ContextIdentifier


TRIPLE_ROUND_TRIP_CASES: Final[tuple[TripleRoundTripCase, ...]] = tuple(
    TripleRoundTripCase(
        id=f"triple-{index:02d}",
        subject=VALID_SUBJECTS[index % len(VALID_SUBJECTS)],
        predicate=VALID_PREDICATES[index % len(VALID_PREDICATES)],
        object_node=VALID_OBJECTS[index % len(VALID_OBJECTS)],
    )
    for index in range(
        max(len(VALID_SUBJECTS), len(VALID_PREDICATES), len(VALID_OBJECTS))
    )
)


QUAD_ROUND_TRIP_CASES: Final[tuple[QuadRoundTripCase, ...]] = tuple(
    QuadRoundTripCase(
        id=f"quad-o{object_index:02d}-g{graph_index:02d}",
        subject=VALID_SUBJECTS[(object_index + graph_index) % len(VALID_SUBJECTS)],
        predicate=VALID_PREDICATES[
            (object_index + graph_index) % len(VALID_PREDICATES)
        ],
        object_node=object_node,
        graph_id=graph_id,
    )
    for object_index, object_node in enumerate(VALID_OBJECTS)
    for graph_index, graph_id in enumerate(VALID_GRAPH_CONTEXTS)
)

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

    object_examples = properties["object"].get("examples")
    assert isinstance(object_examples, list), pretty_schema
    assert '"Project report"' in object_examples, pretty_schema
    assert '"A short human-readable description."' in object_examples, pretty_schema

    n3_node_schema = schema["$defs"]["N3Node"]
    assert '"Project report"' in n3_node_schema.get("examples", []), pretty_schema


# N3Triple Model - Serialization
# -----------------------------------------------------------------------------


def test_triple_round_trip_cases_cover_each_valid_term() -> None:
    assert {case.subject for case in TRIPLE_ROUND_TRIP_CASES} == set(VALID_SUBJECTS)
    assert {case.predicate for case in TRIPLE_ROUND_TRIP_CASES} == set(VALID_PREDICATES)
    assert {case.object_node for case in TRIPLE_ROUND_TRIP_CASES} == set(VALID_OBJECTS)


@pytest.mark.parametrize(
    "case",
    TRIPLE_ROUND_TRIP_CASES,
    ids=lambda case: case.id,
)
def test_triple_serializes_and_deserializes(
    case: TripleRoundTripCase,
) -> None:
    triple = N3Triple(
        subject=case.subject,
        predicate=case.predicate,
        object=case.object_node,
    )
    python = triple.model_dump()
    assert triple.model_validate(python) == triple

    json_payload = triple.model_dump_json()
    assert N3Triple.model_validate_json(json_payload) == triple


def test_triple_accepts_bare_iris_and_serializes_to_canonical_n3() -> None:
    triple = N3Triple(
        subject=URIRef("urn:example:subject"),
        predicate=URIRef("urn:example:predicate"),
        object=URIRef("urn:example:object"),
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


def test_quad_round_trip_cases_cover_pairwise_subject_object_graph_design() -> None:
    assert len(QUAD_ROUND_TRIP_CASES) == len(VALID_OBJECTS) * len(VALID_GRAPH_CONTEXTS)
    assert {case.subject for case in QUAD_ROUND_TRIP_CASES} == set(VALID_SUBJECTS)
    assert {case.predicate for case in QUAD_ROUND_TRIP_CASES} == set(VALID_PREDICATES)
    assert {case.object_node for case in QUAD_ROUND_TRIP_CASES} == set(VALID_OBJECTS)
    assert {case.graph_id for case in QUAD_ROUND_TRIP_CASES} == set(
        VALID_GRAPH_CONTEXTS
    )

    assert {(case.subject, case.object_node) for case in QUAD_ROUND_TRIP_CASES} == {
        (subject, object_node)
        for subject in VALID_SUBJECTS
        for object_node in VALID_OBJECTS
    }
    assert {(case.subject, case.graph_id) for case in QUAD_ROUND_TRIP_CASES} == {
        (subject, graph_id)
        for subject in VALID_SUBJECTS
        for graph_id in VALID_GRAPH_CONTEXTS
    }
    assert {(case.object_node, case.graph_id) for case in QUAD_ROUND_TRIP_CASES} == {
        (object_node, graph_id)
        for object_node in VALID_OBJECTS
        for graph_id in VALID_GRAPH_CONTEXTS
    }


@pytest.mark.parametrize(
    "case",
    QUAD_ROUND_TRIP_CASES,
    ids=lambda case: case.id,
)
def test_quad_serializes_and_deserializes(
    case: QuadRoundTripCase,
) -> None:
    quad = N3Quad(
        subject=case.subject,
        predicate=case.predicate,
        object=case.object_node,
        graph_id=case.graph_id,
    )
    python = quad.model_dump()
    assert N3Quad.model_validate(python) == quad

    json_payload = quad.model_dump_json()
    assert N3Quad.model_validate_json(json_payload) == quad


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
            "object": '"Hominidae"',
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
            "object": '"Hominina"',
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
            "object": '"Haplorhini"',
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
            "object": '"person"',
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
            "object": '"primates"',
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
            "object": '"mammals"',
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
            "object": '"animals"',
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
            "object": '"John"',
        },
        {
            "subject": "urn:ex:John",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#comment",
            "object": '"An instance of a person."',
        },
    ]
}


@pytest.fixture(params=regression["triples"])
def regression_triple(request) -> dict[str, str]:
    return request.param


def test_regression_triple_deserialize(regression_triple: dict[str, str]) -> None:
    # SHOULD NOT THROW
    N3Triple.model_validate(regression_triple)


def test_regression_triples_deserialize() -> None:
    adapter = TypeAdapter(list[N3Triple])
    # SHOULD NOT THROW
    adapter.validate_python(regression["triples"])
