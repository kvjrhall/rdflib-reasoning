from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import count
from typing import cast

from rdflib.namespace import NamespaceManager
from rdflib.term import Node

from .proof import (
    ContradictionClaim,
    DirectProof,
    ProofLeaf,
    ProofNode,
    ProofPayload,
    RuleApplication,
    StructuralClaim,
    TextClaim,
    TripleFact,
)
from .rules import (
    CallbackConsequent,
    PredicateCondition,
    Rule,
    RuleCondition,
    RuleConsequent,
    TripleCondition,
    TripleConsequent,
)
from .rulesets import PRODUCTION_RDFS_RULES


def build_rule_lookup(rules: Iterable[Rule]) -> dict[tuple[str, str], Rule]:
    """Map ``(ruleset, rule_id)`` to the :class:`~rdflib_reasoning.engine.rules.Rule`.

    Raises:
        ValueError: If two rules share the same ``(ruleset, rule_id)`` pair.
    """
    out: dict[tuple[str, str], Rule] = {}
    for rule in rules:
        key = (rule.id.ruleset, rule.id.rule_id)
        if key in out:
            msg = (
                f"Duplicate rule key {key!r}: "
                f"{out[key].id!r} conflicts with {rule.id!r}"
            )
            raise ValueError(msg)
        out[key] = rule
    return out


