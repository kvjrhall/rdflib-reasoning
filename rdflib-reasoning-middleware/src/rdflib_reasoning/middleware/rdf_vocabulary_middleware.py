import logging
from collections.abc import Awaitable, Callable, MutableSet, Sequence, Set
from dataclasses import dataclass
from difflib import SequenceMatcher
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
from rdflib_reasoning.axiom.common import N3IRIRef, Triple
from rdflib_reasoning.middleware.dataset_middleware import (
    WhitelistViolation,
    _format_whitelist_violation_message,
)
from rdflib_reasoning.middleware.dataset_model import SerializationResponse
from rdflib_reasoning.middleware.dataset_state import DatasetState
from rdflib_reasoning.middleware.namespaces.common import VocabularyTermType
from rdflib_reasoning.middleware.namespaces.spec_index import (
    RDFVocabulary,
    VocabularyTerm,
)
from rdflib_reasoning.middleware.shared_services import RunTermTelemetry
from rdflib_reasoning.middleware.vocabulary.search_index import (
    IndexedTerm,
    VocabularySearchIndex,
    uri_local_name,
)
from rdflib_reasoning.middleware.vocabulary.search_model import (
    TermSearchRequest,
    TermSearchResponse,
)
from rdflib_reasoning.middleware.vocabulary_configuration import VocabularyContext

logger = logging.getLogger(__name__)

_VOCABULARY_SYSTEM_PROMPT: Final[str] = """## RDF Vocabulary Guidance

You MUST invoke the `list_vocabularies` tool ONCE, inspect the available indexed
vocabularies and see if any of them are relevant to your task.

You MUST call `list_vocabularies` before using any other vocabulary tool. If
you skip this step, you have not followed the required vocabulary workflow.

After you have begun your task, use the vocabulary tools only to help choose
established RDF terms when you are uncertain whether a standard term fits your
intended meaning.

Working method:
- First identify the main classes, individuals, and relations you expect to
  model. Treat that as a draft graph shape.
- Use vocabulary tools to test whether that draft shape overlaps with one
  indexed ontology or with a small set of indexed vocabularies.
- If several important concepts appear to cluster in the same small indexed
  vocabulary, pause term-by-term lookup and use `list_terms` once to
  familiarize yourself with that ontology as a modeling resource.
- Use that familiarization pass to decide whether the ontology already supplies
  a significant fraction of your intended graph shape, then revise your draft
  shape before you continue modeling.

Default workflow:
- If you already know a core RDF/RDFS/OWL term is appropriate, use it and continue.
- Call `list_vocabularies` once before using any other vocabulary tool so you
  know what indexed vocabularies are available.
- If you know the meaning you want to express but do not yet know the right term, use `search_terms`.
- If you know which vocabulary you want, or repeated hits suggest one small
  vocabulary may cover several target concepts, use `list_terms` for one
  bounded familiarization pass.
- If you already have a candidate term in mind, use `inspect_term`.

Decision policy:
- Prefer one quick inspection over extended self-discussion.
- Prefer `search_terms` when you know the meaning you want to express but do
  not yet know the likely vocabulary or term label.
- Prefer `list_terms` when one available vocabulary appears central to the task
  and has a small `term_count`.
- If `list_vocabularies` shows a vocabulary with a small `term_count` that appears highly relevant to the source, you SHOULD call `list_terms` once before issuing several narrow searches or minting overlapping local terms.
- If several relevant hits point to the same small vocabulary, do not treat
  them as isolated wins. Pause term-by-term lookup and scan that vocabulary
  once before deciding whether to mint overlapping local terms.
- After 1-2 successful `search_terms` hits in the same small vocabulary, pause
  and decide whether a quick `list_terms` scan would reveal nearby terms or
  ontology structure you still need before continuing modeling.
- After one bounded ontology scan or 1-2 targeted checks in the same modeling
  area, decide whether you already have enough vocabulary information to
  continue modeling.
- Do not stop vocabulary exploration merely because one or two plausible terms
  were found when a small relevant indexed vocabulary has not yet been given a
  bounded familiarization pass.
- Do not keep re-checking the same term once `inspect_term` has answered your question.
- Do not repeat the same `search_terms` call unchanged; refine the query or filters if you still need different candidates.
- Do not repeat the same `inspect_term` call unchanged
- Do not repeat the same `list_terms` call unchanged; change the
  vocabulary, filter, offset, or limit if you still need different candidates.
- If `search_terms` or `list_terms` gives you a relevant candidate, move to
  `inspect_term`, revise your draft graph shape, or continue modeling instead
  of widening the search reflexively.
- If repeated searches keep returning plausible candidates, stop expanding the
  search space. Choose one acceptable term or, after one bounded scan of a
  small relevant ontology, mint a local one if needed, then continue modeling.
- Do not skip directly from `list_vocabularies` to minting overlapping local
  classes or properties when a small highly relevant indexed vocabulary is
  available and could be scanned quickly.
- Do not mint local classes or properties that overlap a small relevant indexed
  vocabulary until you have completed one bounded scan of that vocabulary.
- If inspection does not quickly reveal a fitting standard term, mint a local term
  only when it is genuinely needed for a faithful representation, document it,
  and continue.
- Prefer representing explicit source claims over inventing additional ontology
  structure or helper relations that the source does not require.
- Do not assume a term's meaning from its local name alone when you are unsure.
- Do not pause to inspect vocabulary terms that you already know well enough to use correctly.
- Do not expand to additional vocabularies unless the current choices remain
  insufficient for representing the source faithfully.
- Do not begin inspecting unrelated properties from another vocabulary unless
  the source text clearly calls for them or they are needed to complete the
  current modeling step.
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
- `search_terms`: search indexed terms by intended meaning across the visible indexed vocabularies
- `list_terms`: scan candidate indexed terms within one vocabulary
- `inspect_term`: inspect one indexed term in a compact form, optionally including source RDF
"""

