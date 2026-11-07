"""Expose Python hooks for RETE rule predicates and callbacks.

Builtins are split into read-only
:class:`~rdflib_reasoning.engine.PredicateHook` used while evaluating rule
conditions and
:class:`~rdflib_reasoning.engine.CallbackHook` invoked as part of rule
consequents.

These hooks MUST NOT add triples, retract triples, or otherwise mutate graph
state.
Treat them as observational hooks for your application and/or domain logic.

You MAY have your application mutate the graph in response to a callback AFTER
the engine has reached a fixed-point inference closure, but you MUST NOT do so
from within the callback.
The behavior if modifications are made from within the callback is undefined.
Modifications following from callbacks are unmanaged and will not be tracked by
the engine's truth-maintenance mechanisms.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from math import log10
from types import MappingProxyType
from typing import ClassVar, Final, Never, Self

from pydantic import NonNegativeInt
from rdflib.term import Literal as RDFLiteral
from rdflib.term import Node, URIRef

from .errors import BuiltinInputError
from .owl2_rl_datatypes import literal_value_in_datatype


def _format_inputs(inputs: Sequence[Node]) -> str:
    if not inputs:
        return "No arguments provided"

    lpad = int(log10(len(inputs))) + 1
    input_strs = [f"  {idx:>{lpad}}: {input}" for idx, input in enumerate(inputs)]
    inputs_str = "\n".join(input_strs)
    return f"The following arguments were supplied:\n{inputs_str}"


class RuleContext:
    """Read-only context passed to public predicates and callbacks.

    This provides an abstraction similar to Jackson's
    `DeserializationContext <https://javadoc.io/doc/com.fasterxml.jackson.core/jackson-databind/latest/com/fasterxml/jackson/databind/DeserializationContext.html>`_.
    """

    def report_input_mismatch(self, message: str, inputs: Sequence[Node]) -> Never:
        """Report a generic input error with formatted RDFLib node arguments."""
        raise BuiltinInputError(f"{message}\n{_format_inputs(inputs)}")

    def report_argument_count(
        self,
        inputs: Sequence[Node],
        *,
        min_inclusive: NonNegativeInt | None = None,
        max_inclusive: NonNegativeInt | None = None,
    ) -> Never:
        """Report an argument count error."""
        argc = len(inputs)

        message: str
        if min_inclusive is None:
            if max_inclusive is None:
                raise ValueError(
                    "At least one of `min_inclusive` or `max_inclusive` must be provided"
                )
            else:
                assert argc > max_inclusive
                message = f"Expected at most {max_inclusive} argument(s), got {argc}"
        else:
            match max_inclusive:
                case None:
                    assert argc < min_inclusive
                    message = (
                        f"Expected at least {min_inclusive} argument(s), got {argc}"
                    )
                case _ if min_inclusive == max_inclusive:
                    assert argc != min_inclusive
                    message = (
                        f"Expected exactly {min_inclusive} argument(s), got {argc}"
                    )
                case _ if min_inclusive < max_inclusive:
                    assert argc < min_inclusive or argc > max_inclusive
                    message = f"Expected between {min_inclusive} and {max_inclusive} argument(s), got {argc}"
                case _:
                    raise ValueError(
                        f"`min_inclusive` ({min_inclusive}) must be less than `max_inclusive` ({max_inclusive})"
                    )

        self.report_input_mismatch(message, inputs)


class PredicateHook(ABC):
    """Public read-only predicate hook used in rule conditions."""

    @abstractmethod
    def test(self, context: RuleContext, *args: Node) -> bool:
        """Return whether the predicate holds for ``args`` in ``context``."""


class CallbackHook(ABC):
    """Public non-logical callback hook attached to a rule match."""

    @abstractmethod
    def run(self, context: RuleContext, *args: Node) -> None:
        """Run the callback for ``args`` in ``context`` without mutating logical closure."""


class DifferentTermsPredicate(PredicateHook):
    """True when the all arguments are distinct RDF nodes.

    This does not perform a semantic comparison of the terms which would depend
    on the ontology and rulesets' definitions of equality.

    By default, registered as "different_terms" in
    :data:`~rdflib_reasoning.engine.builtins.DEFAULT_PREDICATE_BUILTINS`.
    See :class:`~rdflib_reasoning.engine.builtins.SameTermPredicate` for the
    logical inverse of this predicate.

    :param context: The read-only context passed to the predicate.
    :param args: A sequence of RDF nodes. It is an error to call this predicate with less than two arguments.
    :return: False when any two nodes in the sequence are identical; True otherwise.
    """

    __slots__ = ()

    def test(self, context: RuleContext, *args: Node) -> bool:
        """Return whether every argument is a distinct RDF node."""
        if len(args) < 2:
            context.report_argument_count(args, min_inclusive=2)

        for idx, arg in enumerate(args):
            if any(arg == other for other in args[idx + 1 :]):
                return False
        return True


class NotLiteralPredicate(PredicateHook):
    """True when all arguments are not RDF literals.

    Useful to test if a node is suitable as an RDF 1.1 subject.

    By default, registered as "not_literal" in
    :data:`~rdflib_reasoning.engine.builtins.DEFAULT_PREDICATE_BUILTINS`.
    See :class:`~rdflib_reasoning.engine.builtins.IsLiteralPredicate` for the
    logical inverse of this predicate.

    :param context: The read-only context passed to the predicate.
    :param args: A sequence of RDF nodes. It is an error to call this predicate with less than one argument.
    :return: False when any argument is an RDF literal; True otherwise.
    """

    __slots__ = ()

    def test(self, context: RuleContext, *args: Node) -> bool:
        """Return whether no argument is an RDF literal."""
        if len(args) < 1:
            context.report_argument_count(args, min_inclusive=1)
        return all(not isinstance(arg, RDFLiteral) for arg in args)


class IsLiteralPredicate(PredicateHook):
    """True when all arguments are RDF literals.

    By default, registered as "is_literal" in
    :data:`~rdflib_reasoning.engine.builtins.DEFAULT_PREDICATE_BUILTINS`.
    See :class:`~rdflib_reasoning.engine.builtins.NotLiteralPredicate` for the
    logical inverse of this predicate.

    Args:
        context: The read-only context passed to the predicate.
        args: A sequence of RDF nodes. It is an error to call this predicate
            with less than one argument.

    Returns:
        False when any argument is not an RDF literal; True otherwise.
    """

    __slots__ = ()

    def test(self, context: RuleContext, *args: Node) -> bool:
        """Return whether every argument is an RDF literal."""
        if len(args) < 1:
            context.report_argument_count(args, min_inclusive=1)
        return all(isinstance(arg, RDFLiteral) for arg in args)


class SameTermPredicate(PredicateHook):
    """True when the all arguments are identical RDF nodes.

    This does not perform a semantic comparison of the terms which would depend
    on the ontology and rulesets' definitions of equality.

    By default, registered as "same_term" in
    :data:`~rdflib_reasoning.engine.builtins.DEFAULT_PREDICATE_BUILTINS`.
    See :class:`~rdflib_reasoning.engine.builtins.DifferentTermsPredicate` for
    the logical inverse of this predicate.

    :param context: The read-only context passed to the predicate.
    :param args: A sequence of RDF nodes. It is an error to call this predicate with less than two arguments.
    :return: False when any two nodes in the sequence are different; True otherwise.
    """

    __slots__ = ()

    _different_terms: Final[DifferentTermsPredicate] = DifferentTermsPredicate()

    def test(self, context: RuleContext, *args: Node) -> bool:
        """Return whether every argument is the same RDF node."""
        # It's the logical inverse of DifferentTermsPredicate
        return not self._different_terms.test(context, *args)


class TermInPredicate(PredicateHook):
    """True when the first term equals one of the remaining terms.

    By default, registered as "term_in" in
    :data:`~rdflib_reasoning.engine.builtins.DEFAULT_PREDICATE_BUILTINS`.
    See :class:`~rdflib_reasoning.engine.builtins.TermNotInPredicate` for the
    logical inverse of this predicate.

    :param context: The read-only context passed to the predicate.
    :param args: A sequence of RDF nodes. It is an error to call this predicate with less than two arguments.
    :return: True when the first term equals one of the remaining terms.
    """

    __slots__ = ()

    def test(self, context: RuleContext, *args: Node) -> bool:
        """Return whether the first argument equals one of the remaining arguments."""
        if len(args) < 2:
            context.report_argument_count(args, min_inclusive=2)
        test_term, *reference_terms = args
        return test_term in reference_terms


class TermNotInPredicate(PredicateHook):
    """True when the first term equals none of the remaining terms.

    By default, registered as "term_not_in" in
    :data:`~rdflib_reasoning.engine.builtins.DEFAULT_PREDICATE_BUILTINS`.
    See :class:`~rdflib_reasoning.engine.builtins.TermInPredicate` for the
    logical inverse of this predicate.

    :param context: The read-only context passed to the predicate.
    :param args: A sequence of RDF nodes. It is an error to call this predicate with less than two arguments.
    :return: False when the first term equals one of the remaining terms; True otherwise.
    """

    __slots__ = ()

    _term_in: Final[TermInPredicate] = TermInPredicate()

    def test(self, context: RuleContext, *args: Node) -> bool:
        """Return whether the first argument equals none of the remaining arguments."""
        # It's the logical inverse of TermInPredicate
        return not self._term_in.test(context, *args)


class LiteralSameValuePredicate(PredicateHook):
    """True when two literals denote the same data value.

    Comparison uses RDFLib value-space equality (``Literal.eq``), not RDFLib
    node identity. Non-literal arguments and incomparable or ill-typed pairs
    yield False so rule matching stays boolean.

    By default, registered as "literal_same_value" in
    :data:`~rdflib_reasoning.engine.builtins.DEFAULT_PREDICATE_BUILTINS`.
    See :class:`~rdflib_reasoning.engine.builtins.LiteralDifferentValuePredicate`
    for the related inequality predicate.

    Args:
        context: The read-only context passed to the predicate.
        args: Exactly two RDF nodes.

    Returns:
        True when both arguments are literals that denote the same data value.
    """

    __slots__ = ()

    def test(self, context: RuleContext, *args: Node) -> bool:
        """Return whether two literals denote the same data value."""
        if len(args) != 2:
            context.report_argument_count(args, min_inclusive=2, max_inclusive=2)
        left, right = args
        if not isinstance(left, RDFLiteral) or not isinstance(right, RDFLiteral):
            return False
        try:
            return left.eq(right)
        except TypeError:
            return False


class LiteralDifferentValuePredicate(PredicateHook):
    """True when two literals denote different data values.

    Comparison uses RDFLib value-space inequality (``Literal.neq``).
    Non-literal arguments and incomparable or ill-typed pairs yield False so
    rule matching does not treat unknown inequality as proven difference.

    By default, registered as "literal_different_value" in
    :data:`~rdflib_reasoning.engine.builtins.DEFAULT_PREDICATE_BUILTINS`.
    See :class:`~rdflib_reasoning.engine.builtins.LiteralSameValuePredicate`
    for the related equality predicate.

    Args:
        context: The read-only context passed to the predicate.
        args: Exactly two RDF nodes.

    Returns:
        True when both arguments are literals that denote different data values.
    """

    __slots__ = ()

    def test(self, context: RuleContext, *args: Node) -> bool:
        """Return whether two literals denote different data values."""
        if len(args) != 2:
            context.report_argument_count(args, min_inclusive=2, max_inclusive=2)
        left, right = args
        if not isinstance(left, RDFLiteral) or not isinstance(right, RDFLiteral):
            return False
        try:
            return left.neq(right)
        except TypeError:
            return False


class LiteralInDatatypePredicate(PredicateHook):
    """True when a literal's data value is in a datatype's value space.

    Only OWL 2 RL supported datatype IRIs are recognized. See
    :func:`~rdflib_reasoning.engine.owl2_rl_datatypes.literal_value_in_datatype`.

    By default, registered as "literal_in_datatype" in
    :data:`~rdflib_reasoning.engine.builtins.DEFAULT_PREDICATE_BUILTINS`.
    See :class:`~rdflib_reasoning.engine.builtins.LiteralNotInDatatypePredicate`
    for the logical inverse of this predicate.

    Args:
        context: The read-only context passed to the predicate.
        args: Exactly two RDF nodes ``(literal, datatype_iri)``.

    Returns:
        True when the first argument is a literal whose data value is contained
        in the value space of the datatype IRI given as the second argument.
    """

    __slots__ = ()

    def test(self, context: RuleContext, *args: Node) -> bool:
        """Return whether a literal's value is in a datatype value space."""
        if len(args) != 2:
            context.report_argument_count(args, min_inclusive=2, max_inclusive=2)
        literal, datatype = args
        if not isinstance(literal, RDFLiteral) or not isinstance(datatype, URIRef):
            return False
        return literal_value_in_datatype(literal, datatype)


