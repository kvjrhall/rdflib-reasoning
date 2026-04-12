import pytest
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS
from rdflib_reasoning.middleware import DatasetMiddleware
from rdflib_reasoning.middleware.dataset_middleware import (
    DatasetMiddlewareConfig,
    WhitelistViolation,
    _format_whitelist_violation_message,
)
from rdflib_reasoning.middleware.namespaces.spec_whitelist import (
    RestrictedNamespaceWhitelist,
)

EX = "urn:test:"


def test_default_graph_starts_empty() -> None:
    middleware = DatasetMiddleware()

    assert middleware.list_triples() == ()


def test_default_graph_triple_crud() -> None:
    middleware = DatasetMiddleware()
    triple = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))

    add_response = middleware.add_triples([triple])

    assert add_response.updated == 1
    assert middleware.list_triples() == (triple,)

    remove_response = middleware.remove_triples([triple])

    assert remove_response.updated == 1
    assert middleware.list_triples() == ()


def test_serialize_default_graph() -> None:
    middleware = DatasetMiddleware()
    triple = (URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("default"))

    middleware.add_triples([triple])

    output = middleware.serialize(format="turtle")

    assert "default" in output


def test_reset_dataset_replaces_existing_dataset() -> None:
    middleware = DatasetMiddleware()
    middleware.add_triples([(URIRef(f"{EX}s"), URIRef(f"{EX}p"), Literal("o"))])

    response = middleware.reset_dataset()

    assert response.updated == 1
    assert middleware.list_triples() == ()


# =============================================================================
# Whitelist enforcement tests
# =============================================================================


EX_NS = Namespace("urn:test:")


class TestWhitelistEnforcement:
    """Tests for namespace whitelist integration in DatasetMiddleware."""

    @pytest.fixture()
    def restricted_middleware(self) -> DatasetMiddleware:
        """Middleware with DEFAULT_ENTRIES + open urn:test: namespace.

        The open namespace allows minted subject IRIs to pass while closed
        vocabulary enforcement still applies to predicates and objects.
        """
        config = DatasetMiddlewareConfig(
            namespace_whitelist=RestrictedNamespaceWhitelist().plus_entries(
                ("ex", EX_NS)
            )
        )
        return DatasetMiddleware(config)

    def test_default_config_allows_everything(self) -> None:
        middleware = DatasetMiddleware()
        triple = (
            URIRef("http://unknown.example/s"),
            URIRef("http://unknown.example/p"),
            Literal("o"),
        )

        response = middleware.add_triples([triple])

        assert response.updated == 1
        assert middleware.list_triples() == (triple,)

    def test_allowed_closed_term_passes(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        triple = (URIRef("urn:test:s"), RDF.type, RDFS.Class)

        response = restricted_middleware.add_triples([triple])

        assert response.updated == 1
        assert restricted_middleware.list_triples() == (triple,)

    def test_rejected_unknown_namespace(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        bad_uri = URIRef("http://totally-unknown.example/foo")
        triple = (bad_uri, RDF.type, RDFS.Class)

        with pytest.raises(WhitelistViolation) as exc_info:
            restricted_middleware.add_triples([triple])

        assert exc_info.value.bad_term == bad_uri
        assert exc_info.value.result.allowed is False
        assert exc_info.value.result.nearest_matches == []

    def test_rejected_near_miss_has_remediation(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        bad_uri = URIRef("http://www.w3.org/2000/01/rdf-schema#Classs")
        triple = (URIRef("urn:test:s"), RDF.type, bad_uri)

        with pytest.raises(WhitelistViolation) as exc_info:
            restricted_middleware.add_triples([triple])

        result = exc_info.value.result
        assert result.allowed is False
        assert len(result.nearest_matches) >= 1
        top_qname = result.nearest_matches[0][0].qname
        assert top_qname == "rdfs:Class"

    def test_triple_not_added_on_violation(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        bad_uri = URIRef("http://totally-unknown.example/foo")
        triple = (bad_uri, RDF.type, RDFS.Class)

        with pytest.raises(WhitelistViolation):
            restricted_middleware.add_triples([triple])

        assert restricted_middleware.list_triples() == ()

    def test_confirmed_terms_are_cached(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        triple = (URIRef("urn:test:s"), RDF.type, RDFS.Class)

        restricted_middleware.add_triples([triple])

        assert RDF.type in restricted_middleware._whitelist_confirmed
        assert RDFS.Class in restricted_middleware._whitelist_confirmed

    def test_open_vocab_prefix_accepted(self) -> None:
        ex = Namespace("http://example.org/voc#")
        config = DatasetMiddlewareConfig(
            namespace_whitelist=RestrictedNamespaceWhitelist().plus_entries(("ex", ex))
        )
        middleware = DatasetMiddleware(config)
        triple = (URIRef("http://example.org/voc#AnyThing"), RDF.type, RDFS.Class)

        response = middleware.add_triples([triple])

        assert response.updated == 1

    def test_literal_objects_are_not_checked(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        """Literals are not URIRefs and should never trigger whitelist checks."""
        triple = (URIRef("urn:test:s"), RDFS.label, Literal("hello"))

        response = restricted_middleware.add_triples([triple])

        assert response.updated == 1

    def test_violation_exception_message_contains_uri(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        bad_uri = URIRef("http://totally-unknown.example/foo")
        triple = (bad_uri, RDF.type, RDFS.Class)

        with pytest.raises(
            WhitelistViolation, match="http://totally-unknown.example/foo"
        ):
            restricted_middleware.add_triples([triple])

    def test_build_system_prompt_includes_enumeration(
        self, restricted_middleware: DatasetMiddleware
    ) -> None:
        prompt = restricted_middleware._build_system_prompt()
        assert "### Allowed Vocabularies" in prompt
        assert "rdf:" in prompt
        assert "rdfs:" in prompt

    def test_build_system_prompt_no_enumeration_when_allow_all(self) -> None:
        middleware = DatasetMiddleware()
        prompt = middleware._build_system_prompt()
        assert "### Allowed Vocabularies" not in prompt


class TestFormatWhitelistViolationMessage:
    def test_includes_markdown_table_with_qname_iri_distance(self) -> None:
        bad = URIRef("http://www.w3.org/2000/01/rdf-schema#type")
        wl = RestrictedNamespaceWhitelist()
        result = wl.find_term(bad)
        msg = _format_whitelist_violation_message(bad, result)
        assert "| Qualified name | IRI | Levenshtein distance |" in msg
        assert "`rdf:type`" in msg
        assert f"`{RDF.type}`" in msg
        assert '"allowed"' not in msg
        assert '"nearest_matches"' not in msg
        assert "vocabulary_type" not in msg
        assert (
            "If none of the suggestions fit your intent, you MUST use a different term"
            in msg
        )

    def test_no_matches_branch(self) -> None:
        bad = URIRef("http://totally-unknown.example/term")
        wl = RestrictedNamespaceWhitelist()
        result = wl.find_term(bad)
        msg = _format_whitelist_violation_message(bad, result)
        assert "No close matches were found" in msg
        assert "| Qualified name | IRI | Levenshtein distance |" not in msg
