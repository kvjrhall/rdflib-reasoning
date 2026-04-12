import logging
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Final, Self

from rdflib import DC, FOAF, OWL, RDF, Graph, Literal, Namespace, URIRef
from rdflib.graph import ReadOnlyGraphAggregate
from rdflib.namespace import PROV, RDFS, VANN
from rdflib_reasoning.middleware.namespaces.spec_index import RDFVocabulary

logger = logging.getLogger(__name__)

# NOTE: Disabled caching and fetching remote specs for now; will revisit later.
# from platformdirs import user_cache_path
# KNOWN_SPECS: Final[Set[str]] = frozenset(
#     [
#         str(ns)
#         for ns in [
#             BRICK,
#             CSVW,
#             DC,
#             DCAM,
#             DCAT,
#             DCMITYPE,
#             DCTERMS,
#             DOAP,
#             FOAF,
#             ODRL2,
#             ORG,
#             OWL,
#             PROF,
#             PROV,
#             QB,
#             RDF,
#             RDFS,
#             SDO,
#             SH,
#             SKOS,
#             SOSA,
#             SSN,
#             TIME,
#             VANN,
#             VOID,
#             WGS,
#             XSD,
#         ]
#     ]
# )

_BUNDLED_SPEC_FILENAMES: Final[Mapping[str, str]] = MappingProxyType(
    {
        # str(BRICK): "brick.ttl",
        # str(CSVW): "csvw.ttl",
        # str(DC): "dc.ttl",
        # str(DCAT): "dcat.ttl",
        # str(DCMITYPE): "dctype.ttl",
        # str(DCTERMS): "dcterms.ttl",
        # str(DCAM): "dcam.ttl",
        # str(DOAP): "doap.ttl",
        str(FOAF): "foaf.rdf",
        # str(ODRL2): "odrl2.ttl",
        # str(ORG): "org.ttl",
        str(OWL): "owl.ttl",
        # str(PROF): "prof.ttl",
        str(PROV): "prov-o.ttl",
        # str(QB): "qb.ttl",
        str(RDF): "rdf.ttl",
        str(RDFS): "rdfs.ttl",
        # str(SDO): "sdo.ttl",
        # str(SH): "sh.ttl",
        # str(SKOS): "skos.ttl",
        # str(SOSA): "sosa.ttl",
        # str(SSN): "ssn.ttl",
        # str(TIME): "time.ttl",
        str(VANN): "vann.rdf",
        # str(VOID): "void.ttl",
        # str(WGS): "wgs.ttl",
        # str(XSD): "xsd.ttl",
    }
)


@dataclass(frozen=True, slots=True)
class VocabularyMetadata:
    label: str
    description: str


_DEFAULT_VOCABULARY_DESCRIPTION: Final[str] = (
    "The user supplied this RDF vocabulary for your task."
)
_DEFAULT_VOCABULARY_LABEL: Final[str] = "An Anonymous User-Supplied RDF Vocabulary"
_BUNDLED_VOCABULARY_METADATA: Final[Mapping[str, VocabularyMetadata]] = (
    MappingProxyType(
        {
            str(RDF): VocabularyMetadata(
                label="RDF",
                description=(
                    "Core RDF data model terms for statements, lists, containers, "
                    "and literal/datatype machinery."
                ),
            ),
            str(RDFS): VocabularyMetadata(
                label="RDFS",
                description=(
                    "Schema-level RDF terms for classes, properties, labels, "
                    "comments, domain/range, and hierarchy modeling."
                ),
            ),
            str(OWL): VocabularyMetadata(
                label="OWL",
                description=(
                    "Ontology modeling and logical constraint terms for classes, "
                    "restrictions, axioms, and richer property semantics."
                ),
            ),
            str(PROV): VocabularyMetadata(
                label="PROV-O",
                description=(
                    "Provenance terms for entities, activities, agents, and "
                    "qualified influence relationships."
                ),
            ),
            str(FOAF): VocabularyMetadata(
                label="FOAF",
                description=(
                    "People, agents, profiles, social connections, and related "
                    "online identity and metadata terms."
                ),
            ),
            str(VANN): VocabularyMetadata(
                label="VANN",
                description="A vocabulary for annotating vocabulary descriptions.",
            ),
        }
    )
)


