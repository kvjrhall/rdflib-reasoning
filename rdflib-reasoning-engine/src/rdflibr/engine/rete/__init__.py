"""RETE internal scaffolding.

This package isolates forward-looking RETE internals from the public engine
facade in `rdflibr.engine.api` and from proof/derivation structures in
`rdflibr.engine.proof`. The internals are RETE-OO-inspired, but the intended
logical core remains triple-oriented and engine-managed.
"""

from .agenda import Agenda
from .callbacks import CallbackAction, CallbackContext, rule_action
from .compiler import JoinOptimizer, RuleCompiler
from .consequents import ActionInstance, TripleProduction
from .facts import Fact, PartialMatch
from .network import (
    AlphaNode,
    BetaNode,
    NetworkBuilder,
    NodeRegistry,
    PredicateNode,
    TerminalNode,
)
from .tms import DependencyGraph, Justification, TMSController, WorkingMemory

__all__ = [
    "ActionInstance",
    "Agenda",
    "AlphaNode",
    "BetaNode",
    "CallbackAction",
    "CallbackContext",
    "DependencyGraph",
    "Fact",
    "JoinOptimizer",
    "Justification",
    "NetworkBuilder",
    "NodeRegistry",
    "PartialMatch",
    "PredicateNode",
    "RuleCompiler",
    "TMSController",
    "TerminalNode",
    "TripleProduction",
    "WorkingMemory",
    "rule_action",
]
