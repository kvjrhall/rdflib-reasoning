from rdflib.namespace import RDF, RDFS
from rdflib.term import URIRef, Variable

from ..proof import AuthorityReference, RuleDescription, RuleId
from ..rules import (
    PredicateCondition,
    Rule,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from .rdfs_axioms import CONFORMANT_RDFS_AXIOMS, PRODUCTION_RDFS_AXIOMS

_RDF11_SEMANTICS = URIRef("https://www.w3.org/TR/rdf11-mt/#RDFS_Interpretations")

_X = Variable("x")
_Y = Variable("y")
_A = Variable("a")
_B = Variable("b")
_C = Variable("c")
_P = Variable("p")
_Q = Variable("q")


def _rule_description(rule_name: str, description: str) -> RuleDescription:
    return RuleDescription(
        label=rule_name,
        description=description,
        references=[
            AuthorityReference(
                kind="normative_spec",
                uri=_RDF11_SEMANTICS,
                label="RDF 1.1 Semantics: RDFS Interpretations",
            )
        ],
    )


_RDFS2_BODY = (
    TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
    TripleCondition(
        pattern=TriplePattern(subject=_P, predicate=RDFS.domain, object=_C)
    ),
)
_RDFS2_HEAD = (
    TripleConsequent(pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C)),
)

_RDFS3_BODY = (
    TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
    TripleCondition(pattern=TriplePattern(subject=_P, predicate=RDFS.range, object=_C)),
    PredicateCondition(predicate="not_literal", arguments=(_Y,)),
)
_RDFS3_HEAD = (
    TripleConsequent(pattern=TriplePattern(subject=_Y, predicate=RDF.type, object=_C)),
)

_PRODUCTION_RDFS_NON_AXIOM_RULES: tuple[Rule, ...] = (
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs1"),
        description=_rule_description(
            "Property typing",
            "Infer that every predicate used in a triple is an rdf:Property.",
        ),
        body=(
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_P, predicate=RDF.type, object=RDF.Property
                )
            ),
        ),
        silent=True,
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs2"),
        description=_rule_description(
            "Domain inference (visible non-schema terms)",
            "Production profile variant of rdfs2 that materializes domain typing "
            "for non-schema terms while leaving selected RDF/RDFS vocabulary "
            "closure internal to the engine.",
        ),
        body=(
            *_RDFS2_BODY,
            PredicateCondition(
                predicate="different_terms", arguments=(_C, RDFS.Resource)
            ),
        ),
        head=_RDFS2_HEAD,
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs3"),
        description=_rule_description(
            "Range inference (visible non-schema terms)",
            "Production profile variant of rdfs3 that materializes range typing "
            "for non-schema terms while leaving selected RDF/RDFS vocabulary "
            "closure internal to the engine.",
        ),
        body=(
            *_RDFS3_BODY,
            PredicateCondition(
                predicate="term_not_in",
                arguments=(_Y, RDFS.Class, RDFS.Resource),
            ),
        ),
        head=_RDFS3_HEAD,
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs5"),
        description=_rule_description(
            "Subproperty transitivity",
            "Propagate rdfs:subPropertyOf transitively across asserted property chains.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_A, predicate=RDFS.subPropertyOf, object=_B
                )
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_B, predicate=RDFS.subPropertyOf, object=_C
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_A, predicate=RDFS.subPropertyOf, object=_C
                )
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs7"),
        description=_rule_description(
            "Subproperty inheritance",
            "Propagate property assertions across rdfs:subPropertyOf links.",
        ),
        body=(
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P, predicate=RDFS.subPropertyOf, object=_Q
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_P, _Q)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X, predicate=_Q, object=_Y)
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs9"),
        description=_rule_description(
            "Subclass typing propagation",
            "Propagate rdf:type across rdfs:subClassOf.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=RDFS.subClassOf, object=_Y)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_A, predicate=RDF.type, object=_X)
            ),
            PredicateCondition(predicate="different_terms", arguments=(_X, _Y)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_A, predicate=RDF.type, object=_Y)
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs11"),
        description=_rule_description(
            "Subclass transitivity",
            "Propagate rdfs:subClassOf transitively across asserted class chains.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_A, predicate=RDFS.subClassOf, object=_B)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_B, predicate=RDFS.subClassOf, object=_C)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_A, predicate=RDFS.subClassOf, object=_C)
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs12"),
        description=_rule_description(
            "Container membership inheritance",
            "Infer that every rdfs:ContainerMembershipProperty is an rdfs:subPropertyOf rdfs:member.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P,
                    predicate=RDF.type,
                    object=RDFS.ContainerMembershipProperty,
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_P, predicate=RDFS.subPropertyOf, object=RDFS.member
                )
            ),
        ),
    ),
)

