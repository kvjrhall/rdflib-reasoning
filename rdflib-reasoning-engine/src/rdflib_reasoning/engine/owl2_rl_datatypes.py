"""OWL 2 RL datatype inventory and literal value-space membership tests.

These helpers support read-only predicate builtins used by OWL 2 RL ``dt-*``
rules. They are not a complete XSD processor; they cover the OWL 2 RL
supported datatype set with facet and hierarchy checks needed for rule guards.
"""

from __future__ import annotations

import base64
import datetime
import math
import re
from decimal import Decimal
from typing import Final

from rdflib.namespace import RDF, RDFS, XSD
from rdflib.term import Literal, URIRef

# OWL 2 Profiles §4.1 (OWL 2 RL supported datatypes). Development Agents: see
# docs/specs/owl2-reasoning-profiles/INDEX.md.
OWL2_RL_SUPPORTED_DATATYPES: Final[frozenset[URIRef]] = frozenset(
    {
        RDF.PlainLiteral,
        RDF.XMLLiteral,
        RDFS.Literal,
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
)

_INTEGER_TYPES: Final[frozenset[URIRef]] = frozenset(
    {
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
    }
)

_STRING_FAMILY: Final[frozenset[URIRef]] = frozenset(
    {
        XSD.string,
        XSD.normalizedString,
        XSD.token,
        XSD.language,
        XSD.Name,
        XSD.NCName,
        XSD.NMTOKEN,
    }
)

# XML Schema Name / NCName / language / NMTOKEN patterns (practical subsets).
_LANGUAGE_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*$"
)
_NMTOKEN_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9._:\-]+$")
_NAME_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z_:][\w.\-:]*$", re.UNICODE)
_NCNAME_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z_][\w.\-]*$", re.UNICODE)


def _parse_datetime_value(literal: Literal) -> datetime.datetime | None:
    """Return a parsed datetime for ``literal``, including dateTimeStamp lexicals.

    RDFLib converts ``xsd:dateTime`` lexicals but often leaves
    ``xsd:dateTimeStamp`` values as ``None``. Fall back to re-parsing the
    lexical form as ``xsd:dateTime`` when needed.
    """
    if isinstance(literal.value, datetime.datetime):
        return literal.value
    if literal.datatype not in {XSD.dateTime, XSD.dateTimeStamp}:
        return None
    candidate = Literal(str(literal), datatype=XSD.dateTime)
    if isinstance(candidate.value, datetime.datetime):
        return candidate.value
    return None


def _is_ill_typed_literal(literal: Literal) -> bool:
    """Return whether ``literal`` failed RDFLib lexical-to-value conversion."""
    if literal.datatype is None:
        return False
    if literal.value is not None:
        return False
    # dateTimeStamp is often unconverted by RDFLib even when lexical is valid.
    if literal.datatype in {XSD.dateTime, XSD.dateTimeStamp}:
        return _parse_datetime_value(literal) is None
    return True


def _as_decimal(value: object) -> Decimal | None:
    """Convert a Python numeric value to :class:`~decimal.Decimal` when possible."""
    match value:
        case Decimal():
            return value
        case bool():
            # bool is a subclass of int; treat separately if ever reached.
            return None
        case int():
            return Decimal(value)
        case float():
            if math.isnan(value) or math.isinf(value):
                return None
            return Decimal(str(value))
        case _:
            return None


def _is_whole_number(value: Decimal) -> bool:
    """Return whether ``value`` is an integer in the mathematical sense."""
    return value == value.to_integral_value()


def _integer_in_facets(value: int, datatype: URIRef) -> bool:
    """Return whether ``value`` satisfies the XSD facet bounds for ``datatype``."""
    match datatype:
        case _ if datatype == XSD.integer:
            return True
        case _ if datatype == XSD.nonNegativeInteger:
            return value >= 0
        case _ if datatype == XSD.nonPositiveInteger:
            return value <= 0
        case _ if datatype == XSD.positiveInteger:
            return value > 0
        case _ if datatype == XSD.negativeInteger:
            return value < 0
        case _ if datatype == XSD.long:
            return -(2**63) <= value <= (2**63) - 1
        case _ if datatype == XSD.int:
            return -(2**31) <= value <= (2**31) - 1
        case _ if datatype == XSD.short:
            return -(2**15) <= value <= (2**15) - 1
        case _ if datatype == XSD.byte:
            return -(2**7) <= value <= (2**7) - 1
        case _ if datatype == XSD.unsignedLong:
            return 0 <= value <= (2**64) - 1
        case _ if datatype == XSD.unsignedInt:
            return 0 <= value <= (2**32) - 1
        case _ if datatype == XSD.unsignedShort:
            return 0 <= value <= (2**16) - 1
        case _ if datatype == XSD.unsignedByte:
            return 0 <= value <= (2**8) - 1
        case _:
            return False


