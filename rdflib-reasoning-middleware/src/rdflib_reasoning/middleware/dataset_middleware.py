import logging
from collections.abc import Awaitable, Callable, Iterable, MutableSet, Sequence
from dataclasses import dataclass
from dataclasses import field as DataclassField
from typing import Any, Final, Literal, TypeGuard, override

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
from pydantic import NonNegativeInt
from rdflib import BNode, Dataset, Graph, IdentifiedNode, Node, URIRef
from rdflib_reasoning.axiom.common import Triple
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
from .namespaces.spec_whitelist import (
    AllowAllNamespaceWhitelist,
    NamespaceWhitelist,
    WhitelistResult,
)

logger = logging.getLogger(__name__)


def _format_whitelist_violation_message(
    bad_term: URIRef, result: WhitelistResult
) -> str:
    """Build a single human-oriented tool error for Research Agents (see DR-014)."""
    lines: list[str] = [
        f"The term {bad_term} is not in the vocabulary whitelist for this knowledge base. "
        "You SHOULD verify that you are using the correct term or consider the alternatives "
        "below. "
        "You MUST NOT call `add_triples` again with this same IRI.",
        "",
    ]
    if result.nearest_matches:
        lines.extend(
            [
                "Suggested alternatives (Levenshtein distance measures string similarity; "
                "lower is better):",
                "",
                "| Qualified name | IRI | Levenshtein distance |",
                "| --- | --- | ---: |",
            ]
        )
        for term, dist in result.nearest_matches:
            qn = str(term.qname).replace("|", "\\|")
            iri = str(term.term).replace("|", "\\|")
            lines.append(f"| `{qn}` | `{iri}` | {dist} |")
        lines.append("")
        lines.append(
            "If none of the suggestions fit your intent, you MUST use a different term "
            "from the allowed vocabularies listed in the system prompt."
        )
    else:
        lines.append(
            "No close matches were found. You MUST use a different term from the "
            "allowed vocabularies listed in the system prompt."
        )
    return "\n".join(lines)


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
- If you mint IRIs and the user does not specify a base IRI, you SHOULD use <urn:rdflib_reasoning:> as the default base for minted IRIs.
- When presenting RDF to the user or serializing the knowledge base for inspection, you SHOULD prefer Turtle unless the user requests a different RDF serialization.
- SHOULD NOT mint IRIs if convention dictates that they be blank nodes (e.g., OWL 2 Class Restrictions).
- You SHOULD prefer a minted IRI over a blank node when there is an authorative IRI base for that resource.
- When minting an IRI to represent a Class, Datatype, or Property, you MUST assign it a `rdfs:label` and define it using `rdfs:comment`.

### Knowledge Base Tools

- `list_triples`: inspect the current triples in the knowledge base
- `add_triples`: Add triples to the knowledge base (idempotent)
- `remove_triples`: remove exact triples from the knowledge base
- `serialize_dataset`: render the current knowledge base as RDF text
- `reset_dataset`: clear the entire knowledge base
- `new_blank_node`: create an anonymous resource without an IRI

#### Knowledge Base Tool Guidance

- If you encounter tool rejection for `add_triples`, you SHOULD partition the arguments over multiple `add_triples` calls.
- Prefer `add_triples` and `remove_triples` to correct triples/facts rather than using `reset_dataset`.
- When providing IRIs to dataset tools, you MAY use either canonical N3 form like `<urn:ex:Foo>` or a bare RFC 3987 IRI like `urn:ex:Foo`.
  - The middleware serializes IRIs back in canonical N3 form.
- When a predicate expects text such as `rdfs:label` or `rdfs:comment`, the object MUST be an RDF literal such as `"Person"` or `"A biological classification for humans."`.
- You SHOULD NOT include the same triple in multiple `add_triples` calls; `add_triples` is idempotent.
- Errors like `Value error, Could not parse RDF term` indicate that your RDF term syntax is incorrect.
  - If the value is meant to be an IRI, first check whether it should be wrapped as `<...>` or corrected to a valid bare RFC 3987 IRI.
  - If the value is meant to be plain text, encode it as an RDF literal such as `"Person"` or `"A biological classification for humans."`.
- Mutating knowledge base tool effects are persistant, cumulative, and idempotent.
- You MUST keep each `add_triples` call small enough to recover from a single validation error.
  - You SHOULD prefer one subject per `add_triples` call.
  - You SHOULD NOT mix many unrelated subjects in one `add_triples` call.

