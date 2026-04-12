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
from rdflib_reasoning.axiom.common import Triple
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
_PLAINTEXT_LITERAL_HINT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\s|[.!?,;:]|^[A-Za-z][A-Za-z0-9_-]*$"
)


def _parse_node(value: str | Node) -> Node:
    original_value = value
    input_was_text = not isinstance(value, Node)
    try:
        if isinstance(value, Node):
            node = value
        else:
            candidate = value.strip()
            try:
                parsed = from_n3(candidate)
            except Exception:
                # Accept bare RFC 3987 IRIs as an input convenience, but normalize
                # them through N3 parsing so serialization remains canonical.
                if (
                    candidate
                    and not candidate.startswith(("<", "_:", '"', "'", "(", "["))
                    and is_valid_syntax_iri(candidate)
                ):
                    parsed = from_n3(f"<{candidate}>")
                else:
                    raise
            if not isinstance(parsed, Node):
                raise ValueError(
                    f"Unable to parse RDF term from text: {original_value}"
                )
            node = parsed
        if not isinstance(node, Node):
            raise ValueError(f"Unable to parse RDF term from text: {original_value}")
        node_text = _node_to_string(node).removeprefix("<").removesuffix(">")

        if input_was_text and isinstance(original_value, str):
            candidate = original_value.strip()
            if (
                candidate
                and not candidate.startswith(("<", "_:", '"', "'", "(", "["))
                and isinstance(node, URIRef | BNode)
                and ":" not in candidate
                and _PLAINTEXT_LITERAL_HINT_PATTERN.search(candidate) is not None
            ):
                raise ValueError(
                    "Could not parse RDF term from "
                    f"{original_value}. If this is plain text, encode it as an RDF "
                    f'literal like "\\"{candidate}\\"". If this is an IRI, provide '
                    "it either in canonical N3 form like <urn:example:Thing> or "
                    "as a bare RFC 3987 IRI."
                )

        if isinstance(node, URIRef):
            if not is_valid_syntax_iri(node_text):
                raise ValueError("IRI is not a valid RFC 3987 IRI (required for RDF)")
        elif isinstance(node, BNode) and not _turtle_blank_node_regex.match(node_text):
            raise ValueError(f"Invalid blank node: {node_text}")
        return node
    except Exception as e:
        if input_was_text and isinstance(original_value, str):
            candidate = original_value.strip()
            if candidate and not candidate.startswith(("<", "_:", '"', "'", "(", "[")):
                if (
                    not is_valid_syntax_iri(candidate)
                    and _PLAINTEXT_LITERAL_HINT_PATTERN.search(candidate) is not None
                ):
                    raise ValueError(
                        "Could not parse RDF term from "
                        f"{original_value}. If this is plain text, encode it as an RDF "
                        f'literal like "\\"{candidate}\\"". If this is an IRI, provide '
                        "it either in canonical N3 form like <urn:example:Thing> or "
                        "as a bare RFC 3987 IRI."
                    ) from e
                raise ValueError(
                    "Could not parse RDF term from "
                    f"{original_value}. If this is an IRI, provide it either in "
                    f"canonical N3 form like <{candidate}> or as a bare RFC 3987 IRI."
                ) from e
        raise ValueError(f"Could not parse RDF term from {original_value}.") from e


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
    '"Project report"',
    '"A short human-readable description."',
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
        RDF resource accepted in canonical N3 lexical form and serialized in N3.
        It MUST resolve to a {TURTLE_IRI} or a {TURTLE_BLANK_NODE}.
        Full IRIs MAY be provided either as canonical N3 like <urn:example:s> or
        as a bare RFC 3987 IRI like urn:example:s.
        It SHOULD be an IRI when a globally stable identifier is available.
        """).strip(),
        examples=TURTLE_IRI_EXAMPLES + ["urn:example:s"] + TURTLE_BLANK_NODE_EXAMPLES,
    ),
]

type N3IRIRef = Annotated[
    URIRef,
    BeforeValidator(_parse_iri, json_schema_input_type=str),
    PlainSerializer(_node_to_string, return_type=str),
    # WithJsonSchema({"type": "string"}, mode="serialization"),
    Field(
        description=textwrap.dedent(f"""
        RDF IRI reference accepted in canonical N3 lexical form and serialized in N3.
        It MUST resolve to a {TURTLE_IRI}.
        Full IRIs MAY be provided either as canonical N3 like <urn:example:p> or
        as a bare RFC 3987 IRI like urn:example:p.
        Use this for predicates and for resources that cannot be blank nodes.
        """).strip(),
        examples=TURTLE_IRI_EXAMPLES + ["urn:example:p"],
    ),
]

type N3Node = Annotated[
    Node,
    BeforeValidator(_parse_node, json_schema_input_type=str),
    PlainSerializer(_node_to_string, return_type=str),
    # WithJsonSchema({"type": "string"}, mode="serialization"),
    Field(
        description=textwrap.dedent(f"""
        RDF node accepted in canonical N3 lexical form and serialized in N3.
        It MUST resolve to one of the following:
        - {TURTLE_IRI}
        - {TURTLE_BLANK_NODE}
        - {TURTLE_LITERAL}
        Full IRIs MAY be provided either as canonical N3 like <urn:example:o> or
        as a bare RFC 3987 IRI like urn:example:o.
        """).strip(),
        examples=TURTLE_IRI_EXAMPLES
        + ["urn:example:o"]
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
        RDF graph name accepted in canonical N3 lexical form and serialized in N3.
        It corresponds to a {RDF_GRAPH_TERM}.
        It MUST resolve to a {TURTLE_IRI} or a {TURTLE_BLANK_NODE}.
        Full IRIs MAY be provided either as canonical N3 like <urn:example:g> or
        as a bare RFC 3987 IRI like urn:example:g.
        It SHOULD be an IRI when a globally stable graph identifier is available.
        """).strip(),
        examples=TURTLE_IRI_EXAMPLES + ["urn:example:g"] + TURTLE_BLANK_NODE_EXAMPLES,
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
