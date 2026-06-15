from app.domain.report import LabelOCRField
from app.infrastructure.ocr.label_field_extractor import LabelFieldExtractor


def test_extracts_label_fields_with_legacy_aliases_and_fallbacks() -> None:
    text = (
        "产品名称：一次性使用消融导管\n"
        "REF|NoVAEPP1206\n"
        "LOT2BL009\n"
        "生产日期：2025-12-03\n"
        "失效日期：2027-12-02\n"
        "注册人名称：苏州元科医疗器械有限公司\n"
    )

    fields = LabelFieldExtractor().extract_fields(text)
    by_name = {field.name: field for field in fields}

    assert by_name["product_name"].value == "一次性使用消融导管"
    assert by_name["model_spec"].value == "NoVAEPP1206"
    assert by_name["batch_number"].value == "2BL009"
    assert by_name["production_date"].value == "2025-12-03"
    assert by_name["expiration_date"].value == "2027-12-02"
    assert by_name["registrant"].value == "苏州元科医疗器械有限公司"
    assert all(isinstance(field, LabelOCRField) for field in fields)


def test_extracts_multiline_registrant_address_until_next_label() -> None:
    text = (
        "注册人住所：中国（江苏）自由贸易试验区苏州片区苏州工业\n"
        "园区星湖街328号创意产业园五期A3-403-3单元\n"
        "注册人联系方式：0512-66092209\n"
    )

    fields = LabelFieldExtractor().extract_as_dict(text)

    assert fields["registrant_address"] == (
        "中国（江苏）自由贸易试验区苏州片区苏州工业"
        "园区星湖街328号创意产业园五期A3-403-3单元"
    )


def test_standalone_dates_pick_earliest_as_production_latest_as_expiration() -> None:
    fields = LabelFieldExtractor().extract_as_dict("2027-12-02\n2025-12-03\n")

    assert fields["production_date"] == "2025-12-03"
    assert fields["expiration_date"] == "2027-12-02"
