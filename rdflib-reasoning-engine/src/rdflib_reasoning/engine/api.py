import warnings
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from rdflib.term import BNode, Node, URIRef, Variable
from rdflib.term import Literal as RDFLiteral
from rdflib_reasoning.axiom.common import ContextIdentifier, Triple

from .builtins import DEFAULT_PREDICATE_BUILTINS
from .derivation import DerivationLogger
from .proof import DerivationRecord, TripleFact, VariableBinding
from .rete import (
    Agenda,
    NetworkBuilder,
    NetworkMatcher,
    RuleCompiler,
    TerminalNode,
    TMSController,
    WorkingMemory,
)
from .rules import CallbackHook, ContextData, Rule, RuleContext

_RDF_TRIPLES_SPEC_URL = "https://www.w3.org/TR/rdf11-concepts/#section-triples"


def _n3_term(term: Node | Variable) -> str:
    if isinstance(term, Variable):
        return str(term)
    return term.n3()


def _triple_n3(triple: Triple) -> str:
    s, p, o = triple
    return f"{_n3_term(s)} {_n3_term(p)} {_n3_term(o)} ."


def _format_term_constraint_diagnostics(
    triple: Triple,
    *,
    source: Literal["stated", "inferred"] | None,
    rule_id: Any = None,
    depth: int | None = None,
    pattern: tuple[Node | Variable, Node | Variable, Node | Variable] | None = None,
    bindings: Mapping[str, Node] | None = None,
    premises: tuple[Triple, ...] | None = None,
) -> str:
    lines = [
        f"  triple: {_triple_n3(triple)}",
    ]
    if source is not None:
        lines.append(f"  source: {source}")
    if source == "inferred" and rule_id is not None:
        lines.append(f"  rule_id: {rule_id!r}")
    if source == "inferred" and depth is not None:
        lines.append(f"  depth: {depth}")
    if pattern is not None:
        ps, pp, po = pattern
        lines.append(f"  pattern: {_n3_term(ps)} {_n3_term(pp)} {_n3_term(po)} .")
    if bindings:
        formatted = ", ".join(
            f"{name}={_n3_term(value)}" for name, value in sorted(bindings.items())
        )
        lines.append(f"  bindings: {formatted}")
    if premises:
        premise_lines = "; ".join(_triple_n3(t) for t in premises)
        lines.append(f"  premises: {premise_lines}")
    return "\n".join(lines)


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


class RDFTermConstraintError(FatalRuleError):
    """RDF term-type constraint violation with optional stated/inference context."""

    def __init__(
        self,
        message: str,
        *,
        triple: Triple | None = None,
        source: Literal["stated", "inferred"] | None = None,
        rule_id: Any = None,
        depth: int | None = None,
        pattern: tuple[Node | Variable, Node | Variable, Node | Variable] | None = None,
        bindings: Mapping[str, Node] | None = None,
        premises: tuple[Triple, ...] | None = None,
    ) -> None:
        super().__init__(message)
        self.triple = triple
        self.source = source
        self.rule_id = rule_id
        self.depth = depth
        self.pattern = pattern
        self.bindings = bindings
        self.premises = premises


class RuleTripleWarning(UserWarning):
    """Warning for triples rejected by RDF 1.1 triple well-formedness checks.

    These warnings are emitted when the engine is configured to warn and skip
    malformed triples instead of raising. The governing normative source is the
    RDF 1.1 Concepts triples section:
    https://www.w3.org/TR/rdf11-concepts/#section-triples
    """


class LiteralAsSubjectError(RDFTermConstraintError):
    """Raised when a stated or inferred triple has a literal subject.

    Literal subjects are disallowed by the RDF 1.1 data model, so the engine
    refuses to admit or materialize such triples in error mode.

    When available, :attr:`RDFTermConstraintError.triple` and related fields
    identify the offending triple and (for inferences) the rule activation.
    """


class LiteralAsSubjectWarning(RuleTripleWarning):
    """Warning emitted when a literal-subject triple is skipped in warning mode."""


