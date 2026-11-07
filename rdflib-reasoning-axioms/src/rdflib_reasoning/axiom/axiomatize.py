"""Lift supported RDF graph patterns into structural elements.

The public entry point is :func:`axiomatize`, which partitions a graph into the
currently implemented ``StructuralElement`` models. The implementation uses
RDFLib graph triple-pattern lookup rather than SPARQL or a secondary in-memory
index.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final

from pydantic import ValidationError
from rdflib import OWL, RDF, RDFS, XSD, Graph, IdentifiedNode, Literal, Node, URIRef

from .class_axiom import ClassAssertion, DeclarationClass, SubClassOf
from .common import Triple
from .datatype import (
    DataAllValuesFrom,
    DataAllValuesFromNary,
    DataComplementOf,
    DataExactCardinality,
    DataExactCardinalityQualified,
    DataHasValue,
    DataIntersectionOf,
    DataMaxCardinality,
    DataMaxCardinalityQualified,
    DataMinCardinality,
    DataMinCardinalityQualified,
    DataOneOf,
    DataSomeValuesFrom,
    DataSomeValuesFromNary,
    DatatypeRestriction,
    DataUnionOf,
    DeclarationDatatype,
    FacetEntry,
    FacetList,
)
from .declaration import (
    DeclarationAnnotationProperty,
    DeclarationDataProperty,
    DeclarationObjectProperty,
    NamedIndividual,
)
from .object_expression import (
    ClassExpression,
    DisjointClasses,
    DisjointClassesNary,
    DisjointUnion,
    EquivalentClasses,
    ObjectComplementOf,
    ObjectIntersectionOf,
    ObjectInverseOf,
    ObjectOneOf,
    ObjectUnionOf,
)
from .property_axiom import (
    DataPropertyDomain,
    DataPropertyRange,
    DatatypeDefinition,
    DifferentIndividuals,
    DifferentIndividualsNary,
    DisjointDataProperties,
    DisjointDataPropertiesNary,
    DisjointObjectProperties,
    DisjointObjectPropertiesNary,
    EquivalentDataProperties,
    EquivalentObjectProperties,
    HasKey,
    InverseObjectProperties,
    ObjectPropertyDomain,
    ObjectPropertyRange,
    SameIndividual,
    SubDataPropertyOf,
    SubObjectPropertyOf,
    SubObjectPropertyOfChain,
)
from .property_characteristic import (
    AsymmetricObjectProperty,
    FunctionalDataProperty,
    FunctionalObjectProperty,
    InverseFunctionalObjectProperty,
    IrreflexiveObjectProperty,
    ReflexiveObjectProperty,
    SymmetricObjectProperty,
    TransitiveObjectProperty,
)
from .restriction import (
    ObjectAllValuesFrom,
    ObjectExactCardinality,
    ObjectExactCardinalityQualified,
    ObjectHasSelf,
    ObjectHasValue,
    ObjectMaxCardinality,
    ObjectMaxCardinalityQualified,
    ObjectMinCardinality,
    ObjectMinCardinalityQualified,
    ObjectRestriction,
    ObjectSomeValuesFrom,
)
from .structural_element import Seq, SeqEntry, StructuralElement

_STRUCTURAL_LIST_PREDICATES: Final[frozenset[URIRef]] = frozenset({RDF.first, RDF.rest})
_OBJECT_PROPERTY_TYPE_HINTS: Final[frozenset[URIRef]] = frozenset(
    {
        OWL.ObjectProperty,
        OWL.InverseFunctionalProperty,
        OWL.ReflexiveProperty,
        OWL.IrreflexiveProperty,
        OWL.SymmetricProperty,
        OWL.AsymmetricProperty,
        OWL.TransitiveProperty,
    }
)
_TRUE_BOOLEAN: Final[Literal] = Literal(True, datatype=XSD.boolean)


class AxiomatizationError(ValueError):
    """Base class for graph-to-structural-element lifting errors."""


class UnsupportedGraphError(AxiomatizationError):
    """Raised when graph content is outside the supported v1 axiomatization."""


class MalformedGraphError(AxiomatizationError):
    """Raised when a recognized supported pattern has an invalid RDF shape."""


@dataclass(frozen=True)
class _RDFListCell:
    cell: IdentifiedNode
    value: Node
    first_triple: Triple
    rest_triple: Triple


@dataclass
class _Axiomatizer:
    graph: Graph
    triples: frozenset[Triple]
    context: IdentifiedNode
    consumed: set[Triple] = field(default_factory=set)
    elements: list[StructuralElement] = field(default_factory=list)

    def run(self) -> tuple[StructuralElement, ...]:
        # Richer expression / axiom patterns first; declaration-shaped fallbacks last.
        self._parse_data_intersections()
        self._parse_object_intersections()
        self._parse_data_unions()
        self._parse_object_unions()
        self._parse_data_complements()
        self._parse_object_complements()
        self._parse_data_one_ofs()
        self._parse_object_one_ofs()
        self._parse_datatype_restrictions()
        self._parse_object_has_selfs()
        self._parse_has_values()
        self._parse_qualified_cardinalities()
        self._parse_unqualified_cardinalities()
        self._parse_some_values_froms()
        self._parse_all_values_froms()
        self._parse_inverse_object_properties()
        self._parse_object_inverse_ofs()
        self._parse_disjoint_unions()
        self._parse_disjoint_classes_nary()
        self._parse_disjoint_object_properties_nary()
        self._parse_different_individuals_nary()
        self._parse_disjoint_classes()
        self._parse_subclass_axioms()
        self._parse_sub_property_axioms()
        self._parse_property_chain_axioms()
        self._parse_property_domain_axioms()
        self._parse_property_range_axioms()
        self._parse_property_disjoint_with_axioms()
        self._parse_equivalent_class_axioms()
        self._parse_equivalent_property_axioms()
        self._parse_has_keys()
        self._parse_different_individuals()
        self._parse_same_individuals()
        self._parse_inverse_functional_object_properties()
        self._parse_reflexive_object_properties()
        self._parse_irreflexive_object_properties()
        self._parse_symmetric_object_properties()
        self._parse_asymmetric_object_properties()
        self._parse_transitive_object_properties()
        self._parse_functional_properties()
        self._parse_declaration_datatypes()
        self._parse_declaration_classes()
        self._parse_declaration_object_properties()
        self._parse_declaration_data_properties()
        self._parse_declaration_annotation_properties()
        self._parse_named_individuals()
        self._parse_class_assertions()
        self._raise_if_unconsumed_triples()
        return tuple(sorted(self.elements, key=_element_sort_key))

    def _parse_data_intersections(self) -> None:
        for subject in self._subjects_for_predicate(OWL.intersectionOf):
            if self._has(subject, RDF.type, RDFS.Datatype):
                type_triple, owner_triple, seq, seq_triples = (
                    self._parse_seq_data_range_parts(
                        subject=subject,
                        predicate=OWL.intersectionOf,
                        label="DataIntersectionOf",
                    )
                )
                element = self._build_element(
                    "DataIntersectionOf",
                    DataIntersectionOf,
                    context=self.context,
                    name_value=subject,
                    intersection_of=seq,
                )
                self._add_element(element, type_triple, owner_triple, *seq_triples)

    def _parse_object_intersections(self) -> None:
        for subject in self._subjects_for_predicate(OWL.intersectionOf):
            if self._has(subject, RDF.type, OWL.Class):
                type_triple, owner_triple, seq, seq_triples = (
                    self._parse_seq_class_expression_parts(
                        subject=subject,
                        predicate=OWL.intersectionOf,
                        label="ObjectIntersectionOf",
                    )
                )
                element = self._build_element(
                    "ObjectIntersectionOf",
                    ObjectIntersectionOf,
                    context=self.context,
                    name_value=subject,
                    intersection_of=seq,
                )
                self._add_element(element, type_triple, owner_triple, *seq_triples)

    def _parse_data_unions(self) -> None:
        for subject in self._subjects_for_predicate(OWL.unionOf):
            if self._has(subject, RDF.type, RDFS.Datatype):
                type_triple, owner_triple, seq, seq_triples = (
                    self._parse_seq_data_range_parts(
                        subject=subject,
                        predicate=OWL.unionOf,
                        label="DataUnionOf",
                    )
                )
                element = self._build_element(
                    "DataUnionOf",
                    DataUnionOf,
                    context=self.context,
                    name_value=subject,
                    union_of=seq,
                )
                self._add_element(element, type_triple, owner_triple, *seq_triples)

    def _parse_object_unions(self) -> None:
        for subject in self._subjects_for_predicate(OWL.unionOf):
            if self._has(subject, RDF.type, OWL.Class):
                type_triple, owner_triple, seq, seq_triples = (
                    self._parse_seq_class_expression_parts(
                        subject=subject,
                        predicate=OWL.unionOf,
                        label="ObjectUnionOf",
                    )
                )
                element = self._build_element(
                    "ObjectUnionOf",
                    ObjectUnionOf,
                    context=self.context,
                    name_value=subject,
                    union_of=seq,
                )
                self._add_element(element, type_triple, owner_triple, *seq_triples)

    def _parse_seq_data_range_parts(
        self,
        *,
        subject: IdentifiedNode,
        predicate: URIRef,
        label: str,
    ) -> tuple[Triple, Triple, Seq, tuple[Triple, ...]]:
        type_triple = self._require_triple(subject, RDF.type, RDFS.Datatype)
        list_head, owner_triple = self._require_single_object(
            subject,
            predicate,
            label=label,
        )
        if not isinstance(list_head, IdentifiedNode):
            raise MalformedGraphError(
                f"{label} list head MUST be an RDF resource; got "
                f"{_format_node(list_head)}."
            )
        seq, seq_triples = self._parse_seq(list_head, label=label)
        for value in _seq_values(seq):
            if not isinstance(value, IdentifiedNode):
                raise MalformedGraphError(
                    f"{label} data range operands MUST be RDF resources; got "
                    f"{_format_node(value)}."
                )
        return type_triple, owner_triple, seq, seq_triples

    def _parse_seq_class_expression_parts(
        self,
        *,
        subject: IdentifiedNode,
        predicate: URIRef,
        label: str,
    ) -> tuple[Triple, Triple, Seq, tuple[Triple, ...]]:
        type_triple = self._require_triple(subject, RDF.type, OWL.Class)
        list_head, owner_triple = self._require_single_object(
            subject,
            predicate,
            label=label,
        )
        if not isinstance(list_head, IdentifiedNode):
            raise MalformedGraphError(
                f"{label} list head MUST be an RDF resource; got "
                f"{_format_node(list_head)}."
            )
        seq, seq_triples = self._parse_seq(list_head, label=label)
        for value in _seq_values(seq):
            if not isinstance(value, IdentifiedNode):
                raise MalformedGraphError(
                    f"{label} class expression operands MUST be RDF resources; "
                    f"got {_format_node(value)}."
                )
        return type_triple, owner_triple, seq, seq_triples

    def _parse_data_complements(self) -> None:
        for subject in self._subjects_for_predicate(OWL.complementOf):
            if not self._has(subject, RDF.type, RDFS.Datatype):
                continue
            type_triple = self._require_triple(subject, RDF.type, RDFS.Datatype)
            complement_of, complement_triple = self._require_single_object(
                subject,
                OWL.complementOf,
                label="DataComplementOf",
            )
            if not isinstance(complement_of, IdentifiedNode):
                raise MalformedGraphError(
                    "DataComplementOf operand MUST be an RDF resource; got "
                    f"{_format_node(complement_of)}."
                )
            element = self._build_element(
                "DataComplementOf",
                DataComplementOf,
                context=self.context,
                name_value=subject,
                complement_of=complement_of,
            )
            self._add_element(element, type_triple, complement_triple)

    def _parse_object_complements(self) -> None:
        for subject in self._subjects_for_predicate(OWL.complementOf):
            if not self._has(subject, RDF.type, OWL.Class):
                continue
            type_triple = self._require_triple(subject, RDF.type, OWL.Class)
            complement_of, complement_triple = self._require_single_object(
                subject,
                OWL.complementOf,
                label="ObjectComplementOf",
            )
            if not isinstance(complement_of, IdentifiedNode):
                raise MalformedGraphError(
                    "ObjectComplementOf operand MUST be an RDF resource; got "
                    f"{_format_node(complement_of)}."
                )
            element = self._build_element(
                "ObjectComplementOf",
                ObjectComplementOf,
                context=self.context,
                name_value=subject,
                complement_of=complement_of,
            )
            self._add_element(element, type_triple, complement_triple)

    def _parse_data_one_ofs(self) -> None:
        for subject in self._subjects_for_predicate(OWL.oneOf):
            if not self._has(subject, RDF.type, RDFS.Datatype):
                continue
            type_triple = self._require_triple(subject, RDF.type, RDFS.Datatype)
            list_head, one_of_triple = self._require_single_object(
                subject,
                OWL.oneOf,
                label="DataOneOf",
            )
            if not isinstance(list_head, IdentifiedNode):
                raise MalformedGraphError(
                    "DataOneOf list head MUST be an RDF resource; got "
                    f"{_format_node(list_head)}."
                )
            seq, seq_triples = self._parse_seq(list_head, label="DataOneOf")
            for value in _seq_values(seq):
                if not isinstance(value, Literal):
                    raise MalformedGraphError(
                        "DataOneOf list members MUST be literals; got "
                        f"{_format_node(value)}."
                    )
            element = self._build_element(
                "DataOneOf",
                DataOneOf,
                context=self.context,
                name_value=subject,
                one_of=seq,
            )
            self._add_element(element, type_triple, one_of_triple, *seq_triples)

    def _parse_object_one_ofs(self) -> None:
        for subject in self._subjects_for_predicate(OWL.oneOf):
            if not self._has(subject, RDF.type, OWL.Class):
                continue
            type_triple = self._require_triple(subject, RDF.type, OWL.Class)
            list_head, one_of_triple = self._require_single_object(
                subject,
                OWL.oneOf,
                label="ObjectOneOf",
            )
            if not isinstance(list_head, IdentifiedNode):
                raise MalformedGraphError(
                    "ObjectOneOf list head MUST be an RDF resource; got "
                    f"{_format_node(list_head)}."
                )
            seq, seq_triples = self._parse_seq(list_head, label="ObjectOneOf")
            for value in _seq_values(seq):
                if not isinstance(value, IdentifiedNode):
                    raise MalformedGraphError(
                        "ObjectOneOf list members MUST be individuals "
                        f"(RDF resources); got {_format_node(value)}."
                    )
            element = self._build_element(
                "ObjectOneOf",
                ObjectOneOf,
                context=self.context,
                name_value=subject,
                one_of=seq,
            )
            self._add_element(element, type_triple, one_of_triple, *seq_triples)

    def _parse_inverse_object_properties(self) -> None:
        """Lift IRI-subject ``owl:inverseOf`` as ``InverseObjectProperties``.

        Blank-node subjects are left for :meth:`_parse_object_inverse_ofs`
        (``ObjectInverseOf`` expression form).
        """
        triples = sorted(self._match(predicate=OWL.inverseOf), key=_triple_key)
        for triple in triples:
            if triple in self.consumed:
                continue
            subject, _, object_ = triple
            if not isinstance(subject, URIRef):
                continue
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "InverseObjectProperties operand MUST be an RDF resource; "
                    f"got {_format_node(object_)}."
                )
            element = self._build_element(
                "InverseObjectProperties",
                InverseObjectProperties,
                context=self.context,
                object_property_expression_1=subject,
                object_property_expression_2=object_,
            )
            self._add_element(element, triple)

    def _parse_object_inverse_ofs(self) -> None:
        """Lift blank-node-subject ``owl:inverseOf`` as ``ObjectInverseOf``.

        IRI subjects are claimed earlier by :meth:`_parse_inverse_object_properties`.
        """
        triples = sorted(self._match(predicate=OWL.inverseOf), key=_triple_key)
        for triple in triples:
            if triple in self.consumed:
                continue
            subject, _, object_ = triple
            if isinstance(subject, URIRef):
                continue
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "ObjectInverseOf operand MUST be an RDF resource; got "
                    f"{_format_node(object_)}."
                )
            element = self._build_element(
                "ObjectInverseOf",
                ObjectInverseOf,
                context=self.context,
                name_value=subject,
                inverse_of=object_,
            )
            self._add_element(element, triple)

    def _parse_disjoint_unions(self) -> None:
        for subject in self._subjects_for_predicate(OWL.disjointUnionOf):
            list_head, owner_triple = self._require_single_object(
                subject,
                OWL.disjointUnionOf,
                label="DisjointUnion",
            )
            if not isinstance(list_head, IdentifiedNode):
                raise MalformedGraphError(
                    "DisjointUnion list head MUST be an RDF resource; got "
                    f"{_format_node(list_head)}."
                )
            seq, seq_triples = self._parse_seq(list_head, label="DisjointUnion")
            for value in _seq_values(seq):
                if not isinstance(value, IdentifiedNode):
                    raise MalformedGraphError(
                        "DisjointUnion class expression operands MUST be RDF "
                        f"resources; got {_format_node(value)}."
                    )
            element = self._build_element(
                "DisjointUnion",
                DisjointUnion,
                context=self.context,
                union_class=subject,
                disjoint_union_of=seq,
            )
            self._add_element(element, owner_triple, *seq_triples)

    def _parse_disjoint_classes_nary(self) -> None:
        triples = sorted(
            self._match(predicate=RDF.type, object_=OWL.AllDisjointClasses),
            key=_triple_key,
        )
        for type_triple in triples:
            if type_triple in self.consumed:
                continue
            subject = type_triple[0]
            list_head, members_triple = self._require_single_object(
                subject,
                OWL.members,
                label="DisjointClassesNary",
            )
            if not isinstance(list_head, IdentifiedNode):
                raise MalformedGraphError(
                    "DisjointClassesNary members list head MUST be an RDF "
                    f"resource; got {_format_node(list_head)}."
                )
            seq, seq_triples = self._parse_seq(
                list_head,
                label="DisjointClassesNary",
            )
            for value in _seq_values(seq):
                if not isinstance(value, IdentifiedNode):
                    raise MalformedGraphError(
                        "DisjointClassesNary class expression operands MUST be "
                        f"RDF resources; got {_format_node(value)}."
                    )
            element = self._build_element(
                "DisjointClassesNary",
                DisjointClassesNary,
                context=self.context,
                name_value=subject,
                members=seq,
            )
            self._add_element(element, type_triple, members_triple, *seq_triples)

    def _parse_disjoint_object_properties_nary(self) -> None:
        triples = sorted(
            self._match(predicate=RDF.type, object_=OWL.AllDisjointProperties),
            key=_triple_key,
        )
        for type_triple in triples:
            if type_triple in self.consumed:
                continue
            subject = type_triple[0]
            list_head, members_triple = self._require_single_object(
                subject,
                OWL.members,
                label="DisjointObjectPropertiesNary",
            )
            if not isinstance(list_head, IdentifiedNode):
                raise MalformedGraphError(
                    "AllDisjointProperties members list head MUST be an RDF "
                    f"resource; got {_format_node(list_head)}."
                )
            seq, seq_triples = self._parse_seq(
                list_head,
                label="AllDisjointProperties",
            )
            for value in _seq_values(seq):
                if not isinstance(value, IdentifiedNode):
                    raise MalformedGraphError(
                        "AllDisjointProperties members MUST be RDF resources; "
                        f"got {_format_node(value)}."
                    )
            if self._seq_members_are_data_properties(seq):
                element = self._build_element(
                    "DisjointDataPropertiesNary",
                    DisjointDataPropertiesNary,
                    context=self.context,
                    name_value=subject,
                    members=seq,
                )
            else:
                element = self._build_element(
                    "DisjointObjectPropertiesNary",
                    DisjointObjectPropertiesNary,
                    context=self.context,
                    name_value=subject,
                    members=seq,
                )
            self._add_element(element, type_triple, members_triple, *seq_triples)

    def _parse_different_individuals_nary(self) -> None:
        triples = sorted(
            self._match(predicate=RDF.type, object_=OWL.AllDifferent),
            key=_triple_key,
        )
        for type_triple in triples:
            if type_triple in self.consumed:
                continue
            subject = type_triple[0]
            if self._has_any(subject, OWL.distinctMembers):
                raise UnsupportedGraphError(
                    "DifferentIndividualsNary via owl:distinctMembers is not "
                    f"supported; use owl:members at {_format_node(subject)}."
                )
            list_head, members_triple = self._require_single_object(
                subject,
                OWL.members,
                label="DifferentIndividualsNary",
            )
            if not isinstance(list_head, IdentifiedNode):
                raise MalformedGraphError(
                    "DifferentIndividualsNary members list head MUST be an RDF "
                    f"resource; got {_format_node(list_head)}."
                )
            seq, seq_triples = self._parse_seq(
                list_head,
                label="DifferentIndividualsNary",
            )
            for value in _seq_values(seq):
                if not isinstance(value, IdentifiedNode):
                    raise MalformedGraphError(
                        "DifferentIndividualsNary members MUST be RDF "
                        f"resources; got {_format_node(value)}."
                    )
            element = self._build_element(
                "DifferentIndividualsNary",
                DifferentIndividualsNary,
                context=self.context,
                name_value=subject,
                members=seq,
            )
            self._add_element(element, type_triple, members_triple, *seq_triples)

    def _parse_disjoint_classes(self) -> None:
        triples = sorted(self._match(predicate=OWL.disjointWith), key=_triple_key)
        for triple in triples:
            subject, _, object_ = triple
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "DisjointClasses class expression MUST be an RDF resource; "
                    f"got {_format_node(object_)}."
                )
            element = self._build_element(
                "DisjointClasses",
                DisjointClasses,
                context=self.context,
                class_expression_1=subject,
                class_expression_2=object_,
            )
            self._add_element(element, triple)

    def _parse_datatype_restrictions(self) -> None:
        for subject in self._subjects_for_predicate(OWL.withRestrictions):
            if not self._has(subject, RDF.type, RDFS.Datatype):
                continue
            type_triple = self._require_triple(subject, RDF.type, RDFS.Datatype)
            on_datatype, on_datatype_triple = self._require_single_object(
                subject,
                OWL.onDatatype,
                label="DatatypeRestriction",
            )
            if not isinstance(on_datatype, URIRef):
                raise MalformedGraphError(
                    "DatatypeRestriction owl:onDatatype object MUST be an IRI; got "
                    f"{_format_node(on_datatype)}."
                )
            list_head, with_restrictions_triple = self._require_single_object(
                subject,
                OWL.withRestrictions,
                label="DatatypeRestriction",
            )
            if not isinstance(list_head, IdentifiedNode):
                raise MalformedGraphError(
                    "DatatypeRestriction facet list head MUST be an RDF resource; got "
                    f"{_format_node(list_head)}."
                )
            facets, facet_triples = self._parse_facet_list(
                list_head,
                label="DatatypeRestriction",
            )
            element = self._build_element(
                "DatatypeRestriction",
                DatatypeRestriction,
                context=self.context,
                name_value=subject,
                on_datatype=on_datatype,
                with_restrictions=facets,
            )
            self._add_element(
                element,
                type_triple,
                on_datatype_triple,
                with_restrictions_triple,
                *facet_triples,
            )

    def _parse_object_has_selfs(self) -> None:
        for subject in self._subjects_for_predicate(OWL.hasSelf):
            if not self._has(subject, RDF.type, OWL.Restriction):
                continue
            type_triple = self._require_triple(subject, RDF.type, OWL.Restriction)
            on_property, on_property_triple = self._require_single_object(
                subject,
                OWL.onProperty,
                label="ObjectHasSelf",
            )
            if not isinstance(on_property, URIRef):
                raise MalformedGraphError(
                    "ObjectHasSelf owl:onProperty object MUST be an IRI; got "
                    f"{_format_node(on_property)}."
                )
            has_self, has_self_triple = self._require_single_object(
                subject,
                OWL.hasSelf,
                label="ObjectHasSelf",
            )
            if has_self != _TRUE_BOOLEAN:
                raise MalformedGraphError(
                    "ObjectHasSelf owl:hasSelf object MUST be "
                    '"true"^^xsd:boolean; got '
                    f"{_format_node(has_self)}."
                )
            element = self._build_element(
                "ObjectHasSelf",
                ObjectHasSelf,
                context=self.context,
                name_value=subject,
                on_property=on_property,
            )
            self._add_element(
                element,
                type_triple,
                on_property_triple,
                has_self_triple,
            )

    def _parse_has_values(self) -> None:
        for subject in self._subjects_for_predicate(OWL.hasValue):
            if not self._has(subject, RDF.type, OWL.Restriction):
                continue
            type_triple = self._require_triple(subject, RDF.type, OWL.Restriction)
            on_property, on_property_triple = self._require_single_object(
                subject,
                OWL.onProperty,
                label="HasValue",
            )
            if not isinstance(on_property, URIRef):
                raise MalformedGraphError(
                    "HasValue owl:onProperty object MUST be an IRI; got "
                    f"{_format_node(on_property)}."
                )
            has_value, has_value_triple = self._require_single_object(
                subject,
                OWL.hasValue,
                label="HasValue",
            )
            if isinstance(has_value, Literal):
                element = self._build_element(
                    "DataHasValue",
                    DataHasValue,
                    context=self.context,
                    name_value=subject,
                    on_property=on_property,
                    has_value=has_value,
                )
            elif isinstance(has_value, IdentifiedNode):
                element = self._build_element(
                    "ObjectHasValue",
                    ObjectHasValue,
                    context=self.context,
                    name_value=subject,
                    on_property=on_property,
                    has_value=has_value,
                )
            else:
                raise MalformedGraphError(
                    "HasValue owl:hasValue object MUST be an RDF resource or "
                    f"literal; got {_format_node(has_value)}."
                )
            self._add_element(
                element,
                type_triple,
                on_property_triple,
                has_value_triple,
            )

    def _parse_qualified_cardinalities(self) -> None:
        self._parse_qualified_cardinality_family(
            cardinality_predicate=OWL.minQualifiedCardinality,
            object_label="ObjectMinCardinalityQualified",
            object_cls=ObjectMinCardinalityQualified,
            object_field="min_qualified_cardinality",
            data_label="DataMinCardinalityQualified",
            data_cls=DataMinCardinalityQualified,
            data_field="min_qualified_cardinality",
        )
        self._parse_qualified_cardinality_family(
            cardinality_predicate=OWL.maxQualifiedCardinality,
            object_label="ObjectMaxCardinalityQualified",
            object_cls=ObjectMaxCardinalityQualified,
            object_field="max_qualified_cardinality",
            data_label="DataMaxCardinalityQualified",
            data_cls=DataMaxCardinalityQualified,
            data_field="max_qualified_cardinality",
        )
        self._parse_qualified_cardinality_family(
            cardinality_predicate=OWL.qualifiedCardinality,
            object_label="ObjectExactCardinalityQualified",
            object_cls=ObjectExactCardinalityQualified,
            object_field="qualified_cardinality",
            data_label="DataExactCardinalityQualified",
            data_cls=DataExactCardinalityQualified,
            data_field="qualified_cardinality",
        )

    def _parse_qualified_cardinality_family(
        self,
        *,
        cardinality_predicate: URIRef,
        object_label: str,
        object_cls: Callable[..., StructuralElement],
        object_field: str,
        data_label: str,
        data_cls: Callable[..., StructuralElement],
        data_field: str,
    ) -> None:
        for subject in self._subjects_for_predicate(cardinality_predicate):
            if not self._has(subject, RDF.type, OWL.Restriction):
                continue
            has_on_class = self._has_any(subject, OWL.onClass)
            has_on_data_range = self._has_any(subject, OWL.onDataRange)
            if has_on_class and has_on_data_range:
                raise MalformedGraphError(
                    f"{object_label}/{data_label} subject cannot use both "
                    f"owl:onClass and owl:onDataRange: {_format_node(subject)}."
                )
            if not has_on_class and not has_on_data_range:
                raise MalformedGraphError(
                    f"Qualified cardinality at {_format_node(subject)} MUST "
                    "include owl:onClass or owl:onDataRange."
                )
            type_triple = self._require_triple(subject, RDF.type, OWL.Restriction)
            on_property, on_property_triple = self._require_single_object(
                subject,
                OWL.onProperty,
                label=object_label if has_on_class else data_label,
            )
            if not isinstance(on_property, URIRef):
                raise MalformedGraphError(
                    "Qualified cardinality owl:onProperty object MUST be an IRI; "
                    f"got {_format_node(on_property)}."
                )
            cardinality, cardinality_triple = self._require_single_object(
                subject,
                cardinality_predicate,
                label=object_label if has_on_class else data_label,
            )
            if has_on_class:
                on_class, qualifier_triple = self._require_single_object(
                    subject,
                    OWL.onClass,
                    label=object_label,
                )
                if not isinstance(on_class, IdentifiedNode):
                    raise MalformedGraphError(
                        f"{object_label} owl:onClass object MUST be an RDF "
                        f"resource; got {_format_node(on_class)}."
                    )
                element = self._build_element(
                    object_label,
                    object_cls,
                    context=self.context,
                    name_value=subject,
                    on_property=on_property,
                    on_class=on_class,
                    **{object_field: cardinality},
                )
            else:
                on_data_range, qualifier_triple = self._require_single_object(
                    subject,
                    OWL.onDataRange,
                    label=data_label,
                )
                if not isinstance(on_data_range, IdentifiedNode):
                    raise MalformedGraphError(
                        f"{data_label} owl:onDataRange object MUST be an RDF "
                        f"resource; got {_format_node(on_data_range)}."
                    )
                element = self._build_element(
                    data_label,
                    data_cls,
                    context=self.context,
                    name_value=subject,
                    on_property=on_property,
                    on_data_range=on_data_range,
                    **{data_field: cardinality},
                )
            self._add_element(
                element,
                type_triple,
                on_property_triple,
                cardinality_triple,
                qualifier_triple,
            )

    def _parse_unqualified_cardinalities(self) -> None:
        self._parse_unqualified_cardinality_family(
            cardinality_predicate=OWL.minCardinality,
            object_label="ObjectMinCardinality",
            object_cls=ObjectMinCardinality,
            object_field="min_cardinality",
            data_label="DataMinCardinality",
            data_cls=DataMinCardinality,
            data_field="min_cardinality",
        )
        self._parse_unqualified_cardinality_family(
            cardinality_predicate=OWL.maxCardinality,
            object_label="ObjectMaxCardinality",
            object_cls=ObjectMaxCardinality,
            object_field="max_cardinality",
            data_label="DataMaxCardinality",
            data_cls=DataMaxCardinality,
            data_field="max_cardinality",
        )
        self._parse_unqualified_cardinality_family(
            cardinality_predicate=OWL.cardinality,
            object_label="ObjectExactCardinality",
            object_cls=ObjectExactCardinality,
            object_field="cardinality",
            data_label="DataExactCardinality",
            data_cls=DataExactCardinality,
            data_field="cardinality",
        )

    def _parse_unqualified_cardinality_family(
        self,
        *,
        cardinality_predicate: URIRef,
        object_label: str,
        object_cls: Callable[..., StructuralElement],
        object_field: str,
        data_label: str,
        data_cls: Callable[..., StructuralElement],
        data_field: str,
    ) -> None:
        for subject in self._subjects_for_predicate(cardinality_predicate):
            if not self._has(subject, RDF.type, OWL.Restriction):
                continue
            # Qualified forms also use a distinct predicate; skip if already claimed.
            type_probe = (subject, RDF.type, OWL.Restriction)
            if type_probe in self.consumed:
                continue
            type_triple = self._require_triple(subject, RDF.type, OWL.Restriction)
            on_property, on_property_triple = self._require_single_object(
                subject,
                OWL.onProperty,
                label="Cardinality",
            )
            if not isinstance(on_property, URIRef):
                raise MalformedGraphError(
                    "Cardinality owl:onProperty object MUST be an IRI; got "
                    f"{_format_node(on_property)}."
                )
            cardinality, cardinality_triple = self._require_single_object(
                subject,
                cardinality_predicate,
                label="Cardinality",
            )
            family = self._restriction_property_family(on_property)
            if family == "object":
                element = self._build_element(
                    object_label,
                    object_cls,
                    context=self.context,
                    name_value=subject,
                    on_property=on_property,
                    **{object_field: cardinality},
                )
            else:
                element = self._build_element(
                    data_label,
                    data_cls,
                    context=self.context,
                    name_value=subject,
                    on_property=on_property,
                    **{data_field: cardinality},
                )
            self._add_element(
                element,
                type_triple,
                on_property_triple,
                cardinality_triple,
            )

    def _parse_some_values_froms(self) -> None:
        for subject in self._subjects_for_predicate(OWL.someValuesFrom):
            if not self._has(subject, RDF.type, OWL.Restriction):
                continue
            has_on_property = self._has_any(subject, OWL.onProperty)
            has_on_properties = self._has_any(subject, OWL.onProperties)
            if has_on_property and has_on_properties:
                raise MalformedGraphError(
                    "SomeValuesFrom subject cannot use both owl:onProperty "
                    f"and owl:onProperties: {_format_node(subject)}."
                )
            if has_on_properties:
                self._parse_data_some_values_from_nary(subject)
            elif has_on_property:
                self._parse_some_values_from_unary(subject)

    def _parse_some_values_from_unary(self, subject: IdentifiedNode) -> None:
        type_triple = self._require_triple(subject, RDF.type, OWL.Restriction)
        on_property, on_property_triple = self._require_single_object(
            subject,
            OWL.onProperty,
            label="SomeValuesFrom",
        )
        if not isinstance(on_property, URIRef):
            raise MalformedGraphError(
                "SomeValuesFrom owl:onProperty object MUST be an IRI; got "
                f"{_format_node(on_property)}."
            )
        some_values_from, some_values_from_triple = self._require_single_object(
            subject,
            OWL.someValuesFrom,
            label="SomeValuesFrom",
        )
        if not isinstance(some_values_from, IdentifiedNode):
            raise MalformedGraphError(
                "SomeValuesFrom owl:someValuesFrom object MUST be an RDF "
                f"resource; got {_format_node(some_values_from)}."
            )
        if self._restriction_property_family(on_property) == "object":
            element = self._build_element(
                "ObjectSomeValuesFrom",
                ObjectSomeValuesFrom,
                context=self.context,
                name_value=subject,
                on_property=on_property,
                some_values_from=some_values_from,
            )
        else:
            element = self._build_element(
                "DataSomeValuesFrom",
                DataSomeValuesFrom,
                context=self.context,
                name_value=subject,
                on_property=on_property,
                some_values_from=some_values_from,
            )
        self._add_element(
            element,
            type_triple,
            on_property_triple,
            some_values_from_triple,
        )

    def _parse_data_some_values_from_nary(self, subject: IdentifiedNode) -> None:
        type_triple = self._require_triple(subject, RDF.type, OWL.Restriction)
        list_head, on_properties_triple = self._require_single_object(
            subject,
            OWL.onProperties,
            label="DataSomeValuesFromNary",
        )
        if not isinstance(list_head, IdentifiedNode):
            raise MalformedGraphError(
                "DataSomeValuesFromNary property list head MUST be an RDF "
                f"resource; got {_format_node(list_head)}."
            )
        some_values_from, some_values_from_triple = self._require_single_object(
            subject,
            OWL.someValuesFrom,
            label="DataSomeValuesFromNary",
        )
        if not isinstance(some_values_from, IdentifiedNode):
            raise MalformedGraphError(
                "DataSomeValuesFromNary owl:someValuesFrom object MUST be an "
                f"RDF resource; got {_format_node(some_values_from)}."
            )
        seq, seq_triples = self._parse_seq(
            list_head,
            label="DataSomeValuesFromNary",
        )
        self._require_uri_seq_values(seq, label="DataSomeValuesFromNary")
        element = self._build_element(
            "DataSomeValuesFromNary",
            DataSomeValuesFromNary,
            context=self.context,
            name_value=subject,
            on_properties=seq,
            some_values_from=some_values_from,
        )
        self._add_element(
            element,
            type_triple,
            on_properties_triple,
            some_values_from_triple,
            *seq_triples,
        )

    def _parse_all_values_froms(self) -> None:
        for subject in self._subjects_for_predicate(OWL.allValuesFrom):
            if not self._has(subject, RDF.type, OWL.Restriction):
                continue
            has_on_property = self._has_any(subject, OWL.onProperty)
            has_on_properties = self._has_any(subject, OWL.onProperties)
            if has_on_property and has_on_properties:
                raise MalformedGraphError(
                    "AllValuesFrom subject cannot use both owl:onProperty "
                    f"and owl:onProperties: {_format_node(subject)}."
                )
            if has_on_properties:
                self._parse_data_all_values_from_nary(subject)
            elif has_on_property:
                self._parse_all_values_from_unary(subject)

    def _parse_all_values_from_unary(self, subject: IdentifiedNode) -> None:
        type_triple = self._require_triple(subject, RDF.type, OWL.Restriction)
        on_property, on_property_triple = self._require_single_object(
            subject,
            OWL.onProperty,
            label="AllValuesFrom",
        )
        if not isinstance(on_property, URIRef):
            raise MalformedGraphError(
                "AllValuesFrom owl:onProperty object MUST be an IRI; got "
                f"{_format_node(on_property)}."
            )
        all_values_from, all_values_from_triple = self._require_single_object(
            subject,
            OWL.allValuesFrom,
            label="AllValuesFrom",
        )
        if not isinstance(all_values_from, IdentifiedNode):
            raise MalformedGraphError(
                "AllValuesFrom owl:allValuesFrom object MUST be an RDF "
                f"resource; got {_format_node(all_values_from)}."
            )
        if self._restriction_property_family(on_property) == "object":
            element = self._build_element(
                "ObjectAllValuesFrom",
                ObjectAllValuesFrom,
                context=self.context,
                name_value=subject,
                on_property=on_property,
                all_values_from=all_values_from,
            )
        else:
            element = self._build_element(
                "DataAllValuesFrom",
                DataAllValuesFrom,
                context=self.context,
                name_value=subject,
                on_property=on_property,
                all_values_from=all_values_from,
            )
        self._add_element(
            element,
            type_triple,
            on_property_triple,
            all_values_from_triple,
        )

    def _parse_data_all_values_from_nary(self, subject: IdentifiedNode) -> None:
        type_triple = self._require_triple(subject, RDF.type, OWL.Restriction)
        list_head, on_properties_triple = self._require_single_object(
            subject,
            OWL.onProperties,
            label="DataAllValuesFromNary",
        )
        if not isinstance(list_head, IdentifiedNode):
            raise MalformedGraphError(
                "DataAllValuesFromNary property list head MUST be an RDF "
                f"resource; got {_format_node(list_head)}."
            )
        all_values_from, all_values_from_triple = self._require_single_object(
            subject,
            OWL.allValuesFrom,
            label="DataAllValuesFromNary",
        )
        if not isinstance(all_values_from, IdentifiedNode):
            raise MalformedGraphError(
                "DataAllValuesFromNary owl:allValuesFrom object MUST be an RDF "
                f"resource; got {_format_node(all_values_from)}."
            )
        seq, seq_triples = self._parse_seq(
            list_head,
            label="DataAllValuesFromNary",
        )
        self._require_uri_seq_values(seq, label="DataAllValuesFromNary")
        element = self._build_element(
            "DataAllValuesFromNary",
            DataAllValuesFromNary,
            context=self.context,
            name_value=subject,
            on_properties=seq,
            all_values_from=all_values_from,
        )
        self._add_element(
            element,
            type_triple,
            on_properties_triple,
            all_values_from_triple,
            *seq_triples,
        )

    def _restriction_property_family(self, prop: Node) -> str:
        r"""Return ``"object"`` or ``"data"`` for ambiguous restriction shapes.

        Uses co-occurring property typing in the input graph (looked up, not
        consumed). Untyped properties default to the data family so existing
        ``DataSomeValuesFrom`` round-trips remain stable.
        """
        if not isinstance(prop, IdentifiedNode):
            return "data"
        is_data = self._has(prop, RDF.type, OWL.DatatypeProperty)
        is_object = any(
            self._has(prop, RDF.type, hint) for hint in _OBJECT_PROPERTY_TYPE_HINTS
        )
        if self._has(prop, RDF.type, OWL.FunctionalProperty) and not is_data:
            is_object = True
        if is_object and is_data:
            raise MalformedGraphError(
                "Restriction onProperty cannot be typed as both object and data "
                f"property: {_format_node(prop)}."
            )
        if is_object:
            return "object"
        return "data"

    def _parse_declaration_datatypes(self) -> None:
        self._parse_rdf_type_elements(
            RDFS.Datatype,
            "DeclarationDatatype",
            DeclarationDatatype,
        )

    def _parse_subclass_axioms(self) -> None:
        triples = sorted(self._match(predicate=RDFS.subClassOf), key=_triple_key)
        for triple in triples:
            subject, _, object_ = triple
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "SubClassOf super class expression MUST be an RDF resource; "
                    f"got {_format_node(object_)}."
                )
            element = self._build_element(
                "SubClassOf",
                SubClassOf,
                context=self.context,
                sub_class_expression=subject,
                super_class_expression=object_,
            )
            self._add_element(element, triple)

    def _parse_sub_property_axioms(self) -> None:
        triples = sorted(self._match(predicate=RDFS.subPropertyOf), key=_triple_key)
        for triple in triples:
            subject, _, object_ = triple
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "SubPropertyOf super property expression MUST be an RDF "
                    f"resource; got {_format_node(object_)}."
                )
            if self._is_data_property(subject):
                if not isinstance(object_, URIRef):
                    raise MalformedGraphError(
                        "SubDataPropertyOf super property MUST be an IRI; got "
                        f"{_format_node(object_)}."
                    )
                element = self._build_element(
                    "SubDataPropertyOf",
                    SubDataPropertyOf,
                    context=self.context,
                    sub_data_property_expression=subject,
                    super_data_property_expression=object_,
                )
            else:
                element = self._build_element(
                    "SubObjectPropertyOf",
                    SubObjectPropertyOf,
                    context=self.context,
                    sub_object_property_expression=subject,
                    super_object_property_expression=object_,
                )
            self._add_element(element, triple)

    def _parse_property_chain_axioms(self) -> None:
        for subject in self._subjects_for_predicate(OWL.propertyChainAxiom):
            list_head, owner_triple = self._require_single_object(
                subject,
                OWL.propertyChainAxiom,
                label="SubObjectPropertyOfChain",
            )
            if not isinstance(list_head, IdentifiedNode):
                raise MalformedGraphError(
                    "SubObjectPropertyOfChain list head MUST be an RDF "
                    f"resource; got {_format_node(list_head)}."
                )
            seq, seq_triples = self._parse_seq(
                list_head,
                label="SubObjectPropertyOfChain",
            )
            for value in _seq_values(seq):
                if not isinstance(value, IdentifiedNode):
                    raise MalformedGraphError(
                        "SubObjectPropertyOfChain operands MUST be RDF "
                        f"resources; got {_format_node(value)}."
                    )
            element = self._build_element(
                "SubObjectPropertyOfChain",
                SubObjectPropertyOfChain,
                context=self.context,
                object_property_expression=subject,
                property_chain=seq,
            )
            self._add_element(element, owner_triple, *seq_triples)

    def _parse_property_domain_axioms(self) -> None:
        triples = sorted(self._match(predicate=RDFS.domain), key=_triple_key)
        for triple in triples:
            subject, _, object_ = triple
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "Property domain class expression MUST be an RDF resource; "
                    f"got {_format_node(object_)}."
                )
            if self._is_data_property(subject):
                element = self._build_element(
                    "DataPropertyDomain",
                    DataPropertyDomain,
                    context=self.context,
                    data_property_expression=subject,
                    class_expression=object_,
                )
            else:
                element = self._build_element(
                    "ObjectPropertyDomain",
                    ObjectPropertyDomain,
                    context=self.context,
                    object_property_expression=subject,
                    class_expression=object_,
                )
            self._add_element(element, triple)

    def _parse_property_range_axioms(self) -> None:
        triples = sorted(self._match(predicate=RDFS.range), key=_triple_key)
        for triple in triples:
            subject, _, object_ = triple
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "Property range expression MUST be an RDF resource; got "
                    f"{_format_node(object_)}."
                )
            if self._is_data_property(subject):
                element = self._build_element(
                    "DataPropertyRange",
                    DataPropertyRange,
                    context=self.context,
                    data_property_expression=subject,
                    data_range=object_,
                )
            else:
                element = self._build_element(
                    "ObjectPropertyRange",
                    ObjectPropertyRange,
                    context=self.context,
                    object_property_expression=subject,
                    class_expression=object_,
                )
            self._add_element(element, triple)

    def _parse_property_disjoint_with_axioms(self) -> None:
        triples = sorted(
            self._match(predicate=OWL.propertyDisjointWith),
            key=_triple_key,
        )
        for triple in triples:
            subject, _, object_ = triple
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "propertyDisjointWith operand MUST be an RDF resource; got "
                    f"{_format_node(object_)}."
                )
            if self._is_data_property(subject):
                if not isinstance(object_, URIRef):
                    raise MalformedGraphError(
                        "DisjointDataProperties operand MUST be an IRI; got "
                        f"{_format_node(object_)}."
                    )
                element = self._build_element(
                    "DisjointDataProperties",
                    DisjointDataProperties,
                    context=self.context,
                    data_property_expression_1=subject,
                    data_property_expression_2=object_,
                )
            else:
                element = self._build_element(
                    "DisjointObjectProperties",
                    DisjointObjectProperties,
                    context=self.context,
                    object_property_expression_1=subject,
                    object_property_expression_2=object_,
                )
            self._add_element(element, triple)

    def _parse_equivalent_class_axioms(self) -> None:
        """Lift ``owl:equivalentClass`` as DatatypeDefinition or EquivalentClasses.

        Prefer ``DatatypeDefinition`` when the subject is typed ``rdfs:Datatype``
        (and is an IRI). Otherwise lift as binary ``EquivalentClasses``. Raise
        when both ``rdfs:Datatype`` and ``owl:Class`` typing are present.
        """
        triples = sorted(self._match(predicate=OWL.equivalentClass), key=_triple_key)
        for triple in triples:
            if triple in self.consumed:
                continue
            subject, _, object_ = triple
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "owl:equivalentClass object MUST be an RDF resource; got "
                    f"{_format_node(object_)}."
                )
            is_datatype = self._has(subject, RDF.type, RDFS.Datatype)
            is_class = self._has(subject, RDF.type, OWL.Class)
            if is_datatype and is_class:
                raise MalformedGraphError(
                    "owl:equivalentClass subject cannot be typed as both "
                    f"rdfs:Datatype and owl:Class: {_format_node(subject)}."
                )
            if is_datatype:
                if not isinstance(subject, URIRef):
                    raise MalformedGraphError(
                        "DatatypeDefinition datatype MUST be an IRI; got "
                        f"{_format_node(subject)}."
                    )
                element = self._build_element(
                    "DatatypeDefinition",
                    DatatypeDefinition,
                    context=self.context,
                    datatype=subject,
                    data_range=object_,
                )
            else:
                element = self._build_element(
                    "EquivalentClasses",
                    EquivalentClasses,
                    context=self.context,
                    class_expression_1=subject,
                    class_expression_2=object_,
                )
            self._add_element(element, triple)

    def _parse_equivalent_property_axioms(self) -> None:
        """Lift ``owl:equivalentProperty`` as object or data equivalence.

        Prefer ``EquivalentDataProperties`` when the subject is typed
        ``owl:DatatypeProperty``; otherwise lift as
        ``EquivalentObjectProperties``.
        """
        triples = sorted(
            self._match(predicate=OWL.equivalentProperty),
            key=_triple_key,
        )
        for triple in triples:
            if triple in self.consumed:
                continue
            subject, _, object_ = triple
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "owl:equivalentProperty operand MUST be an RDF resource; got "
                    f"{_format_node(object_)}."
                )
            if self._is_data_property(subject):
                if not isinstance(subject, URIRef) or not isinstance(object_, URIRef):
                    raise MalformedGraphError(
                        "EquivalentDataProperties operands MUST be IRIs; got "
                        f"{_format_node(subject)} / {_format_node(object_)}."
                    )
                element = self._build_element(
                    "EquivalentDataProperties",
                    EquivalentDataProperties,
                    context=self.context,
                    data_property_expression_1=subject,
                    data_property_expression_2=object_,
                )
            else:
                element = self._build_element(
                    "EquivalentObjectProperties",
                    EquivalentObjectProperties,
                    context=self.context,
                    object_property_expression_1=subject,
                    object_property_expression_2=object_,
                )
            self._add_element(element, triple)

    def _parse_has_keys(self) -> None:
        for subject in self._subjects_for_predicate(OWL.hasKey):
            list_head, owner_triple = self._require_single_object(
                subject,
                OWL.hasKey,
                label="HasKey",
            )
            if not isinstance(list_head, IdentifiedNode):
                raise MalformedGraphError(
                    "HasKey property list head MUST be an RDF resource; got "
                    f"{_format_node(list_head)}."
                )
            seq, seq_triples = self._parse_seq(list_head, label="HasKey")
            for value in _seq_values(seq):
                if not isinstance(value, IdentifiedNode):
                    raise MalformedGraphError(
                        "HasKey key properties MUST be RDF resources; got "
                        f"{_format_node(value)}."
                    )
            element = self._build_element(
                "HasKey",
                HasKey,
                context=self.context,
                class_expression=subject,
                key_properties=seq,
            )
            self._add_element(element, owner_triple, *seq_triples)

    def _parse_different_individuals(self) -> None:
        triples = sorted(self._match(predicate=OWL.differentFrom), key=_triple_key)
        for triple in triples:
            subject, _, object_ = triple
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "DifferentIndividuals operand MUST be an RDF resource; got "
                    f"{_format_node(object_)}."
                )
            element = self._build_element(
                "DifferentIndividuals",
                DifferentIndividuals,
                context=self.context,
                individual_1=subject,
                individual_2=object_,
            )
            self._add_element(element, triple)

    def _parse_same_individuals(self) -> None:
        triples = sorted(self._match(predicate=OWL.sameAs), key=_triple_key)
        for triple in triples:
            subject, _, object_ = triple
            if not isinstance(object_, IdentifiedNode):
                raise MalformedGraphError(
                    "SameIndividual operand MUST be an RDF resource; got "
                    f"{_format_node(object_)}."
                )
            element = self._build_element(
                "SameIndividual",
                SameIndividual,
                context=self.context,
                individual_1=subject,
                individual_2=object_,
            )
            self._add_element(element, triple)

    def _is_data_property(self, node: IdentifiedNode) -> bool:
        """Return True when ``node`` is typed ``owl:DatatypeProperty`` in the graph."""
        return self._has(node, RDF.type, OWL.DatatypeProperty)

    def _seq_members_are_data_properties(self, seq: Seq) -> bool:
        values = _seq_values(seq)
        if not values:
            return False
        return all(
            isinstance(value, IdentifiedNode) and self._is_data_property(value)
            for value in values
        )

    def _parse_declaration_classes(self) -> None:
        self._parse_rdf_type_elements(
            OWL.Class,
            "DeclarationClass",
            DeclarationClass,
        )

    def _parse_inverse_functional_object_properties(self) -> None:
        self._parse_rdf_type_elements(
            OWL.InverseFunctionalProperty,
            "InverseFunctionalObjectProperty",
            InverseFunctionalObjectProperty,
        )

    def _parse_reflexive_object_properties(self) -> None:
        self._parse_rdf_type_elements(
            OWL.ReflexiveProperty,
            "ReflexiveObjectProperty",
            ReflexiveObjectProperty,
        )

    def _parse_irreflexive_object_properties(self) -> None:
        self._parse_rdf_type_elements(
            OWL.IrreflexiveProperty,
            "IrreflexiveObjectProperty",
            IrreflexiveObjectProperty,
        )

    def _parse_symmetric_object_properties(self) -> None:
        self._parse_rdf_type_elements(
            OWL.SymmetricProperty,
            "SymmetricObjectProperty",
            SymmetricObjectProperty,
        )

    def _parse_asymmetric_object_properties(self) -> None:
        self._parse_rdf_type_elements(
            OWL.AsymmetricProperty,
            "AsymmetricObjectProperty",
            AsymmetricObjectProperty,
        )

    def _parse_transitive_object_properties(self) -> None:
        self._parse_rdf_type_elements(
            OWL.TransitiveProperty,
            "TransitiveObjectProperty",
            TransitiveObjectProperty,
        )

    def _parse_functional_properties(self) -> None:
        """Lift ``owl:FunctionalProperty`` as object or data characteristic.

        ``FunctionalObjectProperty`` and ``FunctionalDataProperty`` share this
        RDF type. Prefer the data form when the subject is also typed
        ``owl:DatatypeProperty``; otherwise lift as the object form.
        """
        triples = sorted(
            self._match(predicate=RDF.type, object_=OWL.FunctionalProperty),
            key=_triple_key,
        )
        for triple in triples:
            if triple in self.consumed:
                continue
            subject = triple[0]
            if self._has(subject, RDF.type, OWL.DatatypeProperty):
                element = self._build_element(
                    "FunctionalDataProperty",
                    FunctionalDataProperty,
                    context=self.context,
                    name_value=subject,
                )
            else:
                element = self._build_element(
                    "FunctionalObjectProperty",
                    FunctionalObjectProperty,
                    context=self.context,
                    name_value=subject,
                )
            self._add_element(element, triple)

    def _parse_declaration_object_properties(self) -> None:
        self._parse_rdf_type_elements(
            OWL.ObjectProperty,
            "DeclarationObjectProperty",
            DeclarationObjectProperty,
        )

    def _parse_declaration_data_properties(self) -> None:
        self._parse_rdf_type_elements(
            OWL.DatatypeProperty,
            "DeclarationDataProperty",
            DeclarationDataProperty,
        )

    def _parse_declaration_annotation_properties(self) -> None:
        self._parse_rdf_type_elements(
            OWL.AnnotationProperty,
            "DeclarationAnnotationProperty",
            DeclarationAnnotationProperty,
        )

    def _parse_named_individuals(self) -> None:
        self._parse_rdf_type_elements(
            OWL.NamedIndividual,
            "NamedIndividual",
            NamedIndividual,
        )

    def _known_class_expressions(self) -> set[IdentifiedNode]:
        """Return nodes known to be class expressions for ClassAssertion gating.

        Seeds builtins ``owl:Thing`` / ``owl:Nothing``, then harvests CE names and
        CE operands from already-parsed structural elements (declarations,
        class expressions / restrictions, and CE-bearing axioms).
        """
        known: set[IdentifiedNode] = {OWL.Thing, OWL.Nothing}

        def add(node: Node) -> None:
            if isinstance(node, IdentifiedNode):
                known.add(node)

        def add_seq_members(seq: Seq) -> None:
            for value in _seq_values(seq):
                add(value)

        for element in self.elements:
            if isinstance(
                element, (DeclarationClass, ClassExpression, ObjectRestriction)
            ):
                add(element.name)
            if isinstance(element, SubClassOf):
                add(element.sub_class_expression)
                add(element.super_class_expression)
            elif isinstance(element, EquivalentClasses):
                add(element.class_expression_1)
                add(element.class_expression_2)
            elif isinstance(element, DisjointClasses):
                add(element.class_expression_1)
                add(element.class_expression_2)
            elif isinstance(element, DisjointClassesNary):
                add_seq_members(element.members)
            elif isinstance(element, DisjointUnion):
                add(element.union_class)
                add_seq_members(element.disjoint_union_of)
            elif isinstance(element, ObjectComplementOf):
                add(element.complement_of)
            elif isinstance(element, ObjectIntersectionOf):
                add_seq_members(element.intersection_of)
            elif isinstance(element, ObjectUnionOf):
                add_seq_members(element.union_of)
            elif isinstance(element, (ObjectPropertyDomain, ObjectPropertyRange)):
                add(element.class_expression)
            elif isinstance(element, DataPropertyDomain):
                add(element.class_expression)
            elif isinstance(element, HasKey):
                add(element.class_expression)
            elif isinstance(element, ObjectSomeValuesFrom):
                add(element.some_values_from)
            elif isinstance(element, ObjectAllValuesFrom):
                add(element.all_values_from)
            elif isinstance(
                element,
                (
                    ObjectMinCardinalityQualified,
                    ObjectMaxCardinalityQualified,
                    ObjectExactCardinalityQualified,
                ),
            ):
                add(element.on_class)
        return known

    def _parse_class_assertions(self) -> None:
        """Lift ``x rdf:type y`` when ``y`` is a known class expression."""
        known = self._known_class_expressions()
        triples = sorted(self._match(predicate=RDF.type), key=_triple_key)
        for triple in triples:
            if triple in self.consumed:
                continue
            subject, _, object_ = triple
            if not isinstance(object_, IdentifiedNode):
                continue
            if object_ not in known:
                continue
            element = self._build_element(
                "ClassAssertion",
                ClassAssertion,
                context=self.context,
                individual=subject,
                class_expression=object_,
            )
            self._add_element(element, triple)

    def _parse_rdf_type_elements(
        self,
        rdf_type: IdentifiedNode,
        label: str,
        constructor: Callable[..., StructuralElement],
    ) -> None:
        triples = sorted(
            self._match(predicate=RDF.type, object_=rdf_type),
            key=_triple_key,
        )
        for triple in triples:
            if triple in self.consumed:
                continue
            element = self._build_element(
                label,
                constructor,
                context=self.context,
                name_value=triple[0],
            )
            self._add_element(element, triple)

    def _parse_seq(
        self,
        head: IdentifiedNode,
        *,
        label: str,
    ) -> tuple[Seq, tuple[Triple, ...]]:
        cells, triples = self._walk_rdf_list(head, label=label)
        entries = tuple(
            [SeqEntry(cell=cell.cell, value=cell.value) for cell in cells]
            + [SeqEntry(cell=RDF.nil, value=None)]
        )
        try:
            seq = Seq(context=self.context, entries=entries)
        except ValidationError as cause:
            raise MalformedGraphError(f"Malformed {label} rdf:List: {cause}") from cause
        return seq, triples

    def _parse_facet_list(
        self,
        head: IdentifiedNode,
        *,
        label: str,
    ) -> tuple[FacetList, tuple[Triple, ...]]:
        cells, list_triples = self._walk_rdf_list(head, label=label)
        entries: list[FacetEntry] = []
        facet_triples: list[Triple] = []
        for cell in cells:
            anchor = cell.value
            if not isinstance(anchor, IdentifiedNode):
                raise MalformedGraphError(
                    f"{label} facet anchor MUST be an RDF resource; got "
                    f"{_format_node(anchor)}."
                )
            candidates = tuple(
                triple
                for triple in self._match(subject=anchor)
                if triple[1] not in _STRUCTURAL_LIST_PREDICATES
            )
            if len(candidates) != 1:
                raise MalformedGraphError(
                    f"{label} facet anchor {_format_node(anchor)} MUST have "
                    f"exactly one facet predicate/value triple; found "
                    f"{len(candidates)}."
                )
            facet_triple = candidates[0]
            if facet_triple in self.consumed:
                raise MalformedGraphError(
                    f"{label} facet anchor {_format_node(anchor)} is already "
                    "owned by another structural element."
                )
            entries.append(
                FacetEntry(
                    cell=cell.cell,
                    anchor=anchor,
                    facet=facet_triple[1],
                    value=facet_triple[2],
                )
            )
            facet_triples.append(facet_triple)

        entries.append(FacetEntry(cell=RDF.nil, anchor=None, facet=None, value=None))
        try:
            facet_list = FacetList(context=self.context, entries=tuple(entries))
        except ValidationError as cause:
            raise MalformedGraphError(
                f"Malformed {label} FacetList: {cause}"
            ) from cause
        return facet_list, (*list_triples, *facet_triples)

    def _walk_rdf_list(
        self,
        head: IdentifiedNode,
        *,
        label: str,
    ) -> tuple[tuple[_RDFListCell, ...], tuple[Triple, ...]]:
        if head == RDF.nil:
            return (), ()

        cells: list[_RDFListCell] = []
        triples: list[Triple] = []
        seen: set[IdentifiedNode] = set()
        previous: IdentifiedNode | None = None
        current = head

        while current != RDF.nil:
            if current in seen:
                raise MalformedGraphError(
                    f"{label} rdf:List contains a cycle at {_format_node(current)}."
                )
            incoming_rest = self._match(predicate=RDF.rest, object_=current)
            expected_incoming = (
                frozenset()
                if previous is None
                else frozenset({(previous, RDF.rest, current)})
            )
            if incoming_rest != expected_incoming:
                raise MalformedGraphError(
                    f"{label} rdf:List cell {_format_node(current)} is shared "
                    "or is not the head of an owned list."
                )

            first_triples = self._match(subject=current, predicate=RDF.first)
            rest_triples = self._match(subject=current, predicate=RDF.rest)
            if len(first_triples) != 1:
                raise MalformedGraphError(
                    f"{label} rdf:List cell {_format_node(current)} MUST have "
                    f"exactly one rdf:first triple; found {len(first_triples)}."
                )
            if len(rest_triples) != 1:
                raise MalformedGraphError(
                    f"{label} rdf:List cell {_format_node(current)} MUST have "
                    f"exactly one rdf:rest triple; found {len(rest_triples)}."
                )

            first_triple = next(iter(first_triples))
            rest_triple = next(iter(rest_triples))
            if first_triple in self.consumed or rest_triple in self.consumed:
                raise MalformedGraphError(
                    f"{label} rdf:List cell {_format_node(current)} is already "
                    "owned by another structural element."
                )
            rest = rest_triple[2]
            if not isinstance(rest, IdentifiedNode):
                raise MalformedGraphError(
                    f"{label} rdf:List rest object MUST be an RDF resource; got "
                    f"{_format_node(rest)}."
                )

            seen.add(current)
            cells.append(
                _RDFListCell(
                    cell=current,
                    value=first_triple[2],
                    first_triple=first_triple,
                    rest_triple=rest_triple,
                )
            )
            triples.extend((first_triple, rest_triple))
            previous = current
            current = rest

        return tuple(cells), tuple(triples)

    def _require_uri_seq_values(self, seq: Seq, *, label: str) -> None:
        for value in _seq_values(seq):
            if not isinstance(value, URIRef):
                raise MalformedGraphError(
                    f"{label} property operands MUST be IRIs; got "
                    f"{_format_node(value)}."
                )

    def _require_single_object(
        self,
        subject: IdentifiedNode,
        predicate: URIRef,
        *,
        label: str,
    ) -> tuple[Node, Triple]:
        triples = self._match(subject=subject, predicate=predicate)
        if len(triples) != 1:
            raise MalformedGraphError(
                f"{label} at {_format_node(subject)} MUST have exactly one "
                f"{_format_node(predicate)} object; found {len(triples)}."
            )
        triple = next(iter(triples))
        return triple[2], triple

    def _require_triple(
        self,
        subject: IdentifiedNode,
        predicate: URIRef,
        object_: Node,
    ) -> Triple:
        triple = (subject, predicate, object_)
        if not self._has(subject, predicate, object_):
            raise MalformedGraphError(
                f"Missing required triple {_format_triple(triple)}."
            )
        return triple

    def _subjects_for_predicate(self, predicate: URIRef) -> tuple[IdentifiedNode, ...]:
        return tuple(
            sorted(
                {triple[0] for triple in self._match(predicate=predicate)},
                key=_node_key,
            )
        )

    def _has(self, subject: IdentifiedNode, predicate: URIRef, object_: Node) -> bool:
        return bool(self._match(subject=subject, predicate=predicate, object_=object_))

    def _has_any(self, subject: IdentifiedNode, predicate: URIRef) -> bool:
        return bool(self._match(subject=subject, predicate=predicate))

    def _match(
        self,
        *,
        subject: IdentifiedNode | None = None,
        predicate: URIRef | None = None,
        object_: Node | None = None,
    ) -> frozenset[Triple]:
        """Return graph-backed triple-pattern matches from the input snapshot."""
        matches: set[Triple] = set()
        for triple in self.graph.triples((subject, predicate, object_)):
            normalized = _validate_triple(*triple)
            if normalized in self.triples:
                matches.add(normalized)
        return frozenset(matches)

    def _add_element(
        self,
        element: StructuralElement,
        *triples: Triple,
    ) -> None:
        duplicate = next(
            (triple for triple in triples if triple in self.consumed), None
        )
        if duplicate is not None:
            raise MalformedGraphError(
                f"Structural elements overlap on triple {_format_triple(duplicate)}."
            )
        self.consumed.update(triples)
        self.elements.append(element)

    def _build_element(
        self,
        label: str,
        constructor: Callable[..., StructuralElement],
        **kwargs: object,
    ) -> StructuralElement:
        try:
            element = constructor(**kwargs)
        except ValidationError as cause:
            raise MalformedGraphError(f"Malformed {label}: {cause}") from cause
        if not isinstance(element, StructuralElement):
            raise TypeError(f"{label} constructor did not produce a StructuralElement.")
        return element

    def _raise_if_unconsumed_triples(self) -> None:
        leftovers = self.triples.difference(self.consumed)
        if not leftovers:
            return
        examples = ", ".join(
            _format_triple(triple) for triple in sorted(leftovers, key=_triple_key)[:5]
        )
        # OWL 2 Mapping to RDF Section 3 (RDF graphs -> structural specification)
        # applies declaration, expression, and axiom patterns, removing each
        # matched triple from G. When that process finishes, G MUST be empty.
        # Unconsumed triples here are that residue (count + samples below).
        #
        # Until every structural mapping form is Implemented, keep the
        # coverage-oriented message so leftovers are not blamed as mapping
        # violations when they may simply be not-yet-supported. Once coverage
        # is complete, prefer a message aligned with the empty-G requirement,
        # for example:
        #
        # raise UnsupportedGraphError(
        #     "OWL 2 RDF mapping requires the graph to be empty after all "
        #     "declaration, expression, and axiom patterns are applied; "
        #     f"{len(leftovers)} triple(s) remain unparsed. First unmatched: "
        #     f"{examples}."
        # )
        #
        # One important residue class after ClassAssertion exists: rdf:type
        # triples whose object never entered the CE map (CE(y) = epsilon), so
        # ClassAssertion does not match. Those MUST NOT be reinterpreted as
        # ObjectPropertyAssertion. Other leftover families include open-predicate
        # assertions, annotation axioms, and ontology-header triples.
        raise UnsupportedGraphError(
            f"Unsupported RDF graph content: {len(leftovers)} triple(s) were not "
            f"matched by current axiomatization patterns. First unmatched: "
            f"{examples}."
        )


def axiomatize(graph: Graph) -> tuple[StructuralElement, ...]:
    """Lift supported RDF graph patterns from ``graph`` into structural elements.

    The caller is expected not to mutate ``graph`` while axiomatization is in
    progress. V1 is strict: any initial input triple that cannot be assigned to
    a currently supported structural element causes ``UnsupportedGraphError``.
    """
    context = graph.identifier
    if not isinstance(context, IdentifiedNode):
        raise MalformedGraphError(
            f"Graph identifier MUST be an RDF resource; got {context!r}."
        )
    return _Axiomatizer(
        graph=graph,
        triples=_snapshot_graph(graph),
        context=context,
    ).run()


def _seq_values(seq: Seq) -> tuple[Node, ...]:
    return tuple(entry.value for entry in seq.entries if entry.value is not None)


def _snapshot_graph(graph: Graph) -> frozenset[Triple]:
    return frozenset(_validate_triple(*triple) for triple in graph)


def _validate_triple(subject: Node, predicate: Node, object_: Node) -> Triple:
    if not isinstance(subject, IdentifiedNode):
        raise MalformedGraphError(
            f"Triple subject MUST be an RDF resource; got {subject!r}."
        )
    if not isinstance(predicate, URIRef):
        raise MalformedGraphError(
            f"Triple predicate MUST be an IRI; got {predicate!r}."
        )
    if not isinstance(object_, Node):
        raise MalformedGraphError(
            f"Triple object MUST be an RDF node; got {object_!r}."
        )
    return subject, predicate, object_


_FALLBACK_DECLARATION_TYPES: Final[tuple[type[StructuralElement], ...]] = (
    DeclarationDatatype,
    DeclarationClass,
    DeclarationObjectProperty,
    DeclarationDataProperty,
    DeclarationAnnotationProperty,
    NamedIndividual,
)


def _element_sort_key(element: StructuralElement) -> tuple[tuple[str, str], int, str]:
    fallback_rank = 1 if isinstance(element, _FALLBACK_DECLARATION_TYPES) else 0
    return (_node_key(element.name), fallback_rank, element.__class__.__name__)


def _triple_key(
    triple: Triple,
) -> tuple[tuple[str, str], tuple[str, str], tuple[str, str]]:
    return (_node_key(triple[0]), _node_key(triple[1]), _node_key(triple[2]))


def _node_key(node: Node) -> tuple[str, str]:
    if isinstance(node, URIRef):
        return ("0-iri", str(node))
    if isinstance(node, Literal):
        return ("2-literal", node.n3())
    return ("1-bnode", str(node))


def _format_triple(triple: Triple) -> str:
    return (
        f"({_format_node(triple[0])}, {_format_node(triple[1])}, "
        f"{_format_node(triple[2])})"
    )


def _format_node(node: Node) -> str:
    return str(node.n3())


__all__ = [
    "AxiomatizationError",
    "MalformedGraphError",
    "UnsupportedGraphError",
    "axiomatize",
]
