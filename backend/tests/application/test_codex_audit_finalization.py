from app.application.codex_audit_finalization import final_audit_status_for_summary
from app.domain.result import CheckSummary


def test_final_audit_status_requires_manual_review_when_no_confirmed_errors_but_manual_review_remains() -> None:
    summary = CheckSummary(
        confirmed_errors_count=0,
        manual_review_required_count=34,
        codex_runtime_failure_count=0,
        unreviewed_required_findings_count=0,
    )

    assert final_audit_status_for_summary(summary) == "needs_manual_review"


def test_final_audit_status_passes_when_no_confirmed_errors_and_no_manual_review_remains() -> None:
    summary = CheckSummary(
        confirmed_errors_count=0,
        manual_review_required_count=0,
        codex_runtime_failure_count=0,
        unreviewed_required_findings_count=0,
    )

    assert final_audit_status_for_summary(summary) == "passed"


def test_final_audit_status_fails_when_codex_confirms_errors() -> None:
    summary = CheckSummary(
        confirmed_errors_count=1,
        manual_review_required_count=0,
        codex_runtime_failure_count=0,
        unreviewed_required_findings_count=0,
    )

    assert final_audit_status_for_summary(summary) == "failed"


def test_final_audit_status_reports_audit_failed_for_runtime_or_incomplete_audit() -> None:
    runtime_failure_summary = CheckSummary(codex_runtime_failure_count=1)
    incomplete_summary = CheckSummary(unreviewed_required_findings_count=1)

    assert final_audit_status_for_summary(runtime_failure_summary) == "audit_failed"
    assert final_audit_status_for_summary(incomplete_summary) == "audit_failed"
