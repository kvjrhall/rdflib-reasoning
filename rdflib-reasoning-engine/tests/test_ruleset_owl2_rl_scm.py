"""Schema-closure micro-tests for OWL 2 RL ``scm-*`` entailment rules."""

from __future__ import annotations

import textwrap
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Final

import pytest
from rdflib import OWL, RDF, RDFS, BNode, Dataset, Graph, Namespace
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.engine import (
    NO_RULES,
    Builtins,
    InMemoryDerivationLogger,
)
from rdflib_reasoning.engine.rules import Rule
from rdflib_reasoning.engine.rulesets.owl2_rl_scm import OWL2_RL_SCM_RULES

NS = Namespace("urn:test:")

type LoggerAndDataset = tuple[InMemoryDerivationLogger, Dataset]

_EXPECTED_SCM_RULE_IDS: Final[frozenset[str]] = frozenset(
    {
        "scm-cls",
        "scm-sco",
        "scm-eqc1",
        "scm-eqc2",
        "scm-op",
        "scm-dp",
        "scm-spo",
        "scm-eqp1",
        "scm-eqp2",
        "scm-dom1",
        "scm-dom2",
        "scm-rng1",
        "scm-rng2",
        "scm-hv",
        "scm-svf1",
        "scm-svf2",
        "scm-avf1",
        "scm-avf2",
        "scm-int",
        "scm-uni",
    }
)


@dataclass(frozen=True, slots=True, unsafe_hash=True)
class ScmTestCase:
    """Test case for an OWL 2 RL ``scm-*`` rule.

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


def _scm_rules(*rule_ids: str) -> tuple[Rule, ...]:
    wanted = set(rule_ids)
    return tuple(rule for rule in OWL2_RL_SCM_RULES if rule.id.rule_id in wanted)


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
            Error while testing OWL 2 RL scm entailment for graph{name}:
            {graph.serialize(format="turtle")}
            """
        )
        raise AssertionError(message) from cause


def _rdf_list(*members: object) -> tuple[object, set[Triple]]:
    """Build an RDF list head and the triples that encode it."""

    if not members:
        raise ValueError("RDF list requires at least one member")
    cells = [BNode() for _ in members]
    triples: set[Triple] = set()
    for index, member in enumerate(members):
        triples.add((cells[index], RDF.first, member))
        rest = RDF.nil if index == len(members) - 1 else cells[index + 1]
        triples.add((cells[index], RDF.rest, rest))
    return cells[0], triples


_LIST_C1_C2 = _rdf_list(NS.C1, NS.C2)
_LIST_HEAD_INT, _LIST_TRIPLES_INT = _LIST_C1_C2
_LIST_HEAD_UNI, _LIST_TRIPLES_UNI = _rdf_list(NS.A, NS.B)


