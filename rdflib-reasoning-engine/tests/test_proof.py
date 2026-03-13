import pytest
from pydantic import ValidationError
from rdflib import BNode, URIRef
from rdflib.namespace import OWL, RDF, RDFS
from rdflib.term import Variable
from rdflibr.engine.derivation import DerivationProofReconstructor
from rdflibr.engine.proof import (
    AuthorityReference,
    ContradictionClaim,
    DerivationRecord,
    DirectProof,
    ProofLeaf,
    RuleApplication,
    RuleDescription,
    RuleId,
    TripleFact,
    VariableBinding,
)
from rdflibr.engine.rules import Rule, TripleCondition, TripleConsequent, TriplePattern


def test_triple_fact_uses_discriminated_kind() -> None:
    context = BNode()
    subject = URIRef("urn:test:s")
    predicate = URIRef("urn:test:p")
    obj = URIRef("urn:test:o")

    fact = TripleFact(context=context, triple=(subject, predicate, obj))

    assert fact.kind == "triple"
    assert fact.model_dump()["kind"] == "triple"


def test_proof_models_are_immutable() -> None:
    context = BNode()
    fact = TripleFact(
        context=context,
        triple=(
            URIRef("urn:test:s"),
            RDF.type,
            URIRef("urn:test:Immutable"),
        ),
    )

    with pytest.raises(ValidationError):
        fact.kind = "text_claim"


def test_direct_proof_supports_rule_application_tree() -> None:
    context = BNode()
    socrates = URIRef("urn:test:Socrates")
    human = URIRef("urn:test:Human")
    mortal = URIRef("urn:test:Mortal")

    premise_a = TripleFact(context=context, triple=(socrates, RDF.type, human))
    premise_b = TripleFact(context=context, triple=(human, RDFS.subClassOf, mortal))
    conclusion = TripleFact(context=context, triple=(socrates, RDF.type, mortal))
    support_conclusion = TripleFact(
        context=context,
        triple=(human, RDF.type, RDFS.Class),
    )

    rule_description = RuleDescription(
        label="Subclass typing propagation",
        description="Propagate rdf:type across rdfs:subClassOf.",
        references=[
            AuthorityReference(
                kind="normative_spec",
                uri=URIRef("https://www.w3.org/TR/rdf11-mt/#RDFS_Interpretations"),
                label="RDF 1.1 Semantics: RDFS Interpretations",
            )
        ],
    )
    rule = Rule(
        id=RuleId(
            ruleset="rdfs",
            rule_id="rdfs9",
        ),
        description=rule_description,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=Variable("x"),
                    predicate=RDFS.subClassOf,
                    object=Variable("y"),
                )
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=Variable("a"),
                    predicate=RDF.type,
                    object=Variable("x"),
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=Variable("a"),
                    predicate=RDF.type,
                    object=Variable("y"),
                )
            ),
        ),
    )

    proof = DirectProof(
        context=context,
        goal=conclusion,
        proof=RuleApplication.from_rule(
            rule,
            conclusions=[conclusion, support_conclusion],
            premises=[
                ProofLeaf(claim=premise_a),
                ProofLeaf(claim=premise_b),
            ],
            derivation=DerivationRecord(
                context=context,
                conclusions=[conclusion, support_conclusion],
                premises=[premise_a, premise_b],
                rule_id=RuleId(
                    ruleset="rdfs",
                    rule_id="rdfs9",
                ),
                bindings=[
                    VariableBinding(name="?x", value=socrates),
                    VariableBinding(name="?c", value=human),
                    VariableBinding(name="?d", value=mortal),
                ],
            ),
        ),
        verdict="proved",
    )

    dumped = proof.model_dump(mode="python")

    assert dumped["goal"]["kind"] == "triple"
    assert dumped["proof"]["node_kind"] == "rule_application"
    assert len(dumped["proof"]["conclusions"]) == 2
    assert dumped["proof"]["premises"][0]["node_kind"] == "leaf"
    assert dumped["proof"]["premises"][0]["claim"]["kind"] == "triple"
    assert dumped["proof"]["description"]["references"][0]["kind"] == "normative_spec"
    assert dumped["proof"]["rule_id"]["rule_id"] == "rdfs9"


