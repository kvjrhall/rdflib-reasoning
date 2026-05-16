"""Schema-facing N3 lexical validators and reusable type aliases for RDF terms.

Validators normalize string inputs to RDFLib ``Node`` values; serializers emit
canonical N3 for JSON Schema and round-trip fields. Description strings cite W3C
specification titles and public URLs only.
"""

from __future__ import annotations

import textwrap
from typing import Annotated, Final, cast

import regex as re
from pydantic import BeforeValidator, Field, PlainSerializer
from rdflib import IdentifiedNode, Node, URIRef
from rdflib.term import BNode
from rdflib.util import from_n3
from rfc3987_syntax import is_valid_syntax_iri  # type: ignore[import-untyped]

# =============================================================================
# Private validation helpers
# =============================================================================

TURTLE_ECMA_BLANK_NODE_PATTERN: Final[str] = (
    r"^_:[a-zA-Z0-9_](?:[a-zA-Z0-9_.]*[a-zA-Z0-9_])?$"
)
_turtle_blank_node_regex: Final[re.Pattern[str]] = re.compile(
    TURTLE_ECMA_BLANK_NODE_PATTERN
)
_PLAINTEXT_LITERAL_HINT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\s|[.!?,;:]|^[A-Za-z][A-Za-z0-9_-]*$"
)


def _parse_node(value: str | Node) -> Node:
    original_value = value
    input_was_text = not isinstance(value, Node)
    try:
        if isinstance(value, Node):
            node = value
        else:
            candidate = value.strip()
            try:
                parsed = from_n3(candidate)
            except Exception:
                # Accept bare RFC 3987 IRIs as an input convenience, but normalize
                # them through N3 parsing so serialization remains canonical.
                if (
                    candidate
                    and not candidate.startswith(("<", "_:", '"', "'", "(", "["))
                    and is_valid_syntax_iri(candidate)
                ):
                    parsed = from_n3(f"<{candidate}>")
                else:
                    raise
            if not isinstance(parsed, Node):
                raise ValueError(
                    f"Unable to parse RDF term from text: {original_value}"
                )
            node = parsed
        if not isinstance(node, Node):
            raise ValueError(f"Unable to parse RDF term from text: {original_value}")
        node_text = _node_to_string(node).removeprefix("<").removesuffix(">")

        if input_was_text and isinstance(original_value, str):
            candidate = original_value.strip()
            if (
                candidate
                and not candidate.startswith(("<", "_:", '"', "'", "(", "["))
                and isinstance(node, URIRef | BNode)
                and ":" not in candidate
                and _PLAINTEXT_LITERAL_HINT_PATTERN.search(candidate) is not None
            ):
                raise ValueError(
                    "Could not parse RDF term from "
                    f"{original_value}. If this is plain text, encode it as an RDF "
                    f'literal like "\\"{candidate}\\"". If this is an IRI, provide '
                    "it either in canonical N3 form like <urn:example:Thing> or "
                    "as a bare RFC 3987 IRI."
                )

        if isinstance(node, URIRef):
            if not is_valid_syntax_iri(node_text):
                raise ValueError("IRI is not a valid RFC 3987 IRI (required for RDF)")
        elif isinstance(node, BNode) and not _turtle_blank_node_regex.match(node_text):
            raise ValueError(f"Invalid blank node: {node_text}")
        return node
    except Exception as e:
        if input_was_text and isinstance(original_value, str):
            candidate = original_value.strip()
            if candidate and not candidate.startswith(("<", "_:", '"', "'", "(", "[")):
                if (
                    not is_valid_syntax_iri(candidate)
                    and _PLAINTEXT_LITERAL_HINT_PATTERN.search(candidate) is not None
                ):
                    raise ValueError(
                        "Could not parse RDF term from "
                        f"{original_value}. If this is plain text, encode it as an RDF "
                        f'literal like "\\"{candidate}\\"". If this is an IRI, provide '
                        "it either in canonical N3 form like <urn:example:Thing> or "
                        "as a bare RFC 3987 IRI."
                    ) from e
                raise ValueError(
                    "Could not parse RDF term from "
                    f"{original_value}. If this is an IRI, provide it either in "
                    f"canonical N3 form like <{candidate}> or as a bare RFC 3987 IRI."
                ) from e
        raise ValueError(f"Could not parse RDF term from {original_value}.") from e


def _parse_identified_node(value: str | Node) -> IdentifiedNode:
    try:
        node = _parse_node(value)
        if not isinstance(node, IdentifiedNode):
            raise TypeError(f"Expected an IRI or blank node, got {type(node).__name__}")
        return node
    except Exception as e:
        raise ValueError(f"Failed to parse identified node from {value}") from e


def _parse_iri(value: str | Node) -> URIRef:
    try:
        node = _parse_node(value)
        if not isinstance(node, URIRef):
            raise TypeError(f"Expected an IRI, got {type(node).__name__}")
        return node
    except Exception as e:
        raise ValueError(f"Failed to parse IRI from {value}") from e


def _node_to_string(node: Node) -> str:
    n3 = cast(str, node.n3())
    return n3


# =============================================================================
# Normative description strings and examples (JSON Schema metadata)
# =============================================================================

RDF_GRAPH_TERM: Final[str] = (
    "Graph Name as defined by RDF 1.1 Concepts and Abstract Syntax § 4. RDF Datasets "
    + "(https://www.w3.org/TR/rdf11-concepts/#section-dataset)"
)