@dataclass(frozen=True)
class ProofRenderer:
    """Render canonical proof models as presentation-oriented text.

    ``rules`` should be the same rule tuple passed to :class:`~rdflib_reasoning.engine.api.RETEEngine`
    (or :class:`~rdflib_reasoning.engine.api.RETEEngineFactory`) when the proof
    was produced, so rule steps resolve to IF/THEN patterns. When omitted,
    :data:`~rdflib_reasoning.engine.rulesets.PRODUCTION_RDFS_RULES` is used.
    """

    namespace_manager: NamespaceManager | None = None
    rules: tuple[Rule, ...] | None = None
    _rule_lookup: dict[tuple[str, str], Rule] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        rules_source = PRODUCTION_RDFS_RULES if self.rules is None else self.rules
        object.__setattr__(self, "_rule_lookup", build_rule_lookup(rules_source))

    def render_markdown(self, proof: DirectProof) -> str:
        lines: list[str] = ["## Direct Proof", ""]
        lines.append(f"- Context: `{self._term_to_text(cast(Node, proof.context))}`")
        lines.append(f"- Goal: `{self._payload_to_text(proof.goal)}`")
        if proof.verdict is not None:
            lines.append(f"- Verdict: `{proof.verdict}`")
        if proof.notes:
            lines.append(f"- Notes: {proof.notes}")
        lines.extend(["", "### Steps", ""])
        lines.extend(self._render_node_markdown(proof.proof, depth=0))
        return "\n".join(lines)

    def render_mermaid(self, proof: DirectProof) -> str:
        ids = count(1)
        lines = ["flowchart TD"]
        goal_id = f"n{next(ids)}"
        _, root_claim_id = self._append_mermaid_node(proof.proof, lines, ids)
        lines.append(
            self._mermaid_node(goal_id, "goal", self._payload_to_text(proof.goal))
        )
        lines.append(f"{goal_id} -->|justified_by| {root_claim_id}")
        return "\n".join(lines)

    def _append_mermaid_node(
        self, node: ProofNode, lines: list[str], ids: count[int]
    ) -> tuple[str, str]:
        node_id = f"n{next(ids)}"
        if isinstance(node, ProofLeaf):
            lines.append(
                self._mermaid_node(node_id, "leaf", self._payload_to_text(node.claim))
            )
            return node_id, node_id

        lines.append(self._mermaid_node(node_id, "rule", self._rule_node_label(node)))
        first_conclusion_id: str | None = None
        for conclusion in node.conclusions:
            conclusion_id = f"n{next(ids)}"
            lines.append(
                self._mermaid_node(
                    conclusion_id, "conclusion", self._payload_to_text(conclusion)
                )
            )
            lines.append(f"{conclusion_id} -->|entailed_by| {node_id}")
            if first_conclusion_id is None:
                first_conclusion_id = conclusion_id
        for premise in node.premises:
            _, premise_claim_id = self._append_mermaid_node(premise, lines, ids)
            lines.append(f"{node_id} -->|had_premise| {premise_claim_id}")
        if first_conclusion_id is None:
            return node_id, node_id
        return node_id, first_conclusion_id

    def _render_node_markdown(self, node: ProofNode, *, depth: int) -> list[str]:
        indent = "  " * depth
        if isinstance(node, ProofLeaf):
            return [f"{indent}- Leaf: `{self._payload_to_text(node.claim)}`"]

        lines = [f"{indent}- Rule Application: `{self._rule_label(node)}`"]
        if node.conclusions:
            lines.append(f"{indent}  - Conclusions:")
            for conclusion in node.conclusions:
                lines.append(f"{indent}    - `{self._payload_to_text(conclusion)}`")
        if node.premises:
            lines.append(f"{indent}  - Premises:")
            for premise in node.premises:
                lines.extend(self._render_node_markdown(premise, depth=depth + 2))
        return lines

    def _rule_label(self, node: RuleApplication) -> str:
        if node.rule_id is not None:
            return f"{node.rule_id.ruleset}:{node.rule_id.rule_id}"
        if node.description is not None:
            return node.description.label
        return "unknown-rule"

    def _rule_node_label(self, node: RuleApplication) -> str:
        rule_label = self._rule_label(node)
        body_text = self._rule_body_text(node)
        head_text = self._rule_head_text(node)
        if body_text is None and head_text is None:
            return rule_label
        lines = [rule_label]
        if body_text is not None:
            lines.append(f"IF {body_text}")
        if head_text is not None:
            lines.append(f"THEN {head_text}")
        return "\n".join(lines)

    def _rule_body_text(self, node: RuleApplication) -> str | None:
        rule = self._resolve_rule(node)
        if rule is None or not rule.body:
            return None
        return " AND ".join(
            self._render_rule_condition(condition) for condition in rule.body
        )

    def _rule_head_text(self, node: RuleApplication) -> str | None:
        rule = self._resolve_rule(node)
        if rule is None or not rule.head:
            return None
        return " AND ".join(
            self._render_rule_consequent(consequent) for consequent in rule.head
        )

    def _resolve_rule(self, node: RuleApplication) -> Rule | None:
        if node.rule_id is None:
            return None
        return self._rule_lookup.get(
            (node.rule_id.ruleset, node.rule_id.rule_id),
        )

    def _render_rule_condition(self, condition: RuleCondition) -> str:
        if isinstance(condition, TripleCondition):
            pattern = condition.pattern
            s = self._term_to_text(cast(Node, pattern.subject))
            p = self._term_to_text(cast(Node, pattern.predicate))
            o = self._term_to_text(cast(Node, pattern.object))
            return f"({s}, {p}, {o})"
        if isinstance(condition, PredicateCondition):
            args = ", ".join(
                self._term_to_text(cast(Node, argument))
                for argument in condition.arguments
            )
            return f"{condition.predicate}({args})"
        return str(condition)

    def _render_rule_consequent(self, consequent: RuleConsequent) -> str:
        if isinstance(consequent, TripleConsequent):
            pattern = consequent.pattern
            s = self._term_to_text(cast(Node, pattern.subject))
            p = self._term_to_text(cast(Node, pattern.predicate))
            o = self._term_to_text(cast(Node, pattern.object))
            return f"({s}, {p}, {o})"
        if isinstance(consequent, CallbackConsequent):
            args = ", ".join(
                self._term_to_text(cast(Node, argument))
                for argument in consequent.arguments
            )
            return f"{consequent.callback}({args})"
        return str(consequent)

    def _payload_to_text(self, payload: ProofPayload) -> str:
        if isinstance(payload, TripleFact):
            s, p, o = payload.triple
            s_text, s_shortened = self._term_to_text_with_shortening(s)
            p_text, p_shortened = self._term_to_text_with_shortening(p)
            o_text, o_shortened = self._term_to_text_with_shortening(o)
            if s_shortened and p_shortened and o_shortened:
                nbsp = "\u00a0"
                return f"({s_text}{nbsp}{p_text}{nbsp}{o_text})"
            return f"({s_text}, {p_text}, {o_text})"
        if isinstance(payload, ContradictionClaim):
            return f"contradiction witness {self._payload_to_text(payload.witness)}"
        if isinstance(payload, StructuralClaim):
            return f"structural claim {payload.element!r}"
        if isinstance(payload, TextClaim):
            return payload.text
        return str(payload)

    def _term_to_text(self, node: Node) -> str:
        text, _ = self._term_to_text_with_shortening(node)
        return text

    def _term_to_text_with_shortening(self, node: Node) -> tuple[str, bool]:
        default_text = node.n3()
        if self.namespace_manager is not None:
            try:
                shortened = node.n3(namespace_manager=self.namespace_manager)
                return shortened, shortened != default_text
            except Exception:
                pass
        return default_text, False

    @staticmethod
    def _escape_mermaid(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"')

    def _mermaid_node(self, node_id: str, kind: str, label: str) -> str:
        # text = self._escape_mermaid(f"{kind.title()}: {label}")
        text = self._escape_mermaid(label)
        if kind == "goal":
            return f'{node_id}>"{text}"]'
        if kind == "rule":
            return f'{node_id}[["{text}"]]'
        if kind == "leaf":
            return f'{node_id}["{text}"]'
        return f'{node_id}("{text}")'


def render_proof_markdown(
    proof: DirectProof,
    *,
    namespace_manager: NamespaceManager | None = None,
    rules: tuple[Rule, ...] | None = None,
) -> str:
    """Render a `DirectProof` to markdown text."""
    return ProofRenderer(
        namespace_manager=namespace_manager, rules=rules
    ).render_markdown(proof)


def render_proof_mermaid(
    proof: DirectProof,
    *,
    namespace_manager: NamespaceManager | None = None,
    rules: tuple[Rule, ...] | None = None,
) -> str:
    """Render a `DirectProof` to Mermaid graph syntax."""
    return ProofRenderer(
        namespace_manager=namespace_manager, rules=rules
    ).render_mermaid(proof)
