from __future__ import annotations

from datetime import date

from app.domain.common import Confidence, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.report import LabelOCRResult, ReportDocument, ReportField
from app.domain.result import CheckResult, CheckStatus
from app.rules.report.common import (
    evidence_for_field,
    evidence_for_label,
    field_value,
    get_label_field,
    is_see_sample_description,
    make_result,
    parse_date_value,
    select_label,
)
from app.rules.report.context import CheckContext


CHECK_ID = "C03"
CHECK_NAME = "生产日期格式一致性"
COMPARE_VALUE_ENABLED = False


def date_format_pattern(value: str | None) -> str | None:
    parsed_value, pattern = parse_date_value(value)
    return pattern if parsed_value is not None else None


def check_c03_production_date(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    context = context or CheckContext()
    third_field = document.third_page.production_date if document.third_page else None
    page_value = field_value(third_field)

    if is_see_sample_description(page_value):
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=[],
            metadata={"reason": "see_sample_description", "compare_value_enabled": COMPARE_VALUE_ENABLED},
            pass_summary="第三页生产日期指向样品描述栏，C03 跳过",
            empty_status=CheckStatus.SKIP,
        )

    if not page_value:
        finding = _missing_date_finding(
            context=context,
            source="third_page",
            severity=FindingSeverity.ERROR,
            message="C03 第三页生产日期缺失，无法核对格式",
            evidence=[],
        )
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=[finding],
            metadata={"compare_value_enabled": COMPARE_VALUE_ENABLED},
            pass_summary="生产日期格式一致",
            issue_summary="第三页生产日期缺失",
        )

    label = select_label(document)
    label_field = get_label_field(label, "生产日期") if label else None
    label_value = field_value(label_field)
    if label is None or label_field is None or not label_value:
        finding = _missing_date_finding(
            context=context,
            source="label_ocr",
            severity=FindingSeverity.WARN,
            message="C03 未找到中文标签中的生产日期，需人工复核格式",
            evidence=evidence_for_field(third_field, "c03-page-date"),
        )
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=[finding],
            metadata={"compare_value_enabled": COMPARE_VALUE_ENABLED},
            pass_summary="生产日期格式一致",
            issue_summary="缺少中文标签生产日期，需人工复核 C03",
        )

    if label.confidence == Confidence.LOW:
        finding = Finding(
            id=f"{context.task_id}-c03-label-low-confidence",
            task_id=context.task_id,
            check_id=CHECK_ID,
            severity=FindingSeverity.WARN,
            code="C03_LABEL_LOW_CONFIDENCE",
            message="中文标签 OCR 置信度较低，C03 需人工复核",
            evidence=evidence_for_label(label, label_field),
            confidence=Confidence.LOW,
            metadata={
                "label_id": label.label_id,
                "ocr_confidence": label.confidence,
                "compare_value_enabled": COMPARE_VALUE_ENABLED,
            },
        )
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=[finding],
            metadata={"compare_value_enabled": COMPARE_VALUE_ENABLED},
            pass_summary="生产日期格式一致",
            issue_summary="中文标签 OCR 置信度低，需人工复核 C03",
        )

    page_date, page_format = _parse_supported_date(page_value)
    label_date, label_format = _parse_supported_date(label_value)
    evidence = [
        *evidence_for_field(third_field, "c03-page-date"),
        *evidence_for_label(label, label_field),
    ]

    findings: list[Finding] = []
    if page_format is None or label_format is None or page_format != label_format:
        findings.append(
            _format_finding(
                context=context,
                third_field=third_field,
                label=label,
                label_field=label_field,
                expected=label_format,
                actual=page_format,
                page_value=page_value,
                label_value=label_value,
                page_date=page_date,
                label_date=label_date,
                evidence=evidence,
            )
        )

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        evidence=evidence,
        metadata=_result_metadata(
            page_value=page_value,
            label_value=label_value,
            page_date=page_date,
            label_date=label_date,
            page_format=page_format,
            label_format=label_format,
        ),
        pass_summary="第三页生产日期与中文标签生产日期格式一致",
        issue_summary="生产日期格式不一致或无法识别",
    )


def _parse_supported_date(value: str | None) -> tuple[date | None, str | None]:
    parsed_value, pattern = parse_date_value(value)
    if parsed_value is None:
        return None, None
    return parsed_value, pattern


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _result_metadata(
    *,
    page_value: str | None,
    label_value: str | None,
    page_date: date | None,
    label_date: date | None,
    page_format: str | None,
    label_format: str | None,
) -> dict[str, object]:
    return {
        "compare_value_enabled": COMPARE_VALUE_ENABLED,
        "page_format": page_format,
        "label_format": label_format,
        "page_raw_value": page_value,
        "label_raw_value": label_value,
        "page_date_value": _date_text(page_date),
        "label_date_value": _date_text(label_date),
    }


def _missing_date_finding(
    *,
    context: CheckContext,
    source: str,
    severity: FindingSeverity,
    message: str,
    evidence: list,
) -> Finding:
    return Finding(
        id=f"{context.task_id}-c03-{source}-date-missing",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=severity,
        code="DATE_FIELD_MISSING",
        message=message,
        evidence=evidence,
        missing_evidence=[
            MissingEvidence(
                label="生产日期",
                reason="第三页生产日期字段缺失" if source == "third_page" else "中文标签 OCR 未提供生产日期字段",
                expected_source=SourceType.REPORT,
            )
        ],
        confidence=Confidence.MEDIUM,
        metadata={"missing_source": source, "compare_value_enabled": COMPARE_VALUE_ENABLED},
    )


def _format_finding(
    *,
    context: CheckContext,
    third_field: ReportField | None,
    label: LabelOCRResult,
    label_field: ReportField,
    expected: str | None,
    actual: str | None,
    page_value: str | None,
    label_value: str | None,
    page_date: date | None,
    label_date: date | None,
    evidence: list,
) -> Finding:
    return Finding(
        id=f"{context.task_id}-c03-format-error",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code="DATE_FORMAT_ERROR_001",
        message="第三页生产日期与中文标签生产日期格式不一致或无法识别",
        location=third_field.location if third_field else None,
        expected=expected,
        actual=actual,
        evidence=evidence,
        confidence=Confidence.HIGH,
        metadata={
            **_result_metadata(
                page_value=page_value,
                label_value=label_value,
                page_date=page_date,
                label_date=label_date,
                page_format=actual,
                label_format=expected,
            ),
            "label_id": label.label_id,
            "matched_label_key": label_field.name,
        },
    )


__all__ = ["CHECK_ID", "CHECK_NAME", "check_c03_production_date", "date_format_pattern"]
