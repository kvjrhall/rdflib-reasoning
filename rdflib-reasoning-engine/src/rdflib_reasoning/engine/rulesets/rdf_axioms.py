"""Normative axioms for RDF interpretation (finite vocabulary rows).

RDF 1.1 Semantics §8 RDF Interpretations
https://www.w3.org/TR/rdf11-mt/#rdf-interpretations

Bootstrap rules use ``silent=True`` so axiom triples participate in working memory
and rule chaining without being treated as user-facing materialized conclusions.

**Derivation proofs:** :class:`~rdflib_reasoning.engine.derivation.DerivationProofReconstructor`
drops derivation records with ``silent=True``, so axiom steps do not appear in
proofs rebuilt from derivation logs even when a derivation logger is attached.
Use agent-constructed proofs (e.g. :meth:`~rdflib_reasoning.engine.proof.RuleApplication.from_rule`)
or extend the reconstructor if axiom steps must be visible there.
"""

# TODO: ``rdf:_1``, … container membership property IRIs will be handled by a
# future rule based on URI name matching. Rather than behaving axiomatically,
# it will respond to the presence of the membership property within the graph.
# This will require a builtin for this purpose, which we will defer until we
# want this rule. (Normative RDF/RDFS axiom tables include an infinite ``rdf:_n``
# family; we deliberately omit those triples here.)

from __future__ import annotations

from rdflib.namespace import RDF
from rdflib.term import URIRef

from ..proof import AuthorityReference, RuleDescription, RuleId
from ..rules import Rule, TripleConsequent, TriplePattern

_RDF11_RDF_INTERPRETATIONS = URIRef(
    "https://www.w3.org/TR/rdf11-mt/#rdf-interpretations"
)
_RULESET = "rdf_axioms"


def _axiom_description(*, label: str, description: str) -> RuleDescription:
    return RuleDescription(
        label=label,
        description=description,
        references=[
            AuthorityReference(
                kind="normative_spec",
                uri=_RDF11_RDF_INTERPRETATIONS,
                label="RDF 1.1 Semantics: RDF Interpretations",
            )
        ],
    )


def _rdf_axiom(*, rule_id: str, label: str, description: str, triple: tuple) -> Rule:
    s, p, o = triple
    return Rule(
        id=RuleId(ruleset=_RULESET, rule_id=rule_id),
        description=_axiom_description(label=label, description=description),
        body=(),
        head=(
            TripleConsequent(pattern=TriplePattern(subject=s, predicate=p, object=o)),
        ),
        silent=True,
    )


#: §8 RDF axioms for the fixed RDF vocabulary (excluding the infinite ``rdf:_n``
#: ``rdf:type rdf:Property`` family; see module docstring).
PRODUCTION_RDF_AXIOMS: tuple[Rule, ...] = (
    _rdf_axiom(
        rule_id="rdf-axiom-rdf-type",
        label="rdf:type is an rdf:Property",
        description="RDF axiom: rdf:type rdf:type rdf:Property.",
        triple=(RDF.type, RDF.type, RDF.Property),
    ),
    _rdf_axiom(
        rule_id="rdf-axiom-rdf-subject",
        label="rdf:subject is an rdf:Property",
        description="RDF axiom: rdf:subject rdf:type rdf:Property.",
        triple=(RDF.subject, RDF.type, RDF.Property),
    ),
    _rdf_axiom(
        rule_id="rdf-axiom-rdf-predicate",
        label="rdf:predicate is an rdf:Property",
        description="RDF axiom: rdf:predicate rdf:type rdf:Property.",
        triple=(RDF.predicate, RDF.type, RDF.Property),
    ),
    _rdf_axiom(
        rule_id="rdf-axiom-rdf-object",
        label="rdf:object is an rdf:Property",
        description="RDF axiom: rdf:object rdf:type rdf:Property.",
        triple=(RDF.object, RDF.type, RDF.Property),
    ),
    _rdf_axiom(
        rule_id="rdf-axiom-rdf-first",
        label="rdf:first is an rdf:Property",
        description="RDF axiom: rdf:first rdf:type rdf:Property.",
        triple=(RDF.first, RDF.type, RDF.Property),
    ),
    _rdf_axiom(
        rule_id="rdf-axiom-rdf-rest",
        label="rdf:rest is an rdf:Property",
        description="RDF axiom: rdf:rest rdf:type rdf:Property.",
        triple=(RDF.rest, RDF.type, RDF.Property),
    ),
    _rdf_axiom(
        rule_id="rdf-axiom-rdf-value",
        label="rdf:value is an rdf:Property",
        description="RDF axiom: rdf:value rdf:type rdf:Property.",
        triple=(RDF.value, RDF.type, RDF.Property),
    ),
    _rdf_axiom(
        rule_id="rdf-axiom-rdf-nil",
        label="rdf:nil is an rdf:List",
        description="RDF axiom: rdf:nil rdf:type rdf:List.",
        triple=(RDF.nil, RDF.type, RDF.List),
    ),
)
