"""Shared schema-facing RDF term aliases and graph-scoped tuple types.

Triple and quad aliases annotate ``(subject, predicate, object[, context])``
tuples used in RDF projections from graph-scoped Pydantic models.
"""

from typing import Annotated

from pydantic import Field
from rdflib import IdentifiedNode, Node, URIRef

from .n3_terms import (
    RDF_DATASET,
    RDF_GRAPH_TERM,
    RDF_NAMESPACE,
    TURTLE_BLANK_NODE,
    TURTLE_BLANK_NODE_EXAMPLES,
    TURTLE_IRI,
    TURTLE_IRI_EXAMPLES,
    TURTLE_LITERAL,
    TURTLE_LITERAL_EXAMPLES,
    N3ContextIdentifier,
    N3IRIRef,
    N3Node,
    N3Resource,
)

# Same N3 validation and schema metadata as graph names in dataset models.
type ContextIdentifier = N3ContextIdentifier

type Triple = Annotated[
    tuple[IdentifiedNode, URIRef, Node],
    Field(
        ...,
        description="A triple of a subject, predicate, and object; i.e., a fact.",
    ),
]

type Quad = Annotated[
    tuple[IdentifiedNode, URIRef, Node, ContextIdentifier],
    Field(
        ...,
        description=(
            "A quad of a subject, predicate, object, and context identifier; "
            "i.e., a fact in a specific context."
        ),
    ),
]

__all__ = [
    "ContextIdentifier",
    "N3ContextIdentifier",
    "N3IRIRef",
    "N3Node",
    "N3Resource",
    "Quad",
    "RDF_DATASET",
    "RDF_GRAPH_TERM",
    "RDF_NAMESPACE",
    "Triple",
    "TURTLE_BLANK_NODE",
    "TURTLE_BLANK_NODE_EXAMPLES",
    "TURTLE_IRI",
    "TURTLE_IRI_EXAMPLES",
    "TURTLE_LITERAL",
    "TURTLE_LITERAL_EXAMPLES",
]
