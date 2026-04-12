from dataclasses import dataclass
from typing import TypeAlias, cast

from rdflib import Namespace, URIRef
from rdflib.namespace import FOAF, OWL, PROV, RDF, RDFS, DefinedNamespace

from .namespaces.spec_cache import SpecificationCache, UserSpec
from .namespaces.spec_whitelist import RestrictedNamespaceWhitelist, WhitelistEntry

VocabularyNamespace: TypeAlias = Namespace | type[DefinedNamespace] | URIRef | str
ResolvedVocabularyNamespace: TypeAlias = Namespace | type[DefinedNamespace]


def _coerce_namespace(
    namespace: VocabularyNamespace,
) -> ResolvedVocabularyNamespace:
    if isinstance(namespace, Namespace):
        return namespace
    if isinstance(namespace, URIRef):
        return Namespace(str(namespace))
    if isinstance(namespace, str):
        return Namespace(namespace)
    if isinstance(namespace, type) and issubclass(namespace, DefinedNamespace):
        return namespace
    raise TypeError(f"Unsupported vocabulary namespace: {namespace!r}")


def _namespace_uri(namespace: ResolvedVocabularyNamespace) -> str:
    if isinstance(namespace, Namespace):
        return str(namespace)
    return str(namespace._NS)


def _standard_bundled_declarations() -> tuple["VocabularyDeclaration", ...]:
    return STANDARD_BUNDLED_VOCABULARY_DECLARATIONS


@dataclass(frozen=True, slots=True)
class VocabularyDeclaration:
    """One developer-facing vocabulary declaration used to derive shared config."""

    prefix: str
    namespace: Namespace | type[DefinedNamespace] | URIRef | str
    user_spec: UserSpec | None = None

    def __post_init__(self) -> None:
        coerced_namespace = _coerce_namespace(self.namespace)
        object.__setattr__(self, "namespace", coerced_namespace)
        spec_vocab = (
            str(self.user_spec.vocabulary) if self.user_spec is not None else None
        )
        if spec_vocab is not None and spec_vocab != self.namespace_uri:
            raise ValueError(
                f"VocabularyDeclaration.user_spec vocabulary {spec_vocab} does not match the declared namespace {self.namespace_uri}"
            )

    @property
    def resolved_namespace(self) -> ResolvedVocabularyNamespace:
        return cast(ResolvedVocabularyNamespace, self.namespace)

    @property
    def namespace_uri(self) -> str:
        return _namespace_uri(self.resolved_namespace)

    def as_whitelist_entry(self) -> WhitelistEntry:
        return WhitelistEntry(prefix=self.prefix, namespace=self.resolved_namespace)

    @property
    def is_indexed(self) -> bool:
        return (
            self.user_spec is not None
            or self.namespace_uri in _STANDARD_BUNDLED_NAMESPACE_URIS
        )


@dataclass(frozen=True, slots=True)
class VocabularyContext:
    """Validated runtime vocabulary state derived from a configuration."""

    declarations: tuple[VocabularyDeclaration, ...]
    _whitelist: RestrictedNamespaceWhitelist
    _specification_cache: SpecificationCache
    _indexed_vocabularies: tuple[str, ...]

    @property
    def whitelist(self) -> RestrictedNamespaceWhitelist:
        return self._whitelist

    @property
    def specification_cache(self) -> SpecificationCache:
        return self._specification_cache

    @property
    def indexed_vocabularies(self) -> tuple[str, ...]:
        return self._indexed_vocabularies


@dataclass(frozen=True, slots=True)
class VocabularyConfiguration:
    """Declarative vocabulary setup for building a shared vocabulary context."""

    declarations: tuple[VocabularyDeclaration, ...] = ()

    @classmethod
    def bundled_plus(
        cls, *declarations: VocabularyDeclaration
    ) -> "VocabularyConfiguration":
        merged: dict[str, VocabularyDeclaration] = {
            declaration.namespace_uri: declaration
            for declaration in _standard_bundled_declarations()
        }
        for declaration in declarations:
            merged[declaration.namespace_uri] = declaration
        return cls(declarations=tuple(merged.values()))

    def build_context(self) -> VocabularyContext:
        for declaration in _standard_bundled_declarations():
            if not SpecificationCache.has_bundled_resource(declaration.namespace_uri):
                raise ValueError(
                    "Standard bundled vocabulary declaration has no bundled resource: "
                    f"{declaration.namespace_uri}"
                )
        whitelist = RestrictedNamespaceWhitelist(
            declaration.as_whitelist_entry() for declaration in self.declarations
        )
        indexed_vocabularies = tuple(
            sorted(
                declaration.namespace_uri
                for declaration in self.declarations
                if declaration.is_indexed
            )
        )
        specification_cache = SpecificationCache(
            bundled_namespaces=indexed_vocabularies,
            user_specs=tuple(
                declaration.user_spec
                for declaration in self.declarations
                if declaration.user_spec is not None
            ),
        )
        assert set(indexed_vocabularies).issubset(
            {entry.namespace_uri for entry in self.declarations}
        )
        return VocabularyContext(
            declarations=self.declarations,
            _whitelist=whitelist,
            _specification_cache=specification_cache,
            _indexed_vocabularies=indexed_vocabularies,
        )


STANDARD_BUNDLED_VOCABULARY_DECLARATIONS = (
    VocabularyDeclaration(prefix="foaf", namespace=FOAF),
    VocabularyDeclaration(prefix="owl", namespace=OWL),
    VocabularyDeclaration(prefix="prov", namespace=PROV),
    VocabularyDeclaration(prefix="rdf", namespace=RDF),
    VocabularyDeclaration(prefix="rdfs", namespace=RDFS),
)

_STANDARD_BUNDLED_NAMESPACE_URIS = frozenset(
    declaration.namespace_uri
    for declaration in STANDARD_BUNDLED_VOCABULARY_DECLARATIONS
)
