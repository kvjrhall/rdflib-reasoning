import logging
from collections.abc import Generator
from importlib import resources

import pytest
import rdflib_reasoning.middleware.namespaces
from rdflib import PROV, RDF, RDFS, Graph, Literal, Namespace, URIRef
from rdflib.graph import ReadOnlyGraphAggregate
from rdflib.namespace import DC, OWL
from rdflib_reasoning.middleware.namespaces.spec_cache import (
    SpecificationCache,
    UserSpec,
)
from rdflib_reasoning.middleware.namespaces.spec_index import RDFVocabulary


@pytest.fixture(scope="session")
def rdfs_graph() -> Generator[Graph, None, None]:
    with resources.path(rdflib_reasoning.middleware.namespaces, "rdfs.ttl") as path:
        graph = Graph()
        graph.parse(path, format="turtle")
        graph = ReadOnlyGraphAggregate([graph])
        yield graph


@pytest.fixture(scope="session")
def prov_graph() -> Generator[Graph, None, None]:
    with resources.path(rdflib_reasoning.middleware.namespaces, "prov-o.ttl") as path:
        graph = Graph()
        graph.parse(path, format="turtle")
        graph = ReadOnlyGraphAggregate([graph])
        yield graph


def test_vocab_term_counts_rdfs(rdfs_graph: Graph) -> None:
    vocabulary = RDFVocabulary.from_graph(RDFS, rdfs_graph)
    assert len(vocabulary.all_terms) == 15

    assert len(vocabulary.classes) == 6
    assert len(vocabulary.datatypes) == 0
    assert len(vocabulary.individuals) == 0
    assert len(vocabulary.properties) == 9


def test_vocab_term_counts_prov(prov_graph: Graph) -> None:
    vocabulary = RDFVocabulary.from_graph(PROV, prov_graph)
    assert len(vocabulary.all_terms) == 94

    assert len(vocabulary.classes) == 30
    assert len(vocabulary.datatypes) == 0
    assert len(vocabulary.individuals) == 0
    assert len(vocabulary.properties) == 64

    had_member = next(
        term
        for term in vocabulary.properties
        if term.uri == URIRef("http://www.w3.org/ns/prov#hadMember")
    )
    assert "collection is an entity" in had_member.definition.lower()
    assert had_member.termType == "property"

    was_invalidated_by = next(
        term
        for term in vocabulary.properties
        if term.uri == URIRef("http://www.w3.org/ns/prov#wasInvalidatedBy")
    )
    assert "invalidation is the start of the destruction" in (
        was_invalidated_by.definition.lower()
    )


def test_specification_cache_lazily_builds_normalized_vocabularies() -> None:
    cache = SpecificationCache(bundled_namespaces=(RDFS,))

    vocabulary = cache.get_vocabulary(RDFS)

    assert vocabulary.namespace == URIRef(str(RDFS))
    assert len(vocabulary.all_terms) == 15
    assert cache.get_vocabulary(RDFS) is vocabulary


def test_user_spec_from_graph_infers_namespace_and_description_without_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    graph = Graph()
    namespace = URIRef("urn:example:inferred#")
    graph.add((namespace, RDF.type, OWL.Ontology))
    graph.add((namespace, DC.description, Literal("An inferred description.")))

    with caplog.at_level(logging.WARNING):
        user_spec = UserSpec.from_graph(graph)

    assert user_spec.vocabulary == namespace
    assert user_spec.description == "An inferred description."
    assert len(caplog.records) == 0


def test_user_spec_from_graph_falls_back_to_comment_then_title_then_default() -> None:
    comment_graph = Graph()
    comment_namespace = URIRef("urn:example:comment#")
    comment_graph.add((comment_namespace, RDF.type, OWL.Ontology))
    comment_graph.add((comment_namespace, RDFS.comment, Literal("Comment fallback.")))

    title_graph = Graph()
    title_namespace = URIRef("urn:example:title#")
    title_graph.add((title_namespace, RDF.type, OWL.Ontology))
    title_graph.add((title_namespace, DC.title, Literal("Title fallback")))

    default_graph = Graph(identifier=URIRef("urn:example:default#"))

    assert UserSpec.from_graph(comment_graph).description == "Comment fallback."
    assert UserSpec.from_graph(title_graph).description == "Title fallback"
    assert (
        UserSpec.from_graph(default_graph).description
        == "The user supplied this RDF vocabulary for your task."
    )


def test_specification_cache_derives_non_bundled_metadata_from_graph() -> None:
    namespace = Namespace("urn:example:metadata#")
    graph = Graph(identifier=namespace)
    graph.add((URIRef(str(namespace)), RDF.type, OWL.Ontology))
    graph.add(
        (URIRef(str(namespace)), DC.title, Literal("Example Metadata Vocabulary"))
    )
    graph.add(
        (
            URIRef(str(namespace)),
            RDFS.comment,
            Literal("Terms for metadata fallback coverage."),
        )
    )
    graph.add((URIRef(f"{namespace}Thing"), RDF.type, RDFS.Class))
    graph.add((URIRef(f"{namespace}Thing"), RDFS.isDefinedBy, URIRef(str(namespace))))
    graph.add((URIRef(f"{namespace}Thing"), RDFS.comment, Literal("A test class.")))

    cache = SpecificationCache(
        bundled_namespaces=(),
        user_specs=(UserSpec.from_graph(graph),),
    )

    metadata = cache.get_vocabulary_metadata(namespace)

    assert metadata.label == "Example Metadata Vocabulary"
    assert metadata.description == "Terms for metadata fallback coverage."
