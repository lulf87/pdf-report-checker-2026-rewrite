from app.domain.pdf import ParsedPdf, PdfPage
from app.infrastructure.report.page_locator import PageLocator, PageRole


def _parsed_pdf(*pages: PdfPage) -> ParsedPdf:
    return ParsedPdf(
        file_id="report-fixture",
        file_name="report.pdf",
        page_count=len(pages),
        pages=list(pages),
    )


def test_locates_first_and_third_page_without_rule_judgement() -> None:
    parsed = _parsed_pdf(
        PdfPage(page_number=1, text="检 验 报 告\n委托方\nABC"),
        PdfPage(page_number=2, text="目录"),
        PdfPage(page_number=3, text="检 验 报 告 首 页\n样品名称\n导管"),
    )

    page_map = PageLocator().locate(parsed)

    assert page_map.first_page is not None
    assert page_map.first_page.role == PageRole.FIRST_PAGE
    assert page_map.first_page.page_number == 1
    assert page_map.third_page is not None
    assert page_map.third_page.role == PageRole.THIRD_PAGE
    assert page_map.third_page.page_number == 3
    assert page_map.third_page.reason == "title_match"
    assert page_map.diagnostics == []


def test_locates_photo_label_and_sample_description_pages() -> None:
    parsed = _parsed_pdf(
        PdfPage(page_number=1, text="封面"),
        PdfPage(page_number=2, text="空白"),
        PdfPage(page_number=3, text="检验报告首页"),
        PdfPage(page_number=4, text="样品描述\n部件名称\n导管"),
        PdfPage(
            page_number=5,
            text="检验报告照片页\n照片和说明\n№2 导管 中文标签样张",
        ),
        PdfPage(page_number=6, text="检品外观照片"),
    )

    page_map = PageLocator().locate(parsed)

    assert [page.page_number for page in page_map.sample_description_pages] == [4]
    assert [page.page_number for page in page_map.photo_pages] == [5, 6]
    assert [page.page_number for page in page_map.label_pages] == [5]
    assert all(page.evidence for page in page_map.photo_pages + page_map.label_pages)


def test_missing_optional_pages_are_reported_as_diagnostics_not_findings() -> None:
    parsed = _parsed_pdf(PdfPage(page_number=1, text="封面"))

    page_map = PageLocator().locate(parsed)

    assert page_map.first_page is not None
    assert page_map.third_page is None
    assert page_map.photo_pages == []
    assert page_map.label_pages == []
    assert "third page not found" in page_map.diagnostics
