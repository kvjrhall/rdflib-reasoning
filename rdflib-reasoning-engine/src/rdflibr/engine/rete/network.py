class AlphaNode:
    """
    First layer of the RETE network.
    Filters individual facts based on literal constant constraints before any
    join work occurs.
    """

    ...


class PredicateNode:
    """
    Specialized alpha node that wraps read-only predicate callables.

    Predicate nodes represent body-side evaluation only; they are not callback
    hooks and they do not emit logical consequences directly.
    """

    ...


class BetaNode:
    """
    Join node maintaining partial-match memory for conjunctive rule bodies.
    """

    ...


class TerminalNode:
    """
    Leaf node that schedules engine-managed logical production and optional
    observational callbacks from one completed match.
    """

    ...


class NodeRegistry:
    """
    Canonicalizing store for structurally shared network nodes.

    Node sharing is part of the intended RETE optimization strategy and should
    remain independent from proof reconstruction concerns.
    """

    ...
