from app.domain.pdf import ParsedPdf, PdfPage
from app.infrastructure.report.photo_label_extractor import (
    PhotoLabelExtractor,
    extract_label_field_candidates,
    parse_caption_subject,
)


def _parsed_pdf(*pages: PdfPage) -> ParsedPdf:
    return ParsedPdf(
        file_id="photo-label-fixture",
        file_name="report.pdf",
        page_count=len(pages),
        pages=list(pages),
    )


def test_extracts_photo_and_label_captions_with_subject_names() -> None:
    parsed = _parsed_pdf(
        PdfPage(page_number=5, text="检验报告照片页\n№1 导管外观照片\n№2 导管 中文标签样张"),
        PdfPage(page_number=6, text="检品外观照片"),
    )

    captions = PhotoLabelExtractor().extract_captions(parsed)

    assert [caption.text for caption in captions] == ["№1 导管外观照片", "№2 导管 中文标签样张", "检品外观照片"]
    assert captions[0].subject_name == "导管"
    assert captions[0].caption_type == "photo"
    assert captions[1].subject_name == "导管"
    assert captions[1].caption_type == "label"
    assert captions[1].page_number == 5
    assert captions[1].evidence


def test_parse_caption_subject_removes_number_direction_and_category_words() -> None:
    assert parse_caption_subject("№2 一次性使用消化道脉冲电场消融导管 中文标签") == "一次性使用消化道脉冲电场消融导管"
    assert parse_caption_subject("图1: 正面图：导管外观照片") == "导管"
    assert parse_caption_subject("No.3 手柄包装标签样张") == "手柄"


def test_extracts_label_ocr_field_candidates_from_text_layer() -> None:
    parsed = _parsed_pdf(
        PdfPage(
            page_number=7,
            text=(
                "照片和说明\n"
                "№2 一次性使用消化道脉冲电场消融导管 中文标签\n"
                "产品名称：一次性使用消化道脉冲电场消融导管\n"
                "规格型号：RMC01\n"
                "LOT RMC251201\n"
                "生产日期：2025-12-10\n"
                "失效日期：2027-12-09\n"
                "注册人住所：中国（江苏）自由贸易试验区苏州片区苏州工业\n"
                "园区星湖街328号创意产业园五期A3-403-3单元\n"
                "注册人联系方式：0512-66092209\n"
            ),
        )
    )

    labels = PhotoLabelExtractor().extract_labels(parsed)

    assert len(labels) == 1
    label = labels[0]
    assert label.caption_text == "№2 一次性使用消化道脉冲电场消融导管 中文标签"
    fields = {field.name: field.value for field in label.fields}
    assert fields["product_name"] == "一次性使用消化道脉冲电场消融导管"
    assert fields["model_spec"] == "RMC01"
    assert fields["batch_number"] == "RMC251201"
    assert fields["production_date"] == "2025-12-10"
    assert fields["expiration_date"] == "2027-12-09"
    assert fields["registrant_address"] == "中国（江苏）自由贸易试验区苏州片区苏州工业园区星湖街328号创意产业园五期A3-403-3单元"
    assert all(field.raw_value is not None for field in label.fields)


def test_field_candidate_fallbacks_for_ref_lot_and_standalone_dates() -> None:
    fields = extract_label_field_candidates("REF|NoVAEPP1206\nLOT2BL009\n2027-12-02\n2025-12-03")

    assert fields["model_spec"] == "NoVAEPP1206"
    assert fields["batch_number"] == "2BL009"
    assert fields["production_date"] == "2025-12-03"
    assert fields["expiration_date"] == "2027-12-02"


def test_english_long_label_patterns_are_not_truncated_by_short_codes() -> None:
    fields = extract_label_field_candidates("Lot Number: ABC123\nBatch Number: B2025\nExpiration Date: 2027-12-02")

    assert fields["batch_number"] == "ABC123"
    assert fields["expiration_date"] == "2027-12-02"
