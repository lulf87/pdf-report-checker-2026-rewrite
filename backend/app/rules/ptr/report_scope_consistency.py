from __future__ import annotations

import re
from typing import Any

from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.report import InspectionItem
from app.domain.report_scope import ExternalStandardRange, ReportInspectionScope, ReportScopeRange
from app.domain.result import CheckResult, CheckStatus


CLAUSE_NUMBER_RE = re.compile(r"\d+(?:\.\d+)+")


def check_report_scope_consistency(
    report_scope: ReportInspectionScope,
    report_items: list[InspectionItem],
    *,
    task_id: str,
) -> CheckResult:
    actual_scope = _actual_direct_scope(report_scope, report_items)
    findings: list[Finding] = []

    findings.extend(_declared_missing_findings(report_scope, actual_scope, task_id))
    findings.extend(_undeclared_item_findings(report_scope, report_items, task_id))
    findings.extend(_excluded_topic_findings(report_scope, report_items, task_id))
    findings.extend(_external_standard_range_findings(report_scope, report_items, task_id))

    scope_consistency = _scope_consistency_metadata(report_scope, actual_scope, findings)
    return CheckResult(
        task_id=task_id,
        check_id="PTR_REPORT_SCOPE",
        check_name="报告检验范围一致性",
        status=_status_for_findings(findings),
        summary="报告首页检验项目与实际检验表一致。" if not findings else "报告首页检验项目与实际检验表存在不一致。",
        findings=findings,
        evidence=[evidence for finding in findings for evidence in finding.evidence],
        metadata={"scope_consistency": scope_consistency},
    )


def _declared_missing_findings(
    report_scope: ReportInspectionScope,
    actual_scope: list[str],
    task_id: str,
) -> list[Finding]:
    actual = set(actual_scope)
    findings: list[Finding] = []
    for clause_number in report_scope.declared_scope_items:
        if clause_number in actual:
            continue
        findings.append(
            Finding(
                id=f"{task_id}:PTR_REPORT_SCOPE:{clause_number}:declared-missing",
                task_id=task_id,
                check_id="PTR_REPORT_SCOPE",
                severity=FindingSeverity.ERROR,
                code="PTR_SCOPE_DECLARED_ITEM_MISSING_IN_REPORT",
                message=f"报告首页声明检验项目 {clause_number}，但实际检验表未发现对应 2.x 条款。",
                expected=clause_number,
                actual=actual_scope,
                evidence=[_scope_evidence(report_scope)],
                missing_evidence=[
                    MissingEvidence(
                        label="报告实际检验表",
                        reason=f"未找到标准条款 {clause_number} 对应的直接 PTR 检验项。",
                        expected_source=SourceType.REPORT,
                    )
                ],
                metadata={"clause_number": clause_number},
            )
        )
    return findings


def _undeclared_item_findings(
    report_scope: ReportInspectionScope,
    report_items: list[InspectionItem],
    task_id: str,
) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    for item in _direct_report_items(report_scope, report_items):
        clause_number = _root_scope_number(_first_ptr_clause_number(item))
        if not clause_number or _declared_scope_contains(report_scope, clause_number):
            continue
        if clause_number in seen:
            continue
        seen.add(clause_number)
        findings.append(
            Finding(
                id=f"{task_id}:PTR_REPORT_SCOPE:{clause_number}:undeclared",
                task_id=task_id,
                check_id="PTR_REPORT_SCOPE",
                severity=FindingSeverity.ERROR,
                code="PTR_SCOPE_UNDECLARED_REPORT_ITEM",
                message=f"实际检验表出现首页未声明的 PTR 检验项目 {clause_number}。",
                expected=report_scope.declared_scope_items,
                actual=clause_number,
                evidence=[_scope_evidence(report_scope), _report_item_evidence(item, clause_number)],
                metadata={"clause_number": clause_number, "item_no": _item_no(item)},
            )
        )
    return findings


def _excluded_topic_findings(
    report_scope: ReportInspectionScope,
    report_items: list[InspectionItem],
    task_id: str,
) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for item in _direct_report_items(report_scope, report_items):
        item_text = _compact(" ".join([item.standard_clause or "", item.item_name or "", item.standard_requirement or ""]))
        for topic in report_scope.excluded_topics:
            if not _contains_topic(item_text, topic):
                continue
            clause_number = _first_ptr_clause_number(item) or _root_scope_number(_first_ptr_clause_number(item)) or ""
            key = (topic, clause_number or _item_no(item) or "")
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                Finding(
                    id=f"{task_id}:PTR_REPORT_SCOPE:{topic}:{clause_number or _item_no(item)}:excluded",
                    task_id=task_id,
                    check_id="PTR_REPORT_SCOPE",
                    severity=FindingSeverity.ERROR,
                    code="PTR_SCOPE_EXCLUDED_TOPIC_PRESENT",
                    message=f"报告首页声明排除 {topic}，但实际检验表仍出现相关检验项。",
                    expected=f"排除 {topic}",
                    actual=item.standard_requirement or item.item_name or item.standard_clause,
                    evidence=[_scope_evidence(report_scope), _report_item_evidence(item, clause_number)],
                    metadata={
                        "excluded_topic": topic,
                        "clause_number": clause_number,
                        "item_no": _item_no(item),
                    },
                )
            )
    return findings


