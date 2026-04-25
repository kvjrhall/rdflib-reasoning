from importlib.util import module_from_spec, spec_from_file_location
from json import loads as json_loads
from pathlib import Path
from types import SimpleNamespace

from langchain_core.messages import SystemMessage, ToolMessage
from rdflib import FOAF, OWL, PROV, RDF, RDFS, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DC, SKOS, VANN
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
from rdflib_reasoning.middleware.vocabulary.search_model import TermSearchResponse


def _load_demo_utils() -> object:
    spec = spec_from_file_location(
        "demo_utils",
        Path(__file__).resolve().parents[2] / "notebooks" / "demo_utils.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _mark_list_vocabularies_called(middleware: RDFVocabularyMiddleware) -> None:
    list_tool = next(
        tool for tool in middleware.tools if tool.name == "list_vocabularies"
    )
    list_request = SimpleNamespace(
        tool=list_tool,
        tool_call={
            "id": "call-list",
            "name": "list_vocabularies",
            "args": {},
        },
    )
    middleware.wrap_tool_call(
        list_request, lambda req: req.tool.invoke(req.tool_call["args"])
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


def test_search_terms_returns_ranked_candidates() -> None:
    middleware = _middleware()

    response = middleware.search_terms(
        "maker",
        vocabularies=(str(FOAF),),
        term_types=("property",),
        limit=5,
    )

    assert len(response.hits) > 0
    assert response.hits[0].uri == URIRef(str(FOAF.maker))
    assert "exact label match" in response.hits[0].why_matched


def test_search_terms_tool_invoke_returns_structured_response() -> None:
    middleware = _middleware()
    search_tool = next(tool for tool in middleware.tools if tool.name == "search_terms")

    result = search_tool.invoke(
        {"query": "maker", "vocabularies": [str(FOAF)], "term_types": ["property"]}
    )

    assert isinstance(result, str)
    parsed = json_loads(result)
    assert parsed["query"] == "maker"
    assert len(parsed["hits"]) > 0
    assert parsed["hits"][0]["uri"] == f"<{FOAF.maker}>"


def test_search_terms_domain_api_returns_structured_response() -> None:
    middleware = _middleware()
    response = middleware.search_terms(
        "maker",
        vocabularies=(str(FOAF),),
        term_types=("property",),
        limit=5,
    )

    assert isinstance(response, TermSearchResponse)
    assert len(response.hits) > 0
    assert response.hits[0].uri == URIRef(str(FOAF.maker))


def test_list_vocabularies_tool_invoke_returns_json_content() -> None:
    middleware = _middleware()
    list_tool = next(
        tool for tool in middleware.tools if tool.name == "list_vocabularies"
    )

    result = list_tool.invoke({})

    assert isinstance(result, str)
    parsed = json_loads(result)
    assert isinstance(parsed["vocabularies"], list)
    assert any(item["namespace"] == f"<{RDF}>" for item in parsed["vocabularies"])


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
    assert vocabularies[str(SKOS)].label == "SKOS"
    assert "Knowledge Organization System" in vocabularies[str(SKOS)].description
    assert str(VANN) not in vocabularies


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


def test_list_vocabularies_shows_vann_only_when_explicitly_added() -> None:
    middleware = _middleware(
        VocabularyConfiguration.bundled_plus().plus_vann().build_context()
    )

    vocabularies = {
        str(vocabulary.namespace): vocabulary
        for vocabulary in middleware.list_vocabularies()
    }

    assert str(VANN) in vocabularies


def test_vocabulary_tool_schema_and_descriptions_are_agent_facing() -> None:
    middleware = _middleware()
    tools = {tool.name: tool for tool in middleware.tools}
    search_terms_schema = tools["search_terms"].get_input_schema().model_json_schema()
    list_terms_schema = tools["list_terms"].get_input_schema().model_json_schema()
    inspect_term_schema = tools["inspect_term"].get_input_schema().model_json_schema()
    response_schema = VocabularyListResponse.model_json_schema()

    assert "meaning you want to express" in tools["search_terms"].description
    assert "draft graph shape" in tools["search_terms"].description
    assert "switch to `list_terms`" in tools["search_terms"].description
    assert "MUST NOT repeat the same" in tools["search_terms"].description
    assert "offset" in tools["list_terms"].description
    assert "bounded familiarization pass" in tools["list_terms"].description
    assert "compact normalized summary" in tools["inspect_term"].description
    assert "Do not use repeated" in tools["inspect_term"].description
    assert len(search_terms_schema["properties"]["query"]["description"]) > 0
    assert "vocabularies" in search_terms_schema["properties"]
    assert "term_types" in search_terms_schema["properties"]
    assert "limit" in search_terms_schema["properties"]
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


def test_vocabulary_system_prompt_teaches_familiarization_transition() -> None:
    middleware = _middleware()

    prompt = middleware._build_vocabulary_system_prompt()

    assert "draft graph shape" in prompt
    assert "`search_terms`" in prompt
    assert "If you know the meaning you want to express" in prompt
    assert (
        "Prefer `search_terms` when you know the meaning you want to express" in prompt
    )
    assert "pause term-by-term lookup" in prompt
    assert "scan that vocabulary" in prompt
    assert "small `term_count`" in prompt
    assert "minting overlapping local terms" in prompt
    assert "skip directly from `list_vocabularies`" in prompt
    assert "Do not mint local classes or properties that overlap" in prompt
    assert "Indexed Vocabularies Available Here" not in prompt
    assert "FOAF (" not in prompt


def test_demo_utils_vocabulary_tips_and_stopping_criteria_mirror_familiarization() -> (
    None
):
    demo_utils = _load_demo_utils()

    vocabulary_tips = demo_utils.VOCABULARY_TIPS
    stopping_criteria = demo_utils.STOPPING_CRITERIA

    assert "draft graph shape" in vocabulary_tips
    assert "familiarize yourself with that ontology" in vocabulary_tips
    assert "bounded familiarization pass" in vocabulary_tips
    assert "one or two plausible hits by themselves" in vocabulary_tips
    assert (
        "small relevant ontology has not yet been given one bounded familiarization"
        in stopping_criteria
    )


def test_wrap_model_call_requires_list_vocabularies_first_until_it_has_run() -> None:
    middleware = _middleware()
    captured: dict[str, object] = {}

    class FakeRequest:
        def __init__(self, system_message: SystemMessage) -> None:
            self.system_message = system_message

        def override(self, *, system_message: object) -> "FakeRequest":
            assert isinstance(system_message, SystemMessage)
            return FakeRequest(system_message)

    request = FakeRequest(SystemMessage(content="Base system prompt"))

    def handler(req: FakeRequest) -> str:
        captured["system_message"] = req.system_message
        return "ok"

    middleware.wrap_model_call(request, handler)

    system_message = str(captured["system_message"])
    assert (
        "Your next vocabulary action MUST be a `list_vocabularies` tool call"
        in system_message
    )

    list_tool = next(
        tool for tool in middleware.tools if tool.name == "list_vocabularies"
    )
    list_request = SimpleNamespace(
        tool=list_tool,
        tool_call={
            "id": "call-list",
            "name": "list_vocabularies",
            "args": {},
        },
    )
    middleware.wrap_tool_call(
        list_request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    captured.clear()
    middleware.wrap_model_call(request, handler)
    system_message = str(captured["system_message"])
    assert (
        "Your next vocabulary action MUST be a `list_vocabularies` tool call"
        not in system_message
    )


def test_wrap_tool_call_rejects_other_vocabulary_tools_before_list_vocabularies() -> (
    None
):
    middleware = _middleware()
    search_tool = next(tool for tool in middleware.tools if tool.name == "search_terms")
    request = SimpleNamespace(
        tool=search_tool,
        tool_call={
            "id": "call-1",
            "name": "search_terms",
            "args": {"query": "maker", "limit": 5},
        },
    )

    result = middleware.wrap_tool_call(
        request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "required before any other vocabulary tool" in str(result.content)


def test_wrap_tool_call_allows_non_vocabulary_tools_before_list_vocabularies() -> None:
    middleware = _middleware()
    request = SimpleNamespace(
        tool=None,
        tool_call={
            "id": "call-1",
            "name": "write_todos",
            "args": {"todos": [{"content": "plan", "status": "in_progress"}]},
        },
    )

    result = middleware.wrap_tool_call(
        request,
        lambda req: ToolMessage(
            content="ok",
            name=req.tool_call["name"],
            tool_call_id=req.tool_call["id"],
            status="success",
        ),
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "success"
    assert str(result.content) == "ok"


def test_wrap_tool_call_rejects_repeated_identical_inspect_term_query() -> None:
    middleware = _middleware()
    _mark_list_vocabularies_called(middleware)
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
    _mark_list_vocabularies_called(middleware)
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
    _mark_list_vocabularies_called(middleware)
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


def test_wrap_tool_call_rejects_repeated_identical_search_terms_query() -> None:
    middleware = _middleware()
    _mark_list_vocabularies_called(middleware)
    search_tool = next(tool for tool in middleware.tools if tool.name == "search_terms")
    request = SimpleNamespace(
        tool=search_tool,
        tool_call={
            "id": "call-1",
            "name": "search_terms",
            "args": {"query": "maker", "vocabularies": [str(FOAF)], "limit": 5},
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
    assert "repeated `search_terms` query was rejected" in str(second.content)


def test_wrap_tool_call_rejects_non_consecutive_repeated_search_terms_query() -> None:
    middleware = _middleware()
    _mark_list_vocabularies_called(middleware)
    search_tool = next(tool for tool in middleware.tools if tool.name == "search_terms")
    first_request = SimpleNamespace(
        tool=search_tool,
        tool_call={
            "id": "call-1",
            "name": "search_terms",
            "args": {"query": "classified as", "limit": 5},
        },
    )
    second_request = SimpleNamespace(
        tool=search_tool,
        tool_call={
            "id": "call-2",
            "name": "search_terms",
            "args": {"query": "falls under", "limit": 5},
        },
    )
    repeated_first_request = SimpleNamespace(
        tool=search_tool,
        tool_call={
            "id": "call-3",
            "name": "search_terms",
            "args": {"query": "classified as", "limit": 5},
        },
    )

    middleware.wrap_tool_call(
        first_request, lambda req: req.tool.invoke(req.tool_call["args"])
    )
    middleware.wrap_tool_call(
        second_request, lambda req: req.tool.invoke(req.tool_call["args"])
    )
    repeated = middleware.wrap_tool_call(
        repeated_first_request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    assert isinstance(repeated, ToolMessage)
    assert repeated.status == "error"
    assert "repeated `search_terms` query was rejected" in str(repeated.content)


def test_wrap_tool_call_allows_paginated_list_terms_query() -> None:
    middleware = _middleware()
    _mark_list_vocabularies_called(middleware)
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
    _mark_list_vocabularies_called(middleware)
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
    _mark_list_vocabularies_called(middleware)
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
    _mark_list_vocabularies_called(middleware)
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


def test_wrap_tool_call_reports_nearest_indexed_candidates_for_unindexed_term() -> None:
    ex = Namespace("https://example.com/ontology#")
    graph = Graph(identifier=ex)
    graph.add((URIRef(str(ex)), RDF.type, OWL.Ontology))
    graph.add((URIRef(f"{ex}Primate"), RDF.type, RDFS.Class))
    graph.add((URIRef(f"{ex}Primate"), RDFS.isDefinedBy, URIRef(str(ex))))
    graph.add((URIRef(f"{ex}Primate"), RDFS.label, Literal("Primate")))

    middleware = _middleware(
        VocabularyConfiguration(
            declarations=(
                VocabularyDeclaration(
                    prefix="ex",
                    namespace=ex,
                    user_spec=UserSpec(
                        graph=graph,
                        vocabulary=URIRef(str(ex)),
                        label="Example Ontology",
                        description="Example user-supplied ontology.",
                    ),
                ),
            )
        ).build_context()
    )
    _mark_list_vocabularies_called(middleware)
    inspect_tool = next(
        tool for tool in middleware.tools if tool.name == "inspect_term"
    )
    request = SimpleNamespace(
        tool=inspect_tool,
        tool_call={
            "id": "call-1",
            "name": "inspect_term",
            "args": {"term": f"{ex}Primates", "include_source_rdf": True},
        },
    )

    result = middleware.wrap_tool_call(
        request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "Suggested indexed alternatives:" in str(result.content)
    assert f"`{ex}Primate`" in str(result.content)


def test_wrap_tool_call_uses_user_indexed_vocab_for_unindexed_term_suggestions() -> (
    None
):
    ex = Namespace("https://example.com/vocab#")
    graph = Graph(identifier=ex)
    graph.add((URIRef(str(ex)), RDF.type, OWL.Ontology))
    graph.add((URIRef(f"{ex}Process"), RDF.type, RDFS.Class))
    graph.add((URIRef(f"{ex}Process"), RDFS.isDefinedBy, URIRef(str(ex))))
    graph.add((URIRef(f"{ex}Process"), RDFS.label, Literal("Process")))

    middleware = _middleware(
        VocabularyConfiguration(
            declarations=(
                VocabularyDeclaration(
                    prefix="ex",
                    namespace=ex,
                    user_spec=UserSpec(
                        graph=graph,
                        vocabulary=URIRef(str(ex)),
                        label="Example Vocabulary",
                        description="Contains user-indexed terms only.",
                    ),
                ),
            )
        ).build_context()
    )
    _mark_list_vocabularies_called(middleware)
    inspect_tool = next(
        tool for tool in middleware.tools if tool.name == "inspect_term"
    )
    request = SimpleNamespace(
        tool=inspect_tool,
        tool_call={
            "id": "call-1",
            "name": "inspect_term",
            "args": {"term": f"{ex}Processes"},
        },
    )

    result = middleware.wrap_tool_call(
        request, lambda req: req.tool.invoke(req.tool_call["args"])
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert f"`{ex}Process`" in str(result.content)


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
