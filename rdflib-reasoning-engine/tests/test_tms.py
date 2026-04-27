import pytest
from rdflib.namespace import RDF, RDFS
from rdflib.term import BNode, URIRef, Variable
from rdflib_reasoning.engine.api import RETEEngine
from rdflib_reasoning.engine.proof import RuleId
from rdflib_reasoning.engine.rete.tms import RetractionOutcome, TMSController
from rdflib_reasoning.engine.rules import (
    Rule,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)


def _subclass_rule(*, silent: bool = False) -> Rule:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    return Rule(
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
        silent=silent,
    )


def _engine_with_subclass_rule(*, silent: bool = False) -> RETEEngine:
    return RETEEngine(
        context_data={"context": BNode()}, rules=[_subclass_rule(silent=silent)]
    )


def test_support_snapshot_for_stated_fact_reports_stated_and_no_justifications() -> (
    None
):
    engine = RETEEngine(context_data={"context": BNode()}, rules=[])
    stated = (URIRef("urn:test:alice"), RDF.type, URIRef("urn:test:Human"))

    engine.add_triples([stated])
    snapshot = engine.tms.support_snapshot(stated)
    stated_fact = engine.working_memory.get_fact(stated)

    assert stated_fact is not None
    assert snapshot.triple == stated
    assert snapshot.fact_id == stated_fact.id
    assert snapshot.is_present is True
    assert snapshot.is_stated is True
    assert snapshot.justification_ids == ()
    assert snapshot.justification_count == 0
    assert snapshot.is_supported is True


def test_support_snapshot_for_derived_fact_reports_justifications_with_stable_ids() -> (
    None
):
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    derived = (alice, RDF.type, mammal)

    engine.add_triples([(alice, RDF.type, human), (human, RDFS.subClassOf, mammal)])
    supports = engine.tms.justifications_for(derived)
    snapshot = engine.tms.support_snapshot(derived)
    derived_fact = engine.working_memory.get_fact(derived)

    assert derived_fact is not None
    assert len(supports) == 1
    assert snapshot.triple == derived
    assert snapshot.fact_id == derived_fact.id
    assert snapshot.is_present is True
    assert snapshot.is_stated is False
    assert snapshot.justification_ids == (supports[0].id,)
    assert snapshot.justification_count == 1
    assert snapshot.is_supported is True


def test_support_snapshot_for_unknown_triple_returns_absent() -> None:
    tms = TMSController()
    unknown = (URIRef("urn:test:alice"), RDF.type, URIRef("urn:test:Missing"))

    snapshot = tms.support_snapshot(unknown)

    assert snapshot.triple == unknown
    assert snapshot.fact_id is None
    assert snapshot.is_present is False
    assert snapshot.is_stated is False
    assert snapshot.justification_ids == ()
    assert snapshot.justification_count == 0
    assert snapshot.is_supported is False


def test_would_remain_supported_when_alternative_justification_exists() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    person = URIRef("urn:test:Person")
    mammal = URIRef("urn:test:Mammal")
    derived = (alice, RDF.type, mammal)

    engine.add_triples(
        [
            (alice, RDF.type, human),
            (alice, RDF.type, person),
            (human, RDFS.subClassOf, mammal),
            (person, RDFS.subClassOf, mammal),
        ]
    )
    supports = engine.tms.justifications_for(derived)
    alice_human = engine.working_memory.get_fact((alice, RDF.type, human))
    assert alice_human is not None

    assert len(supports) == 2
    assert engine.tms.would_remain_supported(
        derived, without_justification_id=supports[0].id
    )
    assert engine.tms.would_remain_supported(
        derived, without_antecedent_id=alice_human.id
    )


def test_would_remain_supported_returns_false_when_only_path_is_excluded() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    derived = (alice, RDF.type, mammal)

    engine.add_triples([(alice, RDF.type, human), (human, RDFS.subClassOf, mammal)])
    support = engine.tms.justifications_for(derived)[0]

    assert not engine.tms.would_remain_supported(
        derived, without_justification_id=support.id
    )


def test_would_remain_supported_for_stated_fact_returns_true_regardless_of_excluded_path() -> (
    None
):
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    stated_and_derived = (alice, RDF.type, mammal)

    engine.add_triples([(alice, RDF.type, human), (human, RDFS.subClassOf, mammal)])
    support = engine.tms.justifications_for(stated_and_derived)[0]
    engine.add_triples([stated_and_derived])

    assert engine.tms.would_remain_supported(
        stated_and_derived, without_justification_id=support.id
    )


