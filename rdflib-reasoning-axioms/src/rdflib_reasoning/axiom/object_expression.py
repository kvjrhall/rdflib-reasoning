"""OWL 2 object class-expression and class-axiom structural elements.

This module models object-side mirrors of the data-range patterns in
:mod:`rdflib_reasoning.axiom.datatype`, plus Seq-backed class axioms that share
the same owned-list mapping style.

Class expressions (subclasses of :class:`ClassExpression`):

- :class:`ObjectIntersectionOf` --- ``ObjectIntersectionOf( CE1 ... CEn )``,
  ``n >= 2``; owns an :class:`~rdflib_reasoning.axiom.structural_element.Seq`
  fragment.
- :class:`ObjectUnionOf` --- ``ObjectUnionOf( CE1 ... CEn )``, ``n >= 2``; owns
  an :class:`~rdflib_reasoning.axiom.structural_element.Seq` fragment.
- :class:`ObjectComplementOf` --- ``ObjectComplementOf( CE )``; the operand is a
  cross-axiom node reference.
- :class:`ObjectOneOf` --- ``ObjectOneOf( a1 ... an )``, ``n >= 1``; owns an
  :class:`~rdflib_reasoning.axiom.structural_element.Seq` fragment of individual
  resources (not literals).

Object property expression:

- :class:`ObjectInverseOf` --- ``ObjectInverseOf( OP )``; RDF mapping emits only
  ``_:x owl:inverseOf OP`` (no ``rdf:type`` triple).

Class axioms:

- :class:`DisjointClasses` --- binary ``DisjointClasses( CE1 CE2 )`` via
  ``owl:disjointWith``.
- :class:`EquivalentClasses` --- binary ``EquivalentClasses( CE1 CE2 )`` via
  ``owl:equivalentClass`` (n-ary structural forms serialize to multiple
  triples; reverse parse yields binaries).
- :class:`DisjointClassesNary` --- ``DisjointClasses( CE1 ... CEn )``,
  ``n > 2``; ``owl:AllDisjointClasses`` with owned ``owl:members`` Seq.
- :class:`DisjointUnion` --- ``DisjointUnion( C CE1 ... CEn )``, ``n >= 2``;
  named class with owned ``owl:disjointUnionOf`` Seq.

:class:`ClassExpression` is an abstract umbrella: it blocks direct
instantiation, provides the shared ``owl:Class`` declaration triple via
``as_triples``, and concrete subclasses extend that projection with their own
predicate-specific triples. Owned fragments share their owning element's
``context`` and contribute their ``as_triples`` to the owner's RDF partition;
cross-axiom operands are RDF node identifiers via the package's annotated
aliases.
"""

from abc import ABC
from collections.abc import Sequence
from itertools import chain
from typing import Any, ClassVar, Literal, Self, override

from pydantic import (
    AliasChoices,
    Field,
    computed_field,
    model_validator,
)
from rdflib import OWL, RDF, IdentifiedNode

from .common import N3Resource, Triple
from .structural_element import DeclarationElement, Seq, StructuralElement


class ClassExpression(DeclarationElement, ABC):
    """Abstract umbrella for OWL 2 class expressions that declare ``owl:Class``.

    Not directly instantiable. Concrete subclasses include
    ``ObjectIntersectionOf``, ``ObjectUnionOf``, ``ObjectComplementOf``, and
    ``ObjectOneOf``. All concrete class expressions declare
    ``rdf:type owl:Class`` for ``name``.
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Reject direct instantiation of the abstract ``ClassExpression`` base."""
        if cls is ClassExpression:
            raise TypeError(
                "ClassExpression is abstract; use a concrete subclass "
                "(e.g. `ObjectIntersectionOf`)."
            )
        return super().__new__(cls)

    @property
    @override
    def rdf_type(self) -> IdentifiedNode:
        return OWL.Class


