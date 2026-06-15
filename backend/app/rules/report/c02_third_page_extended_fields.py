from __future__ import annotations

from dataclasses import dataclass

from app.domain.common import Confidence, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.report import LabelOCRResult, ReportDocument, ReportField
from app.domain.result import CheckResult
from app.rules.report.common import (
    evidence_for_field,
    evidence_for_label,
    field_value,
    get_label_field,
    is_see_sample_description,
    make_result,
    missing_finding,
    select_label,
    values_match,
)
from app.rules.report.context import CheckContext


CHECK_ID = "C02"
CHECK_NAME = "第三页扩展字段与中文标签 OCR"


@dataclass(frozen=True)
class _ThirdPageField:
    name: str
    attr: str
    label_name: str


_REFERENCE_FIELDS = (
    _ThirdPageField("型号规格", "model_spec", "型号规格"),
    _ThirdPageField("生产日期", "production_date", "生产日期"),
    _ThirdPageField("产品编号/批号", "batch_or_serial", "产品编号/批号"),
)

_OPTIONAL_IDENTITY_FIELDS = (
    _ThirdPageField("委托方", "client", "委托方"),
    _ThirdPageField("委托方地址", "client_address", "委托方地址"),
)


def check_c02_third_page_extended_fields(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    context = context or CheckContext()

    referenced_fields = [
        spec.name
        for spec in _REFERENCE_FIELDS
        if is_see_sample_description(field_value(_third_page_field(document, spec)))
    ]
    if len(referenced_fields) == len(_REFERENCE_FIELDS):
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=[],
            metadata={
                "see_sample_description": "all",
                "fields_using_reference": referenced_fields,
                "optional_field_scope": "unconfirmed",
                "optional_field_results": [],
            },
            pass_summary="第三页型号规格、生产日期、产品编号/批号均指向样品描述栏",
        )

    if referenced_fields:
        finding = Finding(
            id=f"{context.task_id}-c02-see-sample-description-partial",
            task_id=context.task_id,
            check_id=CHECK_ID,
            severity=FindingSeverity.ERROR,
            code="C02_SEE_SAMPLE_DESC_PARTIAL",
            message="第三页仅部分扩展字段填写为见样品描述栏",
            evidence=[
                evidence
                for spec in _REFERENCE_FIELDS
                for evidence in evidence_for_field(_third_page_field(document, spec), f"c02-{spec.attr}")
            ],
            confidence=Confidence.HIGH,
            metadata={"fields_using_reference": referenced_fields},
        )
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=[finding],
            metadata={"see_sample_description": "partial", "fields_using_reference": referenced_fields},
            pass_summary="第三页扩展字段与中文标签一致",
            issue_summary="第三页见样品描述栏填写不完整",
        )

    label = select_label(document)
    if label is None:
        finding = missing_finding(
            context=context,
            check_id=CHECK_ID,
            code="C02_LABEL_MISSING",
            message="C02 未找到可用于比对的中文标签 OCR 结果",
            label="中文标签 OCR",
            reason="ReportDocument.labels 为空",
            metadata={"source": "labels"},
        )
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=[finding],
            metadata={"see_sample_description": "none"},
            pass_summary="第三页扩展字段与中文标签一致",
            issue_summary="缺少中文标签 OCR，需人工复核 C02",
        )

    if label.confidence == Confidence.LOW:
        finding = Finding(
            id=f"{context.task_id}-c02-label-low-confidence",
            task_id=context.task_id,
            check_id=CHECK_ID,
            severity=FindingSeverity.WARN,
            code="C02_LABEL_LOW_CONFIDENCE",
            message="中文标签 OCR 置信度较低，C02 需人工复核",
            evidence=evidence_for_label(label),
            confidence=Confidence.LOW,
            metadata={"label_id": label.label_id, "ocr_confidence": label.confidence},
        )
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=[finding],
            metadata={"see_sample_description": "none", "optional_field_scope": "unconfirmed"},
            pass_summary="第三页扩展字段与中文标签一致",
            issue_summary="中文标签 OCR 置信度低，需人工复核 C02",
        )

    findings: list[Finding] = []
    compared_fields: list[dict[str, object]] = []
    for index, spec in enumerate(_REFERENCE_FIELDS, start=1):
        third_field = _third_page_field(document, spec)
        page_value = field_value(third_field)
        label_field = get_label_field(label, spec.label_name)
        label_value = field_value(label_field)

        if third_field is None or page_value is None or page_value == "":
            findings.append(
                _field_missing_finding(
                    context=context,
                    index=index,
                    spec=spec,
                    code="C02_THIRD_PAGE_FIELD_MISSING",
                    reason="第三页字段缺失或为空",
                    evidence=evidence_for_label(label, label_field),
                    metadata={
                        "label_id": label.label_id,
                        "matched_label_key": label_field.name if label_field else None,
                        "ocr_confidence": label.confidence,
                        "is_sample_description_reference": False,
                    },
                )
            )
            compared_fields.append({"field": spec.name, "matched": False})
            continue

        if label_field is None or label_value is None or label_value == "":
            findings.append(
                _field_missing_finding(
                    context=context,
                    index=index,
                    spec=spec,
                    code="C02_LABEL_FIELD_MISSING",
                    reason="中文标签 OCR 未提供对应字段",
                    evidence=evidence_for_field(third_field, f"c02-{spec.attr}"),
                    actual=page_value,
                    metadata={
                        "label_id": label.label_id,
                        "matched_label_key": None,
                        "ocr_confidence": label.confidence,
                        "is_sample_description_reference": False,
                    },
                )
            )
            compared_fields.append({"field": spec.name, "matched": False})
            continue

        if not values_match(page_value, label_value):
            findings.append(
                Finding(
                    id=f"{context.task_id}-c02-{index}-mismatch",
                    task_id=context.task_id,
                    check_id=CHECK_ID,
                    severity=FindingSeverity.ERROR,
                    code="C02_FIELD_MISMATCH",
                    message=f"第三页{spec.name}与中文标签 OCR 不一致",
                    location=third_field.location,
                    expected=label_value,
                    actual=page_value,
                    evidence=[
                        *evidence_for_field(third_field, f"c02-{spec.attr}"),
                        *evidence_for_label(label, label_field),
                    ],
                    confidence=Confidence.HIGH,
                    metadata={
                        "field_name": spec.name,
                        "label_id": label.label_id,
                        "matched_label_key": label_field.name,
                        "ocr_confidence": label.confidence,
                        "is_sample_description_reference": False,
                        "third_page_raw_value": third_field.raw_value,
                        "label_raw_value": label_field.raw_value,
                    },
                )
            )
            compared_fields.append(
                {
                    "field": spec.name,
                    "matched": False,
                    "matched_label_key": label_field.name,
                    "ocr_confidence": label.confidence,
                    "is_sample_description_reference": False,
                }
            )
            continue

        compared_fields.append(
            {
                "field": spec.name,
                "matched": True,
                "matched_label_key": label_field.name,
                "ocr_confidence": label.confidence,
                "is_sample_description_reference": False,
            }
        )

    optional_field_results = _optional_identity_field_results(document, label)

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        metadata={
            "see_sample_description": "none",
            "label_id": label.label_id,
            "field_results": compared_fields,
            "optional_field_scope": "unconfirmed",
            "optional_field_results": optional_field_results,
        },
        pass_summary="第三页扩展字段与中文标签 OCR 一致",
        issue_summary=f"第三页扩展字段存在 {len(findings)} 项 OCR 比对问题",
    )


