from collections.abc import Generator
from importlib import resources

import pytest
import rdflibr.middleware.namespaces
from rdflib import PROV, RDFS, Graph, URIRef
from rdflib.graph import ReadOnlyGraphAggregate
from rdflibr.middleware.namespaces.spec_cache import SpecificationCache
from rdflibr.middleware.namespaces.spec_index import RDFVocabulary


@pytest.fixture(scope="session")
def rdfs_graph() -> Generator[Graph, None, None]:
    with resources.path(rdflibr.middleware.namespaces, "rdfs.ttl") as path:
        graph = Graph()
        graph.parse(path, format="turtle")
        graph = ReadOnlyGraphAggregate([graph])
        yield graph


@pytest.fixture(scope="session")
def prov_graph() -> Generator[Graph, None, None]:
    with resources.path(rdflibr.middleware.namespaces, "prov-o.ttl") as path:
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
    cache = SpecificationCache()

    vocabulary = cache.get_vocabulary(RDFS)

    assert vocabulary.namespace == URIRef(str(RDFS))
    assert len(vocabulary.all_terms) == 15
    assert cache.get_vocabulary(RDFS) is vocabulary