class LiteralNotInDatatypePredicate(PredicateHook):
    """True when a literal's data value is not in a datatype's value space.

    By default, registered as "literal_not_in_datatype" in
    :data:`~rdflib_reasoning.engine.builtins.DEFAULT_PREDICATE_BUILTINS`.
    See :class:`~rdflib_reasoning.engine.builtins.LiteralInDatatypePredicate`
    for the logical inverse of this predicate.

    Args:
        context: The read-only context passed to the predicate.
        args: Exactly two RDF nodes ``(literal, datatype_iri)``.

    Returns:
        True when :class:`~rdflib_reasoning.engine.builtins.LiteralInDatatypePredicate`
        is False for the same arguments (including arity-valid non-membership).
    """

    __slots__ = ()

    _in_datatype: Final[LiteralInDatatypePredicate] = LiteralInDatatypePredicate()

    def test(self, context: RuleContext, *args: Node) -> bool:
        """Return whether a literal's value is outside a datatype value space."""
        return not self._in_datatype.test(context, *args)


DEFAULT_CALLBACK_BUILTINS: Final[Mapping[str, CallbackHook]] = MappingProxyType({})
"""Default callbacks available to registries.

At this time, no default callbacks are provided.
"""


DEFAULT_PREDICATE_BUILTINS: Final[Mapping[str, PredicateHook]] = MappingProxyType(
    {
        "different_terms": DifferentTermsPredicate(),
        "not_literal": NotLiteralPredicate(),
        "is_literal": IsLiteralPredicate(),
        "same_term": SameTermPredicate(),
        "term_in": TermInPredicate(),
        "term_not_in": TermNotInPredicate(),
        "literal_same_value": LiteralSameValuePredicate(),
        "literal_different_value": LiteralDifferentValuePredicate(),
        "literal_in_datatype": LiteralInDatatypePredicate(),
        "literal_not_in_datatype": LiteralNotInDatatypePredicate(),
    }
)
"""Default predicates available to registries.

At this time, the following predicates are provided:
- ``different_terms``: True when the all arguments are distinct RDF nodes.
- ``not_literal``: True when all arguments are not RDF literals.
- ``is_literal``: True when all arguments are RDF literals.
- ``same_term``: True when the all arguments are identical RDF nodes.
- ``term_in``: True when the first term equals one of the remaining terms.
- ``term_not_in``: True when the first term equals none of the remaining terms.
- ``literal_same_value``: True when two literals denote the same data value.
- ``literal_different_value``: True when two literals denote different data values.
- ``literal_in_datatype``: True when a literal's value is in a datatype value space.
- ``literal_not_in_datatype``: True when a literal's value is not in a datatype value space.
"""


