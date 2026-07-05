from __future__ import annotations

from collections.abc import Sequence
import re
from typing import Any

from app.domain.finding import Finding, FindingSeverity
from app.domain.ptr import PTRClause, PTRDocument
from app.domain.ptr_comparison import (
    PTRComparisonDetails,
    PTRComparisonItem,
    PTRComparisonOverallStatus,
    PTRDisplayFinalStatus,
    PTRNormalizedComparison,
    PTRReportMatch,
    PTRUserFacingStatus,
)
from app.domain.report import InspectionItem, ReportDocument
from app.domain.result import CheckResult
from app.domain.table import CanonicalTable, ParameterRecord


CLAUSE_NUMBER_RE = re.compile(r"\d+(?:\.\d+)+")
USER_PATH_RE = re.compile(r"/Users/[^\s\"'，,；;\)\]\}]+")

MISSING_CODES = {
    "PTR_CLAUSE_MISSING",
    "PTR_TABLE_MISSING",
    "PTR_TABLE_PARAM_MISSING",
}
MISMATCH_CODES = {
    "PTR_CLAUSE_TEXT_MISMATCH",
    "PTR_TABLE_VALUE_MISMATCH",
    "PTR_TABLE_UNIT_MISMATCH",
    "PTR_TABLE_CONDITION_MISMATCH",
    "PTR_TABLE_TOLERANCE_MISMATCH",
}
REVIEW_CODES = {
    "PTR_TABLE_CANDIDATE_AMBIGUOUS",
    "PTR_TABLE_SEGMENT_AMBIGUOUS",
    "PTR_SCOPE_FILTER_REVIEW",
}
PTR_CHECK_IDS = {"PTR_SCOPE", "PTR_CLAUSE", "PTR_TABLE"}


def build_ptr_comparison_details(
    *,
    ptr_doc: PTRDocument,
    report_doc: ReportDocument,
    included_clauses: Sequence[PTRClause],
    check_results: Sequence[CheckResult],
) -> PTRComparisonDetails:
    findings_by_clause = _findings_by_clause(check_results)
    report_matches_by_clause = _report_matches_by_clause(report_doc.inspection_items)
    report_candidates = _candidate_report_items(report_doc.inspection_items)

    items = [
        _comparison_item(
            clause=clause,
            findings=findings_by_clause.get(str(clause.number), []),
            report_matches=report_matches_by_clause.get(str(clause.number), []),
            report_candidates=report_candidates,
            ptr_doc=ptr_doc,
            report_doc=report_doc,
        )
        for clause in included_clauses
    ]
    return _details_from_items(items)


def _comparison_item(
    *,
    clause: PTRClause,
    findings: list[Finding],
    report_matches: list[InspectionItem],
    report_candidates: list[InspectionItem],
    ptr_doc: PTRDocument,
    report_doc: ReportDocument,
) -> PTRComparisonItem:
    clause_number = str(clause.number)
    selected_finding = _primary_finding(findings)
    rule_status = _rule_status(findings)
    user_status = _user_facing_status(findings)
    final_status = _display_final_status(user_status)
    search_keywords = _search_keywords(clause)
    candidate_items = [] if report_matches else [_report_match(item) for item in report_candidates[:5]]

    return PTRComparisonItem(
        ptr_clause_id=clause_number,
        ptr_title=_safe_text(clause.title),
        ptr_page=clause.location.page_number if clause.location else None,
        ptr_requirement_text=_safe_text(clause.body_text or clause.text_content or clause.full_text or ""),
        report_matches=[_report_match(item) for item in report_matches],
        normalized_comparison=_normalized_comparison(
            clause=clause,
            report_matches=report_matches,
            finding=selected_finding,
            ptr_doc=ptr_doc,
            report_doc=report_doc,
        ),
        rule_status=rule_status,
        user_facing_status=user_status,
        final_status=final_status,
        reason=_reason(
            clause=clause,
            finding=selected_finding,
            report_matches=report_matches,
            rule_status=rule_status,
            user_status=user_status,
            search_keywords=search_keywords,
            candidate_items=candidate_items,
        ),
        next_action=_next_action(rule_status, user_status),
        evidence_refs=_evidence_refs(findings),
        search_keywords=search_keywords,
        candidate_report_items=candidate_items,
    )


