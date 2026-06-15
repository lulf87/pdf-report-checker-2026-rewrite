from app.infrastructure.table.numeric_semantics import numeric_expressions_equivalent


def test_basic_numeric_expression_equivalence() -> None:
    assert numeric_expressions_equivalent("1", "1.0")
    assert numeric_expressions_equivalent("1,000", "1000")
    assert numeric_expressions_equivalent("１．０", "1.0")


def test_comparator_expression_equivalence() -> None:
    assert numeric_expressions_equivalent("≥5", ">=5")
    assert numeric_expressions_equivalent("不小于5", "≥5")
    assert numeric_expressions_equivalent("不大于5", "≤5")


def test_range_expression_equivalence_without_misreading_negative_numbers() -> None:
    assert numeric_expressions_equivalent("5~10", "5-10")
    assert numeric_expressions_equivalent("-5", "-5.0")
    assert not numeric_expressions_equivalent("-5", "5")


def test_tolerance_expression_equivalence_in_tolerance_context() -> None:
    assert numeric_expressions_equivalent("±0.5", "+/-0.5", field_kind="tolerance")
    assert numeric_expressions_equivalent("允许误差0.5", "±0.5", field_kind="tolerance")
