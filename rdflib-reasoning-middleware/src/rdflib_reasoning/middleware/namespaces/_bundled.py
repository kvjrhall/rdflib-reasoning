from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from types import MappingProxyType
from typing import Final, TypeAlias, cast

from rdflib import Namespace, URIRef
from rdflib.namespace import (
    DCAM,
    DCMITYPE,
    DCTERMS,
    FOAF,
    OWL,
    PROV,
    RDF,
    RDFS,
    SKOS,
    VANN,
    DefinedNamespace,
)

BundledVocabularyNamespace: TypeAlias = (
    Namespace | type[DefinedNamespace] | URIRef | str
)
ResolvedBundledVocabularyNamespace: TypeAlias = Namespace | type[DefinedNamespace]


def _coerce_namespace(
    namespace: BundledVocabularyNamespace,
) -> ResolvedBundledVocabularyNamespace:
    if isinstance(namespace, Namespace):
        return namespace
    if isinstance(namespace, URIRef):
        return Namespace(str(namespace))
    if isinstance(namespace, str):
        return Namespace(namespace)
    if isinstance(namespace, type) and issubclass(namespace, DefinedNamespace):
        return namespace
    raise TypeError(f"Unsupported vocabulary namespace: {namespace!r}")


def _namespace_uri(namespace: ResolvedBundledVocabularyNamespace) -> str:
    if isinstance(namespace, Namespace):
        return str(namespace)
    return str(namespace._NS)


class BundledVocabularyRegistryError(Exception):
    """Raised when the bundled vocabulary registry is internally inconsistent."""


@dataclass(frozen=True, kw_only=True, slots=True)
class BundledVocabularyInfo:
    description: str
    filename: str
    label: str
    namespace: BundledVocabularyNamespace
    prefix: str
    default_enabled: bool = False
    groups: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "namespace", _coerce_namespace(self.namespace))

    @property
    def resolved_namespace(self) -> ResolvedBundledVocabularyNamespace:
        return cast(ResolvedBundledVocabularyNamespace, self.namespace)

    @property
    def namespace_uri(self) -> str:
        return _namespace_uri(self.resolved_namespace)


ALL_BUNDLED_VOCABULARIES: Final[tuple[BundledVocabularyInfo, ...]] = (
    BundledVocabularyInfo(
        description="Terms used in the _description_ of DCMI metadata terms.",
        filename="dcam.ttl",
        label="DCAM",
        namespace=DCAM,
        prefix="dcam",
        groups=frozenset({"dublin_core"}),
    ),
    BundledVocabularyInfo(
        description=(
            "DCMI Type Vocabulary, which defines classes for basic types of thing "
            "that can be described using DCMI metadata terms."
        ),
        filename="dcmitype.ttl",
        label="DCMITYPE",
        namespace=DCMITYPE,
        prefix="dcmitype",
        groups=frozenset({"dublin_core"}),
    ),
    BundledVocabularyInfo(
        description=(
            "Properties and terms coined outside of the original fifteen-element "
            "Dublin Core and published as ISO 15836-2:2019"
        ),
        filename="dcterms.ttl",
        label="DCTERMS",
        namespace=DCTERMS,
        prefix="dcterms",
        groups=frozenset({"dublin_core"}),
    ),
    BundledVocabularyInfo(
        description=(
            "People, agents, profiles, social connections, and related online "
            "identity and metadata terms."
        ),
        filename="foaf.rdf",
        label="FOAF",
        namespace=FOAF,
        prefix="foaf",
        default_enabled=True,
    ),
    BundledVocabularyInfo(
        description=(
            "Ontology modeling and logical constraint terms for classes, "
            "restrictions, axioms, and richer property semantics."
        ),
        filename="owl.ttl",
        label="OWL",
        namespace=OWL,
        prefix="owl",
        default_enabled=True,
    ),
    BundledVocabularyInfo(
        description=(
            "Provenance terms for entities, activities, agents, and qualified "
            "influence relationships."
        ),
        filename="prov-o.ttl",
        label="PROV-O",
        namespace=PROV,
        prefix="prov",
        default_enabled=True,
    ),
    BundledVocabularyInfo(
        description=(
            "Core RDF data model terms for statements, lists, containers, and "
            "literal/datatype machinery."
        ),
        filename="rdf.ttl",
        label="RDF",
        namespace=RDF,
        prefix="rdf",
        default_enabled=True,
    ),
    BundledVocabularyInfo(
        description=(
            "Schema-level RDF terms for classes, properties, labels, comments, "
            "domain/range, and hierarchy modeling."
        ),
        filename="rdfs.ttl",
        label="RDFS",
        namespace=RDFS,
        prefix="rdfs",
        default_enabled=True,
    ),
    BundledVocabularyInfo(
        description=(
            "The Simple Knowledge Organization System (SKOS) is a common data model "
            "for sharing and linking knowledge organization systems via the "
            "Semantic Web."
        ),
        filename="skos.rdf",
        label="SKOS",
        namespace=SKOS,
        prefix="skos",
        default_enabled=True,
    ),
    BundledVocabularyInfo(
        description="A vocabulary for annotating vocabulary descriptions.",
        filename="vann.rdf",
        label="VANN",
        namespace=VANN,
        prefix="vann",
        groups=frozenset({"vann"}),
    ),
)

