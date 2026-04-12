from types import SimpleNamespace

from langchain_core.messages import ToolMessage
from rdflib import FOAF, OWL, PROV, RDF, RDFS, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DC
from rdflib_reasoning.middleware import (
    RDFVocabularyMiddleware,
    RDFVocabularyMiddlewareConfig,
    VocabularyConfiguration,
    VocabularyContext,
    VocabularyDeclaration,
)
from rdflib_reasoning.middleware.namespaces.spec_cache import UserSpec
from rdflib_reasoning.middleware.rdf_vocabulary_middleware import (
    VocabularyListResponse,
)


def _bundled_context() -> VocabularyContext:
    return VocabularyConfiguration.bundled_plus().build_context()


def _restricted_context() -> VocabularyContext:
    return VocabularyConfiguration(
        declarations=(
            VocabularyDeclaration(prefix="owl", namespace=OWL),
            VocabularyDeclaration(prefix="rdf", namespace=RDF),
            VocabularyDeclaration(prefix="rdfs", namespace=RDFS),
        )
    ).build_context()


def _middleware(
    vocabulary_context: VocabularyContext | None = None,
) -> RDFVocabularyMiddleware:
    return RDFVocabularyMiddleware(
        RDFVocabularyMiddlewareConfig(
            vocabulary_context=vocabulary_context or _bundled_context()
        )
    )


def test_list_terms_filters_classes() -> None:
    middleware = _middleware()

    terms = middleware.list_terms(str(RDFS), term_type="class", limit=50)

    assert len(terms) == 6
    assert all(term.termType == "class" for term in terms)
    assert URIRef("http://www.w3.org/2000/01/rdf-schema#Class") in {
        term.uri for term in terms
    }


def test_list_terms_filters_properties() -> None:
    middleware = _middleware()

    terms = middleware.list_terms(str(PROV), term_type="property", limit=10)

    assert len(terms) == 10
    assert all(term.termType == "property" for term in terms)


def test_list_terms_supports_offset() -> None:
    middleware = _middleware()

    first_page = middleware.list_terms(
        str(PROV), term_type="property", offset=0, limit=5
    )
    second_page = middleware.list_terms(
        str(PROV), term_type="property", offset=5, limit=5
    )

    assert len(first_page) == 5
    assert len(second_page) == 5
    assert {term.uri for term in first_page}.isdisjoint(
        {term.uri for term in second_page}
    )


def test_inspect_term_returns_compact_summary_with_optional_source_rdf() -> None:
    middleware = _middleware()

    summary = middleware.inspect_term("http://www.w3.org/2000/01/rdf-schema#Class")
    detailed = middleware.inspect_term(
        "http://www.w3.org/2000/01/rdf-schema#Class", include_source_rdf=True
    )

    assert summary.uri == URIRef("http://www.w3.org/2000/01/rdf-schema#Class")
    assert summary.termType == "class"
    assert summary.vocabulary == URIRef(str(RDFS))
    assert summary.source_rdf is None
    assert detailed.source_rdf is not None
    assert detailed.source_rdf.format == "turtle"
    assert "rdfs:Class" in detailed.source_rdf.content


def test_list_vocabularies_returns_curated_labels_and_descriptions() -> None:
    middleware = _middleware()

    vocabularies = {
        str(vocabulary.namespace): vocabulary
        for vocabulary in middleware.list_vocabularies()
    }

    assert vocabularies[str(RDF)].label == "RDF"
    assert "Core RDF data model terms" in vocabularies[str(RDF)].description
    assert vocabularies[str(RDFS)].label == "RDFS"
    assert "Schema-level RDF terms" in vocabularies[str(RDFS)].description
    assert vocabularies[str(OWL)].label == "OWL"
    assert "logical constraint terms" in vocabularies[str(OWL)].description
    assert vocabularies[str(PROV)].label == "PROV-O"
    assert "Provenance terms" in vocabularies[str(PROV)].description
    assert vocabularies[str(FOAF)].label == "FOAF"
    assert "social connections" in vocabularies[str(FOAF)].description


