from rdflib.namespace import RDF, RDFS
from rdflib.term import URIRef, Variable
from rdflibr.engine import (
    CallbackConsequent,
    PredicateCondition,
    PredicateHook,
    Rule,
    RuleContext,
    RuleDescription,
    RuleId,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from rdflibr.engine.rete import NetworkBuilder, NetworkMatcher, RuleCompiler


class IsResourcePredicate(PredicateHook):
    def test(self, context: RuleContext, *args: URIRef) -> bool:  # type: ignore[override]
        _ = context
        return len(args) == 1 and str(args[0]).startswith("urn:test:")


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


def test_network_matcher_matches_single_alpha_rule_into_action_instance() -> None:
    x = Variable("x")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="single-match"),
        description=RuleDescription(label="Single match"),
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
        salience=5,
    )
    builder = NetworkBuilder()
    terminal = builder.build_rule(RuleCompiler.compile_rule(rule))
    matcher = NetworkMatcher(builder.registry)

    actions = matcher.match_terminal(
        terminal,
        ((URIRef("urn:test:A"), RDF.type, RDFS.Class),),
    )

    assert len(actions) == 1
    assert actions[0].rule_id.rule_id == "single-match"
    assert actions[0].bindings["x"] == URIRef("urn:test:A")
    assert actions[0].salience == 5
    assert actions[0].kind == "production"


def test_network_matcher_joins_beta_chain_before_emitting_action() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="join-match"),
        description=RuleDescription(label="Join match"),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=y, predicate=RDFS.subClassOf, object=z)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=z)
            ),
        ),
    )
    builder = NetworkBuilder()
    terminal = builder.build_rule(RuleCompiler.compile_rule(rule))
    matcher = NetworkMatcher(builder.registry)

    actions = matcher.match_terminal(
        terminal,
        (
            (URIRef("urn:test:a"), RDF.type, URIRef("urn:test:Human")),
            (URIRef("urn:test:Human"), RDFS.subClassOf, URIRef("urn:test:Mammal")),
            (URIRef("urn:test:Other"), RDFS.subClassOf, URIRef("urn:test:Ignored")),
        ),
    )

    assert len(actions) == 1
    assert actions[0].bindings == {
        "x": URIRef("urn:test:a"),
        "y": URIRef("urn:test:Human"),
        "z": URIRef("urn:test:Mammal"),
    }
    assert actions[0].depth == 1


def test_network_matcher_applies_predicate_filters_before_emitting_action() -> None:
    x = Variable("x")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="predicate-match"),
        description=RuleDescription(label="Predicate match"),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
            PredicateCondition(predicate="is_resource", arguments=(x,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x, predicate=RDFS.subClassOf, object=RDFS.Resource
                )
            ),
            CallbackConsequent(callback="trace", arguments=(x,)),
        ),
    )
    builder = NetworkBuilder()
    terminal = builder.build_rule(RuleCompiler.compile_rule(rule))
    matcher = NetworkMatcher(
        builder.registry,
        predicates={"is_resource": IsResourcePredicate()},
    )

    actions = matcher.match_terminal(
        terminal,
        (
            (URIRef("urn:test:A"), RDF.type, RDFS.Class),
            (URIRef("https://example.org/B"), RDF.type, RDFS.Class),
        ),
    )

    assert len(actions) == 1
    assert actions[0].bindings["x"] == URIRef("urn:test:A")
    assert actions[0].kind == "mixed"


def test_network_matcher_persists_alpha_memory_across_incremental_updates() -> None:
    x = Variable("x")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="alpha-memory"),
        description=RuleDescription(label="Alpha memory"),
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
    builder = NetworkBuilder()
    terminal = builder.build_rule(RuleCompiler.compile_rule(rule))
    matcher = NetworkMatcher(builder.registry)
    alpha_key = terminal.input_keys[0]

    first_actions = matcher.match_terminal(
        terminal,
        ((URIRef("urn:test:A"), RDF.type, RDFS.Class),),
    )
    second_actions = matcher.match_terminal(
        terminal,
        ((URIRef("urn:test:A"), RDF.type, RDFS.Class),),
    )
    third_actions = matcher.match_terminal(
        terminal,
        ((URIRef("urn:test:B"), RDF.type, RDFS.Class),),
    )

    assert len(first_actions) == 1
    assert len(second_actions) == 0
    assert len(third_actions) == 1
    assert matcher.alpha_memory_size(alpha_key) == 2


def test_network_matcher_persists_beta_memory_across_incremental_updates() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="beta-memory"),
        description=RuleDescription(label="Beta memory"),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=y, predicate=RDFS.subClassOf, object=z)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=z)
            ),
        ),
    )
    builder = NetworkBuilder()
    terminal = builder.build_rule(RuleCompiler.compile_rule(rule))
    matcher = NetworkMatcher(builder.registry)
    beta_key = terminal.input_keys[0]

    no_actions = matcher.match_terminal(
        terminal,
        ((URIRef("urn:test:a"), RDF.type, URIRef("urn:test:Human")),),
    )
    joined_actions = matcher.match_terminal(
        terminal,
        ((URIRef("urn:test:Human"), RDFS.subClassOf, URIRef("urn:test:Mammal")),),
    )
    repeated_actions = matcher.match_terminal(
        terminal,
        ((URIRef("urn:test:Human"), RDFS.subClassOf, URIRef("urn:test:Mammal")),),
    )

    assert len(no_actions) == 0
    assert len(joined_actions) == 1
    assert len(repeated_actions) == 0
    assert matcher.beta_memory_size(beta_key) == 1


def test_network_matcher_fans_shared_matches_out_to_multiple_terminals() -> None:
    x = Variable("x")
    shared_body = (
        TripleCondition(
            pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
        ),
    )
    first_rule = Rule(
        id=RuleId(ruleset="test", rule_id="first-shared"),
        description=RuleDescription(label="First shared"),
        body=shared_body,
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x,
                    predicate=RDFS.subClassOf,
                    object=RDFS.Resource,
                )
            ),
        ),
        salience=1,
    )
    second_rule = Rule(
        id=RuleId(ruleset="test", rule_id="second-shared"),
        description=RuleDescription(label="Second shared"),
        body=shared_body,
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        salience=2,
    )
    builder = NetworkBuilder()
    terminals = builder.build_rules(
        (
            RuleCompiler.compile_rule(first_rule),
            RuleCompiler.compile_rule(second_rule),
        )
    )
    matcher = NetworkMatcher(builder.registry)

    actions = matcher.match_terminals(
        terminals,
        ((URIRef("urn:test:A"), RDF.type, RDFS.Class),),
    )

    assert [action.rule_id.rule_id for action in actions] == [
        "first-shared",
        "second-shared",
    ]