def _seq_operand_count(seq: Seq) -> int:
    """Count of non-sentinel rows in ``seq``."""
    return sum(1 for entry in seq.entries if entry.value is not None)


class ObjectIntersectionOf(ClassExpression):
    """Element ``ObjectIntersectionOf( CE1 ... CEn )`` of the OWL 2 structural specification.

    The main RDF node is an anonymous blank node (written ``_:x`` below). OWL
    2 structural syntax requires n >= 2 class expression operands.

    Triples::

        _:x rdf:type owl:Class .
        _:x owl:intersectionOf T(SEQ CE1 ... CEn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectIntersectionOf"] = "ObjectIntersectionOf"

    intersection_of: Seq

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.intersection_of)
        if n < 2:
            raise ValueError(
                "ObjectIntersectionOf requires n >= 2 class expression operands "
                f"per the OWL 2 structural specification; got n = {n}."
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


class ObjectUnionOf(ClassExpression):
    """Element ``ObjectUnionOf( CE1 ... CEn )`` of the OWL 2 structural specification.

    The main RDF node is an anonymous blank node (written ``_:x`` below). OWL
    2 structural syntax requires n >= 2 class expression operands.

    Triples::

        _:x rdf:type owl:Class .
        _:x owl:unionOf T(SEQ CE1 ... CEn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectUnionOf"] = "ObjectUnionOf"

    union_of: Seq

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.union_of)
        if n < 2:
            raise ValueError(
                "ObjectUnionOf requires n >= 2 class expression operands per "
                f"the OWL 2 structural specification; got n = {n}."
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


class ObjectComplementOf(ClassExpression):
    """Element ``ObjectComplementOf( CE )`` of the OWL 2 structural specification.

    The main RDF node is an anonymous blank node (written ``_:x`` below).
    ``complement_of`` is the RDF subject of the complemented class expression
    (IRI or blank node); ``as_triples`` emits only this axiom's triples (shallow
    projection). Declaration and other triples for ``CE`` belong in a separate
    axiom instance or graph partition, not inlined here.

    Triples::

        _:x rdf:type owl:Class .
        _:x owl:complementOf CE .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectComplementOf"] = "ObjectComplementOf"

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


class ObjectOneOf(ClassExpression):
    """Element ``ObjectOneOf( a1 ... an )`` of the OWL 2 structural specification.

    The main RDF node is an anonymous blank node (written ``_:x`` below).
    ``one_of`` is an owned ``Seq`` fragment carrying the enumerated individuals
    as ``rdf:first`` values (IRIs or blank nodes, not literals); the fragment
    shares this element's ``context``. OWL 2 structural syntax requires
    n >= 1 individual operands.

    Triples::

        _:x rdf:type owl:Class .
        _:x owl:oneOf T(SEQ a1 ... an) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectOneOf"] = "ObjectOneOf"

    one_of: Seq

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.one_of)
        if n < 1:
            raise ValueError(
                "ObjectOneOf requires n >= 1 individual operands per the OWL 2 "
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


class ObjectInverseOf(StructuralElement):
    """Element ``ObjectInverseOf( OP )`` of the OWL 2 structural specification.

    The main RDF node is an anonymous blank node (written ``_:x`` below).
    ``inverse_of`` is the RDF node of the inverted object property expression;
    ``as_triples`` emits only this axiom's triples (shallow projection). The OWL
    2 RDF mapping does not emit an ``rdf:type`` triple for this form.

    Triples::

        _:x owl:inverseOf OP .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectInverseOf"] = "ObjectInverseOf"

    name_value: N3Resource = Field(
        ...,
        validation_alias=AliasChoices("name", "name_value"),
        serialization_alias="name",
    )
    inverse_of: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        """Inverse property expression node identifier (alias of ``name_value``)."""
        return self.name_value

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return ((self.name, OWL.inverseOf, self.inverse_of),)


class DisjointClasses(StructuralElement):
    """Element ``DisjointClasses( CE1 CE2 )`` of the OWL 2 structural specification.

    Both operands are RDF node references. If an operand is itself represented by
    another structural element, that element belongs to a separate partition.

    Triples::

        CE1 owl:disjointWith CE2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DisjointClasses"] = "DisjointClasses"

    class_expression_1: N3Resource
    class_expression_2: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.class_expression_1

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (
                self.class_expression_1,
                OWL.disjointWith,
                self.class_expression_2,
            ),
        )


