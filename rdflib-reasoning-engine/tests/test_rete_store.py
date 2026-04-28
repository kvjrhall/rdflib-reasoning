import warnings
from collections.abc import Iterable
from typing import Any

import pytest
from rdflib import Dataset, Graph, Namespace
from rdflib.namespace import RDF, RDFS
from rdflib.plugins.stores.memory import Memory
from rdflib.store import VALID_STORE, Store
from rdflib.term import BNode, URIRef, Variable
from rdflib_reasoning.engine.api import RETEEngine, RETEEngineFactory
from rdflib_reasoning.engine.batch_dispatcher import TripleAddedBatchEvent
from rdflib_reasoning.engine.proof import RuleId
from rdflib_reasoning.engine.rete_store import (
    RETEStore,
    RetractionRematerializeWarning,
)
from rdflib_reasoning.engine.rules import (
    Rule,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)

_NS = Namespace("https://example.org/")
_X = Variable("x")


class DummyRule(Rule):
    id: RuleId = RuleId(ruleset="test", rule_id="dummy-rule")
    body: tuple[TripleCondition, ...] = (
        TripleCondition(
            pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_X)
        ),
    )
    head: tuple[TripleConsequent, ...] = (
        TripleConsequent(
            pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_X)
        ),
    )


class DummyEngine(RETEEngine):
    def __init__(self) -> None:
        super().__init__(context_data={}, rules=[])
        self.warmup_calls: list[list[tuple[int, int, int]]] = []
        self.add_triples_calls: list[list[tuple[int, int, int]]] = []
        self.add_triples_result: set[tuple[int, int, int]] = set()

    def add_triples(
        self, triples: Iterable[tuple[int, int, int]]
    ) -> set[tuple[int, int, int]]:  # type: ignore[override]
        materialized = list(triples)
        self.add_triples_calls.append(materialized)
        return self.add_triples_result

    def warmup(
        self, existing_triples: Iterable[tuple[int, int, int]]
    ) -> set[tuple[int, int, int]]:  # type: ignore[override]
        materialized = list(existing_triples)
        self.warmup_calls.append(materialized)
        return set(materialized)


class DummyFactory(RETEEngineFactory):
    def __init__(self) -> None:
        super().__init__()
        self.engines: dict[Any, DummyEngine] = {}

    def new_engine(self, context: Any) -> DummyEngine:  # type: ignore[override]
        engine = DummyEngine()
        self.engines[context] = engine
        return engine


class ScriptedEngine(RETEEngine):
    def __init__(
        self,
        *,
        scripted_results: dict[
            frozenset[tuple[Any, Any, Any]], set[tuple[Any, Any, Any]]
        ],
    ) -> None:
        super().__init__(context_data={}, rules=[])
        self.scripted_results = scripted_results
        self.add_triples_calls: list[set[tuple[Any, Any, Any]]] = []

    def add_triples(
        self, triples: Iterable[tuple[Any, Any, Any]]
    ) -> set[tuple[Any, Any, Any]]:  # type: ignore[override]
        materialized = set(triples)
        self.add_triples_calls.append(materialized)
        return self.scripted_results.get(frozenset(materialized), set())


class ScriptedFactory(RETEEngineFactory):
    def __init__(
        self,
        *,
        scripted_results: dict[
            frozenset[tuple[Any, Any, Any]], set[tuple[Any, Any, Any]]
        ],
    ) -> None:
        super().__init__()
        self.scripted_results = scripted_results
        self.engines: dict[Any, ScriptedEngine] = {}

    def new_engine(self, context: Any) -> ScriptedEngine:  # type: ignore[override]
        engine = ScriptedEngine(scripted_results=self.scripted_results)
        self.engines[context] = engine
        return engine


def test_rete_store_requires_context_aware_store() -> None:
    class NonContextAwareStore(Store):
        context_aware = False
        graph_aware = False

    with pytest.raises(ValueError, match="Backing store must be context-aware"):
        RETEStore(NonContextAwareStore(), DummyFactory())


def test_rete_store_initialization_and_open_warmup() -> None:
    backing = Memory()
    ds = Dataset(store=backing)
    # Ensure there is at least one context in the backing store.
    ds.default_graph.add((_NS.s, _NS.p, _NS.o))

    factory = DummyFactory()
    store = RETEStore(backing, factory)

    assert store.context_aware is True
    assert store.graph_aware == backing.graph_aware

    # Backing store.open returns a status; RETEStore.open must delegate without error.
    status = store.open(("id", "configuration"), create=True)
    assert status in (VALID_STORE, None)


