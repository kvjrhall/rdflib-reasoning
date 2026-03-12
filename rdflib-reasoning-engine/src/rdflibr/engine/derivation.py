from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .proof import DerivationRecord, DirectProof, ProofPayload


class DerivationLogger(Protocol):
    """Interface for sinks of engine-native derivation records.

    These records are engine provenance artifacts, not user-facing proof steps.
    """

    def record(self, record: DerivationRecord) -> None: ...


class ExplanationReconstructor(Protocol):
    """Interface for rebuilding `DirectProof` values from derivation records."""

    def reconstruct(
        self,
        goal: ProofPayload,
        records: Iterable[DerivationRecord],
    ) -> DirectProof: ...
