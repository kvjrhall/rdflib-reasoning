"""Tests for OWL 2 RL datatype value-space membership helpers."""

from __future__ import annotations

import base64
import math
import warnings
from decimal import Decimal

import pytest
from rdflib import RDF, RDFS, XSD, Literal, URIRef
from rdflib_reasoning.engine.owl2_rl_datatypes import (
    OWL2_RL_SUPPORTED_DATATYPES,
    literal_value_in_datatype,
)


def test_supported_datatypes_include_core_iris() -> None:
    assert RDFS.Literal in OWL2_RL_SUPPORTED_DATATYPES
    assert RDF.PlainLiteral in OWL2_RL_SUPPORTED_DATATYPES
    assert RDF.XMLLiteral in OWL2_RL_SUPPORTED_DATATYPES
    assert XSD.integer in OWL2_RL_SUPPORTED_DATATYPES
    assert XSD.float in OWL2_RL_SUPPORTED_DATATYPES
    assert XSD.double in OWL2_RL_SUPPORTED_DATATYPES
    assert XSD.hexBinary in OWL2_RL_SUPPORTED_DATATYPES
    assert XSD.anyURI in OWL2_RL_SUPPORTED_DATATYPES
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
    assert not literal_value_in_datatype(ill_typed, XSD.float)


def test_integer_in_decimal_and_facets() -> None:
    one = Literal("1", datatype=XSD.integer)
    assert literal_value_in_datatype(one, XSD.integer)
    assert literal_value_in_datatype(one, XSD.decimal)
    assert literal_value_in_datatype(one, XSD.nonNegativeInteger)
    assert literal_value_in_datatype(one, XSD.positiveInteger)
    assert not literal_value_in_datatype(one, XSD.negativeInteger)

    neg = Literal("-1", datatype=XSD.integer)
    assert not literal_value_in_datatype(neg, XSD.nonNegativeInteger)
    assert not literal_value_in_datatype(neg, XSD.positiveInteger)
    assert literal_value_in_datatype(neg, XSD.nonPositiveInteger)
    assert literal_value_in_datatype(neg, XSD.negativeInteger)

    zero = Literal("0", datatype=XSD.integer)
    assert literal_value_in_datatype(zero, XSD.nonNegativeInteger)
    assert literal_value_in_datatype(zero, XSD.nonPositiveInteger)
    assert not literal_value_in_datatype(zero, XSD.positiveInteger)
    assert not literal_value_in_datatype(zero, XSD.negativeInteger)


def test_decimal_fraction_not_in_integer() -> None:
    half = Literal("1.5", datatype=XSD.decimal)
    assert literal_value_in_datatype(half, XSD.decimal)
    assert not literal_value_in_datatype(half, XSD.integer)
    assert not literal_value_in_datatype(half, XSD.long)


@pytest.mark.parametrize(
    ("value", "datatype", "expected"),
    [
        ("127", XSD.byte, True),
        ("128", XSD.byte, False),
        ("-128", XSD.byte, True),
        ("-129", XSD.byte, False),
        ("32767", XSD.short, True),
        ("32768", XSD.short, False),
        ("2147483647", XSD.int, True),
        ("2147483648", XSD.int, False),
        ("9223372036854775807", XSD.long, True),
        ("9223372036854775808", XSD.long, False),
        ("0", XSD.unsignedByte, True),
        ("255", XSD.unsignedByte, True),
        ("256", XSD.unsignedByte, False),
        ("-1", XSD.unsignedByte, False),
        ("65535", XSD.unsignedShort, True),
        ("65536", XSD.unsignedShort, False),
        ("4294967295", XSD.unsignedInt, True),
        ("4294967296", XSD.unsignedInt, False),
        ("18446744073709551615", XSD.unsignedLong, True),
        ("18446744073709551616", XSD.unsignedLong, False),
    ],
)
def test_bounded_integer_facets(value: str, datatype: URIRef, expected: bool) -> None:
    literal = Literal(value, datatype=XSD.integer)
    assert literal_value_in_datatype(literal, datatype) is expected


