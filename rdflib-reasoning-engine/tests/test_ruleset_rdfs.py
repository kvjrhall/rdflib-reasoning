import textwrap
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Final

import pytest
from rdflib import OWL, RDF, RDFS, Dataset, Graph, Namespace
from rdflib.graph import ModificationException
from rdflib.plugins.stores.memory import Memory
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.engine import (
    RDFS_RULES,
    DerivationLogger,
    DerivationRecord,
    RETEEngineFactory,
)
from rdflib_reasoning.engine.rete_store import RETEStore

from .conftest import RDFS_AXIOMS, TestData


@dataclass(frozen=True, slots=True, unsafe_hash=True)
class RdfsTestCase:
    """
    Test case for an RDFS rule.

    Args:
        rule_id: The ID of the rule to test.
        inputs: The input triples to the rule.
        outputs: The expected output triples from the rule.
        example_number: This is the example_number'th test case for rule_id.
    """

    rule_id: str
    inputs: set[Triple]
    outputs: set[Triple]
    example_number: int = 0


class RecordingLoggerSpy(DerivationLogger):
    def __init__(self) -> None:
        self.records: list[DerivationRecord] = []

    def record(self, record: DerivationRecord) -> None:
        self.records.append(record)


type LoggerAndDataset = tuple[RecordingLoggerSpy, Dataset]


@contextmanager
def graph_under_test(
    dataset: Dataset, graph_name: str | None = None
) -> Generator[Graph, None, None]:
    graph = dataset.default_graph
    try:
        yield graph
    except Exception as cause:
        error_message = textwrap.dedent("""
        Error while testing RDFS entailment for graph{graph_name}:
        {graph_string}
        """)

        graph_name = f": {graph_name}" if graph_name is not None else ""
        graph_string = graph.serialize(format="turtle")
        error_message = error_message.format(
            graph_name=graph_name, graph_string=graph_string
        )
        raise AssertionError(error_message) from cause


@pytest.fixture
def rdfs_dataset() -> TestData[LoggerAndDataset]:
    logger = RecordingLoggerSpy()
    factory = RETEEngineFactory(rules=RDFS_RULES, derivation_logger=logger)
    store = RETEStore(Memory(), factory)
    dataset = Dataset(store=store)
    yield logger, dataset


def test_conftest_immutable_rdfs_axioms(rdfs_axioms: Graph) -> None:
    """Sanity check that the RDFS axioms fixture is immutable.

    Does not actually test RDFS engine, just test infrastructure.
    """

    with pytest.raises(ModificationException):
        rdfs_axioms.add((OWL.Class, RDFS.subClassOf, RDFS.Class))


NS = Namespace("urn:test:")


_RDFS_RULE_SPECS: Final[dict[str, str]] = {
    # RDF 1.1 Semantics: Patterns of RDFS entailment (rdfs1–rdfs13)
    "rdfs1": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs1",
    "rdfs2": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs2",
    "rdfs3": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs3",
    "rdfs4a": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs4a",
    "rdfs4b": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs4b",
    "rdfs5": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs5",
    "rdfs6": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs6",
    "rdfs7": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs7",
    "rdfs8": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs8",
    "rdfs9": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs9",
    "rdfs10": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs10",
    "rdfs11": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs11",
    "rdfs12": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs12",
    "rdfs13": "https://www.w3.org/TR/rdf11-mt/#dfn-rdfs13",
}

_IMPLEMENTED_RDFS_RULE_IDS: Final[set[str]] = {rule.id.rule_id for rule in RDFS_RULES}


