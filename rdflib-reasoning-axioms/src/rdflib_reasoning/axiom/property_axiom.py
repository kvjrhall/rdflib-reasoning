"""OWL 2 property, key, and individual-difference structural axioms.

Binary relational axioms mimic :class:`~rdflib_reasoning.axiom.class_axiom.SubClassOf`
(one vocabulary triple over two node references). Seq-backed forms mimic owned-list
patterns such as :class:`~rdflib_reasoning.axiom.object_expression.DisjointUnion`
and :class:`~rdflib_reasoning.axiom.object_expression.DisjointClassesNary`.

Binary relational:

- :class:`SubObjectPropertyOf` --- ``SubObjectPropertyOf( OPE1 OPE2 )``
- :class:`SubDataPropertyOf` --- ``SubDataPropertyOf( DPE1 DPE2 )``
- :class:`ObjectPropertyDomain` / :class:`ObjectPropertyRange`
- :class:`DataPropertyDomain` / :class:`DataPropertyRange`
- :class:`InverseObjectProperties`
- :class:`DatatypeDefinition` --- binary ``DT owl:equivalentClass DR`` only
- :class:`EquivalentObjectProperties` / :class:`EquivalentDataProperties`
  --- binary ``owl:equivalentProperty`` (n-ary forms serialize to chains)
- :class:`DisjointObjectProperties` / :class:`DisjointDataProperties`
- :class:`DifferentIndividuals` --- binary ``owl:differentFrom``
- :class:`SameIndividual` --- binary ``owl:sameAs`` (n-ary forms serialize
  to chains)
- :class:`ObjectPropertyAssertion` --- ``a OPE b`` (resource value; known OPE)
- :class:`DataPropertyAssertion` --- ``a DPE lt`` (literal value; known DPE)
- :class:`NegativeObjectPropertyAssertion` --- reified NPA with ``owl:targetIndividual``
- :class:`NegativeDataPropertyAssertion` --- reified NPA with ``owl:targetValue``

Seq-backed:

- :class:`SubObjectPropertyOfChain` --- ``OPE owl:propertyChainAxiom SEQ``
- :class:`DisjointObjectPropertiesNary` / :class:`DisjointDataPropertiesNary`
- :class:`HasKey` --- ``CE owl:hasKey SEQ``
- :class:`DifferentIndividualsNary` --- ``owl:AllDifferent`` + ``owl:members``
"""

from collections.abc import Sequence
from itertools import chain
from typing import ClassVar, Literal, Self, cast, override

from pydantic import AliasChoices, Field, computed_field, model_validator
from rdflib import OWL, RDF, RDFS, IdentifiedNode
from rdflib import Literal as RDFLiteral

from .common import N3IRIRef, N3Node, N3Resource, Triple
from .structural_element import Seq, StructuralElement


def _seq_operand_count(seq: Seq) -> int:
    """Count of non-sentinel rows in ``seq``."""
    return sum(1 for entry in seq.entries if entry.value is not None)


class SubObjectPropertyOf(StructuralElement):
    """Element ``SubObjectPropertyOf( OPE1 OPE2 )`` of the OWL 2 structural specification.

    Both operands are RDF node references. This is the simple (non-chain) form;
    property chains use :class:`SubObjectPropertyOfChain`.

    Triples::

        OPE1 rdfs:subPropertyOf OPE2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["SubObjectPropertyOf"] = "SubObjectPropertyOf"

    sub_object_property_expression: N3Resource
    super_object_property_expression: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.sub_object_property_expression

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (
                self.sub_object_property_expression,
                RDFS.subPropertyOf,
                self.super_object_property_expression,
            ),
        )


class SubDataPropertyOf(StructuralElement):
    """Element ``SubDataPropertyOf( DPE1 DPE2 )`` of the OWL 2 structural specification.

    Both operands are data property IRIs. The RDF mapping shares
    ``rdfs:subPropertyOf`` with :class:`SubObjectPropertyOf`; graph lifting
    prefers the data form when the subject is typed ``owl:DatatypeProperty``.

    Triples::

        DPE1 rdfs:subPropertyOf DPE2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["SubDataPropertyOf"] = "SubDataPropertyOf"

    sub_data_property_expression: N3IRIRef
    super_data_property_expression: N3IRIRef

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.sub_data_property_expression

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (
                self.sub_data_property_expression,
                RDFS.subPropertyOf,
                self.super_data_property_expression,
            ),
        )


