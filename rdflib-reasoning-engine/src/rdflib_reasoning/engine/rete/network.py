from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field
from rdflib.term import Node, Variable
from rdflib_reasoning.axiom.common import Triple

from ..rules import PredicateHook, RuleContext
from .compiler import (
    AlphaConstraint,
    CompiledPredicateCondition,
    CompiledRule,
    CompiledTripleCondition,
)
from .consequents import ActionInstance
from .facts import Fact, PartialMatch, fact_id_for_triple


class AlphaNode(BaseModel):
    """
    First layer of the RETE network.
    Filters individual facts based on literal constant constraints before any
    join work occurs.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    key: str = Field(..., description="Canonical node key for structural sharing.")
    condition: CompiledTripleCondition = Field(
        ..., description="Compiled triple condition handled by this alpha node."
    )
    constraints: tuple[AlphaConstraint, ...] = Field(
        default_factory=tuple,
        description="Constant-position constraints enforced by this node.",
    )


class PredicateNode(BaseModel):
    """
    Specialized alpha node that wraps read-only predicate callables.

    Predicate nodes represent body-side evaluation only; they are not callback
    hooks and they do not emit logical consequences directly.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    key: str = Field(..., description="Canonical node key for structural sharing.")
    condition: CompiledPredicateCondition = Field(
        ..., description="Compiled predicate condition handled by this node."
    )
    required_variables: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Variables that must be bound before predicate evaluation.",
    )


class BetaNode(BaseModel):
    """
    Join node maintaining partial-match memory for conjunctive rule bodies.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    key: str = Field(..., description="Canonical node key for structural sharing.")
    left_key: str = Field(..., description="Upstream left input key.")
    right_key: str = Field(..., description="Upstream right input key.")
    shared_variables: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Variables used to join left and right inputs.",
    )


class TerminalNode(BaseModel):
    """
    Leaf node that schedules engine-managed logical production and optional
    observational callbacks from one completed match.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    key: str = Field(..., description="Canonical node key for this terminal.")
    rule: CompiledRule = Field(
        ..., description="Compiled rule whose consequents this terminal schedules."
    )
    input_keys: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Upstream alpha, beta, and predicate node keys feeding the terminal.",
    )


