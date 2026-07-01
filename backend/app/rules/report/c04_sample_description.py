from __future__ import annotations

from app.domain.common import Confidence, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.report import LabelOCRField, LabelOCRResult, ReportDocument, SampleComponent
from app.domain.result import CheckResult, CheckStatus
from app.rules.report.common import (
    component_field_value,
    component_is_supporting_equipment,
    component_not_used,
    compact,
    evidence_for_component,
    evidence_for_label,
    field_value,
    get_label_field,
    is_chinese_label,
    is_no_value,
    label_product_name,
    make_result,
    match_name,
)
from app.rules.report.context import CheckContext


CHECK_ID = "C04"
CHECK_NAME = "样品描述表格与中文标签 OCR"

_FIELDS_TO_COMPARE = ("部件名称", "规格型号", "序列号批号", "生产日期", "失效日期")
_IDENTITY_FIELDS = ("规格型号", "序列号批号", "生产日期", "失效日期")


def check_c04_sample_description(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    context = context or CheckContext()
    if not document.sample_components:
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=[],
            metadata={"coverage": []},
            pass_summary="无需要执行 C04 的样品描述部件",
            empty_status=CheckStatus.SKIP,
        )

    findings: list[Finding] = []
    coverage: list[dict[str, str | None]] = []
    for component in document.sample_components:
        if component_is_supporting_equipment(component):
            coverage.append(
                {
                    "component_id": component.component_id,
                    "label_id": None,
                    "matching_strategy": "supporting_equipment_skipped",
                }
            )
            continue
        match = _find_component_label(component, document.labels)
        label = match.label if match else None
        matching_strategy = match.strategy if match else None
        if label is None:
            findings.append(_missing_label_finding(context, component))
            coverage.append(
                {
                    "component_id": component.component_id,
                    "label_id": None,
                    "matching_strategy": None,
                }
            )
            continue

        coverage.append(
            {
                "component_id": component.component_id,
                "label_id": label.label_id,
                "matching_strategy": matching_strategy,
            }
        )
        if _label_ocr_fields_empty(label):
            findings.append(
                _ocr_evidence_insufficient_finding(
                    context=context,
                    component=component,
                    label=label,
                    matching_strategy=matching_strategy,
                )
            )
            continue
        for field_name in _FIELDS_TO_COMPARE:
            component_value = component_field_value(component, field_name)
            label_field = get_label_field(label, field_name)
            label_value = field_value(label_field)

            if is_no_value(component_value) and is_no_value(label_value):
                continue
            if _values_match_exactly(component_value, label_value):
                continue

            findings.append(
                _field_finding(
                    context=context,
                    component=component,
                    label=label,
                    label_field=label_field,
                    field_name=field_name,
                    component_value=component_value,
                    label_value=label_value,
                    matching_strategy=matching_strategy,
                )
            )

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        metadata={"coverage": coverage},
        pass_summary="样品描述表格与中文标签 OCR 一致",
        issue_summary=f"样品描述表格存在 {len(findings)} 项标签比对问题",
    )


class _LabelMatch:
    def __init__(self, label: LabelOCRResult, strategy: str) -> None:
        self.label = label
        self.strategy = strategy


def _find_component_label(component: SampleComponent, labels: list[LabelOCRResult]) -> _LabelMatch | None:
    chinese_labels = [label for label in labels if is_chinese_label(label)]
    scored_matches: list[tuple[tuple[int, int, int, int], LabelOCRResult, str]] = []
    for label in chinese_labels:
        score, strategy = _score_label(component, label)
        if score is None:
            continue
        scored_matches.append((score, label, strategy))

    if not scored_matches:
        return None

    scored_matches.sort(key=lambda item: item[0], reverse=True)
    _, label, strategy = scored_matches[0]
    return _LabelMatch(label, strategy)


def _score_label(
    component: SampleComponent,
    label: LabelOCRResult,
) -> tuple[tuple[int, int, int, int] | None, str]:
    name_match = match_name(component.component_name, label_product_name(label))
    name_score = 2 if name_match == "exact" else 1 if name_match == "partial" else 0
    identity_matches = 0
    identity_mismatches = 0
    comparable = 0

    for field_name in _IDENTITY_FIELDS:
        component_value = component_field_value(component, field_name)
        if is_no_value(component_value):
            continue
        label_value = field_value(get_label_field(label, field_name))
        if is_no_value(label_value):
            continue
        comparable += 1
        if _values_match_exactly(component_value, label_value):
            identity_matches += 1
        else:
            identity_mismatches += 1

    if name_score == 0 and identity_matches == 0:
        return None, "unmatched"

    strategy = "identity" if identity_matches and identity_mismatches == 0 else "name"
    return (identity_matches, -identity_mismatches, name_score, comparable), strategy


def _values_match_exactly(left: str | None, right: str | None) -> bool:
    if is_no_value(left) and is_no_value(right):
        return True
    if is_no_value(left) != is_no_value(right):
        return False
    return (left or "") == (right or "")


def _label_ocr_fields_empty(label: LabelOCRResult) -> bool:
    return is_chinese_label(label) and bool(label.caption_text) and len(label.fields) == 0