def _external_standard_range_findings(
    report_scope: ReportInspectionScope,
    report_items: list[InspectionItem],
    task_id: str,
) -> list[Finding]:
    findings: list[Finding] = []
    for standard_range in report_scope.external_standard_ranges:
        range_items = _items_in_external_range(report_items, standard_range)
        start_present = any(_item_no(item) == standard_range.start_item_no for item in range_items)
        end_present = any(_item_no(item) == standard_range.end_item_no for item in range_items)
        standard_present = any(_standard_matches(standard_range.standard, item) for item in range_items)
        if start_present and end_present and standard_present:
            continue
        findings.append(
            Finding(
                id=f"{task_id}:PTR_REPORT_SCOPE:{standard_range.start_item_no}-{standard_range.end_item_no}:range-mismatch",
                task_id=task_id,
                check_id="PTR_REPORT_SCOPE",
                severity=FindingSeverity.ERROR,
                code="PTR_SCOPE_STANDARD_RANGE_MISMATCH",
                message=f"报告声明序号 {standard_range.start_item_no}～{standard_range.end_item_no} 为 {standard_range.standard}，但实际检验表范围或标准名称不一致。",
                expected=standard_range.model_dump(mode="json"),
                actual=[_report_item_summary(item) for item in range_items],
                evidence=[_external_range_evidence(standard_range)],
                missing_evidence=[
                    MissingEvidence(
                        label="报告实际检验表外部标准序号范围",
                        reason="未同时确认范围起点、终点和标准名称。",
                        expected_source=SourceType.REPORT,
                    )
                ],
                metadata={
                    "standard": standard_range.standard,
                    "start_item_no": standard_range.start_item_no,
                    "end_item_no": standard_range.end_item_no,
                    "start_present": start_present,
                    "end_present": end_present,
                    "standard_present": standard_present,
                },
            )
        )
    return findings


def _scope_consistency_metadata(
    report_scope: ReportInspectionScope,
    actual_scope: list[str],
    findings: list[Finding],
) -> dict[str, Any]:
    status = "passed" if not findings else "failed"
    return {
        "status": status,
        "declared_scope": list(report_scope.declared_scope_items),
        "declared_scope_ranges": [item.model_dump(mode="json") for item in report_scope.declared_scope_ranges],
        "actual_report_scope": actual_scope,
        "external_standard_ranges": [item.model_dump(mode="json") for item in report_scope.external_standard_ranges],
        "excluded_topics": list(report_scope.excluded_topics),
        "ptr_direct_content_starts_after": report_scope.ptr_direct_content_starts_after,
        "source_page": report_scope.source_page,
        "source_text": report_scope.source_text,
        "reason": "报告首页声明与实际检验表一致。" if status == "passed" else "报告首页声明与实际检验表存在不一致。",
    }


def _actual_direct_scope(report_scope: ReportInspectionScope, report_items: list[InspectionItem]) -> list[str]:
    scope: list[str] = []
    for item in _direct_report_items(report_scope, report_items):
        root = _root_scope_number(_first_ptr_clause_number(item))
        if root and root not in scope:
            scope.append(root)
    return scope


def _direct_report_items(report_scope: ReportInspectionScope, report_items: list[InspectionItem]) -> list[InspectionItem]:
    return [item for item in report_items if not _item_in_any_external_range(item, report_scope.external_standard_ranges)]


def _item_in_any_external_range(item: InspectionItem, ranges: list[ExternalStandardRange]) -> bool:
    item_no = _item_no_int(item)
    if item_no is None:
        return False
    for standard_range in ranges:
        start = _safe_int(standard_range.start_item_no)
        end = _safe_int(standard_range.end_item_no)
        if start is None or end is None:
            continue
        if start <= item_no <= end:
            return True
    return False


def _items_in_external_range(report_items: list[InspectionItem], standard_range: ExternalStandardRange) -> list[InspectionItem]:
    start = _safe_int(standard_range.start_item_no)
    end = _safe_int(standard_range.end_item_no)
    if start is None or end is None:
        return []
    return [item for item in report_items if (item_no := _item_no_int(item)) is not None and start <= item_no <= end]