SCM_TEST_CASES: Final[Sequence[ScmTestCase]] = (
    ScmTestCase(
        rule_id="scm-cls",
        inputs={(NS.Person, RDF.type, OWL.Class)},
        outputs={
            (NS.Person, RDFS.subClassOf, NS.Person),
            (NS.Person, OWL.equivalentClass, NS.Person),
            (NS.Person, RDFS.subClassOf, OWL.Thing),
            (OWL.Nothing, RDFS.subClassOf, NS.Person),
        },
    ),
    ScmTestCase(
        rule_id="scm-sco",
        inputs={
            (NS.Dog, RDFS.subClassOf, NS.Mammal),
            (NS.Mammal, RDFS.subClassOf, NS.Animal),
        },
        outputs={(NS.Dog, RDFS.subClassOf, NS.Animal)},
    ),
    ScmTestCase(
        rule_id="scm-eqc1",
        inputs={(NS.Human, OWL.equivalentClass, NS.Person)},
        outputs={
            (NS.Human, RDFS.subClassOf, NS.Person),
            (NS.Person, RDFS.subClassOf, NS.Human),
        },
    ),
    ScmTestCase(
        rule_id="scm-eqc2",
        inputs={
            (NS.Human, RDFS.subClassOf, NS.Person),
            (NS.Person, RDFS.subClassOf, NS.Human),
        },
        outputs={(NS.Human, OWL.equivalentClass, NS.Person)},
    ),
    ScmTestCase(
        rule_id="scm-op",
        inputs={(NS.hasParent, RDF.type, OWL.ObjectProperty)},
        outputs={
            (NS.hasParent, RDFS.subPropertyOf, NS.hasParent),
            (NS.hasParent, OWL.equivalentProperty, NS.hasParent),
        },
    ),
    ScmTestCase(
        rule_id="scm-dp",
        inputs={(NS.age, RDF.type, OWL.DatatypeProperty)},
        outputs={
            (NS.age, RDFS.subPropertyOf, NS.age),
            (NS.age, OWL.equivalentProperty, NS.age),
        },
    ),
    ScmTestCase(
        rule_id="scm-spo",
        inputs={
            (NS.hasMother, RDFS.subPropertyOf, NS.hasParent),
            (NS.hasParent, RDFS.subPropertyOf, NS.hasAncestor),
        },
        outputs={(NS.hasMother, RDFS.subPropertyOf, NS.hasAncestor)},
    ),
    ScmTestCase(
        rule_id="scm-eqp1",
        inputs={(NS.hasParent, OWL.equivalentProperty, NS.hasGuardian)},
        outputs={
            (NS.hasParent, RDFS.subPropertyOf, NS.hasGuardian),
            (NS.hasGuardian, RDFS.subPropertyOf, NS.hasParent),
        },
    ),
    ScmTestCase(
        rule_id="scm-eqp2",
        inputs={
            (NS.hasParent, RDFS.subPropertyOf, NS.hasGuardian),
            (NS.hasGuardian, RDFS.subPropertyOf, NS.hasParent),
        },
        outputs={(NS.hasParent, OWL.equivalentProperty, NS.hasGuardian)},
    ),
    ScmTestCase(
        rule_id="scm-dom1",
        inputs={
            (NS.hasParent, RDFS.domain, NS.Person),
            (NS.Person, RDFS.subClassOf, NS.Animal),
        },
        outputs={(NS.hasParent, RDFS.domain, NS.Animal)},
    ),
    ScmTestCase(
        rule_id="scm-dom2",
        inputs={
            (NS.hasParent, RDFS.domain, NS.Person),
            (NS.hasMother, RDFS.subPropertyOf, NS.hasParent),
        },
        outputs={(NS.hasMother, RDFS.domain, NS.Person)},
    ),
    ScmTestCase(
        rule_id="scm-rng1",
        inputs={
            (NS.hasParent, RDFS.range, NS.Person),
            (NS.Person, RDFS.subClassOf, NS.Animal),
        },
        outputs={(NS.hasParent, RDFS.range, NS.Animal)},
    ),
    ScmTestCase(
        rule_id="scm-rng2",
        inputs={
            (NS.hasParent, RDFS.range, NS.Person),
            (NS.hasMother, RDFS.subPropertyOf, NS.hasParent),
        },
        outputs={(NS.hasMother, RDFS.range, NS.Person)},
    ),
    ScmTestCase(
        rule_id="scm-hv",
        inputs={
            (NS.R1, OWL.hasValue, NS.v),
            (NS.R1, OWL.onProperty, NS.hasMother),
            (NS.R2, OWL.hasValue, NS.v),
            (NS.R2, OWL.onProperty, NS.hasParent),
            (NS.hasMother, RDFS.subPropertyOf, NS.hasParent),
        },
        outputs={(NS.R1, RDFS.subClassOf, NS.R2)},
    ),
    ScmTestCase(
        rule_id="scm-svf1",
        inputs={
            (NS.R1, OWL.someValuesFrom, NS.Dog),
            (NS.R1, OWL.onProperty, NS.hasPet),
            (NS.R2, OWL.someValuesFrom, NS.Animal),
            (NS.R2, OWL.onProperty, NS.hasPet),
            (NS.Dog, RDFS.subClassOf, NS.Animal),
        },
        outputs={(NS.R1, RDFS.subClassOf, NS.R2)},
    ),
    ScmTestCase(
        rule_id="scm-svf2",
        inputs={
            (NS.R1, OWL.someValuesFrom, NS.Animal),
            (NS.R1, OWL.onProperty, NS.hasMother),
            (NS.R2, OWL.someValuesFrom, NS.Animal),
            (NS.R2, OWL.onProperty, NS.hasParent),
            (NS.hasMother, RDFS.subPropertyOf, NS.hasParent),
        },
        outputs={(NS.R1, RDFS.subClassOf, NS.R2)},
    ),
    ScmTestCase(
        rule_id="scm-avf1",
        inputs={
            (NS.R1, OWL.allValuesFrom, NS.Dog),
            (NS.R1, OWL.onProperty, NS.hasPet),
            (NS.R2, OWL.allValuesFrom, NS.Animal),
            (NS.R2, OWL.onProperty, NS.hasPet),
            (NS.Dog, RDFS.subClassOf, NS.Animal),
        },
        outputs={(NS.R1, RDFS.subClassOf, NS.R2)},
    ),
    ScmTestCase(
        rule_id="scm-avf2",
        inputs={
            (NS.R1, OWL.allValuesFrom, NS.Animal),
            (NS.R1, OWL.onProperty, NS.hasMother),
            (NS.R2, OWL.allValuesFrom, NS.Animal),
            (NS.R2, OWL.onProperty, NS.hasParent),
            (NS.hasMother, RDFS.subPropertyOf, NS.hasParent),
        },
        # Contravariant: broader property yields a more restrictive allValuesFrom.
        outputs={(NS.R2, RDFS.subClassOf, NS.R1)},
    ),
    ScmTestCase(
        rule_id="scm-int",
        inputs={
            (NS.Intersection, OWL.intersectionOf, _LIST_HEAD_INT),
            *_LIST_TRIPLES_INT,
        },
        outputs={
            (NS.Intersection, RDFS.subClassOf, NS.C1),
            (NS.Intersection, RDFS.subClassOf, NS.C2),
        },
    ),
    ScmTestCase(
        rule_id="scm-uni",
        inputs={
            (NS.Union, OWL.unionOf, _LIST_HEAD_UNI),
            *_LIST_TRIPLES_UNI,
        },
        outputs={
            (NS.A, RDFS.subClassOf, NS.Union),
            (NS.B, RDFS.subClassOf, NS.Union),
        },
    ),
)


