import logging
from collections.abc import Awaitable, Callable, Iterable, MutableSet, Sequence
from dataclasses import dataclass
from json import dumps as json_dumps
from json import loads as json_loads
from typing import Any, Final, Literal, TypeGuard, override

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
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command
from pydantic import NonNegativeInt
from rdflib import BNode, Node, URIRef
from rdflib_reasoning.axiom.common import Triple

from ._message_heuristics import (
    completed_turtle_answer_represents_empty_graph,
    has_recent_guard_reminder,
    latest_ai_message,
    looks_like_completed_answer,
    looks_like_plan_intent,
    looks_like_recovery_intent,
    summarize_message_tail,
)
from .continuation_state import ContinuationMode
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
    RestrictedNamespaceWhitelist,
    WhitelistResult,
)
from .shared_services import DatasetRuntime, DatasetSession, RunTermTelemetry
from .vocabulary_configuration import VocabularyContext

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


_POPULATE_DATASET_REMINDER_PREFIX: Final[str] = "[rdflib_reasoning-dataset]"
_POPULATE_DATASET_REMINDER: Final[str] = (
    f"{_POPULATE_DATASET_REMINDER_PREFIX} The dataset is still empty. If this task "
    "requires grounded RDF extraction, emit the needed dataset tool call now. "
    "Return a completed answer without adding triples only if an empty graph is "
    "actually the correct result."
)
_OVERLAPPING_GUARD_REMINDER_PREFIXES: Final[tuple[str, ...]] = (
    "[rdflib_reasoning-continuation]",
    "[rdflib_reasoning-recovery]",
    "[rdflib_reasoning-finalize]",
    "[rdflib_reasoning-tool-transcript]",
)


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
- You SHOULD prefer representing explicit source claims over designing additional ontology structure that the source does not require.
- When transforming unstructured content into RDF, you SHOULD prefer controlled vocabularies when they fit the source material and task.
- You SHOULD reuse established terms when they fit your intended meaning, and mint new local terms only when they are genuinely needed for a faithful representation.
- You SHOULD prefer the least ontology invention that still captures the grounded content.
- If you mint IRIs and the user does not specify a base IRI, you SHOULD use <urn:example:> as the default base for minted IRIs.
- When presenting RDF to the user or serializing the knowledge base for inspection, you SHOULD prefer Turtle unless the user requests a different RDF serialization.
- SHOULD NOT mint IRIs if convention dictates that they be blank nodes (e.g., OWL 2 Class Restrictions).
- You SHOULD prefer a minted IRI over a blank node when there is an authorative IRI base for that resource.
- When minting an IRI to represent a Class, Datatype, or Property, you MUST assign it a `rdfs:label` and define it using `rdfs:comment`.
- When minting a new local IRI for a Class or Datatype, the local name SHOULD be singular and use `PascalCase`, for example `ProjectReport`, `FieldObservation`, or `QualityRating`.
- When minting a new local IRI for a Property, the local name SHOULD use `camelCase`, for example `hasInventoryCode`, `recordedAtFacility`, or `reviewStatus`.

### Knowledge Base Tools

- `list_triples`: inspect the current triples in the knowledge base
- `add_triples`: Add triples to the knowledge base (idempotent)
- `remove_triples`: remove exact triples from the knowledge base
- `serialize_dataset`: render the current knowledge base as RDF text
- `reset_dataset`: clear the entire knowledge base
- `new_blank_node`: create an anonymous resource without an IRI

#### Knowledge Base Tool Guidance

- Prefer `add_triples` and `remove_triples` to correct triples/facts rather than using `reset_dataset`.
- When providing IRIs to dataset tools, you MAY use either canonical N3 form like `<urn:example:ProjectReport>` or a bare RFC 3987 IRI like `urn:example:ProjectReport`.
  - The middleware serializes IRIs back in canonical N3 form.
- When a predicate expects text such as `rdfs:label` or `rdfs:comment`, the object MUST be an RDF literal such as `"Project report"` or `"A short human-readable description."`.
- You SHOULD NOT include the same triple in multiple `add_triples` calls; `add_triples` is idempotent.
- If an `add_triples` call fails validation, you SHOULD correct the invalid triple or triples before retrying.
  - You MAY retry with a smaller `add_triples` call if that helps isolate which triple is invalid.
- If an `add_triples` response sets `no_action_needed=true`, you MUST NOT submit any of those same triples again in this run,
  whether in the same batch, a reordered batch, or a smaller subset.
  - After such a response, you SHOULD continue with different triples that are still missing, inspect the dataset once if you are unsure what remains missing, or return your final answer if the dataset already reflects the RDF you intend to present.
