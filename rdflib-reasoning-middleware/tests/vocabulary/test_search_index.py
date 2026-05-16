from functools import cache

import pytest
from rdflib import FOAF, OWL, RDF, RDFS, Graph, Literal, Namespace, URIRef
from rdflib_reasoning.middleware import (
    VocabularyConfiguration,
    VocabularyContext,
    VocabularyDeclaration,
)
from rdflib_reasoning.middleware.namespaces.common import VocabularyTermType
from rdflib_reasoning.middleware.namespaces.spec_cache import UserVocabularySource
from rdflib_reasoning.middleware.vocabulary.search_index import (
    VocabularySearchIndex,
    normalize_text,
    tokenize,
)


@cache
def _bundled_context() -> VocabularyContext:
    return VocabularyConfiguration.bundled_plus().build_context()


@cache
def _build_homo_sapiens_context() -> tuple[VocabularyContext, URIRef]:
    ex = Namespace("https://example.com/ontology#")
    graph = Graph(identifier=ex)
    graph.add((URIRef(str(ex)), RDF.type, OWL.Ontology))

    homo_sapiens = URIRef(f"{ex}HomoSapiens")
    graph.add((homo_sapiens, RDF.type, RDFS.Class))
    graph.add((homo_sapiens, RDFS.isDefinedBy, URIRef(str(ex))))
    graph.add((homo_sapiens, RDFS.comment, Literal("The human species.")))

    context = VocabularyConfiguration.bundled_plus(
        VocabularyDeclaration(
            prefix="exterms",
            namespace=ex,
            user_spec=UserVocabularySource(
                graph=graph,
                vocabulary=URIRef(str(ex)),
                label="Example Ontology",
                description="Vocabulary for search normalization tests.",
            ),
        )
    ).build_context()
    return context, homo_sapiens


def test_search_index_preserves_cross_vocabulary_related_term_labels() -> None:
    search_index = _bundled_context().search_index
    maker = search_index.terms_by_uri[str(FOAF.maker)]
    made = search_index.terms_by_uri[str(FOAF.made)]

    assert str(OWL.Thing) in maker.domain
    assert "Thing" in maker.domain_labels
    assert str(OWL.Thing) in made.range_
    assert "Thing" in made.range_labels


def test_search_prefers_exact_label_matches() -> None:
    search_index = _bundled_context().search_index

    response = search_index.search("Person", vocabularies=(str(FOAF),), limit=5)

    assert response.hits[0].uri == URIRef(str(FOAF.Person))
    assert "exact label match" in response.hits[0].why_matched


def test_search_matches_uri_local_name_tokens() -> None:
    search_index = _bundled_context().search_index

    response = search_index.search("img", vocabularies=(str(FOAF),), limit=5)

    assert response.hits[0].uri == URIRef(str(FOAF.img))
    assert "exact local name match" in response.hits[0].why_matched


def test_search_supports_vocabulary_and_term_type_filters() -> None:
    search_index = _bundled_context().search_index

    response = search_index.search(
        "Class",
        vocabularies=(str(RDFS),),
        term_types=(VocabularyTermType.CLASS,),
        limit=10,
    )

    assert len(response.hits) > 0
    assert all(hit.vocabulary == URIRef(str(RDFS)) for hit in response.hits)
    assert all(hit.termType == VocabularyTermType.CLASS for hit in response.hits)


def test_search_uses_structural_labels_from_related_terms() -> None:
    search_index = _bundled_context().search_index

    response = search_index.search(
        "Thing agent",
        vocabularies=(str(FOAF),),
        term_types=(VocabularyTermType.PROPERTY,),
        limit=25,
    )

    uris = {hit.uri for hit in response.hits}

    assert URIRef(str(FOAF.maker)) in uris
    assert URIRef(str(FOAF.made)) in uris


def test_search_returns_empty_hits_for_blank_query() -> None:
    search_index = _bundled_context().search_index

    response = search_index.search("   ")

    assert response.hits == ()


def test_search_prefers_exact_label_over_definition_only_match() -> None:
    ex = Namespace("urn:example:search#")
    graph = Graph(identifier=ex)
    graph.add((URIRef(str(ex)), RDF.type, OWL.Ontology))

    alpha = URIRef(f"{ex}alpha")
    beta = URIRef(f"{ex}beta")
    graph.add((alpha, RDF.type, RDF.Property))
    graph.add((alpha, RDFS.isDefinedBy, URIRef(str(ex))))
    graph.add((alpha, RDFS.label, Literal("alpha")))
    graph.add((alpha, RDFS.comment, Literal("An alpha property.")))

    graph.add((beta, RDF.type, RDF.Property))
    graph.add((beta, RDFS.isDefinedBy, URIRef(str(ex))))
    graph.add((beta, RDFS.label, Literal("secondary")))
    graph.add((beta, RDFS.comment, Literal("This definition mentions alpha.")))

    context = VocabularyConfiguration.bundled_plus(
        VocabularyDeclaration(
            prefix="ex",
            namespace=ex,
            user_spec=UserVocabularySource(
                graph=graph,
                vocabulary=URIRef(str(ex)),
                label="Example Search Vocabulary",
                description="Terms used for lexical search tests.",
            ),
        )
    ).build_context()
    search_index = VocabularySearchIndex.build(context)

    response = search_index.search(
        "alpha",
        vocabularies=(str(ex),),
        term_types=(VocabularyTermType.PROPERTY,),
        limit=5,
    )

    assert response.hits[0].uri == alpha
    assert "exact label match" in response.hits[0].why_matched


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("homo-sapiens", "homo sapiens"),
        ("homo_sapiens", "homo sapiens"),
        ("HOMO_SAPIENS", "homo sapiens"),
        ("homoSapiens", "homo sapiens"),
        ("HomoSapiens", "homo sapiens"),
    ],
)
def test_normalize_text_supports_common_identifier_variants(
    value: str, expected: str
) -> None:
    assert normalize_text(value) == expected
    assert tokenize(value) == ("homo", "sapiens")


@pytest.mark.parametrize(
    "query",
    (
        "homo-sapiens",
        "homo_sapiens",
        "HOMO_SAPIENS",
        "homoSapiens",
        "HomoSapiens",
    ),
)
def test_search_matches_common_identifier_variants(query: str) -> None:
    context, homo_sapiens = _build_homo_sapiens_context()
    search_index = context.search_index

    response = search_index.search(
        query,
        vocabularies=("https://example.com/ontology#",),
        term_types=(VocabularyTermType.CLASS,),
        limit=5,
    )

    assert len(response.hits) > 0
    assert response.hits[0].uri == homo_sapiens
    assert "local name token match" in response.hits[0].why_matched or (
        "exact local name match" in response.hits[0].why_matched
    )
