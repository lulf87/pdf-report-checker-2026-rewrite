from enum import StrEnum
from typing import Any, Sequence

from pydantic import BaseModel, Field, model_validator

from app.domain.common import Evidence
from app.domain.codex_review import CodexReviewResult
from app.domain.finding import Finding, FindingSeverity, Severity


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"
    SKIP = "skip"
    SYSTEM_ERROR = "system_error"


class CheckSummary(BaseModel):
    audit_scope: str | None = None
    full_audit: bool | None = None
    final_audit_status: str | None = None
    total_checks: int = Field(default=0, ge=0)
    pass_count: int = Field(default=0, ge=0)
    fail_count: int = Field(default=0, ge=0)
    review_count: int = Field(default=0, ge=0)
    skip_count: int = Field(default=0, ge=0)
    system_error_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    warn_count: int = Field(default=0, ge=0)
    info_count: int = Field(default=0, ge=0)
    candidate_findings_count: int = Field(default=0, ge=0)
    candidate_errors_count: int = Field(default=0, ge=0)
    confirmed_findings_count: int = Field(default=0, ge=0)
    confirmed_errors_count: int = Field(default=0, ge=0)
    refuted_findings_count: int = Field(default=0, ge=0)
    manual_review_required_count: int = Field(default=0, ge=0)
    suggested_additional_findings_count: int = Field(default=0, ge=0)
    out_of_scope_findings_count: int = Field(default=0, ge=0)
    summary_only_findings_count: int = Field(default=0, ge=0)
    unreviewed_required_findings_count: int = Field(default=0, ge=0)
    codex_reviews_count: int = Field(default=0, ge=0)
    codex_runtime_failure_count: int = Field(default=0, ge=0)

    @classmethod
    def from_results(cls, results: Sequence["CheckResult"]) -> "CheckSummary":
        summary = cls(total_checks=len(results))
        for result in results:
            if result.status == CheckStatus.PASS:
                summary.pass_count += 1
            elif result.status == CheckStatus.FAIL:
                summary.fail_count += 1
            elif result.status == CheckStatus.REVIEW:
                summary.review_count += 1
            elif result.status == CheckStatus.SKIP:
                summary.skip_count += 1
            elif result.status == CheckStatus.SYSTEM_ERROR:
                summary.system_error_count += 1

            for finding in result.findings:
                summary.candidate_findings_count += 1
                if finding.severity == FindingSeverity.ERROR:
                    summary.error_count += 1
                    summary.candidate_errors_count += 1
                elif finding.severity == FindingSeverity.WARN:
                    summary.warn_count += 1
                elif finding.severity == FindingSeverity.INFO:
                    summary.info_count += 1

                final_status = finding.metadata.get("final_status")
                if final_status == "confirmed":
                    summary.confirmed_findings_count += 1
                    if finding.severity == FindingSeverity.ERROR:
                        summary.confirmed_errors_count += 1
                elif final_status == "refuted":
                    summary.refuted_findings_count += 1
                elif final_status == "manual_review_required":
                    summary.manual_review_required_count += 1
                elif final_status == "suggested_additional_finding":
                    summary.suggested_additional_findings_count += 1
                elif final_status == "out_of_scope":
                    summary.out_of_scope_findings_count += 1
                elif final_status == "summary_only":
                    summary.summary_only_findings_count += 1

                if finding.metadata.get("codex_required") is True and (
                    not finding.metadata.get("codex_review_id") or not finding.metadata.get("final_status")
                ):
                    summary.unreviewed_required_findings_count += 1

            for review in result.codex_reviews:
                summary.codex_reviews_count += 1
                if review.status in {"failed", "skipped"}:
                    summary.codex_runtime_failure_count += 1
                if review.verdict == "add_finding" and review.suggested_finding is not None and not review.target.finding_id:
                    summary.suggested_additional_findings_count += 1

        return summary


ResultSummary = CheckSummary


class CheckResult(BaseModel):
    task_id: str
    check_id: str
    check_name: str
    status: CheckStatus
    severity: FindingSeverity | None = None
    summary: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    codex_reviews: list[CodexReviewResult] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def infer_default_severity(self) -> "CheckResult":
        if self.severity is not None:
            return self

        if any(finding.severity == FindingSeverity.ERROR for finding in self.findings):
            self.severity = FindingSeverity.ERROR
        elif any(finding.severity == FindingSeverity.WARN for finding in self.findings):
            self.severity = FindingSeverity.WARN
        elif self.status == CheckStatus.FAIL:
            self.severity = FindingSeverity.ERROR
        elif self.status in {CheckStatus.REVIEW, CheckStatus.SYSTEM_ERROR}:
            self.severity = FindingSeverity.WARN
        else:
            self.severity = FindingSeverity.INFO
        return self


__all__ = ["CheckResult", "CheckStatus", "CheckSummary", "ResultSummary", "Severity"]
