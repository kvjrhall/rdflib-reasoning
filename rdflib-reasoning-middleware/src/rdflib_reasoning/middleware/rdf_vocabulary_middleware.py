import logging
from collections.abc import Awaitable, Callable, MutableSet, Sequence, Set
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
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt
from rdflib import RDFS, Graph, IdentifiedNode, URIRef
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.middleware.dataset_model import N3IRIRef, SerializationResponse
from rdflib_reasoning.middleware.dataset_state import DatasetState
from rdflib_reasoning.middleware.namespaces.spec_cache import SpecificationCache
from rdflib_reasoning.middleware.namespaces.spec_index import (
    RDFVocabulary,
    VocabularyTerm,
)

logger = logging.getLogger(__name__)

_VOCABULARY_SYSTEM_PROMPT: Final[str] = """## RDF Vocabularies (Controlled)

- Think carefully about the facts that you want to assert:
  - Are there terms from standard RDF Vocabularies that apply?
     - Have you checked with `describe_term` or `describe_term_spec`?
  - Have you introduced definitions for terms into your knowledge base?
- Existing terms are broadly defined as:
  - terms already present in the current dataset
  - terms available from `list_terms`
  - well-established controlled vocahatbularies outside the index when the task clearly requires them
- You SHOULD inspect indexed vocabularies with `list_vocabularies`, `list_terms`, `describe_term`, or `describe_term_spec` when that inspection is useful for deciding whether an indexed term fits.
- You MUST NOT assume the meaning of an indexed term from its name alone
  - You SHOULD inspect indexed terms with `describe_term` for a coarse determination of its relevance
  - You SHOULD compare your intended use of indexed terms with `describe_term_spec` BEFORE their first use (e.g., domains/ranges, etc.)

### RDF Vocabulary Tools

- `list_vocabularies`: List all indexed RDF vocabularies
- `list_terms`: List indexed terms in a vocabulary
- `describe_term`: Describe one indexed vocabulary term
- `describe_term_spec`: Describe a term in native RDF from its indexed source graph
"""

LIST_VOCABULARIES_TOOL_DESCRIPTION: Final[
    str
] = """List the RDF vocabularies indexed by this middleware.

Use this tool when you need to discover which controlled vocabularies are available
before selecting terms.

Call this tool with no arguments.
"""

LIST_TERMS_TOOL_DESCRIPTION: Final[str] = """List indexed RDF terms from one vocabulary.

Pass `vocabulary`, `term_type`, and `limit` as top-level arguments.
You MUST NOT wrap those arguments inside a `properties` object.

Example arguments:
- `{"vocabulary": "<http://www.w3.org/2000/01/rdf-schema#>", "term_type": "class", "limit": 25}`
- `{"vocabulary": "http://www.w3.org/ns/prov#", "term_type": "property", "limit": 10}`
"""

DESCRIBE_TERM_TOOL_DESCRIPTION: Final[
    str
] = """Describe one indexed RDF vocabulary term using normalized schema-facing fields.

Pass `term` as a top-level argument naming the indexed vocabulary term to inspect.

Example arguments:
- `{"term": "<http://www.w3.org/2000/01/rdf-schema#Class>"}`
- `{"term": "http://www.w3.org/ns/prov#Agent"}`
"""

DESCRIBE_TERM_SPEC_TOOL_DESCRIPTION: Final[
    str
] = """Render one indexed RDF vocabulary term in native RDF.

Pass `term` as a top-level argument naming the indexed vocabulary term whose source
description you want serialized.

Example arguments:
- `{"term": "<http://www.w3.org/2000/01/rdf-schema#Class>"}`
- `{"term": "http://www.w3.org/ns/prov#wasDerivedFrom"}`
"""

_VOCABULARY_LABELS: Final[dict[str, str]] = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "RDF",
    "http://www.w3.org/2000/01/rdf-schema#": "RDFS",
    "http://www.w3.org/ns/prov#": "PROV-O",
}
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
        examples=["RDF", "RDFS", "PROV-O"],
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
                    "term_count": 7,
                },
                {
                    "namespace": "<http://www.w3.org/2000/01/rdf-schema#>",
                    "label": "RDFS",
                    "term_count": 13,
                },
            ],
            [
                {
                    "namespace": "<http://www.w3.org/ns/prov#>",
                    "label": "PROV-O",
                    "term_count": 80,
                }
            ],
        ],
    )


class ListTermsRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    vocabulary: N3IRIRef = Field(
        description="IRI of the indexed vocabulary to inspect.",
        examples=[
            "<http://www.w3.org/2000/01/rdf-schema#>",
            "http://www.w3.org/ns/prov#",
        ],
    )
    term_type: Literal["class", "datatype", "individual", "property"] | None = Field(
        default=None,
        description="Optional term type filter applied within the selected vocabulary.",
        examples=["class", "property", None],
    )
    limit: NonNegativeInt = Field(
        default=50,
        description="Maximum number of terms to return.",
        examples=[10, 25, 50],
    )


class TermDescriptionRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    term: N3IRIRef = Field(
        description="IRI of the indexed vocabulary term to inspect.",
        examples=[
            "<http://www.w3.org/2000/01/rdf-schema#Class>",
            "http://www.w3.org/ns/prov#Agent",
        ],
    )


