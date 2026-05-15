"""OWL 2 Data Range and data-property class-expression structural elements.

This module models two related families of OWL 2 structural elements plus the
owned ``StructuralFragment`` scaffolding their RDF mappings require.

Data Range expressions (subclasses of :class:`DataRange`):

- :class:`DeclarationDatatype` --- ``Declaration( Datatype( DT ) )``; the
  fallback when no richer data range can be reconstructed from the graph.
- :class:`DataIntersectionOf` --- ``DataIntersectionOf( DR1 ... DRn )``,
  ``n >= 2``; owns an :class:`~rdflib_reasoning.axiom.structural_element.Seq`
  fragment.
- :class:`DataUnionOf` --- ``DataUnionOf( DR1 ... DRn )``, ``n >= 2``; owns
  an :class:`~rdflib_reasoning.axiom.structural_element.Seq` fragment.
- :class:`DataComplementOf` --- ``DataComplementOf( DR )``; the operand is a
  cross-axiom node reference.
- :class:`DataOneOf` --- ``DataOneOf( lt1 ... ltn )``, ``n >= 1``; owns an
  :class:`~rdflib_reasoning.axiom.structural_element.Seq` fragment of literals.
- :class:`DatatypeRestriction` ---
  ``DatatypeRestriction( DT F1 lt1 ... Fn ltn )``; owns a :class:`FacetList`
  fragment carrying both the cons-cell chain and the per-facet
  ``(_:yi Fi lti)`` triples.

Data property class expressions (subclasses of :class:`DataRestriction`):

- :class:`DataSomeValuesFrom` --- unary form ``DataSomeValuesFrom( DPE DR )``.
- :class:`DataSomeValuesFromNary` --- n-ary form
  ``DataSomeValuesFrom( DPE1 ... DPEn DR )``, ``n >= 2``; owns an
  :class:`~rdflib_reasoning.axiom.structural_element.Seq` fragment of property
  expressions.
- :class:`DataAllValuesFromNary` --- n-ary form
  ``DataAllValuesFrom( DPE1 ... DPEn DR )``, ``n >= 2``; owns an
  :class:`~rdflib_reasoning.axiom.structural_element.Seq` fragment of property
  expressions.

Owned scaffolding fragments defined here:

- :class:`FacetEntry` and :class:`FacetList` --- the ``rdf:List`` carrier for
  :class:`DatatypeRestriction`'s facet operand list, including the per-facet
  anchor triple.

:class:`DataRange` and :class:`DataRestriction` are abstract umbrellas: both
block direct instantiation, both provide the shared declaration triple
(``rdfs:Datatype`` for ``DataRange`` subclasses, ``owl:Restriction`` for
``DataRestriction`` subclasses) via ``as_triples``, and concrete subclasses
extend that projection with their own predicate-specific triples. Owned
fragments share their owning element's ``context`` and contribute their
``as_triples`` to the owner's RDF partition; cross-axiom operands are RDF
node identifiers via the package's annotated aliases.
"""

from abc import ABC
from collections.abc import Generator, Sequence
from itertools import chain
from typing import Any, ClassVar, Literal, Self, override

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)
from rdflib import OWL, RDF, RDFS, IdentifiedNode

from .common import N3IRIRef, N3Node, N3Resource, Triple
from .structural_element import (
    DeclarationElement,
    Seq,
    StructuralElement,
    StructuralFragment,
)


class DataRange(DeclarationElement, ABC):
    """Abstract umbrella for OWL 2 Data Range expressions.

    Not directly instantiable. Concrete subclasses include ``DeclarationDatatype``
    (the fallback when no richer data range can be constructed from the graph)
    and the richer expressions ``DataIntersectionOf``, ``DataUnionOf``,
    ``DataComplementOf``, ``DataOneOf``, and ``DatatypeRestriction``. All
    concrete data ranges declare ``rdf:type rdfs:Datatype`` for ``name``.
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if cls is DataRange:
            raise TypeError(
                "DataRange is abstract; use a concrete subclass "
                "(e.g. `DeclarationDatatype` as a fallback, or a richer data "
                "range class)."
            )
        return super().__new__(cls)

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


def _seq_operand_count(seq: Seq) -> int:
    """Count of non-sentinel rows in ``seq``."""
    return sum(1 for entry in seq.entries if entry.value is not None)


class DataIntersectionOf(DataRange):
    """Element ``DataIntersectionOf( DR1 ... DRn )`` of the OWL 2 structural specification.

    The main RDF node is an anonymous blank node (written ``_:x`` below). OWL
    2 structural syntax requires n >= 2 data range operands.

    Triples::

        _:x rdf:type rdfs:Datatype .
        _:x owl:intersectionOf T(SEQ DR1 ... DRn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataIntersectionOf"] = "DataIntersectionOf"

    intersection_of: Seq

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.intersection_of)
        if n < 2:
            raise ValueError(
                "DataIntersectionOf requires n >= 2 data range operands per the "
                f"OWL 2 structural specification; got n = {n}."
            )
        return self

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

    The main RDF node is an anonymous blank node (written ``_:x`` below). OWL
    2 structural syntax requires n >= 2 data range operands.

    Triples::

        _:x rdf:type rdfs:Datatype .
        _:x owl:unionOf T(SEQ DR1 ... DRn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataUnionOf"] = "DataUnionOf"

    union_of: Seq

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.union_of)
        if n < 2:
            raise ValueError(
                "DataUnionOf requires n >= 2 data range operands per the OWL 2 "
                f"structural specification; got n = {n}."
            )
        return self

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

    The main RDF node is an anonymous blank node (written ``_:x`` below).
    ``one_of`` is an owned ``Seq`` fragment carrying the enumerated RDF literals
    as ``rdf:first`` values; the fragment shares this element's ``context``.
    OWL 2 structural syntax requires n >= 1 literal operands.

    Triples::

        _:x rdf:type rdfs:Datatype .
        _:x owl:oneOf T(SEQ lt1 ... ltn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataOneOf"] = "DataOneOf"

    one_of: Seq

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.one_of)
        if n < 1:
            raise ValueError(
                "DataOneOf requires n >= 1 literal operands per the OWL 2 "
                f"structural specification; got n = {n}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.one_of.as_triples,
                super().as_triples,
                [(self.name, OWL.oneOf, self.one_of.name)],
            ),
        )


