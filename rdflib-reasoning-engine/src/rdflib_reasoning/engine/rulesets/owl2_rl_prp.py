"""OWL 2 RL property (``prp-*``) entailment rules.

Implements the triple-producing property rules from OWL 2 Profiles Section 4.3.

**Production choices**

- ``prp-ap`` uses empty-body bootstrap rules with ``silent=True`` so built-in
  annotation-property typing participates in working memory without graph
  materialization (same pattern as RDF axiom bootstrap rules).
- ``prp-rng`` guards the object with ``not_literal`` so range typing never
  places a literal in subject position of an ``rdf:type`` conclusion.
- ``prp-fp``, ``prp-ifp``, and ``prp-key`` add ``different_terms`` on the
  equated pair so trivial reflexive ``owl:sameAs`` conclusions are not
  produced when both bindings are the same term.
- ``prp-spo1``, ``prp-eqp1``, and ``prp-eqp2`` add ``different_terms`` on the
  two properties to skip no-op reassertion when the properties coincide.

**LIST-dependent rules**

``prp-spo2`` and ``prp-key`` expand ``LIST[...]`` via
:func:`~rdflib_reasoning.engine.rulesets.owl2_rl_lists.owl2_rl_list_conditions`
for fixed chain lengths ``1..3`` (property chains) and ``1..2`` (keys). Longer
lists are outside this finite expansion and are not covered by the exported
tuple.
"""

from __future__ import annotations

from rdflib.namespace import OWL, RDF, RDFS
from rdflib.term import URIRef, Variable

from ..rules import (
    PredicateCondition,
    Rule,
    TripleCondition,
    TripleConsequent,
    TriplePattern,
)
from .owl2_rl_common import (
    C as _C,
)
from .owl2_rl_common import (
    P as _P,
)
from .owl2_rl_common import (
    X as _X,
)
from .owl2_rl_common import (
    Y as _Y,
)
from .owl2_rl_common import (
    owl2_rl_rule_description as _rule_description,
)
from .owl2_rl_common import (
    owl2_rl_rule_id as _rule_id,
)
from .owl2_rl_lists import owl2_rl_list_conditions as _list_conditions

_Y1 = Variable("y1")
_Y2 = Variable("y2")
_X1 = Variable("x1")
_X2 = Variable("x2")
_P1 = Variable("p1")
_P2 = Variable("p2")
_Z = Variable("z")

#: Built-in OWL 2 annotation properties typed by ``prp-ap``.
_BUILTIN_ANNOTATION_PROPERTIES: tuple[URIRef, ...] = (
    RDFS.label,
    RDFS.comment,
    RDFS.seeAlso,
    RDFS.isDefinedBy,
    OWL.deprecated,
    OWL.versionInfo,
    OWL.priorVersion,
    OWL.backwardCompatibleWith,
    OWL.incompatibleWith,
)

#: Finite property-chain lengths covered by ``prp-spo2`` expansions.
_PRP_SPO2_LENGTHS: tuple[int, ...] = (1, 2, 3)

#: Finite hasKey list lengths covered by ``prp-key`` expansions.
_PRP_KEY_LENGTHS: tuple[int, ...] = (1, 2)


def _prp_ap_rules() -> tuple[Rule, ...]:
    """Empty-body silent bootstrap for built-in annotation properties."""
    return tuple(
        Rule(
            id=_rule_id("prp-ap"),
            description=_rule_description(
                "Built-in annotation property typing",
                "Assert that each built-in OWL 2 annotation property is an "
                "owl:AnnotationProperty.",
            ),
            body=(),
            head=(
                TripleConsequent(
                    pattern=TriplePattern(
                        subject=ap,
                        predicate=RDF.type,
                        object=OWL.AnnotationProperty,
                    )
                ),
            ),
            silent=True,
        )
        for ap in _BUILTIN_ANNOTATION_PROPERTIES
    )


