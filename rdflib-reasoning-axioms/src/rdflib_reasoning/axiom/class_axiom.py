"""OWL 2 class declaration and class axiom structural elements."""

from collections.abc import Sequence
from typing import ClassVar, Literal, override

from pydantic import computed_field
from rdflib import OWL, RDFS, IdentifiedNode

from .common import N3Resource, Triple
from .structural_element import DeclarationElement, StructuralElement


class DeclarationClass(DeclarationElement):
    """Element ``Declaration( Class( C ) )`` of the OWL 2 structural specification.

    Triples::

        C rdf:type owl:Class .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DeclarationClass"] = "DeclarationClass"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.Class


class SubClassOf(StructuralElement):
    """Element ``SubClassOf( CE1 CE2 )`` of the OWL 2 structural specification.

    Both operands are RDF node references. If an operand is itself represented by
    another structural element, that element belongs to a separate partition.

    Triples::

        CE1 rdfs:subClassOf CE2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["SubClassOf"] = "SubClassOf"

    sub_class_expression: N3Resource
    super_class_expression: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.sub_class_expression

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (
                self.sub_class_expression,
                RDFS.subClassOf,
                self.super_class_expression,
            ),
        )


__all__ = [
    "DeclarationClass",
    "SubClassOf",
]
