from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.domain.common import Confidence, Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.inspection_group import InspectionItemGroup
from app.domain.report import InspectionItem, ReportDocument
from app.domain.result import CheckResult
from app.infrastructure.report.inspection_item_group_builder import build_inspection_item_groups
from app.rules.report.common import make_result
from app.rules.report.context import CheckContext


CHECK_ID = "C10"
CHECK_NAME = "续表标记"

_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


@dataclass(frozen=True)
class _GroupRow:
    item: InspectionItem
    source_index: int
    page: int
    row_index: int
    item_no: str
    continuation_number: int | None

    @property
    def has_continuation_marker(self) -> bool:
        return self.continuation_number is not None


def check_c10_continuation(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    context = context or CheckContext()
    group_result = build_inspection_item_groups(document.inspection_items)
    missing_context_rows = _missing_context_rows(document.inspection_items)

    if missing_context_rows:
        findings = [_context_missing_finding(context, document.inspection_items, missing_context_rows)]
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=findings,
            metadata={
                "missing_context_rows": missing_context_rows,
                "boundary_uncertain": True,
                "group_builder_diagnostics": group_result.diagnostics,
            },
            pass_summary="续表标记位置正确",
            issue_summary="续表标记缺少页码或页内行号信息，需人工复核",
        )

    findings: list[Finding] = []
    emitted_keys: set[tuple[str, str]] = set()

    for group in group_result.groups:
        _append_group_boundary_findings(context, group, findings, emitted_keys)

    for finding in _standalone_page_first_marker_findings(context, group_result.groups):
        _append_once(findings, emitted_keys, finding)

    checked_pages = sorted({page for group in group_result.groups for page in group.pages})
    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        metadata={
            "pages_checked": checked_pages,
            "group_count": len(group_result.groups),
            "ungrouped_row_count": len(group_result.ungrouped_rows),
            "group_builder_diagnostics": group_result.diagnostics,
        },
        pass_summary="续表标记位置正确",
        issue_summary=f"续表标记存在 {len(findings)} 项问题",
    )


def _append_group_boundary_findings(
    context: CheckContext,
    group: InspectionItemGroup,
    findings: list[Finding],
    emitted_keys: set[tuple[str, str]],
) -> None:
    group_rows = _group_rows(group)
    if not group_rows:
        return

    page_rows = _group_rows_by_page(group_rows)
    pages = list(page_rows)

    for page_index, page in enumerate(pages):
        rows_on_page = page_rows[page]
        first_row = rows_on_page[0]
        later_markers = [row for row in rows_on_page[1:] if row.has_continuation_marker]
        if not later_markers:
            continue

        previous_page = pages[page_index - 1] if page_index > 0 else page
        marker_row = later_markers[0]
        finding = _continuation_finding(
            context,
            group=group,
            row=marker_row,
            code="CONTINUATION_MARK_ERROR_002",
            message="续字只能出现在本页第一条相关检验项目行的序号中。",
            expected="续字只能出现在本页第一行",
            actual=_item_no(marker_row.item),
            previous_page=previous_page,
            current_page=page,
            current_page_rows=rows_on_page,
            first_related_row=first_row,
            marker_row=marker_row,
        )
        _append_once(findings, emitted_keys, finding)

    if len(pages) <= 1:
        return

    for previous_page, current_page in zip(pages, pages[1:], strict=False):
        current_page_rows = page_rows[current_page]
        first_related_row = current_page_rows[0]
        marker_rows = [row for row in current_page_rows if row.has_continuation_marker]

        if first_related_row.has_continuation_marker:
            if _marker_item_no(first_related_row) != group.item_no:
                finding = _continuation_finding(
                    context,
                    group=group,
                    row=first_related_row,
                    code="CONTINUATION_MARK_MISMATCH",
                    message=(
                        f"续表标记与当前检验项目序号不一致：应写为“续{group.item_no}”，"
                        f"实际为“{_item_no(first_related_row.item)}”。"
                    ),
                    expected=f"续{group.item_no}",
                    actual=_item_no(first_related_row.item),
                    previous_page=previous_page,
                    current_page=current_page,
                    current_page_rows=current_page_rows,
                    first_related_row=first_related_row,
                    marker_row=first_related_row,
                )
                _append_once(findings, emitted_keys, finding)
            continue

        if marker_rows:
            marker_row = marker_rows[0]
            finding = _continuation_finding(
                context,
                group=group,
                row=marker_row,
                code="CONTINUATION_MARK_ERROR_002",
                message="续字只能出现在本页第一条相关检验项目行的序号中。",
                expected="续字只能出现在本页第一行",
                actual=_item_no(marker_row.item),
                previous_page=previous_page,
                current_page=current_page,
                current_page_rows=current_page_rows,
                first_related_row=first_related_row,
                marker_row=marker_row,
            )
            _append_once(findings, emitted_keys, finding)
            continue

        finding = _continuation_finding(
            context,
            group=group,
            row=first_related_row,
            code="CONTINUATION_MARK_ERROR_001",
            message=f"跨页续表当前页首条相关行缺少续表标记，应写为“续{group.item_no}”。",
            expected=f"续{group.item_no}",
            actual=_item_no(first_related_row.item),
            previous_page=previous_page,
            current_page=current_page,
            current_page_rows=current_page_rows,
            first_related_row=first_related_row,
            marker_row=None,
        )
        _append_once(findings, emitted_keys, finding)


