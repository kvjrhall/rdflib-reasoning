# from __future__ import annotations

import textwrap
import warnings
from collections.abc import Generator, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from rdflib import OWL, PROV, RDFS, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DefinedNamespace
from rdflib.query import Result, ResultRow
from rdflibr.middleware.namespaces.spec_index import (
    RDFVocabulary,
    VocabularyTerm,
    VocabularyTermType,
)


def _base_query(inner_select: str) -> str:
    inner_select = textwrap.dedent(inner_select)
    inner_select = textwrap.indent(inner_select, "        ")

    return textwrap.dedent("""
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?node WHERE {
    INNER_SELECT
    }
    """).replace("INNER_SELECT", inner_select)


_FIND_CLASSES_QUERY = _base_query("""
    ?node rdfs:subClassOf*/rdf:type ?root .

    VALUES (?root) {
        (rdfs:Class)
        (owl:Class)
    }

    FILTER( isURI(?node) ) .
""")

_FIND_DATATYPES_QUERY = _base_query("""
    ?node rdf:type rdfs:Datatype .

    FILTER( isURI(?node) ) .
""")

_FIND_INDIVIDUALS_QUERY = _base_query("""
    ?node rdf:type ?class .
    ?class rdf:type/rdfs:subClassOf* rdfs:Class .

    FILTER(isURI(?node))
    FILTER NOT EXISTS {
        ?node rdf:type/rdfs:subClassOf* rdfs:Class .
    }
    FILTER NOT EXISTS {
        ?node rdf:type rdfs:Datatype .
    }
    FILTER NOT EXISTS {
        ?class rdf:type/rdfs:subPropertyOf* rdf:Property .
    }
""")

_FIND_PROPERTIES_QUERY = _base_query("""
    ?node rdfs:subPropertyOf*/rdf:type ?root .

    VALUES (?root) {
        (rdf:Property)
        (owl:ObjectProperty)
        (owl:DatatypeProperty)
        (owl:AnnotationProperty)
    }

    FILTER( isURI(?node) )
""")


_PROV_O: Final[URIRef] = URIRef("http://www.w3.org/ns/prov-o#")
_PROV_SHARES_DEFINITION_WITH: Final[URIRef] = URIRef(f"{PROV}sharesDefinitionWith")
_AUTHORITY_ALIASES: Final[Mapping[str, frozenset[URIRef]]] = MappingProxyType(
    {
        str(PROV): frozenset({URIRef(str(PROV)), _PROV_O}),
    }
)
_DEFINITION_PROPERTIES: Final[Sequence[URIRef]] = (
    URIRef(f"{PROV}definition"),
    URIRef(f"{PROV}editorsDefinition"),
    RDFS.comment,
)
_KNOWN_MISSING_DEFINITIONS: Final[frozenset[URIRef]] = frozenset(
    {
        URIRef("http://www.w3.org/ns/prov#aq"),
        URIRef("http://www.w3.org/ns/prov#hadPrimarySource"),
        URIRef("http://www.w3.org/ns/prov#sharesDefinitionWith"),
    }
)


@dataclass(frozen=True)
class _VocabularyDefinitionScope:
    namespace: URIRef
    authorities: frozenset[URIRef]

    def contains_term(self, term: URIRef, authority: URIRef) -> bool:
        return (
            str(term).startswith(str(self.namespace)) and authority in self.authorities
        )


@dataclass(frozen=True)
class _DefinitionResolution:
    value: str


def build_vocabulary(
    namespace: type[Namespace]
    | type[DefinedNamespace]
    | Namespace
    | DefinedNamespace
    | URIRef
    | str,
    graph: Graph,
) -> RDFVocabulary:
    scope = _scope_from_namespace(namespace)

    classes = _collect_terms(
        scope, VocabularyTermType.CLASS, graph, _FIND_CLASSES_QUERY
    )
    datatypes = _collect_terms(
        scope, VocabularyTermType.DATATYPE, graph, _FIND_DATATYPES_QUERY
    )
    individuals = _collect_terms(
        scope, VocabularyTermType.INDIVIDUAL, graph, _FIND_INDIVIDUALS_QUERY
    )
    properties = _collect_terms(
        scope, VocabularyTermType.PROPERTY, graph, _FIND_PROPERTIES_QUERY
    )

    return RDFVocabulary(
        namespace=scope.namespace,
        classes=classes,
        datatypes=datatypes,
        individuals=individuals,
        properties=properties,
    )


def _scope_from_namespace(
    namespace: type[Namespace]
    | type[DefinedNamespace]
    | Namespace
    | DefinedNamespace
    | URIRef
    | str,
) -> _VocabularyDefinitionScope:
    namespace_iri = URIRef(str(namespace))
    return _VocabularyDefinitionScope(
        namespace=namespace_iri,
        authorities=_AUTHORITY_ALIASES.get(
            str(namespace_iri), frozenset({namespace_iri})
        ),
    )


def _collect_terms(
    scope: _VocabularyDefinitionScope,
    term_type: VocabularyTermType,
    graph: Graph,
    query: str,
) -> set[VocabularyTerm]:
    return set(
        sorted(
            _terms_from_results(scope, term_type, graph, graph.query(query)),
            key=lambda term: term.uri,
        )
    )


def _terms_from_results(
    scope: _VocabularyDefinitionScope,
    term_type: VocabularyTermType,
    graph: Graph,
    results: Result,
) -> Generator[VocabularyTerm, None, None]:
    seen: set[URIRef] = set()
    for result in results:
        if not isinstance(result, ResultRow):
            continue
        node = result["node"]
        if not isinstance(node, URIRef) or node in seen:
            continue

        if _get_authority(node, graph, scope) is None:
            continue

        seen.add(node)
        yield VocabularyTerm(
            uri=node,
            label=_get_term_label(node, graph),
            definition=_get_term_definition(node, graph).value,
            termType=term_type,
        )


