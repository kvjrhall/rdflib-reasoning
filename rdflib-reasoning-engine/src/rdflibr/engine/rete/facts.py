from pydantic import BaseModel, ConfigDict, Field
from rdflib.term import Node
from rdflibr.axiom.common import Triple


class Fact(BaseModel):
    """
    Fundamental unit of data within the RETE internals.

    In the current design, logical entailment is triple-oriented. Any broader
    RETE-OO-style object handling remains internal scaffolding and MUST NOT
    bypass the engine's triple-based materialization contract.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(..., description="Stable internal identifier for this fact.")
    triple: Triple = Field(
        ..., description="The RDFLib triple represented by the fact."
    )
    stated: bool = Field(
        default=True,
        description="Whether the fact is an asserted input rather than derived output.",
    )


class PartialMatch(BaseModel):
    """
    A collection of Facts that have satisfied a subset of a rule's
    preconditions.

    Partial matches are the join-time support structure later referenced by
    agenda scheduling, justification tracking, and explanation reconstruction.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    facts: tuple[Fact, ...] = Field(
        default_factory=tuple,
        description="Facts participating in the partial match in join order.",
    )
    bindings: dict[str, Node] = Field(
        default_factory=dict,
        description="Current variable bindings by RDFLib variable name.",
    )
    depth: int = Field(
        default=0,
        description="Breadth-first derivation depth used by agenda scheduling.",
    )
