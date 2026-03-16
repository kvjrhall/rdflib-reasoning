from typing import Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)
from rdflib import IdentifiedNode, Node, URIRef
from rdflib.graph import Graph, ReadOnlyGraphAggregate, _QuadType
from rdflib.term import BNode
from rdflib.util import from_n3
from rfc3987_syntax import is_valid_syntax_iri  # type: ignore

from .dataset_middleware import DatasetMiddleware
from .dataset_state import DatasetState


def _parse_node(value: str) -> Node:
    try:
        node = from_n3(value)
        if not isinstance(node, Node):
            raise ValueError("Unable to parse RDF term from text")
        elif isinstance(value, URIRef):
            if not is_valid_syntax_iri(value):
                raise ValueError(
                    "IRI is not a RFC 3987 absolute IRI (required for RDF)"
                )
        return node
    except Exception as e:
        raise ValueError(f"Could not parse RDF term from {value!r}.") from e


def _parse_identified_node(value: str) -> IdentifiedNode:
    try:
        node = _parse_node(value)
        if not isinstance(node, IdentifiedNode):
            raise TypeError(f"Expected an IRI or blank node, got {type(node).__name__}")
        return node
    except Exception as e:
        raise ValueError(f"Failed to parse identified node from {value!r}") from e


def _parse_iri(value: str) -> URIRef:
    try:
        node = _parse_node(value)
        if not isinstance(node, URIRef):
            raise TypeError(f"Expected an IRI, got {type(node).__name__}")
        return node
    except Exception as e:
        raise ValueError(f"Failed to parse IRI from {value!r}") from e


def _parse_graph_context(value: str) -> Graph:
    try:
        # This graph is effectively an identifier and MUST NOT be modified
        graphContext = Graph(identifier=_parse_identified_node(value))
        return ReadOnlyGraphAggregate([graphContext])
    except Exception as e:
        raise ValueError(f"Could not parse graph context from {value!r}.") from e


def _node_to_string(node: Node) -> str:
    return cast(str, node.n3())


def _graph_context_to_string(graph: Graph) -> str:
    return _node_to_string(graph.identifier)


class RDFTripleModel(BaseModel):
    """Schema-facing triple payload for Research Agent dataset tools."""

    model_config = ConfigDict(frozen=True)

    subject: str = Field(
        description="N3 subject term, usually an IRI like `<urn:example:s>`."
    )
    predicate: str = Field(description="N3 predicate term; this MUST be an IRI.")
    object: str = Field(
        description="N3 object term such as an IRI, blank node, or literal."
    )

    @field_validator("subject")
    @classmethod
    def _validate_subject(cls, value: str) -> str:
        _parse_identified_node(value)
        return value

    @field_validator("predicate")
    @classmethod
    def _validate_predicate(cls, value: str) -> str:
        _parse_iri(value)
        return value

    @field_validator("object")
    @classmethod
    def _validate_object(cls, value: str) -> str:
        _parse_node(value)
        return value

    def to_rdflib(self) -> tuple[IdentifiedNode, URIRef, Node]:
        return (
            _parse_identified_node(self.subject),
            _parse_iri(self.predicate),
            _parse_node(self.object),
        )

    @classmethod
    def from_rdflib(
        cls, triple: tuple[IdentifiedNode, URIRef, Node]
    ) -> "RDFTripleModel":
        return cls(
            subject=_node_to_string(triple[0]),
            predicate=_node_to_string(triple[1]),
            object=_node_to_string(triple[2]),
        )


class RDFQuadModel(BaseModel):
    """Schema-facing quad payload for Research Agent dataset tools."""

    model_config = ConfigDict(frozen=True)

    subject: str = Field(
        description="N3 subject term, usually an IRI like `<urn:example:s>`."
    )
    predicate: str = Field(description="N3 predicate term; this MUST be an IRI.")
    object: str = Field(
        description="N3 object term such as an IRI, blank node, or literal."
    )
    graph: str = Field(
        description="N3 graph identifier; this MUST be an IRI or blank node."
    )

    @field_validator("subject")
    @classmethod
    def _validate_subject(cls, value: str) -> str:
        _parse_identified_node(value)
        return value

    @field_validator("predicate")
    @classmethod
    def _validate_predicate(cls, value: str) -> str:
        _parse_iri(value)
        return value

    @field_validator("object")
    @classmethod
    def _validate_object(cls, value: str) -> str:
        _parse_node(value)
        return value

    @field_validator("graph")
    @classmethod
    def _validate_graph(cls, value: str) -> str:
        _parse_identified_node(value)
        return value

    def to_rdflib(self) -> tuple[IdentifiedNode, URIRef, Node, IdentifiedNode]:
        return (
            _parse_identified_node(self.subject),
            _parse_iri(self.predicate),
            _parse_node(self.object),
            _parse_identified_node(self.graph),
        )

    @classmethod
    def from_rdflib(
        cls, quad: tuple[IdentifiedNode, URIRef, Node, IdentifiedNode]
    ) -> "RDFQuadModel":
        return cls(
            subject=_node_to_string(quad[0]),
            predicate=_node_to_string(quad[1]),
            object=_node_to_string(quad[2]),
            graph=_node_to_string(quad[3]),
        )


