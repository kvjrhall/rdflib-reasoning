from dataclasses import dataclass
from typing import TypeAlias, cast

from rdflib import Namespace, URIRef
from rdflib.namespace import VANN, DefinedNamespace

from .namespaces._bundled import (
    DEFAULT_BUNDLED_VOCABULARIES,
    BundledVocabularyInfo,
    bundled_vocabularies_for_group,
    bundled_vocabulary_by_namespace,
)
from .namespaces.spec_cache import SpecificationCache, UserVocabularySource
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


def _merge_declarations(
    base: tuple["VocabularyDeclaration", ...],
    *declarations: "VocabularyDeclaration",
) -> tuple["VocabularyDeclaration", ...]:
    merged: dict[str, VocabularyDeclaration] = {
        declaration.namespace_uri: declaration for declaration in base
    }
    for declaration in declarations:
        merged[declaration.namespace_uri] = declaration
    return tuple(merged.values())


def _declaration_from_bundled_vocabulary(
    vocabulary: BundledVocabularyInfo,
) -> "VocabularyDeclaration":
    return VocabularyDeclaration(
        prefix=vocabulary.prefix,
        namespace=vocabulary.resolved_namespace,
    )


@dataclass(frozen=True, slots=True)
class VocabularyDeclaration:
    """One developer-facing vocabulary declaration used to derive shared config."""

    prefix: str
    namespace: Namespace | type[DefinedNamespace] | URIRef | str
    user_spec: UserVocabularySource | None = None

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
        return self.user_spec is not None or SpecificationCache.has_bundled_resource(
            self.namespace_uri
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
        return cls(
            declarations=_merge_declarations(
                tuple(
                    _declaration_from_bundled_vocabulary(vocabulary)
                    for vocabulary in DEFAULT_BUNDLED_VOCABULARIES
                ),
                *declarations,
            )
        )

    def plus(self, *declarations: VocabularyDeclaration) -> "VocabularyConfiguration":
        """Return a new configuration extended by the supplied declarations."""

        return VocabularyConfiguration(
            declarations=_merge_declarations(self.declarations, *declarations)
        )

    def plus_dublin_core(self) -> "VocabularyConfiguration":
        """Add the extended Dublin Core published as ISO 15836-2:2019: https://www.iso.org/standard/71341.html."""

        return self.plus(
            *(
                _declaration_from_bundled_vocabulary(vocabulary)
                for vocabulary in bundled_vocabularies_for_group("dublin_core")
            )
        )

    def plus_vann(self) -> "VocabularyConfiguration":
        """Add the bundled VANN vocabulary declaration to this configuration."""

        return self.plus(
            _declaration_from_bundled_vocabulary(bundled_vocabulary_by_namespace(VANN))
        )

    def build_context(self) -> VocabularyContext:
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
