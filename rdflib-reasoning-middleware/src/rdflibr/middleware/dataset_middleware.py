from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from dataclasses import field as DataclassField
from typing import Final, Literal, override

from deepagents.middleware._utils import append_to_system_message
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import (
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from langchain.tools import BaseTool, tool
from pydantic import BaseModel, NonNegativeInt
from rdflib import Dataset
from rdflibr.axiom.common import Triple
from readerwriterlock import rwlock

from .dataset_model import (
    MutationResponse,
    N3Triple,
    SerializationResponse,
    SerializeRequest,
    TripleBatchRequest,
    TripleListResponse,
)
from .dataset_state import DatasetState

RESET_DATASET_TOOL_DESCRIPTION: Final[str] = """Reset the RDF dataset to an empty state.

Use this only when you intentionally want to discard the current knowledge base.
Before resetting, you SHOULD consider whether removing or rewriting only the
incorrect triples would preserve more useful context.
"""

DATASET_SYSTEM_PROMPT: Final[str] = """## Knowledge Base

- You have a knowledge base implemented as RDF.
- In the current middleware phase, the knowledge base is the default RDF graph only.
- Use the knowledge base when facts should persist across multiple reasoning steps.
- Use the knowledge base when semantics should be unambiguously represented.
- Use the knowledge base if you are expected to output RDF
- Prefer adding or correcting exact triples over resetting the entire knowledge base.
- Model facts in an atemporal, stable way when possible rather than storing transient phrasing as timeless truth.

### Knowledge Base Tools

- `list_triples`: inspect the current triples in the knowledge base
- `add_triples`: add exact triples to the knowledge base
- `remove_triples`: remove exact triples from the knowledge base
- `serialize_dataset`: render the current knowledge base as RDF text
- `reset_dataset`: clear the entire knowledge base
"""


@dataclass(frozen=True, slots=True)
class _DatasetSession:
    dataset: Dataset
    lock: rwlock.RWLockable = DataclassField(default_factory=rwlock.RWLockFairD)


class DatasetMiddlewareConfig(BaseModel):
    """Configuration for the initial dataset middleware surface."""

    pass


class DatasetMiddleware(AgentMiddleware[DatasetState, ContextT, ResponseT]):
    """
    Initial dataset middleware for dataset-backed agent experiments.

    This phase intentionally exposes only default-graph operations to the
    Research Agent.
    """

    state_schema = DatasetState
    _session: _DatasetSession
    tools: Sequence[BaseTool]

    def __init__(self, config: DatasetMiddlewareConfig | None = None) -> None:
        self.config = config or DatasetMiddlewareConfig()
        self._session = _DatasetSession(dataset=Dataset())
        self.tools = self._build_tools()

    def _create_state(self) -> DatasetState:
        """Create a fresh middleware state."""
        return {"messages": []}

    def _reset_state(self) -> DatasetState:
        """Replace any existing dataset session with a fresh empty one."""
        self._replace_dataset()
        return self._create_state()

    @override
    def before_agent(
        self,
        state: DatasetState,
        runtime: object,
    ) -> None:
        """Dataset session state is owned by the middleware itself."""
        del state, runtime
        return None

    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                DATASET_SYSTEM_PROMPT,
            )
        )
        return handler(request)

    def _replace_dataset(self) -> None:
        """Replace the middleware-owned dataset session."""
        with self._session.lock.gen_wlock():
            self._session.dataset.close()
            object.__setattr__(self, "_session", _DatasetSession(dataset=Dataset()))

    def list_triples(self) -> tuple[Triple, ...]:
        """Return all exact triples currently present in the default graph."""
        with self._session.lock.gen_rlock():
            return tuple(
                self._session.dataset.default_graph.triples((None, None, None))
            )

    def add_triples(self, triples: Iterable[Triple]) -> MutationResponse:
        """Add exact triples to the default graph."""
        with self._session.lock.gen_wlock():
            graph = self._session.dataset.default_graph
            before = len(graph)
            for triple in triples:
                graph.add(triple)
            updated = len(graph) - before
        return MutationResponse(
            updated=NonNegativeInt(updated),
            message="Triples added to the default graph.",
        )

    def remove_triples(self, triples: Iterable[Triple]) -> MutationResponse:
        """Remove exact triples from the default graph."""
        with self._session.lock.gen_wlock():
            graph = self._session.dataset.default_graph
            before = len(graph)
            for triple in triples:
                graph.remove(triple)
            updated = before - len(graph)
        return MutationResponse(
            updated=NonNegativeInt(updated),
            message="Triples removed from the default graph.",
        )

    def reset_dataset(self) -> MutationResponse:
        """Reset the middleware-owned dataset session."""
        with self._session.lock.gen_wlock():
            updated = len(self._session.dataset.default_graph)
            self._session.dataset.close()
            object.__setattr__(self, "_session", _DatasetSession(dataset=Dataset()))
        return MutationResponse(
            updated=NonNegativeInt(updated),
            message="Dataset state reset.",
        )

    def serialize(
        self,
        format: Literal["trig", "turtle", "nt", "n3"] = "trig",
    ) -> str:
        """Serialize the default graph as RDF text."""
        with self._session.lock.gen_rlock():
            data = self._session.dataset.default_graph.serialize(format=format)
        return data.decode("utf-8") if isinstance(data, bytes) else data

    def _build_tools(self) -> tuple[BaseTool, ...]:
        """Build the schema-facing tool surface."""

        @tool(
            "list_triples",
            description="List all exact triples currently stored in the knowledge base.",
        )
        def list_triples_tool() -> dict[str, object]:
            triples = tuple(
                N3Triple.from_rdflib(triple) for triple in self.list_triples()
            )
            return TripleListResponse(triples=triples).model_dump(mode="json")

        @tool(
            "add_triples",
            args_schema=TripleBatchRequest,
            description="Add exact triples to the default RDF graph knowledge base.",
        )
        def add_triples_tool(triples: tuple[N3Triple, ...]) -> dict[str, object]:
            response = self.add_triples(triple.as_rdflib for triple in triples)
            return response.model_dump(mode="json")

        @tool(
            "remove_triples",
            args_schema=TripleBatchRequest,
            description="Remove exact triples from the default RDF graph knowledge base.",
        )
        def remove_triples_tool(triples: tuple[N3Triple, ...]) -> dict[str, object]:
            response = self.remove_triples(triple.as_rdflib for triple in triples)
            return response.model_dump(mode="json")

        @tool(
            "serialize_dataset",
            args_schema=SerializeRequest,
            description="Serialize the current default-graph knowledge base as RDF text.",
        )
        def serialize_dataset_tool(
            format: Literal["trig", "turtle", "nt", "n3"] = "trig",
        ) -> dict[str, object]:
            return SerializationResponse(
                format=format,
                content=self.serialize(format=format),
            ).model_dump(mode="json")

        @tool("reset_dataset", description=RESET_DATASET_TOOL_DESCRIPTION)
        def reset_dataset_tool() -> dict[str, object]:
            return self.reset_dataset().model_dump(mode="json")

        return (
            list_triples_tool,
            add_triples_tool,
            remove_triples_tool,
            serialize_dataset_tool,
            reset_dataset_tool,
        )
