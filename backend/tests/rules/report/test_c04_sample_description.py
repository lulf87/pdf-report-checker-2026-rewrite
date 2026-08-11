import pytest

from app.domain.finding import FindingSeverity
from app.domain.result import CheckStatus
from app.rules.report.context import CheckContext
from app.rules.report.c04_sample_description import check_c04_sample_description

from .helpers import base_document, component, field, label, label_field


def test_c04_uses_report_sample_name_for_generic_main_unit_label_matching() -> None:
    main_label = label(
        "label-main",
        caption_text="№5 射频皮肤治疗仪 中文铭牌",
        fields=[],
        page=102,
    )
    document = base_document(labels=[main_label])
    document.first_page.sample_name = field("样品名称", "射频皮肤治疗仪", page=1)
    document.sample_components = [
        component(
            "main-unit",
            "主机",
            model=None,
            batch=None,
            production_date=None,
            expiration_date=None,
        )
    ]

    result = check_c04_sample_description(document, CheckContext(task_id="task-c04-main"))

    assert [finding.code for finding in result.findings] == ["OCR_EVIDENCE_INSUFFICIENT"]
    assert result.findings[0].metadata["label_id"] == "label-main"
    assert result.metadata["coverage"][0]["matching_strategy"] == "name"


def _component_label(
    *,
    label_id: str = "label-component",
    caption_text: str = "消化道脉冲电场消融导管 中文标签",
    product_name: str = "消化道脉冲电场消融导管",
    model: str = "RMC01",
    batch: str = "RMC251201",
    production: str = "2025-12-10",
    expiration: str | None = "2027-12-09",
    batch_field_name: str = "批号",
    production_field_name: str = "生产日期",
    expiration_field_name: str = "失效日期",
):
    fields = [
        label_field("产品名称", product_name),
        label_field("规格型号", model, aliases=["型号规格"]),
        label_field(batch_field_name, batch, aliases=["序列号批号"]),
        label_field(production_field_name, production),
    ]
    if expiration is not None:
        fields.append(label_field(expiration_field_name, expiration, aliases=["有效期至"]))
    return label(
        label_id,
        caption_text=caption_text,
        fields=fields,
    )


def _run(document):
    return check_c04_sample_description(document, CheckContext(task_id="task-c04"))


def test_c04_passes_when_single_component_five_fields_match_label_ocr() -> None:
    document = base_document(labels=[_component_label()])
    document.sample_components = [
        component(
            "c1",
            "消化道脉冲电场消融导管",
            expiration_date="2027-12-09",
        )
    ]

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


@pytest.mark.parametrize(
    ("component_kwargs", "label_kwargs", "field_name"),
    [
        ({}, {"product_name": "消化道消融导管"}, "部件名称"),
        ({"model": "RMC01"}, {"model": "RMC02"}, "规格型号"),
        ({"batch": "RMC251201"}, {"batch": "RMC251202"}, "序列号批号"),
        ({"production_date": "2025-12-10"}, {"production": "2025-12-11"}, "生产日期"),
        ({"expiration_date": "2027-12-09"}, {"expiration": "2027-12-10"}, "失效日期"),
    ],
)
def test_c04_reports_each_field_mismatch_as_error(component_kwargs, label_kwargs, field_name) -> None:
    document = base_document(labels=[_component_label(**label_kwargs)])
    base_component_kwargs = {"expiration_date": "2027-12-09"}
    base_component_kwargs.update(component_kwargs)
    document.sample_components = [
        component(
            "c1",
            "消化道脉冲电场消融导管",
            **base_component_kwargs,
        )
    ]

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    finding = next(f for f in result.findings if f.metadata["field_name"] == field_name)
    assert finding.code == "SAMPLE_FIELD_MISMATCH"
    assert finding.severity == FindingSeverity.ERROR
    assert finding.metadata["component_key"]
    assert finding.metadata["label_key"] == "label-component"


