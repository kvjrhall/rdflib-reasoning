from abc import ABC, abstractmethod
from collections.abc import Generator, Sequence
from itertools import chain
from typing import Any, ClassVar, Literal, Self, get_args, get_origin, get_type_hints

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    SerializeAsAny,
    computed_field,
    model_validator,
)
from rdflib import RDF, IdentifiedNode

from .common import ContextIdentifier, N3Resource, Quad, Triple


class GraphBacked(BaseModel, ABC):
    """Universal base for graph-scoped Pydantic models in this package.

    An instance MUST be associated with a single, required graph (context). Any
    field whose type is another GraphBacked or StructuralElement MUST share the
    same context; cross-context relationships are expressed only at the
    triple/quad level, not by embedding foreign-context instances. Models MUST
    NOT embed rdflib.Graph, ConjunctiveGraph, SPARQL result objects, or other
    container/session/handle types; they MAY use rdflib node types (URIRef,
    BNode, Literal, IdentifiedNode, etc.).
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


class StructuralElement(GraphBacked, ABC):
    """Universal base for OWL 2 structural elements.

    Concrete class names SHOULD match the paired structural element's name
    (e.g. NegativeDataPropertyAssertion). Each concrete subclass MUST
    correspond to a well-identified OWL 2 structural element; as_triples (and
    as_quads) MUST conform to owl2-mapping-to-rdf and transitive specs.
    as_triples MUST NOT recurse into related elements.
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
        """Triples representing this element as RDF; MUST NOT recurse into related elements."""
        pass

    @property
    def as_quads(self) -> Sequence[Quad]:
        """Quads for this element: each triple from as_triples with context as fourth element."""
        return tuple((*t, self.context) for t in self.as_triples)


class Seq[T: StructuralElement](StructuralElement):
    """RDF list encoding ``T(SEQ E1 ... En)`` for a finite sequence of structural elements.

    Each list cell ``names[i]`` links to ``elements[i].name`` via ``rdf:first``;
    ``rdf:rest`` chains cells and ends with ``rdf:nil``. ``as_triples`` emits
    only list structure edges and does not include nested elements' triples.

    Triples (schematically, list heads ``L1 ... Ln``)::

        Li rdf:first Ei.name .
        Li rdf:rest L(i+1) .    # i < n
        Ln rdf:rest rdf:nil .
    """

    _require_concrete_kind: ClassVar[bool] = True
    kind: Literal["seq"] = "seq"

    names: Sequence[N3Resource] = Field(
        ...,
        description="Identifiers for each `rdf:List` node in the sequence; typically blank nodes in the absence of skolemization.",
    )
    elements: Sequence[SerializeAsAny[T]]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def name(self) -> IdentifiedNode:
        return self.names[0]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def as_triples(self) -> Sequence[Triple]:
        def heads() -> Generator[Triple]:
            for name, element in zip(self.names, self.elements, strict=True):
                yield (name, RDF.first, element.name)

        def tails() -> Generator[Triple]:
            for head, tail in zip(
                self.names, chain(self.names[1:], [RDF.nil]), strict=True
            ):
                yield (head, RDF.rest, tail)

        # NOTE: We MUST NOT recurse into related elements; i.e., tuple(
        #     [triple for element in self.elements for triple in element.as_triples]
        # )

        return tuple(chain(heads(), tails()))

    @model_validator(mode="after")
    def check_list_integrity(self) -> Self:
        if len(self.names) != len(self.elements):
            raise ValueError(
                f"The number of names ({len(self.names)}) and elements ({len(self.elements)}) MUST match."
            )
        if any(name == RDF.nil for name in self.names):
            raise ValueError("The `rdf:nil` node MUST NOT be used as a list head.")
        if len(set(self.names)) != len(self.names):
            duplicates = sorted(
                [name for name in self.names if self.names.count(name) > 1]
            )
            raise ValueError(
                "The list names MUST be unique but found duplicates: "
                + ", ".join(duplicates)
            )
        for el in self.elements:
            if el.context != self.context:
                raise ValueError(
                    f"Related structural elements MUST share the same context; "
                    f"expected {self.context}, got {el.context}. Use the same "
                    "ContextIdentifier for all elements in this sequence."
                )
        return self


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