def test_would_remain_supported_requires_exactly_one_kwarg() -> None:
    tms = TMSController()
    triple = (URIRef("urn:test:alice"), RDF.type, URIRef("urn:test:Human"))

    with pytest.raises(ValueError, match="exactly one"):
        tms.would_remain_supported(triple)
    with pytest.raises(ValueError, match="exactly one"):
        tms.would_remain_supported(
            triple,
            without_justification_id="support-a",
            without_antecedent_id="fact-a",
        )


def test_transitively_supported_for_chain_of_derivations() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    a_class = URIRef("urn:test:A")
    b_class = URIRef("urn:test:B")
    c_class = URIRef("urn:test:C")
    derived = (alice, RDF.type, c_class)

    engine.add_triples(
        [
            (alice, RDF.type, a_class),
            (a_class, RDFS.subClassOf, b_class),
            (b_class, RDFS.subClassOf, c_class),
        ]
    )

    assert engine.tms.transitively_supported(derived)


def test_transitively_supported_is_cycle_safe() -> None:
    tms = TMSController()
    a = (URIRef("urn:test:a"), RDF.type, URIRef("urn:test:A"))
    b = (URIRef("urn:test:b"), RDF.type, URIRef("urn:test:B"))
    a_fact = tms.working_memory.add_fact(a, stated=False)
    b_fact = tms.record_derivation(
        b,
        rule_id=RuleId(ruleset="test", rule_id="a-to-b"),
        premises=(a_fact,),
        bindings={},
        depth=1,
    )
    tms.record_derivation(
        a,
        rule_id=RuleId(ruleset="test", rule_id="b-to-a"),
        premises=(b_fact,),
        bindings={},
        depth=2,
    )

    assert not tms.transitively_supported(a)


def test_dependents_of_returns_direct_consequents() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    stated = (alice, RDF.type, human)
    derived = (alice, RDF.type, mammal)

    engine.add_triples([stated, (human, RDFS.subClassOf, mammal)])
    derived_fact = engine.working_memory.get_fact(derived)

    assert derived_fact is not None
    assert engine.tms.dependents_of(stated) == (derived_fact.id,)


def test_transitive_dependents_of_returns_full_downstream_set_in_deterministic_order() -> (
    None
):
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    a_class = URIRef("urn:test:A")
    b_class = URIRef("urn:test:B")
    c_class = URIRef("urn:test:C")
    stated = (alice, RDF.type, a_class)
    derived_b = (alice, RDF.type, b_class)
    derived_c = (alice, RDF.type, c_class)

    engine.add_triples(
        [
            stated,
            (a_class, RDFS.subClassOf, b_class),
            (b_class, RDFS.subClassOf, c_class),
        ]
    )
    b_fact = engine.working_memory.get_fact(derived_b)
    c_fact = engine.working_memory.get_fact(derived_c)

    assert b_fact is not None
    assert c_fact is not None
    assert engine.tms.transitive_dependents_of(stated) == tuple(
        sorted((b_fact.id, c_fact.id))
    )


def test_silent_derivation_contributes_to_support_validity() -> None:
    engine = _engine_with_subclass_rule(silent=True)
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    derived = (alice, RDF.type, mammal)

    inferred = engine.add_triples(
        [(alice, RDF.type, human), (human, RDFS.subClassOf, mammal)]
    )
    support = engine.tms.justifications_for(derived)[0]

    assert inferred == set()
    assert engine.tms.transitively_supported(derived)
    assert not engine.tms.would_remain_supported(
        derived, without_justification_id=support.id
    )


def test_support_verification_does_not_mutate_tms_state() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    stated = (alice, RDF.type, human)
    derived = (alice, RDF.type, mammal)

    engine.add_triples([stated, (human, RDFS.subClassOf, mammal)])
    support = engine.tms.justifications_for(derived)[0]
    before_facts = tuple(
        (fact.id, fact.triple, fact.stated) for fact in engine.working_memory.facts()
    )
    before_supports = {
        fact_id: tuple(sorted(supports))
        for fact_id, supports in engine.tms.justifications_by_consequent.items()
    }

    engine.tms.support_snapshot(derived)
    engine.tms.would_remain_supported(derived, without_justification_id=support.id)
    engine.tms.transitively_supported(derived)
    engine.tms.dependents_of(stated)
    engine.tms.transitive_dependents_of(stated)

    after_facts = tuple(
        (fact.id, fact.triple, fact.stated) for fact in engine.working_memory.facts()
    )
    after_supports = {
        fact_id: tuple(sorted(supports))
        for fact_id, supports in engine.tms.justifications_by_consequent.items()
    }
    assert after_facts == before_facts
    assert after_supports == before_supports


