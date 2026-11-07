"""Tests for OWL 2 RL ``dt-*`` datatype entailment rules."""

from __future__ import annotations

import warnings

import pytest
from rdflib.namespace import OWL, RDF, RDFS, XSD
from rdflib.term import Literal, URIRef
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.engine import (
    Builtins,
    LiteralAsSubjectError,
    LiteralAsSubjectWarning,
    RaiseOnContradictionRecorder,
    RETEEngine,
    RETEEngineFactory,
    RETEEngineFactoryConfig,
)
from rdflib_reasoning.engine.api import LiteralSubjectPolicy
from rdflib_reasoning.engine.derivation import DropDerivationLogger
from rdflib_reasoning.engine.owl2_rl_datatypes import OWL2_RL_SUPPORTED_DATATYPES
from rdflib_reasoning.engine.rulesets.owl2_rl_dt import OWL2_RL_DT_RULES

_NS = URIRef("urn:test:dt:")
_S = URIRef(f"{_NS}s")
_S2 = URIRef(f"{_NS}s2")
_P = URIRef(f"{_NS}p")
_P2 = URIRef(f"{_NS}p2")


def _engine(*, literal_subject_policy: LiteralSubjectPolicy = "error") -> RETEEngine:
    factory = RETEEngineFactory(
        config=RETEEngineFactoryConfig(
            rules=OWL2_RL_DT_RULES,
            builtins=Builtins(),
            derivation_logger_factory=lambda _context: DropDerivationLogger(),
            contradiction_recorder_factory=lambda _context: (
                RaiseOnContradictionRecorder()
            ),
            literal_subject_policy=literal_subject_policy,
            predicate_term_policy="error",
        )
    )
    return factory.new_engine(URIRef(f"{_NS}ctx"))


def test_owl2_rl_dt_export_covers_four_rule_ids() -> None:
    rule_ids = {rule.id.rule_id for rule in OWL2_RL_DT_RULES}
    assert rule_ids == {"dt-type1", "dt-type2", "dt-eq", "dt-diff"}
    assert all(rule.id.ruleset == "owl2-rl" for rule in OWL2_RL_DT_RULES)


def test_dt_type1_bootstraps_all_supported_datatypes() -> None:
    engine = _engine()
    engine.warmup(())
    for datatype in OWL2_RL_SUPPORTED_DATATYPES:
        assert (datatype, RDF.type, RDFS.Datatype) in engine.known_triples
    # Spec-supported specials are included (not excluded) by dt-type1.
    assert (RDFS.Literal, RDF.type, RDFS.Datatype) in engine.known_triples
    assert (RDF.PlainLiteral, RDF.type, RDFS.Datatype) in engine.known_triples
    assert (RDF.XMLLiteral, RDF.type, RDFS.Datatype) in engine.known_triples


def test_dt_type2_attempts_literal_datatype_typing() -> None:
    """dt-type2 matches literal objects and attempts ``lt rdf:type dt``.

    Under the default RDF 1.1 literal-subject policy the conclusion is rejected
    with ``LiteralAsSubjectError``; the exception proves the rule fired.
    """
    engine = _engine()
    engine.warmup(())
    one = Literal("1", datatype=XSD.integer)
    stated: Triple = (_S, _P, one)
    with pytest.raises(LiteralAsSubjectError) as excinfo:
        engine.add_triples({stated})
    err = excinfo.value
    assert err.source == "inferred"
    assert err.rule_id is not None
    assert err.rule_id.rule_id == "dt-type2"
    assert err.triple is not None
    assert err.triple[0] == one
    assert err.triple[1] == RDF.type
    assert err.triple[2] in OWL2_RL_SUPPORTED_DATATYPES


def test_dt_eq_attempts_same_value_same_as() -> None:
    engine = _engine(literal_subject_policy="warning")
    engine.warmup(())
    left = Literal("1", datatype=XSD.integer)
    right = Literal("1.0", datatype=XSD.decimal)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", LiteralAsSubjectWarning)
        engine.add_triples({(_S, _P, left), (_S2, _P2, right)})
    # Warnings prove generalized-RDF conclusions were attempted.
    assert any(issubclass(w.category, LiteralAsSubjectWarning) for w in caught)
    warning_text = "\n".join(str(w.message) for w in caught)
    assert "dt-eq" in warning_text
    assert str(OWL.sameAs) in warning_text
    # RDF 1.1 policy: literal subjects never enter working memory.
    assert (left, OWL.sameAs, right) not in engine.known_triples
    assert (right, OWL.sameAs, left) not in engine.known_triples


def test_dt_diff_attempts_different_value_different_from() -> None:
    engine = _engine(literal_subject_policy="warning")
    engine.warmup(())
    left = Literal("1", datatype=XSD.integer)
    right = Literal("2", datatype=XSD.integer)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", LiteralAsSubjectWarning)
        engine.add_triples({(_S, _P, left), (_S2, _P2, right)})
    assert any(issubclass(w.category, LiteralAsSubjectWarning) for w in caught)
    warning_text = "\n".join(str(w.message) for w in caught)
    assert "dt-diff" in warning_text
    assert str(OWL.differentFrom) in warning_text
    assert (left, OWL.differentFrom, right) not in engine.known_triples


def test_dt_type1_count_matches_supported_datatype_inventory() -> None:
    type1 = [rule for rule in OWL2_RL_DT_RULES if rule.id.rule_id == "dt-type1"]
    assert len(type1) == len(OWL2_RL_SUPPORTED_DATATYPES)
    asserted = {
        consequent.pattern.subject
        for rule in type1
        for consequent in rule.head
        if consequent.kind == "triple"
    }
    assert asserted == set(OWL2_RL_SUPPORTED_DATATYPES)
