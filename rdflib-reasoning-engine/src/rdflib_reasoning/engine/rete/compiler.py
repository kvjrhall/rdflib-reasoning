from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from rdflib.namespace import RDF
from rdflib.term import Node, Variable

from ..proof import RuleId
from ..rules import (
    CallbackConsequent,
    PatternTerm,
    PredicateCondition,
    Rule,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from .consequents import CallbackSchedule, TripleProduction


class AlphaConstraint(BaseModel):
    """A constant-position filter used by the alpha side of the network."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    position: Literal["subject", "predicate", "object"]
    value: Node


class CompiledTripleCondition(BaseModel):
    """Normalized triple body condition with explicit alpha constraints and binders."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_index: int
    pattern: TriplePattern
    constraints: tuple[AlphaConstraint, ...] = Field(default_factory=tuple)
    bound_variables: tuple[str, ...] = Field(default_factory=tuple)


class CompiledPredicateCondition(BaseModel):
    """Normalized predicate condition with explicit binding dependencies."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_index: int
    predicate: str
    arguments: tuple[Node, ...] = Field(default_factory=tuple)
    required_variables: tuple[str, ...] = Field(default_factory=tuple)


class CompiledRule(BaseModel):
    """Compiler output consumed by RETE network construction."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    rule_id: RuleId
    salience: int = 0
    silent: bool = False
    triple_conditions: tuple[CompiledTripleCondition, ...] = Field(
        default_factory=tuple
    )
    predicate_conditions: tuple[CompiledPredicateCondition, ...] = Field(
        default_factory=tuple
    )
    productions: tuple[TripleProduction, ...] = Field(default_factory=tuple)
    callbacks: tuple[CallbackSchedule, ...] = Field(default_factory=tuple)
    variables: tuple[str, ...] = Field(default_factory=tuple)


class JoinOptimizer:
    """
    Construction-time utility for ordering joins in conjunctive rule bodies.
    """

    @staticmethod
    def order_triple_conditions(
        conditions: tuple[CompiledTripleCondition, ...],
    ) -> tuple[CompiledTripleCondition, ...]:
        """Order triple joins using simple selectivity heuristics.

        More constants are better. Constant predicates are preferred, and
        constants other than `rdf:type` are treated as more selective.
        """

        def score(condition: CompiledTripleCondition) -> tuple[int, int, int, int]:
            constant_positions = {
                constraint.position for constraint in condition.constraints
            }
            constant_count = len(constant_positions)
            predicate_constraint = next(
                (
                    constraint
                    for constraint in condition.constraints
                    if constraint.position == "predicate"
                ),
                None,
            )
            has_constant_predicate = 1 if predicate_constraint is not None else 0
            non_type_predicate_bonus = (
                1
                if predicate_constraint is not None
                and predicate_constraint.value != RDF.type
                else 0
            )
            variable_bonus = -len(condition.bound_variables)
            return (
                constant_count,
                has_constant_predicate,
                non_type_predicate_bonus,
                variable_bonus,
            )

        return tuple(
            sorted(
                conditions,
                key=lambda condition: score(condition),
                reverse=True,
            )
        )


class RuleCompiler:
    """
    Entry point for translating public rule definitions into RETE IR.

    This remains a programmatic rule-definition boundary; no text syntax is
    implied by this scaffold.
    """

    @staticmethod
    def _normalize_term(term: PatternTerm) -> Node:
        return term

    @staticmethod
    def _required_variables(terms: tuple[PatternTerm, ...]) -> tuple[str, ...]:
        return tuple(str(term) for term in terms if isinstance(term, Variable))

    @classmethod
    def _compile_triple_condition(
        cls,
        condition: TripleCondition,
        source_index: int,
    ) -> CompiledTripleCondition:
        constraints: list[AlphaConstraint] = []
        variables: list[str] = []
        for position in ("subject", "predicate", "object"):
            value = getattr(condition.pattern, position)
            if isinstance(value, Variable):
                variables.append(str(value))
            else:
                constraints.append(AlphaConstraint(position=position, value=value))
        return CompiledTripleCondition(
            source_index=source_index,
            pattern=condition.pattern,
            constraints=tuple(constraints),
            bound_variables=tuple(variables),
        )

    @classmethod
    def _compile_predicate_condition(
        cls,
        condition: PredicateCondition,
        source_index: int,
        available_bindings: set[str],
    ) -> CompiledPredicateCondition:
        required_variables = cls._required_variables(condition.arguments)
        missing = tuple(
            name for name in required_variables if name not in available_bindings
        )
        if missing:
            raise ValueError(
                "Predicate conditions MUST NOT introduce new bindings; "
                f"missing variables for `{condition.predicate}`: {missing}"
            )
        return CompiledPredicateCondition(
            source_index=source_index,
            predicate=condition.predicate,
            arguments=tuple(cls._normalize_term(arg) for arg in condition.arguments),
            required_variables=required_variables,
        )

    @classmethod
    def compile_rule(cls, rule: Rule) -> CompiledRule:
        triple_conditions = tuple(
            cls._compile_triple_condition(condition, idx)
            for idx, condition in enumerate(rule.body)
            if isinstance(condition, TripleCondition)
        )
        ordered_triples = JoinOptimizer.order_triple_conditions(triple_conditions)
        available_bindings = {
            variable
            for condition in ordered_triples
            for variable in condition.bound_variables
        }
        predicate_conditions = tuple(
            cls._compile_predicate_condition(condition, idx, available_bindings)
            for idx, condition in enumerate(rule.body)
            if isinstance(condition, PredicateCondition)
        )

        productions = tuple(
            TripleProduction(
                rule_id=rule.id,
                pattern=consequent.pattern,
                required_variables=cls._required_variables(
                    (
                        consequent.pattern.subject,
                        consequent.pattern.predicate,
                        consequent.pattern.object,
                    )
                ),
            )
            for consequent in rule.head
            if isinstance(consequent, TripleConsequent)
        )
        callbacks = tuple(
            CallbackSchedule(
                callback=consequent.callback,
                arguments=tuple(
                    cls._normalize_term(arg) for arg in consequent.arguments
                ),
                required_variables=cls._required_variables(consequent.arguments),
            )
            for consequent in rule.head
            if isinstance(consequent, CallbackConsequent)
        )
        variables = tuple(sorted(available_bindings))

        return CompiledRule(
            rule_id=rule.id,
            salience=rule.salience,
            silent=rule.silent,
            triple_conditions=ordered_triples,
            predicate_conditions=predicate_conditions,
            productions=productions,
            callbacks=callbacks,
            variables=variables,
        )
