"""Profile-level OWL 2 RL conformance cases against the full ruleset.

These tests exercise W3C-style conformance kinds (positive entailment, negative
entailment, consistency, inconsistency) under
:data:`~rdflib_reasoning.engine.api.OWL2_RL_RETE_MATERIALIZED` /
:data:`~rdflib_reasoning.engine.rulesets.OWL2_RL_RULES`, not isolated family
subsets. Premises avoid literal objects so RDF 1.1 ``literal_subject_policy``
does not abort saturation via ``dt-type2``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Final, Literal

import pytest
from rdflib import OWL, RDF, RDFS, XSD, BNode, Namespace, URIRef
from rdflib.term import IdentifiedNode
from rdflib_reasoning.axiom.common import Triple
from rdflib_reasoning.engine import (
    OWL2_RL_RETE_MATERIALIZED,
    InMemoryContradictionRecorder,
    RETEEngine,
)

NS = Namespace("urn:example:owl2-rl-conformance:")

Owl2RlConformanceKind = Literal[
    "positive_entailment",
    "negative_entailment",
    "consistency",
    "inconsistency",
]


@dataclass(frozen=True, slots=True)
class Owl2RlConformanceCase:
    """One curated OWL 2 RL profile-level conformance case.

    Args:
        case_id: Stable identifier used as the pytest parameter id.
        kind: Conformance test kind mirrored from OWL 2 Conformance.
        premises: Asserted triples saturated under the full OWL 2 RL profile.
        conclusions: Triples that must be present after saturation (positive).
        non_conclusions: Triples that must be absent after saturation (negative).
        expected_contradiction_ids: Optional expected contradiction rule ids
            (inconsistency). When ``None``, only non-emptiness is checked.
    """

    case_id: str
    kind: Owl2RlConformanceKind
    premises: frozenset[Triple]
    conclusions: frozenset[Triple] = frozenset()
    non_conclusions: frozenset[Triple] = frozenset()
    expected_contradiction_ids: frozenset[str] | None = None


def _list2(
    head: IdentifiedNode, first: IdentifiedNode, second: IdentifiedNode
) -> frozenset[Triple]:
    """Encode a length-2 RDF list rooted at ``head``."""
    rest = BNode()
    return frozenset(
        {
            (head, RDF.first, first),
            (head, RDF.rest, rest),
            (rest, RDF.first, second),
            (rest, RDF.rest, RDF.nil),
        }
    )


def _full_profile_engine() -> RETEEngine:
    """Return a RETE engine configured with the full OWL 2 RL profile.

    Contradiction diagnostics are retained without raising so inconsistency
    cases remain observable after saturation.
    """
    spec = replace(
        OWL2_RL_RETE_MATERIALIZED,
        contradiction_recorder_factory=lambda _context: InMemoryContradictionRecorder(
            warn=False
        ),
        contradiction_policy="record",
    )
    return spec.engine_factory().new_engine(URIRef(f"{NS}engine"))


def _saturate(premises: frozenset[Triple]) -> RETEEngine:
    """Warm bootstrap rules and saturate ``premises`` under the full profile."""
    engine = _full_profile_engine()
    engine.warmup(premises)
    return engine


def _cases_of(kind: Owl2RlConformanceKind) -> Sequence[Owl2RlConformanceCase]:
    return tuple(case for case in OWL2_RL_CONFORMANCE_CASES if case.kind == kind)


# ---------------------------------------------------------------------------
# Curated cases (full OWL2_RL_RULES / OWL2_RL_RETE_MATERIALIZED)
# ---------------------------------------------------------------------------

OWL2_RL_CONFORMANCE_CASES: Final[tuple[Owl2RlConformanceCase, ...]] = (
    # --- Positive entailment: eq-* ---
    Owl2RlConformanceCase(
        case_id="pos-eq-sym-trans",
        kind="positive_entailment",
        premises=frozenset(
            {
                (NS.a, OWL.sameAs, NS.b),
                (NS.b, OWL.sameAs, NS.c),
            }
        ),
        conclusions=frozenset(
            {
                (NS.b, OWL.sameAs, NS.a),
                (NS.a, OWL.sameAs, NS.c),
            }
        ),
    ),
    Owl2RlConformanceCase(
        case_id="pos-eq-rep-s",
        kind="positive_entailment",
        premises=frozenset(
            {
                (NS.a, OWL.sameAs, NS.a2),
                (NS.a, NS.p, NS.b),
            }
        ),
        conclusions=frozenset({(NS.a2, NS.p, NS.b)}),
    ),
    # --- Positive entailment: prp-* ---
    Owl2RlConformanceCase(
        case_id="pos-prp-dom-rng",
        kind="positive_entailment",
        premises=frozenset(
            {
                (NS.hasParent, RDFS.domain, NS.Person),
                (NS.hasParent, RDFS.range, NS.Person),
                (NS.alice, NS.hasParent, NS.bob),
            }
        ),
        conclusions=frozenset(
            {
                (NS.alice, RDF.type, NS.Person),
                (NS.bob, RDF.type, NS.Person),
            }
        ),
    ),
    Owl2RlConformanceCase(
        case_id="pos-prp-symp-trp",
        kind="positive_entailment",
        premises=frozenset(
            {
                (NS.knows, RDF.type, OWL.SymmetricProperty),
                (NS.alice, NS.knows, NS.bob),
                (NS.ancestor, RDF.type, OWL.TransitiveProperty),
                (NS.alice, NS.ancestor, NS.bob),
                (NS.bob, NS.ancestor, NS.carol),
            }
        ),
        conclusions=frozenset(
            {
                (NS.bob, NS.knows, NS.alice),
                (NS.alice, NS.ancestor, NS.carol),
            }
        ),
    ),
    Owl2RlConformanceCase(
        case_id="pos-prp-spo1",
        kind="positive_entailment",
        premises=frozenset(
            {
                (NS.hasMother, RDFS.subPropertyOf, NS.hasParent),
                (NS.alice, NS.hasMother, NS.mary),
            }
        ),
        conclusions=frozenset({(NS.alice, NS.hasParent, NS.mary)}),
    ),
    # --- Positive entailment: cls-* ---
    Owl2RlConformanceCase(
        case_id="pos-cls-avf",
        kind="positive_entailment",
        premises=frozenset(
            {
                (NS.R, OWL.allValuesFrom, NS.C),
                (NS.R, OWL.onProperty, NS.p),
                (NS.u, RDF.type, NS.R),
                (NS.u, NS.p, NS.v),
            }
        ),
        conclusions=frozenset({(NS.v, RDF.type, NS.C)}),
    ),
    Owl2RlConformanceCase(
        case_id="pos-cls-hv",
        kind="positive_entailment",
        premises=frozenset(
            {
                (NS.R, OWL.hasValue, NS.y),
                (NS.R, OWL.onProperty, NS.p),
                (NS.u, RDF.type, NS.R),
            }
        ),
        conclusions=frozenset({(NS.u, NS.p, NS.y)}),
    ),
    # --- Positive entailment: cax-* ---
    Owl2RlConformanceCase(
        case_id="pos-cax-sco",
        kind="positive_entailment",
        premises=frozenset(
            {
                (NS.Person, RDFS.subClassOf, NS.Animal),
                (NS.alice, RDF.type, NS.Person),
            }
        ),
        conclusions=frozenset({(NS.alice, RDF.type, NS.Animal)}),
    ),
    Owl2RlConformanceCase(
        case_id="pos-cax-eqc1",
        kind="positive_entailment",
        premises=frozenset(
            {
                (NS.Human, OWL.equivalentClass, NS.Person),
                (NS.alice, RDF.type, NS.Human),
            }
        ),
        conclusions=frozenset({(NS.alice, RDF.type, NS.Person)}),
    ),
    # --- Positive entailment: scm-* ---
    Owl2RlConformanceCase(
        case_id="pos-scm-sco",
        kind="positive_entailment",
        premises=frozenset(
            {
                (NS.Dog, RDFS.subClassOf, NS.Mammal),
                (NS.Mammal, RDFS.subClassOf, NS.Animal),
            }
        ),
        conclusions=frozenset({(NS.Dog, RDFS.subClassOf, NS.Animal)}),
    ),
    # --- Positive: multi-family interaction (scm + cax) ---
    Owl2RlConformanceCase(
        case_id="pos-scm-cax-chain",
        kind="positive_entailment",
        premises=frozenset(
            {
                (NS.Dog, RDFS.subClassOf, NS.Mammal),
                (NS.Mammal, RDFS.subClassOf, NS.Animal),
                (NS.fido, RDF.type, NS.Dog),
            }
        ),
        conclusions=frozenset(
            {
                (NS.Dog, RDFS.subClassOf, NS.Animal),
                (NS.fido, RDF.type, NS.Mammal),
                (NS.fido, RDF.type, NS.Animal),
            }
        ),
    ),
    # --- Positive: dt-* bootstrap under the combined profile ---
    Owl2RlConformanceCase(
        case_id="pos-dt-type1-bootstrap",
        kind="positive_entailment",
        premises=frozenset(),
        conclusions=frozenset(
            {
                (XSD.integer, RDF.type, RDFS.Datatype),
                (XSD.string, RDF.type, RDFS.Datatype),
                (RDFS.Literal, RDF.type, RDFS.Datatype),
            }
        ),
    ),
    # --- Negative entailment ---
    Owl2RlConformanceCase(
        case_id="neg-no-unrelated-typing",
        kind="negative_entailment",
        premises=frozenset(
            {
                (NS.hasParent, RDFS.domain, NS.Person),
                (NS.alice, NS.hasParent, NS.bob),
            }
        ),
        non_conclusions=frozenset(
            {
                (NS.alice, RDF.type, NS.UnrelatedClass),
                (NS.bob, RDF.type, NS.Person),
                (NS.bob, NS.hasParent, NS.alice),
            }
        ),
    ),
    Owl2RlConformanceCase(
        case_id="neg-no-invented-property",
        kind="negative_entailment",
        premises=frozenset(
            {
                (NS.knows, RDF.type, OWL.SymmetricProperty),
                (NS.alice, NS.knows, NS.bob),
            }
        ),
        non_conclusions=frozenset(
            {
                (NS.alice, NS.invented, NS.bob),
                (NS.carol, NS.knows, NS.alice),
                (NS.alice, RDF.type, NS.UnrelatedClass),
            }
        ),
    ),
    Owl2RlConformanceCase(
        case_id="neg-subclass-does-not-invert",
        kind="negative_entailment",
        premises=frozenset(
            {
                (NS.Dog, RDFS.subClassOf, NS.Mammal),
                (NS.fido, RDF.type, NS.Mammal),
            }
        ),
        non_conclusions=frozenset(
            {
                (NS.fido, RDF.type, NS.Dog),
                (NS.Mammal, RDFS.subClassOf, NS.Dog),
            }
        ),
    ),
    # --- Consistency ---
    Owl2RlConformanceCase(
        case_id="cons-axiom-rich-no-conflict",
        kind="consistency",
        premises=frozenset(
            {
                (NS.Person, RDFS.subClassOf, NS.Animal),
                (NS.Dog, RDFS.subClassOf, NS.Mammal),
                (NS.Mammal, RDFS.subClassOf, NS.Animal),
                (NS.hasParent, RDFS.domain, NS.Person),
                (NS.hasParent, RDFS.range, NS.Person),
                (NS.knows, RDF.type, OWL.SymmetricProperty),
                (NS.alice, RDF.type, NS.Person),
                (NS.alice, NS.hasParent, NS.bob),
                (NS.alice, NS.knows, NS.carol),
                (NS.fido, RDF.type, NS.Dog),
            }
        ),
    ),
    Owl2RlConformanceCase(
        case_id="cons-equivalent-classes",
        kind="consistency",
        premises=frozenset(
            {
                (NS.Human, OWL.equivalentClass, NS.Person),
                (NS.alice, RDF.type, NS.Human),
                (NS.bob, RDF.type, NS.Person),
            }
        ),
    ),
    # --- Inconsistency (false-family under full ruleset) ---
    Owl2RlConformanceCase(
        case_id="incons-eq-diff1",
        kind="inconsistency",
        premises=frozenset(
            {
                (NS.a, OWL.sameAs, NS.b),
                (NS.a, OWL.differentFrom, NS.b),
            }
        ),
        expected_contradiction_ids=frozenset({"eq-diff1"}),
    ),
    Owl2RlConformanceCase(
        case_id="incons-cls-nothing2",
        kind="inconsistency",
        premises=frozenset({(NS.x, RDF.type, OWL.Nothing)}),
        expected_contradiction_ids=frozenset({"cls-nothing2"}),
    ),
    Owl2RlConformanceCase(
        case_id="incons-cax-dw",
        kind="inconsistency",
        premises=frozenset(
            {
                (NS.C1, OWL.disjointWith, NS.C2),
                (NS.x, RDF.type, NS.C1),
                (NS.x, RDF.type, NS.C2),
            }
        ),
        expected_contradiction_ids=frozenset({"cax-dw"}),
    ),
    Owl2RlConformanceCase(
        case_id="incons-prp-pdw",
        kind="inconsistency",
        premises=frozenset(
            {
                (NS.p1, OWL.propertyDisjointWith, NS.p2),
                (NS.s, NS.p1, NS.o),
                (NS.s, NS.p2, NS.o),
            }
        ),
        expected_contradiction_ids=frozenset({"prp-pdw"}),
    ),
    Owl2RlConformanceCase(
        case_id="incons-prp-asyp",
        kind="inconsistency",
        premises=frozenset(
            {
                (NS.p, RDF.type, OWL.AsymmetricProperty),
                (NS.x, NS.p, NS.y),
                (NS.y, NS.p, NS.x),
            }
        ),
        expected_contradiction_ids=frozenset({"prp-asyp"}),
    ),
    Owl2RlConformanceCase(
        case_id="incons-prp-irp",
        kind="inconsistency",
        premises=frozenset(
            {
                (NS.p, RDF.type, OWL.IrreflexiveProperty),
                (NS.x, NS.p, NS.x),
            }
        ),
        expected_contradiction_ids=frozenset({"prp-irp"}),
    ),
    Owl2RlConformanceCase(
        case_id="incons-eq-diff2",
        kind="inconsistency",
        premises=frozenset(
            {
                (NS.ad, RDF.type, OWL.AllDifferent),
                (NS.ad, OWL.members, NS.members),
                *_list2(NS.members, NS.z1, NS.z2),
                (NS.z1, OWL.sameAs, NS.z2),
            }
        ),
        expected_contradiction_ids=frozenset({"eq-diff2"}),
    ),
)


@pytest.mark.parametrize(
    "case",
    _cases_of("positive_entailment"),
    ids=lambda case: case.case_id,
)
def test_owl2_rl_positive_entailment(case: Owl2RlConformanceCase) -> None:
    """Saturated premises under the full profile entail every conclusion triple."""
    engine = _saturate(case.premises)
    missing = case.conclusions - set(engine.known_triples)
    assert not missing, f"{case.case_id}: missing conclusions {sorted(missing)!r}"
    assert engine.contradiction_records() == ()


@pytest.mark.parametrize(
    "case",
    _cases_of("negative_entailment"),
    ids=lambda case: case.case_id,
)
def test_owl2_rl_negative_entailment(case: Owl2RlConformanceCase) -> None:
    """Saturated premises must not invent named non-conclusion triples."""
    engine = _saturate(case.premises)
    present = case.non_conclusions & set(engine.known_triples)
    assert not present, f"{case.case_id}: unexpected triples {sorted(present)!r}"
    assert engine.contradiction_records() == ()


@pytest.mark.parametrize(
    "case",
    _cases_of("consistency"),
    ids=lambda case: case.case_id,
)
def test_owl2_rl_consistency(case: Owl2RlConformanceCase) -> None:
    """Axiom-rich but coherent premises saturate with no contradiction records."""
    engine = _saturate(case.premises)
    assert engine.contradiction_records() == ()


@pytest.mark.parametrize(
    "case",
    _cases_of("inconsistency"),
    ids=lambda case: case.case_id,
)
def test_owl2_rl_inconsistency(case: Owl2RlConformanceCase) -> None:
    """Inconsistent premises retain at least one contradiction under the full profile."""
    engine = _saturate(case.premises)
    records = engine.contradiction_records()
    assert records, f"{case.case_id}: expected at least one contradiction record"
    if case.expected_contradiction_ids is not None:
        found = {record.rule_id.rule_id for record in records}
        assert case.expected_contradiction_ids <= found, (
            f"{case.case_id}: expected {sorted(case.expected_contradiction_ids)!r} "
            f"among {sorted(found)!r}"
        )


def test_owl2_rl_conformance_suite_covers_all_kinds() -> None:
    """Harness inventory spans the four OWL 2 Conformance-style kinds."""
    kinds = {case.kind for case in OWL2_RL_CONFORMANCE_CASES}
    assert kinds == {
        "positive_entailment",
        "negative_entailment",
        "consistency",
        "inconsistency",
    }
    assert OWL2_RL_RETE_MATERIALIZED.rules  # profile is non-empty
