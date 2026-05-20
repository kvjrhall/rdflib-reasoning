from collections.abc import Iterable

import pytest
from rdflib.namespace import OWL, RDF, RDFS
from rdflib.term import BNode, Literal, URIRef, Variable
from rdflib_reasoning.axiom.common import ContextIdentifier
from rdflib_reasoning.engine.api import (
    NO_RULES,
    RDFS_RETE_MATERIALIZED,
    FatalRuleError,
    LiteralSubjectPolicy,
    PredicateTermPolicy,
    RETEEngine,
    RETEEngineConfig,
    RETEEngineFactory,
    RETEEngineFactoryConfig,
)
from rdflib_reasoning.engine.builtins import (
    Builtins,
    CallbackHook,
    PredicateHook,
    RuleContext,
)
from rdflib_reasoning.engine.derivation import (
    ContradictionDetectedError,
    ContradictionRecorder,
    DerivationLogger,
    DropDerivationLogger,
    InMemoryDerivationLogger,
    RaiseOnContradictionRecorder,
)
from rdflib_reasoning.engine.proof import DerivationRecord, RuleId, TripleFact
from rdflib_reasoning.engine.rules import (
    CallbackConsequent,
    ContradictionConsequent,
    PredicateCondition,
    Rule,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from rdflib_reasoning.engine.rulesets import PRODUCTION_RDFS_RULES

_X = Variable("x")


def _engine_config(
    *,
    context: ContextIdentifier | None = None,
    builtins: Builtins | None = None,
    derivation_logger: DerivationLogger | None = None,
    contradiction_recorder: ContradictionRecorder | None = None,
    literal_subject_policy: LiteralSubjectPolicy = "error",
    predicate_term_policy: PredicateTermPolicy = "error",
) -> RETEEngineConfig:
    return RETEEngineConfig(
        context=context or BNode(),
        builtins=builtins or Builtins(),
        derivation_logger=derivation_logger or DropDerivationLogger(),
        contradiction_recorder=contradiction_recorder or RaiseOnContradictionRecorder(),
        literal_subject_policy=literal_subject_policy,
        predicate_term_policy=predicate_term_policy,
    )


def _factory(
    rules: Iterable[Rule] = (),
    *,
    builtins: Builtins | None = None,
    derivation_logger_factory=lambda _context: None,
    literal_subject_policy: LiteralSubjectPolicy = "error",
    predicate_term_policy: PredicateTermPolicy = "error",
) -> RETEEngineFactory:
    return RETEEngineFactory(
        config=RETEEngineFactoryConfig(
            rules=tuple(rules),
            builtins=builtins or Builtins(),
            derivation_logger_factory=derivation_logger_factory,
            contradiction_recorder_factory=lambda _context: (
                RaiseOnContradictionRecorder()
            ),
            literal_subject_policy=literal_subject_policy,
            predicate_term_policy=predicate_term_policy,
        )
    )


def test_warmup_with_production_rdfs_loads_finite_axiom_triples_into_working_memory() -> (
    None
):
    factory = _factory(PRODUCTION_RDFS_RULES)
    engine = factory.new_engine(URIRef("urn:test:axiom-ctx"))
    engine.warmup(())
    assert (RDF.type, RDF.type, RDF.Property) in engine.known_triples
    assert (RDFS.domain, RDFS.domain, RDF.Property) in engine.known_triples
    assert (RDF.Seq, RDFS.subClassOf, RDFS.Container) in engine.known_triples
    assert (RDF._1, RDF.type, RDF.Property) not in engine.known_triples


def test_conformant_rdfs_rules_materialize_axioms_and_inference() -> None:
    from rdflib_reasoning.engine.rulesets import CONFORMANT_RDFS_RULES

    axiom = next(r for r in CONFORMANT_RDFS_RULES if r.id.ruleset == "rdf_axioms")
    assert axiom.silent is False
    rdfs2 = next(
        r
        for r in CONFORMANT_RDFS_RULES
        if r.id.ruleset == "rdfs" and r.id.rule_id == "rdfs2"
    )
    assert rdfs2.silent is False


class DummyRule(Rule):
    """Concrete Rule subclass for type-checking purposes."""

    id: RuleId = RuleId(ruleset="test", rule_id="dummy-rule")
    body: tuple[TripleCondition, ...] = (
        TripleCondition(
            pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_X)
        ),
    )
    head: tuple[TripleConsequent, ...] = (
        TripleConsequent(
            pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_X)
        ),
    )


class WarmupEngine(RETEEngine):
    """Concrete RETEEngine that implements add_triples for testing warmup."""

    def __init__(self, config: RETEEngineConfig, rules: Iterable[Rule]) -> None:
        super().__init__(config=config, rules=rules)
        self.add_triples_called_with: list[list[tuple[int, int, int]]] = []

    def add_triples(  # type: ignore[override]
        self, triples: Iterable[tuple[int, int, int]]
    ) -> set[tuple[int, int, int]]:  # type: ignore[override]
        materialized = list(triples)
        self.add_triples_called_with.append(materialized)
        # Echo the input triples back as "inferred" for easy assertions.
        return set(materialized)


