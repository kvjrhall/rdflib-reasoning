import pytest
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
)
from rdflib_reasoning.middleware.namespaces._bundled import (
    ALL_BUNDLED_VOCABULARIES,
    BUNDLED_VOCABULARY_GROUPS,
    DEFAULT_BUNDLED_VOCABULARIES,
    BundledVocabularyInfo,
    BundledVocabularyRegistryError,
    _validate_registry,
    bundled_vocabularies_for_group,
    bundled_vocabulary_by_namespace,
    has_bundled_vocabulary,
)


def test_all_bundled_entries_expose_normalized_namespace_uris() -> None:
    assert all(
        vocabulary.namespace_uri == str(vocabulary.namespace)
        for vocabulary in ALL_BUNDLED_VOCABULARIES
    )


def test_default_bundled_vocabularies_match_expected_v030_default_set() -> None:
    assert {
        vocabulary.namespace_uri for vocabulary in DEFAULT_BUNDLED_VOCABULARIES
    } == {
        str(FOAF),
        str(OWL),
        str(PROV),
        str(RDF),
        str(RDFS),
        str(SKOS),
    }


def test_all_bundled_vocabularies_include_vann() -> None:
    assert str(VANN) in {
        vocabulary.namespace_uri for vocabulary in ALL_BUNDLED_VOCABULARIES
    }


def test_dublin_core_group_contains_exact_expected_vocabularies() -> None:
    assert {
        vocabulary.namespace_uri
        for vocabulary in bundled_vocabularies_for_group("dublin_core")
    } == {str(DCAM), str(DCMITYPE), str(DCTERMS)}


def test_vann_group_contains_only_vann() -> None:
    assert {
        vocabulary.namespace_uri
        for vocabulary in bundled_vocabularies_for_group("vann")
    } == {str(VANN)}


def test_group_views_match_exported_mapping() -> None:
    assert (
        bundled_vocabularies_for_group("dublin_core")
        == BUNDLED_VOCABULARY_GROUPS["dublin_core"]
    )


@pytest.mark.parametrize(
    "namespace",
    (
        FOAF,
        Namespace(str(FOAF)),
        URIRef(str(FOAF)),
        str(FOAF),
    ),
)
def test_bundled_vocabulary_lookup_accepts_supported_namespace_forms(
    namespace: object,
) -> None:
    vocabulary = bundled_vocabulary_by_namespace(namespace)

    assert vocabulary.namespace_uri == str(FOAF)
    assert vocabulary.prefix == "foaf"


def test_has_bundled_vocabulary_reports_known_and_unknown_namespaces() -> None:
    assert has_bundled_vocabulary(FOAF) is True
    assert has_bundled_vocabulary("urn:example:not-bundled#") is False


def test_validate_registry_rejects_duplicate_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "rdflib_reasoning.middleware.namespaces._bundled._resource_file_exists",
        lambda filename: True,
    )
    duplicate = (
        BundledVocabularyInfo(
            description="One",
            filename="one.ttl",
            label="One",
            namespace=FOAF,
            prefix="one",
        ),
        BundledVocabularyInfo(
            description="Two",
            filename="two.ttl",
            label="Two",
            namespace=FOAF,
            prefix="two",
        ),
    )

    with pytest.raises(BundledVocabularyRegistryError, match="duplicate namespaces"):
        _validate_registry(duplicate)


def test_validate_registry_rejects_duplicate_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "rdflib_reasoning.middleware.namespaces._bundled._resource_file_exists",
        lambda filename: True,
    )
    duplicate = (
        BundledVocabularyInfo(
            description="One",
            filename="one.ttl",
            label="One",
            namespace=FOAF,
            prefix="dup",
        ),
        BundledVocabularyInfo(
            description="Two",
            filename="two.ttl",
            label="Two",
            namespace=OWL,
            prefix="dup",
        ),
    )

    with pytest.raises(BundledVocabularyRegistryError, match="duplicate prefixes"):
        _validate_registry(duplicate)


def test_validate_registry_rejects_duplicate_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "rdflib_reasoning.middleware.namespaces._bundled._resource_file_exists",
        lambda filename: True,
    )
    duplicate = (
        BundledVocabularyInfo(
            description="One",
            filename="dup.ttl",
            label="One",
            namespace=FOAF,
            prefix="one",
        ),
        BundledVocabularyInfo(
            description="Two",
            filename="dup.ttl",
            label="Two",
            namespace=OWL,
            prefix="two",
        ),
    )

    with pytest.raises(BundledVocabularyRegistryError, match="duplicate filenames"):
        _validate_registry(duplicate)


def test_validate_registry_rejects_missing_packaged_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "rdflib_reasoning.middleware.namespaces._bundled._resource_file_exists",
        lambda filename: filename != "missing.ttl",
    )
    invalid = (
        BundledVocabularyInfo(
            description="Missing",
            filename="missing.ttl",
            label="Missing",
            namespace=FOAF,
            prefix="missing",
        ),
    )

    with pytest.raises(
        BundledVocabularyRegistryError, match="missing packaged vocabulary files"
    ):
        _validate_registry(invalid)


def test_declared_registry_files_exist_as_packaged_resources() -> None:
    _validate_registry(ALL_BUNDLED_VOCABULARIES)
