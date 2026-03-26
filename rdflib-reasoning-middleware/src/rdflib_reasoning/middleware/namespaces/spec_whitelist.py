from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from inspect import get_annotations
from typing import Annotated, ClassVar, Literal, Self, overload, override

from pydantic import BaseModel, ConfigDict, Field
from rdflib import Namespace, URIRef
from rdflib.namespace import (
    BRICK,
    CSVW,
    DC,
    DCAM,
    DCAT,
    DCMITYPE,
    DCTERMS,
    DOAP,
    FOAF,
    ODRL2,
    ORG,
    OWL,
    PROF,
    PROV,
    QB,
    RDF,
    RDFS,
    SDO,
    SH,
    SKOS,
    SOSA,
    SSN,
    TIME,
    VANN,
    VOID,
    WGS,
    XSD,
    DefinedNamespace,
)
from rdflib_reasoning.middleware.dataset_model import N3IRIRef

# SCHEMA FACING RESULT TYPES
# -----------------------------------------------------------------------------


type MatchDistance = Annotated[
    int,
    Field(
        ge=0,
        description=(
            "Levenshtein distance between the rejected qualified name and the "
            "suggested qualified name, used for ranking (lower is better). "
            "For example, the distance between rdfs:type and rdf:type is 1; "
            "between rdfs:Classs and owl:Class is 5."
        ),
        examples=[0, 1, 3],
    ),
]


class WhitelistedTerm(BaseModel):
    """A whitelisted term from a namespace.

    Appears in tool error responses when a term is rejected by the namespace
    whitelist, identifying valid alternatives the agent may use instead.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    namespace: str = Field(
        ...,
        description="The namespace that defines the term.",
        examples=[
            "http://www.w3.org/2000/01/rdf-schema#",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "http://www.w3.org/2001/XMLSchema#",
        ],
    )
    vocabulary_type: Literal["closed", "open"] = Field(
        ...,
        description="The terms of a closed vocabulary are fully enumerated, while the terms of an open vocabulary are unrestricted",
    )
    prefix: str = Field(
        ...,
        description="The prefix typically used to abbreviate the namespace.",
        examples=[
            "rdfs",
            "rdf",
            "xsd",
        ],
    )
    term: N3IRIRef = Field(..., description="The IRI of the term.")
    qname: str = Field(
        ...,
        description="The qualified name of the term.",
        examples=[
            "rdfs:Class",
            "rdf:type",
            "xsd:string",
        ],
    )

    @classmethod
    def _from_trusted(
        cls,
        *,
        namespace: str,
        vocabulary_type: Literal["closed", "open"],
        prefix: str,
        term: URIRef,
        qname: str,
    ) -> "WhitelistedTerm":
        """Construct without Pydantic validation for known-good vocabulary data.

        N3IRIRef validation runs RFC 3987 syntax checking at ~8 ms per term.
        For internally-constructed terms sourced from rdflib DefinedNamespace
        or Namespace objects the IRIs are already well-formed, so we bypass
        validation via model_construct for a ~100x speedup during index
        construction (~0.01 ms vs ~8 ms per term).
        """
        return cls.model_construct(
            namespace=namespace,
            vocabulary_type=vocabulary_type,
            prefix=prefix,
            term=term,
            qname=qname,
        )


class WhitelistResult(BaseModel):
    """Result of checking a term against the namespace whitelist.

    Returned as structured JSON in tool error responses so the agent can
    inspect whether the term was allowed, retrieve metadata about the
    matched vocabulary entry, and review nearest-match suggestions.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    allowed: bool = Field(
        ..., description="Whether the term is allowed to be used in the knowledge base."
    )
    term: WhitelistedTerm | None = Field(
        ...,
        description="The whitelisted term's metadata if it was found as part of matching.",
    )
    nearest_matches: Sequence[tuple[WhitelistedTerm, MatchDistance]] = Field(
        ...,
        description="The nearest matches to the rejected term, if any.",
    )


# Internal Types (MUST NOT BE EXPOSED TO SCHEMA)
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WhitelistEntry:
    """Internal vocabulary entry pairing a prefix with an rdflib namespace.

    Closed vocabularies (``DefinedNamespace`` subclasses) support term-level
    membership testing; open vocabularies (``Namespace``) support prefix-only
    matching.  This dataclass is developer-facing and is never serialized to
    the agent boundary.
    """

    prefix: str
    namespace: Namespace | type[DefinedNamespace]

    @property
    def is_closed(self) -> bool:
        return not isinstance(self.namespace, Namespace)

    def __lt__(self, other: Self) -> bool:
        this = (self.prefix, self._ns_key(self.namespace))
        that = (other.prefix, other._ns_key(other.namespace))
        return this < that

    @staticmethod
    def _ns_key(ns: Namespace | type[DefinedNamespace]) -> str:
        return str(ns if isinstance(ns, Namespace) else ns._NS)


