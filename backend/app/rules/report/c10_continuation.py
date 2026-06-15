from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.common import Confidence, Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.report import InspectionItem, ReportDocument
from app.domain.result import CheckResult
from app.rules.report.common import make_result
from app.rules.report.context import CheckContext


CHECK_ID = "C10"
CHECK_NAME = "续表标记"

_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


@dataclass(frozen=True)
class _Row:
    item: InspectionItem
    position: int
    page: int
    row_index: int
    number: int | None
    continuation_number: int | None

    @property
    def has_continuation_marker(self) -> bool:
        return self.continuation_number is not None


def check_c10_continuation(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    context = context or CheckContext()
    rows, missing_context_rows = _parse_rows(document.inspection_items)

    if missing_context_rows:
        findings = [_context_missing_finding(context, document.inspection_items, missing_context_rows)]
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=findings,
            metadata={"missing_context_rows": missing_context_rows},
            pass_summary="续表标记位置正确",
            issue_summary="续表标记缺少页码或页内行号信息，需人工复核",
        )

    pages = _group_rows_by_page(rows)
    findings: list[Finding] = []

    for page_index, (page_number, page_rows) in enumerate(pages):
        first_row = page_rows[0]
        previous_tail = pages[page_index - 1][1][-1] if page_index > 0 else None

        if first_row.has_continuation_marker:
            if previous_tail is None:
                findings.append(
                    _continuation_finding(
                        context,
                        first_row,
                        code="CONTINUATION_MARK_MISMATCH",
                        message="首页或首个检验项目页不应出现续表标记。",
                        expected="不应出现续表标记",
                        actual=_item_no(first_row.item),
                        previous_tail=previous_tail,
                        current_page_first=first_row,
                        is_first_row_on_page=True,
                    )
                )
            elif first_row.continuation_number != previous_tail.number:
                findings.append(
                    _continuation_finding(
                        context,
                        first_row,
                        code="CONTINUATION_MARK_MISMATCH",
                        message=(
                            f"续表标记与上一页末尾序号不一致：上一页末尾为 {previous_tail.number}，"
                            f"当前页首行为 {_item_no(first_row.item)}。"
                        ),
                        expected=f"续{previous_tail.number}",
                        actual=_item_no(first_row.item),
                        previous_tail=previous_tail,
                        current_page_first=first_row,
                        is_first_row_on_page=True,
                    )
                )
        elif previous_tail is not None and first_row.number == previous_tail.number:
            findings.append(
                _continuation_finding(
                    context,
                    first_row,
                    code="CONTINUATION_MARK_ERROR_001",
                    message=f"跨页续表首行缺少续表标记，应写为“续{previous_tail.number}”。",
                    expected=f"续{previous_tail.number}",
                    actual=_item_no(first_row.item),
                    previous_tail=previous_tail,
                    current_page_first=first_row,
                    is_first_row_on_page=True,
                )
            )

        for row in page_rows[1:]:
            if not row.has_continuation_marker:
                continue
            findings.append(
                _continuation_finding(
                    context,
                    row,
                    code="CONTINUATION_MARK_ERROR_002",
                    message="续字只能出现在本页第一行的序号中。",
                    expected="续字只能出现在本页第一行",
                    actual=_item_no(row.item),
                    previous_tail=previous_tail,
                    current_page_first=first_row,
                    is_first_row_on_page=False,
                )
            )

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        metadata={
            "pages_checked": [page_number for page_number, _ in pages],
            "row_count": len(rows),
        },
        pass_summary="续表标记位置正确",
        issue_summary=f"续表标记存在 {len(findings)} 项问题",
    )


def is_continuation_no(value: int | str | None) -> int | None:
    if value is None:
        return None
    text = re.sub(r"\s+", "", str(value).strip()).translate(_FULLWIDTH_DIGITS)
    match = re.fullmatch(r"续(\d+)", text)
    return int(match.group(1)) if match else None


def _parse_rows(items: list[InspectionItem]) -> tuple[list[_Row], list[int]]:
    rows: list[_Row] = []
    missing_context_rows: list[int] = []
    for position, item in enumerate(items):
        if item.source_page is None or item.row_index_in_page is None:
            missing_context_rows.append(position)
            continue

        number = _item_number(item)
        continuation_number = is_continuation_no(item.sequence_raw)
        if continuation_number is None and item.is_continuation:
            continuation_number = number

        rows.append(
            _Row(
                item=item,
                position=position,
                page=item.source_page,
                row_index=item.row_index_in_page,
                number=number,
                continuation_number=continuation_number,
            )
        )
    return rows, missing_context_rows


def _group_rows_by_page(rows: list[_Row]) -> list[tuple[int, list[_Row]]]:
    sorted_rows = sorted(rows, key=lambda row: (row.page, row.row_index, row.position))
    grouped: list[tuple[int, list[_Row]]] = []
    for row in sorted_rows:
        if not grouped or grouped[-1][0] != row.page:
            grouped.append((row.page, [row]))
        else:
            grouped[-1][1].append(row)
    return grouped


def _item_number(item: InspectionItem) -> int | None:
    if item.sequence is not None:
        return item.sequence
    raw = (item.sequence_raw or "").translate(_FULLWIDTH_DIGITS)
    marker_number = is_continuation_no(raw)
    if marker_number is not None:
        return marker_number
    match = re.fullmatch(r"\s*(\d+)\s*", raw)
    return int(match.group(1)) if match else None


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
        metadata={"missing_context_rows": missing_context_rows},
    )


def _continuation_finding(
    context: CheckContext,
    row: _Row,
    *,
    code: str,
    message: str,
    expected: object,
    actual: object,
    previous_tail: _Row | None,
    current_page_first: _Row,
    is_first_row_on_page: bool,
) -> Finding:
    return Finding(
        id=f"{context.task_id}-c10-{code.lower()}-{row.page}-{row.row_index}-{row.position}",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code=code,
        message=message,
        location=row.item.row_location,
        expected=expected,
        actual=actual,
        evidence=_row_evidence(previous_tail, current_page_first, row),
        confidence=Confidence.HIGH,
        metadata={
            "previous_page_last_item_no": previous_tail.number if previous_tail else None,
            "previous_page": previous_tail.page if previous_tail else None,
            "previous_page_last_row_index": previous_tail.row_index if previous_tail else None,
            "current_page_first_item_no": current_page_first.number,
            "current_page": current_page_first.page,
            "current_page_first_row_index": current_page_first.row_index,
            "item_no": row.number,
            "sequence_raw": _item_no(row.item),
            "is_first_row_on_page": is_first_row_on_page,
        },
    )


def _row_evidence(*rows: _Row | None) -> list[Evidence]:
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
                id=f"c10-row-{row.page}-{row.row_index}-{row.position}",
                source_type=SourceType.REPORT,
                location=row.item.row_location,
                raw_text=f"序号：{_item_no(row.item)}；检验项目：{row.item.item_name or ''}",
                value=_item_no(row.item),
                method=EvidenceMethod.PDF_TEXT,
                confidence=Confidence.HIGH,
            )
        )
    return evidence


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
