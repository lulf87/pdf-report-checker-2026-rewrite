from app.domain.pdf import ParsedPdf, PdfPage, PdfTable
from app.infrastructure.report.inspection_table_extractor import InspectionTableExtractor


HEADERS = ["序号", "检验项目", "标准条款", "标准要求", "检验结果", "单项结论", "备注"]


def _parsed_pdf(*pages: PdfPage) -> ParsedPdf:
    return ParsedPdf(
        file_id="inspection-fixture",
        file_name="report.pdf",
        page_count=len(pages),
        pages=list(pages),
        tables=[table for page in pages for table in page.tables],
    )


def _table(page_number: int, rows: list[list[str]], *, metadata: dict | None = None) -> PdfTable:
    return PdfTable(
        table_id=f"table-{page_number}",
        page_numbers=[page_number],
        columns=HEADERS,
        rows=rows,
        metadata=metadata or {},
    )


def test_extracts_inspection_items_with_page_row_col_evidence() -> None:
    parsed = _parsed_pdf(
        PdfPage(
            page_number=4,
            text="检验项目表",
            tables=[
                _table(
                    4,
                    [
                        HEADERS,
                        ["1", "导管外观", "2.1.1", "应完整", "符合要求", "符合", "/"],
                        ["2", "尺寸", "2.1.2", "应符合要求", "符合要求", "符合", "正常"],
                    ],
                )
            ],
        )
    )

    table = InspectionTableExtractor().extract_table(parsed)

    assert table is not None
    assert table.header_fields == HEADERS
    assert table.page_span == (4, 4)
    assert len(table.items) == 2

    first = table.items[0]
    assert first.sequence_raw == "1"
    assert first.sequence == 1
    assert first.item_name == "导管外观"
    assert first.standard_clause == "2.1.1"
    assert first.standard_requirement == "应完整"
    assert first.test_result == "符合要求"
    assert first.conclusion == "符合"
    assert first.remark == "/"
    assert first.source_page == 4
    assert first.row_index_in_page == 1
    assert first.metadata["item_no"] == "1"
    assert first.metadata["single_conclusion"] == "符合"
    assert any(
        evidence.location
        and evidence.location.row_index == 1
        and evidence.location.column_name == "检验结果"
        and evidence.value == "符合要求"
        for evidence in first.evidence
    )


def test_keeps_blank_sequence_rows_as_logical_continuations() -> None:
    parsed = _parsed_pdf(
        PdfPage(
            page_number=8,
            text="检验项目表",
            tables=[
                _table(
                    8,
                    [
                        HEADERS,
                        ["25", "ME设备标记", "201.7.4.2", "应清晰", "——", "符合", "/"],
                        ["", "a) 最低要求", "", "补充要求", "符合要求", "", ""],
                    ],
                )
            ],
        )
    )

    items = InspectionTableExtractor().extract_items(parsed)

    assert len(items) == 2
    assert items[0].sequence_raw == "25"
    assert items[1].sequence_raw == ""
    assert items[1].sequence is None
    assert items[1].is_continuation is True
    assert items[1].item_name == "a) 最低要求"
    assert items[1].test_result == "符合要求"


def test_merged_cells_fill_down_non_empty_anchor_but_not_empty_anchor() -> None:
    parsed = _parsed_pdf(
        PdfPage(
            page_number=9,
            text="检验项目表",
            tables=[
                _table(
                    9,
                    [
                        HEADERS,
                        ["1", "应用条件", "4.1", "应满足要求", "符合要求", "符合", "/"],
                        ["", "", "", "", "", "", ""],
                        ["2", "控制装置", "201.7.4.2", "增补：...", "", "/", "/"],
                        ["", "", "", "", "", "", ""],
                    ],
                    metadata={
                        "cell_spans": [
                            {"row": 1, "col": 4, "row_span": 2},
                            {"row": 1, "col": 5, "row_span": 2},
                            {"row": 1, "col": 6, "row_span": 2},
                            {"row": 3, "col": 4, "row_span": 2},
                            {"row": 3, "col": 5, "row_span": 2},
                            {"row": 3, "col": 6, "row_span": 2},
                        ]
                    },
                )
            ],
        )
    )

    items = InspectionTableExtractor().extract_items(parsed)

    assert len(items) == 4
    assert items[1].test_result == "符合要求"
    assert items[1].conclusion == "符合"
    assert items[1].remark == "/"
    assert items[1].field_provenance["test_result"] == "merge_inferred"

    assert items[3].test_result == ""
    assert items[3].conclusion == "/"
    assert items[3].remark == "/"
    assert items[3].field_provenance["test_result"] == "native"


def test_merges_inspection_tables_across_pages_without_losing_order() -> None:
    parsed = _parsed_pdf(
        PdfPage(
            page_number=4,
            text="检验项目表",
            tables=[_table(4, [HEADERS, ["1", "外观", "2.1", "应完整", "符合要求", "符合", "/"]])],
        ),
        PdfPage(
            page_number=5,
            text="检验项目表（续）",
            tables=[_table(5, [HEADERS, ["续1", "外观续", "2.1", "续行", "符合要求", "", ""]])],
        ),
    )

    table = InspectionTableExtractor().extract_table(parsed)

    assert table is not None
    assert table.page_span == (4, 5)
    assert [item.sequence_raw for item in table.items] == ["1", "续1"]
    assert table.items[1].sequence == 1
    assert table.items[1].is_continuation is True
