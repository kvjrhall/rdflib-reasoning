"""OWL 2 RL contradiction-signaling rules (non-mutating diagnostics channel).

These rules model contradiction-producing RL rule families that are representable
with the currently available rule IR and predicate builtins. Rule heads emit
``ContradictionConsequent`` actions rather than mutating logical closure.
"""

from rdflib.namespace import OWL, RDF
from rdflib.term import Variable

from ..proof import RuleId
from ..rules import (
    ContradictionConsequent,
    Rule,
    TripleCondition,
    TriplePattern,
)

_X = Variable("x")
_Y = Variable("y")
_P = Variable("p")
_A = Variable("a")
_I = Variable("i")
_I1 = Variable("i1")
_I2 = Variable("i2")
_LT = Variable("lt")
_NPA = Variable("npa")


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
)