class RDFVocabularyMiddleware(AgentMiddleware[DatasetState, ContextT, ResponseT]):
    tools: Sequence[BaseTool]
    cache: SpecificationCache

    def __init__(self, cache: SpecificationCache | None = None) -> None:
        self.cache = cache or SpecificationCache()
        self.tools = self._build_tools()

    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        """Append RDF vocabulary guidance to the system prompt before model execution."""
        logger.debug("Wrapping model call for RDF Vocabulary Middleware")
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                _VOCABULARY_SYSTEM_PROMPT,
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
        logger.debug("Async wrapping model call for RDF Vocabulary Middleware (async)")
        request = request.override(
            system_message=append_to_system_message(
                request.system_message,
                _VOCABULARY_SYSTEM_PROMPT,
            )
        )
        return await handler(request)

    def list_vocabularies(self) -> tuple[VocabularySummary, ...]:
        summaries = []
        for namespace in self.cache.list_indexed_vocabularies():
            vocabulary = self.cache.get_vocabulary(namespace)
            summaries.append(
                VocabularySummary(
                    namespace=URIRef(namespace),
                    label=_VOCABULARY_LABELS.get(namespace, namespace),
                    term_count=len(vocabulary.all_terms),
                )
            )
        return tuple(summaries)

    def list_terms(
        self,
        vocabulary: URIRef | str,
        term_type: Literal["class", "datatype", "individual", "property"] | None = None,
        limit: int = 50,
    ) -> tuple[VocabularyTerm, ...]:
        terms = self._terms_for_vocabulary(vocabulary, term_type)
        return terms[:limit]

    def describe_term(self, term: URIRef | str) -> VocabularyTerm:
        for vocabulary_iri in self.cache.list_indexed_vocabularies():
            vocabulary = self.cache.get_vocabulary(vocabulary_iri)
            for candidate in vocabulary.all_terms:
                if candidate.uri == URIRef(str(term)):
                    return candidate
        raise ValueError(f"Term is not available in the indexed vocabularies: {term}")

    def describe_term_spec(self, term: URIRef | str) -> str:
        term_iri = URIRef(str(term))
        vocabulary = self._vocabulary_for_term(term_iri)
        graph = self.cache.get_spec(vocabulary.namespace)
        term_graph = graph.cbd(term_iri, include_reifications=False)

        # NOTE: Inefficient linear lookup for right now; optimization for future.
        if any(candidate.uri == term_iri for candidate in vocabulary.classes):
            path = get_transitive_path(graph, term_iri, RDFS.subClassOf)
            for triple in path:
                term_graph.add(triple)
        elif any(candidate.uri == term_iri for candidate in vocabulary.properties):
            path = get_transitive_path(graph, term_iri, RDFS.subPropertyOf)
            for triple in path:
                term_graph.add(triple)
        # NOTE: No datatype or annotation property support yet

        serialized = term_graph.serialize(format="turtle")
        return (
            serialized.decode("utf-8") if isinstance(serialized, bytes) else serialized
        )

    def _terms_for_vocabulary(
        self,
        vocabulary: URIRef | str,
        term_type: Literal["class", "datatype", "individual", "property"] | None = None,
    ) -> tuple[VocabularyTerm, ...]:
        indexed = self.cache.get_vocabulary(vocabulary)
        if term_type is None:
            terms = indexed.all_terms
        else:
            terms = getattr(indexed, _TERM_TYPE_TO_COLLECTION[term_type])
        return tuple(sorted(terms, key=lambda term: term.uri))

    def _vocabulary_for_term(self, term: URIRef) -> RDFVocabulary:
        for vocabulary_iri in self.cache.list_indexed_vocabularies():
            vocabulary = self.cache.get_vocabulary(vocabulary_iri)
            if any(candidate.uri == term for candidate in vocabulary.all_terms):
                return vocabulary
        raise ValueError(f"Term is not available in the indexed vocabularies: {term}")

    def _build_tools(self) -> tuple[BaseTool, ...]:
        @tool(
            "list_vocabularies",
            description=LIST_VOCABULARIES_TOOL_DESCRIPTION,
        )
        def list_vocabularies_tool() -> VocabularyListResponse:
            logger.debug("Listing RDF vocabularies")
            return VocabularyListResponse(vocabularies=self.list_vocabularies())

        @tool(
            "list_terms",
            args_schema=ListTermsRequest,
            description=LIST_TERMS_TOOL_DESCRIPTION,
        )
        def list_terms_tool(
            vocabulary: N3IRIRef,
            term_type: Literal["class", "datatype", "individual", "property"]
            | None = None,
            limit: int = 50,
        ) -> tuple[VocabularyTerm, ...]:
            logger.debug(f"Listing RDF terms for vocabulary: {vocabulary}")
            return self.list_terms(
                vocabulary=vocabulary, term_type=term_type, limit=limit
            )

        @tool(
            "describe_term",
            args_schema=TermDescriptionRequest,
            description=DESCRIBE_TERM_TOOL_DESCRIPTION,
        )
        def describe_term_tool(term: N3IRIRef) -> VocabularyTerm:
            logger.debug(f"Describing RDF term: {term}")
            return self.describe_term(term)

        @tool(
            "describe_term_spec",
            args_schema=TermDescriptionRequest,
            description=DESCRIBE_TERM_SPEC_TOOL_DESCRIPTION,
        )
        def describe_term_spec_tool(term: N3IRIRef) -> SerializationResponse:
            logger.debug(f"Describing RDF term spec: {term}")
            return SerializationResponse(
                format="turtle",
                content=self.describe_term_spec(term),
            )

        return (
            list_vocabularies_tool,
            list_terms_tool,
            describe_term_tool,
            describe_term_spec_tool,
        )


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
