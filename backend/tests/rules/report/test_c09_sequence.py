from app.domain.finding import FindingSeverity
from app.domain.report import ReportDocument
from app.domain.result import CheckStatus
from app.rules.report.c09_sequence import check_c09_sequence, parse_item_no
from app.rules.report.context import CheckContext

from .helpers import item


def _run(document: ReportDocument):
    return check_c09_sequence(document, CheckContext(task_id="task-c09"))


def _codes(result) -> list[str]:
    return [finding.code for finding in result.findings]


def test_parse_item_no_recognizes_plain_and_continuation_numbers() -> None:
    plain = parse_item_no("12")
    continuation = parse_item_no("续12")
    spaced_continuation = parse_item_no("续 12")
    fullwidth = parse_item_no("１２")

    assert plain.number == 12
    assert plain.is_continuation is False
    assert fullwidth.number == 12
    assert fullwidth.is_continuation is False
    assert continuation.number == 12
    assert continuation.is_continuation is True
    assert spaced_continuation.number == 12
    assert spaced_continuation.is_continuation is True
    assert parse_item_no("").number is None
    assert parse_item_no("ABC").number is None


def test_c09_passes_for_sequence_1_2_3() -> None:
    result = _run(ReportDocument(inspection_items=[item(1), item(2), item(3)]))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["actual_sequence"] == [1, 2, 3]


def test_c09_errors_when_sequence_does_not_start_from_one() -> None:
    result = _run(ReportDocument(inspection_items=[item(2), item(3)]))

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["SERIAL_NUMBER_NOT_START_FROM_ONE"]
    finding = result.findings[0]
    assert finding.severity == FindingSeverity.ERROR
    assert finding.expected == 1
    assert finding.actual == 2
    assert finding.metadata["normalized_sequence"] == 2


def test_c09_errors_when_sequence_has_gap() -> None:
    result = _run(ReportDocument(inspection_items=[item(1), item(3)]))

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["SERIAL_NUMBER_ERROR_001"]
    assert result.findings[0].expected == [1, 2, 3]
    assert result.findings[0].actual == [1, 3]
    assert result.findings[0].metadata["missing_numbers"] == [2]


def test_c09_errors_when_plain_sequence_is_duplicated() -> None:
    result = _run(ReportDocument(inspection_items=[item(1), item(2), item(2), item(3)]))

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["SERIAL_NUMBER_DUPLICATED"]
    assert result.findings[0].metadata["duplicated_numbers"] == [2]
    assert result.findings[0].metadata["normalized_sequence"] == 2


def test_c09_errors_when_sequence_cell_is_blank() -> None:
    result = _run(ReportDocument(inspection_items=[item(1, row=0), item(None, raw="", row=1), item(2, row=2)]))

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["SERIAL_NUMBER_ERROR_002"]
    finding = result.findings[0]
    assert finding.metadata["blank_rows"] == [1]
    assert finding.metadata["row_index"] == 1
    assert finding.location.row_index == 1


def test_c09_does_not_count_continuation_as_duplicate() -> None:
    document = ReportDocument(
        inspection_items=[
            item(1),
            item(2),
            item(2, raw="续2", continued=True),
            item(3),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["actual_sequence"] == [1, 2, 3]
    assert result.metadata["continuation_numbers"] == [2]


def test_c09_allows_continuation_position_to_be_checked_by_c10() -> None:
    document = ReportDocument(
        inspection_items=[
            item(1),
            item(1, raw="续1", continued=True),
            item(2),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["actual_sequence"] == [1, 2]


def test_c09_errors_when_continuation_references_missing_sequence() -> None:
    document = ReportDocument(
        inspection_items=[
            item(1),
            item(2),
            item(4, raw="续4", continued=True),
            item(3),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["SERIAL_NUMBER_ERROR_001"]
    assert result.findings[0].metadata["invalid_continuation_numbers"] == [4]
    assert result.findings[0].metadata["missing_numbers"] == []


def test_c09_passes_for_continuous_sequence_across_pages() -> None:
    document = ReportDocument(
        inspection_items=[
            item(1, page=5, row=0),
            item(2, page=5, row=1),
            item(3, page=6, row=0),
            item(4, page=6, row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["actual_sequence"] == [1, 2, 3, 4]


def test_c09_errors_for_gap_across_pages() -> None:
    document = ReportDocument(
        inspection_items=[
            item(1, page=5, row=0),
            item(2, page=5, row=1),
            item(4, page=6, row=0),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert _codes(result) == ["SERIAL_NUMBER_ERROR_001"]
    assert result.findings[0].metadata["missing_numbers"] == [3]