RDF_DATASET: Final[str] = (
    "Dataset as defined by RDF 1.1 Concepts and Abstract Syntax § 4. RDF Datasets "
    + "(https://www.w3.org/TR/rdf11-concepts/#section-dataset) and taking the semantics of "
    + "RDF 1.1: On Semantics of RDF Datasets § 3.4 Each named graph defines its own context "
    + "(https://www.w3.org/TR/rdf11-datasets/#each-named-graph-defines-its-own-context)"
)

RDF_NAMESPACE: Final[str] = (
    "RDF Vocabulary (Namespace) as defined in "
    + "RDF 1.1 Concepts and Abstract Syntax § 3.3 Literals "
    + "(https://www.w3.org/TR/rdf11-concepts/#vocabularies)"
)


TURTLE_BLANK_NODE: Final[str] = (
    "RDF Blank Node as defined in RDF 1.1 Turtle § 2.6 RDF Blank Nodes "
    + "(https://www.w3.org/TR/turtle/#BNodes)"
)
TURTLE_BLANK_NODE_EXAMPLES: Final[list[str]] = [
    "_:b",
    "_:g70",
    "_:personEntity",
]


TURTLE_IRI: Final[str] = (
    "RFC 3987 IRI as used in RDF 1.1 Turtle § 2.4 IRIs "
    + "(https://www.w3.org/TR/turtle/#sec-iri)"
)
TURTLE_IRI_EXAMPLES: Final[list[str]] = [
    "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>",
    "<urn:example:s>",
    "<mailto:user@example.com>",
]


TURTLE_LITERAL: Final[str] = (
    "RDF Literal as defined in RDF 1.1 Turtle § 2.5 RDF Literals "
    + "(https://www.w3.org/TR/turtle/#literals)"
)
TURTLE_LITERAL_EXAMPLES: Final[list[str]] = [
    '"Project report"',
    '"A short human-readable description."',
    '"Hello, World!"@en',
    '"Hello, World!"^^<http://www.w3.org/2001/XMLSchema#string>',
    '"123"^^<http://www.w3.org/2001/XMLSchema#integer>',
    '"2026-03-15"^^<http://www.w3.org/2001/XMLSchema#date>',
    '"2026-03-15T12:00:00Z"^^<http://www.w3.org/2001/XMLSchema#dateTime>',
]


type N3Resource = Annotated[
    IdentifiedNode,
    BeforeValidator(_parse_identified_node, json_schema_input_type=str),
    PlainSerializer(_node_to_string, return_type=str),
    Field(
        description=textwrap.dedent(f"""
        RDF resource accepted in canonical N3 lexical form and serialized in N3.
        It MUST resolve to a {TURTLE_IRI} or a {TURTLE_BLANK_NODE}.
        Full IRIs MAY be provided either as canonical N3 like <urn:example:s> or
        as a bare RFC 3987 IRI like urn:example:s.
        It SHOULD be an IRI when a globally stable identifier is available.
        """).strip(),
        examples=TURTLE_IRI_EXAMPLES + ["urn:example:s"] + TURTLE_BLANK_NODE_EXAMPLES,
    ),
]

type N3IRIRef = Annotated[
    URIRef,
    BeforeValidator(_parse_iri, json_schema_input_type=str),
    PlainSerializer(_node_to_string, return_type=str),
    Field(
        description=textwrap.dedent(f"""
        RDF IRI reference accepted in canonical N3 lexical form and serialized in N3.
        It MUST resolve to a {TURTLE_IRI}.
        Full IRIs MAY be provided either as canonical N3 like <urn:example:p> or
        as a bare RFC 3987 IRI like urn:example:p.
        Use this for predicates and for resources that cannot be blank nodes.
        """).strip(),
        examples=TURTLE_IRI_EXAMPLES + ["urn:example:p"],
    ),
]

type N3Node = Annotated[
    Node,
    BeforeValidator(_parse_node, json_schema_input_type=str),
    PlainSerializer(_node_to_string, return_type=str),
    Field(
        description=textwrap.dedent(f"""
        RDF node accepted in canonical N3 lexical form and serialized in N3.
        It MUST resolve to one of the following:
        - {TURTLE_IRI}
        - {TURTLE_BLANK_NODE}
        - {TURTLE_LITERAL}
        Full IRIs MAY be provided either as canonical N3 like <urn:example:o> or
        as a bare RFC 3987 IRI like urn:example:o.
        """).strip(),
        examples=TURTLE_IRI_EXAMPLES
        + ["urn:example:o"]
        + TURTLE_BLANK_NODE_EXAMPLES
        + TURTLE_LITERAL_EXAMPLES,
    ),
]

type N3ContextIdentifier = Annotated[
    IdentifiedNode,
    BeforeValidator(_parse_identified_node, json_schema_input_type=str),
    PlainSerializer(_node_to_string, return_type=str),
    Field(
        description=textwrap.dedent(f"""
        RDF graph name accepted in canonical N3 lexical form and serialized in N3.
        It corresponds to a {RDF_GRAPH_TERM}.
        It MUST resolve to a {TURTLE_IRI} or a {TURTLE_BLANK_NODE}.
        Full IRIs MAY be provided either as canonical N3 like <urn:example:g> or
        as a bare RFC 3987 IRI like urn:example:g.
        It SHOULD be an IRI when a globally stable graph identifier is available.
        """).strip(),
        examples=TURTLE_IRI_EXAMPLES + ["urn:example:g"] + TURTLE_BLANK_NODE_EXAMPLES,
    ),
]