def test_rete_store_on_triples_added_materializes_inferred_triples() -> None:
    backing = Memory()
    factory = DummyFactory()
    store = RETEStore(backing, factory)

    context_id = BNode()
    engine, engine_graph = store._ensure_engine(context_id)
    assert isinstance(engine, DummyEngine)

    # Configure the engine to infer a new triple.
    inferred = {(_NS.a, _NS.b, _NS.c)}
    engine.add_triples_result = inferred  # type: ignore[assignment]

    batch = TripleAddedBatchEvent(events=inferred, context_id=context_id)
    store._on_triples_added(batch)

    # The inferred triples must be materialized into the engine's context graph.
    assert all(triple in engine_graph for triple in inferred)


def test_rete_store_add_and_triples_delegate_to_backing_store() -> None:
    backing = Memory()
    factory = DummyFactory()
    store = RETEStore(backing, factory)
    ds = Dataset(store=store)

    s, p, o = _NS.s, _NS.p, _NS.o
    ds.add((s, p, o))

    triples = list(store.triples((s, p, o)))
    assert len(triples) == 1


def test_rete_store_add_graph_ensures_engine_and_delegates() -> None:
    backing = Memory()
    factory = DummyFactory()
    store = RETEStore(backing, factory)

    g = Graph(identifier=_NS.g, store=store)
    g.add((_NS.s, _NS.p, _NS.o))

    store.add_graph(g)

    # Engine must be created for the graph identifier.
    assert _NS.g in factory.engines


def test_rete_store_dataset_add_drives_batch_dispatch_and_materialization() -> None:
    backing = Memory()
    seed = (_NS.s, _NS.p, _NS.o)
    first_inference = (_NS.a, _NS.b, _NS.c)
    second_inference = (_NS.x, _NS.y, _NS.z)
    factory = ScriptedFactory(
        scripted_results={
            frozenset({seed}): {first_inference},
            frozenset({first_inference}): {second_inference},
            frozenset({second_inference}): set(),
        }
    )
    store = RETEStore(backing, factory)
    dataset = Dataset(store=store)

    dataset.default_graph.add(seed)

    engine = factory.engines[dataset.default_graph.identifier]
    assert engine.add_triples_calls == [
        set(),
        {seed},
        {first_inference},
        {second_inference},
    ]
    assert seed in dataset.default_graph
    assert first_inference in dataset.default_graph
    assert second_inference in dataset.default_graph


def test_rete_store_does_not_rematerialize_existing_inferred_triple() -> None:
    backing = Memory()
    seed = (_NS.s, _NS.p, _NS.o)
    inferred = (_NS.a, _NS.b, _NS.c)
    factory = ScriptedFactory(
        scripted_results={
            frozenset({seed}): {inferred},
            frozenset({inferred}): {inferred},
        }
    )
    store = RETEStore(backing, factory)
    dataset = Dataset(store=store)

    dataset.default_graph.add(seed)

    engine = factory.engines[dataset.default_graph.identifier]
    assert engine.add_triples_calls == [set(), {seed}, {inferred}]
    assert list(dataset.default_graph.triples(inferred)) == [inferred]


def test_rete_store_uses_real_factory_engine_to_materialize_inference() -> None:
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    rule = Rule(
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
    )
    store = RETEStore(Memory(), RETEEngineFactory(rules=[rule]))
    dataset = Dataset(store=store)
    alice = URIRef("urn:test:alice")
    human = URIRef("urn:test:Human")
    mammal = URIRef("urn:test:Mammal")

    dataset.default_graph.add((alice, RDF.type, human))
    dataset.default_graph.add((human, RDFS.subClassOf, mammal))

    assert (alice, RDF.type, mammal) in dataset.default_graph


def test_rete_store_warmup_does_not_materialize_non_silent_bootstrap_rule() -> None:
    bootstrap = (URIRef("urn:test:bootstrap"), RDF.type, RDFS.Resource)
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="bootstrap"),
        description=None,
        body=(),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=bootstrap[0],
                    predicate=bootstrap[1],
                    object=bootstrap[2],
                )
            ),
        ),
    )
    store = RETEStore(Memory(), RETEEngineFactory(rules=[rule]))
    dataset = Dataset(store=store)

    # Trigger engine creation for the default context through a store event.
    dataset.default_graph.add((_NS.seed, _NS.p, _NS.o))

    assert bootstrap not in dataset.default_graph


