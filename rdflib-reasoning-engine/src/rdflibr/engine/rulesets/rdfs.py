from rdflib.namespace import RDF, RDFS
from rdflib.term import URIRef, Variable

from ..proof import AuthorityReference, RuleDescription, RuleId
from ..rules import Rule, TripleCondition, TripleConsequent, TriplePattern

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
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_A, predicate=RDF.type, object=_Y)
            ),
        ),
    ),
)
