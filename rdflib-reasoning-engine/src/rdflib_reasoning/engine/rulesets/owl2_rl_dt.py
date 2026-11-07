"""OWL 2 RL datatype (``dt-*``) entailment rules.

These rules implement Table 8 of OWL 2 Profiles Section 4.3 (Semantics of
Datatypes): ``dt-type1``, ``dt-type2``, ``dt-eq``, and ``dt-diff``.

Encoding notes
--------------
The specification states schema-style quantification ("for each datatype",
"for each literal"). A RETE engine cannot enumerate the infinite literal
space, so non-bootstrap rules are grounded on literals that already appear in
working memory:

- ``dt-type1``: empty-body bootstrap, one silent rule per IRI in
  :data:`~rdflib_reasoning.engine.owl2_rl_datatypes.OWL2_RL_SUPPORTED_DATATYPES`
  (including ``rdfs:Literal``, ``rdf:PlainLiteral``, and ``rdf:XMLLiteral``,
  which OWL 2 RL lists as supported datatypes). Each rule asserts
  ``T(dt, rdf:type, rdfs:Datatype)``.
- ``dt-type2``: match any working-memory triple whose object is a literal
  (``?s ?p ?lt``), join datatype IRIs via ``?dt rdf:type rdfs:Datatype``
  (populated by ``dt-type1``), and guard with read-only builtins
  ``is_literal(?lt)`` and ``literal_in_datatype(?lt, ?dt)``. Conclude
  ``T(lt, rdf:type, dt)``.
- ``dt-eq`` / ``dt-diff``: join two object-position literals from working
  memory (``?s1 ?p1 ?lt1`` and ``?s2 ?p2 ?lt2``), guard with ``is_literal``
  and ``literal_same_value`` / ``literal_different_value``. ``dt-eq`` also
  requires ``different_terms(?lt1, ?lt2)`` so identical nodes do not emit
  reflexive ``owl:sameAs``. Conclude ``owl:sameAs`` or ``owl:differentFrom``.

Literal-subject conclusions are generalized-RDF forms required by OWL 2 RL.
Callers that enforce RDF 1.1 triple well-formedness (the engine default
``literal_subject_policy``) will reject those conclusions; the rule encodings
remain faithful to the profile tables.
"""

from __future__ import annotations

from rdflib.namespace import OWL, RDF, RDFS
from rdflib.term import URIRef, Variable

from ..owl2_rl_datatypes import OWL2_RL_SUPPORTED_DATATYPES
from ..rules import (
    PredicateCondition,
    Rule,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from .owl2_rl_common import owl2_rl_rule_description, owl2_rl_rule_id

_S = Variable("s")
_S1 = Variable("s1")
_S2 = Variable("s2")
_P = Variable("p")
_P1 = Variable("p1")
_P2 = Variable("p2")
_LT = Variable("lt")
_LT1 = Variable("lt1")
_LT2 = Variable("lt2")
_DT = Variable("dt")


def _dt_type1_rule(datatype: URIRef) -> Rule:
    """Build a silent ``dt-type1`` bootstrap rule for one supported datatype."""
    return Rule(
        id=owl2_rl_rule_id("dt-type1"),
        description=owl2_rl_rule_description(
            "Supported datatype typing",
            "Assert that each OWL 2 RL supported datatype IRI is an rdfs:Datatype.",
        ),
        body=(),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=datatype, predicate=RDF.type, object=RDFS.Datatype
                )
            ),
        ),
        silent=True,
    )


_DT_TYPE1_RULES: tuple[Rule, ...] = tuple(
    _dt_type1_rule(datatype)
    for datatype in sorted(OWL2_RL_SUPPORTED_DATATYPES, key=str)
)

_DT_TYPE2_RULE = Rule(
    id=owl2_rl_rule_id("dt-type2"),
    description=owl2_rl_rule_description(
        "Literal datatype membership",
        "When a literal appears in working memory and its data value lies in "
        "an OWL 2 RL datatype value space, type the literal with that "
        "datatype.",
    ),
    body=(
        TripleCondition(pattern=TriplePattern(subject=_S, predicate=_P, object=_LT)),
        TripleCondition(
            pattern=TriplePattern(subject=_DT, predicate=RDF.type, object=RDFS.Datatype)
        ),
        PredicateCondition(predicate="is_literal", arguments=(_LT,)),
        PredicateCondition(predicate="literal_in_datatype", arguments=(_LT, _DT)),
    ),
    head=(
        TripleConsequent(
            pattern=TriplePattern(subject=_LT, predicate=RDF.type, object=_DT)
        ),
    ),
)

_DT_EQ_RULE = Rule(
    id=owl2_rl_rule_id("dt-eq"),
    description=owl2_rl_rule_description(
        "Literal same-value equality",
        "When two distinct literal terms that appear in working memory denote "
        "the same data value, conclude owl:sameAs.",
    ),
    body=(
        TripleCondition(pattern=TriplePattern(subject=_S1, predicate=_P1, object=_LT1)),
        TripleCondition(pattern=TriplePattern(subject=_S2, predicate=_P2, object=_LT2)),
        PredicateCondition(predicate="is_literal", arguments=(_LT1,)),
        PredicateCondition(predicate="is_literal", arguments=(_LT2,)),
        PredicateCondition(predicate="different_terms", arguments=(_LT1, _LT2)),
        PredicateCondition(predicate="literal_same_value", arguments=(_LT1, _LT2)),
    ),
    head=(
        TripleConsequent(
            pattern=TriplePattern(subject=_LT1, predicate=OWL.sameAs, object=_LT2)
        ),
    ),
)

_DT_DIFF_RULE = Rule(
    id=owl2_rl_rule_id("dt-diff"),
    description=owl2_rl_rule_description(
        "Literal different-value inequality",
        "When two literals that appear in working memory denote different data "
        "values, conclude owl:differentFrom.",
    ),
    body=(
        TripleCondition(pattern=TriplePattern(subject=_S1, predicate=_P1, object=_LT1)),
        TripleCondition(pattern=TriplePattern(subject=_S2, predicate=_P2, object=_LT2)),
        PredicateCondition(predicate="is_literal", arguments=(_LT1,)),
        PredicateCondition(predicate="is_literal", arguments=(_LT2,)),
        PredicateCondition(predicate="literal_different_value", arguments=(_LT1, _LT2)),
    ),
    head=(
        TripleConsequent(
            pattern=TriplePattern(
                subject=_LT1, predicate=OWL.differentFrom, object=_LT2
            )
        ),
    ),
)


#: OWL 2 RL ``dt-*`` entailment rules (Table 8).
OWL2_RL_DT_RULES: tuple[Rule, ...] = (
    *_DT_TYPE1_RULES,
    _DT_TYPE2_RULE,
    _DT_EQ_RULE,
    _DT_DIFF_RULE,
)