def test_c04_treats_slash_as_no_value_when_label_field_absent() -> None:
    document = base_document(labels=[_component_label(expiration=None)])
    document.sample_components = [
        component("c1", "消化道脉冲电场消融导管", expiration_date="/"),
    ]

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c04_treats_blank_as_no_value_when_label_field_absent() -> None:
    document = base_document(labels=[_component_label(expiration=None)])
    document.sample_components = [
        component("c1", "消化道脉冲电场消融导管", expiration_date=""),
    ]

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c04_reports_missing_table_value_when_slash_but_label_has_value() -> None:
    document = base_document(labels=[_component_label(expiration="2027-12-09")])
    document.sample_components = [
        component("c1", "消化道脉冲电场消融导管", expiration_date="/"),
    ]

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "SAMPLE_FIELD_MISSING_IN_TABLE"
    assert result.findings[0].severity == FindingSeverity.ERROR
    assert result.findings[0].metadata["field_name"] == "失效日期"
    assert result.findings[0].expected == "2027-12-09"
    assert result.findings[0].actual == "/"


@pytest.mark.parametrize(
    ("batch_field_name", "production_field_name"),
    [
        ("LOT", "MFG"),
        ("SN", "MFD"),
    ],
)
def test_c04_matches_label_field_synonyms_for_lot_sn_mfg_mfd_and_exp(
    batch_field_name,
    production_field_name,
) -> None:
    document = base_document(
        labels=[
            _component_label(
                batch_field_name=batch_field_name,
                production_field_name=production_field_name,
                expiration_field_name="EXP",
            )
        ]
    )
    document.sample_components = [
        component(
            "c1",
            "消化道脉冲电场消融导管",
            expiration_date="2027-12-09",
        )
    ]

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c04_ignores_sequence_and_remark_fields() -> None:
    document = base_document(labels=[_component_label()])
    row = component(
        "c1",
        "消化道脉冲电场消融导管",
        expiration_date="2027-12-09",
        remark="备注内容与标签无关",
    )
    row.metadata["序号"] = "999"
    document.sample_components = [row]

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c04_downgrades_unused_component_field_mismatch_to_warn() -> None:
    document = base_document(labels=[_component_label(model="RMC02")])
    document.sample_components = [
        component(
            "c1",
            "消化道脉冲电场消融导管",
            remark="本次检测未使用",
            expiration_date="2027-12-09",
        )
    ]

    result = _run(document)

    assert result.status == CheckStatus.REVIEW
    assert result.findings[0].code == "SAMPLE_UNUSED_COMPONENT_FIELD_WARNING"
    assert result.findings[0].severity == FindingSeverity.WARN
    assert result.findings[0].metadata["field_name"] == "规格型号"


def test_c04_matches_same_name_rows_by_non_empty_identity_fields() -> None:
    document = base_document(
        labels=[
            _component_label(
                label_id="label-rmc01",
                model="RMC01",
                batch="LOT001",
                caption_text="导管 中文标签",
            ),
            _component_label(
                label_id="label-rmc02",
                model="RMC02",
                batch="LOT002",
                caption_text="导管 中文标签",
            ),
        ]
    )
    document.sample_components = [
        component(
            "c1",
            "消化道脉冲电场消融导管",
            model="RMC01",
            batch="LOT001",
            expiration_date="2027-12-09",
        ),
        component(
            "c2",
            "消化道脉冲电场消融导管",
            model="RMC02",
            batch="LOT002",
            expiration_date="2027-12-09",
        ),
    ]

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["coverage"] == [
        {"component_id": "c1", "label_id": "label-rmc01", "matching_strategy": "identity"},
        {"component_id": "c2", "label_id": "label-rmc02", "matching_strategy": "identity"},
    ]


