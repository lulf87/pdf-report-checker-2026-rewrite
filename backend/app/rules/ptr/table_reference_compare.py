from __future__ import annotations

import re

from app.domain.common import Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.ptr import PTRClause, PTRDocument, PTRClauseNumber, TableReference
from app.rules.ptr.atomic_compare import table_for_clause


def check_table_references(
    ptr_doc: PTRDocument,
    *,
    clauses: list[PTRClause] | None = None,
    task_id: str = "ptr-table",
) -> list[Finding]:
    findings: list[Finding] = []
    target_clauses = clauses if clauses is not None else ptr_doc.clauses
    for clause in target_clauses:
        for reference in _references_for_clause(clause):
            candidates = ptr_doc.get_tables_by_number(reference.table_number)
            if not candidates:
                if _has_parent_or_section_table_evidence(clause, reference, ptr_doc):
                    continue
                findings.append(_missing_table_finding(clause, reference, task_id))
            elif len(candidates) > 1 and table_for_clause(clause, ptr_doc) is None:
                findings.append(_ambiguous_table_finding(clause, reference, candidates, task_id))
    return findings


def _references_for_clause(clause: PTRClause) -> list[TableReference]:
    if clause.table_references:
        return clause.table_references
    return [TableReference(table_number=table_number, clause_id=clause.clause_id) for table_number in clause.table_refs]


def _has_parent_or_section_table_evidence(
    clause: PTRClause,
    reference: TableReference,
    ptr_doc: PTRDocument,
) -> bool:
    """Allow a child requirement to use a table caption defined by its parent section.

    Some PTRs place tables immediately under a parent clause such as 2.1, then
    child clauses such as 2.1.1 only say "应符合表3". In that shape, absence of a
    structured PTRTable object should not become a table-missing candidate when
    the parent/same-section text visibly contains the table caption.
    """

    table_number = str(reference.table_number or "").strip()
    if not table_number:
        return False
    for candidate in ptr_doc.clauses:
        if candidate.clause_id == clause.clause_id:
            continue
        if not _is_parent_or_previous_same_section(candidate, clause):
            continue
        if _clause_defines_table(candidate, table_number):
            return True
    return False


def _is_parent_or_previous_same_section(candidate: PTRClause, clause: PTRClause) -> bool:
    if candidate.number == clause.number:
        return False
    if clause.number.is_descendant_of(candidate.number):
        return True
    parent = clause.number.parent()
    if parent is None:
        return False
    if candidate.parent_number != parent:
        return False
    return _safe_number_tuple(candidate.number) < _safe_number_tuple(clause.number)


def _safe_number_tuple(number: PTRClauseNumber) -> tuple[int, ...]:
    return tuple(number.parts)


def _clause_defines_table(clause: PTRClause, table_number: str) -> bool:
    text = "\n".join(
        part
        for part in (
            clause.title or "",
            clause.body_text or "",
            clause.text_content or "",
            clause.full_text or "",
        )
        if part
    )
    normalized_number = _normalize_table_number(table_number)
    for line in text.splitlines():
        normalized_line = _normalize_table_number(line.strip())
        if re.match(rf"^表\s*{re.escape(normalized_number)}(?:\D|$)", normalized_line):
            return True
    return False


def _normalize_table_number(value: str) -> str:
    return str(value or "").translate(str.maketrans({"‑": "-", "－": "-", "–": "-", "—": "-"}))


def _missing_table_finding(clause: PTRClause, reference: TableReference, task_id: str) -> Finding:
    table_number = reference.table_number
    clause_number = str(clause.number)
    return Finding(
        id=f"{task_id}:PTR_TABLE:{clause_number}:table-{table_number}:missing",
        task_id=task_id,
        check_id="PTR_TABLE",
        severity=FindingSeverity.ERROR,
        code="PTR_TABLE_MISSING",
        message=f"PTR 条款 {clause_number} 引用的表 {table_number} 未找到。",
        location=reference.location or clause.location,
        expected=f"表{table_number}",
        actual=None,
        evidence=[_clause_evidence(clause)],
        missing_evidence=[
            MissingEvidence(label=f"表{table_number}", reason="PTR 文档中未找到对应表格。", expected_source=SourceType.PTR)
        ],
        metadata={"clause_number": clause_number, "table_number": table_number},
    )


def _ambiguous_table_finding(clause: PTRClause, reference: TableReference, candidates: list, task_id: str) -> Finding:
    table_number = reference.table_number
    clause_number = str(clause.number)
    candidate_ids = [candidate.table_id for candidate in candidates]
    return Finding(
        id=f"{task_id}:PTR_TABLE:{clause_number}:table-{table_number}:ambiguous",
        task_id=task_id,
        check_id="PTR_TABLE",
        severity=FindingSeverity.WARN,
        code="PTR_TABLE_CANDIDATE_AMBIGUOUS",
        message=f"PTR 条款 {clause_number} 引用的表 {table_number} 存在多个候选。",
        location=reference.location or clause.location,
        expected=f"唯一表{table_number}",
        actual=candidate_ids,
        evidence=[_clause_evidence(clause)],
        metadata={"clause_number": clause_number, "table_number": table_number, "candidate_ids": candidate_ids},
    )


def _clause_evidence(clause: PTRClause) -> Evidence:
    return Evidence(
        id=f"{clause.clause_id}:table-reference",
        source_type=SourceType.PTR,
        location=clause.location,
        raw_text=clause.body_text,
        method=EvidenceMethod.PDF_TEXT,
    )