### Guidance for Modeling Facts

- You MAY incrementally build your dataset using multiple `add_triples` calls.
  - You SHOULD prefer that each `add_triples` call completely describes one single concept or entity.

The following is an example of something that completely describes one single concept or entity.
The subject of this example is a class called `Foo`, but it is analogous to definitions introduced by your knowledge base.

```text/turtle
<urn:ex:Foo> a <rdfs:Class> ;
    rdfs:label "Foo" ;
    rdfs:comment "Foo are known to be used in examples." ;
    rdfs:subClassOf <urn:ex:Bar> .
```

- `<urn:ex:Foo> a <rdfs:Class>` is syntactic sugar for `<urn:ex:Foo> rdf:type <rdfs:Class>`.
- For `rdfs:label`, the object SHOULD usually be a short string literal such as `"Foo"`.
- For `rdfs:comment`, the object SHOULD usually be a descriptive string literal such as `"Foo are known to be used in examples."`.

- Model facts in an atemporal, stable way when possible rather than storing transient phrasing as timeless truth.
- When asserting facts into the knowledge base, you SHOULD keep them grounded in the provided content unless the user explicitly asks for inference, extrapolation, or hypothesis generation.
- You SHOULD NOT assert uncertain facts as settled triples.

### Usage of IRIs and Blank Nodes

- When transforming unstructured content into RDF, you SHOULD prefer controlled vocabularies when they fit the source material and task.
- If you mint IRIs and the user does not specify a base IRI, you SHOULD use <urn:rdflib_reasoning:> as the default base for minted IRIs.
- You SHOULD NOT mint IRIs if convention dictates that they be blank nodes (e.g., OWL 2 Class Restrictions).
- You SHOULD prefer a minted IRI over a blank node when there is an authorative IRI base for that resource.
- When minting an IRI to represent a Class, Datatype, or Property, you MUST assign it a `rdfs:label` and define it using `rdfs:comment`.
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

LIST_TRIPLES_TOOL_DESCRIPTION: Final[
    str
] = """List all exact triples currently stored in the default RDF graph knowledge base.

Call this tool with no arguments when you need to inspect the current graph state before
adding, removing, or describing facts.
"""

ADD_TRIPLES_TOOL_DESCRIPTION: Final[
    str
] = """Add one or more exact RDF triples to the default RDF graph knowledge base.

Pass `triples` as a top-level argument containing one or more RDF triples.
IRI inputs MAY be given either in canonical N3 form like `<urn:example:Person>` or
as bare RFC 3987 IRIs like `urn:example:Person`.
Literal text MUST be encoded as RDF literals like `"Person"` or
`"A biological classification for humans."`.
You SHOULD keep each call small and recoverable.
You SHOULD prefer one subject per call.

Example arguments:
- `{"triples": [{"subject": "<urn:example:Person>", "predicate": "<http://www.w3.org/2000/01/rdf-schema#label>", "object": "\"Person\""}]}`
- `{"triples": [{"subject": "<urn:example:Person>", "predicate": "<http://www.w3.org/2000/01/rdf-schema#comment>", "object": "\"A biological classification for humans.\""}]}`
- `{"triples": [{"subject": "urn:example:Person", "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "object": "http://www.w3.org/2000/01/rdf-schema#Class"}]}`
"""

REMOVE_TRIPLES_TOOL_DESCRIPTION: Final[
    str
] = """Remove one or more exact RDF triples from the default RDF graph knowledge base.

Pass `triples` as a top-level argument containing the exact triples to remove.
IRI inputs MAY be given either in canonical N3 form like `<urn:example:Person>` or
as bare RFC 3987 IRIs like `urn:example:Person`.

Example arguments:
- `{"triples": [{"subject": "<urn:example:Person>", "predicate": "<http://www.w3.org/2000/01/rdf-schema#label>", "object": "\"Person\""}]}`
- `{"triples": [{"subject": "urn:example:Person", "predicate": "http://www.w3.org/2000/01/rdf-schema#comment", "object": "\"A person.\""}]}`
"""