class SameTermPredicate(PredicateHook):
    def test(self, context: RuleContext, *args: URIRef) -> bool:  # type: ignore[override]
        _ = context
        return len(args) == 2 and args[0] == args[1]


class RecordingCallback(CallbackHook):
    def __init__(self) -> None:
        self.calls: list[tuple[object, tuple[URIRef, ...]]] = []

    def run(self, context: RuleContext, *args: URIRef) -> None:  # type: ignore[override]
        self.calls.append((context, args))
        context.record({"callback": "recording", "args": args})  # type: ignore[attr-defined]


class RecordingLogger(DerivationLogger):
    def __init__(self) -> None:
        self.records: list[DerivationRecord] = []

    def record(self, record: DerivationRecord) -> None:
        self.records.append(record)


def test_rete_engine_init_and_close() -> None:
    context = BNode()
    config = _engine_config(context=context)
    rules: list[Rule] = [
        DummyRule(id=RuleId(ruleset="test", rule_id="dummy-rule-1")),
        DummyRule(id=RuleId(ruleset="test", rule_id="dummy-rule-2")),
    ]

    engine = RETEEngine(config=config, rules=rules)

    assert engine.config is config
    assert engine.rules == tuple(rules)

    # close() is currently a no-op but should be callable.
    engine.close()


def test_rete_engine_warmup_uses_add_triples() -> None:
    context = BNode()
    config = _engine_config(context=context)
    rules: list[Rule] = []
    engine = WarmupEngine(config=config, rules=rules)

    existing_triples = [(1, 2, 3), (4, 5, 6)]

    inferred = engine.warmup(existing_triples)  # type: ignore[arg-type]

    # warmup must delegate to add_triples and return its results.
    assert inferred == set(existing_triples)
    assert engine.add_triples_called_with == [existing_triples]


def test_rete_engine_factory_config_is_preserved() -> None:
    config = NO_RULES.engine_factory_config()
    factory = RETEEngineFactory(config=config)

    assert factory.config is config
    assert factory.rules_template == ()


def test_rete_engine_factory_new_engine_uses_configured_rules_and_engine_config() -> (
    None
):
    context = BNode()
    rule = DummyRule(id=RuleId(ruleset="test", rule_id="factory-rule"))
    logger_by_context: dict[ContextIdentifier, InMemoryDerivationLogger] = {}

    def logger_factory(context_id: ContextIdentifier) -> InMemoryDerivationLogger:
        logger = InMemoryDerivationLogger()
        logger_by_context[context_id] = logger
        return logger

    factory = _factory([rule], derivation_logger_factory=logger_factory)

    engine = factory.new_engine(context)

    assert isinstance(engine, RETEEngine)
    assert engine.config.context == context
    assert engine.config.derivation_logger is logger_by_context[context]
    assert engine.rules == (rule,)


def test_rdfs_rete_materialized_spec_creates_production_rdfs_factory() -> None:
    factory = RDFS_RETE_MATERIALIZED.engine_factory()
    engine = factory.new_engine(URIRef("urn:test:canonical-rdfs"))

    assert engine.rules == PRODUCTION_RDFS_RULES
    assert RDFS_RETE_MATERIALIZED.materializes_inferences is True
    assert RDFS_RETE_MATERIALIZED.supports_retraction is True
    assert RDFS_RETE_MATERIALIZED.supports_derivation_logging is True
    assert RDFS_RETE_MATERIALIZED.contradiction_policy == "raise"


def test_rdfs_rete_materialized_spec_creates_per_context_loggers() -> None:
    factory = RDFS_RETE_MATERIALIZED.engine_factory()

    first = factory.new_engine(URIRef("urn:test:first"))
    second = factory.new_engine(URIRef("urn:test:second"))

    assert isinstance(first.derivation_logger, DropDerivationLogger), (
        "The first context's derivation logger should be an InMemoryDerivationLogger "
        f"Got {type(first.derivation_logger)}"
    )
    assert isinstance(second.derivation_logger, DropDerivationLogger), (
        "The second context's derivation logger should be an InMemoryDerivationLogger"
    )
    assert first.derivation_logger is not second.derivation_logger, (
        "The same logger instance was used for multiple contexts"
    )


def test_rdfs_rete_materialized_spec_raises_and_retains_contradictions() -> None:
    x = Variable("x")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="nothing"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=OWL.Nothing)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="cls-nothing2",
                detail="Individual typed as owl:Nothing.",
                arguments=(x, RDF.type, OWL.Nothing),
            ),
        ),
    )
    spec = RDFS_RETE_MATERIALIZED
    factory = RETEEngineFactory(
        config=RETEEngineFactoryConfig(
            rules=(rule,),
            builtins=spec.builtins,
            literal_subject_policy=spec.literal_subject_policy,
            predicate_term_policy=spec.predicate_term_policy,
            derivation_logger_factory=spec.derivation_logger_factory,
            contradiction_recorder_factory=spec.contradiction_recorder_factory,
        )
    )
    engine = factory.new_engine(URIRef("urn:test:contradiction"))
    triple = (URIRef("urn:test:a"), RDF.type, OWL.Nothing)

    with pytest.raises(ContradictionDetectedError):
        engine.add_triples([triple])

    records = engine.contradiction_records()
    assert len(records) == 1
    assert records[0].witness is not None
    assert records[0].witness.triple == triple


