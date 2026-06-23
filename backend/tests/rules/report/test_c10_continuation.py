from app.domain.finding import FindingSeverity
from app.domain.report import ReportDocument
from app.domain.result import CheckStatus
from app.rules.report.c10_continuation import check_c10_continuation, is_continuation_no
from app.rules.report.context import CheckContext

from .helpers import item


def _run(document: ReportDocument):
    return check_c10_continuation(document, CheckContext(task_id="task-c10"))


def _codes(result) -> list[str]:
    return [finding.code for finding in result.findings]


def test_is_continuation_no_recognizes_supported_forms() -> None:
    assert is_continuation_no("续5") == 5
    assert is_continuation_no("续 5") == 5
    assert is_continuation_no("续５") == 5
    assert is_continuation_no("5") is None
    assert is_continuation_no("续：5") is None


def test_c10_passes_when_cross_page_group_first_related_row_uses_continuation_marker() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(5, raw="续5", page=6, row=0, continued=True),
            item(None, raw="", page=6, row=1, name="续表子行"),
            item(6, raw="6", page=6, row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c10_reports_missing_marker_once_per_group_page_boundary() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(5, raw="5", page=6, row=0),
            item(None, raw="", page=6, row=1, name="续表子行 1"),
            item(None, raw="", page=6, row=2, name="续表子行 2"),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["CONTINUATION_MARK_ERROR_001"]
    finding = result.findings[0]
    assert finding.severity == FindingSeverity.ERROR
    assert finding.expected == "续5"
    assert finding.actual == "5"
    assert finding.metadata["boundary_key"] == "5:5->6"
    assert finding.metadata["item_no"] == "5"
    assert finding.metadata["previous_page"] == 5
    assert finding.metadata["current_page"] == 6
    assert finding.metadata["expected_marker"] == "续5"
    assert finding.metadata["actual_marker"] == "5"
    assert finding.metadata["first_related_row_index"] == 0
    assert finding.metadata["duplicate_suppressed_count"] == 2


def test_c10_reports_misplaced_marker_when_marker_is_second_related_row() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(None, raw="", page=6, row=0, name="续表子行"),
            item(5, raw="续5", page=6, row=1, continued=True),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["CONTINUATION_MARK_ERROR_002"]
    assert result.findings[0].expected == "续字只能出现在本页第一行"
    assert result.findings[0].actual == "续5"
    assert result.findings[0].metadata["boundary_key"] == "5:5->6"
    assert result.findings[0].metadata["first_related_row_index"] == 0
    assert result.findings[0].metadata["marker_row_index"] == 1
    assert result.findings[0].metadata["duplicate_suppressed_count"] == 1


def test_c10_reports_mismatch_when_first_row_marker_differs_from_previous_tail() -> None:
    document = ReportDocument(
        inspection_items=[
            item(3, raw="3", page=5, row=2),
            item(4, raw="续4", page=6, row=0, continued=True),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["CONTINUATION_MARK_MISMATCH"]
    assert result.findings[0].expected == "续3"
    assert result.findings[0].actual == "续4"
    assert result.findings[0].metadata["boundary_key"] == "3:5->6"
    assert result.findings[0].metadata["item_no"] == "3"
    assert result.findings[0].metadata["expected_marker"] == "续3"
    assert result.findings[0].metadata["actual_marker"] == "续4"


def test_c10_passes_when_new_page_starts_new_sequence_without_pending_continuation() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(6, raw="6", page=6, row=0),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c10_reports_same_page_continuation_marker_as_wrong_position() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=0),
            item(5, raw="续5", page=5, row=1, continued=True),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["CONTINUATION_MARK_ERROR_002"]
    assert result.findings[0].metadata["boundary_key"] == "5:5->5"
    assert result.findings[0].metadata["marker_row_index"] == 1


def test_c10_checks_each_boundary_once_for_three_page_group() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(5, raw="续5", page=6, row=0, continued=True),
            item(None, raw="", page=6, row=1, name="page 6 子行"),
            item(5, raw="5", page=7, row=0),
            item(None, raw="", page=7, row=1, name="page 7 子行"),
            item(6, raw="6", page=7, row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["CONTINUATION_MARK_ERROR_001"]
    assert result.findings[0].metadata["boundary_key"] == "5:6->7"
    assert result.findings[0].metadata["duplicate_suppressed_count"] == 1


def test_c10_passes_for_multiple_pages_with_correct_continuation_markers() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(5, raw="续5", page=6, row=0, continued=True),
            item(None, raw="", page=6, row=1, name="page 6 子行"),
            item(5, raw="续 5", page=7, row=0, continued=True),
            item(None, raw="", page=7, row=1, name="page 7 子行"),
            item(6, raw="6", page=7, row=2),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c10_blank_sequence_payload_rows_do_not_duplicate_boundary_finding() -> None:
    document = ReportDocument(
        inspection_items=[
            item(7, raw="7", page=10, row=4),
            item(None, raw="", page=11, row=0, name="子项目 A"),
            item(None, raw="", page=11, row=1, name="子项目 B"),
            item(None, raw="", page=11, row=2, name="子项目 C"),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["CONTINUATION_MARK_ERROR_001"]
    assert result.findings[0].metadata["boundary_key"] == "7:10->11"
    assert result.findings[0].metadata["duplicate_suppressed_count"] == 2


def test_c10_metadata_contains_boundary_group_and_source_rows() -> None:
    document = ReportDocument(
        inspection_items=[
            item(8, raw="8", page=12, row=3),
            item(8, raw="8", page=13, row=0),
            item(None, raw="", page=13, row=1, name="子项目"),
        ]
    )

    result = _run(document)

    finding = result.findings[0]
    assert finding.metadata["boundary_key"] == "8:12->13"
    assert finding.metadata["item_no"] == "8"
    assert finding.metadata["previous_page"] == 12
    assert finding.metadata["current_page"] == 13
    assert finding.metadata["expected_marker"] == "续8"
    assert finding.metadata["actual_marker"] == "8"
    assert finding.metadata["group_row_count"] == 3
    assert finding.metadata["group_pages"] == [12, 13]
    assert finding.metadata["source_rows"] == [
        {"source_index": 0, "page_number": 12, "row_index": 3, "sequence_raw": "8", "item_no": "8"},
        {"source_index": 1, "page_number": 13, "row_index": 0, "sequence_raw": "8", "item_no": "8"},
        {"source_index": 2, "page_number": 13, "row_index": 1, "sequence_raw": "", "item_no": "8"},
    ]


def test_c10_qw2025_2795_like_cross_page_mini_fixture_passes_when_first_row_is_continuation() -> None:
    document = ReportDocument(
        inspection_items=[
            item(3, raw="3", page=14, row=31, name="检验项目 3"),
            item(3, raw="续 3", page=15, row=0, continued=True, name="检验项目 3 续"),
            item(None, raw="", page=15, row=1, name="a) 子项目"),
            item(None, raw="", page=15, row=2, name="b) 子项目"),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c10_qw2025_2795_like_cross_page_mini_fixture_reports_one_missing_marker() -> None:
    document = ReportDocument(
        inspection_items=[
            item(3, raw="3", page=14, row=31, name="检验项目 3"),
            item(3, raw="3", page=15, row=0, name="检验项目 3 续"),
            item(None, raw="", page=15, row=1, name="a) 子项目"),
            item(None, raw="", page=15, row=2, name="b) 子项目"),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["CONTINUATION_MARK_ERROR_001"]
    assert result.findings[0].metadata["boundary_key"] == "3:14->15"
    assert result.findings[0].metadata["duplicate_suppressed_count"] == 2


def test_c10_reviews_when_page_or_row_context_is_missing() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(5, raw="续5", page=6, row=0, continued=True),
            item(6, raw="6", page=7, row=0),
        ]
    )
    document.inspection_items[1].source_page = None
    document.inspection_items[2].row_index_in_page = None

    result = _run(document)

    assert result.status == CheckStatus.REVIEW
    assert _codes(result) == ["CONTINUATION_CONTEXT_MISSING"]
    finding = result.findings[0]
    assert finding.severity == FindingSeverity.WARN
    assert finding.metadata["missing_context_rows"] == [1, 2]
    assert result.metadata["boundary_uncertain"] is True
