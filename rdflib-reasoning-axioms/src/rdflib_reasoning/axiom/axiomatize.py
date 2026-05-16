"""Lift supported RDF graph patterns into structural elements.

The public entry point is :func:`axiomatize`, which partitions a graph into the
currently implemented datatype-oriented ``StructuralElement`` models. The
implementation uses RDFLib graph triple-pattern lookup rather than SPARQL or a
secondary in-memory index.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final

from pydantic import ValidationError
from rdflib import OWL, RDF, RDFS, Graph, IdentifiedNode, Literal, Node, URIRef

from .common import Triple
from .datatype import (
    DataAllValuesFromNary,
    DataComplementOf,
    DataIntersectionOf,
    DataOneOf,
    DataSomeValuesFrom,
    DataSomeValuesFromNary,
    DatatypeRestriction,
    DataUnionOf,
    DeclarationDatatype,
    FacetEntry,
    FacetList,
)
from .structural_element import Seq, SeqEntry, StructuralElement

_STRUCTURAL_LIST_PREDICATES: Final[frozenset[URIRef]] = frozenset({RDF.first, RDF.rest})


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
        self._parse_data_intersections()
        self._parse_data_unions()
        self._parse_data_complements()
        self._parse_data_one_ofs()
        self._parse_datatype_restrictions()
        self._parse_data_some_values_froms()
        self._parse_data_all_values_from_narys()
        self._parse_declaration_datatypes()
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

    def _parse_data_some_values_froms(self) -> None:
        for subject in self._subjects_for_predicate(OWL.someValuesFrom):
            if not self._has(subject, RDF.type, OWL.Restriction):
                continue
            has_on_property = self._has_any(subject, OWL.onProperty)
            has_on_properties = self._has_any(subject, OWL.onProperties)
            if has_on_property and has_on_properties:
                raise MalformedGraphError(
                    "DataSomeValuesFrom subject cannot use both owl:onProperty "
                    f"and owl:onProperties: {_format_node(subject)}."
                )
            if has_on_properties:
                self._parse_data_some_values_from_nary(subject)
            elif has_on_property:
                self._parse_data_some_values_from_unary(subject)

    def _parse_data_some_values_from_unary(self, subject: IdentifiedNode) -> None:
        type_triple = self._require_triple(subject, RDF.type, OWL.Restriction)
        on_property, on_property_triple = self._require_single_object(
            subject,
            OWL.onProperty,
            label="DataSomeValuesFrom",
        )
        if not isinstance(on_property, URIRef):
            raise MalformedGraphError(
                "DataSomeValuesFrom owl:onProperty object MUST be an IRI; got "
                f"{_format_node(on_property)}."
            )
        some_values_from, some_values_from_triple = self._require_single_object(
            subject,
            OWL.someValuesFrom,
            label="DataSomeValuesFrom",
        )
        if not isinstance(some_values_from, IdentifiedNode):
            raise MalformedGraphError(
                "DataSomeValuesFrom owl:someValuesFrom object MUST be an RDF "
                f"resource; got {_format_node(some_values_from)}."
            )
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

    def _parse_data_all_values_from_narys(self) -> None:
        for subject in self._subjects_for_predicate(OWL.allValuesFrom):
            if not self._has(subject, RDF.type, OWL.Restriction):
                continue
            has_on_property = self._has_any(subject, OWL.onProperty)
            has_on_properties = self._has_any(subject, OWL.onProperties)
            if has_on_property and has_on_properties:
                raise MalformedGraphError(
                    "DataAllValuesFrom subject cannot use both owl:onProperty "
                    f"and owl:onProperties: {_format_node(subject)}."
                )
            if has_on_properties:
                self._parse_data_all_values_from_nary(subject)

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

    def _parse_declaration_datatypes(self) -> None:
        triples = sorted(
            self._match(predicate=RDF.type, object_=RDFS.Datatype),
            key=_triple_key,
        )
        for triple in triples:
            if triple in self.consumed:
                continue
            subject = triple[0]
            element = self._build_element(
                "DeclarationDatatype",
                DeclarationDatatype,
                context=self.context,
                name_value=subject,
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
        raise UnsupportedGraphError(
            f"Unsupported RDF graph content: {len(leftovers)} triple(s) were not "
            f"matched by current datatype axiomatization patterns. First unmatched: "
            f"{examples}."
        )


def axiomatize(graph: Graph) -> tuple[StructuralElement, ...]:
    """Lift supported datatype RDF patterns from ``graph`` into structural elements.

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


def _element_sort_key(element: StructuralElement) -> tuple[tuple[str, str], int, str]:
    fallback_rank = 1 if isinstance(element, DeclarationDatatype) else 0
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
