from __future__ import annotations

import pytest

from app.domain.inspection_group import InspectionItemGroup
from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument
from app.domain.report import InspectionItem
from app.rules.ptr.atomic_compare import build_atomic_comparison_rows
from app.rules.ptr.clause_text_compare import compare_clause_texts
from app.rules.ptr.atomic_result_check import check_atomic_result_bindings
from app.rules.ptr.requirement_classifier import RequirementType, classify_requirement


def _clause(number: str, title: str, body: str) -> PTRClause:
    return PTRClause(
        clause_id=f"ptr-{number}",
        number=PTRClauseNumber.from_string(number),
        title=title,
        body_text=f"{title}\n{body}",
        full_text=f"{number} {title}\n{body}",
    )


def _report_item(
    *,
    item_no: str,
    clause_number: str,
    title: str,
    requirement: str,
    actual: str,
    page: int = 32,
) -> InspectionItem:
    return InspectionItem(
        sequence_raw=item_no,
        sequence=int(item_no),
        item_name=title,
        standard_clause=clause_number,
        standard_requirement=requirement,
        test_result=actual,
        result_values=[actual],
        conclusion="符合",
        remark="/",
        source_page=page,
    )


@pytest.mark.parametrize(
    ("clause", "expected_value", "expected_unit", "expected_label"),
    [
        (_clause("2.6", "环氧乙烷残留量", "应不超过 10µg/g。"), 10.0, "μg/g", "环氧乙烷残留量"),
        (_clause("2.7", "细菌内毒素", "应不超过 20EU/件。"), 20.0, "EU/件", "细菌内毒素"),
    ],
)
def test_classifier_extracts_generic_numeric_limit_from_title_and_body(
    clause: PTRClause,
    expected_value: float,
    expected_unit: str,
    expected_label: str,
) -> None:
    classification = classify_requirement(clause, PTRDocument(clauses=[clause]))

    assert classification.requirement_type == RequirementType.NUMERIC_LIMIT
    assert len(classification.atomic_requirements) == 1
    requirement = classification.atomic_requirements[0]
    assert requirement.label == expected_label
    assert requirement.operator == "<="
    assert requirement.expected_value == expected_value
    assert requirement.unit == expected_unit


@pytest.mark.parametrize(
    ("clause", "report_item"),
    [
        (
            _clause("2.6", "环氧乙烷残留量", "应不超过 10µg/g。"),
            _report_item(
                item_no="40",
                clause_number="2.6",
                title="环氧乙烷\n残留量",
                requirement="应不超过 10µg/g。\n单位：µg/g",
                actual="＜0.5",
            ),
        ),
        (
            _clause("2.7", "细菌内毒素", "应不超过 20EU/件。"),
            _report_item(
                item_no="41",
                clause_number="2.7",
                title="细菌内毒\n素",
                requirement="应不超过 20EU/件。\n单位：EU/件",
                actual="＜20",
            ),
        ),
    ],
)
def test_numeric_limit_title_and_unit_line_variations_do_not_create_clause_text_mismatch(
    clause: PTRClause,
    report_item: InspectionItem,
) -> None:
    findings = compare_clause_texts([clause], [report_item], task_id="numeric-limit")

    assert not any(finding.code == "PTR_CLAUSE_TEXT_MISMATCH" for finding in findings)


def test_numeric_limit_with_same_limit_but_different_parameter_name_remains_mismatch() -> None:
    clause = _clause("2.7", "细菌内毒素", "应不超过 20EU/件。")
    report_item = _report_item(
        item_no="41",
        clause_number="2.7",
        title="其他污染物",
        requirement="其他污染物应不超过 20EU/件。\n单位：EU/件",
        actual="＜20",
    )

    findings = compare_clause_texts([clause], [report_item], task_id="numeric-limit")

    assert any(finding.code == "PTR_CLAUSE_TEXT_MISMATCH" for finding in findings)