def _ocr_evidence_insufficient_finding(
    *,
    context: CheckContext,
    component: SampleComponent,
    label: LabelOCRResult,
    matching_strategy: str | None,
) -> Finding:
    component_name = component.component_name or component.component_id
    return Finding(
        id=f"{context.task_id}-c04-{component.component_id}-ocr-evidence-insufficient",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.WARN,
        code="OCR_EVIDENCE_INSUFFICIENT",
        message=(
            f"样品描述部件“{component_name}”已找到中文标签样张 caption，"
            "但未抽取到可比对的标签 OCR 字段，需视觉复核标签内容。"
        ),
        location=component.row_location,
        expected="可读取的中文标签字段 OCR 或视觉证据",
        actual="仅找到中文标签样张 caption，结构化 OCR 字段为空",
        evidence=[
            *evidence_for_component(component),
            *evidence_for_label(label),
        ],
        confidence=Confidence.MEDIUM,
        metadata={
            "component_id": component.component_id,
            "component_key": component.identity_key,
            "label_id": label.label_id,
            "label_key": label.label_id,
            "matched_label_key": None,
            "matched_ocr_field_count": 0,
            "label_caption_exists": True,
            "label_caption_text": label.caption_text,
            "matching_strategy": matching_strategy,
            "needs_visual_review": True,
            "user_facing_status": "needs_review",
        },
    )


def _field_finding(
    *,
    context: CheckContext,
    component: SampleComponent,
    label: LabelOCRResult,
    label_field: LabelOCRField | None,
    field_name: str,
    component_value: str | None,
    label_value: str | None,
    matching_strategy: str | None,
) -> Finding:
    code = _field_issue_code(component_value, label_value)
    severity = FindingSeverity.ERROR
    if component_not_used(component):
        code = "SAMPLE_UNUSED_COMPONENT_FIELD_WARNING"
        severity = FindingSeverity.WARN

    return Finding(
        id=f"{context.task_id}-c04-{component.component_id}-{compact(field_name)}",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=severity,
        code=code,
        message=_field_message(
            component=component,
            field_name=field_name,
            component_value=component_value,
            label_value=label_value,
            code=code,
        ),
        location=component.row_location,
        expected=label_value,
        actual=component_value,
        evidence=[
            *evidence_for_component(component),
            *evidence_for_label(label, label_field),
        ],
        confidence=Confidence.MEDIUM if severity == FindingSeverity.WARN else Confidence.HIGH,
        metadata={
            "component_id": component.component_id,
            "component_key": component.identity_key,
            "label_id": label.label_id,
            "label_key": label.label_id,
            "field_name": field_name,
            "matched_label_key": label_field.name if label_field else None,
            "ocr_confidence": _confidence_value(label_field, label),
            "matching_strategy": matching_strategy,
            "is_unused_component": component_not_used(component),
        },
    )


def _confidence_value(label_field: LabelOCRField | None, label: LabelOCRResult) -> str | None:
    confidence = label_field.confidence if label_field and label_field.confidence else label.confidence
    return str(confidence) if confidence else None


def _field_issue_code(component_value: str | None, label_value: str | None) -> str:
    if is_no_value(component_value) and not is_no_value(label_value):
        return "SAMPLE_FIELD_MISSING_IN_TABLE"
    if not is_no_value(component_value) and is_no_value(label_value):
        return "SAMPLE_FIELD_MISSING_IN_LABEL"
    return "SAMPLE_FIELD_MISMATCH"


def _field_message(
    *,
    component: SampleComponent,
    field_name: str,
    component_value: str | None,
    label_value: str | None,
    code: str,
) -> str:
    component_name = component.component_name or component.component_id
    if code == "SAMPLE_UNUSED_COMPONENT_FIELD_WARNING":
        return (
            f"样品描述部件“{component_name}”备注为本次检测未使用，"
            f"但{field_name}与中文标签 OCR 不一致：表格值“{component_value or ''}”，标签值“{label_value or ''}”"
        )
    if code == "SAMPLE_FIELD_MISSING_IN_TABLE":
        return f"样品描述部件“{component_name}”{field_name}未填写，但中文标签 OCR 有值“{label_value}”"
    if code == "SAMPLE_FIELD_MISSING_IN_LABEL":
        return f"样品描述部件“{component_name}”{field_name}为“{component_value}”，但中文标签 OCR 未识别到对应字段"
    return (
        f"样品描述部件“{component_name}”{field_name}与中文标签 OCR 不一致："
        f"表格值“{component_value or ''}”，标签值“{label_value or ''}”"
    )


def _missing_label_finding(context: CheckContext, component: SampleComponent) -> Finding:
    return Finding(
        id=f"{context.task_id}-c04-{component.component_id}-label-missing",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.WARN,
        code="SAMPLE_COMPONENT_LABEL_NOT_FOUND",
        message="未找到与样品描述部件匹配的中文标签 OCR",
        location=component.row_location,
        evidence=evidence_for_component(component),
        missing_evidence=[
            MissingEvidence(
                label=f"{component.component_name or component.component_id} 中文标签",
                reason="ReportDocument.labels 中没有匹配该样品描述部件的中文标签",
                expected_source=SourceType.REPORT,
                location=component.row_location,
            )
        ],
        confidence=Confidence.MEDIUM,
        metadata={
            "component_id": component.component_id,
            "component_key": component.identity_key,
        },
    )


__all__ = ["CHECK_ID", "CHECK_NAME", "check_c04_sample_description"]