# Private Helpers (NOT EXPOSED TO SCHEMA)
# -----------------------------------------------------------------------------


def _levenshtein(a: str, b: str) -> int:
    """Minimum edit distance between two strings (insert, delete, substitute)."""
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1] + [0] * len(b)
        for j, cb in enumerate(b):
            curr[j + 1] = min(
                prev[j + 1] + 1,
                curr[j] + 1,
                prev[j] + (0 if ca == cb else 1),
            )
        prev = curr
    return prev[-1]


def _closed_vocab_local_names(ns: type[DefinedNamespace]) -> frozenset[str]:
    """Enumerate the declared local names of a closed vocabulary."""
    names: set[str] = set()
    for c in ns.mro():
        if issubclass(c, DefinedNamespace):
            names.update(k for k in get_annotations(c) if not k.startswith("_"))
            names.update(getattr(c, "_extras", []))
    return frozenset(names)


# Whitelists (NOT EXPOSED TO SCHEMA)
# -----------------------------------------------------------------------------


class NamespaceWhitelist(ABC):
    """Abstract contract for namespace whitelisting strategies.

    Two implementations are provided:

    - ``AllowAllNamespaceWhitelist`` -- no-op pass-through (default).
    - ``RestrictedNamespaceWhitelist`` -- enforces a fixed set of allowed
      vocabularies with optional Levenshtein-based remediation for closed
      namespaces.
    """

    @abstractmethod
    def find_term(self, uri: URIRef) -> WhitelistResult:
        pass

    @abstractmethod
    def enumerate_prompt(self) -> str | None:
        """Return a prompt section enumerating allowed vocabularies, or None."""
        pass


class AllowAllNamespaceWhitelist(NamespaceWhitelist):
    """A whitelist that allows all namespaces."""

    @override
    def find_term(self, uri: URIRef) -> WhitelistResult:
        return WhitelistResult(allowed=True, term=None, nearest_matches=[])

    @override
    def enumerate_prompt(self) -> str | None:
        return None