class NodeRegistry(BaseModel):
    """
    Canonicalizing store for structurally shared network nodes.

    Node sharing is part of the intended RETE optimization strategy and should
    remain independent from proof reconstruction concerns.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    alpha_nodes: dict[str, AlphaNode] = Field(default_factory=dict)
    predicate_nodes: dict[str, PredicateNode] = Field(default_factory=dict)
    beta_nodes: dict[str, BetaNode] = Field(default_factory=dict)
    terminal_nodes: dict[str, TerminalNode] = Field(default_factory=dict)
    alpha_memory: dict[str, dict[str, PartialMatch]] = Field(default_factory=dict)
    beta_memory: dict[str, dict[str, PartialMatch]] = Field(default_factory=dict)

    def get_or_create_alpha(self, node: AlphaNode) -> AlphaNode:
        created = self.alpha_nodes.setdefault(node.key, node)
        self.alpha_memory.setdefault(node.key, {})
        return created

    def get_or_create_predicate(self, node: PredicateNode) -> PredicateNode:
        return self.predicate_nodes.setdefault(node.key, node)

    def get_or_create_beta(self, node: BetaNode) -> BetaNode:
        created = self.beta_nodes.setdefault(node.key, node)
        self.beta_memory.setdefault(node.key, {})
        return created

    def add_terminal(self, node: TerminalNode) -> TerminalNode:
        self.terminal_nodes[node.key] = node
        return node

    def evict_partial_matches_referencing(self, fact_ids: frozenset[str]) -> None:
        """Drop persisted partial matches that reference any of these fact ids.

        Network alpha and beta memories accumulate ``PartialMatch`` records
        across calls to ``NetworkMatcher.match_terminals``. When the engine
        retracts triples, the corresponding ``Fact`` objects leave working
        memory; the persisted partial matches must also be evicted so that
        subsequent join passes do not produce activations grounded in
        removed facts.
        """
        if not fact_ids:
            return
        for memory in (self.alpha_memory, self.beta_memory):
            for matches in memory.values():
                stale_keys = [
                    match_key
                    for match_key, match in matches.items()
                    if any(fact.id in fact_ids for fact in match.facts)
                ]
                for match_key in stale_keys:
                    del matches[match_key]


class NetworkBuilder:
    """
    Orchestrator for RETE network assembly from compiled rule representations.

    The builder turns compiled rules into canonical alpha, beta, and predicate
    nodes plus per-rule terminal nodes using a left-deep join assembly.
    """

    registry: NodeRegistry

    def __init__(self, registry: NodeRegistry | None = None) -> None:
        self.registry = NodeRegistry() if registry is None else registry

    @staticmethod
    def _alpha_key(condition: CompiledTripleCondition) -> str:
        constraint_parts = ",".join(
            f"{constraint.position}={constraint.value.n3()}"
            for constraint in condition.constraints
        )
        variable_parts = ",".join(condition.bound_variables)
        return f"alpha:{constraint_parts}|vars={variable_parts}"

    @staticmethod
    def _predicate_key(condition: CompiledPredicateCondition) -> str:
        argument_parts = ",".join(
            f"?{argument}" if isinstance(argument, Variable) else argument.n3()
            for argument in condition.arguments
        )
        return f"predicate:{condition.predicate}:{argument_parts}"

    @staticmethod
    def _terminal_key(rule: CompiledRule) -> str:
        return f"terminal:{rule.rule_id.ruleset}:{rule.rule_id.rule_id}"

    @staticmethod
    def _beta_key(
        left_key: str, right_key: str, shared_variables: tuple[str, ...]
    ) -> str:
        shared = ",".join(shared_variables)
        return f"beta:{left_key}+{right_key}|shared={shared}"

    def _build_join_chain(self, rule: CompiledRule) -> tuple[str | None, set[str]]:
        current_key: str | None = None
        current_variables: set[str] = set()

        for condition in rule.triple_conditions:
            alpha = self.registry.get_or_create_alpha(
                AlphaNode(
                    key=self._alpha_key(condition),
                    condition=condition,
                    constraints=condition.constraints,
                )
            )
            condition_variables = set(condition.bound_variables)

            if current_key is None:
                current_key = alpha.key
                current_variables = set(condition_variables)
                continue

            shared_variables = tuple(sorted(current_variables & condition_variables))
            beta = self.registry.get_or_create_beta(
                BetaNode(
                    key=self._beta_key(current_key, alpha.key, shared_variables),
                    left_key=current_key,
                    right_key=alpha.key,
                    shared_variables=shared_variables,
                )
            )
            current_key = beta.key
            current_variables.update(condition_variables)

        return current_key, current_variables

    def build_rule(self, rule: CompiledRule) -> TerminalNode:
        input_keys: list[str] = []
        join_root, _ = self._build_join_chain(rule)
        if join_root is not None:
            input_keys.append(join_root)

        for condition in rule.predicate_conditions:
            predicate = self.registry.get_or_create_predicate(
                PredicateNode(
                    key=self._predicate_key(condition),
                    condition=condition,
                    required_variables=condition.required_variables,
                )
            )
            input_keys.append(predicate.key)

        terminal = TerminalNode(
            key=self._terminal_key(rule),
            rule=rule,
            input_keys=tuple(input_keys),
        )
        return self.registry.add_terminal(terminal)

    def build_rules(self, rules: tuple[CompiledRule, ...]) -> tuple[TerminalNode, ...]:
        return tuple(self.build_rule(rule) for rule in rules)


class MatcherContext(RuleContext):
    """Minimal read-only rule context for builtin predicate evaluation."""

    def __init__(self, terminal: TerminalNode) -> None:
        self.terminal = terminal


class NetworkMatcher:
    """Minimal matching pass over alpha, beta, predicate, and terminal nodes."""

    registry: NodeRegistry
    predicates: dict[str, PredicateHook]

    def __init__(
        self,
        registry: NodeRegistry,
        *,
        predicates: dict[str, PredicateHook] | None = None,
    ) -> None:
        self.registry = registry
        self.predicates = {} if predicates is None else predicates

    @staticmethod
    def _pattern_terms(
        condition: CompiledTripleCondition,
    ) -> tuple[object, object, object]:
        return (
            condition.pattern.subject,
            condition.pattern.predicate,
            condition.pattern.object,
        )

    @staticmethod
    def _fact_from_triple(triple: Triple) -> Fact:
        return Fact(id=fact_id_for_triple(triple), triple=triple)

    @staticmethod
    def _partial_match_key(match: PartialMatch) -> str:
        fact_ids = ",".join(fact.id for fact in match.facts)
        binding_parts = ",".join(
            f"{name}={value.n3()}" for name, value in sorted(match.bindings.items())
        )
        return f"facts={fact_ids}|bindings={binding_parts}|depth={match.depth}"

    def _store_matches(
        self,
        memory: dict[str, PartialMatch],
        matches: Iterable[PartialMatch],
    ) -> tuple[PartialMatch, ...]:
        new_matches: list[PartialMatch] = []
        for match in matches:
            match_key = self._partial_match_key(match)
            if match_key not in memory:
                memory[match_key] = match
                new_matches.append(match)
        return tuple(new_matches)

    def _match_alpha(
        self,
        node: AlphaNode,
        facts: tuple[Fact, ...],
    ) -> tuple[PartialMatch, ...]:
        matches: list[PartialMatch] = []
        pattern_terms = self._pattern_terms(node.condition)
        for fact in facts:
            triple = fact.triple
            bindings: dict[str, Node] = {}
            matched = True
            for pattern_term, triple_term in zip(pattern_terms, triple, strict=True):
                if isinstance(pattern_term, Variable):
                    variable_name = str(pattern_term)
                    existing = bindings.get(variable_name)
                    if existing is not None and existing != triple_term:
                        matched = False
                        break
                    bindings[variable_name] = triple_term
                elif pattern_term != triple_term:
                    matched = False
                    break
            if matched:
                matches.append(PartialMatch(facts=(fact,), bindings=bindings, depth=0))
        return self._store_matches(self.registry.alpha_memory[node.key], matches)

    @staticmethod
    def _bindings_compatible(
        left: dict[str, Node],
        right: dict[str, Node],
    ) -> bool:
        shared = set(left) & set(right)
        return all(left[name] == right[name] for name in shared)

    def _join_beta(
        self,
        node: BetaNode,
        partial_matches: dict[str, tuple[PartialMatch, ...]],
    ) -> tuple[PartialMatch, ...]:
        left_memory = self.registry.alpha_memory.get(
            node.left_key, self.registry.beta_memory.get(node.left_key, {})
        )
        right_memory = self.registry.alpha_memory.get(
            node.right_key, self.registry.beta_memory.get(node.right_key, {})
        )
        left_matches = partial_matches.get(node.left_key, ())
        right_matches = partial_matches.get(node.right_key, ())
        joined: list[PartialMatch] = []

        def join_pairs(
            new_left: Iterable[PartialMatch],
            all_right: Iterable[PartialMatch],
        ) -> None:
            for left in new_left:
                left_fact_ids = {fact.id for fact in left.facts}
                for right in all_right:
                    if any(fact.id in left_fact_ids for fact in right.facts):
                        continue
                    if not self._bindings_compatible(left.bindings, right.bindings):
                        continue
                    merged_bindings = {**left.bindings, **right.bindings}
                    merged_facts = left.facts + tuple(
                        fact for fact in right.facts if fact.id not in left_fact_ids
                    )
                    joined.append(
                        PartialMatch(
                            facts=merged_facts,
                            bindings=merged_bindings,
                            depth=max(left.depth, right.depth) + 1,
                        )
                    )

        join_pairs(left_matches, right_memory.values())
        join_pairs(left_memory.values(), right_matches)

        return self._store_matches(self.registry.beta_memory[node.key], joined)

    def _apply_predicate(
        self,
        node: PredicateNode,
        matches: tuple[PartialMatch, ...],
        *,
        terminal: TerminalNode,
    ) -> tuple[PartialMatch, ...]:
        hook = self.predicates.get(node.condition.predicate)
        if hook is None:
            raise KeyError(f"Unknown predicate hook `{node.condition.predicate}`")
        context = MatcherContext(terminal)
        filtered: list[PartialMatch] = []
        for match in matches:
            arguments: list[Node] = []
            for argument in node.condition.arguments:
                if isinstance(argument, Variable):
                    arguments.append(match.bindings[str(argument)])
                else:
                    arguments.append(argument)
            if hook.test(context, *arguments):
                filtered.append(match)
        return tuple(filtered)

    @staticmethod
    def _root_matches(
        terminal: TerminalNode,
        partial_matches: dict[str, tuple[PartialMatch, ...]],
    ) -> tuple[PartialMatch, ...]:
        root_key = terminal.input_keys[0] if terminal.input_keys else None
        if root_key is None:
            return (PartialMatch(facts=(), bindings={}, depth=0),)
        return partial_matches.get(root_key, ())

    def _actions_for_terminal(
        self,
        terminal: TerminalNode,
        partial_matches: dict[str, tuple[PartialMatch, ...]],
    ) -> tuple[ActionInstance, ...]:
        matches = self._root_matches(terminal, partial_matches)

        for key in terminal.input_keys[1:]:
            predicate_node = self.registry.predicate_nodes[key]
            matches = self._apply_predicate(predicate_node, matches, terminal=terminal)

        return tuple(
            ActionInstance(
                rule_id=terminal.rule.rule_id,
                bindings=match.bindings,
                premises=match.facts,
                depth=match.depth,
                salience=terminal.rule.salience,
                productions=terminal.rule.productions,
                callbacks=terminal.rule.callbacks,
                contradictions=terminal.rule.contradictions,
                silent=terminal.rule.silent,
                bootstrap=terminal.rule.bootstrap,
            )
            for match in matches
        )

    def match_terminal(
        self,
        terminal: TerminalNode,
        facts: Iterable[Fact | Triple],
    ) -> tuple[ActionInstance, ...]:
        normalized_facts = tuple(
            fact if isinstance(fact, Fact) else self._fact_from_triple(fact)
            for fact in facts
        )
        partial_matches: dict[str, tuple[PartialMatch, ...]] = {}

        for key, node in self.registry.alpha_nodes.items():
            partial_matches[key] = self._match_alpha(node, normalized_facts)

        for key, beta_node in self.registry.beta_nodes.items():
            partial_matches[key] = self._join_beta(beta_node, partial_matches)
        return self._actions_for_terminal(terminal, partial_matches)

    def alpha_memory_size(self, key: str) -> int:
        return len(self.registry.alpha_memory[key])

    def beta_memory_size(self, key: str) -> int:
        return len(self.registry.beta_memory[key])

    def match_terminals(
        self,
        terminals: Iterable[TerminalNode],
        facts: Iterable[Fact | Triple],
    ) -> tuple[ActionInstance, ...]:
        normalized_facts = tuple(
            fact if isinstance(fact, Fact) else self._fact_from_triple(fact)
            for fact in facts
        )
        partial_matches: dict[str, tuple[PartialMatch, ...]] = {}

        for key, node in self.registry.alpha_nodes.items():
            partial_matches[key] = self._match_alpha(node, normalized_facts)

        for key, beta_node in self.registry.beta_nodes.items():
            partial_matches[key] = self._join_beta(beta_node, partial_matches)

        actions: list[ActionInstance] = []
        for terminal in terminals:
            actions.extend(self._actions_for_terminal(terminal, partial_matches))
        return tuple(actions)
