"""OWL 2 object and data property characteristic structural elements.

Each characteristic is a declaration-shaped axiom: a single
``name rdf:type owl:*Property`` triple. ``FunctionalObjectProperty`` and
``FunctionalDataProperty`` share the RDF type ``owl:FunctionalProperty``; graph
lifting disambiguates them using a co-occurring datatype-property declaration
when present.
"""

from typing import ClassVar, Literal, override

from rdflib import OWL, IdentifiedNode

from .structural_element import DeclarationElement


class FunctionalObjectProperty(DeclarationElement):
    """Element ``FunctionalObjectProperty( OPE )`` of the OWL 2 structural specification.

    Triples::

        OPE rdf:type owl:FunctionalProperty .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["FunctionalObjectProperty"] = "FunctionalObjectProperty"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.FunctionalProperty


class InverseFunctionalObjectProperty(DeclarationElement):
    """Element ``InverseFunctionalObjectProperty( OPE )`` of the OWL 2 structural specification.

    Triples::

        OPE rdf:type owl:InverseFunctionalProperty .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["InverseFunctionalObjectProperty"] = "InverseFunctionalObjectProperty"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.InverseFunctionalProperty


class ReflexiveObjectProperty(DeclarationElement):
    """Element ``ReflexiveObjectProperty( OPE )`` of the OWL 2 structural specification.

    Triples::

        OPE rdf:type owl:ReflexiveProperty .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ReflexiveObjectProperty"] = "ReflexiveObjectProperty"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.ReflexiveProperty


class IrreflexiveObjectProperty(DeclarationElement):
    """Element ``IrreflexiveObjectProperty( OPE )`` of the OWL 2 structural specification.

    Triples::

        OPE rdf:type owl:IrreflexiveProperty .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["IrreflexiveObjectProperty"] = "IrreflexiveObjectProperty"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.IrreflexiveProperty


class SymmetricObjectProperty(DeclarationElement):
    """Element ``SymmetricObjectProperty( OPE )`` of the OWL 2 structural specification.

    Triples::

        OPE rdf:type owl:SymmetricProperty .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["SymmetricObjectProperty"] = "SymmetricObjectProperty"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.SymmetricProperty


class AsymmetricObjectProperty(DeclarationElement):
    """Element ``AsymmetricObjectProperty( OPE )`` of the OWL 2 structural specification.

    Triples::

        OPE rdf:type owl:AsymmetricProperty .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["AsymmetricObjectProperty"] = "AsymmetricObjectProperty"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.AsymmetricProperty


class TransitiveObjectProperty(DeclarationElement):
    """Element ``TransitiveObjectProperty( OPE )`` of the OWL 2 structural specification.

    Triples::

        OPE rdf:type owl:TransitiveProperty .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["TransitiveObjectProperty"] = "TransitiveObjectProperty"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.TransitiveProperty


class FunctionalDataProperty(DeclarationElement):
    """Element ``FunctionalDataProperty( DPE )`` of the OWL 2 structural specification.

    Shares the RDF mapping ``DPE rdf:type owl:FunctionalProperty`` with
    :class:`FunctionalObjectProperty`. Graph lifting prefers this form when the
    same name is also typed ``owl:DatatypeProperty``.

    Triples::

        DPE rdf:type owl:FunctionalProperty .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["FunctionalDataProperty"] = "FunctionalDataProperty"

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.FunctionalProperty


__all__ = [
    "AsymmetricObjectProperty",
    "FunctionalDataProperty",
    "FunctionalObjectProperty",
    "InverseFunctionalObjectProperty",
    "IrreflexiveObjectProperty",
    "ReflexiveObjectProperty",
    "SymmetricObjectProperty",
    "TransitiveObjectProperty",
]
