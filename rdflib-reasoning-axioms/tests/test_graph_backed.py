from typing import Literal

import pytest
from rdflib_reasoning.axiom.structural_element import GraphBacked


def test_missing_kind_raises_type_error() -> None:
    with pytest.raises(TypeError):

        class MissingKind(GraphBacked):
            pass


def test_kind_missing_annotation_raises_type_error() -> None:
    with pytest.raises(TypeError):

        class MissingAnnotation(GraphBacked):
            kind = "foo"


def test_kind_annotation_not_literal_raises_type_error() -> None:
    with pytest.raises(TypeError):

        class MissingAnnotation(GraphBacked):
            kind: str = "my_kind"


def test_kind_annotation_not_string_literal_raises_type_error() -> None:
    with pytest.raises(TypeError):

        class NotStringLiteral(GraphBacked):
            kind: Literal[1] = 1


def test_kind_annotation_not_single_literal_raises_type_error() -> None:
    with pytest.raises(TypeError):

        class NotStringLiteral(GraphBacked):
            kind: Literal["foo", "bar"] = "foo"
