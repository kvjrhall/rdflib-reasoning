from abc import ABC, abstractmethod
from collections.abc import Generator, Mapping, Sequence
from itertools import chain
from typing import (
    Any,
    ClassVar,
    Literal,
    Self,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)
from rdflib import RDF, Graph, IdentifiedNode

from .common import ContextIdentifier, N3Node, N3Resource, Quad, Triple


class GraphBacked(BaseModel, ABC):
    """Universal base for graph-scoped Pydantic models in this package.

    Each instance MUST have a single required ``context`` (graph identifier).
    Cross-context structure MUST be expressed only at the triple or quad level,
    not by composing models defined in another context.

    Three roles partition models in this hierarchy (DR-031; see package
    ``AGENTS.md``):

    - ``StructuralElement`` axiom heads. One OWL 2 structural element per
      partition. Cross-axiom references MUST use RDF node-level types only;
      axiom heads MUST NOT compose other ``StructuralElement`` instances.
    - ``StructuralFragment`` owned scaffolding. May be embedded as a Pydantic
      field on a single owning ``StructuralElement``; its ``as_triples``
      contributes to the owner's partition; MUST share the owner's ``context``.
    - Node references via package-defined annotated aliases (``N3Resource``,
      ``N3IRIRef``, ``N3Node``, ``N3ContextIdentifier``). Used for cross-axiom
      links by identity.

    Models MUST NOT embed rdflib.Graph, ConjunctiveGraph, SPARQL result objects,
    or other container/session/handle types. Schema-facing fields MUST use the
    annotated RDF aliases above rather than raw rdflib node classes; raw rdflib
    node classes MAY still be used in internal non-schema logic.
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if cls is GraphBacked:
            raise TypeError(
                "GraphBacked cannot be instantiated directly; subclass a concrete "
                "graph-backed model."
            )
        return super().__new__(cls)

    context: ContextIdentifier = Field(
        ..., description="The graph (context) wherein this entity is defined."
    )
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    _require_concrete_kind: ClassVar[bool] = True

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs) -> None:
        super().__pydantic_init_subclass__(**kwargs)

        if cls is GraphBacked or not cls._require_concrete_kind:
            return

        annotation = get_type_hints(cls, include_extras=True).get("kind")
        if annotation is None:
            raise TypeError(f"{cls.__name__} MUST define `kind: Literal[...]`.")

        if get_origin(annotation) is not Literal:
            raise TypeError(f"{cls.__name__}.kind MUST be typed as `Literal[...]`.")

        values = get_args(annotation)
        if len(values) != 1 or not isinstance(values[0], str):
            raise TypeError(
                f"{cls.__name__}.kind MUST be a single string `Literal`, "
                'e.g. `Literal["my_kind"]`.'
            )


class StructuralFragment(GraphBacked, ABC):
    """Owned scaffolding for a single ``StructuralElement`` (DR-031).

    A fragment models a graph fragment that is co-essential to one OWL axiom's
    RDF mapping (for example an ``rdf:List`` carrying ``owl:intersectionOf``
    members). Fragments MAY be embedded as Pydantic fields on a single owning
    ``StructuralElement``; their ``as_triples`` belong to the owner's partition.

    A fragment MUST share its owner's ``context``; ``StructuralElement`` enforces
    this via a centralized validator. Fragments are not partition units on their
    own and are not OWL axioms.
    """

    _require_concrete_kind: ClassVar[bool] = False

    @property
    @abstractmethod
    def as_triples(self) -> Sequence[Triple]:
        """Triples for this fragment; flow into the owning element's partition."""
        pass

    @property
    def as_quads(self) -> Sequence[Quad]:
        """Quads for this fragment: each triple from ``as_triples`` with ``context``."""
        return tuple((*t, self.context) for t in self.as_triples)


def _iter_fragments(value: Any) -> Generator[StructuralFragment]:
    """Yield ``StructuralFragment`` values directly held by ``value``.

    Walks one level: the value itself, items of a non-string sequence, or values
    of a mapping. Does not descend into nested fragments (each fragment validates
    its own context against its own owner).
    """
    if isinstance(value, StructuralFragment):
        yield value
    elif isinstance(value, str | bytes):
        return
    elif isinstance(value, Mapping):
        for item in value.values():
            if isinstance(item, StructuralFragment):
                yield item
    elif isinstance(value, Sequence):
        for item in value:
            if isinstance(item, StructuralFragment):
                yield item


class StructuralElement(GraphBacked, ABC):
    """Universal base for OWL 2 structural elements (axiom heads; DR-031).

    Concrete class names SHOULD match the paired structural element's name
    (e.g. ``NegativeDataPropertyAssertion``). Each concrete subclass MUST
    correspond to a well-identified OWL 2 structural element; ``as_triples``
    (and ``as_quads``) MUST conform to ``owl2-mapping-to-rdf`` and transitive
    specs.

    ``as_triples`` MUST NOT recurse into other axiom heads. Owned scaffolding
    expressed as ``StructuralFragment`` fields contributes triples to this
    element's partition and MUST share this element's ``context`` (enforced).
    Cross-axiom references MUST use RDF node-level types only.
    """

    _require_concrete_kind: ClassVar[bool] = False

    @property
    @abstractmethod
    def name(self) -> IdentifiedNode:
        """Canonical identifier for this element; SHOULD be the subject of a rdf:type triple."""
        pass

    @property
    @abstractmethod
    def as_triples(self) -> Sequence[Triple]:
        """Triples representing this element as RDF; MUST NOT recurse into other axiom heads."""
        pass

    @property
    def as_quads(self) -> Sequence[Quad]:
        """Quads for this element: each triple from as_triples with context as fourth element."""
        return tuple((*t, self.context) for t in self.as_triples)

    @model_validator(mode="after")
    def _check_owned_fragment_contexts(self) -> Self:
        for field_name in type(self).model_fields:
            value = getattr(self, field_name, None)
            for fragment in _iter_fragments(value):
                if fragment.context != self.context:
                    raise ValueError(
                        f"Owned StructuralFragment in field {field_name!r} MUST "
                        f"share its owner's context; expected {self.context}, "
                        f"got {fragment.context}."
                    )
        return self


