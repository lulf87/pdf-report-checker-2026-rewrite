from app.domain.pdf import ParsedPdf, PdfPage
from app.domain.report import ReportDocument
from app.infrastructure.report.field_extractor import FieldExtractor, split_inspection_items


def _parsed_pdf(*pages: PdfPage) -> ParsedPdf:
    return ParsedPdf(
        file_id="report-fixture",
        file_name="report.pdf",
        page_count=len(pages),
        pages=list(pages),
    )


def test_extracts_first_page_fields_and_preserves_raw_values() -> None:
    parsed = _parsed_pdf(
        PdfPage(
            page_number=1,
            text=(
                "检 验 报 告\n"
                "委 托 方\n"
                "苏州 元科医疗器械有限公司  \n"
                "样品名称\n"
                "一次性使用消化道脉冲电场消融导管\n"
                "型号规格\n"
                "RMC01  \n"
            ),
        ),
        PdfPage(page_number=3, text="检验报告首页"),
    )

    report = FieldExtractor().extract(parsed)

    assert isinstance(report, ReportDocument)
    assert report.first_page is not None
    assert report.first_page.client is not None
    assert report.first_page.client.raw_value == "苏州 元科医疗器械有限公司  "
    assert report.first_page.client.value == "苏州 元科医疗器械有限公司"
    assert report.first_page.model_spec is not None
    assert report.first_page.model_spec.raw_value == "RMC01  "
    assert report.first_page.model_spec.value == "RMC01"
    assert report.first_page.client.evidence[0].raw_text.startswith("委 托 方")


def test_extracts_third_page_fields_multiline_address_and_scope_items() -> None:
    parsed = _parsed_pdf(
        PdfPage(page_number=1, text="封面"),
        PdfPage(page_number=2, text="目录"),
        PdfPage(
            page_number=3,
            text=(
                "检 验 报 告 首 页\n"
                "样品名称\n"
                "一次性使用消化道脉冲电场消融导管\n"
                "型号规格\n"
                "RMC01  \n"
                "委托方\n"
                "苏州元科医疗器械有限公司\n"
                "生产日期\n"
                "20251210\n"
                "产品编号／\n"
                "批号\n"
                "RMC251201\n"
                "委托方地址\n"
                "中国（江苏）自由贸易试验区苏州片区苏州\n"
                "工业园区星湖街328 号创意产业园五期A3-40\n"
                "3-3 单元\n"
                "检验项目\n"
                "2.1～2.8（除生物相容性、电磁兼容性）\n"
            ),
        ),
    )

    report = FieldExtractor().extract(parsed)

    assert report.third_page is not None
    assert report.third_page.model_spec is not None
    assert report.third_page.model_spec.raw_value == "RMC01  "
    assert report.third_page.model_spec.value == "RMC01"
    assert report.third_page.production_date is not None
    assert report.third_page.production_date.value == "20251210"
    assert report.third_page.batch_or_serial is not None
    assert report.third_page.batch_or_serial.value == "RMC251201"
    assert report.third_page.client_address is not None
    assert (
        report.third_page.client_address.value
        == "中国（江苏）自由贸易试验区苏州片区苏州工业园区星湖街328 号创意产业园五期A3-403-3 单元"
    )

    inspection_scope = next(field for field in report.third_page.fields if field.name == "检验项目")
    assert inspection_scope.metadata["items"] == ["2.1～2.8（除生物相容性、电磁兼容性）"]
    assert report.page_map["first_page"] == 1
    assert report.page_map["third_page"] == 3
    assert not report.inspection_items


def test_split_inspection_items_preserves_commas_inside_parentheses() -> None:
    assert split_inspection_items("2.1、2.2（除A、B），2.3") == [
        "2.1",
        "2.2（除A、B）",
        "2.3",
    ]
