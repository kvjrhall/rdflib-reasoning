import warnings
from collections.abc import Generator

import pytest
from rdflib import RDF, XSD, BNode, Literal, Node, URIRef
from rdflib_reasoning.engine.builtins import (
    DEFAULT_CALLBACK_BUILTINS,
    DEFAULT_PREDICATE_BUILTINS,
    Builtins,
    CallbackHook,
    DifferentTermsPredicate,
    IsLiteralPredicate,
    LiteralDifferentValuePredicate,
    LiteralInDatatypePredicate,
    LiteralNotInDatatypePredicate,
    LiteralSameValuePredicate,
    NotLiteralPredicate,
    PredicateHook,
    RuleContext,
    SameTermPredicate,
    TermInPredicate,
    TermNotInPredicate,
)
from rdflib_reasoning.engine.errors import BuiltinError, BuiltinInputError


@pytest.fixture
def context() -> Generator[RuleContext, None, None]:
    yield RuleContext()


def test_builtins_defaults() -> None:
    defaults = Builtins()
    assert defaults.callbacks == DEFAULT_CALLBACK_BUILTINS
    assert defaults.predicates == DEFAULT_PREDICATE_BUILTINS


def test_builtins_extended() -> None:
    class TestCallback(CallbackHook):
        def run(self, context: RuleContext, *args: Node) -> None:
            return None

    class TestPredicate(PredicateHook):
        def test(self, context: RuleContext, *args: Node) -> bool:
            return True

    callback = TestCallback()
    predicate = TestPredicate()

    extended = Builtins.extend_defaults(
        more_callbacks={"test": callback},
        more_predicates={"test": predicate},
    )
    assert extended.callbacks == {
        **DEFAULT_CALLBACK_BUILTINS,
        "test": callback,
    }
    assert extended.predicates == {
        **DEFAULT_PREDICATE_BUILTINS,
        "test": predicate,
    }


