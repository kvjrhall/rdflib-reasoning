"""Focused firing tests for OWL 2 RL contradiction (false-family) rules."""

from __future__ import annotations

import warnings

import pytest
from rdflib import IdentifiedNode
from rdflib.namespace import OWL, RDF, XSD
from rdflib.term import BNode, Literal, Node, URIRef
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.engine import Builtins, LiteralAsSubjectError
from rdflib_reasoning.engine.api import RETEEngine, RETEEngineConfig
from rdflib_reasoning.engine.derivation import (
    DropDerivationLogger,
    InMemoryContradictionRecorder,
)
from rdflib_reasoning.engine.rules import Rule
from rdflib_reasoning.engine.rulesets import OWL2_RL_CONTRADICTION_RULES

_ZERO = Literal("0", datatype=XSD.nonNegativeInteger)


def _rule(rule_id: str) -> Rule:
    for rule in OWL2_RL_CONTRADICTION_RULES:
        if rule.id.rule_id == rule_id:
            return rule
    raise KeyError(rule_id)


def _engine(*rules: Rule, builtins: Builtins | None = None) -> RETEEngine:
    context = BNode()
    return RETEEngine(
        config=RETEEngineConfig(
            context=context,
            builtins=builtins if builtins is not None else Builtins.EMPTY,
            derivation_logger=DropDerivationLogger(),
            contradiction_recorder=InMemoryContradictionRecorder(warn=False),
            literal_subject_policy="error",
            predicate_term_policy="error",
        ),
        rules=list(rules),
    )


def _list2(head: IdentifiedNode, first: Node, second: Node) -> list[Triple]:
    rest = BNode()
    return [
        (head, RDF.first, first),
        (head, RDF.rest, rest),
        (rest, RDF.first, second),
        (rest, RDF.rest, RDF.nil),
    ]


def _assert_single_category(engine: RETEEngine, category: str) -> None:
    records = engine.contradiction_records()
    assert len(records) == 1
    assert records[0].category == category
    assert records[0].rule_id.rule_id == category


def test_prp_pdw_records_disjoint_property_conflict() -> None:
    engine = _engine(_rule("prp-pdw"))
    p1 = URIRef("urn:test:p1")
    p2 = URIRef("urn:test:p2")
    s = URIRef("urn:test:s")
    o = URIRef("urn:test:o")

    inferred = engine.add_triples(
        [
            (p1, OWL.propertyDisjointWith, p2),
            (s, p1, o),
            (s, p2, o),
        ]
    )

    assert inferred == set()
    _assert_single_category(engine, "prp-pdw")


def test_cls_com_records_complement_overlap() -> None:
    engine = _engine(_rule("cls-com"))
    c1 = URIRef("urn:test:C1")
    c2 = URIRef("urn:test:C2")
    x = URIRef("urn:test:x")

    inferred = engine.add_triples(
        [
            (c1, OWL.complementOf, c2),
            (x, RDF.type, c1),
            (x, RDF.type, c2),
        ]
    )

    assert inferred == set()
    _assert_single_category(engine, "cls-com")


def test_cls_maxc1_records_max_cardinality_zero_violation() -> None:
    engine = _engine(_rule("cls-maxc1"))
    restriction = URIRef("urn:test:R")
    prop = URIRef("urn:test:p")
    individual = URIRef("urn:test:u")
    filler = URIRef("urn:test:y")

    inferred = engine.add_triples(
        [
            (restriction, OWL.maxCardinality, _ZERO),
            (restriction, OWL.onProperty, prop),
            (individual, RDF.type, restriction),
            (individual, prop, filler),
        ]
    )

    assert inferred == set()
    _assert_single_category(engine, "cls-maxc1")


def test_cls_maxqc1_records_qualified_max_cardinality_zero_violation() -> None:
    engine = _engine(_rule("cls-maxqc1"))
    restriction = URIRef("urn:test:R")
    prop = URIRef("urn:test:p")
    cls = URIRef("urn:test:C")
    individual = URIRef("urn:test:u")
    filler = URIRef("urn:test:y")

    inferred = engine.add_triples(
        [
            (restriction, OWL.maxQualifiedCardinality, _ZERO),
            (restriction, OWL.onProperty, prop),
            (restriction, OWL.onClass, cls),
            (individual, RDF.type, restriction),
            (individual, prop, filler),
            (filler, RDF.type, cls),
        ]
    )

    assert inferred == set()
    _assert_single_category(engine, "cls-maxqc1")


def test_cls_maxqc2_records_thing_qualified_max_cardinality_zero_violation() -> None:
    engine = _engine(_rule("cls-maxqc2"))
    restriction = URIRef("urn:test:R")
    prop = URIRef("urn:test:p")
    individual = URIRef("urn:test:u")
    filler = URIRef("urn:test:y")

    inferred = engine.add_triples(
        [
            (restriction, OWL.maxQualifiedCardinality, _ZERO),
            (restriction, OWL.onProperty, prop),
            (restriction, OWL.onClass, OWL.Thing),
            (individual, RDF.type, restriction),
            (individual, prop, filler),
        ]
    )

    assert inferred == set()
    _assert_single_category(engine, "cls-maxqc2")


