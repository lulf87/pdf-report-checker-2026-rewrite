from __future__ import annotations

from app.domain.common import Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.ptr import PTRClause, PTRDocument, TableReference


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
                findings.append(_missing_table_finding(clause, reference, task_id))
            elif len(candidates) > 1:
                findings.append(_ambiguous_table_finding(clause, reference, candidates, task_id))
    return findings


def _references_for_clause(clause: PTRClause) -> list[TableReference]:
    if clause.table_references:
        return clause.table_references
    return [TableReference(table_number=table_number, clause_id=clause.clause_id) for table_number in clause.table_refs]


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

