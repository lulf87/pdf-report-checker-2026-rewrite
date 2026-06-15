from collections.abc import Sequence

from pydantic import BaseModel, Field

from app.domain.finding import FindingSeverity
from app.domain.result import CheckResult, CheckStatus


STATUS_LABELS: dict[CheckStatus, str] = {
    CheckStatus.PASS: "通过",
    CheckStatus.FAIL: "不通过",
    CheckStatus.REVIEW: "需复核",
    CheckStatus.SKIP: "已跳过",
    CheckStatus.SYSTEM_ERROR: "系统异常",
}

STATUS_VARIANTS: dict[CheckStatus, str] = {
    CheckStatus.PASS: "success",
    CheckStatus.FAIL: "danger",
    CheckStatus.REVIEW: "warn",
    CheckStatus.SKIP: "info",
    CheckStatus.SYSTEM_ERROR: "warn",
}


class ResultPresentationStatus(BaseModel):
    check_id: str
    check_name: str
    status: CheckStatus
    display_label: str
    display_variant: str
    finding_count: int
    severity_counts: dict[str, int]


class PresentationSummary(BaseModel):
    total_checks: int
    status_counts: dict[str, int]
    severity_counts: dict[str, int]
    actionable_finding_count: int
    overall_status: CheckStatus
    display_variant: str
    failed_check_ids: list[str] = Field(default_factory=list)
    review_check_ids: list[str] = Field(default_factory=list)


def _empty_status_counts() -> dict[str, int]:
    return {status.value: 0 for status in CheckStatus}


def _empty_severity_counts() -> dict[str, int]:
    return {severity.value: 0 for severity in FindingSeverity}


def _severity_counts_for_result(result: CheckResult) -> dict[str, int]:
    counts = _empty_severity_counts()
    for finding in result.findings:
        counts[finding.severity.value] += 1
    return counts


def presentation_status_for_result(result: CheckResult) -> ResultPresentationStatus:
    severity_counts = _severity_counts_for_result(result)
    return ResultPresentationStatus(
        check_id=result.check_id,
        check_name=result.check_name,
        status=result.status,
        display_label=STATUS_LABELS[result.status],
        display_variant=STATUS_VARIANTS[result.status],
        finding_count=len(result.findings),
        severity_counts=severity_counts,
    )


def build_presentation_summary(results: Sequence[CheckResult]) -> PresentationSummary:
    status_counts = _empty_status_counts()
    severity_counts = _empty_severity_counts()
    failed_check_ids: list[str] = []
    review_check_ids: list[str] = []

    for result in results:
        status_counts[result.status.value] += 1
        if result.status == CheckStatus.FAIL:
            failed_check_ids.append(result.check_id)
        elif result.status in {CheckStatus.REVIEW, CheckStatus.SYSTEM_ERROR}:
            review_check_ids.append(result.check_id)

        for finding in result.findings:
            severity_counts[finding.severity.value] += 1

    if status_counts[CheckStatus.FAIL.value] > 0:
        overall_status = CheckStatus.FAIL
    elif status_counts[CheckStatus.SYSTEM_ERROR.value] > 0:
        overall_status = CheckStatus.SYSTEM_ERROR
    elif status_counts[CheckStatus.REVIEW.value] > 0:
        overall_status = CheckStatus.REVIEW
    elif results and status_counts[CheckStatus.PASS.value] == 0 and status_counts[CheckStatus.SKIP.value] == len(results):
        overall_status = CheckStatus.SKIP
    else:
        overall_status = CheckStatus.PASS

    return PresentationSummary(
        total_checks=len(results),
        status_counts=status_counts,
        severity_counts=severity_counts,
        actionable_finding_count=severity_counts[FindingSeverity.ERROR.value] + severity_counts[FindingSeverity.WARN.value],
        overall_status=overall_status,
        display_variant=STATUS_VARIANTS[overall_status],
        failed_check_ids=failed_check_ids,
        review_check_ids=review_check_ids,
    )


__all__ = [
    "PresentationSummary",
    "ResultPresentationStatus",
    "build_presentation_summary",
    "presentation_status_for_result",
]
