import pytest
from rdflib import FOAF, OWL, RDF, RDFS, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAM, DCMITYPE, DCTERMS, PROV, SKOS, VANN
from rdflib_reasoning.middleware import (
    DatasetMiddleware,
    DatasetMiddlewareConfig,
    DatasetRuntime,
    RDFVocabularyMiddleware,
    RDFVocabularyMiddlewareConfig,
    RunTermTelemetry,
    VocabularyConfiguration,
    VocabularyDeclaration,
)
from rdflib_reasoning.middleware.dataset_middleware import WhitelistViolation
from rdflib_reasoning.middleware.namespaces.spec_cache import UserVocabularySource


def _build_domain_graph(namespace: Namespace) -> Graph:
    graph = Graph(identifier=namespace)
    graph.add((URIRef(str(namespace)), RDF.type, OWL.Ontology))
    graph.add((URIRef(str(namespace)), RDFS.comment, Literal("Task-specific terms.")))
    graph.add((URIRef(f"{namespace}Thing"), RDF.type, RDFS.Class))
    graph.add((URIRef(f"{namespace}Thing"), RDFS.isDefinedBy, URIRef(str(namespace))))
    graph.add((URIRef(f"{namespace}Thing"), RDFS.comment, Literal("A task term.")))
    return graph


def test_build_context_exposes_cached_whitelist_and_specification_cache() -> None:
    ex = Namespace("urn:example:vocab#")
    configuration = VocabularyConfiguration(
        declarations=(
            VocabularyDeclaration(
                prefix="ex",
                namespace=ex,
                user_spec=UserVocabularySource(
                    graph=_build_domain_graph(ex),
                    vocabulary=URIRef(str(ex)),
                    description="Task-specific terms.",
                ),
            ),
            VocabularyDeclaration(prefix="rdf", namespace=RDF),
        )
    )

    context = configuration.build_context()

    assert context.whitelist.allows_namespace(str(ex)) is True
    assert context.whitelist.allows_namespace(str(RDF)) is True
    assert context.specification_cache.get_vocabulary(ex).namespace == URIRef(str(ex))
    assert context.specification_cache.get_vocabulary(RDF).namespace == URIRef(str(RDF))


def test_context_indexes_only_declared_bundled_vocabularies() -> None:
    configuration = VocabularyConfiguration(
        declarations=(VocabularyDeclaration(prefix="rdf", namespace=RDF),)
    )

    context = configuration.build_context()

    assert str(RDF) in context.indexed_vocabularies
    assert str(RDFS) not in context.indexed_vocabularies
    assert str(OWL) not in context.indexed_vocabularies


def test_declared_open_namespace_without_user_spec_is_allowed_but_not_indexed() -> None:
    ex = Namespace("urn:example:open#")
    context = VocabularyConfiguration(
        declarations=(VocabularyDeclaration(prefix="ex", namespace=ex),)
    ).build_context()

    assert context.whitelist.allows_namespace(str(ex)) is True
    assert str(ex) not in context.indexed_vocabularies


def test_indexed_vocabularies_are_always_whitelisted() -> None:
    ex = Namespace("urn:example:vocab#")
    context = VocabularyConfiguration.bundled_plus(
        VocabularyDeclaration(
            prefix="ex",
            namespace=ex,
            user_spec=UserVocabularySource(
                graph=_build_domain_graph(ex),
                vocabulary=URIRef(str(ex)),
                description="Task-specific terms.",
            ),
        )
    ).build_context()

    assert all(
        context.whitelist.allows_namespace(namespace)
        for namespace in context.indexed_vocabularies
    )


def test_bundled_plus_includes_repository_standard_bundled_vocabularies() -> None:
    ex = Namespace("urn:example:task#")
    context = VocabularyConfiguration.bundled_plus(
        VocabularyDeclaration(prefix="ex", namespace=ex)
    ).build_context()

    assert str(FOAF) in context.indexed_vocabularies
    assert str(OWL) in context.indexed_vocabularies
    assert str(PROV) in context.indexed_vocabularies
    assert str(RDF) in context.indexed_vocabularies
    assert str(RDFS) in context.indexed_vocabularies
    assert str(SKOS) in context.indexed_vocabularies
    assert str(VANN) not in context.indexed_vocabularies
    assert str(DCAM) not in context.indexed_vocabularies
    assert str(DCMITYPE) not in context.indexed_vocabularies
    assert str(DCTERMS) not in context.indexed_vocabularies
    assert context.whitelist.allows_namespace(str(ex)) is True


def test_standard_bundled_declarations_map_to_loadable_resources() -> None:
    context = VocabularyConfiguration.bundled_plus().build_context()

    for namespace in context.indexed_vocabularies:
        graph = context.specification_cache.get_spec(namespace)
        assert len(graph) > 0


