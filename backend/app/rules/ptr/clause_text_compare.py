from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import DiffFragment, DiffFragmentKind, Finding, FindingSeverity, MissingEvidence
from app.domain.inspection_group import InspectionItemGroup
from app.domain.ptr import PTRClause
from app.domain.report import InspectionItem
from app.rules.ptr.report_item_grouping import (
    build_ptr_report_item_groups,
    ptr_group_compact_rows,
    ptr_group_for_clause,
    ptr_group_invalid_candidates_for_clause,
    ptr_group_standard_requirement,
    ptr_group_supports_clause,
)
from app.infrastructure.text.normalizer import normalize_text


def compare_clause_texts(
    ptr_clauses: list[PTRClause],
    report_items: list[InspectionItem],
    *,
    task_id: str = "ptr-clause",
) -> list[Finding]:
    findings: list[Finding] = []
    report_by_clause = _index_report_items(report_items)
    report_groups = build_ptr_report_item_groups(report_items)
    for clause in ptr_clauses:
        clause_number = str(clause.number)
        report_item = report_by_clause.get(clause_number)
        report_group = ptr_group_for_clause(clause_number, report_groups)
        invalid_candidates = ptr_group_invalid_candidates_for_clause(clause_number, report_groups)
        if report_item is not None:
            if _modifier_limited_report_item_satisfies_clause(clause, report_item):
                continue
            expected = normalize_text(clause.body_text or "")
            actual = normalize_text(report_item.standard_requirement or "")
            if _compact(expected) == _compact(actual):
                continue
            if report_group is not None and len(report_group.rows) > 1 and ptr_group_supports_clause(clause_number, report_group):
                continue
            findings.append(_mismatch_finding(clause, report_item, expected, actual, task_id))
            continue

        if report_group is not None and ptr_group_supports_clause(clause_number, report_group):
            continue

        if invalid_candidates:
            findings.append(_invalid_match_candidate_finding(clause, invalid_candidates, task_id))
            continue

        report_item = _parent_report_item_for_clause(clause_number, report_by_clause)
        if report_item is None:
            findings.append(_missing_finding(clause, task_id))
            continue

        expected = normalize_text(clause.body_text or "")
        actual = normalize_text(ptr_group_standard_requirement(report_group) if report_group is not None else report_item.standard_requirement or "")
        if _compact(expected) == _compact(actual):
            continue
        findings.append(_mismatch_finding(clause, report_item, expected, actual, task_id))
    return findings


def _parent_report_item_for_clause(clause_number: str, report_by_clause: dict[str, InspectionItem]) -> InspectionItem | None:
    parts = clause_number.split(".")
    for index in range(len(parts) - 1, 1, -1):
        parent_number = ".".join(parts[:index])
        if parent_number in report_by_clause:
            return report_by_clause[parent_number]
    return None


def _modifier_limited_report_item_satisfies_clause(clause: PTRClause, report_item: InspectionItem) -> bool:
    clause_number = str(clause.number)
    if clause_number != "2.3":
        return False
    report_text = _compact(
        " ".join(
            [
                report_item.standard_requirement or "",
                report_item.item_name or "",
                report_item.test_result or "",
                report_item.conclusion or "",
                report_item.remark or "",
            ]
        )
    ).lower()
    ptr_text = _compact(" ".join([clause.body_text or "", clause.title or ""])).lower()
    return (
        "仅检" in report_text
        and "pvc" in report_text
        and "反应" in report_text
        and "pvc" in ptr_text
        and "反应" in ptr_text
        and ("符合" in report_text or "pass" in report_text)
    )


def _index_report_items(report_items: list[InspectionItem]) -> dict[str, InspectionItem]:
    indexed: dict[str, InspectionItem] = {}
    for item in report_items:
        clause_number = _extract_clause_number(item.standard_clause or "")
        if clause_number and clause_number not in indexed:
            indexed[clause_number] = item
            continue
        requirement_clause = _extract_clause_number(item.standard_requirement or "")
        if requirement_clause and requirement_clause not in indexed and _can_index_requirement_clause(item, requirement_clause):
            indexed[requirement_clause] = item
    return indexed


def _can_index_requirement_clause(item: InspectionItem, requirement_clause: str) -> bool:
    standard_clause = _extract_clause_number(item.standard_clause or "")
    if not standard_clause:
        text = re.sub(r"\s+", "", item.standard_clause or "")
        return text in {"", "/", "-", "——"}
    return _report_clause_covers_ptr_clause(requirement_clause, standard_clause)


def _missing_finding(clause: PTRClause, task_id: str) -> Finding:
    clause_number = str(clause.number)
    return Finding(
        id=f"{task_id}:PTR_CLAUSE:{clause_number}:missing",
        task_id=task_id,
        check_id="PTR_CLAUSE",
        severity=FindingSeverity.ERROR,
        code="PTR_CLAUSE_MISSING",
        message=f"报告标准要求中未找到 PTR 条款 {clause_number}。",
        location=clause.location,
        expected=normalize_text(clause.body_text),
        actual=None,
        evidence=[_ptr_evidence(clause)],
        missing_evidence=[
            MissingEvidence(
                label="报告标准要求",
                reason=f"未找到标准条款 {clause_number} 对应的报告条款正文。",
                expected_source=SourceType.REPORT,
            )
        ],
        metadata={"clause_number": clause_number},
    )