PRODUCTION_RDFS_RULES: tuple[Rule, ...] = (
    *PRODUCTION_RDFS_AXIOMS,
    *_PRODUCTION_RDFS_NON_AXIOM_RULES,
)


def _build_conformant_rdfs_rules() -> tuple[Rule, ...]:
    conformant_rules: list[Rule] = list(CONFORMANT_RDFS_AXIOMS)
    for rule in _PRODUCTION_RDFS_NON_AXIOM_RULES:
        match rule.id.rule_id:
            case "rdfs2":
                continue
            case "rdfs3":
                continue
            case "rdfs7":
                continue
            case "rdfs9":
                continue
            case _:
                conformant_rules.append(rule.model_copy(update=dict(silent=False)))
    return tuple(conformant_rules)


#: Conformance-oriented RDFS profile with inference rules materialized.
#:
#: This profile reuses :data:`CONFORMANT_RDFS_AXIOMS`, restores the omitted
#: canonical rules, and forces non-axiom inference rules ``silent=False`` so
#: axiomatic triples and ordinary RDFS entailments are both visible in graph
#: materialization-based conformance tests.
#:
#: The profile is still not generalized-RDF complete because predicate guards
#: such as ``not_literal`` (including on ``rdfs3`` range conclusions) and
#: ``different_terms`` are retained.
CONFORMANT_RDFS_RULES: tuple[Rule, ...] = (
    *_build_conformant_rdfs_rules(),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs2"),
        description=_rule_description(
            "Domain inference",
            "Propagate rdf:type to the subject of a property using its domain.",
        ),
        body=(
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
            TripleCondition(
                pattern=TriplePattern(subject=_P, predicate=RDFS.domain, object=_C)
            ),
        ),
        head=_RDFS2_HEAD,
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs3"),
        description=_rule_description(
            "Range inference",
            "Propagate rdf:type to the object of a property using its range. "
            "Literal objects are skipped so conclusions remain RDF 1.1 concrete "
            "triples (no literal subjects).",
        ),
        body=_RDFS3_BODY,
        head=_RDFS3_HEAD,
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs4a"),
        description=_rule_description(
            "Subject resource typing",
            "Infer that the subject of every triple is an rdfs:Resource.",
        ),
        body=(
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_X, predicate=RDF.type, object=RDFS.Resource
                )
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs4b"),
        description=_rule_description(
            "Object resource typing",
            "Infer that the object of every triple is an rdfs:Resource when the "
            "object is an IRI or blank node (well-formed RDF 1.1; literals skipped).",
        ),
        body=(
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
            # This is NOT strictly conformant if one allows generalized RDF. We do not.
            PredicateCondition(predicate="not_literal", arguments=(_Y,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_Y, predicate=RDF.type, object=RDFS.Resource
                )
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs6"),
        description=_rule_description(
            "Property reflexivity",
            "Infer that every rdf:Property is an rdfs:subPropertyOf itself.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P, predicate=RDF.type, object=RDF.Property
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_P, predicate=RDFS.subPropertyOf, object=_P
                )
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs7"),
        description=_rule_description(
            "Subproperty inheritance",
            "Propagate property assertions across rdfs:subPropertyOf links.",
        ),
        body=(
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P, predicate=RDFS.subPropertyOf, object=_Q
                )
            ),
            # This is what differentiates this rule from production variant
            # PredicateCondition(predicate="different_terms", arguments=(_P, _Q)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X, predicate=_Q, object=_Y)
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs8"),
        description=_rule_description(
            "Class resource inclusion",
            "Infer that every rdfs:Class is an rdfs:subClassOf rdfs:Resource.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_C, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_C, predicate=RDFS.subClassOf, object=RDFS.Resource
                )
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs9"),
        description=_rule_description(
            "Subclass typing propagation",
            "Propagate rdf:type across rdfs:subClassOf.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=RDFS.subClassOf, object=_Y)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_A, predicate=RDF.type, object=_X)
            ),
            # This is what differentiates this rule from production variant
            # PredicateCondition(predicate="different_terms", arguments=(_X, _Y)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_A, predicate=RDF.type, object=_Y)
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs10"),
        description=_rule_description(
            "Class reflexivity",
            "Infer that every rdfs:Class is an rdfs:subClassOf itself.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_C, predicate=RDF.type, object=RDFS.Class)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_C, predicate=RDFS.subClassOf, object=_C)
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs13"),
        description=_rule_description(
            "Datatype literal inclusion",
            "Infer that every rdfs:Datatype is an rdfs:subClassOf rdfs:Literal.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C, predicate=RDF.type, object=RDFS.Datatype
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_C, predicate=RDFS.subClassOf, object=RDFS.Literal
                )
            ),
        ),
    ),
)
