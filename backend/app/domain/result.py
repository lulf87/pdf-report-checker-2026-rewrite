from enum import StrEnum
from typing import Any, Sequence

from pydantic import BaseModel, Field, model_validator

from app.domain.common import Evidence
from app.domain.finding import Finding, FindingSeverity, Severity


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"
    SKIP = "skip"
    SYSTEM_ERROR = "system_error"


class CheckSummary(BaseModel):
    total_checks: int = Field(default=0, ge=0)
    pass_count: int = Field(default=0, ge=0)
    fail_count: int = Field(default=0, ge=0)
    review_count: int = Field(default=0, ge=0)
    skip_count: int = Field(default=0, ge=0)
    system_error_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    warn_count: int = Field(default=0, ge=0)
    info_count: int = Field(default=0, ge=0)

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
                if finding.severity == FindingSeverity.ERROR:
                    summary.error_count += 1
                elif finding.severity == FindingSeverity.WARN:
                    summary.warn_count += 1
                elif finding.severity == FindingSeverity.INFO:
                    summary.info_count += 1

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
