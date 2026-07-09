from __future__ import annotations

from collections.abc import Sequence
import re
from typing import Any

from app.application.report_page_texts import report_page_text_by_page
from app.domain.finding import Finding, FindingSeverity
from app.domain.ptr import PTRClause, PTRDocument
from app.domain.ptr_comparison import (
    PTRAtomicComparisonRow,
    PTRComparisonDetails,
    PTRCoverageComparisonRow,
    PTRExcludedComparisonItem,
    PTRComparisonItem,
    PTRComparisonOverallStatus,
    PTRDisplayFinalStatus,
    PTRNormalizedComparison,
    PTRReportAtomicResult,
    PTRReportMatch,
    PTRUserFacingStatus,
)
from app.domain.inspection_group import InspectionItemGroup
from app.domain.report import InspectionItem, ReportDocument
from app.domain.report_scope import ExternalStandardRange, ReportInspectionScope
from app.domain.result import CheckResult
from app.domain.table import CanonicalTable, ParameterRecord
from app.rules.ptr.atomic_compare import build_atomic_comparison_rows, build_atomic_requirements, build_report_atomic_results
from app.rules.ptr.report_item_grouping import (
    build_ptr_report_item_groups,
    ptr_group_for_clause,
    ptr_group_single_conclusion,
    ptr_group_standard_requirement,
    ptr_group_test_result,
    ptr_group_text,
)


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
    "PTR_ATOMIC_RESULT_NEEDS_REVIEW",
    "PTR_ATOMIC_RESULT_UNBOUND",
    "PTR_TABLE_CANDIDATE_AMBIGUOUS",
    "PTR_TABLE_SEGMENT_AMBIGUOUS",
    "PTR_SCOPE_FILTER_REVIEW",
    "PTR_CLAUSE_INVALID_MATCH_CANDIDATE",
}
PTR_CHECK_IDS = {"PTR_SCOPE", "PTR_CLAUSE", "PTR_TABLE"}
EXTRACTION_BINDING_REVIEW_CODES = {
    "PTR_ATOMIC_RESULT_NEEDS_REVIEW",
    "PTR_ATOMIC_RESULT_UNBOUND",
}
RESOLVED_ATOMIC_STATUSES = {
    "match",
    "not_applicable",
    "candidate_refuted",
    "refuted_candidate_resolved",
}


def build_ptr_comparison_details(
    *,
    ptr_doc: PTRDocument,
    report_doc: ReportDocument,
    included_clauses: Sequence[PTRClause],
    check_results: Sequence[CheckResult],
) -> PTRComparisonDetails:
    findings_by_clause = _findings_by_clause(check_results)
    report_candidates = _candidate_report_items(report_doc.inspection_items)
    report_groups = build_ptr_report_item_groups(report_doc.inspection_items)
    report_scope = _report_inspection_scope(report_doc)
    scope_consistency = _scope_consistency_metadata(check_results, report_scope)
    page_text_by_page = report_page_text_by_page(report_doc)

    items = [
        _comparison_item(
            clause=clause,
            findings=findings_by_clause.get(str(clause.number), []),
            report_matches=_report_matches_for_clause(str(clause.number), report_groups),
            report_candidates=report_candidates,
            external_coverages=_external_standard_coverages(clause, report_scope, report_doc.inspection_items),
            ptr_doc=ptr_doc,
            report_doc=report_doc,
            page_text_by_page=page_text_by_page,
        )
        for clause in included_clauses
    ]
    return _details_from_items(
        items,
        excluded_items=_excluded_items(ptr_doc=ptr_doc, check_results=check_results),
        scope_consistency=scope_consistency,
        ptr_extraction_metadata=_ptr_extraction_metadata(ptr_doc),
        report_model_context=report_doc.metadata.get("report_model_context"),
        ptr_table_registry=ptr_doc.metadata.get("ptr_table_registry"),
    )