def _standalone_page_first_marker_findings(
    context: CheckContext,
    groups: list[InspectionItemGroup],
) -> list[Finding]:
    findings: list[Finding] = []
    all_rows = _all_group_rows(groups)
    rows_by_page = _group_rows_by_page(all_rows)
    pages = list(rows_by_page)
    group_by_source_index = _group_by_source_index(groups)

    for page_index, page in enumerate(pages):
        first_row = rows_by_page[page][0]
        if not first_row.has_continuation_marker:
            continue

        group = group_by_source_index.get(first_row.source_index)
        if group is not None and any(previous_page < page for previous_page in group.pages):
            continue

        previous_tail = rows_by_page[pages[page_index - 1]][-1] if page_index > 0 else None
        if previous_tail is not None and _marker_item_no(first_row) == previous_tail.item_no:
            continue

        expected_item_no = previous_tail.item_no if previous_tail is not None else None
        expected = f"续{expected_item_no}" if expected_item_no is not None else "不应出现续表标记"
        boundary_item_no = expected_item_no or first_row.item_no
        previous_page = previous_tail.page if previous_tail is not None else page
        evidence_rows = [row for row in (previous_tail, first_row) if row is not None]
        synthetic_group = group or _group_for_single_marker(first_row)
        findings.append(
            _continuation_finding(
                context,
                group=synthetic_group,
                row=first_row,
                code="CONTINUATION_MARK_MISMATCH",
                message=(
                    f"续表标记与上一页末尾序号不一致：应写为“{expected}”，"
                    f"实际为“{_item_no(first_row.item)}”。"
                ),
                expected=expected,
                actual=_item_no(first_row.item),
                previous_page=previous_page,
                current_page=page,
                current_page_rows=[first_row],
                first_related_row=first_row,
                marker_row=first_row,
                boundary_item_no=boundary_item_no,
                extra_source_rows=evidence_rows,
            )
        )
    return findings


def _append_once(
    findings: list[Finding],
    emitted_keys: set[tuple[str, str]],
    finding: Finding,
) -> None:
    key = (finding.code, str(finding.metadata.get("boundary_key") or finding.id))
    if key in emitted_keys:
        return
    emitted_keys.add(key)
    findings.append(finding)


def is_continuation_no(value: int | str | None) -> int | None:
    if value is None:
        return None
    text = re.sub(r"\s+", "", str(value).strip()).translate(_FULLWIDTH_DIGITS)
    match = re.fullmatch(r"续(\d+)", text)
    return int(match.group(1)) if match else None


def _missing_context_rows(items: list[InspectionItem]) -> list[int]:
    return [
        position
        for position, item in enumerate(items)
        if item.source_page is None or item.row_index_in_page is None
    ]


def _group_rows(group: InspectionItemGroup) -> list[_GroupRow]:
    rows: list[_GroupRow] = []
    for item, source_evidence in zip(group.rows, group.source_evidence, strict=False):
        if item.source_page is None or item.row_index_in_page is None:
            continue
        rows.append(
            _GroupRow(
                item=item,
                source_index=int(source_evidence.get("source_index") or 0),
                page=item.source_page,
                row_index=item.row_index_in_page,
                item_no=group.item_no,
                continuation_number=is_continuation_no(item.sequence_raw),
            )
        )
    return sorted(rows, key=lambda row: (row.page, row.row_index, row.source_index))


def _all_group_rows(groups: list[InspectionItemGroup]) -> list[_GroupRow]:
    rows: list[_GroupRow] = []
    for group in groups:
        rows.extend(_group_rows(group))
    return sorted(rows, key=lambda row: (row.page, row.row_index, row.source_index))


def _group_by_source_index(groups: list[InspectionItemGroup]) -> dict[int, InspectionItemGroup]:
    mapping: dict[int, InspectionItemGroup] = {}
    for group in groups:
        for source_evidence in group.source_evidence:
            source_index = source_evidence.get("source_index")
            if isinstance(source_index, int):
                mapping[source_index] = group
    return mapping


def _group_for_single_marker(row: _GroupRow) -> InspectionItemGroup:
    return InspectionItemGroup(
        item_no=row.item_no,
        display_item_no=_item_no(row.item),
        rows=[row.item],
        pages=[row.page],
        source_evidence=[
            {
                "source_index": row.source_index,
                "page_number": row.page,
                "row_index": row.row_index,
                "item_no": _item_no(row.item),
                "normalized_item_no": row.item_no,
            }
        ],
    )


def _group_rows_by_page(rows: list[_GroupRow]) -> dict[int, list[_GroupRow]]:
    grouped: dict[int, list[_GroupRow]] = {}
    for row in sorted(rows, key=lambda value: (value.page, value.row_index, value.source_index)):
        grouped.setdefault(row.page, []).append(row)
    return grouped