@dataclass(frozen=True, slots=True)
class UserSpec:
    graph: Graph
    vocabulary: URIRef
    label: str
    description: str

    @classmethod
    def from_graph(
        cls,
        graph: Graph,
        namespace: Namespace | URIRef | str | None = None,
        label: str | None = None,
        description: str | None = None,
    ) -> Self:
        ontology = _find_ontology(graph)
        if namespace is None and isinstance(graph.identifier, URIRef):
            namespace = graph.identifier
        if namespace is None and ontology is not None:
            namespace = ontology
        if label is None:
            label = _resolve_title(graph, ontology)
        if description is None:
            description = _resolve_description(
                graph,
                ontology,
                fallback_to_default=False,
            )

        if namespace is None:
            logger.warning(
                "Unable to dynamically infer namespace from graph %s",
                graph.identifier,
            )

        vocabulary = URIRef(namespace) if namespace is not None else None
        if vocabulary is None:
            raise ValueError("Unable to infer vocabulary name from arguments or graph")

        label = label or _DEFAULT_VOCABULARY_LABEL
        description = description or _DEFAULT_VOCABULARY_DESCRIPTION

        return cls(
            graph=graph, vocabulary=vocabulary, label=label, description=description
        )


class SpecificationCache:
    # cache_path: Path
    _bundled_specs: frozenset[str]
    _specs: MutableMapping[str, ReadOnlyGraphAggregate]
    _metadata: MutableMapping[str, VocabularyMetadata]
    _vocabularies: MutableMapping[str, RDFVocabulary]

    def __init__(
        self,
        *,
        bundled_namespaces: Sequence[URIRef | Namespace | str],
        user_specs: Sequence[UserSpec] = (),
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
        for user_spec in user_specs:
            # We make a read-only copy of the graph to avoid external modifications
            g = Graph(identifier=user_spec.vocabulary)
            for prefix, uri in user_spec.graph.namespace_manager.namespaces():
                g.namespace_manager.bind(prefix, uri)
            for triple in user_spec.graph:
                g.add(triple)
            key = str(user_spec.vocabulary)
            self._specs[key] = ReadOnlyGraphAggregate([g])
            self._metadata[key] = VocabularyMetadata(
                label=user_spec.label,
                description=user_spec.description,
            )

    def get_spec(self, namespace: URIRef | Namespace | str) -> Graph:
        key = str(namespace)
        if key in self._specs:
            return self._specs[key]

        if key not in self._bundled_specs:
            raise ValueError(f"Namespace is not bundled or cached: {key}")

        filename = _BUNDLED_SPEC_FILENAMES[key]
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

        with resources.path(__package__, filename) as bundled_path:
            graph = Graph()
            graph.parse(bundled_path, format=format)
            self._specs[key] = ReadOnlyGraphAggregate([graph])

        return self._specs[key]

    def get_vocabulary(self, namespace: URIRef | Namespace | str) -> RDFVocabulary:
        key = str(namespace)
        if key in self._vocabularies:
            return self._vocabularies[key]

        vocabulary = RDFVocabulary.from_graph(namespace, self.get_spec(namespace))
        self._vocabularies[key] = vocabulary
        return vocabulary

    def get_vocabulary_metadata(
        self, namespace: URIRef | Namespace | str
    ) -> VocabularyMetadata:
        key = str(namespace)
        # Bundled vocabularies have static metadata.
        if key in _BUNDLED_VOCABULARY_METADATA:
            return _BUNDLED_VOCABULARY_METADATA[key]
        # User-supplied vocabularies have eagerly-computed metadata
        if key in self._metadata:
            return self._metadata[key]

        # Other cases, we'd build metadata on-the-fly.
        # NOTE: No mechanism currently exists to fetch specs dynamically, so
        #       this would raise an error out of `get_spec`.
        metadata = self._build_metadata(URIRef(key), self.get_spec(key))
        self._metadata[key] = metadata
        return metadata

    @staticmethod
    def has_bundled_resource(namespace: URIRef | Namespace | str) -> bool:
        return str(namespace) in _BUNDLED_SPEC_FILENAMES

    def _build_metadata(
        self,
        namespace: URIRef,
        graph: Graph,
        description: str | None = None,
    ) -> VocabularyMetadata:
        ontology = _find_ontology(graph)
        title = _resolve_title(graph, ontology)
        resolved_description = _resolve_description(
            graph,
            ontology,
            description=description,
        )
        assert resolved_description is not None
        return VocabularyMetadata(
            label=title or str(namespace),
            description=resolved_description,
        )


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
    description: str | None = None,
    *,
    fallback_to_default: bool = True,
) -> str | None:
    if description is not None:
        return description
    if ontology is not None:
        for predicate in (DC.description, RDFS.comment, DC.title):
            if (value := _literal_to_str(graph.value(ontology, predicate))) is not None:
                return value
    if fallback_to_default:
        return _DEFAULT_VOCABULARY_DESCRIPTION
    return None


def _literal_to_str(value: object) -> str | None:
    if not isinstance(value, Literal):
        return None
    literal_value = value.toPython()
    if isinstance(literal_value, str):
        return literal_value
    return None
