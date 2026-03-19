import logging
from collections.abc import Awaitable, Callable, Iterable, MutableSet, Sequence
from dataclasses import dataclass
from dataclasses import field as DataclassField
from typing import Any, Final, Literal, override

import more_itertools
from deepagents.middleware._utils import append_to_system_message
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import (
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
    ToolCallRequest,
)
from langchain.tools import BaseTool, tool
from langchain_core.messages import ToolMessage
from pydantic import BaseModel, NonNegativeInt
from rdflib import BNode, Dataset, Graph, IdentifiedNode, Node
from rdflibr.axiom.common import Triple
from readerwriterlock import rwlock

from .dataset_model import (
    TURTLE_BLANK_NODE,
    MutationResponse,
    N3Triple,
    NewResourceNodeResponse,
    SerializationResponse,
    SerializeRequest,
    TripleBatchRequest,
    TripleListResponse,
)
from .dataset_state import DatasetState

logger = logging.getLogger(__name__)

DATASET_SYSTEM_PROMPT: Final[str] = """## Knowledge Base

- You have a knowledge base implemented as RDF.
- In the current middleware phase, the knowledge base is the default RDF graph only.
- Use the knowledge base when facts should persist across multiple reasoning steps.
- Use the knowledge base when semantics should be unambiguously represented.
- Use the knowledge base if you are expected to output RDF
- Prefer adding or correcting exact triples over resetting the entire knowledge base.
- Model facts in an atemporal, stable way when possible rather than storing transient phrasing as timeless truth.
- When asserting facts into the knowledge base, you SHOULD keep them grounded in the provided content unless the user explicitly asks for inference, extrapolation, or hypothesis generation.
- You SHOULD NOT assert uncertain facts as settled triples.
- When transforming unstructured content into RDF, you SHOULD prefer controlled vocabularies when they fit the source material and task.
- If you mint IRIs and the user does not specify a base IRI, you SHOULD use <urn:rdflibr:> as the default base for minted IRIs.
- When presenting RDF to the user or serializing the knowledge base for inspection, you SHOULD prefer Turtle unless the user requests a different RDF serialization.
- SHOULD NOT mint IRIs if convention dictates that they be blank nodes (e.g., OWL 2 Class Restrictions).
- You SHOULD prefer a minted IRI over a blank node when there is an authorative IRI base for that resource.
- When minting an IRI to represent a Class, Datatype, or Property, you MUST assign it a `rdfs:label` and define it using `rdfs:comment`.


### Knowledge Base Tools

- `list_triples`: inspect the current triples in the knowledge base
- `add_triples`: add exact triples to the knowledge base
- `remove_triples`: remove exact triples from the knowledge base
- `serialize_dataset`: render the current knowledge base as RDF text
- `reset_dataset`: clear the entire knowledge base
- `new_blank_node`: create an anonymous resource without an IRI
"""


RESET_DATASET_TOOL_DESCRIPTION: Final[str] = """Reset the RDF dataset to an empty state.

This permanently discards the current knowledge base state for the current session.

You MUST NOT use this tool as part of normal iterative drafting, exploration, or correction.
You MUST NOT call this tool repeatedly while deciding what triples to add.
You SHOULD prefer `remove_triples` or adding corrected triples when only part of the dataset is wrong.

Use this tool only when ALL of the following are true:
- the current dataset is broadly unusable or fundamentally mis-modeled
- targeted correction would be less clear or less reliable than starting over
- you are prepared to rebuild the dataset immediately after resetting it

After calling this tool, you SHOULD proceed directly to rebuilding the dataset rather than continuing to deliberate.
"""


CREATE_BLANK_NODE_TOOL_DESCRIPTION: Final[
    str
] = f"""Create a new RDF Blank Node Identifier for use as the subject of object of a triple in your knowledge base.

The **NEED** for a {TURTLE_BLANK_NODE} **MUST** precede its creation by this tool.
The entity MUST be necessary as the subject or object of a triple in your knowledge base.

You MUST use a Blank Node when conventions dictate. E.g.,:
   - OWL 2 Class Restrictions
   - RDF Collections
   - SHACL Constraints
   - Other structural conventions dictated by a specific standard, specification, or application.

Blank Nodes used outside of those conventions MUST also satisfy the following requirements:
- There MUST NOT be a meaningful IRI that can be associated with the entity.
- It MUST be outside your authority to mint a new IRI for this entity, or adding a new IRI reduces clarity.
- A Blank Node MUST be assigned one or more `rdf:type`s, one `rdfs:label`, and one definitional `rdfs:comment`.
- A Blank Node MUST NOT be used to represent vocabulary terms that you introduce.
"""

