import logging
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from threading import RLock
from types import MappingProxyType
from typing import Final

from rdflib import DC, OWL, RDF, Graph, Literal, Namespace, URIRef
from rdflib.graph import ReadOnlyGraphAggregate
from rdflib.namespace import RDFS, VANN, DefinedNamespace
from rdflib_reasoning.middleware.namespaces._bundled import (
    ALL_BUNDLED_VOCABULARIES,
    bundled_vocabulary_by_namespace,
    has_bundled_vocabulary,
)
from rdflib_reasoning.middleware.namespaces.spec_index import RDFVocabulary

logger = logging.getLogger(__name__)


_BUNDLED_SPEC_FILENAMES: Final[Mapping[str, str]] = MappingProxyType(
    {
        vocabulary.namespace_uri: vocabulary.filename
        for vocabulary in ALL_BUNDLED_VOCABULARIES
    }
)
_BUNDLED_CACHE_LOCK: Final = RLock()
_BUNDLED_SPEC_CACHE: Final[MutableMapping[str, ReadOnlyGraphAggregate]] = {}
_BUNDLED_METADATA_CACHE: Final[MutableMapping[str, "OntologyDescription"]] = {}
_BUNDLED_VOCABULARY_CACHE: Final[MutableMapping[str, RDFVocabulary]] = {}


@dataclass(frozen=True, slots=True)
class OntologyDescription:
    vocabulary: URIRef
    label: str
    description: str
    preferred_namespace_prefix: str | None = None
    preferred_namespace_uri: str | None = None


_DEFAULT_VOCABULARY_DESCRIPTION: Final[str] = (
    "The user supplied this RDF vocabulary for your task."
)
_DEFAULT_VOCABULARY_LABEL: Final[str] = "An Anonymous User-Supplied RDF Vocabulary"


@dataclass(frozen=True, slots=True)
class UserVocabularySource:
    graph: Graph
    vocabulary: URIRef
    label: str | None = None
    description: str | None = None
    preferred_namespace_prefix: str | None = None
    preferred_namespace_uri: str | None = None


class SpecificationCache:
    # cache_path: Path
    _bundled_specs: frozenset[str]
    _specs: MutableMapping[str, ReadOnlyGraphAggregate]
    _metadata: MutableMapping[str, OntologyDescription]
    _vocabularies: MutableMapping[str, RDFVocabulary]
    _user_spec_keys: frozenset[str]

    def __init__(
        self,
        *,
        bundled_namespaces: Sequence[URIRef | Namespace | type[DefinedNamespace] | str],
        user_specs: Sequence[UserVocabularySource] = (),
    ) -> None:
        # self.cache_path = user_cache_path(
        #     "rdflib-reasoning",
        #     appauthor=False,
        #     ensure_exists=True,
        # )
        self._bundled_specs = frozenset(
            str(namespace) for namespace in bundled_namespaces
        )
        self._specs = {}
        self._metadata = {}
        self._vocabularies = {}
        self._user_spec_keys = frozenset(
            str(source.vocabulary) for source in user_specs
        )
        for user_spec in user_specs:
            # We make a read-only copy of the graph to avoid external modifications
            g = Graph(identifier=user_spec.vocabulary)
            for prefix, uri in user_spec.graph.namespace_manager.namespaces():
                g.namespace_manager.bind(prefix, uri)
            for triple in user_spec.graph:
                g.add(triple)
            key = str(user_spec.vocabulary)
            self._specs[key] = ReadOnlyGraphAggregate([g])
            self._metadata[key] = self._build_ontology_description(
                user_spec.vocabulary,
                g,
                label=user_spec.label,
                description=user_spec.description,
                preferred_namespace_prefix=user_spec.preferred_namespace_prefix,
                preferred_namespace_uri=user_spec.preferred_namespace_uri,
            )

    def get_spec(
        self, namespace: URIRef | Namespace | type[DefinedNamespace] | str
    ) -> Graph:
        key = str(namespace)
        if key in self._specs:
            return self._specs[key]

        if key not in self._bundled_specs:
            raise ValueError(f"Namespace is not bundled or cached: {key}")

        with _BUNDLED_CACHE_LOCK:
            spec = _BUNDLED_SPEC_CACHE.get(key)
            if spec is None:
                spec = _load_bundled_spec(key)
                _BUNDLED_SPEC_CACHE[key] = spec
            self._specs[key] = spec

        return self._specs[key]

    def get_vocabulary(
        self, namespace: URIRef | Namespace | type[DefinedNamespace] | str
    ) -> RDFVocabulary:
        key = str(namespace)
        if key in self._vocabularies:
            return self._vocabularies[key]

        if key in self._bundled_specs and key not in self._user_spec_keys:
            with _BUNDLED_CACHE_LOCK:
                vocabulary = _BUNDLED_VOCABULARY_CACHE.get(key)
                if vocabulary is None:
                    vocabulary = RDFVocabulary.from_graph(
                        URIRef(key), self.get_spec(key)
                    )
                    _BUNDLED_VOCABULARY_CACHE[key] = vocabulary
            self._vocabularies[key] = vocabulary
            return vocabulary

        vocabulary = RDFVocabulary.from_graph(namespace, self.get_spec(namespace))
        self._vocabularies[key] = vocabulary
        return vocabulary

    def get_vocabulary_metadata(
        self, namespace: URIRef | Namespace | type[DefinedNamespace] | str
    ) -> OntologyDescription:
        key = str(namespace)
        if key in self._metadata:
            return self._metadata[key]

        if key in self._bundled_specs and key not in self._user_spec_keys:
            with _BUNDLED_CACHE_LOCK:
                metadata = _BUNDLED_METADATA_CACHE.get(key)
                if metadata is None:
                    metadata = self._build_ontology_description(
                        URIRef(key), self.get_spec(key)
                    )
                    _BUNDLED_METADATA_CACHE[key] = metadata
            self._metadata[key] = metadata
            return metadata

        # NOTE: No mechanism currently exists to fetch specs dynamically, so
        #       this would raise an error out of `get_spec`.
        metadata = self._build_ontology_description(URIRef(key), self.get_spec(key))
        self._metadata[key] = metadata
        return metadata

    @staticmethod
    def has_bundled_resource(
        namespace: URIRef | Namespace | type[DefinedNamespace] | str,
    ) -> bool:
        return has_bundled_vocabulary(namespace)

    def _build_ontology_description(
        self,
        namespace: URIRef,
        graph: Graph,
        *,
        label: str | None = None,
        description: str | None = None,
        preferred_namespace_prefix: str | None = None,
        preferred_namespace_uri: str | None = None,
    ) -> OntologyDescription:
        extracted = _extract_ontology_metadata(graph, namespace)
        bundled_defaults = None
        if self.has_bundled_resource(namespace):
            bundled_defaults = bundled_vocabulary_by_namespace(namespace)

        resolved_label = (
            label
            or extracted.label
            or (bundled_defaults.label if bundled_defaults is not None else None)
            or _DEFAULT_VOCABULARY_LABEL
        )
        resolved_description = (
            description
            or extracted.description
            or (bundled_defaults.description if bundled_defaults is not None else None)
            or _DEFAULT_VOCABULARY_DESCRIPTION
        )
        resolved_prefix = (
            preferred_namespace_prefix or extracted.preferred_namespace_prefix
        )
        resolved_namespace_uri = (
            preferred_namespace_uri or extracted.preferred_namespace_uri
        )

        return OntologyDescription(
            vocabulary=namespace,
            label=resolved_label,
            description=resolved_description,
            preferred_namespace_prefix=resolved_prefix,
            preferred_namespace_uri=resolved_namespace_uri,
        )


