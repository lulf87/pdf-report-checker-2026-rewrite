from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping

from pydantic import BaseModel, Field

from app.domain.inspection_group import InspectionItemGroup
from app.domain.report import InspectionItem


CLAUSE_NUMBER_RE = re.compile(r"(?<![\d.])2(?:\.\d+)+(?![\d.])(?=\s*[A-Za-z\u4e00-\u9fff])")
DIRECT_CLAUSE_RE = re.compile(r"^\s*(?P<number>2(?:\.\d+)+)(?![\d.])\s*(?P<title>.*?)\s*$")
CONTINUATION_CLAUSE_RE = re.compile(
    r"^\s*(?:续\s*)?\d+\s+(?P<number>2(?:\.\d+)+)(?![\d.])\s*(?P<title>.*?)\s*$"
)
PAGE_CLAUSE_RE = re.compile(r"^\s*(?P<number>2(?:\.\d+)+)\s+(?P<title>.+?)\s*$")
RESULT_TOKEN_RE = re.compile(
    r"(?:符合|不符合|不适用|——|/|[<>≤≥＜＞]?[+\-－＋]?\d+(?:\.\d+)?(?:\s*[～~至/]\s*[+\-－＋]?\d+(?:\.\d+)?)?)"
)


class ReportResultRow(BaseModel):
    report_clause_number: str | None = None
    report_clause_title: str | None = None
    normalized_clause_title: str | None = None
    table_row_label: str | None = None
    condition: str | None = None
    standard_requirement: str | None = None
    test_result: str
    conclusion: str | None = None
    source_page: int | None = None
    source_row: int | None = None
    item_no: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


class ReportResultRowIndex(BaseModel):
    rows: list[ReportResultRow] = Field(default_factory=list)

    def find(
        self,
        *,
        clause_number: str,
        clause_title: str | None,
        row_label: str | None = None,
        condition: str | None = None,
        expected_text: str | None = None,
        prefer_numeric: bool = False,
    ) -> list[ReportResultRow]:
        target_title = normalize_semantic_title(clause_title)
        exact = [row for row in self.rows if row.report_clause_number == clause_number]
        exact_compatible = [
            row
            for row in exact
            if not target_title
            or not row.normalized_clause_title
            or _titles_compatible(target_title, row.normalized_clause_title)
        ]

        diagnostics: list[str] = []
        if exact_compatible:
            scoped = exact_compatible
        else:
            scoped = [
                row
                for row in self.rows
                if target_title
                and row.normalized_clause_title
                and _titles_compatible(target_title, row.normalized_clause_title)
            ]
            if scoped and any(row.report_clause_number != clause_number for row in scoped):
                diagnostics.append("clause_number_mismatch_but_title_match")

        if not scoped and row_label:
            scoped = [row for row in self.rows if _row_matches_label(row, row_label, condition)]
        if not scoped:
            return []

        direct = [row for row in scoped if _row_matches_label(row, row_label, condition)] if row_label else []
        label_only = [row for row in scoped if _row_matches_label(row, row_label, None)] if row_label else []
        candidates = direct or label_only or scoped
        expected_matches = [row for row in candidates if _row_matches_expected(row, expected_text)]
        if expected_matches:
            candidates = expected_matches
        if prefer_numeric:
            numeric = [row for row in candidates if _is_numeric_result(row.test_result)]
            selected = numeric or candidates
        else:
            selected = candidates
            passing = [row for row in selected if "符合" in row.test_result and "不符合" not in row.test_result]
            if passing:
                selected = passing

        result: list[ReportResultRow] = []
        for row in _dedupe_matching_rows(selected):
            if diagnostics:
                row = row.model_copy(update={"diagnostics": [*row.diagnostics, *diagnostics]})
            result.append(row)
        return result


