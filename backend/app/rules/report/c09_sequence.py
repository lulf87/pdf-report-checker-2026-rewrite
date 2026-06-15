from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.report import InspectionItem, ReportDocument
from app.domain.result import CheckResult
from app.rules.report.common import make_result
from app.rules.report.context import CheckContext


CHECK_ID = "C09"
CHECK_NAME = "检验项目序号连续性"

_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


@dataclass(frozen=True)
class ParsedItemNo:
    raw: str
    number: int | None
    is_continuation: bool = False


@dataclass(frozen=True)
class _ParsedRow:
    item: InspectionItem
    row_position: int
    parsed: ParsedItemNo


def check_c09_sequence(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    context = context or CheckContext()
    rows = [_parse_row(item, index) for index, item in enumerate(document.inspection_items)]
    ordinary_rows = [row for row in rows if row.parsed.number is not None and not row.parsed.is_continuation]
    continuation_rows = [row for row in rows if row.parsed.number is not None and row.parsed.is_continuation]
    blank_rows = [row for row in rows if row.parsed.number is None]

    actual_sequence = [row.parsed.number for row in ordinary_rows if row.parsed.number is not None]
    continuation_numbers = [row.parsed.number for row in continuation_rows if row.parsed.number is not None]
    raw_sequence_values = [row.parsed.raw for row in rows]
    findings: list[Finding] = []

    if ordinary_rows and actual_sequence[0] != 1:
        first = ordinary_rows[0]
        findings.append(
            _sequence_finding(
                context,
                document.inspection_items,
                code="SERIAL_NUMBER_NOT_START_FROM_ONE",
                message=f"检验项目序号应从 1 开始，实际从 {actual_sequence[0]} 开始。",
                location=first.item.row_location,
                expected=1,
                actual=actual_sequence[0],
                metadata={
                    "normalized_sequence": actual_sequence[0],
                    "missing_numbers": [],
                    "duplicated_numbers": [],
                    "blank_rows": [],
                    "actual_sequence": actual_sequence,
                    "raw_sequence_values": raw_sequence_values,
                },
            )
        )

    missing_numbers = _missing_numbers(actual_sequence)
    invalid_continuation_numbers = _invalid_continuation_numbers(actual_sequence, continuation_numbers)
    if missing_numbers or invalid_continuation_numbers:
        location_row = _first_row_for_number(ordinary_rows, missing_numbers[0]) if missing_numbers else continuation_rows[0]
        findings.append(
            _sequence_finding(
                context,
                document.inspection_items,
                code="SERIAL_NUMBER_ERROR_001",
                message=_gap_message(missing_numbers, invalid_continuation_numbers),
                location=location_row.item.row_location if location_row else None,
                expected=_expected_sequence(actual_sequence),
                actual=actual_sequence,
                metadata={
                    "normalized_sequence": location_row.parsed.number if location_row else None,
                    "missing_numbers": missing_numbers,
                    "duplicated_numbers": [],
                    "blank_rows": [],
                    "invalid_continuation_numbers": invalid_continuation_numbers,
                    "continuation_numbers": continuation_numbers,
                    "actual_sequence": actual_sequence,
                    "raw_sequence_values": raw_sequence_values,
                },
            )
        )

    duplicated_numbers = _duplicated_numbers(actual_sequence)
    if duplicated_numbers:
        duplicate_row = _duplicate_row(ordinary_rows, duplicated_numbers[0])
        findings.append(
            _sequence_finding(
                context,
                document.inspection_items,
                code="SERIAL_NUMBER_DUPLICATED",
                message=f"检验项目序号存在重复：{duplicated_numbers}。",
                location=duplicate_row.item.row_location if duplicate_row else None,
                expected="无重复普通序号",
                actual=actual_sequence,
                metadata={
                    "normalized_sequence": duplicated_numbers[0],
                    "missing_numbers": [],
                    "duplicated_numbers": duplicated_numbers,
                    "blank_rows": [],
                    "actual_sequence": actual_sequence,
                    "raw_sequence_values": raw_sequence_values,
                },
            )
        )

    if blank_rows:
        first_blank = blank_rows[0]
        blank_row_indices = [row.item.row_index_in_page for row in blank_rows]
        findings.append(
            _sequence_finding(
                context,
                document.inspection_items,
                code="SERIAL_NUMBER_ERROR_002",
                message=f"检验项目序号列存在空白或无法识别的序号：{blank_row_indices}。",
                location=first_blank.item.row_location,
                expected="非空且可识别的序号",
                actual=first_blank.parsed.raw,
                metadata={
                    "normalized_sequence": None,
                    "missing_numbers": [],
                    "duplicated_numbers": [],
                    "blank_rows": blank_row_indices,
                    "row_index": first_blank.item.row_index_in_page,
                    "actual_sequence": actual_sequence,
                    "raw_sequence_values": raw_sequence_values,
                },
            )
        )

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        metadata={
            "actual_sequence": actual_sequence,
            "continuation_numbers": continuation_numbers,
            "raw_sequence_values": raw_sequence_values,
        },
        pass_summary="检验项目序号从 1 开始连续递增，且无重复或空白",
        issue_summary=f"检验项目序号存在 {len(findings)} 项问题",
    )