_VOCABULARY_FIRST_STEP_REMINDER: Final[str] = """
### Required First Step

You have not yet invoked `list_vocabularies` in this run.

Your next vocabulary action MUST be a `list_vocabularies` tool call.
Do not call `search_terms`, `list_terms`, or `inspect_term` first.
Do not finalize your answer until `list_vocabularies` has been called once.
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

This is especially useful when one vocabulary appears central to the task, has
few enough terms to scan quickly, and may already supply a significant fraction
of your intended graph shape.
Treat this as a bounded familiarization pass to improve modeling decisions, not
as an exhaustive cataloging step.

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

SEARCH_TERMS_TOOL_DESCRIPTION: Final[
    str
] = """Search indexed RDF vocabulary terms by intended meaning.

Use this when you know the meaning you want to express but do not yet know the
right indexed term or even the right vocabulary.

This is best for probing overlap between your draft graph shape and the indexed
vocabularies when you can already describe a target concept in words. If one
relevant vocabulary is already known and has few terms, `list_terms` may be
faster and more complete than issuing several narrow searches.
If repeated searches in the same area keep returning plausible candidates from
one small vocabulary, you SHOULD switch to `list_terms` for one bounded scan of
that vocabulary rather than continuing isolated searches.

This search is lexical and deterministic over the static indexed vocabulary set
for this run. You MUST NOT repeat the same `search_terms` call unchanged and
expect a different result. If you still need different candidates, refine the
query, change the vocabulary or term type filters, or inspect one of the
returned candidates.

Arguments:
- `query`: intended meaning, label fragment, or short descriptive phrase
- `vocabularies`: optional indexed vocabulary namespace filter
- `term_types`: optional normalized term type filter (`class`, `property`, `individual`, `datatype`)
- `limit`: maximum number of ranked candidate terms to return

Example arguments:
- `{"query": "birth place", "limit": 8}`
- `{"query": "creator", "vocabularies": ["<http://xmlns.com/foaf/0.1/>"], "term_types": ["property"], "limit": 5}`
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