def test_plain_literal_membership() -> None:
    assert literal_value_in_datatype(Literal("hi", lang="en"), RDF.PlainLiteral)
    assert literal_value_in_datatype(Literal("hi"), RDF.PlainLiteral)
    assert literal_value_in_datatype(
        Literal("hi", datatype=XSD.string), RDF.PlainLiteral
    )
    assert not literal_value_in_datatype(
        Literal("1", datatype=XSD.integer), RDF.PlainLiteral
    )


def test_xml_literal_membership() -> None:
    well_formed = Literal("<a/>", datatype=RDF.XMLLiteral)
    assert literal_value_in_datatype(well_formed, RDF.XMLLiteral)
    assert literal_value_in_datatype(well_formed, RDFS.Literal)
    assert not literal_value_in_datatype(
        Literal("hi", datatype=XSD.string), RDF.XMLLiteral
    )


def test_string_family_facets() -> None:
    assert literal_value_in_datatype(Literal("a b", datatype=XSD.string), XSD.string)
    assert not literal_value_in_datatype(
        Literal("a\tb", datatype=XSD.string), XSD.normalizedString
    )
    assert not literal_value_in_datatype(
        Literal("a\nb", datatype=XSD.string), XSD.normalizedString
    )
    assert not literal_value_in_datatype(Literal(" a", datatype=XSD.string), XSD.token)
    assert not literal_value_in_datatype(Literal("a ", datatype=XSD.string), XSD.token)
    assert not literal_value_in_datatype(
        Literal("a  b", datatype=XSD.string), XSD.token
    )
    assert literal_value_in_datatype(Literal("a b", datatype=XSD.string), XSD.token)
    assert literal_value_in_datatype(Literal("en", datatype=XSD.string), XSD.language)
    assert not literal_value_in_datatype(
        Literal("en-@", datatype=XSD.string), XSD.language
    )
    assert literal_value_in_datatype(Literal("abc", datatype=XSD.string), XSD.NMTOKEN)
    assert not literal_value_in_datatype(
        Literal("a b", datatype=XSD.string), XSD.NMTOKEN
    )
    assert literal_value_in_datatype(Literal("foo:bar", datatype=XSD.string), XSD.Name)
    assert not literal_value_in_datatype(Literal("1foo", datatype=XSD.string), XSD.Name)
    assert literal_value_in_datatype(
        Literal("foo_bar", datatype=XSD.string), XSD.NCName
    )
    assert not literal_value_in_datatype(
        Literal("foo:bar", datatype=XSD.string), XSD.NCName
    )
    # Language-tagged literals are not xsd:string-family members.
    assert not literal_value_in_datatype(Literal("en", lang="en"), XSD.string)


def test_unknown_datatype_iri_rejected() -> None:
    assert not literal_value_in_datatype(
        Literal("1", datatype=XSD.integer), URIRef("urn:example:NotADatatype")
    )


def test_boolean_membership() -> None:
    assert literal_value_in_datatype(Literal("true", datatype=XSD.boolean), XSD.boolean)
    assert literal_value_in_datatype(
        Literal("false", datatype=XSD.boolean), XSD.boolean
    )
    assert not literal_value_in_datatype(
        Literal("1", datatype=XSD.integer), XSD.boolean
    )


