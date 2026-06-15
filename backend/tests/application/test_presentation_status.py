from app.application.presentation_status import build_presentation_summary, presentation_status_for_result
from app.domain.result import CheckStatus
from tests.fixtures.export_result_builder import sample_check_results


def test_build_presentation_summary_counts_status_and_severity() -> None:
    summary = build_presentation_summary(sample_check_results(task_id="task-presentation"))

    assert summary.total_checks == 3
    assert summary.status_counts == {
        "pass": 1,
        "fail": 1,
        "review": 1,
        "skip": 0,
        "system_error": 0,
    }
    assert summary.severity_counts == {"error": 1, "warn": 1, "info": 0}
    assert summary.actionable_finding_count == 2
    assert summary.overall_status == CheckStatus.FAIL
    assert summary.display_variant == "danger"
    assert summary.failed_check_ids == ["C01"]
    assert summary.review_check_ids == ["PTR_CLAUSE"]


def test_presentation_status_for_result_uses_new_check_result_contract() -> None:
    result = sample_check_results()[1]

    status = presentation_status_for_result(result)

    assert status.check_id == "PTR_CLAUSE"
    assert status.status == CheckStatus.REVIEW
    assert status.display_label == "需复核"
    assert status.display_variant == "warn"
    assert status.finding_count == 1
    assert status.severity_counts == {"error": 0, "warn": 1, "info": 0}
