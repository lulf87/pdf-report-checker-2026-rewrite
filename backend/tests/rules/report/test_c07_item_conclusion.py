from app.domain.finding import FindingSeverity
from app.domain.report import ReportDocument
from app.domain.result import CheckStatus
from app.rules.report.c07_item_conclusion import (
    check_c07_item_conclusion,
    infer_expected_conclusion,
    normalize_item_no,
)
from app.rules.report.context import CheckContext

from .helpers import item


def _run(document: ReportDocument):
    return check_c07_item_conclusion(document, CheckContext(task_id="task-c07"))


def _one_finding(document: ReportDocument):
    result = _run(document)
    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    return result.findings[0]


def test_normalize_item_no_groups_continuation_marker_with_original_sequence() -> None:
    assert normalize_item_no("续5") == "5"
    assert normalize_item_no("续 5") == "5"
    assert normalize_item_no(5) == "5"
    assert normalize_item_no("") is None


def test_infer_expected_conclusion_uses_c07_priority_order() -> None:
    assert infer_expected_conclusion(["符合要求", "——"]).expected == "符合"
    assert infer_expected_conclusion(["符合要求", "不符合要求"]).expected == "不符合"
    assert infer_expected_conclusion(["——", "——"]).expected == "/"
    assert infer_expected_conclusion(["/", "/"]).expected == "/"
    assert infer_expected_conclusion(["", ""]).expected == "/"
    assert infer_expected_conclusion(["100", "——"]).expected == "符合"
    assert infer_expected_conclusion(["69%", "0.08", "＜0.01", "IPX0", "CF 型"]).expected == "符合"