def test_cax_dw_records_disjoint_class_overlap() -> None:
    engine = _engine(_rule("cax-dw"))
    c1 = URIRef("urn:test:C1")
    c2 = URIRef("urn:test:C2")
    x = URIRef("urn:test:x")

    inferred = engine.add_triples(
        [
            (c1, OWL.disjointWith, c2),
            (x, RDF.type, c1),
            (x, RDF.type, c2),
        ]
    )

    assert inferred == set()
    _assert_single_category(engine, "cax-dw")


def test_dt_not_type_encodes_spec_antecedent_and_datatype_guard() -> None:
    """``dt-not-type`` is encoded faithfully; RDF 1.1 policy blocks firing.

    The OWL 2 RL antecedent is ``T(lt, rdf:type, dt)`` with a value-space
    guard. Under this engine's RDF 1.1 literal-subject policy, that premise
    cannot enter working memory, so coverage here is structural.
    """
    rule = _rule("dt-not-type")
    assert rule.id.ruleset == "owl2-rl-contradiction"
    assert rule.head[0].kind == "contradiction"
    assert rule.head[0].category == "dt-not-type"

    triple_patterns = [
        condition.pattern for condition in rule.body if condition.kind == "triple"
    ]
    assert len(triple_patterns) == 1
    assert triple_patterns[0].predicate == RDF.type

    predicates = {
        condition.predicate for condition in rule.body if condition.kind == "predicate"
    }
    assert predicates == {"is_literal", "literal_not_in_datatype"}

    # Premise is rejected before matching under the default RDF 1.1 policy.
    engine = _engine(_rule("dt-not-type"), builtins=Builtins())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bad = Literal("not-a-number", datatype=XSD.integer)
    # Generalized-RDF premise shape required by the OWL 2 RL table.
    bad_triple = (bad, RDF.type, XSD.integer)
    with pytest.raises(LiteralAsSubjectError):
        engine.add_triples([bad_triple])  # type: ignore[arg-type]
    assert engine.contradiction_records() == ()


def test_eq_diff2_records_alldifferent_members_sameas() -> None:
    engine = _engine(_rule("eq-diff2"))
    axiom = URIRef("urn:test:ad")
    members = BNode()
    z1 = URIRef("urn:test:z1")
    z2 = URIRef("urn:test:z2")
    triples: list[Triple] = [
        (axiom, RDF.type, OWL.AllDifferent),
        (axiom, OWL.members, members),
        *_list2(members, z1, z2),
        (z1, OWL.sameAs, z2),
    ]

    inferred = engine.add_triples(triples)

    assert inferred == set()
    _assert_single_category(engine, "eq-diff2")


def test_eq_diff3_records_distinct_members_sameas() -> None:
    engine = _engine(_rule("eq-diff3"))
    axiom = URIRef("urn:test:ad")
    members = BNode()
    z1 = URIRef("urn:test:z1")
    z2 = URIRef("urn:test:z2")
    triples: list[Triple] = [
        (axiom, RDF.type, OWL.AllDifferent),
        (axiom, OWL.distinctMembers, members),
        *_list2(members, z1, z2),
        (z1, OWL.sameAs, z2),
    ]

    inferred = engine.add_triples(triples)

    assert inferred == set()
    _assert_single_category(engine, "eq-diff3")


def test_prp_adp_records_alldisjointproperties_conflict() -> None:
    engine = _engine(_rule("prp-adp"))
    axiom = URIRef("urn:test:adp")
    members = BNode()
    p1 = URIRef("urn:test:p1")
    p2 = URIRef("urn:test:p2")
    u = URIRef("urn:test:u")
    v = URIRef("urn:test:v")
    triples: list[Triple] = [
        (axiom, RDF.type, OWL.AllDisjointProperties),
        (axiom, OWL.members, members),
        *_list2(members, p1, p2),
        (u, p1, v),
        (u, p2, v),
    ]

    inferred = engine.add_triples(triples)

    assert inferred == set()
    _assert_single_category(engine, "prp-adp")


def test_cax_adc_records_alldisjointclasses_overlap() -> None:
    engine = _engine(_rule("cax-adc"))
    axiom = URIRef("urn:test:adc")
    members = BNode()
    c1 = URIRef("urn:test:C1")
    c2 = URIRef("urn:test:C2")
    individual = URIRef("urn:test:z")
    triples: list[Triple] = [
        (axiom, RDF.type, OWL.AllDisjointClasses),
        (axiom, OWL.members, members),
        *_list2(members, c1, c2),
        (individual, RDF.type, c1),
        (individual, RDF.type, c2),
    ]

    inferred = engine.add_triples(triples)

    assert inferred == set()
    _assert_single_category(engine, "cax-adc")