class RestrictedNamespaceWhitelist(NamespaceWhitelist):
    """A fixed whitelist of namespaces that are allowed to be used in the knowledge base.

    Typical Usage:
    ```python
    from rdflib import Namespace

    EX = Namespace("http://example.org/voc#")

    whitelist = RestrictedNamespaceWhitelist().plus_entries(
        ("ex", EX),
    )

    result0 = whitelist.find_term(EX.foo)
    result1 = whitelist.find_term(RDF.type)
    ```
    """

    ALL_RDFLIB_ENTRIES: ClassVar[Sequence[WhitelistEntry]] = [
        WhitelistEntry(prefix="brick", namespace=BRICK),
        WhitelistEntry(prefix="csvw", namespace=CSVW),
        WhitelistEntry(prefix="dc", namespace=DC),
        WhitelistEntry(prefix="dcat", namespace=DCAT),
        WhitelistEntry(prefix="dctype", namespace=DCMITYPE),
        WhitelistEntry(prefix="dcterms", namespace=DCTERMS),
        WhitelistEntry(prefix="dcam", namespace=DCAM),
        WhitelistEntry(prefix="doap", namespace=DOAP),
        WhitelistEntry(prefix="foaf", namespace=FOAF),
        WhitelistEntry(prefix="odrl2", namespace=ODRL2),
        WhitelistEntry(prefix="org", namespace=ORG),
        WhitelistEntry(prefix="owl", namespace=OWL),
        WhitelistEntry(prefix="prof", namespace=PROF),
        WhitelistEntry(prefix="prov", namespace=PROV),
        WhitelistEntry(prefix="qb", namespace=QB),
        WhitelistEntry(prefix="rdf", namespace=RDF),
        WhitelistEntry(prefix="rdfs", namespace=RDFS),
        WhitelistEntry(prefix="sdo", namespace=SDO),
        WhitelistEntry(prefix="sh", namespace=SH),
        WhitelistEntry(prefix="skos", namespace=SKOS),
        WhitelistEntry(prefix="sosa", namespace=SOSA),
        WhitelistEntry(prefix="ssn", namespace=SSN),
        WhitelistEntry(prefix="time", namespace=TIME),
        WhitelistEntry(prefix="vann", namespace=VANN),
        WhitelistEntry(prefix="void", namespace=VOID),
        WhitelistEntry(prefix="wgs", namespace=WGS),
        WhitelistEntry(prefix="xsd", namespace=XSD),
    ]

    DEFAULT_ENTRIES: ClassVar[Sequence[WhitelistEntry]] = [
        WhitelistEntry(prefix="owl", namespace=OWL),
        WhitelistEntry(prefix="rdf", namespace=RDF),
        WhitelistEntry(prefix="rdfs", namespace=RDFS),
        WhitelistEntry(prefix="xsd", namespace=XSD),
    ]

    entries: tuple[WhitelistEntry, ...]
    _qname_index: Mapping[str, tuple[WhitelistedTerm, ...]]

    def __init__(self, whitelist: Iterable[WhitelistEntry] = DEFAULT_ENTRIES) -> None:
        self.entries = tuple(sorted(whitelist))
        self._qname_index = self._build_qname_index()

    def _build_qname_index(self) -> Mapping[str, tuple[WhitelistedTerm, ...]]:
        index: dict[str, list[WhitelistedTerm]] = defaultdict(list)
        for entry in self.entries:
            if not entry.is_closed:
                continue
            ns = entry.namespace._NS  # type: ignore[union-attr]
            for local_name in _closed_vocab_local_names(entry.namespace):  # type: ignore[arg-type]
                index[local_name].append(
                    WhitelistedTerm._from_trusted(
                        namespace=str(ns),
                        vocabulary_type="closed",
                        prefix=entry.prefix,
                        term=URIRef(f"{ns}{local_name}"),
                        qname=f"{entry.prefix}:{local_name}",
                    )
                )
        return {k: tuple(sorted(v, key=lambda t: t.qname)) for k, v in index.items()}

    @override
    def find_term(self, uri: URIRef) -> WhitelistResult:
        for entry in self.entries:
            ns: Namespace = (
                entry.namespace._NS if entry.is_closed else entry.namespace  # type: ignore[assignment]
            )
            if uri in entry.namespace:
                return WhitelistResult(
                    allowed=True,
                    term=WhitelistedTerm._from_trusted(
                        namespace=str(ns),
                        vocabulary_type="closed" if entry.is_closed else "open",
                        prefix=entry.prefix,
                        term=uri,
                        qname=entry.prefix + ":" + uri.removeprefix(ns),
                    ),
                    nearest_matches=[],
                )
            elif entry.is_closed and uri.startswith(ns):
                local_name = uri.removeprefix(ns)
                rejected_qname = f"{entry.prefix}:{local_name}"
                # Stage 1: local-name filter -- select plausible term names
                filtered: list[WhitelistedTerm] = []
                for indexed_name, terms in self._qname_index.items():
                    if _levenshtein(local_name, indexed_name) <= 3:
                        filtered.extend(terms)
                # Stage 2: qname rank -- score by namespace-aware distance
                ranked = sorted(
                    ((t, _levenshtein(rejected_qname, t.qname)) for t in filtered),
                    key=lambda pair: (pair[1], pair[0].qname),
                )
                return WhitelistResult(
                    allowed=False,
                    term=None,
                    nearest_matches=ranked[:3],
                )
        return WhitelistResult(allowed=False, term=None, nearest_matches=[])

    @override
    def enumerate_prompt(self) -> str | None:
        lines = [
            "### Allowed Vocabularies",
            "",
            "You MUST only use terms from the following vocabularies in the knowledge base.",
            "Terms from other namespaces will be rejected.",
            "",
        ]
        for entry in self.entries:
            kind = "closed" if entry.is_closed else "open"
            ns_uri = WhitelistEntry._ns_key(entry.namespace)
            lines.append(f"- `{entry.prefix}:` ({kind}) {ns_uri}")
        lines.append("")
        lines.append(
            "Closed vocabularies only allow declared terms. "
            "Open vocabularies allow any term under the namespace prefix."
        )
        lines.append("")
        lines.append(
            "If an `add_triples` tool call is rejected due to a namespace whitelist "
            "violation, you MUST NOT use that rejected IRI again in subsequent "
            "`add_triples` calls. You SHOULD treat the rejected IRI as disallowed until "
            "you substitute a whitelisted term."
        )
        return "\n".join(lines)

    @overload
    def plus_entries(self, *entries: WhitelistEntry) -> Self:
        pass

    @overload
    def plus_entries(
        self, *entries: tuple[str, Namespace | type[DefinedNamespace]]
    ) -> Self:
        pass

    def plus_entries(
        self,
        *entries: WhitelistEntry | tuple[str, Namespace | type[DefinedNamespace]],
    ) -> Self:
        def new_entry(
            entry: WhitelistEntry | tuple[str, Namespace | type[DefinedNamespace]],
        ) -> WhitelistEntry:
            if isinstance(entry, WhitelistEntry):
                return entry
            else:
                prefix, namespace = entry
                return WhitelistEntry(prefix=prefix, namespace=namespace)

        return type(self)({new_entry(entry) for entry in entries}.union(self.entries))
