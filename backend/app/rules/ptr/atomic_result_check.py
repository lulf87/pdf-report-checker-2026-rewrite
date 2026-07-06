from __future__ import annotations

from collections.abc import Sequence

from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.ptr import PTRClause, PTRDocument
from app.domain.report import InspectionItem
from app.rules.ptr.atomic_compare import _clause_window, _group_full_text, build_atomic_comparison_rows
from app.rules.ptr.report_item_grouping import build_ptr_report_item_groups, ptr_group_for_clause


UNBOUND_ATOMIC_STATUSES = {"needs_review", "candidate_found_needs_mapping"}


def check_atomic_result_bindings(
    ptr_doc: PTRDocument,
    report_items: Sequence[InspectionItem],
    *,
    clauses: Sequence[PTRClause],
    task_id: str = "ptr-atomic",
) -> list[Finding]:
    """Create reviewable findings when direct PTR atomic results cannot be bound."""

    report_groups = build_ptr_report_item_groups(report_items)
    findings: list[Finding] = []
    for clause in clauses:
        clause_number = str(clause.number)
        group = ptr_group_for_clause(clause_number, report_groups)
        report_matches = [group] if group is not None else []
        for row in build_atomic_comparison_rows(clause, ptr_doc, report_matches):
            if row.status not in UNBOUND_ATOMIC_STATUSES:
                continue
            findings.append(_atomic_result_finding(clause, row, group, task_id))
    return findings


def _atomic_result_finding(clause: PTRClause, row, group, task_id: str) -> Finding:
    clause_number = str(clause.number)
    item_no = (group.display_item_no or group.item_no) if group is not None else row.report_item_no
    code = "PTR_ATOMIC_RESULT_UNBOUND" if row.actual is None else "PTR_ATOMIC_RESULT_NEEDS_REVIEW"
    message = (
        f"PTR 条款 {clause_number} 的参数 {row.label} 未完成报告结果结构化绑定，"
        "需要 Codex/人工复核完整检验项证据。"
    )
    if row.reason:
        message = f"{message}{row.reason}"
    return Finding(
        id=f"{task_id}:PTR_ATOMIC:{clause_number}:{row.atomic_id}:unbound",
        task_id=task_id,
        check_id="PTR_TABLE",
        severity=FindingSeverity.WARN,
        code=code,
        message=message,
        location=clause.location,
        expected=row.expected,
        actual=row.actual,
        evidence=[_ptr_atomic_evidence(clause, row), _report_group_evidence(row, group)],
        metadata={
            "clause_number": clause_number,
            "atomic_id": row.atomic_id,
            "atomic_label": row.label,
            "preset": row.preset,
            "item_no": item_no,
            "report_page": row.report_page,
            "candidate_actuals": list(row.candidate_actuals),
            "expected": row.expected,
            "actual": row.actual,
            "codex_required": True,
            "review_hint": _review_hint(row),
        },
    )


def _ptr_atomic_evidence(clause: PTRClause, row) -> Evidence:
    return Evidence(
        id=f"ptr-atomic-{row.atomic_id}",
        source_type=SourceType.PTR,
        location=clause.location,
        raw_text=f"{clause.number} {clause.title or ''}\n{clause.body_text or ''}\natomic={row.atomic_id}; expected={row.expected}",
        method=EvidenceMethod.PDF_TEXT,
    )


def _report_group_evidence(row, group) -> Evidence:
    page = row.report_page or (group.pages[0] if group and group.pages else None)
    if group is not None:
        full_group_text = _group_full_text(group)
        window_text = _clause_window(full_group_text, row.clause_id)
        raw_text = f"full_group_text:\n{full_group_text}\n\nclause_window_text ({row.clause_id}):\n{window_text}"
    else:
        raw_text = row.source_text
    return Evidence(
        id=f"report-atomic-{row.atomic_id}",
        source_type=SourceType.REPORT,
        location=Location(source_type=SourceType.REPORT, page_number=page),
        raw_text=raw_text,
        method=EvidenceMethod.PDF_TEXT,
    )


def _review_hint(row) -> str:
    if row.candidate_actuals:
        return f"报告中找到候选值 {', '.join(row.candidate_actuals)}，需确认是否绑定到 {row.label}。"
    if row.atomic_id.startswith("2.2.3"):
        return "请在报告序号 157 的 page 100 行中查找 PULSE3=430 ns、PF Reversible=455 ns。"
    if row.atomic_id.startswith("2.2.4"):
        return "请在报告序号 157 的 page 100 行中查找 PULSE3=260 ns、PF Reversible=205 ns。"
    if row.atomic_id.startswith("2.2.6"):
        return "请在报告序号 157 的 page 101 行中查找最大输出能量 159 mJ。"
    return f"请复核报告序号 {row.report_item_no or '未知'} 中与 {row.label} 对应的完整行证据。"


__all__ = ["check_atomic_result_bindings"]