def test_retract_triple_for_unknown_triple_returns_empty_outcome() -> None:
    tms = TMSController()
    unknown = (URIRef("urn:test:alice"), RDF.type, URIRef("urn:test:Missing"))

    outcome = tms.retract_triple(unknown)

    assert outcome == RetractionOutcome()
    assert outcome.is_empty
    assert tms.working_memory.facts() == ()
    assert tms.justifications_by_consequent == {}


def test_retract_triple_removes_isolated_stated_fact() -> None:
    engine = RETEEngine(context_data={"context": BNode()}, rules=[])
    stated = (URIRef("urn:test:alice"), RDF.type, URIRef("urn:test:Human"))

    engine.add_triples([stated])
    stated_fact = engine.working_memory.get_fact(stated)
    assert stated_fact is not None

    outcome = engine.tms.retract_triple(stated)

    assert outcome.removed_fact_ids == (stated_fact.id,)
    assert outcome.removed_triples == (stated,)
    assert outcome.removed_justification_ids == ()
    assert outcome.unstated_fact_ids == ()
    assert engine.working_memory.get_fact(stated) is None
    assert not engine.working_memory.has_fact(stated)


def test_retract_triple_preserves_dependents_with_alternative_support() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    person = URIRef("urn:test:Person")
    mammal = URIRef("urn:test:Mammal")
    stated_to_retract = (alice, RDF.type, human)
    alternative_stated = (alice, RDF.type, person)
    derived = (alice, RDF.type, mammal)

    engine.add_triples(
        [
            stated_to_retract,
            alternative_stated,
            (human, RDFS.subClassOf, mammal),
            (person, RDFS.subClassOf, mammal),
        ]
    )
    derived_fact = engine.working_memory.get_fact(derived)
    stated_fact = engine.working_memory.get_fact(stated_to_retract)
    assert derived_fact is not None and stated_fact is not None
    supports_before = engine.tms.justifications_for(derived)
    assert len(supports_before) == 2
    via_human_id = next(
        justification.id
        for justification in supports_before
        if stated_fact.id in justification.antecedent_ids
    )

    outcome = engine.tms.retract_triple(stated_to_retract)

    assert outcome.removed_fact_ids == (stated_fact.id,)
    assert outcome.removed_triples == (stated_to_retract,)
    assert outcome.removed_justification_ids == (via_human_id,)
    assert outcome.unstated_fact_ids == ()
    assert engine.working_memory.get_fact(stated_to_retract) is None
    surviving_derived_fact = engine.working_memory.get_fact(derived)
    assert surviving_derived_fact is not None
    surviving_justifications = engine.tms.justifications_for(derived)
    assert len(surviving_justifications) == 1
    surviving_justification = surviving_justifications[0]
    assert via_human_id != surviving_justification.id


def test_retract_triple_cascades_through_chain_of_derivations() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    a_class = URIRef("urn:test:A")
    b_class = URIRef("urn:test:B")
    c_class = URIRef("urn:test:C")
    seed = (alice, RDF.type, a_class)
    derived_b = (alice, RDF.type, b_class)
    derived_c = (alice, RDF.type, c_class)

    engine.add_triples(
        [
            seed,
            (a_class, RDFS.subClassOf, b_class),
            (b_class, RDFS.subClassOf, c_class),
        ]
    )
    seed_fact = engine.working_memory.get_fact(seed)
    derived_b_fact = engine.working_memory.get_fact(derived_b)
    derived_c_fact = engine.working_memory.get_fact(derived_c)
    assert seed_fact is not None
    assert derived_b_fact is not None
    assert derived_c_fact is not None

    outcome = engine.tms.retract_triple(seed)

    expected_fact_ids = tuple(
        sorted((seed_fact.id, derived_b_fact.id, derived_c_fact.id))
    )
    assert outcome.removed_fact_ids == expected_fact_ids
    assert set(outcome.removed_triples) == {seed, derived_b, derived_c}
    assert engine.working_memory.get_fact(seed) is None
    assert engine.working_memory.get_fact(derived_b) is None
    assert engine.working_memory.get_fact(derived_c) is None
    schema_class = (a_class, RDFS.subClassOf, b_class)
    assert engine.working_memory.get_fact(schema_class) is not None