- If a `remove_triples` response sets `no_action_needed=true`, you MUST NOT submit any of those same triples again in this run,
  whether in the same batch, a reordered batch, or a smaller subset.
  - After such a response, you SHOULD continue with a different specific dataset change, inspect the dataset once if you are unsure whether the correction is already reflected, or return your final answer if the dataset already reflects the RDF you intend to present.
- If an `add_triples` call is rejected as misuse or because a term violates vocabulary/policy constraints, you SHOULD follow the remediation advice in the tool response rather than retrying automatically.
- If you have already added the triples needed for a modeling step, you SHOULD NOT restate the same intention and repeat overlapping `add_triples` calls.
  - Move to the next missing concept, inspect the dataset once if needed, or return your final answer.
- `serialize_dataset` is mainly a checkpoint or inspection tool, not a drafting loop.
  - You SHOULD usually call `serialize_dataset` only when the graph is substantially complete or when one explicit inspection pass is needed to resolve uncertainty.
  - After calling `serialize_dataset`, you SHOULD usually either return your final answer immediately or make a specific dataset change that the serialization revealed.
  - You SHOULD NOT call `serialize_dataset` repeatedly without first changing the dataset or deciding to return your final answer.
  - `serialize_dataset` does NOT add data, infer data, or improve data; changing serialization formats cannot improve an unchanged dataset.
  - If a `serialize_dataset` response sets `is_empty=true`, the default graph is empty; changing formats will not add data, so your next step SHOULD be to add triples or return an explicitly empty-graph answer.
  - If `serialize_dataset` reports that the dataset is unchanged since the previous serialization in that format, you MUST NOT call `serialize_dataset` again until you have changed the dataset.
  - After such a response, you MUST either return your final answer immediately or make one or more specific dataset changes before using `serialize_dataset` again.
- Errors like `Value error, Could not parse RDF term` indicate that your RDF term syntax is incorrect.
  - If the value is meant to be an IRI, first check whether it should be wrapped as `<...>` or corrected to a valid bare RFC 3987 IRI.
  - If the value is meant to be plain text, encode it as an RDF literal such as `"Project report"` or `"A short human-readable description."`.
- Mutating knowledge base tool effects are persistant, cumulative, and idempotent.
- You MUST keep each `add_triples` call small enough to recover from a single validation error.
  - You SHOULD prefer one subject per `add_triples` call.
  - You SHOULD NOT mix many unrelated subjects in one `add_triples` call.

### Guidance for Modeling Facts

- You MAY incrementally build your dataset using multiple `add_triples` calls.
  - You SHOULD prefer that each `add_triples` call completely describes one single concept or entity.

The following is an example of something that completely describes one single concept or entity.
The subject of this example is a minted class called `ProjectReport`, while the
supporting superclass reuses a standard vocabulary term.

```text/turtle
@prefix schema: <https://schema.org/> .

<urn:example:ProjectReport> a rdfs:Class ;
    rdfs:label "Project report" ;
    rdfs:comment "A written report that summarizes project work." ;
    rdfs:subClassOf schema:CreativeWork .
```

- `<urn:example:ProjectReport> a rdfs:Class` is syntactic sugar for `<urn:example:ProjectReport> rdf:type rdfs:Class`.
- For `rdfs:label`, the object SHOULD usually be a short string literal such as `"Project report"`.
- For `rdfs:comment`, the object SHOULD usually be a descriptive string literal such as `"A written report that summarizes project work."`.

- Model facts in an atemporal, stable way when possible rather than storing transient phrasing as timeless truth.
- When asserting facts into the knowledge base, you SHOULD keep them grounded in the provided content unless the user explicitly asks for inference, extrapolation, or hypothesis generation.
- You SHOULD NOT assert uncertain facts as settled triples.
- You SHOULD avoid introducing helper abstractions, organizing concepts, or auxiliary relations unless they are genuinely needed to represent explicit grounded claims.

### Usage of IRIs and Blank Nodes

