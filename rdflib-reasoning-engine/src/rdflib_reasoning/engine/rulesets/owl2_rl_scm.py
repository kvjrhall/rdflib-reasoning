"""OWL 2 RL schema-vocabulary (``scm-*``) entailment rules.

Implements Table 9 of OWL 2 Profiles Section 4.3: class and property schema
closure, subclass/subproperty transitivity and equivalence bridges, domain and
range propagation, and restriction-schema subclass relationships.

List-dependent rules ``scm-int`` and ``scm-uni`` expand ``LIST[…]`` atoms into
``rdf:first`` / ``rdf:rest`` / ``rdf:nil`` conjunctions for fixed arities 1–3
(covering typical ontology list shapes).
"""

from __future__ import annotations

from rdflib.namespace import OWL, RDF, RDFS
from rdflib.term import Variable

from ..rules import (
    PredicateCondition,
    Rule,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from .owl2_rl_common import (
    C,
    I,
    P,
    X,
    owl2_rl_rule_description,
    owl2_rl_rule_id,
)
from .owl2_rl_lists import owl2_rl_list_conditions

_C1 = Variable("c1")
_C2 = Variable("c2")
_C3 = Variable("c3")
_P1 = Variable("p1")
_P2 = Variable("p2")
_P3 = Variable("p3")
_Y1 = Variable("y1")
_Y2 = Variable("y2")
_Y = Variable("y")

#: Maximum ``LIST`` arity expanded for ``scm-int`` / ``scm-uni``.
_SCM_LIST_MAX_ARITY = 3


def _scm_int_rules() -> tuple[Rule, ...]:
    """Build fixed-arity ``scm-int`` rules for list lengths 1–3."""
    rules: list[Rule] = []
    for n in range(1, _SCM_LIST_MAX_ARITY + 1):
        elements = tuple(Variable(f"c{i}") for i in range(1, n + 1))
        rules.append(
            Rule(
                id=owl2_rl_rule_id("scm-int"),
                description=owl2_rl_rule_description(
                    "Intersection schema projection",
                    "Infer that an owl:intersectionOf class is an "
                    f"rdfs:subClassOf each of its {n} listed operands.",
                ),
                body=(
                    TripleCondition(
                        pattern=TriplePattern(
                            subject=C, predicate=OWL.intersectionOf, object=X
                        )
                    ),
                    *owl2_rl_list_conditions(X, elements),
                ),
                head=tuple(
                    TripleConsequent(
                        pattern=TriplePattern(
                            subject=C, predicate=RDFS.subClassOf, object=element
                        )
                    )
                    for element in elements
                ),
            )
        )
    return tuple(rules)


def _scm_uni_rules() -> tuple[Rule, ...]:
    """Build fixed-arity ``scm-uni`` rules for list lengths 1–3."""
    rules: list[Rule] = []
    for n in range(1, _SCM_LIST_MAX_ARITY + 1):
        elements = tuple(Variable(f"c{i}") for i in range(1, n + 1))
        rules.append(
            Rule(
                id=owl2_rl_rule_id("scm-uni"),
                description=owl2_rl_rule_description(
                    "Union schema injection",
                    "Infer that each of the "
                    f"{n} listed owl:unionOf operands is an rdfs:subClassOf "
                    "the union class.",
                ),
                body=(
                    TripleCondition(
                        pattern=TriplePattern(
                            subject=C, predicate=OWL.unionOf, object=X
                        )
                    ),
                    *owl2_rl_list_conditions(X, elements),
                ),
                head=tuple(
                    TripleConsequent(
                        pattern=TriplePattern(
                            subject=element, predicate=RDFS.subClassOf, object=C
                        )
                    )
                    for element in elements
                ),
            )
        )
    return tuple(rules)


_OWL2_RL_SCM_NON_LIST_RULES: tuple[Rule, ...] = (
    Rule(
        id=owl2_rl_rule_id("scm-cls"),
        description=owl2_rl_rule_description(
            "Class schema closure",
            "Infer subclass reflexivity, equivalent-class reflexivity, "
            "subclassing of owl:Thing, and owl:Nothing as a subclass of every "
            "owl:Class.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=C, predicate=RDF.type, object=OWL.Class)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=C, predicate=RDFS.subClassOf, object=C)
            ),
            TripleConsequent(
                pattern=TriplePattern(
                    subject=C, predicate=OWL.equivalentClass, object=C
                )
            ),
            TripleConsequent(
                pattern=TriplePattern(
                    subject=C, predicate=RDFS.subClassOf, object=OWL.Thing
                )
            ),
            TripleConsequent(
                pattern=TriplePattern(
                    subject=OWL.Nothing, predicate=RDFS.subClassOf, object=C
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-sco"),
        description=owl2_rl_rule_description(
            "Subclass transitivity",
            "Propagate rdfs:subClassOf transitively across asserted class chains "
            "when the chain endpoints differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=RDFS.subClassOf, object=_C2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C2, predicate=RDFS.subClassOf, object=_C3
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C3)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_C1, predicate=RDFS.subClassOf, object=_C3
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-eqc1"),
        description=owl2_rl_rule_description(
            "Equivalent class to subclasses",
            "Expand owl:equivalentClass into mutual rdfs:subClassOf assertions.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=OWL.equivalentClass, object=_C2
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_C1, predicate=RDFS.subClassOf, object=_C2
                )
            ),
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_C2, predicate=RDFS.subClassOf, object=_C1
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-eqc2"),
        description=owl2_rl_rule_description(
            "Mutual subclasses to equivalent class",
            "Collapse mutual rdfs:subClassOf assertions into owl:equivalentClass "
            "when the equated classes differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=RDFS.subClassOf, object=_C2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C2, predicate=RDFS.subClassOf, object=_C1
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_C1, predicate=OWL.equivalentClass, object=_C2
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-op"),
        description=owl2_rl_rule_description(
            "Object property schema closure",
            "Infer subproperty and equivalent-property reflexivity for every "
            "owl:ObjectProperty.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=P, predicate=RDF.type, object=OWL.ObjectProperty
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=P, predicate=RDFS.subPropertyOf, object=P)
            ),
            TripleConsequent(
                pattern=TriplePattern(
                    subject=P, predicate=OWL.equivalentProperty, object=P
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-dp"),
        description=owl2_rl_rule_description(
            "Datatype property schema closure",
            "Infer subproperty and equivalent-property reflexivity for every "
            "owl:DatatypeProperty.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=P, predicate=RDF.type, object=OWL.DatatypeProperty
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=P, predicate=RDFS.subPropertyOf, object=P)
            ),
            TripleConsequent(
                pattern=TriplePattern(
                    subject=P, predicate=OWL.equivalentProperty, object=P
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-spo"),
        description=owl2_rl_rule_description(
            "Subproperty transitivity",
            "Propagate rdfs:subPropertyOf transitively across asserted property "
            "chains when the chain endpoints differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=RDFS.subPropertyOf, object=_P2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P2, predicate=RDFS.subPropertyOf, object=_P3
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_P1, _P3)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_P1, predicate=RDFS.subPropertyOf, object=_P3
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-eqp1"),
        description=owl2_rl_rule_description(
            "Equivalent property to subproperties",
            "Expand owl:equivalentProperty into mutual rdfs:subPropertyOf assertions.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=OWL.equivalentProperty, object=_P2
                )
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_P1, predicate=RDFS.subPropertyOf, object=_P2
                )
            ),
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_P2, predicate=RDFS.subPropertyOf, object=_P1
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-eqp2"),
        description=owl2_rl_rule_description(
            "Mutual subproperties to equivalent property",
            "Collapse mutual rdfs:subPropertyOf assertions into "
            "owl:equivalentProperty when the equated properties differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=RDFS.subPropertyOf, object=_P2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P2, predicate=RDFS.subPropertyOf, object=_P1
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_P1, _P2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_P1, predicate=OWL.equivalentProperty, object=_P2
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-dom1"),
        description=owl2_rl_rule_description(
            "Domain subclass propagation",
            "Propagate rdfs:domain across rdfs:subClassOf of the domain class "
            "when the domain classes differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=P, predicate=RDFS.domain, object=_C1)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=RDFS.subClassOf, object=_C2
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=P, predicate=RDFS.domain, object=_C2)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-dom2"),
        description=owl2_rl_rule_description(
            "Domain subproperty propagation",
            "Propagate rdfs:domain from a super-property to a sub-property when "
            "the properties differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_P2, predicate=RDFS.domain, object=C)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=RDFS.subPropertyOf, object=_P2
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_P1, _P2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_P1, predicate=RDFS.domain, object=C)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-rng1"),
        description=owl2_rl_rule_description(
            "Range subclass propagation",
            "Propagate rdfs:range across rdfs:subClassOf of the range class "
            "when the range classes differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=P, predicate=RDFS.range, object=_C1)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=RDFS.subClassOf, object=_C2
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=P, predicate=RDFS.range, object=_C2)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-rng2"),
        description=owl2_rl_rule_description(
            "Range subproperty propagation",
            "Propagate rdfs:range from a super-property to a sub-property when "
            "the properties differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_P2, predicate=RDFS.range, object=C)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=RDFS.subPropertyOf, object=_P2
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_P1, _P2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_P1, predicate=RDFS.range, object=C)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-hv"),
        description=owl2_rl_rule_description(
            "HasValue schema subclass",
            "Infer rdfs:subClassOf between owl:hasValue restrictions that share "
            "a filler when the on-property of the first is an "
            "rdfs:subPropertyOf the second and the restriction classes differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_C1, predicate=OWL.hasValue, object=I)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_C1, predicate=OWL.onProperty, object=_P1)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_C2, predicate=OWL.hasValue, object=I)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_C2, predicate=OWL.onProperty, object=_P2)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=RDFS.subPropertyOf, object=_P2
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_C1, predicate=RDFS.subClassOf, object=_C2
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-svf1"),
        description=owl2_rl_rule_description(
            "SomeValuesFrom filler subclass",
            "Infer rdfs:subClassOf between owl:someValuesFrom restrictions on "
            "the same property when the first filler is an rdfs:subClassOf the "
            "second and the restriction classes differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=OWL.someValuesFrom, object=_Y1
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_C1, predicate=OWL.onProperty, object=P)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C2, predicate=OWL.someValuesFrom, object=_Y2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_C2, predicate=OWL.onProperty, object=P)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_Y1, predicate=RDFS.subClassOf, object=_Y2
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_C1, predicate=RDFS.subClassOf, object=_C2
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-svf2"),
        description=owl2_rl_rule_description(
            "SomeValuesFrom property subclass",
            "Infer rdfs:subClassOf between owl:someValuesFrom restrictions with "
            "the same filler when the first on-property is an "
            "rdfs:subPropertyOf the second and the restriction classes differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=OWL.someValuesFrom, object=_Y
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_C1, predicate=OWL.onProperty, object=_P1)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C2, predicate=OWL.someValuesFrom, object=_Y
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_C2, predicate=OWL.onProperty, object=_P2)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=RDFS.subPropertyOf, object=_P2
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_C1, predicate=RDFS.subClassOf, object=_C2
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-avf1"),
        description=owl2_rl_rule_description(
            "AllValuesFrom filler subclass",
            "Infer rdfs:subClassOf between owl:allValuesFrom restrictions on "
            "the same property when the first filler is an rdfs:subClassOf the "
            "second and the restriction classes differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=OWL.allValuesFrom, object=_Y1
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_C1, predicate=OWL.onProperty, object=P)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C2, predicate=OWL.allValuesFrom, object=_Y2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_C2, predicate=OWL.onProperty, object=P)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_Y1, predicate=RDFS.subClassOf, object=_Y2
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_C1, predicate=RDFS.subClassOf, object=_C2
                )
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("scm-avf2"),
        description=owl2_rl_rule_description(
            "AllValuesFrom property subclass",
            "Infer the contravariant rdfs:subClassOf between owl:allValuesFrom "
            "restrictions with the same filler when the first on-property is an "
            "rdfs:subPropertyOf the second and the restriction classes differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=OWL.allValuesFrom, object=_Y
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_C1, predicate=OWL.onProperty, object=_P1)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C2, predicate=OWL.allValuesFrom, object=_Y
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_C2, predicate=OWL.onProperty, object=_P2)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=RDFS.subPropertyOf, object=_P2
                )
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=_C2, predicate=RDFS.subClassOf, object=_C1
                )
            ),
        ),
    ),
)


#: OWL 2 RL Table 9 schema-vocabulary entailment rules (``scm-*``).
OWL2_RL_SCM_RULES: tuple[Rule, ...] = (
    *_OWL2_RL_SCM_NON_LIST_RULES,
    *_scm_int_rules(),
    *_scm_uni_rules(),
)
