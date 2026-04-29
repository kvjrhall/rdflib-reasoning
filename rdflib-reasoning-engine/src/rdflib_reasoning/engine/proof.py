from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from rdflib.term import Node, URIRef
from rdflib_reasoning.axiom.common import ContextIdentifier, Triple
from rdflib_reasoning.axiom.structural_element import GraphBacked, StructuralElement

if TYPE_CHECKING:
    from .rules import Rule


class ProofModel(BaseModel):
    """Base model for proof and derivation structures using rdflib node types."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)


class ProofPayloadKind(StrEnum):
    TRIPLE = "triple"
    STRUCTURAL_ELEMENT = "structural_element"
    CONTRADICTION = "contradiction"
    TEXT_CLAIM = "text_claim"


class TripleFact(GraphBacked):
    """A graph-scoped claim represented directly as a triple."""

    kind: Literal["triple"] = "triple"
    triple: Triple = Field(..., description="The triple asserted or derived.")


class StructuralClaim(GraphBacked):
    """A graph-scoped claim represented as a structural element."""

    kind: Literal["structural_element"] = "structural_element"
    element: StructuralElement = Field(
        ..., description="The structural element supporting or expressing the claim."
    )


class ContradictionClaim(GraphBacked):
    """A graph-scoped contradiction witness used in proof outputs."""

    kind: Literal["contradiction"] = "contradiction"
    witness: TripleFact = Field(
        ...,
        description=(
            "The triple witnessing a contradiction, typically of the form "
            "`?x rdf:type owl:Nothing`."
        ),
    )


class TextClaim(GraphBacked):
    """A free-text claim for baseline or partially structured proofs."""

    kind: Literal["text_claim"] = "text_claim"
    text: str = Field(..., description="A free-text claim used in a proof step.")


ProofPayload = Annotated[
    TripleFact | StructuralClaim | ContradictionClaim | TextClaim,
    Field(discriminator="kind"),
]


class RuleDescription(ProofModel):
    """Structured semantic metadata attached to a rule or proof step."""

    label: str = Field(..., description="Short human-readable label for the rule.")
    description: str | None = Field(
        default=None,
        description="Optional longer description of the rule or inference step.",
    )
    references: list[AuthorityReference] = Field(
        default_factory=list,
        description=(
            "Authoritative or explanatory references relevant to the rule, its "
            "semantics, or its structural interpretation."
        ),
    )


class RuleId(ProofModel):
    """Stable engine-level identifier for an applied rule."""

    ruleset: str = Field(
        ...,
        description=(
            "Stable identifier for the ruleset family, e.g. `owl2_rl`, `rdfs`, "
            "or a custom ruleset name."
        ),
    )
    rule_id: str = Field(..., description="Stable identifier for the rule.")


class AuthorityReference(ProofModel):
    """Reference to an authoritative or explanatory source for a rule."""

    kind: Literal[
        "normative_spec",
        "non_normative_spec",
        "implementation_reference",
        "structural_interpretation",
    ] = Field(..., description="The type of authority or reference being cited.")
    uri: URIRef = Field(
        ...,
        description="Authoritative URI, ideally including a document fragment or section.",
    )
    label: str = Field(..., description="Human-readable label for the reference.")


class VariableBinding(ProofModel):
    """One variable binding captured when a rule application fired."""

    name: str = Field(..., description="The variable name used in the rule.")
    value: Node = Field(..., description="The RDF term bound to the variable.")


class ContradictionRecord(ProofModel):
    """Engine-native trace for one contradiction-triggering rule application."""

    context: ContextIdentifier = Field(
        ..., description="The graph (context) wherein the contradiction was detected."
    )
    rule_id: RuleId = Field(
        ..., description="Stable identifier for the contradiction-triggering rule."
    )
    premises: list[TripleFact] = Field(
        ...,
        min_length=1,
        description=(
            "Triple-level premises matched by the contradiction rule application."
        ),
    )
    bindings: list[VariableBinding] = Field(
        default_factory=list,
        description="Optional variable bindings captured for this contradiction event.",
    )
    sequence_id: int = Field(
        ..., ge=1, description="Monotonic sequence id preserving record order."
    )
    witness: TripleFact | None = Field(
        default=None,
        description=(
            "Optional contradiction witness triple for presentation, commonly "
            "an `?x rdf:type owl:Nothing` style witness."
        ),
    )
    category: str | None = Field(
        default=None,
        description="Optional contradiction category label for coarse grouping.",
    )
    detail: str | None = Field(
        default=None,
        description="Optional short contradiction detail message.",
    )


class DerivationRecord(ProofModel):
    """Engine-native trace for one fired rule application."""

    context: ContextIdentifier = Field(
        ..., description="The graph (context) wherein the derivation occurred."
    )
    conclusions: list[TripleFact] = Field(
        ...,
        min_length=1,
        description=(
            "The triple-level conclusions produced by this rule firing. A single "
            "rule application may yield one or more triples."
        ),
    )
    premises: list[TripleFact] = Field(
        default_factory=list,
        description="The supporting triple-level premises used by the rule firing.",
    )
    rule_id: RuleId = Field(
        ..., description="The stable identifier for the derivation step's rule."
    )
    bindings: list[VariableBinding] = Field(
        default_factory=list,
        description="Optional variable bindings captured for the rule application.",
    )
    depth: int | None = Field(
        default=None,
        description="Optional derivation depth within the current explanation graph.",
    )
    silent: bool = Field(
        default=False,
        description=(
            "Whether this rule firing is effectively silent for materialization "
            "and explanation purposes."
        ),
    )
    bootstrap: bool = Field(
        default=False,
        description=(
            "Whether this rule firing occurred during the bootstrap phase before "
            "warmup over existing graph content."
        ),
    )


class SourceSpan(ProofModel):
    """Optional grounding metadata back to an input document."""

    document_id: str | None = Field(
        default=None, description="Identifier for the source document."
    )
    quote: str | None = Field(
        default=None, description="Short supporting quote from the source document."
    )
    start_char: int | None = Field(
        default=None, description="Start offset of the quote in the source document."
    )
    end_char: int | None = Field(
        default=None, description="End offset of the quote in the source document."
    )


class ProofLeaf(ProofModel):
    """A leaf proof node containing a claim and optional grounding."""

    node_kind: Literal["leaf"] = "leaf"
    claim: ProofPayload = Field(..., description="The leaf-level claim.")
    grounding: list[SourceSpan] = Field(
        default_factory=list,
        description="Optional grounding spans supporting the leaf claim.",
    )


class RuleApplication(ProofModel):
    """One direct proof step combining premises, rule attribution, and conclusions."""

    node_kind: Literal["rule_application"] = "rule_application"
    conclusions: list[ProofPayload] = Field(
        ...,
        min_length=1,
        description=(
            "The grouped conclusions established by this proof step. A single "
            "proof step may justify one or more related claims."
        ),
    )
    premises: list[ProofNode] = Field(
        default_factory=list,
        description="The premise proof nodes required for this proof step.",
    )
    rule_id: RuleId | None = Field(
        default=None,
        description=(
            "Optional stable identifier for the rule used in this proof step. "
            "Agent-authored steps may omit this when only a description is known."
        ),
    )
    description: RuleDescription | None = Field(
        default=None,
        description="Optional shared descriptive metadata for this proof step.",
    )
    derivation: DerivationRecord | None = Field(
        default=None,
        description="Optional engine-native derivation record for this proof step.",
    )
    rationale: str | None = Field(
        default=None,
        description="Optional natural-language rationale attached to the step.",
    )
    stated_theorem_name: str | None = Field(
        default=None,
        description="Optional theorem or rule name supplied by the Research Agent.",
    )

    @classmethod
    def from_rule(
        cls,
        rule: "Rule",
        *,
        conclusions: list[ProofPayload],
        premises: list[ProofNode] | None = None,
        derivation: DerivationRecord | None = None,
        rationale: str | None = None,
        stated_theorem_name: str | None = None,
    ) -> "RuleApplication":
        """Construct a proof step from a defined rule and its shared description."""
        return cls(
            conclusions=conclusions,
            premises=[] if premises is None else premises,
            rule_id=rule.id,
            description=rule.description,
            derivation=derivation,
            rationale=rationale,
            stated_theorem_name=stated_theorem_name,
        )

    @classmethod
    def from_description(
        cls,
        description: RuleDescription,
        *,
        conclusions: list[ProofPayload],
        premises: list[ProofNode] | None = None,
        derivation: DerivationRecord | None = None,
        rationale: str | None = None,
        stated_theorem_name: str | None = None,
    ) -> "RuleApplication":
        """Construct a proof step from agent-provided descriptive semantics alone."""
        return cls(
            conclusions=conclusions,
            premises=[] if premises is None else premises,
            description=description,
            derivation=derivation,
            rationale=rationale,
            stated_theorem_name=stated_theorem_name,
        )

    @model_validator(mode="after")
    def check_derivation_alignment(self) -> "RuleApplication":
        if self.rule_id is None and self.description is None:
            raise ValueError(
                "RuleApplication MUST provide at least one of `rule_id` or `description`."
            )
        if (
            self.derivation is not None
            and self.rule_id is not None
            and self.rule_id != self.derivation.rule_id
        ):
            raise ValueError(
                "RuleApplication.rule_id MUST match DerivationRecord.rule_id "
                "when a derivation record is attached and a rule_id is provided."
            )
        return self


ProofNode = Annotated[
    ProofLeaf | RuleApplication,
    Field(discriminator="node_kind"),
]


class DirectProof(ProofModel):
    """A reconstructed or agent-proposed direct proof for evaluation."""

    context: ContextIdentifier = Field(
        ..., description="The graph (context) wherein the proof is evaluated."
    )
    goal: ProofPayload = Field(
        ..., description="The claim the proof aims to establish."
    )
    proof: ProofNode = Field(..., description="The proof tree supporting the goal.")
    verdict: Literal["proved", "disproved", "contradiction", "incomplete"] | None = (
        Field(
            default=None,
            description="Optional summary verdict attached to the proof.",
        )
    )
    notes: str | None = Field(
        default=None,
        description="Optional proof-level notes from the engine or Research Agent.",
    )


RuleApplication.model_rebuild()
DirectProof.model_rebuild()
