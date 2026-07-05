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
from app.domain.report_scope import ExternalStandardRange, ReportInspectionScope
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
    report_candidates = _candidate_report_items(report_doc.inspection_items)
    report_scope = _report_inspection_scope(report_doc)
    scope_consistency = _scope_consistency_metadata(check_results, report_scope)

    items = [
        _comparison_item(
            clause=clause,
            findings=findings_by_clause.get(str(clause.number), []),
            report_matches=_report_matches_for_clause(str(clause.number), report_doc.inspection_items),
            report_candidates=report_candidates,
            external_coverage=_external_standard_coverage(clause, report_scope, report_doc.inspection_items),
            ptr_doc=ptr_doc,
            report_doc=report_doc,
        )
        for clause in included_clauses
    ]
    return _details_from_items(items, scope_consistency=scope_consistency)


def _comparison_item(
    *,
    clause: PTRClause,
    findings: list[Finding],
    report_matches: list[InspectionItem],
    report_candidates: list[InspectionItem],
    external_coverage: dict[str, Any] | None,
    ptr_doc: PTRDocument,
    report_doc: ReportDocument,
) -> PTRComparisonItem:
    clause_number = str(clause.number)
    selected_finding = _primary_finding(findings)
    rule_status = _rule_status(findings)
    user_status = _user_facing_status(findings)
    final_status = _display_final_status(user_status)
    search_keywords = _search_keywords(clause)
    candidate_items = [] if report_matches or external_coverage else [_report_match(item) for item in report_candidates[:5]]

    return PTRComparisonItem(
        ptr_clause_id=clause_number,
        ptr_title=_safe_text(clause.title),
        ptr_page=clause.location.page_number if clause.location else None,
        ptr_requirement_text=_safe_text(clause.body_text or clause.text_content or clause.full_text or ""),
        report_matches=[_report_match(item) for item in report_matches],
        external_standard_coverage=_safe_payload(external_coverage),
        normalized_comparison=_normalized_comparison(
            clause=clause,
            report_matches=report_matches,
            external_coverage=external_coverage,
            finding=selected_finding,
            ptr_doc=ptr_doc,
            report_doc=report_doc,
        ),
        rule_status=rule_status,
        coverage_status=user_status,
        user_facing_status=user_status,
        final_status=final_status,
        reason=_reason(
            clause=clause,
            finding=selected_finding,
            report_matches=report_matches,
            external_coverage=external_coverage,
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


def _details_from_items(items: list[PTRComparisonItem], *, scope_consistency: dict[str, Any] | None = None) -> PTRComparisonDetails:
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
        scope_consistency=_safe_payload(scope_consistency),
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


def _report_item_clause_numbers(item: InspectionItem) -> list[str]:
    text = " ".join([item.standard_clause or "", item.standard_requirement or ""])
    return [number for number in dict.fromkeys(CLAUSE_NUMBER_RE.findall(text)) if number.startswith("2.")]


def _report_matches_for_clause(clause_number: str, report_items: Sequence[InspectionItem]) -> list[InspectionItem]:
    matches: list[InspectionItem] = []
    for item in report_items:
        if any(_related_clause_numbers(clause_number, report_number) for report_number in _report_item_clause_numbers(item)):
            matches.append(item)
    return matches


def _related_clause_numbers(ptr_clause_number: str, report_clause_number: str) -> bool:
    return (
        ptr_clause_number == report_clause_number
        or ptr_clause_number.startswith(report_clause_number + ".")
        or report_clause_number.startswith(ptr_clause_number + ".")
    )


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
    external_coverage: dict[str, Any] | None,
    finding: Finding | None,
    ptr_doc: PTRDocument,
    report_doc: ReportDocument,
) -> PTRNormalizedComparison:
    if finding is None:
        actual = report_matches[0].standard_requirement if report_matches else (external_coverage or {}).get("standard")
        return PTRNormalizedComparison(
            requirement_type="external_standard_coverage" if external_coverage else ("coverage" if report_matches else "unknown"),
            expected=_safe_text(clause.body_text or clause.text_content or clause.full_text or ""),
            actual=_safe_text(actual),
            status="match" if report_matches or external_coverage else "needs_review",
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
    external_coverage: dict[str, Any] | None,
    rule_status: PTRUserFacingStatus,
    user_status: PTRUserFacingStatus,
    search_keywords: list[str],
    candidate_items: list[PTRReportMatch],
) -> str:
    title = _safe_text(clause.title) or f"PTR 条款 {clause.number}"
    if finding is None:
        if external_coverage:
            standard = external_coverage.get("standard")
            start = external_coverage.get("start_item_no")
            end = external_coverage.get("end_item_no")
            return _safe_text(f"报告声明序号 {start}～{end} 为 {standard} 标准内容，可覆盖 {title} 相关外部标准要求。")
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


def _safe_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _safe_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_safe_payload(item) for item in value]
    if isinstance(value, str):
        return _safe_text(value)
    return value


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


