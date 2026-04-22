import pytest
from rdflib import BNode, Graph, URIRef
from rdflib.namespace import RDF, RDFS
from rdflib.term import Variable
from rdflib_reasoning.engine.proof import (
    DirectProof,
    ProofLeaf,
    RuleApplication,
    RuleId,
    TripleFact,
)
from rdflib_reasoning.engine.proof_rendering import (
    ProofRenderer,
    build_rule_lookup,
    render_proof_markdown,
    render_proof_mermaid,
)
from rdflib_reasoning.engine.rules import (
    Rule,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from rdflib_reasoning.engine.rulesets import (
    PRODUCTION_RDF_AXIOMS,
    PRODUCTION_RDFS_RULES,
)


def _sample_rule() -> Rule:
    return Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs9"),
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


def _sample_proof() -> DirectProof:
    context = BNode()
    alice = URIRef("urn:test:alice")
    mammal = URIRef("urn:test:Mammal")
    animal = URIRef("urn:test:Animal")

    premise = TripleFact(context=context, triple=(alice, RDF.type, mammal))
    conclusion = TripleFact(context=context, triple=(alice, RDF.type, animal))

    proof_node = RuleApplication.from_rule(
        _sample_rule(),
        conclusions=[conclusion],
        premises=[ProofLeaf(claim=premise)],
    )
    return DirectProof(
        context=context, goal=conclusion, proof=proof_node, verdict="proved"
    )


def test_build_rule_lookup_rejects_duplicate_ruleset_rule_id() -> None:
    r = PRODUCTION_RDF_AXIOMS[0]
    dup = r.model_copy(deep=True)
    with pytest.raises(ValueError, match="Duplicate rule key"):
        build_rule_lookup((r, dup))


def test_render_proof_markdown_resolves_rdf_axiom_with_explicit_rules_tuple() -> None:
    axiom = PRODUCTION_RDF_AXIOMS[0]
    context = BNode()
    conclusion = TripleFact(context=context, triple=(RDF.type, RDF.type, RDF.Property))
    proof = DirectProof(
        context=context,
        goal=conclusion,
        proof=RuleApplication.from_rule(axiom, conclusions=[conclusion]),
        verdict="proved",
    )
    rendered = render_proof_markdown(proof, rules=PRODUCTION_RDFS_RULES)
    assert "rdf_axioms:rdf-axiom-rdf-type" in rendered
    assert "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" in rendered


def test_render_proof_markdown_resolves_bundled_axiom_using_default_registry() -> None:
    axiom = PRODUCTION_RDF_AXIOMS[0]
    context = BNode()
    conclusion = TripleFact(context=context, triple=(RDF.type, RDF.type, RDF.Property))
    proof = DirectProof(
        context=context,
        goal=conclusion,
        proof=RuleApplication.from_rule(axiom, conclusions=[conclusion]),
        verdict="proved",
    )
    rendered = render_proof_markdown(proof)
    assert "rdf_axioms:rdf-axiom-rdf-type" in rendered


def test_render_proof_mermaid_includes_then_for_resolved_axiom_rule() -> None:
    axiom = PRODUCTION_RDF_AXIOMS[0]
    context = BNode()
    conclusion = TripleFact(context=context, triple=(RDF.type, RDF.type, RDF.Property))
    proof = DirectProof(
        context=context,
        goal=conclusion,
        proof=RuleApplication.from_rule(axiom, conclusions=[conclusion]),
        verdict="proved",
    )
    mermaid = render_proof_mermaid(proof, rules=PRODUCTION_RDFS_RULES)
    assert "THEN" in mermaid
    assert "rdf_axioms:rdf-axiom-rdf-type" in mermaid


def test_proof_renderer_returns_none_head_when_rule_missing_from_registry() -> None:
    proof = _sample_proof()
    renderer = ProofRenderer(rules=())
    assert isinstance(proof.proof, RuleApplication)
    assert renderer._resolve_rule(proof.proof) is None


def test_render_proof_markdown_includes_step_content() -> None:
    proof = _sample_proof()

    rendered = render_proof_markdown(proof)

    assert "## Direct Proof" in rendered
    assert "Rule Application" in rendered
    assert "Conclusions" in rendered
    assert "Premises" in rendered


def test_render_proof_mermaid_includes_symbolic_if_then_rule_definition() -> None:
    proof = _sample_proof()

    rendered = render_proof_mermaid(proof)

    assert "flowchart TD" in rendered
    assert "rdfs:rdfs9" in rendered
    assert "\nIF (" in rendered
    assert "THEN (" in rendered
    assert "?x" in rendered
    assert "?y" in rendered


def test_render_proof_markdown_uses_nonbreaking_spaces_for_fully_shortened_triples() -> (
    None
):
    proof = _sample_proof()
    graph = Graph()
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("test", URIRef("urn:test:"))

    rendered = render_proof_markdown(proof, namespace_manager=graph.namespace_manager)

    assert "(test:alice\u00a0rdf:type\u00a0test:Animal)" in rendered
    assert "(test:alice\u00a0rdf:type\u00a0test:Mammal)" in rendered


def test_render_proof_markdown_falls_back_to_comma_when_not_all_terms_shorten() -> None:
    proof = _sample_proof()
    graph = Graph()
    graph.bind("rdf", RDF)

    rendered = render_proof_markdown(proof, namespace_manager=graph.namespace_manager)

    assert "(<urn:test:alice>, rdf:type, <urn:test:Animal>)" in rendered


def test_notebook_proof_renderer_displays_markdown_and_mermaid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("IPython")
    from rdflib_reasoning.engine.proof_notebook import NotebookProofRenderer

    shown: list[str] = []
    monkeypatch.setattr(
        "rdflib_reasoning.engine.proof_notebook.Markdown",
        lambda text: text,
    )
    monkeypatch.setattr(
        "rdflib_reasoning.engine.proof_notebook.display",
        lambda payload: shown.append(payload),
    )

    proof = _sample_proof()
    renderer = NotebookProofRenderer()
    markdown = renderer.markdown(proof)
    mermaid = renderer.mermaid(proof)

    assert markdown in shown[0]
    assert "```mermaid\n" in shown[1]
    assert mermaid in shown[1]
