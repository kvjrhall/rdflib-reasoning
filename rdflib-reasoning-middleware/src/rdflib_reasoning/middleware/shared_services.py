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
        return self.session.snapshot_dataset()

    def dataset_size(self) -> int:
        with self.session._lock.gen_rlock():
            return len(self.session._dataset)

    def default_graph_size(self) -> int:
        with self.session._lock.gen_rlock():
            return len(self.session._dataset.default_graph)

    def replace_dataset(self) -> None:
        with self.session._lock.gen_wlock():
            self.session._dataset.close()
            self.session = _new_dataset_session()


@dataclass(slots=True)
class RunTermTelemetry:
    """Default in-memory run-local telemetry for asserted RDF term usage."""

    _asserted_term_counts: Counter[str] = DataclassField(default_factory=Counter)
    _lock: Lock = DataclassField(default_factory=Lock)

    def record_asserted_terms(self, terms: Iterable[URIRef]) -> None:
        with self._lock:
            self._asserted_term_counts.update(str(term) for term in terms)

    def asserted_term_count(self, term: URIRef | str) -> int:
        with self._lock:
            return self._asserted_term_counts[str(term)]

    def snapshot_asserted_term_counts(self) -> Mapping[str, int]:
        with self._lock:
            return dict(self._asserted_term_counts)
