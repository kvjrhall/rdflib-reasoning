"""Shared vocabulary term type labels for middleware indexing and search."""

from enum import StrEnum


class VocabularyTermType(StrEnum):
    """Normalized RDF vocabulary term categories used by search and listing tools."""

    CLASS = "class"
    DATATYPE = "datatype"
    INDIVIDUAL = "individual"
    PROPERTY = "property"