def test_different_terms_0_args(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        DifferentTermsPredicate().test(context)


def test_different_terms_1_args(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        DifferentTermsPredicate().test(context, BNode())


def test_different_terms_bnode_2_same(context: RuleContext) -> None:
    node = BNode()
    assert not DifferentTermsPredicate().test(context, node, node)


def test_different_terms_bnode_2_diff(context: RuleContext) -> None:
    assert DifferentTermsPredicate().test(context, BNode(), BNode())


def test_different_terms_uri_3_same(context: RuleContext) -> None:
    node = URIRef("urn:test:s")
    assert not DifferentTermsPredicate().test(context, node, node, node)


def test_different_terms_uri_3_diff(context: RuleContext) -> None:
    nodes = [URIRef("urn:test:s"), BNode(), Literal(1)]
    assert DifferentTermsPredicate().test(context, *nodes)


def test_not_literal_0_args(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        NotLiteralPredicate().test(context)


def test_not_literal_false(context: RuleContext) -> None:
    assert not NotLiteralPredicate().test(context, Literal(1))


def test_not_literal_many_false(context: RuleContext) -> None:
    nodes = [
        Literal(1),
        Literal("words", lang="en"),
        Literal(True, datatype=XSD.boolean),
    ]
    assert not NotLiteralPredicate().test(context, *nodes)


def test_not_literal_many_true(context: RuleContext) -> None:
    nodes = [
        BNode(),
        URIRef("urn:test:s"),
        URIRef("urn:test:p"),
    ]
    assert NotLiteralPredicate().test(context, *nodes)


def test_not_literal_mixed(context: RuleContext) -> None:
    nodes = [URIRef("urn:test:s"), BNode(), Literal(1)]
    assert not NotLiteralPredicate().test(context, *nodes)


def test_not_literal_true(context: RuleContext) -> None:
    assert NotLiteralPredicate().test(context, BNode())


def test_report_argument_count_between(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError) as exc_info:
        context.report_argument_count(
            [BNode(), URIRef("urn:test:p")], max_inclusive=1, min_inclusive=0
        )
    assert "Expected between 0 and 1 argument(s), got 2" in str(exc_info.value)


def test_report_argument_count_exact(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError) as exc_info:
        context.report_argument_count(
            [BNode(), URIRef("urn:test:p")], max_inclusive=1, min_inclusive=1
        )
    assert "Expected exactly 1 argument(s), got 2" in str(exc_info.value)


def test_report_argument_count_max_inclusive(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError) as exc_info:
        context.report_argument_count([BNode(), URIRef("urn:test:p")], max_inclusive=1)
    assert "Expected at most 1 argument(s), got 2" in str(exc_info.value)


def test_report_argument_count_min_inclusive(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError) as exc_info:
        context.report_argument_count([], min_inclusive=1)
    assert "Expected at least 1 argument(s), got 0" in str(exc_info.value)


def test_report_argument_count_missing_bounds(context: RuleContext) -> None:
    with pytest.raises(ValueError) as exc_info:
        context.report_argument_count([])
    assert not isinstance(exc_info.value, BuiltinError)
    assert "At least one of `min_inclusive` or `max_inclusive` must be provided" in str(
        exc_info.value
    )


def test_report_argument_count_unordered_bounds(context: RuleContext) -> None:
    with pytest.raises(ValueError) as exc_info:
        context.report_argument_count([], max_inclusive=0, min_inclusive=1)
    assert not isinstance(exc_info.value, BuiltinError)
    assert "`min_inclusive` (1) must be less than `max_inclusive` (0)" in str(
        exc_info.value
    )


def test_report_input_mismatch_with_args(context: RuleContext) -> None:
    message = "test-message"
    with pytest.raises(BuiltinInputError) as exc_info:
        context.report_input_mismatch(
            message, [URIRef("urn:test:s"), URIRef("urn:test:p"), URIRef("urn:test:o")]
        )
    assert message in str(exc_info.value)


def test_report_input_mismatch_no_args(context: RuleContext) -> None:
    message = "test-message"
    with pytest.raises(BuiltinInputError) as exc_info:
        context.report_input_mismatch(message, [])
    assert message in str(exc_info.value)
    assert "No arguments provided" in str(exc_info.value)


def test_different_terms_predicate() -> None:
    predicate = DifferentTermsPredicate()
    assert predicate.test(
        RuleContext(), URIRef("urn:test:s"), URIRef("urn:test:p"), URIRef("urn:test:o")
    )


def test_same_term_0_args(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        SameTermPredicate().test(context)


def test_same_term_1_args(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        SameTermPredicate().test(context, BNode())


def test_same_term_bnode_2_same(context: RuleContext) -> None:
    node = BNode()
    assert SameTermPredicate().test(context, node, node)


def test_same_term_bnode_2_diff(context: RuleContext) -> None:
    assert not SameTermPredicate().test(context, BNode(), BNode())


def test_same_term_uri_3_same(context: RuleContext) -> None:
    node = URIRef("urn:test:s")
    assert SameTermPredicate().test(context, node, node, node)


def test_same_term_uri_3_diff(context: RuleContext) -> None:
    nodes = [URIRef("urn:test:s"), BNode(), Literal(1)]
    assert not SameTermPredicate().test(context, *nodes)


def test_term_in_0_args(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        TermInPredicate().test(context)


def test_term_in_1_args(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        TermInPredicate().test(context, BNode())


def test_term_in_bnode_2_true(context: RuleContext) -> None:
    node = BNode()
    assert TermInPredicate().test(context, node, node)


def test_term_in_bnode_3_false(context: RuleContext) -> None:
    assert not TermInPredicate().test(context, BNode(), BNode(), BNode())


def test_term_in_bnode_3_true(context: RuleContext) -> None:
    node = BNode()
    assert TermInPredicate().test(context, node, node, BNode())


def test_term_not_in_0_args(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        TermNotInPredicate().test(context)


def test_term_not_in_1_args(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        TermInPredicate().test(context, BNode())


def test_term_not_in_bnode_2_false(context: RuleContext) -> None:
    node = BNode()
    assert not TermNotInPredicate().test(context, node, node)


def test_term_not_in_bnode_3_true(context: RuleContext) -> None:
    assert TermNotInPredicate().test(context, BNode(), BNode(), BNode())


def test_term_not_in_bnode_3_false(context: RuleContext) -> None:
    node = BNode()
    assert not TermNotInPredicate().test(context, node, node, BNode())


def test_is_literal_0_args(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        IsLiteralPredicate().test(context)


def test_is_literal_true_and_false(context: RuleContext) -> None:
    assert IsLiteralPredicate().test(context, Literal(1))
    assert not IsLiteralPredicate().test(context, BNode())
    assert not IsLiteralPredicate().test(context, Literal(1), URIRef("urn:test:s"))


def test_literal_same_value_arity(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        LiteralSameValuePredicate().test(context, Literal(1))


def test_literal_same_value_cross_type(context: RuleContext) -> None:
    left = Literal("1", datatype=XSD.integer)
    right = Literal("1.0", datatype=XSD.decimal)
    assert LiteralSameValuePredicate().test(context, left, right)
    assert not LiteralSameValuePredicate().test(
        context, left, Literal("2", datatype=XSD.integer)
    )
    assert not LiteralSameValuePredicate().test(context, left, URIRef("urn:test:s"))


def test_literal_same_value_ill_typed_incomparable(context: RuleContext) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ill_typed = Literal("not-a-number", datatype=XSD.integer)
    assert not LiteralSameValuePredicate().test(
        context, ill_typed, Literal("1", datatype=XSD.integer)
    )


def test_literal_different_value(context: RuleContext) -> None:
    left = Literal("1", datatype=XSD.integer)
    right = Literal("2", datatype=XSD.integer)
    assert LiteralDifferentValuePredicate().test(context, left, right)
    assert not LiteralDifferentValuePredicate().test(context, left, left)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ill_typed = Literal("not-a-number", datatype=XSD.integer)
    assert not LiteralDifferentValuePredicate().test(
        context, ill_typed, Literal("1", datatype=XSD.integer)
    )


def test_literal_in_datatype_predicate(context: RuleContext) -> None:
    one = Literal("1", datatype=XSD.integer)
    assert LiteralInDatatypePredicate().test(context, one, XSD.integer)
    assert LiteralInDatatypePredicate().test(context, one, XSD.decimal)
    assert LiteralInDatatypePredicate().test(context, one, XSD.float)
    assert LiteralInDatatypePredicate().test(context, one, XSD.double)
    assert not LiteralInDatatypePredicate().test(context, one, XSD.negativeInteger)
    assert not LiteralInDatatypePredicate().test(
        context, one, URIRef("urn:example:NotADatatype")
    )
    assert not LiteralInDatatypePredicate().test(context, BNode(), XSD.integer)
    assert LiteralInDatatypePredicate().test(
        context, Literal("<a/>", datatype=RDF.XMLLiteral), RDF.XMLLiteral
    )


def test_literal_in_datatype_arity(context: RuleContext) -> None:
    with pytest.raises(BuiltinInputError):
        LiteralInDatatypePredicate().test(context, Literal(1))


def test_literal_not_in_datatype_predicate(context: RuleContext) -> None:
    one = Literal("1", datatype=XSD.integer)
    assert LiteralNotInDatatypePredicate().test(context, one, XSD.negativeInteger)
    assert not LiteralNotInDatatypePredicate().test(context, one, XSD.integer)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ill_typed = Literal("not-a-number", datatype=XSD.integer)
    assert LiteralNotInDatatypePredicate().test(context, ill_typed, XSD.integer)
    assert LiteralNotInDatatypePredicate().test(
        context, Literal("128", datatype=XSD.integer), XSD.byte
    )


def test_default_registry_includes_literal_predicates() -> None:
    assert "is_literal" in DEFAULT_PREDICATE_BUILTINS
    assert "literal_same_value" in DEFAULT_PREDICATE_BUILTINS
    assert "literal_different_value" in DEFAULT_PREDICATE_BUILTINS
    assert "literal_in_datatype" in DEFAULT_PREDICATE_BUILTINS
    assert "literal_not_in_datatype" in DEFAULT_PREDICATE_BUILTINS
