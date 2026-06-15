from app.domain.common import Confidence
from app.domain.finding import FindingSeverity
from app.domain.result import CheckStatus
from app.rules.report.context import CheckContext
from app.rules.report.c06_label_coverage import build_component_key, check_c06_label_coverage

from .helpers import base_document, component, label, label_field, photo_caption


def _label(
    label_id: str,
    *,
    name: str = "消化道脉冲电场消融导管",
    model: str | None = "RMC01",
    batch: str | None = "RMC251201",
    production_date: str | None = "2025-12-10",
    expiration_date: str | None = None,
    caption: str = "消化道脉冲电场消融导管 中文标签",
    confidence: Confidence | str = Confidence.HIGH,
):
    fields = [label_field("产品名称", name)]
    if model is not None:
        fields.append(label_field("规格型号", model))
    if batch is not None:
        fields.append(label_field("批号", batch, aliases=["序列号批号"]))
    if production_date is not None:
        fields.append(label_field("生产日期", production_date))
    if expiration_date is not None:
        fields.append(label_field("失效日期", expiration_date))
    return label(
        label_id,
        caption_text=caption,
        fields=fields,
        confidence=confidence,
    )


def test_build_component_key_ignores_no_value_markers() -> None:
    key = build_component_key(
        component(
            "c1",
            "消化道脉冲电场消融导管",
            model="/",
            batch="RMC251201",
            production_date="见实物",
            expiration_date="",
        )
    )

    assert key == {
        "部件名称": "消化道脉冲电场消融导管",
        "序列号批号": "RMC251201",
    }


def test_c06_passes_when_component_has_chinese_label_caption() -> None:
    document = base_document(labels=[_label("label-1")])
    document.sample_components = [component("c1", "消化道脉冲电场消融导管")]

    result = check_c06_label_coverage(document, CheckContext(task_id="task-c06"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["coverage"][0]["matching_strategy"] == "identity"
    assert result.metadata["coverage"][0]["matched_label_key"] == "label-1"


def test_c06_passes_when_component_has_chinese_label_sample_caption() -> None:
    document = base_document(labels=[_label("label-1", caption="消化道脉冲电场消融导管 中文标签样张")])
    document.sample_components = [component("c1", "消化道脉冲电场消融导管")]

    result = check_c06_label_coverage(document, CheckContext(task_id="task-c06"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c06_passes_when_component_has_label_sample_caption() -> None:
    document = base_document(labels=[_label("label-1", caption="消化道脉冲电场消融导管 标签样张")])
    document.sample_components = [component("c1", "消化道脉冲电场消融导管")]

    result = check_c06_label_coverage(document, CheckContext(task_id="task-c06"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c06_errors_for_missing_chinese_label() -> None:
    document = base_document()
    document.sample_components = [component("c1", "消化道脉冲电场消融导管")]

    result = check_c06_label_coverage(document, CheckContext(task_id="task-c06"))

    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "LABEL_COVERAGE_MISSING"
    assert result.findings[0].severity == FindingSeverity.ERROR
    assert result.findings[0].expected == "至少一张中文标签"
    assert result.findings[0].actual == "未匹配到中文标签"
    assert result.findings[0].metadata["component_key"] == {
        "部件名称": "消化道脉冲电场消融导管",
        "规格型号": "RMC01",
        "序列号批号": "RMC251201",
        "生产日期": "2025-12-10",
    }


def test_c06_skips_not_used_component() -> None:
    document = base_document()
    document.sample_components = [component("c1", "备用导管", remark="本次检测未使用")]

    result = check_c06_label_coverage(document, CheckContext(task_id="task-c06"))

    assert result.status == CheckStatus.SKIP
    assert result.findings == []
    assert result.metadata["coverage"][0]["is_unused_component"] is True
    assert result.metadata["coverage"][0]["matching_strategy"] == "unused_component_skipped"


def test_c06_distinguishes_same_name_components_by_non_empty_identity_fields() -> None:
    document = base_document(
        labels=[
            _label("label-1", model="A", batch="A001", caption="消化道脉冲电场消融导管 中文标签"),
            _label("label-2", model="B", batch="B002", caption="消化道脉冲电场消融导管 中文标签"),
        ]
    )
    document.sample_components = [
        component("c1", "消化道脉冲电场消融导管", model="A", batch="A001"),
        component("c2", "消化道脉冲电场消融导管", model="B", batch="B002"),
    ]

    result = check_c06_label_coverage(document, CheckContext(task_id="task-c06"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert [entry["matched_label_key"] for entry in result.metadata["coverage"]] == ["label-1", "label-2"]


def test_c06_errors_when_same_name_components_have_only_one_matching_label() -> None:
    document = base_document(labels=[_label("label-1", model="A", batch="A001")])
    document.sample_components = [
        component("c1", "消化道脉冲电场消融导管", model="A", batch="A001"),
        component("c2", "消化道脉冲电场消融导管", model="B", batch="B002"),
    ]

    result = check_c06_label_coverage(document, CheckContext(task_id="task-c06"))

    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "LABEL_COMPONENT_KEY_NOT_MATCHED"
    assert result.findings[0].severity == FindingSeverity.ERROR
    assert result.findings[0].metadata["component_id"] == "c2"
    assert result.metadata["coverage"][1]["matched_label_key"] is None


def test_c06_joint_key_ignores_empty_and_slash_values_when_matching() -> None:
    document = base_document(labels=[_label("label-1", model=None, batch="LOT-1", production_date=None)])
    document.sample_components = [
        component("c1", "消化道脉冲电场消融导管", model="/", batch="LOT-1", production_date="见实物")
    ]

    result = check_c06_label_coverage(document, CheckContext(task_id="task-c06"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c06_extracts_label_subject_from_number_prefix_and_direction_words() -> None:
    document = base_document(
        labels=[
            _label(
                "label-1",
                name="其他名称",
                model=None,
                batch=None,
                production_date=None,
                caption="№113 消化道脉冲电场消融导管前侧 中文标签",
            )
        ]
    )
    document.sample_components = [
        component("c1", "消化道脉冲电场消融导管", model=None, batch=None, production_date=None)
    ]

    result = check_c06_label_coverage(document, CheckContext(task_id="task-c06"))

    assert result.status == CheckStatus.PASS
    assert result.metadata["coverage"][0]["matching_strategy"] == "caption_subject"


def test_c06_does_not_count_ordinary_photo_caption_as_chinese_label() -> None:
    document = base_document()
    document.sample_components = [component("c1", "消化道脉冲电场消融导管")]
    document.photo_captions = [photo_caption("photo-1", "消化道脉冲电场消融导管 外观照片")]

    result = check_c06_label_coverage(document, CheckContext(task_id="task-c06"))

    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "LABEL_COVERAGE_MISSING"


def test_c06_warns_when_matching_label_has_low_confidence() -> None:
    document = base_document(labels=[_label("label-1", confidence=Confidence.LOW)])
    document.sample_components = [component("c1", "消化道脉冲电场消融导管")]

    result = check_c06_label_coverage(document, CheckContext(task_id="task-c06"))

    assert result.status == CheckStatus.REVIEW
    assert [finding.code for finding in result.findings] == ["LABEL_CAPTION_UNCERTAIN"]
    assert result.findings[0].severity == FindingSeverity.WARN
    assert result.findings[0].metadata["matched_label_key"] == "label-1"
    assert result.findings[0].metadata["ocr_confidence"] == "low"
