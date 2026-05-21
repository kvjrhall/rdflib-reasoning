"""RETE engine facade for per-context triple entailment and truth maintenance."""

import warnings
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from rdflib.namespace import OWL, RDF
from rdflib.term import BNode, Node, URIRef, Variable
from rdflib.term import Literal as RDFLiteral
from rdflib_reasoning.axiom.common import ContextIdentifier, Triple

from .builtins import DEFAULT_PREDICATE_BUILTINS, Builtins, CallbackHook, RuleContext
from .derivation import (
    ContradictionRecorder,
    DerivationLogger,
)
from .proof import ContradictionRecord, DerivationRecord, TripleFact, VariableBinding
from .rete import (
    Agenda,
    NetworkBuilder,
    NetworkMatcher,
    RuleCompiler,
    TerminalNode,
    TMSController,
    WorkingMemory,
)
from .rete_errors import (
    RDF_TRIPLES_SPEC_URL,
    BlankNodePredicateError,
    BlankNodePredicateWarning,
    FatalRuleError,
    LiteralAsSubjectError,
    LiteralAsSubjectWarning,
    LiteralPredicateError,
    LiteralPredicateWarning,
    format_term_constraint_diagnostics,
)
from .rules import Rule

LiteralSubjectPolicy = Literal["error", "warning"]
PredicateTermPolicy = Literal["error", "warning"]


@dataclass
class EngineCallbackContext(RuleContext):
    """Read-only callback context for one fired rule activation."""

    context: ContextIdentifier | None
    rule_id: Any
    bindings: Mapping[str, Node]
    premises: tuple[Triple, ...]
    depth: int
    _events: list[Any] = field(default_factory=list)
    # _recorder: Any = None

    def record(self, event: Any) -> None:
        """Append one observational callback event to this activation context."""
        self._events.append(event)
        # if self._recorder is not None:
        #     self._recorder.record(event)


@dataclass(frozen=True, slots=True)
class RETEEngineConfig:
    """Explicit configuration for one RETE engine context."""

    context: ContextIdentifier
    builtins: Builtins
    derivation_logger: DerivationLogger
    contradiction_recorder: ContradictionRecorder
    # callback_recorder: object | None
    literal_subject_policy: LiteralSubjectPolicy
    predicate_term_policy: PredicateTermPolicy


