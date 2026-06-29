from app.domain.pdf import ParsedPdf, PdfPage, PdfTable
from app.infrastructure.report.sample_description_extractor import SampleDescriptionExtractor


def _parsed_pdf(*pages: PdfPage) -> ParsedPdf:
    return ParsedPdf(
        file_id="sample-fixture",
        file_name="report.pdf",
        page_count=len(pages),
        pages=list(pages),
        tables=[table for page in pages for table in page.tables],
    )


def test_extracts_sample_components_with_expiration_date_and_remark_preserved() -> None:
    table = PdfTable(
        table_id="sample-table",
        page_numbers=[4],
        columns=["序号", "部件名称", "规格型号", "序列号/批号", "生产日期", "失效日期", "备注"],
        rows=[
            ["序号", "部件名称", "规格型号", "序列号/批号", "生产日期", "失效日期", "备注"],
            ["1", "导管", "RMC01", "RMC251201", "20251210", "20271209", "本次检测未使用"],
        ],
    )
    parsed = _parsed_pdf(PdfPage(page_number=4, text="样品描述", tables=[table]))

    components = SampleDescriptionExtractor().extract_components(parsed)

    assert len(components) == 1
    component = components[0]
    assert component.component_name == "导管"
    assert component.model == "RMC01"
    assert component.batch_or_serial == "RMC251201"
    assert component.production_date == "20251210"
    assert component.expiration_date == "20271209"
    assert component.remark == "本次检测未使用"
    assert component.metadata["unused_note"] == "本次检测未使用"
    assert component.row_location is not None
    assert component.row_location.page_number == 4
    assert any(evidence.location and evidence.location.column_name == "失效日期" for evidence in component.evidence)


def test_extracts_rows_with_header_synonyms_and_keeps_empty_values() -> None:
    table = PdfTable(
        table_id="sample-table",
        page_numbers=[6],
        columns=["编号", "样品名称", "型号规格", "批号/序列号", "制造日期", "有效期至", "说明"],
        rows=[
            ["编号", "样品名称", "型号规格", "批号/序列号", "制造日期", "有效期至", "说明"],
            ["2", "手柄", "H-01", "/", "2025-01-01", "", "/"],
        ],
    )
    parsed = _parsed_pdf(PdfPage(page_number=6, text="样品描述表", tables=[table]))

    rows = SampleDescriptionExtractor().extract_rows(parsed)

    assert len(rows) == 1
    row = rows[0]
    assert row.sequence_raw == "2"
    assert row.component_name is not None
    assert row.component_name.value == "手柄"
    assert row.model is not None
    assert row.model.value == "H-01"
    assert row.batch_or_serial is not None
    assert row.batch_or_serial.value == "/"
    assert row.expiration_date is not None
    assert row.expiration_date.value == ""
    assert row.remark is not None
    assert row.remark.value == "/"


def test_marks_page_8_cooperating_use_table_as_supporting_equipment() -> None:
    table = PdfTable(
        table_id="supporting-equipment-table",
        page_numbers=[8],
        columns=["序号", "部件名称", "规格型号", "序列号/批号", "生产日期", "备注"],
        rows=[
            ["序号", "部件名称", "规格型号", "序列号/批号", "生产日期", "备注"],
            ["1", "三维心脏电生理标测系统", "ENSITE-X", "ABC123", "2025-01-01", ""],
        ],
    )
    parsed = _parsed_pdf(
        PdfPage(
            page_number=8,
            text="本次检验配合使用设备如下：",
            tables=[table],
        )
    )

    components = SampleDescriptionExtractor().extract_components(parsed)

    assert len(components) == 1
    assert components[0].metadata["sample_role"] == "supporting_equipment"
    assert components[0].metadata["supporting_equipment"] is True
    assert components[0].metadata["source_context"] == "本次检验配合使用"
