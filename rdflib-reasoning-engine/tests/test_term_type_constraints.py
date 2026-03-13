import warnings

import pytest
from rdflib import RDF, BNode, Literal, URIRef
from rdflib.term import Node
from rdflibr.axiom.common import Triple
from rdflibr.engine import (
    BlankNodePredicateError,
    BlankNodePredicateWarning,
    LiteralAsSubjectError,
    LiteralAsSubjectWarning,
    LiteralPredicateError,
    LiteralPredicateWarning,
    RETEEngine,
    RETEEngineFactory,
)


def make_engine(**policies: str) -> RETEEngine:
    """Helper to construct a bare RETEEngine with configurable term policies."""

    factory = RETEEngineFactory(rules=(), **policies)
    return factory.new_engine(URIRef("urn:test:ctx"))


def test_literal_subject_raises_error_by_default() -> None:
    engine = make_engine()
    bad_triple: Triple = (Literal("x"), URIRef("urn:test:p"), URIRef("urn:test:o"))  # type: ignore[assignment]

    with pytest.raises(LiteralAsSubjectError) as excinfo:
        engine.add_triples({bad_triple})

    assert "rdf11-concepts/#section-triples" in str(excinfo.value)


def test_literal_subject_warning_mode_emits_warning_and_skips_triple() -> None:
    engine = make_engine(literal_subject_policy="warning")
    bad_triple: Triple = (Literal("x"), URIRef("urn:test:p"), URIRef("urn:test:o"))

    with pytest.warns(LiteralAsSubjectWarning) as caught:
        result = engine.add_triples({bad_triple})

    assert result == set()
    assert bad_triple not in engine.known_triples
    assert len(caught) == 1
    assert "rdf11-concepts/#section-triples" in str(caught[0].message)


@pytest.mark.parametrize(
    ("predicate", "error_type", "warning_type"),
    [
        (BNode(), BlankNodePredicateError, BlankNodePredicateWarning),
        (Literal("p"), LiteralPredicateError, LiteralPredicateWarning),
    ],
)
def test_non_iri_predicate_raises_error_by_default(
    predicate: Node, error_type: type[Exception], warning_type: type[Warning]
) -> None:
    _ = warning_type
    engine = make_engine()
    bad_triple: Triple = (URIRef("urn:test:s"), predicate, URIRef("urn:test:o"))  # type: ignore[assignment]

    with pytest.raises(error_type) as excinfo:
        engine.add_triples({bad_triple})

    assert "rdf11-concepts/#section-triples" in str(excinfo.value)


@pytest.mark.parametrize(
    ("predicate", "error_type", "warning_type"),
    [
        (BNode(), BlankNodePredicateError, BlankNodePredicateWarning),
        (Literal("p"), LiteralPredicateError, LiteralPredicateWarning),
    ],
)
def test_non_iri_predicate_warning_mode_emits_warning_and_skips_triple(
    predicate: Node, error_type: type[Exception], warning_type: type[Warning]
) -> None:
    _ = error_type
    engine = make_engine(predicate_term_policy="warning")
    bad_triple: Triple = (URIRef("urn:test:s"), predicate, URIRef("urn:test:o"))  # type: ignore[assignment]

    with pytest.warns(warning_type) as caught:
        result = engine.add_triples({bad_triple})

    assert result == set()
    assert bad_triple not in engine.known_triples
    assert len(caught) == 1
    assert "rdf11-concepts/#section-triples" in str(caught[0].message)


def test_valid_triple_is_accepted_and_returned() -> None:
    engine = make_engine(
        literal_subject_policy="warning",
        predicate_term_policy="warning",
    )
    good_triple: Triple = (URIRef("urn:test:s"), RDF.type, URIRef("urn:test:o"))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("error")
        result = engine.add_triples({good_triple})

    # A valid triple must be accepted without errors or warnings; add_triples
    # returns only newly derived triples, so with no rules configured the
    # result is the empty set.
    assert result == set()
    assert good_triple in engine.known_triples
    assert caught == []
