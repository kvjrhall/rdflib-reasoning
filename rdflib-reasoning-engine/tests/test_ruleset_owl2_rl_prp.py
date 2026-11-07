"""Micro-tests for OWL 2 RL ``prp-*`` entailment rules."""

from __future__ import annotations

import textwrap
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import replace
from typing import Final

from rdflib import OWL, RDF, RDFS, XSD, Dataset, Graph, Literal, Namespace
from rdflib.term import BNode, URIRef
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.engine import (
    NO_RULES,
    Builtins,
    InMemoryDerivationLogger,
    RETEEngine,
    RETEEngineConfig,
)
from rdflib_reasoning.engine.derivation import DropContradictionRecorder
from rdflib_reasoning.engine.rules import Rule
from rdflib_reasoning.engine.rulesets.owl2_rl_prp import OWL2_RL_PRP_RULES

NS = Namespace("urn:test:")

type LoggerAndDataset = tuple[InMemoryDerivationLogger, Dataset]

_EXPECTED_PRP_RULE_IDS: Final[frozenset[str]] = frozenset(
    {
        "prp-ap",
        "prp-dom",
        "prp-rng",
        "prp-fp",
        "prp-ifp",
        "prp-symp",
        "prp-trp",
        "prp-spo1",
        "prp-spo2",
        "prp-eqp1",
        "prp-eqp2",
        "prp-inv1",
        "prp-inv2",
        "prp-key",
    }
)

_BUILTIN_ANNOTATION_PROPERTIES: Final[tuple[URIRef, ...]] = (
    RDFS.label,
    RDFS.comment,
    RDFS.seeAlso,
    RDFS.isDefinedBy,
    OWL.deprecated,
    OWL.versionInfo,
    OWL.priorVersion,
    OWL.backwardCompatibleWith,
    OWL.incompatibleWith,
)


def _prp_rules(*rule_ids: str) -> tuple[Rule, ...]:
    wanted = set(rule_ids)
    return tuple(rule for rule in OWL2_RL_PRP_RULES if rule.id.rule_id in wanted)


def _dataset_for_rules(rules: Sequence[Rule]) -> LoggerAndDataset:
    logger = InMemoryDerivationLogger()
    dataset = replace(
        NO_RULES,
        rules=tuple(rules),
        builtins=Builtins(),
        derivation_logger_factory=lambda _context: logger,
    ).dataset()
    return logger, dataset


@contextmanager
def graph_under_test(
    dataset: Dataset, graph_name: str | None = None
) -> Generator[Graph, None, None]:
    graph = dataset.default_graph
    try:
        yield graph
    except Exception as cause:
        name = f": {graph_name}" if graph_name is not None else ""
        message = textwrap.dedent(
            f"""
            Error while testing OWL 2 RL prp entailment for graph{name}:
            {graph.serialize(format="turtle")}
            """
        )
        raise AssertionError(message) from cause


def _assert_derived(
    logger: InMemoryDerivationLogger,
    *,
    rule_id: str,
    output: Triple,
) -> None:
    matching = [
        record
        for record in logger.records
        if record.rule_id.rule_id == rule_id
        and any(conclusion.triple == output for conclusion in record.conclusions)
    ]
    assert matching, f"Expected derivation for {output!r} via {rule_id}"


def test_owl2_rl_prp_rule_ids() -> None:
    """Export surface covers the requested triple-producing ``prp-*`` rules."""

    present = {rule.id.rule_id for rule in OWL2_RL_PRP_RULES}
    assert {rule.id.ruleset for rule in OWL2_RL_PRP_RULES} == {"owl2-rl"}
    assert present == _EXPECTED_PRP_RULE_IDS


def test_prp_ap_bootstrap_types_builtin_annotation_properties() -> None:
    """``prp-ap`` silently seeds built-in annotation property typing."""

    context = BNode()
    engine = RETEEngine(
        config=RETEEngineConfig(
            context=context,
            builtins=Builtins(),
            derivation_logger=InMemoryDerivationLogger(),
            contradiction_recorder=DropContradictionRecorder(),
            literal_subject_policy="error",
            predicate_term_policy="error",
        ),
        rules=_prp_rules("prp-ap"),
    )
    engine.warmup(())

    for ap in _BUILTIN_ANNOTATION_PROPERTIES:
        assert (ap, RDF.type, OWL.AnnotationProperty) in engine.known_triples
    assert engine.materialized_triples == set()