def _third_page_field(document: ReportDocument, spec: _ThirdPageField) -> ReportField | None:
    if document.third_page is None:
        return None
    field = getattr(document.third_page, spec.attr, None)
    if field is not None:
        return field
    for candidate in document.third_page.fields:
        if candidate.name == spec.name or spec.name in candidate.aliases:
            return candidate
    return None


def _field_missing_finding(
    *,
    context: CheckContext,
    index: int,
    spec: _ThirdPageField,
    code: str,
    reason: str,
    evidence: list,
    expected: str | None = None,
    actual: str | None = None,
    metadata: dict[str, object] | None = None,
) -> Finding:
    return Finding(
        id=f"{context.task_id}-c02-{index}-missing",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.WARN,
        code=code,
        message=f"C02 无法完成{spec.name}比对",
        expected=expected,
        actual=actual,
        evidence=evidence,
        missing_evidence=[
            MissingEvidence(
                label=spec.name,
                reason=reason,
                expected_source=SourceType.REPORT,
            )
        ],
        confidence=Confidence.MEDIUM,
        metadata={"field_name": spec.name, **(metadata or {})},
    )


def _optional_identity_field_results(
    document: ReportDocument,
    label: LabelOCRResult,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for spec in _OPTIONAL_IDENTITY_FIELDS:
        third_field = _third_page_field(document, spec)
        label_field = get_label_field(label, spec.label_name)
        third_value = field_value(third_field)
        label_value = field_value(label_field)
        comparable = bool(third_value) and bool(label_value)
        results.append(
            {
                "field": spec.name,
                "scope": "unconfirmed",
                "matched": values_match(third_value, label_value) if comparable else None,
                "third_page_value": third_value,
                "label_value": label_value,
                "matched_label_key": label_field.name if label_field else None,
                "ocr_confidence": label.confidence,
            }
        )
    return results


__all__ = ["CHECK_ID", "CHECK_NAME", "check_c02_third_page_extended_fields"]
