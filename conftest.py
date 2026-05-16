"""Shared pytest fixtures for RDF / N3 term tests (middleware, axioms, etc.)."""

from __future__ import annotations

import datetime
from collections.abc import Generator
from typing import Any, Final
from xml.dom.minidom import Document

import pytest
from pytest import FixtureRequest
from rdflib import RDF, XSD, BNode, IdentifiedNode, Literal, Node, URIRef
from rdflib_reasoning.axiom.common import N3ContextIdentifier

type TestData[T] = Generator[T, Any, Any]


VALID_GRAPH_CONTEXTS: Final[tuple[N3ContextIdentifier, ...]] = (
    URIRef("http://example.com/valid-graph-context"),
    URIRef("http://example.com/valid-graph-context#fragment"),
    URIRef("urn:example:text:subpart"),
    BNode(value="g"),
    BNode(value="g1"),
    BNode(value="pascalCaseBlankGraph"),
    BNode(value="snake_case_blank_graph"),
)

VALID_PREDICATES: Final[tuple[URIRef, ...]] = (
    URIRef("http://example.com/valid-predicate"),
)

VALID_SUBJECTS: Final[tuple[IdentifiedNode, ...]] = (
    URIRef("http://example.com/valid-subject"),
    URIRef("http://example.com/valid-subject#fragment"),
    BNode(value="s"),
    BNode(value="b1"),
    BNode(value="pascalCaseBlankSubject"),
    BNode(value="snake_case_blank_subject"),
)


def _create_html_literal() -> Literal:
    doc = Document()
    frag = doc.createDocumentFragment()

    div = doc.createElement("div")
    frag.appendChild(div)

    span = doc.createElement("span")
    div.appendChild(span)

    text = doc.createTextNode("Hello, World!")
    span.appendChild(text)

    return Literal(frag, datatype=RDF.HTML)


def _create_xml_literal() -> Literal:
    doc = Document()
    root = doc.createElement("root")
    doc.appendChild(root)

    child = doc.createElement("child")
    root.appendChild(child)

    text = doc.createTextNode("Hello, World!")
    child.appendChild(text)

    return Literal(doc, datatype=RDF.XMLLiteral)


VALID_OBJECTS: Final[tuple[Node, ...]] = (
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
)


@pytest.fixture(
    params=VALID_GRAPH_CONTEXTS,
    ids=lambda param: param.n3(),
)
def valid_graph_context(request: FixtureRequest) -> TestData[N3ContextIdentifier]:
    yield request.param


@pytest.fixture(
    params=VALID_OBJECTS,
    ids=lambda param: param.n3(),
)
def valid_object(request: FixtureRequest) -> TestData[Node]:
    yield request.param


@pytest.fixture(
    params=VALID_PREDICATES,
    ids=lambda param: param.n3(),
)
def valid_predicate(request: FixtureRequest) -> TestData[URIRef]:
    yield request.param


@pytest.fixture(
    params=VALID_SUBJECTS,
    ids=lambda param: param.n3(),
)
def valid_subject(request: FixtureRequest) -> TestData[IdentifiedNode]:
    yield request.param


@pytest.fixture(
    params=[
        URIRef("relative/iri"),
        URIRef("#auth-1/2"),
        URIRef("../onto/events"),
        URIRef("image.png"),
        URIRef("?type=person"),
        URIRef("http://unescaped/iri characters"),
        URIRef("http://example.com/disallowed>characters"),
        BNode(value="_:s"),
        BNode(value="foo>bar"),
        BNode(value="endsWith."),
    ],
    ids=lambda param: str(param),
)
def bad_subject(request: FixtureRequest) -> TestData[IdentifiedNode]:
    yield request.param
