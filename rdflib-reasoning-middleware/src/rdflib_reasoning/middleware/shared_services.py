"""Shared in-process services for dataset sessions and run-local RDF term telemetry."""

from collections import Counter
from collections.abc import Generator, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field as DataclassField
from threading import Lock

from rdflib import Dataset, Graph, URIRef
from rdflib_reasoning.axiom.common import ContextIdentifier
from rdflib_reasoning.engine.api import NO_RULES, ReasonerSpecification
from rdflib_reasoning.middleware.common import copy_dataset, copy_graph, not_none
from readerwriterlock import rwlock


@dataclass(frozen=True, slots=True)
class DatasetSession:
    """Mutable dataset state.

    This developer-facing session remains internal runtime infrastructure rather
    than copied agent state. The shared :class:`DatasetRuntime` service owns the
    active session for middleware that needs coordinated access to the same dataset.

    The :attr:`dataset` is a mutable :class:`rdflib.Dataset` object, whose
    thread safety depends on the underlying store and the usage of transactions
    by client code.
    To avoid any unexpected behavior, all interactions with the dataset should
    be performed through the :class:`DatasetRuntime` service.
    """

    dataset: Dataset


@dataclass(slots=True)
class DatasetRuntime:
    """Shared mutable dataset coordination boundary for middleware.

    You MUST NOT assume that the synchronization primitives used by this runtime
    are re-entrant. That is, you MUST NOT invoke other ``DatasetRuntime`` inside
    any context managers provided by this class
    (e.g., the one provided by ::meth:`dataset_write`).
    """

    specification: ReasonerSpecification = DataclassField(default=NO_RULES)
    _session: DatasetSession = DataclassField(init=False)
    _lock: rwlock.RWLockableD = DataclassField(init=False)

    def __post_init__(self) -> None:
        """Initialize variables of the runtime."""
        self._session = DatasetSession(dataset=self.specification.dataset())
        self._lock = rwlock.RWLockFairD()

    def dataset_size(self) -> int:
        """Return the total quad count in the live dataset.

        This method obtains a read lock on the runtime.
        """
        with self._lock.gen_rlock():
            return len(self._session.dataset)

    @contextmanager
    def dataset_write(self) -> Generator[Dataset, None, None]:
        """Context manager for write access to the live dataset.

        You MUST NOT mutate the dataset outside of this context manager.
        You MUST NOT invoke other ``DatasetRuntime`` methods INSIDE this context manager.

        This method obtains a write lock on the runtime.
        """
        with self._lock.gen_wlock():
            yield self._session.dataset

    def graph_size(self, context: ContextIdentifier | None = None) -> int:
        """Return the triple count in a named or default graph.

        This method obtains a read lock on the dataset.
        """
        with self._lock.gen_rlock():
            if context is None:
                return len(self._session.dataset.default_graph)
            else:
                try:
                    return len(
                        not_none(
                            self._session.dataset.get_graph(context),
                            f"Graph {context} not found",
                        )
                    )
                except IndexError as e:
                    # Though `get_graph` returns `Graph | None`, it's possible
                    # for `IndexError` to be raised if the graph is not found.
                    raise ValueError(f"Graph {context} not found") from e

    def replace_dataset(self) -> None:
        """Close the current dataset and start a fresh empty session.

        This method obtains a write lock on the runtime.
        """
        with self._lock.gen_wlock():
            self._session.dataset.close()
            self._session = DatasetSession(dataset=self.specification.dataset())

    def snapshot_dataset(self) -> Dataset:
        """Return a deep copy of the live dataset.

        This method obtains a read lock on the runtime.
        """
        with self._lock.gen_rlock():
            return copy_dataset(self._session.dataset)

    def snapshot_graph(self, context: ContextIdentifier | None = None) -> Graph:
        """Return a deep copy of a named or default graph.

        This method obtains a read lock on the runtime.
        """
        with self._lock.gen_rlock():
            source_graph: Graph
            if context is None:
                source_graph = self._session.dataset.default_graph
            else:
                source_graph = not_none(
                    self._session.dataset.get_graph(context),
                    f"Graph {context} not found",
                )

            return copy_graph(source_graph)


@dataclass(slots=True)
class RunTermTelemetry:
    """Default in-memory run-local telemetry for asserted RDF term usage.

    Following `DR-020` (preceded by `DR-019` and `DR-017`), this data object
    is notified when terms are used by :class:`DatasetMiddleware`.
    Not yet implemented is usage by :class:`RDFVocabularyMiddleware` to be able
    to rank/boost terms in search results.

    If some more sophisticated search strategy is implemented, the application
    of this class will need to be revisited.
    """

    _asserted_term_counts: Counter[str] = DataclassField(default_factory=Counter)
    _lock: Lock = DataclassField(default_factory=Lock)

    def record_asserted_terms(self, terms: Iterable[URIRef]) -> None:
        """Increment per-IRI counts for terms asserted during the current run."""
        with self._lock:
            self._asserted_term_counts.update(str(term) for term in terms)

    def asserted_term_count(self, term: URIRef | str) -> int:
        """Return how many times ``term`` was recorded in this run."""
        with self._lock:
            return self._asserted_term_counts[str(term)]

    def snapshot_asserted_term_counts(self) -> Mapping[str, int]:
        """Return a copy of asserted-term counts keyed by IRI string."""
        with self._lock:
            return dict(self._asserted_term_counts)
