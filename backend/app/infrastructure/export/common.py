from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
import re
from typing import Any, Literal

from app.domain.common import Evidence
from app.domain.finding import Finding, FindingSeverity
from app.domain.result import (
    CheckResult,
    CheckStatus,
    CheckSummary,
    annotate_user_facing_statuses,
    user_facing_status_for_finding,
)


ExportView = Literal["audit", "final"]
FINAL_VISIBLE_FINDING_STATUSES = {
    "confirmed_error",
    "confirmed_issue",
    "confirmed_document_issue",
    "needs_review",
    "needs_policy_review",
    "candidate_issue",
}
FINAL_METADATA_EXCLUDED_KEYS = {
    "audit_options",
    "audit_options_source",
    "effective_audit_options",
    "effective_model",
    "effective_reasoning_effort",
    "model_source",
    "performance_profile",
    "progress_details",
    "reasoning_effort_source",
    "requested_model",
    "requested_profile",
    "requested_reasoning_effort",
}


def build_export_payload(
    results: Sequence[CheckResult],
    *,
    task_id: str | None = None,
    task_type: str | None = None,
    input_files: Sequence[str] | None = None,
    diagnostics: Sequence[str] | None = None,
    metadata: dict[str, Any] | None = None,
    view: ExportView = "audit",
) -> dict[str, Any]:
    if view not in {"audit", "final"}:
        raise ValueError(f"Unsupported export view: {view}")
    export_results = [result.model_copy(deep=True) for result in results]
    annotate_user_facing_statuses(export_results)
    export_metadata = metadata or {}
    if view == "final":
        export_results = [_final_result(result) for result in export_results]
        summary = _final_summary(export_results, export_metadata)
        export_metadata = _sanitize_final_value(export_metadata)
    else:
        summary = CheckSummary.from_results(export_results).model_dump(mode="json")
        codex_audit = export_metadata.get("codex_audit")
        if isinstance(codex_audit, dict):
            for field_name in CheckSummary.model_fields:
                if field_name in codex_audit:
                    summary[field_name] = codex_audit[field_name]
    findings = flatten_findings(export_results)
    return {
        "view": view,
        "task": {
            "task_id": task_id,
            "task_type": task_type,
            "input_files": list(input_files or []),
        },
        "summary": summary,
        "check_results": [_export_result_payload(result, view=view) for result in export_results],
        "findings": [finding.model_dump(mode="json") for finding in findings],
        "evidence": [evidence.model_dump(mode="json") for evidence in flatten_evidence(export_results)],
        "diagnostics": list(diagnostics or []),
        "metadata": export_metadata,
    }


def _export_result_payload(result: CheckResult, *, view: ExportView) -> dict[str, Any]:
    payload = result.model_dump(mode="json")
    if view == "final":
        payload.pop("codex_reviews", None)
        payload.pop("metrics", None)
        payload["final_status"] = result.metadata.get("user_facing_status")
        payload["final_summary"] = result.summary
        return payload
    payload["deterministic_status"] = payload["status"]
    payload["deterministic_summary"] = payload.get("summary")
    payload["final_status"] = result.metadata.get("user_facing_status")
    payload["final_summary"] = _final_result_summary(result)
    return payload


def _final_result(result: CheckResult) -> CheckResult:
    source_metadata = dict(result.metadata)
    has_refuted_finding = any(
        finding.metadata.get("final_status") == "refuted"
        for finding in result.findings
    )
    visible_findings = [finding for finding in result.findings if _finding_visible_in_final_export(finding)]
    result.findings = visible_findings
    result.codex_reviews = []

    statuses = [user_facing_status_for_finding(finding) for finding in visible_findings]
    if result.status == CheckStatus.SYSTEM_ERROR:
        final_status = "audit_incomplete"
        result.severity = FindingSeverity.WARN
    elif any(status in {"confirmed_error", "confirmed_issue"} for status in statuses):
        final_status = "confirmed_error"
        result.status = CheckStatus.FAIL
        result.severity = FindingSeverity.ERROR
    elif "confirmed_document_issue" in statuses:
        final_status = "confirmed_document_issue"
        result.status = CheckStatus.REVIEW
        result.severity = FindingSeverity.WARN
    elif statuses:
        final_status = "needs_review"
        result.status = CheckStatus.REVIEW
        result.severity = FindingSeverity.WARN
    else:
        final_status = "passed"
        result.status = CheckStatus.SKIP if result.status == CheckStatus.SKIP else CheckStatus.PASS
        result.severity = FindingSeverity.INFO

    for finding in visible_findings:
        status = user_facing_status_for_finding(finding)
        if status == "candidate_issue":
            status = "needs_review"
        finding.metadata = _sanitize_final_value(finding.metadata)
        finding.metadata["user_facing_status"] = status

    result.summary = _final_result_summary_from_visible(result, statuses)
    result.metadata = _final_result_metadata(
        source_metadata,
        final_status=final_status,
        has_refuted_finding=has_refuted_finding,
    )
    return result


