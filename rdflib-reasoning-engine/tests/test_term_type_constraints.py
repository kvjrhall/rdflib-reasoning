import warnings

import pytest
from rdflib import RDF, RDFS, BNode, Literal, URIRef
from rdflib.term import Node, Variable
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.engine import (
    RDFS_RULES,
    BlankNodePredicateError,
    BlankNodePredicateWarning,
    LiteralAsSubjectError,
    LiteralAsSubjectWarning,
    LiteralPredicateError,
    LiteralPredicateWarning,
    RETEEngine,
    RETEEngineFactory,
    Rule,
    RuleDescription,
    RuleId,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
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

    err = excinfo.value
    assert "rdf11-concepts/#section-triples" in str(err)
    assert "  triple:" in str(err)
    assert err.triple == bad_triple
    assert err.source == "stated"


def test_literal_subject_inferred_includes_rule_diagnostics() -> None:
    """A rule that places a bound literal in subject position surfaces rule context."""
    lit = Variable("lit")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="literal-as-subject-head"),
        description=RuleDescription(label="Promote object literal to subject"),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=URIRef("urn:test:bad-rule:s"),
                    predicate=URIRef("urn:test:bad-rule:has"),
                    object=lit,
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=lit,
                    predicate=URIRef("urn:test:bad-rule:p"),
                    object=URIRef("urn:test:bad-rule:o"),
                )
            ),
        ),
    )
    factory = RETEEngineFactory(rules=(rule,))
    engine = factory.new_engine(URIRef("urn:test:ctx"))
    stated_triple: Triple = (
        URIRef("urn:test:bad-rule:s"),
        URIRef("urn:test:bad-rule:has"),
        Literal("x"),
    )
    with pytest.raises(LiteralAsSubjectError) as excinfo:
        engine.add_triples({stated_triple})

    err = excinfo.value
    assert err.source == "inferred"
    assert err.triple is not None
    assert err.rule_id is not None
    assert err.pattern is not None
    assert err.bindings is not None
    assert err.premises is not None
    text = str(err)
    assert "source: inferred" in text
    assert "rule_id:" in text
    assert "pattern:" in text
    assert "bindings:" in text
    assert "premises:" in text
    assert "depth:" in text
    assert err.depth is not None


def test_rdfs4b_skips_literal_objects_without_literal_as_subject_error() -> None:
    """rdfs4b must not emit (literal rdf:type rdfs:Resource)—illegal RDF 1.1 triples."""
    factory = RETEEngineFactory(rules=RDFS_RULES)
    engine = factory.new_engine(URIRef("urn:test:ctx"))
    s = URIRef("urn:ex:Person")
    label_triple: Triple = (s, RDFS.label, Literal("Person"))
    engine.add_triples({label_triple})
    assert (Literal("Person"), RDF.type, RDFS.Resource) not in engine.known_triples
    for triple in engine.known_triples:
        assert not isinstance(triple[0], Literal)


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

    err = excinfo.value
    assert "rdf11-concepts/#section-triples" in str(err)
    assert "  triple:" in str(err)
    assert err.triple == bad_triple
    assert err.source == "stated"


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
