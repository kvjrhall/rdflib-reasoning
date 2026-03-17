"""
Schema-facing RDF dataset boundary models for Research Agent tools and state.

Design rules for these models are governed by:
- `docs/dev/architecture.md` under "Structural elements and middleware"
- `docs/dev/decision-records/DR-011 Schema-Facing RDF Boundary Models.md`
"""

import textwrap
from typing import Annotated, Final, Self, cast
from typing import Literal as LiteralType

import regex as re
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    NonNegativeInt,
    PlainSerializer,
)
from pydantic.json_schema import SkipJsonSchema
from rdflib import IdentifiedNode, Node, URIRef
from rdflib.graph import Graph, ReadOnlyGraphAggregate
from rdflib.term import BNode
from rdflib.util import from_n3
from rdflibr.axiom.common import Triple
from rfc3987_syntax import is_valid_syntax_iri  # type: ignore

# =============================================================================
# Private Validation Functions
# =============================================================================

_TURTLE_ECMA_BLANK_NODE_PATTERN: Final[str] = (
    r"^_:[a-zA-Z0-9_](?:[a-zA-Z0-9_.]*[a-zA-Z0-9_])?$"
)
_turtle_blank_node_regex: Final[re.Pattern[str]] = re.compile(
    _TURTLE_ECMA_BLANK_NODE_PATTERN
)


def _parse_node(value: str | Node) -> Node:
    try:
        node = value if isinstance(value, Node) else from_n3(value)
        if not isinstance(node, Node):
            raise ValueError(f"Unable to parse RDF term from text: ${value}")
        node_text = _node_to_string(node).removeprefix("<").removesuffix(">")

        if isinstance(node, URIRef):
            if not is_valid_syntax_iri(node_text):
                raise ValueError("IRI is not a valid RFC 3987 IRI (required for RDF)")
        elif isinstance(node, BNode) and not _turtle_blank_node_regex.match(node_text):
            raise ValueError(f"Invalid blank node: {node_text}")
        return node
    except Exception as e:
        raise ValueError(f"Could not parse RDF term from {value}.") from e


def _parse_identified_node(value: str | Node) -> IdentifiedNode:
    try:
        node = _parse_node(value)
        if not isinstance(node, IdentifiedNode):
            raise TypeError(f"Expected an IRI or blank node, got {type(node).__name__}")
        return node
    except Exception as e:
        raise ValueError(f"Failed to parse identified node from {value}") from e


def _parse_iri(value: str | Node) -> URIRef:
    try:
        node = _parse_node(value)
        if not isinstance(node, URIRef):
            raise TypeError(f"Expected an IRI, got {type(node).__name__}")
        return node
    except Exception as e:
        raise ValueError(f"Failed to parse IRI from {value}") from e


def _parse_graph_context(value: str | Node) -> Graph:
    try:
        # This graph is effectively an identifier and MUST NOT be modified
        graphContext = Graph(identifier=_parse_identified_node(value))
        return ReadOnlyGraphAggregate([graphContext])
    except Exception as e:
        raise ValueError(f"Could not parse graph context from {value!r}.") from e


def _node_to_string(node: Node) -> str:
    n3 = cast(str, node.n3())
    # return n3.removeprefix("<").removesuffix(">") if isinstance(node, URIRef) else n3
    return n3


def _graph_context_to_string(graph: Graph) -> str:
    return _node_to_string(graph.identifier)


# =============================================================================
# Dataset Content Models
# =============================================================================

RDF_GRAPH_TERM: Final[str] = (
    "Graph Name as defined by RDF 1.1 Concepts and Abstract Syntax § 4. RDF Datasets "
    + "(https://www.w3.org/TR/rdf11-concepts/#section-dataset)"
)

RDF_DATASET: Final[str] = (
    "Dataset as defined by RDF 1.1 Concepts and Abstract Syntax § 4. RDF Datasets "
    + "(https://www.w3.org/TR/rdf11-concepts/#section-dataset) and taking the semantics of "
    + "RDF 1.1: On Semantics of RDF Datasets § 3.4 Each named graph defines its own context "
    + "(https://www.w3.org/TR/rdf11-datasets/#each-named-graph-defines-its-own-context)"
)

RDF_NAMESPACE: Final[str] = (
    "RDF Vocabulary (Namespace) as defined in "
    + "RDF 1.1 Concepts and Abstract Syntax § 3.3 Literals "
    + "(https://www.w3.org/TR/rdf11-concepts/#vocabularies)"
)


TURTLE_BLANK_NODE: Final[str] = (
    "RDF Blank Node as defined in RDF 1.1 Turtle § 2.6 RDF Blank Nodes "
    + "(https://www.w3.org/TR/turtle/#BNodes)"
)
TURTLE_BLANK_NODE_EXAMPLES: Final[list[str]] = [
    "_:b",
    "_:g70",
    "_:personEntity",
]


TURTLE_IRI: Final[str] = (
    "RFC 3987 IRI as used in RDF 1.1 Turtle § 2.4 IRIs "
    + "(https://www.w3.org/TR/turtle/#sec-iri)"
)
TURTLE_IRI_EXAMPLES: Final[list[str]] = [
    "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>",
    "<urn:example:s>",
    "<mailto:user@example.com>",
]


TURTLE_LITERAL: Final[str] = (
    "RDF Literal as defined in RDF 1.1 Turtle § 2.5 RDF Literals "
    + "(https://www.w3.org/TR/turtle/#literals)"
)
TURTLE_LITERAL_EXAMPLES: Final[list[str]] = [
    '"Hello, World!"@en',
    '"Hello, World!"^^<http://www.w3.org/2001/XMLSchema#string>',
    '"123"^^<http://www.w3.org/2001/XMLSchema#integer>',
    '"2026-03-15"^^<http://www.w3.org/2001/XMLSchema#date>',
    '"2026-03-15T12:00:00Z"^^<http://www.w3.org/2001/XMLSchema#dateTime>',
]


