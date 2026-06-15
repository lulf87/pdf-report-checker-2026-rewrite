from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from typing import Any

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.report import InspectionItem, LabelOCRField, LabelOCRResult, ReportDocument, ReportField, SampleComponent
from app.domain.result import CheckResult, CheckStatus
from app.rules.report.context import CheckContext


NO_VALUE_MARKERS = {"", "/", "／", "-", "—", "——", "见实物"}
PLACEHOLDER_MARKERS = {"/", "／", "-", "—", "——"}
CHINESE_LABEL_KEYWORDS = ("中文标签", "中文标签样张", "标签样张", "铭牌", "标牌")
LABEL_WORDS = ("标签", "中文标签", "标签样张", "中文标签样张", "包装标签")
PHOTO_WORDS = ("照片", "图片", "外观", "检品外观")
SEE_SAMPLE_DESCRIPTION_PATTERN = re.compile(r"见\s*[\"'“”‘’]?\s*样品描述\s*[\"'“”‘’]?\s*栏")

LABEL_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "部件名称": ("部件名称", "产品名称", "样品名称", "名称", "器械名称", "品名"),
    "样品名称": ("样品名称", "产品名称", "部件名称", "名称", "器械名称", "品名"),
    "型号规格": ("型号规格", "规格型号", "型号/规格", "型号", "规格", "Model", "Spec"),
    "规格型号": ("规格型号", "型号规格", "型号/规格", "型号", "规格", "Model", "Spec"),
    "生产日期": ("生产日期", "MFG", "MFD", "制造日期", "Manufacturing Date"),
    "产品编号/批号": ("产品编号/批号", "批号/序列号", "序列号/批号", "批号", "序列号", "LOT", "SN"),
    "序列号批号": ("序列号批号", "产品编号/批号", "批号/序列号", "序列号/批号", "批号", "序列号", "LOT", "SN"),
    "委托方": ("委托方", "注册人", "注册人名称", "制造商"),
    "委托方地址": ("委托方地址", "注册人住所", "注册人地址", "制造商地址"),
    "失效日期": ("失效日期", "有效期至", "EXP", "有效期", "Expiration Date"),
}


def field_value(field: ReportField | None) -> str | None:
    if field is None:
        return None
    if field.value is not None:
        return field.value
    if field.raw_value is not None:
        return field.raw_value
    return field.normalized_value


def compact(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip()).replace("／", "/")


def is_no_value(value: str | None) -> bool:
    return compact(value) in NO_VALUE_MARKERS


def is_see_sample_description(value: str | None) -> bool:
    return bool(SEE_SAMPLE_DESCRIPTION_PATTERN.search(value or ""))


def is_required_empty(value: str | None) -> bool:
    return value is None or not str(value).strip()


def normalize_name(value: str | None) -> str:
    text = compact(value)
    text = re.sub(r"^(?:№|No\.?|编号)?\s*\d+[\s、:：.-]*", "", text, flags=re.IGNORECASE)
    for word in ("正面", "背面", "侧面", "局部", "整体", *LABEL_WORDS, *PHOTO_WORDS):
        if text.endswith(word) and len(text) > len(word):
            text = text[: -len(word)]
    return text


def match_name(left: str | None, right: str | None) -> str | None:
    left_norm = normalize_name(left)
    right_norm = normalize_name(right)
    if not left_norm or not right_norm:
        return None
    if left_norm == right_norm:
        return "exact"
    if left_norm in right_norm or right_norm in left_norm:
        return "partial"
    return None


def component_not_used(component: SampleComponent) -> bool:
    return "本次检测未使用" in (component.remark or "")


def evidence_for_field(field: ReportField | None, fallback_id: str) -> list[Evidence]:
    if field is None:
        return []
    if field.evidence:
        return field.evidence
    value = field_value(field)
    if value is None:
        return []
    return [
        Evidence(
            id=f"ev-{fallback_id}",
            source_type=SourceType.REPORT,
            location=field.location,
            raw_text=field.raw_value,
            normalized_text=field.normalized_value,
            value=field.value or value,
            method=EvidenceMethod.PDF_TEXT,
            confidence=field.confidence,
        )
    ]


def evidence_for_component(component: SampleComponent) -> list[Evidence]:
    if component.evidence:
        return component.evidence
    return [
        Evidence(
            id=f"ev-component-{component.component_id}",
            source_type=SourceType.REPORT,
            location=component.row_location,
            raw_text=component.component_name,
            value=component.component_name,
            method=EvidenceMethod.PDF_TEXT,
        )
    ]


def evidence_for_label(label: LabelOCRResult, field: LabelOCRField | None = None) -> list[Evidence]:
    if field and field.evidence:
        return field.evidence
    if label.evidence:
        return label.evidence
    return [
        Evidence(
            id=f"ev-label-{label.label_id}",
            source_type=SourceType.REPORT,
            location=Location(source_type=SourceType.REPORT, page_number=label.page_number),
            raw_text=label.caption_text or "\n".join(label.raw_blocks),
            method=EvidenceMethod.OCR,
            confidence=label.confidence,
            image_ref=label.image_ref,
        )
    ]


def field_names_for(standard_name: str) -> set[str]:
    names = {standard_name, *LABEL_FIELD_ALIASES.get(standard_name, ())}
    return {compact(name).lower() for name in names}


def get_label_field(label: LabelOCRResult, standard_name: str) -> LabelOCRField | None:
    aliases = field_names_for(standard_name)
    for field in label.fields:
        names = {field.name, *field.aliases}
        if any(compact(name).lower() in aliases for name in names):
            return field
    return None


def get_label_value(label: LabelOCRResult, standard_name: str) -> str | None:
    return field_value(get_label_field(label, standard_name))


