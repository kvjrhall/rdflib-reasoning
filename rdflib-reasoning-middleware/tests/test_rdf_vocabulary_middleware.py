from rdflib import PROV, RDFS, URIRef
from rdflibr.middleware.rdf_vocabulary_middleware import RDFVocabularyMiddleware


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
