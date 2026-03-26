import json

import pytest
from rdflib import Namespace, URIRef
from rdflib.namespace import RDF, RDFS
from rdflib_reasoning.middleware.namespaces.spec_whitelist import (
    AllowAllNamespaceWhitelist,
    RestrictedNamespaceWhitelist,
    WhitelistedTerm,
    WhitelistEntry,
    WhitelistResult,
    _closed_vocab_local_names,
    _levenshtein,
)

# =============================================================================
# Schema-facing model tests
# =============================================================================


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

    def test_match_distance_examples_are_integers(self) -> None:
        """MatchDistance examples must be valid instances of the type (int, not str)."""
        schema = WhitelistResult.model_json_schema()
        examples = schema["$defs"]["MatchDistance"]["examples"]
        assert len(examples) >= 2
        for ex in examples:
            assert isinstance(ex, int), f"Expected int, got {type(ex).__name__}: {ex!r}"

    def test_roundtrip_allowed_result(self) -> None:
        term = WhitelistedTerm(
            namespace="http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            vocabulary_type="closed",
            prefix="rdf",
            term=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
            qname="rdf:type",
        )
        result = WhitelistResult(allowed=True, term=term, nearest_matches=[])
        roundtripped = WhitelistResult.model_validate_json(result.model_dump_json())
        assert roundtripped.allowed is True
        assert roundtripped.term == term
        assert roundtripped.nearest_matches == []

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


# =============================================================================
# _levenshtein tests
# =============================================================================


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

    def test_symmetric(self) -> None:
        assert _levenshtein("abc", "xyz") == _levenshtein("xyz", "abc")


# =============================================================================
# _closed_vocab_local_names tests
# =============================================================================


class TestClosedVocabLocalNames:
    def test_rdfs_contains_expected_terms(self) -> None:
        names = _closed_vocab_local_names(RDFS)
        assert "Class" in names
        assert "subClassOf" in names
        assert "label" in names
        assert "comment" in names

    def test_rdf_contains_expected_terms(self) -> None:
        names = _closed_vocab_local_names(RDF)
        assert "type" in names
        assert "Property" in names

    def test_excludes_private_attrs(self) -> None:
        names = _closed_vocab_local_names(RDFS)
        assert "_NS" not in names
        assert "_fail" not in names
        assert "_warn" not in names
        assert "_extras" not in names


# =============================================================================
# AllowAllNamespaceWhitelist tests
# =============================================================================


class TestAllowAllNamespaceWhitelist:
    def test_allows_any_uri(self) -> None:
        wl = AllowAllNamespaceWhitelist()
        result = wl.find_term(URIRef("http://anything.example/whatever"))
        assert result.allowed is True
        assert result.term is None
        assert result.nearest_matches == []

    def test_enumerate_prompt_returns_none(self) -> None:
        wl = AllowAllNamespaceWhitelist()
        assert wl.enumerate_prompt() is None


# =============================================================================
# enumerate_prompt tests
# =============================================================================


class TestEnumeratePrompt:
    def test_restricted_contains_all_prefixes(self) -> None:
        wl = RestrictedNamespaceWhitelist()
        prompt = wl.enumerate_prompt()
        assert prompt is not None
        assert "owl:" in prompt
        assert "rdf:" in prompt
        assert "rdfs:" in prompt
        assert "xsd:" in prompt

    def test_restricted_distinguishes_open_and_closed(self) -> None:
        wl = RestrictedNamespaceWhitelist().plus_entries(
            ("ex", Namespace("http://example.org/voc#"))
        )
        prompt = wl.enumerate_prompt()
        assert prompt is not None
        assert "(closed)" in prompt
        assert "(open)" in prompt
        assert "ex:" in prompt

    def test_restricted_contains_namespace_uris(self) -> None:
        wl = RestrictedNamespaceWhitelist()
        prompt = wl.enumerate_prompt()
        assert prompt is not None
        assert "http://www.w3.org/2002/07/owl#" in prompt
        assert "http://www.w3.org/1999/02/22-rdf-syntax-ns#" in prompt

    def test_enumerate_prompt_rejection_policy(self) -> None:
        prompt = RestrictedNamespaceWhitelist().enumerate_prompt()
        assert prompt is not None
        assert "add_triples" in prompt
        assert "MUST NOT use that rejected IRI" in prompt


# =============================================================================
# RestrictedNamespaceWhitelist tests -- DEFAULT_ENTRIES
# =============================================================================


