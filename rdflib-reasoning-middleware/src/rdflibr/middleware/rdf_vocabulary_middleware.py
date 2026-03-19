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
from rdflibr.axiom.common import Triple
from rdflibr.middleware.dataset_model import N3IRIRef, SerializationResponse
from rdflibr.middleware.dataset_state import DatasetState
from rdflibr.middleware.namespaces.spec_cache import SpecificationCache
from rdflibr.middleware.namespaces.spec_index import RDFVocabulary, VocabularyTerm

logger = logging.getLogger(__name__)

_VOCABULARY_SYSTEM_PROMPT: Final[str] = """## RDF Vocabularies (Controlled)

- When asserting RDF, you MUST prefer an existing term when one already fits the intended meaning.
- Existing terms include:
  - terms already present in the current dataset
  - terms available from indexed vocabularies exposed by your tools
  - well-established controlled vocabularies outside the index when the task clearly requires them
- You MUST prefer IRIs from controlled vocabularies when they fit the task and the domain.
- Before minting a new RDF term, you MUST consider whether an existing term already fits.
- You SHOULD inspect indexed vocabularies with `list_vocabularies`, `list_terms`, `describe_term`, or `describe_term_spec` when that inspection is useful for deciding whether an indexed term fits.
- You MUST NOT assume the meaning of an unfamiliar indexed term from its local name alone; if you are considering using it, you SHOULD inspect it first with `describe_term` or `describe_term_spec`.
- You MAY introduce a new term only when no existing term adequately fits the intended meaning.

### RDF Vocabulary Tools

- `list_vocabularies`: List all indexed RDF vocabularies
- `list_terms`: List indexed terms in a vocabulary
- `describe_term`: Describe one indexed vocabulary term
- `describe_term_spec`: Describe a term in native RDF from its indexed source graph
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
    namespace: N3IRIRef
    label: str
    term_count: NonNegativeInt


class VocabularyListResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    vocabularies: tuple[VocabularySummary, ...]


class ListTermsRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    vocabulary: N3IRIRef = Field(description="IRI of the indexed vocabulary.")
    term_type: Literal["class", "datatype", "individual", "property"] | None = Field(
        default=None,
        description="Optional term type filter.",
    )
    limit: NonNegativeInt = Field(default=50, description="Maximum number of terms.")


class TermDescriptionRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    term: N3IRIRef = Field(description="IRI of the indexed vocabulary term.")


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
            description="List all indexed RDF vocabularies available through this middleware.",
        )
        def list_vocabularies_tool() -> VocabularyListResponse:
            logger.debug("Listing RDF vocabularies")
            return VocabularyListResponse(vocabularies=self.list_vocabularies())

        @tool(
            "list_terms",
            args_schema=ListTermsRequest,
            description="List indexed terms in one RDF vocabulary.",
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
            description="Describe one indexed RDF vocabulary term using normalized schema-facing fields.",
        )
        def describe_term_tool(term: N3IRIRef) -> VocabularyTerm:
            logger.debug(f"Describing RDF term: {term}")
            return self.describe_term(term)

        @tool(
            "describe_term_spec",
            args_schema=TermDescriptionRequest,
            description="Render one indexed RDF vocabulary term in its native RDF.",
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
