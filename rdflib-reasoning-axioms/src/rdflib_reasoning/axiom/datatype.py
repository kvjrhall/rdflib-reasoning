from abc import ABC
from collections.abc import Sequence
from itertools import chain
from typing import ClassVar, Literal, override

from pydantic import computed_field
from rdflib import OWL, RDF, RDFS, IdentifiedNode, URIRef

from .common import Triple
from .structural_element import DeclarationElement, Seq, StructuralElement


class DataRange(DeclarationElement):
    """Base class for all data axioms of the structural specification.

    This is **not** a formal OWL axiom; it is a convenience for type checking,
    type bounds, and centralizing common functionality. Note that `DataRange`
    and `DataRestriction` are disjoint.
    """

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return RDFS.Datatype


class DeclarationDatatype(DataRange):
    """Element `Declaration( Datatype( DT ) )` of the structural specification.

    Note that all of our `DataRange` classes share the same properties as a
    `DeclarationDatatype` instance, but we keep this as a separate axiom so
    that OWL axioms can partition a graph. _This_ axiom is only constructed if
    we are lacking the necessary triples to construct a different `DataRange`
    axiom.
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DeclarationDatatype"] = "DeclarationDatatype"


class DataIntersectionOf(DataRange):
    """Element ``DataIntersectionOf( DR1 ... DRn )`` of the OWL 2 structural specification.

    The main RDF node is an anonymous blank node (written ``_:x`` below).

    Triples::

        _:x rdf:type rdfs:Datatype .
        _:x owl:intersectionOf T(SEQ DR1 ... DRn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataIntersectionOf"] = "DataIntersectionOf"

    intersection_of: Seq[DataRange]

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.intersection_of.as_triples,
                super().as_triples,
                [(self.name, OWL.intersectionOf, self.intersection_of.name)],
            ),
        )


class DataUnionOf(DataRange):
    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataUnionOf"] = "DataUnionOf"

    union_of: Seq[DataRange]

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.union_of.as_triples,
                super().as_triples,
                [(self.name, OWL.unionOf, self.union_of.name)],
            ),
        )


class DataComplementOf(DataRange):
    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataComplementOf"] = "DataComplementOf"

    complement_of: DataRange

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.complement_of.as_triples,
                super().as_triples,
                [(self.name, OWL.complementOf, self.complement_of.name)],
            ),
        )


class DataOneOf(DataRange):
    # TODO: figure out how to represent a list of literals.
    pass


class DatatypeRestriction(DataRange):
    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DatatypeRestriction"] = "DatatypeRestriction"

    on_datatype: IdentifiedNode
    with_restrictions: Seq["DataRestriction"]


# TODO: move to structural_element module
class RestrictionFacet(StructuralElement, ABC):
    pass


class DataRestriction(RestrictionFacet, ABC):
    @property
    def as_triples(self) -> Sequence[Triple]:
        """Triples representing this element as RDF; MUST NOT recurse into related elements."""
        return ((self.name, RDF.type, OWL.Restriction),)


class DataSomeValuesFrom(DataRestriction):
    # _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataSomeValuesFrom"] = "DataSomeValuesFrom"

    on_property: URIRef
    some_values_from: IdentifiedNode

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                super().as_triples,
                [
                    (self.name, OWL.onProperty, self.on_property),
                    (self.name, OWL.someValuesFrom, self.some_values_from),
                ],
            ),
        )
