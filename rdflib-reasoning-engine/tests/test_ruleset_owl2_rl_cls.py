"""Minimal entailment tests for OWL 2 RL ``cls`` rules."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Final

from rdflib import OWL, RDF, XSD, BNode, Dataset, Literal, Namespace, URIRef
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.engine import NO_RULES, Builtins, InMemoryDerivationLogger
from rdflib_reasoning.engine.api import RETEEngine, RETEEngineConfig
from rdflib_reasoning.engine.derivation import DropContradictionRecorder
from rdflib_reasoning.engine.rules import Rule
from rdflib_reasoning.engine.rulesets.owl2_rl_cls import OWL2_RL_CLS_RULES

NS = Namespace("urn:test:")

_MAX_CARD_ONE: Final[Literal] = Literal("1", datatype=XSD.nonNegativeInteger)

_EXPECTED_CLS_RULE_IDS: Final[frozenset[str]] = frozenset(
    {
        "cls-thing",
        "cls-nothing1",
        "cls-int1",
        "cls-int2",
        "cls-uni",
        "cls-svf1",
        "cls-svf2",
        "cls-avf",
        "cls-hv1",
        "cls-hv2",
        "cls-maxc2",
        "cls-maxqc3",
        "cls-maxqc4",
        "cls-oo",
    }
)

_LIST_RULE_IDS: Final[frozenset[str]] = frozenset(
    {
        "cls-int1",
        "cls-int2",
        "cls-uni",
        "cls-oo",
    }
)


def _cls_rules(*rule_ids: str) -> tuple[Rule, ...]:
    wanted = set(rule_ids)
    return tuple(rule for rule in OWL2_RL_CLS_RULES if rule.id.rule_id in wanted)


def _dataset_for_rules(
    rules: Sequence[Rule],
) -> tuple[InMemoryDerivationLogger, Dataset]:
    logger = InMemoryDerivationLogger()
    dataset = replace(
        NO_RULES.extend(more_rules=rules),
        builtins=Builtins(),
        derivation_logger_factory=lambda _context: logger,
        contradiction_recorder_factory=lambda _context: DropContradictionRecorder(),
    ).dataset()
    return logger, dataset


def _engine_for_rules(rules: Sequence[Rule]) -> RETEEngine:
    return RETEEngine(
        config=RETEEngineConfig(
            context=URIRef("urn:test:cls-ctx"),
            builtins=Builtins(),
            derivation_logger=InMemoryDerivationLogger(),
            contradiction_recorder=DropContradictionRecorder(),
            literal_subject_policy="error",
            predicate_term_policy="error",
        ),
        rules=list(rules),
    )


def _rdf_list(*elements: URIRef) -> tuple[BNode, set[Triple]]:
    """Build a terminating ``rdf:List`` and return ``(head, triples)``."""
    if not elements:
        raise ValueError("test lists require at least one element")
    cells = [BNode() for _ in elements]
    triples: set[Triple] = set()
    for index, element in enumerate(elements):
        cell = cells[index]
        triples.add((cell, RDF.first, element))
        rest: URIRef | BNode = (
            RDF.nil if index == len(elements) - 1 else cells[index + 1]
        )
        triples.add((cell, RDF.rest, rest))
    return cells[0], triples


def test_owl2_rl_cls_exports_expected_rule_ids() -> None:
    present = {rule.id.rule_id for rule in OWL2_RL_CLS_RULES}
    assert present == _EXPECTED_CLS_RULE_IDS
    assert all(rule.id.ruleset == "owl2-rl" for rule in OWL2_RL_CLS_RULES)


def test_owl2_rl_cls_list_rules_are_present() -> None:
    present = {rule.id.rule_id for rule in OWL2_RL_CLS_RULES}
    assert _LIST_RULE_IDS <= present
    assert sum(1 for rule in OWL2_RL_CLS_RULES if rule.id.rule_id == "cls-uni") == 2


def test_cls_thing_and_nothing1_bootstrap() -> None:
    engine = _engine_for_rules(_cls_rules("cls-thing", "cls-nothing1"))
    engine.warmup(())
    assert (OWL.Thing, RDF.type, OWL.Class) in engine.known_triples
    assert (OWL.Nothing, RDF.type, OWL.Class) in engine.known_triples
    thing_rule = next(r for r in OWL2_RL_CLS_RULES if r.id.rule_id == "cls-thing")
    nothing_rule = next(r for r in OWL2_RL_CLS_RULES if r.id.rule_id == "cls-nothing1")
    assert thing_rule.silent is True
    assert nothing_rule.silent is True


def test_cls_svf1() -> None:
    restriction = NS.R
    _, dataset = _dataset_for_rules(_cls_rules("cls-svf1"))
    graph = dataset.default_graph
    graph.add((restriction, OWL.someValuesFrom, NS.C))
    graph.add((restriction, OWL.onProperty, NS.p))
    graph.add((NS.u, NS.p, NS.v))
    graph.add((NS.v, RDF.type, NS.C))
    assert (NS.u, RDF.type, restriction) in graph


def test_cls_svf2() -> None:
    restriction = NS.R
    _, dataset = _dataset_for_rules(_cls_rules("cls-svf2"))
    graph = dataset.default_graph
    graph.add((restriction, OWL.someValuesFrom, OWL.Thing))
    graph.add((restriction, OWL.onProperty, NS.p))
    graph.add((NS.u, NS.p, NS.v))
    assert (NS.u, RDF.type, restriction) in graph


def test_cls_avf() -> None:
    restriction = NS.R
    _, dataset = _dataset_for_rules(_cls_rules("cls-avf"))
    graph = dataset.default_graph
    graph.add((restriction, OWL.allValuesFrom, NS.C))
    graph.add((restriction, OWL.onProperty, NS.p))
    graph.add((NS.u, RDF.type, restriction))
    graph.add((NS.u, NS.p, NS.v))
    assert (NS.v, RDF.type, NS.C) in graph


def test_cls_hv1() -> None:
    restriction = NS.R
    _, dataset = _dataset_for_rules(_cls_rules("cls-hv1"))
    graph = dataset.default_graph
    graph.add((restriction, OWL.hasValue, NS.y))
    graph.add((restriction, OWL.onProperty, NS.p))
    graph.add((NS.u, RDF.type, restriction))
    assert (NS.u, NS.p, NS.y) in graph


def test_cls_hv2() -> None:
    restriction = NS.R
    _, dataset = _dataset_for_rules(_cls_rules("cls-hv2"))
    graph = dataset.default_graph
    graph.add((restriction, OWL.hasValue, NS.y))
    graph.add((restriction, OWL.onProperty, NS.p))
    graph.add((NS.u, NS.p, NS.y))
    assert (NS.u, RDF.type, restriction) in graph


def test_cls_maxc2() -> None:
    restriction = NS.R
    _, dataset = _dataset_for_rules(_cls_rules("cls-maxc2"))
    graph = dataset.default_graph
    graph.add((restriction, OWL.maxCardinality, _MAX_CARD_ONE))
    graph.add((restriction, OWL.onProperty, NS.p))
    graph.add((NS.u, RDF.type, restriction))
    graph.add((NS.u, NS.p, NS.y1))
    graph.add((NS.u, NS.p, NS.y2))
    assert (NS.y1, OWL.sameAs, NS.y2) in graph


def test_cls_maxqc3() -> None:
    restriction = NS.R
    _, dataset = _dataset_for_rules(_cls_rules("cls-maxqc3"))
    graph = dataset.default_graph
    graph.add((restriction, OWL.maxQualifiedCardinality, _MAX_CARD_ONE))
    graph.add((restriction, OWL.onProperty, NS.p))
    graph.add((restriction, OWL.onClass, NS.C))
    graph.add((NS.u, RDF.type, restriction))
    graph.add((NS.u, NS.p, NS.y1))
    graph.add((NS.y1, RDF.type, NS.C))
    graph.add((NS.u, NS.p, NS.y2))
    graph.add((NS.y2, RDF.type, NS.C))
    assert (NS.y1, OWL.sameAs, NS.y2) in graph


def test_cls_maxqc4() -> None:
    restriction = NS.R
    _, dataset = _dataset_for_rules(_cls_rules("cls-maxqc4"))
    graph = dataset.default_graph
    graph.add((restriction, OWL.maxQualifiedCardinality, _MAX_CARD_ONE))
    graph.add((restriction, OWL.onProperty, NS.p))
    graph.add((restriction, OWL.onClass, OWL.Thing))
    graph.add((NS.u, RDF.type, restriction))
    graph.add((NS.u, NS.p, NS.y1))
    graph.add((NS.u, NS.p, NS.y2))
    assert (NS.y1, OWL.sameAs, NS.y2) in graph


def test_cls_int1() -> None:
    head, list_triples = _rdf_list(NS.C1, NS.C2)
    _, dataset = _dataset_for_rules(_cls_rules("cls-int1"))
    graph = dataset.default_graph
    for triple in list_triples:
        graph.add(triple)
    graph.add((NS.C, OWL.intersectionOf, head))
    graph.add((NS.y, RDF.type, NS.C1))
    graph.add((NS.y, RDF.type, NS.C2))
    assert (NS.y, RDF.type, NS.C) in graph


def test_cls_int2() -> None:
    head, list_triples = _rdf_list(NS.C1, NS.C2)
    _, dataset = _dataset_for_rules(_cls_rules("cls-int2"))
    graph = dataset.default_graph
    for triple in list_triples:
        graph.add(triple)
    graph.add((NS.C, OWL.intersectionOf, head))
    graph.add((NS.y, RDF.type, NS.C))
    assert (NS.y, RDF.type, NS.C1) in graph
    assert (NS.y, RDF.type, NS.C2) in graph


def test_cls_uni() -> None:
    head, list_triples = _rdf_list(NS.C1, NS.C2)
    _, dataset = _dataset_for_rules(_cls_rules("cls-uni"))
    graph = dataset.default_graph
    for triple in list_triples:
        graph.add(triple)
    graph.add((NS.C, OWL.unionOf, head))
    graph.add((NS.y, RDF.type, NS.C2))
    assert (NS.y, RDF.type, NS.C) in graph


def test_cls_oo() -> None:
    head, list_triples = _rdf_list(NS.y1, NS.y2)
    _, dataset = _dataset_for_rules(_cls_rules("cls-oo"))
    graph = dataset.default_graph
    for triple in list_triples:
        graph.add(triple)
    graph.add((NS.C, OWL.oneOf, head))
    assert (NS.y1, RDF.type, NS.C) in graph
    assert (NS.y2, RDF.type, NS.C) in graph
