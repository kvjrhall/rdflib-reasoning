from collections.abc import Mapping
from typing import Any, Literal

from rdflib.term import Node, Variable
from rdflib_reasoning.axiom.common import Triple

RDF_TRIPLES_SPEC_URL = "https://www.w3.org/TR/rdf11-concepts/#section-triples"


def _n3_term(term: Node | Variable) -> str:
    if isinstance(term, Variable):
        return str(term)
    return term.n3()


def _triple_n3(triple: Triple) -> str:
    s, p, o = triple
    return f"{_n3_term(s)} {_n3_term(p)} {_n3_term(o)} ."


def format_term_constraint_diagnostics(
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
