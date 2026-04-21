"""Default PredicateHook implementations merged into every RETEEngine."""

from rdflib.term import Literal as RDFLiteral
from rdflib.term import Node

from .rules import PredicateHook, RuleContext


class DifferentTermsPredicate(PredicateHook):
    """True when the terms are different."""

    def test(self, context: RuleContext, *args: Node) -> bool:
        _ = context
        if len(args) != 2:
            return False
        return args[0] != args[1]


class NotLiteralPredicate(PredicateHook):
    """True when the term is not an RDF literal (suitable as an RDF 1.1 subject)."""

    def test(self, context: RuleContext, *args: Node) -> bool:
        _ = context
        if len(args) != 1:
            return False
        return not isinstance(args[0], RDFLiteral)


DEFAULT_PREDICATE_BUILTINS: dict[str, PredicateHook] = {
    "different_terms": DifferentTermsPredicate(),
    "not_literal": NotLiteralPredicate(),
}
