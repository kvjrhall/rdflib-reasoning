import pytest
from rdflib.namespace import RDF, RDFS
from rdflib.term import BNode, URIRef, Variable
from rdflib_reasoning.engine.api import RETEEngine
from rdflib_reasoning.engine.proof import RuleId
from rdflib_reasoning.engine.rete.tms import TMSController
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