def test_float_and_double_membership() -> None:
    one = Literal("1", datatype=XSD.integer)
    assert literal_value_in_datatype(one, XSD.float)
    assert literal_value_in_datatype(one, XSD.double)

    fl = Literal("1.5", datatype=XSD.float)
    assert literal_value_in_datatype(fl, XSD.float)
    assert literal_value_in_datatype(fl, XSD.double)
    assert not literal_value_in_datatype(fl, XSD.integer)

    nan = Literal(float("nan"), datatype=XSD.float)
    assert isinstance(nan.value, float) and math.isnan(nan.value)
    assert literal_value_in_datatype(nan, XSD.float)
    assert literal_value_in_datatype(nan, XSD.double)

    inf = Literal(float("inf"), datatype=XSD.double)
    assert literal_value_in_datatype(inf, XSD.double)
    assert literal_value_in_datatype(inf, XSD.float)

    # Booleans must not be treated as numeric float/double values.
    assert not literal_value_in_datatype(
        Literal("true", datatype=XSD.boolean), XSD.float
    )
    assert not literal_value_in_datatype(
        Literal("true", datatype=XSD.boolean), XSD.double
    )
    assert not literal_value_in_datatype(Literal("hi", datatype=XSD.string), XSD.float)


def test_decimal_from_python_decimal_value() -> None:
    lit = Literal(Decimal("2.5"), datatype=XSD.decimal)
    assert literal_value_in_datatype(lit, XSD.decimal)
    assert not literal_value_in_datatype(lit, XSD.integer)


def test_boolean_and_datetime() -> None:
    stamped = Literal("2009-01-01T00:00:00Z", datatype=XSD.dateTimeStamp)
    assert literal_value_in_datatype(stamped, XSD.dateTimeStamp)
    assert literal_value_in_datatype(stamped, XSD.dateTime)
    tz_datetime = Literal("2009-01-01T00:00:00Z", datatype=XSD.dateTime)
    assert literal_value_in_datatype(tz_datetime, XSD.dateTimeStamp)
    unstamped = Literal("2009-01-01T00:00:00", datatype=XSD.dateTime)
    assert literal_value_in_datatype(unstamped, XSD.dateTime)
    assert not literal_value_in_datatype(unstamped, XSD.dateTimeStamp)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bad_stamp = Literal("not-a-datetime", datatype=XSD.dateTimeStamp)
    assert not literal_value_in_datatype(bad_stamp, XSD.dateTimeStamp)
    assert not literal_value_in_datatype(bad_stamp, XSD.dateTime)


