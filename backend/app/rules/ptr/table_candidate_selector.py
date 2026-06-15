from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.domain.common import Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.table import CanonicalTable, CanonicalTableDiagnostics


SIGNATURE_GAP_THRESHOLD = 0.25


@dataclass(frozen=True)
class TableCandidateSelection:
    selected_table: CanonicalTable | None
    findings: list[Finding]
    matching_strategy: str
    candidates: list[CanonicalTable]


def select_report_table_candidate(
    expected_table: CanonicalTable,
    report_tables: list[CanonicalTable],
    *,
    table_number: str,
    task_id: str,
    clause_number: str = "",
) -> TableCandidateSelection:
    """Select the report-side table for a PTR referenced table.

    This helper only chooses candidates and emits ambiguity findings. It does
    not compare parameter values; that remains the job of parameter_compare.
    """

    candidates = [table for table in report_tables if _same_table_number(table.table_number, table_number)]
    if not candidates:
        return TableCandidateSelection(None, [], "no_candidate", [])
    if len(candidates) == 1:
        return TableCandidateSelection(candidates[0], [], "table_number_exact", candidates)

    caption_matches = _caption_matches(expected_table, candidates)
    if len(caption_matches) == 1:
        return TableCandidateSelection(caption_matches[0], [], "caption_normalized", candidates)

    considered_candidates = caption_matches or candidates
    scored = [(table, _parameter_signature_overlap(expected_table, table)) for table in considered_candidates]
    top_score = max(score for _, score in scored)
    top = [table for table, score in scored if score == top_score]
    second_score = max((score for _, score in scored if score < top_score), default=None)
    if top_score > 0 and len(top) == 1 and (second_score is None or top_score - second_score >= SIGNATURE_GAP_THRESHOLD):
        return TableCandidateSelection(top[0], [], "parameter_signature_overlap", candidates)

    merged = [table for table in top if _is_merged_table(table)]
    if len(merged) == 1:
        return TableCandidateSelection(merged[0], [], "merged_table_preferred", candidates)

    return TableCandidateSelection(
        None,
        [
            _ambiguous_report_table_finding(
                expected_table,
                considered_candidates,
                scored,
                task_id,
                clause_number,
                table_number,
            )
        ],
        "ambiguous",
        candidates,
    )


def _same_table_number(left: str | None, right: str) -> bool:
    return str(left or "").strip() == str(right or "").strip()


def _caption_matches(expected_table: CanonicalTable, candidates: list[CanonicalTable]) -> list[CanonicalTable]:
    expected = _normalized_caption(expected_table)
    if not expected:
        return []
    return [candidate for candidate in candidates if _normalized_caption(candidate) == expected]


def _normalized_caption(table: CanonicalTable) -> str:
    raw = table.caption or str(table.metadata.get("source_title") or table.metadata.get("title") or "")
    normalized = unicodedata.normalize("NFKC", raw).lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", normalized)


def _parameter_signature_overlap(expected_table: CanonicalTable, candidate: CanonicalTable) -> float:
    expected = set(_normalized_parameter_names(expected_table))
    actual = set(_normalized_parameter_names(candidate))
    if not expected or not actual:
        return 0.0
    return len(expected & actual) / len(expected)


def _normalized_parameter_names(table: CanonicalTable) -> list[str]:
    names: list[str] = []
    for record in table.parameter_records:
        raw = record.parameter_name or record.raw_name or record.normalized_name or ""
        normalized = re.sub(r"\s+", "", unicodedata.normalize("NFKC", raw).lower())
        if normalized and normalized not in names:
            names.append(normalized)
    return names


def _display_parameter_names(table: CanonicalTable) -> list[str]:
    names: list[str] = []
    for record in table.parameter_records:
        raw = record.parameter_name or record.raw_name or record.normalized_name or ""
        if raw and raw not in names:
            names.append(raw)
    return names


def _is_merged_table(table: CanonicalTable) -> bool:
    if bool(table.metadata.get("merged") or table.metadata.get("continuation_merged")):
        return True
    diagnostics = table.diagnostics
    if isinstance(diagnostics, CanonicalTableDiagnostics):
        return diagnostics.continuation_merged
    if isinstance(diagnostics, list):
        return any("merged" in str(item).lower() for item in diagnostics)
    return False


def _ambiguous_report_table_finding(
    expected_table: CanonicalTable,
    candidates: list[CanonicalTable],
    scored: list[tuple[CanonicalTable, float]],
    task_id: str,
    clause_number: str,
    table_number: str,
) -> Finding:
    score_by_id = {table.table_id: score for table, score in scored}
    actual = [_candidate_summary(candidate, score_by_id.get(candidate.table_id, 0.0)) for candidate in candidates]
    return Finding(
        id=f"{task_id}:PTR_TABLE:{clause_number}:table-{table_number}:report-candidate-ambiguous",
        task_id=task_id,
        check_id="PTR_TABLE",
        severity=FindingSeverity.WARN,
        code="PTR_TABLE_CANDIDATE_AMBIGUOUS",
        message=f"报告侧表 {table_number} 存在多个候选，无法唯一确定用于 PTR 参数比对的表格。",
        location=_first_location(candidates) or _first_location([expected_table]),
        expected=f"表{table_number}",
        actual=actual,
        evidence=[_candidate_evidence(candidate, score_by_id.get(candidate.table_id, 0.0)) for candidate in candidates],
        metadata={
            "clause_number": clause_number,
            "table_number": str(table_number),
            "matching_strategy": "ambiguous",
            "candidate_ids": [candidate.table_id for candidate in candidates],
            "candidate_scores": {candidate.table_id: round(score_by_id.get(candidate.table_id, 0.0), 6) for candidate in candidates},
        },
    )


def _candidate_summary(table: CanonicalTable, score: float) -> dict[str, Any]:
    return {
        "table_id": table.table_id,
        "table_number": table.table_number,
        "caption": table.caption,
        "parameter_names": _display_parameter_names(table),
        "score": round(score, 6),
    }


def _candidate_evidence(table: CanonicalTable, score: float) -> Evidence:
    parameter_names = "、".join(_display_parameter_names(table))
    raw_text = f"{table.caption or table.table_id}；参数：{parameter_names}".strip("；")
    return Evidence(
        id=f"{table.table_id}:candidate",
        source_type=SourceType.REPORT,
        location=_first_location([table]),
        raw_text=raw_text,
        method=EvidenceMethod.PDF_LAYOUT,
        metadata={
            "table_id": table.table_id,
            "table_number": table.table_number,
            "caption": table.caption,
            "score": round(score, 6),
        },
    )


def _first_location(tables: list[CanonicalTable]):
    for table in tables:
        if table.source_locations:
            return table.source_locations[0]
    return None


__all__ = ["TableCandidateSelection", "select_report_table_candidate"]