def test_rdfs_rete_materialized_spec_store_materializes_rdfs_closure() -> None:
    dataset = RDFS_RETE_MATERIALIZED.dataset()
    person = URIRef("urn:test:Person")
    mammal = URIRef("urn:test:Mammal")
    alice = URIRef("urn:test:alice")

    dataset.default_graph.add((person, RDFS.subClassOf, mammal))
    dataset.default_graph.add((alice, RDF.type, person))

    assert (alice, RDF.type, mammal) in dataset.default_graph


def test_no_rules_spec_has_logically_noop_metadata() -> None:
    assert NO_RULES.rules == ()
    assert NO_RULES.materializes_inferences is True, (
        "No-op spec should materialize inferences"
    )
    assert NO_RULES.supports_retraction is True, "No-op spec should support retraction"
    assert NO_RULES.supports_derivation_logging is True, (
        "No-op spec should support derivation logging"
    )
    assert NO_RULES.contradiction_policy == "raise", (
        "No-op spec should raise on contradictions"
    )


def test_no_rules_spec_creates_noop_engine_without_derivation_logger() -> None:
    engine = NO_RULES.engine_factory().new_engine(URIRef("urn:test:no-rules"))

    assert engine.rules == ()
    assert isinstance(engine.derivation_logger, DropDerivationLogger), (
        "The derivation logger should be a DropDerivationLogger"
    )
    assert isinstance(engine.contradiction_recorder, RaiseOnContradictionRecorder)
    assert engine.literal_subject_policy == "error"
    assert engine.predicate_term_policy == "error"


def test_no_rules_spec_store_preserves_assertions_without_materializing_closure() -> (
    None
):
    dataset = NO_RULES.dataset()
    person = URIRef("urn:test:Person")
    mammal = URIRef("urn:test:Mammal")
    alice = URIRef("urn:test:alice")

    dataset.default_graph.add((person, RDFS.subClassOf, mammal))
    dataset.default_graph.add((alice, RDF.type, person))

    assert (person, RDFS.subClassOf, mammal) in dataset.default_graph
    assert (alice, RDF.type, person) in dataset.default_graph
    assert (alice, RDF.type, mammal) not in dataset.default_graph


def test_no_rules_spec_store_supports_retraction_of_assertions() -> None:
    dataset = NO_RULES.dataset()
    triple = (URIRef("urn:test:alice"), RDF.type, URIRef("urn:test:Person"))

    dataset.default_graph.add(triple)
    dataset.default_graph.remove(triple)

    assert triple not in dataset.default_graph


def test_rete_engine_add_triples_materializes_inference_to_fixed_point() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    rules: list[Rule] = [
        Rule(
            id=RuleId(ruleset="test", rule_id="subclass"),
            description=None,
            body=(
                TripleCondition(
                    pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
                ),
                TripleCondition(
                    pattern=TriplePattern(
                        subject=y, predicate=RDFS.subClassOf, object=z
                    )
                ),
            ),
            head=(
                TripleConsequent(
                    pattern=TriplePattern(subject=x, predicate=RDF.type, object=z)
                ),
            ),
        )
    ]
    engine = RETEEngine(config=_engine_config(), rules=rules)
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    animal = URIRef("urn:test:Animal")
    alice = URIRef("urn:test:alice")

    inferred = engine.add_triples(
        [
            (alice, RDF.type, human),
            (human, RDFS.subClassOf, mammal),
            (mammal, RDFS.subClassOf, animal),
        ]
    )

    assert inferred == {
        (alice, RDF.type, mammal),
        (alice, RDF.type, animal),
    }


def test_rete_engine_add_triples_is_idempotent_for_known_triples() -> None:
    x = Variable("x")
    y = Variable("y")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="copy-type"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
        ),
    )
    engine = RETEEngine(config=_engine_config(), rules=[rule])
    triple = (URIRef("urn:test:a"), RDF.type, URIRef("urn:test:A"))

    assert engine.add_triples([triple]) == set()
    assert engine.add_triples([triple]) == set()


def test_rete_engine_add_triples_supports_builtin_predicates() -> None:
    x = Variable("x")
    y = Variable("y")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="same-term"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
            PredicateCondition(predicate="same_term", arguments=(x, x)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDFS.subClassOf, object=y)
            ),
        ),
    )
    builtins = Builtins.EMPTY.extend(more_predicates={"same_term": SameTermPredicate()})
    config = _engine_config(builtins=builtins)
    engine = RETEEngine(config=config, rules=[rule])
    triple = (URIRef("urn:test:a"), RDF.type, URIRef("urn:test:A"))

    inferred = engine.add_triples([triple])

    assert inferred == {(URIRef("urn:test:a"), RDFS.subClassOf, URIRef("urn:test:A"))}


def test_rete_engine_same_term_predicate_builtin_by_default() -> None:
    x = Variable("x")
    y = Variable("y")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="same-term-default"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
            PredicateCondition(predicate="same_term", arguments=(x, x)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=x, predicate=RDFS.subClassOf, object=y)
            ),
        ),
    )
    engine = _factory([rule]).new_engine(URIRef("urn:test:ctx-default"))

    inferred = engine.add_triples(
        [(URIRef("urn:test:a"), RDF.type, URIRef("urn:test:A"))]
    )

    assert inferred == {(URIRef("urn:test:a"), RDFS.subClassOf, URIRef("urn:test:A"))}