def _report_inspection_scope(report_doc: ReportDocument) -> ReportInspectionScope | None:
    raw_scope = report_doc.metadata.get("inspection_scope")
    if isinstance(raw_scope, ReportInspectionScope):
        return raw_scope
    if isinstance(raw_scope, dict):
        return ReportInspectionScope.model_validate(raw_scope)
    return None


def _scope_consistency_metadata(
    check_results: Sequence[CheckResult],
    report_scope: ReportInspectionScope | None,
) -> dict[str, Any] | None:
    for result in check_results:
        if result.check_id == "PTR_REPORT_SCOPE":
            value = result.metadata.get("scope_consistency")
            return _safe_payload(value) if isinstance(value, dict) else None
    if report_scope is None:
        return None
    return _safe_payload(
        {
            "status": "needs_review",
            "declared_scope": list(report_scope.declared_scope_items),
            "declared_scope_ranges": [item.model_dump(mode="json") for item in report_scope.declared_scope_ranges],
            "actual_report_scope": [],
            "external_standard_ranges": [item.model_dump(mode="json") for item in report_scope.external_standard_ranges],
            "excluded_topics": list(report_scope.excluded_topics),
            "ptr_direct_content_starts_after": report_scope.ptr_direct_content_starts_after,
            "reason": "未运行报告检验范围一致性规则。",
        }
    )


def _external_standard_coverage(
    clause: PTRClause,
    report_scope: ReportInspectionScope | None,
    report_items: Sequence[InspectionItem],
) -> dict[str, Any] | None:
    if report_scope is None:
        return None
    clause_text = _normalize_standard_text(" ".join([clause.title or "", clause.body_text or "", clause.full_text or ""]))
    for standard_range in report_scope.external_standard_ranges:
        if _normalize_standard_text(standard_range.standard) not in clause_text:
            continue
        range_items = _items_in_standard_range(report_items, standard_range)
        return {
            "standard": _safe_text(standard_range.standard),
            "start_item_no": standard_range.start_item_no,
            "end_item_no": standard_range.end_item_no,
            "source_page": standard_range.source_page,
            "source_text": _safe_text(standard_range.source_text),
            "item_count": len(range_items),
            "passed_count": sum(1 for item in range_items if _looks_passed(item)),
            "review_count": sum(1 for item in range_items if not _looks_passed(item)),
            "sample_items": [_report_match(item).model_dump(mode="json") for item in range_items[:5]],
        }
    return None


def _items_in_standard_range(
    report_items: Sequence[InspectionItem],
    standard_range: ExternalStandardRange,
) -> list[InspectionItem]:
    start = _safe_int(standard_range.start_item_no)
    end = _safe_int(standard_range.end_item_no)
    if start is None or end is None:
        return []
    return [
        item
        for item in report_items
        if (item_no := _item_no_int(item)) is not None and start <= item_no <= end
    ]


def _item_no_int(item: InspectionItem) -> int | None:
    value = item.sequence_raw or (str(item.sequence) if item.sequence is not None else None)
    if value is None:
        return None
    text = str(value).strip()
    return int(text) if text.isdigit() else None


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    return int(text) if text.isdigit() else None


def _looks_passed(item: InspectionItem) -> bool:
    text = " ".join([item.test_result or "", item.conclusion or "", *item.result_values])
    return "符合" in text and "不符合" not in text


def _normalize_standard_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "").upper()


__all__ = ["build_ptr_comparison_details"]
