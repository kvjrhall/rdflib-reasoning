import logging
import warnings
from collections.abc import Generator
from importlib import resources

import pytest
import rdflib_reasoning.middleware.namespaces
from rdflib import PROV, RDF, RDFS, Graph, Literal, Namespace, URIRef
from rdflib.graph import ReadOnlyGraphAggregate
from rdflib.namespace import DC, OWL
from rdflib_reasoning.middleware.namespaces.spec_cache import (
    _BUNDLED_SPEC_FILENAMES,
    _BUNDLED_VOCABULARY_METADATA,
    SpecificationCache,
    UserSpec,
)
from rdflib_reasoning.middleware.namespaces.spec_index import RDFVocabulary
from rdflib_reasoning.middleware.namespaces.spec_normalizer import (
    DefinitionWarning,
    LabelWarning,
)


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


@pytest.mark.parametrize(
    ("namespace", "filename"),
    sorted(_BUNDLED_SPEC_FILENAMES.items()),
)
def test_bundled_vocabulary_normalization_emits_no_label_or_definition_warnings(
    namespace: str, filename: str
) -> None:
    cache = SpecificationCache(bundled_namespaces=(namespace,))

    with warnings.catch_warnings():
        warnings.simplefilter("error", LabelWarning)
        warnings.simplefilter("error", DefinitionWarning)
        vocabulary = cache.get_vocabulary(namespace)

    assert len(vocabulary.all_terms) > 0, filename


@pytest.mark.parametrize("namespace", sorted(_BUNDLED_SPEC_FILENAMES))
def test_bundled_vocabulary_terms_have_explicit_labels_in_source_graph(
    namespace: str,
) -> None:
    cache = SpecificationCache(bundled_namespaces=(namespace,))
    graph = cache.get_spec(namespace)
    vocabulary = cache.get_vocabulary(namespace)

    missing_labels = sorted(
        str(term.uri)
        for term in vocabulary.all_terms
        if not isinstance(graph.value(term.uri, RDFS.label), Literal)
        # NOTE: We give annotation properties a pass when it comes to labels.
        and (term.uri, RDF.type, OWL.AnnotationProperty) not in graph
    )

    assert missing_labels == [], (
        f"{len(missing_labels)} Terms SHOULD have explicit labels in source graph: {missing_labels}"
    )


@pytest.mark.parametrize("namespace", sorted(_BUNDLED_SPEC_FILENAMES))
def test_bundled_vocabulary_terms_have_no_placeholder_or_lexicalized_metadata(
    namespace: str,
) -> None:
    from rdflib_reasoning.middleware.namespaces.spec_normalizer import (
        _KNOWN_MISSING_DEFINITIONS,
    )

    cache = SpecificationCache(bundled_namespaces=(namespace,))
    vocabulary = cache.get_vocabulary(namespace)

    invalid_terms = sorted(
        str(term.uri)
        for term in vocabulary.all_terms
        if term.uri not in _KNOWN_MISSING_DEFINITIONS
        and (
            "<literal_definition_missing>" in term.definition
            or "<literal_definition_lexical_form>" in term.definition
            or "<literal_label_lexical_form>" in term.label
        )
    )

    assert invalid_terms == [], (
        f"{len(invalid_terms)} Terms MUST NOT have placeholder definitions: {invalid_terms}"
    )


@pytest.mark.parametrize("namespace", sorted(_BUNDLED_SPEC_FILENAMES))
def test_bundled_vocabulary_has_curated_vocabulary_metadata(namespace: str) -> None:
    cache = SpecificationCache(bundled_namespaces=(namespace,))
    metadata = cache.get_vocabulary_metadata(namespace)

    assert namespace in _BUNDLED_VOCABULARY_METADATA
    assert metadata.label.strip() != ""
    assert metadata.description.strip() != ""
    assert metadata.label != namespace
    assert metadata.description != namespace