def test_rete_engine_term_in_predicates_builtin_by_default() -> None:
    x = Variable("x")
    y = Variable("y")
    guard_rule = Rule(
        id=RuleId(ruleset="test", rule_id="term-in-default"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
            PredicateCondition(
                predicate="term_in", arguments=(y, RDFS.Class, RDFS.Resource)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=y, predicate=RDFS.subClassOf, object=y)
            ),
        ),
    )
    deny_rule = Rule(
        id=RuleId(ruleset="test", rule_id="term-not-in-default"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
            PredicateCondition(
                predicate="term_not_in", arguments=(y, RDFS.Class, RDFS.Resource)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=y, predicate=RDFS.subClassOf, object=RDFS.Resource
                )
            ),
        ),
    )
    engine = _factory([guard_rule, deny_rule]).new_engine(
        URIRef("urn:test:ctx-term-in")
    )

    inferred = engine.add_triples([(URIRef("urn:test:a"), RDF.type, RDFS.Class)])

    assert (RDFS.Class, RDFS.subClassOf, RDFS.Class) in inferred
    assert (RDFS.Class, RDFS.subClassOf, RDFS.Resource) not in inferred


def test_rete_engine_not_literal_predicate_builtin_by_default() -> None:
    x = Variable("x")
    y = Variable("y")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="not-literal-guard"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=y)
            ),
            PredicateCondition(predicate="not_literal", arguments=(y,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=y, predicate=RDFS.subClassOf, object=y)
            ),
        ),
    )
    engine = _factory([rule]).new_engine(URIRef("urn:test:ctx"))
    a = URIRef("urn:test:a")
    b = URIRef("urn:test:b")
    inferred = engine.add_triples([(a, RDF.type, b)])
    assert (b, RDFS.subClassOf, b) in inferred

    engine_lit = _factory([rule]).new_engine(URIRef("urn:test:ctx2"))
    inferred_lit = engine_lit.add_triples([(a, RDF.type, Literal("lit"))])
    assert inferred_lit == set()
    assert (
        Literal("lit"),
        RDFS.subClassOf,
        Literal("lit"),
    ) not in engine_lit.known_triples


def test_rete_engine_user_may_override_not_literal_predicate() -> None:
    class AlwaysFalse(PredicateHook):
        def test(self, context: RuleContext, *args: object) -> bool:  # noqa: ARG002
            return False

    triple = (URIRef("urn:x"), URIRef("urn:p"), URIRef("urn:y"))
    range_triple = (triple[1], RDFS.range, URIRef("urn:test:C"))
    default_engine = _factory(PRODUCTION_RDFS_RULES).new_engine(URIRef("urn:ctx"))
    default_engine.add_triples([range_triple, triple])
    assert (triple[2], RDF.type, range_triple[2]) in default_engine.known_triples

    builtins = Builtins.EMPTY.extend(more_predicates={"not_literal": AlwaysFalse()})
    override_engine = _factory(PRODUCTION_RDFS_RULES, builtins=builtins).new_engine(
        URIRef("urn:ctx")
    )
    override_engine.add_triples([range_triple, triple])
    assert (triple[2], RDF.type, range_triple[2]) not in override_engine.known_triples


def test_production_rdfs_omits_selected_schema_axioms_from_working_memory() -> None:
    engine = _factory(PRODUCTION_RDFS_RULES).new_engine(URIRef("urn:ctx"))
    engine.warmup(())

    assert (RDF.type, RDFS.domain, RDFS.Resource) not in engine.known_triples
    assert (RDF.type, RDFS.range, RDFS.Class) not in engine.known_triples


def test_rete_engine_add_triples_records_derivations_for_new_conclusions() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    logger = RecordingLogger()
    context = BNode()
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="subclass"),
        description=None,
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
    engine = RETEEngine(
        config=_engine_config(context=context, derivation_logger=logger),
        rules=[rule],
    )
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    alice = URIRef("urn:test:alice")

    inferred = engine.add_triples(
        [
            (alice, RDF.type, human),
            (human, RDFS.subClassOf, mammal),
        ]
    )

    assert inferred == {(alice, RDF.type, mammal)}
    assert len(logger.records) == 1

    record = logger.records[0]
    assert record.context == context
    assert record.rule_id == rule.id
    assert record.depth == 1
    assert [conclusion.triple for conclusion in record.conclusions] == [
        (alice, RDF.type, mammal)
    ]
    assert {premise.triple for premise in record.premises} == {
        (alice, RDF.type, human),
        (human, RDFS.subClassOf, mammal),
    }
    assert [(binding.name, binding.value) for binding in record.bindings] == [
        ("x", alice),
        ("y", human),
        ("z", mammal),
    ]
    assert record.silent is False
    assert record.bootstrap is False


