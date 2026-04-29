"""Named rule profiles for RDF reasoning.

Use :data:`PRODUCTION_RDFS_RULES` for production-oriented inference behavior
where selected rules remain silent, and use :data:`CONFORMANT_RDFS_RULES` for
materialization-oriented RDFS conformance tests.

RDF/RDFS normative axiom rules live under :data:`PRODUCTION_RDF_AXIOMS`,
:data:`PRODUCTION_RDFS_AXIOMS`, and :data:`CONFORMANT_RDFS_AXIOMS`.
"""

from .owl2_rl_contradictions import OWL2_RL_CONTRADICTION_RULES
from .rdf_axioms import PRODUCTION_RDF_AXIOMS
from .rdfs import CONFORMANT_RDFS_RULES, PRODUCTION_RDFS_RULES
from .rdfs_axioms import CONFORMANT_RDFS_AXIOMS, PRODUCTION_RDFS_AXIOMS

__all__ = [
    "PRODUCTION_RDF_AXIOMS",
    "PRODUCTION_RDFS_AXIOMS",
    "CONFORMANT_RDFS_AXIOMS",
    "PRODUCTION_RDFS_RULES",
    "CONFORMANT_RDFS_RULES",
    "OWL2_RL_CONTRADICTION_RULES",
]
