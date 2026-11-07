"""Public construction API for canonical RDFLib reasoners.

This module is the stable assembly surface for callers that want to construct a
reasoner-backed RDFLib dataset, store, or per-context RETE engine factory
without wiring the lower-level RETE components by hand. Start with a
:class:`ReasonerSpecification` constant such as :data:`RDFS_RETE_MATERIALIZED`,
:data:`OWL2_RL_RETE_MATERIALIZED`, or :data:`NO_RULES`, then ask it for the
RDFLib integration object you need.

Examples:
    Create a materializing RDFS dataset backed by RDFLib's in-memory store::

        from rdflib_reasoning.engine.api import RDFS_RETE_MATERIALIZED

        dataset = RDFS_RETE_MATERIALIZED.dataset()
        graph = dataset.default_graph

    Wrap an existing RDFLib store with the canonical RDFS reasoner::

        from rdflib.plugins.stores.memory import Memory
        from rdflib_reasoning.engine.api import RDFS_RETE_MATERIALIZED

        store = RDFS_RETE_MATERIALIZED.store(Memory())

    Advanced callers that coordinate contexts directly can request a fresh
    engine factory and construct per-context engines::

        factory = RDFS_RETE_MATERIALIZED.engine_factory()
        engine = factory.new_engine(dataset.default_graph.identifier)

:class:`ReasonerSpecification` documents extending specification constants
to add new rules, logical predicates, or observational callbacks.

The low-level ``RETEEngine``, ``RETEEngineFactory``, ``RETEStore``, and RETE
error classes are re-exported here for convenience, but ordinary callers should
prefer the typed specifications over assembling those pieces directly.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Final, Literal

from rdflib import Dataset
from rdflib.plugins.stores.memory import Memory
from rdflib.store import Store
from rdflib_reasoning.axiom.common import ContextIdentifier

from .builtins import Builtins, CallbackHook, PredicateHook
from .derivation import (
    ContradictionRecorder,
    DerivationLogger,
    DropDerivationLogger,
    RaiseOnContradictionRecorder,
)
from .rete_engine import (
    LiteralSubjectPolicy,
    PredicateTermPolicy,
    RETEEngine,
    RETEEngineConfig,
)
from .rete_errors import (
    BlankNodePredicateError,
    BlankNodePredicateWarning,
    FatalRuleError,
    LiteralAsSubjectError,
    LiteralAsSubjectWarning,
    LiteralPredicateError,
    LiteralPredicateWarning,
    RDFTermConstraintError,
    RuleTripleWarning,
)
from .rete_factory import RETEEngineFactory, RETEEngineFactoryConfig
from .rete_store import RETEStore
from .rules import Rule
from .rulesets.owl2_rl import OWL2_RL_RULES
from .rulesets.rdfs import PRODUCTION_RDFS_RULES

ContradictionPolicy = Literal["raise", "record", "drop"]


@dataclass(frozen=True, slots=True)
class ReasonerSpecification:
    """Canonical configuration for assembling an RDFLib-backed reasoner.

    A specification encapsulates the process of assembling a
    :class:`rdflib.Dataset` with rdflib-reasoning enabled.
    There is a lot that is configurable and boilerplate during this assembly
    process, most of which is only relevant to advanced use cases.
    Using a `ReasonerSpecification` is the preferred mechanism if you just need
    to obtain a ready-to-use reasoner.

    A common use case is to add a few domain-specific rules and/or callbacks to
    an existing reasoner specification.
    Use :func:`extend` for a simple way to add rules and builtins to an existing
    specification.

    Most advanced configurations can be supported by extending any of the
    existing reasoner specifications using :func:`dataclasses.replace`.
    Specifications are immutable :func:`dataclasses.dataclass`es.
    The following example demonstrates the same behavior as the
    :func:`extend` helper, extending the default RDFS reasoner with a new rule
    which uses custom callbacks and predicates:

    .. code-block:: python

        from dataclasses import replace

        from rdflib_reasoning.engine.api import RDFS_RETE_MATERIALIZED

        spec = replace(
            RDFS_RETE_MATERIALIZED,
            rules=tuple(RDFS_RETE_MATERIALIZED.rules) + (your_rule,),
            builtins=RDFS_RETE_MATERIALIZED.builtins.extend(
                more_callbacks,
                more_predicates,
            ),
        )
    """

    name: str
    rules: Sequence[Rule]
    builtins: Builtins
    literal_subject_policy: LiteralSubjectPolicy
    predicate_term_policy: PredicateTermPolicy
    derivation_logger_factory: Callable[[ContextIdentifier], DerivationLogger]
    contradiction_recorder_factory: Callable[[ContextIdentifier], ContradictionRecorder]
    materializes_inferences: bool
    supports_retraction: bool
    supports_derivation_logging: bool
    contradiction_policy: ContradictionPolicy

    def engine_factory_config(self) -> RETEEngineFactoryConfig:
        """Return a fresh explicit factory configuration for this specification."""
        return RETEEngineFactoryConfig(
            rules=self.rules,
            builtins=self.builtins,
            literal_subject_policy=self.literal_subject_policy,
            predicate_term_policy=self.predicate_term_policy,
            derivation_logger_factory=self.derivation_logger_factory,
            contradiction_recorder_factory=self.contradiction_recorder_factory,
        )

    def engine_factory(self) -> RETEEngineFactory:
        """Return a fresh RETE engine factory using a fresh configuration."""
        return RETEEngineFactory(config=self.engine_factory_config())

    def extend(
        self,
        more_rules: Iterable[Rule],
        more_callbacks: Mapping[str, CallbackHook] = {},
        more_predicates: Mapping[str, PredicateHook] = {},
    ) -> ReasonerSpecification:
        """Return a new reasoner specification with the additional rules.

        This is the preferred way to take a reasoning profile and add a few
        domain-specific inference rules and/or callbacks. For example, if you
        simply want RDFS entailment plus some callback triggers, you can do:

        .. code-block:: python

            from rdflib_reasoning.engine.api import RDFS_RETE_MATERIALIZED

            spec = RDFS_RETE_MATERIALIZED.extend(
                more_rules=(your_rule,),
                more_callbacks={"your_callback": your_callback},
            )

        :param more_rules: Additional rules to add to the reasoner specification.
        :param more_callbacks: Additional callbacks if needed by the new rules.
        :param more_predicates: Additional predicates if needed by the new rules.
        :return: A new reasoner specification with the additional rules and builtins.
        """
        builtins = self.builtins.extend(more_callbacks, more_predicates)
        return replace(
            self,
            rules=tuple(self.rules) + tuple(more_rules),
            builtins=builtins,
        )

    def store(self, backing_store: Store) -> RETEStore:
        """Return a new materializing RETE store over the supplied backing store using a fresh engine factory."""
        return RETEStore(backing_store, self.engine_factory())

    def dataset(self, backing_store: Store | None = None) -> Dataset:
        """Return a new RDFLib dataset backed by this reasoner specification using a new RETE store."""
        return Dataset(store=self.store(backing_store or Memory()))


NO_RULES: Final[ReasonerSpecification] = ReasonerSpecification(
    name="no-op",
    rules=(),
    builtins=Builtins.EMPTY,
    literal_subject_policy="error",
    predicate_term_policy="error",
    derivation_logger_factory=lambda _context: DropDerivationLogger(),
    contradiction_recorder_factory=lambda _context: RaiseOnContradictionRecorder(),
    materializes_inferences=True,
    supports_retraction=True,
    supports_derivation_logging=True,
    contradiction_policy="raise",
)
"""No-op RETE-backed reasoner specification with an empty rule set.

