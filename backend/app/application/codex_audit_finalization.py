from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.codex_audit_targeting import CodexAuditTargetSelection
from app.domain.codex_review import CodexReviewResult
from app.domain.finding import Finding
from app.domain.result import CheckResult, CheckSummary


FINAL_STATUS_CONFIRMED = "confirmed"
FINAL_STATUS_REFUTED = "refuted"
FINAL_STATUS_MANUAL_REVIEW_REQUIRED = "manual_review_required"
FINAL_STATUS_SUGGESTED_ADDITIONAL_FINDING = "suggested_additional_finding"
FINAL_STATUS_OUT_OF_SCOPE = "out_of_scope"
FINAL_STATUS_SUMMARY_ONLY = "summary_only"


def final_status_for_verdict(verdict: str | None) -> str:
    if verdict == "confirm":
        return FINAL_STATUS_CONFIRMED
    if verdict == "refute":
        return FINAL_STATUS_REFUTED
    if verdict == "uncertain":
        return FINAL_STATUS_MANUAL_REVIEW_REQUIRED
    if verdict == "add_finding":
        return FINAL_STATUS_SUGGESTED_ADDITIONAL_FINDING
    return "pending"


def annotate_candidate_findings_with_codex_status(
    check_results: list[CheckResult],
    reviews: list[CodexReviewResult],
) -> None:
    findings_by_id = {
        finding.id: finding
        for check_result in check_results
        for finding in check_result.findings
    }
    for review in reviews:
        finding_id = review.target.finding_id
        if not finding_id or finding_id not in findings_by_id:
            continue
        finding = findings_by_id[finding_id]
        verdict = review.verdict.value if review.verdict is not None else None
        finding.metadata["codex_required"] = True
        finding.metadata["codex_review_id"] = review.review_id
        finding.metadata["codex_verdict"] = verdict
        _copy_visual_review_metadata(finding, review)
        final_status = final_status_for_verdict(verdict)
        diagnostic = _defensive_finalization_diagnostic(finding, review, verdict)
        if diagnostic is not None:
            if diagnostic == "CODEX_CONFIRMED_UNUSED_COMPONENT_GAP":
                final_status = FINAL_STATUS_REFUTED
            else:
                final_status = FINAL_STATUS_MANUAL_REVIEW_REQUIRED
            finding.metadata["codex_finalization_diagnostic"] = diagnostic
            finding.metadata["finalization_reason"] = diagnostic
        review_type = _review_type_for_finding(finding)
        if review_type is not None:
            finding.metadata["review_type"] = review_type
        finding.metadata["final_status"] = final_status


def finalize_codex_audit(
    check_results: list[CheckResult],
    *,
    target_selection: CodexAuditTargetSelection,
    is_reviewable_finding: Callable[[Finding], bool],
) -> dict[str, Any]:
    targeted = target_selection_has_filters(target_selection)

    for result in check_results:
        for finding in result.findings:
            final_status = _metadata_str(finding, "final_status")
            if final_status:
                continue

            if targeted and not target_selection.allows(finding):
                finding.metadata["codex_required"] = False
                finding.metadata["final_status"] = FINAL_STATUS_OUT_OF_SCOPE
                finding.metadata["audit_scope"] = "targeted"
                continue

            if is_reviewable_finding(finding) and target_selection.allows(finding):
                finding.metadata["codex_required"] = True
                continue

            finding.metadata["codex_required"] = False
            finding.metadata["final_status"] = FINAL_STATUS_SUMMARY_ONLY
            finding.metadata["summary_only"] = True

    summary = CheckSummary.from_results(check_results)
    final_audit_status = final_audit_status_for_summary(summary)
    metadata = {
        "audit_scope": "targeted" if targeted else "full",
        "full_audit": not targeted,
        "final_audit_status": final_audit_status,
        "included_check_ids": sorted(target_selection.included_check_ids),
        "included_finding_codes": sorted(target_selection.included_finding_codes),
        "excluded_check_ids": sorted(target_selection.excluded_check_ids),
        "priority_check_ids": list(target_selection.priority_check_ids),
        "candidate_findings_count": summary.candidate_findings_count,
        "candidate_errors_count": summary.candidate_errors_count,
        "confirmed_findings_count": summary.confirmed_findings_count,
        "confirmed_errors_count": summary.confirmed_errors_count,
        "refuted_findings_count": summary.refuted_findings_count,
        "manual_review_required_count": summary.manual_review_required_count,
        "suggested_additional_findings_count": summary.suggested_additional_findings_count,
        "out_of_scope_findings_count": summary.out_of_scope_findings_count,
        "summary_only_findings_count": summary.summary_only_findings_count,
        "unreviewed_required_findings_count": summary.unreviewed_required_findings_count,
        "codex_reviews_count": summary.codex_reviews_count,
        "codex_runtime_failure_count": summary.codex_runtime_failure_count,
    }
    if not targeted and summary.unreviewed_required_findings_count > 0:
        raise RuntimeError(
            "CODEX_AUDIT_INCOMPLETE: "
            f"{summary.unreviewed_required_findings_count} required candidate finding(s) lack Codex finalization."
        )
    return metadata


def target_selection_has_filters(selection: CodexAuditTargetSelection) -> bool:
    return bool(selection.included_check_ids or selection.included_finding_codes or selection.excluded_check_ids)


