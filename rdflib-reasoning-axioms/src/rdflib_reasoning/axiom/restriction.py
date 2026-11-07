"""OWL 2 object-property class-expression (restriction) structural elements.

Mirrors the data-property restriction family in
:mod:`rdflib_reasoning.axiom.datatype`. Concrete subclasses of
:class:`ObjectRestriction` declare ``rdf:type owl:Restriction`` and pair
``owl:onProperty`` with a filler or cardinality predicate per the OWL 2 RDF
mapping.

Value and universal/existential restrictions:

- :class:`ObjectSomeValuesFrom` --- ``ObjectSomeValuesFrom( OPE CE )``.
- :class:`ObjectAllValuesFrom` --- ``ObjectAllValuesFrom( OPE CE )``.
- :class:`ObjectHasValue` --- ``ObjectHasValue( OPE a )``.
- :class:`ObjectHasSelf` --- ``ObjectHasSelf( OPE )``.

Cardinality restrictions (unqualified and qualified via ``owl:onClass``):

- :class:`ObjectMinCardinality` / :class:`ObjectMinCardinalityQualified`
- :class:`ObjectMaxCardinality` / :class:`ObjectMaxCardinalityQualified`
- :class:`ObjectExactCardinality` / :class:`ObjectExactCardinalityQualified`
"""

from abc import ABC
from collections.abc import Sequence
from itertools import chain
from typing import Any, ClassVar, Literal, Self, override

from pydantic import AliasChoices, Field, computed_field, model_validator
from rdflib import OWL, RDF, XSD, IdentifiedNode, Node
from rdflib import Literal as RDFLiteral

from .common import N3IRIRef, N3Node, N3Resource, Triple
from .structural_element import StructuralElement

_TRUE_BOOLEAN = RDFLiteral(True, datatype=XSD.boolean)


def _require_non_negative_integer_literal(value: Node, *, label: str) -> None:
    """Require ``value`` to be an ``xsd:nonNegativeInteger`` literal."""
    if not isinstance(value, RDFLiteral):
        raise ValueError(f"{label} MUST be an RDF literal; got {type(value).__name__}.")
    if value.datatype != XSD.nonNegativeInteger:
        raise ValueError(
            f"{label} MUST have datatype xsd:nonNegativeInteger; got "
            f"{value.datatype!r}."
        )


class ObjectRestriction(StructuralElement, ABC):
    """Abstract base for OWL 2 class expressions that restrict an object property.

    Not directly instantiable. Each concrete subclass declares a node of
    ``rdf:type owl:Restriction`` and pairs ``owl:onProperty`` with a class,
    individual, self, or cardinality predicate per the OWL 2 RDF mapping.
    ``name`` is the RDF subject of the restriction node (typically a blank node).
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Reject direct instantiation of the abstract ``ObjectRestriction`` base."""
        if cls is ObjectRestriction:
            raise TypeError(
                "ObjectRestriction is abstract; use a concrete subclass "
                "(e.g. `ObjectSomeValuesFrom`)."
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
        """Restriction node identifier (alias of ``name_value``)."""
        return self.name_value

    @property
    def as_triples(self) -> Sequence[Triple]:
        """Triples representing this element as RDF; MUST NOT recurse into related elements."""
        return ((self.name, RDF.type, OWL.Restriction),)


class ObjectSomeValuesFrom(ObjectRestriction):
    """Element ``ObjectSomeValuesFrom( OPE CE )`` in the OWL 2 structural specification.

    The RDF subject is typically an anonymous blank node (written ``_:x`` below).

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty OPE .
        _:x owl:someValuesFrom CE .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectSomeValuesFrom"] = "ObjectSomeValuesFrom"

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


class ObjectAllValuesFrom(ObjectRestriction):
    """Element ``ObjectAllValuesFrom( OPE CE )`` in the OWL 2 structural specification.

    The RDF subject is typically an anonymous blank node (written ``_:x`` below).

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty OPE .
        _:x owl:allValuesFrom CE .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectAllValuesFrom"] = "ObjectAllValuesFrom"

    on_property: N3IRIRef
    all_values_from: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                super().as_triples,
                [
                    (self.name, OWL.onProperty, self.on_property),
                    (self.name, OWL.allValuesFrom, self.all_values_from),
                ],
            ),
        )


class ObjectHasValue(ObjectRestriction):
    """Element ``ObjectHasValue( OPE a )`` in the OWL 2 structural specification.

    The RDF subject is typically an anonymous blank node (written ``_:x`` below).
    ``has_value`` is an individual (IRI or blank node).

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty OPE .
        _:x owl:hasValue a .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectHasValue"] = "ObjectHasValue"

    on_property: N3IRIRef
    has_value: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                super().as_triples,
                [
                    (self.name, OWL.onProperty, self.on_property),
                    (self.name, OWL.hasValue, self.has_value),
                ],
            ),
        )


class ObjectHasSelf(ObjectRestriction):
    """Element ``ObjectHasSelf( OPE )`` in the OWL 2 structural specification.

    The RDF subject is typically an anonymous blank node (written ``_:x`` below).
    The mapping always uses the boolean literal ``"true"^^xsd:boolean``.

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty OPE .
        _:x owl:hasSelf "true"^^xsd:boolean .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectHasSelf"] = "ObjectHasSelf"

    on_property: N3IRIRef

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                super().as_triples,
                [
                    (self.name, OWL.onProperty, self.on_property),
                    (self.name, OWL.hasSelf, _TRUE_BOOLEAN),
                ],
            ),
        )