RESET_DATASET_MISUSE_MESSAGE: Final[str] = """Misuse: `reset_dataset` was rejected.

Your dataset is empty. You have not yet used `add_triples` to add content.

Use `reset_dataset` only when the current dataset is broadly unusable and you are ready
to rebuild it immediately. Do not use it for iterative drafting, exploration, or
repeated correction while deciding what triples to add.
"""

NEW_BLANK_NODE_MISUSE_MESSAGE: Final[str] = """Misuse: `new_blank_node` was rejected.

You have already requested 2 blank nodes, but have yet to use either in an `add_triples` call.

Use `new_blank_node` only when an anonymous RDF resource is genuinely required. Do not
use it as a placeholder while exploring, and do not use blank nodes for vocabulary
terms that you introduce. You must use your existing blank nodes before creating
new ones: {existing}
"""


@dataclass(frozen=True, slots=True)
class DatasetSession:
    _dataset: Dataset
    _blank_nodes: MutableSet[BNode] = DataclassField(default_factory=set)
    _lock: rwlock.RWLockable = DataclassField(default_factory=rwlock.RWLockFairD)

    def snapshot_dataset(self) -> Dataset:
        def _cleanup_quad(
            quad: tuple[Node, Node, Node, IdentifiedNode | None],
        ) -> tuple[Node, Node, Node, Graph]:
            s, p, o, gId = quad
            g = (
                self._dataset.get_graph(gId)
                if gId is not None
                else self._dataset.default_graph
            )
            assert isinstance(g, Graph)
            return (s, p, o, g)

        with self._lock.gen_rlock():
            dataset = Dataset()
            for chunk in more_itertools.chunked(
                map(_cleanup_quad, self._dataset.quads((None, None, None, None))),
                1000,
            ):
                dataset.addN(chunk)
            return dataset


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
    session: DatasetSession
    tools: Sequence[BaseTool]

    def __init__(self, config: DatasetMiddlewareConfig | None = None) -> None:
        self.config = config or DatasetMiddlewareConfig()
        self.session = DatasetSession(_dataset=Dataset())
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
        """Append dataset guidance to the system prompt before model execution."""
        logger.debug("Wrapping model call for Dataset Middleware")
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                DATASET_SYSTEM_PROMPT,
            )
        )
        return handler(request)

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[
            [ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]
        ],
    ) -> Any:
        """Append dataset guidance to the system prompt before async model execution."""
        logger.debug("Async wrapping model call for Dataset Middleware (async)")
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                DATASET_SYSTEM_PROMPT,
            )
        )
        return await handler(request)

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Any],
    ) -> ToolMessage | Any:
        """Reject invalid dataset tool usage before calling the wrapped tool."""
        tool_name = (
            request.tool.name if request.tool is not None else request.tool_call["name"]
        )
        tool_call_id = request.tool_call["id"]

        if tool_name == "reset_dataset" and self._should_reject_reset_dataset(request):
            return ToolMessage(
                content=RESET_DATASET_MISUSE_MESSAGE,
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )

        if tool_name == "new_blank_node" and self._should_reject_new_blank_node(
            request
        ):
            unused_blank_nodes = ", ".join([b.n3() for b in self.session._blank_nodes])
            return ToolMessage(
                content=NEW_BLANK_NODE_MISUSE_MESSAGE.format(
                    existing=unused_blank_nodes
                ),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )

        return handler(request)

    def _should_reject_reset_dataset(self, request: ToolCallRequest) -> bool:
        """Hook for reset-dataset misuse detection."""
        with self.session._lock.gen_rlock():
            return len(self.session._dataset) == 0

    def _should_reject_new_blank_node(self, request: ToolCallRequest) -> bool:
        """Hook for blank-node misuse detection."""
        with self.session._lock.gen_rlock():
            too_many = len(self.session._blank_nodes) >= 2
        if too_many:
            with self.session._lock.gen_wlock():
                dataset = self.session._dataset
                for blank_node in list(self.session._blank_nodes):
                    if (blank_node, None, None, None) in dataset:
                        self.session._blank_nodes.remove(blank_node)
                return len(self.session._blank_nodes) >= 2
        else:
            return False

        # There are already 2 unusred blank nodes, which is enough to make a
        # triple, so this is an extraneous request.

    def _replace_dataset(self) -> None:
        """Replace the middleware-owned dataset session."""
        with self.session._lock.gen_wlock():
            self.session._dataset.close()
            object.__setattr__(self, "session", DatasetSession(_dataset=Dataset()))

    def list_triples(self) -> tuple[Triple, ...]:
        """Return all exact triples currently present in the default graph."""
        with self.session._lock.gen_rlock():
            return tuple(
                self.session._dataset.default_graph.triples((None, None, None))
            )

    def add_triples(self, triples: Iterable[Triple]) -> MutationResponse:
        """Add exact triples to the default graph."""
        with self.session._lock.gen_wlock():
            graph = self.session._dataset.default_graph
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
        with self.session._lock.gen_wlock():
            graph = self.session._dataset.default_graph
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
        with self.session._lock.gen_wlock():
            updated = len(self.session._dataset.default_graph)
            self.session._dataset.close()
            object.__setattr__(self, "session", DatasetSession(_dataset=Dataset()))
        return MutationResponse(
            updated=NonNegativeInt(updated),
            message="Dataset state reset.",
        )

    def serialize(
        self,
        format: Literal["trig", "turtle", "nt", "n3"] = "trig",
    ) -> str:
        """Serialize the default graph as RDF text."""
        with self.session._lock.gen_rlock():
            data = self.session._dataset.default_graph.serialize(format=format)
        return data.decode("utf-8") if isinstance(data, bytes) else data

    def _build_tools(self) -> tuple[BaseTool, ...]:
        """Build the schema-facing tool surface."""

        @tool(
            "list_triples",
            description="List all exact triples currently stored in the knowledge base.",
        )
        def list_triples_tool() -> TripleListResponse:
            logger.debug("Listing triples")
            triples = tuple(
                N3Triple.from_rdflib(triple) for triple in self.list_triples()
            )
            return TripleListResponse(triples=triples)

        @tool(
            "add_triples",
            args_schema=TripleBatchRequest,
            description="Add exact triples to the default RDF graph knowledge base.",
        )
        def add_triples_tool(triples: tuple[N3Triple, ...]) -> MutationResponse:
            logger.debug("Adding triples")
            return self.add_triples(triple.as_rdflib for triple in triples)

        @tool(
            "remove_triples",
            args_schema=TripleBatchRequest,
            description="Remove exact triples from the default RDF graph knowledge base.",
        )
        def remove_triples_tool(triples: tuple[N3Triple, ...]) -> MutationResponse:
            logger.debug("Removing triples")
            return self.remove_triples(triple.as_rdflib for triple in triples)

        @tool(
            "serialize_dataset",
            args_schema=SerializeRequest,
            description="Serialize the current default-graph knowledge base as RDF text.",
        )
        def serialize_dataset_tool(
            format: Literal["trig", "turtle", "nt", "n3"] = "trig",
        ) -> SerializationResponse:
            logger.debug("Serializing dataset")
            return SerializationResponse(
                format=format,
                content=self.serialize(format=format),
            )

        @tool("reset_dataset", description=RESET_DATASET_TOOL_DESCRIPTION)
        def reset_dataset_tool() -> MutationResponse:
            logger.debug("Resetting dataset")
            return self.reset_dataset()

        @tool(
            "new_blank_node",
            description=CREATE_BLANK_NODE_TOOL_DESCRIPTION,
        )
        def new_blank_node_tool() -> NewResourceNodeResponse:
            logger.debug("Creating new blank node")
            resource = BNode()
            with self.session._lock.gen_wlock():
                self.session._blank_nodes.add(resource)
            return NewResourceNodeResponse(resource=resource.n3())

        return (
            list_triples_tool,
            add_triples_tool,
            remove_triples_tool,
            serialize_dataset_tool,
            reset_dataset_tool,
            new_blank_node_tool,
        )
