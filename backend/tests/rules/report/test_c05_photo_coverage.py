from app.domain.finding import FindingSeverity
from app.domain.result import CheckStatus
from app.rules.report.context import CheckContext
from app.rules.report.c05_photo_coverage import (
    check_c05_photo_coverage,
    extract_photo_caption_subject,
    match_photo_subject,
)

from .helpers import base_document, component, photo_caption


def test_extract_photo_caption_subject_removes_prefix_direction_and_category_words() -> None:
    assert extract_photo_caption_subject("№113 消化道脉冲电场消融导管 前侧 照片") == "消化道脉冲电场消融导管"
    assert extract_photo_caption_subject("No.113 消化道脉冲电场消融导管后侧") == "消化道脉冲电场消融导管"
    assert extract_photo_caption_subject("25: 心脏脉冲电场消融仪-主机") == "心脏脉冲电场消融仪-主机"


def test_match_photo_subject_uses_specified_connector_rules() -> None:
    assert match_photo_subject("心脏脉冲电场消融仪-主机", "心脏脉冲电场消融仪-主机") == "exact"
    assert (
        match_photo_subject("心脏脉冲电场消融仪-主机", "心脏脉冲电场消融仪-主机及推车")
        == "component_in_subject_allowed_connector"
    )
    assert match_photo_subject("主机-前面板", "主机") == "subject_in_component_allowed_connector"
    assert match_photo_subject("电极", "一次性射频消融电极") is None


def test_c05_passes_when_photo_caption_subject_matches_component() -> None:
    document = base_document()
    document.sample_components = [component("c1", "消化道脉冲电场消融导管")]
    document.photo_captions = [photo_caption("p1", "№1 消化道脉冲电场消融导管照片", subject="消化道脉冲电场消融导管")]

    result = check_c05_photo_coverage(document, CheckContext(task_id="task-c05"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["coverage"][0]["matching_strategy"] == "exact"
    assert result.metadata["coverage"][0]["matched_captions"] == ["№1 消化道脉冲电场消融导管照片"]
    assert result.metadata["coverage"][0]["is_unused_component"] is False


def test_c05_passes_when_component_name_is_followed_by_allowed_connector_in_subject() -> None:
    document = base_document()
    document.sample_components = [component("c1", "心脏脉冲电场消融仪-主机")]
    document.photo_captions = [photo_caption("p1", "心脏脉冲电场消融仪-主机及推车照片")]

    result = check_c05_photo_coverage(document, CheckContext(task_id="task-c05"))

    assert result.status == CheckStatus.PASS
    assert result.metadata["coverage"][0]["matching_strategy"] == "component_in_subject_allowed_connector"


def test_c05_passes_when_subject_name_is_followed_by_allowed_connector_in_component() -> None:
    document = base_document()
    document.sample_components = [component("c1", "主机-前面板")]
    document.photo_captions = [photo_caption("p1", "№1 主机照片")]

    result = check_c05_photo_coverage(document, CheckContext(task_id="task-c05"))

    assert result.status == CheckStatus.PASS
    assert result.metadata["coverage"][0]["matching_strategy"] == "subject_in_component_allowed_connector"


def test_c05_extracts_caption_subject_from_number_prefix_and_direction_words() -> None:
    document = base_document()
    document.sample_components = [component("c1", "消化道脉冲电场消融导管")]
    document.photo_captions = [photo_caption("p1", "№113 消化道脉冲电场消融导管前侧照片", subject=None)]

    result = check_c05_photo_coverage(document, CheckContext(task_id="task-c05"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["coverage"][0]["matching_strategy"] == "exact"


def test_c05_errors_when_component_has_no_non_label_photo() -> None:
    document = base_document()
    document.sample_components = [component("c1", "消化道脉冲电场消融导管")]
    document.photo_captions = [photo_caption("label-1", "消化道脉冲电场消融导管 中文标签", caption_type="photo")]

    result = check_c05_photo_coverage(document, CheckContext(task_id="task-c05"))

    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "PHOTO_COVERAGE_MISSING"
    assert result.findings[0].severity == FindingSeverity.ERROR
    assert result.findings[0].expected == "至少一张照片"
    assert result.findings[0].actual == "未匹配到照片"
    assert result.findings[0].metadata["component_name"] == "消化道脉冲电场消融导管"
    assert result.findings[0].metadata["matched_captions"] == []
    assert result.findings[0].metadata["matching_strategy"] is None
    assert result.findings[0].metadata["is_unused_component"] is False


def test_c05_skips_component_marked_not_used() -> None:
    document = base_document()
    document.sample_components = [component("c1", "备用导管", remark="本次检测未使用")]

    result = check_c05_photo_coverage(document, CheckContext(task_id="task-c05"))

    assert result.status == CheckStatus.SKIP
    assert result.findings == []
    assert result.metadata["coverage"][0]["is_unused_component"] is True
    assert result.metadata["coverage"][0]["matching_strategy"] == "unused_component_skipped"


def test_c05_skips_supporting_equipment_by_default() -> None:
    document = base_document()
    supporting = component("c1", "配合使用设备")
    supporting.metadata["sample_role"] = "supporting_equipment"
    document.sample_components = [supporting]

    result = check_c05_photo_coverage(document, CheckContext(task_id="task-c05"))

    assert result.status == CheckStatus.SKIP
    assert result.findings == []
    assert result.metadata["coverage"][0]["sample_role"] == "supporting_equipment"
    assert result.metadata["coverage"][0]["matching_strategy"] == "supporting_equipment_skipped"


def test_c05_warns_when_matching_caption_has_low_confidence() -> None:
    document = base_document()
    document.sample_components = [component("c1", "消化道脉冲电场消融导管")]
    low_confidence_caption = photo_caption("p1", "№1 消化道脉冲电场消融导管照片", subject=None)
    low_confidence_caption.metadata["ocr_confidence"] = "low"
    document.photo_captions = [low_confidence_caption]

    result = check_c05_photo_coverage(document, CheckContext(task_id="task-c05"))

    assert result.status == CheckStatus.REVIEW
    assert [finding.code for finding in result.findings] == ["PHOTO_CAPTION_UNCERTAIN"]
    assert result.findings[0].severity == FindingSeverity.WARN
    assert result.findings[0].metadata["ocr_confidence"] == "low"
    assert result.findings[0].metadata["matched_captions"] == ["№1 消化道脉冲电场消融导管照片"]
