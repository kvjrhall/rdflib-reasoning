from pydantic import BaseModel


class Fact(BaseModel):
    """
    Fundamental unit of data within the RETE internals.

    In the current design, logical entailment is triple-oriented. Any broader
    RETE-OO-style object handling remains internal scaffolding and MUST NOT
    bypass the engine's triple-based materialization contract.
    """

    ...


class PartialMatch(BaseModel):
    """
    A collection of Facts that have satisfied a subset of a rule's
    preconditions.

    Partial matches are the join-time support structure later referenced by
    agenda scheduling, justification tracking, and explanation reconstruction.
    """

    ...
