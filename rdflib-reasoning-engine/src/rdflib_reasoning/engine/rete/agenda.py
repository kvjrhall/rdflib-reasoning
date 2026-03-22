from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from heapq import heappop, heappush

from .consequents import ActionInstance


@dataclass(order=True, frozen=True, slots=True)
class AgendaEntry:
    """Sortable agenda entry implementing conflict-resolution priorities."""

    salience_rank: int
    depth_rank: int
    insertion_rank: int
    action: ActionInstance = field(compare=False)


class Agenda:
    """
    Central scheduler for rule activations.

    The agenda applies conflict resolution using user-defined salience first,
    then breadth-first inference depth, while preserving stable insertion order
    among otherwise equivalent activations.
    """

    _entries: list[AgendaEntry]
    _next_insertion_rank: int

    def __init__(self, actions: Iterable[ActionInstance] = ()) -> None:
        self._entries = []
        self._next_insertion_rank = 0
        self.extend(actions)

    @staticmethod
    def _entry(action: ActionInstance, insertion_rank: int) -> AgendaEntry:
        return AgendaEntry(
            salience_rank=-action.salience,
            depth_rank=action.depth,
            insertion_rank=insertion_rank,
            action=action,
        )

    def enqueue(self, action: ActionInstance) -> None:
        heappush(self._entries, self._entry(action, self._next_insertion_rank))
        self._next_insertion_rank += 1

    def extend(self, actions: Iterable[ActionInstance]) -> None:
        for action in actions:
            self.enqueue(action)

    def pop(self) -> ActionInstance:
        return heappop(self._entries).action

    def drain(self) -> tuple[ActionInstance, ...]:
        drained: list[ActionInstance] = []
        while len(self._entries) > 0:
            drained.append(self.pop())
        return tuple(drained)

    def __bool__(self) -> bool:
        return len(self._entries) > 0

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[ActionInstance]:
        return iter(self.drain())
