from abc import ABC
from collections.abc import Sequence
from itertools import chain
from typing import ClassVar, Literal, override

from pydantic import AliasChoices, Field, computed_field
from rdflib import OWL, RDF, RDFS, IdentifiedNode
from rdflib import Literal as RdfLiteral

from .common import N3IRIRef, N3Resource, Triple
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

    intersection_of: Seq

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
    """Element ``DataUnionOf( DR1 ... DRn )`` of the OWL 2 structural specification.

    The main RDF node is an anonymous blank node (written ``_:x`` below).

    Triples::

        _:x rdf:type rdfs:Datatype .
        _:x owl:unionOf T(SEQ DR1 ... DRn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataUnionOf"] = "DataUnionOf"

    union_of: Seq

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
    """Element ``DataComplementOf( DR )`` of the OWL 2 structural specification.

    The main RDF node is an anonymous blank node (written ``_:x`` below).
    ``complement_of`` is the RDF subject of the complemented datatype description
    (IRI or blank node); ``as_triples`` emits only this axiom's triples (shallow
    projection per DR-031). Declaration and other triples for ``DR`` belong in
    a separate axiom instance or graph partition, not inlined here.

    Triples::

        _:x rdf:type rdfs:Datatype .
        _:x owl:complementOf DR .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataComplementOf"] = "DataComplementOf"

    complement_of: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                super().as_triples,
                [(self.name, OWL.complementOf, self.complement_of)],
            ),
        )


class DataOneOf(DataRange):
    """Element ``DataOneOf( lt1 ... ltn )`` of the OWL 2 structural specification.

    ``one_of`` holds the enumerated RDF literals. Full ``as_triples`` projection
    (``owl:oneOf`` plus ``rdf:List`` structure per the OWL 2 RDF mapping) is not
    implemented yet; callers currently receive only the ``rdfs:Datatype``
    declaration triple for ``name``.
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataOneOf"] = "DataOneOf"

    one_of: tuple[RdfLiteral, ...] = Field(
        ...,
        min_length=1,
        description="Finite non-empty sequence of data literals in this enumeration.",
    )


# TODO: move to structural_element module
class RestrictionFacet(StructuralElement, ABC):
    """Abstract base for facet expressions used in datatype restrictions (OWL 2)."""


class DataRestriction(RestrictionFacet, ABC):
    @property
    def as_triples(self) -> Sequence[Triple]:
        """Triples representing this element as RDF; MUST NOT recurse into related elements."""
        return ((self.name, RDF.type, OWL.Restriction),)


class DataSomeValuesFrom(DataRestriction):
    """Element ``DataSomeValuesFrom`` (data existential restriction) in the OWL 2 structural specification.

    The RDF subject is typically an anonymous blank node (written ``_:x`` below).

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty OP .
        _:x owl:someValuesFrom CE .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataSomeValuesFrom"] = "DataSomeValuesFrom"

    name_value: N3Resource = Field(
        ...,
        validation_alias=AliasChoices("name", "name_value"),
        serialization_alias="name",
    )

    on_property: N3IRIRef
    some_values_from: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    def name(self) -> IdentifiedNode:
        return self.name_value

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


class DatatypeRestriction(DataRange):
    """Element ``DatatypeRestriction( DT F1 lt1 ... Fn ltn )`` in the OWL 2 structural specification.

    Fields ``on_datatype`` and ``with_restrictions`` carry the structured form.
    ``with_restrictions`` is a ``Seq`` whose ``rdf:first`` objects are the RDF
    subjects of facet restrictions (typically blank nodes or IRIs); facet triples
    are not inlined inside ``Seq.as_triples`` (shallow projection per DR-031).
    Additional OWL 2 datatype-facet classes may be modeled later.
    ``as_triples`` currently emits only the ``rdfs:Datatype`` declaration for
    ``name``; additional mapping triples may be added in a later revision.
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DatatypeRestriction"] = "DatatypeRestriction"

    on_datatype: N3IRIRef
    with_restrictions: Seq
