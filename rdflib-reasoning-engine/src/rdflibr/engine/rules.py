from abc import ABC, abstractmethod
from typing import TypedDict

from pydantic import Field
from rdflib.term import Node
from rdflibr.axiom.common import ContextIdentifier

from .proof import ProofModel, RuleDescription, RuleId


class RuleContext:
    """Placeholder read-only context passed to public predicates and callbacks."""


class PredicateHook(ABC):
    """Placeholder public read-only predicate hook used in rule conditions."""

    @abstractmethod
    def test(self, context: RuleContext, *args: Node) -> bool:
        pass


class CallbackHook(ABC):
    """Placeholder public non-logical callback hook attached to a rule match."""

    @abstractmethod
    def run(self, context: RuleContext, *args: Node) -> None:
        pass


class Builtins(TypedDict, total=False):
    """Placeholder registry for host-provided predicates and callbacks.

    Public builtins are split into read-only predicate evaluation and
    observational callbacks. Logical triple production remains engine-managed
    and is therefore not represented as a builtin hook.
    """

    predicates: dict[str, PredicateHook]
    callbacks: dict[str, CallbackHook]


class ContextData(TypedDict, total=False):
    """Per-engine contextual inputs supplied by the factory for one graph."""

    builtins: Builtins
    context: ContextIdentifier


class Rule(ProofModel):
    """Placeholder public rule definition consumed by the engine facade."""

    id: RuleId = Field(..., description="Stable identifier for this rule definition.")
    description: RuleDescription | None = Field(
        default=None,
        description="Optional shared descriptive metadata for this rule.",
    )
