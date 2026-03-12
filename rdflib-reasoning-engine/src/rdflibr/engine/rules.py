from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Annotated, Literal, TypeAlias, TypedDict

from pydantic import Field
from rdflib.term import Node, Variable
from rdflibr.axiom.common import ContextIdentifier

from .proof import ProofModel, RuleDescription, RuleId

if TYPE_CHECKING:
    from .derivation import DerivationLogger


class RuleContext:
    """Placeholder read-only context passed to public predicates and callbacks."""


class PredicateHook(ABC):
    """Placeholder public read-only predicate hook used in rule conditions."""

    @abstractmethod
    def test(self, context: RuleContext, *args: Node) -> bool:
        pass


class CallbackHook(ABC):
    """Placeholder public non-logical callback hook attached to a rule match."""

    @abstractmethod
    def run(self, context: RuleContext, *args: Node) -> None:
        pass


class Builtins(TypedDict, total=False):
    """Placeholder registry for host-provided predicates and callbacks.

    Public builtins are split into read-only predicate evaluation and
    observational callbacks. Logical triple production remains engine-managed
    and is therefore not represented as a builtin hook.
    """

    predicates: dict[str, PredicateHook]
    callbacks: dict[str, CallbackHook]


class ContextData(TypedDict, total=False):
    """Per-engine contextual inputs supplied by the factory for one graph."""

    builtins: Builtins
    context: ContextIdentifier
    derivation_logger: "DerivationLogger"


PatternTerm: TypeAlias = Node | Variable
"""A term in a rule pattern, either concrete RDFLib node or RDFLib variable."""


class TriplePattern(ProofModel):
    """A triple-pattern template used in rule bodies and logical productions."""

    subject: PatternTerm = Field(..., description="Subject node or RDFLib variable.")
    predicate: PatternTerm = Field(
        ..., description="Predicate node or RDFLib variable."
    )
    object: PatternTerm = Field(..., description="Object node or RDFLib variable.")


class TripleCondition(ProofModel):
    """A triple-pattern match required in a rule body."""

    kind: Literal["triple"] = "triple"
    pattern: TriplePattern = Field(
        ..., description="The triple pattern that must match working memory."
    )


class PredicateCondition(ProofModel):
    """A read-only predicate invocation used in a rule body."""

    kind: Literal["predicate"] = "predicate"
    predicate: str = Field(
        ..., description="Lookup key in the builtin predicate registry."
    )
    arguments: tuple[PatternTerm, ...] = Field(
        default_factory=tuple,
        description="Ordered RDFLib terms or variables passed to the predicate.",
    )


RuleCondition = Annotated[
    TripleCondition | PredicateCondition,
    Field(discriminator="kind"),
]


class TripleConsequent(ProofModel):
    """An engine-managed logical triple production in a rule head."""

    kind: Literal["triple"] = "triple"
    pattern: TriplePattern = Field(
        ..., description="The triple pattern instantiated when the rule fires."
    )


class CallbackConsequent(ProofModel):
    """A non-mutating callback scheduled when a rule match completes."""

    kind: Literal["callback"] = "callback"
    callback: str = Field(..., description="Lookup key in the callback registry.")
    arguments: tuple[PatternTerm, ...] = Field(
        default_factory=tuple,
        description="Ordered RDFLib terms or variables passed to the callback.",
    )


RuleConsequent = Annotated[
    TripleConsequent | CallbackConsequent,
    Field(discriminator="kind"),
]


class Rule(ProofModel):
    """Public rule definition consumed by the engine facade.

    The public Rule IR stays RDF triple-oriented. It uses RDFLib Variables for
    bindings, read-only predicate calls for body-side tests, engine-managed
    triple production for logical consequents, and optional non-mutating
    callbacks for observational side effects.
    """

    id: RuleId = Field(..., description="Stable identifier for this rule definition.")
    description: RuleDescription | None = Field(
        default=None,
        description="Optional shared descriptive metadata for this rule.",
    )
    body: tuple[RuleCondition, ...] = Field(
        ...,
        min_length=1,
        description="Conjunctive body conditions required for the rule to match.",
    )
    head: tuple[RuleConsequent, ...] = Field(
        ...,
        min_length=1,
        description="Consequents scheduled when the body matches.",
    )
    salience: int = Field(
        default=0,
        description="Optional agenda priority used during conflict resolution.",
    )