def final_audit_status_for_summary(summary: CheckSummary) -> str:
    if summary.codex_runtime_failure_count > 0 or summary.unreviewed_required_findings_count > 0:
        return "audit_failed"
    if summary.confirmed_errors_count > 0:
        return "failed"
    if summary.manual_review_required_count > 0:
        return "needs_manual_review"
    return "passed"


def codex_audit_summary_for_results(results: list[CheckResult]) -> dict[str, Any]:
    summary = CheckSummary.from_results(results)
    return {
        "final_audit_status": final_audit_status_for_summary(summary),
        "candidate_findings_count": summary.candidate_findings_count,
        "candidate_errors_count": summary.candidate_errors_count,
        "confirmed_findings_count": summary.confirmed_findings_count,
        "confirmed_errors_count": summary.confirmed_errors_count,
        "refuted_findings_count": summary.refuted_findings_count,
        "manual_review_required_count": summary.manual_review_required_count,
        "suggested_additional_findings_count": summary.suggested_additional_findings_count,
        "out_of_scope_findings_count": summary.out_of_scope_findings_count,
        "summary_only_findings_count": summary.summary_only_findings_count,
        "unreviewed_required_findings_count": summary.unreviewed_required_findings_count,
        "codex_reviews_count": summary.codex_reviews_count,
        "codex_runtime_failure_count": summary.codex_runtime_failure_count,
    }


def _metadata_str(finding: Finding, key: str) -> str | None:
    value = finding.metadata.get(key)
    return value if isinstance(value, str) and value else None


def _copy_visual_review_metadata(finding: Finding, review: CodexReviewResult) -> None:
    if "observed_label_fields" in review.metadata:
        finding.metadata["codex_observed_label_fields"] = review.metadata["observed_label_fields"]
    if "field_comparisons" in review.metadata:
        finding.metadata["codex_field_comparisons"] = review.metadata["field_comparisons"]
    if "visual_evidence_quality" in review.metadata:
        finding.metadata["codex_visual_evidence_quality"] = review.metadata["visual_evidence_quality"]


def _defensive_finalization_diagnostic(
    finding: Finding,
    review: CodexReviewResult,
    verdict: str | None,
) -> str | None:
    if (
        finding.check_id == "C07"
        and finding.code == "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN"
        and verdict in {"confirm", "uncertain"}
    ):
        return "CODEX_CONFIRMED_EXTRACTION_UNCERTAINTY"
    if verdict != "confirm":
        return None
    if (
        finding.check_id == "C04"
        and str(review.metadata.get("visual_evidence_quality") or "").strip().lower()
        in {"unreadable", "wrong_crop"}
    ):
        return "CODEX_CONFIRMED_UNREADABLE_LABEL_IMAGE"
    if finding.check_id in {"C04", "C05", "C06"} and _metadata_bool(
        finding.metadata,
        review.target.metadata,
        key="is_unused_component",
    ):
        return "CODEX_CONFIRMED_UNUSED_COMPONENT_GAP"
    if finding.check_id == "C07" and _metadata_bool(
        finding.metadata,
        review.target.metadata,
        key="complex_matrix_table",
    ):
        return "CODEX_CONFIRMED_COMPLEX_MATRIX_TABLE"
    if (
        finding.check_id == "C04"
        and finding.code == "SAMPLE_COMPONENT_LABEL_NOT_FOUND"
        and _metadata_bool(
            finding.metadata,
            review.target.metadata,
            key="evidence_has_matching_label_caption",
        )
        and _metadata_false(
            finding.metadata,
            review.target.metadata,
            key="evidence_has_matched_label_ocr",
        )
    ):
        return "CODEX_CONFIRMED_LABEL_MISSING_BUT_CAPTION_EXISTS"
    if finding.check_id in {"C04", "C06"} and _metadata_false(
        finding.metadata,
        review.target.metadata,
        key="evidence_can_verify_label_content",
    ):
        return "CODEX_CONFIRMED_UNVERIFIABLE_LABEL_CONTENT"
    return None


def _review_type_for_finding(finding: Finding) -> str | None:
    if finding.check_id != "C07":
        return None
    if finding.code == "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN":
        return "extraction_uncertainty"
    if finding.code == "CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX" or _metadata_bool(
        finding.metadata,
        key="complex_matrix_table",
    ):
        return "complex_matrix"
    return None


def _metadata_bool(*sources: dict[str, Any], key: str) -> bool:
    for source in sources:
        value = source.get(key)
        if value is True:
            return True
        if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}:
            return True
    return False


def _metadata_false(*sources: dict[str, Any], key: str) -> bool:
    for source in sources:
        if key not in source:
            continue
        value = source[key]
        if value is False:
            return True
        if isinstance(value, str) and value.strip().lower() in {"false", "0", "no"}:
            return True
    return False


__all__ = [
    "FINAL_STATUS_CONFIRMED",
    "FINAL_STATUS_MANUAL_REVIEW_REQUIRED",
    "FINAL_STATUS_OUT_OF_SCOPE",
    "FINAL_STATUS_REFUTED",
    "FINAL_STATUS_SUMMARY_ONLY",
    "FINAL_STATUS_SUGGESTED_ADDITIONAL_FINDING",
    "annotate_candidate_findings_with_codex_status",
    "codex_audit_summary_for_results",
    "final_audit_status_for_summary",
    "final_status_for_verdict",
    "finalize_codex_audit",
    "target_selection_has_filters",
]