class DataRestriction(StructuralElement, ABC):
    """Abstract base for OWL 2 class expressions that restrict a data property.

    Not directly instantiable. Each concrete subclass declares a node of
    ``rdf:type owl:Restriction`` and pairs ``owl:onProperty`` (or
    ``owl:onProperties`` for n-ary forms) with a range or value predicate per
    the OWL 2 RDF mapping. ``name`` is the RDF subject of the restriction node
    (typically a blank node).
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if cls is DataRestriction:
            raise TypeError(
                "DataRestriction is abstract; use a concrete subclass "
                "(e.g. `DataSomeValuesFrom`)."
            )
        return super().__new__(cls)

    name_value: N3Resource = Field(
        ...,
        validation_alias=AliasChoices("name", "name_value"),
        serialization_alias="name",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def name(self) -> IdentifiedNode:
        return self.name_value

    @property
    def as_triples(self) -> Sequence[Triple]:
        """Triples representing this element as RDF; MUST NOT recurse into related elements."""
        return ((self.name, RDF.type, OWL.Restriction),)


class DataSomeValuesFrom(DataRestriction):
    """Element ``DataSomeValuesFrom`` (data existential restriction) in the OWL 2 structural specification.

    The RDF subject is typically an anonymous blank node (written ``_:x`` below).

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty DPE .
        _:x owl:someValuesFrom DR .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataSomeValuesFrom"] = "DataSomeValuesFrom"

    on_property: N3IRIRef
    some_values_from: N3Resource

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


class DataSomeValuesFromNary(DataRestriction):
    """Element ``DataSomeValuesFrom( DPE1 ... DPEn DR )``, n >= 2, in the OWL 2 structural specification.

    The RDF subject is typically an anonymous blank node (written ``_:x`` below).
    ``on_properties`` is an owned ``Seq`` fragment carrying the data property
    expressions; the fragment shares this element's ``context``.

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperties T(SEQ DPE1 ... DPEn) .
        _:x owl:someValuesFrom DR .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataSomeValuesFromNary"] = "DataSomeValuesFromNary"

    on_properties: Seq
    some_values_from: N3Resource

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.on_properties)
        if n < 2:
            raise ValueError(
                "DataSomeValuesFromNary requires n >= 2 data property "
                f"operands per the OWL 2 structural specification; got n = {n}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.on_properties.as_triples,
                super().as_triples,
                [
                    (self.name, OWL.onProperties, self.on_properties.name),
                    (self.name, OWL.someValuesFrom, self.some_values_from),
                ],
            ),
        )


class DataAllValuesFromNary(DataRestriction):
    """Element ``DataAllValuesFrom( DPE1 ... DPEn DR )``, n >= 2, in the OWL 2 structural specification.

    The RDF subject is typically an anonymous blank node (written ``_:x`` below).
    ``on_properties`` is an owned ``Seq`` fragment carrying the data property
    expressions; the fragment shares this element's ``context``.

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperties T(SEQ DPE1 ... DPEn) .
        _:x owl:allValuesFrom DR .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataAllValuesFromNary"] = "DataAllValuesFromNary"

    on_properties: Seq
    all_values_from: N3Resource

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.on_properties)
        if n < 2:
            raise ValueError(
                "DataAllValuesFromNary requires n >= 2 data property "
                f"operands per the OWL 2 structural specification; got n = {n}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.on_properties.as_triples,
                super().as_triples,
                [
                    (self.name, OWL.onProperties, self.on_properties.name),
                    (self.name, OWL.allValuesFrom, self.all_values_from),
                ],
            ),
        )


