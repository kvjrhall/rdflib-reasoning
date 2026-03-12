from rdflibr.engine import (
    RDFS_RULES,
    CallbackConsequent,
    DerivationLogger,
    DirectProof,
    ExplanationReconstructor,
    PredicateCondition,
    RETEEngine,
    RETEEngineFactory,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from rdflibr.engine.api import RETEEngine as ApiEngine
from rdflibr.engine.derivation import (
    ExplanationReconstructor as DerivationReconstructor,
)
from rdflibr.engine.rete import Fact, RuleCompiler, TMSController


def test_public_engine_api_is_exposed_from_api() -> None:
    assert RETEEngine is ApiEngine
    assert RETEEngineFactory.__name__ == "RETEEngineFactory"


def test_derivation_interfaces_are_exposed() -> None:
    assert ExplanationReconstructor is DerivationReconstructor
    assert DerivationLogger.__name__ == "DerivationLogger"
    assert DirectProof.__name__ == "DirectProof"


def test_rete_package_exposes_split_internal_stubs() -> None:
    assert Fact.__name__ == "Fact"
    assert RuleCompiler.__name__ == "RuleCompiler"
    assert TMSController.__name__ == "TMSController"


def test_public_rule_ir_and_rulesets_are_exposed() -> None:
    assert TriplePattern.__name__ == "TriplePattern"
    assert TripleCondition.__name__ == "TripleCondition"
    assert PredicateCondition.__name__ == "PredicateCondition"
    assert TripleConsequent.__name__ == "TripleConsequent"
    assert CallbackConsequent.__name__ == "CallbackConsequent"
    assert len(RDFS_RULES) >= 1
