from app.domain.common import Location, SourceType
from app.domain.pdf import ParsedPdf, PdfPage
from app.domain.report import ReportDocument, ReportField, ThirdPageInfo
from app.infrastructure.report.inspection_scope_extractor import ReportInspectionScopeExtractor


def test_extracts_declared_scope_items_exclusions_and_ranges_from_report_document() -> None:
    scope_field = ReportField(
        name="检验项目",
        value="2.2、2.5、2.6（除生物相容性、电磁兼容性）",
        location=Location(source_type=SourceType.REPORT, page_number=3),
        metadata={"items": ["2.2", "2.5", "2.6（除生物相容性、电磁兼容性）"]},
    )
    report = ReportDocument(
        parsed_pdf=ParsedPdf(
            file_id="report-1539-like",
            file_name="report.pdf",
            page_count=5,
            pages=[
                PdfPage(page_number=3, text="检验项目：2.2、2.5、2.6（除生物相容性、电磁兼容性）"),
                PdfPage(
                    page_number=5,
                    text=(
                        "型号规格或其他说明\n"
                        "序号 1～序号 118 为 GB 9706.1-2020 标准的内容\n"
                        "序号 119～156 为 GB9706.202-2021 标准的内容"
                    ),
                ),
            ],
        ),
        third_page=ThirdPageInfo(fields=[scope_field]),
        fields=[scope_field],
    )

    scope = ReportInspectionScopeExtractor().extract(report)

    assert scope.declared_scope_items == ["2.2", "2.5", "2.6"]
    assert scope.declared_scope_ranges == []
    assert scope.excluded_topics == ["生物相容性", "电磁兼容性"]
    assert scope.source_page == 3
    assert scope.source_text == "2.2、2.5、2.6（除生物相容性、电磁兼容性）"
    assert [item.model_dump(mode="json") for item in scope.external_standard_ranges] == [
        {
            "start_item_no": "1",
            "end_item_no": "118",
            "standard": "GB 9706.1-2020",
            "source_page": 5,
            "source_text": "序号 1～序号 118 为 GB 9706.1-2020 标准的内容",
        },
        {
            "start_item_no": "119",
            "end_item_no": "156",
            "standard": "GB9706.202-2021",
            "source_page": 5,
            "source_text": "序号 119～156 为 GB9706.202-2021 标准的内容",
        },
    ]
    assert scope.ptr_direct_content_starts_after == "156"


def test_extracts_declared_scope_ranges_with_supported_range_separators() -> None:
    values = ["2.1～2.14", "2.1-2.14", "2.1至2.14"]

    for value in values:
        scope_field = ReportField(
            name="检验项目",
            value=value,
            location=Location(source_type=SourceType.REPORT, page_number=3),
        )
        report = ReportDocument(
            third_page=ThirdPageInfo(fields=[scope_field]),
            fields=[scope_field],
        )

        scope = ReportInspectionScopeExtractor().extract(report)

        assert [item.model_dump(mode="json") for item in scope.declared_scope_ranges] == [
            {"start": "2.1", "end": "2.14", "source_text": value}
        ]


def test_extracts_external_standard_ranges_when_standard_name_is_split_across_lines() -> None:
    scope_field = ReportField(
        name="检验项目",
        value="2.2、2.5、2.6（除生物相容性、电磁兼容性）",
        location=Location(source_type=SourceType.REPORT, page_number=3),
    )
    report = ReportDocument(
        parsed_pdf=ParsedPdf(
            file_id="report-1539-cross-line",
            file_name="report.pdf",
            page_count=5,
            pages=[
                PdfPage(page_number=3, text="检验项目：2.2、2.5、2.6（除生物相容性、电磁兼容性）"),
                PdfPage(
                    page_number=5,
                    text=(
                        "型号规格或其他说明\n"
                        "序号 1～序号 118 为 GB 9706.1-2020\n"
                        "序号 119～156 为 GB 9706.\n"
                        "202-2021"
                    ),
                ),
            ],
        ),
        third_page=ThirdPageInfo(fields=[scope_field]),
        fields=[scope_field],
    )

    scope = ReportInspectionScopeExtractor().extract(report)

    assert [item.model_dump(mode="json") for item in scope.external_standard_ranges] == [
        {
            "start_item_no": "1",
            "end_item_no": "118",
            "standard": "GB 9706.1-2020",
            "source_page": 5,
            "source_text": "序号 1～序号 118 为 GB 9706.1-2020",
        },
        {
            "start_item_no": "119",
            "end_item_no": "156",
            "standard": "GB 9706.202-2021",
            "source_page": 5,
            "source_text": "序号 119～156 为 GB 9706.202-2021",
        },
    ]
    assert scope.ptr_direct_content_starts_after == "156"
