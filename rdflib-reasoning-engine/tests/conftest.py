from collections.abc import Generator, Set
from typing import Any, Final

import pytest
from rdflib import RDF, RDFS, Graph
from rdflib.graph import ReadOnlyGraphAggregate
from rdflibr.axiom.common import Triple

type TestData[T] = Generator[T, Any, Any]

RDFS_AXIOMS: Final[Set[Triple]] = frozenset(
    [
        (RDF.type, RDFS.range, RDFS.Class),
        (RDFS.Resource, RDF.type, RDFS.Class),
        (RDFS.Literal, RDF.type, RDFS.Class),
        (RDF.Statement, RDF.type, RDFS.Class),
        (RDF.nil, RDF.type, RDF.List),
        (RDF.subject, RDF.type, RDF.Property),
        (RDF.object, RDF.type, RDF.Property),
        (RDF.predicate, RDF.type, RDF.Property),
        (RDF.first, RDF.type, RDF.Property),
        (RDF.rest, RDF.type, RDF.Property),
        #
        (RDFS.subPropertyOf, RDFS.domain, RDF.Property),
        (RDFS.subClassOf, RDFS.domain, RDFS.Class),
        (RDFS.domain, RDFS.domain, RDF.Property),
        (RDFS.range, RDFS.domain, RDF.Property),
        (RDF.subject, RDFS.domain, RDF.Statement),
        (RDF.predicate, RDFS.domain, RDF.Statement),
        (RDF.object, RDFS.domain, RDF.Statement),
        (RDF.first, RDFS.domain, RDF.List),
        (RDF.rest, RDFS.domain, RDF.List),
        #
        (RDFS.subPropertyOf, RDFS.range, RDF.Property),
        (RDFS.subClassOf, RDFS.range, RDFS.Class),
        (RDFS.domain, RDFS.range, RDFS.Class),
        (RDFS.range, RDFS.range, RDFS.Class),
        (RDFS.comment, RDFS.range, RDFS.Literal),
        (RDFS.label, RDFS.range, RDFS.Literal),
        (RDF.rest, RDFS.range, RDF.List),
        #
        (RDF.Alt, RDFS.subClassOf, RDFS.Container),
        (RDF.Bag, RDFS.subClassOf, RDFS.Container),
        (RDF.Seq, RDFS.subClassOf, RDFS.Container),
        (RDFS.ContainerMembershipProperty, RDFS.subClassOf, RDF.Property),
        #
        (RDFS.isDefinedBy, RDFS.subPropertyOf, RDFS.seeAlso),
        #
        (RDF.XMLLiteral, RDF.type, RDFS.Datatype),
        (RDFS.Datatype, RDFS.subClassOf, RDFS.Class),
    ]
)


@pytest.fixture
def rdfs_axioms() -> TestData[Graph]:
    """An immutable graph containing the RDFS axioms."""
    graph = Graph()
    for triple in RDFS_AXIOMS:
        graph.add(triple)
    yield ReadOnlyGraphAggregate(graphs=[graph])
