"""Aggregated OWL 2 RL rule profiles composed from family modules.

``OWL2_RL_ENTAILMENT_RULES`` concatenates the triple-producing family tuples.
``OWL2_RL_RULES`` adds the contradiction-diagnostics ruleset on top.
"""

from __future__ import annotations

from ..rules import Rule
from .owl2_rl_cax import OWL2_RL_CAX_RULES
from .owl2_rl_cls import OWL2_RL_CLS_RULES
from .owl2_rl_contradictions import OWL2_RL_CONTRADICTION_RULES
from .owl2_rl_dt import OWL2_RL_DT_RULES
from .owl2_rl_eq import OWL2_RL_EQ_RULES
from .owl2_rl_prp import OWL2_RL_PRP_RULES
from .owl2_rl_scm import OWL2_RL_SCM_RULES

#: Triple-producing OWL 2 RL entailment rules across all family modules.
OWL2_RL_ENTAILMENT_RULES: tuple[Rule, ...] = (
    *OWL2_RL_EQ_RULES,
    *OWL2_RL_PRP_RULES,
    *OWL2_RL_CLS_RULES,
    *OWL2_RL_CAX_RULES,
    *OWL2_RL_DT_RULES,
    *OWL2_RL_SCM_RULES,
)

#: Combined OWL 2 RL profile: entailment rules plus contradiction diagnostics.
OWL2_RL_RULES: tuple[Rule, ...] = (
    *OWL2_RL_ENTAILMENT_RULES,
    *OWL2_RL_CONTRADICTION_RULES,
)

__all__ = [
    "OWL2_RL_EQ_RULES",
    "OWL2_RL_PRP_RULES",
    "OWL2_RL_CLS_RULES",
    "OWL2_RL_CAX_RULES",
    "OWL2_RL_DT_RULES",
    "OWL2_RL_SCM_RULES",
    "OWL2_RL_CONTRADICTION_RULES",
    "OWL2_RL_ENTAILMENT_RULES",
    "OWL2_RL_RULES",
]