class TripleBatchRequest(BaseModel):
    """Request payload for exact-match triple updates."""

    triples: list[RDFTripleModel] = Field(min_length=1)


class QuadBatchRequest(BaseModel):
    """Request payload for exact-match quad updates."""

    quads: list[RDFQuadModel] = Field(min_length=1)


class CreateGraphRequest(BaseModel):
    """Request payload for named graph creation."""

    graph: str = Field(
        description="N3 graph identifier; this MUST be an IRI or blank node."
    )

    @field_validator("graph")
    @classmethod
    def _validate_graph(cls, value: str) -> str:
        _parse_identified_node(value)
        return value


class SerializeRequest(BaseModel):
    """Request payload for serializing dataset state."""

    format: Literal["trig", "turtle", "nt", "n3"] = "trig"
    graph: str | None = Field(
        default=None,
        description="Optional N3 graph identifier. Omit to serialize the full dataset.",
    )

    @field_validator("graph")
    @classmethod
    def _validate_graph(cls, value: str | None) -> str | None:
        if value is not None:
            _parse_identified_node(value)
        return value


class GraphListResponse(BaseModel):
    """Response payload listing current graph identifiers."""

    graphs: list[str]


class TripleListResponse(BaseModel):
    """Response payload listing triples from the default graph."""

    triples: list[RDFTripleModel]


class QuadListResponse(BaseModel):
    """Response payload listing quads across the dataset."""

    quads: list[RDFQuadModel]


class MutationResponse(BaseModel):
    """Response payload for state-mutating dataset tools."""

    updated: int
    message: str


class SerializationResponse(BaseModel):
    """Response payload for dataset or graph serialization."""

    format: str
    content: str


class DatasetToolLayer:
    """Thin Research Agent-facing tool layer over dataset middleware state."""

    def __init__(
        self,
        middleware: DatasetMiddleware | None = None,
        state: DatasetState | None = None,
    ) -> None:
        self.middleware = middleware or DatasetMiddleware()
        self.state = state or self.middleware.create_state()

    def reset_dataset(self) -> MutationResponse:
        self.state = self.middleware.reset_state(self.state)
        return MutationResponse(updated=0, message="Dataset state reset.")

    def list_graphs(self) -> GraphListResponse:
        graphs = [
            _node_to_string(graph.identifier)
            for graph in self.middleware.list_graphs(self.state)
        ]
        return GraphListResponse(graphs=graphs)

    def create_graph(self, request: CreateGraphRequest) -> MutationResponse:
        self.middleware.create_graph(self.state, _parse_identified_node(request.graph))
        return MutationResponse(updated=1, message="Graph created or already present.")

    def remove_graph(self, request: CreateGraphRequest) -> MutationResponse:
        self.middleware.remove_graph(self.state, _parse_identified_node(request.graph))
        return MutationResponse(updated=1, message="Graph removed if it existed.")

    def list_triples(self) -> TripleListResponse:
        triples = [
            RDFTripleModel.from_rdflib(
                cast(tuple[IdentifiedNode, URIRef, Node], triple)
            )
            for triple in self.middleware.list_triples(self.state)
        ]
        return TripleListResponse(triples=triples)

    def add_triples(self, request: TripleBatchRequest) -> MutationResponse:
        self.middleware.add_triples(
            self.state, [triple.to_rdflib() for triple in request.triples]
        )
        return MutationResponse(
            updated=len(request.triples),
            message="Triples added to the default graph.",
        )

    def remove_triples(self, request: TripleBatchRequest) -> MutationResponse:
        self.middleware.remove_triples(
            self.state, [triple.to_rdflib() for triple in request.triples]
        )
        return MutationResponse(
            updated=len(request.triples),
            message="Triples removed from the default graph.",
        )

    def list_quads(self) -> QuadListResponse:
        quads = [
            RDFQuadModel.from_rdflib(
                cast(tuple[IdentifiedNode, URIRef, Node, IdentifiedNode], quad)
            )
            for quad in self.middleware.list_quads(self.state)
            if isinstance(quad[3], (URIRef, BNode))
        ]
        return QuadListResponse(quads=quads)

    def add_quads(self, request: QuadBatchRequest) -> MutationResponse:
        quads = cast(list[_QuadType], [quad.to_rdflib() for quad in request.quads])
        self.middleware.add_quads(self.state, quads)
        return MutationResponse(
            updated=len(request.quads),
            message="Quads added to the dataset.",
        )

    def remove_quads(self, request: QuadBatchRequest) -> MutationResponse:
        quads = cast(list[_QuadType], [quad.to_rdflib() for quad in request.quads])
        self.middleware.remove_quads(self.state, quads)
        return MutationResponse(
            updated=len(request.quads),
            message="Quads removed from the dataset.",
        )

    def serialize(
        self, request: SerializeRequest | None = None
    ) -> SerializationResponse:
        request = request or SerializeRequest()
        content = self.middleware.serialize(
            self.state,
            format=request.format,
            graph_identifier=(
                _parse_identified_node(request.graph)
                if request.graph is not None
                else None
            ),
        )
        return SerializationResponse(format=request.format, content=content)
