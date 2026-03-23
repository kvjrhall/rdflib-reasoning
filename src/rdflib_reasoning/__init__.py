"""Namespace package for rdflib-reasoning subpackages."""

from pkgutil import extend_path

# extend_path prevents the metapackage from exclusively owning the namespace by
# widening the package’s search path to include sibling contributions. It is
# basically the older explicit-namespace mechanism that predates
# PEP 420 implicit namespaces.
#
# We're using is to that we can attach metadata and documentation to the
# root namespace as-needed. Each of the subprojects would be unable to do that
# without accidentally "claiming" the root namespace.
__path__ = extend_path(__path__, __name__)
