from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from rdflib.term import Node, Variable
from rdflibr.axiom.common import ContextIdentifier, Triple

from .derivation import DerivationLogger
from .proof import DerivationRecord, TripleFact, VariableBinding
from .rete import Agenda, NetworkBuilder, NetworkMatcher, RuleCompiler, TerminalNode
from .rules import CallbackHook, ContextData, Rule, RuleContext


@dataclass
class EngineCallbackContext(RuleContext):
    """Read-only callback context for one fired rule activation."""

    context: ContextIdentifier | None
    rule_id: Any
    bindings: Mapping[str, Node]
    premises: tuple[Triple, ...]
    depth: int
    _events: list[Any] = field(default_factory=list)
    _recorder: Any = None

    def record(self, event: Any) -> None:
        self._events.append(event)
        if self._recorder is not None:
            self._recorder.record(event)


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
    terminals: tuple[TerminalNode, ...]
    known_triples: set[Triple]
    matcher: NetworkMatcher
    derivation_logger: DerivationLogger | None
    callbacks: dict[str, CallbackHook]
    callback_recorder: Any

    def __init__(self, context_data: ContextData, rules: Iterable[Rule]) -> None:
        self.context_data = context_data
        self.rules = tuple(rules)
        compiled_rules = tuple(RuleCompiler.compile_rule(rule) for rule in self.rules)
        builder = NetworkBuilder()
        self.terminals = builder.build_rules(compiled_rules)
        builtins = self.context_data.get("builtins", {})
        predicates = builtins.get("predicates", {})
        self.callbacks = builtins.get("callbacks", {})
        self.matcher = NetworkMatcher(builder.registry, predicates=predicates)
        self.known_triples = set()
        self.derivation_logger = self.context_data.get("derivation_logger")
        self.callback_recorder = self.context_data.get("callback_recorder")

    def close(self) -> None:
        self.known_triples.clear()

    @staticmethod
    def _instantiate_triple(
        pattern: tuple[Node | Variable, Node | Variable, Node | Variable],
        bindings: Mapping[str, Node],
    ) -> Triple:
        instantiated: list[Node] = []
        for term in pattern:
            if isinstance(term, Variable):
                variable_name = str(term)
                if variable_name not in bindings:
                    raise FatalRuleError(
                        f"Missing binding for required variable `{variable_name}`"
                    )
                instantiated.append(bindings[variable_name])
            else:
                instantiated.append(term)
        return cast(Triple, tuple(instantiated))

    @staticmethod
    def _resolve_callback_arguments(
        arguments: tuple[Node, ...],
        bindings: Mapping[str, Node],
    ) -> tuple[Node, ...]:
        resolved: list[Node] = []
        for argument in arguments:
            if isinstance(argument, Variable):
                variable_name = str(argument)
                if variable_name not in bindings:
                    raise FatalRuleError(
                        f"Missing binding for required variable `{variable_name}`"
                    )
                resolved.append(bindings[variable_name])
            else:
                resolved.append(argument)
        return tuple(resolved)

    def add_triples(self, triples: Iterable[Triple]) -> set[Triple]:
        pending = {cast(Triple, triple) for triple in triples}
        self.known_triples.update(pending)
        newly_derived: set[Triple] = set()
        context = self.context_data.get("context")

        while True:
            try:
                actions = self.matcher.match_terminals(
                    self.terminals, tuple(self.known_triples)
                )
                agenda = Agenda(actions)
            except Exception as exc:  # pragma: no cover - defensive wrapping
                if isinstance(exc, FatalRuleError):
                    raise
                raise FatalRuleError(str(exc)) from exc

            iteration_new: set[Triple] = set()
            for action in agenda:
                action_new: list[Triple] = []
                for production in action.productions:
                    pattern = (
                        production.pattern.subject,
                        production.pattern.predicate,
                        production.pattern.object,
                    )
                    triple = self._instantiate_triple(pattern, action.bindings)
                    if triple not in self.known_triples:
                        iteration_new.add(triple)
                        action_new.append(triple)

                callback_context = EngineCallbackContext(
                    context=context,
                    rule_id=action.rule_id,
                    bindings=action.bindings,
                    premises=tuple(fact.triple for fact in action.premises),
                    depth=action.depth,
                    _recorder=self.callback_recorder,
                )
                for callback in action.callbacks:
                    hook = self.callbacks.get(callback.callback)
                    if hook is None:
                        raise FatalRuleError(
                            f"Unknown callback hook `{callback.callback}`"
                        )
                    arguments = self._resolve_callback_arguments(
                        callback.arguments, action.bindings
                    )
                    try:
                        hook.run(callback_context, *arguments)
                    except Exception as exc:  # pragma: no cover - defensive wrapping
                        if isinstance(exc, FatalRuleError):
                            raise
                        raise FatalRuleError(str(exc)) from exc

                if (
                    context is not None
                    and self.derivation_logger is not None
                    and len(action_new) > 0
                ):
                    self.derivation_logger.record(
                        DerivationRecord(
                            context=context,
                            conclusions=[
                                TripleFact(context=context, triple=triple)
                                for triple in action_new
                            ],
                            premises=[
                                TripleFact(context=context, triple=fact.triple)
                                for fact in action.premises
                            ],
                            rule_id=action.rule_id,
                            bindings=[
                                VariableBinding(name=name, value=value)
                                for name, value in sorted(action.bindings.items())
                            ],
                            depth=action.depth,
                        )
                    )

            if not iteration_new:
                break

            self.known_triples.update(iteration_new)
            newly_derived.update(iteration_new)

        return newly_derived

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
    rules_template: tuple[Rule, ...]

    def __init__(self, *, rules: Iterable[Rule] = (), **context_data: Any) -> None:
        if "context" in context_data:
            raise ValueError("context is a reserved keyword")
        self.context_template = context_data
        self.rules_template = tuple(rules)

    def new_engine(self, context: ContextIdentifier) -> RETEEngine:
        raw_context_data: dict[str, Any] = {"context": context, **self.context_template}
        context_data = cast(ContextData, raw_context_data)
        return RETEEngine(context_data=context_data, rules=self.rules_template)