@pytest.mark.parametrize(
    ("clause", "report_item", "expected", "actual", "unit"),
    [
        (
            _clause("2.6", "环氧乙烷残留量", "应不超过 10µg/g。"),
            _report_item(
                item_no="40",
                clause_number="2.6",
                title="环氧乙烷\n残留量",
                requirement="应不超过 10µg/g。\n单位：µg/g",
                actual="＜0.5",
            ),
            "≤10 μg/g",
            "<0.5",
            "μg/g",
        ),
        (
            _clause("2.7", "细菌内毒素", "应不超过 20EU/件。"),
            _report_item(
                item_no="41",
                clause_number="2.7",
                title="细菌内毒\n素",
                requirement="应不超过 20EU/件。\n单位：EU/件",
                actual="＜20",
            ),
            "≤20 EU/件",
            "<20",
            "EU/件",
        ),
    ],
)
def test_numeric_limit_atomic_row_compares_report_measurement(
    clause: PTRClause,
    report_item: InspectionItem,
    expected: str,
    actual: str,
    unit: str,
) -> None:
    group = InspectionItemGroup(
        item_no=report_item.sequence_raw,
        display_item_no=report_item.sequence_raw,
        pages=[report_item.source_page or 32],
        rows=[report_item],
    )

    rows = build_atomic_comparison_rows(clause, PTRDocument(clauses=[clause]), [group])

    assert len(rows) == 1
    assert rows[0].expected == expected
    assert rows[0].actual == actual
    assert rows[0].unit == unit
    assert rows[0].status == "match"


def test_numeric_limit_atomic_row_is_mismatch_only_when_actual_exceeds_limit() -> None:
    clause = _clause("2.6", "环氧乙烷残留量", "应不超过 10µg/g。")
    report_item = _report_item(
        item_no="40",
        clause_number="2.6",
        title="环氧乙烷残留量",
        requirement="应不超过 10µg/g。\n单位：µg/g",
        actual="11",
    )
    group = InspectionItemGroup(
        item_no="40",
        display_item_no="40",
        pages=[32],
        rows=[report_item],
    )

    rows = build_atomic_comparison_rows(clause, PTRDocument(clauses=[clause]), [group])

    assert len(rows) == 1
    assert rows[0].actual == "11"
    assert rows[0].status == "mismatch"
    assert "不满足" in rows[0].reason

    findings = check_atomic_result_bindings(
        PTRDocument(clauses=[clause]),
        [report_item],
        clauses=[clause],
        task_id="numeric-limit",
    )
    assert len(findings) == 1
    assert findings[0].code == "PTR_TABLE_VALUE_MISMATCH"
    assert findings[0].metadata["parameter_name"] == "环氧乙烷残留量"
    assert findings[0].metadata["expected_operator"] == "<="
    assert findings[0].metadata["expected_value"] == 10.0
    assert findings[0].metadata["expected_unit"] == "μg/g"
    assert findings[0].metadata["actual_operator"] == "="
    assert findings[0].metadata["actual_value"] == 11.0
    assert findings[0].metadata["actual_unit"] == "μg/g"
    assert findings[0].metadata["report_conclusion"] == "符合"


def test_numeric_limit_converts_report_result_unit_before_comparison() -> None:
    clause = _clause("2.5", "连接电缆绝缘电阻", "连接电缆任意两芯脚之间的绝缘电阻应不小于 5MΩ。")
    report_item = _report_item(
        item_no="161",
        clause_number="2.5",
        title="连接电缆\n绝缘电阻",
        requirement="连接电缆任意两芯脚之间的绝缘电阻应不小于 5MΩ。\n单位：GΩ",
        actual="1.1～2.6",
    )
    group = InspectionItemGroup(
        item_no="161",
        display_item_no="161",
        pages=[106],
        rows=[report_item],
    )

    rows = build_atomic_comparison_rows(clause, PTRDocument(clauses=[clause]), [group])

    assert len(rows) == 1
    assert rows[0].expected == "≥5 MΩ"
    assert rows[0].actual == "1.1～2.6"
    assert rows[0].unit == "GΩ"
    assert rows[0].status == "match"


def test_torque_wrench_range_keeps_specialized_a_b_atomic_requirements() -> None:
    clause = _clause(
        "2.8.2",
        "扭矩扳手尺寸",
        "0.88 毫米≤ A ≤ 0.89 毫米\n0.96 毫米≤ B ≤ 1 毫米",
    )

    rows = build_atomic_comparison_rows(clause, PTRDocument(clauses=[clause]), [])

    assert {row.atomic_id for row in rows} == {
        "2.8.2:torque_wrench:A",
        "2.8.2:torque_wrench:B",
    }
