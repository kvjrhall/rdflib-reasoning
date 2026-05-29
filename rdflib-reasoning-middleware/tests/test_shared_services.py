import pytest
from rdflib import RDF, RDFS, Graph, Namespace
from rdflib_reasoning.engine.api import NO_RULES, RDFS_RETE_MATERIALIZED
from rdflib_reasoning.middleware import DatasetRuntime

EX = "urn:test:"
EX_NS = Namespace(EX)

entity = EX_NS.entity
class_a = EX_NS.classA
class_b = EX_NS.classB
named_graph = EX_NS.namedGraph


def test_dataset_runtime_default_graph() -> None:
    runtime = DatasetRuntime(specification=NO_RULES)
    assert runtime.dataset_size() == 0

    with runtime.dataset_write() as dataset:
        dataset.add((entity, RDF.type, class_a))
        dataset.add((class_a, RDFS.subClassOf, class_b))

    assert runtime.dataset_size() == 2
    assert runtime.graph_size(context=None) == 2

    assert len(runtime.snapshot_dataset()) == 2
    assert len(runtime.snapshot_graph(context=None)) == 2


def test_dataset_runtime_default_graph_inf() -> None:
    runtime = DatasetRuntime(specification=RDFS_RETE_MATERIALIZED)
    assert runtime.dataset_size() == 0

    with runtime.dataset_write() as dataset:
        dataset.add((entity, RDF.type, class_a))
        dataset.add((class_a, RDFS.subClassOf, class_b))

    dataset = runtime.snapshot_dataset()
    content = dataset.serialize(format="trig")

    try:
        graph = runtime.snapshot_graph(context=None)
        assert (entity, RDF.type, class_a) in graph
        assert (entity, RDF.type, class_b) in graph
        assert (class_a, RDFS.subClassOf, class_b) in graph
        assert (class_a, RDF.type, RDFS.Class) in graph
        assert (class_b, RDF.type, RDFS.Class) in graph
        assert runtime.graph_size(context=None) == 5
    except AssertionError as e:
        e.add_note(f"Dataset content: {content}")
        raise


def test_dataset_runtime_missing_graph() -> None:
    runtime = DatasetRuntime(specification=NO_RULES)

    with pytest.raises(ValueError) as e:
        runtime.graph_size(context=named_graph)
    assert str(e.value) == f"Graph {named_graph} not found"


def test_dataset_runtime_named_graph() -> None:
    runtime = DatasetRuntime(specification=NO_RULES)
    assert runtime.dataset_size() == 0

    context = Graph(identifier=named_graph)
    with runtime.dataset_write() as dataset:
        dataset.add((entity, RDF.type, class_a, context))
        dataset.add((class_a, RDFS.subClassOf, class_b, context))

    assert len(runtime.snapshot_dataset()) == 2
    assert runtime.graph_size(context=named_graph) == 2
    assert len(runtime.snapshot_graph(context=named_graph)) == 2


def test_dataset_runtime_named_graph_inf() -> None:
    runtime = DatasetRuntime(specification=RDFS_RETE_MATERIALIZED)
    assert runtime.dataset_size() == 0

    context = Graph(identifier=named_graph)
    with runtime.dataset_write() as dataset:
        dataset.add((entity, RDF.type, class_a, context))
        dataset.add((class_a, RDFS.subClassOf, class_b, context))

    dataset = runtime.snapshot_dataset()
    content = dataset.serialize(format="trig")
    try:
        graph = runtime.snapshot_graph(context=named_graph)
        assert (entity, RDF.type, class_a) in graph
        assert (entity, RDF.type, class_b) in graph
        assert (class_a, RDFS.subClassOf, class_b) in graph
        assert (class_a, RDF.type, RDFS.Class) in graph
        assert (class_b, RDF.type, RDFS.Class) in graph
        assert runtime.graph_size(context=named_graph) == 5

    except AssertionError as e:
        e.add_note(f"Dataset content: {content}")
        raise


def test_dataset_runtime_replace_dataset() -> None:
    runtime = DatasetRuntime(specification=NO_RULES)
    assert runtime.dataset_size() == 0

    with runtime.dataset_write() as dataset:
        dataset.add((entity, RDF.type, class_a))
        dataset.add((class_a, RDFS.subClassOf, class_b))

    assert runtime.dataset_size() == 2
    runtime.replace_dataset()
    assert runtime.dataset_size() == 0


def test_dataset_runtime_replace_dataset_inf() -> None:
    runtime = DatasetRuntime(specification=RDFS_RETE_MATERIALIZED)
    assert runtime.dataset_size() == 0

    with runtime.dataset_write() as dataset:
        dataset.add((entity, RDF.type, class_a))
        dataset.add((class_a, RDFS.subClassOf, class_b))

    assert runtime.dataset_size() == 5
    runtime.replace_dataset()
    assert runtime.dataset_size() == 0