class SeqEntry(BaseModel):
    """One RDF list cell: ``cell`` is the list node; ``value`` is the ``rdf:first`` object.

    The terminal sentinel row uses ``cell == rdf:nil`` and ``value is None``; that
    row emits no ``rdf:first`` triple in `Seq.as_triples`. Non-sentinel rows MUST
    supply a ``value`` (the list member, typically an IRI, blank node, or literal).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    cell: N3Resource = Field(
        ...,
        description="The `rdf:List` node containing this entry (i.e., a `cons` cell); typically blank nodes in the absence of skolemization.",
    )
    value: N3Node | None = Field(
        ...,
        description="The value of this entry via `rdf:first` (i.e., the `car` of the `cons` cell).",
    )

    @model_validator(mode="after")
    def check_rdf_nil_or_value(self) -> Self:
        if self.cell == RDF.nil and self.value is not None:
            raise ValueError("The `rdf:nil` node MUST NOT have a `rdf:first` value.")
        if self.cell != RDF.nil and self.value is None:
            raise ValueError(
                f"The `rdf:List` node {self.cell} MUST have a `rdf:first` value."
            )
        return self


class Seq(StructuralFragment):
    """OWL / RDF list helper encoding ``T(SEQ v1 ... vn)`` (finite ``rdf:List``).

    ``Seq`` is a ``StructuralFragment``: it models owned ``rdf:List`` scaffolding
    for a single owning ``StructuralElement`` (for example the operand list of
    ``DataIntersectionOf``). Each member is an RDF term referenced by
    ``rdf:first`` (no nested axiom instances; DR-031).

    ``entries`` pairs each list cell node with its ``rdf:first`` value; the last
    row is the sentinel ``(rdf:nil, None)`` (OWL empty list uses only that row).
    ``name`` is the list head: ``entries[0].cell``.

    ``as_triples`` emits list scaffolding only; the owning element's
    ``as_triples`` is responsible for chaining these triples into its partition.

    Triples (omit ``rdf:first`` where ``value`` is ``None``)::

        Ei.cell rdf:first Ei.value .    # when Ei.value is not None
        Ei.cell rdf:rest entries[i+1].cell .    # i < len(entries)-1
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["seq"] = "seq"

    entries: Sequence[SeqEntry] = Field(
        ...,
        description="The ordered entries of an rdf:List sequence",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def name(self) -> IdentifiedNode:
        return self.entries[0].cell

    @computed_field  # type: ignore[prop-decorator]
    @property
    def as_triples(self) -> Sequence[Triple]:
        def heads() -> Generator[Triple]:
            for entry in self.entries:
                if entry.value is not None:
                    yield (entry.cell, RDF.first, entry.value)

        def tails() -> Generator[Triple]:
            names = [entry.cell for entry in self.entries]
            for head, tail in zip(names[:-1], names[1:], strict=True):
                yield (head, RDF.rest, tail)

        return tuple(chain(heads(), tails()))

    @model_validator(mode="after")
    def check_list_integrity(self) -> Self:
        if len(self.entries) == 0:
            raise ValueError(
                "An empty list MUST be encoded as a single entry containing `rdf:nil`."
            )
        if self.entries[-1].cell != RDF.nil:
            raise ValueError(
                "The last entry in an rdf:List sequence MUST be `rdf:nil`."
            )
        names = [entry.cell for entry in self.entries]
        if len(set(names)) != len(names):
            duplicates = sorted([name for name in names if names.count(name) > 1])
            raise ValueError(
                "The list names MUST be unique but found duplicates: "
                + ", ".join(duplicates)
            )

        # NOTE: the ends-with rdf:nil check + the no-duplicates check =>
        #       that rdf:nil does not appear in the middle of the list.
        return self

    @classmethod
    def from_rdflib(cls, graph: Graph, head: IdentifiedNode) -> Self:
        entries: list[SeqEntry] = []
        rest: IdentifiedNode | None = head
        try:
            while head != RDF.nil:
                first = graph.value(head, RDF.first, any=False)
                assert first is not None, (
                    f"{head} rdf:first MUST have a value but found None."
                )
                entries.append(SeqEntry(cell=head, value=first))

                rest = graph.value(rest, RDF.rest, any=False)  # type: ignore[assignment]
                assert rest is not None, (
                    f"{rest} rdf:rest MUST have a value but found None."
                )
                assert isinstance(rest, IdentifiedNode), (
                    f"{rest} rdf:rest MUST be an identified node but found {type(rest)}."
                )
                head = rest
            entries.append(SeqEntry(cell=RDF.nil, value=None))
        except Exception as cause:
            raise ValueError(
                f"Failed to parse complete Seq from {graph} at {head}."
            ) from cause
        return cls(context=graph.identifier, entries=tuple(entries))


class DeclarationElement(StructuralElement, ABC):
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
    @abstractmethod
    def rdf_type(self) -> IdentifiedNode:
        pass

    @computed_field  # type: ignore[prop-decorator]
    @property
    def as_triples(self) -> Sequence[Triple]:
        return ((self.name, RDF.type, self.rdf_type),)