def _numeric_in_datatype(value: object, datatype: URIRef) -> bool:
    """Return whether a Python numeric value lies in ``datatype``'s value space."""
    if datatype == XSD.float:
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float, Decimal)):
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return True
            try:
                float(value)
            except OverflowError, ValueError:
                return False
            return True
        return False

    if datatype == XSD.double:
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float, Decimal)):
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return True
            try:
                float(value)
            except OverflowError, ValueError:
                return False
            return True
        return False

    decimal_value = _as_decimal(value)
    if decimal_value is None:
        return False

    if datatype == XSD.decimal:
        return True

    if datatype in _INTEGER_TYPES:
        if not _is_whole_number(decimal_value):
            return False
        try:
            as_int = int(decimal_value)
        except OverflowError, ValueError:
            return False
        return _integer_in_facets(as_int, datatype)

    return False


def _string_in_datatype(text: str, datatype: URIRef) -> bool:
    """Return whether ``text`` lies in a string-family datatype value space."""
    match datatype:
        case _ if datatype == XSD.string:
            return True
        case _ if datatype == XSD.normalizedString:
            return "\t" not in text and "\n" not in text and "\r" not in text
        case _ if datatype == XSD.token:
            if not _string_in_datatype(text, XSD.normalizedString):
                return False
            if text.startswith(" ") or text.endswith(" "):
                return False
            return "  " not in text
        case _ if datatype == XSD.language:
            return bool(_LANGUAGE_RE.fullmatch(text))
        case _ if datatype == XSD.NMTOKEN:
            return bool(_NMTOKEN_RE.fullmatch(text))
        case _ if datatype == XSD.Name:
            return bool(_NAME_RE.fullmatch(text))
        case _ if datatype == XSD.NCName:
            return bool(_NCNAME_RE.fullmatch(text))
        case _:
            return False


def _binary_in_datatype(literal: Literal, datatype: URIRef) -> bool:
    """Return whether ``literal`` is in a binary datatype value space."""
    lexical = str(literal)
    if datatype == XSD.hexBinary:
        if len(lexical) % 2 != 0:
            return False
        try:
            bytes.fromhex(lexical)
        except ValueError:
            return False
        return True
    if datatype == XSD.base64Binary:
        try:
            base64.b64decode(lexical, validate=True)
        except ValueError, TypeError:
            return False
        return True
    return False


def _datetime_in_datatype(literal: Literal, datatype: URIRef) -> bool:
    """Return whether ``literal`` lies in a dateTime/dateTimeStamp value space."""
    value = _parse_datetime_value(literal)
    if value is None:
        return False
    if datatype == XSD.dateTime:
        return True
    if datatype == XSD.dateTimeStamp:
        return value.tzinfo is not None and value.utcoffset() is not None
    return False


def literal_value_in_datatype(literal: Literal, datatype: URIRef) -> bool:
    """Return whether ``literal``'s data value is in ``datatype``'s value space.

    Only OWL 2 RL supported datatype IRIs are recognized. Ill-typed literals
    (typed literals whose lexical form does not map to a value) are members of
    ``rdfs:Literal`` only.

    Args:
        literal: An RDFLib literal term.
        datatype: A datatype IRI.

    Returns:
        True when the literal's data value is contained in the datatype's value
        space under the OWL 2 RL supported datatype set; False otherwise.
    """
    if datatype not in OWL2_RL_SUPPORTED_DATATYPES:
        return False

    if datatype == RDFS.Literal:
        return True

    if _is_ill_typed_literal(literal):
        return False

    if datatype == RDF.PlainLiteral:
        if literal.language is not None:
            return True
        if literal.datatype is None:
            return True
        if literal.datatype == XSD.string:
            return isinstance(literal.value, str)
        return False

    if datatype == RDF.XMLLiteral:
        return literal.datatype == RDF.XMLLiteral and literal.value is not None

    if datatype == XSD.boolean:
        return isinstance(literal.value, bool)

    if datatype in {XSD.float, XSD.double, XSD.decimal} | _INTEGER_TYPES:
        return _numeric_in_datatype(literal.value, datatype)

    if datatype in _STRING_FAMILY:
        if literal.language is not None:
            # Language-tagged literals are rdf:langString-shaped, not xsd:string.
            return False
        text: str
        if isinstance(literal.value, str):
            text = literal.value
        elif literal.datatype is None:
            text = str(literal)
        else:
            return False
        return _string_in_datatype(text, datatype)

    if datatype in {XSD.hexBinary, XSD.base64Binary}:
        if literal.value is None and literal.datatype not in {
            XSD.hexBinary,
            XSD.base64Binary,
        }:
            return False
        # Prefer lexical validation; RDFLib may leave .value as bytes or str.
        return _binary_in_datatype(literal, datatype)

    if datatype == XSD.anyURI:
        if isinstance(literal.value, str):
            return True
        if literal.datatype in {None, XSD.string, XSD.anyURI} and isinstance(
            str(literal), str
        ):
            return len(str(literal)) > 0 or literal.datatype == XSD.anyURI
        return False

    if datatype in {XSD.dateTime, XSD.dateTimeStamp}:
        return _datetime_in_datatype(literal, datatype)

    return False
