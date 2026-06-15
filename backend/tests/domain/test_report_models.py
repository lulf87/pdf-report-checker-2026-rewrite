import pytest
from pydantic import ValidationError

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.report import (
    InspectionItem,
    LabelOCRField,
    LabelOCRResult,
    PhotoCaption,
    ReportField,
    SampleComponent,
)


def test_report_field_keeps_raw_normalized_location_and_confidence() -> None:
    location = Location(source_type=SourceType.REPORT, page_number=3, row_index=4, column_name="型号规格")
    field = ReportField(
        name="型号规格",
        raw_value=" ABC - 1 ",
        normalized_value="ABC-1",
        location=location,
        confidence="high",
        aliases=["规格型号", "型号"],
    )

    payload = field.model_dump(mode="json")

    assert payload["raw_value"] == " ABC - 1 "
    assert payload["normalized_value"] == "ABC-1"
    assert payload["location"]["page_number"] == 3
    assert payload["location"]["row_index"] == 4
    assert payload["confidence"] == "high"
    assert field.confidence is Confidence.HIGH


def test_report_field_rejects_unknown_confidence_value() -> None:
    with pytest.raises(ValidationError):
        ReportField(name="委托方", raw_value="医院", confidence="certain")


def test_inspection_item_is_fact_model_not_c07_rule_model() -> None:
    item = InspectionItem(
        sequence_raw="1",
        sequence=1,
        item_name="电气安全",
        standard_clause="GB 9706.1-2020 8.7",
        standard_requirement="漏电流应符合要求",
        test_result="",
        result_values=[],
        conclusion="",
        remark="/",
        source_page=8,
        row_index_in_page=12,
        field_provenance={"remark": "pdf_text"},
    )

    payload = item.model_dump(mode="json")

    assert payload["standard_clause"] == "GB 9706.1-2020 8.7"
    assert payload["test_result"] == ""
    assert payload["source_page"] == 8
    assert payload["row_index_in_page"] == 12
    assert payload["field_provenance"] == {"remark": "pdf_text"}
    assert not hasattr(item, "expected_conclusion")
    assert not hasattr(item, "conclusion_matches")


def test_sample_component_builds_non_empty_identity_key_from_available_fields() -> None:
    component = SampleComponent(
        component_id="sample-1",
        component_name="主机",
        model="ABC-1",
        batch_or_serial="SN001",
        production_date="2026-01-08",
        expiration_date="2028-01-08",
    )

    assert component.identity_key == "主机|ABC-1|SN001|2026-01-08|2028-01-08"
    assert component.model_dump(mode="json")["identity_key"] == "主机|ABC-1|SN001|2026-01-08|2028-01-08"


def test_label_ocr_and_photo_caption_preserve_ocr_evidence() -> None:
    evidence = Evidence(
        id="ev-label-model",
        source_type=SourceType.REPORT,
        location=Location(source_type=SourceType.REPORT, page_number=12),
        raw_text="型号规格：ABC-1",
        method=EvidenceMethod.OCR,
        confidence="medium",
    )
    label = LabelOCRResult(
        label_id="label-1",
        page_number=12,
        caption_id="caption-1",
        caption_text="№6 主机中文标签样张",
        fields=[
            LabelOCRField(
                name="型号规格",
                raw_value="型号规格：ABC-1",
                normalized_value="ABC-1",
                confidence="medium",
                evidence=[evidence],
            )
        ],
        raw_blocks=["型号规格：ABC-1"],
        language="zh",
        ocr_engine="paddleocr",
        confidence="medium",
        image_ref="runtime/label-1.png",
    )
    caption = PhotoCaption(
        caption_id="caption-1",
        text="№6 主机中文标签样张",
        subject_name="主机",
        caption_type="chinese_label",
        page_number=12,
    )

    payload = label.model_dump(mode="json")

    assert payload["confidence"] == "medium"
    assert payload["fields"][0]["evidence"][0]["method"] == "ocr"
    assert caption.model_dump(mode="json")["caption_type"] == "chinese_label"
