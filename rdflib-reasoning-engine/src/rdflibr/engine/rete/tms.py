from typing import Any

from pydantic import BaseModel

from ..proof import RuleId


class DependencyGraph:
    """
    Bidirectional map tracking logical support relationships among facts.
    """

    ...


class Justification(BaseModel):
    """
    A single reason for a fact's logical support.

    Justifications are logical support records used for future truth
    maintenance; they are distinct from user-facing proof nodes.
    """

    rule_id: RuleId
    consequent_id: str
    antecedent_ids: tuple[str, ...]
    metadata: dict[str, Any]


class TMSController:
    """
    Controller for truth-maintenance bookkeeping and recursive retraction.

    Retraction remains future work, but the controller scaffold marks the
    boundary that add-only implementations should remain compatible with.
    """

    ...


class WorkingMemory:
    """
    Reactive store of currently asserted facts flowing through the network.

    Working memory is an execution-time structure, not a persisted proof or
    derivation artifact.
    """

    ...
