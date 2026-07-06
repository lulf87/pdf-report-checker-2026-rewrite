from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from app.domain.inspection_group import InspectionItemGroup
from app.domain.report import InspectionItem
from app.infrastructure.report.inspection_item_group_builder import build_inspection_item_groups


def build_ptr_report_item_groups(items: Sequence[InspectionItem]) -> list[InspectionItemGroup]:
    result = build_inspection_item_groups(list(items))
    groups_by_no = {group.item_no: group for group in result.groups}
    order = [group.item_no for group in result.groups]
    active_item_no: str | None = None

    for item in _ordered_items(items):
        item_no = _normalized_item_no(item)
        if item_no:
            if item_no in groups_by_no:
                active_item_no = item_no
            continue
        if active_item_no is None or not _looks_like_group_payload_row(item):
            continue
        group = groups_by_no.get(active_item_no)
        if group is None or _row_in_group(item, group):
            continue
        rows = _ordered_items([*group.rows, item])
        groups_by_no[active_item_no] = group.model_copy(
            update={
                "rows": rows,
                "pages": _ordered_pages(rows),
                "effective_test_results": ptr_group_test_results(group.model_copy(update={"rows": rows})),
            }
        )

    return [groups_by_no[item_no] for item_no in order]


def ptr_group_for_clause(
    clause_number: str,
    groups: Sequence[InspectionItemGroup],
) -> InspectionItemGroup | None:
    anchored_matches = [group for group in groups if ptr_group_anchor_matches_clause(clause_number, group)]
    if anchored_matches:
        exact_anchored = [
            group
            for group in anchored_matches
            if _compact_clause_number(clause_number) in _compact(ptr_group_text(group))
        ]
        if exact_anchored:
            return exact_anchored[0]
        supported_anchored = [group for group in anchored_matches if ptr_group_supports_clause(clause_number, group)]
        return supported_anchored[0] if supported_anchored else anchored_matches[0]

    exact_matches = [
        group
        for group in groups
        if _compact_clause_number(clause_number) in _compact(ptr_group_text(group))
        and not _has_unrelated_standard_clause(clause_number, group)
    ]
    if exact_matches:
        return exact_matches[0]
    return None


def ptr_group_anchor_matches_clause(clause_number: str, group: InspectionItemGroup) -> bool:
    ptr_number = _compact_clause_number(clause_number)
    if not ptr_number:
        return False
    return any(_report_clause_covers_ptr_clause(ptr_number, row.standard_clause or "") for row in group.rows)


def ptr_group_invalid_candidates_for_clause(
    clause_number: str,
    groups: Sequence[InspectionItemGroup],
) -> list[InspectionItemGroup]:
    compact_clause = _compact_clause_number(clause_number)
    if not compact_clause:
        return []
    return [
        group
        for group in groups
        if compact_clause in _compact(ptr_group_text(group)) and _has_unrelated_standard_clause(clause_number, group)
    ]


def ptr_group_supports_clause(clause_number: str, group: InspectionItemGroup) -> bool:
    compact_text = _compact(ptr_group_text(group))
    compact_clause = _compact_clause_number(clause_number)
    if _has_unrelated_standard_clause(clause_number, group):
        return False
    if compact_clause and compact_clause in compact_text:
        return True
    return len(group.rows) > 1 and ptr_group_anchor_matches_clause(clause_number, group)


def ptr_group_standard_requirement(group: InspectionItemGroup) -> str:
    values: list[str] = []
    for row in group.rows:
        if row.standard_requirement:
            values.append(row.standard_requirement)
        if _looks_like_shifted_parameter_row(row) and row.sequence_raw:
            values.append(row.sequence_raw)
        elif _looks_like_limit_result_payload_row(row) and row.sequence_raw:
            values.append(row.sequence_raw)
        elif _looks_like_clause_payload(row.sequence_raw or ""):
            values.append(row.sequence_raw or "")
    return _join_unique(values)


def ptr_group_test_result(group: InspectionItemGroup) -> str:
    return " / ".join(ptr_group_test_results(group))


def ptr_group_test_results(group: InspectionItemGroup) -> list[str]:
    values: list[str] = []
    for row in group.rows:
        if row.result_values:
            values.extend(row.result_values)
        elif row.test_result:
            values.append(row.test_result)
        if _looks_like_shifted_parameter_row(row) and _is_result_like(row.item_name):
            values.append(row.item_name or "")
        if _looks_like_limit_result_payload_row(row) and _is_result_like(row.item_name):
            values.append(row.item_name or "")
        values.extend(_preset_payload_result_values(row))
    return _unique_non_empty(values)


def ptr_group_single_conclusion(group: InspectionItemGroup) -> str | None:
    if group.effective_single_conclusion:
        return group.effective_single_conclusion
    for row in group.rows:
        if row.conclusion and row.conclusion.strip():
            return row.conclusion.strip()
    return None


def ptr_group_text(group: InspectionItemGroup) -> str:
    values: list[str] = []
    for row in group.rows:
        values.extend(
            [
                row.sequence_raw,
                row.item_name,
                row.standard_clause,
                row.standard_requirement,
                row.test_result,
                row.conclusion,
                row.remark,
                _metadata_text(row, "row_text"),
            ]
        )
    return _join_unique(values)


def ptr_group_compact_rows(group: InspectionItemGroup) -> list[dict[str, Any]]:
    return [
        {
            "page_number": row.source_page,
            "row_index": row.row_index_in_page,
            "sequence_raw": row.sequence_raw,
            "item_name": row.item_name,
            "standard_clause": row.standard_clause,
            "standard_requirement": row.standard_requirement,
            "test_result": row.test_result,
            "single_conclusion": row.conclusion,
            "remark": row.remark,
        }
        for row in group.rows
    ]