def _load_bundled_spec(key: str) -> ReadOnlyGraphAggregate:
    filename = bundled_vocabulary_by_namespace(key).filename
    match Path(filename).suffix:
        case ".jsonld":
            format = "json-ld"
        case ".n3":
            format = "n3"
        case ".nt":
            format = "n"
        case ".rdf":
            format = "xml"
        case ".ttl":
            format = "turtle"
        case _:
            raise ValueError(f"Unknown file extension: {filename}")

    assert __package__ is not None
    with resources.path(__package__, filename) as bundled_path:
        graph = Graph()
        graph.parse(bundled_path, format=format)
        return ReadOnlyGraphAggregate([graph])


@dataclass(frozen=True, slots=True)
class _ExtractedOntologyMetadata:
    label: str | None = None
    description: str | None = None
    preferred_namespace_prefix: str | None = None
    preferred_namespace_uri: str | None = None


def _find_ontology(graph: Graph) -> URIRef | None:
    ontology = next(
        (
            subject
            for subject in graph.subjects(RDF.type, OWL.Ontology)
            if isinstance(subject, URIRef)
        ),
        None,
    )
    return ontology


def _resolve_title(graph: Graph, ontology: URIRef | None) -> str | None:
    if ontology is None:
        return None
    return _literal_to_str(graph.value(ontology, DC.title))


def _resolve_description(
    graph: Graph,
    ontology: URIRef | None,
) -> str | None:
    if ontology is not None:
        for predicate in (DC.description, RDFS.comment, DC.title):
            if (value := _literal_to_str(graph.value(ontology, predicate))) is not None:
                return value
    return None


def _extract_ontology_metadata(
    graph: Graph,
    namespace: URIRef,
) -> _ExtractedOntologyMetadata:
    ontology = _find_ontology(graph)
    if ontology is None and isinstance(graph.identifier, URIRef):
        ontology = graph.identifier
    if ontology is None:
        logger.warning(
            "Unable to dynamically infer ontology resource from graph %s",
            graph.identifier,
        )

    preferred_namespace_prefix = None
    preferred_namespace_uri = None
    if ontology is not None:
        preferred_namespace_prefix = _literal_to_str(
            graph.value(ontology, VANN.preferredNamespacePrefix)
        )
        preferred_namespace_uri = _literal_to_str(
            graph.value(ontology, VANN.preferredNamespaceUri)
        )

    return _ExtractedOntologyMetadata(
        label=_resolve_title(graph, ontology),
        description=_resolve_description(graph, ontology),
        preferred_namespace_prefix=preferred_namespace_prefix,
        preferred_namespace_uri=preferred_namespace_uri,
    )


def _literal_to_str(value: object) -> str | None:
    if not isinstance(value, Literal):
        return None
    literal_value = value.toPython()
    if isinstance(literal_value, str):
        return literal_value
    return None
