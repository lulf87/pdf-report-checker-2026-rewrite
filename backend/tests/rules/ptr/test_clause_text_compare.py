from app.domain.ptr import PTRClause
from app.domain.report import InspectionItem
from app.rules.ptr.clause_text_compare import compare_clause_texts
from app.rules.ptr.report_item_grouping import build_ptr_report_item_groups, ptr_group_for_clause


def _clause(number: str, body: str) -> PTRClause:
    return PTRClause(clause_id=f"ptr-{number}", number=number, title=body[:8], body_text=body)


def test_clause_text_compare_accepts_strict_normalized_match() -> None:
    findings = compare_clause_texts(
        [_clause("2.1.1", "导管外观\n应无杂质。")],
        [InspectionItem(standard_clause="2.1.1", standard_requirement="导管外观 应无杂质。")],
    )

    assert findings == []


def test_clause_text_compare_outputs_finding_for_strict_mismatch() -> None:
    findings = compare_clause_texts(
        [_clause("2.1.1", "电阻值应≤10Ω。")],
        [InspectionItem(standard_clause="2.1.1", standard_requirement="电阻值应<10Ω。")],
        task_id="task-ptr",
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "PTR_CLAUSE"
    assert finding.code == "PTR_CLAUSE_TEXT_MISMATCH"
    assert finding.expected == "电阻值应<=10Ω。"
    assert finding.actual == "电阻值应<10Ω。"
    assert finding.metadata["clause_number"] == "2.1.1"
    assert any(fragment.kind.value in {"delete", "insert", "replace"} for fragment in finding.diff_fragments)


def test_clause_text_compare_outputs_missing_finding() -> None:
    findings = compare_clause_texts(
        [_clause("2.1.9", "缺失条款应符合要求。")],
        [InspectionItem(standard_clause="2.1.1", standard_requirement="其他条款。")],
        task_id="task-ptr",
    )

    assert len(findings) == 1
    assert findings[0].code == "PTR_CLAUSE_MISSING"
    assert findings[0].missing_evidence[0].label == "报告标准要求"


def test_clause_text_compare_uses_parent_report_clause_as_evidence_instead_of_missing() -> None:
    findings = compare_clause_texts(
        [_clause("2.6.1", "软件功能应符合产品技术要求。")],
        [InspectionItem(standard_clause="2.6", standard_requirement="——", source_page=99)],
        task_id="task-ptr",
    )

    assert len(findings) == 1
    assert findings[0].code == "PTR_CLAUSE_TEXT_MISMATCH"
    assert findings[0].metadata["clause_number"] == "2.6.1"


def test_clause_text_compare_uses_grouped_report_item_instead_of_first_physical_row() -> None:
    findings = compare_clause_texts(
        [_clause("2.2.1", "心脏脉冲电场消融仪输出电压、电流应符合产品技术要求。")],
        [
            InspectionItem(
                sequence_raw="157",
                sequence=157,
                standard_clause="2.2",
                standard_requirement="2.2.1 心脏脉冲电场消融仪输出\n电压：3333V（峰值）",
                test_result="3375",
                result_values=["3375"],
                conclusion="符合",
                source_page=99,
                row_index_in_page=3,
            ),
            InspectionItem(
                sequence_raw="电流：57A（峰值）\n单位：A",
                item_name="59",
                standard_clause="/",
                source_page=99,
                row_index_in_page=4,
            ),
            InspectionItem(
                sequence_raw="续\n157",
                sequence=157,
                is_continuation=True,
                standard_clause="2.2",
                standard_requirement="2.2.5 脉冲衰减应在 10%内。",
                test_result="1%",
                result_values=["1%"],
                conclusion="符合",
                source_page=101,
                row_index_in_page=1,
            ),
        ],
        task_id="task-ptr",
    )

    assert findings == []


def test_ptr_group_for_clause_prefers_direct_scope_anchor_over_unrelated_text_hit() -> None:
    groups = build_ptr_report_item_groups(
        [
            InspectionItem(
                sequence_raw="65",
                sequence=65,
                standard_clause="9.2.2",
                item_name="俘获区域",
                standard_requirement="外部标准说明中引用 2.2.1 心脏脉冲电场消融仪输出。",
                test_result="符合要求",
                conclusion="符合",
                source_page=40,
                row_index_in_page=1,
            ),
            InspectionItem(
                sequence_raw="157",
                sequence=157,
                standard_clause="2.2",
                standard_requirement="2.2.1 心脏脉冲电场消融仪输出\n电压：3333V（峰值）",
                test_result="3375",
                result_values=["3375"],
                conclusion="符合",
                source_page=99,
                row_index_in_page=3,
            ),
            InspectionItem(
                sequence_raw="电流：57A（峰值）",
                item_name="59",
                standard_clause="/",
                source_page=99,
                row_index_in_page=4,
            ),
        ]
    )

    match = ptr_group_for_clause("2.2.1", groups)

    assert match is not None
    assert match.item_no == "157"


def test_ptr_group_for_clause_rejects_unrelated_parent_for_direct_software_clause() -> None:
    groups = build_ptr_report_item_groups(
        [
            InspectionItem(
                sequence_raw="14",
                sequence=14,
                standard_clause="5.5",
                item_name="供电电压、电流类型、供电方式和频率",
                standard_requirement="软件功能相关供电项目。",
                test_result="符合要求",
                conclusion="符合",
                source_page=12,
                row_index_in_page=1,
            ),
            InspectionItem(
                sequence_raw="159",
                sequence=159,
                standard_clause="2.6",
                item_name="软件功能",
                standard_requirement="软件功能应符合产品技术要求。",
                test_result="符合要求",
                conclusion="符合",
                source_page=99,
                row_index_in_page=7,
            ),
        ]
    )

    match = ptr_group_for_clause("2.6", groups)

    assert match is not None
    assert match.item_no == "159"


def test_clause_text_compare_downgrades_unrelated_direct_match_candidate_to_review() -> None:
    findings = compare_clause_texts(
        [_clause("2.2.1", "心脏脉冲电场消融仪输出电压、电流应符合产品技术要求。")],
        [
            InspectionItem(
                sequence_raw="65",
                sequence=65,
                standard_clause="9.2.2",
                item_name="俘获区域",
                standard_requirement="2.2.1 心脏脉冲电场消融仪输出电压、电流应符合产品技术要求。",
                test_result="符合要求",
                conclusion="符合",
                source_page=40,
                row_index_in_page=1,
            )
        ],
        task_id="task-ptr",
    )

    assert len(findings) == 1
    assert findings[0].severity == "warn"
    assert findings[0].code == "PTR_CLAUSE_INVALID_MATCH_CANDIDATE"
    assert findings[0].metadata["item_no"] == "65"
    assert findings[0].metadata["candidate_standard_clause"] == "9.2.2"