def test_in_memory_derivation_logger_records_entries() -> None:
    context = BNode()
    logger = InMemoryDerivationLogger()
    record = DerivationRecord(
        context=context,
        conclusions=[
            TripleFact(
                context=context,
                triple=(
                    URIRef("urn:test:s"),
                    URIRef("urn:test:p"),
                    URIRef("urn:test:o"),
                ),
            )
        ],
        rule_id=RuleId(ruleset="test", rule_id="rule"),
    )

    logger.record(record)

    assert logger.records == [record]


def test_rete_engine_silent_rule_is_not_materialized_but_logged_and_available() -> None:
    x = Variable("x")
    logger = RecordingLogger()
    context = BNode()
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="silent-type"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x,
                    predicate=URIRef("urn:test:silent"),
                    object=RDFS.Resource,
                )
            ),
        ),
        silent=True,
    )
    engine = RETEEngine(
        config=_engine_config(context=context, derivation_logger=logger),
        rules=[rule],
    )
    triple = (URIRef("urn:test:A"), RDF.type, RDFS.Class)

    inferred = engine.add_triples([triple])

    silent_conclusion = (
        URIRef("urn:test:A"),
        URIRef("urn:test:silent"),
        RDFS.Resource,
    )
    assert inferred == set()
    assert silent_conclusion in engine.known_triples
    assert len(logger.records) == 1
    assert logger.records[0].silent is True
    assert logger.records[0].bootstrap is False
    assert [fact.triple for fact in logger.records[0].conclusions] == [
        silent_conclusion
    ]


def test_silent_only_same_output_triple_remains_non_materialized() -> None:
    x = Variable("x")
    logger = RecordingLogger()
    conclusion = (URIRef("urn:test:A"), URIRef("urn:test:tag"), RDFS.Resource)
    silent_rule = Rule(
        id=RuleId(ruleset="test", rule_id="silent-out"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x, predicate=URIRef("urn:test:tag"), object=RDFS.Resource
                )
            ),
        ),
        silent=True,
    )
    nonsilent_unsatisfied = Rule(
        id=RuleId(ruleset="test", rule_id="nonsilent-unsatisfied"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=x, predicate=URIRef("urn:test:missing"), object=RDFS.Class
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x, predicate=URIRef("urn:test:tag"), object=RDFS.Resource
                )
            ),
        ),
        silent=False,
    )
    engine = RETEEngine(
        config=_engine_config(derivation_logger=logger),
        rules=[silent_rule, nonsilent_unsatisfied],
    )

    inferred = engine.add_triples([(URIRef("urn:test:A"), RDF.type, RDFS.Class)])

    assert inferred == set()
    assert conclusion in engine.known_triples
    assert any(record.silent for record in logger.records)


def test_non_silent_only_same_output_triple_materializes() -> None:
    x = Variable("x")
    logger = RecordingLogger()
    conclusion = (URIRef("urn:test:A"), URIRef("urn:test:tag"), RDFS.Resource)
    silent_unsatisfied = Rule(
        id=RuleId(ruleset="test", rule_id="silent-unsatisfied"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=x, predicate=URIRef("urn:test:missing"), object=RDFS.Class
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x, predicate=URIRef("urn:test:tag"), object=RDFS.Resource
                )
            ),
        ),
        silent=True,
    )
    nonsilent_rule = Rule(
        id=RuleId(ruleset="test", rule_id="nonsilent-out"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x, predicate=URIRef("urn:test:tag"), object=RDFS.Resource
                )
            ),
        ),
        silent=False,
    )
    engine = RETEEngine(
        config=_engine_config(derivation_logger=logger),
        rules=[silent_unsatisfied, nonsilent_rule],
    )

    inferred = engine.add_triples([(URIRef("urn:test:A"), RDF.type, RDFS.Class)])

    assert inferred == {conclusion}
    assert any(not record.silent for record in logger.records)
    assert all(not record.bootstrap for record in logger.records)


def test_non_silent_wins_when_silent_and_non_silent_derive_same_triple() -> None:
    x = Variable("x")
    logger = RecordingLogger()
    conclusion = (URIRef("urn:test:A"), URIRef("urn:test:tag"), RDFS.Resource)
    # Higher salience ensures silent activation executes first.
    silent_rule = Rule(
        id=RuleId(ruleset="test", rule_id="silent-first"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x, predicate=URIRef("urn:test:tag"), object=RDFS.Resource
                )
            ),
        ),
        salience=10,
        silent=True,
    )
    nonsilent_rule = Rule(
        id=RuleId(ruleset="test", rule_id="nonsilent-second"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x, predicate=URIRef("urn:test:tag"), object=RDFS.Resource
                )
            ),
        ),
        salience=1,
        silent=False,
    )
    engine = RETEEngine(
        config=_engine_config(derivation_logger=logger),
        rules=[silent_rule, nonsilent_rule],
    )

    inferred = engine.add_triples([(URIRef("urn:test:A"), RDF.type, RDFS.Class)])

    assert inferred == {conclusion}
    assert any(record.silent for record in logger.records)
    assert any(not record.silent for record in logger.records)
    assert all(not record.bootstrap for record in logger.records)