def is_chinese_label(label: LabelOCRResult) -> bool:
    caption = label.caption_text or ""
    return any(keyword in caption for keyword in CHINESE_LABEL_KEYWORDS)


def select_label(document: ReportDocument) -> LabelOCRResult | None:
    chinese_labels = [label for label in document.labels if is_chinese_label(label)]
    return chinese_labels[0] if chinese_labels else (document.labels[0] if document.labels else None)


def label_product_name(label: LabelOCRResult) -> str | None:
    return get_label_value(label, "部件名称") or get_label_value(label, "样品名称") or label.caption_text


def values_match(left: str | None, right: str | None, *, allow_date_separator_equivalence: bool = True) -> bool:
    if is_no_value(left) and is_no_value(right):
        return True
    if is_no_value(left) != is_no_value(right):
        return False
    left_text = left or ""
    right_text = right or ""
    if allow_date_separator_equivalence:
        left_digits = re.sub(r"\D", "", left_text)
        right_digits = re.sub(r"\D", "", right_text)
        if len(left_digits) == 8 and len(right_digits) == 8:
            return left_digits == right_digits
    return compact(left_text).upper() == compact(right_text).upper()


def component_field_value(component: SampleComponent, field_name: str) -> str | None:
    if field_name == "部件名称":
        return component.component_name
    if field_name in {"规格型号", "型号规格"}:
        return component.model
    if field_name in {"序列号批号", "产品编号/批号"}:
        return component.batch_or_serial
    if field_name == "生产日期":
        return component.production_date
    if field_name == "失效日期":
        return component.expiration_date
    return None


def component_matches_label(component: SampleComponent, label: LabelOCRResult) -> bool:
    if match_name(component.component_name, label_product_name(label)):
        name_ok = True
    else:
        name_ok = False

    comparable = 0
    for field_name in ("规格型号", "序列号批号", "生产日期", "失效日期"):
        component_value = component_field_value(component, field_name)
        if is_no_value(component_value):
            continue
        label_value = get_label_value(label, field_name)
        if is_no_value(label_value):
            continue
        comparable += 1
        if not values_match(component_value, label_value):
            return False
    return comparable > 0 or name_ok


def result_status(findings: list[Finding], *, empty_status: CheckStatus = CheckStatus.PASS) -> CheckStatus:
    if any(finding.severity == FindingSeverity.ERROR for finding in findings):
        return CheckStatus.FAIL
    if any(finding.severity == FindingSeverity.WARN for finding in findings):
        return CheckStatus.REVIEW
    return empty_status


def make_result(
    *,
    context: CheckContext,
    check_id: str,
    check_name: str,
    findings: list[Finding],
    evidence: list[Evidence] | None = None,
    metadata: dict[str, Any] | None = None,
    pass_summary: str,
    issue_summary: str | None = None,
    empty_status: CheckStatus = CheckStatus.PASS,
) -> CheckResult:
    status = result_status(findings, empty_status=empty_status)
    return CheckResult(
        task_id=context.task_id,
        check_id=check_id,
        check_name=check_name,
        status=status,
        summary=pass_summary if status in {CheckStatus.PASS, CheckStatus.SKIP} else issue_summary or f"{check_id} 发现 {len(findings)} 项问题",
        findings=findings,
        evidence=dedupe_evidence(evidence or []),
        metadata=metadata or {},
    )


def dedupe_evidence(evidence_items: list[Evidence]) -> list[Evidence]:
    seen: set[str] = set()
    result: list[Evidence] = []
    for item in evidence_items:
        if item.id in seen:
            continue
        seen.add(item.id)
        result.append(item)
    return result


def missing_finding(
    *,
    context: CheckContext,
    check_id: str,
    code: str,
    message: str,
    label: str,
    reason: str,
    location: Location | None = None,
    metadata: dict[str, Any] | None = None,
) -> Finding:
    return Finding(
        id=f"{context.task_id}-{check_id.lower()}-{code.lower()}-{len(label)}",
        task_id=context.task_id,
        check_id=check_id,
        severity=FindingSeverity.WARN,
        code=code,
        message=message,
        location=location,
        missing_evidence=[
            MissingEvidence(
                label=label,
                reason=reason,
                expected_source=SourceType.REPORT,
                location=location,
            )
        ],
        confidence=Confidence.MEDIUM,
        metadata=metadata or {},
    )


def group_inspection_items(items: Iterable[InspectionItem]) -> list[tuple[int, list[InspectionItem]]]:
    groups: dict[int, list[InspectionItem]] = defaultdict(list)
    order: list[int] = []
    current: int | None = None
    for item in items:
        seq = item.sequence
        if seq is None:
            raw = item.sequence_raw or ""
            match = re.search(r"(\d+)", raw)
            seq = int(match.group(1)) if match else None
        if seq is not None:
            current = seq
            if seq not in groups:
                order.append(seq)
            groups[seq].append(item)
            continue
        if current is not None and any((value or "").strip() for value in (item.test_result, item.conclusion, item.remark, item.standard_requirement)):
            groups[current].append(item)
    return [(seq, groups[seq]) for seq in order]


def parse_date_value(value: str | None) -> tuple[date | None, str | None]:
    text = (value or "").strip()
    patterns = [
        (re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$"), "YYYY-MM-DD"),
        (re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$"), "YYYY/MM/DD"),
        (re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$"), "YYYY.MM.DD"),
        (re.compile(r"^(\d{4})(\d{2})(\d{2})$"), "YYYYMMDD"),
    ]
    for pattern, fmt in patterns:
        match = pattern.match(text)
        if not match:
            continue
        year, month, day = [int(part) for part in match.groups()]
        try:
            return date(year, month, day), fmt
        except ValueError:
            return None, fmt
    return None, None