- When transforming unstructured content into RDF, you SHOULD prefer controlled vocabularies when they fit the source material and task.
- If you mint IRIs and the user does not specify a base IRI, you SHOULD use <urn:example:> as the default base for minted IRIs.
- The fact that a local base IRI is available does NOT by itself justify minting a new local term.
- You SHOULD NOT mint IRIs if convention dictates that they be blank nodes (e.g., OWL 2 Class Restrictions).
- You SHOULD prefer a minted IRI over a blank node when there is an authorative IRI base for that resource.
- When minting an IRI to represent a Class, Datatype, or Property, you MUST assign it a `rdfs:label` and define it using `rdfs:comment`.
- When minting a new local IRI for a Class or Datatype, the local name SHOULD be singular and use `PascalCase`, for example `ProjectReport`, `FieldObservation`, or `QualityRating`.
- When minting a new local IRI for a Property, the local name SHOULD use `camelCase`, for example `hasInventoryCode`, `recordedAtFacility`, or `reviewStatus`.
- If the current dataset already reflects the RDF you intend to present, you SHOULD serialize it at most once and then return your final answer rather than repeatedly re-serializing it.
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
IRI inputs MAY be given either in canonical N3 form like `<urn:example:ProjectReport>` or
as bare RFC 3987 IRIs like `urn:example:ProjectReport`.
Literal text MUST be encoded as RDF literals like `"Project report"` or
`"A short human-readable description."`.
You SHOULD keep each call small and recoverable.
You SHOULD prefer one subject per call.
If the response sets `no_action_needed=true`, the requested triples are already
present and you MUST NOT submit any of those same triples again in this run,
whether in the same batch, a reordered batch, or a smaller subset.
After such a response, you SHOULD continue with different triples that are
still missing, inspect the dataset once if you are unsure what remains
missing, or return your final answer if the dataset already reflects the RDF
you intend to present.

Example arguments:
- `{"triples": [{"subject": "<urn:example:ProjectReport>", "predicate": "<http://www.w3.org/2000/01/rdf-schema#label>", "object": "\"Project report\""}]}`
- `{"triples": [{"subject": "<urn:example:ProjectReport>", "predicate": "<http://www.w3.org/2000/01/rdf-schema#comment>", "object": "\"A written report that summarizes project work.\""}]}`
- `{"triples": [{"subject": "urn:example:ProjectReport", "predicate": "http://www.w3.org/2000/01/rdf-schema#subClassOf", "object": "https://schema.org/CreativeWork"}]}`
"""

REMOVE_TRIPLES_TOOL_DESCRIPTION: Final[
    str
] = """Remove one or more exact RDF triples from the default RDF graph knowledge base.

Pass `triples` as a top-level argument containing the exact triples to remove.
IRI inputs MAY be given either in canonical N3 form like `<urn:example:ProjectReport>` or
as bare RFC 3987 IRIs like `urn:example:ProjectReport`.
Literal text MUST be encoded as RDF literals like `"Project report"` or
`"A short human-readable description."`.
If the response sets `no_action_needed=true`, the requested triples are already
absent and you MUST NOT submit any of those same triples again in this run,
whether in the same batch, a reordered batch, or a smaller subset.
After such a response, you SHOULD continue with a different specific dataset
change, inspect the dataset once if you are unsure whether the correction is
already reflected, or return your final answer if the dataset already reflects
the RDF you intend to present.

Example arguments:
- `{"triples": [{"subject": "<urn:example:ProjectReport>", "predicate": "<http://www.w3.org/2000/01/rdf-schema#label>", "object": "\"Project report\""}]}`
- `{"triples": [{"subject": "urn:example:ProjectReport", "predicate": "http://www.w3.org/2000/01/rdf-schema#comment", "object": "\"A written report that summarizes project work.\""}]}`
"""

SERIALIZE_DATASET_TOOL_DESCRIPTION: Final[
    str
] = """Serialize the current default-graph knowledge base as RDF text.

Pass `format` as a top-level argument when you need a specific RDF serialization.
Use this mainly as a checkpoint when the graph is substantially complete or when
one inspection pass is needed to decide on a specific correction.
This tool does NOT modify, normalize, or improve the dataset; it only renders
the current graph state as RDF text.
Changing serialization formats cannot improve an unchanged dataset or add
missing triples.
If the response sets `is_empty=true`, the default graph is empty and another
serialization format will still be empty until you change the dataset.
If the serialization already reflects the graph you intend to present, the next
step SHOULD usually be to return your final answer.
If the serialization reveals a problem, the next step SHOULD usually be a
dataset change rather than another identical serialization request.
If `serialize_dataset` reports that the dataset is unchanged since the previous
serialization in that format, you MUST NOT call `serialize_dataset` again until
you have changed the dataset.
After such a response, you MUST either return your final answer immediately or
make one or more specific dataset changes before using `serialize_dataset`
again.
You SHOULD NOT repeatedly call `serialize_dataset` without first changing the
dataset or deciding to return your final answer.

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

REPEATED_ADD_TRIPLES_NOOP_MESSAGE: Final[
    str
] = """Misuse: repeated `add_triples` no-op was rejected.

Your previous `add_triples` call with these same triples was already satisfied.

You MUST NOT retry the same `add_triples` call unchanged. Either add different triples,
inspect the current dataset state, or return your final answer.
"""