class ObjectMinCardinality(ObjectRestriction):
    """Element ``ObjectMinCardinality( n OPE )`` in the OWL 2 structural specification.

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty OPE .
        _:x owl:minCardinality "n"^^xsd:nonNegativeInteger .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectMinCardinality"] = "ObjectMinCardinality"

    on_property: N3IRIRef
    min_cardinality: N3Node

    @model_validator(mode="after")
    def _check_cardinality_literal(self) -> Self:
        _require_non_negative_integer_literal(
            self.min_cardinality, label="ObjectMinCardinality.min_cardinality"
        )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                super().as_triples,
                [
                    (self.name, OWL.onProperty, self.on_property),
                    (self.name, OWL.minCardinality, self.min_cardinality),
                ],
            ),
        )


class ObjectMinCardinalityQualified(ObjectRestriction):
    """Element ``ObjectMinCardinality( n OPE CE )`` in the OWL 2 structural specification.

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty OPE .
        _:x owl:minQualifiedCardinality "n"^^xsd:nonNegativeInteger .
        _:x owl:onClass CE .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectMinCardinalityQualified"] = "ObjectMinCardinalityQualified"

    on_property: N3IRIRef
    min_qualified_cardinality: N3Node
    on_class: N3Resource

    @model_validator(mode="after")
    def _check_cardinality_literal(self) -> Self:
        _require_non_negative_integer_literal(
            self.min_qualified_cardinality,
            label="ObjectMinCardinalityQualified.min_qualified_cardinality",
        )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                super().as_triples,
                [
                    (self.name, OWL.onProperty, self.on_property),
                    (
                        self.name,
                        OWL.minQualifiedCardinality,
                        self.min_qualified_cardinality,
                    ),
                    (self.name, OWL.onClass, self.on_class),
                ],
            ),
        )


class ObjectMaxCardinality(ObjectRestriction):
    """Element ``ObjectMaxCardinality( n OPE )`` in the OWL 2 structural specification.

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty OPE .
        _:x owl:maxCardinality "n"^^xsd:nonNegativeInteger .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectMaxCardinality"] = "ObjectMaxCardinality"

    on_property: N3IRIRef
    max_cardinality: N3Node

    @model_validator(mode="after")
    def _check_cardinality_literal(self) -> Self:
        _require_non_negative_integer_literal(
            self.max_cardinality, label="ObjectMaxCardinality.max_cardinality"
        )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                super().as_triples,
                [
                    (self.name, OWL.onProperty, self.on_property),
                    (self.name, OWL.maxCardinality, self.max_cardinality),
                ],
            ),
        )


class ObjectMaxCardinalityQualified(ObjectRestriction):
    """Element ``ObjectMaxCardinality( n OPE CE )`` in the OWL 2 structural specification.

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty OPE .
        _:x owl:maxQualifiedCardinality "n"^^xsd:nonNegativeInteger .
        _:x owl:onClass CE .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectMaxCardinalityQualified"] = "ObjectMaxCardinalityQualified"

    on_property: N3IRIRef
    max_qualified_cardinality: N3Node
    on_class: N3Resource

    @model_validator(mode="after")
    def _check_cardinality_literal(self) -> Self:
        _require_non_negative_integer_literal(
            self.max_qualified_cardinality,
            label="ObjectMaxCardinalityQualified.max_qualified_cardinality",
        )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                super().as_triples,
                [
                    (self.name, OWL.onProperty, self.on_property),
                    (
                        self.name,
                        OWL.maxQualifiedCardinality,
                        self.max_qualified_cardinality,
                    ),
                    (self.name, OWL.onClass, self.on_class),
                ],
            ),
        )


class ObjectExactCardinality(ObjectRestriction):
    """Element ``ObjectExactCardinality( n OPE )`` in the OWL 2 structural specification.

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty OPE .
        _:x owl:cardinality "n"^^xsd:nonNegativeInteger .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectExactCardinality"] = "ObjectExactCardinality"

    on_property: N3IRIRef
    cardinality: N3Node

    @model_validator(mode="after")
    def _check_cardinality_literal(self) -> Self:
        _require_non_negative_integer_literal(
            self.cardinality, label="ObjectExactCardinality.cardinality"
        )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                super().as_triples,
                [
                    (self.name, OWL.onProperty, self.on_property),
                    (self.name, OWL.cardinality, self.cardinality),
                ],
            ),
        )


class ObjectExactCardinalityQualified(ObjectRestriction):
    """Element ``ObjectExactCardinality( n OPE CE )`` in the OWL 2 structural specification.

    Triples::

        _:x rdf:type owl:Restriction .
        _:x owl:onProperty OPE .
        _:x owl:qualifiedCardinality "n"^^xsd:nonNegativeInteger .
        _:x owl:onClass CE .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectExactCardinalityQualified"] = "ObjectExactCardinalityQualified"

    on_property: N3IRIRef
    qualified_cardinality: N3Node
    on_class: N3Resource

    @model_validator(mode="after")
    def _check_cardinality_literal(self) -> Self:
        _require_non_negative_integer_literal(
            self.qualified_cardinality,
            label="ObjectExactCardinalityQualified.qualified_cardinality",
        )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                super().as_triples,
                [
                    (self.name, OWL.onProperty, self.on_property),
                    (
                        self.name,
                        OWL.qualifiedCardinality,
                        self.qualified_cardinality,
                    ),
                    (self.name, OWL.onClass, self.on_class),
                ],
            ),
        )


__all__ = [
    "ObjectAllValuesFrom",
    "ObjectExactCardinality",
    "ObjectExactCardinalityQualified",
    "ObjectHasSelf",
    "ObjectHasValue",
    "ObjectMaxCardinality",
    "ObjectMaxCardinalityQualified",
    "ObjectMinCardinality",
    "ObjectMinCardinalityQualified",
    "ObjectRestriction",
    "ObjectSomeValuesFrom",
]
