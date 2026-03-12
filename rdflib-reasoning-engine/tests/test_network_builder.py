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
from rdflibr.engine.rete import NetworkBuilder, RuleCompiler


def test_network_builder_creates_terminal_with_alpha_and_predicate_inputs() -> None:
    x = Variable("x")
    y = Variable("y")
    p = Variable("p")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="builder-shape"),
        description=RuleDescription(label="Builder shape"),
        body=(
            TripleCondition(pattern=TriplePattern(subject=x, predicate=p, object=y)),
            TripleCondition(
                pattern=TriplePattern(
                    subject=p,
                    predicate=RDFS.domain,
                    object=RDFS.Class,
                )
            ),
            PredicateCondition(predicate="not_literal", arguments=(y,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x,
                    predicate=RDF.type,
                    object=RDFS.Resource,
                )
            ),
            CallbackConsequent(
                callback="trace_match",
                arguments=(x, URIRef("urn:test:marker")),
            ),
        ),
    )

    compiled = RuleCompiler.compile_rule(rule)
    builder = NetworkBuilder()
    terminal = builder.build_rule(compiled)

    assert terminal.rule.rule_id == rule.id
    assert len(terminal.input_keys) == 2
    assert len(builder.registry.alpha_nodes) == 2
    assert len(builder.registry.beta_nodes) == 1
    assert len(builder.registry.predicate_nodes) == 1
    assert terminal.key in builder.registry.terminal_nodes


def test_network_builder_shares_equivalent_alpha_and_predicate_nodes() -> None:
    x = Variable("x")
    y = Variable("y")
    body = (
        TripleCondition(
            pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
        ),
        PredicateCondition(predicate="not_literal", arguments=(x,)),
    )
    head = (
        TripleConsequent(
            pattern=TriplePattern(subject=x, predicate=RDFS.subClassOf, object=y)
        ),
    )
    rule_a = Rule(
        id=RuleId(ruleset="test", rule_id="a"),
        description=RuleDescription(label="A"),
        body=body,
        head=head,
    )
    rule_b = Rule(
        id=RuleId(ruleset="test", rule_id="b"),
        description=RuleDescription(label="B"),
        body=body,
        head=head,
    )

    compiled_a = RuleCompiler.compile_rule(rule_a)
    compiled_b = RuleCompiler.compile_rule(rule_b)

    builder = NetworkBuilder()
    terminal_a = builder.build_rule(compiled_a)
    terminal_b = builder.build_rule(compiled_b)

    assert len(builder.registry.alpha_nodes) == 1
    assert len(builder.registry.beta_nodes) == 0
    assert len(builder.registry.predicate_nodes) == 1
    assert terminal_a.input_keys == terminal_b.input_keys
    assert terminal_a.key != terminal_b.key


def test_network_builder_build_rules_returns_terminals_in_rule_order() -> None:
    x = Variable("x")
    rule_a = Rule(
        id=RuleId(ruleset="test", rule_id="first"),
        description=RuleDescription(label="First"),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x, predicate=RDFS.subClassOf, object=RDFS.Resource
                )
            ),
        ),
    )
    rule_b = Rule(
        id=RuleId(ruleset="test", rule_id="second"),
        description=RuleDescription(label="Second"),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=x, predicate=RDFS.subClassOf, object=RDFS.Resource
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
    )

    compiled_rules = (
        RuleCompiler.compile_rule(rule_a),
        RuleCompiler.compile_rule(rule_b),
    )
    builder = NetworkBuilder()

    terminals = builder.build_rules(compiled_rules)

    assert [terminal.rule.rule_id.rule_id for terminal in terminals] == [
        "first",
        "second",
    ]


def test_network_builder_builds_left_deep_beta_chain_for_multiple_triples() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="beta-chain"),
        description=RuleDescription(label="Beta chain"),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=y, predicate=RDFS.subClassOf, object=z)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=z, predicate=RDFS.subClassOf, object=RDFS.Resource
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x, predicate=RDF.type, object=RDFS.Resource
                )
            ),
        ),
    )

    compiled = RuleCompiler.compile_rule(rule)
    builder = NetworkBuilder()
    terminal = builder.build_rule(compiled)

    assert len(builder.registry.alpha_nodes) == 3
    assert len(builder.registry.beta_nodes) == 2
    join_root = terminal.input_keys[0]
    beta_root = builder.registry.beta_nodes[join_root]
    assert beta_root.left_key.startswith("beta:")
    assert beta_root.right_key.startswith("alpha:")
    assert beta_root.shared_variables == ("y",)
    assert {node.shared_variables for node in builder.registry.beta_nodes.values()} == {
        ("y",),
        ("z",),
    }


def test_network_builder_shares_equivalent_beta_nodes_across_rules() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    body = (
        TripleCondition(pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)),
        TripleCondition(
            pattern=TriplePattern(subject=y, predicate=RDFS.subClassOf, object=z)
        ),
    )
    head = (
        TripleConsequent(
            pattern=TriplePattern(subject=x, predicate=RDF.type, object=z)
        ),
    )
    rule_a = Rule(
        id=RuleId(ruleset="test", rule_id="join-a"),
        description=RuleDescription(label="Join A"),
        body=body,
        head=head,
    )
    rule_b = Rule(
        id=RuleId(ruleset="test", rule_id="join-b"),
        description=RuleDescription(label="Join B"),
        body=body,
        head=head,
    )

    builder = NetworkBuilder()
    terminal_a = builder.build_rule(RuleCompiler.compile_rule(rule_a))
    terminal_b = builder.build_rule(RuleCompiler.compile_rule(rule_b))

    assert len(builder.registry.alpha_nodes) == 2
    assert len(builder.registry.beta_nodes) == 1
    assert terminal_a.input_keys == terminal_b.input_keys