class TestRestrictedNamespaceWhitelistDefaults:
    """Tests using DEFAULT_ENTRIES (OWL, RDF, RDFS, XSD)."""

    @pytest.fixture(scope="class")
    def wl(self) -> RestrictedNamespaceWhitelist:
        return RestrictedNamespaceWhitelist()

    def test_default_entries_are_four_core_vocabs(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        prefixes = {e.prefix for e in wl.entries}
        assert prefixes == {"owl", "rdf", "rdfs", "xsd"}

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
        top = result.nearest_matches[0]
        assert top[0].qname == "rdfs:Class"
        assert top[1] == 1

    def test_intra_namespace_typo_includes_cross_namespace(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        """Two-stage filtering should include owl:Class for rdfs:Classs."""
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

    def test_nearest_matches_sorted_by_distance(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        result = wl.find_term(URIRef("http://www.w3.org/2000/01/rdf-schema#Classs"))
        distances = [d for _, d in result.nearest_matches]
        assert distances == sorted(distances)

    def test_qname_index_spans_all_closed_vocabs(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        assert "type" in wl._qname_index
        assert any(t.prefix == "rdf" for t in wl._qname_index["type"])

    def test_qname_index_has_cross_vocab_entries(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        assert "Class" in wl._qname_index
        prefixes = {t.prefix for t in wl._qname_index["Class"]}
        assert prefixes == {"owl", "rdfs"}


# =============================================================================
# RestrictedNamespaceWhitelist tests -- ALL_RDFLIB_ENTRIES
# =============================================================================

# NOTE: ALL_RDFLIB_ENTRIES indexes ~5500 terms; WhitelistedTerm construction
# takes ~7ms each due to N3IRIRef regex validation, making init ~42s.
# scope="class" ensures we build this only once per test class.


class TestRestrictedNamespaceWhitelistAllRdflib:
    """Tests using ALL_RDFLIB_ENTRIES."""

    @pytest.fixture(scope="class")
    def wl(self) -> RestrictedNamespaceWhitelist:
        return RestrictedNamespaceWhitelist(
            RestrictedNamespaceWhitelist.ALL_RDFLIB_ENTRIES
        )

    def test_all_rdflib_includes_many_vocabs(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        prefixes = {e.prefix for e in wl.entries}
        assert len(prefixes) == 27
        assert "foaf" in prefixes
        assert "skos" in prefixes
        assert "prov" in prefixes
        assert "brick" in prefixes

    def test_prov_term_allowed(self, wl: RestrictedNamespaceWhitelist) -> None:
        result = wl.find_term(URIRef("http://www.w3.org/ns/prov#Entity"))
        assert result.allowed is True
        assert result.term is not None
        assert result.term.prefix == "prov"

    def test_foaf_not_in_defaults(self) -> None:
        default_wl = RestrictedNamespaceWhitelist()
        result = default_wl.find_term(URIRef("http://xmlns.com/foaf/0.1/Person"))
        assert result.allowed is False


# =============================================================================
# Open vocabulary tests
# =============================================================================


class TestRestrictedNamespaceWhitelistOpenVocab:
    """Tests for open (Namespace) vocabulary entries."""

    @pytest.fixture(scope="class")
    def wl(self) -> RestrictedNamespaceWhitelist:
        ex = Namespace("http://example.org/voc#")
        return RestrictedNamespaceWhitelist().plus_entries(("ex", ex))

    def test_open_vocab_term_allowed(self, wl: RestrictedNamespaceWhitelist) -> None:
        result = wl.find_term(URIRef("http://example.org/voc#AnyTerm"))
        assert result.allowed is True
        assert result.term is not None
        assert result.term.vocabulary_type == "open"
        assert result.term.prefix == "ex"
        assert result.term.qname == "ex:AnyTerm"

    def test_open_vocab_arbitrary_term_allowed(
        self, wl: RestrictedNamespaceWhitelist
    ) -> None:
        result = wl.find_term(URIRef("http://example.org/voc#CompletelyInvented"))
        assert result.allowed is True

    def test_closed_vocabs_still_work(self, wl: RestrictedNamespaceWhitelist) -> None:
        result = wl.find_term(RDF.type)
        assert result.allowed is True
        assert result.term is not None
        assert result.term.qname == "rdf:type"


# =============================================================================
# plus_entries tests
# =============================================================================


class TestPlusEntries:
    def test_plus_entries_with_tuples(self) -> None:
        ex = Namespace("http://example.org/voc#")
        wl = RestrictedNamespaceWhitelist().plus_entries(("ex", ex))
        prefixes = {e.prefix for e in wl.entries}
        assert "ex" in prefixes
        assert "rdf" in prefixes

    def test_plus_entries_with_whitelist_entry(self) -> None:
        entry = WhitelistEntry(
            prefix="ex", namespace=Namespace("http://example.org/voc#")
        )
        wl = RestrictedNamespaceWhitelist().plus_entries(entry)
        prefixes = {e.prefix for e in wl.entries}
        assert "ex" in prefixes

    def test_plus_entries_rebuilds_qname_index(self) -> None:
        wl = RestrictedNamespaceWhitelist()
        index_before = wl._qname_index
        wl2 = wl.plus_entries(("ex", Namespace("http://example.org/voc#")))
        assert wl2._qname_index is not index_before

    def test_plus_entries_returns_same_type(self) -> None:
        wl = RestrictedNamespaceWhitelist()
        wl2 = wl.plus_entries(("ex", Namespace("http://example.org/voc#")))
        assert type(wl2) is RestrictedNamespaceWhitelist