RDFS_TEST_CASES: Final[Sequence[RdfsTestCase]] = (
    # rdfs1 – property typing
    RdfsTestCase(
        rule_id="rdfs1",
        inputs={
            (NS.x, NS.p, NS.y),
        },
        outputs={
            (NS.p, RDF.type, RDF.Property),
        },
    ),
    # rdfs2 – domain entailment
    RdfsTestCase(
        rule_id="rdfs2",
        inputs={
            (NS.x, NS.p, NS.y),
            (NS.p, RDFS.domain, NS.c),
        },
        outputs={
            (NS.x, RDF.type, NS.c),
        },
    ),
    # rdfs3 – range entailment
    RdfsTestCase(
        rule_id="rdfs3",
        inputs={
            (NS.x, NS.p, NS.y),
            (NS.p, RDFS.range, NS.c),
        },
        outputs={
            (NS.y, RDF.type, NS.c),
        },
    ),
    # rdfs5 – subPropertyOf transitivity (spec rdfs5)
    RdfsTestCase(
        rule_id="rdfs5",
        inputs={
            (NS.a, RDFS.subPropertyOf, NS.b),
            (NS.b, RDFS.subPropertyOf, NS.c),
        },
        outputs={
            (NS.a, RDFS.subPropertyOf, NS.c),
        },
        example_number=0,
    ),
    # rdfs7 – subPropertyOf inheritance of property assertions
    RdfsTestCase(
        rule_id="rdfs7",
        inputs={
            (NS.x, NS.p, NS.y),
            (NS.p, RDFS.subPropertyOf, NS.q),
        },
        outputs={
            (NS.x, NS.q, NS.y),
        },
    ),
    # rdfs9 – subclass typing propagation
    RdfsTestCase(
        rule_id="rdfs9",
        inputs={
            (NS.a, RDFS.subClassOf, NS.b),
            (NS.x, RDF.type, NS.a),
        },
        outputs={
            (NS.x, RDF.type, NS.b),
        },
    ),
    # rdfs4a – subject resource typing
    RdfsTestCase(
        rule_id="rdfs4a",
        inputs={
            (NS.x, NS.p, NS.y),
        },
        outputs={
            (NS.x, RDF.type, RDFS.Resource),
        },
    ),
    # rdfs4b – object resource typing
    RdfsTestCase(
        rule_id="rdfs4b",
        inputs={
            (NS.x, NS.p, NS.y),
        },
        outputs={
            (NS.y, RDF.type, RDFS.Resource),
        },
    ),
    # rdfs6 – property reflexivity
    RdfsTestCase(
        rule_id="rdfs6",
        inputs={
            (NS.p, RDF.type, RDF.Property),
        },
        outputs={
            (NS.p, RDFS.subPropertyOf, NS.p),
        },
    ),
    # rdfs8 – class inclusion in resource
    RdfsTestCase(
        rule_id="rdfs8",
        inputs={
            (NS.c, RDF.type, RDFS.Class),
        },
        outputs={
            (NS.c, RDFS.subClassOf, RDFS.Resource),
        },
    ),
    # rdfs10 – class reflexivity
    RdfsTestCase(
        rule_id="rdfs10",
        inputs={
            (NS.c, RDF.type, RDFS.Class),
        },
        outputs={
            (NS.c, RDFS.subClassOf, NS.c),
        },
    ),
    # rdfs11 – subClassOf transitivity
    RdfsTestCase(
        rule_id="rdfs11",
        inputs={
            (NS.a, RDFS.subClassOf, NS.b),
            (NS.b, RDFS.subClassOf, NS.c),
        },
        outputs={
            (NS.a, RDFS.subClassOf, NS.c),
        },
    ),
    # rdfs12 – container membership inheritance
    RdfsTestCase(
        rule_id="rdfs12",
        inputs={
            (NS.p, RDF.type, RDFS.ContainerMembershipProperty),
        },
        outputs={
            (NS.p, RDFS.subPropertyOf, RDFS.member),
        },
    ),
    # rdfs13 – datatype literal inclusion
    RdfsTestCase(
        rule_id="rdfs13",
        inputs={
            (NS.d, RDF.type, RDFS.Datatype),
        },
        outputs={
            (NS.d, RDFS.subClassOf, RDFS.Literal),
        },
    ),
)


@pytest.fixture(
    params=RDFS_TEST_CASES,
    ids=lambda test_case: f"{test_case.rule_id}-{test_case.example_number}",
)
def test_case(request) -> TestData[RdfsTestCase]:
    test_case = request.param
    yield test_case


def test_rdfs_entailment_micro(
    rdfs_dataset: LoggerAndDataset,
    test_case: RdfsTestCase,
) -> None:
    if test_case.rule_id not in _IMPLEMENTED_RDFS_RULE_IDS:
        pytest.xfail(
            f"RDFS rule {test_case.rule_id} is not yet implemented in RDFS_RULES"
        )

    logger, dataset = rdfs_dataset
    with graph_under_test(dataset) as graph:
        for input in test_case.inputs:
            graph.add(input)
        for output in test_case.outputs:
            assert output in graph

        # There may be multiple derivations for the same entailed triple as the
        # ruleset evolves. Assert that at least one derivation record matches
        # the micro example for the intended rule.
        for output in test_case.outputs:
            matching_records = [
                record
                for record in logger.records
                if record.rule_id.rule_id == test_case.rule_id
                and any(
                    conclusion.triple == output for conclusion in record.conclusions
                )
            ]
            assert matching_records, (
                "Expected a derivation record for "
                f"{output!r} from rule {test_case.rule_id} "
                f"(example {test_case.example_number})"
            )


def test_rdfs_rule_ids_are_known_to_spec_index() -> None:
    """Ensure every RDFS rule id in the engine has a known RDFS Semantics anchor.

    This provides a spec-driven contract between the engine's RDFS_RULES and the
    RDF 1.1 Semantics RDFS entailment section. External reviewers without a
    local cache can follow the association using the public W3C URLs.
    """

    rule_ids = {rule.id.rule_id for rule in RDFS_RULES}

    # All implemented RDFS rule ids must be present in the spec mapping.
    assert rule_ids <= _RDFS_RULE_SPECS.keys()