def test_rete_engine_warmup_runs_bootstrap_rule_once_per_engine_context() -> None:
    bootstrap_rule = Rule(
        id=RuleId(ruleset="test", rule_id="bootstrap"),
        description=None,
        body=(),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=URIRef("urn:test:bootstrap"),
                    predicate=RDF.type,
                    object=RDFS.Resource,
                )
            ),
        ),
    )
    engine = RETEEngine(config=_engine_config(), rules=[bootstrap_rule])

    first = engine.warmup([])
    second = engine.warmup([])

    bootstrap_triple = (URIRef("urn:test:bootstrap"), RDF.type, RDFS.Resource)
    assert first == set()
    assert second == set()
    assert bootstrap_triple in engine.known_triples
    assert bootstrap_triple not in engine.materialized_triples


def test_rete_engine_bootstrap_logs_effective_silence_separately_from_rule_policy() -> (
    None
):
    logger = RecordingLogger()
    bootstrap_rule = Rule(
        id=RuleId(ruleset="test", rule_id="bootstrap"),
        description=None,
        body=(),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=URIRef("urn:test:bootstrap"),
                    predicate=RDF.type,
                    object=RDFS.Resource,
                )
            ),
        ),
        silent=False,
    )
    engine = RETEEngine(
        config=_engine_config(derivation_logger=logger),
        rules=[bootstrap_rule],
    )

    engine.warmup([])

    assert len(logger.records) == 1
    assert logger.records[0].rule_id == bootstrap_rule.id
    assert logger.records[0].bootstrap is True
    assert logger.records[0].silent is True


def test_rete_engine_bootstrap_suppresses_non_silent_bootstrap_only_closure() -> None:
    bootstrap_seed = (URIRef("urn:test:seed"), RDFS.domain, RDFS.Class)
    bootstrap_rule = Rule(
        id=RuleId(ruleset="test", rule_id="bootstrap"),
        description=None,
        body=(),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=bootstrap_seed[0],
                    predicate=bootstrap_seed[1],
                    object=bootstrap_seed[2],
                )
            ),
        ),
        silent=True,
    )
    stimulated_rule = Rule(
        id=RuleId(ruleset="test", rule_id="stimulated"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=bootstrap_seed[0],
                    predicate=bootstrap_seed[1],
                    object=bootstrap_seed[2],
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=RDF.List,
                    predicate=RDF.type,
                    object=RDFS.Resource,
                )
            ),
        ),
    )
    engine = RETEEngine(
        config=_engine_config(),
        rules=[bootstrap_rule, stimulated_rule],
    )

    inferred = engine.warmup([])
    closure_triple = (RDF.List, RDF.type, RDFS.Resource)

    assert inferred == set()
    assert bootstrap_seed in engine.known_triples
    assert closure_triple in engine.known_triples
    assert closure_triple not in engine.materialized_triples


def test_rete_engine_bootstrap_marks_stimulated_derivations_as_bootstrap_and_silent() -> (
    None
):
    logger = RecordingLogger()
    bootstrap_seed = (URIRef("urn:test:seed"), RDFS.domain, RDFS.Class)
    bootstrap_rule = Rule(
        id=RuleId(ruleset="test", rule_id="bootstrap"),
        description=None,
        body=(),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=bootstrap_seed[0],
                    predicate=bootstrap_seed[1],
                    object=bootstrap_seed[2],
                )
            ),
        ),
        silent=True,
    )
    stimulated_rule = Rule(
        id=RuleId(ruleset="test", rule_id="stimulated"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=bootstrap_seed[0],
                    predicate=bootstrap_seed[1],
                    object=bootstrap_seed[2],
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=RDF.List,
                    predicate=RDF.type,
                    object=RDFS.Resource,
                )
            ),
        ),
        silent=False,
    )
    engine = RETEEngine(
        config=_engine_config(derivation_logger=logger),
        rules=[bootstrap_rule, stimulated_rule],
    )

    engine.warmup([])

    assert len(logger.records) == 2
    assert all(record.bootstrap for record in logger.records)
    assert all(record.silent for record in logger.records)
    assert {record.rule_id.rule_id for record in logger.records} == {
        "bootstrap",
        "stimulated",
    }


def test_rete_engine_processes_matches_in_agenda_order() -> None:
    x = Variable("x")
    logger = RecordingLogger()
    context = BNode()
    broad_rule = Rule(
        id=RuleId(ruleset="test", rule_id="broad"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x,
                    predicate=URIRef("urn:test:derived"),
                    object=URIRef("urn:test:broad"),
                )
            ),
        ),
        salience=1,
    )
    prioritized_rule = Rule(
        id=RuleId(ruleset="test", rule_id="prioritized"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=x,
                    predicate=URIRef("urn:test:derived"),
                    object=URIRef("urn:test:priority"),
                )
            ),
        ),
        salience=10,
    )
    engine = RETEEngine(
        config=_engine_config(context=context, derivation_logger=logger),
        rules=[broad_rule, prioritized_rule],
    )

    inferred = engine.add_triples([(URIRef("urn:test:A"), RDF.type, RDFS.Class)])

    assert inferred == {
        (URIRef("urn:test:A"), URIRef("urn:test:derived"), URIRef("urn:test:broad")),
        (
            URIRef("urn:test:A"),
            URIRef("urn:test:derived"),
            URIRef("urn:test:priority"),
        ),
    }
    assert [record.rule_id.rule_id for record in logger.records] == [
        "prioritized",
        "broad",
    ]


