"""OWL 2 RL contradiction-signaling rules (non-mutating diagnostics channel).

These rules model contradiction-producing RL rule families that are representable
with the currently available rule IR and predicate builtins. Rule heads emit
``ContradictionConsequent`` actions rather than mutating logical closure.

LIST-backed rules expand Table 3 ``LIST[…]`` atoms for pairwise length-2 member
lists via :func:`~rdflib_reasoning.engine.rulesets.owl2_rl_lists.owl2_rl_list_conditions`.

``dt-not-type`` keeps the OWL 2 RL antecedent ``T(lt, rdf:type, dt)``. Under the
engine's default RDF 1.1 ``literal_subject_policy``, that premise cannot enter
working memory, so the rule is encoded but does not fire unless callers admit
generalized-RDF facts.
"""

from rdflib.namespace import OWL, RDF, XSD
from rdflib.term import Literal, Variable

from ..proof import RuleId
from ..rules import (
    ContradictionConsequent,
    PredicateCondition,
    Rule,
    TripleCondition,
    TriplePattern,
)
from .owl2_rl_lists import owl2_rl_list_conditions

_X = Variable("x")
_Y = Variable("y")
_P = Variable("p")
_P1 = Variable("p1")
_P2 = Variable("p2")
_A = Variable("a")
_C = Variable("c")
_C1 = Variable("c1")
_C2 = Variable("c2")
_I = Variable("i")
_I1 = Variable("i1")
_I2 = Variable("i2")
_LT = Variable("lt")
_DT = Variable("dt")
_NPA = Variable("npa")
_U = Variable("u")
_V = Variable("v")
_Z1 = Variable("z1")
_Z2 = Variable("z2")

_ZERO = Literal("0", datatype=XSD.nonNegativeInteger)