def _ordered_items(items: Sequence[InspectionItem]) -> list[InspectionItem]:
    return sorted(
        list(items),
        key=lambda item: (
            item.source_page or 0,
            item.row_index_in_page if item.row_index_in_page is not None else 10**9,
        ),
    )


def _ordered_pages(rows: Sequence[InspectionItem]) -> list[int]:
    pages: list[int] = []
    for row in rows:
        if row.source_page is not None and row.source_page not in pages:
            pages.append(row.source_page)
    return pages


def _normalized_item_no(item: InspectionItem) -> str | None:
    raw = str(item.sequence_raw or "").strip()
    compact_raw = _compact(raw)
    match = re.fullmatch(r"续(\d+)", compact_raw)
    if match:
        return str(int(match.group(1)))
    if compact_raw.isdigit():
        return str(int(compact_raw))
    if item.sequence is not None:
        return str(item.sequence)
    return None


def _row_in_group(item: InspectionItem, group: InspectionItemGroup) -> bool:
    return any(row is item or (row.source_page, row.row_index_in_page, row.sequence_raw) == (item.source_page, item.row_index_in_page, item.sequence_raw) for row in group.rows)


def _looks_like_shifted_parameter_row(item: InspectionItem) -> bool:
    text = item.sequence_raw or ""
    return bool(
        text
        and re.search(r"[：:]", text)
        and re.search(r"\d", text)
        and (item.item_name or item.standard_clause or item.test_result)
    )


def _looks_like_group_payload_row(item: InspectionItem) -> bool:
    return (
        _looks_like_shifted_parameter_row(item)
        or _looks_like_limit_result_payload_row(item)
        or _looks_like_clause_payload(item.sequence_raw or "")
    )


def _looks_like_limit_result_payload_row(item: InspectionItem) -> bool:
    return bool(
        item.sequence_raw
        and re.search(r"[≤>=<>]", item.sequence_raw)
        and _is_result_like(item.item_name)
        and not _meaningful_standard_clause(item.standard_clause)
    )


def _looks_like_clause_payload(value: str) -> bool:
    return bool(re.match(r"\s*2(?:\.\d+)+", value or ""))


def _is_result_like(value: str | None) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    return bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:\s*[A-Za-zμΩ°/%]+)?", text) or "符合" in text)


def _preset_payload_result_values(item: InspectionItem) -> list[str]:
    values: list[str] = []
    context = " ".join(
        str(value or "")
        for value in [
            item.standard_clause,
            item.standard_requirement,
            _metadata_text(item, "row_text"),
            _metadata_text(item, "source_text"),
            _metadata_text(item, "table_row_text"),
            _metadata_text(item, "combined_row_text"),
        ]
    )
    if _is_result_like(item.item_name) and re.search(r"PULSE\s*3|PULSE3|PF\s*Reversi\s*ble|PFReversi\s*ble|PF\s*Reversible|PFReversible", context, re.IGNORECASE):
        values.append(str(item.item_name or ""))

    source_text = " ".join([context, str(item.item_name or "")])
    preset_pattern = r"PULSE\s*3|PULSE3|PF\s*Reversi\s*ble|PFReversi\s*ble|PF\s*Reversible|PFReversible"
    for pattern in (
        re.compile(rf"([-+]?\d+(?:\.\d+)?)\s*(?:ns|mJ|%|V|A)?\s*(?:{preset_pattern})\s*预\s*设", re.IGNORECASE),
        re.compile(rf"(?:{preset_pattern})\s*预\s*设\D{{0,80}}?(?:检验)?结果\s*[:：]?\s*([-+]?\d+(?:\.\d+)?)", re.IGNORECASE),
    ):
        values.extend(match.group(1) for match in pattern.finditer(source_text))
    return _unique_non_empty(values)


def _report_clause_covers_ptr_clause(ptr_clause_number: str, report_clause_number: str) -> bool:
    report_number = _ptr_report_clause_number(report_clause_number)
    if not report_number:
        return False
    return (
        ptr_clause_number == report_number
        or ptr_clause_number.startswith(report_number + ".")
        or report_number.startswith(ptr_clause_number + ".")
    )


def _has_unrelated_standard_clause(ptr_clause_number: str, group: InspectionItemGroup) -> bool:
    meaningful_clauses = [
        row.standard_clause or ""
        for row in group.rows
        if _meaningful_standard_clause(row.standard_clause)
    ]
    if not meaningful_clauses:
        return False
    return not any(_report_clause_covers_ptr_clause(ptr_clause_number, clause) for clause in meaningful_clauses)


def _meaningful_standard_clause(value: str | None) -> bool:
    text = _compact(str(value or ""))
    return bool(text and text not in {"/", "-", "——"})


def _ptr_report_clause_number(value: str) -> str:
    text = re.sub(r"\s+", "", value or "")
    return text if re.fullmatch(r"2(?:\.\d+)+", text) else ""


def _compact_clause_number(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def _metadata_text(item: InspectionItem, key: str) -> str | None:
    value = item.metadata.get(key)
    return str(value) if value is not None else None


def _join_unique(values: Sequence[str | None]) -> str:
    return "；".join(_unique_non_empty(values))


def _unique_non_empty(values: Sequence[str | None]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in result:
            continue
        result.append(text)
    return result