def build_report_result_row_index(
    group: InspectionItemGroup | None,
    *,
    page_text_by_page: Mapping[int, str] | None = None,
) -> ReportResultRowIndex:
    if group is None:
        return ReportResultRowIndex()

    current_clause_number: str | None = None
    current_clause_title: str | None = None
    rows: list[ReportResultRow] = []
    item_no = group.display_item_no or group.item_no
    for row in group.rows:
        marker = extract_report_clause_marker(row)
        if marker is not None:
            current_clause_number, detected_title = marker
            if detected_title:
                current_clause_title = detected_title

        recovered = _result_payload(row)
        if recovered is None:
            continue
        requirement, test_result, table_row_label, condition, diagnostics = recovered
        if _invalid_actual(test_result, item_no=item_no, clause_number=current_clause_number, page=row.source_page):
            continue
        rows.append(
            ReportResultRow(
                report_clause_number=current_clause_number,
                report_clause_title=current_clause_title,
                normalized_clause_title=normalize_semantic_title(current_clause_title),
                table_row_label=table_row_label,
                condition=condition,
                standard_requirement=requirement or None,
                test_result=test_result,
                conclusion=row.conclusion or row.metadata.get("single_conclusion") or group.effective_single_conclusion,
                source_page=row.source_page,
                source_row=row.row_index_in_page,
                item_no=item_no,
                diagnostics=diagnostics,
            )
        )
    rows.extend(_rows_from_page_text(group, page_text_by_page or {}))
    return ReportResultRowIndex(rows=_dedupe_rows(rows))


def extract_report_clause_marker(row: InspectionItem) -> tuple[str, str | None] | None:
    """Return a row's own report clause marker, excluding incidental body references."""

    standard_clause = str(row.standard_clause or "").strip()
    standard_match = DIRECT_CLAUSE_RE.fullmatch(standard_clause)
    standard_number = standard_match.group("number") if standard_match else None

    anchored_values = (
        str(row.metadata.get("row_text") or "").strip(),
        str(row.sequence_raw or "").strip(),
        str(row.item_name or "").strip(),
        str(row.standard_requirement or "").strip(),
    )
    candidates: list[tuple[int, int, str, str | None]] = []
    for priority, value in enumerate(anchored_values):
        value = re.sub(r"\s+", " ", value).strip()
        if not value:
            continue
        marker_matches = _anchored_clause_markers(value)
        if not marker_matches:
            continue
        for number, title in marker_matches:
            if standard_number and number != standard_number and not number.startswith(f"{standard_number}."):
                continue
            candidates.append((len(number.split(".")), -priority, number, title))
    if candidates:
        _, _, number, title = max(candidates, key=lambda item: (item[0], item[1]))
        return number, title

    if standard_number:
        title = _page_clause_title(str(row.item_name or "")) or _page_clause_title(
            str(row.standard_requirement or "")
        )
        return standard_number, title or None
    return None


def _anchored_clause_markers(value: str) -> list[tuple[str, str | None]]:
    match = DIRECT_CLAUSE_RE.match(value) or CONTINUATION_CLAUSE_RE.match(value)
    if match is None:
        return []
    root_number = match.group("number")
    markers = [(root_number, _page_clause_title(match.group("title")) or None)]
    clause_matches = list(CLAUSE_NUMBER_RE.finditer(value))
    for index, clause_match in enumerate(clause_matches):
        number = clause_match.group(0)
        if number == root_number or not number.startswith(f"{root_number}."):
            continue
        next_start = clause_matches[index + 1].start() if index + 1 < len(clause_matches) else len(value)
        tail = value[clause_match.end() : next_start]
        markers.append((number, _page_clause_title(tail) or None))
    return markers


