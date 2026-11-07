"""Expand OWL 2 RL ``LIST[h, e1, ..., en]`` abbreviations into triple conditions.

OWL 2 Profiles Section 4.3 Table 3 expands list atoms into ``rdf:first`` /
``rdf:rest`` / ``rdf:nil`` conjunctions. Fresh rest-cell variables ``z2`` …
``zn`` are introduced for list cells after the head.
"""

from __future__ import annotations

from rdflib.namespace import RDF
from rdflib.term import Variable

from ..rules import PatternTerm, TripleCondition, TriplePattern


def owl2_rl_list_conditions(
    head: PatternTerm,
    elements: tuple[PatternTerm, ...] | list[PatternTerm],
    *,
    cell_prefix: str = "z",
) -> tuple[TripleCondition, ...]:
    """Expand ``LIST[head, *elements]`` into Table 3 ``TripleCondition`` tuples.

    For ``n = len(elements) >= 1`` the expansion is:

    - ``T(head, rdf:first, e1)`` and ``T(head, rdf:rest, z2)`` (or ``rdf:nil``
      when ``n == 1``)
    - for each subsequent element ``ei`` (``2 <= i < n``): ``T(zi, rdf:first,
      ei)`` and ``T(zi, rdf:rest, z{i+1})``
    - for the final element when ``n >= 2``: ``T(zn, rdf:first, en)`` and
      ``T(zn, rdf:rest, rdf:nil)``

    Fresh cell variables are named ``{cell_prefix}2`` ... ``{cell_prefix}{n}``.
    Callers that use more than one list abbreviation in the same rule body
    SHOULD choose distinct ``cell_prefix`` values so those variables stay fresh.

    This helper only builds read-only match conditions. It does not mutate
    graphs or register builtins.

    Args:
        head: List head term or variable (``h`` in the OWL 2 Profiles
            abbreviation).
        elements: Ordered list element terms or variables (``e1`` ... ``en``).
            At least one element is required.
        cell_prefix: Prefix for fresh intermediate cell variables. Defaults to
            ``"z"`` so cells are ``z2`` ... ``zn`` as in Table 3.

    Returns:
        Ordered ``TripleCondition`` values implementing the Table 3 expansion.

    Raises:
        ValueError: If ``elements`` is empty.
    """
    if not elements:
        raise ValueError("OWL 2 RL LIST expansion requires at least one element")

    n = len(elements)
    conditions: list[TripleCondition] = []

    def cell(index: int) -> PatternTerm:
        # Table 3 uses h for the first cell and z2..zn for later cells.
        if index == 1:
            return head
        return Variable(f"{cell_prefix}{index}")

    for i, element in enumerate(elements, start=1):
        current = cell(i)
        conditions.append(
            TripleCondition(
                pattern=TriplePattern(
                    subject=current, predicate=RDF.first, object=element
                )
            )
        )
        rest_object: PatternTerm = RDF.nil if i == n else cell(i + 1)
        conditions.append(
            TripleCondition(
                pattern=TriplePattern(
                    subject=current, predicate=RDF.rest, object=rest_object
                )
            )
        )

    return tuple(conditions)
