import logging
from collections.abc import Awaitable, Callable, MutableSet, Sequence, Set
from dataclasses import dataclass
from json import dumps as json_dumps
from json import loads as json_loads
from typing import Any, Final, Literal, override

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
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt
from rdflib import RDFS, Graph, IdentifiedNode, URIRef
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.middleware.dataset_middleware import (
    WhitelistViolation,
    _format_whitelist_violation_message,
)
from rdflib_reasoning.middleware.dataset_model import N3IRIRef, SerializationResponse
from rdflib_reasoning.middleware.dataset_state import DatasetState
from rdflib_reasoning.middleware.namespaces.spec_index import (
    RDFVocabulary,
    VocabularyTerm,
)
from rdflib_reasoning.middleware.shared_services import RunTermTelemetry
from rdflib_reasoning.middleware.vocabulary_configuration import VocabularyContext

logger = logging.getLogger(__name__)

_VOCABULARY_SYSTEM_PROMPT: Final[str] = """## RDF Vocabulary Guidance

You MUST invoke the `list_vocabularies` tool ONCE, inspect the available indexed
vocabularies and see if any of them are relevant to your task.

You have FAILED in your task if you have not invoked the `list_vocabularies`
tool once.

After you have begun your task, use the vocabulary tools only to help choose
established RDF terms when you are uncertain whether a standard term fits your
intended meaning.

Default workflow:
- If you already know a core RDF/RDFS/OWL term is appropriate, use it and continue.
- If you know which vocabulary you want, use `list_terms` to scan candidate terms.
- If you already have a candidate term in mind, use `inspect_term`.
- Use `list_vocabularies` only when you do not yet know which indexed vocabulary to inspect.

Decision policy:
- Prefer one quick inspection over extended self-discussion.
- Do not keep re-checking the same term once `inspect_term` has answered your question.
- Do not repeat the same `inspect_term` call unchanged
- Do not repeat the same `list_terms` call unchanged; change the
  vocabulary, filter, offset, or limit if you still need different candidates.
- If `list_terms` gives you a relevant candidate, move to `inspect_term` or
  continue modeling instead of widening the search reflexively.
- If inspection does not quickly reveal a fitting standard term, mint a local term
  only when it is genuinely needed for a faithful representation, document it,
  and continue.
- Prefer representing explicit source claims over inventing additional ontology
  structure or helper relations that the source does not require.
- Do not assume a term's meaning from its local name alone when you are unsure.
- Do not pause to inspect vocabulary terms that you already know well enough to use correctly.
- You MAY use the following core terms without inspection when they are clearly appropriate:
  `rdf:type`, `rdfs:label`, `rdfs:comment`.
- Before the first use of another standard term, you SHOULD use `inspect_term`
  when that term is semantically important to your modeling decision.
  - Terms such as `rdfs:Class`, `rdfs:subClassOf`, and `owl:Class` are often
    modeling-significant rather than mere bookkeeping.
- When choosing between minting a local term or reusing a standard indexed term,
  you SHOULD inspect at least one candidate indexed term first.

### Indexed Vocabulary Tools

- `list_vocabularies`: discover which vocabularies are indexed
- `list_terms`: scan candidate indexed terms within one vocabulary
- `inspect_term`: inspect one indexed term in a compact form, optionally including source RDF
"""

LIST_VOCABULARIES_TOOL_DESCRIPTION: Final[
    str
] = """List the RDF vocabularies indexed by this middleware.

Use this tool when you do not know which vocabularies are indexed and you want to discover them.

Call this tool with no arguments.
"""

LIST_TERMS_TOOL_DESCRIPTION: Final[
    str
] = """List candidate indexed terms from one vocabulary.

Use this when you know the vocabulary but want to scan available classes,
properties, individuals, or datatypes before choosing one.

The vocabulary index is static for this run. You MUST NOT repeat the same
`list_terms` call unchanged and expect a different result. If you still need
different candidates, change `term_type`, `offset`, or `limit`.

Arguments:
- `vocabulary`: vocabulary namespace IRI
- `term_type`: optional filter (`class`, `property`, `individual`, `datatype`)
- `offset`: number of matching terms to skip before returning results
- `limit`: maximum number of terms to return

Example arguments:
- `{"vocabulary": "<http://www.w3.org/2000/01/rdf-schema#>", "term_type": "class", "limit": 25}`
- `{"vocabulary": "<http://www.w3.org/2002/07/owl#>", "term_type": "property", "offset": 10, "limit": 10}`
"""