This profile constructs the same RDFLib ``RETEStore`` integration used by
reasoning profiles, but supplies no inference rules.
It is useful when callers want a canonical specification object, store, or
dataset without entailment. Ordinary RDFLib graph mutation still
works, and asserted triples can be retracted.

This specification's defaults intend for it to be extended.
By default, no builtins are provided, derivation logging is disabled,
contradictions are raised, and strict RDF term validation is enforced.
Stores and datasets constructed from this specification materialize inference
closure through ordinary RDFLib graph mutation and support dependency-aware
retraction of asserted triples.
"""


RDFS_RETE_MATERIALIZED: Final[ReasonerSpecification] = replace(
    NO_RULES,
    name="rdfs-rete-materialized",
    rules=PRODUCTION_RDFS_RULES,
    builtins=Builtins(),
)
"""Canonical materializing RDFS RETE reasoner specification.

Extends the :data:`NO_RULES` specification with the production RDFS rule set
and provides the default :class:`~rdflib_reasoning.engine.Builtins`.
This specification is is intended to be extended in cases where you want
RDFS entailment plus some domain-specific rules and/or callbacks.
"""


OWL2_RL_RETE_MATERIALIZED: Final[ReasonerSpecification] = replace(
    NO_RULES,
    name="owl2-rl-rete-materialized",
    rules=OWL2_RL_RULES,
    builtins=Builtins(),
)
"""Canonical materializing OWL 2 RL RETE reasoner specification.

Extends the :data:`NO_RULES` specification with
:data:`~rdflib_reasoning.engine.rulesets.OWL2_RL_RULES` (entailment families
plus contradiction diagnostics) and the default
:class:`~rdflib_reasoning.engine.Builtins`. Contradiction-producing rules use
the dual-channel diagnostics path; the default recorder policy raises when a
contradiction is detected.
"""

__all__ = [
    "BlankNodePredicateError",
    "BlankNodePredicateWarning",
    "ContradictionPolicy",
    "FatalRuleError",
    "LiteralAsSubjectError",
    "LiteralAsSubjectWarning",
    "LiteralPredicateError",
    "LiteralPredicateWarning",
    "LiteralSubjectPolicy",
    "NO_RULES",
    "OWL2_RL_RETE_MATERIALIZED",
    "PredicateTermPolicy",
    "RDFS_RETE_MATERIALIZED",
    "RDFTermConstraintError",
    "RETEEngine",
    "RETEEngineConfig",
    "RETEEngineFactory",
    "RETEEngineFactoryConfig",
    "RETEStore",
    "ReasonerSpecification",
    "RuleTripleWarning",
]