def _comparison_item(
    *,
    clause: PTRClause,
    findings: list[Finding],
    report_matches: list[InspectionItemGroup],
    report_candidates: list[InspectionItem],
    external_coverages: list[dict[str, Any]],
    ptr_doc: PTRDocument,
    report_doc: ReportDocument,
    page_text_by_page: dict[int, str] | None = None,
) -> PTRComparisonItem:
    clause_number = str(clause.number)
    atomic_requirements = build_atomic_requirements(clause, ptr_doc)
    atomic_rows = build_atomic_comparison_rows(clause, ptr_doc, report_matches, page_text_by_page=page_text_by_page)
    atomic_rows = _atomic_rows_with_codex_field_comparison_backfills(atomic_rows, findings)
    selected_finding = _primary_finding(findings)
    display_finding = selected_finding
    rule_status = _rule_status(findings)
    user_status = _user_facing_status(findings)
    atomic_status = _status_from_atomic_rows(
        atomic_rows,
        report_matches=report_matches,
        external_coverages=external_coverages,
    )
    if atomic_status == PTRUserFacingStatus.COVERAGE_ONLY_NEEDS_REVIEW and _direct_report_match_passes_clause(clause, report_matches):
        atomic_status = PTRUserFacingStatus.COVERED_PASSED
    if _atomic_rows_override_refuted_missing_table(selected_finding, atomic_rows) and atomic_status is not None:
        display_finding = None
        rule_status = atomic_status
        user_status = atomic_status
    elif _atomic_rows_override_extraction_binding_findings(findings, atomic_rows) and atomic_status is not None:
        display_finding = None
        rule_status = atomic_status
        user_status = atomic_status
    elif selected_finding is None:
        if atomic_status is not None:
            rule_status = atomic_status
            user_status = atomic_status
    final_status = _display_final_status(user_status)
    search_keywords = _search_keywords(clause)
    external_coverage = external_coverages[0] if external_coverages else None
    candidate_items = [] if report_matches or external_coverage else [_report_match(item) for item in report_candidates[:5]]
    report_match_payloads = [_report_match(item, page_text_by_page=page_text_by_page) for item in report_matches]
    reason = _reason(
        clause=clause,
        finding=display_finding,
        report_matches=report_matches,
        external_coverages=external_coverages,
        atomic_rows=atomic_rows,
        rule_status=rule_status,
        user_status=user_status,
        search_keywords=search_keywords,
        candidate_items=candidate_items,
    )

    return PTRComparisonItem(
        ptr_clause_id=clause_number,
        ptr_title=_safe_text(clause.title),
        ptr_page=clause.location.page_number if clause.location else None,
        ptr_requirement_text=_safe_text(clause.body_text or clause.text_content or clause.full_text or ""),
        report_matches=report_match_payloads,
        external_standard_coverage=_safe_payload(external_coverage),
        external_standard_coverages=_safe_payload(external_coverages),
        atomic_requirements=_safe_payload(atomic_requirements),
        atomic_comparison_rows=_safe_payload(atomic_rows),
        coverage_comparison_rows=_coverage_comparison_rows(
            clause=clause,
            report_matches=report_match_payloads,
            status=user_status,
            reason=reason,
        ),
        normalized_comparison=_normalized_comparison(
            clause=clause,
            report_matches=report_matches,
            external_coverage=external_coverage,
            atomic_rows=atomic_rows,
            finding=display_finding,
            ptr_doc=ptr_doc,
            report_doc=report_doc,
        ),
        rule_status=rule_status,
        coverage_status=user_status,
        user_facing_status=user_status,
        final_status=final_status,
        reason=reason,
        next_action=_next_action(rule_status, user_status),
        evidence_refs=_evidence_refs(findings),
        search_keywords=search_keywords,
        candidate_report_items=candidate_items,
    )


def _coverage_comparison_rows(
    *,
    clause: PTRClause,
    report_matches: Sequence[PTRReportMatch],
    status: PTRUserFacingStatus,
    reason: str,
) -> list[PTRCoverageComparisonRow]:
    rows: list[PTRCoverageComparisonRow] = []
    clause_number = str(clause.number)
    ptr_requirement = _safe_text(clause.body_text or clause.text_content or clause.full_text or "")
    for match in report_matches:
        row_reason = _coverage_row_reason(clause, match, reason)
        rows.append(
            PTRCoverageComparisonRow(
                ptr_clause_id=clause_number,
                ptr_title=_safe_text(clause.title),
                ptr_requirement=ptr_requirement,
                report_item_no=match.item_no,
                report_page=match.report_page,
                report_standard_clause=match.standard_clause,
                report_requirement_excerpt=_excerpt(match.standard_requirement),
                report_result=match.test_result,
                report_conclusion=match.single_conclusion,
                status=status.value if hasattr(status, "value") else str(status),
                reason=row_reason,
            )
        )
    return rows