class BlankNodePredicateError(RDFTermConstraintError):
    """Raised when a stated or inferred triple has a blank node predicate.

    Predicates must be IRIs in RDF 1.1, so the engine refuses to admit or
    materialize such triples in error mode.
    """


class BlankNodePredicateWarning(RuleTripleWarning):
    """Warning emitted when a blank-node-predicate triple is skipped in warning mode."""


class LiteralPredicateError(RDFTermConstraintError):
    """Raised when a stated or inferred triple has a non-IRI predicate.

    Literal predicates are explicitly invalid, and this exception is also used
    for the broader non-IRI predicate path when the engine is configured to
    fail fast.
    """


class LiteralPredicateWarning(RuleTripleWarning):
    """Warning emitted when a non-IRI-predicate triple is skipped in warning mode."""


LiteralSubjectPolicy = Literal["error", "warning"]
PredicateTermPolicy = Literal["error", "warning"]


class RETEEngine:
    """Public engine facade for fixed-point triple entailment within one context.

    The facade represents the add-only first implementation boundary:
    triple-oriented rule execution, optional derivation logging, and warm-start
    over an existing context. User-facing proof reconstruction is layered on top
    of derivation records rather than being the engine's execution format.

    The engine also enforces RDF 1.1 triple well-formedness for both stated and
    inferred triples. Literal subjects and non-IRI predicates never enter
    working memory or derived outputs. Callers can choose fail-fast or
    warning-and-skip behavior via ``literal_subject_policy`` and
    ``predicate_term_policy`` in the engine context data.
    """

    context_data: ContextData
    rules: Sequence[Rule]
    terminals: tuple[TerminalNode, ...]
    known_triples: set[Triple]
    materialized_triples: set[Triple]
    matcher: NetworkMatcher
    derivation_logger: DerivationLogger | None
    callbacks: dict[str, CallbackHook]
    callback_recorder: Any
    tms: TMSController
    working_memory: WorkingMemory
    literal_subject_policy: LiteralSubjectPolicy
    predicate_term_policy: PredicateTermPolicy
    _bootstrap_completed: bool

    def __init__(self, context_data: ContextData, rules: Iterable[Rule]) -> None:
        self.context_data = context_data
        self.rules = tuple(rules)
        compiled_rules = tuple(RuleCompiler.compile_rule(rule) for rule in self.rules)
        builder = NetworkBuilder()
        self.terminals = builder.build_rules(compiled_rules)
        builtins = self.context_data.get("builtins", {})
        user_predicates = builtins.get("predicates", {})
        predicates = {**DEFAULT_PREDICATE_BUILTINS, **user_predicates}
        self.callbacks = builtins.get("callbacks", {})
        self.matcher = NetworkMatcher(builder.registry, predicates=predicates)
        self.known_triples = set()
        self.materialized_triples = set()
        self.derivation_logger = self.context_data.get("derivation_logger")
        self.callback_recorder = self.context_data.get("callback_recorder")
        # Configure RDF term-type enforcement; default to strict error mode.
        self.literal_subject_policy = cast(
            LiteralSubjectPolicy,
            self.context_data.get("literal_subject_policy", "error"),
        )
        self.predicate_term_policy = cast(
            PredicateTermPolicy,
            self.context_data.get("predicate_term_policy", "error"),
        )
        self.tms = TMSController()
        self.working_memory = self.tms.working_memory
        self._bootstrap_completed = False

    def close(self) -> None:
        self.known_triples.clear()
        self.materialized_triples.clear()
        self.tms.clear()

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

    def _triple_is_permitted(
        self,
        triple: Triple,
        *,
        source: Literal["stated", "inferred"] | None = None,
        rule_id: Any = None,
        depth: int | None = None,
        pattern: tuple[Node | Variable, Node | Variable, Node | Variable] | None = None,
        bindings: Mapping[str, Node] | None = None,
        premises: tuple[Triple, ...] | None = None,
    ) -> bool:
        """Enforce RDF 1.1 term-type constraints on asserted triples.

        The RDF 1.1 Concepts and Abstract Syntax specification requires that
        subjects are IRIs or blank nodes and predicates are IRIs:
        https://www.w3.org/TR/rdf11-concepts/#section-triples

        This helper enforces those constraints according to the configured
        literal_subject_policy and predicate_term_policy. It returns True if
        the triple is permitted for use in the RETE working memory and as an
        inferred triple, and False if the triple should be ignored (warning
        mode). In error mode, it raises one of the dedicated FatalRuleError
        subclasses.

        Optional ``source`` / rule fields are included in raised exception
        messages and on :class:`RDFTermConstraintError` for debugging.
        """

        diag_kwargs = {
            "triple": triple,
            "source": source,
            "rule_id": rule_id,
            "depth": depth,
            "pattern": pattern,
            "bindings": bindings,
            "premises": premises,
        }
        diag_for_format = {
            "source": source,
            "rule_id": rule_id,
            "depth": depth,
            "pattern": pattern,
            "bindings": bindings,
            "premises": premises,
        }

        subject, predicate, _ = triple

        # Literal subjects are never allowed in RDF triples.
        if isinstance(subject, RDFLiteral):
            message = (
                "Attempted to assert a triple whose subject is a literal, which "
                "is disallowed by the RDF 1.1 data model; see "
                f"{_RDF_TRIPLES_SPEC_URL}"
            )
            detail = _format_term_constraint_diagnostics(triple, **diag_for_format)
            full_message = f"{message}\n{detail}"
            if self.literal_subject_policy == "error":
                raise LiteralAsSubjectError(full_message, **diag_kwargs)
            warnings.warn(full_message, LiteralAsSubjectWarning, stacklevel=3)
            return False

        # Predicates MUST be IRIs; they MUST NOT be blank nodes or literals.
        if not isinstance(predicate, URIRef):
            if isinstance(predicate, BNode):
                message = (
                    "Attempted to assert a triple whose predicate is a blank node, "
                    "which is disallowed by the RDF 1.1 data model; see "
                    f"{_RDF_TRIPLES_SPEC_URL}"
                )
                detail = _format_term_constraint_diagnostics(triple, **diag_for_format)
                full_message = f"{message}\n{detail}"
                if self.predicate_term_policy == "error":
                    raise BlankNodePredicateError(full_message, **diag_kwargs)
                warnings.warn(full_message, BlankNodePredicateWarning, stacklevel=3)
                return False

            if isinstance(predicate, RDFLiteral):
                message = (
                    "Attempted to assert a triple whose predicate is a literal, "
                    "which is disallowed by the RDF 1.1 data model; see "
                    f"{_RDF_TRIPLES_SPEC_URL}"
                )
                detail = _format_term_constraint_diagnostics(triple, **diag_for_format)
                full_message = f"{message}\n{detail}"
                if self.predicate_term_policy == "error":
                    raise LiteralPredicateError(full_message, **diag_kwargs)
                warnings.warn(full_message, LiteralPredicateWarning, stacklevel=3)
                return False

            # Any other non-URIRef predicate is also disallowed by the RDF model.
            message = (
                "Attempted to assert a triple whose predicate is not an IRI, "
                "which is disallowed by the RDF 1.1 data model; see "
                f"{_RDF_TRIPLES_SPEC_URL}"
            )
            detail = _format_term_constraint_diagnostics(triple, **diag_for_format)
            full_message = f"{message}\n{detail}"
            if self.predicate_term_policy == "error":
                raise LiteralPredicateError(full_message, **diag_kwargs)
            warnings.warn(full_message, LiteralPredicateWarning, stacklevel=3)
            return False

        return True

    def add_triples(self, triples: Iterable[Triple]) -> set[Triple]:
        """Add stated triples, saturate inference, and return newly derived triples.

        Incoming triples are first checked against the engine's RDF 1.1 triple
        well-formedness policies. Triples rejected under those policies are
        either raised as errors or warned-and-skipped before they can enter
        working memory or derivation outputs.
        """
        # Filter incoming triples according to RDF term-type policies.
        raw_pending = {cast(Triple, triple) for triple in triples}
        pending: set[Triple] = set()
        for triple in raw_pending:
            if self._triple_is_permitted(triple, source="stated"):
                pending.add(triple)

        if not pending:
            return set()

        self.tms.register_stated(pending)
        self.known_triples.update(pending)
        self.materialized_triples.update(pending)
        return self._saturate_from_working_memory()

    def _saturate_from_working_memory(self) -> set[Triple]:
        """Run agenda iterations to fixed point and return non-silent conclusions."""
        newly_materialized: set[Triple] = set()
        context = self.context_data.get("context")

        while True:
            try:
                actions = self.matcher.match_terminals(
                    self.terminals, self.working_memory.facts()
                )
                agenda = Agenda(actions)
            except Exception as exc:  # pragma: no cover - defensive wrapping
                if isinstance(exc, FatalRuleError):
                    raise
                raise FatalRuleError(str(exc)) from exc

            iteration_new: set[Triple] = set()
            iteration_materialized: set[Triple] = set()
            for action in agenda:
                action_loggable: list[Triple] = []
                for production in action.productions:
                    pattern = (
                        production.pattern.subject,
                        production.pattern.predicate,
                        production.pattern.object,
                    )
                    triple = self._instantiate_triple(pattern, action.bindings)
                    premise_triples = tuple(fact.triple for fact in action.premises)
                    if not self._triple_is_permitted(
                        triple,
                        source="inferred",
                        rule_id=action.rule_id,
                        depth=action.depth,
                        pattern=pattern,
                        bindings=action.bindings,
                        premises=premise_triples,
                    ):
                        continue
                    self.tms.record_derivation(
                        triple,
                        rule_id=action.rule_id,
                        premises=action.premises,
                        bindings=action.bindings,
                        depth=action.depth,
                    )
                    is_new_fact = (
                        triple not in self.known_triples and triple not in iteration_new
                    )
                    if is_new_fact:
                        iteration_new.add(triple)
                    should_materialize = (
                        not action.silent
                        and triple not in self.materialized_triples
                        and triple not in iteration_materialized
                    )
                    if should_materialize:
                        iteration_materialized.add(triple)
                    if (
                        is_new_fact or should_materialize
                    ) and triple not in action_loggable:
                        action_loggable.append(triple)

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
                    and len(action_loggable) > 0
                ):
                    self.derivation_logger.record(
                        DerivationRecord(
                            context=context,
                            conclusions=[
                                TripleFact(context=context, triple=triple)
                                for triple in action_loggable
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
                            silent=action.silent,
                        )
                    )

            self.known_triples.update(iteration_new)
            self.materialized_triples.update(iteration_materialized)
            newly_materialized.update(iteration_materialized)
            if not iteration_new:
                break

        return newly_materialized

    def retract_triples(self, triple: Triple) -> None:
        raise NotImplementedError("RETEEngine.retract_triple is not implemented")

    def _run_bootstrap_rules(self) -> set[Triple]:
        """Execute zero-precondition rules once for this engine context."""
        if self._bootstrap_completed:
            return set()
        self._bootstrap_completed = True
        return self._saturate_from_working_memory()

    def warmup(self, existing_triples: Iterable[Triple]) -> set[Triple]:
        """Warm the engine from existing triples and return engine-managed deductions."""
        bootstrap_inferences = self._run_bootstrap_rules()
        warmup_inferences = self.add_triples(existing_triples)
        return warmup_inferences.union(bootstrap_inferences)


class RETEEngineFactory:
    """Factory for per-context engine instances and contextual hook registries.

    The factory passes context-template values through to each engine instance,
    including optional RDF triple well-formedness policies such as
    ``literal_subject_policy`` and ``predicate_term_policy``.
    """

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