@dataclass(frozen=True, slots=True, kw_only=True)
class Builtins:
    """Registry for host-provided predicates and callbacks.

    Registries are immutable :func:`dataclasses.dataclass` instances, but they
    can be extended/overridden with
    :meth:`~rdflib_reasoning.engine.builtins.Builtins.extend`.

    The no-args initializer for ``Builtins`` defaults to using
    :data:`DEFAULT_CALLBACK_BUILTINS` and :data:`DEFAULT_PREDICATE_BUILTINS`.
    :attr:`~rdflib_reasoning.engine.builtins.Builtins.EMPTY` is also provided
    as a convenience.
    """

    callbacks: Mapping[str, CallbackHook] = field(
        default_factory=lambda: DEFAULT_CALLBACK_BUILTINS
    )
    predicates: Mapping[str, PredicateHook] = field(
        default_factory=lambda: DEFAULT_PREDICATE_BUILTINS
    )

    def __post_init__(self) -> None:
        """Wrap callback and predicate mappings in read-only proxies."""
        object.__setattr__(
            self,
            "callbacks",
            MappingProxyType(dict(self.callbacks)),
        )
        object.__setattr__(
            self,
            "predicates",
            MappingProxyType(dict(self.predicates)),
        )

    #: Builtins registry with no predicates or callbacks.
    #:
    #: Unlike a default :class:`~rdflib_reasoning.engine.builtins.Builtins`
    #: instance (which loads
    #: :data:`~rdflib_reasoning.engine.builtins.DEFAULT_PREDICATE_BUILTINS` and
    #: :data:`~rdflib_reasoning.engine.builtins.DEFAULT_CALLBACK_BUILTINS`),
    #: ``EMPTY`` starts from an empty
    #: registry. Call :meth:`~rdflib_reasoning.engine.builtins.Builtins.extend`
    #: to register only the hooks a test
    #: or ruleset needs::
    #:
    #:     builtins = Builtins.EMPTY.extend(
    #:         more_predicates={"same_term": SameTermPredicate()}
    #:     )
    EMPTY: ClassVar[Self]

    def extend(
        self,
        more_callbacks: Mapping[str, CallbackHook] | None = None,
        more_predicates: Mapping[str, PredicateHook] | None = None,
    ) -> Self:
        """Return a new registry with additional callbacks and predicates merged in."""
        return replace(
            self,
            callbacks=dict(self.callbacks) | dict(more_callbacks or {}),
            predicates=dict(self.predicates) | dict(more_predicates or {}),
        )

    @classmethod
    def extend_defaults(
        cls,
        more_callbacks: Mapping[str, CallbackHook] = {},
        more_predicates: Mapping[str, PredicateHook] = {},
    ) -> Self:
        """Create a new builtins registry, overriding the defaults with the provided callbacks and predicates.

        Typically, we want to extend the standard library of predicates & callbacks.
        This fits into cases where we want to build a custom ruleset or add rules to an existing one.

        :param more_callbacks: Additional callbacks to add to the registry.
        :param more_predicates: Additional predicates to add to the registry.
        :return: A new builtins registry.
        """
        defaults = cls()
        return defaults.extend(more_callbacks, more_predicates)


Builtins.EMPTY = Builtins(callbacks={}, predicates={})