def test_prp_dom_entailment() -> None:
    """``prp-dom`` types the subject from a property domain."""

    logger, dataset = _dataset_for_rules(_prp_rules("prp-dom"))
    with graph_under_test(dataset, graph_name="prp-dom") as graph:
        graph.add((NS.hasParent, RDFS.domain, NS.Person))
        graph.add((NS.alice, NS.hasParent, NS.bob))
        output = (NS.alice, RDF.type, NS.Person)
        assert output in graph
        _assert_derived(logger, rule_id="prp-dom", output=output)


def test_prp_rng_entailment_and_literal_guard() -> None:
    """``prp-rng`` types non-literal objects and skips literal objects."""

    logger, dataset = _dataset_for_rules(_prp_rules("prp-rng"))
    with graph_under_test(dataset, graph_name="prp-rng") as graph:
        graph.add((NS.hasParent, RDFS.range, NS.Person))
        graph.add((NS.alice, NS.hasParent, NS.bob))
        graph.add((NS.name, RDFS.range, RDFS.Literal))
        graph.add((NS.alice, NS.name, Literal("Alice")))

        output = (NS.bob, RDF.type, NS.Person)
        assert output in graph
        _assert_derived(logger, rule_id="prp-rng", output=output)
        assert (Literal("Alice"), RDF.type, RDFS.Literal) not in graph


def test_prp_fp_and_ifp_equality() -> None:
    """``prp-fp`` / ``prp-ifp`` equate distinct fillers and skip self-sameAs."""

    logger, dataset = _dataset_for_rules(_prp_rules("prp-fp", "prp-ifp"))
    with graph_under_test(dataset, graph_name="prp-fp-ifp") as graph:
        graph.add((NS.mother, RDF.type, OWL.FunctionalProperty))
        graph.add((NS.alice, NS.mother, NS.m1))
        graph.add((NS.alice, NS.mother, NS.m2))
        graph.add((NS.ssn, RDF.type, OWL.InverseFunctionalProperty))
        graph.add((NS.alice, NS.ssn, NS.ssn1))
        graph.add((NS.bob, NS.ssn, NS.ssn1))

        fp_out = (NS.m1, OWL.sameAs, NS.m2)
        ifp_out = (NS.alice, OWL.sameAs, NS.bob)
        assert fp_out in graph
        assert ifp_out in graph
        _assert_derived(logger, rule_id="prp-fp", output=fp_out)
        _assert_derived(logger, rule_id="prp-ifp", output=ifp_out)

        # Reflexive filler pairs must not produce trivial sameAs noise.
        assert not any(
            record.rule_id.rule_id == "prp-fp"
            and any(
                conclusion.triple == (NS.m1, OWL.sameAs, NS.m1)
                for conclusion in record.conclusions
            )
            for record in logger.records
        )


def test_prp_symp_and_trp() -> None:
    """``prp-symp`` reverses assertions; ``prp-trp`` composes them."""

    logger, dataset = _dataset_for_rules(_prp_rules("prp-symp", "prp-trp"))
    with graph_under_test(dataset, graph_name="prp-symp-trp") as graph:
        graph.add((NS.knows, RDF.type, OWL.SymmetricProperty))
        graph.add((NS.alice, NS.knows, NS.bob))
        graph.add((NS.ancestor, RDF.type, OWL.TransitiveProperty))
        graph.add((NS.alice, NS.ancestor, NS.bob))
        graph.add((NS.bob, NS.ancestor, NS.carol))

        sym_out = (NS.bob, NS.knows, NS.alice)
        trp_out = (NS.alice, NS.ancestor, NS.carol)
        assert sym_out in graph
        assert trp_out in graph
        _assert_derived(logger, rule_id="prp-symp", output=sym_out)
        _assert_derived(logger, rule_id="prp-trp", output=trp_out)


