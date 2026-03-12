from collections.abc import Generator, Iterable, Iterator, Mapping
from typing import Any

from rdflib import Graph
from rdflib.graph import (
    _ContextType,
    _QuadType,
    _TripleChoiceType,
    _TriplePatternType,
    _TripleType,
)
from rdflib.plugins.sparql.sparql import Query
from rdflib.plugins.sparql.update import Update
from rdflib.query import Result
from rdflib.store import Store, StoreCreatedEvent
from rdflib.term import Identifier, URIRef
from rdflibr.axiom.common import ContextIdentifier
from rdflibr.engine.api import RETEEngine, RETEEngineFactory
from rdflibr.engine.batch_dispatcher import BatchDispatcher, TripleAddedBatchEvent


class StoreWrapper(Store):
    """A proxy adapter for arbitrary rdflib.store.Store instances"""

    store: Store
    factory: RETEEngineFactory
    dispatcher: BatchDispatcher
    engines: dict[ContextIdentifier, RETEEngine]

    engine_contexts: dict[ContextIdentifier, Graph] | None

    def __init__(self, store: Store, factory: RETEEngineFactory):
        # NOTE: We're currently missing RETE Engine initialization & ruleset management.
        #       I *think* that we want to externalize the rete engine configuration.
        super().__init__()
        self.store = store
        self.factory = factory
        self.engines = dict()
        self.engine_contexts = dict()

        # The batch dispatcher listens to low-level store events and emits
        # per-context batch events that can drive the RETE engine.
        self.dispatcher = BatchDispatcher(store)
        store.dispatcher.subscribe(StoreCreatedEvent, self.dispatcher.dispatch)
        self.dispatcher.subscribe(TripleAddedBatchEvent, self._on_triples_added)

        self.context_aware = store.context_aware
        self.graph_aware = store.graph_aware
        self.formula_aware = False
        self.transaction_aware = store.transaction_aware

    def _get_engine(self, context_id: ContextIdentifier) -> RETEEngine:
        if context_id not in self.engines:
            self.engines[context_id] = self.factory.new_engine(context_id)
        return self.engines[context_id]

    def _on_triples_added(self, event: TripleAddedBatchEvent) -> None:
        # NOTE: The integration with RETEEngine is intentionally minimal for now.
        # Once RETEEngine.add_triples is implemented, this method SHOULD:
        #   1. Look up / create the engine for the event.context_id.
        #   2. Call engine.add_triples with event.events.
        #   3. Materialize any inferred triples into the backing store.
        _ = event

    def create(self, configuration: str) -> None:
        self.store.create(configuration)

    def open(
        self, configuration: str | tuple[str, str], create: bool = False
    ) -> int | None:
        return self.store.open(configuration, create)

    def close(self, commit_pending_transaction: bool = False) -> None:
        self.store.close(commit_pending_transaction)

    def gc(self) -> None:
        self.store.gc()

    def add(
        self,
        triple: _TripleType,
        context: _ContextType,
        quoted: bool = False,
    ) -> None:
        self.store.add(triple, context, quoted)

    def addN(self, quads: Iterable[_QuadType]) -> None:  # type: ignore[misc,override]
        self.store.addN(quads)

    def remove(
        self,
        triple: _TriplePatternType,
        context: _ContextType | None = None,
    ) -> None:
        self.store.remove(triple, context)

    def triples_choices(
        self,
        triple: _TripleChoiceType,
        context: _ContextType | None = None,
    ) -> Generator[tuple[_TripleType, Iterator[_ContextType | None]], None, None]:
        yield from self.store.triples_choices(triple, context)  # type: ignore[arg-type,misc]

    def triples(  # type: ignore[return]
        self,
        triple_pattern: _TriplePatternType,  # type: ignore[misc,override]
        context: _ContextType | None = None,
    ) -> Iterator[tuple[_TripleType, Iterator[_ContextType | None]]]:
        return self.store.triples(triple_pattern, context)  # type: ignore[return-value]

    def __len__(self, context: _ContextType | None = None) -> int:
        return len(self.store)

    def contexts(
        self,
        triple: _TripleType | None = None,  # type: ignore[misc,override]
    ) -> Generator[_ContextType, None, None]:
        return self.store.contexts(triple)

    def query(
        self,
        query: Query | str,
        initNs: Mapping[str, Any],  # noqa: N803
        initBindings: Mapping[str, Identifier],  # noqa: N803
        queryGraph: str,  # noqa: N803
        **kwargs: Any,
    ) -> Result:
        return self.store.query(query, initNs, initBindings, queryGraph, **kwargs)

    def update(
        self,
        update: Update | str,
        initNs: Mapping[str, Any],  # noqa: N803
        initBindings: Mapping[str, Identifier],  # noqa: N803
        queryGraph: str,  # noqa: N803
        **kwargs: Any,
    ) -> None:
        return self.store.update(update, initNs, initBindings, queryGraph, **kwargs)

    def bind(self, prefix: str, namespace: URIRef, override: bool = True) -> None:
        return self.store.bind(prefix, namespace, override)

    def prefix(self, namespace: URIRef) -> str | None:
        return self.store.prefix(namespace)

    def namespace(self, prefix: str) -> URIRef | None:
        return self.store.namespace(prefix)

    def namespaces(self) -> Iterator[tuple[str, URIRef]]:
        yield from self.store.namespaces()

    def commit(self) -> None:
        self.store.commit()

    def rollback(self) -> None:
        self.store.rollback()

    def add_graph(self, graph: Graph) -> None:
        self.store.add_graph(graph)

    def remove_graph(self, graph: Graph) -> None:
        self.store.remove_graph(graph)