def _prp_spo2_rule(length: int) -> Rule:
    """Build a fixed-length ``prp-spo2`` expansion for a property chain."""
    props = tuple(Variable(f"p{i}") for i in range(1, length + 1))
    nodes = tuple(Variable(f"u{i}") for i in range(1, length + 2))
    list_head = Variable("x")
    chain_assertions = tuple(
        TripleCondition(
            pattern=TriplePattern(
                subject=nodes[i], predicate=props[i], object=nodes[i + 1]
            )
        )
        for i in range(length)
    )
    return Rule(
        id=_rule_id("prp-spo2"),
        description=_rule_description(
            "Property chain assertion",
            "Propagate a property assertion across an owl:propertyChainAxiom "
            f"whose RDF list has length {length}.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P, predicate=OWL.propertyChainAxiom, object=list_head
                )
            ),
            *_list_conditions(list_head, props, cell_prefix="chaincell"),
            *chain_assertions,
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(
                    subject=nodes[0], predicate=_P, object=nodes[length]
                )
            ),
        ),
    )


def _prp_key_rule(length: int) -> Rule:
    """Build a fixed-length ``prp-key`` expansion for an ``owl:hasKey`` list."""
    props = tuple(Variable(f"p{i}") for i in range(1, length + 1))
    values = tuple(Variable(f"kv{i}") for i in range(1, length + 1))
    list_head = Variable("u")
    x_assertions = tuple(
        TripleCondition(
            pattern=TriplePattern(subject=_X1, predicate=props[i], object=values[i])
        )
        for i in range(length)
    )
    y_assertions = tuple(
        TripleCondition(
            pattern=TriplePattern(subject=_X2, predicate=props[i], object=values[i])
        )
        for i in range(length)
    )
    return Rule(
        id=_rule_id("prp-key"),
        description=_rule_description(
            "HasKey individual equality",
            "Infer owl:sameAs for distinct individuals of a class that share "
            f"the same values for an owl:hasKey list of length {length}.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_C, predicate=OWL.hasKey, object=list_head
                )
            ),
            *_list_conditions(list_head, props, cell_prefix="keycell"),
            TripleCondition(
                pattern=TriplePattern(subject=_X1, predicate=RDF.type, object=_C)
            ),
            *x_assertions,
            TripleCondition(
                pattern=TriplePattern(subject=_X2, predicate=RDF.type, object=_C)
            ),
            *y_assertions,
            PredicateCondition(predicate="different_terms", arguments=(_X1, _X2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X1, predicate=OWL.sameAs, object=_X2)
            ),
        ),
    )