SERIALIZE_DATASET_TOOL_DESCRIPTION: Final[
    str
] = """Serialize the current default-graph knowledge base as RDF text.

Pass `format` as a top-level argument when you need a specific RDF serialization.

Example arguments:
- `{"format": "turtle"}`
- `{"format": "trig"}`
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


@dataclass(frozen=True, slots=True)
class DatasetMiddlewareConfig:
    """Configuration for the dataset middleware surface."""

    namespace_whitelist: NamespaceWhitelist = DataclassField(
        default_factory=AllowAllNamespaceWhitelist
    )


class DatasetMiddleware(AgentMiddleware[DatasetState, ContextT, ResponseT]):
    """Dataset middleware for dataset-backed agent experiments.

    Exposes default-graph operations (``add_triples``, ``serialize_dataset``,
    ``reset_dataset``) to the Research Agent and appends RDF-modeling guidance
    to the system prompt.

    When configured with a ``RestrictedNamespaceWhitelist``, the middleware also:

    - **Enforces** namespace constraints by rejecting URIs from non-whitelisted
      namespaces in ``add_triples``.
    - **Enumerates** allowed vocabularies in the system prompt.
    - **Suggests remediation** via Levenshtein-distance nearest matches for
      closed-vocabulary near-misses.
    """

    state_schema = DatasetState
    session: DatasetSession
    tools: Sequence[BaseTool]
    whitelist: NamespaceWhitelist
    _whitelist_confirmed: MutableSet[URIRef]

    def __init__(self, config: DatasetMiddlewareConfig | None = None) -> None:
        self.config = config or DatasetMiddlewareConfig()
        self.session = DatasetSession(_dataset=Dataset())
        self.tools = self._build_tools()
        self.whitelist = self.config.namespace_whitelist
        self._whitelist_confirmed = set()

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

    def _build_system_prompt(self) -> str:
        """Assemble the full middleware system prompt, including enumeration if active."""
        prompt = DATASET_SYSTEM_PROMPT
        enumeration = self.whitelist.enumerate_prompt()
        if enumeration is not None:
            prompt = prompt + "\n" + enumeration
        return prompt

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
                self._build_system_prompt(),
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
                self._build_system_prompt(),
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

        try:
            return handler(request)
        except WhitelistViolation as e:
            return ToolMessage(
                content=_format_whitelist_violation_message(e.bad_term, e.result),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )

    def _should_check_whitelist_node(self, node: Node) -> TypeGuard[URIRef]:
        if isinstance(node, URIRef) and node not in self._whitelist_confirmed:
            return True
        return False

    def _should_check_whitelist(self, statement: Iterable[Node]) -> Sequence[URIRef]:
        return tuple(
            node for node in statement if self._should_check_whitelist_node(node)
        )

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
        given = 0
        with self.session._lock.gen_wlock():
            graph = self.session._dataset.default_graph
            before = len(graph)
            for triple in triples:
                given += 1
                for to_check in self._should_check_whitelist(triple):
                    result = self.whitelist.find_term(to_check)
                    if result.allowed:
                        self._whitelist_confirmed.add(to_check)
                    else:
                        raise WhitelistViolation(to_check, result)

                graph.add(triple)
            updated = len(graph) - before

        preexisting = given - updated

        message = f"{updated} of {given} triples added."
        if preexisting > 0:
            message += f" {preexisting} of {given} triples already existed."

        return MutationResponse(
            updated=NonNegativeInt(updated),
            message=message,
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
            description=LIST_TRIPLES_TOOL_DESCRIPTION,
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
            description=ADD_TRIPLES_TOOL_DESCRIPTION,
        )
        def add_triples_tool(triples: tuple[N3Triple, ...]) -> MutationResponse:
            logger.debug("Adding triples")
            return self.add_triples(triple.as_rdflib for triple in triples)

        @tool(
            "remove_triples",
            args_schema=TripleBatchRequest,
            description=REMOVE_TRIPLES_TOOL_DESCRIPTION,
        )
        def remove_triples_tool(triples: tuple[N3Triple, ...]) -> MutationResponse:
            logger.debug("Removing triples")
            return self.remove_triples(triple.as_rdflib for triple in triples)

        @tool(
            "serialize_dataset",
            args_schema=SerializeRequest,
            description=SERIALIZE_DATASET_TOOL_DESCRIPTION,
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


class WhitelistViolation(Exception):
    """Exception raised when a term is rejected by the whitelist."""

    def __init__(self, bad_term: URIRef, result: WhitelistResult) -> None:
        self.bad_term = bad_term
        self.result = result
        super().__init__(f"Whitelist violation: {bad_term}")
