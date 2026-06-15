import pytest

from app.domain.common import Confidence
from app.domain.finding import FindingSeverity
from app.domain.result import CheckStatus
from app.rules.report.context import CheckContext
from app.rules.report.c02_third_page_extended_fields import check_c02_third_page_extended_fields

from .helpers import base_document, field, label, label_field


def _core_label(
    *,
    model_key: str = "规格型号",
    date_key: str = "生产日期",
    batch_key: str = "批号",
    model_value: str = "RMC01",
    date_value: str = "2025-12-10",
    batch_value: str = "RMC251201",
    confidence: Confidence = Confidence.HIGH,
):
    return label(
        "label-1",
        caption_text="№2 一次性使用消化道脉冲电场消融导管 中文标签",
        fields=[
            label_field("产品名称", "一次性使用消化道脉冲电场消融导管"),
            label_field(model_key, model_value),
            label_field(date_key, date_value),
            label_field(batch_key, batch_value),
        ],
        confidence=confidence,
    )


def _label_with_optional_identity_fields(*, client: str, address: str):
    base = _core_label()
    base.fields.extend(
        [
            label_field("注册人", client, aliases=["委托方"]),
            label_field("注册人住所", address, aliases=["委托方地址"]),
        ]
    )
    return base


def _finding_by_field(result, field_name: str):
    return next(finding for finding in result.findings if finding.metadata.get("field_name") == field_name)


def _assert_single_core_mismatch(result, field_name: str, *, expected: str, actual: str) -> None:
    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "C02_FIELD_MISMATCH"
    assert finding.severity == FindingSeverity.ERROR
    assert finding.metadata["field_name"] == field_name
    assert finding.expected == expected
    assert finding.actual == actual
    assert finding.metadata["matched_label_key"]
    assert finding.metadata["ocr_confidence"] == Confidence.HIGH
    assert finding.metadata["is_sample_description_reference"] is False


