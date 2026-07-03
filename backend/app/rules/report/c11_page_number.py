from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.pdf import PdfPage
from app.domain.report import PageNumberEvidence, ReportDocument
from app.domain.result import CheckResult
from app.rules.report.common import make_result
from app.rules.report.comparison_details import comparison_field, comparison_source, field_extract
from app.rules.report.context import CheckContext
from app.rules.report.explanation_details import (
    comparison_row,
    decision_detail,
    evidence_group,
    evidence_item,
    explanation_details,
    source_section,
)


CHECK_ID = "C11"
CHECK_NAME = "页码连续性"

_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")

_PAGE_PATTERNS = (
    (re.compile(r"共\s*(\d+)\s*页\s*第\s*(\d+)\s*页"), "total_current"),
    (re.compile(r"第\s*(\d+)\s*页\s*/\s*共\s*(\d+)\s*页"), "current_total"),
    (re.compile(r"Page\s*(\d+)\s*of\s*(\d+)", re.IGNORECASE), "current_total"),
    (re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$"), "current_total"),
)

_PAGE_NUMBER_LIKE_PATTERN = re.compile(
    r"共\s*\S{1,12}\s*页\s*第\s*\S{1,12}\s*页|"
    r"第\s*\S{1,12}\s*页\s*/\s*共\s*\S{1,12}\s*页|"
    r"Page\s+\S{1,12}\s+of\s+\S{1,12}|"
    r"^\s*\S{1,12}\s*/\s*\S{1,12}\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _PageNumberMatch:
    current_page: int
    total_pages: int
    raw_text: str


@dataclass(frozen=True)
class _ParsedPageNumber:
    source: PageNumberEvidence
    current_page: int
    total_pages: int
    raw_text: str


def parse_page_number_text(text: str | None) -> tuple[int | None, int | None]:
    match = _match_page_number_text(text)
    if match is None:
        return None, None
    return match.current_page, match.total_pages


def check_c11_page_number(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    context = context or CheckContext()
    start_page = _start_page(document)
    sources = _page_number_sources(document, start_page)
    findings: list[Finding] = []
    parsed_items: list[_ParsedPageNumber] = []

    if not sources:
        findings.append(_no_page_number_sources_finding(context, start_page))

    for item in sources:
        resolved = _resolve_page_number(item)
        if resolved is None:
            findings.append(_invalid_page_number_finding(context, item))
            continue
        parsed_items.append(resolved)

    parsed_items.sort(key=lambda item: item.source.page_number)
    parsed_summary = _parsed_summary(parsed_items)
    total_values = sorted({item.total_pages for item in parsed_items})
    duplicated_y = _duplicated_y(parsed_items)
    missing_y = _missing_y(parsed_items)

    if len(total_values) > 1:
        findings.append(_total_inconsistent_finding(context, parsed_items, total_values, parsed_summary))

    if duplicated_y:
        findings.append(_duplicate_finding(context, parsed_items, duplicated_y, parsed_summary))

    if missing_y or _has_non_increasing_sequence(parsed_items):
        findings.append(_continuity_finding(context, parsed_items, missing_y, parsed_summary))

    if parsed_items:
        final_item = parsed_items[-1]
        if final_item.current_page != final_item.total_pages:
            findings.append(_final_page_mismatch_finding(context, parsed_items, final_item, parsed_summary))

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        metadata={
            "start_pdf_page": start_page,
            "parsed_page_numbers": parsed_summary,
            "missing_y": missing_y,
            "duplicated_y": duplicated_y,
            "total_values": total_values,
            "comparison_details": _comparison_details(
                start_page=start_page,
                parsed_items=parsed_items,
                parsed_summary=parsed_summary,
                missing_y=missing_y,
                duplicated_y=duplicated_y,
                total_values=total_values,
                finding_count=len(findings),
            ),
            "explanation_details": _explanation_details(
                document=document,
                start_page=start_page,
                parsed_items=parsed_items,
                parsed_summary=parsed_summary,
                missing_y=missing_y,
                duplicated_y=duplicated_y,
                total_values=total_values,
                findings=findings,
            ),
        },
        pass_summary="报告页码连续且总页数一致",
        issue_summary=f"报告页码存在 {len(findings)} 项问题",
    )


def _match_page_number_text(text: str | None) -> _PageNumberMatch | None:
    if text is None:
        return None

    normalized = text.translate(_FULLWIDTH_DIGITS)
    for pattern, order in _PAGE_PATTERNS:
        match = pattern.search(normalized)
        if not match:
            continue
        first, second = int(match.group(1)), int(match.group(2))
        if first <= 0 or second <= 0:
            return None
        if order == "total_current":
            return _PageNumberMatch(current_page=second, total_pages=first, raw_text=match.group(0))
        return _PageNumberMatch(current_page=first, total_pages=second, raw_text=match.group(0))
    return None


def _start_page(document: ReportDocument) -> int:
    for key in ("third_page", "report_home_page"):
        value = document.page_map.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return 3


def _page_number_sources(document: ReportDocument, start_page: int) -> list[PageNumberEvidence]:
    if document.page_numbers:
        return sorted(
            [item for item in document.page_numbers if item.page_number >= start_page],
            key=lambda item: item.page_number,
        )

    if document.parsed_pdf is None:
        return []

    return [_page_number_source_from_pdf_page(page, document.parsed_pdf.file_id) for page in document.parsed_pdf.pages if page.page_number >= start_page]


def _page_number_source_from_pdf_page(page: PdfPage, source_id: str) -> PageNumberEvidence:
    match = _match_page_number_text(page.text)
    displayed_number = match.raw_text if match else (page.text if _looks_like_page_number(page.text) else None)
    return PageNumberEvidence(
        page_number=page.page_number,
        displayed_number=displayed_number,
        parsed_number=match.current_page if match else None,
        total_pages=match.total_pages if match else None,
        location=Location(
            source_id=source_id,
            source_type=SourceType.REPORT,
            page_number=page.page_number,
            column_name="页码",
            section="页码",
        ),
        metadata={"source": "parsed_pdf_page_text"},
    )


def _looks_like_page_number(text: str | None) -> bool:
    if not text:
        return False
    return bool(_PAGE_NUMBER_LIKE_PATTERN.search(text.translate(_FULLWIDTH_DIGITS)))


def _resolve_page_number(item: PageNumberEvidence) -> _ParsedPageNumber | None:
    current = _positive_int(item.parsed_number)
    total = _positive_int(item.total_pages)
    raw_text = (item.displayed_number or "").strip()

    if current is not None and total is not None:
        return _ParsedPageNumber(
            source=item,
            current_page=current,
            total_pages=total,
            raw_text=raw_text or f"共 {total} 页 第 {current} 页",
        )

    match = _match_page_number_text(raw_text)
    if match is None:
        return None

    return _ParsedPageNumber(
        source=item,
        current_page=match.current_page,
        total_pages=match.total_pages,
        raw_text=match.raw_text,
    )


def _positive_int(value: int | None) -> int | None:
    if value is None or value <= 0:
        return None
    return value


def _invalid_page_number_finding(context: CheckContext, item: PageNumberEvidence) -> Finding:
    raw_text = (item.displayed_number or "").strip()
    is_missing = not raw_text
    code = "PAGE_NUMBER_MISSING" if is_missing else "PAGE_NUMBER_PARSE_FAILED"
    message = f"PDF 第 {item.page_number} 页缺少报告内部页码。" if is_missing else f"PDF 第 {item.page_number} 页页码文本无法解析。"
    missing_evidence = [
        MissingEvidence(
            label=f"PDF 第 {item.page_number} 页右上角页码",
            reason="未抽取到页码文本" if is_missing else "页码格式不是“共 XXX 页 第 Y 页”或等价格式",
            expected_source=SourceType.REPORT,
            location=item.location,
        )
    ]
    return Finding(
        id=f"{context.task_id}-c11-{code.lower()}-{item.page_number}",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code=code,
        message=message,
        location=item.location,
        expected="共 XXX 页 第 Y 页",
        actual=raw_text or None,
        evidence=[] if is_missing else _page_evidence(item),
        missing_evidence=missing_evidence if is_missing else [],
        confidence=Confidence.HIGH,
        metadata={
            "pdf_page_number": item.page_number,
            "raw_text": raw_text or None,
            "parsed_page_numbers": [],
            "missing_y": [],
            "duplicated_y": [],
            "total_values": [],
        },
    )


def _no_page_number_sources_finding(context: CheckContext, start_page: int) -> Finding:
    return Finding(
        id=f"{context.task_id}-c11-page-number-sources-missing",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code="PAGE_NUMBER_MISSING",
        message="缺少第三页起的报告内部页码证据，无法核对页码连续性。",
        expected=f"从 PDF 第 {start_page} 页起提供页码文本",
        actual="未提供 page_numbers，且 ParsedPdf 中无可用页面文本",
        missing_evidence=[
            MissingEvidence(
                label="第三页起报告内部页码",
                reason="ReportDocument.page_numbers 为空，且无法从 ParsedPdf 页面文本构造页码证据",
                expected_source=SourceType.REPORT,
                location=Location(source_type=SourceType.REPORT, page_number=start_page, section="页码"),
            )
        ],
        confidence=Confidence.MEDIUM,
        metadata={"start_pdf_page": start_page},
    )


def _total_inconsistent_finding(
    context: CheckContext,
    parsed_items: list[_ParsedPageNumber],
    total_values: list[int],
    parsed_summary: list[dict[str, object]],
) -> Finding:
    return Finding(
        id=f"{context.task_id}-c11-page-number-total-inconsistent",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code="PAGE_NUMBER_ERROR_003",
        message=f"报告页码总页数 XXX 不一致：{total_values}。",
        expected="所有页 XXX 一致",
        actual=total_values,
        evidence=_parsed_evidence(parsed_items),
        confidence=Confidence.HIGH,
        metadata={
            "parsed_page_numbers": parsed_summary,
            "missing_y": _missing_y(parsed_items),
            "duplicated_y": _duplicated_y(parsed_items),
            "total_values": total_values,
        },
    )


def _duplicate_finding(
    context: CheckContext,
    parsed_items: list[_ParsedPageNumber],
    duplicated_y: list[int],
    parsed_summary: list[dict[str, object]],
) -> Finding:
    return Finding(
        id=f"{context.task_id}-c11-page-number-duplicated",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code="PAGE_NUMBER_DUPLICATED",
        message=f"报告内部页码 Y 存在重复：{duplicated_y}。",
        expected="Y 从 1 开始连续递增且不重复",
        actual=[item.current_page for item in parsed_items],
        evidence=_parsed_evidence([item for item in parsed_items if item.current_page in duplicated_y]),
        confidence=Confidence.HIGH,
        metadata={
            "parsed_page_numbers": parsed_summary,
            "missing_y": _missing_y(parsed_items),
            "duplicated_y": duplicated_y,
            "total_values": sorted({item.total_pages for item in parsed_items}),
        },
    )


def _continuity_finding(
    context: CheckContext,
    parsed_items: list[_ParsedPageNumber],
    missing_y: list[int],
    parsed_summary: list[dict[str, object]],
) -> Finding:
    sequence = [item.current_page for item in parsed_items]
    first_problem = _first_continuity_problem(parsed_items, missing_y)
    return Finding(
        id=f"{context.task_id}-c11-page-number-continuity",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code="PAGE_NUMBER_ERROR_001",
        message="报告内部页码 Y 未从 1 开始连续递增。",
        location=first_problem.source.location if first_problem else None,
        expected=missing_y or _expected_sequence_for_length(parsed_items),
        actual=sequence,
        evidence=_parsed_evidence(parsed_items),
        confidence=Confidence.HIGH,
        metadata={
            "parsed_page_numbers": parsed_summary,
            "missing_y": missing_y,
            "duplicated_y": _duplicated_y(parsed_items),
            "total_values": sorted({item.total_pages for item in parsed_items}),
        },
    )


def _final_page_mismatch_finding(
    context: CheckContext,
    parsed_items: list[_ParsedPageNumber],
    final_item: _ParsedPageNumber,
    parsed_summary: list[dict[str, object]],
) -> Finding:
    return Finding(
        id=f"{context.task_id}-c11-final-page-mismatch",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code="PAGE_NUMBER_ERROR_002",
        message=f"报告末页内部页码 Y={final_item.current_page}，与总页数 XXX={final_item.total_pages} 不一致。",
        location=final_item.source.location,
        expected=final_item.total_pages,
        actual=final_item.current_page,
        evidence=_parsed_evidence(parsed_items),
        confidence=Confidence.HIGH,
        metadata={
            "parsed_page_numbers": parsed_summary,
            "missing_y": _missing_y(parsed_items),
            "duplicated_y": _duplicated_y(parsed_items),
            "total_values": sorted({item.total_pages for item in parsed_items}),
            "final_pdf_page_number": final_item.source.page_number,
        },
    )


def _missing_y(parsed_items: list[_ParsedPageNumber]) -> list[int]:
    if not parsed_items:
        return []
    current_values = {item.current_page for item in parsed_items}
    return [number for number in range(1, max(current_values) + 1) if number not in current_values]


def _duplicated_y(parsed_items: list[_ParsedPageNumber]) -> list[int]:
    counts = Counter(item.current_page for item in parsed_items)
    return sorted(number for number, count in counts.items() if count > 1)


def _has_non_increasing_sequence(parsed_items: list[_ParsedPageNumber]) -> bool:
    sequence = [item.current_page for item in parsed_items]
    if not sequence:
        return False
    if sequence[0] != 1:
        return True
    return any(current <= previous for previous, current in zip(sequence, sequence[1:]))


def _expected_sequence_for_length(parsed_items: list[_ParsedPageNumber]) -> list[int]:
    return list(range(1, len(parsed_items) + 1))


def _first_continuity_problem(parsed_items: list[_ParsedPageNumber], missing_y: list[int]) -> _ParsedPageNumber | None:
    if missing_y:
        first_missing = missing_y[0]
        for item in parsed_items:
            if item.current_page > first_missing:
                return item
    expected = 1
    for item in parsed_items:
        if item.current_page != expected:
            return item
        expected += 1
    return parsed_items[0] if parsed_items else None


def _parsed_summary(parsed_items: list[_ParsedPageNumber]) -> list[dict[str, object]]:
    return [
        {
            "pdf_page_number": item.source.page_number,
            "current_page": item.current_page,
            "total_pages": item.total_pages,
            "raw_text": item.raw_text,
        }
        for item in parsed_items
    ]


def _page_evidence(item: PageNumberEvidence) -> list[Evidence]:
    if item.evidence:
        return item.evidence
    return [
        Evidence(
            id=f"ev-page-number-{item.page_number}",
            source_type=SourceType.REPORT,
            location=item.location,
            raw_text=item.displayed_number,
            value=item.displayed_number,
            method=EvidenceMethod.PDF_TEXT,
            confidence=Confidence.MEDIUM,
        )
    ]


def _parsed_evidence(items: list[_ParsedPageNumber]) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen: set[str] = set()
    for item in items:
        for evidence_item in _page_evidence(item.source):
            if evidence_item.id in seen:
                continue
            seen.add(evidence_item.id)
            evidence.append(evidence_item)
    return evidence


def _comparison_details(
    *,
    start_page: int,
    parsed_items: list[_ParsedPageNumber],
    parsed_summary: list[dict[str, object]],
    missing_y: list[int],
    duplicated_y: list[int],
    total_values: list[int],
    finding_count: int,
) -> dict[str, object]:
    current_pages = [item.current_page for item in parsed_items]
    first_pdf_page = parsed_items[0].source.page_number if parsed_items else start_page
    last_pdf_page = parsed_items[-1].source.page_number if parsed_items else start_page
    source_label = f"PDF 第 {first_pdf_page}-{last_pdf_page} 页" if parsed_items else f"PDF 第 {start_page} 页起"
    overall_status = "match" if finding_count == 0 and parsed_items else "mismatch"
    if not parsed_items:
        overall_reason = f"从 PDF 第 {start_page} 页起未获得可解析页码，无法核对连续性。"
    elif finding_count == 0:
        total = total_values[0] if total_values else parsed_items[-1].total_pages
        overall_reason = f"报告页码从 1 到 {total} 连续，且各页声明总页数一致。"
    else:
        reasons: list[str] = []
        if missing_y:
            reasons.append(f"缺少内部页码 {missing_y}")
        if duplicated_y:
            reasons.append(f"重复内部页码 {duplicated_y}")
        if len(total_values) > 1:
            reasons.append(f"声明总页数不一致 {total_values}")
        final_item = parsed_items[-1]
        if final_item.current_page != final_item.total_pages:
            reasons.append(f"末页内部页码 {final_item.current_page} 与总页数 {final_item.total_pages} 不一致")
        overall_reason = "；".join(reasons) or "页码连续性需复核。"

    declared_total_status = "match" if len(total_values) == 1 and parsed_items else "mismatch"
    continuity_status = "match" if parsed_items and not missing_y and not duplicated_y and not _has_non_increasing_sequence(parsed_items) else "mismatch"
    actual_range = ", ".join(str(page) for page in current_pages)
    expected_range = ", ".join(str(page) for page in range(1, (max(current_pages) if current_pages else 0) + 1))

    return {
        "title": CHECK_NAME,
        "overall_status": overall_status,
        "overall_reason": overall_reason,
        "sources": [
            comparison_source(
                source_key="page_numbers",
                label="报告内部页码",
                page_number=first_pdf_page,
                display_page_label=source_label,
                section="页眉/页脚页码",
            )
        ],
        "fields": [
            comparison_field(
                field_key="declared_total_pages",
                field_label="声明总页数",
                left=field_extract(
                    source_key="page_numbers",
                    label="各页声明总页数",
                    page_number=first_pdf_page,
                    display_page_label=source_label,
                    raw_text=", ".join(str(value) for value in total_values),
                    normalized_text=", ".join(str(value) for value in total_values),
                ),
                status=declared_total_status,
                reason="各页声明总页数一致" if declared_total_status == "match" else "各页声明总页数不一致或缺失",
            ),
            comparison_field(
                field_key="actual_page_range",
                field_label="实际提取页码范围",
                left=field_extract(
                    source_key="page_numbers",
                    label="提取到的内部页码",
                    page_number=first_pdf_page,
                    display_page_label=source_label,
                    raw_text=actual_range,
                    normalized_text=expected_range,
                ),
                status="match" if actual_range == expected_range and bool(parsed_items) else "mismatch",
                reason="内部页码从 1 开始覆盖到末页" if actual_range == expected_range and parsed_items else "内部页码范围不完整或无法解析",
            ),
            comparison_field(
                field_key="continuity",
                field_label="连续性",
                left=field_extract(
                    source_key="page_numbers",
                    label="页码连续性",
                    page_number=first_pdf_page,
                    display_page_label=source_label,
                    raw_text=actual_range,
                    normalized_text=actual_range,
                ),
                status=continuity_status,
                reason="页码连续且无重复" if continuity_status == "match" else "页码存在缺失、重复或非递增",
            ),
        ],
        "parsed_page_numbers": parsed_summary,
    }


def _explanation_details(
    *,
    document: ReportDocument,
    start_page: int,
    parsed_items: list[_ParsedPageNumber],
    parsed_summary: list[dict[str, object]],
    missing_y: list[int],
    duplicated_y: list[int],
    total_values: list[int],
    findings: list[Finding],
) -> dict[str, object]:
    current_pages = [item.current_page for item in parsed_items]
    first_pdf_page = parsed_items[0].source.page_number if parsed_items else start_page
    last_pdf_page = parsed_items[-1].source.page_number if parsed_items else start_page
    pdf_total = document.parsed_pdf.page_count if document.parsed_pdf else None
    expected_range = list(range(1, (max(current_pages) if current_pages else 0) + 1))
    if findings:
        status, label, reason = (
            "candidate_issue",
            "候选问题",
            "报告页码存在缺失、重复、跳号、总页数不一致或末页不一致的候选问题。",
        )
    elif parsed_items:
        total = total_values[0] if total_values else parsed_items[-1].total_pages
        status, label, reason = (
            "passed",
            "通过",
            f"报告正文页码连续且总页数一致：内部页码 1 到 {total} 均已识别。",
        )
    else:
        status, label, reason = (
            "needs_review",
            "需复核",
            f"从 PDF 第 {start_page} 页起未获得可解析页码，无法核对连续性。",
        )
    return explanation_details(
        check_goal="核对报告正文页码是否连续且总页数一致。",
        user_question="报告声明总页数、PDF 总页数和实际提取的正文页码范围分别是什么？",
        overall_reason=reason,
        source_sections=[
            source_section(
                label="报告正文页码",
                page_number=first_pdf_page,
                display_page_label=f"PDF 第 {first_pdf_page}-{last_pdf_page} 页",
                description=f"从 PDF 第 {start_page} 页起核对；封面/注意事项页已排除。",
            )
        ],
        comparison_rows=[
            comparison_row(
                field="报告声明总页数",
                left_label="页码文本声明",
                left_value=total_values[0] if len(total_values) == 1 else total_values,
                right_label="PDF 总页数",
                right_value=pdf_total,
                status="match" if len(total_values) == 1 and parsed_items else "needs_review",
                reason="各页声明总页数一致。" if len(total_values) == 1 and parsed_items else "声明总页数缺失或不一致。",
            ),
            comparison_row(
                field="实际提取页码范围",
                left_label="提取到的内部页码",
                left_value=current_pages,
                right_label="预期连续范围",
                right_value=expected_range,
                status="match" if current_pages == expected_range and bool(parsed_items) else "mismatch",
                reason="正文页码从 1 开始连续。" if current_pages == expected_range and parsed_items else "正文页码存在缺失或跳号。",
            ),
            comparison_row(
                field="缺页/重复页/跳号",
                left_label="缺页",
                left_value=missing_y,
                right_label="重复页",
                right_value=duplicated_y,
                status="match" if not missing_y and not duplicated_y else "mismatch",
                reason="未发现缺页或重复页。" if not missing_y and not duplicated_y else "发现缺页、重复页或非递增页码。",
            ),
            comparison_row(
                field="封面/注意事项排除",
                left_label="核对起始 PDF 页",
                left_value=start_page,
                right_label="排除说明",
                right_value="封面和注意事项不纳入正文页码连续性。",
                status="skipped",
                reason="C11 从报告首页/第三页开始核对正文内部页码。",
            ),
        ],
        evidence_groups=[
            evidence_group(
                "页码文本摘录",
                [
                    evidence_item(
                        label=str(item.get("raw_text") or ""),
                        page_number=item.get("pdf_page_number") if isinstance(item.get("pdf_page_number"), int) else None,
                        evidence_type="page_number_text",
                        status="parsed",
                    )
                    for item in parsed_summary[:80]
                ],
            )
        ],
        decision=decision_detail(status, label, reason),
        next_action="如页码候选异常，请查看对应 PDF 页右上/页脚页码文本。",
    )


__all__ = ["CHECK_ID", "CHECK_NAME", "check_c11_page_number", "parse_page_number_text"]