class FacetEntry(BaseModel):
    """One facet row in a ``DatatypeRestriction`` operand list.

    ``cell`` is the ``rdf:List`` cons-cell node (the ``_:li`` in the OWL 2
    mapping). ``anchor`` is the facet anchor node referenced by the
    cons-cell's ``rdf:first`` (the ``_:yi``). ``facet`` is the facet predicate
    (for example ``xsd:minInclusive``) and ``value`` is the facet literal.

    The terminal sentinel row uses ``cell == rdf:nil`` with ``anchor``,
    ``facet``, and ``value`` all ``None`` and emits no facet or
    list-membership triple from ``FacetList.as_triples``. Non-sentinel rows
    MUST supply all three of ``anchor``, ``facet``, and ``value``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    cell: N3Resource = Field(
        ...,
        description=(
            "The `rdf:List` cons-cell node for this facet row; "
            "typically a blank node in the absence of skolemization."
        ),
    )
    anchor: N3Resource | None = Field(
        ...,
        description=(
            "The facet anchor node (the `rdf:first` value of `cell`); "
            "typically a blank node in the absence of skolemization."
        ),
    )
    facet: N3IRIRef | None = Field(
        ...,
        description="The facet predicate (e.g. `xsd:minInclusive`).",
    )
    value: N3Node | None = Field(
        ...,
        description="The facet value (the constraining literal for this facet).",
    )

    @model_validator(mode="after")
    def check_rdf_nil_or_facet_value(self) -> Self:
        is_sentinel = self.cell == RDF.nil
        any_set = (
            self.anchor is not None or self.facet is not None or self.value is not None
        )
        all_set = (
            self.anchor is not None
            and self.facet is not None
            and self.value is not None
        )
        if is_sentinel and any_set:
            raise ValueError(
                "The `rdf:nil` sentinel row MUST NOT carry an anchor, facet, or value."
            )
        if not is_sentinel and not all_set:
            raise ValueError(
                f"Facet entry at {self.cell} MUST supply all of `anchor`, "
                "`facet`, and `value`."
            )
        return self


class FacetList(StructuralFragment):
    """Owned ``rdf:List`` scaffolding for the operand list of ``DatatypeRestriction``.

    Encodes both the cons-cell chain of facet anchor nodes and each per-facet
    ``(_:yi Fi lti)`` triple in a single ``as_triples`` projection (all rows
    belong to the owning ``DatatypeRestriction``'s partition per DR-031).

    Triples (omit ``rdf:first`` and facet rows where ``cell == rdf:nil``)::

        Ei.cell rdf:first Ei.anchor .          # when row is non-sentinel
        Ei.anchor Ei.facet Ei.value .          # when row is non-sentinel
        Ei.cell rdf:rest entries[i+1].cell .   # i < len(entries)-1
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["facet_list"] = "facet_list"

    entries: Sequence[FacetEntry] = Field(
        ...,
        description="The ordered facet entries of a DatatypeRestriction operand list.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def name(self) -> IdentifiedNode:
        return self.entries[0].cell

    @computed_field  # type: ignore[prop-decorator]
    @property
    def as_triples(self) -> Sequence[Triple]:
        def members() -> Generator[Triple]:
            for entry in self.entries:
                if (
                    entry.anchor is not None
                    and entry.facet is not None
                    and entry.value is not None
                ):
                    yield (entry.cell, RDF.first, entry.anchor)
                    yield (entry.anchor, entry.facet, entry.value)

        def tails() -> Generator[Triple]:
            names = [entry.cell for entry in self.entries]
            for head, tail in zip(names[:-1], names[1:], strict=True):
                yield (head, RDF.rest, tail)

        return tuple(chain(members(), tails()))

    @model_validator(mode="after")
    def check_list_integrity(self) -> Self:
        if len(self.entries) == 0:
            raise ValueError(
                "An empty facet list MUST be encoded as a single entry containing `rdf:nil`."
            )
        if self.entries[-1].cell != RDF.nil:
            raise ValueError(
                "The last entry in a FacetList sequence MUST be `rdf:nil`."
            )
        cells = [entry.cell for entry in self.entries]
        if len(set(cells)) != len(cells):
            duplicates = sorted([str(name) for name in cells if cells.count(name) > 1])
            raise ValueError(
                "The facet list cell names MUST be unique but found duplicates: "
                + ", ".join(duplicates)
            )

        return self


class DatatypeRestriction(DataRange):
    """Element ``DatatypeRestriction( DT F1 lt1 ... Fn ltn )`` in the OWL 2 structural specification.

    The main RDF node is an anonymous blank node (written ``_:x`` below).
    ``on_datatype`` is the constrained datatype IRI; ``with_restrictions`` is
    an owned ``FacetList`` fragment that carries the facet anchor nodes and
    their per-facet ``(_:yi Fi lti)`` triples.

    Triples::

        _:x rdf:type rdfs:Datatype .
        _:x owl:onDatatype DT .
        _:x owl:withRestrictions T(SEQ _:y1 ... _:yn) .
        _:y1 F1 lt1 .
        ...
        _:yn Fn ltn .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DatatypeRestriction"] = "DatatypeRestriction"

    on_datatype: N3IRIRef
    with_restrictions: FacetList

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.with_restrictions.as_triples,
                super().as_triples,
                [
                    (self.name, OWL.onDatatype, self.on_datatype),
                    (self.name, OWL.withRestrictions, self.with_restrictions.name),
                ],
            ),
        )