class EquivalentClasses(StructuralElement):
    """Element ``EquivalentClasses( CE1 CE2 )`` of the OWL 2 structural specification.

    Binary form only. An n-ary structural ``EquivalentClasses( CE1 ... CEn )``
    serializes to n-1 ``owl:equivalentClass`` triples; OWL 2 RDF reverse mapping
    parses each triple as a binary axiom. This class models that binary parse
    shape. Shares ``owl:equivalentClass`` with
    :class:`~rdflib_reasoning.axiom.property_axiom.DatatypeDefinition`.

    Both operands are RDF node references. If an operand is itself represented by
    another structural element, that element belongs to a separate partition.

    Triples::

        CE1 owl:equivalentClass CE2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["EquivalentClasses"] = "EquivalentClasses"

    class_expression_1: N3Resource
    class_expression_2: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.class_expression_1

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (
                self.class_expression_1,
                OWL.equivalentClass,
                self.class_expression_2,
            ),
        )


class DisjointClassesNary(StructuralElement):
    """Element ``DisjointClasses( CE1 ... CEn )``, n > 2, of the OWL 2 structural specification.

    The RDF subject is typically an anonymous blank node (written ``_:x`` below)
    of type ``owl:AllDisjointClasses``. ``members`` is an owned ``Seq`` fragment
    carrying the class expression operands; the fragment shares this element's
    ``context``.

    Triples::

        _:x rdf:type owl:AllDisjointClasses .
        _:x owl:members T(SEQ CE1 ... CEn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DisjointClassesNary"] = "DisjointClassesNary"

    name_value: N3Resource = Field(
        ...,
        validation_alias=AliasChoices("name", "name_value"),
        serialization_alias="name",
    )
    members: Seq

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.members)
        if n <= 2:
            raise ValueError(
                "DisjointClassesNary requires n > 2 class expression operands "
                f"per the OWL 2 structural specification; got n = {n}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        """AllDisjointClasses node identifier (alias of ``name_value``)."""
        return self.name_value

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.members.as_triples,
                [
                    (self.name, RDF.type, OWL.AllDisjointClasses),
                    (self.name, OWL.members, self.members.name),
                ],
            ),
        )


class DisjointUnion(StructuralElement):
    """Element ``DisjointUnion( C CE1 ... CEn )`` of the OWL 2 structural specification.

    ``union_class`` is the named class ``C``. ``disjoint_union_of`` is an owned
    ``Seq`` fragment carrying the covering class expression operands
    (``n >= 2``); the fragment shares this element's ``context``. The OWL 2 RDF
    mapping does not emit an ``rdf:type`` triple for this axiom.

    Triples::

        C owl:disjointUnionOf T(SEQ CE1 ... CEn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DisjointUnion"] = "DisjointUnion"

    union_class: N3Resource
    disjoint_union_of: Seq

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.disjoint_union_of)
        if n < 2:
            raise ValueError(
                "DisjointUnion requires n >= 2 class expression operands per "
                f"the OWL 2 structural specification; got n = {n}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.union_class

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.disjoint_union_of.as_triples,
                [(self.union_class, OWL.disjointUnionOf, self.disjoint_union_of.name)],
            ),
        )


__all__ = [
    "ClassExpression",
    "DisjointClasses",
    "DisjointClassesNary",
    "DisjointUnion",
    "EquivalentClasses",
    "ObjectComplementOf",
    "ObjectIntersectionOf",
    "ObjectInverseOf",
    "ObjectOneOf",
    "ObjectUnionOf",
]
