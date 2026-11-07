"""Micro-tests for OWL 2 RL ``cax-*`` entailment rules."""

from __future__ import annotations

import textwrap
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Final

from rdflib import OWL, RDF, RDFS, Dataset, Graph, Namespace
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.engine import (
    NO_RULES,
    Builtins,
    InMemoryDerivationLogger,
)
from rdflib_reasoning.engine.rules import Rule
from rdflib_reasoning.engine.rulesets.owl2_rl_cax import OWL2_RL_CAX_RULES

NS = Namespace("urn:test:")

type LoggerAndDataset = tuple[InMemoryDerivationLogger, Dataset]


@dataclass(frozen=True, slots=True, unsafe_hash=True)
class CaxTestCase:
    """Test case for an OWL 2 RL ``cax-*`` rule.

    Args:
        rule_id: Canonical OWL 2 RL rule identifier under test.
        inputs: Asserted input triples.
        outputs: Expected entailed triples.
        example_number: Distinguishes multiple examples for the same rule.
    """

    rule_id: str
    inputs: set[Triple]
    outputs: set[Triple]
    example_number: int = 0


_CAX_RULES_BY_ID: Final[dict[str, Rule]] = {
    rule.id.rule_id: rule for rule in OWL2_RL_CAX_RULES
}


def _cax_rules(*rule_ids: str) -> tuple[Rule, ...]:
    return tuple(_CAX_RULES_BY_ID[rule_id] for rule_id in rule_ids)


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
            Error while testing OWL 2 RL cax entailment for graph{name}:
            {graph.serialize(format="turtle")}
            """
        )
        raise AssertionError(message) from cause


CAX_TEST_CASES: Final[Sequence[CaxTestCase]] = (
    CaxTestCase(
        rule_id="cax-sco",
        inputs={
            (NS.Person, RDFS.subClassOf, NS.Animal),
            (NS.alice, RDF.type, NS.Person),
        },
        outputs={
            (NS.alice, RDF.type, NS.Animal),
        },
    ),
    CaxTestCase(
        rule_id="cax-eqc1",
        inputs={
            (NS.Human, OWL.equivalentClass, NS.Person),
            (NS.alice, RDF.type, NS.Human),
        },
        outputs={
            (NS.alice, RDF.type, NS.Person),
        },
    ),
    CaxTestCase(
        rule_id="cax-eqc2",
        inputs={
            (NS.Human, OWL.equivalentClass, NS.Person),
            (NS.bob, RDF.type, NS.Person),
        },
        outputs={
            (NS.bob, RDF.type, NS.Human),
        },
    ),
)


def test_owl2_rl_cax_rule_ids() -> None:
    """Export surface covers the three triple-producing ``cax-*`` rules."""

    assert {rule.id.ruleset for rule in OWL2_RL_CAX_RULES} == {"owl2-rl"}
    assert set(_CAX_RULES_BY_ID) == {"cax-sco", "cax-eqc1", "cax-eqc2"}


def test_cax_sco_entailment() -> None:
    """``cax-sco`` propagates typing across ``rdfs:subClassOf``."""

    case = CAX_TEST_CASES[0]
    logger, dataset = _dataset_for_rules(_cax_rules(case.rule_id))
    with graph_under_test(dataset, graph_name=case.rule_id) as graph:
        for triple in case.inputs:
            graph.add(triple)
        for output in case.outputs:
            assert output in graph
            matching = [
                record
                for record in logger.records
                if record.rule_id.rule_id == case.rule_id
                and any(
                    conclusion.triple == output for conclusion in record.conclusions
                )
            ]
            assert matching, f"Expected derivation for {output!r} via {case.rule_id}"


def test_cax_eqc1_entailment() -> None:
    """``cax-eqc1`` propagates typing left-to-right across ``owl:equivalentClass``."""

    case = CAX_TEST_CASES[1]
    logger, dataset = _dataset_for_rules(_cax_rules(case.rule_id))
    with graph_under_test(dataset, graph_name=case.rule_id) as graph:
        for triple in case.inputs:
            graph.add(triple)
        for output in case.outputs:
            assert output in graph
            matching = [
                record
                for record in logger.records
                if record.rule_id.rule_id == case.rule_id
                and any(
                    conclusion.triple == output for conclusion in record.conclusions
                )
            ]
            assert matching, f"Expected derivation for {output!r} via {case.rule_id}"


def test_cax_eqc2_entailment() -> None:
    """``cax-eqc2`` propagates typing right-to-left across ``owl:equivalentClass``."""

    case = CAX_TEST_CASES[2]
    logger, dataset = _dataset_for_rules(_cax_rules(case.rule_id))
    with graph_under_test(dataset, graph_name=case.rule_id) as graph:
        for triple in case.inputs:
            graph.add(triple)
        for output in case.outputs:
            assert output in graph
            matching = [
                record
                for record in logger.records
                if record.rule_id.rule_id == case.rule_id
                and any(
                    conclusion.triple == output for conclusion in record.conclusions
                )
            ]
            assert matching, f"Expected derivation for {output!r} via {case.rule_id}"


def test_cax_sco_skips_reflexive_subclass() -> None:
    """``different_terms`` prevents a no-op self-typing conclusion for ``cax-sco``."""

    logger, dataset = _dataset_for_rules(_cax_rules("cax-sco"))
    with graph_under_test(dataset, graph_name="cax-sco-reflexive") as graph:
        graph.add((NS.Person, RDFS.subClassOf, NS.Person))
        graph.add((NS.alice, RDF.type, NS.Person))
        assert not any(record.rule_id.rule_id == "cax-sco" for record in logger.records)


def test_cax_equivalent_class_both_directions() -> None:
    """Together, ``cax-eqc1`` and ``cax-eqc2`` close membership both ways."""

    _, dataset = _dataset_for_rules(_cax_rules("cax-eqc1", "cax-eqc2"))
    with graph_under_test(dataset, graph_name="eqc-both-ways") as graph:
        graph.add((NS.Human, OWL.equivalentClass, NS.Person))
        graph.add((NS.alice, RDF.type, NS.Human))
        graph.add((NS.bob, RDF.type, NS.Person))

        assert (NS.alice, RDF.type, NS.Person) in graph
        assert (NS.bob, RDF.type, NS.Human) in graph