class SubObjectPropertyOfChain(StructuralElement):
    """Element ``SubObjectPropertyOf( ObjectPropertyChain( OPE1 ... OPEn ) OPE )``.

    ``object_property_expression`` is the super-property. ``property_chain`` is
    an owned ``Seq`` of chain operands (``n >= 2``) sharing this element's
    ``context``. The OWL 2 RDF mapping does not emit an ``rdf:type`` triple.

    Triples::

        OPE owl:propertyChainAxiom T(SEQ OPE1 ... OPEn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["SubObjectPropertyOfChain"] = "SubObjectPropertyOfChain"

    object_property_expression: N3Resource
    property_chain: Seq

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.property_chain)
        if n < 2:
            raise ValueError(
                "SubObjectPropertyOfChain requires n >= 2 object property "
                f"operands per the OWL 2 structural specification; got n = {n}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.object_property_expression

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.property_chain.as_triples,
                [
                    (
                        self.object_property_expression,
                        OWL.propertyChainAxiom,
                        self.property_chain.name,
                    )
                ],
            ),
        )


class ObjectPropertyDomain(StructuralElement):
    """Element ``ObjectPropertyDomain( OPE CE )`` of the OWL 2 structural specification.

    Triples::

        OPE rdfs:domain CE .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectPropertyDomain"] = "ObjectPropertyDomain"

    object_property_expression: N3Resource
    class_expression: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.object_property_expression

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return ((self.object_property_expression, RDFS.domain, self.class_expression),)


class ObjectPropertyRange(StructuralElement):
    """Element ``ObjectPropertyRange( OPE CE )`` of the OWL 2 structural specification.

    Triples::

        OPE rdfs:range CE .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectPropertyRange"] = "ObjectPropertyRange"

    object_property_expression: N3Resource
    class_expression: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.object_property_expression

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return ((self.object_property_expression, RDFS.range, self.class_expression),)


class DataPropertyDomain(StructuralElement):
    """Element ``DataPropertyDomain( DPE CE )`` of the OWL 2 structural specification.

    Shares ``rdfs:domain`` with :class:`ObjectPropertyDomain`; lifting prefers
    the data form when the property is typed ``owl:DatatypeProperty``.

    Triples::

        DPE rdfs:domain CE .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataPropertyDomain"] = "DataPropertyDomain"

    data_property_expression: N3IRIRef
    class_expression: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.data_property_expression

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return ((self.data_property_expression, RDFS.domain, self.class_expression),)


class DataPropertyRange(StructuralElement):
    """Element ``DataPropertyRange( DPE DR )`` of the OWL 2 structural specification.

    Shares ``rdfs:range`` with :class:`ObjectPropertyRange`; lifting prefers the
    data form when the property is typed ``owl:DatatypeProperty``.

    Triples::

        DPE rdfs:range DR .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataPropertyRange"] = "DataPropertyRange"

    data_property_expression: N3IRIRef
    data_range: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.data_property_expression

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return ((self.data_property_expression, RDFS.range, self.data_range),)


class InverseObjectProperties(StructuralElement):
    """Element ``InverseObjectProperties( OPE1 OPE2 )`` of the OWL 2 structural specification.

    Triples::

        OPE1 owl:inverseOf OPE2 .

    Note that ``ObjectInverseOf( OP )`` uses the same predicate with a blank-node
    expression subject; graph lifting treats IRI subjects as this axiom.
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["InverseObjectProperties"] = "InverseObjectProperties"

    object_property_expression_1: N3Resource
    object_property_expression_2: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.object_property_expression_1

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (
                self.object_property_expression_1,
                OWL.inverseOf,
                self.object_property_expression_2,
            ),
        )


class DatatypeDefinition(StructuralElement):
    """Element ``DatatypeDefinition( DT DR )`` of the OWL 2 structural specification.

    Binary form only: a single ``owl:equivalentClass`` triple. Shares that
    predicate with binary
    :class:`~rdflib_reasoning.axiom.object_expression.EquivalentClasses`; graph
    lifting prefers this class when the subject is typed ``rdfs:Datatype``.

    Triples::

        DT owl:equivalentClass DR .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DatatypeDefinition"] = "DatatypeDefinition"

    datatype: N3IRIRef
    data_range: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.datatype

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return ((self.datatype, OWL.equivalentClass, self.data_range),)


class EquivalentObjectProperties(StructuralElement):
    """Element ``EquivalentObjectProperties( OPE1 OPE2 )`` of the OWL 2 structural specification.

    Binary form only. An n-ary structural equivalence axiom serializes to
    multiple ``owl:equivalentProperty`` triples; reverse parse yields binaries.
    Shares that predicate with :class:`EquivalentDataProperties`.

    Triples::

        OPE1 owl:equivalentProperty OPE2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["EquivalentObjectProperties"] = "EquivalentObjectProperties"

    object_property_expression_1: N3Resource
    object_property_expression_2: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.object_property_expression_1

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (
                self.object_property_expression_1,
                OWL.equivalentProperty,
                self.object_property_expression_2,
            ),
        )