def test_rete_store_warmup_does_not_materialize_bootstrap_only_nonsilent_closure() -> (
    None
):
    bootstrap = (URIRef("urn:test:bootstrap"), RDFS.domain, RDFS.Class)
    closure = (RDF.List, RDF.type, RDFS.Resource)
    bootstrap_rule = Rule(
        id=RuleId(ruleset="test", rule_id="bootstrap"),
        description=None,
        body=(),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=bootstrap[0],
                    predicate=bootstrap[1],
                    object=bootstrap[2],
                )
            ),
        ),
        silent=True,
    )
    stimulated_rule = Rule(
        id=RuleId(ruleset="test", rule_id="stimulated"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=bootstrap[0],
                    predicate=bootstrap[1],
                    object=bootstrap[2],
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=closure[0],
                    predicate=closure[1],
                    object=closure[2],
                )
            ),
        ),
    )
    store = RETEStore(
        Memory(), RETEEngineFactory(rules=[bootstrap_rule, stimulated_rule])
    )
    dataset = Dataset(store=store)

    dataset.default_graph.add((_NS.seed_bootstrap, _NS.p, _NS.o))

    assert closure not in dataset.default_graph


def _subclass_chain_rule() -> Rule:
    """RDFS-style ``rdfs9`` subclass chain rule used by the removal tests."""
    x = Variable("x")
    y = Variable("y")
    z = Variable("z")
    return Rule(
        id=RuleId(ruleset="test", rule_id="subclass-chain"),
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
    )


def test_dataset_remove_drives_engine_retraction_and_cascade_in_backing_graph() -> None:
    rule = _subclass_chain_rule()
    store = RETEStore(Memory(), RETEEngineFactory(rules=[rule]))
    dataset = Dataset(store=store)
    alice = URIRef("urn:test:alice")
    a_cls = URIRef("urn:test:A")
    b_cls = URIRef("urn:test:B")
    c_cls = URIRef("urn:test:C")
    seed = (alice, RDF.type, a_cls)
    schema_ab = (a_cls, RDFS.subClassOf, b_cls)
    schema_bc = (b_cls, RDFS.subClassOf, c_cls)
    derived_b = (alice, RDF.type, b_cls)
    derived_c = (alice, RDF.type, c_cls)

    dataset.default_graph.add(seed)
    dataset.default_graph.add(schema_ab)
    dataset.default_graph.add(schema_bc)
    assert derived_b in dataset.default_graph
    assert derived_c in dataset.default_graph

    dataset.default_graph.remove(seed)

    assert seed not in dataset.default_graph
    assert derived_b not in dataset.default_graph
    assert derived_c not in dataset.default_graph
    assert schema_ab in dataset.default_graph
    assert schema_bc in dataset.default_graph


def test_dataset_remove_is_idempotent_for_already_absent_triple() -> None:
    rule = _subclass_chain_rule()
    store = RETEStore(Memory(), RETEEngineFactory(rules=[rule]))
    dataset = Dataset(store=store)
    seed = (URIRef("urn:test:alice"), RDF.type, URIRef("urn:test:A"))
    dataset.default_graph.add(seed)

    dataset.default_graph.remove(seed)
    assert seed not in dataset.default_graph

    dataset.default_graph.remove(seed)
    assert seed not in dataset.default_graph


def test_dataset_remove_rematerializes_stated_and_derived_triple_with_warning() -> None:
    rule = _subclass_chain_rule()
    store = RETEStore(Memory(), RETEEngineFactory(rules=[rule]))
    dataset = Dataset(store=store)
    alice = URIRef("urn:test:alice")
    a_cls = URIRef("urn:test:A")
    b_cls = URIRef("urn:test:B")
    schema = (a_cls, RDFS.subClassOf, b_cls)
    seed = (alice, RDF.type, a_cls)
    derived = (alice, RDF.type, b_cls)

    dataset.default_graph.add(seed)
    dataset.default_graph.add(schema)
    assert derived in dataset.default_graph
    dataset.default_graph.add(derived)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RetractionRematerializeWarning)
        dataset.default_graph.remove(derived)

    rematerialize_warnings = [
        w for w in caught if issubclass(w.category, RetractionRematerializeWarning)
    ]
    assert len(rematerialize_warnings) == 1
    assert derived in dataset.default_graph


