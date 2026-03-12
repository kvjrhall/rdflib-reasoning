from pydantic import BaseModel


class TripleProduction(BaseModel):
    """
    Declarative logical consequent managed by the engine.

    Logical rule heads are represented as engine-managed triple production so
    that fixed-point reasoning and future truth maintenance remain centralized.
    """

    ...


class ActionInstance:
    """
    Scheduled unit of work derived from a completed match.

    An action instance may represent logical triple production, an
    observational callback, or both as separate scheduled consequences of a
    single terminal match.
    """

    ...