def _declared_scope_contains(report_scope: ReportInspectionScope, clause_number: str) -> bool:
    if clause_number in report_scope.declared_scope_items:
        return True
    number_tuple = _number_tuple(clause_number)
    return any(_range_contains(number_tuple, scope_range) for scope_range in report_scope.declared_scope_ranges)


def _range_contains(number_tuple: tuple[int, ...], scope_range: ReportScopeRange) -> bool:
    start = _number_tuple(scope_range.start)
    end = _number_tuple(scope_range.end)
    if not number_tuple or not start or not end:
        return False
    depth = min(len(start), len(end), len(number_tuple))
    return start[:depth] <= number_tuple[:depth] <= end[:depth]


def _first_ptr_clause_number(item: InspectionItem) -> str:
    text = " ".join([item.standard_clause or "", item.standard_requirement or ""])
    for match in CLAUSE_NUMBER_RE.findall(text):
        if match.startswith("2."):
            return match
    return ""


def _root_scope_number(clause_number: str) -> str:
    parts = clause_number.split(".")
    if len(parts) < 2 or parts[0] != "2":
        return ""
    return ".".join(parts[:2])


def _number_tuple(value: str) -> tuple[int, ...]:
    parts = []
    for token in value.split("."):
        if not token.isdigit():
            return tuple()
        parts.append(int(token))
    return tuple(parts)


def _contains_topic(item_text: str, topic: str) -> bool:
    compact_topic = _compact(topic)
    reduced = compact_topic.rstrip("性")
    return bool(
        compact_topic
        and (
            compact_topic in item_text
            or (reduced and reduced in item_text)
            or f"{compact_topic}性" in item_text
        )
    )


def _standard_matches(expected: str, item: InspectionItem) -> bool:
    expected_norm = _normalize_standard(expected)
    if not expected_norm:
        return False
    actual_text = " ".join([item.standard_clause or "", item.standard_requirement or "", item.item_name or ""])
    return expected_norm in _normalize_standard(actual_text)


def _normalize_standard(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).upper()


def _scope_evidence(report_scope: ReportInspectionScope) -> Evidence:
    return Evidence(
        id="report-scope-declaration",
        source_type=SourceType.REPORT,
        location=Location(source_type=SourceType.REPORT, page_number=report_scope.source_page),
        raw_text=report_scope.source_text,
        method=EvidenceMethod.PDF_TEXT,
    )


def _external_range_evidence(standard_range: ExternalStandardRange) -> Evidence:
    return Evidence(
        id=f"report-external-standard-range-{standard_range.start_item_no}-{standard_range.end_item_no}",
        source_type=SourceType.REPORT,
        location=Location(source_type=SourceType.REPORT, page_number=standard_range.source_page),
        raw_text=standard_range.source_text,
        method=EvidenceMethod.PDF_TEXT,
        metadata={"standard": standard_range.standard},
    )


def _report_item_evidence(item: InspectionItem, clause_number: str) -> Evidence:
    item_no = _item_no(item) or clause_number or "unknown"
    return Evidence(
        id=f"report-inspection-item-{item_no}",
        source_type=SourceType.REPORT,
        location=item.row_location
        or Location(source_type=SourceType.REPORT, page_number=item.source_page, row_index=item.row_index_in_page),
        raw_text="；".join(filter(None, [item.standard_clause, item.standard_requirement, item.test_result, item.conclusion])),
        method=EvidenceMethod.PDF_TEXT,
        metadata=_report_item_summary(item),
    )


def _report_item_summary(item: InspectionItem) -> dict[str, Any]:
    return {
        "item_no": _item_no(item),
        "page": item.source_page,
        "standard_clause": item.standard_clause,
        "standard_requirement": item.standard_requirement,
        "test_result": item.test_result,
        "single_conclusion": item.conclusion,
        "remark": item.remark,
    }


def _item_no(item: InspectionItem) -> str | None:
    return item.sequence_raw or (str(item.sequence) if item.sequence is not None else None)


def _item_no_int(item: InspectionItem) -> int | None:
    value = _item_no(item)
    return _safe_int(value)


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    return int(text) if text.isdigit() else None


def _status_for_findings(findings: list[Finding]) -> CheckStatus:
    if any(finding.severity == FindingSeverity.ERROR for finding in findings):
        return CheckStatus.FAIL
    if any(finding.severity == FindingSeverity.WARN for finding in findings):
        return CheckStatus.REVIEW
    return CheckStatus.PASS


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


__all__ = ["check_report_scope_consistency"]
