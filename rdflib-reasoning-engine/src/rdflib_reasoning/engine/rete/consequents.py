from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from rdflib.term import Node

from ..proof import RuleId
from ..rules import TriplePattern
from .facts import Fact


class TripleProduction(BaseModel):
    """
    Declarative logical consequent managed by the engine.

    Logical rule heads are represented as engine-managed triple production so
    that fixed-point reasoning and future truth maintenance remain centralized.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    rule_id: RuleId = Field(..., description="Rule that produced this consequent.")
    pattern: TriplePattern = Field(
        ..., description="Normalized triple template to instantiate from bindings."
    )
    required_variables: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Variable names that must be bound before instantiation.",
    )


class CallbackSchedule(BaseModel):
    """A normalized non-mutating callback scheduled from a completed match."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    callback: str = Field(..., description="Callback registry key.")
    arguments: tuple[Node, ...] = Field(
        default_factory=tuple,
        description="Normalized callback arguments as RDFLib terms or Variables.",
    )
    required_variables: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Variable names that must be bound before invocation.",
    )


class ActionInstance(BaseModel):
    """
    Scheduled unit of work derived from a completed match.

    An action instance may represent logical triple production, an
    observational callback, or both as separate scheduled consequences of a
    single terminal match.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    rule_id: RuleId
    bindings: dict[str, Node]
    premises: tuple[Fact, ...] = ()
    depth: int = 0
    salience: int = 0
    productions: tuple[TripleProduction, ...] = ()
    callbacks: tuple[CallbackSchedule, ...] = ()

    @property
    def kind(self) -> Literal["production", "callback", "mixed", "empty"]:
        has_productions = len(self.productions) > 0
        has_callbacks = len(self.callbacks) > 0
        if has_productions and has_callbacks:
            return "mixed"
        if has_productions:
            return "production"
        if has_callbacks:
            return "callback"
        return "empty"
