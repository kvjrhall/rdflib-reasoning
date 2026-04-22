"""Normative axioms for RDFS interpretation (finite rows of the axiomatic triples table).

RDF 1.1 Semantics §9 RDFS Interpretations
https://www.w3.org/TR/rdf11-mt/#rdfs-interpretations

Composes :data:`PRODUCTION_RDF_AXIOMS` with §9-only axioms (same pattern as
:data:`~rdflib_reasoning.engine.rulesets.rdfs.PRODUCTION_RDFS_RULES` composing
inference rules after this tuple). Container membership ``rdf:_n`` rows from
the normative table are omitted; see the ``# TODO`` in
:mod:`rdflib_reasoning.engine.rulesets.rdf_axioms`.

Production axioms use ``silent=True``; see
:mod:`rdflib_reasoning.engine.rulesets.rdf_axioms` for notes on materialization
and derivation proof reconstruction. Conformant axioms restore the omitted
normative rows and set ``silent=False`` for materialization-oriented tests.
"""

from __future__ import annotations

from rdflib.namespace import RDF, RDFS
from rdflib.term import URIRef

from ..proof import AuthorityReference, RuleDescription, RuleId
from ..rules import Rule, TripleConsequent, TriplePattern
from .rdf_axioms import PRODUCTION_RDF_AXIOMS

_RDF11_RDFS_INTERPRETATIONS = URIRef(
    "https://www.w3.org/TR/rdf11-mt/#rdfs-interpretations"
)
_RULESET = "rdfs_axioms"


def _axiom_description(*, label: str, description: str) -> RuleDescription:
    return RuleDescription(
        label=label,
        description=description,
        references=[
            AuthorityReference(
                kind="normative_spec",
                uri=_RDF11_RDFS_INTERPRETATIONS,
                label="RDF 1.1 Semantics: RDFS Interpretations",
            )
        ],
    )


def _rdfs_axiom(*, rule_id: str, label: str, description: str, triple: tuple) -> Rule:
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