@pytest.fixture(
    params=SCM_TEST_CASES,
    ids=lambda case: f"{case.rule_id}-{case.example_number}",
)
def scm_test_case(request: pytest.FixtureRequest) -> ScmTestCase:
    return request.param


def test_owl2_rl_scm_rule_ids() -> None:
    """Export surface covers every Table 9 ``scm-*`` rule id."""

    assert {rule.id.ruleset for rule in OWL2_RL_SCM_RULES} == {"owl2-rl"}
    assert {rule.id.rule_id for rule in OWL2_RL_SCM_RULES} == _EXPECTED_SCM_RULE_IDS
    # Fixed-arity LIST expansions contribute multiple Rule objects per id.
    assert sum(1 for rule in OWL2_RL_SCM_RULES if rule.id.rule_id == "scm-int") == 3
    assert sum(1 for rule in OWL2_RL_SCM_RULES if rule.id.rule_id == "scm-uni") == 3


def test_scm_entailment_micro(scm_test_case: ScmTestCase) -> None:
    """Each ``scm-*`` micro-example materializes the expected schema closure."""

    logger, dataset = _dataset_for_rules(_scm_rules(scm_test_case.rule_id))
    with graph_under_test(dataset, graph_name=scm_test_case.rule_id) as graph:
        for triple in scm_test_case.inputs:
            graph.add(triple)
        for output in scm_test_case.outputs:
            assert output in graph
            matching = [
                record
                for record in logger.records
                if record.rule_id.rule_id == scm_test_case.rule_id
                and any(
                    conclusion.triple == output for conclusion in record.conclusions
                )
            ]
            assert matching, (
                "Expected a derivation record for "
                f"{output!r} from rule {scm_test_case.rule_id}"
            )


