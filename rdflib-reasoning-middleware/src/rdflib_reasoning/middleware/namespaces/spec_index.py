"""Indexed RDF vocabulary term records derived from specification graphs."""

from collections.abc import Mapping, Set
from functools import cached_property
from typing import overload

from pydantic import BaseModel, ConfigDict
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DefinedNamespace
from rdflib_reasoning.axiom.common import N3IRIRef

from .common import VocabularyTermType


class VocabularyTerm(BaseModel):
    """One indexed RDF vocabulary term with label, definition, and kind."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    uri: N3IRIRef
    label: str
    definition: str
    termType: VocabularyTermType


class RDFVocabulary(BaseModel):
    """Term sets for one vocabulary namespace, grouped by normalized term kind."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    namespace: N3IRIRef
    classes: Set[VocabularyTerm]
    datatypes: Set[VocabularyTerm]
    individuals: Set[VocabularyTerm]
    properties: Set[VocabularyTerm]

    @cached_property
    def all_terms(self) -> Set[VocabularyTerm]:
        """Return every indexed term across classes, datatypes, individuals, and properties."""
        return self.classes | self.datatypes | self.individuals | self.properties

    @cached_property
    def _lookup_table(self) -> Mapping[URIRef, VocabularyTerm]:
        """Map term IRIs to their indexed records."""
        return {term.uri: term for term in self.all_terms}

    def get_term(self, uri: URIRef) -> VocabularyTerm:
        """Return the indexed term for ``uri``."""
        return self._lookup_table[uri]

    def contains_term(self, uri: URIRef) -> bool:
        """Return whether ``uri`` is indexed in this vocabulary."""
        return uri in self._lookup_table

    @classmethod
    @overload
    def from_graph(
        cls, namespace: type[Namespace] | type[DefinedNamespace], graph: Graph
    ) -> "RDFVocabulary":
        pass

    @classmethod
    @overload
    def from_graph(
        cls, namespace: Namespace | DefinedNamespace, graph: Graph
    ) -> "RDFVocabulary":
        pass

    @classmethod
    @overload
    def from_graph(cls, namespace: URIRef | str, graph: Graph) -> "RDFVocabulary":
        pass

    @classmethod
    def from_graph(
        cls,
        namespace: type[Namespace]
        | type[DefinedNamespace]
        | Namespace
        | DefinedNamespace
        | URIRef
        | str,
        graph: Graph,
    ) -> "RDFVocabulary":
        """Build an indexed vocabulary from ``graph`` for ``namespace``."""
        from rdflib_reasoning.middleware.namespaces.spec_normalizer import (
            build_vocabulary,
        )

        return build_vocabulary(namespace, graph)