def test_dataset_remove_pattern_drives_per_triple_engine_retraction() -> None:
    rule = _subclass_chain_rule()
    store = RETEStore(Memory(), RETEEngineFactory(rules=[rule]))
    dataset = Dataset(store=store)
    alice = URIRef("urn:test:alice")
    bob = URIRef("urn:test:bob")
    a_cls = URIRef("urn:test:A")
    b_cls = URIRef("urn:test:B")
    schema = (a_cls, RDFS.subClassOf, b_cls)
    alice_seed = (alice, RDF.type, a_cls)
    bob_seed = (bob, RDF.type, a_cls)

    dataset.default_graph.add(alice_seed)
    dataset.default_graph.add(bob_seed)
    dataset.default_graph.add(schema)
    assert (alice, RDF.type, b_cls) in dataset.default_graph
    assert (bob, RDF.type, b_cls) in dataset.default_graph

    dataset.default_graph.remove((None, RDF.type, a_cls))

    assert alice_seed not in dataset.default_graph
    assert bob_seed not in dataset.default_graph
    assert (alice, RDF.type, b_cls) not in dataset.default_graph
    assert (bob, RDF.type, b_cls) not in dataset.default_graph
    assert schema in dataset.default_graph


def test_dataset_re_add_after_remove_re_derives_inference() -> None:
    """Stale partial-match safety: after retract + re-add, no spurious old derivations."""
    rule = _subclass_chain_rule()
    store = RETEStore(Memory(), RETEEngineFactory(rules=[rule]))
    dataset = Dataset(store=store)
    alice = URIRef("urn:test:alice")
    bob = URIRef("urn:test:bob")
    a_cls = URIRef("urn:test:A")
    b_cls = URIRef("urn:test:B")
    schema = (a_cls, RDFS.subClassOf, b_cls)
    alice_seed = (alice, RDF.type, a_cls)
    bob_seed = (bob, RDF.type, a_cls)

    dataset.default_graph.add(alice_seed)
    dataset.default_graph.add(schema)
    assert (alice, RDF.type, b_cls) in dataset.default_graph

    dataset.default_graph.remove(alice_seed)
    assert (alice, RDF.type, b_cls) not in dataset.default_graph

    dataset.default_graph.add(bob_seed)
    assert (bob, RDF.type, b_cls) in dataset.default_graph
    assert (alice, RDF.type, b_cls) not in dataset.default_graph


def test_dataset_remove_with_scripted_engine_calls_retract_triples_once_per_batch() -> (
    None
):
    """Validate that ``RETEStore`` invokes ``engine.retract_triples`` exactly once
    per dispatched batch (analogous to the add path's ``add_triples`` call)."""

    class RemoveScriptedEngine(RETEEngine):
        def __init__(self) -> None:
            super().__init__(context_data={}, rules=[])
            self.add_triples_calls: list[set[Any]] = []
            self.retract_triples_calls: list[set[Any]] = []

        def add_triples(self, triples):  # type: ignore[override]
            collected = set(triples)
            self.add_triples_calls.append(collected)
            return set()

        def retract_triples(self, triples):  # type: ignore[override]
            collected = set(triples)
            self.retract_triples_calls.append(collected)
            return set()

        def warmup(self, existing_triples):  # type: ignore[override]
            return set(existing_triples)

    class RemoveScriptedFactory(RETEEngineFactory):
        def __init__(self) -> None:
            super().__init__()
            self.engines: dict[Any, RemoveScriptedEngine] = {}

        def new_engine(self, context: Any) -> RemoveScriptedEngine:  # type: ignore[override]
            engine = RemoveScriptedEngine()
            self.engines[context] = engine
            return engine

    factory = RemoveScriptedFactory()
    store = RETEStore(Memory(), factory)
    dataset = Dataset(store=store)
    seed = (_NS.s, _NS.p, _NS.o)
    dataset.default_graph.add(seed)
    engine = factory.engines[dataset.default_graph.identifier]

    engine.retract_triples_calls.clear()
    dataset.default_graph.remove(seed)

    assert engine.retract_triples_calls == [{seed}]


def test_rete_store_warmup_does_not_materialize_silent_bootstrap_rule() -> None:
    silent_bootstrap = (URIRef("urn:test:silent-bootstrap"), RDF.type, RDFS.Resource)
    rule = Rule(
        id=RuleId(ruleset="test", rule_id="silent-bootstrap"),
        description=None,
        body=(),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=silent_bootstrap[0],
                    predicate=silent_bootstrap[1],
                    object=silent_bootstrap[2],
                )
            ),
        ),
        silent=True,
    )
    store = RETEStore(Memory(), RETEEngineFactory(rules=[rule]))
    dataset = Dataset(store=store)

    dataset.default_graph.add((_NS.seed2, _NS.p, _NS.o))

    assert silent_bootstrap not in dataset.default_graph