def parse_item_no(value: int | str | None) -> ParsedItemNo:
    if value is None:
        return ParsedItemNo(raw="", number=None)

    raw = str(value).strip()
    text = re.sub(r"\s+", "", raw).translate(_FULLWIDTH_DIGITS)
    if not text:
        return ParsedItemNo(raw=raw, number=None)

    is_continuation = text.startswith("续")
    number_text = text[1:] if is_continuation else text
    if not re.fullmatch(r"\d+", number_text):
        return ParsedItemNo(raw=raw, number=None, is_continuation=is_continuation)
    return ParsedItemNo(raw=raw, number=int(number_text), is_continuation=is_continuation)


def _parse_row(item: InspectionItem, index: int) -> _ParsedRow:
    raw_value: int | str | None
    if item.sequence_raw is not None and item.sequence_raw.strip():
        raw_value = item.sequence_raw
    elif item.sequence is not None:
        raw_value = item.sequence
    else:
        raw_value = item.sequence_raw

    parsed = parse_item_no(raw_value)
    if item.is_continuation and parsed.number is not None:
        parsed = ParsedItemNo(raw=parsed.raw, number=parsed.number, is_continuation=True)
    return _ParsedRow(item=item, row_position=index + 1, parsed=parsed)


def _missing_numbers(actual_sequence: list[int]) -> list[int]:
    if not actual_sequence:
        return []
    unique_numbers = set(actual_sequence)
    return [number for number in range(min(unique_numbers), max(unique_numbers) + 1) if number not in unique_numbers]


def _invalid_continuation_numbers(actual_sequence: list[int], continuation_numbers: list[int]) -> list[int]:
    ordinary_numbers = set(actual_sequence)
    return sorted({number for number in continuation_numbers if number not in ordinary_numbers})


def _duplicated_numbers(actual_sequence: list[int]) -> list[int]:
    seen: set[int] = set()
    duplicates: set[int] = set()
    for number in actual_sequence:
        if number in seen:
            duplicates.add(number)
        seen.add(number)
    return sorted(duplicates)


def _expected_sequence(actual_sequence: list[int]) -> list[int]:
    if not actual_sequence:
        return []
    return list(range(min(actual_sequence), max(actual_sequence) + 1))


def _first_row_for_number(rows: list[_ParsedRow], number: int) -> _ParsedRow | None:
    for row in rows:
        if row.parsed.number and row.parsed.number > number:
            return row
    return rows[-1] if rows else None


def _duplicate_row(rows: list[_ParsedRow], number: int) -> _ParsedRow | None:
    found_once = False
    for row in rows:
        if row.parsed.number != number:
            continue
        if found_once:
            return row
        found_once = True
    return None


def _gap_message(missing_numbers: list[int], invalid_continuation_numbers: list[int]) -> str:
    parts: list[str] = []
    if missing_numbers:
        parts.append(f"检验项目序号不连续，缺少 {missing_numbers}")
    if invalid_continuation_numbers:
        parts.append(f"续表序号引用不存在的普通序号 {invalid_continuation_numbers}")
    return "；".join(parts) + "。"


def _sequence_finding(
    context: CheckContext,
    items: list[InspectionItem],
    *,
    code: str,
    message: str,
    metadata: dict[str, object],
    location: Location | None = None,
    expected: object | None = None,
    actual: object | None = None,
) -> Finding:
    return Finding(
        id=f"{context.task_id}-c09-{code.lower()}-{len(metadata.get('raw_sequence_values', []))}",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code=code,
        message=message,
        location=location,
        expected=expected,
        actual=actual,
        evidence=_sequence_evidence(items),
        confidence=Confidence.HIGH,
        metadata=metadata,
    )


def _sequence_evidence(items: list[InspectionItem]) -> list[Evidence]:
    raw_values = [_item_no(item) for item in items]
    evidence_items = [
        Evidence(
            id="c09-sequence-column",
            source_type=SourceType.REPORT,
            raw_text="序号列：" + "，".join(raw_values),
            value=",".join(raw_values),
            method=EvidenceMethod.PDF_TEXT,
            confidence=Confidence.HIGH,
            metadata={
                "sequence_values": raw_values,
                "row_indices": [item.row_index_in_page for item in items],
                "page_numbers": [item.source_page for item in items],
            },
        )
    ]
    for item in items:
        evidence_items.extend(item.evidence)
    return evidence_items


def _item_no(item: InspectionItem) -> str:
    raw = (item.sequence_raw or "").strip()
    if raw:
        return raw
    if item.sequence is not None:
        return str(item.sequence)
    return ""


__all__ = ["CHECK_ID", "CHECK_NAME", "ParsedItemNo", "check_c09_sequence", "parse_item_no"]
