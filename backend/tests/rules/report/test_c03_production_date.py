from app.domain.common import Confidence
from app.domain.finding import FindingSeverity
from app.domain.result import CheckStatus
from app.rules.report.context import CheckContext
from app.rules.report.c03_production_date import check_c03_production_date, date_format_pattern

from .helpers import base_document, field, label, label_field


def _date_label(value: str | None = "2025-12-10", *, confidence: Confidence | str = Confidence.HIGH):
    fields = [label_field("产品名称", "一次性使用消化道脉冲电场消融导管")]
    if value is not None:
        fields.append(label_field("生产日期", value))
    return label(
        "label-date",
        caption_text="一次性使用消化道脉冲电场消融导管 中文标签",
        confidence=confidence,
        fields=fields,
    )


def test_c03_date_format_pattern_identifies_supported_formats() -> None:
    assert date_format_pattern("2025-12-10") == "YYYY-MM-DD"
    assert date_format_pattern("2025/12/10") == "YYYY/MM/DD"
    assert date_format_pattern("2025.12.10") == "YYYY.MM.DD"
    assert date_format_pattern("20251210") == "YYYYMMDD"
    assert date_format_pattern("2025/1/8") == "YYYY/MM/DD"
    assert date_format_pattern("生产日期待定") is None


def test_c03_skips_when_third_page_date_uses_sample_description_reference() -> None:
    document = base_document(labels=[_date_label("2025-12-10")])
    document.third_page.production_date = field("生产日期", '见"样品描述"栏', page=3)

    result = check_c03_production_date(document, CheckContext(task_id="task-c03"))

    assert result.status == CheckStatus.SKIP
    assert result.findings == []
    assert result.metadata["reason"] == "see_sample_description"


def test_c03_passes_when_date_format_matches() -> None:
    result = check_c03_production_date(
        base_document(labels=[_date_label("2025-12-10")]),
        CheckContext(task_id="task-c03"),
    )

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["compare_value_enabled"] is False
    assert result.metadata["page_format"] == "YYYY-MM-DD"
    assert result.metadata["label_format"] == "YYYY-MM-DD"


def test_c03_reports_format_mismatch_using_label_format_as_expected() -> None:
    document = base_document(labels=[_date_label("2025/12/10")])

    result = check_c03_production_date(document, CheckContext(task_id="task-c03"))

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "DATE_FORMAT_ERROR_001"
    assert finding.severity == FindingSeverity.ERROR
    assert finding.expected == "YYYY/MM/DD"
    assert finding.actual == "YYYY-MM-DD"
    assert finding.metadata["compare_value_enabled"] is False
    assert finding.metadata["page_raw_value"] == "2025-12-10"
    assert finding.metadata["label_raw_value"] == "2025/12/10"


def test_c03_treats_slash_dates_with_or_without_zero_padding_as_same_format() -> None:
    document = base_document(labels=[_date_label("2025/1/8")])
    document.third_page.production_date = field("生产日期", "2025/01/08", page=3)

    result = check_c03_production_date(document, CheckContext(task_id="task-c03"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["page_format"] == "YYYY/MM/DD"
    assert result.metadata["label_format"] == "YYYY/MM/DD"


def test_c03_does_not_emit_value_mismatch_when_only_date_value_differs() -> None:
    document = base_document(labels=[_date_label("2025-12-11")])

    result = check_c03_production_date(document, CheckContext(task_id="task-c03"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["compare_value_enabled"] is False
    assert result.metadata["page_date_value"] == "2025-12-10"
    assert result.metadata["label_date_value"] == "2025-12-11"


def test_c03_reports_missing_third_page_date_as_error() -> None:
    document = base_document(labels=[_date_label("2025-12-10")])
    document.third_page.production_date = None

    result = check_c03_production_date(document, CheckContext(task_id="task-c03"))

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "DATE_FIELD_MISSING"
    assert finding.severity == FindingSeverity.ERROR
    assert finding.metadata["missing_source"] == "third_page"


def test_c03_reviews_missing_label_date_because_ocr_evidence_is_unconfirmed() -> None:
    result = check_c03_production_date(
        base_document(labels=[_date_label(None)]),
        CheckContext(task_id="task-c03"),
    )

    assert result.status == CheckStatus.REVIEW
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "DATE_FIELD_MISSING"
    assert finding.severity == FindingSeverity.WARN
    assert finding.metadata["missing_source"] == "label_ocr"


def test_c03_reports_unparseable_date_string_as_format_error() -> None:
    document = base_document(labels=[_date_label("2025-12-10")])
    document.third_page.production_date = field("生产日期", "生产日期待定", page=3)

    result = check_c03_production_date(document, CheckContext(task_id="task-c03"))

    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "DATE_FORMAT_ERROR_001"
    assert result.findings[0].severity == FindingSeverity.ERROR
    assert result.findings[0].metadata["page_format"] is None
    assert result.findings[0].metadata["label_format"] == "YYYY-MM-DD"


def test_c03_reviews_low_confidence_label_without_silent_pass() -> None:
    low = check_c03_production_date(
        base_document(labels=[_date_label("2025-12-10", confidence=Confidence.LOW)]),
        CheckContext(task_id="task-c03"),
    )

    assert low.status == CheckStatus.REVIEW
    assert low.findings[0].code == "C03_LABEL_LOW_CONFIDENCE"
    assert low.findings[0].severity == FindingSeverity.WARN
    assert low.findings[0].metadata["ocr_confidence"] == Confidence.LOW