def test_list_vocabularies_uses_user_supplied_description() -> None:
    domain_ns = Namespace("urn:example:vocab#")
    graph = Graph(identifier=domain_ns)
    graph.add((URIRef(str(domain_ns)), RDF.type, OWL.Ontology))
    graph.add((URIRef(str(domain_ns)), DC.title, Literal("Example Task Vocabulary")))
    graph.add((URIRef(f"{domain_ns}Thing"), RDF.type, RDFS.Class))
    graph.add((URIRef(f"{domain_ns}Thing"), RDFS.isDefinedBy, URIRef(str(domain_ns))))
    graph.add((URIRef(f"{domain_ns}Thing"), RDFS.comment, Literal("A test term.")))

    middleware = _middleware(
        VocabularyConfiguration.bundled_plus(
            VocabularyDeclaration(
                prefix="example",
                namespace=domain_ns,
                user_spec=UserSpec(
                    graph=graph,
                    vocabulary=URIRef(str(domain_ns)),
                    label="Example Task Vocabulary",
                    description="Domain-specific terms for the current extraction task.",
                ),
            )
        ).build_context()
    )

    vocabularies = {
        str(vocabulary.namespace): vocabulary
        for vocabulary in middleware.list_vocabularies()
    }

    assert (
        vocabularies[str(domain_ns)].description
        == "Domain-specific terms for the current extraction task."
    )


def test_vocabulary_tool_schema_and_descriptions_are_agent_facing() -> None:
    middleware = _middleware()
    tools = {tool.name: tool for tool in middleware.tools}
    list_terms_schema = tools["list_terms"].get_input_schema().model_json_schema()
    inspect_term_schema = tools["inspect_term"].get_input_schema().model_json_schema()
    response_schema = VocabularyListResponse.model_json_schema()

    assert "offset" in tools["list_terms"].description
    assert "compact normalized summary" in tools["inspect_term"].description
    assert "MUST NOT repeat the same" in tools["list_terms"].description
    assert "MUST NOT repeat the same" in tools["inspect_term"].description
    assert len(list_terms_schema["properties"]["vocabulary"]["examples"]) >= 2
    assert len(list_terms_schema["properties"]["term_type"]["examples"]) >= 2
    assert len(list_terms_schema["properties"]["offset"]["examples"]) >= 2
    assert "paginating" in list_terms_schema["properties"]["offset"]["description"]
    assert len(inspect_term_schema["properties"]["term"]["examples"]) >= 2
    assert "include_source_rdf" in inspect_term_schema["properties"]
    assert (
        "compact summary provides"
        in inspect_term_schema["properties"]["include_source_rdf"]["description"]
    )
    assert "description" in response_schema["$defs"]["VocabularySummary"]["properties"]
    assert (
        "what the vocabulary is for"
        in response_schema["$defs"]["VocabularySummary"]["properties"]["description"][
            "description"
        ]
    )


