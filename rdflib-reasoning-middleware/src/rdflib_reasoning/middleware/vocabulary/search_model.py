from pydantic import BaseModel, ConfigDict, Field
from rdflib_reasoning.axiom.common import N3IRIRef
from rdflib_reasoning.middleware.namespaces.common import VocabularyTermType


class TermSearchRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    query: str = Field(
        description="Meaning or term description the agent wants to express."
    )
    vocabularies: tuple[N3IRIRef, ...] = Field(
        default=(),
        description="Optional vocabulary namespace IRIs to restrict search.",
    )
    term_types: tuple[VocabularyTermType, ...] = Field(
        default=(),
        description="Optional normalized term types to restrict search.",
    )
    limit: int = Field(
        default=8,
        ge=1,
        le=25,
        description="Maximum number of ranked candidate terms to return.",
    )


class TermSearchHit(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    uri: N3IRIRef
    label: str
    definition: str
    termType: VocabularyTermType
    vocabulary: N3IRIRef
    score: float = Field(description="Normalized final lexical ranking score.")
    why_matched: tuple[str, ...] = Field(
        default=(),
        description="Compact ranking explanations intended for agent use.",
    )


class TermSearchResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    query: str
    hits: tuple[TermSearchHit, ...]