def test_rete_engine_add_triples_executes_callbacks_via_agenda() -> None:
    x = Variable("x")
    callback = RecordingCallback()
    context = BNode()
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="callback"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(
            CallbackConsequent(
                callback="trace_class",
                arguments=(x, URIRef("urn:test:marker")),
            ),
        ),
        salience=4,
    )
    engine = RETEEngine(
        config=_engine_config(
            context=context,
            builtins=Builtins.EMPTY.extend(more_callbacks={"trace_class": callback}),
        ),
        rules=[rule],
    )

    inferred = engine.add_triples([(URIRef("urn:test:A"), RDF.type, RDFS.Class)])

    assert inferred == set()
    assert len(callback.calls) == 1
    callback_context, callback_args = callback.calls[0]
    assert callback_args == (URIRef("urn:test:A"), URIRef("urn:test:marker"))
    assert callback_context.context == context
    assert callback_context.rule_id == rule.id
    assert callback_context.bindings == {"x": URIRef("urn:test:A")}
    assert callback_context.premises == ((URIRef("urn:test:A"), RDF.type, RDFS.Class),)
    assert callback_context.depth == 0


def test_rete_engine_add_triples_rejects_unknown_callback_hook() -> None:
    x = Variable("x")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="missing-callback"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=x, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(CallbackConsequent(callback="missing", arguments=(x,)),),
    )
    engine = RETEEngine(config=_engine_config(), rules=[rule])

    with pytest.raises(FatalRuleError, match="Unknown callback hook `missing`"):
        engine.add_triples([(URIRef("urn:test:A"), RDF.type, RDFS.Class)])


def test_rete_engine_tracks_stated_and_derived_facts_in_working_memory() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="subclass"),
        description=None,
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
    engine = RETEEngine(config=_engine_config(), rules=[rule])
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    alice = URIRef("urn:test:alice")
    stated = (alice, RDF.type, human)
    derived = (alice, RDF.type, mammal)

    inferred = engine.add_triples([stated, (human, RDFS.subClassOf, mammal)])

    assert inferred == {derived}
    stated_fact = engine.working_memory.get_fact(stated)
    derived_fact = engine.working_memory.get_fact(derived)
    assert stated_fact is not None
    assert derived_fact is not None
    assert stated_fact.stated is True
    assert derived_fact.stated is False
    assert engine.tms.is_supported(stated)
    assert engine.tms.is_supported(derived)
    assert engine.tms.support_count(derived) == 1


def _subclass_chain_engine() -> tuple[RETEEngine, Rule]:
    """Build an engine with a single ``rdfs9``-style subclass-chain rule."""
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="subclass-chain"),
        description=None,
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
    engine = RETEEngine(config=_engine_config(), rules=[rule])
    return engine, rule


def test_retract_triples_stated_with_no_dependents_updates_engine_state() -> None:
    engine, _ = _subclass_chain_engine()
    triple = (URIRef("urn:test:alice"), RDF.type, URIRef("urn:test:Human"))
    engine.add_triples([triple])
    assert triple in engine.known_triples
    assert triple in engine.materialized_triples

    cascade = engine.retract_triples([triple])

    assert cascade == {triple}
    assert triple not in engine.known_triples
    assert triple not in engine.materialized_triples
    assert engine.working_memory.get_fact(triple) is None


def test_retract_triples_returns_empty_set_for_absent_triple() -> None:
    engine, _ = _subclass_chain_engine()
    absent = (URIRef("urn:test:absent"), RDF.type, URIRef("urn:test:Class"))

    assert engine.retract_triples([absent]) == set()
    assert engine.retract_triples([]) == set()


def test_retract_triples_cascades_multi_hop_rdfs_subclass_chain() -> None:
    engine, _ = _subclass_chain_engine()
    alice = URIRef("urn:test:alice")
    a_cls = URIRef("urn:test:A")
    b_cls = URIRef("urn:test:B")
    c_cls = URIRef("urn:test:C")
    seed = (alice, RDF.type, a_cls)
    derived_b = (alice, RDF.type, b_cls)
    derived_c = (alice, RDF.type, c_cls)

    inferred = engine.add_triples(
        [
            seed,
            (a_cls, RDFS.subClassOf, b_cls),
            (b_cls, RDFS.subClassOf, c_cls),
        ]
    )
    assert {derived_b, derived_c}.issubset(inferred)

    cascade = engine.retract_triples([seed])

    assert cascade == {seed, derived_b, derived_c}
    for triple in cascade:
        assert triple not in engine.known_triples
        assert triple not in engine.materialized_triples
        assert engine.working_memory.get_fact(triple) is None


def test_retract_triples_is_idempotent_for_already_retracted_triple() -> None:
    engine, _ = _subclass_chain_engine()
    alice = URIRef("urn:test:alice")
    a_cls = URIRef("urn:test:A")
    b_cls = URIRef("urn:test:B")
    seed = (alice, RDF.type, a_cls)

    engine.add_triples([seed, (a_cls, RDFS.subClassOf, b_cls)])
    first_cascade = engine.retract_triples([seed])
    assert seed in first_cascade

    second_cascade = engine.retract_triples([seed])

    assert second_cascade == set()