def test_retract_triple_verify_fixed_point_promotes_through_kept_facts() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    a_class = URIRef("urn:test:A")
    b_class = URIRef("urn:test:B")
    c_class = URIRef("urn:test:C")
    seed = (alice, RDF.type, a_class)
    direct_to_b = (alice, RDF.type, b_class)
    derived_c = (alice, RDF.type, c_class)

    engine.add_triples(
        [
            seed,
            direct_to_b,
            (a_class, RDFS.subClassOf, b_class),
            (b_class, RDFS.subClassOf, c_class),
        ]
    )
    direct_to_b_fact = engine.working_memory.get_fact(direct_to_b)
    derived_c_fact = engine.working_memory.get_fact(derived_c)
    assert direct_to_b_fact is not None and derived_c_fact is not None

    outcome = engine.tms.retract_triple(seed)

    assert engine.working_memory.get_fact(direct_to_b) is direct_to_b_fact
    assert engine.working_memory.get_fact(derived_c) is derived_c_fact
    assert direct_to_b_fact.id not in outcome.removed_fact_ids
    assert derived_c_fact.id not in outcome.removed_fact_ids
    assert engine.working_memory.get_fact(seed) is None
    surviving_c_justifications = engine.tms.justifications_for(derived_c)
    assert len(surviving_c_justifications) == 1
    assert direct_to_b_fact.id in surviving_c_justifications[0].antecedent_ids


def test_retract_triple_clears_stated_flag_when_independent_support_exists() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    stated_and_derived = (alice, RDF.type, mammal)

    engine.add_triples([(alice, RDF.type, human), (human, RDFS.subClassOf, mammal)])
    derived_fact = engine.working_memory.get_fact(stated_and_derived)
    assert derived_fact is not None
    engine.add_triples([stated_and_derived])
    assert derived_fact.stated is True
    supports_before = engine.tms.justifications_for(stated_and_derived)
    assert len(supports_before) == 1

    outcome = engine.tms.retract_triple(stated_and_derived)

    assert outcome.removed_fact_ids == ()
    assert outcome.removed_triples == ()
    assert outcome.removed_justification_ids == ()
    assert outcome.unstated_fact_ids == (derived_fact.id,)
    surviving_fact = engine.working_memory.get_fact(stated_and_derived)
    assert surviving_fact is derived_fact
    assert surviving_fact.stated is False
    assert engine.tms.is_supported(stated_and_derived)
    supports_after = engine.tms.justifications_for(stated_and_derived)
    assert {justification.id for justification in supports_after} == {
        support.id for support in supports_before
    }


def test_retract_triple_rejects_derived_only_facts() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    derived = (alice, RDF.type, mammal)

    engine.add_triples([(alice, RDF.type, human), (human, RDFS.subClassOf, mammal)])
    before_facts = tuple(
        (fact.id, fact.triple, fact.stated) for fact in engine.working_memory.facts()
    )
    before_supports = {
        fact_id: tuple(sorted(supports))
        for fact_id, supports in engine.tms.justifications_by_consequent.items()
    }

    with pytest.raises(ValueError, match="only accepts stated facts"):
        engine.tms.retract_triple(derived)

    after_facts = tuple(
        (fact.id, fact.triple, fact.stated) for fact in engine.working_memory.facts()
    )
    after_supports = {
        fact_id: tuple(sorted(supports))
        for fact_id, supports in engine.tms.justifications_by_consequent.items()
    }
    assert after_facts == before_facts
    assert after_supports == before_supports


def test_retract_triple_cascades_through_silent_derivations() -> None:
    engine = _engine_with_subclass_rule(silent=True)
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    seed = (alice, RDF.type, human)
    silent_derived = (alice, RDF.type, mammal)

    engine.add_triples([seed, (human, RDFS.subClassOf, mammal)])
    seed_fact = engine.working_memory.get_fact(seed)
    silent_fact = engine.working_memory.get_fact(silent_derived)
    assert seed_fact is not None and silent_fact is not None

    outcome = engine.tms.retract_triple(seed)

    assert set(outcome.removed_fact_ids) == {seed_fact.id, silent_fact.id}
    assert set(outcome.removed_triples) == {seed, silent_derived}
    assert engine.working_memory.get_fact(seed) is None
    assert engine.working_memory.get_fact(silent_derived) is None


