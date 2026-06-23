from __future__ import annotations

import re
from typing import Any

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.inspection_group import InspectionItemGroup
from app.domain.report import InspectionItem, ReportDocument
from app.domain.result import CheckResult
from app.infrastructure.report.inspection_item_group_builder import build_inspection_item_groups
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
    group_result = build_inspection_item_groups(document.inspection_items)

    for group_index, group in enumerate(group_result.groups):
        for field_name, attr in REQUIRED_FIELDS:
            if _group_has_effective_field(group, attr):
                continue

            findings.append(
                Finding(
                    id=f"{context.task_id}-c08-group-{group_index}-{attr}-empty",
                    task_id=context.task_id,
                    check_id=CHECK_ID,
                    severity=FindingSeverity.ERROR,
                    code="INSPECTION_FIELD_EMPTY",
                    message=_empty_field_message(group, field_name),
                    location=_field_location(group, field_name),
                    expected="非空值",
                    actual="",
                    evidence=_field_evidence(group, field_name, attr),
                    confidence=Confidence.HIGH,
                    metadata=_finding_metadata(group, field_name, attr),
                )
            )

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        metadata={
            "source": "inspection_item_group_builder",
            "input_row_count": len(document.inspection_items),
            "group_count": len(group_result.groups),
            "ungrouped_row_count": len(group_result.ungrouped_rows),
            "group_builder_diagnostics": group_result.diagnostics,
            "group_builder_metadata": group_result.metadata,
        },
        pass_summary="检验项目必填字段均非空",
        issue_summary=f"检验项目存在 {len(findings)} 个必填字段为空",
    )


def _group_has_effective_field(group: InspectionItemGroup, attr: str) -> bool:
    if attr == "test_result":
        return any(not is_empty_required_field(value) for value in group.effective_test_results)
    if attr == "conclusion":
        return not is_empty_required_field(group.effective_single_conclusion)
    if attr == "remark":
        return not is_empty_required_field(group.effective_remark)
    return False


def _empty_field_message(group: InspectionItemGroup, field_name: str) -> str:
    item_no = group.display_item_no or group.item_no or "未知序号"
    return f"序号 {item_no} 的{field_name}为空，已按同序号/续表行聚合后的有效字段判断。"


def _field_location(group: InspectionItemGroup, field_name: str) -> Location | None:
    first_empty_row = next(
        (row for row in group.rows if _physical_field_empty(row, _field_key_for_name(field_name))),
        None,
    )
    row = first_empty_row or (group.rows[0] if group.rows else None)
    if row is None or row.row_location is None:
        return None
    return row.row_location.model_copy(update={"column_name": field_name})


def _field_key_for_name(field_name: str) -> str:
    for required_name, attr in REQUIRED_FIELDS:
        if required_name == field_name:
            return attr
    return ""


def _field_evidence(group: InspectionItemGroup, field_name: str, attr: str) -> list[Evidence]:
    evidence_items: list[Evidence] = []
    seen_ids: set[str] = set()
    for row in group.rows:
        for evidence in row.evidence:
            if evidence.id in seen_ids:
                continue
            seen_ids.add(evidence.id)
            evidence_items.append(evidence)

    evidence_items.append(
        Evidence(
            id=f"c08-group-{_safe_id_part(group.item_no)}-{attr}",
            source_type=SourceType.REPORT,
            location=_field_location(group, field_name),
            raw_text=(
                f"序号：{group.display_item_no or group.item_no}；"
                f"行数：{len(group.rows)}；"
                f"检验结果：{' / '.join(group.effective_test_results)}；"
                f"单项结论：{group.effective_single_conclusion or ''}；"
                f"备注：{group.effective_remark or ''}"
            ),
            value="",
            method=EvidenceMethod.PDF_TEXT,
            confidence=Confidence.HIGH,
            metadata={
                "field_name": field_name,
                "field_key": attr,
                "item_no": group.display_item_no or group.item_no,
                "normalized_item_no": group.item_no,
                "pages": list(group.pages),
                "group_row_count": len(group.rows),
            },
        )
    )
    return evidence_items


def _finding_metadata(group: InspectionItemGroup, field_name: str, attr: str) -> dict[str, Any]:
    empty_rows = _empty_physical_rows(group, attr)
    return {
        "item_no": group.display_item_no or group.item_no,
        "normalized_item_no": group.item_no,
        "field_name": field_name,
        "field_key": attr,
        "group_row_count": len(group.rows),
        "pages": list(group.pages),
        "source_rows": _source_rows(group),
        "empty_physical_rows": empty_rows,
        "inherited_fields": [field.model_dump() for field in group.inherited_merged_fields],
        "suppressed_physical_row_count": max(0, len(empty_rows) - 1),
        "group_diagnostics": list(group.diagnostics),
        "continuation_markers": [marker.model_dump() for marker in group.continuation_markers],
        "effective_test_results": list(group.effective_test_results),
        "effective_single_conclusion": group.effective_single_conclusion,
        "effective_remark": group.effective_remark,
    }


def _source_rows(group: InspectionItemGroup) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row, evidence in zip(group.rows, group.source_evidence, strict=False):
        rows.append(
            {
                "source_index": evidence.get("source_index"),
                "page_number": evidence.get("page_number"),
                "row_index": evidence.get("row_index"),
                "sequence_raw": _sequence_raw(row),
                "test_result": row.test_result,
                "single_conclusion": row.conclusion,
                "remark": row.remark,
            }
        )
    return rows


def _empty_physical_rows(group: InspectionItemGroup, attr: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row, evidence in zip(group.rows, group.source_evidence, strict=False):
        if not _physical_field_empty(row, attr):
            continue
        rows.append(
            {
                "source_index": evidence.get("source_index"),
                "page_number": row.source_page,
                "row_index": row.row_index_in_page,
                "sequence_raw": _sequence_raw(row),
            }
        )
    return rows


def _physical_field_empty(row: InspectionItem, attr: str) -> bool:
    if attr == "test_result":
        if any(not is_empty_required_field(value) for value in row.result_values):
            return False
    return is_empty_required_field(getattr(row, attr, None))


def _sequence_raw(row: InspectionItem) -> str:
    if row.sequence_raw is not None:
        return row.sequence_raw
    if row.sequence is not None:
        return str(row.sequence)
    return ""


def _safe_id_part(value: str | None) -> str:
    text = value or "unknown"
    return re.sub(r"[^0-9A-Za-z_-]+", "-", text).strip("-") or "unknown"


__all__ = [
    "CHECK_ID",
    "CHECK_NAME",
    "REQUIRED_FIELDS",
    "check_c08_non_empty_fields",
    "is_empty_required_field",
]
