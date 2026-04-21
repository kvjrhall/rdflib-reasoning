import unicodedata
from collections.abc import Generator, Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from typing import Self, TypeAlias

import regex as re
from rdflib import Graph, Node, URIRef
from rdflib.namespace import RDFS
from rdflib_reasoning.middleware.namespaces.common import VocabularyTermType
from rdflib_reasoning.middleware.namespaces.spec_index import (
    RDFVocabulary,
    VocabularyTerm,
)
from rdflib_reasoning.middleware.vocabulary_configuration import VocabularyContext

from .search_model import TermSearchHit, TermSearchResponse


@dataclass(frozen=True, slots=True)
class IndexedTerm:
    uri: str
    label: str
    definition: str
    term_type: VocabularyTermType
    vocabulary: str

    super_terms: tuple[str, ...] = ()
    domain: tuple[str, ...] = ()
    range_: tuple[str, ...] = ()

    label_norm: str = ""
    label_tokens: tuple[str, ...] = ()
    uri_local_name: str = ""
    uri_local_name_norm: str = ""
    uri_local_tokens: tuple[str, ...] = ()
    definition_norm: str = ""
    definition_tokens: tuple[str, ...] = ()
    super_term_labels: tuple[str, ...] = ()
    super_term_tokens: tuple[str, ...] = ()
    domain_labels: tuple[str, ...] = ()
    domain_tokens: tuple[str, ...] = ()
    range_labels: tuple[str, ...] = ()
    range_tokens: tuple[str, ...] = ()
    searchable_text: str = ""


_WORD_RE = re.compile(r"[a-z0-9]+")
LabelLookup: TypeAlias = Mapping[str, str]


def strip_accents(text: str) -> str:
    return "".join(
        ch
        for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )


def split_identifier(text: str) -> str:
    # Split camelCase / PascalCase
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    # Replace common separators
    text = re.sub(r"[_:/#\-.]+", " ", text)
    return text


