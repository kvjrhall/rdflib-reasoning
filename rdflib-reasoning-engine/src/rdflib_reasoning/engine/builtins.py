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


class SameTermPredicate(PredicateHook):
    """True when the terms are equal."""

    def test(self, context: RuleContext, *args: Node) -> bool:
        _ = context
        if len(args) != 2:
            return False
        return args[0] == args[1]


class NotLiteralPredicate(PredicateHook):
    """True when the term is not an RDF literal (suitable as an RDF 1.1 subject)."""

    def test(self, context: RuleContext, *args: Node) -> bool:
        _ = context
        if len(args) != 1:
            return False
        return not isinstance(args[0], RDFLiteral)


class TermInPredicate(PredicateHook):
    """True when the first term equals one of the remaining terms."""

    def test(self, context: RuleContext, *args: Node) -> bool:
        _ = context
        if len(args) < 2:
            return False
        test_term, *reference_terms = args
        return test_term in reference_terms


class TermNotInPredicate(PredicateHook):
    """True when the first term equals none of the remaining terms."""

    def test(self, context: RuleContext, *args: Node) -> bool:
        _ = context
        if len(args) < 2:
            return False
        test_term, *reference_terms = args
        return test_term not in reference_terms


DEFAULT_PREDICATE_BUILTINS: dict[str, PredicateHook] = {
    "same_term": SameTermPredicate(),
    "different_terms": DifferentTermsPredicate(),
    "not_literal": NotLiteralPredicate(),
    "term_in": TermInPredicate(),
    "term_not_in": TermNotInPredicate(),
}