DEFAULT_BUNDLED_VOCABULARIES: Final[tuple[BundledVocabularyInfo, ...]] = tuple(
    vocabulary
    for vocabulary in ALL_BUNDLED_VOCABULARIES
    if vocabulary.default_enabled is True
)

_grouped_vocabularies: dict[str, list[BundledVocabularyInfo]] = defaultdict(list)
for vocabulary in ALL_BUNDLED_VOCABULARIES:
    for group in vocabulary.groups:
        _grouped_vocabularies[group].append(vocabulary)

BUNDLED_VOCABULARY_GROUPS: Final[Mapping[str, tuple[BundledVocabularyInfo, ...]]] = (
    MappingProxyType(
        {
            group: tuple(vocabularies)
            for group, vocabularies in sorted(_grouped_vocabularies.items())
        }
    )
)

_BUNDLED_VOCABULARY_BY_NAMESPACE: Final[Mapping[str, BundledVocabularyInfo]] = (
    MappingProxyType(
        {
            vocabulary.namespace_uri: vocabulary
            for vocabulary in ALL_BUNDLED_VOCABULARIES
        }
    )
)


def bundled_vocabulary_by_namespace(
    namespace: BundledVocabularyNamespace,
) -> BundledVocabularyInfo:
    return _BUNDLED_VOCABULARY_BY_NAMESPACE[
        _namespace_uri(_coerce_namespace(namespace))
    ]


def bundled_vocabularies_for_group(group: str) -> tuple[BundledVocabularyInfo, ...]:
    return BUNDLED_VOCABULARY_GROUPS.get(group, ())


def has_bundled_vocabulary(namespace: BundledVocabularyNamespace) -> bool:
    return (
        _namespace_uri(_coerce_namespace(namespace)) in _BUNDLED_VOCABULARY_BY_NAMESPACE
    )


def _resource_file_exists(filename: str) -> bool:
    assert __package__ is not None
    return resources.files(__package__).joinpath(filename).is_file()


def _validate_registry(
    vocabularies: tuple[BundledVocabularyInfo, ...] = ALL_BUNDLED_VOCABULARIES,
) -> None:
    problems: list[str] = []

    namespace_uris = [vocabulary.namespace_uri for vocabulary in vocabularies]
    prefixes = [vocabulary.prefix for vocabulary in vocabularies]
    filenames = [vocabulary.filename for vocabulary in vocabularies]

    duplicate_namespaces = sorted(
        namespace_uri
        for namespace_uri in set(namespace_uris)
        if namespace_uris.count(namespace_uri) > 1
    )
    duplicate_prefixes = sorted(
        prefix for prefix in set(prefixes) if prefixes.count(prefix) > 1
    )
    duplicate_filenames = sorted(
        filename for filename in set(filenames) if filenames.count(filename) > 1
    )
    missing_files = sorted(
        vocabulary.filename
        for vocabulary in vocabularies
        if _resource_file_exists(vocabulary.filename) is False
    )

    if duplicate_namespaces:
        problems.append(f"duplicate namespaces: {duplicate_namespaces}")
    if duplicate_prefixes:
        problems.append(f"duplicate prefixes: {duplicate_prefixes}")
    if duplicate_filenames:
        problems.append(f"duplicate filenames: {duplicate_filenames}")
    if missing_files:
        problems.append(f"missing packaged vocabulary files: {missing_files}")

    if problems:
        joined = "; ".join(problems)
        raise BundledVocabularyRegistryError(
            f"Bundled vocabulary registry is invalid: {joined}"
        )


_validate_registry()


__all__ = [
    "ALL_BUNDLED_VOCABULARIES",
    "BUNDLED_VOCABULARY_GROUPS",
    "DEFAULT_BUNDLED_VOCABULARIES",
    "BundledVocabularyInfo",
    "BundledVocabularyRegistryError",
    "bundled_vocabularies_for_group",
    "bundled_vocabulary_by_namespace",
    "has_bundled_vocabulary",
]
