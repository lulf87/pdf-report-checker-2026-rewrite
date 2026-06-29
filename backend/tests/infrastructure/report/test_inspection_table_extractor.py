from app.domain.pdf import ParsedPdf, PdfPage, PdfTable
from app.infrastructure.report.inspection_table_extractor import InspectionTableExtractor, parse_sequence


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


def test_parse_sequence_only_accepts_plain_numeric_or_continuation_sequence() -> None:
    assert parse_sequence("10") == 10
    assert parse_sequence(" 118 ") == 118
    assert parse_sequence("续 3") == 3
    assert parse_sequence("——所有其他 ME 设备和 ME 系统，500V。") is None
    assert parse_sequence("当外壳的分类为 IPX0 时，保持 ME 设备和其部件在潮湿箱里 48h。") is None
    assert parse_sequence("4.10.2") is None


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


def test_inspection_items_include_visual_geometry_for_c07_crops() -> None:
    table = PdfTable(
        table_id="p22-t1",
        page_numbers=[22],
        bbox=(10, 20, 210, 120),
        columns=["序号", "检验项目", "检验结果", "单项结论", "备注"],
        rows=[
            ["33", "分类标记", "——", "符合", "/"],
            ["", "分类是 IPX0 或 IP0X 的 ME 设备不需要标记。", "", "", ""],
        ],
        metadata={
            "cell_bboxes": [
                [[10, 20, 35, 50], [35, 20, 110, 50], [110, 20, 150, 50], [150, 20, 185, 50], [185, 20, 210, 50]],
                [[10, 50, 35, 80], [35, 50, 110, 80], [110, 50, 150, 80], [150, 50, 185, 80], [185, 50, 210, 80]],
            ]
        },
    )
    parsed = _parsed_pdf(PdfPage(page_number=22, text="检验项目表", tables=[table]))

    extracted = InspectionTableExtractor().extract_items(parsed)

    visual_geometry = extracted[0].metadata["visual_geometry"]
    assert visual_geometry["table_id"] == "p22-t1"
    assert visual_geometry["table_bbox"] == [10.0, 20.0, 210.0, 120.0]
    assert visual_geometry["row_bbox"] == [10.0, 20.0, 210.0, 50.0]
    assert visual_geometry["field_bboxes"]["test_result"] == [110.0, 20.0, 150.0, 50.0]
    assert visual_geometry["field_bboxes"]["conclusion"] == [150.0, 20.0, 185.0, 50.0]
    assert visual_geometry["field_bboxes"]["remark"] == [185.0, 20.0, 210.0, 50.0]


def test_inspection_items_without_cell_bboxes_keep_existing_behavior() -> None:
    table = _table(22, [HEADERS, ["33", "分类标记", "7.2.9", "要求", "——", "符合", "/"]])
    parsed = _parsed_pdf(PdfPage(page_number=22, text="检验项目表", tables=[table]))

    extracted = InspectionTableExtractor().extract_items(parsed)

    assert "visual_geometry" not in extracted[0].metadata
    assert extracted[0].test_result == "——"
    assert extracted[0].conclusion == "符合"


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
