import json

import pytest
from rdflib import Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD
from rdflib_reasoning.middleware.namespaces.spec_whitelist import (
    RestrictedNamespaceWhitelist,
    WhitelistedTerm,
    WhitelistEntry,
    WhitelistResult,
    _closed_vocab_local_names,
    _levenshtein,
)


def _core_entries() -> tuple[WhitelistEntry, ...]:
    return (
        WhitelistEntry(prefix="owl", namespace=OWL),
        WhitelistEntry(prefix="rdf", namespace=RDF),
        WhitelistEntry(prefix="rdfs", namespace=RDFS),
        WhitelistEntry(prefix="xsd", namespace=XSD),
    )


def _core_plus_open_entries() -> tuple[WhitelistEntry, ...]:
    return _core_entries() + (
        WhitelistEntry(prefix="ex", namespace=Namespace("http://example.org/voc#")),
    )


class TestWhitelistedTermSchema:
    def test_json_schema_structure(self) -> None:
        schema = WhitelistedTerm.model_json_schema()
        try:
            assert schema["title"] == "WhitelistedTerm"
            assert "A whitelisted term from a namespace." in schema["description"]
            assert schema["type"] == "object"
            assert schema["properties"] is not None
            assert schema["properties"]["namespace"] is not None
            assert schema["properties"]["vocabulary_type"] is not None
            assert schema["properties"]["prefix"] is not None
            assert schema["properties"]["term"] is not None
            assert schema["properties"]["qname"] is not None
        except Exception:
            print(json.dumps(schema, indent=2))
            raise

    def test_roundtrip_json(self) -> None:
        expected = WhitelistedTerm(
            namespace="http://www.w3.org/2000/01/rdf-schema#",
            vocabulary_type="closed",
            prefix="rdfs",
            term=URIRef("http://www.w3.org/2000/01/rdf-schema#Class"),
            qname="rdfs:Class",
        )
        actual = WhitelistedTerm.model_validate_json(expected.model_dump_json())
        assert actual == expected

    def test_roundtrip_python(self) -> None:
        expected = WhitelistedTerm(
            namespace="http://www.w3.org/2000/01/rdf-schema#",
            vocabulary_type="closed",
            prefix="rdfs",
            term=URIRef("http://www.w3.org/2000/01/rdf-schema#Class"),
            qname="rdfs:Class",
        )
        actual = WhitelistedTerm.model_validate(expected.model_dump())
        assert actual == expected

    def test_open_vocabulary_type(self) -> None:
        term = WhitelistedTerm(
            namespace="http://example.org/voc#",
            vocabulary_type="open",
            prefix="ex",
            term=URIRef("http://example.org/voc#Thing"),
            qname="ex:Thing",
        )
        assert term.vocabulary_type == "open"
        roundtripped = WhitelistedTerm.model_validate_json(term.model_dump_json())
        assert roundtripped == term


class TestWhitelistResultSchema:
    def test_json_schema_structure(self) -> None:
        schema = WhitelistResult.model_json_schema()
        try:
            assert schema["properties"]["allowed"] is not None
            assert schema["properties"]["term"] is not None
            assert schema["properties"]["nearest_matches"] is not None
            assert "$defs" in schema
            assert "MatchDistance" in schema["$defs"]
            match_def = schema["$defs"]["MatchDistance"]
            assert match_def["type"] == "integer"
            assert match_def["minimum"] == 0
            assert all(isinstance(ex, int) for ex in match_def["examples"])
        except Exception:
            print(json.dumps(schema, indent=2))
            raise

    def test_roundtrip_rejected_result_with_matches(self) -> None:
        suggestion = WhitelistedTerm(
            namespace="http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            vocabulary_type="closed",
            prefix="rdf",
            term=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
            qname="rdf:type",
        )
        result = WhitelistResult(
            allowed=False, term=None, nearest_matches=[(suggestion, 1)]
        )
        roundtripped = WhitelistResult.model_validate_json(result.model_dump_json())
        assert roundtripped.allowed is False
        assert roundtripped.term is None
        assert len(roundtripped.nearest_matches) == 1
        assert roundtripped.nearest_matches[0][0] == suggestion
        assert roundtripped.nearest_matches[0][1] == 1


class TestLevenshtein:
    def test_identical_strings(self) -> None:
        assert _levenshtein("abc", "abc") == 0

    def test_empty_strings(self) -> None:
        assert _levenshtein("", "") == 0

    def test_one_empty(self) -> None:
        assert _levenshtein("abc", "") == 3
        assert _levenshtein("", "abc") == 3

    def test_single_insertion(self) -> None:
        assert _levenshtein("Class", "Classs") == 1

    def test_single_substitution(self) -> None:
        assert _levenshtein("type", "typo") == 1

    def test_qname_cross_namespace(self) -> None:
        assert _levenshtein("rdfs:type", "rdf:type") == 1