INSPECT_TERM_TOOL_DESCRIPTION: Final[str] = """Inspect one indexed RDF term.

Use this when you already have a candidate term and want to confirm whether it
fits your intended meaning before using it.

By default this returns a compact normalized summary. Set
`include_source_rdf=true` only when you need the original RDF description for
finer detail.

The vocabulary index is static for this run. You MUST NOT repeat the same
`inspect_term` call unchanged and expect new information. After one inspection,
either use the term, inspect a different candidate, or mint a local term if no
indexed term fits.

Arguments:
- `term`: indexed term IRI to inspect
- `include_source_rdf`: include Turtle from the source vocabulary when needed

Example arguments:
- `{"term": "<http://www.w3.org/2000/01/rdf-schema#Class>"}`
- `{"term": "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>", "include_source_rdf": true}`
"""

_TERM_TYPE_TO_COLLECTION: Final[dict[str, str]] = {
    "class": "classes",
    "datatype": "datatypes",
    "individual": "individuals",
    "property": "properties",
}


class VocabularySummary(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    namespace: N3IRIRef = Field(
        description="Namespace IRI of the indexed vocabulary.",
        examples=[
            "<http://www.w3.org/1999/02/22-rdf-syntax-ns#>",
            "http://www.w3.org/2000/01/rdf-schema#",
        ],
    )
    label: str = Field(
        description="Short human-readable label for the indexed vocabulary.",
        examples=["RDF", "RDFS", "PROV-O", "FOAF"],
    )
    description: str = Field(
        description="Short human-readable description of what the vocabulary is for.",
        examples=[
            "Core RDF data model terms for statements, lists, containers, and literal/datatype machinery.",
            "Provenance terms for entities, activities, agents, and qualified influence relationships.",
        ],
    )
    term_count: NonNegativeInt = Field(
        description="Number of indexed terms available from this vocabulary.",
        examples=[10, 60, 500],
    )


class VocabularyListResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    vocabularies: tuple[VocabularySummary, ...] = Field(
        description="Indexed vocabularies currently available through this middleware.",
        examples=[
            [
                {
                    "namespace": "<http://www.w3.org/1999/02/22-rdf-syntax-ns#>",
                    "label": "RDF",
                    "description": "Core RDF data model terms for statements, lists, containers, and literal/datatype machinery.",
                    "term_count": 7,
                },
                {
                    "namespace": "<http://www.w3.org/2000/01/rdf-schema#>",
                    "label": "RDFS",
                    "description": "Schema-level RDF terms for classes, properties, labels, comments, domain/range, and hierarchy modeling.",
                    "term_count": 13,
                },
                {
                    "namespace": "<http://www.w3.org/2002/07/owl#>",
                    "label": "OWL",
                    "description": "Ontology modeling and logical constraint terms for classes, restrictions, axioms, and richer property semantics.",
                    "term_count": 60,
                },
            ],
            [
                {
                    "namespace": "<http://www.w3.org/ns/prov#>",
                    "label": "PROV-O",
                    "description": "Provenance terms for entities, activities, agents, and qualified influence relationships.",
                    "term_count": 80,
                }
            ],
        ],
    )


class ListTermsRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    vocabulary: N3IRIRef = Field(
        description=(
            "IRI of the indexed vocabulary to inspect. Keep this unchanged only "
            "when you are intentionally continuing the same scan."
        ),
        examples=[
            "<http://www.w3.org/1999/02/22-rdf-syntax-ns#>",
            "<http://www.w3.org/2000/01/rdf-schema#>",
            "<http://www.w3.org/2002/07/owl#>",
        ],
    )
    term_type: Literal["class", "datatype", "individual", "property"] | None = Field(
        default=None,
        description=(
            "Optional term type filter applied within the selected vocabulary. "
            "Change this when narrowing or broadening the scan."
        ),
        examples=["class", "property", None],
    )
    offset: NonNegativeInt = Field(
        default=0,
        description=(
            "Number of matching terms to skip before returning results. Increase "
            "this only when intentionally paginating to new candidates."
        ),
        examples=[0, 10, 25],
    )
    limit: NonNegativeInt = Field(
        default=50,
        description=(
            "Maximum number of terms to return. Keep this modest and increase it "
            "only when the current page does not contain enough candidates."
        ),
        examples=[10, 25, 50],
    )


class InspectTermRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    term: N3IRIRef = Field(
        description=(
            "IRI of the indexed vocabulary term to inspect. Do not resubmit the "
            "same unchanged term inspection in this run."
        ),
        examples=[
            "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>",
            "<http://www.w3.org/2000/01/rdf-schema#Class>",
            "<http://www.w3.org/2002/07/owl#Class>",
        ],
    )
    include_source_rdf: bool = Field(
        default=False,
        description=(
            "When true, include a Turtle rendering of the term's source "
            "description. Leave false unless you need finer detail than the "
            "compact summary provides."
        ),
        examples=[False, True],
    )


class TermInspectionResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    uri: N3IRIRef = Field(description="IRI of the indexed term.")
    label: str = Field(description="Human-readable label for the term.")
    definition: str = Field(description="Normalized definition text for the term.")
    termType: Literal["class", "datatype", "individual", "property"] = Field(
        description="Normalized kind of RDF vocabulary term."
    )
    vocabulary: N3IRIRef = Field(
        description="Namespace IRI of the vocabulary that defines this term."
    )
    superTerms: tuple[N3IRIRef, ...] = Field(
        default=(),
        description="Transitive superclasses or superproperties when available.",
    )
    domain: tuple[N3IRIRef, ...] = Field(
        default=(),
        description="`rdfs:domain` values declared for the term when available.",
    )
    range: tuple[N3IRIRef, ...] = Field(
        default=(),
        description="`rdfs:range` values declared for the term when available.",
    )
    source_rdf: SerializationResponse | None = Field(
        default=None,
        description="Optional Turtle serialization of the term's source description.",
    )


@dataclass(frozen=True, slots=True)
class RDFVocabularyMiddlewareConfig:
    """Configuration for the RDF vocabulary middleware surface."""

    vocabulary_context: VocabularyContext
    run_term_telemetry: RunTermTelemetry | None = None


class RDFVocabularyMiddleware(AgentMiddleware[DatasetState, ContextT, ResponseT]):
    vocabulary_context: VocabularyContext
    tools: Sequence[BaseTool]
    run_term_telemetry: RunTermTelemetry
    _previous_list_terms_signature: str | None
    _previous_inspect_term_signature: str | None

    def __init__(self, config: RDFVocabularyMiddlewareConfig) -> None:
        self.config = config
        self.vocabulary_context = self.config.vocabulary_context
        self.run_term_telemetry = self.config.run_term_telemetry or RunTermTelemetry()
        self.tools = self._build_tools()
        self._previous_list_terms_signature = None
        self._previous_inspect_term_signature = None

    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        """Append RDF vocabulary guidance to the system prompt before model execution."""
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                self._build_vocabulary_system_prompt(),
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
    ) -> ModelResponse[ResponseT]:
        """Append RDF vocabulary guidance to the system prompt before async model execution."""
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                self._build_vocabulary_system_prompt(),
            )
        )
        return await handler(request)

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        tool_name = (
            request.tool.name if request.tool is not None else request.tool_call["name"]
        )
        tool_call_id = request.tool_call["id"]
        tool_signature = self._tool_call_signature(request)

        if (
            tool_name == "list_terms"
            and tool_signature is not None
            and tool_signature == self._previous_list_terms_signature
        ):
            logger.debug(
                "Rejecting repeated list_terms retry because the previous identical call already returned the static indexed result"
            )
            return ToolMessage(
                content=(
                    "Misuse: repeated `list_terms` query was rejected.\n\n"
                    "The indexed vocabulary set is static for this run, so the same "
                    "unchanged `list_terms` call will return the same candidates. "
                    "Do not retry it unchanged. Either inspect one of the terms you "
                    "already saw, change `term_type`, `offset`, or `limit`, switch "
                    "to a different vocabulary, or continue modeling."
                ),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )

        if (
            tool_name == "inspect_term"
            and tool_signature is not None
            and tool_signature == self._previous_inspect_term_signature
        ):
            logger.debug(
                "Rejecting repeated inspect_term retry because the previous identical call already answered the question"
            )
            return ToolMessage(
                content=(
                    "Misuse: repeated `inspect_term` query was rejected.\n\n"
                    "You already inspected this exact term with the same options in "
                    "this run, and the indexed result will not change. Do not call "
                    "`inspect_term` again unchanged. Either use the term, inspect a "
                    "different candidate, request `include_source_rdf=true` if you "
                    "genuinely need the source description, or mint a local term if "
                    "no indexed term fits."
                ),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )

        try:
            result = handler(request)
        except WhitelistViolation as e:
            logger.debug(
                "Converting vocabulary whitelist violation for tool %s and term %s into a tool-facing error",
                tool_name,
                e.bad_term,
            )
            return ToolMessage(
                content=_format_whitelist_violation_message(e.bad_term, e.result),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )
        except VocabularyNamespaceNotAllowed as e:
            logger.debug(
                "Rejecting vocabulary namespace %s because it is disallowed by the injected whitelist",
                e.namespace,
            )
            return ToolMessage(
                content=self._format_disallowed_vocabulary_message(e.namespace),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )
        except IndexedVocabularyNamespaceNotFound as e:
            logger.debug(
                "Rejecting list_terms for %s because it is allowed but not available in the indexed vocabularies",
                e.namespace,
            )
            return ToolMessage(
                content=self._format_indexed_namespace_not_found_message(e.namespace),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )
        except IndexedVocabularyTermNotFound as e:
            logger.debug(
                "Rejecting inspect_term for %s because it is not available in the indexed vocabularies",
                e.term,
            )
            return ToolMessage(
                content=self._format_indexed_term_not_found_message(e.term),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )
        if not self._tool_result_is_error(result):
            if tool_name == "list_terms":
                self._previous_list_terms_signature = tool_signature
            elif tool_name == "inspect_term":
                self._previous_inspect_term_signature = tool_signature
        return result

    def list_vocabularies(self) -> tuple[VocabularySummary, ...]:
        summaries = []
        for namespace in self._visible_indexed_vocabularies():
            vocabulary = self.vocabulary_context.specification_cache.get_vocabulary(
                namespace
            )
            metadata = (
                self.vocabulary_context.specification_cache.get_vocabulary_metadata(
                    namespace
                )
            )
            summaries.append(
                VocabularySummary(
                    namespace=URIRef(namespace),
                    label=metadata.label,
                    description=metadata.description,
                    term_count=len(vocabulary.all_terms),
                )
            )
        return tuple(summaries)

    def list_terms(
        self,
        vocabulary: URIRef | str,
        term_type: Literal["class", "datatype", "individual", "property"] | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[VocabularyTerm, ...]:
        if not self.vocabulary_context.whitelist.allows_namespace(vocabulary):
            raise VocabularyNamespaceNotAllowed(URIRef(str(vocabulary)))
        if str(vocabulary) not in self._visible_indexed_vocabularies():
            raise IndexedVocabularyNamespaceNotFound(URIRef(str(vocabulary)))
        terms = self._terms_for_vocabulary(vocabulary, term_type)
        return terms[offset : offset + limit]

    def inspect_term(
        self, term: URIRef | str, include_source_rdf: bool = False
    ) -> TermInspectionResponse:
        term_iri = URIRef(str(term))
        whitelist_result = self.vocabulary_context.whitelist.find_term(term_iri)
        if not whitelist_result.allowed:
            raise WhitelistViolation(term_iri, whitelist_result)
        vocabulary = self._vocabulary_for_term(term_iri)
        candidate = next(
            candidate for candidate in vocabulary.all_terms if candidate.uri == term_iri
        )
        graph = self.vocabulary_context.specification_cache.get_spec(
            vocabulary.namespace
        )
        term_graph = graph.cbd(term_iri, include_reifications=False)
        super_terms: tuple[URIRef, ...] = ()

        # NOTE: Inefficient linear lookup for right now; optimization for future.
        if any(candidate.uri == term_iri for candidate in vocabulary.classes):
            path = get_transitive_path(graph, term_iri, RDFS.subClassOf)
            for triple in path:
                term_graph.add(triple)
            super_terms = tuple(
                sorted(
                    {
                        obj
                        for _, _, obj in path
                        if isinstance(obj, URIRef) and obj != term_iri
                    },
                    key=str,
                )
            )
        elif any(candidate.uri == term_iri for candidate in vocabulary.properties):
            path = get_transitive_path(graph, term_iri, RDFS.subPropertyOf)
            for triple in path:
                term_graph.add(triple)
            super_terms = tuple(
                sorted(
                    {
                        obj
                        for _, _, obj in path
                        if isinstance(obj, URIRef) and obj != term_iri
                    },
                    key=str,
                )
            )
        # NOTE: No datatype or annotation property support yet

        domain_terms = tuple(
            sorted(
                {
                    obj
                    for obj in graph.objects(term_iri, RDFS.domain)
                    if isinstance(obj, URIRef)
                },
                key=str,
            )
        )
        range_terms = tuple(
            sorted(
                {
                    obj
                    for obj in graph.objects(term_iri, RDFS.range)
                    if isinstance(obj, URIRef)
                },
                key=str,
            )
        )
        source_rdf = None
        if include_source_rdf:
            serialized = term_graph.serialize(format="turtle")
            triple_count = len(term_graph)
            source_rdf = SerializationResponse(
                format="turtle",
                content=(
                    serialized.decode("utf-8")
                    if isinstance(serialized, bytes)
                    else serialized
                ),
                default_graph_triple_count=triple_count,
                is_empty=triple_count == 0,
                message=(
                    f"Serialized the current default graph containing {triple_count} triples."
                ),
            )

        return TermInspectionResponse(
            uri=candidate.uri,
            label=candidate.label,
            definition=candidate.definition,
            termType=candidate.termType.value,
            vocabulary=vocabulary.namespace,
            superTerms=super_terms,
            domain=domain_terms,
            range=range_terms,
            source_rdf=source_rdf,
        )

    def _build_vocabulary_system_prompt(self) -> str:
        indexed = []
        for namespace in self._visible_indexed_vocabularies():
            metadata = (
                self.vocabulary_context.specification_cache.get_vocabulary_metadata(
                    namespace
                )
            )
            indexed.append(f"- {metadata.label} ({namespace})")

        return (
            _VOCABULARY_SYSTEM_PROMPT
            + "\n\n### Indexed Vocabularies Available Here\n\n"
            + "\n".join(indexed)
        )

    def _tool_call_signature(self, request: ToolCallRequest) -> str | None:
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

    def _tool_result_is_error(self, result: ToolMessage | Command[Any]) -> bool:
        return (
            isinstance(result, ToolMessage)
            and getattr(result, "status", None) == "error"
        )

    def _terms_for_vocabulary(
        self,
        vocabulary: URIRef | str,
        term_type: Literal["class", "datatype", "individual", "property"] | None = None,
    ) -> tuple[VocabularyTerm, ...]:
        indexed = self.vocabulary_context.specification_cache.get_vocabulary(vocabulary)
        if term_type is None:
            terms = indexed.all_terms
        else:
            terms = getattr(indexed, _TERM_TYPE_TO_COLLECTION[term_type])
        return tuple(sorted(terms, key=lambda term: term.uri))

    def _vocabulary_for_term(self, term: URIRef) -> RDFVocabulary:
        for vocabulary_iri in self._visible_indexed_vocabularies():
            vocabulary = self.vocabulary_context.specification_cache.get_vocabulary(
                vocabulary_iri
            )
            if any(candidate.uri == term for candidate in vocabulary.all_terms):
                return vocabulary
        raise IndexedVocabularyTermNotFound(term)

    def _visible_indexed_vocabularies(self) -> tuple[str, ...]:
        return self.vocabulary_context.indexed_vocabularies

    def _format_disallowed_vocabulary_message(self, namespace: URIRef) -> str:
        lines = [
            f"The vocabulary namespace {namespace} is not allowed by the current vocabulary policy.",
            "",
            "Choose a different vocabulary from `list_vocabularies`.",
            "",
            "Allowed vocabularies:",
            "",
        ]
        for entry in self.vocabulary_context.whitelist.entries:
            lines.append(f"- `{entry.prefix}:` {entry._ns_key(entry.namespace)}")
        return "\n".join(lines)

    @staticmethod
    def _format_indexed_term_not_found_message(term: URIRef) -> str:
        return (
            f"The term {term} is allowed by the current vocabulary policy, but it is not "
            "available in the indexed vocabularies for this run. Choose a different indexed "
            "term, inspect one of the visible vocabularies, or continue modeling without "
            "`inspect_term` if you genuinely need a new local term."
        )

    @staticmethod
    def _format_indexed_namespace_not_found_message(namespace: URIRef) -> str:
        return (
            f"The vocabulary namespace {namespace} is allowed by the current vocabulary policy, "
            "but it is not available in the indexed vocabularies for this run. Choose a "
            "different indexed vocabulary from `list_vocabularies`."
        )

    def _build_tools(self) -> tuple[BaseTool, ...]:
        @tool(
            "list_vocabularies",
            description=LIST_VOCABULARIES_TOOL_DESCRIPTION,
        )
        def list_vocabularies_tool() -> VocabularyListResponse:
            vocabularies = self.list_vocabularies()
            logger.debug("Listing %s indexed RDF vocabularies", len(vocabularies))
            return VocabularyListResponse(vocabularies=vocabularies)

        @tool(
            "list_terms",
            args_schema=ListTermsRequest,
            description=LIST_TERMS_TOOL_DESCRIPTION,
        )
        def list_terms_tool(
            vocabulary: N3IRIRef,
            term_type: Literal["class", "datatype", "individual", "property"]
            | None = None,
            offset: int = 0,
            limit: int = 50,
        ) -> tuple[VocabularyTerm, ...]:
            logger.debug(
                "Listing RDF terms for vocabulary %s (term_type=%s, offset=%s, limit=%s)",
                vocabulary,
                term_type,
                offset,
                limit,
            )
            return self.list_terms(
                vocabulary=vocabulary,
                term_type=term_type,
                offset=offset,
                limit=limit,
            )

        @tool(
            "inspect_term",
            args_schema=InspectTermRequest,
            description=INSPECT_TERM_TOOL_DESCRIPTION,
        )
        def inspect_term_tool(
            term: N3IRIRef, include_source_rdf: bool = False
        ) -> TermInspectionResponse:
            logger.debug(
                "Inspecting RDF term %s (include_source_rdf=%s)",
                term,
                include_source_rdf,
            )
            return self.inspect_term(term, include_source_rdf=include_source_rdf)

        return (
            list_vocabularies_tool,
            list_terms_tool,
            inspect_term_tool,
        )


class VocabularyNamespaceNotAllowed(Exception):
    def __init__(self, namespace: URIRef) -> None:
        self.namespace = namespace
        super().__init__(f"Disallowed vocabulary namespace: {namespace}")


class IndexedVocabularyNamespaceNotFound(Exception):
    def __init__(self, namespace: URIRef) -> None:
        self.namespace = namespace
        super().__init__(
            f"Vocabulary namespace is not available in the indexed vocabularies: {namespace}"
        )


class IndexedVocabularyTermNotFound(Exception):
    def __init__(self, term: URIRef) -> None:
        self.term = term
        super().__init__(f"Term is not available in the indexed vocabularies: {term}")


def get_transitive_path(
    graph: Graph, leaf_node: URIRef, predicate: URIRef
) -> Set[Triple]:
    hierarchy: MutableSet[Triple] = set()
    current_classes: list[IdentifiedNode] = [leaf_node]

    while current_classes:
        next_parents = []
        for node in current_classes:
            # Query parents of current class
            for parent in graph.objects(node, predicate):
                if isinstance(parent, IdentifiedNode):
                    triple = (node, predicate, parent)
                    if triple not in hierarchy:
                        hierarchy.add(triple)
                        next_parents.append(parent)
        current_classes = next_parents
    return hierarchy