def _details_from_items(items: list[PTRComparisonItem]) -> PTRComparisonDetails:
    requirements_count = len(items)
    covered_count = sum(1 for item in items if item.user_facing_status in {PTRUserFacingStatus.COVERED_PASSED, PTRUserFacingStatus.REFUTED})
    missing_count = sum(1 for item in items if item.rule_status == PTRUserFacingStatus.MISSING_IN_REPORT and item.user_facing_status != PTRUserFacingStatus.REFUTED)
    mismatch_count = sum(1 for item in items if item.rule_status == PTRUserFacingStatus.VALUE_MISMATCH and item.user_facing_status != PTRUserFacingStatus.REFUTED)
    confirmed_errors_count = sum(1 for item in items if item.user_facing_status == PTRUserFacingStatus.CONFIRMED_ERROR)
    manual_review_required_count = sum(1 for item in items if item.user_facing_status == PTRUserFacingStatus.NEEDS_REVIEW)
    refuted_findings_count = sum(1 for item in items if item.user_facing_status == PTRUserFacingStatus.REFUTED)
    needs_review_count = sum(
        1
        for item in items
        if item.user_facing_status
        in {
            PTRUserFacingStatus.NEEDS_REVIEW,
            PTRUserFacingStatus.CANDIDATE_ISSUE,
            PTRUserFacingStatus.AUDIT_INCOMPLETE,
        }
    )

    if any(item.user_facing_status == PTRUserFacingStatus.AUDIT_INCOMPLETE for item in items):
        overall_status = PTRComparisonOverallStatus.AUDIT_INCOMPLETE
    elif confirmed_errors_count > 0:
        overall_status = PTRComparisonOverallStatus.FAILED
    elif needs_review_count > 0 or missing_count > 0 or mismatch_count > 0:
        overall_status = PTRComparisonOverallStatus.NEEDS_REVIEW
    else:
        overall_status = PTRComparisonOverallStatus.PASSED

    return PTRComparisonDetails(
        overall_status=overall_status,
        overall_summary=(
            f"本次共比对 {requirements_count} 条技术要求，其中 {covered_count} 条已覆盖，"
            f"{needs_review_count} 条需复核，{missing_count} 条未覆盖。"
        ),
        requirements_count=requirements_count,
        covered_count=covered_count,
        missing_count=missing_count,
        mismatch_count=mismatch_count,
        needs_review_count=needs_review_count,
        confirmed_errors_count=confirmed_errors_count,
        manual_review_required_count=manual_review_required_count,
        refuted_findings_count=refuted_findings_count,
        items=items,
    )


def _findings_by_clause(check_results: Sequence[CheckResult]) -> dict[str, list[Finding]]:
    grouped: dict[str, list[Finding]] = {}
    for result in check_results:
        if result.check_id not in PTR_CHECK_IDS:
            continue
        for finding in result.findings:
            clause_number = _finding_clause_number(finding)
            if not clause_number:
                continue
            grouped.setdefault(clause_number, []).append(finding)
    return grouped


def _finding_clause_number(finding: Finding) -> str:
    metadata_value = finding.metadata.get("clause_number")
    if isinstance(metadata_value, str) and metadata_value.strip():
        return metadata_value.strip()
    match = CLAUSE_NUMBER_RE.search(finding.id)
    return match.group(0) if match else ""


def _report_matches_by_clause(report_items: Sequence[InspectionItem]) -> dict[str, list[InspectionItem]]:
    matches: dict[str, list[InspectionItem]] = {}
    for item in report_items:
        for number in _report_item_clause_numbers(item):
            matches.setdefault(number, []).append(item)
    return matches


def _report_item_clause_numbers(item: InspectionItem) -> list[str]:
    text = " ".join([item.standard_clause or "", item.standard_requirement or ""])
    return list(dict.fromkeys(CLAUSE_NUMBER_RE.findall(text)))


def _candidate_report_items(report_items: Sequence[InspectionItem]) -> list[InspectionItem]:
    return list(report_items)


def _report_match(item: InspectionItem) -> PTRReportMatch:
    item_no = item.sequence_raw or (str(item.sequence) if item.sequence is not None else None)
    return PTRReportMatch(
        item_no=_safe_text(item_no),
        report_page=item.source_page or (item.row_location.page_number if item.row_location else None),
        standard_clause=_safe_text(item.standard_clause),
        item_name=_safe_text(item.item_name),
        standard_requirement=_safe_text(item.standard_requirement),
        test_result=_safe_text(item.test_result or "; ".join(item.result_values)),
        single_conclusion=_safe_text(item.conclusion),
        remark=_safe_text(item.remark),
    )


