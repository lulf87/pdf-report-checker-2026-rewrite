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