def test_c04_reviews_when_no_matching_label_is_found() -> None:
    document = base_document()
    document.sample_components = [
        component("c1", "消化道脉冲电场消融导管", expiration_date="2027-12-09")
    ]

    result = _run(document)

    assert result.status == CheckStatus.REVIEW
    assert result.findings[0].code == "SAMPLE_COMPONENT_LABEL_NOT_FOUND"
    assert result.findings[0].severity == FindingSeverity.WARN


def test_c04_skips_2797_like_supporting_equipment_without_label_missing_error() -> None:
    document = base_document()
    document.sample_components = [
        component("sample-row-7", "射频消融仪", model="FG-01", batch="/", page=8),
        component("sample-row-8", "灌注泵", model="CoolFlow", batch="/", page=8),
        component("sample-row-9", "电生理记录系统", model="WorkMate", batch="/", page=8),
    ]
    for item in document.sample_components:
        item.metadata.update(
            {
                "sample_role": "supporting_equipment",
                "supporting_equipment": True,
                "source_context": "本次检验配合使用",
            }
        )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["coverage"] == [
        {
            "component_id": "sample-row-7",
            "label_id": None,
            "matching_strategy": "supporting_equipment_skipped",
        },
        {
            "component_id": "sample-row-8",
            "label_id": None,
            "matching_strategy": "supporting_equipment_skipped",
        },
        {
            "component_id": "sample-row-9",
            "label_id": None,
            "matching_strategy": "supporting_equipment_skipped",
        },
    ]
    details = result.metadata["explanation_details"]
    assert details["decision"]["user_facing_status"] == "passed"
    assert any(row["status"] == "not_applicable" for row in details["comparison_rows"])
    assert "本次检验配合使用设备表" in str(details)
    assert "/Users/" not in str(details)


def test_c04_label_caption_with_empty_ocr_fields_needs_visual_review_not_error() -> None:
    document = base_document(
        labels=[
            label(
                "label-caption-only",
                caption_text="消化道脉冲电场消融导管 中文标签样张",
                fields=[],
            )
        ]
    )
    document.sample_components = [
        component("c1", "消化道脉冲电场消融导管", expiration_date="2027-12-09")
    ]

    result = _run(document)

    assert result.status == CheckStatus.REVIEW
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "OCR_EVIDENCE_INSUFFICIENT"
    assert finding.severity == FindingSeverity.WARN
    assert finding.metadata["user_facing_status"] == "needs_review"
    assert finding.metadata["label_caption_exists"] is True
    assert finding.metadata["matched_ocr_field_count"] == 0
    details = result.metadata["explanation_details"]
    assert details["decision"]["user_facing_status"] == "needs_review"
    assert "标签样张存在，但 OCR 未抽取到可比对字段，需视觉复核" in str(details)
    assert any(row["field"] == "规格型号" and row["status"] == "needs_review" for row in details["comparison_rows"])
    assert any(group["title"] == "匹配到的中文标签样张" for group in details["evidence_groups"])
    assert "/Users/" not in str(details)


def test_c04_matches_controller_console_alias_before_requesting_visual_review() -> None:
    document = base_document(
        labels=[
            label(
                "label-controller",
                caption_text="控制台 中文标签样张",
                fields=[],
            )
        ]
    )
    document.sample_components = [
        component(
            "c1",
            "控制器",
            model=None,
            batch=None,
            production_date=None,
            expiration_date=None,
        )
    ]

    result = _run(document)

    assert result.status == CheckStatus.REVIEW
    assert [finding.code for finding in result.findings] == ["OCR_EVIDENCE_INSUFFICIENT"]
    assert result.metadata["coverage"][0]["label_id"] == "label-controller"


def test_c04_handles_flattened_merged_sample_description_rows() -> None:
    document = base_document(labels=[_component_label()])
    flattened_row = component(
        "c1",
        "消化道脉冲电场消融导管",
        expiration_date="2027-12-09",
    )
    flattened_row.metadata["row_source"] = "merge_inferred"
    document.sample_components = [flattened_row]

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
