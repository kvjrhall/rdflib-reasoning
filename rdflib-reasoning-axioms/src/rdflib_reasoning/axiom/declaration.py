"""OWL 2 entity declaration structural elements beyond class and datatype.

Concrete subclasses of
:class:`~rdflib_reasoning.axiom.structural_element.DeclarationElement` for
object, data, and annotation properties and for named individuals. Each maps to
a single ``name rdf:type …`` triple.
"""

from typing import ClassVar, Literal, override

from rdflib import OWL, IdentifiedNode

from .structural_element import DeclarationElement


class DeclarationObjectProperty(DeclarationElement):
    """Element ``Declaration( ObjectProperty( OP ) )`` of the OWL 2 structural specification.

    Triples::

        OP rdf:type owl:ObjectProperty .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DeclarationObjectProperty"] = "DeclarationObjectProperty"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.ObjectProperty


class DeclarationDataProperty(DeclarationElement):
    """Element ``Declaration( DataProperty( DP ) )`` of the OWL 2 structural specification.

    Triples::

        DP rdf:type owl:DatatypeProperty .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DeclarationDataProperty"] = "DeclarationDataProperty"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.DatatypeProperty


class DeclarationAnnotationProperty(DeclarationElement):
    """Element ``Declaration( AnnotationProperty( AP ) )`` of the OWL 2 structural specification.

    Triples::

        AP rdf:type owl:AnnotationProperty .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DeclarationAnnotationProperty"] = "DeclarationAnnotationProperty"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.AnnotationProperty


class NamedIndividual(DeclarationElement):
    """Element ``Declaration( NamedIndividual( a ) )`` of the OWL 2 structural specification.

    Triples::

        a rdf:type owl:NamedIndividual .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["NamedIndividual"] = "NamedIndividual"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.NamedIndividual


__all__ = [
    "DeclarationAnnotationProperty",
    "DeclarationDataProperty",
    "DeclarationObjectProperty",
    "NamedIndividual",
]