def normalize_text(text: str) -> str:
    text = strip_accents(text).strip()
    text = split_identifier(text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(_WORD_RE.findall(normalize_text(text)))


def uri_local_name(uri: str) -> str:
    for sep in ("#", "/", ":"):
        if sep in uri:
            uri = uri.rsplit(sep, 1)[-1]
    return uri


@dataclass(frozen=True, slots=True)
class VocabularySearchIndex:
    terms: tuple[IndexedTerm, ...]
    terms_by_uri: Mapping[str, IndexedTerm]
    # optional inverted/token structures later

    @classmethod
    def build(cls, context: VocabularyContext) -> Self:
        # We pre-populate the lookup with known-good labels, so that we only
        # create ad-hoc labels for uncontrolled terms.
        labels_by_uri: MutableMapping[str, str] = {}
        for vocabulary_name in context.indexed_vocabularies:
            vocabulary = context.specification_cache.get_vocabulary(vocabulary_name)
            for term in vocabulary.all_terms:
                labels_by_uri[str(term.uri)] = term.label

        terms: list[IndexedTerm] = []
        terms_by_uri: dict[str, IndexedTerm] = {}
        for vocabulary_name in context.indexed_vocabularies:
            vocabulary = context.specification_cache.get_vocabulary(vocabulary_name)
            spec = context.specification_cache.get_spec(vocabulary.namespace)
            for indexed_term in _index_vocabulary(vocabulary, spec, labels_by_uri):
                terms.append(indexed_term)
                terms_by_uri[indexed_term.uri] = indexed_term
        return cls(terms=tuple(terms), terms_by_uri=terms_by_uri)

    def search(
        self,
        query: str,
        *,
        vocabularies: tuple[str, ...] = (),
        term_types: tuple[VocabularyTermType, ...] = (),
        limit: int = 8,
    ) -> TermSearchResponse:
        normalized_query = normalize_text(query)
        query_tokens = tokenize(query)
        if not normalized_query or len(query_tokens) == 0:
            return TermSearchResponse(query=query, hits=())

        hits: list[TermSearchHit] = []
        for term in self.terms:
            if len(vocabularies) > 0 and term.vocabulary not in vocabularies:
                continue
            if len(term_types) > 0 and term.term_type not in term_types:
                continue

            score, reasons = _score_term(term, normalized_query, query_tokens)
            if score <= 0:
                continue

            hits.append(
                TermSearchHit(
                    uri=URIRef(term.uri),
                    label=term.label,
                    definition=term.definition,
                    termType=term.term_type,
                    vocabulary=URIRef(term.vocabulary),
                    score=score,
                    why_matched=reasons,
                )
            )

        hits.sort(key=lambda hit: (-hit.score, hit.label.lower(), str(hit.uri)))
        return TermSearchResponse(query=query, hits=tuple(hits[:limit]))


def _index_term(
    vocabulary: RDFVocabulary,
    term: VocabularyTerm,
    super_terms: tuple[URIRef, ...],
    domain_terms: tuple[URIRef, ...],
    range_terms: tuple[URIRef, ...],
    labels_by_uri: LabelLookup,
) -> IndexedTerm:
    local_name = uri_local_name(str(term.uri))

    super_labels = tuple(_lookup_label(uri, labels_by_uri) for uri in super_terms)
    domain_labels = tuple(_lookup_label(uri, labels_by_uri) for uri in domain_terms)
    range_labels = tuple(_lookup_label(uri, labels_by_uri) for uri in range_terms)

    label_tokens = tokenize(term.label)
    local_tokens = tokenize(local_name)
    definition_tokens = tokenize(term.definition)
    super_tokens = tuple(tok for label in super_labels for tok in tokenize(label))
    domain_tokens = tuple(tok for label in domain_labels for tok in tokenize(label))
    range_tokens = tuple(tok for label in range_labels for tok in tokenize(label))

    searchable_text = normalize_text(
        " ".join(
            part
            for part in (
                term.label,
                local_name,
                term.definition,
                " ".join(super_labels),
                " ".join(domain_labels),
                " ".join(range_labels),
                term.termType,
                str(vocabulary.namespace),
            )
            if part
        )
    )

    return IndexedTerm(
        uri=str(term.uri),
        label=term.label,
        definition=term.definition,
        term_type=term.termType,
        vocabulary=str(vocabulary.namespace),
        super_terms=tuple(str(super_term) for super_term in super_terms),
        domain=tuple(str(domain_term) for domain_term in domain_terms),
        range_=tuple(str(range_term) for range_term in range_terms),
        label_norm=normalize_text(term.label),
        label_tokens=label_tokens,
        uri_local_name=local_name,
        uri_local_name_norm=normalize_text(local_name),
        uri_local_tokens=local_tokens,
        definition_norm=normalize_text(term.definition),
        definition_tokens=definition_tokens,
        super_term_labels=super_labels,
        super_term_tokens=super_tokens,
        domain_labels=domain_labels,
        domain_tokens=domain_tokens,
        range_labels=range_labels,
        range_tokens=range_tokens,
        searchable_text=searchable_text,
    )


def _index_vocabulary(
    vocabulary: RDFVocabulary,
    spec: Graph,
    labels_by_uri: LabelLookup,
) -> Generator[IndexedTerm, None, None]:

    term: VocabularyTerm
    for term in vocabulary.all_terms:
        # NOTE: if eventually needed
        # term_graph = spec.cbd(term.uri, include_reifications=False)

        super_rel: URIRef | None = None
        if term.termType == VocabularyTermType.CLASS:
            super_rel = RDFS.subClassOf
        elif term.termType == VocabularyTermType.PROPERTY:
            super_rel = RDFS.subPropertyOf

        super_terms: tuple[URIRef, ...] = ()
        if super_rel is not None:
            super_terms = _sorted_uris(
                (
                    obj
                    for obj in spec.transitive_objects(term.uri, super_rel)
                    if obj != term.uri
                ),
            )
        domain_terms = _sorted_uris(spec.objects(term.uri, RDFS.domain))
        range_terms = _sorted_uris(spec.objects(term.uri, RDFS.range))

        yield _index_term(
            vocabulary,
            term,
            super_terms,
            domain_terms,
            range_terms,
            labels_by_uri,
        )


def _sorted_uris(iterable: Iterable[Node | None]) -> tuple[URIRef, ...]:
    return tuple(sorted({obj for obj in iterable if isinstance(obj, URIRef)}, key=str))


def _lookup_label(uri: URIRef, labels_by_uri: LabelLookup) -> str:
    return labels_by_uri.get(str(uri), uri_local_name(str(uri)))


def _score_term(
    term: IndexedTerm, query_norm: str, query_tokens: tuple[str, ...]
) -> tuple[float, tuple[str, ...]]:
    score = 0.0
    reasons: list[str] = []

    if term.label_norm == query_norm:
        score += 100.0
        reasons.append("exact label match")
    elif query_norm == term.uri_local_name_norm:
        score += 90.0
        reasons.append("exact local name match")

    if term.label_norm.startswith(query_norm) and term.label_norm != query_norm:
        score += 20.0
        reasons.append("label prefix match")
    if (
        term.uri_local_name_norm.startswith(query_norm)
        and term.uri_local_name_norm != query_norm
    ):
        score += 16.0
        reasons.append("local name prefix match")

    label_overlap = _token_overlap(query_tokens, term.label_tokens)
    local_overlap = _token_overlap(query_tokens, term.uri_local_tokens)
    definition_overlap = _token_overlap(query_tokens, term.definition_tokens)
    super_overlap = _token_overlap(query_tokens, term.super_term_tokens)
    domain_overlap = _token_overlap(query_tokens, term.domain_tokens)
    range_overlap = _token_overlap(query_tokens, term.range_tokens)

    score += 10.0 * label_overlap
    score += 8.0 * local_overlap
    score += 4.0 * definition_overlap
    score += 3.0 * super_overlap
    score += 3.0 * domain_overlap
    score += 3.0 * range_overlap

    if label_overlap > 0:
        reasons.append("label token match")
    if local_overlap > 0:
        reasons.append("local name token match")
    if definition_overlap > 0:
        reasons.append("definition token match")
    if super_overlap > 0:
        reasons.append("superterm token match")
    if domain_overlap > 0:
        reasons.append("domain token match")
    if range_overlap > 0:
        reasons.append("range token match")

    if len(query_tokens) > 1 and query_norm in term.searchable_text:
        score += 12.0
        reasons.append("phrase match")

    return score, tuple(dict.fromkeys(reasons))


def _token_overlap(
    query_tokens: tuple[str, ...], field_tokens: tuple[str, ...]
) -> float:
    if len(query_tokens) == 0 or len(field_tokens) == 0:
        return 0.0
    query_token_set = set(query_tokens)
    field_token_set = set(field_tokens)
    return len(query_token_set & field_token_set) / len(query_token_set)
