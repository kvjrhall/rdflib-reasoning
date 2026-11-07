"""Tests for OWL 2 RL datatype value-space membership helpers."""

from __future__ import annotations

import warnings

from rdflib import RDF, RDFS, XSD, Literal, URIRef
from rdflib_reasoning.engine.owl2_rl_datatypes import (
    OWL2_RL_SUPPORTED_DATATYPES,
    literal_value_in_datatype,
)


def test_supported_datatypes_include_core_iris() -> None:
    assert RDFS.Literal in OWL2_RL_SUPPORTED_DATATYPES
    assert RDF.PlainLiteral in OWL2_RL_SUPPORTED_DATATYPES
    assert XSD.integer in OWL2_RL_SUPPORTED_DATATYPES
    assert XSD.dateTimeStamp in OWL2_RL_SUPPORTED_DATATYPES


def test_rdfs_literal_includes_all_literals() -> None:
    assert literal_value_in_datatype(Literal("hi"), RDFS.Literal)
    assert literal_value_in_datatype(Literal(1), RDFS.Literal)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ill_typed = Literal("not-a-number", datatype=XSD.integer)
    assert literal_value_in_datatype(ill_typed, RDFS.Literal)


def test_ill_typed_not_in_typed_value_spaces() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ill_typed = Literal("not-a-number", datatype=XSD.integer)
    assert not literal_value_in_datatype(ill_typed, XSD.integer)
    assert not literal_value_in_datatype(ill_typed, XSD.decimal)


def test_integer_in_decimal_and_facets() -> None:
    one = Literal("1", datatype=XSD.integer)
    assert literal_value_in_datatype(one, XSD.integer)
    assert literal_value_in_datatype(one, XSD.decimal)
    assert literal_value_in_datatype(one, XSD.nonNegativeInteger)
    assert not literal_value_in_datatype(one, XSD.negativeInteger)

    neg = Literal("-1", datatype=XSD.integer)
    assert not literal_value_in_datatype(neg, XSD.nonNegativeInteger)
    assert literal_value_in_datatype(neg, XSD.nonPositiveInteger)
    assert literal_value_in_datatype(neg, XSD.negativeInteger)


def test_decimal_fraction_not_in_integer() -> None:
    half = Literal("1.5", datatype=XSD.decimal)
    assert literal_value_in_datatype(half, XSD.decimal)
    assert not literal_value_in_datatype(half, XSD.integer)


def test_byte_facet_bounds() -> None:
    ok = Literal("127", datatype=XSD.integer)
    too_big = Literal("128", datatype=XSD.integer)
    assert literal_value_in_datatype(ok, XSD.byte)
    assert not literal_value_in_datatype(too_big, XSD.byte)


def test_plain_literal_membership() -> None:
    assert literal_value_in_datatype(Literal("hi", lang="en"), RDF.PlainLiteral)
    assert literal_value_in_datatype(Literal("hi"), RDF.PlainLiteral)
    assert literal_value_in_datatype(
        Literal("hi", datatype=XSD.string), RDF.PlainLiteral
    )
    assert not literal_value_in_datatype(
        Literal("1", datatype=XSD.integer), RDF.PlainLiteral
    )


def test_string_family_facets() -> None:
    assert literal_value_in_datatype(Literal("a b", datatype=XSD.string), XSD.string)
    assert not literal_value_in_datatype(
        Literal("a\tb", datatype=XSD.string), XSD.normalizedString
    )
    assert not literal_value_in_datatype(Literal(" a", datatype=XSD.string), XSD.token)
    assert literal_value_in_datatype(Literal("en", datatype=XSD.string), XSD.language)
    assert not literal_value_in_datatype(
        Literal("en-@", datatype=XSD.string), XSD.language
    )


def test_unknown_datatype_iri_rejected() -> None:
    assert not literal_value_in_datatype(
        Literal("1", datatype=XSD.integer), URIRef("urn:example:NotADatatype")
    )


def test_boolean_and_datetime() -> None:
    assert literal_value_in_datatype(Literal("true", datatype=XSD.boolean), XSD.boolean)
    # RDFLib may not populate .value for xsd:dateTimeStamp; membership still
    # accepts timezone-qualified dateTime lexicals in that value space.
    stamped = Literal("2009-01-01T00:00:00Z", datatype=XSD.dateTimeStamp)
    assert literal_value_in_datatype(stamped, XSD.dateTimeStamp)
    assert literal_value_in_datatype(stamped, XSD.dateTime)
    tz_datetime = Literal("2009-01-01T00:00:00Z", datatype=XSD.dateTime)
    assert literal_value_in_datatype(tz_datetime, XSD.dateTimeStamp)
    unstamped = Literal("2009-01-01T00:00:00", datatype=XSD.dateTime)
    assert literal_value_in_datatype(unstamped, XSD.dateTime)
    assert not literal_value_in_datatype(unstamped, XSD.dateTimeStamp)
