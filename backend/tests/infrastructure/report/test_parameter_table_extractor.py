from app.domain.pdf import ParsedPdf, PdfPage
from app.domain.report import ReportDocument
from app.infrastructure.report.parameter_table_extractor import ReportParameterTableExtractor
from tests.fixtures.table_fixture_builder import build_pdf_table


def test_report_parameter_table_extractor_normalizes_pdf_tables_to_canonical_tables() -> None:
    parsed_pdf = ParsedPdf(
        file_id="report-fixture",
        file_name="report.pdf",
        page_count=1,
        pages=[
            PdfPage(
                page_number=5,
                text="表 1 起搏参数",
                tables=[
                    build_pdf_table(
                        rows=[
                            ["参数", "单位", "型号", "标准设置", "允许误差", "备注"],
                            ["脉冲宽度", "ms", "全部型号", "0.4", "±20μs", "用于起搏"],
                        ],
                        page=5,
                        table_id="report-table-1",
                        table_number="1",
                        caption="表 1 起搏参数",
                    )
                ],
            )
        ],
    )

    tables = ReportParameterTableExtractor().extract_tables(parsed_pdf)

    assert len(tables) == 1
    canonical = tables[0]
    assert canonical.table_number == "1"
    assert canonical.caption == "表 1 起搏参数"
    assert canonical.source_locations[0].page_number == 5
    record = canonical.parameter_records[0]
    assert record.parameter_name == "脉冲宽度"
    assert record.unit == "ms"
    assert record.dimensions["型号"] == "全部型号"
    assert record.values["标准设置"] == "0.4"
    assert record.values["允许误差"] == "±20μs"
    assert record.values["备注"] == "用于起搏"


def test_report_document_metadata_serializes_canonical_tables_without_losing_parameter_data() -> None:
    parsed_pdf = ParsedPdf(
        file_id="report-fixture",
        file_name="report.pdf",
        page_count=1,
        tables=[
            build_pdf_table(
                rows=[["参数", "单位", "型号", "标准设置"], ["基础频率", "bpm", "全部型号", "60"]],
                table_id="report-table-1",
                table_number="1",
                caption="表 1 起搏参数",
            )
        ],
    )
    canonical = ReportParameterTableExtractor().extract_tables(parsed_pdf)[0]
    document = ReportDocument(metadata={"canonical_tables": [canonical]})

    dumped = document.model_dump(mode="json")
    restored = ReportDocument.model_validate(dumped)

    restored_table = restored.metadata["canonical_tables"][0]
    assert restored_table["table_number"] == "1"
    assert restored_table["parameter_records"][0]["parameter_name"] == "基础频率"
    assert restored_table["parameter_records"][0]["unit"] == "bpm"
    assert restored_table["parameter_records"][0]["values"]["标准设置"] == "60"