def test_prp_spo1_eqp_and_inv() -> None:
    """``prp-spo1``, ``prp-eqp*``, and ``prp-inv*`` propagate property links."""

    logger, dataset = _dataset_for_rules(
        _prp_rules("prp-spo1", "prp-eqp1", "prp-eqp2", "prp-inv1", "prp-inv2")
    )
    with graph_under_test(dataset, graph_name="prp-spo-eqp-inv") as graph:
        graph.add((NS.hasMother, RDFS.subPropertyOf, NS.hasParent))
        graph.add((NS.alice, NS.hasMother, NS.mary))
        graph.add((NS.likes, OWL.equivalentProperty, NS.enjoys))
        graph.add((NS.alice, NS.likes, NS.coffee))
        graph.add((NS.bob, NS.enjoys, NS.tea))
        graph.add((NS.hasChild, OWL.inverseOf, NS.hasParentOf))
        graph.add((NS.mary, NS.hasChild, NS.alice))
        graph.add((NS.bob, NS.hasParentOf, NS.carol))

        spo_out = (NS.alice, NS.hasParent, NS.mary)
        eqp1_out = (NS.alice, NS.enjoys, NS.coffee)
        eqp2_out = (NS.bob, NS.likes, NS.tea)
        inv1_out = (NS.alice, NS.hasParentOf, NS.mary)
        inv2_out = (NS.carol, NS.hasChild, NS.bob)

        for rule_id, output in (
            ("prp-spo1", spo_out),
            ("prp-eqp1", eqp1_out),
            ("prp-eqp2", eqp2_out),
            ("prp-inv1", inv1_out),
            ("prp-inv2", inv2_out),
        ):
            assert output in graph
            _assert_derived(logger, rule_id=rule_id, output=output)


def test_prp_spo2_property_chain_length_2() -> None:
    """``prp-spo2`` fires for an RDF list property chain of length 2."""

    logger, dataset = _dataset_for_rules(_prp_rules("prp-spo2"))
    list_head = BNode("chain")
    list_tail = BNode("chainTail")
    with graph_under_test(dataset, graph_name="prp-spo2") as graph:
        graph.add((NS.uncle, OWL.propertyChainAxiom, list_head))
        graph.add((list_head, RDF.first, NS.hasParent))
        graph.add((list_head, RDF.rest, list_tail))
        graph.add((list_tail, RDF.first, NS.hasBrother))
        graph.add((list_tail, RDF.rest, RDF.nil))
        graph.add((NS.alice, NS.hasParent, NS.bob))
        graph.add((NS.bob, NS.hasBrother, NS.charlie))

        output = (NS.alice, NS.uncle, NS.charlie)
        assert output in graph
        _assert_derived(logger, rule_id="prp-spo2", output=output)


def test_prp_key_shared_key_values() -> None:
    """``prp-key`` equates distinct individuals that share key values."""

    logger, dataset = _dataset_for_rules(_prp_rules("prp-key"))
    key_list = BNode("key")
    with graph_under_test(dataset, graph_name="prp-key") as graph:
        graph.add((NS.Person, OWL.hasKey, key_list))
        graph.add((key_list, RDF.first, NS.ssn))
        graph.add((key_list, RDF.rest, RDF.nil))
        graph.add((NS.alice, RDF.type, NS.Person))
        graph.add((NS.bob, RDF.type, NS.Person))
        graph.add((NS.alice, NS.ssn, Literal("123", datatype=XSD.string)))
        graph.add((NS.bob, NS.ssn, Literal("123", datatype=XSD.string)))

        output = (NS.alice, OWL.sameAs, NS.bob)
        assert output in graph
        _assert_derived(logger, rule_id="prp-key", output=output)

        assert not any(
            record.rule_id.rule_id == "prp-key"
            and any(
                conclusion.triple == (NS.alice, OWL.sameAs, NS.alice)
                for conclusion in record.conclusions
            )
            for record in logger.records
        )
