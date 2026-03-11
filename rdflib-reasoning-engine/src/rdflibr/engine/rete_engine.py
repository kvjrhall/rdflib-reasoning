from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Any, TypedDict, cast

from rdflib.term import Node
from rdflibr.axiom.common import ContextIdentifier, Triple


# TODO: Relocate and make actual class - Proposed for discussion basis
class FatalRuleError(RuntimeError):
    pass


# TODO: Relocate and make actual class - Proposed for discussion basis
class RuleContext:
    pass


# TODO: Relocate and make actual class - Proposed for discussion basis
class RuleAction(ABC):
    @abstractmethod
    def head_action(self, context: RuleContext, *args: Node) -> None:
        pass


# TODO: Relocate and make actual class - Proposed for discussion basis
class Builtins(TypedDict, total=False):
    """A mapping of identifiers to rule actions or predicates."""

    add_triple: RuleAction
    retract_triple: RuleAction


# TODO: Relocate and make actual class - Proposed for discussion basis
class ContextData(TypedDict, total=False):
    builtins: Builtins
    context: ContextIdentifier


# TODO: Relocate and make actual class - Proposed for discussion basis
class Rule:
    pass


class RETEEngine:
    context_data: ContextData
    rules: Sequence[Rule]

    def __init__(self, context_data: ContextData, rules: Iterable[Rule]) -> None:
        # NOTE: I like the idea that users can add context data that will be available to their builtins.
        self.context_data = context_data
        self.rules = tuple(rules)
        # TODO: initialize the engine

    def close(self) -> None:
        # TODO: consider if this is actually necessary
        pass

    def add_triples(self, triples: Iterable[Triple]) -> set[Triple]:
        raise NotImplementedError("RETEEngine.add_triple is not implemented")

    def retract_triples(self, triple: Triple) -> None:
        raise NotImplementedError("RETEEngine.retract_triple is not implemented")

    def warmup(self, existing_triples: Iterable[Triple]) -> set[Triple]:
        """Warmup the engine by running precondition-free rules & processing any existing triples.

        Returns the set of triples that were deduced during the warmup.
        """
        # If present, NON-SILENT precondition-free rules generate triples that should be materialized.
        # TODO: get axiomatic_triples by running precondition-free rules
        axiomatic_triples: Sequence[Triple] = []

        # We don't need to add axiomatic_triples to this input as they are already in RETE nework.
        warmup_inferences = self.add_triples(existing_triples)
        return warmup_inferences.union(axiomatic_triples)


class RETEEngineFactory:
    context_template: dict[str, Any]

    def __init__(self, **context_data: Any) -> None:
        if "context" in context_data:
            raise ValueError("context is a reserved keyword")
        self.context_template = context_data

    def new_engine(self, context: ContextIdentifier) -> RETEEngine:
        raw_context_data: dict[str, Any] = {"context": context, **self.context_template}
        context_data = cast(ContextData, raw_context_data)  # noqa: F841
        # NOTE: RETEEngine wiring will be implemented in a subsequent iteration.
        raise NotImplementedError("RETEEngineFactory.new_engine is not implemented")