def _get_authority(
    term: URIRef, graph: Graph, scope: _VocabularyDefinitionScope
) -> URIRef | None:
    authorities = sorted(
        (
            authority
            for authority in graph.objects(term, RDFS.isDefinedBy)
            if isinstance(authority, URIRef) and scope.contains_term(term, authority)
        ),
        key=str,
    )
    if len(authorities) == 0:
        return None
    return authorities[0]


def _get_term_label(term: URIRef, graph: Graph) -> str:
    label = graph.value(term, RDFS.label)
    if label is None or not isinstance(label, Literal):
        local_name = _get_local_name(term)
        label = Literal(local_name)

    if not isinstance(label_value := label.toPython(), str):
        warnings.warn(
            f"Label for {term} is not a string",
            WrongLabelTypeWarning,
            stacklevel=2,
        )
        return f"<literal_label_lexical_form>{label.n3()}</literal_label_lexical_form>"

    return label_value


def _get_local_name(term: URIRef) -> str:
    term_str = str(term)
    if "#" in term_str:
        fragment = term_str.rsplit("#", maxsplit=1)[1]
        if fragment:
            return fragment

    path = term_str.rstrip("/")
    if "/" in path:
        segment = path.rsplit("/", maxsplit=1)[1]
        if segment:
            return segment

    return term_str


def _get_term_definition(term: URIRef, graph: Graph) -> _DefinitionResolution:
    if (definition := _resolve_definition(term, graph)) is not None:
        return definition

    if term not in _KNOWN_MISSING_DEFINITIONS:
        warnings.warn(
            f"No valid definition for {term} found",
            NoDefinitionWarning,
            stacklevel=2,
        )
    return _DefinitionResolution(
        value=(
            f"<literal_definition_missing>The vocabulary has no definition for "
            f"{term}</literal_definition_missing>"
        )
    )


def _resolve_definition(term: URIRef, graph: Graph) -> _DefinitionResolution | None:
    if (definition := _get_direct_definition(term, graph)) is not None:
        return definition

    shares_definition_with = graph.value(term, _PROV_SHARES_DEFINITION_WITH)
    if isinstance(shares_definition_with, URIRef):
        if (
            shared_definition := _resolve_shared_definition(
                shares_definition_with, graph
            )
        ) is not None:
            return shared_definition

    for inverse_term in _iter_inverse_terms(term, graph):
        if (
            inverse_definition := _resolve_inverse_definition(inverse_term, graph)
        ) is not None:
            return inverse_definition

    return None


def _resolve_shared_definition(
    term: URIRef, graph: Graph
) -> _DefinitionResolution | None:
    return _get_direct_definition(term, graph)


def _resolve_inverse_definition(
    inverse_term: URIRef, graph: Graph
) -> _DefinitionResolution | None:
    if (definition := _get_direct_definition(inverse_term, graph)) is not None:
        return definition

    shares_definition_with = graph.value(inverse_term, _PROV_SHARES_DEFINITION_WITH)
    if isinstance(shares_definition_with, URIRef):
        return _resolve_shared_definition(shares_definition_with, graph)

    return None


def _get_direct_definition(term: URIRef, graph: Graph) -> _DefinitionResolution | None:
    for predicate in _DEFINITION_PROPERTIES:
        definition = graph.value(term, predicate)
        if definition is None:
            continue
        if not isinstance(definition, Literal):
            warnings.warn(
                f"Definition for {term} is not a literal",
                WrongDefinitionTypeWarning,
                stacklevel=2,
            )
            return _DefinitionResolution(
                value=(
                    f"<literal_definition_lexical_form>{definition.n3()}"
                    f"</literal_definition_lexical_form>"
                )
            )

        if not isinstance(definition_value := definition.toPython(), str):
            warnings.warn(
                f"Definition for {term} is not a string",
                WrongDefinitionTypeWarning,
                stacklevel=2,
            )
            return _DefinitionResolution(
                value=(
                    f"<literal_definition_lexical_form>{definition.n3()}"
                    f"</literal_definition_lexical_form>"
                )
            )

        return _DefinitionResolution(value=definition_value)

    return None


def _iter_inverse_terms(term: URIRef, graph: Graph) -> Generator[URIRef, None, None]:
    seen: set[URIRef] = set()
    for candidate in graph.objects(term, OWL.inverseOf):
        if isinstance(candidate, URIRef) and candidate not in seen:
            seen.add(candidate)
            yield candidate
    for candidate in graph.subjects(OWL.inverseOf, term):
        if isinstance(candidate, URIRef) and candidate not in seen:
            seen.add(candidate)
            yield candidate


class VocabularyWarning(UserWarning):
    """Base class for warnings related to vocabulary terms."""


class LabelWarning(VocabularyWarning):
    """Base class for warnings related to labels of vocabulary terms."""


class NoLabelWarning(LabelWarning):
    """Warning emitted when a vocabulary term has no label."""


class WrongLabelTypeWarning(LabelWarning):
    """Warning emitted when a vocabulary term has a label is not an xsd:string."""


class DefinitionWarning(VocabularyWarning):
    """Base class for warnings related to definitions of vocabulary terms."""


class NoDefinitionWarning(DefinitionWarning):
    """Warning emitted when a vocabulary term has no definition."""


class WrongDefinitionTypeWarning(DefinitionWarning):
    """Warning emitted when a vocabulary term has a definition is not an xsd:string."""