def test_shared_context_can_be_injected_into_both_middlewares() -> None:
    ex = Namespace("urn:example:vocab#")
    context = VocabularyConfiguration.bundled_plus(
        VocabularyDeclaration(
            prefix="ex",
            namespace=ex,
            user_spec=UserVocabularySource(
                graph=_build_domain_graph(ex),
                vocabulary=URIRef(str(ex)),
                description="Task-specific terms.",
            ),
        )
    ).build_context()
    runtime = DatasetRuntime()
    telemetry = RunTermTelemetry()

    dataset_middleware = DatasetMiddleware(
        DatasetMiddlewareConfig(
            vocabulary_context=context,
            runtime=runtime,
            run_term_telemetry=telemetry,
        )
    )
    vocabulary_middleware = RDFVocabularyMiddleware(
        RDFVocabularyMiddlewareConfig(
            vocabulary_context=context,
            run_term_telemetry=telemetry,
        )
    )
    triple = (URIRef(f"{ex}Thing"), RDF.type, RDFS.Class)

    dataset_middleware.add_triples([triple])

    assert telemetry.asserted_term_count(triple[0]) == 1
    assert str(ex) in {
        str(vocabulary.namespace)
        for vocabulary in vocabulary_middleware.list_vocabularies()
    }


def test_context_without_foaf_makes_foaf_impossible_across_middlewares() -> None:
    ex = Namespace("urn:example:")
    context = VocabularyConfiguration(
        declarations=(
            VocabularyDeclaration(prefix="ex", namespace=ex),
            VocabularyDeclaration(prefix="owl", namespace=OWL),
            VocabularyDeclaration(prefix="prov", namespace=PROV),
            VocabularyDeclaration(prefix="rdf", namespace=RDF),
            VocabularyDeclaration(prefix="rdfs", namespace=RDFS),
        )
    ).build_context()
    dataset_middleware = DatasetMiddleware(
        DatasetMiddlewareConfig(vocabulary_context=context)
    )
    vocabulary_middleware = RDFVocabularyMiddleware(
        RDFVocabularyMiddlewareConfig(vocabulary_context=context)
    )

    assert str(FOAF) not in {
        str(vocabulary.namespace)
        for vocabulary in vocabulary_middleware.list_vocabularies()
    }
    with pytest.raises(WhitelistViolation):
        dataset_middleware.add_triples(
            [(URIRef(f"{ex}john"), RDF.type, URIRef(f"{FOAF}Person"))]
        )


def test_context_with_foaf_allows_foaf_across_middlewares() -> None:
    ex = Namespace("urn:example:")
    context = VocabularyConfiguration.bundled_plus(
        VocabularyDeclaration(prefix="ex", namespace=ex)
    ).build_context()
    dataset_middleware = DatasetMiddleware(
        DatasetMiddlewareConfig(vocabulary_context=context)
    )
    vocabulary_middleware = RDFVocabularyMiddleware(
        RDFVocabularyMiddlewareConfig(vocabulary_context=context)
    )
    triple = (URIRef(f"{ex}john"), RDF.type, URIRef(f"{FOAF}Person"))

    assert str(FOAF) in {
        str(vocabulary.namespace)
        for vocabulary in vocabulary_middleware.list_vocabularies()
    }
    response = dataset_middleware.add_triples([triple])

    assert response.updated == 1


def test_plus_returns_new_configuration_without_mutating_original() -> None:
    base = VocabularyConfiguration.bundled_plus()

    extended = base.plus(VocabularyDeclaration(prefix="vann", namespace=VANN))

    assert str(VANN) not in {
        declaration.namespace_uri for declaration in base.declarations
    }
    assert str(VANN) in {
        declaration.namespace_uri for declaration in extended.declarations
    }


def test_plus_overrides_existing_declaration_by_namespace() -> None:
    base = VocabularyConfiguration.bundled_plus()

    overridden = base.plus(
        VocabularyDeclaration(prefix="rdfs-alt", namespace=RDFS),
    )

    declarations = {
        declaration.namespace_uri: declaration
        for declaration in overridden.declarations
    }

    assert declarations[str(RDFS)].prefix == "rdfs-alt"


def test_explicit_non_default_bundled_vocabulary_is_still_indexed() -> None:
    context = VocabularyConfiguration(
        declarations=(VocabularyDeclaration(prefix="vann", namespace=VANN),)
    ).build_context()

    assert str(VANN) in context.indexed_vocabularies


def test_plus_dublin_core_adds_all_three_extended_dublin_core_vocabularies() -> None:
    context = VocabularyConfiguration.bundled_plus().plus_dublin_core().build_context()

    assert str(DCAM) in context.indexed_vocabularies
    assert str(DCMITYPE) in context.indexed_vocabularies
    assert str(DCTERMS) in context.indexed_vocabularies


def test_plus_vann_adds_vann_explicitly() -> None:
    context = VocabularyConfiguration.bundled_plus().plus_vann().build_context()

    assert str(VANN) in context.indexed_vocabularies
