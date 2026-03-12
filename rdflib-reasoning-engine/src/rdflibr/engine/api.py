from collections.abc import Iterable, Sequence
from typing import Any, cast

from rdflibr.axiom.common import ContextIdentifier, Triple

from .rules import ContextData, Rule


class FatalRuleError(RuntimeError):
    """Fatal error raised by public rule, predicate, or callback execution."""


class RETEEngine:
    """Public engine facade for fixed-point triple entailment within one context.

    The facade represents the add-only first implementation boundary:
    triple-oriented rule execution, optional derivation logging, and warm-start
    over an existing context. User-facing proof reconstruction is layered on top
    of derivation records rather than being the engine's execution format.
    """

    context_data: ContextData
    rules: Sequence[Rule]

    def __init__(self, context_data: ContextData, rules: Iterable[Rule]) -> None:
        self.context_data = context_data
        self.rules = tuple(rules)

    def close(self) -> None:
        pass

    def add_triples(self, triples: Iterable[Triple]) -> set[Triple]:
        raise NotImplementedError("RETEEngine.add_triple is not implemented")

    def retract_triples(self, triple: Triple) -> None:
        raise NotImplementedError("RETEEngine.retract_triple is not implemented")

    def warmup(self, existing_triples: Iterable[Triple]) -> set[Triple]:
        """Warm the engine from existing triples and return engine-managed deductions."""
        axiomatic_triples: Sequence[Triple] = []
        warmup_inferences = self.add_triples(existing_triples)
        return warmup_inferences.union(axiomatic_triples)


class RETEEngineFactory:
    """Factory for per-context engine instances and contextual hook registries."""

    context_template: dict[str, Any]

    def __init__(self, **context_data: Any) -> None:
        if "context" in context_data:
            raise ValueError("context is a reserved keyword")
        self.context_template = context_data

    def new_engine(self, context: ContextIdentifier) -> RETEEngine:
        raw_context_data: dict[str, Any] = {"context": context, **self.context_template}
        context_data = cast(ContextData, raw_context_data)  # noqa: F841
        raise NotImplementedError("RETEEngineFactory.new_engine is not implemented")