Treat this as a confirmatory tool for one candidate term or a small number of
modeling-significant terms after familiarization. Do not use repeated
`inspect_term` calls to reconstruct an ontology term by term.

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
_REQUIRES_LIST_VOCABULARIES_FIRST_TOOLS: Final[frozenset[str]] = frozenset(
    {"search_terms", "list_terms", "inspect_term"}
)


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
    preferredPrefix: str | None = Field(
        default=None,
        description=(
            "Preferred namespace prefix advertised by the vocabulary metadata "
            "when available."
        ),
        examples=["rdf", "prov", None],
    )
    preferredNamespace: N3IRIRef | None = Field(
        default=None,
        description=(
            "Preferred namespace IRI advertised by the vocabulary metadata when "
            "available. This is advisory presentation metadata only."
        ),
        examples=["<http://purl.org/dc/terms/>", None],
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
    termType: VocabularyTermType = Field(
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
    search_index: VocabularySearchIndex | None = None
    run_term_telemetry: RunTermTelemetry | None = None


class RDFVocabularyMiddleware(AgentMiddleware[DatasetState, ContextT, ResponseT]):
    vocabulary_context: VocabularyContext
    search_index: VocabularySearchIndex
    tools: Sequence[BaseTool]
    run_term_telemetry: RunTermTelemetry
    _has_listed_vocabularies: bool
    _seen_search_terms_signatures: set[str]
    _seen_list_terms_signatures: set[str]
    _seen_inspect_term_signatures: set[str]
    _indexed_term_not_found_suggestion_limit: int

    def __init__(self, config: RDFVocabularyMiddlewareConfig) -> None:
        self.config = config
        self.vocabulary_context = self.config.vocabulary_context
        self.search_index = (
            self.config.search_index
            if self.config.search_index is not None
            else VocabularySearchIndex.build(self.vocabulary_context)
        )
        self.run_term_telemetry = self.config.run_term_telemetry or RunTermTelemetry()
        self.tools = self._build_tools()
        self._has_listed_vocabularies = False
        self._seen_search_terms_signatures = set()
        self._seen_list_terms_signatures = set()
        self._seen_inspect_term_signatures = set()
        self._indexed_term_not_found_suggestion_limit = 3

    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        """Append RDF vocabulary guidance to the system prompt before model execution."""
        vocabulary_prompt = self._build_vocabulary_system_prompt()
        if not self._has_listed_vocabularies:
            vocabulary_prompt += "\n\n" + _VOCABULARY_FIRST_STEP_REMINDER
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                vocabulary_prompt,
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
        vocabulary_prompt = self._build_vocabulary_system_prompt()
        if not self._has_listed_vocabularies:
            vocabulary_prompt += "\n\n" + _VOCABULARY_FIRST_STEP_REMINDER
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                vocabulary_prompt,
            )
        )
        return await handler(request)

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """Guard repeated static vocabulary lookups and adapt tool-facing errors."""
        tool_name = (
            request.tool.name if request.tool is not None else request.tool_call["name"]
        )
        tool_call_id = request.tool_call["id"]
        tool_signature = self._tool_call_signature(request)

        if (
            not self._has_listed_vocabularies
            and tool_name in _REQUIRES_LIST_VOCABULARIES_FIRST_TOOLS
        ):
            logger.debug(
                "Rejecting %s because list_vocabularies has not yet been called in this run",
                tool_name,
            )
            return ToolMessage(
                content=(
                    "Misuse: `list_vocabularies` is required before any other vocabulary tool.\n\n"
                    "Call `list_vocabularies` now, inspect the available indexed vocabularies, "
                    "and only then decide whether to use `search_terms`, `list_terms`, or "
                    "`inspect_term`."
                ),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )

        if (
            tool_name == "search_terms"
            and tool_signature is not None
            and tool_signature in self._seen_search_terms_signatures
        ):
            logger.debug(
                "Rejecting repeated search_terms retry because the same identical call already returned the static indexed result earlier in this run"
            )
            return ToolMessage(
                content=(
                    "Misuse: repeated `search_terms` query was rejected.\n\n"
                    "The indexed vocabulary set is static for this run, so the same "
                    "unchanged `search_terms` call will return the same ranked candidates. "
                    "Do not retry it unchanged. Either inspect one of the returned terms, "
                    "refine the query text, change the vocabulary or term type filters, "
                    "or continue modeling."
                ),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )

        if (
            tool_name == "list_terms"
            and tool_signature is not None
            and tool_signature in self._seen_list_terms_signatures
        ):
            logger.debug(
                "Rejecting repeated list_terms retry because the same identical call already returned the static indexed result earlier in this run"
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
            and tool_signature in self._seen_inspect_term_signatures
        ):
            logger.debug(
                "Rejecting repeated inspect_term retry because the same identical call already answered the question earlier in this run"
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
            suggestions = self._nearest_indexed_term_candidates(
                e.term, limit=self._indexed_term_not_found_suggestion_limit
            )
            return ToolMessage(
                content=self._format_indexed_term_not_found_message(
                    e.term, suggestions=suggestions
                ),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )
        if not self._tool_result_is_error(result):
            if tool_name == "list_vocabularies":
                self._has_listed_vocabularies = True
            elif tool_name == "search_terms":
                if tool_signature is not None:
                    self._seen_search_terms_signatures.add(tool_signature)
            elif tool_name == "list_terms":
                if tool_signature is not None:
                    self._seen_list_terms_signatures.add(tool_signature)
            elif tool_name == "inspect_term":
                if tool_signature is not None:
                    self._seen_inspect_term_signatures.add(tool_signature)
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
                    preferredPrefix=metadata.preferred_namespace_prefix,
                    preferredNamespace=(
                        URIRef(metadata.preferred_namespace_uri)
                        if metadata.preferred_namespace_uri is not None
                        else None
                    ),
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

    def search_terms(
        self,
        query: str,
        vocabularies: tuple[URIRef | str, ...] = (),
        term_types: tuple[VocabularyTermType, ...] = (),
        limit: int = 8,
    ) -> TermSearchResponse:
        normalized_vocabularies = tuple(str(vocabulary) for vocabulary in vocabularies)
        for vocabulary in normalized_vocabularies:
            if not self.vocabulary_context.whitelist.allows_namespace(vocabulary):
                raise VocabularyNamespaceNotAllowed(URIRef(vocabulary))
            if vocabulary not in self._visible_indexed_vocabularies():
                raise IndexedVocabularyNamespaceNotFound(URIRef(vocabulary))

        return self.search_index.search(
            query,
            vocabularies=normalized_vocabularies,
            term_types=term_types,
            limit=limit,
        )

    def inspect_term(
        self, term: URIRef | str, include_source_rdf: bool = False
    ) -> TermInspectionResponse:
        term_iri = URIRef(str(term))
        whitelist_result = self.vocabulary_context.whitelist.find_term(term_iri)
        if not whitelist_result.allowed:
            raise WhitelistViolation(term_iri, whitelist_result)
        vocabulary = self._vocabulary_for_term(term_iri)
        candidate: VocabularyTerm = next(
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
            termType=candidate.termType,
            vocabulary=vocabulary.namespace,
            superTerms=super_terms,
            domain=domain_terms,
            range=range_terms,
            source_rdf=source_rdf,
        )

    def _build_vocabulary_system_prompt(self) -> str:
        return _VOCABULARY_SYSTEM_PROMPT

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
    def _format_indexed_term_not_found_message(
        term: URIRef, suggestions: Sequence[IndexedTerm] = ()
    ) -> str:
        lines = [
            f"The term {term} is allowed by the current vocabulary policy, but it is not "
            "available in the indexed vocabularies for this run. Choose a different indexed "
            "term, inspect one of the visible vocabularies, or continue modeling without "
            "`inspect_term` if you genuinely need a new local term."
        ]
        if len(suggestions) == 0:
            return "".join(lines)

        lines.extend(("", "", "Suggested indexed alternatives:"))
        for candidate in suggestions:
            lines.append(f"- `{candidate.label}` (`{candidate.uri}`)")
        return "\n".join(lines)

    def _nearest_indexed_term_candidates(
        self, term: URIRef, limit: int = 3
    ) -> tuple[IndexedTerm, ...]:
        if limit <= 0:
            return ()
        term_value = str(term)
        rejected_local_name = uri_local_name(term_value)
        if rejected_local_name == "":
            return ()

        ranked_candidates = sorted(
            (
                (
                    self._local_name_similarity_score(
                        rejected_local_name, candidate.uri
                    ),
                    candidate,
                )
                for candidate in self.search_index.terms
                if candidate.uri != term_value
            ),
            key=lambda pair: (-pair[0], pair[1].vocabulary, pair[1].uri),
        )
        filtered_candidates = tuple(
            candidate for score, candidate in ranked_candidates if score >= 0.75
        )
        return filtered_candidates[:limit]

    @staticmethod
    def _local_name_similarity_score(
        rejected_local_name: str, candidate_uri: str
    ) -> float:
        candidate_local_name = uri_local_name(candidate_uri)
        if candidate_local_name == "":
            return 0.0
        return SequenceMatcher(
            None,
            rejected_local_name.lower(),
            candidate_local_name.lower(),
        ).ratio()

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
        def list_vocabularies_tool() -> str:
            vocabularies = self.list_vocabularies()
            logger.debug("Listing %s indexed RDF vocabularies", len(vocabularies))
            return self._json_tool_content(
                VocabularyListResponse(vocabularies=vocabularies)
            )

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
        ) -> str:
            logger.debug(
                "Listing RDF terms for vocabulary %s (term_type=%s, offset=%s, limit=%s)",
                vocabulary,
                term_type,
                offset,
                limit,
            )
            return self._json_tool_content(
                self.list_terms(
                    vocabulary=vocabulary,
                    term_type=term_type,
                    offset=offset,
                    limit=limit,
                )
            )

        @tool(
            "search_terms",
            args_schema=TermSearchRequest,
            description=SEARCH_TERMS_TOOL_DESCRIPTION,
        )
        def search_terms_tool(
            query: str,
            vocabularies: tuple[N3IRIRef, ...] = (),
            term_types: tuple[VocabularyTermType, ...] = (),
            limit: int = 8,
        ) -> str:
            logger.debug(
                "Searching RDF terms for query %r (vocabularies=%s, term_types=%s, limit=%s)",
                query,
                vocabularies,
                term_types,
                limit,
            )
            return self._json_tool_content(
                self.search_terms(
                    query=query,
                    vocabularies=vocabularies,
                    term_types=term_types,
                    limit=limit,
                )
            )

        @tool(
            "inspect_term",
            args_schema=InspectTermRequest,
            description=INSPECT_TERM_TOOL_DESCRIPTION,
        )
        def inspect_term_tool(term: N3IRIRef, include_source_rdf: bool = False) -> str:
            logger.debug(
                "Inspecting RDF term %s (include_source_rdf=%s)",
                term,
                include_source_rdf,
            )
            return self._json_tool_content(
                self.inspect_term(term, include_source_rdf=include_source_rdf)
            )

        return (
            list_vocabularies_tool,
            search_terms_tool,
            list_terms_tool,
            inspect_term_tool,
        )

    def _json_tool_content(self, payload: Any) -> str:
        """Serialize tool output into stable JSON for model-facing ToolMessage content."""
        if isinstance(payload, BaseModel):
            return payload.model_dump_json()
        normalized = self._to_json_compatible(payload)
        return json_dumps(normalized, ensure_ascii=False, sort_keys=True)

    def _to_json_compatible(self, payload: Any) -> Any:
        if isinstance(payload, BaseModel):
            return payload.model_dump(mode="json")
        if isinstance(payload, dict):
            return {
                str(key): self._to_json_compatible(value)
                for key, value in payload.items()
            }
        if isinstance(payload, (tuple, list, set, frozenset)):
            return [self._to_json_compatible(item) for item in payload]
        return payload


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
