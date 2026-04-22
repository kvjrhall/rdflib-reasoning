import pytest
from pydantic import ValidationError
from rdflib.namespace import RDF, RDFS
from rdflib.term import Variable
from rdflib_reasoning.engine import (
    PRODUCTION_RDFS_RULES,
    CallbackConsequent,
    PredicateCondition,
    Rule,
    RuleDescription,
    RuleId,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)


def test_rule_ir_uses_rdflib_variables_in_patterns() -> None:
    x = Variable("x")
    p = Variable("p")
    y = Variable("y")

    rule = Rule(
        id=RuleId(ruleset="test", rule_id="triple-copy"),
        description=RuleDescription(label="Copy matched triple"),
        body=(
            TripleCondition(pattern=TriplePattern(subject=x, predicate=p, object=y)),
        ),
        head=(
            TripleConsequent(pattern=TriplePattern(subject=x, predicate=p, object=y)),
        ),
    )

    assert rule.body[0].kind == "triple"
    assert rule.head[0].kind == "triple"
    assert rule.body[0].pattern.subject == x
    assert rule.head[0].pattern.object == y


def test_rule_ir_supports_body_predicates_and_callback_consequents() -> None:
    x = Variable("x")

    rule = Rule(
        id=RuleId(ruleset="test", rule_id="predicate-and-callback"),
        description=RuleDescription(label="Predicate and callback"),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
            PredicateCondition(predicate="not_literal", arguments=(x,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDFS.subClassOf, object=x)
            ),
            CallbackConsequent(callback="trace_rule", arguments=(x,)),
        ),
        salience=10,
    )

    assert rule.body[1].kind == "predicate"
    assert rule.head[1].kind == "callback"
    assert rule.salience == 10


def test_rule_validation_allows_empty_body_bootstrap_rule() -> None:
    x = Variable("x")

    rule = Rule(
        id=RuleId(ruleset="test", rule_id="empty-body"),
        description=RuleDescription(label="Empty body"),
        body=(),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=x)
            ),
        ),
    )

    assert rule.body == ()


def test_rule_ir_supports_silent_flag() -> None:
    x = Variable("x")
    y = Variable("y")

    rule = Rule(
        id=RuleId(ruleset="test", rule_id="silent-rule"),
        description=RuleDescription(label="Silent rule"),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDFS.subClassOf, object=y)
            ),
        ),
        silent=True,
    )

    assert rule.silent is True


def test_rule_validation_rejects_empty_head() -> None:
    x = Variable("x")

    with pytest.raises(ValidationError, match="at least 1 item"):
        Rule(
            id=RuleId(ruleset="test", rule_id="empty-head"),
            description=RuleDescription(label="Empty head"),
            body=(
                TripleCondition(
                    pattern=TriplePattern(subject=x, predicate=RDF.type, object=x)
                ),
            ),
            head=(),
        )


def test_rdfs_rule_examples_cover_core_entailment_shapes() -> None:
    rule_ids = {rule.id.rule_id for rule in PRODUCTION_RDFS_RULES}

    assert {
        "rdfs1",
        "rdfs2",
        "rdfs3",
        "rdfs5",
        "rdfs7",
        "rdfs9",
        "rdfs11",
        "rdfs12",
    } <= rule_ids

    rdfs2 = next(
        rule
        for rule in PRODUCTION_RDFS_RULES
        if rule.id.ruleset == "rdfs" and rule.id.rule_id == "rdfs2"
    )
    assert len(rdfs2.body) == 3
    assert isinstance(rdfs2.body[0], TripleCondition)
    assert isinstance(rdfs2.body[-1], PredicateCondition)
    assert rdfs2.body[-1].predicate == "different_terms"
    assert rdfs2.head[0].pattern.predicate == RDF.type

    rdfs3 = next(
        rule
        for rule in PRODUCTION_RDFS_RULES
        if rule.id.ruleset == "rdfs" and rule.id.rule_id == "rdfs3"
    )
    assert len(rdfs3.body) == 4
    assert isinstance(rdfs3.body[-1], PredicateCondition)
    assert rdfs3.body[-1].predicate == "term_not_in"
    assert rdfs3.head[0].pattern.predicate == RDF.type

    rdfs7 = next(
        rule
        for rule in PRODUCTION_RDFS_RULES
        if rule.id.ruleset == "rdfs" and rule.id.rule_id == "rdfs7"
    )
    assert rdfs7.head[0].pattern.subject == Variable("x")
    assert rdfs7.head[0].pattern.object == Variable("y")

    rdfs11 = next(
        rule
        for rule in PRODUCTION_RDFS_RULES
        if rule.id.ruleset == "rdfs" and rule.id.rule_id == "rdfs11"
    )
    assert len(rdfs11.body) == 2
    assert rdfs11.head[0].pattern.predicate == RDFS.subClassOf

    all_reference_uris = {
        str(reference.uri)
        for rule in PRODUCTION_RDFS_RULES
        if rule.description is not None
        for reference in rule.description.references
    }
    assert "https://www.w3.org/TR/rdf11-mt/#RDFS_Interpretations" in all_reference_uris
    assert "https://www.w3.org/TR/rdf11-mt/#rdf-interpretations" in all_reference_uris
    assert "https://www.w3.org/TR/rdf11-mt/#rdfs-interpretations" in all_reference_uris

    assert sum(1 for r in PRODUCTION_RDFS_RULES if r.id.ruleset == "rdf_axioms") == 8
    assert sum(1 for r in PRODUCTION_RDFS_RULES if r.id.ruleset == "rdfs_axioms") == 36