def test_retract_triple_is_cycle_safe() -> None:
    tms = TMSController()
    seed_triple = (URIRef("urn:test:seed"), RDF.type, URIRef("urn:test:Seed"))
    a = (URIRef("urn:test:a"), RDF.type, URIRef("urn:test:A"))
    b = (URIRef("urn:test:b"), RDF.type, URIRef("urn:test:B"))
    seed_fact = tms.working_memory.add_fact(seed_triple, stated=True)
    a_fact = tms.record_derivation(
        a,
        rule_id=RuleId(ruleset="test", rule_id="seed-to-a"),
        premises=(seed_fact,),
        bindings={},
        depth=1,
    )
    b_fact = tms.record_derivation(
        b,
        rule_id=RuleId(ruleset="test", rule_id="a-to-b"),
        premises=(a_fact,),
        bindings={},
        depth=2,
    )
    tms.record_derivation(
        a,
        rule_id=RuleId(ruleset="test", rule_id="b-to-a"),
        premises=(b_fact,),
        bindings={},
        depth=3,
    )

    outcome = tms.retract_triple(seed_triple)

    assert set(outcome.removed_fact_ids) == {seed_fact.id, a_fact.id, b_fact.id}
    assert set(outcome.removed_triples) == {seed_triple, a, b}
    assert tms.working_memory.facts() == ()
    assert tms.justifications_by_consequent == {}


def test_retract_triple_preserves_dependency_graph_consistency() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    person = URIRef("urn:test:Person")
    mammal = URIRef("urn:test:Mammal")
    stated_to_retract = (alice, RDF.type, human)
    alternative_stated = (alice, RDF.type, person)
    derived = (alice, RDF.type, mammal)

    engine.add_triples(
        [
            stated_to_retract,
            alternative_stated,
            (human, RDFS.subClassOf, mammal),
            (person, RDFS.subClassOf, mammal),
        ]
    )
    person_fact = engine.working_memory.get_fact(alternative_stated)
    derived_fact = engine.working_memory.get_fact(derived)
    assert person_fact is not None and derived_fact is not None

    engine.tms.retract_triple(stated_to_retract)

    assert engine.tms.dependents_of(stated_to_retract) == ()
    assert engine.tms.transitive_dependents_of(stated_to_retract) == ()
    assert engine.tms.dependents_of(alternative_stated) == (derived_fact.id,)
    assert engine.tms.transitive_dependents_of(alternative_stated) == (derived_fact.id,)
    assert engine.tms.transitive_dependents_of(derived) == ()
    surviving_antecedents = engine.tms.dependency_graph.antecedents_of(derived_fact.id)
    assert person_fact.id in surviving_antecedents


def test_retract_triple_is_idempotent_for_swept_seed() -> None:
    engine = RETEEngine(context_data={"context": BNode()}, rules=[])
    stated = (URIRef("urn:test:alice"), RDF.type, URIRef("urn:test:Human"))

    engine.add_triples([stated])
    first_outcome = engine.tms.retract_triple(stated)
    assert not first_outcome.is_empty

    second_outcome = engine.tms.retract_triple(stated)
    assert second_outcome == RetractionOutcome()
    assert second_outcome.is_empty


def test_retract_triple_updates_support_snapshots_for_swept_facts() -> None:
    engine = _engine_with_subclass_rule()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    seed = (alice, RDF.type, human)
    derived = (alice, RDF.type, mammal)

    engine.add_triples([seed, (human, RDFS.subClassOf, mammal)])

    engine.tms.retract_triple(seed)

    seed_snapshot = engine.tms.support_snapshot(seed)
    derived_snapshot = engine.tms.support_snapshot(derived)
    assert seed_snapshot.is_present is False
    assert seed_snapshot.fact_id is None
    assert seed_snapshot.justification_ids == ()
    assert seed_snapshot.is_supported is False
    assert derived_snapshot.is_present is False
    assert derived_snapshot.fact_id is None
    assert derived_snapshot.justification_ids == ()
    assert derived_snapshot.is_supported is False