_RDFS_SECTION9_AXIOMS: tuple[Rule, ...] = (
    _rdfs_axiom(
        rule_id="rdfs-axiom-domain-domain-property",
        label="rdfs:domain rdfs:domain rdf:Property",
        description="RDFS axiomatic triple.",
        triple=(RDFS.domain, RDFS.domain, RDF.Property),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-range-domain-property",
        label="rdfs:range rdfs:domain rdf:Property",
        description="RDFS axiomatic triple.",
        triple=(RDFS.range, RDFS.domain, RDF.Property),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-subpropertyof-domain-property",
        label="rdfs:subPropertyOf rdfs:domain rdf:Property",
        description="RDFS axiomatic triple.",
        triple=(RDFS.subPropertyOf, RDFS.domain, RDF.Property),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-subclassof-domain-class",
        label="rdfs:subClassOf rdfs:domain rdfs:Class",
        description="RDFS axiomatic triple.",
        triple=(RDFS.subClassOf, RDFS.domain, RDFS.Class),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-subject-domain-statement",
        label="rdf:subject rdfs:domain rdf:Statement",
        description="RDFS axiomatic triple.",
        triple=(RDF.subject, RDFS.domain, RDF.Statement),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-predicate-domain-statement",
        label="rdf:predicate rdfs:domain rdf:Statement",
        description="RDFS axiomatic triple.",
        triple=(RDF.predicate, RDFS.domain, RDF.Statement),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-object-domain-statement",
        label="rdf:object rdfs:domain rdf:Statement",
        description="RDFS axiomatic triple.",
        triple=(RDF.object, RDFS.domain, RDF.Statement),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-member-domain-resource",
        label="rdfs:member rdfs:domain rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDFS.member, RDFS.domain, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-first-domain-list",
        label="rdf:first rdfs:domain rdf:List",
        description="RDFS axiomatic triple.",
        triple=(RDF.first, RDFS.domain, RDF.List),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-rest-domain-list",
        label="rdf:rest rdfs:domain rdf:List",
        description="RDFS axiomatic triple.",
        triple=(RDF.rest, RDFS.domain, RDF.List),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-seealso-domain-resource",
        label="rdfs:seeAlso rdfs:domain rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDFS.seeAlso, RDFS.domain, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-isdefinedby-domain-resource",
        label="rdfs:isDefinedBy rdfs:domain rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDFS.isDefinedBy, RDFS.domain, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-comment-domain-resource",
        label="rdfs:comment rdfs:domain rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDFS.comment, RDFS.domain, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-label-domain-resource",
        label="rdfs:label rdfs:domain rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDFS.label, RDFS.domain, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-value-domain-resource",
        label="rdf:value rdfs:domain rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDF.value, RDFS.domain, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-type-domain-resource",
        label="rdf:type rdfs:domain rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDF.type, RDFS.domain, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-type-range-class",
        label="rdf:type rdfs:range rdfs:Class",
        description="RDFS axiomatic triple.",
        triple=(RDF.type, RDFS.range, RDFS.Class),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-domain-range-class",
        label="rdfs:domain rdfs:range rdfs:Class",
        description="RDFS axiomatic triple.",
        triple=(RDFS.domain, RDFS.range, RDFS.Class),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-range-range-class",
        label="rdfs:range rdfs:range rdfs:Class",
        description="RDFS axiomatic triple.",
        triple=(RDFS.range, RDFS.range, RDFS.Class),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-subpropertyof-range-property",
        label="rdfs:subPropertyOf rdfs:range rdf:Property",
        description="RDFS axiomatic triple.",
        triple=(RDFS.subPropertyOf, RDFS.range, RDF.Property),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-subclassof-range-class",
        label="rdfs:subClassOf rdfs:range rdfs:Class",
        description="RDFS axiomatic triple.",
        triple=(RDFS.subClassOf, RDFS.range, RDFS.Class),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-subject-range-resource",
        label="rdf:subject rdfs:range rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDF.subject, RDFS.range, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-predicate-range-resource",
        label="rdf:predicate rdfs:range rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDF.predicate, RDFS.range, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-object-range-resource",
        label="rdf:object rdfs:range rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDF.object, RDFS.range, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-member-range-resource",
        label="rdfs:member rdfs:range rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDFS.member, RDFS.range, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-first-range-resource",
        label="rdf:first rdfs:range rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDF.first, RDFS.range, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-rest-range-list",
        label="rdf:rest rdfs:range rdf:List",
        description="RDFS axiomatic triple.",
        triple=(RDF.rest, RDFS.range, RDF.List),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-seealso-range-resource",
        label="rdfs:seeAlso rdfs:range rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDFS.seeAlso, RDFS.range, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-isdefinedby-range-resource",
        label="rdfs:isDefinedBy rdfs:range rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDFS.isDefinedBy, RDFS.range, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-comment-range-literal",
        label="rdfs:comment rdfs:range rdfs:Literal",
        description="RDFS axiomatic triple.",
        triple=(RDFS.comment, RDFS.range, RDFS.Literal),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-label-range-literal",
        label="rdfs:label rdfs:range rdfs:Literal",
        description="RDFS axiomatic triple.",
        triple=(RDFS.label, RDFS.range, RDFS.Literal),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-value-range-resource",
        label="rdf:value rdfs:range rdfs:Resource",
        description="RDFS axiomatic triple.",
        triple=(RDF.value, RDFS.range, RDFS.Resource),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-alt-subclass-container",
        label="rdf:Alt rdfs:subClassOf rdfs:Container",
        description="RDFS axiomatic triple.",
        triple=(RDF.Alt, RDFS.subClassOf, RDFS.Container),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-bag-subclass-container",
        label="rdf:Bag rdfs:subClassOf rdfs:Container",
        description="RDFS axiomatic triple.",
        triple=(RDF.Bag, RDFS.subClassOf, RDFS.Container),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-seq-subclass-container",
        label="rdf:Seq rdfs:subClassOf rdfs:Container",
        description="RDFS axiomatic triple.",
        triple=(RDF.Seq, RDFS.subClassOf, RDFS.Container),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-cmp-subclass-property",
        label="rdfs:ContainerMembershipProperty rdfs:subClassOf rdf:Property",
        description="RDFS axiomatic triple.",
        triple=(RDFS.ContainerMembershipProperty, RDFS.subClassOf, RDF.Property),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-isdefinedby-subproperty-seealso",
        label="rdfs:isDefinedBy rdfs:subPropertyOf rdfs:seeAlso",
        description="RDFS axiomatic triple.",
        triple=(RDFS.isDefinedBy, RDFS.subPropertyOf, RDFS.seeAlso),
    ),
    _rdfs_axiom(
        rule_id="rdfs-axiom-datatype-subclass-class",
        label="rdfs:Datatype rdfs:subClassOf rdfs:Class",
        description="RDFS axiomatic triple.",
        triple=(RDFS.Datatype, RDFS.subClassOf, RDFS.Class),
    ),
)

_PRODUCTION_OMITTED_RDFS_AXIOM_RULE_IDS = frozenset(
    {
        "rdfs-axiom-type-domain-resource",
        "rdfs-axiom-type-range-class",
    }
)


#: RDF §8 axioms plus a production-curated subset of RDFS §9 axiomatic triples
#: (finite rows only; no ``rdf:_n``).
PRODUCTION_RDFS_AXIOMS: tuple[Rule, ...] = (
    *PRODUCTION_RDF_AXIOMS,
    *(
        rule
        for rule in _RDFS_SECTION9_AXIOMS
        if rule.id.rule_id not in _PRODUCTION_OMITTED_RDFS_AXIOM_RULE_IDS
    ),
)


#: Full finite RDF/RDFS axiom inventory with conformant materialization policy.
CONFORMANT_RDFS_AXIOMS: tuple[Rule, ...] = tuple(
    rule.model_copy(update=dict(silent=False))
    for rule in (*PRODUCTION_RDF_AXIOMS, *_RDFS_SECTION9_AXIOMS)
)
