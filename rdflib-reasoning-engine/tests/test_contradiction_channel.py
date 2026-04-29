import warnings

import pytest
from rdflib.namespace import OWL, RDF
from rdflib.term import BNode, URIRef, Variable
from rdflib_reasoning.engine.api import RETEEngine
from rdflib_reasoning.engine.derivation import (
    ContradictionWarning,
    DerivationProofReconstructor,
    DropContradictionRecorder,
    InMemoryContradictionRecorder,
)
from rdflib_reasoning.engine.proof import (
    ContradictionClaim,
    ContradictionRecord,
    RuleId,
    TripleFact,
)
from rdflib_reasoning.engine.rules import (
    ContradictionConsequent,
    Rule,
    TripleCondition,
    TriplePattern,
)
from rdflib_reasoning.engine.rulesets import OWL2_RL_CONTRADICTION_RULES

_X = Variable("x")
_P = Variable("p")


def test_contradiction_consequent_records_non_mutating_diagnostics() -> None:
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="prp-irp"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P,
                    predicate=RDF.type,
                    object=OWL.IrreflexiveProperty,
                )
            ),
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_X)),
        ),
        head=(
            ContradictionConsequent(
                category="prp-irp",
                detail="Irreflexive property used reflexively.",
                arguments=(_X, _P, _X),
            ),
        ),
    )
    context = BNode()
    silent_recorder = InMemoryContradictionRecorder(warn=False)
    engine = RETEEngine(
        context_data={"context": context, "contradiction_recorder": silent_recorder},
        rules=[rule],
    )
    prop = URIRef("urn:test:p")
    subject = URIRef("urn:test:s")
    irreflexive = (prop, RDF.type, OWL.IrreflexiveProperty)
    violation = (subject, prop, subject)

    inferred = engine.add_triples([irreflexive, violation])

    assert inferred == set()
    assert engine.known_triples == {irreflexive, violation}
    records = engine.contradiction_records(context=context)
    assert len(records) == 1
    record = records[0]
    assert record.rule_id == rule.id
    assert record.category == "prp-irp"
    assert record.sequence_id == 1
    assert {premise.triple for premise in record.premises} == {irreflexive, violation}
    assert record.witness is not None
    assert record.witness.triple == violation


def test_owl2_rl_contradiction_profile_contains_expected_false_family_rules() -> None:
    expected = {
        "eq-diff1",
        "prp-irp",
        "prp-asyp",
        "prp-npa1",
        "prp-npa2",
        "cls-nothing2",
    }
    present = {rule.id.rule_id for rule in OWL2_RL_CONTRADICTION_RULES}

    assert expected == present


def test_contradiction_api_clear_resets_sequence() -> None:
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="nothing"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=RDF.type, object=OWL.Nothing
                )
            ),
        ),
        head=(
            ContradictionConsequent(
                category="cls-nothing2",
                detail="Individual typed as owl:Nothing.",
                arguments=(_X, RDF.type, OWL.Nothing),
            ),
        ),
    )
    context = BNode()
    silent_recorder = InMemoryContradictionRecorder(warn=False)
    engine = RETEEngine(
        context_data={"context": context, "contradiction_recorder": silent_recorder},
        rules=[rule],
    )
    triple = (URIRef("urn:test:a"), RDF.type, OWL.Nothing)
    triple2 = (URIRef("urn:test:b"), RDF.type, OWL.Nothing)

    engine.add_triples([triple2])
    assert [r.sequence_id for r in engine.contradiction_records()] == [1]

    engine.clear_contradiction_records()
    assert engine.contradiction_records() == ()

    engine.add_triples([triple])
    assert [r.sequence_id for r in engine.contradiction_records()] == [1]


def test_reconstructor_builds_contradiction_proof_from_contradiction_records() -> None:
    context = BNode()
    witness = TripleFact(
        context=context,
        triple=(URIRef("urn:test:s"), RDF.type, OWL.Nothing),
    )
    goal = ContradictionClaim(context=context, witness=witness)
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="nothing"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=RDF.type, object=OWL.Nothing
                )
            ),
        ),
        head=(
            ContradictionConsequent(
                category="cls-nothing2",
                detail="Individual typed as owl:Nothing.",
                arguments=(_X, RDF.type, OWL.Nothing),
            ),
        ),
    )
    silent_recorder = InMemoryContradictionRecorder(warn=False)
    engine = RETEEngine(
        context_data={"context": context, "contradiction_recorder": silent_recorder},
        rules=[rule],
    )

    engine.add_triples([witness.triple])

    records = engine.contradiction_records()
    proof = DerivationProofReconstructor().reconstruct(goal, records)

    assert proof.verdict == "contradiction"
    assert proof.goal == goal


def _sample_contradiction_record() -> ContradictionRecord:
    ctx = BNode()
    tf = TripleFact(
        context=ctx, triple=(URIRef("urn:contradiction-sample"), RDF.type, OWL.Nothing)
    )
    return ContradictionRecord(
        context=ctx,
        rule_id=RuleId(ruleset="sample", rule_id="rule"),
        premises=[tf],
        sequence_id=1,
        witness=tf,
        category="sample",
        detail="sample contradiction",
    )


def test_in_memory_contradiction_recorder_warn_emits_contradiction_warning() -> None:
    rec = _sample_contradiction_record()
    sink = InMemoryContradictionRecorder(warn=True)
    with pytest.warns(ContradictionWarning):
        sink.record(rec)
    assert len(tuple(sink.iter_records())) == 1


def test_in_memory_contradiction_recorder_warn_false_is_quiet() -> None:
    rec = _sample_contradiction_record()
    sink = InMemoryContradictionRecorder(warn=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sink.record(rec)
    assert len(caught) == 0


def test_drop_contradiction_recorder_has_no_retention_warns_by_default() -> None:
    rec = _sample_contradiction_record()
    drop = DropContradictionRecorder(warn=True)
    with pytest.warns(ContradictionWarning):
        drop.record(rec)
    assert tuple(drop.iter_records()) == ()


def test_drop_contradiction_recorder_warn_false_emits_no_warning() -> None:
    rec = _sample_contradiction_record()
    drop = DropContradictionRecorder(warn=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        drop.record(rec)
    assert len(caught) == 0