OWL2_RL_PRP_RULES: tuple[Rule, ...] = (
    *_prp_ap_rules(),
    Rule(
        id=_rule_id("prp-dom"),
        description=_rule_description(
            "Property domain inference",
            "Propagate rdf:type to the subject of a property using its domain.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_P, predicate=RDFS.domain, object=_C)
            ),
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X, predicate=RDF.type, object=_C)
            ),
        ),
    ),
    Rule(
        id=_rule_id("prp-rng"),
        description=_rule_description(
            "Property range inference",
            "Propagate rdf:type to the object of a property using its range. "
            "Literal objects are skipped so conclusions remain RDF 1.1 concrete "
            "triples (no literal subjects).",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_P, predicate=RDFS.range, object=_C)
            ),
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
            PredicateCondition(predicate="not_literal", arguments=(_Y,)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_Y, predicate=RDF.type, object=_C)
            ),
        ),
    ),
    Rule(
        id=_rule_id("prp-fp"),
        description=_rule_description(
            "Functional property equality",
            "Infer owl:sameAs between distinct objects of a functional property "
            "for the same subject.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P, predicate=RDF.type, object=OWL.FunctionalProperty
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=_P, object=_Y1)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=_P, object=_Y2)
            ),
            PredicateCondition(predicate="different_terms", arguments=(_Y1, _Y2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_Y1, predicate=OWL.sameAs, object=_Y2)
            ),
        ),
    ),
    Rule(
        id=_rule_id("prp-ifp"),
        description=_rule_description(
            "Inverse-functional property equality",
            "Infer owl:sameAs between distinct subjects of an inverse-functional "
            "property for the same object.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P,
                    predicate=RDF.type,
                    object=OWL.InverseFunctionalProperty,
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X1, predicate=_P, object=_Y)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X2, predicate=_P, object=_Y)
            ),
            PredicateCondition(predicate="different_terms", arguments=(_X1, _X2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X1, predicate=OWL.sameAs, object=_X2)
            ),
        ),
    ),
    Rule(
        id=_rule_id("prp-symp"),
        description=_rule_description(
            "Symmetric property assertion",
            "Propagate a symmetric property assertion in the reverse direction.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P, predicate=RDF.type, object=OWL.SymmetricProperty
                )
            ),
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_Y, predicate=_P, object=_X)
            ),
        ),
    ),
    Rule(
        id=_rule_id("prp-trp"),
        description=_rule_description(
            "Transitive property assertion",
            "Compose consecutive assertions of a transitive property.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P, predicate=RDF.type, object=OWL.TransitiveProperty
                )
            ),
            TripleCondition(pattern=TriplePattern(subject=_X, predicate=_P, object=_Y)),
            TripleCondition(pattern=TriplePattern(subject=_Y, predicate=_P, object=_Z)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X, predicate=_P, object=_Z)
            ),
        ),
    ),
    Rule(
        id=_rule_id("prp-spo1"),
        description=_rule_description(
            "Subproperty assertion inheritance",
            "Propagate property assertions across rdfs:subPropertyOf.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=RDFS.subPropertyOf, object=_P2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=_P1, object=_Y)
            ),
            PredicateCondition(predicate="different_terms", arguments=(_P1, _P2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X, predicate=_P2, object=_Y)
            ),
        ),
    ),
    *(_prp_spo2_rule(n) for n in _PRP_SPO2_LENGTHS),
    Rule(
        id=_rule_id("prp-eqp1"),
        description=_rule_description(
            "Equivalent property forward assertion",
            "Propagate assertions from the left to the right of "
            "owl:equivalentProperty.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=OWL.equivalentProperty, object=_P2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=_P1, object=_Y)
            ),
            PredicateCondition(predicate="different_terms", arguments=(_P1, _P2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X, predicate=_P2, object=_Y)
            ),
        ),
    ),
    Rule(
        id=_rule_id("prp-eqp2"),
        description=_rule_description(
            "Equivalent property reverse assertion",
            "Propagate assertions from the right to the left of "
            "owl:equivalentProperty.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(
                    subject=_P1, predicate=OWL.equivalentProperty, object=_P2
                )
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=_P2, object=_Y)
            ),
            PredicateCondition(predicate="different_terms", arguments=(_P1, _P2)),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_X, predicate=_P1, object=_Y)
            ),
        ),
    ),
    Rule(
        id=_rule_id("prp-inv1"),
        description=_rule_description(
            "Inverse property forward assertion",
            "Propagate an assertion across owl:inverseOf from the left property "
            "to the right property in reverse direction.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_P1, predicate=OWL.inverseOf, object=_P2)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=_P1, object=_Y)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_Y, predicate=_P2, object=_X)
            ),
        ),
    ),
    Rule(
        id=_rule_id("prp-inv2"),
        description=_rule_description(
            "Inverse property reverse assertion",
            "Propagate an assertion across owl:inverseOf from the right property "
            "to the left property in reverse direction.",
        ),
        body=(
            TripleCondition(
                pattern=TriplePattern(subject=_P1, predicate=OWL.inverseOf, object=_P2)
            ),
            TripleCondition(
                pattern=TriplePattern(subject=_X, predicate=_P2, object=_Y)
            ),
        ),
        head=(
            TripleConsequent(
                pattern=TriplePattern(subject=_Y, predicate=_P1, object=_X)
            ),
        ),
    ),
    *(_prp_key_rule(n) for n in _PRP_KEY_LENGTHS),
)
