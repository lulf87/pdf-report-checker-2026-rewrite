from __future__ import annotations

import re
from typing import Any

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.report import InspectionItem, ReportDocument
from app.domain.result import CheckResult
from app.rules.report.common import make_result
from app.rules.report.context import CheckContext


CHECK_ID = "C08"
CHECK_NAME = "检验项目非空字段"

REQUIRED_FIELDS: tuple[tuple[str, str], ...] = (
    ("检验结果", "test_result"),
    ("单项结论", "conclusion"),
    ("备注", "remark"),
)


def is_empty_required_field(value: str | None) -> bool:
    return value is None or not str(value).strip()


def check_c08_non_empty_fields(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    context = context or CheckContext()
    findings: list[Finding] = []

    for item_index, item in enumerate(document.inspection_items):
        for field_name, attr in REQUIRED_FIELDS:
            value = getattr(item, attr)
            if not is_empty_required_field(value):
                continue

            is_merged_cell = _is_merged_field(item, attr)
            findings.append(
                Finding(
                    id=f"{context.task_id}-c08-row-{item_index}-{attr}-empty",
                    task_id=context.task_id,
                    check_id=CHECK_ID,
                    severity=FindingSeverity.ERROR,
                    code="INSPECTION_MERGED_FIELD_EMPTY" if is_merged_cell else "INSPECTION_FIELD_EMPTY",
                    message=_empty_field_message(item, field_name, is_merged_cell),
                    location=_field_location(item, field_name),
                    expected="非空值",
                    actual=value or "",
                    evidence=_field_evidence(item, field_name, attr, value),
                    confidence=Confidence.HIGH,
                    metadata={
                        "item_no": _item_no(item),
                        "normalized_item_no": _normalized_item_no(item),
                        "row_index": item.row_index_in_page,
                        "field_name": field_name,
                        "field_key": attr,
                        "is_merged_cell": is_merged_cell,
                        "value_provenance": _field_provenance(item, attr),
                        "source_page": item.source_page,
                    },
                )
            )

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        pass_summary="检验项目必填字段均非空",
        issue_summary=f"检验项目存在 {len(findings)} 个必填字段为空",
    )


def _item_no(item: InspectionItem) -> str:
    raw = (item.sequence_raw or "").strip()
    if raw:
        return raw
    if item.sequence is not None:
        return str(item.sequence)
    return ""


def _normalized_item_no(item: InspectionItem) -> str | None:
    text = _item_no(item)
    match = re.search(r"\d+", text)
    if match:
        return match.group(0)
    return None


def _field_provenance(item: InspectionItem, attr: str) -> str | None:
    return item.field_provenance.get(attr) or item.field_provenance.get(_legacy_field_key(attr))


def _legacy_field_key(attr: str) -> str:
    if attr == "conclusion":
        return "item_conclusion"
    return attr


def _is_merged_field(item: InspectionItem, attr: str) -> bool:
    provenance = _field_provenance(item, attr) or ""
    if provenance.startswith("merge"):
        return True

    merged_fields = item.metadata.get("merged_fields")
    if isinstance(merged_fields, dict):
        return bool(merged_fields.get(attr) or merged_fields.get(_legacy_field_key(attr)))
    if isinstance(merged_fields, (list, tuple, set)):
        return attr in merged_fields or _legacy_field_key(attr) in merged_fields
    return False


def _empty_field_message(item: InspectionItem, field_name: str, is_merged_cell: bool) -> str:
    item_no = _item_no(item) or "空序号行"
    row = item.row_index_in_page if item.row_index_in_page is not None else "未知行"
    if is_merged_cell:
        return f"序号 {item_no} 第 {row} 行的{field_name}为空，合并单元格首行为空导致该字段无有效值。"
    return f"序号 {item_no} 第 {row} 行的{field_name}为空。"


def _field_location(item: InspectionItem, field_name: str) -> Location | None:
    if item.row_location is None:
        return None
    return item.row_location.model_copy(update={"column_name": field_name})


def _field_evidence(item: InspectionItem, field_name: str, attr: str, value: Any) -> list[Evidence]:
    evidence_items = list(item.evidence)
    evidence_items.append(
        Evidence(
            id=f"c08-{item.source_page or 'p'}-{item.row_index_in_page if item.row_index_in_page is not None else 'r'}-{attr}",
            source_type=SourceType.REPORT,
            location=_field_location(item, field_name),
            raw_text=(
                f"序号：{_item_no(item)}；"
                f"检验结果：{item.test_result or ''}；"
                f"单项结论：{item.conclusion or ''}；"
                f"备注：{item.remark or ''}"
            ),
            value="" if value is None else str(value),
            method=EvidenceMethod.PDF_TEXT,
            confidence=Confidence.HIGH,
            metadata={
                "field_name": field_name,
                "field_key": attr,
                "value_provenance": _field_provenance(item, attr),
                "is_merged_cell": _is_merged_field(item, attr),
            },
        )
    )
    return evidence_items


__all__ = [
    "CHECK_ID",
    "CHECK_NAME",
    "REQUIRED_FIELDS",
    "check_c08_non_empty_fields",
    "is_empty_required_field",
]
