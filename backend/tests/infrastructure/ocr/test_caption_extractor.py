from app.infrastructure.ocr.caption_extractor import CaptionExtractor


def test_parse_caption_detects_chinese_label_and_main_name() -> None:
    info = CaptionExtractor().parse("№2 一次性使用消化道脉冲电场消融导管 中文标签")

    assert info.caption_number == "2"
    assert info.is_chinese_label is True
    assert info.main_name == "一次性使用消化道脉冲电场消融导管"
    assert info.caption_type == "label"


def test_extract_from_page_text_prefers_explicit_label_caption() -> None:
    page_text = (
        "照片和说明\n"
        "№1 一次性使用消化道脉冲电场消融导管\n"
        "№2 一次性使用消化道脉冲电场消融导管 中文标签\n"
    )

    info = CaptionExtractor().extract_from_page_text(page_text)

    assert info is not None
    assert info.raw_caption.endswith("中文标签")
    assert info.is_chinese_label is True


def test_photo_caption_removes_direction_and_category_noise() -> None:
    extractor = CaptionExtractor()

    assert extractor.parse("左侧显示：电极照片").main_name == "电极"
    assert extractor.parse("中文标签样张：产品").main_name == "产品"
