"""Shared in-process services for dataset sessions and run-local RDF term telemetry."""

from collections import Counter
from collections.abc import Iterable, Mapping, MutableSet
from dataclasses import dataclass
from dataclasses import field as DataclassField
from threading import Lock

import more_itertools
from rdflib import BNode, Dataset, Graph, IdentifiedNode, Node, URIRef
from readerwriterlock import rwlock


@dataclass(frozen=True, slots=True)
class DatasetSession:
    """Mutable dataset state plus its coordination primitives.

    This developer-facing session remains internal runtime infrastructure rather
    than copied agent state. The shared `DatasetRuntime` service owns the active
    session for middleware that needs coordinated access to the same dataset.
    """

    _dataset: Dataset
    _blank_nodes: MutableSet[BNode] = DataclassField(default_factory=set)
    _lock: rwlock.RWLockable = DataclassField(default_factory=rwlock.RWLockFairD)

    def snapshot_dataset(self) -> Dataset:
        """Return a deep copy of the live dataset under a read lock."""

        def _cleanup_quad(
            quad: tuple[Node, Node, Node, IdentifiedNode | None],
        ) -> tuple[Node, Node, Node, Graph]:
            s, p, o, g_id = quad
            g = (
                self._dataset.get_graph(g_id)
                if g_id is not None
                else self._dataset.default_graph
            )
            assert isinstance(g, Graph)
            return (s, p, o, g)

        with self._lock.gen_rlock():
            dataset = Dataset()
            for chunk in more_itertools.chunked(
                map(_cleanup_quad, self._dataset.quads((None, None, None, None))),
                1000,
            ):
                dataset.addN(chunk)
            return dataset


def _new_dataset_session() -> DatasetSession:
    return DatasetSession(_dataset=Dataset())


@dataclass(slots=True)
class DatasetRuntime:
    """Shared mutable dataset coordination boundary for middleware."""

    session: DatasetSession = DataclassField(default_factory=_new_dataset_session)

    def snapshot_dataset(self) -> Dataset:
        """Return a deep copy of the coordinated dataset session."""
        return self.session.snapshot_dataset()

    def dataset_size(self) -> int:
        """Return the total quad count in the live dataset."""
        with self.session._lock.gen_rlock():
            return len(self.session._dataset)

    def default_graph_size(self) -> int:
        """Return the triple count in the dataset default graph."""
        with self.session._lock.gen_rlock():
            return len(self.session._dataset.default_graph)

    def replace_dataset(self) -> None:
        """Close the current dataset and start a fresh empty session."""
        with self.session._lock.gen_wlock():
            self.session._dataset.close()
            self.session = _new_dataset_session()


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
