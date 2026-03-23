from typing import Annotated

from pydantic import Field
from rdflib import IdentifiedNode, Node, URIRef

type ContextIdentifier = Annotated[
    IdentifiedNode,
    Field(..., description="The graph (context) wherein some fact(s) apply."),
]

type Triple = Annotated[
    tuple[IdentifiedNode, URIRef, Node],
    Field(
        ..., description="A triple of a subject, predicate, and object; i.e., a fact."
    ),
]

type Quad = Annotated[
    tuple[*Triple, ContextIdentifier],
    Field(
        ...,
        description="A quad of a subject, predicate, object, and context identifier; i.e., a fact in a specific context.",
    ),
]
