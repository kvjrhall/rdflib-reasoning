import pytest
from rdflib.namespace import RDF, RDFS
from rdflib.term import URIRef, Variable
from rdflibr.engine import (
    CallbackConsequent,
    PredicateCondition,
    Rule,
    RuleDescription,
    RuleId,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from rdflibr.engine.rete import (
    ActionInstance,
    Agenda,
    Fact,
    JoinOptimizer,
    PartialMatch,
    RuleCompiler,
)


def test_join_optimizer_prefers_more_selective_triple_patterns() -> None:
    x = Variable("x")
    y = Variable("y")
    p = Variable("p")
    broad = RuleCompiler._compile_triple_condition(
        TripleCondition(pattern=TriplePattern(subject=x, predicate=p, object=y)),
        0,
    )
    rdf_type = RuleCompiler._compile_triple_condition(
        TripleCondition(pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)),
        1,
    )
    sub_class = RuleCompiler._compile_triple_condition(
        TripleCondition(
            pattern=TriplePattern(
                subject=x, predicate=RDFS.subClassOf, object=RDFS.Class
            )
        ),
        2,
    )

    ordered = JoinOptimizer.order_triple_conditions((broad, rdf_type, sub_class))

    assert ordered[0].pattern.predicate == RDFS.subClassOf
    assert ordered[-1].pattern.predicate == p


def test_rule_compiler_normalizes_bindings_and_consequents() -> None:
    x = Variable("x")
    y = Variable("y")
    p = Variable("p")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="normalize"),
        description=RuleDescription(label="Normalization example"),
        body=(
            TripleCondition(pattern=TriplePattern(subject=x, predicate=p, object=y)),
            TripleCondition(
                pattern=TriplePattern(
                    subject=p, predicate=RDFS.domain, object=RDFS.Class
                )
            ),
            PredicateCondition(predicate="not_literal", arguments=(y,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x, predicate=RDF.type, object=RDFS.Resource
                )
            ),
            CallbackConsequent(
                callback="trace_match",
                arguments=(x, URIRef("urn:test:marker")),
            ),
        ),
        salience=7,
    )

    compiled = RuleCompiler.compile_rule(rule)

    assert compiled.rule_id == rule.id
    assert compiled.salience == 7
    assert compiled.variables == ("p", "x", "y")
    assert len(compiled.triple_conditions) == 2
    assert compiled.predicate_conditions[0].required_variables == ("y",)
    assert compiled.productions[0].required_variables == ("x",)
    assert compiled.callbacks[0].arguments == (
        Variable("x"),
        URIRef("urn:test:marker"),
    )


def test_rule_compiler_rejects_predicate_with_unbound_variable() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="unbound-predicate"),
        description=RuleDescription(label="Unbound predicate argument"),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
            PredicateCondition(predicate="same_term", arguments=(z,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
        ),
    )

    with pytest.raises(ValueError, match="MUST NOT introduce new bindings"):
        RuleCompiler.compile_rule(rule)


def test_action_instance_and_partial_match_capture_normalized_runtime_state() -> None:
    fact = Fact(
        id="f1",
        triple=(URIRef("urn:test:s"), RDF.type, RDFS.Class),
        stated=True,
    )
    match = PartialMatch(facts=(fact,), bindings={"x": URIRef("urn:test:s")}, depth=2)
    compiled = RuleCompiler.compile_rule(
        Rule(
            id=RuleId(ruleset="test", rule_id="runtime-shape"),
            description=RuleDescription(label="Runtime shape"),
            body=(
                TripleCondition(
                    pattern=TriplePattern(
                        subject=Variable("x"),
                        predicate=RDF.type,
                        object=RDFS.Class,
                    )
                ),
            ),
            head=(
                TripleConsequent(
                    pattern=TriplePattern(
                        subject=Variable("x"),
                        predicate=RDFS.subClassOf,
                        object=RDFS.Resource,
                    )
                ),
                CallbackConsequent(callback="trace", arguments=(Variable("x"),)),
            ),
        )
    )

    action = ActionInstance(
        rule_id=compiled.rule_id,
        bindings=match.bindings,
        depth=match.depth,
        productions=compiled.productions,
        callbacks=compiled.callbacks,
    )

    assert action.kind == "mixed"
    assert action.depth == 2
    assert action.bindings["x"] == URIRef("urn:test:s")


def test_agenda_orders_actions_by_salience_then_depth_then_insertion_order() -> None:
    high_salience = ActionInstance(
        rule_id=RuleId(ruleset="test", rule_id="high-salience"),
        bindings={},
        salience=10,
        depth=3,
    )
    shallow = ActionInstance(
        rule_id=RuleId(ruleset="test", rule_id="shallow"),
        bindings={},
        salience=5,
        depth=0,
    )
    deep = ActionInstance(
        rule_id=RuleId(ruleset="test", rule_id="deep"),
        bindings={},
        salience=5,
        depth=2,
    )
    shallow_later = ActionInstance(
        rule_id=RuleId(ruleset="test", rule_id="shallow-later"),
        bindings={},
        salience=5,
        depth=0,
    )

    agenda = Agenda((deep, shallow, high_salience, shallow_later))

    assert [action.rule_id.rule_id for action in agenda] == [
        "high-salience",
        "shallow",
        "shallow-later",
        "deep",
    ]
