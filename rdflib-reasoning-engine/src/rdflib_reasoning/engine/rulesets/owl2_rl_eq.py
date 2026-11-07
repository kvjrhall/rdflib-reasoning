"""OWL 2 RL equality (``eq-*``) entailment rules.

These rules materialize ``owl:sameAs`` reflexivity, symmetry, transitivity, and
replacement properties from OWL 2 Profiles Section 4.3 Table 4.
"""

from __future__ import annotations

from rdflib.namespace import OWL
from rdflib.term import Variable

from ..rules import (
    PredicateCondition,
    Rule,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from .owl2_rl_common import (
    P,
    X,
    Y,
    Z,
    owl2_rl_rule_description,
    owl2_rl_rule_id,
)

_S = Variable("s")
_O = Variable("o")
_S_PRIME = Variable("s_prime")
_P_PRIME = Variable("p_prime")
_O_PRIME = Variable("o_prime")

#: OWL 2 RL Table 4 equality entailment rules (``eq-ref`` … ``eq-rep-o``).
#:
#: ``eq-ref`` is split across two ``Rule`` objects that share the canonical
#: rule id so subject/predicate reflexivity still fires when the object is a
#: literal (illegal as an RDF 1.1 subject).
OWL2_RL_EQ_RULES: tuple[Rule, ...] = (
    Rule(
        id=owl2_rl_rule_id("eq-ref"),
        description=owl2_rl_rule_description(
            "Reflexive equality (subject and predicate)",
            "Infer owl:sameAs reflexivity for the subject and predicate of every "
            "matched triple.",
        ),
        body=(
            TripleCondition(pattern=TriplePattern(subject=_S, predicate=P, object=_O)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_S, predicate=OWL.sameAs, object=_S)
            ),
            TripleConsequent(
                pattern=TriplePattern(subject=P, predicate=OWL.sameAs, object=P)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("eq-ref"),
        description=owl2_rl_rule_description(
            "Reflexive equality (object)",
            "Infer owl:sameAs reflexivity for the object of a matched triple when "
            "the object is a legal RDF 1.1 subject (IRI or blank node).",
        ),
        body=(
            TripleCondition(pattern=TriplePattern(subject=_S, predicate=P, object=_O)),
            PredicateCondition(predicate="not_literal", arguments=(_O,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_O, predicate=OWL.sameAs, object=_O)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("eq-sym"),
        description=owl2_rl_rule_description(
            "Symmetric equality",
            "Infer the symmetric owl:sameAs assertion when the equated terms "
            "differ and the object is a legal RDF 1.1 subject.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=X, predicate=OWL.sameAs, object=Y)
            ),
            PredicateCondition(predicate="different_terms", arguments=(X, Y)),
            PredicateCondition(predicate="not_literal", arguments=(Y,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=Y, predicate=OWL.sameAs, object=X)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("eq-trans"),
        description=owl2_rl_rule_description(
            "Transitive equality",
            "Propagate owl:sameAs transitively across equated individuals when "
            "the endpoints differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=X, predicate=OWL.sameAs, object=Y)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=Y, predicate=OWL.sameAs, object=Z)
            ),
            PredicateCondition(predicate="different_terms", arguments=(X, Z)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=X, predicate=OWL.sameAs, object=Z)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("eq-rep-s"),
        description=owl2_rl_rule_description(
            "Subject equality replacement",
            "Replace the subject of a triple with an owl:sameAs-equivalent "
            "subject when the equated terms differ and the replacement is a "
            "legal RDF 1.1 subject.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_S, predicate=OWL.sameAs, object=_S_PRIME)
            ),
            TripleCondition(pattern=TriplePattern(subject=_S, predicate=P, object=_O)),
            PredicateCondition(predicate="different_terms", arguments=(_S, _S_PRIME)),
            PredicateCondition(predicate="not_literal", arguments=(_S_PRIME,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_S_PRIME, predicate=P, object=_O)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("eq-rep-p"),
        description=owl2_rl_rule_description(
            "Predicate equality replacement",
            "Replace the predicate of a triple with an owl:sameAs-equivalent "
            "predicate when the equated terms differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=P, predicate=OWL.sameAs, object=_P_PRIME)
            ),
            TripleCondition(pattern=TriplePattern(subject=_S, predicate=P, object=_O)),
            PredicateCondition(predicate="different_terms", arguments=(P, _P_PRIME)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_S, predicate=_P_PRIME, object=_O)
            ),
        ),
    ),
    Rule(
        id=owl2_rl_rule_id("eq-rep-o"),
        description=owl2_rl_rule_description(
            "Object equality replacement",
            "Replace the object of a triple with an owl:sameAs-equivalent object "
            "when the equated terms differ.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_O, predicate=OWL.sameAs, object=_O_PRIME)
            ),
            TripleCondition(pattern=TriplePattern(subject=_S, predicate=P, object=_O)),
            PredicateCondition(predicate="different_terms", arguments=(_O, _O_PRIME)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_S, predicate=P, object=_O_PRIME)
            ),
        ),
    ),
)
