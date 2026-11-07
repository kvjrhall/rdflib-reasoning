"""OWL 2 RL class-expression entailment rules (Table 6).

Canonical rule identifiers use ``RuleId(ruleset="owl2-rl", rule_id="cls-...")``.
Contradiction-producing class rules such as ``cls-nothing2`` and ``cls-com``
remain in the dedicated contradiction ruleset.

LIST-dependent rules expand ``LIST[…]`` via
:func:`~rdflib_reasoning.engine.rulesets.owl2_rl_lists.owl2_rl_list_conditions`
for a fixed length of two (Table 3). ``cls-uni`` is instantiated once per list
position (``1 ≤ i ≤ 2``) as required by the "for each" column.
"""

from __future__ import annotations

from rdflib.namespace import OWL, RDF, XSD
from rdflib.term import Literal, Variable

from ..rules import (
    PatternTerm,
    PredicateCondition,
    Rule,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from .owl2_rl_common import (
    C,
    P,
    U,
    X,
    Y,
    owl2_rl_rule_description,
    owl2_rl_rule_id,
)
from .owl2_rl_lists import owl2_rl_list_conditions

_V = Variable("v")
_Y1 = Variable("y1")
_Y2 = Variable("y2")
_C1 = Variable("c1")
_C2 = Variable("c2")

_MAX_CARD_ONE = Literal("1", datatype=XSD.nonNegativeInteger)

_LIST_LEN = 2


def _tc(
    subject: PatternTerm, predicate: PatternTerm, obj: PatternTerm
) -> TripleCondition:
    return TripleCondition(
        pattern=TriplePattern(subject=subject, predicate=predicate, object=obj)
    )


def _th(
    subject: PatternTerm, predicate: PatternTerm, obj: PatternTerm
) -> TripleConsequent:
    return TripleConsequent(
        pattern=TriplePattern(subject=subject, predicate=predicate, object=obj)
    )


#: OWL 2 RL Table 6 class-expression entailment rules implemented here.
OWL2_RL_CLS_RULES: tuple[Rule, ...] = (
    Rule(
        id=owl2_rl_rule_id("cls-thing"),
        description=owl2_rl_rule_description(
            "cls-thing",
            "Bootstrap axiom: owl:Thing is an owl:Class.",
        ),
        body=(),
        head=(_th(OWL.Thing, RDF.type, OWL.Class),),
        silent=True,
    ),
    Rule(
        id=owl2_rl_rule_id("cls-nothing1"),
        description=owl2_rl_rule_description(
            "cls-nothing1",
            "Bootstrap axiom: owl:Nothing is an owl:Class.",
        ),
        body=(),
        head=(_th(OWL.Nothing, RDF.type, OWL.Class),),
        silent=True,
    ),
    Rule(
        id=owl2_rl_rule_id("cls-int1"),
        description=owl2_rl_rule_description(
            "cls-int1",
            "An individual typed as every member of an owl:intersectionOf list "
            f"(length {_LIST_LEN}) is typed as the intersection class.",
        ),
        body=(
            _tc(C, OWL.intersectionOf, X),
            *owl2_rl_list_conditions(X, (_C1, _C2)),
            _tc(Y, RDF.type, _C1),
            _tc(Y, RDF.type, _C2),
        ),
        head=(_th(Y, RDF.type, C),),
    ),
    Rule(
        id=owl2_rl_rule_id("cls-int2"),
        description=owl2_rl_rule_description(
            "cls-int2",
            "An individual typed as an owl:intersectionOf class is typed as "
            f"every member of that list (length {_LIST_LEN}).",
        ),
        body=(
            _tc(C, OWL.intersectionOf, X),
            *owl2_rl_list_conditions(X, (_C1, _C2)),
            _tc(Y, RDF.type, C),
        ),
        head=(
            _th(Y, RDF.type, _C1),
            _th(Y, RDF.type, _C2),
        ),
    ),
    # cls-uni: "for each 1 ≤ i ≤ n" — one rule per list position for n=2.
    Rule(
        id=owl2_rl_rule_id("cls-uni"),
        description=owl2_rl_rule_description(
            "cls-uni",
            "An individual typed as a member of an owl:unionOf list "
            f"(length {_LIST_LEN}, position 1) is typed as the union class.",
        ),
        body=(
            _tc(C, OWL.unionOf, X),
            *owl2_rl_list_conditions(X, (_C1, _C2)),
            _tc(Y, RDF.type, _C1),
        ),
        head=(_th(Y, RDF.type, C),),
    ),
    Rule(
        id=owl2_rl_rule_id("cls-uni"),
        description=owl2_rl_rule_description(
            "cls-uni",
            "An individual typed as a member of an owl:unionOf list "
            f"(length {_LIST_LEN}, position 2) is typed as the union class.",
        ),
        body=(
            _tc(C, OWL.unionOf, X),
            *owl2_rl_list_conditions(X, (_C1, _C2), cell_prefix="zu"),
            _tc(Y, RDF.type, _C2),
        ),
        head=(_th(Y, RDF.type, C),),
    ),
    Rule(
        id=owl2_rl_rule_id("cls-svf1"),
        description=owl2_rl_rule_description(
            "cls-svf1",
            "An individual with a property filler typed as the "
            "owl:someValuesFrom class is a member of the restriction.",
        ),
        body=(
            _tc(X, OWL.someValuesFrom, Y),
            _tc(X, OWL.onProperty, P),
            _tc(U, P, _V),
            _tc(_V, RDF.type, Y),
        ),
        head=(_th(U, RDF.type, X),),
    ),
    Rule(
        id=owl2_rl_rule_id("cls-svf2"),
        description=owl2_rl_rule_description(
            "cls-svf2",
            "An individual with any filler of an owl:someValuesFrom owl:Thing "
            "restriction is a member of the restriction.",
        ),
        body=(
            _tc(X, OWL.someValuesFrom, OWL.Thing),
            _tc(X, OWL.onProperty, P),
            _tc(U, P, _V),
        ),
        head=(_th(U, RDF.type, X),),
    ),
    Rule(
        id=owl2_rl_rule_id("cls-avf"),
        description=owl2_rl_rule_description(
            "cls-avf",
            "Fillers of an owl:allValuesFrom restriction on a typed individual "
            "are typed as the filler class.",
        ),
        body=(
            _tc(X, OWL.allValuesFrom, Y),
            _tc(X, OWL.onProperty, P),
            _tc(U, RDF.type, X),
            _tc(U, P, _V),
        ),
        head=(_th(_V, RDF.type, Y),),
    ),
    Rule(
        id=owl2_rl_rule_id("cls-hv1"),
        description=owl2_rl_rule_description(
            "cls-hv1",
            "A member of an owl:hasValue restriction has the stated property value.",
        ),
        body=(
            _tc(X, OWL.hasValue, Y),
            _tc(X, OWL.onProperty, P),
            _tc(U, RDF.type, X),
        ),
        head=(_th(U, P, Y),),
    ),
    Rule(
        id=owl2_rl_rule_id("cls-hv2"),
        description=owl2_rl_rule_description(
            "cls-hv2",
            "An individual with the stated owl:hasValue property value is a "
            "member of the restriction.",
        ),
        body=(
            _tc(X, OWL.hasValue, Y),
            _tc(X, OWL.onProperty, P),
            _tc(U, P, Y),
        ),
        head=(_th(U, RDF.type, X),),
    ),
    Rule(
        id=owl2_rl_rule_id("cls-maxc2"),
        description=owl2_rl_rule_description(
            "cls-maxc2",
            "Distinct fillers of an owl:maxCardinality 1 restriction on a typed "
            "individual are owl:sameAs.",
        ),
        body=(
            _tc(X, OWL.maxCardinality, _MAX_CARD_ONE),
            _tc(X, OWL.onProperty, P),
            _tc(U, RDF.type, X),
            _tc(U, P, _Y1),
            _tc(U, P, _Y2),
            PredicateCondition(predicate="different_terms", arguments=(_Y1, _Y2)),
        ),
        head=(_th(_Y1, OWL.sameAs, _Y2),),
    ),
    Rule(
        id=owl2_rl_rule_id("cls-maxqc3"),
        description=owl2_rl_rule_description(
            "cls-maxqc3",
            "Distinct fillers typed as the owl:onClass of an "
            "owl:maxQualifiedCardinality 1 restriction are owl:sameAs.",
        ),
        body=(
            _tc(X, OWL.maxQualifiedCardinality, _MAX_CARD_ONE),
            _tc(X, OWL.onProperty, P),
            _tc(X, OWL.onClass, C),
            _tc(U, RDF.type, X),
            _tc(U, P, _Y1),
            _tc(_Y1, RDF.type, C),
            _tc(U, P, _Y2),
            _tc(_Y2, RDF.type, C),
            PredicateCondition(predicate="different_terms", arguments=(_Y1, _Y2)),
        ),
        head=(_th(_Y1, OWL.sameAs, _Y2),),
    ),
    Rule(
        id=owl2_rl_rule_id("cls-maxqc4"),
        description=owl2_rl_rule_description(
            "cls-maxqc4",
            "Distinct fillers of an owl:maxQualifiedCardinality 1 restriction "
            "on owl:Thing are owl:sameAs.",
        ),
        body=(
            _tc(X, OWL.maxQualifiedCardinality, _MAX_CARD_ONE),
            _tc(X, OWL.onProperty, P),
            _tc(X, OWL.onClass, OWL.Thing),
            _tc(U, RDF.type, X),
            _tc(U, P, _Y1),
            _tc(U, P, _Y2),
            PredicateCondition(predicate="different_terms", arguments=(_Y1, _Y2)),
        ),
        head=(_th(_Y1, OWL.sameAs, _Y2),),
    ),
    Rule(
        id=owl2_rl_rule_id("cls-oo"),
        description=owl2_rl_rule_description(
            "cls-oo",
            f"Every member of an owl:oneOf list (length {_LIST_LEN}) is typed "
            "as the enumeration class.",
        ),
        body=(
            _tc(C, OWL.oneOf, X),
            *owl2_rl_list_conditions(X, (_Y1, _Y2)),
        ),
        head=(
            _th(_Y1, RDF.type, C),
            _th(_Y2, RDF.type, C),
        ),
    ),
)