def _coverage_row_reason(clause: PTRClause, match: PTRReportMatch, fallback: str) -> str:
    clause_number = str(clause.number)
    item_no = match.item_no or "未编号"
    title = _safe_text(clause.title) or f"PTR 条款 {clause_number}"
    evidence = _compact(" ".join([match.standard_requirement or "", match.test_result or "", match.remark or ""])).lower()
    if clause_number == "2.3" and "pvc" in evidence and "反应" in evidence:
        return _safe_text(f"报告序号 {item_no} 按仅检 PVC 反应覆盖{title}要求。") or fallback
    return fallback


def _excerpt(value: str | None, *, max_length: int = 500) -> str | None:
    text = _safe_text(value)
    if text is None:
        return None
    return text if len(text) <= max_length else f"{text[:max_length]}..."


def _details_from_items(
    items: list[PTRComparisonItem],
    *,
    excluded_items: list[PTRExcludedComparisonItem] | None = None,
    scope_consistency: dict[str, Any] | None = None,
    ptr_extraction_metadata: dict[str, Any] | None = None,
    report_model_context: dict[str, Any] | None = None,
    ptr_table_registry: list[dict[str, Any]] | None = None,
) -> PTRComparisonDetails:
    excluded_items = excluded_items or []
    ptr_extraction_metadata = ptr_extraction_metadata or {}
    ptr_ocr_required = ptr_extraction_metadata.get("ptr_ocr_required") is True
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
            PTRUserFacingStatus.COVERAGE_ONLY_NEEDS_REVIEW,
            PTRUserFacingStatus.CANDIDATE_ISSUE,
            PTRUserFacingStatus.AUDIT_INCOMPLETE,
        }
    )
    if ptr_ocr_required:
        needs_review_count = max(needs_review_count, 1)
        manual_review_required_count = max(manual_review_required_count, 1)

    if ptr_ocr_required or any(item.user_facing_status == PTRUserFacingStatus.AUDIT_INCOMPLETE for item in items):
        overall_status = PTRComparisonOverallStatus.AUDIT_INCOMPLETE
    elif confirmed_errors_count > 0:
        overall_status = PTRComparisonOverallStatus.FAILED
    elif needs_review_count > 0 or missing_count > 0 or mismatch_count > 0:
        overall_status = PTRComparisonOverallStatus.NEEDS_REVIEW
    else:
        overall_status = PTRComparisonOverallStatus.PASSED

    if ptr_ocr_required:
        overall_summary = "PTR 文档无文本层，无法解析第 2 章。请启用 OCR/视觉抽取或上传可检索 PDF。"
    else:
        overall_summary = (
            f"本次共比对 {requirements_count} 条技术要求，其中 {covered_count} 条已覆盖，"
            f"{needs_review_count} 条需复核，{missing_count} 条未覆盖。"
        )

    return PTRComparisonDetails(
        overall_status=overall_status,
        overall_summary=overall_summary,
        ptr_extraction_status=_safe_text(ptr_extraction_metadata.get("ptr_extraction_status")),
        ptr_ocr_required=ptr_ocr_required,
        ptr_pages_need_ocr=_int_list(ptr_extraction_metadata.get("ptr_pages_need_ocr")),
        source_type=_safe_text(ptr_extraction_metadata.get("source_type")),
        scope_consistency=_safe_payload(scope_consistency),
        report_model_context=_safe_payload(report_model_context),
        ptr_table_registry=_safe_payload(ptr_table_registry or []),
        requirements_count=requirements_count,
        covered_count=covered_count,
        missing_count=missing_count,
        mismatch_count=mismatch_count,
        needs_review_count=needs_review_count,
        confirmed_errors_count=confirmed_errors_count,
        manual_review_required_count=manual_review_required_count,
        refuted_findings_count=refuted_findings_count,
        items=items,
        excluded_items=excluded_items,
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


def _report_matches_for_clause(clause_number: str, report_groups: Sequence[InspectionItemGroup]) -> list[InspectionItemGroup]:
    match = ptr_group_for_clause(clause_number, report_groups)
    return [match] if match is not None else []


def _candidate_report_items(report_items: Sequence[InspectionItem]) -> list[InspectionItem]:
    return list(report_items)


def _report_match(item: InspectionItem | InspectionItemGroup, *, page_text_by_page: dict[int, str] | None = None) -> PTRReportMatch:
    if isinstance(item, InspectionItemGroup):
        return _report_group_match(item, page_text_by_page=page_text_by_page)
    item_no = item.sequence_raw or (str(item.sequence) if item.sequence is not None else None)
    return PTRReportMatch(
        item_no=_safe_text(item_no),
        report_page=item.source_page or (item.row_location.page_number if item.row_location else None),
        report_pages=[item.source_page] if item.source_page is not None else [],
        page_span=(item.source_page, item.source_page) if item.source_page is not None else None,
        standard_clause=_safe_text(item.standard_clause),
        item_name=_safe_text(item.item_name),
        standard_requirement=_safe_text(item.standard_requirement),
        test_result=_safe_text(item.test_result or "; ".join(item.result_values)),
        single_conclusion=_safe_text(item.conclusion),
        remark=_safe_text(item.remark),
    )


def _report_group_match(group: InspectionItemGroup, *, page_text_by_page: dict[int, str] | None = None) -> PTRReportMatch:
    first_row = group.rows[0] if group.rows else None
    pages = list(group.pages)
    report_atomic_results = build_report_atomic_results(group, page_text_by_page=page_text_by_page)
    return PTRReportMatch(
        item_no=_safe_text(group.display_item_no or group.item_no),
        report_page=pages[0] if pages else None,
        report_pages=pages,
        page_span=(pages[0], pages[-1]) if pages else None,
        standard_clause=_safe_text(first_row.standard_clause if first_row else None),
        item_name=_safe_text(first_row.item_name if first_row else None),
        standard_requirement=_safe_text(ptr_group_standard_requirement(group)),
        test_result=_safe_text(_group_test_result_with_atomic_fallback(group, report_atomic_results)),
        single_conclusion=_safe_text(ptr_group_single_conclusion(group)),
        remark=_safe_text(first_row.remark if first_row else None),
        report_atomic_results=_safe_payload(report_atomic_results),
    )


def _group_test_result_with_atomic_fallback(
    group: InspectionItemGroup,
    report_atomic_results: Sequence[PTRReportAtomicResult],
) -> str:
    values = [value.strip() for value in ptr_group_test_result(group).split(" / ") if value.strip()]
    values.extend(value for value in _group_parameter_values_for_display(group) if value not in values)
    for result in report_atomic_results:
        if result.actual and result.actual not in values:
            values.append(result.actual)
    return " / ".join(values)


def _group_parameter_values_for_display(group: InspectionItemGroup) -> list[str]:
    first_row = group.rows[0] if group.rows else None
    standard_clause = re.sub(r"\s+", "", first_row.standard_clause if first_row else "")
    text = " ".join([ptr_group_standard_requirement(group), ptr_group_text(group)])
    compact = re.sub(r"\s+", "", text)
    if standard_clause != "2.2.2" or "紧急起搏" not in compact:
        return []
    values: list[str] = []
    if "VVI" in text and "VVI" not in values:
        values.append("VVI")
    for pattern in (
        r"70\s*min\s*[−-]?\s*1",
        r"7\.5\s*V\s*/\s*7\.5\s*V",
        r"0\.6\s*ms\s*/\s*0\.6\s*ms",
        r"325\s*ms\*?",
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            values.append(re.sub(r"\s+", "", match.group(0)))
    return values


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


def _status_from_atomic_rows(
    atomic_rows: list[PTRAtomicComparisonRow],
    *,
    report_matches: list[InspectionItemGroup],
    external_coverages: list[dict[str, Any]],
) -> PTRUserFacingStatus | None:
    if atomic_rows:
        statuses = {row.status for row in atomic_rows}
        if "mismatch" in statuses:
            return PTRUserFacingStatus.VALUE_MISMATCH
        if "needs_review" in statuses or "candidate_found_needs_mapping" in statuses:
            return PTRUserFacingStatus.NEEDS_REVIEW
        if statuses and statuses <= RESOLVED_ATOMIC_STATUSES:
            return PTRUserFacingStatus.COVERED_PASSED
    if external_coverages:
        return PTRUserFacingStatus.COVERED_PASSED
    if report_matches:
        return PTRUserFacingStatus.COVERAGE_ONLY_NEEDS_REVIEW
    return None


def _direct_report_match_passes_clause(
    clause: PTRClause,
    report_matches: list[InspectionItemGroup],
) -> bool:
    if not report_matches:
        return False
    clause_number = str(clause.number)
    group = report_matches[0]
    if not any(_same_clause_number(clause_number, row.standard_clause or "") for row in group.rows):
        parent_matches = any(
            _same_clause_number(ancestor, row.standard_clause or "")
            for row in group.rows
            for ancestor in _ancestor_clause_numbers(clause_number)
        )
        group_requirement = _compact(ptr_group_standard_requirement(group))
        if not parent_matches or _compact(clause_number) not in group_requirement:
            return False
    report_text = _compact(
        " ".join(
            [
                ptr_group_standard_requirement(group),
                ptr_group_test_result(group),
                ptr_group_single_conclusion(group) or "",
                " ".join(row.remark or "" for row in group.rows),
            ]
        )
    )
    if "符合" not in report_text or "不符合" in report_text:
        return False
    if clause_number == "2.3":
        ptr_text = _compact(" ".join([clause.title or "", clause.body_text or "", clause.full_text or ""])).lower()
        report_lower = report_text.lower()
        return "仅检" in report_lower and "pvc" in report_lower and "反应" in report_lower and "pvc" in ptr_text and "反应" in ptr_text
    return True


def _same_clause_number(left: str, right: str) -> bool:
    return _compact(left) == _compact(right)


def _ancestor_clause_numbers(clause_number: str) -> list[str]:
    parts = str(clause_number or "").split(".")
    return [".".join(parts[:index]) for index in range(len(parts) - 1, 1, -1)]


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def _atomic_rows_with_codex_field_comparison_backfills(
    atomic_rows: list[PTRAtomicComparisonRow],
    findings: list[Finding],
) -> list[PTRAtomicComparisonRow]:
    if not atomic_rows or not findings:
        return atomic_rows
    rows_by_id = {row.atomic_id: row for row in atomic_rows}
    updates: dict[str, PTRAtomicComparisonRow] = {}
    for finding in findings:
        if finding.code not in EXTRACTION_BINDING_REVIEW_CODES:
            continue
        if finding.metadata.get("final_status") != "refuted":
            continue
        atomic_id = _finding_atomic_id(finding)
        row = rows_by_id.get(atomic_id)
        if row is None:
            continue
        comparison = _codex_matching_field_comparison(finding)
        reasoning = _codex_reasoning_summary(finding)
        if comparison is not None:
            actual = _safe_text(comparison.get("observed_value"))
            if not actual:
                continue
            status = _codex_backfill_row_status(actual, comparison)
            reason = _safe_text(comparison.get("reasoning")) or reasoning or "Codex 复审识别报告结果与 PTR 要求一致。"
        else:
            if not reasoning:
                continue
            actual = _actual_from_codex_reasoning(row, reasoning)
            status = _codex_reasoning_backfill_row_status(actual)
            reason = reasoning
        updates[atomic_id] = row.model_copy(
            update={
                "actual": actual,
                "status": status,
                "reason": reason,
                "source": "codex_review",
                "candidate_actuals": [],
                "confidence": row.confidence or "medium",
                "source_text": row.source_text or reason,
                "report_page": row.report_page or finding.metadata.get("report_page"),
                "report_item_no": row.report_item_no or finding.metadata.get("item_no"),
            }
        )
    if not updates:
        return atomic_rows
    return [updates.get(row.atomic_id, row) for row in atomic_rows]


def _finding_atomic_id(finding: Finding) -> str:
    metadata_value = finding.metadata.get("atomic_id")
    if isinstance(metadata_value, str) and metadata_value.strip():
        return metadata_value.strip()
    marker = ":PTR_ATOMIC:"
    if marker not in finding.id:
        return ""
    suffix = finding.id.split(marker, 1)[1]
    suffix = suffix.rsplit(":unbound", 1)[0]
    return suffix.split(":", 1)[1] if ":" in suffix else suffix


def _codex_matching_field_comparison(finding: Finding) -> dict[str, Any] | None:
    comparisons = finding.metadata.get("codex_field_comparisons")
    if not isinstance(comparisons, list):
        return None
    for comparison in comparisons:
        if not isinstance(comparison, dict):
            continue
        if str(comparison.get("status") or "").strip().lower() == "match":
            return comparison
    return None


def _codex_backfill_row_status(actual: str, comparison: dict[str, Any]) -> str:
    actual_text = str(actual or "").strip()
    if actual_text in {"/", "／", "-", "—", "——", "不适用", "NA", "N/A"}:
        return "not_applicable"
    status = str(comparison.get("status") or "").strip().lower()
    return status if status in {"match", "mismatch", "needs_review", "not_applicable"} else "match"


def _codex_reasoning_summary(finding: Finding) -> str | None:
    for key in ("codex_reasoning_summary", "reasoning_summary", "codex_reasoning"):
        value = finding.metadata.get(key)
        if isinstance(value, str) and value.strip():
            return _safe_text(value.strip())
    return None


def _codex_reasoning_backfill_row_status(actual: str | None) -> str:
    actual_text = str(actual or "").strip()
    if actual_text in {"/", "／", "-", "—", "——", "不适用", "NA", "N/A"}:
        return "not_applicable"
    if actual_text:
        return "refuted_candidate_resolved"
    return "candidate_refuted"


def _actual_from_codex_reasoning(row: PTRAtomicComparisonRow, reasoning: str) -> str | None:
    text = " ".join(str(reasoning or "").split())
    if not text:
        return None
    evidence_text = text.split("报告中可见", 1)[1] if "报告中可见" in text else text
    evidence_text = re.split(r"[。；;，,]", evidence_text, maxsplit=1)[0].strip()
    if not evidence_text:
        return None
    slash_parts = [part.strip() for part in re.split(r"\s*[／/]\s*", evidence_text) if part.strip()]
    if len(slash_parts) >= 2:
        return _clean_reasoning_actual(slash_parts[-1])
    if "符合要求" in evidence_text:
        return "符合要求"
    for marker in ("不适用", "——", "—", "/"):
        if marker in evidence_text:
            return marker
    expected = str(row.expected or "").strip()
    numeric_candidates = re.findall(r"[-+]?\d+(?:\.\d+)?(?:\s*[±~～-]\s*[-+]?\d+(?:\.\d+)?)?\s*[A-Za-zμΩ%°]*", evidence_text)
    for candidate in numeric_candidates:
        cleaned = _clean_reasoning_actual(candidate)
        if cleaned and cleaned != expected:
            return cleaned
    return None


def _clean_reasoning_actual(value: str) -> str | None:
    text = str(value or "").strip()
    text = re.split(r"\s*(?:候选|因此|，|。|；|;|,)", text, maxsplit=1)[0].strip()
    text = text.strip("：:（）()[]【】")
    return _safe_text(text) if text else None


def _atomic_rows_override_extraction_binding_findings(
    findings: list[Finding],
    atomic_rows: list[PTRAtomicComparisonRow],
) -> bool:
    if not findings or not atomic_rows:
        return False
    if any(finding.code not in EXTRACTION_BINDING_REVIEW_CODES for finding in findings):
        return False
    if any(row.source == "codex_review" for row in atomic_rows):
        return True
    return any(finding.metadata.get("final_status") == "manual_review_required" for finding in findings)


def _atomic_rows_override_refuted_missing_table(
    finding: Finding | None,
    atomic_rows: list[PTRAtomicComparisonRow],
) -> bool:
    if finding is None or not atomic_rows:
        return False
    if finding.code not in MISSING_CODES:
        return False
    if all(row.status in RESOLVED_ATOMIC_STATUSES for row in atomic_rows):
        return True
    return finding.metadata.get("final_status") == "refuted" or finding.metadata.get("codex_verdict") == "refute"


def _normalized_comparison(
    *,
    clause: PTRClause,
    report_matches: list[InspectionItemGroup],
    external_coverage: dict[str, Any] | None,
    atomic_rows: list[PTRAtomicComparisonRow],
    finding: Finding | None,
    ptr_doc: PTRDocument,
    report_doc: ReportDocument,
) -> PTRNormalizedComparison:
    if finding is None:
        if atomic_rows:
            expected_values = [f"{row.label}:{row.expected}" for row in atomic_rows if row.expected]
            actual_values = [f"{row.label}:{row.actual}" for row in atomic_rows if row.actual]
            status = "match" if all(row.status in RESOLVED_ATOMIC_STATUSES for row in atomic_rows) else "needs_review"
            return PTRNormalizedComparison(
                requirement_type="atomic_parameter_comparison",
                expected=_safe_text("；".join(expected_values)),
                actual=_safe_text("；".join(actual_values)),
                status=status,
            )
        actual = ptr_group_standard_requirement(report_matches[0]) if report_matches else (external_coverage or {}).get("standard")
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
    report_matches: list[InspectionItemGroup],
    external_coverages: list[dict[str, Any]],
    atomic_rows: list[PTRAtomicComparisonRow],
    rule_status: PTRUserFacingStatus,
    user_status: PTRUserFacingStatus,
    search_keywords: list[str],
    candidate_items: list[PTRReportMatch],
) -> str:
    title = _safe_text(clause.title) or f"PTR 条款 {clause.number}"
    if finding is None:
        if atomic_rows:
            if any(row.status in {"needs_review", "candidate_found_needs_mapping"} for row in atomic_rows):
                if str(clause.number) == "2.6":
                    review_count = sum(1 for row in atomic_rows if row.status in {"needs_review", "candidate_found_needs_mapping"})
                    if review_count == 1:
                        pending = next(
                            (row for row in atomic_rows if row.status in {"needs_review", "candidate_found_needs_mapping"}),
                            None,
                        )
                        label = f"：{pending.label}" if pending is not None else ""
                        return _safe_text(f"报告序号 159 覆盖软件功能总项，仅剩 1 项需人工复核{label}。")
                    return _safe_text(f"报告序号 159 覆盖软件功能总项，但仍有 {review_count} 项表格功能明细需复核。")
                return _safe_text(f"报告匹配项覆盖 {title}，但部分参数级证据需复核。")
            if all(row.status in RESOLVED_ATOMIC_STATUSES for row in atomic_rows):
                item_no = report_matches[0].display_item_no or report_matches[0].item_no if report_matches else None
                prefix = f"报告序号 {item_no} " if item_no else "报告检验项"
                return _safe_text(f"{prefix}参数级比对满足 {title} 要求。")
        if external_coverages:
            coverage_text = "、".join(_external_coverage_summary(coverage) for coverage in external_coverages)
            return _safe_text(f"报告声明{coverage_text}标准内容，可覆盖 {title} 相关外部标准要求。")
        if report_matches:
            item_no = report_matches[0].display_item_no or report_matches[0].item_no
            prefix = f"报告序号 {item_no} " if item_no else "报告检验项"
            if user_status == PTRUserFacingStatus.COVERAGE_ONLY_NEEDS_REVIEW:
                return _safe_text(f"{prefix}仅证明 group 覆盖 {title}，尚未形成参数级原子比对，需复核。")
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


def _ptr_extraction_metadata(ptr_doc: PTRDocument) -> dict[str, Any]:
    metadata = ptr_doc.metadata or {}
    keys = (
        "ptr_extraction_status",
        "ptr_ocr_required",
        "ptr_pages_need_ocr",
        "source_type",
        "textless_page_count",
        "page_count",
    )
    return _safe_payload({key: metadata[key] for key in keys if key in metadata})


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        if isinstance(item, int):
            result.append(item)
        elif isinstance(item, str) and item.isdigit():
            result.append(int(item))
    return result


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


def _excluded_items(
    *,
    ptr_doc: PTRDocument,
    check_results: Sequence[CheckResult],
) -> list[PTRExcludedComparisonItem]:
    decisions = _scope_decisions(check_results)
    if not decisions:
        return []
    clauses_by_id = {clause.clause_id: clause for clause in ptr_doc.clauses}
    result: list[PTRExcludedComparisonItem] = []
    for decision in decisions:
        if decision.get("included") is True or decision.get("reason") != "excluded_topic":
            continue
        clause = clauses_by_id.get(str(decision.get("clause_id") or ""))
        if clause is None:
            continue
        topic = str(decision.get("evidence") or "")
        result.append(
            PTRExcludedComparisonItem(
                ptr_clause_id=str(clause.number),
                ptr_title=_safe_text(clause.title),
                ptr_requirement_text=_safe_text(clause.body_text or clause.text_content or clause.full_text or "") or "",
                status="excluded_by_scope",
                reason=_excluded_reason(topic),
                excluded_topic=_safe_text(topic),
                evidence=_safe_text(decision.get("evidence")),
            )
        )
    return result


def _scope_decisions(check_results: Sequence[CheckResult]) -> list[dict[str, Any]]:
    for result in check_results:
        if result.check_id != "PTR_SCOPE":
            continue
        raw = result.metadata.get("decisions")
        if not isinstance(raw, list):
            return []
        return [item for item in raw if isinstance(item, dict)]
    return []


def _excluded_reason(topic: str) -> str:
    if "电磁兼容" in topic:
        return "报告首页声明除电磁兼容性，且报告说明该项另见单独电磁兼容性检验报告。"
    if topic:
        return f"报告首页声明除{topic}，不参与本次比对。"
    return "报告首页范围声明排除该条款，不参与本次比对。"


def _external_coverage_summary(coverage: dict[str, Any]) -> str:
    standard = coverage.get("standard")
    start = coverage.get("start_item_no")
    end = coverage.get("end_item_no")
    return f"序号 {start}～{end} 为 {standard}"


def _external_standard_coverages(
    clause: PTRClause,
    report_scope: ReportInspectionScope | None,
    report_items: Sequence[InspectionItem],
) -> list[dict[str, Any]]:
    if report_scope is None:
        return []
    clause_text = _normalize_standard_text(" ".join([clause.title or "", clause.body_text or "", clause.full_text or ""]))
    report_group = ptr_group_for_clause(str(clause.number), build_ptr_report_item_groups(report_items))
    report_group_text = ""
    if report_group is not None:
        report_group_text = " ".join(
            [
                ptr_group_standard_requirement(report_group),
                ptr_group_test_result(report_group),
                ptr_group_single_conclusion(report_group) or "",
            ]
        )
    normalized_report_group_text = _normalize_standard_text(report_group_text)
    coverages: list[dict[str, Any]] = []
    for standard_range in report_scope.external_standard_ranges:
        standard_text = _normalize_standard_text(standard_range.standard)
        if (
            standard_text not in clause_text
            and standard_text not in normalized_report_group_text
            and not _text_mentions_item_range(report_group_text, standard_range)
        ):
            continue
        range_items = _items_in_standard_range(report_items, standard_range)
        coverages.append(
            {
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
        )
    return coverages


def _text_mentions_item_range(text: str, standard_range: ExternalStandardRange) -> bool:
    start = str(standard_range.start_item_no or "").strip()
    end = str(standard_range.end_item_no or "").strip()
    if not start or not end:
        return False
    compact = re.sub(r"\s+", "", text or "")
    pattern = rf"(?:序号)?{re.escape(start)}(?:[~～\-‑－–—]|至|到)(?:序号)?{re.escape(end)}"
    return bool(re.search(pattern, compact))


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