def _rows_from_page_text(
    group: InspectionItemGroup,
    page_text_by_page: Mapping[int, str],
) -> list[ReportResultRow]:
    rows: list[ReportResultRow] = []
    item_no = group.display_item_no or group.item_no
    clause_roots = _group_page_clause_roots(group)
    page_numbers = group.pages or sorted(page_text_by_page)
    current_clause_number: str | None = None
    current_clause_title: str | None = None
    for page_number in page_numbers:
        text = str(page_text_by_page.get(page_number) or "")
        if not text.strip():
            continue
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
        section_start = 0
        last_result_index = -1
        shared_context_lines: list[str] = []
        for index, line in enumerate(lines):
            marker = PAGE_CLAUSE_RE.match(line)
            if marker is not None:
                candidate_number = marker.group("number")
                if clause_roots and not any(
                    candidate_number == root or candidate_number.startswith(f"{root}.")
                    for root in clause_roots
                ):
                    current_clause_number = None
                    current_clause_title = None
                    shared_context_lines = []
                    continue
                current_clause_number = candidate_number
                current_clause_title = _page_clause_title(marker.group("title"))
                section_start = index
                last_result_index = index
                shared_context_lines = []
                continue
            if current_clause_number is None:
                continue
            if not _is_page_result_line(line):
                if _is_shared_requirement_context(line) and line not in shared_context_lines:
                    shared_context_lines.append(line)
                continue
            if _is_unit_exponent_line(line, lines[index - 1] if index > 0 else ""):
                continue
            context_start = max(section_start, last_result_index + 1, index - 10)
            local_context_lines = lines[context_start:index]
            context_lines = [*shared_context_lines, *local_context_lines]
            context_lines = list(dict.fromkeys(context_lines))
            context = " ".join([current_clause_title or "", *context_lines]).strip()
            rows.append(
                ReportResultRow(
                    report_clause_number=current_clause_number,
                    report_clause_title=current_clause_title,
                    normalized_clause_title=normalize_semantic_title(current_clause_title),
                    table_row_label=context or current_clause_title,
                    condition=_page_context_condition(local_context_lines),
                    standard_requirement=context or None,
                    test_result=_normalize_result_token(line),
                    conclusion=group.effective_single_conclusion,
                    source_page=page_number,
                    source_row=index,
                    item_no=item_no,
                    diagnostics=["recovered_from_page_text"],
                )
            )
            last_result_index = index
    return rows


def _group_page_clause_roots(group: InspectionItemGroup) -> list[str]:
    roots = {
        value
        for row in group.rows
        if (value := str(row.standard_clause or "").strip())
        and re.fullmatch(r"2(?:\.\d+)+", value)
    }
    if not roots:
        return []
    shallowest = min(len(root.split(".")) for root in roots)
    return sorted(root for root in roots if len(root.split(".")) == shallowest)


def _is_shared_requirement_context(value: str) -> bool:
    compact = re.sub(r"\s+", "", str(value or ""))
    return bool(re.search(r"允许误差|允差|公差|^单位[:：]", compact))


def _page_clause_title(value: str) -> str:
    title = re.split(r"\n|心脏起搏器|应符合|的数值|允许误差", str(value or ""), maxsplit=1)[0]
    return title.strip(" ：:，,。；;")


def _is_page_result_line(value: str) -> bool:
    compact = re.sub(r"\s+", "", str(value or ""))
    if compact in {"符合", "符合要求", "不符合", "不适用", "——"}:
        return True
    return bool(
        re.fullmatch(
            r"(?:[<>≤≥＜＞])?[+＋\-－−]\d+(?:\.\d+)?%?"
            r"(?:[～~至][+＋\-－−]?\d+(?:\.\d+)?%?)?",
            compact,
        )
    )


def _normalize_result_token(value: str) -> str:
    return (
        re.sub(r"\s+", "", str(value or ""))
        .replace("＋", "+")
        .replace("－", "-")
        .replace("−", "-")
        .replace("~", "～")
        .replace("至", "～")
    )


def _is_unit_exponent_line(value: str, previous_line: str) -> bool:
    compact = _normalize_result_token(value)
    if compact != "-1":
        return False
    previous = re.sub(r"\s+", "", str(previous_line or "")).lower()
    return bool(re.search(r"(?:单位[:：]?)?min$", previous))


def _page_context_condition(lines: list[str]) -> str | None:
    joined = " ".join(lines)
    loads = re.findall(r"@\s*\d+(?:\.\d+)?\s*Ω", joined, flags=re.IGNORECASE)
    if loads:
        return re.sub(r"\s+", "", loads[-1])
    condition_values = {
        "心房",
        "心室",
        "起搏",
        "感知",
        "正向",
        "负向",
        "正常状态",
        "单一故障状态",
    }
    for line in reversed(lines):
        compact = re.sub(r"\s+", "", line)
        if compact in condition_values:
            return compact
    return _condition_from_text(joined)