def _marker_item_no(row: _GroupRow) -> str | None:
    if row.continuation_number is None:
        return None
    return str(row.continuation_number)


def _continuation_finding(
    context: CheckContext,
    *,
    group: InspectionItemGroup,
    row: _GroupRow,
    code: str,
    message: str,
    expected: object,
    actual: object,
    previous_page: int,
    current_page: int,
    current_page_rows: list[_GroupRow],
    first_related_row: _GroupRow,
    marker_row: _GroupRow | None,
    boundary_item_no: str | None = None,
    extra_source_rows: list[_GroupRow] | None = None,
) -> Finding:
    item_no = boundary_item_no or group.item_no
    boundary_key = f"{item_no}:{previous_page}->{current_page}"
    return Finding(
        id=f"{context.task_id}-c10-{code.lower()}-{boundary_key}-{row.row_index}-{row.source_index}",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code=code,
        message=message,
        location=row.item.row_location,
        expected=expected,
        actual=actual,
        evidence=_row_evidence(*(extra_source_rows or current_page_rows)),
        confidence=Confidence.HIGH,
        metadata={
            "item_no": item_no,
            "previous_page": previous_page,
            "current_page": current_page,
            "expected_marker": f"续{item_no}" if item_no is not None else expected,
            "actual_marker": actual,
            "boundary_key": boundary_key,
            "first_related_row_index": first_related_row.row_index,
            "marker_row_index": marker_row.row_index if marker_row is not None else None,
            "group_row_count": len(group.rows),
            "group_pages": list(group.pages),
            "continuation_markers": [marker.model_dump() for marker in group.continuation_markers],
            "duplicate_suppressed_count": max(0, len(current_page_rows) - 1),
            "source_rows": _source_rows(group, override_rows=extra_source_rows),
            "group_diagnostics": list(group.diagnostics),
        },
    )


def _row_evidence(*rows: _GroupRow | None) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen: set[str] = set()
    for row in rows:
        if row is None:
            continue
        if row.item.evidence:
            for item in row.item.evidence:
                if item.id in seen:
                    continue
                seen.add(item.id)
                evidence.append(item)
            continue
        evidence.append(
            Evidence(
                id=f"c10-row-{row.page}-{row.row_index}-{row.source_index}",
                source_type=SourceType.REPORT,
                location=row.item.row_location,
                raw_text=f"序号：{_item_no(row.item)}；检验项目：{row.item.item_name or ''}",
                value=_item_no(row.item),
                method=EvidenceMethod.PDF_TEXT,
                confidence=Confidence.HIGH,
            )
        )
    return evidence


def _source_rows(
    group: InspectionItemGroup,
    *,
    override_rows: list[_GroupRow] | None = None,
) -> list[dict[str, Any]]:
    if override_rows is not None:
        return [
            {
                "source_index": row.source_index,
                "page_number": row.page,
                "row_index": row.row_index,
                "sequence_raw": _item_no(row.item),
                "item_no": row.item_no,
            }
            for row in override_rows
        ]

    rows: list[dict[str, Any]] = []
    for item, evidence in zip(group.rows, group.source_evidence, strict=False):
        rows.append(
            {
                "source_index": evidence.get("source_index"),
                "page_number": evidence.get("page_number"),
                "row_index": evidence.get("row_index"),
                "sequence_raw": _item_no(item),
                "item_no": group.item_no,
            }
        )
    return rows


def _context_missing_finding(
    context: CheckContext,
    items: list[InspectionItem],
    missing_context_rows: list[int],
) -> Finding:
    return Finding(
        id=f"{context.task_id}-c10-continuation-context-missing",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.WARN,
        code="CONTINUATION_CONTEXT_MISSING",
        message="续表标记核对缺少页码或页内行号信息，无法可靠判断续字位置。",
        expected="每个检验项目行都有 page_number 和 row_index_in_page",
        actual=f"缺少结构信息的行：{missing_context_rows}",
        evidence=_continuation_evidence(items),
        confidence=Confidence.MEDIUM,
        metadata={"missing_context_rows": missing_context_rows, "boundary_uncertain": True},
    )


def _continuation_evidence(items: list[InspectionItem]) -> list[Evidence]:
    raw_values = [_item_no(item) for item in items]
    return [
        Evidence(
            id="c10-continuation-rows",
            source_type=SourceType.REPORT,
            raw_text="续表候选行：" + "，".join(raw_values),
            value=",".join(raw_values),
            method=EvidenceMethod.PDF_LAYOUT,
            confidence=Confidence.MEDIUM,
            metadata={
                "sequence_values": raw_values,
                "row_indices": [item.row_index_in_page for item in items],
                "page_numbers": [item.source_page for item in items],
            },
        )
    ]


def _item_no(item: InspectionItem) -> str:
    raw = (item.sequence_raw or "").strip()
    if raw:
        return raw
    if item.sequence is not None:
        return str(item.sequence)
    return ""


__all__ = ["CHECK_ID", "CHECK_NAME", "check_c10_continuation", "is_continuation_no"]