type N3Resource = Annotated[
    IdentifiedNode,
    BeforeValidator(_parse_identified_node, json_schema_input_type=str),
    PlainSerializer(_node_to_string, return_type=str),
    Field(
        description=textwrap.dedent(f"""
        RDF resource in N3 lexical form.
        It MUST be a {TURTLE_IRI} or a {TURTLE_BLANK_NODE}.
        It SHOULD be an IRI when a globally stable identifier is available.
        """),
        examples=TURTLE_IRI_EXAMPLES + TURTLE_BLANK_NODE_EXAMPLES,
        json_schema_extra={
            "oneOf": [
                {"format": "iri"},
                {"pattern": _TURTLE_ECMA_BLANK_NODE_PATTERN},
            ]
        },
    ),
]

type N3IRIRef = Annotated[
    URIRef,
    BeforeValidator(_parse_iri, json_schema_input_type=str),
    PlainSerializer(_node_to_string, return_type=str),
    # WithJsonSchema({"type": "string"}, mode="serialization"),
    Field(
        description=textwrap.dedent(f"""
        RDF IRI reference in N3 lexical form.
        It MUST be a {TURTLE_IRI}.
        Use this for predicates and for resources that cannot be blank nodes.
        """),
        examples=TURTLE_IRI_EXAMPLES,
        # https://json-schema.org/draft/2020-12/json-schema-core#name-example-meta-schema-with-vo
        # https://json-schema.org/draft/2020-12/json-schema-validation#name-resource-identifiers
        json_schema_extra={"format": "iri"},
    ),
]

type N3Node = Annotated[
    Node,
    BeforeValidator(_parse_node, json_schema_input_type=str),
    PlainSerializer(_node_to_string, return_type=str),
    # WithJsonSchema({"type": "string"}, mode="serialization"),
    Field(
        description=textwrap.dedent(f"""
        RDF node in N3 lexical form.
        It MUST be one of the following:
        - {TURTLE_IRI}
        - {TURTLE_BLANK_NODE}
        - {TURTLE_LITERAL}
        """),
        examples=TURTLE_IRI_EXAMPLES
        + TURTLE_BLANK_NODE_EXAMPLES
        + TURTLE_LITERAL_EXAMPLES,
    ),
]

type N3ContextIdentifier = Annotated[
    IdentifiedNode,
    BeforeValidator(_parse_identified_node, json_schema_input_type=str),
    PlainSerializer(_node_to_string, return_type=str),
    Field(
        description=textwrap.dedent(f"""
        RDF graph name in N3 lexical form.
        It corresponds to a {RDF_GRAPH_TERM}.
        It MUST be a {TURTLE_IRI} or a {TURTLE_BLANK_NODE}.
        It SHOULD be an IRI when a globally stable graph identifier is available.
        """),
        examples=TURTLE_IRI_EXAMPLES + TURTLE_BLANK_NODE_EXAMPLES,
        json_schema_extra={
            "oneOf": [
                {"format": "iri"},
                {"pattern": _TURTLE_ECMA_BLANK_NODE_PATTERN},
            ]
        },
    ),
]

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
        examples=["<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"],
    )
    object: N3Node = Field(
        ...,
        description="The object of relationship indicated by the predicate.",
        examples=[
            "<https://schema.org/Person>",
            "<http://www.w3.org/ns/prov#Agent>",
            "<http://xmlns.com/foaf/0.1/Person>",
        ],
    )


class N3Triple(_HasSpo):
    """
    RDF triple represented in N3 lexical form.

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
    RDF quad represented in N3 lexical form.

    Use this model when the triple is asserted within a specific named graph given by `graph_id`.
    See RDF 1.1 Concepts and Abstract Syntax § 4 RDF Datasets.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    graph_id: Final[N3ContextIdentifier] = Field(
        ..., description="The name of the RDF Graph wherein this statement is asserted."
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

    updated: NonNegativeInt = Field(
        description="Number of RDF statements or graphs affected by the operation."
    )
    message: str = Field(description="Short human-readable summary of the mutation.")


class NewResourceNodeResponse(BaseModel):
    """Response payload when a blank node or IRI is defined.

    This resource is not in the knowlede base until it is asserted in a statement.
    """

    model_config = ConfigDict(frozen=True)

    resource: str = Field(description="The newly defined resource in N3 lexical form.")


class SerializationResponse(BaseModel):
    """Response payload for dataset or graph serialization."""

    model_config = ConfigDict(frozen=True)

    format: LiteralType["trig", "turtle", "nt", "n3"] = Field(
        description="Serialization format used for the returned content."
    )
    content: str = Field(description="Serialized RDF content.")


class SerializeRequest(BaseModel):
    """Request payload for serializing dataset state."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    format: LiteralType["trig", "turtle", "nt", "n3"] = Field(
        default="trig",
        description="Serialization format for the current default-graph knowledge base.",
    )


class TripleBatchRequest(BaseModel):
    """Request payload for exact-match triple updates."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    triples: tuple[N3Triple, ...] = Field(
        min_length=1,
        description="One or more exact RDF triples to add or remove.",
    )


class TripleListResponse(BaseModel):
    """Response payload listing triples from the default graph."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    triples: tuple[N3Triple, ...] = Field(
        description="Triples currently present in the default graph."
    )