def normalize_semantic_title(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"[（(][^）)]*(?:只适用|适用于)[^）)]*[）)]", "", text)
    text = re.sub(r"[（(](?:只适用|适用于).*$", "", text)
    text = re.sub(r"(?:心脏)?起搏器的", "", text)
    text = re.sub(r"(?:产品)?物理特性及参数", "物理特性", text)
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()
    return text


def _result_payload(row: InspectionItem) -> tuple[str, str, str | None, str | None, list[str]] | None:
    direct = _direct_result(row)
    if direct is not None:
        requirement = " ".join(
            str(value or "").strip()
            for value in (row.item_name, row.standard_requirement)
            if str(value or "").strip()
        )
        label = str(row.item_name or "").strip() or _short_label(requirement)
        return requirement, direct, label or None, _condition_from_text(requirement), []

    if row.sequence is not None or _looks_like_sequence(row.sequence_raw):
        return None
    values = [
        str(value or "").strip()
        for value in (row.sequence_raw, row.item_name, row.standard_clause, row.standard_requirement)
    ]
    while values and not values[-1]:
        values.pop()
    if len(values) < 2 or not _looks_like_result(values[-1]):
        return None
    test_result = values[-1]
    source_values = values[:-1]
    requirement = " | ".join(source_values)
    label = source_values[0] if source_values else None
    condition = " / ".join(source_values[1:-1] if len(source_values) > 2 else []) or _condition_from_text(requirement)
    return requirement, test_result, label, condition or None, ["recovered_result_value_column"]


def _direct_result(row: InspectionItem) -> str | None:
    values = [str(value).strip() for value in row.result_values if str(value or "").strip()]
    if values:
        return " / ".join(values)
    value = str(row.test_result or "").strip()
    return value or None


def _deepest_clause_marker(text: str) -> tuple[str, str | None] | None:
    matches = list(CLAUSE_NUMBER_RE.finditer(text or ""))
    if not matches:
        return None
    match = max(matches, key=lambda item: (len(item.group(0).split(".")), item.start()))
    tail = str(text or "")[match.end() :].strip()
    title = re.split(r"\n|心脏起搏器|应符合|的数值|允许误差", tail, maxsplit=1)[0]
    title = title.strip(" ：:，,。；;")
    return match.group(0), title or None


def _inspection_row_text(row: InspectionItem) -> str:
    return " ".join(
        str(value or "")
        for value in (
            row.sequence_raw,
            row.item_name,
            row.standard_clause,
            row.standard_requirement,
            row.test_result,
        )
        if str(value or "").strip()
    )


def _row_matches_label(row: ReportResultRow, row_label: str | None, condition: str | None) -> bool:
    label = _semantic_key(row_label)
    haystack = _semantic_key(" ".join([row.table_row_label or "", row.condition or "", row.standard_requirement or ""]))
    semantic_label = normalize_semantic_title(row_label)
    semantic_haystack = normalize_semantic_title(
        " ".join([row.table_row_label or "", row.condition or "", row.standard_requirement or ""])
    )
    semantic_match = bool(
        semantic_label
        and semantic_haystack
        and (semantic_label in semantic_haystack or semantic_haystack in semantic_label)
    )
    dimensional_alias = "尺寸" in label and any(token in haystack for token in ("高", "宽", "厚"))
    label_match = (
        not label
        or label in haystack
        or semantic_match
        or dimensional_alias
        or _significant_tokens(label) <= _significant_tokens(haystack)
    )
    condition_match = _conditions_compatible(condition, row.condition or _condition_from_text(row.standard_requirement or ""))
    return label_match and condition_match


def _row_matches_expected(row: ReportResultRow, expected_text: str | None) -> bool:
    expected = _comparable_value(expected_text)
    if not expected:
        return False
    requirement = _comparable_value(row.standard_requirement)
    return bool(requirement and expected in requirement)


def _conditions_compatible(expected: str | None, actual: str | None) -> bool:
    if not _semantic_key(expected):
        return True
    if not _semantic_key(actual):
        return False

    expected_load = _load_condition(expected)
    actual_load = _load_condition(actual)
    if expected_load:
        return expected_load == actual_load

    expected_chamber = _chamber_condition(expected)
    actual_chamber = _chamber_condition(actual)
    if expected_chamber and actual_chamber:
        return expected_chamber == actual_chamber

    expected_action = _action_condition(expected)
    actual_action = _action_condition(actual)
    if expected_action and actual_action:
        return expected_action == actual_action

    expected_key = _semantic_key(expected)
    actual_key = _semantic_key(actual)
    return expected_key in actual_key or actual_key in expected_key