def _primary_finding(findings: list[Finding]) -> Finding | None:
    if not findings:
        return None
    priority = {
        "confirmed": 0,
        "manual_review_required": 1,
        "pending": 2,
        "": 2,
        "refuted": 3,
        "summary_only": 4,
        "out_of_scope": 4,
    }
    return sorted(
        findings,
        key=lambda finding: (
            priority.get(str(finding.metadata.get("final_status") or ""), 2),
            0 if finding.severity == FindingSeverity.ERROR else 1,
        ),
    )[0]


def _rule_status(findings: list[Finding]) -> PTRUserFacingStatus:
    if not findings:
        return PTRUserFacingStatus.COVERED_PASSED
    if any(finding.code in MISSING_CODES for finding in findings):
        return PTRUserFacingStatus.MISSING_IN_REPORT
    if any(finding.code in MISMATCH_CODES for finding in findings):
        return PTRUserFacingStatus.VALUE_MISMATCH
    if any(finding.code in REVIEW_CODES or finding.severity == FindingSeverity.WARN for finding in findings):
        return PTRUserFacingStatus.NEEDS_REVIEW
    return PTRUserFacingStatus.CANDIDATE_ISSUE


def _user_facing_status(findings: list[Finding]) -> PTRUserFacingStatus:
    if not findings:
        return PTRUserFacingStatus.COVERED_PASSED
    statuses = [_status_for_finding(finding) for finding in findings]
    for status in (
        PTRUserFacingStatus.CONFIRMED_ERROR,
        PTRUserFacingStatus.AUDIT_INCOMPLETE,
        PTRUserFacingStatus.NEEDS_REVIEW,
        PTRUserFacingStatus.CANDIDATE_ISSUE,
        PTRUserFacingStatus.REFUTED,
    ):
        if status in statuses:
            return status
    return PTRUserFacingStatus.CANDIDATE_ISSUE


def _status_for_finding(finding: Finding) -> PTRUserFacingStatus:
    final_status = finding.metadata.get("final_status")
    if final_status == "confirmed":
        return PTRUserFacingStatus.CONFIRMED_ERROR if finding.severity == FindingSeverity.ERROR else PTRUserFacingStatus.NEEDS_REVIEW
    if final_status == "refuted":
        return PTRUserFacingStatus.REFUTED
    if final_status == "manual_review_required":
        return PTRUserFacingStatus.NEEDS_REVIEW
    if final_status in {"failed", "audit_failed"}:
        return PTRUserFacingStatus.AUDIT_INCOMPLETE
    if final_status in {"out_of_scope", "summary_only"}:
        return PTRUserFacingStatus.NEEDS_REVIEW
    if finding.metadata.get("codex_required") is True and not finding.metadata.get("codex_review_id"):
        return PTRUserFacingStatus.AUDIT_INCOMPLETE
    if finding.severity == FindingSeverity.ERROR:
        return PTRUserFacingStatus.CANDIDATE_ISSUE
    if finding.severity == FindingSeverity.WARN:
        return PTRUserFacingStatus.NEEDS_REVIEW
    return PTRUserFacingStatus.COVERED_PASSED


def _display_final_status(user_status: PTRUserFacingStatus) -> PTRDisplayFinalStatus:
    if user_status == PTRUserFacingStatus.COVERED_PASSED:
        return PTRDisplayFinalStatus.PASSED
    if user_status == PTRUserFacingStatus.CONFIRMED_ERROR:
        return PTRDisplayFinalStatus.CONFIRMED_ERROR
    if user_status == PTRUserFacingStatus.REFUTED:
        return PTRDisplayFinalStatus.REFUTED
    if user_status == PTRUserFacingStatus.AUDIT_INCOMPLETE:
        return PTRDisplayFinalStatus.AUDIT_INCOMPLETE
    if user_status == PTRUserFacingStatus.CANDIDATE_ISSUE:
        return PTRDisplayFinalStatus.CANDIDATE_ISSUE
    return PTRDisplayFinalStatus.MANUAL_REVIEW_REQUIRED