# Rules that emit ``ContradictionConsequent`` diagnostics rather than triples.
OWL2_RL_CONTRADICTION_RULES: tuple[Rule, ...] = (
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="eq-diff1"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=OWL.sameAs, object=_Y)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=OWL.differentFrom, object=_Y
                )
            ),
        ),
        head=(
            ContradictionConsequent(
                category="eq-diff1",
                detail="owl:sameAs and owl:differentFrom hold for the same pair.",
                arguments=(_X, OWL.sameAs, _Y),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="eq-diff2"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=RDF.type, object=OWL.AllDifferent
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=OWL.members, object=_Y)
            ),
            *owl2_rl_list_conditions(_Y, (_Z1, _Z2), cell_prefix="eqdiff2"),
            TripleCondition(
                pattern=TriplePattern(subject=_Z1, predicate=OWL.sameAs, object=_Z2)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="eq-diff2",
                detail="owl:AllDifferent members list contains owl:sameAs individuals.",
                arguments=(_Z1, OWL.sameAs, _Z2),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="eq-diff3"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=RDF.type, object=OWL.AllDifferent
                )
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=OWL.distinctMembers, object=_Y
                )
            ),
            *owl2_rl_list_conditions(_Y, (_Z1, _Z2), cell_prefix="eqdiff3"),
            TripleCondition(
                pattern=TriplePattern(subject=_Z1, predicate=OWL.sameAs, object=_Z2)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="eq-diff3",
                detail=(
                    "owl:AllDifferent distinctMembers list contains owl:sameAs "
                    "individuals."
                ),
                arguments=(_Z1, OWL.sameAs, _Z2),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="prp-irp"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P, predicate=RDF.type, object=OWL.IrreflexiveProperty
                )
            ),
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_X)),
        ),
        head=(
            ContradictionConsequent(
                category="prp-irp",
                detail="Irreflexive property used reflexively.",
                arguments=(_X, _P, _X),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="prp-asyp"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P, predicate=RDF.type, object=OWL.AsymmetricProperty
                )
            ),
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
            TripleCondition(pattern=TriplePattern(subject=_Y, predicate=_P, object=_X)),
        ),
        head=(
            ContradictionConsequent(
                category="prp-asyp",
                detail="Asymmetric property used in both directions.",
                arguments=(_X, _P, _Y),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="prp-pdw"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=OWL.propertyDisjointWith, object=_P2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=_P1, object=_Y)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=_P2, object=_Y)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="prp-pdw",
                detail="Disjoint properties share a subject-object pair.",
                arguments=(_X, _P1, _Y),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="prp-adp"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=RDF.type, object=OWL.AllDisjointProperties
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=OWL.members, object=_Y)
            ),
            *owl2_rl_list_conditions(_Y, (_P1, _P2), cell_prefix="prpadp"),
            TripleCondition(
                pattern=TriplePattern(subject=_U, predicate=_P1, object=_V)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_U, predicate=_P2, object=_V)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="prp-adp",
                detail=("AllDisjointProperties members share a subject-object pair."),
                arguments=(_U, _P1, _V),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="prp-npa1"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_NPA, predicate=OWL.sourceIndividual, object=_I1
                )
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_NPA, predicate=OWL.assertionProperty, object=_P
                )
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_NPA, predicate=OWL.targetIndividual, object=_I2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_I1, predicate=_P, object=_I2)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="prp-npa1",
                detail="Negative object property assertion contradicted by a positive assertion.",
                arguments=(_I1, _P, _I2),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="prp-npa2"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_NPA, predicate=OWL.sourceIndividual, object=_I
                )
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_NPA, predicate=OWL.assertionProperty, object=_P
                )
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_NPA, predicate=OWL.targetValue, object=_LT
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_I, predicate=_P, object=_LT)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="prp-npa2",
                detail="Negative data property assertion contradicted by a positive assertion.",
                arguments=(_I, _P, _LT),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="cls-nothing2"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_A, predicate=RDF.type, object=OWL.Nothing
                )
            ),
        ),
        head=(
            ContradictionConsequent(
                category="cls-nothing2",
                detail="Individual is typed as owl:Nothing.",
                arguments=(_A, RDF.type, OWL.Nothing),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="cls-com"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=OWL.complementOf, object=_C2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C1)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C2)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="cls-com",
                detail="Individual is typed as both a class and its complement.",
                arguments=(_X, RDF.type, _C1),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="cls-maxc1"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=OWL.maxCardinality, object=_ZERO
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=OWL.onProperty, object=_P)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_U, predicate=RDF.type, object=_X)
            ),
            TripleCondition(pattern=TriplePattern(subject=_U, predicate=_P, object=_Y)),
        ),
        head=(
            ContradictionConsequent(
                category="cls-maxc1",
                detail="Max cardinality 0 restriction violated by a property assertion.",
                arguments=(_U, _P, _Y),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="cls-maxqc1"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=OWL.maxQualifiedCardinality, object=_ZERO
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=OWL.onProperty, object=_P)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=OWL.onClass, object=_C)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_U, predicate=RDF.type, object=_X)
            ),
            TripleCondition(pattern=TriplePattern(subject=_U, predicate=_P, object=_Y)),
            TripleCondition(
                pattern=TriplePattern(subject=_Y, predicate=RDF.type, object=_C)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="cls-maxqc1",
                detail=(
                    "Qualified max cardinality 0 restriction violated by a typed "
                    "filler."
                ),
                arguments=(_U, _P, _Y),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="cls-maxqc2"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=OWL.maxQualifiedCardinality, object=_ZERO
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=OWL.onProperty, object=_P)
            ),
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=OWL.onClass, object=OWL.Thing
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_U, predicate=RDF.type, object=_X)
            ),
            TripleCondition(pattern=TriplePattern(subject=_U, predicate=_P, object=_Y)),
        ),
        head=(
            ContradictionConsequent(
                category="cls-maxqc2",
                detail=(
                    "Thing-qualified max cardinality 0 restriction violated by a "
                    "property assertion."
                ),
                arguments=(_U, _P, _Y),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="cax-dw"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=OWL.disjointWith, object=_C2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C1)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C2)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="cax-dw",
                detail="Individual is typed as two owl:disjointWith classes.",
                arguments=(_X, RDF.type, _C1),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="cax-adc"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_X, predicate=RDF.type, object=OWL.AllDisjointClasses
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=OWL.members, object=_Y)
            ),
            *owl2_rl_list_conditions(_Y, (_C1, _C2), cell_prefix="caxadc"),
            TripleCondition(
                pattern=TriplePattern(subject=_Z1, predicate=RDF.type, object=_C1)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_Z1, predicate=RDF.type, object=_C2)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="cax-adc",
                detail="Individual is typed as two AllDisjointClasses members.",
                arguments=(_Z1, RDF.type, _C1),
            ),
        ),
    ),
    Rule(
        id=RuleId(ruleset="owl2-rl-contradiction", rule_id="dt-not-type"),
        description=None,
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_LT, predicate=RDF.type, object=_DT)
            ),
            PredicateCondition(predicate="is_literal", arguments=(_LT,)),
            PredicateCondition(
                predicate="literal_not_in_datatype", arguments=(_LT, _DT)
            ),
        ),
        head=(
            ContradictionConsequent(
                category="dt-not-type",
                detail="Literal typed with a datatype that does not contain its value.",
                arguments=(_LT, RDF.type, _DT),
            ),
        ),
    ),
)
