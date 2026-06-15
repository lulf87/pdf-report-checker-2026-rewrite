from app.domain.pdf import ParsedPdf, PdfPage
from app.domain.report import ReportDocument
from app.domain.result import CheckStatus
from app.rules.report.c11_page_number import check_c11_page_number, parse_page_number_text
from app.rules.report.context import CheckContext

from .helpers import page_number


def _codes(document: ReportDocument) -> set[str]:
    result = check_c11_page_number(document, CheckContext(task_id="task-c11"))
    return {finding.code for finding in result.findings}


def test_parse_page_number_text_supports_report_formats() -> None:
    assert parse_page_number_text("共5页第1页") == (1, 5)
    assert parse_page_number_text("共 5 页 第 1 页") == (1, 5)
    assert parse_page_number_text("页眉 共005页 第001页") == (1, 5)
    assert parse_page_number_text("第1页/共5页") == (1, 5)
    assert parse_page_number_text("Page 1 of 5") == (1, 5)
    assert parse_page_number_text("1/5") == (1, 5)
    assert parse_page_number_text("页码不可识别") == (None, None)


def test_passes_for_continuous_internal_pages_from_physical_third_page() -> None:
    document = ReportDocument(
        page_numbers=[
            page_number(3, 1, 5),
            page_number(4, 2, 5),
            page_number(5, 3, 5),
            page_number(6, 4, 5),
            page_number(7, 5, 5),
        ],
        page_map={"third_page": 3},
    )

    result = check_c11_page_number(document, CheckContext(task_id="task-c11"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["parsed_page_numbers"] == [
        {"pdf_page_number": 3, "current_page": 1, "total_pages": 5, "raw_text": "共 5 页 第 1 页"},
        {"pdf_page_number": 4, "current_page": 2, "total_pages": 5, "raw_text": "共 5 页 第 2 页"},
        {"pdf_page_number": 5, "current_page": 3, "total_pages": 5, "raw_text": "共 5 页 第 3 页"},
        {"pdf_page_number": 6, "current_page": 4, "total_pages": 5, "raw_text": "共 5 页 第 4 页"},
        {"pdf_page_number": 7, "current_page": 5, "total_pages": 5, "raw_text": "共 5 页 第 5 页"},
    ]


def test_ignores_page_number_evidence_before_physical_third_page() -> None:
    document = ReportDocument(
        page_numbers=[
            page_number(1, 99, 99),
            page_number(2, 1, 1),
            page_number(3, 1, 3),
            page_number(4, 2, 3),
            page_number(5, 3, 3),
        ],
        page_map={"third_page": 3},
    )

    result = check_c11_page_number(document, CheckContext(task_id="task-c11"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_reports_gap_when_internal_y_skips_a_page() -> None:
    document = ReportDocument(
        page_numbers=[
            page_number(3, 1, 5),
            page_number(4, 2, 5),
            page_number(5, 4, 5),
        ],
        page_map={"third_page": 3},
    )

    result = check_c11_page_number(document, CheckContext(task_id="task-c11"))

    assert result.status == CheckStatus.FAIL
    assert [finding.code for finding in result.findings] == ["PAGE_NUMBER_ERROR_001", "PAGE_NUMBER_ERROR_002"]
    gap = result.findings[0]
    assert gap.expected == [3]
    assert gap.actual == [1, 2, 4]
    assert gap.metadata["missing_y"] == [3]


def test_reports_duplicate_internal_y() -> None:
    document = ReportDocument(
        page_numbers=[
            page_number(3, 1, 4),
            page_number(4, 2, 4),
            page_number(5, 2, 4),
            page_number(6, 3, 4),
        ],
        page_map={"third_page": 3},
    )

    result = check_c11_page_number(document, CheckContext(task_id="task-c11"))

    assert result.status == CheckStatus.FAIL
    duplicate = next(finding for finding in result.findings if finding.code == "PAGE_NUMBER_DUPLICATED")
    assert duplicate.actual == [1, 2, 2, 3]
    assert duplicate.metadata["duplicated_y"] == [2]


def test_reports_final_page_y_not_equal_to_total_pages() -> None:
    document = ReportDocument(
        page_numbers=[
            page_number(3, 1, 5),
            page_number(4, 2, 5),
            page_number(5, 3, 5),
            page_number(6, 4, 5),
        ],
        page_map={"third_page": 3},
    )

    assert "PAGE_NUMBER_ERROR_002" in _codes(document)


def test_reports_inconsistent_total_pages() -> None:
    document = ReportDocument(
        page_numbers=[
            page_number(3, 1, 5),
            page_number(4, 2, 6),
            page_number(5, 3, 5),
            page_number(6, 4, 5),
            page_number(7, 5, 5),
        ],
        page_map={"third_page": 3},
    )

    result = check_c11_page_number(document, CheckContext(task_id="task-c11"))

    total = next(finding for finding in result.findings if finding.code == "PAGE_NUMBER_ERROR_003")
    assert total.expected == "所有页 XXX 一致"
    assert total.actual == [5, 6]
    assert total.metadata["total_values"] == [5, 6]


def test_reports_missing_page_number_on_third_page() -> None:
    document = ReportDocument(
        page_numbers=[
            page_number(3, None, None),
            page_number(4, 1, 2),
            page_number(5, 2, 2),
        ],
        page_map={"third_page": 3},
    )

    assert "PAGE_NUMBER_MISSING" in _codes(document)


def test_reports_unparseable_page_number_text() -> None:
    document = ReportDocument(
        page_numbers=[
            page_number(3, None, None, raw="页码：共五页 第壹页"),
            page_number(4, 1, 1),
        ],
        page_map={"third_page": 3},
    )

    assert "PAGE_NUMBER_PARSE_FAILED" in _codes(document)


def test_can_parse_from_parsed_pdf_text_without_opening_pdf() -> None:
    parsed_pdf = ParsedPdf(
        file_id="report-fixture",
        file_name="report.pdf",
        page_count=5,
        pages=[
            PdfPage(page_number=1, text="封面 共99页第99页"),
            PdfPage(page_number=2, text="注意事项 共1页第1页"),
            PdfPage(page_number=3, text="检验报告首页\n共3页第1页\n正文"),
            PdfPage(page_number=4, text="共3页第2页\n样品描述"),
            PdfPage(page_number=5, text="共3页第3页\n照片页"),
        ],
    )
    document = ReportDocument(parsed_pdf=parsed_pdf, page_map={"third_page": 3})

    result = check_c11_page_number(document, CheckContext(task_id="task-c11"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_reports_missing_page_number_when_parsed_pdf_page_has_no_page_number_text() -> None:
    parsed_pdf = ParsedPdf(
        file_id="report-fixture",
        file_name="report.pdf",
        page_count=4,
        pages=[
            PdfPage(page_number=1, text="封面"),
            PdfPage(page_number=2, text="注意事项"),
            PdfPage(page_number=3, text="检验报告首页正文"),
            PdfPage(page_number=4, text="共1页第1页"),
        ],
    )
    document = ReportDocument(parsed_pdf=parsed_pdf, page_map={"third_page": 3})

    assert "PAGE_NUMBER_MISSING" in _codes(document)
