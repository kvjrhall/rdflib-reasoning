import pytest
from rdflib import BNode
from rdflib_reasoning.axiom.structural_element import (
    DeclarationElement,
    GraphBacked,
    StructuralElement,
)


def test_cannot_instantiate_abc_graph_backed():
    with pytest.raises(TypeError):
        GraphBacked(context=BNode())


def test_cannot_instantiate_abc_structural_element():
    with pytest.raises(TypeError):
        StructuralElement(context=BNode())  # pyright: ignore[reportAbstractUsage]


def test_cannot_instantiate_abc_declaration_element():
    with pytest.raises(TypeError):
        DeclarationElement(context=BNode(), name_value=BNode())  # pyright: ignore[reportAbstractUsage]
