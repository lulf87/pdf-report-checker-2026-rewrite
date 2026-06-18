from datetime import datetime, timezone

import pytest

from app.domain.codex_review import (
    CodexEvidenceRef,
    CodexReviewConfidence,
    CodexReviewError,
    CodexReviewRequest,
    CodexReviewResult,
    CodexReviewStatus,
    CodexReviewTarget,
    CodexReviewTargetType,
    CodexReviewVerdict,
    CodexSuggestedFinding,
)
from app.domain.evidence_package import (
    EvidenceItem,
    EvidencePackage,
    EvidencePackageKind,
    EvidenceSourceType,
    EvidenceTarget,
)
from app.infrastructure.codex.fake_codex_runner import FakeCodexRunner
from app.infrastructure.codex.runner import CodexRunnerConfigurationError


CREATED_AT = datetime(2026, 6, 17, 9, 0, tzinfo=timezone.utc)


def _target(target_id: str = "target-1") -> CodexReviewTarget:
    return CodexReviewTarget(
        target_id=target_id,
        target_type=CodexReviewTargetType.REPORT_RULE,
        check_id="C02",
        finding_id=f"finding-{target_id}",
        finding_code="C02_FIELD_MISMATCH",
        title=f"Review {target_id}",
        evidence_refs=[CodexEvidenceRef(ref_id="ev-1", source_type="pdf_text")],
    )


def _request(targets: list[CodexReviewTarget] | None = None) -> CodexReviewRequest:
    return CodexReviewRequest(
        request_id="request-1",
        task_id="task-1",
        task_type="report_check",
        targets=targets or [_target()],
        prompt_version="test-prompt-v1",
        schema_version="codex-review-result-v1",
        created_at=CREATED_AT,
    )


def _package() -> EvidencePackage:
    return EvidencePackage(
        package_id="pkg-1",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        targets=[
            EvidenceTarget(
                target_id="target-1",
                target_type="report_rule",
                check_id="C02",
                evidence_refs=["ev-1"],
            )
        ],
        items=[
            EvidenceItem(
                ref_id="ev-1",
                source_type=EvidenceSourceType.PDF_TEXT,
                text="第三页型号规格: ABC-2",
            )
        ],
    )


def _result(
    *,
    target: CodexReviewTarget | None = None,
    status: CodexReviewStatus = CodexReviewStatus.SUCCEEDED,
    verdict: CodexReviewVerdict | None = CodexReviewVerdict.CONFIRM,
    confidence: CodexReviewConfidence | None = CodexReviewConfidence.MEDIUM,
    suggested_finding: CodexSuggestedFinding | None = None,
    error: CodexReviewError | None = None,
) -> CodexReviewResult:
    return CodexReviewResult(
        review_id="review-1",
        request_id="request-1",
        task_id="task-1",
        target=target or _target(),
        status=status,
        verdict=verdict,
        confidence=confidence,
        reasoning_summary="Fake review result",
        suggested_finding=suggested_finding,
        error=error,
        created_at=CREATED_AT,
        completed_at=CREATED_AT,
    )


def test_fake_runner_defaults_to_confirm_for_each_target(tmp_path) -> None:
    request = _request([_target("target-1"), _target("target-2")])
    runner = FakeCodexRunner()

    results = runner.run_review(request, _package(), tmp_path)

    assert [result.target.target_id for result in results] == ["target-1", "target-2"]
    assert {result.status for result in results} == {CodexReviewStatus.SUCCEEDED}
    assert {result.verdict for result in results} == {CodexReviewVerdict.CONFIRM}
    assert {result.confidence for result in results} == {CodexReviewConfidence.MEDIUM}


def test_fake_runner_returns_injected_refute_result(tmp_path) -> None:
    injected = _result(verdict=CodexReviewVerdict.REFUTE, confidence=CodexReviewConfidence.LOW)
    runner = FakeCodexRunner(results=[injected])

    results = runner.run_review(_request(), _package(), tmp_path)

    assert results == [injected]
    assert results[0].verdict is CodexReviewVerdict.REFUTE


def test_fake_runner_returns_injected_uncertain_result(tmp_path) -> None:
    injected = _result(verdict=CodexReviewVerdict.UNCERTAIN, confidence=CodexReviewConfidence.LOW)
    runner = FakeCodexRunner(results=[injected])

    results = runner.run_review(_request(), _package(), tmp_path)

    assert results[0].verdict is CodexReviewVerdict.UNCERTAIN
    assert results[0].confidence is CodexReviewConfidence.LOW


def test_fake_runner_returns_injected_add_finding_result(tmp_path) -> None:
    suggested = CodexSuggestedFinding(
        check_id="C02",
        severity="warn",
        code="C02_LABEL_AMBIGUOUS",
        message="Codex 建议新增标签字段歧义 finding。",
        evidence_refs=["ev-1"],
    )
    injected = _result(verdict=CodexReviewVerdict.ADD_FINDING, suggested_finding=suggested)
    runner = FakeCodexRunner(results=[injected])

    results = runner.run_review(_request(), _package(), tmp_path)

    assert results[0].verdict is CodexReviewVerdict.ADD_FINDING
    assert results[0].suggested_finding == suggested


def test_fake_runner_can_generate_target_specific_verdicts(tmp_path) -> None:
    request = _request([_target("target-1"), _target("target-2")])
    runner = FakeCodexRunner(
        verdicts_by_target={
            "target-1": CodexReviewVerdict.REFUTE,
            "target-2": CodexReviewVerdict.UNCERTAIN,
        }
    )

    results = runner.run_review(request, _package(), tmp_path)

    assert [result.verdict for result in results] == [
        CodexReviewVerdict.REFUTE,
        CodexReviewVerdict.UNCERTAIN,
    ]


def test_fake_runner_can_generate_add_finding_with_suggested_finding(tmp_path) -> None:
    suggested = CodexSuggestedFinding(
        check_id="C02",
        severity="warn",
        code="C02_LABEL_AMBIGUOUS",
        message="Codex 建议新增标签字段歧义 finding。",
        evidence_refs=["ev-1"],
    )
    runner = FakeCodexRunner(
        verdicts_by_target={"target-1": CodexReviewVerdict.ADD_FINDING},
        suggested_findings_by_target={"target-1": suggested},
    )

    results = runner.run_review(_request(), _package(), tmp_path)

    assert results[0].verdict is CodexReviewVerdict.ADD_FINDING
    assert results[0].suggested_finding == suggested


def test_fake_runner_can_simulate_failed_results(tmp_path) -> None:
    runner = FakeCodexRunner(fail=True)

    results = runner.run_review(_request(), _package(), tmp_path)

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "FAKE_CODEX_FAILURE"


def test_fake_runner_rejects_injected_results_that_do_not_match_request_targets(tmp_path) -> None:
    mismatched = _result(target=_target("other-target"))
    runner = FakeCodexRunner(results=[mismatched])

    with pytest.raises(CodexRunnerConfigurationError, match="target"):
        runner.run_review(_request(), _package(), tmp_path)
