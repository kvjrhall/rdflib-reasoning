from collections.abc import Set
from enum import StrEnum
from functools import cached_property
from typing import overload

from pydantic import BaseModel, ConfigDict
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DefinedNamespace
from rdflib_reasoning.middleware.dataset_model import N3IRIRef


class VocabularyTermType(StrEnum):
    CLASS = "class"
    DATATYPE = "datatype"
    INDIVIDUAL = "individual"
    PROPERTY = "property"


class VocabularyTerm(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    uri: N3IRIRef
    label: str
    definition: str
    termType: VocabularyTermType


class RDFVocabulary(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    namespace: N3IRIRef
    classes: Set[VocabularyTerm]
    datatypes: Set[VocabularyTerm]
    individuals: Set[VocabularyTerm]
    properties: Set[VocabularyTerm]

    @cached_property
    def all_terms(self) -> Set[VocabularyTerm]:
        return self.classes | self.datatypes | self.individuals | self.properties

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
        from rdflib_reasoning.middleware.namespaces.spec_normalizer import (
            build_vocabulary,
        )

        return build_vocabulary(namespace, graph)