def test_scm_sco_transitive_chain() -> None:
    """``scm-sco`` closes subclass chains longer than two hops."""

    _, dataset = _dataset_for_rules(_scm_rules("scm-sco"))
    with graph_under_test(dataset, graph_name="scm-sco-chain") as graph:
        graph.add((NS.A, RDFS.subClassOf, NS.B))
        graph.add((NS.B, RDFS.subClassOf, NS.C))
        graph.add((NS.C, RDFS.subClassOf, NS.D))
        assert (NS.A, RDFS.subClassOf, NS.D) in graph


def test_scm_spo_transitive_chain() -> None:
    """``scm-spo`` closes subproperty chains longer than two hops."""

    _, dataset = _dataset_for_rules(_scm_rules("scm-spo"))
    with graph_under_test(dataset, graph_name="scm-spo-chain") as graph:
        graph.add((NS.p, RDFS.subPropertyOf, NS.q))
        graph.add((NS.q, RDFS.subPropertyOf, NS.r))
        graph.add((NS.r, RDFS.subPropertyOf, NS.s))
        assert (NS.p, RDFS.subPropertyOf, NS.s) in graph


def test_scm_eqc_bridge_round_trip() -> None:
    """``scm-eqc1`` then ``scm-eqc2`` recover equivalent-class from mutual sco."""

    _, dataset = _dataset_for_rules(_scm_rules("scm-eqc1", "scm-eqc2"))
    with graph_under_test(dataset, graph_name="scm-eqc-round-trip") as graph:
        graph.add((NS.Human, OWL.equivalentClass, NS.Person))
        assert (NS.Human, RDFS.subClassOf, NS.Person) in graph
        assert (NS.Person, RDFS.subClassOf, NS.Human) in graph
        assert (NS.Human, OWL.equivalentClass, NS.Person) in graph


def test_scm_domain_and_range_compose() -> None:
    """Domain/range subclass and subproperty rules compose under schema closure."""

    _, dataset = _dataset_for_rules(
        _scm_rules("scm-dom1", "scm-dom2", "scm-rng1", "scm-rng2")
    )
    with graph_under_test(dataset, graph_name="scm-dom-rng-compose") as graph:
        graph.add((NS.hasParent, RDFS.domain, NS.Person))
        graph.add((NS.hasParent, RDFS.range, NS.Person))
        graph.add((NS.Person, RDFS.subClassOf, NS.Animal))
        graph.add((NS.hasMother, RDFS.subPropertyOf, NS.hasParent))

        assert (NS.hasParent, RDFS.domain, NS.Animal) in graph
        assert (NS.hasParent, RDFS.range, NS.Animal) in graph
        assert (NS.hasMother, RDFS.domain, NS.Person) in graph
        assert (NS.hasMother, RDFS.range, NS.Person) in graph
        assert (NS.hasMother, RDFS.domain, NS.Animal) in graph
        assert (NS.hasMother, RDFS.range, NS.Animal) in graph


def test_scm_sco_skips_identical_endpoints() -> None:
    """``different_terms`` prevents a no-op self-subclass conclusion for ``scm-sco``."""

    logger, dataset = _dataset_for_rules(_scm_rules("scm-sco"))
    with graph_under_test(dataset, graph_name="scm-sco-reflexive") as graph:
        graph.add((NS.Person, RDFS.subClassOf, NS.Person))
        assert not any(record.rule_id.rule_id == "scm-sco" for record in logger.records)