def test_rdfs_transitive_subproperty_chain() -> None:
    """Integration: transitive closure for subPropertyOf chains of length > 2."""

    logger = RecordingLoggerSpy()
    factory = RETEEngineFactory(rules=RDFS_RULES, derivation_logger=logger)
    store = RETEStore(Memory(), factory)
    dataset = Dataset(store=store)

    with graph_under_test(dataset, graph_name="transitive-subproperty") as graph:
        graph.add((NS.a, RDFS.subPropertyOf, NS.b))
        graph.add((NS.b, RDFS.subPropertyOf, NS.c))
        graph.add((NS.c, RDFS.subPropertyOf, NS.d))

        assert (NS.a, RDFS.subPropertyOf, NS.d) in graph


def test_rdfs_transitive_subclass_chain() -> None:
    """Integration: transitive closure for subClassOf chains of length > 2."""

    logger = RecordingLoggerSpy()
    factory = RETEEngineFactory(rules=RDFS_RULES, derivation_logger=logger)
    store = RETEStore(Memory(), factory)
    dataset = Dataset(store=store)

    with graph_under_test(dataset, graph_name="transitive-subclass") as graph:
        graph.add((NS.A, RDFS.subClassOf, NS.B))
        graph.add((NS.B, RDFS.subClassOf, NS.C))
        graph.add((NS.C, RDFS.subClassOf, NS.D))
        graph.add((NS.x, RDF.type, NS.A))

        assert (NS.x, RDF.type, NS.D) in graph


def test_rdfs_subproperty_cycle_terminates() -> None:
    """Integration: subPropertyOf cycles do not cause non-terminating inference."""

    logger = RecordingLoggerSpy()
    factory = RETEEngineFactory(rules=RDFS_RULES, derivation_logger=logger)
    store = RETEStore(Memory(), factory)
    dataset = Dataset(store=store)

    with graph_under_test(dataset, graph_name="subproperty-cycle") as graph:
        graph.add((NS.p, RDFS.subPropertyOf, NS.q))
        graph.add((NS.q, RDFS.subPropertyOf, NS.p))
        graph.add((NS.x, NS.p, NS.y))

        # Closure should be finite but include the expected propagated assertion.
        assert (NS.x, NS.q, NS.y) in graph


def test_rdfs_multiple_domain_entailment() -> None:
    """Integration: multiple rdfs:domain declarations yield multiple type assertions."""

    logger = RecordingLoggerSpy()
    factory = RETEEngineFactory(rules=RDFS_RULES, derivation_logger=logger)
    store = RETEStore(Memory(), factory)
    dataset = Dataset(store=store)

    with graph_under_test(dataset, graph_name="multiple-domain") as graph:
        graph.add((NS.p, RDFS.domain, NS.C1))
        graph.add((NS.p, RDFS.domain, NS.C2))
        graph.add((NS.x, NS.p, NS.y))

        assert (NS.x, RDF.type, NS.C1) in graph
        assert (NS.x, RDF.type, NS.C2) in graph


def test_rdfs_multiple_range_entailment() -> None:
    """Integration: multiple rdfs:range declarations yield multiple type assertions."""

    logger = RecordingLoggerSpy()
    factory = RETEEngineFactory(rules=RDFS_RULES, derivation_logger=logger)
    store = RETEStore(Memory(), factory)
    dataset = Dataset(store=store)

    with graph_under_test(dataset, graph_name="multiple-range") as graph:
        graph.add((NS.p, RDFS.range, NS.C1))
        graph.add((NS.p, RDFS.range, NS.C2))
        graph.add((NS.x, NS.p, NS.y))

        assert (NS.y, RDF.type, NS.C1) in graph
        assert (NS.y, RDF.type, NS.C2) in graph


def test_rdfs_non_entailment_without_domain_or_range() -> None:
    """Negative test: no domain/range declarations means no type entailments."""

    logger = RecordingLoggerSpy()
    factory = RETEEngineFactory(rules=RDFS_RULES, derivation_logger=logger)
    store = RETEStore(Memory(), factory)
    dataset = Dataset(store=store)

    with graph_under_test(dataset, graph_name="no-domain-or-range") as graph:
        graph.add((NS.x, NS.p, NS.y))

        assert (NS.x, RDF.type, NS.C1) not in graph
        assert (NS.y, RDF.type, NS.C1) not in graph


def test_rdfs_axioms_inventory_is_subset_of_closure() -> None:
    """Treat the RDFS axioms fixture as an inventory of axioms on the empty graph."""

    logger = RecordingLoggerSpy()
    factory = RETEEngineFactory(rules=RDFS_RULES, derivation_logger=logger)
    store = RETEStore(Memory(), factory)
    dataset = Dataset(store=store)

    with graph_under_test(dataset, graph_name="axioms-inventory") as graph:
        for triple in RDFS_AXIOMS:
            graph.add(triple)

        for triple in RDFS_AXIOMS:
            assert triple in graph


def test_multiple_derivation_paths_are_recoverable() -> None:
    """Intended property: derivation logging should preserve multiple proof paths.

    This test documents the intent that, in future, the derivation logging and proof
    reconstruction machinery will be able to expose multiple distinct derivation
    paths for the same entailed triple without constraining the current mechanism.
    """

    pytest.xfail("Multiple-derivation tracking is not yet implemented.")