def _normalized_comparison(
    *,
    clause: PTRClause,
    report_matches: list[InspectionItem],
    finding: Finding | None,
    ptr_doc: PTRDocument,
    report_doc: ReportDocument,
) -> PTRNormalizedComparison:
    if finding is None:
        actual = report_matches[0].standard_requirement if report_matches else None
        return PTRNormalizedComparison(
            requirement_type="coverage" if report_matches else "unknown",
            expected=_safe_text(clause.body_text or clause.text_content or clause.full_text or ""),
            actual=_safe_text(actual),
            status="match" if report_matches else "needs_review",
        )

    expected = _safe_value(finding.expected)
    actual = _safe_value(finding.actual)
    unit = _numeric_unit(expected) or _numeric_unit(actual) or _record_unit_for_finding(finding, ptr_doc, report_doc)
    operator = _numeric_operator(expected) or _numeric_operator(actual)
    requirement_type = "numeric_limit" if operator or unit or _looks_numeric(expected) or _looks_numeric(actual) else "text_requirement"
    status = "needs_review" if finding.severity == FindingSeverity.WARN else "mismatch"
    if finding.code in MISSING_CODES:
        status = "needs_review"
        requirement_type = "coverage"
    return PTRNormalizedComparison(
        requirement_type=requirement_type,
        expected=expected,
        actual=actual,
        unit=unit,
        operator=operator,
        status=status,
    )


def _record_unit_for_finding(finding: Finding, ptr_doc: PTRDocument, report_doc: ReportDocument) -> str | None:
    parameter_name = str(finding.metadata.get("parameter_name") or "")
    table_number = str(finding.metadata.get("table_number") or "")
    if not parameter_name:
        return None
    for table in [*_ptr_tables(ptr_doc, table_number), *_report_tables(report_doc, table_number)]:
        for record in table.parameter_records:
            if _same_parameter(record, parameter_name) and record.unit:
                return _safe_text(record.unit)
    return None


def _ptr_tables(ptr_doc: PTRDocument, table_number: str) -> list[CanonicalTable]:
    tables: list[CanonicalTable] = []
    for ptr_table in ptr_doc.tables:
        if table_number and str(ptr_table.table_number or "") != table_number:
            continue
        if ptr_table.canonical_table is not None:
            tables.append(ptr_table.canonical_table)
    return tables


def _report_tables(report_doc: ReportDocument, table_number: str) -> list[CanonicalTable]:
    tables: list[CanonicalTable] = []
    for key in ("canonical_tables", "parameter_tables", "ptr_compare_tables"):
        tables.extend(_coerce_canonical_tables(report_doc.metadata.get(key)))
    if not table_number:
        return tables
    return [table for table in tables if str(table.table_number or "") == table_number]


def _coerce_canonical_tables(value: Any) -> list[CanonicalTable]:
    if value is None:
        return []
    if isinstance(value, CanonicalTable):
        return [value]
    if isinstance(value, dict):
        if "table_id" in value:
            return [CanonicalTable.model_validate(value)]
        return [table for item in value.values() for table in _coerce_canonical_tables(item)]
    if isinstance(value, (list, tuple)):
        return [table for item in value for table in _coerce_canonical_tables(item)]
    canonical_table = getattr(value, "canonical_table", None)
    if isinstance(canonical_table, CanonicalTable):
        return [canonical_table]
    return []


def _same_parameter(record: ParameterRecord, parameter_name: str) -> bool:
    names = {record.parameter_name, record.raw_name, record.normalized_name, record.parameter_id}
    return parameter_name in {str(name) for name in names if name}


def _reason(
    *,
    clause: PTRClause,
    finding: Finding | None,
    report_matches: list[InspectionItem],
    rule_status: PTRUserFacingStatus,
    user_status: PTRUserFacingStatus,
    search_keywords: list[str],
    candidate_items: list[PTRReportMatch],
) -> str:
    title = _safe_text(clause.title) or f"PTR 条款 {clause.number}"
    if finding is None:
        if report_matches:
            item_no = report_matches[0].sequence_raw or (str(report_matches[0].sequence) if report_matches[0].sequence is not None else "")
            prefix = f"报告序号 {item_no} " if item_no else "报告检验项"
            return _safe_text(f"{prefix}覆盖{title}要求。")
        return _safe_text(f"未发现规则问题，但报告匹配项不足，需人工确认 {title}。")

    if user_status == PTRUserFacingStatus.REFUTED:
        return _safe_text(f"Codex 复审认为规则初筛候选不成立，候选问题已排除。规则初筛：{finding.message}")
    if user_status == PTRUserFacingStatus.CONFIRMED_ERROR:
        return _safe_text(f"Codex 复审确认规则初筛问题。{_rule_reason(rule_status, finding, search_keywords, candidate_items)}")
    if user_status == PTRUserFacingStatus.NEEDS_REVIEW:
        return _safe_text(f"Codex 复审未能确认或排除，需要人工复核。{_rule_reason(rule_status, finding, search_keywords, candidate_items)}")
    if user_status == PTRUserFacingStatus.AUDIT_INCOMPLETE:
        return _safe_text(f"LLM/Codex 复审未完成。{_rule_reason(rule_status, finding, search_keywords, candidate_items)}")
    return _safe_text(f"规则初筛候选，待复审。{_rule_reason(rule_status, finding, search_keywords, candidate_items)}")


