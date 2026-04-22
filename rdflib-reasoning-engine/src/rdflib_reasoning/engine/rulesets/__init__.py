"""Named rule profiles for RDF reasoning.

Use :data:`PRODUCTION_RDFS_RULES` for production-oriented inference behavior
where selected rules remain silent, and use :data:`CONFORMANT_RDFS_RULES` for
materialization-oriented RDFS conformance tests.
"""

from .rdfs import CONFORMANT_RDFS_RULES, PRODUCTION_RDFS_RULES

__all__ = ["PRODUCTION_RDFS_RULES", "CONFORMANT_RDFS_RULES"]
