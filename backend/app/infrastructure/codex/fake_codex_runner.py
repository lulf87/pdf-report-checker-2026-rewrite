from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.domain.codex_review import (
    CodexReviewConfidence,
    CodexReviewError,
    CodexReviewRequest,
    CodexReviewResult,
    CodexReviewStatus,
    CodexReviewTarget,
    CodexReviewVerdict,
    CodexSuggestedFinding,
)
from app.domain.evidence_package import EvidencePackage
from app.infrastructure.codex.runner import (
    CodexRunnerConfigurationError,
    CodexRunnerTimeout,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FakeCodexRunner:
    """Deterministic Codex runner for unit and usecase tests."""

    def __init__(
        self,
        *,
        results: list[CodexReviewResult] | None = None,
        verdicts_by_target: dict[str, CodexReviewVerdict] | None = None,
        suggested_findings_by_target: dict[str, CodexSuggestedFinding] | None = None,
        fail: bool = False,
        raise_timeout: bool = False,
        raise_error: Exception | None = None,
    ) -> None:
        self.results = results
        self.verdicts_by_target = verdicts_by_target or {}
        self.suggested_findings_by_target = suggested_findings_by_target or {}
        self.fail = fail
        self.raise_timeout = raise_timeout
        self.raise_error = raise_error
        self.last_image_paths: list[Path] = []

    def run_review(
        self,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
        workspace_dir: Path,
        *,
        output_schema_path: Path | None = None,
        prompt_path: Path | None = None,
        image_paths: list[Path] | None = None,
    ) -> list[CodexReviewResult]:
        del evidence_package, workspace_dir, output_schema_path, prompt_path
        self.last_image_paths = list(image_paths or [])

        if self.raise_timeout:
            raise CodexRunnerTimeout("fake Codex runner timeout")
        if self.raise_error is not None:
            raise self.raise_error

        if self.results is not None:
            self._validate_result_targets(request, self.results)
            return list(self.results)

        if self.fail:
            return [self._failed_result(request, target) for target in request.targets]

        return [self._success_result(request, target) for target in request.targets]

    def _success_result(self, request: CodexReviewRequest, target: CodexReviewTarget) -> CodexReviewResult:
        verdict = self.verdicts_by_target.get(target.target_id, CodexReviewVerdict.CONFIRM)
        suggested_finding = self.suggested_findings_by_target.get(target.target_id)
        if verdict == CodexReviewVerdict.ADD_FINDING and suggested_finding is None:
            raise CodexRunnerConfigurationError(
                f"target {target.target_id} add_finding verdict requires a suggested finding"
            )

        return CodexReviewResult(
            review_id=f"{request.request_id}:{target.target_id}:fake",
            request_id=request.request_id,
            task_id=request.task_id,
            target=target,
            status=CodexReviewStatus.SUCCEEDED,
            verdict=verdict,
            confidence=CodexReviewConfidence.MEDIUM,
            reasoning_summary="Fake Codex runner generated a deterministic test review.",
            suggested_finding=suggested_finding,
            evidence_refs=[ref.ref_id for ref in target.evidence_refs],
            created_at=_utc_now(),
            completed_at=_utc_now(),
            metadata={"runner": "fake_codex"},
        )

    def _failed_result(self, request: CodexReviewRequest, target: CodexReviewTarget) -> CodexReviewResult:
        return CodexReviewResult(
            review_id=f"{request.request_id}:{target.target_id}:fake-failed",
            request_id=request.request_id,
            task_id=request.task_id,
            target=target,
            status=CodexReviewStatus.FAILED,
            error=CodexReviewError(
                code="FAKE_CODEX_FAILURE",
                message="Fake Codex runner simulated a failed review.",
                retryable=False,
            ),
            created_at=_utc_now(),
            completed_at=_utc_now(),
            metadata={"runner": "fake_codex"},
        )

    def _validate_result_targets(
        self,
        request: CodexReviewRequest,
        results: list[CodexReviewResult],
    ) -> None:
        expected_target_ids = {target.target_id for target in request.targets}
        actual_target_ids = {result.target.target_id for result in results}
        if expected_target_ids != actual_target_ids:
            raise CodexRunnerConfigurationError(
                f"injected Codex review results target mismatch: expected {sorted(expected_target_ids)}, "
                f"got {sorted(actual_target_ids)}"
            )

        for result in results:
            if result.request_id != request.request_id or result.task_id != request.task_id:
                raise CodexRunnerConfigurationError(
                    "injected Codex review results must match request_id and task_id"
                )


__all__ = ["FakeCodexRunner"]
