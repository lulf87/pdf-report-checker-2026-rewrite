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
from app.rules.report.explanation_details import (
    comparison_row,
    decision_detail,
    evidence_group,
    evidence_item,
    explanation_details,
    source_section,
)


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
    detail_rows: list[dict[str, object]] = []
    label_items: list[dict[str, object]] = []
    component_items: list[dict[str, object]] = []
    for component in document.sample_components:
        component_items.append(
            evidence_item(
                label=component.component_name or component.component_id,
                page_number=component.row_location.page_number if component.row_location else None,
                evidence_type="sample_component",
                status=_component_role(component),
            )
        )
        if component_is_supporting_equipment(component):
            coverage.append(
                {
                    "component_id": component.component_id,
                    "label_id": None,
                    "matching_strategy": "supporting_equipment_skipped",
                }
            )
            detail_rows.append(
                comparison_row(
                    field=component.component_name or component.component_id,
                    left_label="样品描述",
                    left_value=_component_summary(component),
                    right_label="C04 适用范围",
                    right_value=None,
                    status="not_applicable",
                    reason="该行来自本次检验配合使用设备表，不按主样品标签字段一致性判错。",
                )
            )
            continue
        match = _find_component_label(component, document.labels)
        label = match.label if match else None
        matching_strategy = match.strategy if match else None
        if label is None:
            findings.append(_missing_label_finding(context, component))
            detail_rows.append(
                comparison_row(
                    field=component.component_name or component.component_id,
                    left_label="样品描述",
                    left_value=_component_summary(component),
                    right_label="中文标签 caption/OCR",
                    right_value=None,
                    status="missing",
                    reason="未找到与该样品描述部件匹配的中文标签 caption 或 OCR。",
                )
            )
            coverage.append(
                {
                    "component_id": component.component_id,
                    "label_id": None,
                    "matching_strategy": None,
                }
            )
            continue

        label_items.append(
            evidence_item(
                label=label.caption_text or label.label_id,
                page_number=label.page_number,
                evidence_type="label_caption",
                status="matched",
            )
        )
        coverage.append(
            {
                "component_id": component.component_id,
                "label_id": label.label_id,
                "matching_strategy": matching_strategy,
            }
        )
        if _label_ocr_fields_empty(label):
            for field_name in _FIELDS_TO_COMPARE:
                detail_rows.append(
                    comparison_row(
                        field=field_name,
                        left_label=f"样品描述：{component.component_name or component.component_id}",
                        left_value=component_field_value(component, field_name),
                        right_label="中文标签 OCR",
                        right_value=None,
                        status="needs_review",
                        reason="标签样张存在，但 OCR 未抽取到可比对字段，需视觉复核。",
                    )
                )
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
            detail_rows.append(
                comparison_row(
                    field=field_name,
                    left_label=f"样品描述：{component.component_name or component.component_id}",
                    left_value=component_value,
                    right_label="中文标签 OCR",
                    right_value=label_value,
                    status=_field_status(component_value, label_value),
                    reason=_field_reason(component_value, label_value, matching_strategy),
                )
            )

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
        metadata={
            "coverage": coverage,
            "explanation_details": _build_explanation_details(
                document=document,
                findings=findings,
                detail_rows=detail_rows,
                component_items=component_items,
                label_items=label_items,
            ),
        },
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


def _build_explanation_details(
    *,
    document: ReportDocument,
    findings: list[Finding],
    detail_rows: list[dict[str, object]],
    component_items: list[dict[str, object]],
    label_items: list[dict[str, object]],
) -> dict[str, object]:
    status, label, reason = _decision_from_findings(findings, "样品描述部件与中文标签 OCR 一致。")
    source_pages = sorted(
        {
            component.row_location.page_number
            for component in document.sample_components
            if component.row_location and component.row_location.page_number is not None
        }
    )
    label_pages = sorted({label.page_number for label in document.labels if label.page_number is not None})
    sources = [
        source_section(
            label="样品描述表",
            page_number=source_pages[0] if source_pages else None,
            description="样品描述部件行，含部件名称、型号、序列号/批号、生产日期和备注。",
        )
    ]
    if label_pages:
        sources.append(
            source_section(
                label="中文标签 OCR/样张 caption",
                page_number=label_pages[0],
                description="中文标签样张 caption 及结构化 OCR 字段。",
            )
        )
    return explanation_details(
        check_goal="核对样品描述字段与中文标签字段是否一致。",
        user_question="样品描述行匹配到了哪个中文标签？哪些字段参与比对？",
        overall_reason=reason,
        source_sections=sources,
        comparison_rows=detail_rows,
        evidence_groups=[
            evidence_group("样品描述部件", component_items),
            evidence_group("匹配到的中文标签样张", label_items),
        ],
        decision=decision_detail(status, label, reason),
        next_action="如显示需视觉复核，请查看匹配到的中文标签样张图片和 OCR 字段。",
    )


def _decision_from_findings(findings: list[Finding], pass_reason: str) -> tuple[str, str, str]:
    if not findings:
        return "passed", "通过", pass_reason
    if any(finding.severity == FindingSeverity.ERROR for finding in findings):
        return "candidate_issue", "候选问题", f"规则发现 {len(findings)} 项候选标签比对问题，需结合最终审核确认。"
    return "needs_review", "需复核", f"规则发现 {len(findings)} 项证据不足或需视觉复核项。"


def _component_role(component: SampleComponent) -> str:
    if component_is_supporting_equipment(component):
        return "supporting_equipment"
    if component_not_used(component):
        return "unused_component"
    return "main_sample"


def _component_summary(component: SampleComponent) -> str:
    values = [
        component.component_name,
        component.model,
        component.batch_or_serial,
        component.production_date,
        component.expiration_date,
        component.remark,
    ]
    return " / ".join(value for value in values if value)


def _field_status(component_value: str | None, label_value: str | None) -> str:
    if _values_match_exactly(component_value, label_value):
        return "match"
    if is_no_value(component_value) or is_no_value(label_value):
        return "missing"
    return "mismatch"


def _field_reason(component_value: str | None, label_value: str | None, matching_strategy: str | None) -> str:
    if _values_match_exactly(component_value, label_value):
        return f"两处字段一致，匹配策略：{matching_strategy or '未标注'}。"
    if is_no_value(label_value):
        return "中文标签 OCR 未抽取到该字段。"
    if is_no_value(component_value):
        return "样品描述表未填写该字段。"
    return "样品描述表与中文标签 OCR 字段不一致。"


__all__ = ["CHECK_ID", "CHECK_NAME", "check_c04_sample_description"]