def _titles_compatible(left: str, right: str) -> bool:
    return bool(left and right and (left == right or left in right or right in left))


def _semantic_key(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff@Ω]+", "", text).lower()


def _significant_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z]+|\d+|[\u4e00-\u9fff]{1,6}", value)
        if token not in {"参数", "数值", "要求", "允许误差", "单位"}
    }


def _short_label(value: str) -> str:
    return re.split(r"[:：;；\n]", str(value or ""), maxsplit=1)[0].strip()


def _condition_from_text(value: str) -> str | None:
    text = str(value or "")
    loads = re.findall(r"@\s*\d+(?:\.\d+)?\s*Ω", text, flags=re.IGNORECASE)
    if loads:
        return re.sub(r"\s+", "", loads[-1])
    chambers = re.findall(r"心房|心室", text)
    if chambers:
        return chambers[-1]
    actions = re.findall(r"起搏|感知|正向|负向|正常状态|单一故障状态", text)
    return actions[-1] if actions else None


def _load_condition(value: str | None) -> str | None:
    matches = re.findall(r"@\s*\d+(?:\.\d+)?\s*Ω", str(value or ""), flags=re.IGNORECASE)
    return re.sub(r"\s+", "", matches[-1]).lower() if matches else None


def _chamber_condition(value: str | None) -> str | None:
    matches = re.findall(r"心房|心室", str(value or ""))
    return matches[-1] if matches else None


def _action_condition(value: str | None) -> str | None:
    matches = re.findall(r"起搏|感知|正向|负向|正常状态|单一故障状态", str(value or ""))
    return matches[-1] if matches else None


def _comparable_value(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("μ", "µ").replace("−", "-").replace("－", "-").replace("＋", "+")
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fffµΩ+\-±./]+", "", text).lower()


def _looks_like_result(value: str) -> bool:
    compact = re.sub(r"\s+", "", str(value or ""))
    return bool(compact and RESULT_TOKEN_RE.search(compact))


def _is_numeric_result(value: str) -> bool:
    compact = re.sub(r"\s+", "", str(value or ""))
    return bool(re.search(r"[+\-－＋<>≤≥＜＞]?\d", compact)) and "符合要求" not in compact


def _looks_like_sequence(value: str | None) -> bool:
    return bool(re.fullmatch(r"(?:续\s*)?\d+", re.sub(r"\s+", "", str(value or ""))))


def _invalid_actual(value: str, *, item_no: str | None, clause_number: str | None, page: int | None) -> bool:
    compact = re.sub(r"\s+", "", str(value or ""))
    return compact in {
        re.sub(r"\s+", "", str(item_no or "")),
        re.sub(r"\s+", "", str(clause_number or "")),
        str(page or ""),
    }


def _dedupe_rows(rows: list[ReportResultRow]) -> list[ReportResultRow]:
    result: list[ReportResultRow] = []
    seen: set[tuple] = set()
    for row in rows:
        key = (row.report_clause_number, row.table_row_label, row.condition, row.test_result, row.source_page, row.source_row)
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _dedupe_matching_rows(rows: list[ReportResultRow]) -> list[ReportResultRow]:
    ordered = sorted(rows, key=lambda row: "recovered_from_page_text" in row.diagnostics)
    result: list[ReportResultRow] = []
    seen: set[tuple[str, str]] = set()
    for row in ordered:
        condition = row.condition or _condition_from_text(row.standard_requirement or "")
        key = (_result_semantic_key(row.test_result), _semantic_key(condition))
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _result_semantic_key(value: str) -> str:
    normalized = _normalize_result_token(value)
    if "符合" in normalized and "不符合" not in normalized:
        return "符合"
    return normalized


__all__ = [
    "ReportResultRow",
    "ReportResultRowIndex",
    "build_report_result_row_index",
    "extract_report_clause_marker",
    "normalize_semantic_title",
]