def test_c07_passes_when_conforming_and_placeholder_results_expect_conforming() -> None:
    document = ReportDocument(
        inspection_items=[
            item(1, result="符合要求", conclusion="符合", row=0),
            item(1, result="——", conclusion="", row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["groups"][0]["expected_conclusion"] == "符合"
    assert result.metadata["groups"][0]["decision_reason"] == "has_conforming_or_non_empty_result"


def test_c07_passes_when_any_result_is_nonconforming_and_conclusion_is_nonconforming() -> None:
    document = ReportDocument(
        inspection_items=[
            item(2, result="符合要求", conclusion="不符合", row=0),
            item(2, result="不符合要求", conclusion="", row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["groups"][0]["expected_conclusion"] == "不符合"


def test_c07_passes_when_all_results_are_dash_placeholders() -> None:
    document = ReportDocument(
        inspection_items=[
            item(3, result="——", conclusion="/", row=0),
            item(3, result="——", conclusion="", row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["groups"][0]["expected_conclusion"] == "/"


def test_c07_passes_when_all_results_are_slash_placeholders() -> None:
    document = ReportDocument(
        inspection_items=[
            item(4, result="/", conclusion="/", row=0),
            item(4, result="/", conclusion="", row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["groups"][0]["expected_conclusion"] == "/"


def test_c07_passes_when_all_results_are_blank_and_conclusion_is_slash() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, result="", conclusion="/", row=0),
            item(5, result="   ", conclusion="", row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["groups"][0]["expected_conclusion"] == "/"
    assert result.metadata["groups"][0]["decision_reason"] == "all_placeholders_or_blank"


def test_c07_passes_when_numeric_result_and_placeholder_expect_conforming() -> None:
    document = ReportDocument(
        inspection_items=[
            item(6, result="100", conclusion="符合", row=0),
            item(6, result="——", conclusion="", row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["groups"][0]["expected_conclusion"] == "符合"


def test_c07_reports_error_when_expected_slash_but_actual_is_conforming() -> None:
    finding = _one_finding(
        ReportDocument(
            inspection_items=[
                item(7, result="——", conclusion="符合", row=0),
                item(7, result="/", conclusion="", row=1),
            ]
        )
    )

    assert finding.code == "CONCLUSION_MISMATCH_001"
    assert finding.severity == FindingSeverity.ERROR
    assert finding.expected == "/"
    assert finding.actual == "符合"
    assert finding.metadata["item_no"] == "7"
    assert finding.metadata["normalized_item_no"] == "7"
    assert finding.metadata["result_values"] == ["——", "/"]


def test_c07_reports_error_when_expected_conforming_but_actual_is_slash() -> None:
    finding = _one_finding(ReportDocument(inspection_items=[item(8, result="100", conclusion="/")]))

    assert finding.code == "CONCLUSION_MISMATCH_002"
    assert finding.severity == FindingSeverity.ERROR
    assert finding.expected == "符合"
    assert finding.actual == "/"
    assert finding.metadata["decision_reason"] == "has_conforming_or_non_empty_result"


def test_c07_reports_one_group_level_finding_for_conforming_rows_with_slash_conclusion() -> None:
    document = ReportDocument(
        inspection_items=[
            item(8, result="符合要求", conclusion="/", page=14, row=0),
            item(None, raw="", result="符合要求", conclusion="", page=14, row=1),
            item(8, raw="续 8", continued=True, result="符合要求", conclusion="", page=15, row=0),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.expected == "符合"
    assert finding.actual == "/"
    assert finding.metadata["item_no"] == "8"
    assert finding.metadata["effective_test_results"] == ["符合要求", "符合要求", "符合要求"]
    assert finding.metadata["group_row_count"] == 3
    assert finding.metadata["pages"] == [14, 15]
    assert finding.metadata["continuation_markers"][0]["raw_text"] == "续 8"
    assert finding.metadata["suppressed_physical_row_count"] == 2
    assert finding.metadata["result_summary"]["conforming_or_non_empty_count"] == 3
    assert finding.metadata["reasoning_basis"] == "has_conforming_or_non_empty_result"


def test_c07_reports_error_when_expected_nonconforming_but_actual_is_conforming() -> None:
    finding = _one_finding(ReportDocument(inspection_items=[item(9, result="不符合要求", conclusion="符合")]))

    assert finding.code == "CONCLUSION_MISMATCH_003"
    assert finding.severity == FindingSeverity.ERROR
    assert finding.expected == "不符合"
    assert finding.actual == "符合"
    assert finding.metadata["decision_reason"] == "has_nonconforming_result"


def test_c07_groups_same_sequence_multiple_rows_before_decision() -> None:
    document = ReportDocument(
        inspection_items=[
            item(10, result="——", conclusion="符合", row=0),
            item(10, result="符合要求", conclusion="", row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["groups"][0]["result_values"] == ["——", "符合要求"]


def test_c07_uses_group_builder_so_requirement_text_does_not_become_item_no() -> None:
    document = ReportDocument(
        inspection_items=[
            item(15, result="符合要求", conclusion="符合", row=0),
            item(
                None,
                raw="当外壳的分类为 IPX0 时，保持 ME 设备和其部件在潮湿箱里 48h。",
                result="符合要求",
                conclusion="",
                row=1,
            ),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert [group["item_no"] for group in result.metadata["groups"]] == ["15"]
    assert result.metadata["groups"][0]["effective_test_results"] == ["符合要求", "符合要求"]


def test_c07_groups_continuation_sequence_with_original_sequence() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, result="——", conclusion="不符合", row=0),
            item(5, raw="续5", continued=True, result="不符合要求", conclusion="", row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["groups"][0]["item_no"] == "5"
    assert result.metadata["groups"][0]["normalized_item_no"] == "5"
    assert result.metadata["groups"][0]["expected_conclusion"] == "不符合"


def test_c07_blank_test_result_does_not_default_to_nonconforming() -> None:
    finding = _one_finding(ReportDocument(inspection_items=[item(11, result="", conclusion="不符合")]))

    assert finding.code == "CONCLUSION_MISMATCH_001"
    assert finding.expected == "/"
    assert finding.actual == "不符合"
    assert finding.metadata["decision_reason"] == "all_placeholders_or_blank"


def test_c07_missing_conclusion_is_reported_as_conclusion_mismatch() -> None:
    finding = _one_finding(ReportDocument(inspection_items=[item(12, result="符合要求", conclusion="")]))

    assert finding.code == "CONCLUSION_MISMATCH_002"
    assert finding.expected == "符合"
    assert finding.actual == ""
    assert "单项结论" in finding.message


def test_c07_item_94_recovered_result_tokens_prevent_all_placeholder_error() -> None:
    document = ReportDocument(
        inspection_items=[
            item(94, raw="94", result="——", conclusion="符合", remark="/", page=72, row=10),
            item(94, raw="续 94", result="——", conclusion="", remark="/", continued=True, page=73, row=0),
            item(None, raw="12.4.2", result="", conclusion="", remark="", page=73, row=1).model_copy(
                update={"metadata": {"row_text": "12.4.2 控制器保护，检验结果：符合要求"}}
            ),
            item(None, raw="12.4.4", result="", conclusion="", remark="", page=73, row=2).model_copy(
                update={"metadata": {"row_text": "12.4.4 防止误动作 检验结果 符合要求"}}
            ),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    group = result.metadata["groups"][0]
    assert group["item_no"] == "94"
    assert group["original_effective_test_results"] == ["——", "——"]
    assert group["recovered_result_tokens"] == ["符合要求", "符合要求"]
    assert group["expected_conclusion"] == "符合"
    assert group["decision_reason"] == "has_conforming_or_non_empty_result"


def test_c07_recovered_result_tokens_prevent_all_placeholder_error_for_known_residual_items() -> None:
    for item_no in (27, 33, 41, 72, 121, 142, 149):
        document = ReportDocument(
            inspection_items=[
                item(item_no, raw=str(item_no), result="——", conclusion="符合", remark="/", page=40, row=1),
                item(None, raw="12.4.2", result="", conclusion="", remark="", page=40, row=2).model_copy(
                    update={"metadata": {"row_text": "12.4.2 相关子条款 检验结果：符合要求"}}
                ),
            ]
        )

        result = _run(document)

        assert result.status == CheckStatus.PASS
        assert result.findings == []
        assert result.metadata["groups"][0]["item_no"] == str(item_no)
        assert result.metadata["groups"][0]["recovered_result_tokens"] == ["符合要求"]


def test_c07_uncertain_result_token_recovery_outputs_review_needed_warn_not_error() -> None:
    document = ReportDocument(
        inspection_items=[
            item(41, raw="41", result="——", conclusion="符合", remark="/", page=30, row=5),
            item(None, raw="12.4.2", result="", conclusion="", remark="", page=30, row=6).model_copy(
                update={"metadata": {"row_text": "12.4.2 应符合本标准要求"}}
            ),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.REVIEW
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == FindingSeverity.WARN
    assert finding.code == "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN"
    assert finding.metadata["needs_codex_review"] is True
    assert finding.metadata["result_token_recovery_confidence"] == "uncertain"


def test_c07_item_151_all_dash_actual_conforming_still_remains_candidate() -> None:
    finding = _one_finding(
        ReportDocument(
            inspection_items=[
                item(151, raw="151", result="——", conclusion="符合", remark="/", page=80, row=4),
                item(151, raw="续 151", result="——", conclusion="", remark="/", continued=True, page=81, row=0),
            ]
        )
    )

    assert finding.code == "CONCLUSION_MISMATCH_001"
    assert finding.severity == FindingSeverity.ERROR
    assert finding.expected == "/"
    assert finding.actual == "符合"


def test_c07_complex_leakage_current_matrix_outputs_review_needed_warn_not_error() -> None:
    rows = [
        item(59, raw="59", result="符合要求", conclusion="/", remark="/", page=42, row=0).model_copy(
            update={"standard_clause": "201.8.7", "standard_requirement": "漏电流矩阵表应符合限值"}
        )
    ]
    matrix_values = [
        ("正常状态下≤0.05mA", "＜0.01"),
        ("单一故障状态≤0.5mA", "＜0.02"),
        ("直流漏电流", "符合"),
        ("交流漏电流", "符合"),
        ("患者辅助电流", "正常状态下≤0.05mA"),
        ("外壳漏电流", "单一故障状态≤0.5mA"),
        ("接地漏电流", "＜0.01"),
        ("mA 测量值", "＜0.01"),
        ("μA 测量值", "＜10"),
        ("电流限值", "符合"),
        ("漏电流复核", "符合"),
    ]
    for offset, (requirement, result_value) in enumerate(matrix_values, start=1):
        rows.append(
            item(
                None,
                raw="",
                result=result_value,
                conclusion="",
                remark="",
                page=42 + min(3, offset // 3),
                row=offset,
                name="漏电流矩阵",
            ).model_copy(
                update={
                    "standard_clause": "201.8.7",
                    "standard_requirement": requirement,
                    "metadata": {"row_text": f"漏电流矩阵 {requirement} 检验结果 {result_value}"},
                }
            )
        )

    result = _run(ReportDocument(inspection_items=rows))

    assert result.status == CheckStatus.REVIEW
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX"
    assert finding.severity == FindingSeverity.WARN
    assert finding.metadata["complex_matrix_table"] is True
    assert "漏电流" in finding.metadata["complex_matrix_reason"]
    assert finding.metadata["needs_codex_review"] is True