def _mismatch_finding(
    clause: PTRClause,
    report_item: InspectionItem,
    expected: str,
    actual: str,
    task_id: str,
) -> Finding:
    clause_number = str(clause.number)
    return Finding(
        id=f"{task_id}:PTR_CLAUSE:{clause_number}:mismatch",
        task_id=task_id,
        check_id="PTR_CLAUSE",
        severity=FindingSeverity.ERROR,
        code="PTR_CLAUSE_TEXT_MISMATCH",
        message=f"PTR 条款 {clause_number} 正文与报告标准要求不一致。",
        location=clause.location,
        expected=expected,
        actual=actual,
        evidence=[_ptr_evidence(clause), _report_evidence(report_item, clause_number)],
        diff_fragments=_build_diff(_compact(expected), _compact(actual)),
        metadata={"clause_number": clause_number},
    )


def _invalid_match_candidate_finding(
    clause: PTRClause,
    candidates: list[InspectionItemGroup],
    task_id: str,
) -> Finding:
    clause_number = str(clause.number)
    first_group = candidates[0]
    first_row = first_group.rows[0] if first_group.rows else InspectionItem()
    item_no = first_group.display_item_no or first_group.item_no
    standard_clause = first_row.standard_clause
    return Finding(
        id=f"{task_id}:PTR_CLAUSE:{clause_number}:invalid-match-candidate",
        task_id=task_id,
        check_id="PTR_CLAUSE",
        severity=FindingSeverity.WARN,
        code="PTR_CLAUSE_INVALID_MATCH_CANDIDATE",
        message=(
            f"PTR 条款 {clause_number} 只命中了报告序号 {item_no} 的无关标准条款 "
            f"{standard_clause or '未标注'}，未作为已覆盖结论。"
        ),
        location=clause.location,
        expected=normalize_text(clause.body_text or ""),
        actual=normalize_text(ptr_group_standard_requirement(first_group)),
        evidence=[_ptr_evidence(clause), _report_evidence(first_row, clause_number)],
        metadata={
            "clause_number": clause_number,
            "item_no": item_no,
            "candidate_standard_clause": standard_clause,
            "invalid_candidate_count": len(candidates),
            "invalid_candidates": [
                {
                    "item_no": group.display_item_no or group.item_no,
                    "standard_clause": group.rows[0].standard_clause if group.rows else None,
                    "item_name": group.rows[0].item_name if group.rows else None,
                    "compact_rows": ptr_group_compact_rows(group),
                }
                for group in candidates[:5]
            ],
        },
    )


def _ptr_evidence(clause: PTRClause) -> Evidence:
    clause_number = str(clause.number)
    return Evidence(
        id=f"ptr-clause-{clause_number}",
        source_type=SourceType.PTR,
        location=clause.location,
        raw_text=clause.body_text,
        normalized_text=normalize_text(clause.body_text),
        method=EvidenceMethod.PDF_TEXT,
    )


def _report_evidence(item: InspectionItem, clause_number: str) -> Evidence:
    return Evidence(
        id=f"report-clause-{clause_number}",
        source_type=SourceType.REPORT,
        location=item.row_location
        or Location(source_type=SourceType.REPORT, page_number=item.source_page, row_index=item.row_index_in_page),
        raw_text=item.standard_requirement,
        normalized_text=normalize_text(item.standard_requirement),
        method=EvidenceMethod.PDF_TEXT,
    )


def _build_diff(expected: str, actual: str) -> list[DiffFragment]:
    fragments: list[DiffFragment] = []
    matcher = SequenceMatcher(None, expected, actual, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            fragments.append(DiffFragment(kind=DiffFragmentKind.EQUAL, text=expected[i1:i2], source="both"))
        elif tag == "delete":
            fragments.append(DiffFragment(kind=DiffFragmentKind.DELETE, text=expected[i1:i2], source="ptr"))
        elif tag == "insert":
            fragments.append(DiffFragment(kind=DiffFragmentKind.INSERT, text=actual[j1:j2], source="report"))
        elif tag == "replace":
            fragments.append(DiffFragment(kind=DiffFragmentKind.REPLACE, text=f"{expected[i1:i2]} -> {actual[j1:j2]}", source="both"))
    return fragments


def _extract_clause_number(text: str) -> str:
    match = re.search(r"(\d+(?:\.\d+)+)", text or "")
    return match.group(1) if match else ""


def _report_clause_covers_ptr_clause(ptr_clause_number: str, report_clause_number: str) -> bool:
    ptr_number = _compact(ptr_clause_number)
    report_number = _compact(report_clause_number)
    return (
        bool(ptr_number and report_number)
        and (
            ptr_number == report_number
            or ptr_number.startswith(report_number + ".")
            or report_number.startswith(ptr_number + ".")
        )
    )


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")
