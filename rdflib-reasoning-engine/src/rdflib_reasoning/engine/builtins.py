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
from rdflib.term import Node

from .errors import BuiltinInputError


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


DEFAULT_CALLBACK_BUILTINS: Final[Mapping[str, CallbackHook]] = MappingProxyType({})
"""Default callbacks available to registries.

At this time, no default callbacks are provided.
"""


DEFAULT_PREDICATE_BUILTINS: Final[Mapping[str, PredicateHook]] = MappingProxyType(
    {
        "different_terms": DifferentTermsPredicate(),
        "not_literal": NotLiteralPredicate(),
        "same_term": SameTermPredicate(),
        "term_in": TermInPredicate(),
        "term_not_in": TermNotInPredicate(),
    }
)
"""Default predicates available to registries.

At this time, the following predicates are provided:
- ``different_terms``: True when the all arguments are distinct RDF nodes.
- ``not_literal``: True when all arguments are not RDF literals.
- ``same_term``: True when the all arguments are identical RDF nodes.
- ``term_in``: True when the first term equals one of the remaining terms.
- ``term_not_in``: True when the first term equals none of the remaining terms.
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