def test_hex_binary_membership() -> None:
    ok = Literal("0a1B", datatype=XSD.hexBinary)
    assert literal_value_in_datatype(ok, XSD.hexBinary)
    assert not literal_value_in_datatype(
        Literal("0a1", datatype=XSD.hexBinary), XSD.hexBinary
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bad = Literal("zz", datatype=XSD.hexBinary)
    # Ill-typed hexBinary is not in the hexBinary value space.
    assert not literal_value_in_datatype(bad, XSD.hexBinary)
    assert not literal_value_in_datatype(
        Literal("1", datatype=XSD.integer), XSD.hexBinary
    )


def test_base64_binary_membership() -> None:
    encoded = base64.b64encode(b"hello").decode("ascii")
    ok = Literal(encoded, datatype=XSD.base64Binary)
    assert literal_value_in_datatype(ok, XSD.base64Binary)
    # RDFLib leaves some invalid lexicals as ill-typed (value is None).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ill_typed = Literal("abc", datatype=XSD.base64Binary)
    assert ill_typed.value is None
    assert not literal_value_in_datatype(ill_typed, XSD.base64Binary)
    assert not literal_value_in_datatype(
        Literal("1", datatype=XSD.integer), XSD.base64Binary
    )


def test_any_uri_membership() -> None:
    uri = Literal("http://example.org/a", datatype=XSD.anyURI)
    assert literal_value_in_datatype(uri, XSD.anyURI)
    assert literal_value_in_datatype(
        Literal("http://example.org/a", datatype=XSD.string), XSD.anyURI
    )
    assert not literal_value_in_datatype(Literal("1", datatype=XSD.integer), XSD.anyURI)


@pytest.mark.parametrize(
    ("literal", "datatype"),
    [
        (Literal("x"), RDFS.Literal),
        (Literal("x", lang="en"), RDF.PlainLiteral),
        (Literal("<a/>", datatype=RDF.XMLLiteral), RDF.XMLLiteral),
        (Literal("1", datatype=XSD.integer), XSD.integer),
        (Literal("1", datatype=XSD.integer), XSD.decimal),
        (Literal("1", datatype=XSD.integer), XSD.float),
        (Literal("1", datatype=XSD.integer), XSD.double),
        (Literal("true", datatype=XSD.boolean), XSD.boolean),
        (Literal("hi", datatype=XSD.string), XSD.string),
        (Literal("hi", datatype=XSD.string), XSD.normalizedString),
        (Literal("hi", datatype=XSD.string), XSD.token),
        (Literal("en", datatype=XSD.string), XSD.language),
        (Literal("abc", datatype=XSD.string), XSD.NMTOKEN),
        (Literal("abc", datatype=XSD.string), XSD.Name),
        (Literal("abc", datatype=XSD.string), XSD.NCName),
        (Literal("0a", datatype=XSD.hexBinary), XSD.hexBinary),
        (
            Literal(base64.b64encode(b"x").decode("ascii"), datatype=XSD.base64Binary),
            XSD.base64Binary,
        ),
        (Literal("http://example.org/", datatype=XSD.anyURI), XSD.anyURI),
        (Literal("2009-01-01T00:00:00", datatype=XSD.dateTime), XSD.dateTime),
        (
            Literal("2009-01-01T00:00:00Z", datatype=XSD.dateTimeStamp),
            XSD.dateTimeStamp,
        ),
        (Literal("1", datatype=XSD.integer), XSD.long),
        (Literal("1", datatype=XSD.integer), XSD.int),
        (Literal("1", datatype=XSD.integer), XSD.short),
        (Literal("1", datatype=XSD.integer), XSD.byte),
        (Literal("1", datatype=XSD.integer), XSD.unsignedLong),
        (Literal("1", datatype=XSD.integer), XSD.unsignedInt),
        (Literal("1", datatype=XSD.integer), XSD.unsignedShort),
        (Literal("1", datatype=XSD.integer), XSD.unsignedByte),
        (Literal("1", datatype=XSD.integer), XSD.nonNegativeInteger),
        (Literal("1", datatype=XSD.integer), XSD.positiveInteger),
        (Literal("-1", datatype=XSD.integer), XSD.nonPositiveInteger),
        (Literal("-1", datatype=XSD.integer), XSD.negativeInteger),
    ],
)
def test_every_supported_datatype_has_positive_witness(
    literal: Literal, datatype: URIRef
) -> None:
    assert datatype in OWL2_RL_SUPPORTED_DATATYPES
    assert literal_value_in_datatype(literal, datatype)


def test_supported_datatype_inventory_has_positive_coverage() -> None:
    """Fail loudly if a supported datatype gains no positive membership witness."""
    covered = {
        RDFS.Literal,
        RDF.PlainLiteral,
        RDF.XMLLiteral,
        XSD.decimal,
        XSD.integer,
        XSD.nonNegativeInteger,
        XSD.nonPositiveInteger,
        XSD.positiveInteger,
        XSD.negativeInteger,
        XSD.long,
        XSD.int,
        XSD.short,
        XSD.byte,
        XSD.unsignedLong,
        XSD.unsignedInt,
        XSD.unsignedShort,
        XSD.unsignedByte,
        XSD.float,
        XSD.double,
        XSD.string,
        XSD.normalizedString,
        XSD.token,
        XSD.language,
        XSD.Name,
        XSD.NCName,
        XSD.NMTOKEN,
        XSD.boolean,
        XSD.hexBinary,
        XSD.base64Binary,
        XSD.anyURI,
        XSD.dateTime,
        XSD.dateTimeStamp,
    }
    assert covered == OWL2_RL_SUPPORTED_DATATYPES
