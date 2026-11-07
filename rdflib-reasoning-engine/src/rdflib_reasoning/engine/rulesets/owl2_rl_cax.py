"""OWL 2 RL class-axiom (``cax-*``) entailment rules.

Implements the triple-producing class axiom rules from OWL 2 Profiles
Section 4.3: ``cax-sco``, ``cax-eqc1``, and ``cax-eqc2``. Contradiction-family
rules such as ``cax-dw`` and ``cax-adc`` remain in the dedicated contradiction
ruleset.
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
from .owl2_rl_common import owl2_rl_rule_description, owl2_rl_rule_id

_X = Variable("x")
_C1 = Variable("c1")
_C2 = Variable("c2")


OWL2_RL_CAX_RULES: tuple[Rule, ...] = (
    Rule(
        id=owl2_rl_rule_id("cax-sco"),
        description=owl2_rl_rule_description(
            "Subclass membership inheritance",
            "Propagate rdf:type across rdfs:subClassOf.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=RDFS.subClassOf, object=_C2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C1)
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C2)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("cax-eqc1"),
        description=owl2_rl_rule_description(
            "Equivalent class forward membership",
            "Propagate rdf:type from the left to the right of owl:equivalentClass.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=OWL.equivalentClass, object=_C2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C1)
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C2)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("cax-eqc2"),
        description=owl2_rl_rule_description(
            "Equivalent class reverse membership",
            "Propagate rdf:type from the right to the left of owl:equivalentClass.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C1, predicate=OWL.equivalentClass, object=_C2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C2)
            ),
            PredicateCondition(predicate="different_terms", arguments=(_C1, _C2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C1)
            ),
        ),
    ),
)
