from collections.abc import Generator, Iterable, Iterator, Mapping
from typing import Any, Literal, cast

from rdflib import Graph, URIRef
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
from rdflib.store import VALID_STORE, Store
from rdflib.term import Identifier
from rdflibr.axiom.common import ContextIdentifier, Triple

from .api import RETEEngine, RETEEngineFactory
from .batch_dispatcher import BatchDispatcher, TripleAddedBatchEvent

# Return type for open(): rdflib stores use 1, 0, -1 (VALID_STORE, CORRUPTED_STORE, NO_STORE)
_OpenResult = Literal[1, 0, -1] | None


class RETEStore(Store):
    store: Store
    factory: RETEEngineFactory
    engines: dict[ContextIdentifier, RETEEngine]
    engine_contexts: dict[ContextIdentifier, Graph]

    def __init__(self, store: Store, factory: RETEEngineFactory):
        super().__init__()
        if not store.context_aware:
            raise ValueError("Backing store must be context-aware")

        self.context_aware = True
        self.graph_aware = store.graph_aware
        self.formula_aware = False
        self.transaction_aware = False  # Requires truth maintenance support

        self.store = store
        self.factory = factory
        self.engines = dict()
        self.engine_contexts = {}

        self.dispatcher = BatchDispatcher(backing_store=store)
        self.dispatcher.subscribe(TripleAddedBatchEvent, self._on_triples_added)
        # self.dispatcher.subscribe(TripleRemovedBatchEvent, self._on_triples_removed)

    def _ensure_engine(self, context_id: ContextIdentifier) -> tuple[RETEEngine, Graph]:
        if context_id not in self.engines:
            engine = self.factory.new_engine(context_id)
            engine_context = Graph(store=self, identifier=context_id)

            self.engines[context_id] = engine
            self.engine_contexts[context_id] = Graph(store=self, identifier=context_id)
            existing_data = [
                cast(Triple, triple)
                for (triple, _) in self.store.triples(
                    (None, None, None), engine_context
                )
            ]
            warmup_deductions = engine.warmup(existing_data)

            # This addition MUST NOT trigger any inferences as all output triples are already in the engine's network.
            # See `DDR-04 RETE Store Persistence and Engine Update Contract`.
            engine_context.addN([(*t, engine_context) for t in warmup_deductions])

        return self.engines[context_id], self.engine_contexts[context_id]

    def _on_triples_added(self, batch: TripleAddedBatchEvent):
        engine, context = self._ensure_engine(batch.context_id)

        quads_produced = [
            (*t, context) for t in engine.add_triples(batch.events) if t not in context
        ]
        context.addN(quads_produced)

    # def _on_triples_removed(self, batch: TripleRemovedBatchEvent):
    #     raise NotImplementedError("RETEStore._on_triples_removed is not implemented")

    def create(self, configuration: str) -> None:
        # Delegated to the backing store
        self.store.create(configuration)

    def open(
        self, configuration: str | tuple[str, str], create: bool = False
    ) -> _OpenResult:
        store_status = cast(_OpenResult, self.store.open(configuration, create))
        if store_status is VALID_STORE:
            for context in self.store.contexts():
                self._ensure_engine(context.identifier)
        return store_status

    def close(self, commit_pending_transaction: bool = False) -> None:
        # Delegated to the backing store
        self.store.close(commit_pending_transaction)

    def gc(self) -> None:
        # Delegated to the backing store
        self.store.gc()

    def add(
        self,
        triple: _TripleType,
        context: _ContextType,
        quoted: bool = False,
    ) -> None:
        # Delegated to the backing store
        self.store.add(triple, context, quoted)

    def addN(self, quads: Iterable[_QuadType]) -> None:  # type: ignore[misc,override]
        # Delegated to the backing store
        self.store.addN(quads)

    def remove(
        self, triple: _TriplePatternType, context: _ContextType | None = None
    ) -> None:
        raise NotImplementedError(
            "Retractions (i.e., truth maintenance) are not yet supported"
        )

    def triples_choices(
        self,
        triple: _TripleChoiceType,
        context: _ContextType | None = None,
    ) -> Generator[tuple[_TripleType, Iterator[_ContextType | None]], None, None]:
        # Delegated to the backing store
        yield from self.store.triples_choices(triple, context)  # type: ignore[arg-type,misc]

    def triples(  # type: ignore[return]
        self,
        triple_pattern: _TriplePatternType,  # type: ignore[misc,override]
        context: _ContextType | None = None,
    ) -> Iterator[tuple[_TripleType, Iterator[_ContextType | None]]]:
        # Delegated to the backing store
        return self.store.triples(triple_pattern, context)  # type: ignore[return-value]

    def __len__(self, context: _ContextType | None = None) -> int:
        # Delegated to the backing store
        return len(self.store)

    def contexts(
        self,
        triple: _TripleType | None = None,  # type: ignore[misc,override]
    ) -> Generator[_ContextType, None, None]:
        # Delegated to the backing store
        return self.store.contexts(triple)

    def query(
        self,
        query: Query | str,
        initNs: Mapping[str, Any],  # noqa: N803
        initBindings: Mapping[str, Identifier],  # noqa: N803
        queryGraph: str,  # noqa: N803
        **kwargs: Any,
    ) -> Result:
        # Delegated to the backing store
        return self.store.query(query, initNs, initBindings, queryGraph, **kwargs)

    def update(
        self,
        update: Update | str,
        initNs: Mapping[str, Any],  # noqa: N803
        initBindings: Mapping[str, Identifier],  # noqa: N803
        queryGraph: str,  # noqa: N803
        **kwargs: Any,
    ) -> None:
        # return self.store.update(update, initNs, initBindings, queryGraph, **kwargs)
        # Without truth maintenance support, we can't support SPARQL Update.
        # Update operations can remove triples, delete graphs, etc.
        raise NotImplementedError("SPARQL Update is not supported yet")

    def bind(self, prefix: str, namespace: URIRef, override: bool = True) -> None:
        # Delegated to the backing store
        return self.store.bind(prefix, namespace, override)

    def prefix(self, namespace: URIRef) -> str | None:
        # Delegated to the backing store
        return self.store.prefix(namespace)

    def namespace(self, prefix: str) -> URIRef | None:
        # Delegated to the backing store
        return self.store.namespace(prefix)

    def namespaces(self) -> Iterator[tuple[str, URIRef]]:
        # Delegated to the backing store
        yield from self.store.namespaces()

    def commit(self) -> None:
        # Delegated to the backing store
        self.store.commit()

    def rollback(self) -> None:
        # Delegated to the backing store
        self.store.rollback()

    def add_graph(self, graph: Graph) -> None:
        self._ensure_engine(graph.identifier)
        self.store.add_graph(graph)

    def remove_graph(self, graph: Graph) -> None:
        # super().remove_graph(graph)
        # context_id = graph.identifier
        # del self.engine_contexts[context_id]
        # self.engines.pop(context_id).close()
        raise NotImplementedError(
            "Graph removal (Retraction/Truth Maintenance) is not yet supported"
        )