def _final_result_metadata(
    source_metadata: dict[str, Any],
    *,
    final_status: str,
    has_refuted_finding: bool,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {"user_facing_status": final_status}
    final_details = source_metadata.get("final_comparison_details")
    if isinstance(final_details, dict):
        metadata["comparison_details"] = _sanitize_final_value(final_details)
        return metadata

    if has_refuted_finding:
        return metadata

    comparison_details = source_metadata.get("comparison_details")
    if isinstance(comparison_details, dict):
        metadata["comparison_details"] = _sanitize_final_value(comparison_details)
    explanation_details = source_metadata.get("explanation_details")
    if isinstance(explanation_details, dict):
        metadata["explanation_details"] = _sanitize_final_value(explanation_details)
    return metadata


def _finding_visible_in_final_export(finding: Finding) -> bool:
    if finding.metadata.get("final_status") in {"refuted", "out_of_scope", "summary_only"}:
        return False
    status = str(finding.metadata.get("user_facing_status") or user_facing_status_for_finding(finding))
    return status in FINAL_VISIBLE_FINDING_STATUSES


def _final_result_summary_from_visible(result: CheckResult, statuses: list[str]) -> str:
    confirmed = sum(status in {"confirmed_error", "confirmed_issue"} for status in statuses)
    document_issues = statuses.count("confirmed_document_issue")
    needs_review = sum(
        status in {"needs_review", "needs_policy_review", "candidate_issue"}
        for status in statuses
    )
    parts: list[str] = []
    if confirmed:
        parts.append(f"确认 {confirmed} 项问题")
    if document_issues:
        parts.append(f"确认 {document_issues} 项文档问题")
    if needs_review:
        parts.append(f"{needs_review} 项仍需人工复核")
    if parts:
        return "，".join(parts) + "。"
    if result.status == CheckStatus.SKIP:
        return result.summary or "本项不适用。"
    return "核对通过，未发现最终问题。"


def _final_summary(results: Sequence[CheckResult], metadata: dict[str, Any]) -> dict[str, Any]:
    status_counts = Counter(result.status.value for result in results)
    finding_statuses = [
        str(finding.metadata.get("user_facing_status") or user_facing_status_for_finding(finding))
        for result in results
        for finding in result.findings
    ]
    confirmed_errors = sum(status in {"confirmed_error", "confirmed_issue"} for status in finding_statuses)
    confirmed_document_issues = finding_statuses.count("confirmed_document_issue")
    manual_reviews = sum(
        status in {"needs_review", "needs_policy_review", "candidate_issue"}
        for status in finding_statuses
    )
    policy_reviews = finding_statuses.count("needs_policy_review")
    system_errors = status_counts[CheckStatus.SYSTEM_ERROR.value]
    audit = metadata.get("codex_audit")
    source_final_status = audit.get("final_audit_status") if isinstance(audit, dict) else None
    if source_final_status:
        final_audit_status = source_final_status
    elif system_errors > 0:
        final_audit_status = "audit_failed"
    elif confirmed_errors > 0:
        final_audit_status = "failed"
    elif manual_reviews > 0 or status_counts[CheckStatus.REVIEW.value] > 0:
        final_audit_status = "needs_manual_review"
    else:
        final_audit_status = "passed"

    return {
        "final_audit_status": final_audit_status,
        "total_checks": len(results),
        "pass_count": status_counts[CheckStatus.PASS.value],
        "fail_count": status_counts[CheckStatus.FAIL.value],
        "review_count": status_counts[CheckStatus.REVIEW.value],
        "skip_count": status_counts[CheckStatus.SKIP.value],
        "system_error_count": system_errors,
        "confirmed_findings_count": confirmed_errors + confirmed_document_issues,
        "confirmed_errors_count": confirmed_errors,
        "confirmed_document_issue_count": confirmed_document_issues,
        "manual_review_required_count": manual_reviews,
        "policy_review_required_count": policy_reviews,
    }


def _sanitize_final_value(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if (
                normalized_key.startswith("codex")
                or normalized_key.startswith("candidate_")
                or normalized_key.startswith("refuted_")
                or normalized_key in FINAL_METADATA_EXCLUDED_KEYS
                or normalized_key in {"final_status", "deterministic_status", "deterministic_summary"}
            ):
                continue
            sanitized[str(key)] = _sanitize_final_value(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_final_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_final_value(item) for item in value]
    if isinstance(value, str) and "codex" in value.lower():
        return re.sub(r"codex", "automatic_review", value, flags=re.IGNORECASE)
    return value


def _final_result_summary(result: CheckResult) -> str:
    if not result.findings:
        return result.summary or "未发现问题。"

    statuses = Counter(
        str(finding.metadata.get("user_facing_status") or "candidate_issue")
        for finding in result.findings
    )
    confirmed = sum(
        statuses[status]
        for status in ("confirmed_error", "confirmed_issue", "confirmed_document_issue")
    )
    needs_review = sum(
        statuses[status]
        for status in ("needs_review", "needs_policy_review", "candidate_issue")
    )
    refuted = statuses["refuted"]
    total = len(result.findings)

    if refuted == total:
        return f"规则候选 {total} 项，最终审核后均已排除。"

    parts: list[str] = []
    if confirmed:
        parts.append(f"最终确认 {confirmed} 项问题")
    if needs_review:
        parts.append(f"{needs_review} 项仍需复核")
    if refuted:
        parts.append(f"{refuted} 项候选已排除")
    return "，".join(parts) + "。" if parts else (result.summary or "未发现问题。")


def flatten_findings(results: Sequence[CheckResult]) -> list[Finding]:
    findings: list[Finding] = []
    for result in results:
        findings.extend(result.findings)
    return findings


def flatten_evidence(results: Sequence[CheckResult]) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen_ids: set[str] = set()
    for result in results:
        for item in result.evidence:
            if item.id not in seen_ids:
                evidence.append(item)
                seen_ids.add(item.id)
        for finding in result.findings:
            for item in finding.evidence:
                if item.id not in seen_ids:
                    evidence.append(item)
                    seen_ids.add(item.id)
    return evidence


def evidence_page_label(evidence: Evidence) -> str:
    if evidence.location and evidence.location.page_number is not None:
        return str(evidence.location.page_number)
    return ""
