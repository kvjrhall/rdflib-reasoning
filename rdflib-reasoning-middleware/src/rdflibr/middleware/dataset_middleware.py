from collections.abc import Iterable
from typing import cast

from pydantic import BaseModel, Field
from rdflib import Dataset, Graph, IdentifiedNode
from rdflib.graph import _QuadType, _TriplePatternType, _TripleType

from .dataset_state import DatasetState


class DatasetMiddlewareConfig(BaseModel):
    """Configuration for the initial dataset middleware surface."""

    default_graph_base: str = Field(
        default="urn:rdflibr:graph:",
        description="Base IRI used when the middleware later creates named graphs.",
    )


class DatasetMiddleware:
    """
    Initial dataset middleware for dataset-backed agent experiments.

    This class provides the baseline dataset CRUD surface that later retrieval
    and inference middleware can compose over.
    """

    def __init__(self, config: DatasetMiddlewareConfig | None = None) -> None:
        self.config = config or DatasetMiddlewareConfig()

    def _dataset(self, state: DatasetState) -> Dataset:
        return state["dataset"]

    def create_state(self) -> DatasetState:
        """Create a fresh dataset-backed middleware state."""
        return cast(DatasetState, {"messages": [], "dataset": Dataset()})

    def reset_state(self, state: DatasetState | None = None) -> DatasetState:
        """Replace any existing dataset with a fresh empty one."""
        del state
        return self.create_state()

    def list_triples(self, state: DatasetState) -> list[_TripleType]:
        """Return all triples currently present in the default graph."""
        return list(self._dataset(state).default_graph.triples((None, None, None)))

    def add_triples(
        self, state: DatasetState, triples: Iterable[_TripleType]
    ) -> DatasetState:
        """Add triples to the default graph."""
        graph = self._dataset(state).default_graph
        for triple in triples:
            graph.add(triple)
        return state

    def remove_triples(
        self, state: DatasetState, triples: Iterable[_TriplePatternType]
    ) -> DatasetState:
        """Remove matching triples from the default graph."""
        graph = self._dataset(state).default_graph
        for triple in triples:
            graph.remove(triple)
        return state

    def list_quads(self, state: DatasetState) -> list[_QuadType]:
        """Return all quads currently present in the dataset."""
        return cast(
            list[_QuadType],
            list(self._dataset(state).quads((None, None, None, None))),
        )

    def add_quads(
        self, state: DatasetState, quads: Iterable[_QuadType]
    ) -> DatasetState:
        """Add quads to the dataset, creating named graphs as needed."""
        self._dataset(state).addN(quads)
        return state

    def remove_quads(
        self, state: DatasetState, quads: Iterable[_QuadType]
    ) -> DatasetState:
        """Remove quads from the dataset."""
        dataset = self._dataset(state)
        for subject, predicate, obj, graph in quads:
            dataset.remove((subject, predicate, obj, graph))
        return state

    def create_graph(self, state: DatasetState, identifier: IdentifiedNode) -> Graph:
        """Create or retrieve a named graph in the dataset."""
        return self._dataset(state).graph(identifier)

    def list_graphs(self, state: DatasetState) -> list[Graph]:
        """List the graphs currently present in the dataset."""
        return list(self._dataset(state).graphs())

    def remove_graph(
        self, state: DatasetState, identifier: IdentifiedNode
    ) -> DatasetState:
        """Remove a named graph from the dataset."""
        self._dataset(state).remove_graph(identifier)
        return state

    def serialize(
        self,
        state: DatasetState,
        format: str = "trig",
        graph_identifier: IdentifiedNode | None = None,
    ) -> str:
        """Serialize either the whole dataset or a selected graph for inspection."""
        serializable = (
            self._dataset(state).graph(graph_identifier)
            if graph_identifier is not None
            else self._dataset(state)
        )
        data = serializable.serialize(format=format)
        return data.decode("utf-8") if isinstance(data, bytes) else data
