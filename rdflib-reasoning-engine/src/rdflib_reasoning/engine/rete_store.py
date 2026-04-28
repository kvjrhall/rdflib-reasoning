import warnings
from collections.abc import Generator, Iterable, Iterator, Mapping
from typing import Any, Literal, cast

from rdflib import Graph, URIRef
from rdflib.events import Dispatcher
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
from rdflib.store import VALID_STORE, Store, TripleAddedEvent, TripleRemovedEvent
from rdflib.term import Identifier
from rdflib_reasoning.axiom.common import ContextIdentifier, Triple

from .api import RETEEngine, RETEEngineFactory
from .batch_dispatcher import (
    BatchDispatcher,
    TripleAddedBatchEvent,
    TripleRemovedBatchEvent,
)


class RetractionRematerializeWarning(UserWarning):
    """Warning emitted when a store removal is logically ineffective.

    The engine still derives the removed triple, so ``RETEStore`` re-adds it
    to the backing context graph after the original removal pass completes.
    Callers that intend the triple to actually disappear must retract a
    supporting stated fact instead.
    """


# Return type for open(): rdflib stores use 1, 0, -1 (VALID_STORE, CORRUPTED_STORE, NO_STORE)
_OpenResult = Literal[1, 0, -1] | None


class RETEStore(Store):
    store: Store
    factory: RETEEngineFactory
    engines: dict[ContextIdentifier, RETEEngine]
    engine_contexts: dict[ContextIdentifier, Graph]
    _pending_rematerialize: dict[ContextIdentifier, set[Triple]]
    _remove_depth: int
    _raw_dispatcher: Dispatcher

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
        self._pending_rematerialize = {}
        self._remove_depth = 0

        # Per DR-026, RETEStore owns raw event emission; BatchDispatcher
        # subscribes to a private dispatcher rather than the backing store's.
        self._raw_dispatcher = Dispatcher()
        self.dispatcher = BatchDispatcher(
            source_dispatcher=self._raw_dispatcher, backing_store=store
        )
        self.dispatcher.subscribe(TripleAddedBatchEvent, self._on_triples_added)
        self.dispatcher.subscribe(TripleRemovedBatchEvent, self._on_triples_removed)

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

    def _on_triples_removed(self, batch: TripleRemovedBatchEvent) -> None:
        """Drive support-aware removal through the engine and reconcile the store.

        The dispatcher delivers a per-context batch of triples that are about
        to be removed from the backing store. ``RETEEngine.retract_triples``
        decides which input triples actually leave the engine's logical
        closure and what cascade consequents lose support. This handler:

        1. Issues backing-store removes for cascade consequents that were
           not in the original batch. ``BatchDispatcher`` queues these into a
           follow-up batch; the engine no-ops on that pass because each
           triple is already absent from working memory.
        2. Records any input triple whose working-memory fact survived
           because the engine still derives it (DR-025
           re-materialize-with-warning policy) into
           ``_pending_rematerialize``. The actual re-add is deferred to
           ``_flush_rematerialize`` so that it executes after the backing
           store's remove mutation completes; otherwise an inline
           ``context.add`` would be a no-op while the triple is still
           present in the backing store.
        """
        engine, context = self._ensure_engine(batch.context_id)

        cascade = engine.retract_triples(batch.events)

        cascade_to_remove = [t for t in cascade if t not in batch.events]
        for triple in cascade_to_remove:
            context.remove(triple)

        rematerialize = [t for t in batch.events if engine.working_memory.has_fact(t)]
        if rematerialize:
            self._pending_rematerialize.setdefault(batch.context_id, set()).update(
                rematerialize
            )

    def _flush_rematerialize(self) -> None:
        """Re-add re-materialized triples and emit warnings.

        Called from the outermost ``RETEStore.remove`` frame after the
        backing-store mutation has completed. At this point the original
        triples are gone from the backing store, so re-adding through the
        normal ``Graph.add`` path will succeed and the engine will see the
        re-add as an idempotent re-assertion of a fact it already believes.
        """
        if not self._pending_rematerialize:
            return
        pending = self._pending_rematerialize
        self._pending_rematerialize = {}
        for ctx_id, triples in pending.items():
            ctx_graph = self.engine_contexts.get(ctx_id)
            if ctx_graph is None:
                continue
            for triple in triples:
                warnings.warn(
                    "Removal of triple "
                    f"{triple[0].n3()} {triple[1].n3()} {triple[2].n3()} . "
                    "was logically ineffective: the engine still derives "
                    "this triple from another supported justification, so "
                    "it has been re-added to the backing store. Retract a "
                    "supporting stated fact instead if you intend the "
                    "triple to actually disappear.",
                    RetractionRematerializeWarning,
                    stacklevel=4,
                )
                ctx_graph.add(triple)

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
        # Per DR-026, emit the pre-mutation event ourselves on the private
        # raw dispatcher; BatchDispatcher will dedup against the backing
        # store via Store.contexts(triple).
        self._raw_dispatcher.dispatch(TripleAddedEvent(triple=triple, context=context))
        self.store.add(triple, context, quoted)

    def addN(self, quads: Iterable[_QuadType]) -> None:  # type: ignore[misc,override]
        # Per DR-026, materialize the iterable so we can emit one
        # pre-mutation event per quad on the private raw dispatcher before
        # delegating to the backing store.
        materialized_quads = list(quads)
        for quad in materialized_quads:
            subject, predicate, obj, context = quad
            self._raw_dispatcher.dispatch(
                TripleAddedEvent(
                    triple=(subject, predicate, obj),
                    context=context,
                )
            )
        self.store.addN(materialized_quads)

    def remove(
        self, triple: _TriplePatternType, context: _ContextType | None = None
    ) -> None:
        # Per DR-026, RETEStore owns pre-mutation event emission for
        # remove: snapshot the concrete triples matching the pattern in
        # the requested context, emit one ``TripleRemovedEvent`` per match
        # on the private raw dispatcher, then delegate to the backing
        # store. The depth counter ensures re-materializations queued by
        # ``_on_triples_removed`` are flushed only at the outermost frame,
        # after the backing mutation has completed.
        if context is None:
            self.store.remove(triple, context)
            return

        self._remove_depth += 1
        try:
            concrete_matches = [
                cast(Triple, match)
                for match, _ctxs in self.store.triples(triple, context)
            ]
            for match in concrete_matches:
                self._raw_dispatcher.dispatch(
                    TripleRemovedEvent(triple=match, context=context)
                )
            self.store.remove(triple, context)
        finally:
            self._remove_depth -= 1
            if self._remove_depth == 0:
                self._flush_rematerialize()

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
