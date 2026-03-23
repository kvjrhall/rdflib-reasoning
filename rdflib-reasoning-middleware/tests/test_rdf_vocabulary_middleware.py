from rdflib import PROV, RDFS, URIRef
from rdflib_reasoning.middleware.rdf_vocabulary_middleware import (
    RDFVocabularyMiddleware,
)


def test_list_terms_filters_classes() -> None:
    middleware = RDFVocabularyMiddleware()

    terms = middleware.list_terms(str(RDFS), term_type="class", limit=50)

    assert len(terms) == 6
    assert all(term.termType == "class" for term in terms)
    assert URIRef("http://www.w3.org/2000/01/rdf-schema#Class") in {
        term.uri for term in terms
    }


def test_list_terms_filters_properties() -> None:
    middleware = RDFVocabularyMiddleware()

    terms = middleware.list_terms(str(PROV), term_type="property", limit=10)

    assert len(terms) == 10
    assert all(term.termType == "property" for term in terms)


def test_vocabulary_tool_schema_and_descriptions_are_agent_facing() -> None:
    middleware = RDFVocabularyMiddleware()
    tools = {tool.name: tool for tool in middleware.tools}
    list_terms_schema = tools["list_terms"].get_input_schema().model_json_schema()
    describe_term_schema = tools["describe_term"].get_input_schema().model_json_schema()

    assert "MUST NOT wrap" in tools["list_terms"].description
    assert "Example arguments" in tools["describe_term"].description
    assert len(list_terms_schema["properties"]["vocabulary"]["examples"]) >= 2
    assert len(list_terms_schema["properties"]["term_type"]["examples"]) >= 2
    assert len(describe_term_schema["properties"]["term"]["examples"]) >= 2