def _rule_reason(
    rule_status: PTRUserFacingStatus,
    finding: Finding,
    search_keywords: list[str],
    candidate_items: list[PTRReportMatch],
) -> str:
    if rule_status == PTRUserFacingStatus.MISSING_IN_REPORT:
        candidates = _candidate_summary(candidate_items)
        return f"报告中未找到对应检验项；已搜索关键词：{'、'.join(search_keywords)}；候选报告项：{candidates}。"
    if rule_status == PTRUserFacingStatus.VALUE_MISMATCH:
        return f"规则初筛发现 PTR 要求与报告摘录不一致：{finding.message}"
    if rule_status == PTRUserFacingStatus.NEEDS_REVIEW:
        return f"规则初筛无法唯一判断：{finding.message}"
    return finding.message


def _candidate_summary(items: list[PTRReportMatch]) -> str:
    if not items:
        return "无"
    values = []
    for item in items:
        label = item.item_no or item.standard_clause or item.item_name or "未编号"
        text = item.standard_requirement or item.item_name or ""
        values.append(f"{label}:{text}".strip(":"))
    return "；".join(values)


def _next_action(rule_status: PTRUserFacingStatus, user_status: PTRUserFacingStatus) -> str | None:
    if user_status == PTRUserFacingStatus.REFUTED or user_status == PTRUserFacingStatus.COVERED_PASSED:
        return None
    if rule_status == PTRUserFacingStatus.MISSING_IN_REPORT:
        return "请人工确认报告中是否存在等效检验项或补充报告侧证据。"
    if rule_status == PTRUserFacingStatus.VALUE_MISMATCH:
        return "请复核 PTR 技术要求、报告检验结果和单项结论。"
    return "请人工复核该 PTR 条款与报告摘录。"


def _evidence_refs(findings: list[Finding]) -> list[str]:
    refs: list[str] = []
    for finding in findings:
        refs.append(f"finding:{finding.id}")
        refs.extend(evidence.id for evidence in finding.evidence)
    return list(dict.fromkeys(_safe_text(ref) or "" for ref in refs if ref))


def _search_keywords(clause: PTRClause) -> list[str]:
    keywords = [str(clause.number)]
    if clause.title:
        keywords.append(clause.title)
    words = re.findall(r"[\u4e00-\u9fffA-Za-z0-9%Ωμ]+", clause.body_text or "")
    keywords.extend(word for word in words[:4] if len(word) >= 2)
    return list(dict.fromkeys(_safe_text(keyword) or "" for keyword in keywords if keyword))


def _safe_value(value: Any) -> Any:
    if isinstance(value, str):
        return _safe_text(value)
    if value is None:
        return None
    return _safe_text(str(value))


def _safe_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    text = USER_PATH_RE.sub("[redacted-path]", text)
    text = text.replace("file://", "[redacted-path]")
    text = text.replace("../", "[redacted-path]")
    text = text.replace("..\\", "[redacted-path]")
    return text


def _numeric_operator(value: Any) -> str | None:
    text = str(value or "")
    if "≤" in text or "<=" in text or "不大于" in text or "不超过" in text or "小于等于" in text:
        return "≤"
    if "≥" in text or ">=" in text or "不小于" in text or "不少于" in text or "大于等于" in text:
        return "≥"
    if "<" in text or "小于" in text:
        return "<"
    if ">" in text or "大于" in text:
        return ">"
    return None


def _numeric_unit(value: Any) -> str | None:
    text = str(value or "")
    match = re.search(r"[-+]?\d+(?:\.\d+)?\s*([A-Za-zμΩ°/%套]+)", text)
    if not match:
        return None
    unit = match.group(1)
    return unit or None


def _looks_numeric(value: Any) -> bool:
    return bool(re.search(r"\d", str(value or "")))


__all__ = ["build_ptr_comparison_details"]
