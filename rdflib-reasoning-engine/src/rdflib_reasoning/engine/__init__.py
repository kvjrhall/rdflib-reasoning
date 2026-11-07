"""RDFLib-integrated reasoning engine public package.

Most applications should construct reasoners through the canonical profiles in
:mod:`rdflib_reasoning.engine.api`, especially
:data:`rdflib_reasoning.engine.api.RDFS_RETE_MATERIALIZED` for materializing
RDFS entailment and :data:`rdflib_reasoning.engine.api.NO_RULES` for a
reasoner-shaped no-op profile.

The package root re-exports the common engine, rule, proof, derivation, and
diagnostic types for convenience. Lower-level RETE classes remain available for
tests and advanced integrations, but the profile constants are the preferred
entrypoint for stable construction.
"""

from .api import (
    NO_RULES,
    RDFS_RETE_MATERIALIZED,
    BlankNodePredicateError,
    BlankNodePredicateWarning,
    FatalRuleError,
    LiteralAsSubjectError,
    LiteralAsSubjectWarning,
    LiteralPredicateError,
    LiteralPredicateWarning,
    RDFTermConstraintError,
    ReasonerSpecification,
    RETEEngine,
    RETEEngineConfig,
    RETEEngineFactory,
    RETEEngineFactoryConfig,
    RETEStore,
)
from .builtins import (
    Builtins,
    CallbackHook,
    PredicateHook,
    RuleContext,
)
from .derivation import (
    ContradictionRecorder,
    DerivationLogger,
    DerivationProofReconstructor,
    DropContradictionRecorder,
    ExplanationReconstructor,
    InMemoryContradictionRecorder,
    InMemoryDerivationLogger,
    RaiseOnContradictionRecorder,
)
from .proof import (
    AuthorityReference,
    ContradictionClaim,
    ContradictionRecord,
    DerivationRecord,
    DirectProof,
    ProofLeaf,
    RuleApplication,
    RuleDescription,
    RuleId,
    SourceSpan,
    StructuralClaim,
    TextClaim,
    TripleFact,
    VariableBinding,
)
from .proof_rendering import (
    ProofRenderer,
    build_rule_lookup,
    render_proof_markdown,
    render_proof_mermaid,
)
from .rete_store import RetractionRematerializeWarning
from .rules import (
    CallbackConsequent,
    ContradictionConsequent,
    PatternTerm,
    PredicateCondition,
    Rule,
    RuleCondition,
    RuleConsequent,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from .rulesets import (
    CONFORMANT_RDFS_AXIOMS,
    CONFORMANT_RDFS_RULES,
    OWL2_RL_CONTRADICTION_RULES,
    OWL2_RL_ENTAILMENT_RULES,
    OWL2_RL_RULES,
    PRODUCTION_RDF_AXIOMS,
    PRODUCTION_RDFS_AXIOMS,
    PRODUCTION_RDFS_RULES,
)

__all__ = [
    "Builtins",
    "CallbackConsequent",
    "ContradictionConsequent",
    "CallbackHook",
    "AuthorityReference",
    "ContradictionClaim",
    "ContradictionRecorder",
    "DropContradictionRecorder",
    "InMemoryContradictionRecorder",
    "RaiseOnContradictionRecorder",
    "ContradictionRecord",
    "DerivationLogger",
    "DerivationProofReconstructor",
    "InMemoryDerivationLogger",
    "DerivationRecord",
    "DirectProof",
    "ExplanationReconstructor",
    "FatalRuleError",
    "RDFTermConstraintError",
    "BlankNodePredicateError",
    "BlankNodePredicateWarning",
    "LiteralAsSubjectError",
    "LiteralAsSubjectWarning",
    "LiteralPredicateError",
    "LiteralPredicateWarning",
    "NO_RULES",
    "RDFS_RETE_MATERIALIZED",
    "PatternTerm",
    "PredicateCondition",
    "PredicateHook",
    "ProofLeaf",
    "PRODUCTION_RDF_AXIOMS",
    "PRODUCTION_RDFS_AXIOMS",
    "CONFORMANT_RDFS_AXIOMS",
    "PRODUCTION_RDFS_RULES",
    "CONFORMANT_RDFS_RULES",
    "OWL2_RL_CONTRADICTION_RULES",
    "OWL2_RL_ENTAILMENT_RULES",
    "OWL2_RL_RULES",
    "build_rule_lookup",
    "RETEEngine",
    "RETEEngineConfig",
    "RETEEngineFactory",
    "RETEEngineFactoryConfig",
    "RETEStore",
    "RetractionRematerializeWarning",
    "ReasonerSpecification",
    "Rule",
    "RuleCondition",
    "RuleConsequent",
    "RuleApplication",
    "RuleDescription",
    "RuleContext",
    "RuleId",
    "SourceSpan",
    "StructuralClaim",
    "TextClaim",
    "TripleCondition",
    "TripleConsequent",
    "TriplePattern",
    "TripleFact",
    "VariableBinding",
    "ProofRenderer",
    "render_proof_markdown",
    "render_proof_mermaid",
]
