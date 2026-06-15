from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import DiffFragment, DiffFragmentKind, Finding, FindingSeverity, MissingEvidence
from app.domain.ptr import PTRClause
from app.domain.report import InspectionItem
from app.infrastructure.text.normalizer import normalize_text


def compare_clause_texts(
    ptr_clauses: list[PTRClause],
    report_items: list[InspectionItem],
    *,
    task_id: str = "ptr-clause",
) -> list[Finding]:
    findings: list[Finding] = []
    report_by_clause = _index_report_items(report_items)
    for clause in ptr_clauses:
        clause_number = str(clause.number)
        report_item = report_by_clause.get(clause_number)
        if report_item is None:
            findings.append(_missing_finding(clause, task_id))
            continue

        expected = normalize_text(clause.body_text or "")
        actual = normalize_text(report_item.standard_requirement or "")
        if _compact(expected) == _compact(actual):
            continue
        findings.append(_mismatch_finding(clause, report_item, expected, actual, task_id))
    return findings


def _index_report_items(report_items: list[InspectionItem]) -> dict[str, InspectionItem]:
    indexed: dict[str, InspectionItem] = {}
    for item in report_items:
        clause_number = _extract_clause_number(item.standard_clause or "")
        if clause_number and clause_number not in indexed:
            indexed[clause_number] = item
            continue
        requirement_clause = _extract_clause_number(item.standard_requirement or "")
        if requirement_clause and requirement_clause not in indexed:
            indexed[requirement_clause] = item
    return indexed


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


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")