class TestClosedVocabLocalNames:
    def test_rdfs_contains_expected_terms(self) -> None:
        names = _closed_vocab_local_names(RDFS)
        assert "Class" in names
        assert "subClassOf" in names
        assert "label" in names
        assert "comment" in names

    def test_excludes_private_attrs(self) -> None:
        names = _closed_vocab_local_names(RDFS)
        assert "_NS" not in names
        assert "_fail" not in names
        assert "_warn" not in names
        assert "_extras" not in names


class TestEnumeratePrompt:
    def test_contains_explicit_prefixes(self) -> None:
        prompt = RestrictedNamespaceWhitelist(_core_entries()).enumerate_prompt()
        assert prompt is not None
        assert "owl:" in prompt
        assert "rdf:" in prompt
        assert "rdfs:" in prompt
        assert "xsd:" in prompt

    def test_distinguishes_open_and_closed_entries(self) -> None:
        prompt = RestrictedNamespaceWhitelist(
            _core_plus_open_entries()
        ).enumerate_prompt()
        assert prompt is not None
        assert "(closed)" in prompt
        assert "(open)" in prompt
        assert "ex:" in prompt

    def test_includes_rejection_policy(self) -> None:
        prompt = RestrictedNamespaceWhitelist(_core_entries()).enumerate_prompt()
        assert prompt is not None
        assert "add_triples" in prompt
        assert "MUST NOT use that rejected IRI" in prompt


class TestRestrictedNamespaceWhitelist:
    @pytest.fixture(scope="class")
    def wl(self) -> RestrictedNamespaceWhitelist:
        return RestrictedNamespaceWhitelist(_core_entries())

    def test_allows_namespace_checks_declared_entries(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        assert wl.allows_namespace(str(RDF)) is True
        assert wl.allows_namespace("http://example.org/ns#") is False

    def test_valid_closed_term_allowed(self, wl: RestrictedNamespaceWhitelist) -> None:
        result = wl.find_term(RDF.type)
        assert result.allowed is True
        assert result.term is not None
        assert result.term.qname == "rdf:type"
        assert result.term.vocabulary_type == "closed"

    def test_valid_closed_term_metadata(self, wl: RestrictedNamespaceWhitelist) -> None:
        result = wl.find_term(RDFS.Class)
        assert result.allowed is True
        assert result.term is not None
        assert result.term.prefix == "rdfs"
        assert result.term.namespace == str(RDFS._NS)
        assert result.term.term == RDFS.Class

    def test_unknown_namespace_rejected_no_suggestions(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        result = wl.find_term(URIRef("http://totally-unknown.example/foo"))
        assert result.allowed is False
        assert result.term is None
        assert result.nearest_matches == []

    def test_intra_namespace_typo_suggests_same_namespace_first(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        result = wl.find_term(URIRef("http://www.w3.org/2000/01/rdf-schema#Classs"))
        assert result.allowed is False
        assert len(result.nearest_matches) >= 1
        assert result.nearest_matches[0][0].qname == "rdfs:Class"
        assert result.nearest_matches[0][1] == 1

    def test_intra_namespace_typo_includes_cross_namespace(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        result = wl.find_term(URIRef("http://www.w3.org/2000/01/rdf-schema#Classs"))
        qnames = [t.qname for t, _ in result.nearest_matches]
        assert "owl:Class" in qnames

    def test_cross_namespace_confusion_rdfs_type(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        result = wl.find_term(URIRef("http://www.w3.org/2000/01/rdf-schema#type"))
        assert result.allowed is False
        assert len(result.nearest_matches) >= 1
        assert result.nearest_matches[0][0].qname == "rdf:type"
        assert result.nearest_matches[0][1] == 1

    def test_top_k_capped_at_three(self, wl: RestrictedNamespaceWhitelist) -> None:
        result = wl.find_term(URIRef("http://www.w3.org/2000/01/rdf-schema#type"))
        assert len(result.nearest_matches) <= 3

    def test_qname_index_has_cross_vocab_entries(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        assert "Class" in wl._qname_index
        assert {t.prefix for t in wl._qname_index["Class"]} == {"owl", "rdfs"}


class TestRestrictedNamespaceWhitelistOpenVocabulary:
    @pytest.fixture(scope="class")
    def wl(self) -> RestrictedNamespaceWhitelist:
        return RestrictedNamespaceWhitelist(_core_plus_open_entries())

    def test_open_vocab_term_allowed(self, wl: RestrictedNamespaceWhitelist) -> None:
        result = wl.find_term(URIRef("http://example.org/voc#AnyTerm"))
        assert result.allowed is True
        assert result.term is not None
        assert result.term.vocabulary_type == "open"
        assert result.term.prefix == "ex"
        assert result.term.qname == "ex:AnyTerm"

    def test_closed_vocab_terms_still_work(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        result = wl.find_term(RDF.type)
        assert result.allowed is True
        assert result.term is not None
        assert result.term.qname == "rdf:type"