class RETEEngine:
    """Public engine facade for fixed-point triple entailment within one context.

    The facade represents the direct implementation boundary: triple-oriented
    rule execution, dependency-aware retraction, optional derivation logging,
    and warm-start over an existing context. User-facing proof reconstruction is
    layered on top of derivation records rather than being the engine's
    execution format.

    The engine also enforces RDF 1.1 triple well-formedness for both stated and
    inferred triples. Literal subjects and non-IRI predicates never enter
    working memory or derived outputs. Callers can choose fail-fast or
    warning-and-skip behavior via ``literal_subject_policy`` and
    ``predicate_term_policy`` in the engine config.
    """

    config: RETEEngineConfig
    rules: Sequence[Rule]
    terminals: tuple[TerminalNode, ...]
    known_triples: set[Triple]
    materialized_triples: set[Triple]
    matcher: NetworkMatcher
    derivation_logger: DerivationLogger
    contradiction_recorder: ContradictionRecorder
    callbacks: Mapping[str, CallbackHook]
    # callback_recorder: Any
    tms: TMSController
    working_memory: WorkingMemory
    literal_subject_policy: LiteralSubjectPolicy
    predicate_term_policy: PredicateTermPolicy
    _bootstrap_completed: bool
    _contradiction_sequence: int

    def __init__(self, config: RETEEngineConfig, rules: Iterable[Rule]) -> None:
        """Compile ``rules`` and initialize working memory for ``config.context``."""
        self.config = config
        self.rules = tuple(rules)
        compiled_rules = tuple(RuleCompiler.compile_rule(rule) for rule in self.rules)
        builder = NetworkBuilder()
        self.terminals = builder.build_rules(compiled_rules)
        user_predicates = self.config.builtins.predicates
        predicates = {**DEFAULT_PREDICATE_BUILTINS, **user_predicates}
        self.callbacks = self.config.builtins.callbacks
        self.matcher = NetworkMatcher(builder.registry, predicates=predicates)
        self.known_triples = set()
        self.materialized_triples = set()
        self.derivation_logger = self.config.derivation_logger
        self.contradiction_recorder = self.config.contradiction_recorder
        # self.callback_recorder = self.config.callback_recorder
        self.literal_subject_policy = self.config.literal_subject_policy
        self.predicate_term_policy = self.config.predicate_term_policy
        self.tms = TMSController()
        self.working_memory = self.tms.working_memory
        self._bootstrap_completed = False
        self._contradiction_sequence = 0

    def close(self) -> None:
        """Clear working memory, tracked triples, and attached recorders for this context."""
        self.known_triples.clear()
        self.materialized_triples.clear()
        self.tms.clear()
        self.contradiction_recorder.clear()
        self.derivation_logger.clear()
        self._contradiction_sequence = 0

    def next_contradiction_sequence(self) -> int:
        """Return the next monotonic contradiction sequence id."""
        self._contradiction_sequence += 1
        return self._contradiction_sequence

    def contradiction_records(
        self, *, context: ContextIdentifier | None = None
    ) -> tuple[ContradictionRecord, ...]:
        """Return contradiction records, optionally filtered by context."""
        records = tuple(self.contradiction_recorder.iter_records())
        if context is None:
            return records
        return tuple(record for record in records if record.context == context)

    def clear_contradiction_records(self) -> None:
        """Clear contradiction records and reset sequence numbering."""
        self.contradiction_recorder.clear()
        self._contradiction_sequence = 0

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
                f"{RDF_TRIPLES_SPEC_URL}"
            )
            detail = format_term_constraint_diagnostics(triple, **diag_for_format)
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
                    f"{RDF_TRIPLES_SPEC_URL}"
                )
                detail = format_term_constraint_diagnostics(triple, **diag_for_format)
                full_message = f"{message}\n{detail}"
                if self.predicate_term_policy == "error":
                    raise BlankNodePredicateError(full_message, **diag_kwargs)
                warnings.warn(full_message, BlankNodePredicateWarning, stacklevel=3)
                return False

            if isinstance(predicate, RDFLiteral):
                message = (
                    "Attempted to assert a triple whose predicate is a literal, "
                    "which is disallowed by the RDF 1.1 data model; see "
                    f"{RDF_TRIPLES_SPEC_URL}"
                )
                detail = format_term_constraint_diagnostics(triple, **diag_for_format)
                full_message = f"{message}\n{detail}"
                if self.predicate_term_policy == "error":
                    raise LiteralPredicateError(full_message, **diag_kwargs)
                warnings.warn(full_message, LiteralPredicateWarning, stacklevel=3)
                return False

            # Any other non-URIRef predicate is also disallowed by the RDF model.
            message = (
                "Attempted to assert a triple whose predicate is not an IRI, "
                "which is disallowed by the RDF 1.1 data model; see "
                f"{RDF_TRIPLES_SPEC_URL}"
            )
            detail = format_term_constraint_diagnostics(triple, **diag_for_format)
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

        Per DR-004, this method is idempotent for triples the engine already
        knows. Triples already present in ``known_triples`` are skipped
        before ``register_stated`` runs so that materialization round-trips
        through the store dispatcher do not retroactively promote derived
        facts to stated facts.
        """
        # Filter incoming triples according to RDF term-type policies.
        raw_pending = {cast(Triple, triple) for triple in triples}
        pending: set[Triple] = set()
        for triple in raw_pending:
            if self._triple_is_permitted(triple, source="stated"):
                pending.add(triple)

        if not pending:
            return set()

        fresh = pending - self.known_triples
        if not fresh:
            return set()

        self.tms.register_stated(fresh)
        self.known_triples.update(fresh)
        self.materialized_triples.update(fresh)
        return self._saturate_from_working_memory()

    def _saturate_from_working_memory(
        self, *, materialize: bool = True, bootstrap_phase: bool = False
    ) -> set[Triple]:
        """Run agenda iterations to fixed point and return visible conclusions."""
        newly_materialized: set[Triple] = set()
        context = self.config.context

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
                if action.bootstrap and not bootstrap_phase:
                    continue
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
                        materialize
                        and not action.silent
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
                    # _recorder=self.callback_recorder,
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

                if context is not None:
                    premise_facts = [
                        TripleFact(context=context, triple=fact.triple)
                        for fact in action.premises
                    ]
                    binding_facts = [
                        VariableBinding(name=name, value=value)
                        for name, value in sorted(action.bindings.items())
                    ]
                    for contradiction in action.contradictions:
                        resolved = self._resolve_callback_arguments(
                            contradiction.arguments,
                            action.bindings,
                        )
                        witness: TripleFact | None = None
                        if len(resolved) >= 3:
                            maybe_witness = cast(
                                Triple,
                                (resolved[0], resolved[1], resolved[2]),
                            )
                            witness = TripleFact(context=context, triple=maybe_witness)
                        elif len(resolved) == 1:
                            candidate = cast(Triple, action.premises[0].triple)
                            witness = TripleFact(context=context, triple=candidate)
                        # Prefer explicit owl:Nothing witness when present in premises.
                        for premise in premise_facts:
                            if (
                                premise.triple[1] == RDF.type
                                and premise.triple[2] == OWL.Nothing
                            ):
                                witness = premise
                                break

                        self.contradiction_recorder.record(
                            ContradictionRecord(
                                context=context,
                                rule_id=action.rule_id,
                                premises=premise_facts,
                                bindings=binding_facts,
                                sequence_id=self.next_contradiction_sequence(),
                                witness=witness,
                                category=contradiction.category,
                                detail=contradiction.detail,
                            )
                        )

                if (
                    context is not None
                    and self.derivation_logger is not None
                    and len(action_loggable) > 0
                ):
                    effective_silent = action.silent or bootstrap_phase
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
                            silent=effective_silent,
                            bootstrap=bootstrap_phase,
                        )
                    )

            self.known_triples.update(iteration_new)
            self.materialized_triples.update(iteration_materialized)
            newly_materialized.update(iteration_materialized)
            if not iteration_new:
                break

        return newly_materialized

    def retract_triples(self, triples: Iterable[Triple]) -> set[Triple]:
        """Retract triples; return all triples that left the logical closure.

        For each input triple the engine looks up the working-memory fact:

        - If the fact is absent, the input is skipped (idempotent for
          already-absent triples; a second call with the same input is a
          no-op).
        - If the fact is stated, the engine delegates to
          ``TMSController.retract_triple`` and consumes the resulting
          ``RetractionOutcome``. Stated facts that also have derived
          justifications have only the ``stated`` flag cleared; they remain
          in working memory and are NOT included in the returned set.
        - If the fact is derived only, the engine leaves working memory
          unchanged and does NOT include the triple in the returned set.
          Callers that received this triple from a store-side removal event
          are expected to re-add it to the backing store under the policy
          documented in DR-025.

        After all TMS calls finish, the engine evicts persisted partial
        matches that referenced the removed facts so that subsequent join
        passes do not produce activations grounded in retracted facts.
        ``known_triples`` and ``materialized_triples`` are updated so they
        no longer include triples that left the logical closure; triples
        whose working-memory fact survived (stated-and-derived clearings,
        derived-only) remain in both sets.

        Returns the union of (a) input triples whose working-memory fact
        was actually removed and (b) cascade consequents removed by
        Mark-Verify-Sweep. Idempotence is the symmetric counterpart of the
        DR-004 requirement that ``add_triples`` is idempotent for
        already-known triples; ``BatchDispatcher`` relies on this symmetry
        to converge cascade events without an explicit reentrancy guard.
        """
        inputs = {cast(Triple, triple) for triple in triples}
        if not inputs:
            return set()

        cascade: set[Triple] = set()
        removed_fact_ids: set[str] = set()

        for triple in inputs:
            fact = self.working_memory.get_fact(triple)
            if fact is None:
                continue
            if not fact.stated:
                continue
            outcome = self.tms.retract_triple(triple)
            cascade.update(outcome.removed_triples)
            removed_fact_ids.update(outcome.removed_fact_ids)

        if removed_fact_ids:
            self.matcher.registry.evict_partial_matches_referencing(
                frozenset(removed_fact_ids)
            )

        if cascade:
            self.known_triples.difference_update(cascade)
            self.materialized_triples.difference_update(cascade)

        return cascade

    def _run_bootstrap_rules(self) -> None:
        """Execute zero-precondition rules once for this engine context.

        Bootstrap is an engine-internal initialization phase. Its derived
        closure seeds working memory and derivation logs, but it does not
        expose produced triples as materialized warmup output.
        """
        if self._bootstrap_completed:
            return
        self._bootstrap_completed = True
        self._saturate_from_working_memory(materialize=False, bootstrap_phase=True)

    def warmup(self, existing_triples: Iterable[Triple]) -> set[Triple]:
        """Warm the engine from existing triples and return engine-managed deductions."""
        self._run_bootstrap_rules()
        return self.add_triples(existing_triples)
