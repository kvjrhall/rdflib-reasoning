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


RDFS_RULES: tuple[Rule, ...] = (
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
            "Domain inference",
            "Propagate rdf:type to the subject of a property using its domain.",
        ),
        body=(
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
            TripleCondition(
                pattern=TriplePattern(subject=_P, predicate=RDFS.domain, object=_C)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C)
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="rdfs", rule_id="rdfs3"),
        description=_rule_description(
            "Range inference",
            "Propagate rdf:type to the object of a property using its range.",
        ),
        body=(
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
            TripleCondition(
                pattern=TriplePattern(subject=_P, predicate=RDFS.range, object=_C)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_Y, predicate=RDF.type, object=_C)
            ),
        ),
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
        silent=True,
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
        id=RuleId(ruleset="rdfs", rule_id="rdfs4b"),
        description=_rule_description(
            "Object resource typing",
            "Infer that the object of every triple is an rdfs:Resource when the "
            "object is an IRI or blank node (well-formed RDF 1.1; literals skipped).",
        ),
        body=(
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
            PredicateCondition(predicate="not_literal", arguments=(_Y,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_Y, predicate=RDF.type, object=RDFS.Resource
                )
            ),
        ),
        silent=True,
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
        silent=True,
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
        silent=True,
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
        silent=True,
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
        silent=True,
    ),
)