def test_c02_passes_when_three_reference_fields_all_see_sample_description() -> None:
    document = base_document(labels=[_core_label()])
    document.third_page.model_spec = field("型号规格", "见 “样品描述” 栏", page=3)
    document.third_page.production_date = field("生产日期", '见"样品描述"栏', page=3)
    document.third_page.batch_or_serial = field("产品编号/批号", "见'样品描述'栏中", page=3)

    result = check_c02_third_page_extended_fields(document, CheckContext(task_id="task-c02"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["see_sample_description"] == "all"


@pytest.mark.parametrize(
    ("reference_values", "expected_fields"),
    [
        ({"model_spec": "见样品描述栏"}, ["型号规格"]),
        ({"model_spec": "见样品描述栏", "production_date": "见'样品描述'栏"}, ["型号规格", "生产日期"]),
    ],
)
def test_c02_errors_when_only_part_of_three_reference_fields_use_see_sample_description(
    reference_values: dict[str, str],
    expected_fields: list[str],
) -> None:
    document = base_document(labels=[_core_label()])
    field_names = {
        "model_spec": "型号规格",
        "production_date": "生产日期",
        "batch_or_serial": "产品编号/批号",
    }
    for attr, value in reference_values.items():
        setattr(document.third_page, attr, field(field_names[attr], value, page=3))

    result = check_c02_third_page_extended_fields(document, CheckContext(task_id="task-c02"))

    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "C02_SEE_SAMPLE_DESC_PARTIAL"
    assert result.findings[0].severity == FindingSeverity.ERROR
    assert result.findings[0].metadata["fields_using_reference"] == expected_fields


def test_c02_passes_when_core_fields_match_and_optional_identity_fields_are_unconfirmed() -> None:
    document = base_document(labels=[_core_label()])

    result = check_c02_third_page_extended_fields(document, CheckContext(task_id="task-c02"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert [item["field"] for item in result.metadata["field_results"]] == ["型号规格", "生产日期", "产品编号/批号"]
    assert result.metadata["optional_field_scope"] == "unconfirmed"


@pytest.mark.parametrize(
    ("attr", "field_name", "actual", "expected"),
    [
        ("model_spec", "型号规格", "RMC02", "RMC01"),
        ("production_date", "生产日期", "2025-12-11", "2025-12-10"),
        ("batch_or_serial", "产品编号/批号", "RMC251202", "RMC251201"),
    ],
)
def test_c02_errors_when_core_field_does_not_match_label(
    attr: str,
    field_name: str,
    actual: str,
    expected: str,
) -> None:
    document = base_document(labels=[_core_label()])
    setattr(document.third_page, attr, field(field_name, actual, page=3))

    result = check_c02_third_page_extended_fields(document, CheckContext(task_id="task-c02"))

    _assert_single_core_mismatch(result, field_name, expected=expected, actual=actual)


@pytest.mark.parametrize(
    ("date_key", "batch_key"),
    [
        ("MFG", "LOT"),
        ("MFD", "SN"),
    ],
)
def test_c02_matches_label_field_synonyms(date_key: str, batch_key: str) -> None:
    document = base_document(labels=[_core_label(model_key="型号", date_key=date_key, batch_key=batch_key)])

    result = check_c02_third_page_extended_fields(document, CheckContext(task_id="task-c02"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert all(item["matched"] for item in result.metadata["field_results"])


def test_c02_missing_label_field_outputs_warn_for_manual_review() -> None:
    document = base_document(
        labels=[
            label(
                "label-missing-date",
                caption_text="№2 一次性使用消化道脉冲电场消融导管 中文标签",
                fields=[
                    label_field("规格型号", "RMC01"),
                    label_field("批号", "RMC251201"),
                ],
            )
        ]
    )

    result = check_c02_third_page_extended_fields(document, CheckContext(task_id="task-c02"))

    assert result.status == CheckStatus.REVIEW
    assert len(result.findings) == 1
    finding = _finding_by_field(result, "生产日期")
    assert finding.code == "C02_LABEL_FIELD_MISSING"
    assert finding.severity == FindingSeverity.WARN
    assert finding.metadata["field_name"] == "生产日期"


def test_c02_low_confidence_label_outputs_warn_without_silent_pass() -> None:
    document = base_document(labels=[_core_label(confidence=Confidence.LOW)])

    result = check_c02_third_page_extended_fields(document, CheckContext(task_id="task-c02"))

    assert result.status == CheckStatus.REVIEW
    assert len(result.findings) == 1
    assert result.findings[0].code == "C02_LABEL_LOW_CONFIDENCE"
    assert result.findings[0].severity == FindingSeverity.WARN
    assert result.findings[0].metadata["ocr_confidence"] == Confidence.LOW


def test_c02_optional_client_and_address_do_not_create_error_until_scope_is_confirmed() -> None:
    document = base_document(
        labels=[
            _label_with_optional_identity_fields(
                client="标签注册人不同",
                address="标签地址不同",
            )
        ]
    )

    result = check_c02_third_page_extended_fields(document, CheckContext(task_id="task-c02"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["optional_field_scope"] == "unconfirmed"
    optional_results = {item["field"]: item for item in result.metadata["optional_field_results"]}
    assert optional_results["委托方"]["matched"] is False
    assert optional_results["委托方地址"]["matched"] is False


def test_c02_reviews_when_no_label_result_exists() -> None:
    no_label_result = check_c02_third_page_extended_fields(base_document(), CheckContext(task_id="task-c02"))
    assert no_label_result.status == CheckStatus.REVIEW
    assert no_label_result.findings[0].code == "C02_LABEL_MISSING"


def test_c02_reviews_when_third_page_core_field_missing() -> None:
    document = base_document(labels=[_core_label()])
    document.third_page.batch_or_serial = None

    result = check_c02_third_page_extended_fields(document, CheckContext(task_id="task-c02"))

    assert result.status == CheckStatus.REVIEW
    assert len(result.findings) == 1
    finding = _finding_by_field(result, "产品编号/批号")
    assert finding.code == "C02_THIRD_PAGE_FIELD_MISSING"
    assert finding.severity == FindingSeverity.WARN
    assert finding.metadata["field_name"] == "产品编号/批号"
