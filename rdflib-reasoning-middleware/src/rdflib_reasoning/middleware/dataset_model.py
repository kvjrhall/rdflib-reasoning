"""
Schema-facing RDF dataset boundary models for Research Agent tools and state.

Design rules for these models are governed by:
- `docs/dev/architecture.md` under "Structural elements and middleware"
- `docs/dev/decision-records/DR-011 Schema-Facing RDF Boundary Models.md`
"""

from typing import Annotated, Final, Self
from typing import Literal as LiteralType

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt
from pydantic.json_schema import SkipJsonSchema
from rdflib import IdentifiedNode, Node, URIRef
from rdflib.graph import Graph, ReadOnlyGraphAggregate
from rdflib_reasoning.axiom.common import (
    N3ContextIdentifier,
    N3IRIRef,
    N3Node,
    N3Resource,
    Triple,
)
from rdflib_reasoning.axiom.n3_terms import _node_to_string, _parse_identified_node


def _parse_graph_context(value: str | Node) -> Graph:
    try:
        # This graph is effectively an identifier and MUST NOT be modified
        graphContext = Graph(identifier=_parse_identified_node(value))
        return ReadOnlyGraphAggregate([graphContext])
    except Exception as e:
        raise ValueError(f"Could not parse graph context from {value!r}.") from e


def _graph_context_to_string(graph: Graph) -> str:
    return _node_to_string(graph.identifier)


# NOTE: This is _NOT_ part of the schema-facing API, but makes our development API consistent.
type N3GraphContext = Annotated[Graph, SkipJsonSchema()]


# RDF_BLANK_NODE: Final[str] = (
#     "RDF Blank Node as defined by RDF 1.1 Concepts and Abstract Syntax § 3.4 Blank Nodes "
#     + "(https://www.w3.org/TR/rdf11-concepts/#section-blank-nodes)"
# )
#
# RDF_IRI: Final[str] = (
#     "RFC 3987 IRI used as in RDF 1.1 Concepts and Abstract Syntax § 3.2 IRIs "
#     "(https://www.w3.org/TR/rdf11-concepts/#section-IRIs)"
# )
#
# RDF_LITERAL: Final[str] = (
#     "RDF Literal as defined by RDF 1.1 Concepts and Abstract Syntax § 3.3 Literals "
#     + "(https://www.w3.org/TR/rdf11-concepts/#section-Graph-Literal)"
# )


# TODO: Somewhere, we need to make sure agents know to reword things that are temporal into atemporal.
#       This will require examples, techniques, and vocabularies.


class _HasSpo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    subject: N3Resource = Field(
        ...,
        description="The subject whose relationship with the object is given by the predicate.",
        examples=["<http://example.com/rob>", "_:b1"],
    )
    predicate: N3IRIRef = Field(
        ...,
        description="The predicate relating the subject to the object.",
        examples=[
            "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>",
            "http://www.w3.org/2000/01/rdf-schema#label",
        ],
    )
    object: N3Node = Field(
        ...,
        description=(
            "The object of relationship indicated by the predicate. "
            "Use RDF literals for plain text values such as labels and comments."
        ),
        examples=[
            "<https://schema.org/CreativeWork>",
            "<http://www.w3.org/ns/prov#Entity>",
            "<urn:example:ProjectReport>",
            '"Project report"',
            '"A short human-readable description."',
        ],
    )


class N3Triple(_HasSpo):
    """
    RDF triple accepted in canonical N3 lexical form and serialized in N3.

    Use this model when a statement is scoped only by its subject, predicate, and object.
    See RDF 1.1 Concepts and Abstract Syntax § 3.1 RDF Triples.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    @property
    def as_rdflib(self) -> Triple:
        return (self.subject, self.predicate, self.object)

    @classmethod
    def from_rdflib(cls, triple: tuple[Node, Node, Node]) -> Self:
        return cls.model_validate(
            {
                "subject": triple[0],
                "predicate": triple[1],
                "object": triple[2],
            }
        )


class N3Quad(_HasSpo):
    """
    RDF quad accepted in canonical N3 lexical form and serialized in N3.

    Use this model when the triple is asserted within a specific named graph given by `graph_id`.
    See RDF 1.1 Concepts and Abstract Syntax § 4 RDF Datasets.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    graph_id: Final[N3ContextIdentifier] = Field(
        ...,
        description="The name of the RDF Graph wherein this statement is asserted.",
        examples=["<urn:example:graph>", "urn:example:context", "_:g1"],
    )

    @property
    def graph(self) -> N3GraphContext:
        return _parse_graph_context(self.graph_id)

    @property
    def as_rdflib(self) -> tuple[IdentifiedNode, URIRef, Node, Graph]:
        return (self.subject, self.predicate, self.object, self.graph)

    @classmethod
    def from_rdflib(
        cls, quad: tuple[Node, Node, Node, IdentifiedNode | Graph | None]
    ) -> Self:
        graph_identifier = quad[3].identifier if isinstance(quad[3], Graph) else quad[3]
        return cls.model_validate(
            {
                "subject": quad[0],
                "predicate": quad[1],
                "object": quad[2],
                "graph_id": graph_identifier,
            }
        )


