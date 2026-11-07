"""Shared helpers for OWL 2 RL Section 4.3 rule definitions.

Entailment rules use ``RuleId(ruleset="owl2-rl", rule_id=...)``. Contradiction
rules keep ``RuleId(ruleset="owl2-rl-contradiction", rule_id=...)`` and live in
the dedicated contradiction ruleset module.
"""

from __future__ import annotations

from rdflib.term import URIRef, Variable

from ..proof import AuthorityReference, RuleDescription, RuleId

#: Stable ruleset id for OWL 2 RL entailment (triple-producing) rules.
OWL2_RL_RULESET: str = "owl2-rl"

#: Stable ruleset id for OWL 2 RL contradiction-signaling rules.
OWL2_RL_CONTRADICTION_RULESET: str = "owl2-rl-contradiction"

#: Official OWL 2 Profiles URI for Section 4.3 rule tables.
OWL2_RL_PROFILES_SECTION_URI: URIRef = URIRef(
    "https://www.w3.org/TR/owl2-profiles/"
    "#Reasoning_in_OWL_2_RL_and_RDF_Graphs_using_Rules"
)

# Common Section 4.3 variable names shared across family rule modules.
X = Variable("x")
Y = Variable("y")
Z = Variable("z")
P = Variable("p")
Q = Variable("q")
C = Variable("c")
A = Variable("a")
B = Variable("b")
I = Variable("i")  # noqa: E741  # NOTE: matches specification variable name
U = Variable("u")
W = Variable("w")
LT = Variable("lt")
T = Variable("t")


def owl2_rl_rule_id(rule_id: str) -> RuleId:
    """Build a ``RuleId`` for an OWL 2 RL entailment rule.

    Args:
        rule_id: Canonical OWL 2 RL rule name (for example ``eq-sym`` or
            ``prp-dom``).

    Returns:
        A ``RuleId`` with ``ruleset`` set to :data:`OWL2_RL_RULESET`.
    """
    return RuleId(ruleset=OWL2_RL_RULESET, rule_id=rule_id)


def owl2_rl_rule_description(
    label: str,
    description: str | None = None,
) -> RuleDescription:
    """Build package-consumer-safe metadata for an OWL 2 RL entailment rule.

    References cite the official OWL 2 Profiles Section 4.3 URI rather than
    repository-local documentation paths.

    Args:
        label: Short human-readable rule label.
        description: Optional longer description of the inference step.

    Returns:
        A ``RuleDescription`` with a normative OWL 2 Profiles authority
        reference.
    """
    return RuleDescription(
        label=label,
        description=description,
        references=[
            AuthorityReference(
                kind="normative_spec",
                uri=OWL2_RL_PROFILES_SECTION_URI,
                label=(
                    "OWL 2 Profiles: Reasoning in OWL 2 RL and RDF Graphs using Rules"
                ),
            )
        ],
    )
