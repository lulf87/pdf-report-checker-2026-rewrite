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


def test_c10_passes_when_cross_page_repeat_uses_continuation_marker_on_first_row() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(5, raw="续5", page=6, row=0, continued=True),
            item(6, raw="6", page=6, row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c10_reports_missing_marker_when_new_page_first_row_continues_previous_sequence() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(5, raw="5", page=6, row=0),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["CONTINUATION_MARK_ERROR_001"]
    finding = result.findings[0]
    assert finding.severity == FindingSeverity.ERROR
    assert finding.expected == "续5"
    assert finding.actual == "5"
    assert finding.metadata["previous_page_last_item_no"] == 5
    assert finding.metadata["current_page_first_item_no"] == 5
    assert finding.metadata["is_first_row_on_page"] is True


def test_c10_reports_wrong_position_when_continuation_marker_is_on_second_row() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(6, raw="6", page=6, row=0),
            item(5, raw="续5", page=6, row=1, continued=True),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["CONTINUATION_MARK_ERROR_002"]
    assert result.findings[0].expected == "续字只能出现在本页第一行"
    assert result.findings[0].actual == "续5"
    assert result.findings[0].metadata["is_first_row_on_page"] is False


def test_c10_reports_mismatch_when_first_row_continuation_number_differs_from_previous_tail() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(6, raw="续6", page=6, row=0, continued=True),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["CONTINUATION_MARK_MISMATCH"]
    assert result.findings[0].expected == "续5"
    assert result.findings[0].actual == "续6"
    assert result.findings[0].metadata["previous_page_last_item_no"] == 5
    assert result.findings[0].metadata["current_page_first_item_no"] == 6


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


def test_c10_passes_for_multiple_pages_with_correct_continuation_markers() -> None:
    document = ReportDocument(
        inspection_items=[
            item(5, raw="5", page=5, row=2),
            item(5, raw="续5", page=6, row=0, continued=True),
            item(5, raw="续 5", page=7, row=0, continued=True),
            item(6, raw="6", page=7, row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


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
