import logging
from typing import cast

from rdflib import Graph
from rdflib.events import Dispatcher, Event
from rdflib.graph import _ContextType
from rdflib.store import Store, TripleAddedEvent, TripleRemovedEvent
from rdflibr.axiom.common import ContextIdentifier, Triple

logger = logging.getLogger(__name__)


class BatchEvent(Event):
    events: set[Triple]
    context_id: ContextIdentifier

    def __init__(self, events: set[Triple], context_id: ContextIdentifier):
        super().__init__(events=events, context_id=context_id)

    def __repr__(self) -> str:
        return f"BatchEvent(events={self.events}, context_id={self.context_id})"


class TripleAddedBatchEvent(BatchEvent):
    def __init__(self, events: set[Triple], context_id: ContextIdentifier):
        super().__init__(events=events, context_id=context_id)


class TripleRemovedBatchEvent(BatchEvent):
    def __init__(self, events: set[Triple], context_id: ContextIdentifier):
        super().__init__(events=events, context_id=context_id)


class BatchDispatcher(Dispatcher):
    """A dispatcher that batches store events and drives fixed-point iteration.

    If a listener to a `rdflib.Store` is sensitive to reentrant event handlers,
    this dispatcher allows for batches of events to be handled without re-entrancy.

    Additionally, this dispatcher will forward `TripleAddedEvent` and
    `TripleRemovedEvent` events after deduplication.
    Subscribers can assume that each event will be unique.

    **Store event contract**

    The batch dispatcher assumes that backing stores *always* emit
    ``TripleAddedEvent`` (respectively ``TripleRemovedEvent``) on every
    ``add()`` / ``remove()`` call, even when the triple is already present or
    absent, and that they do so *before* performing the mutation. The
    dispatcher uses a ``triple in context`` check to filter duplicate events
    (skip adding to the batch when the triple is already in the context).

    **Fixed-point procedure**

    1. If a ``TripleAddedEvent`` or ``TripleRemovedEvent`` is received, it is
       added to the current batch for its context.
    2. If there are a nonzero number of batches for the context, the batch is
       popped and dispatched.
    3. During dispatch, any additional events received for that context are
       added to the next batch for that context.
    4. When the dispatch ends, we return to step 2.

    **Inference engine entrypoint**

    The entrypoint for the inference engine (e.g. RETE) is subscription to
    ``TripleAddedBatchEvent`` (and optionally ``TripleRemovedBatchEvent``).
    Subscribers receive per-context batches and fixed point is achieved by the
    dispatcher's loop. Reasoners SHOULD subscribe to these batch events and
    handle the batches accordingly (e.g. materialize derived triples).
    """

    _current_additions: dict[ContextIdentifier, set[Triple]]
    _current_removals: dict[ContextIdentifier, set[Triple]]

    _handling_addition: bool
    _handling_removal: bool

    backing_store: Store

    def __init__(self, backing_store: Store):
        super().__init__()
        self.backing_store = backing_store
        self._current_additions = dict()
        self._current_removals = dict()
        self._handling_addition = False
        self._handling_removal = False

        # We subscribe to the triple addition events
        backing_store.dispatcher.subscribe(TripleAddedEvent, self._on_triple_added)
        backing_store.dispatcher.subscribe(TripleRemovedEvent, self._on_triple_removed)

    def _exists_in_store(self, triple: Triple, context_id: ContextIdentifier) -> bool:
        def matches_context(context: _ContextType) -> bool:
            return context.identifier == context_id

        # The type contract for `contexts` requires non-null identifiers, so we can safely assume
        # that we will receive `rdflib.graph.DATASET_DEFAULT_GRAPH_ID` for the default graph.
        return any(map(matches_context, self.backing_store.contexts(triple)))

    def _has_any_subscriber[T: Event](self, event_type: type[T]) -> bool:
        """Calling `dispatch` without any subscribers raises an exception."""
        return self._dispatch_map is not None and event_type in self._dispatch_map

    def _on_triple_added(self, event: TripleAddedEvent) -> None:
        triple = cast(Triple, event.triple)  # type: ignore[attr-defined]
        event_context_id = cast(Graph, event.context).identifier  # type: ignore[attr-defined]

        if self._exists_in_store(triple, event_context_id):
            # Store event contract: event is emitted on every add(); skip if triple already in context.
            # Caveat: event_context is caller-passed and may not be the store's graph (see docstring).
            return

        # Forward de-duplicated event to our subscribers
        self._safe_dispatch(event)

        self._current_additions.setdefault(event_context_id, set()).add(triple)

        if not self._handling_addition:
            self._handling_addition = True
            while event_context_id in self._current_additions:
                additions = self._current_additions.pop(event_context_id)
                if len(additions) == 0:
                    continue

                if self._has_any_subscriber(TripleAddedBatchEvent):
                    batch_event = TripleAddedBatchEvent(
                        events=set(additions),
                        context_id=event_context_id,
                    )
                    self.dispatch(batch_event)

            self._handling_addition = False

    def _on_triple_removed(self, event: TripleRemovedEvent):
        triple = cast(Triple, event.triple)  # type: ignore[attr-defined]
        event_context_id = cast(Graph, event.context).identifier  # type: ignore[attr-defined]

        if not self._exists_in_store(triple, event_context_id):
            # Store event contract: event is emitted on every remove(); skip if triple already absent.
            # Caveat: event_context is caller-passed and may not be the store's graph (see docstring).
            return

        # Forward de-duplicated event to our subscribers
        self._safe_dispatch(event)

        self._current_removals.setdefault(event_context_id, set()).add(triple)

        if not self._handling_removal:
            self._handling_removal = True
            while event_context_id in self._current_removals:
                removals = self._current_removals.pop(event_context_id)
                if len(removals) == 0:
                    continue

                batch_event = TripleRemovedBatchEvent(
                    events=set(removals),
                    context_id=event_context_id,
                )
                self._safe_dispatch(batch_event)

            self._handling_removal = False

    def _safe_dispatch[T: Event](self, event: T) -> None:
        if self._has_any_subscriber(type(event)):
            self.dispatch(event)
