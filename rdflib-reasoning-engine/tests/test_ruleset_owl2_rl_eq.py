"""Unit tests for OWL 2 RL Table 4 equality (``eq-*``) entailment rules."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from rdflib import OWL, Literal, Namespace
from rdflib.term import BNode
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.engine.api import RETEEngine, RETEEngineConfig
from rdflib_reasoning.engine.builtins import Builtins
from rdflib_reasoning.engine.derivation import (
    DropDerivationLogger,
    InMemoryDerivationLogger,
    RaiseOnContradictionRecorder,
)
from rdflib_reasoning.engine.rules import Rule
from rdflib_reasoning.engine.rulesets.owl2_rl_eq import OWL2_RL_EQ_RULES

NS = Namespace("urn:test:")

_EQ_RULES_BY_ID: Final[dict[str, tuple[Rule, ...]]] = {}
for _rule in OWL2_RL_EQ_RULES:
    _EQ_RULES_BY_ID.setdefault(_rule.id.rule_id, ())
    _EQ_RULES_BY_ID[_rule.id.rule_id] = (
        *_EQ_RULES_BY_ID[_rule.id.rule_id],
        _rule,
    )

_EXPECTED_EQ_RULE_IDS: Final[frozenset[str]] = frozenset(
    {
        "eq-ref",
        "eq-sym",
        "eq-trans",
        "eq-rep-s",
        "eq-rep-p",
        "eq-rep-o",
    }
)


def _rules_for(*rule_ids: str) -> tuple[Rule, ...]:
    rules: list[Rule] = []
    for rule_id in rule_ids:
        rules.extend(_EQ_RULES_BY_ID[rule_id])
    return tuple(rules)


def _engine(
    rule_ids: Sequence[str],
    *,
    logger: InMemoryDerivationLogger | DropDerivationLogger | None = None,
) -> RETEEngine:
    return RETEEngine(
        config=RETEEngineConfig(
            context=BNode(),
            builtins=Builtins(),
            derivation_logger=logger or DropDerivationLogger(),
            contradiction_recorder=RaiseOnContradictionRecorder(),
            literal_subject_policy="error",
            predicate_term_policy="error",
        ),
        rules=list(_rules_for(*rule_ids)),
    )


def _known_after(rule_ids: Sequence[str], inputs: set[Triple]) -> set[Triple]:
    engine = _engine(rule_ids)
    engine.add_triples(inputs)
    return set(engine.known_triples)


def test_owl2_rl_eq_exports_all_six_rule_ids() -> None:
    present = {rule.id.rule_id for rule in OWL2_RL_EQ_RULES}
    assert present == _EXPECTED_EQ_RULE_IDS
    for rule in OWL2_RL_EQ_RULES:
        assert rule.id.ruleset == "owl2-rl"
        assert rule.description is not None
        assert rule.description.references
        assert str(rule.description.references[0].uri).startswith(
            "https://www.w3.org/TR/owl2-profiles/"
        )


def test_eq_ref_materializes_reflexive_same_as() -> None:
    known = _known_after(["eq-ref"], {(NS.a, NS.p, NS.b)})
    assert (NS.a, OWL.sameAs, NS.a) in known
    assert (NS.p, OWL.sameAs, NS.p) in known
    assert (NS.b, OWL.sameAs, NS.b) in known


def test_eq_ref_skips_literal_object_reflexivity() -> None:
    """Literal objects must not become subjects under RDF 1.1 error policy."""
    known = _known_after(["eq-ref"], {(NS.a, NS.p, Literal("value"))})
    assert (NS.a, OWL.sameAs, NS.a) in known
    assert (NS.p, OWL.sameAs, NS.p) in known
    assert (Literal("value"), OWL.sameAs, Literal("value")) not in known


def test_eq_sym_materializes_symmetric_same_as() -> None:
    known = _known_after(["eq-sym"], {(NS.a, OWL.sameAs, NS.b)})
    assert (NS.b, OWL.sameAs, NS.a) in known


def test_eq_sym_skips_reflexive_same_as() -> None:
    asserted: set[Triple] = {(NS.a, OWL.sameAs, NS.a)}
    known = _known_after(["eq-sym"], asserted)
    assert known == asserted


def test_eq_trans_materializes_transitive_same_as() -> None:
    known = _known_after(
        ["eq-trans"],
        {
            (NS.a, OWL.sameAs, NS.b),
            (NS.b, OWL.sameAs, NS.c),
        },
    )
    assert (NS.a, OWL.sameAs, NS.c) in known


def test_eq_rep_s_replaces_subject() -> None:
    known = _known_after(
        ["eq-rep-s"],
        {
            (NS.a, OWL.sameAs, NS.a2),
            (NS.a, NS.p, NS.b),
        },
    )
    assert (NS.a2, NS.p, NS.b) in known


def test_eq_rep_p_replaces_predicate() -> None:
    known = _known_after(
        ["eq-rep-p"],
        {
            (NS.p, OWL.sameAs, NS.q),
            (NS.a, NS.p, NS.b),
        },
    )
    assert (NS.a, NS.q, NS.b) in known


def test_eq_rep_o_replaces_object() -> None:
    known = _known_after(
        ["eq-rep-o"],
        {
            (NS.b, OWL.sameAs, NS.b2),
            (NS.a, NS.p, NS.b),
        },
    )
    assert (NS.a, NS.p, NS.b2) in known


def test_eq_rep_rules_skip_identical_replacements() -> None:
    asserted: set[Triple] = {
        (NS.a, OWL.sameAs, NS.a),
        (NS.p, OWL.sameAs, NS.p),
        (NS.b, OWL.sameAs, NS.b),
        (NS.a, NS.p, NS.b),
    }
    known = _known_after(["eq-rep-s", "eq-rep-p", "eq-rep-o"], asserted)
    assert known == asserted


def test_eq_ref_derivation_records_use_canonical_rule_id() -> None:
    logger = InMemoryDerivationLogger()
    engine = _engine(["eq-ref"], logger=logger)
    engine.add_triples({(NS.a, NS.p, NS.b)})
    rule_ids = {record.rule_id.rule_id for record in logger.records}
    assert rule_ids == {"eq-ref"}