class EquivalentDataProperties(StructuralElement):
    """Element ``EquivalentDataProperties( DPE1 DPE2 )`` of the OWL 2 structural specification.

    Binary form only. Shares ``owl:equivalentProperty`` with
    :class:`EquivalentObjectProperties`; lifting prefers the data form when the
    subject is typed ``owl:DatatypeProperty``.

    Triples::

        DPE1 owl:equivalentProperty DPE2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["EquivalentDataProperties"] = "EquivalentDataProperties"

    data_property_expression_1: N3IRIRef
    data_property_expression_2: N3IRIRef

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.data_property_expression_1

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (
                self.data_property_expression_1,
                OWL.equivalentProperty,
                self.data_property_expression_2,
            ),
        )


class DisjointObjectProperties(StructuralElement):
    """Element ``DisjointObjectProperties( OPE1 OPE2 )`` of the OWL 2 structural specification.

    Triples::

        OPE1 owl:propertyDisjointWith OPE2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DisjointObjectProperties"] = "DisjointObjectProperties"

    object_property_expression_1: N3Resource
    object_property_expression_2: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.object_property_expression_1

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (
                self.object_property_expression_1,
                OWL.propertyDisjointWith,
                self.object_property_expression_2,
            ),
        )


class DisjointDataProperties(StructuralElement):
    """Element ``DisjointDataProperties( DPE1 DPE2 )`` of the OWL 2 structural specification.

    Shares ``owl:propertyDisjointWith`` with :class:`DisjointObjectProperties`;
    lifting prefers the data form when the subject is typed
    ``owl:DatatypeProperty``.

    Triples::

        DPE1 owl:propertyDisjointWith DPE2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DisjointDataProperties"] = "DisjointDataProperties"

    data_property_expression_1: N3IRIRef
    data_property_expression_2: N3IRIRef

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.data_property_expression_1

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (
                self.data_property_expression_1,
                OWL.propertyDisjointWith,
                self.data_property_expression_2,
            ),
        )


class DisjointObjectPropertiesNary(StructuralElement):
    """Element ``DisjointObjectProperties( OPE1 ... OPEn )``, n > 2.

    The RDF subject is typically an anonymous blank node of type
    ``owl:AllDisjointProperties``. ``members`` is an owned ``Seq`` fragment.

    Triples::

        _:x rdf:type owl:AllDisjointProperties .
        _:x owl:members T(SEQ OPE1 ... OPEn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DisjointObjectPropertiesNary"] = "DisjointObjectPropertiesNary"

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
                "DisjointObjectPropertiesNary requires n > 2 object property "
                f"operands per the OWL 2 structural specification; got n = {n}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        """AllDisjointProperties node identifier (alias of ``name_value``)."""
        return self.name_value

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.members.as_triples,
                [
                    (self.name, RDF.type, OWL.AllDisjointProperties),
                    (self.name, OWL.members, self.members.name),
                ],
            ),
        )


class DisjointDataPropertiesNary(StructuralElement):
    """Element ``DisjointDataProperties( DPE1 ... DPEn )``, n > 2.

    Shares the ``owl:AllDisjointProperties`` mapping with
    :class:`DisjointObjectPropertiesNary`; lifting prefers the data form when
    members are typed ``owl:DatatypeProperty``.

    Triples::

        _:x rdf:type owl:AllDisjointProperties .
        _:x owl:members T(SEQ DPE1 ... DPEn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DisjointDataPropertiesNary"] = "DisjointDataPropertiesNary"

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
                "DisjointDataPropertiesNary requires n > 2 data property "
                f"operands per the OWL 2 structural specification; got n = {n}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        """AllDisjointProperties node identifier (alias of ``name_value``)."""
        return self.name_value

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.members.as_triples,
                [
                    (self.name, RDF.type, OWL.AllDisjointProperties),
                    (self.name, OWL.members, self.members.name),
                ],
            ),
        )


class HasKey(StructuralElement):
    """Element ``HasKey( CE ( OPE1 ... OPEm ) ( DPE1 ... DPEn ) )``.

    ``class_expression`` is the key-bearing class. ``key_properties`` is an owned
    ``Seq`` of property node references (object and/or data properties concatenated
    as in the OWL 2 RDF mapping). At least one key property is required.

    Triples::

        CE owl:hasKey T(SEQ OPE1 ... OPEm DPE1 ... DPEn) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["HasKey"] = "HasKey"

    class_expression: N3Resource
    key_properties: Seq

    @model_validator(mode="after")
    def _check_arity(self) -> Self:
        n = _seq_operand_count(self.key_properties)
        if n < 1:
            raise ValueError(
                "HasKey requires at least one key property operand per the OWL 2 "
                f"structural specification; got n = {n}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.class_expression

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.key_properties.as_triples,
                [(self.class_expression, OWL.hasKey, self.key_properties.name)],
            ),
        )


class ObjectPropertyAssertion(StructuralElement):
    """Element ``ObjectPropertyAssertion( OPE a1 a2 )`` of the OWL 2 structural specification.

    Binary RDF form ``a1 OPE a2`` with a resource (individual) value. Graph
    lifting claims a triple only when ``OPE`` is a known object property
    expression (declaration, object-property characteristic, object restriction
    ``onProperty``, ``ObjectInverseOf`` blank node, or OPE operand of an
    already-parsed axiom). Unknown predicates remain unconsumed.

    Triples::

        a1 OPE a2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["ObjectPropertyAssertion"] = "ObjectPropertyAssertion"

    object_property_expression: N3Resource
    individual: N3Resource
    value: N3Resource

    @model_validator(mode="after")
    def _require_resource_value(self) -> Self:
        if not isinstance(self.value, IdentifiedNode):
            raise ValueError(
                "ObjectPropertyAssertion value MUST be an RDF resource "
                f"(IdentifiedNode); got {type(self.value).__name__}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.individual

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        # OPE may be a blank-node ObjectInverseOf; Triple's predicate alias is
        # URIRef-narrow for typical RDF, so cast the generalized OWL shape.
        return cast(
            Sequence[Triple],
            ((self.individual, self.object_property_expression, self.value),),
        )


class DataPropertyAssertion(StructuralElement):
    """Element ``DataPropertyAssertion( DPE a lt )`` of the OWL 2 structural specification.

    Binary RDF form ``a DPE lt`` with a literal value. Graph lifting claims a
    triple only when ``DPE`` is a known data property expression (declaration,
    data restriction ``onProperty`` / ``onProperties``, or DPE operand of an
    already-parsed axiom). Unknown predicates remain unconsumed.

    Triples::

        a DPE lt .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DataPropertyAssertion"] = "DataPropertyAssertion"

    data_property_expression: N3IRIRef
    individual: N3Resource
    value: N3Node

    @model_validator(mode="after")
    def _require_literal_value(self) -> Self:
        if not isinstance(self.value, RDFLiteral):
            raise ValueError(
                "DataPropertyAssertion value MUST be an RDF literal; got "
                f"{type(self.value).__name__}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.individual

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return ((self.individual, self.data_property_expression, self.value),)


class NegativeObjectPropertyAssertion(StructuralElement):
    """Element ``NegativeObjectPropertyAssertion( OPE a1 a2 )`` of the OWL 2 structural specification.

    Reified RDF form headed by ``owl:NegativePropertyAssertion`` with a resource
    ``owl:targetIndividual``. Graph lifting claims a node only when
    ``owl:assertionProperty`` is a known object property expression. Nodes that
    use ``owl:targetValue`` are claimed as
    :class:`NegativeDataPropertyAssertion` instead.

    Triples::

        _:x rdf:type owl:NegativePropertyAssertion .
        _:x owl:sourceIndividual a1 .
        _:x owl:assertionProperty OPE .
        _:x owl:targetIndividual a2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["NegativeObjectPropertyAssertion"] = "NegativeObjectPropertyAssertion"

    name_value: N3Resource = Field(
        ...,
        validation_alias=AliasChoices("name", "name_value"),
        serialization_alias="name",
    )
    object_property_expression: N3Resource
    individual: N3Resource
    value: N3Resource

    @model_validator(mode="after")
    def _require_resource_value(self) -> Self:
        if not isinstance(self.value, IdentifiedNode):
            raise ValueError(
                "NegativeObjectPropertyAssertion value MUST be an RDF resource "
                f"(IdentifiedNode); got {type(self.value).__name__}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        """NegativePropertyAssertion node identifier (alias of ``name_value``)."""
        return self.name_value

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (self.name, RDF.type, OWL.NegativePropertyAssertion),
            (self.name, OWL.sourceIndividual, self.individual),
            (self.name, OWL.assertionProperty, self.object_property_expression),
            (self.name, OWL.targetIndividual, self.value),
        )


class NegativeDataPropertyAssertion(StructuralElement):
    """Element ``NegativeDataPropertyAssertion( DPE a lt )`` of the OWL 2 structural specification.

    Reified RDF form headed by ``owl:NegativePropertyAssertion`` with a literal
    ``owl:targetValue``. Graph lifting claims a node only when
    ``owl:assertionProperty`` is a known data property expression. Nodes that
    use ``owl:targetIndividual`` are claimed as
    :class:`NegativeObjectPropertyAssertion` instead.

    Triples::

        _:x rdf:type owl:NegativePropertyAssertion .
        _:x owl:sourceIndividual a .
        _:x owl:assertionProperty DPE .
        _:x owl:targetValue lt .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["NegativeDataPropertyAssertion"] = "NegativeDataPropertyAssertion"

    name_value: N3Resource = Field(
        ...,
        validation_alias=AliasChoices("name", "name_value"),
        serialization_alias="name",
    )
    data_property_expression: N3IRIRef
    individual: N3Resource
    value: N3Node

    @model_validator(mode="after")
    def _require_literal_value(self) -> Self:
        if not isinstance(self.value, RDFLiteral):
            raise ValueError(
                "NegativeDataPropertyAssertion value MUST be an RDF literal; got "
                f"{type(self.value).__name__}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        """NegativePropertyAssertion node identifier (alias of ``name_value``)."""
        return self.name_value

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return (
            (self.name, RDF.type, OWL.NegativePropertyAssertion),
            (self.name, OWL.sourceIndividual, self.individual),
            (self.name, OWL.assertionProperty, self.data_property_expression),
            (self.name, OWL.targetValue, self.value),
        )


class DifferentIndividuals(StructuralElement):
    """Element ``DifferentIndividuals( a1 a2 )`` of the OWL 2 structural specification.

    Triples::

        a1 owl:differentFrom a2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DifferentIndividuals"] = "DifferentIndividuals"

    individual_1: N3Resource
    individual_2: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.individual_1

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return ((self.individual_1, OWL.differentFrom, self.individual_2),)


class SameIndividual(StructuralElement):
    """Element ``SameIndividual( a1 a2 )`` of the OWL 2 structural specification.

    Binary form only. An n-ary structural ``SameIndividual( a1 ... an )``
    serializes to n-1 ``owl:sameAs`` triples; reverse parse yields binaries.

    Triples::

        a1 owl:sameAs a2 .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["SameIndividual"] = "SameIndividual"

    individual_1: N3Resource
    individual_2: N3Resource

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        return self.individual_1

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return ((self.individual_1, OWL.sameAs, self.individual_2),)


class DifferentIndividualsNary(StructuralElement):
    """Element ``DifferentIndividuals( a1 ... an )``, n > 2.

    Serializes with the OWL 2 RDF forward-mapping form ``owl:members``.
    Graph lifting also accepts the OWL 1 legacy reverse-mapping form
    ``owl:distinctMembers`` for the same structural axiom; round-trip
    therefore normalizes legacy graphs to ``owl:members``.

    Triples::

        _:x rdf:type owl:AllDifferent .
        _:x owl:members T(SEQ a1 ... an) .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["DifferentIndividualsNary"] = "DifferentIndividualsNary"

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
                "DifferentIndividualsNary requires n > 2 individual operands "
                f"per the OWL 2 structural specification; got n = {n}."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def name(self) -> IdentifiedNode:
        """AllDifferent node identifier (alias of ``name_value``)."""
        return self.name_value

    @computed_field  # type: ignore[prop-decorator]
    @property
    @override
    def as_triples(self) -> Sequence[Triple]:
        return tuple(
            chain(
                self.members.as_triples,
                [
                    (self.name, RDF.type, OWL.AllDifferent),
                    (self.name, OWL.members, self.members.name),
                ],
            ),
        )


__all__ = [
    "DataPropertyAssertion",
    "DataPropertyDomain",
    "DataPropertyRange",
    "DatatypeDefinition",
    "DifferentIndividuals",
    "DifferentIndividualsNary",
    "DisjointDataProperties",
    "DisjointDataPropertiesNary",
    "DisjointObjectProperties",
    "DisjointObjectPropertiesNary",
    "EquivalentDataProperties",
    "EquivalentObjectProperties",
    "HasKey",
    "InverseObjectProperties",
    "NegativeDataPropertyAssertion",
    "NegativeObjectPropertyAssertion",
    "ObjectPropertyAssertion",
    "ObjectPropertyDomain",
    "ObjectPropertyRange",
    "SameIndividual",
    "SubDataPropertyOf",
    "SubObjectPropertyOf",
    "SubObjectPropertyOfChain",
]
