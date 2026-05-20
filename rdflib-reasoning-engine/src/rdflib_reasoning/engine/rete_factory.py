from collections.abc import Callable, Sequence
from dataclasses import dataclass

from rdflib_reasoning.axiom.common import ContextIdentifier

from .builtins import Builtins
from .derivation import (
    ContradictionRecorder,
    DerivationLogger,
)
from .rete_engine import (
    LiteralSubjectPolicy,
    PredicateTermPolicy,
    RETEEngine,
    RETEEngineConfig,
)
from .rules import Rule


@dataclass(frozen=True, slots=True, kw_only=True)
class RETEEngineFactoryConfig:
    """Explicit per-context RETE engine assembly configuration.

    This configuration is supplied to :class:`RETEEngineFactory` and specifies the template for new engines.
    It is used to create a new engine for each context.

    :param rules: The common ruleset applied to all engines.
    :param contradiction_recorder_factory: The factory to use to create a new contradiction recorder for each context. Recorders are shared iff the same instance is always returned by this factory.
    :param derivation_logger_factory: The factory to use to create a new derivation logger for each context. Loggers are shared iff the same instance is always returned by this factory.
    :param builtins: The builtins (predicates / callbacks) to use for new engines. These are shared across all engines and are generally assumed to be stateless.
    :param literal_subject_policy: The literal subject policy to use for the engine.
    :param predicate_term_policy: The predicate term policy to use for the engine.
    """

    rules: Sequence[Rule]
    contradiction_recorder_factory: Callable[[ContextIdentifier], ContradictionRecorder]
    derivation_logger_factory: Callable[[ContextIdentifier], DerivationLogger]
    builtins: Builtins
    literal_subject_policy: LiteralSubjectPolicy
    predicate_term_policy: PredicateTermPolicy


class RETEEngineFactory:
    """Factory for per-context RETE engine instances.

    This factory is used by :class:`RETEStore` to lazily create new RETE engines for each context (read: graph) whenever they are needed.

    :param config: The configuration for the factory. This configuration will be reused for each new engine.
    """

    config: RETEEngineFactoryConfig

    def __init__(self, *, config: RETEEngineFactoryConfig) -> None:
        self.config = config

    @property
    def rules_template(self) -> Sequence[Rule]:
        return self.config.rules

    def new_engine(self, context: ContextIdentifier) -> RETEEngine:
        engine_config = RETEEngineConfig(
            context=context,
            builtins=self.config.builtins,
            derivation_logger=self.config.derivation_logger_factory(context),
            contradiction_recorder=self.config.contradiction_recorder_factory(context),
            literal_subject_policy=self.config.literal_subject_policy,
            predicate_term_policy=self.config.predicate_term_policy,
        )
        return RETEEngine(
            config=engine_config,
            rules=self.config.rules,
        )