def test_retract_triples_keeps_stated_and_derived_fact_with_stated_cleared() -> None:
    engine, _ = _subclass_chain_engine()
    alice = URIRef("urn:test:alice")
    a_cls = URIRef("urn:test:A")
    b_cls = URIRef("urn:test:B")
    derived = (alice, RDF.type, b_cls)

    # The user's batch contains both the eventual antecedents AND the derived
    # triple; per JTMS semantics this fact ends up stated AND derived.
    engine.add_triples(
        [
            (alice, RDF.type, a_cls),
            derived,
            (a_cls, RDFS.subClassOf, b_cls),
        ]
    )
    fact = engine.working_memory.get_fact(derived)
    assert fact is not None and fact.stated is True
    assert engine.tms.justifications_for(derived)

    cascade = engine.retract_triples([derived])

    assert cascade == set()
    surviving = engine.working_memory.get_fact(derived)
    assert surviving is not None
    assert surviving.stated is False
    assert derived in engine.known_triples
    assert derived in engine.materialized_triples


def test_retract_triples_preserves_derived_only_fact() -> None:
    engine, _ = _subclass_chain_engine()
    alice = URIRef("urn:test:alice")
    a_cls = URIRef("urn:test:A")
    b_cls = URIRef("urn:test:B")
    derived = (alice, RDF.type, b_cls)

    engine.add_triples(
        [
            (alice, RDF.type, a_cls),
            (a_cls, RDFS.subClassOf, b_cls),
        ]
    )

    cascade = engine.retract_triples([derived])

    assert cascade == set()
    surviving = engine.working_memory.get_fact(derived)
    assert surviving is not None
    assert surviving.stated is False
    assert derived in engine.known_triples


def test_retract_triples_evicts_stale_partial_matches_so_replay_does_not_misfire() -> (
    None
):
    engine, _ = _subclass_chain_engine()
    alice = URIRef("urn:test:alice")
    a_cls = URIRef("urn:test:A")
    b_cls = URIRef("urn:test:B")
    seed = (alice, RDF.type, a_cls)
    schema = (a_cls, RDFS.subClassOf, b_cls)
    derived = (alice, RDF.type, b_cls)

    engine.add_triples([seed, schema])
    assert derived in engine.known_triples

    engine.retract_triples([seed])

    registry = engine.matcher.registry
    for memory in (registry.alpha_memory, registry.beta_memory):
        for matches in memory.values():
            for match in matches.values():
                assert all(
                    fact.triple != seed and fact.triple != derived
                    for fact in match.facts
                )

    other = URIRef("urn:test:bob")
    new_seed = (other, RDF.type, a_cls)
    inferred = engine.add_triples([new_seed])

    assert (other, RDF.type, b_cls) in inferred
    assert derived not in engine.known_triples


def test_retract_triples_supports_iterable_input_and_batch_call() -> None:
    engine, _ = _subclass_chain_engine()
    alice = URIRef("urn:test:alice")
    bob = URIRef("urn:test:bob")
    a_cls = URIRef("urn:test:A")
    b_cls = URIRef("urn:test:B")
    seed_a = (alice, RDF.type, a_cls)
    seed_b = (bob, RDF.type, a_cls)
    schema = (a_cls, RDFS.subClassOf, b_cls)

    engine.add_triples([seed_a, seed_b, schema])

    cascade = engine.retract_triples(iter([seed_a, seed_b]))

    assert {seed_a, seed_b}.issubset(cascade)
    assert (alice, RDF.type, b_cls) in cascade
    assert (bob, RDF.type, b_cls) in cascade
    assert all(engine.working_memory.get_fact(triple) is None for triple in cascade)


def test_rete_engine_tracks_multiple_supports_for_one_derived_fact() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="subclass"),
        description=None,
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
    engine = RETEEngine(config=_engine_config(), rules=[rule])
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    person = URIRef("urn:test:Person")
    mammal = URIRef("urn:test:Mammal")
    derived = (alice, RDF.type, mammal)

    inferred = engine.add_triples(
        [
            (alice, RDF.type, human),
            (alice, RDF.type, person),
            (human, RDFS.subClassOf, mammal),
            (person, RDFS.subClassOf, mammal),
        ]
    )

    assert inferred == {derived}
    supports = engine.tms.justifications_for(derived)
    alice_human = engine.working_memory.get_fact((alice, RDF.type, human))
    human_mammal = engine.working_memory.get_fact((human, RDFS.subClassOf, mammal))
    alice_person = engine.working_memory.get_fact((alice, RDF.type, person))
    person_mammal = engine.working_memory.get_fact((person, RDFS.subClassOf, mammal))
    assert alice_human is not None
    assert human_mammal is not None
    assert alice_person is not None
    assert person_mammal is not None
    assert len(supports) == 2
    assert {frozenset(justification.antecedent_ids) for justification in supports} == {
        frozenset((alice_human.id, human_mammal.id)),
        frozenset((alice_person.id, person_mammal.id)),
    }
    assert engine.tms.support_count(derived) == 2