def test_wrap_tool_call_rejects_repeated_identical_inspect_term_query() -> None:
    middleware = _middleware()
    inspect_tool = next(
        tool for tool in middleware.tools if tool.name == "inspect_term"
    )
    request = SimpleNamespace(
        tool=inspect_tool,
        tool_call={
            "id": "call-1",
            "name": "inspect_term",
            "args": {"term": str(RDFS.Class)},
        },
    )

    first = middleware.wrap_tool_call(
        request, lambda req: req.tool.invoke(req.tool_call["args"])
    )
    second = middleware.wrap_tool_call(
        request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    assert second != first
    assert isinstance(second, ToolMessage)
    assert second.status == "error"
    assert "repeated `inspect_term` query was rejected" in str(second.content)


def test_wrap_tool_call_allows_changed_inspect_term_query() -> None:
    middleware = _middleware()
    inspect_tool = next(
        tool for tool in middleware.tools if tool.name == "inspect_term"
    )
    first_request = SimpleNamespace(
        tool=inspect_tool,
        tool_call={
            "id": "call-1",
            "name": "inspect_term",
            "args": {"term": str(RDFS.Class)},
        },
    )
    second_request = SimpleNamespace(
        tool=inspect_tool,
        tool_call={
            "id": "call-2",
            "name": "inspect_term",
            "args": {"term": str(RDFS.Class), "include_source_rdf": True},
        },
    )

    middleware.wrap_tool_call(
        first_request, lambda req: req.tool.invoke(req.tool_call["args"])
    )
    second = middleware.wrap_tool_call(
        second_request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    assert not isinstance(second, ToolMessage) or second.status != "error"


def test_wrap_tool_call_rejects_repeated_identical_list_terms_query() -> None:
    middleware = _middleware()
    list_tool = next(tool for tool in middleware.tools if tool.name == "list_terms")
    request = SimpleNamespace(
        tool=list_tool,
        tool_call={
            "id": "call-1",
            "name": "list_terms",
            "args": {"vocabulary": str(PROV), "term_type": "property", "limit": 5},
        },
    )

    first = middleware.wrap_tool_call(
        request, lambda req: req.tool.invoke(req.tool_call["args"])
    )
    second = middleware.wrap_tool_call(
        request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    assert second != first
    assert isinstance(second, ToolMessage)
    assert second.status == "error"
    assert "repeated `list_terms` query was rejected" in str(second.content)


def test_wrap_tool_call_allows_paginated_list_terms_query() -> None:
    middleware = _middleware()
    list_tool = next(tool for tool in middleware.tools if tool.name == "list_terms")
    first_request = SimpleNamespace(
        tool=list_tool,
        tool_call={
            "id": "call-1",
            "name": "list_terms",
            "args": {"vocabulary": str(PROV), "term_type": "property", "limit": 5},
        },
    )
    second_request = SimpleNamespace(
        tool=list_tool,
        tool_call={
            "id": "call-2",
            "name": "list_terms",
            "args": {
                "vocabulary": str(PROV),
                "term_type": "property",
                "offset": 5,
                "limit": 5,
            },
        },
    )

    middleware.wrap_tool_call(
        first_request, lambda req: req.tool.invoke(req.tool_call["args"])
    )
    second = middleware.wrap_tool_call(
        second_request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    assert not isinstance(second, ToolMessage) or second.status != "error"


def test_list_vocabularies_filters_to_injected_whitelist() -> None:
    middleware = _middleware(_restricted_context())

    visible_vocabularies = {
        str(vocabulary.namespace) for vocabulary in middleware.list_vocabularies()
    }

    assert str(RDF) in visible_vocabularies
    assert str(RDFS) in visible_vocabularies
    assert str(OWL) in visible_vocabularies
    assert str(PROV) not in visible_vocabularies


def test_wrap_tool_call_rejects_disallowed_vocabulary_namespace() -> None:
    middleware = _middleware(_restricted_context())
    list_tool = next(tool for tool in middleware.tools if tool.name == "list_terms")
    request = SimpleNamespace(
        tool=list_tool,
        tool_call={
            "id": "call-1",
            "name": "list_terms",
            "args": {"vocabulary": str(PROV), "term_type": "property", "limit": 5},
        },
    )

    result = middleware.wrap_tool_call(
        request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "not allowed by the current vocabulary policy" in str(result.content)


def test_wrap_tool_call_returns_whitelist_nearest_matches_for_bad_term() -> None:
    middleware = _middleware(_restricted_context())
    inspect_tool = next(
        tool for tool in middleware.tools if tool.name == "inspect_term"
    )
    request = SimpleNamespace(
        tool=inspect_tool,
        tool_call={
            "id": "call-1",
            "name": "inspect_term",
            "args": {"term": "http://www.w3.org/2002/07/owl#Classs"},
        },
    )

    result = middleware.wrap_tool_call(
        request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "`owl:Class`" in str(result.content)


def test_wrap_tool_call_reports_allowed_but_unindexed_term_gracefully() -> None:
    ex = Namespace("urn:example:vocab#")
    middleware = _middleware(
        VocabularyConfiguration(
            declarations=(VocabularyDeclaration(prefix="ex", namespace=ex),)
        ).build_context()
    )
    inspect_tool = next(
        tool for tool in middleware.tools if tool.name == "inspect_term"
    )
    request = SimpleNamespace(
        tool=inspect_tool,
        tool_call={
            "id": "call-1",
            "name": "inspect_term",
            "args": {"term": f"{ex}Thing"},
        },
    )

    result = middleware.wrap_tool_call(
        request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "not available in the indexed vocabularies" in str(result.content)


def test_undeclared_foaf_is_not_visible_from_list_vocabularies() -> None:
    middleware = _middleware(
        VocabularyConfiguration(
            declarations=(
                VocabularyDeclaration(prefix="owl", namespace=OWL),
                VocabularyDeclaration(prefix="prov", namespace=PROV),
                VocabularyDeclaration(prefix="rdf", namespace=RDF),
                VocabularyDeclaration(prefix="rdfs", namespace=RDFS),
            )
        ).build_context()
    )

    visible_vocabularies = {
        str(vocabulary.namespace) for vocabulary in middleware.list_vocabularies()
    }

    assert str(FOAF) not in visible_vocabularies


def test_declared_foaf_is_visible_from_list_vocabularies() -> None:
    middleware = _middleware(
        VocabularyConfiguration.bundled_plus(
            VocabularyDeclaration(prefix="ex", namespace=Namespace("urn:example:task#"))
        ).build_context()
    )

    visible_vocabularies = {
        str(vocabulary.namespace) for vocabulary in middleware.list_vocabularies()
    }

    assert str(FOAF) in visible_vocabularies
