from typing import Final

from langchain.tools import tool
from rdflib.namespace import NamespaceManager
from rdflibr.axiom.namespaces import create_prefix_cc_namespace_manager

_namespaces: Final[NamespaceManager] = create_prefix_cc_namespace_manager()


@tool
def resolve_prefix(prefix: str) -> str:
    """Resolves a prefix to a URI."""
    namespace = _namespaces.store.namespace(prefix)
    if namespace is None:
        raise ValueError(f"Unknown prefix: {prefix}")
    return str(namespace)


@tool
def get_qname(iri: str) -> str:
    """Returns the QName for a given IRI.

    In RDF, a QName (Qualified Name) is a syntactic shorthand used primarily in the RDF/XML serialization to represent a full Internationalized Resource Identifier (IRI) in a more human-readable form.
    For example, the IRI ``http://www.w3.org/1999/02/22-rdf-syntax-ns#type`` can be abbreviated as ``rdf:type``.
    This tool returns the QName for a given prefix."""
    return _namespaces.qname(iri)


# TODO: Roadmap tools for skolemization and unskolemization
#       https://www.w3.org/TR/rdf11-concepts/#section-skolemization