# =============================================================================
# Dataset Interaction Models
# =============================================================================


class MutationResponse(BaseModel):
    """Response payload for state-mutating dataset tools."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    requested: NonNegativeInt | None = Field(
        default=None,
        description=(
            "Number of RDF statements or graphs the caller asked this operation to "
            "consider when that count is well-defined."
        ),
        examples=[None, 1, 2, 3],
    )
    updated: NonNegativeInt = Field(
        description="Number of RDF statements or graphs affected by the operation.",
        examples=[0, 1, 3],
    )
    unchanged: NonNegativeInt = Field(
        default=0,
        description=(
            "Number of requested RDF statements or graphs already in the desired "
            "state after this call."
        ),
        examples=[0, 1, 2],
    )
    no_action_needed: bool = Field(
        default=False,
        description=(
            "Whether the requested end state was already satisfied, so retrying the "
            "same mutation unchanged is unnecessary."
        ),
        examples=[False, True],
    )
    message: str = Field(
        description="Short human-readable summary of the mutation.",
        examples=[
            "Triples added to the default graph.",
            "No action was needed. All requested triples were already present.",
            "Triples removed from the default graph.",
            "Dataset reset.",
        ],
    )


class NewResourceNodeResponse(BaseModel):
    """Response payload when a blank node or IRI is defined.

    This resource is not in the knowlede base until it is asserted in a statement.
    """

    model_config = ConfigDict(frozen=True)

    resource: str = Field(
        description="The newly defined resource serialized in canonical N3 lexical form.",
        examples=["_:b0", "_:personEntity", "_:restriction1"],
    )


class SerializationResponse(BaseModel):
    """Response payload for dataset or graph serialization."""

    model_config = ConfigDict(frozen=True)

    format: LiteralType["trig", "turtle", "nt", "n3"] = Field(
        description="Serialization format used for the returned content.",
        examples=["turtle", "trig", "nt"],
    )
    content: str = Field(
        description="Serialized RDF content.",
        examples=[
            '<urn:example:s> <urn:example:p> "value" .',
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        ],
    )
    default_graph_triple_count: NonNegativeInt = Field(
        description="Number of triples currently present in the default graph.",
        examples=[0, 1, 3],
    )
    is_empty: bool = Field(
        description="Whether the default graph is currently empty.",
        examples=[False, True],
    )
    message: str | None = Field(
        default=None,
        description=(
            "Optional operational guidance about the serialization result. This "
            "guidance is separate from `content`, which remains pure RDF text."
        ),
        examples=[
            "Serialized the current default graph containing 3 triples.",
            "The default graph is empty. Changing serialization formats will not add data to an unchanged dataset.",
        ],
    )


class SerializeRequest(BaseModel):
    """Request payload for serializing dataset state."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    format: LiteralType["trig", "turtle", "nt", "n3"] = Field(
        default="trig",
        description="Serialization format for the current default-graph knowledge base.",
        examples=["trig", "turtle", "nt"],
    )


class TripleBatchRequest(BaseModel):
    """Request payload for exact-match triple updates."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    triples: tuple[N3Triple, ...] = Field(
        min_length=1,
        description="One or more exact RDF triples to add or remove.",
        examples=[
            [
                {
                    "subject": "<urn:example:ProjectReport>",
                    "predicate": "<http://www.w3.org/2000/01/rdf-schema#label>",
                    "object": '"Project report"',
                }
            ],
            [
                {
                    "subject": "urn:example:ProjectReport",
                    "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                    "object": "http://www.w3.org/2000/01/rdf-schema#Class",
                },
                {
                    "subject": "urn:example:ProjectReport",
                    "predicate": "http://www.w3.org/2000/01/rdf-schema#subClassOf",
                    "object": "https://schema.org/CreativeWork",
                },
            ],
        ],
    )


class TripleListResponse(BaseModel):
    """Response payload listing triples from the default graph."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    triples: tuple[N3Triple, ...] = Field(
        description="Triples currently present in the default graph.",
        examples=[
            [
                {
                    "subject": "<urn:example:ProjectReport>",
                    "predicate": "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>",
                    "object": "<http://www.w3.org/2000/01/rdf-schema#Class>",
                }
            ],
            [
                {
                    "subject": "<urn:example:ProjectReport>",
                    "predicate": "<http://www.w3.org/2000/01/rdf-schema#label>",
                    "object": '"Project report"',
                },
                {
                    "subject": "<urn:example:ProjectReport>",
                    "predicate": "<http://www.w3.org/2000/01/rdf-schema#comment>",
                    "object": '"A written report that summarizes project work."',
                },
            ],
        ],
    )