def test_contradiction_claim_wraps_triple_witness() -> None:
    context = BNode()
    witness = TripleFact(
        context=context,
        triple=(URIRef("urn:test:x"), RDF.type, OWL.Nothing),
    )

    contradiction = ContradictionClaim(context=context, witness=witness)

    assert contradiction.kind == "contradiction"
    assert contradiction.witness.triple[2] == OWL.Nothing


def test_rule_application_rejects_misaligned_derivation_rule() -> None:
    context = BNode()
    premise = TripleFact(
        context=context,
        triple=(URIRef("urn:test:s"), RDF.type, URIRef("urn:test:A")),
    )
    conclusion = TripleFact(
        context=context,
        triple=(URIRef("urn:test:s"), RDF.type, URIRef("urn:test:B")),
    )

    with pytest.raises(ValidationError, match="MUST match DerivationRecord.rule_id"):
        RuleApplication(
            conclusions=[conclusion],
            premises=[ProofLeaf(claim=premise)],
            rule_id=RuleId(ruleset="rdfs", rule_id="rdfs9"),
            description=RuleDescription(label="Subclass typing propagation"),
            derivation=DerivationRecord(
                context=context,
                conclusions=[conclusion],
                premises=[premise],
                rule_id=RuleId(
                    ruleset="custom",
                    rule_id="custom-1",
                ),
            ),
        )


def test_rule_application_allows_agent_description_without_rule_id() -> None:
    context = BNode()
    claim = TripleFact(
        context=context,
        triple=(URIRef("urn:test:s"), RDF.type, URIRef("urn:test:Human")),
    )

    step = RuleApplication.from_description(
        conclusions=[claim],
        premises=[ProofLeaf(claim=claim)],
        description=RuleDescription(
            label="Agent-supplied intended semantics",
            description="This step is justified by the agent's intended reading.",
        ),
    )

    assert step.rule_id is None
    assert step.description is not None


def test_rule_application_requires_rule_id_or_description() -> None:
    context = BNode()
    claim = TripleFact(
        context=context,
        triple=(URIRef("urn:test:s"), RDF.type, URIRef("urn:test:Human")),
    )

    with pytest.raises(
        ValidationError, match="at least one of `rule_id` or `description`"
    ):
        RuleApplication(
            conclusions=[claim],
            premises=[ProofLeaf(claim=claim)],
        )


def test_derivation_proof_reconstructor_builds_nested_direct_proof_tree() -> None:
    context = BNode()
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")
    animal = URIRef("urn:test:Animal")
    goal = TripleFact(context=context, triple=(alice, RDF.type, animal))
    intermediate = TripleFact(context=context, triple=(alice, RDF.type, mammal))
    premise_a = TripleFact(context=context, triple=(alice, RDF.type, human))
    premise_b = TripleFact(context=context, triple=(human, RDFS.subClassOf, mammal))
    premise_c = TripleFact(context=context, triple=(mammal, RDFS.subClassOf, animal))

    records = [
        DerivationRecord(
            context=context,
            conclusions=[intermediate],
            premises=[premise_a, premise_b],
            rule_id=RuleId(ruleset="rdfs", rule_id="rdfs9"),
            depth=1,
        ),
        DerivationRecord(
            context=context,
            conclusions=[goal],
            premises=[intermediate, premise_c],
            rule_id=RuleId(ruleset="rdfs", rule_id="rdfs9"),
            depth=2,
        ),
    ]

    proof = DerivationProofReconstructor().reconstruct(goal, records)

    assert proof.context == context
    assert proof.goal == goal
    assert proof.verdict == "proved"
    assert isinstance(proof.proof, RuleApplication)
    assert proof.proof.derivation == records[1]
    assert isinstance(proof.proof.premises[0], RuleApplication)
    assert proof.proof.premises[0].derivation == records[0]
    assert isinstance(proof.proof.premises[1], ProofLeaf)
    assert proof.proof.premises[1].claim == premise_c


def test_derivation_proof_reconstructor_uses_leaf_for_unexplained_goal() -> None:
    context = BNode()
    goal = TripleFact(
        context=context,
        triple=(URIRef("urn:test:s"), RDF.type, URIRef("urn:test:Human")),
    )

    proof = DerivationProofReconstructor().reconstruct(goal, [])

    assert proof.verdict == "incomplete"
    assert isinstance(proof.proof, ProofLeaf)
    assert proof.proof.claim == goal