REPEATED_REMOVE_TRIPLES_NOOP_MESSAGE: Final[
    str
] = """Misuse: repeated `remove_triples` no-op was rejected.

Your previous `remove_triples` call with these same triples was already satisfied.

You MUST NOT retry the same `remove_triples` call unchanged. Either make a
different specific dataset change, inspect the current dataset state, or return
your final answer.
"""


@dataclass(frozen=True, slots=True)
class DatasetMiddlewareConfig:
    """Configuration for the dataset middleware surface.

    Attributes:
        vocabulary_context: Shared runtime vocabulary policy and index
            configuration for dataset-backed middleware.
    """

    vocabulary_context: VocabularyContext
    runtime: DatasetRuntime | None = None
    run_term_telemetry: RunTermTelemetry | None = None


class DatasetMiddleware(AgentMiddleware[DatasetState, ContextT, ResponseT]):
    """Dataset middleware for dataset-backed agent experiments.

    Exposes default-graph operations (``add_triples``, ``serialize_dataset``,
    ``reset_dataset``) to the Research Agent and appends RDF-modeling guidance
    to the system prompt.

    When configured with a ``VocabularyContext``, the middleware also:

    - **Enforces** namespace constraints by rejecting URIs from non-whitelisted
      namespaces in ``add_triples``.
    - **Enumerates** allowed vocabularies in the system prompt.
    - **Suggests remediation** via Levenshtein-distance nearest matches for
      closed-vocabulary near-misses.
    """

    state_schema = DatasetState
    vocabulary_context: VocabularyContext
    runtime: DatasetRuntime
    tools: Sequence[BaseTool]
    whitelist: RestrictedNamespaceWhitelist
    run_term_telemetry: RunTermTelemetry
    _whitelist_confirmed: MutableSet[URIRef]
    _last_add_triples_noop_signature: str | None
    _last_remove_triples_noop_signature: str | None
    _dataset_revision: int
    _last_serialize_signature: tuple[int, str] | None

    def __init__(self, config: DatasetMiddlewareConfig) -> None:
        self.config = config
        self.vocabulary_context = self.config.vocabulary_context
        self.runtime = self.config.runtime or DatasetRuntime()
        self.whitelist = self.vocabulary_context.whitelist
        self.run_term_telemetry = self.config.run_term_telemetry or RunTermTelemetry()
        self.tools = self._build_tools()
        self._whitelist_confirmed = set()
        self._last_add_triples_noop_signature = None
        self._last_remove_triples_noop_signature = None
        self._dataset_revision = 0
        self._last_serialize_signature = None

    @property
    def session(self) -> DatasetSession:
        return self.runtime.session

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
        runtime: Any,
    ) -> None:
        """Dataset session state is owned by the middleware itself."""
        del state, runtime
        return None

    @override
    def after_model(  # type: ignore[override]  # after_model's type hints are dated
        self, state: DatasetState, runtime: Any
    ) -> dict[str, Any] | Command[Any] | None:
        # We don't need to step in if the dataset is populated.
        with self.session._lock.gen_rlock():
            dataset_is_empty = len(self.session._dataset) == 0

        if not dataset_is_empty:
            return None

        # Otherwise, we should only step in if the agent is calling it quits;
        # to prove that's happening, we need to look at its current output.
        messages = state.get("messages")
        if not isinstance(messages, list) or not messages:
            return None

        last_ai_message = latest_ai_message(messages)
        if last_ai_message is None or last_ai_message.tool_calls:
            return None

        content = (
            last_ai_message.text
            if isinstance(last_ai_message.text, str)
            else str(last_ai_message.content)
        )
        if not content:
            return None

        completed_answer = looks_like_completed_answer(content)
        if completed_answer:
            # Special case where the agent doesn't need reminding.
            if completed_turtle_answer_represents_empty_graph(content):
                logger.debug(
                    "Skipping empty-dataset reminder because the latest AI message already represents an explicitly empty graph; last_ai_message_id=%s dataset_is_empty=%s completed_answer=%s recent_messages=%s",
                    getattr(last_ai_message, "id", None),
                    dataset_is_empty,
                    completed_answer,
                    summarize_message_tail(messages),
                )
                return None

        if looks_like_plan_intent(content) or looks_like_recovery_intent(content):
            logger.warning(
                "Deferring empty-dataset reminder because the latest AI output looks like unfinished continuation content and ContinuationGuardMiddleware should own the re-prompt for this assistant turn; last_ai_message_id=%s dataset_is_empty=%s completed_answer=%s recent_messages=%s",
                getattr(last_ai_message, "id", None),
                dataset_is_empty,
                completed_answer,
                summarize_message_tail(messages),
            )
            return None

        overlapping_guard_prefix = next(
            (
                prefix
                for prefix in _OVERLAPPING_GUARD_REMINDER_PREFIXES
                if has_recent_guard_reminder(messages, prefix)
            ),
            None,
        )
        if overlapping_guard_prefix is not None:
            logger.warning(
                "Deferring empty-dataset reminder because another recovery-oriented middleware already injected a reminder for the latest AI turn; last_ai_message_id=%s dataset_is_empty=%s completed_answer=%s overlapping_reminder_prefix=%s recent_messages=%s",
                getattr(last_ai_message, "id", None),
                dataset_is_empty,
                completed_answer,
                overlapping_guard_prefix,
                summarize_message_tail(messages),
            )
            return None

        if has_recent_guard_reminder(messages, _POPULATE_DATASET_REMINDER_PREFIX):
            logger.debug(
                "Suppressing empty-dataset reminder because it was already injected for the latest AI response; last_ai_message_id=%s dataset_is_empty=%s completed_answer=%s recent_messages=%s",
                getattr(last_ai_message, "id", None),
                dataset_is_empty,
                completed_answer,
                summarize_message_tail(messages),
            )
            return None

        logger.debug(
            "Injecting empty-dataset reminder because the model stopped without populating the dataset; last_ai_message_id=%s dataset_is_empty=%s completed_answer=%s recent_messages=%s",
            getattr(last_ai_message, "id", None),
            dataset_is_empty,
            completed_answer,
            summarize_message_tail(messages),
        )
        return Command(
            update={"messages": [HumanMessage(content=_POPULATE_DATASET_REMINDER)]},
            goto="model",
        )

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
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any] | Any],
    ) -> ToolMessage | Command[Any] | Any:
        """Reject invalid dataset tool usage before calling the wrapped tool."""
        tool_name = (
            request.tool.name if request.tool is not None else request.tool_call["name"]
        )
        tool_call_id = request.tool_call["id"]
        continuation_mode = self._continuation_mode_from_state(
            getattr(request, "state", None)
        )

        if continuation_mode == "stop_now":
            logger.debug(
                "continuation_mode=stop_now; delegating to tool handler without dataset "
                "policy Commands that could overwrite orchestration state"
            )
            return handler(request)

        if tool_name == "reset_dataset" and self._should_reject_reset_dataset(request):
            logger.debug("Rejecting reset_dataset misuse because the dataset is empty")
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
            logger.debug(
                "Rejecting new_blank_node misuse because %s unused blank nodes are already tracked",
                len(self.session._blank_nodes),
            )
            return ToolMessage(
                content=NEW_BLANK_NODE_MISUSE_MESSAGE.format(
                    existing=unused_blank_nodes
                ),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )

        if tool_name == "serialize_dataset":
            if continuation_mode == "finalize_only":
                logger.debug(
                    "Rejecting serialize_dataset because continuation_mode=finalize_only and the dataset must change before further serialization"
                )
                # Do not set continuation_mode here: the graph is already finalize_only, and
                # emitting it again can merge after ContinuationGuardMiddleware.after_model
                # sets stop_now in the same superstep, clobbering orchestration state.
                return Command(
                    update={
                        "messages": [
                            ToolMessage(
                                content=(
                                    "You are already in final-answer-only mode after a repeated "
                                    "`serialize_dataset` rejection. The dataset is unchanged, "
                                    "and changing serialization formats will not add data or "
                                    "improve the graph. Do not call `serialize_dataset` again "
                                    "until you have made one or more specific dataset changes. "
                                    "Return your final answer now, or make the missing dataset "
                                    "change before any further serialization."
                                ),
                                name=tool_name,
                                tool_call_id=tool_call_id,
                                status="error",
                            )
                        ],
                    }
                )
            serialize_signature = self._serialize_tool_call_signature(request)
            if (
                serialize_signature is not None
                and serialize_signature == self._last_serialize_signature
            ):
                logger.debug(
                    "Rejecting repeated serialize_dataset retry because the dataset has not changed since the previous serialization in the same format"
                )
                return Command(
                    update={
                        "messages": [
                            ToolMessage(
                                content=(
                                    "The dataset has not changed since the previous "
                                    "`serialize_dataset` call in this format. Re-serializing will "
                                    "not reformat or improve the graph. Use the previous "
                                    "successful serialization as your final answer if it "
                                    "already reflects the graph you intend to present. Do "
                                    "not call `serialize_dataset` again until you have "
                                    "changed the dataset. Return your final answer now, or "
                                    "make one or more specific dataset changes before any further "
                                    "serialization."
                                ),
                                name=tool_name,
                                tool_call_id=tool_call_id,
                                status="error",
                            )
                        ],
                        "continuation_mode": "finalize_only",
                    }
                )
        else:
            serialize_signature = None

        graph_size_before: int | None = None
        if tool_name in {"add_triples", "remove_triples", "reset_dataset"}:
            with self.session._lock.gen_rlock():
                graph_size_before = len(self.session._dataset.default_graph)
        graph_size_after: int | None = None

        add_triples_signature = None
        remove_triples_signature = None
        if tool_name == "add_triples":
            add_triples_signature = self._tool_call_signature(request)
            if (
                add_triples_signature is not None
                and add_triples_signature == self._last_add_triples_noop_signature
            ):
                logger.debug(
                    "Rejecting repeated add_triples retry because the previous identical call was already satisfied"
                )
                return ToolMessage(
                    content=REPEATED_ADD_TRIPLES_NOOP_MESSAGE,
                    name=tool_name,
                    tool_call_id=tool_call_id,
                    status="error",
                )
        elif tool_name == "remove_triples":
            remove_triples_signature = self._tool_call_signature(request)
            if (
                remove_triples_signature is not None
                and remove_triples_signature == self._last_remove_triples_noop_signature
            ):
                logger.debug(
                    "Rejecting repeated remove_triples retry because the previous identical call was already satisfied"
                )
                return ToolMessage(
                    content=REPEATED_REMOVE_TRIPLES_NOOP_MESSAGE,
                    name=tool_name,
                    tool_call_id=tool_call_id,
                    status="error",
                )

        try:
            result = handler(request)
        except WhitelistViolation as e:
            logger.debug(
                "Converting whitelist violation for tool %s and term %s into a tool-facing error",
                tool_name,
                e.bad_term,
            )
            return ToolMessage(
                content=_format_whitelist_violation_message(e.bad_term, e.result),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )
        if graph_size_before is not None:
            with self.session._lock.gen_rlock():
                graph_size_after = len(self.session._dataset.default_graph)
        self._update_repeated_call_guard(
            tool_name,
            result,
            add_triples_signature=add_triples_signature,
            remove_triples_signature=remove_triples_signature,
            serialize_signature=serialize_signature,
            graph_size_before=graph_size_before,
            graph_size_after=graph_size_after,
        )
        next_mode = self._continuation_mode_after_success(
            tool_name,
            continuation_mode=continuation_mode,
            graph_size_before=graph_size_before,
            graph_size_after=graph_size_after,
        )
        if next_mode is None:
            return result
        return self._with_continuation_mode(result, next_mode)

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
        del request
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

    def _tool_call_signature(self, request: ToolCallRequest) -> str | None:
        """Return a stable signature for the current tool call payload."""
        raw_args = request.tool_call.get("args")
        if raw_args is None:
            raw_args = request.tool_call.get("arguments")
        if raw_args is None:
            return None
        if isinstance(raw_args, str):
            try:
                parsed_args = json_loads(raw_args)
            except ValueError:
                return raw_args
            return json_dumps(parsed_args, sort_keys=True, default=str)
        return json_dumps(raw_args, sort_keys=True, default=str)

    def _serialize_tool_call_signature(
        self, request: ToolCallRequest
    ) -> tuple[int, str] | None:
        tool_call_signature = self._tool_call_signature(request)
        if tool_call_signature is None:
            return None
        return (self._dataset_revision, tool_call_signature)

    def _tool_result_is_error(self, result: ToolMessage | Any) -> bool:
        if isinstance(result, Command):
            update = result.update
            if not isinstance(update, dict):
                return False
            messages = update.get("messages")
            if isinstance(messages, list):
                return any(
                    isinstance(message, ToolMessage)
                    and getattr(message, "status", None) == "error"
                    for message in messages
                )
            return False
        return (
            isinstance(result, ToolMessage)
            and getattr(result, "status", None) == "error"
        )

    @staticmethod
    def _continuation_mode_from_state(state: Any) -> ContinuationMode:
        if isinstance(state, dict):
            mode = state.get("continuation_mode", "normal")
            if mode in {"normal", "finalize_only", "stop_now"}:
                return mode
        return "normal"

    @staticmethod
    def _with_continuation_mode(
        result: ToolMessage | Command[Any] | Any, continuation_mode: ContinuationMode
    ) -> ToolMessage | Command[Any] | Any:
        if isinstance(result, Command):
            update = dict(result.update or {})
            update["continuation_mode"] = continuation_mode
            return Command(
                graph=result.graph,
                update=update,
                resume=result.resume,
                goto=result.goto,
            )
        if isinstance(result, ToolMessage):
            return Command(
                update={
                    "messages": [result],
                    "continuation_mode": continuation_mode,
                }
            )
        return result

    @staticmethod
    def _continuation_mode_after_success(
        tool_name: str,
        *,
        continuation_mode: ContinuationMode,
        graph_size_before: int | None,
        graph_size_after: int | None,
    ) -> ContinuationMode | None:
        if continuation_mode == "normal":
            return None
        if (
            tool_name == "add_triples"
            and graph_size_before is not None
            and graph_size_after is not None
        ):
            if graph_size_after > graph_size_before:
                return "normal"
            return None
        if (
            tool_name in {"remove_triples", "reset_dataset"}
            and graph_size_before is not None
            and graph_size_after is not None
        ):
            if graph_size_after < graph_size_before:
                return "normal"
        return None

    def _update_repeated_call_guard(
        self,
        tool_name: str,
        result: ToolMessage | Any,
        *,
        add_triples_signature: str | None,
        remove_triples_signature: str | None,
        serialize_signature: tuple[int, str] | None,
        graph_size_before: int | None,
        graph_size_after: int | None,
    ) -> None:
        """Track repeated-call guard state from observable tool effects."""
        if self._tool_result_is_error(result):
            return

        if tool_name == "add_triples":
            if graph_size_before is None or graph_size_after is None:
                return
            if graph_size_after == graph_size_before:
                self._last_add_triples_noop_signature = add_triples_signature
            elif graph_size_after > graph_size_before:
                self._last_add_triples_noop_signature = None
                self._last_remove_triples_noop_signature = None
                self._dataset_revision += 1
                self._last_serialize_signature = None
            return
        if tool_name == "remove_triples":
            if graph_size_before is None or graph_size_after is None:
                return
            if graph_size_after == graph_size_before:
                self._last_remove_triples_noop_signature = remove_triples_signature
            elif graph_size_after < graph_size_before:
                self._dataset_revision += 1
                self._last_serialize_signature = None
                self._last_remove_triples_noop_signature = None
            self._last_add_triples_noop_signature = None
            return
        if tool_name == "reset_dataset":
            if graph_size_before is None or graph_size_after is None:
                return
            if graph_size_after < graph_size_before:
                self._dataset_revision += 1
                self._last_serialize_signature = None
            self._last_add_triples_noop_signature = None
            self._last_remove_triples_noop_signature = None
            return
        if tool_name == "serialize_dataset":
            self._last_serialize_signature = serialize_signature
            return
        if tool_name in {"remove_triples", "reset_dataset"}:
            self._last_add_triples_noop_signature = None

    def _replace_dataset(self) -> None:
        """Replace the middleware-owned dataset session."""
        self.runtime.replace_dataset()
        self._dataset_revision += 1
        self._last_serialize_signature = None

    def list_triples(self) -> tuple[Triple, ...]:
        """Return all exact triples currently present in the default graph."""
        with self.session._lock.gen_rlock():
            return tuple(
                self.session._dataset.default_graph.triples((None, None, None))
            )

    def add_triples(self, triples: Iterable[Triple]) -> MutationResponse:
        """Add exact triples to the default graph."""
        triples = tuple(triples)
        given = len(triples)
        added_terms: list[URIRef] = []
        with self.session._lock.gen_wlock():
            graph = self.session._dataset.default_graph
            before = len(graph)
            for triple in triples:
                for to_check in self._should_check_whitelist(triple):
                    result = self.whitelist.find_term(to_check)
                    if result.allowed:
                        self._whitelist_confirmed.add(to_check)
                    else:
                        raise WhitelistViolation(to_check, result)

                triple_is_new = triple not in graph
                graph.add(triple)
                if triple_is_new:
                    added_terms.extend(
                        node for node in triple if isinstance(node, URIRef)
                    )
            updated = len(graph) - before

        preexisting = given - updated
        if added_terms:
            self.run_term_telemetry.record_asserted_terms(added_terms)

        no_action_needed = given > 0 and updated == 0 and preexisting == given
        if no_action_needed:
            message = (
                f"No action was needed. All {given} requested triples were already "
                "present in the default graph. Do not retry this same `add_triples` "
                "call unless you change the triples."
            )
        else:
            message = f"{updated} of {given} triples added."
            if preexisting > 0:
                message += f" {preexisting} of {given} triples were already present."

        return MutationResponse(
            requested=NonNegativeInt(given),
            updated=NonNegativeInt(updated),
            unchanged=NonNegativeInt(preexisting),
            no_action_needed=no_action_needed,
            message=message,
        )

    def remove_triples(self, triples: Iterable[Triple]) -> MutationResponse:
        """Remove exact triples from the default graph."""
        triples = tuple(triples)
        given = len(triples)
        with self.session._lock.gen_wlock():
            graph = self.session._dataset.default_graph
            before = len(graph)
            for triple in triples:
                graph.remove(triple)
            updated = before - len(graph)
        unchanged = given - updated
        no_action_needed = given > 0 and updated == 0 and unchanged == given
        if no_action_needed:
            message = (
                f"No action was needed. All {given} requested triples were already "
                "absent from the default graph. Do not retry this same "
                "`remove_triples` call unless you change the triples."
            )
        else:
            message = "Triples removed from the default graph."
        return MutationResponse(
            requested=NonNegativeInt(given),
            updated=NonNegativeInt(updated),
            unchanged=NonNegativeInt(unchanged),
            no_action_needed=no_action_needed,
            message=message,
        )

    def reset_dataset(self) -> MutationResponse:
        """Reset the middleware-owned dataset session."""
        updated = self.runtime.default_graph_size()
        self.runtime.replace_dataset()
        no_action_needed = updated == 0
        return MutationResponse(
            requested=NonNegativeInt(updated),
            updated=NonNegativeInt(updated),
            unchanged=NonNegativeInt(0),
            no_action_needed=no_action_needed,
            message=(
                "No action was needed. The dataset was already empty."
                if no_action_needed
                else "Dataset state reset."
            ),
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
            triples = tuple(
                N3Triple.from_rdflib(triple) for triple in self.list_triples()
            )
            logger.debug("Listing %s triples from the default graph", len(triples))
            return TripleListResponse(triples=triples)

        @tool(
            "add_triples",
            args_schema=TripleBatchRequest,
            description=ADD_TRIPLES_TOOL_DESCRIPTION,
        )
        def add_triples_tool(triples: tuple[N3Triple, ...]) -> MutationResponse:
            logger.debug("Adding %s triples to the default graph", len(triples))
            return self.add_triples(triple.as_rdflib for triple in triples)

        @tool(
            "remove_triples",
            args_schema=TripleBatchRequest,
            description=REMOVE_TRIPLES_TOOL_DESCRIPTION,
        )
        def remove_triples_tool(triples: tuple[N3Triple, ...]) -> MutationResponse:
            logger.debug("Removing %s triples from the default graph", len(triples))
            return self.remove_triples(triple.as_rdflib for triple in triples)

        @tool(
            "serialize_dataset",
            args_schema=SerializeRequest,
            description=SERIALIZE_DATASET_TOOL_DESCRIPTION,
        )
        def serialize_dataset_tool(
            format: Literal["trig", "turtle", "nt", "n3"] = "trig",
        ) -> SerializationResponse:
            with self.session._lock.gen_rlock():
                default_graph = self.session._dataset.default_graph
                triple_count = len(default_graph)
                serialized = default_graph.serialize(format=format)
            if isinstance(serialized, bytes):
                serialized = serialized.decode("utf-8")
            is_empty = triple_count == 0
            message = (
                "The default graph is empty. Changing serialization formats will not add "
                "data to an unchanged dataset."
                if is_empty
                else f"Serialized the current default graph containing {triple_count} triples."
            )
            logger.debug(
                "Serializing dataset as %s with %s triples in the default graph",
                format,
                triple_count,
            )
            return SerializationResponse(
                format=format,
                content=serialized,
                default_graph_triple_count=triple_count,
                is_empty=is_empty,
                message=message,
            )

        @tool("reset_dataset", description=RESET_DATASET_TOOL_DESCRIPTION)
        def reset_dataset_tool() -> MutationResponse:
            with self.session._lock.gen_rlock():
                triple_count = len(self.session._dataset.default_graph)
            logger.debug(
                "Resetting dataset with %s triples in the default graph", triple_count
            )
            return self.reset_dataset()

        @tool(
            "new_blank_node",
            description=CREATE_BLANK_NODE_TOOL_DESCRIPTION,
        )
        def new_blank_node_tool() -> NewResourceNodeResponse:
            resource = BNode()
            with self.session._lock.gen_wlock():
                self.session._blank_nodes.add(resource)
                blank_node_count = len(self.session._blank_nodes)
            logger.debug(
                "Creating new blank node; %s tracked blank nodes now available",
                blank_node_count,
            )
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
