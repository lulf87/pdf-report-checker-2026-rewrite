from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from app.domain.codex_review import (
    CodexReviewError,
    CodexReviewRequest,
    CodexReviewResult,
    CodexReviewStatus,
)
from app.domain.evidence_package import EvidencePackage
from app.infrastructure.audit.evidence_package_writer import EvidencePackageWriter
from app.infrastructure.codex.prompt_builder import PromptBuilder
from app.infrastructure.codex.runner import CodexRunner, CodexRunnerError, CodexRunnerTimeout
from app.infrastructure.codex.schemas import (
    CODEX_REVIEW_OUTPUT_SCHEMA_FILENAME,
    get_codex_review_output_schema_path,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CodexAuditService:
    """Application service that orchestrates a controlled Codex audit run."""

    def __init__(
        self,
        *,
        evidence_writer: EvidencePackageWriter,
        prompt_builder: PromptBuilder,
        runner: CodexRunner,
        output_schema_path: Path | None = None,
    ) -> None:
        self.evidence_writer = evidence_writer
        self.prompt_builder = prompt_builder
        self.runner = runner
        self.output_schema_path = output_schema_path

    def review(
        self,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
    ) -> list[CodexReviewResult]:
        mismatch_error = self._request_package_mismatch_error(request, evidence_package)
        if mismatch_error is not None:
            return self._failed_results(request, mismatch_error)

        try:
            manifest = self.evidence_writer.write_package(evidence_package)
        except Exception as exc:
            return self._failed_results(
                request,
                CodexReviewError(
                    code="CODEX_AUDIT_PACKAGE_WRITE_FAILED",
                    message="Codex audit evidence package could not be written.",
                    detail=str(exc),
                    retryable=False,
                ),
            )

        workspace_dir = Path(manifest.root_dir).resolve()

        try:
            prompt = self.prompt_builder.build_review_prompt(request, evidence_package)
            prompt_path = self._write_prompt(workspace_dir, prompt)
        except Exception as exc:
            return self._failed_results(
                request,
                CodexReviewError(
                    code="CODEX_AUDIT_PROMPT_BUILD_FAILED",
                    message="Codex audit prompt could not be prepared.",
                    detail=str(exc),
                    retryable=False,
                ),
            )

        try:
            output_schema_path = self._write_output_schema(workspace_dir)
        except Exception as exc:
            return self._failed_results(
                request,
                CodexReviewError(
                    code="CODEX_AUDIT_SCHEMA_PREPARE_FAILED",
                    message="Codex audit output schema could not be prepared.",
                    detail=str(exc),
                    retryable=False,
                ),
            )

        try:
            results = self.runner.run_review(
                request,
                evidence_package,
                workspace_dir,
                output_schema_path=output_schema_path,
                prompt_path=prompt_path,
            )
        except CodexRunnerTimeout as exc:
            return self._failed_results(
                request,
                CodexReviewError(
                    code="CODEX_AUDIT_RUNNER_FAILED",
                    message="Codex audit runner timed out.",
                    detail=str(exc),
                    retryable=True,
                ),
            )
        except CodexRunnerError as exc:
            return self._failed_results(
                request,
                CodexReviewError(
                    code="CODEX_AUDIT_RUNNER_FAILED",
                    message="Codex audit runner failed.",
                    detail=str(exc),
                    retryable=False,
                ),
            )
        except Exception as exc:
            return self._failed_results(
                request,
                CodexReviewError(
                    code="CODEX_AUDIT_RUNNER_FAILED",
                    message="Codex audit runner raised an unexpected error.",
                    detail=str(exc),
                    retryable=False,
                ),
            )

        validation_error = self._validate_runner_results(request, results)
        if validation_error is not None:
            return self._failed_results(request, validation_error)

        return results

    def _request_package_mismatch_error(
        self,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
    ) -> CodexReviewError | None:
        if request.task_id != evidence_package.task_id:
            return CodexReviewError(
                code="CODEX_AUDIT_REQUEST_PACKAGE_MISMATCH",
                message="Codex review request task_id must match evidence package task_id.",
                detail=f"request.task_id={request.task_id}, evidence_package.task_id={evidence_package.task_id}",
                retryable=False,
            )
        if request.task_type != evidence_package.task_type:
            return CodexReviewError(
                code="CODEX_AUDIT_REQUEST_PACKAGE_MISMATCH",
                message="Codex review request task_type must match evidence package task_type.",
                detail=f"request.task_type={request.task_type}, evidence_package.task_type={evidence_package.task_type}",
                retryable=False,
            )
        return None

    def _write_prompt(self, workspace_dir: Path, prompt: str) -> Path:
        prompt_path = (workspace_dir / "prompt.md").resolve()
        if not prompt_path.is_relative_to(workspace_dir):
            raise ValueError("prompt path must stay inside the Codex audit workspace")
        prompt_path.write_text(prompt, encoding="utf-8")
        return prompt_path

    def _write_output_schema(self, workspace_dir: Path) -> Path:
        source_schema_path = self.output_schema_path or get_codex_review_output_schema_path()
        schema_data = json.loads(Path(source_schema_path).read_text(encoding="utf-8"))
        schema_path = (workspace_dir / CODEX_REVIEW_OUTPUT_SCHEMA_FILENAME).resolve()
        if not schema_path.is_relative_to(workspace_dir):
            raise ValueError("output schema path must stay inside the Codex audit workspace")
        schema_path.write_text(
            json.dumps(schema_data, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return schema_path

    def _validate_runner_results(
        self,
        request: CodexReviewRequest,
        results: list[CodexReviewResult],
    ) -> CodexReviewError | None:
        if not results:
            return CodexReviewError(
                code="CODEX_AUDIT_RUNNER_EMPTY_RESULT",
                message="Codex audit runner returned no review results.",
                retryable=False,
            )

        expected_target_ids = [target.target_id for target in request.targets]
        actual_target_ids = [result.target.target_id for result in results]
        if sorted(actual_target_ids) != sorted(expected_target_ids) or len(actual_target_ids) != len(set(actual_target_ids)):
            return CodexReviewError(
                code="CODEX_AUDIT_RESULT_TARGET_MISMATCH",
                message="Codex audit runner results did not cover request targets exactly once.",
                detail=f"expected={sorted(expected_target_ids)}, actual={sorted(actual_target_ids)}",
                retryable=False,
            )

        for result in results:
            if result.request_id != request.request_id or result.task_id != request.task_id:
                return CodexReviewError(
                    code="CODEX_AUDIT_RESULT_TARGET_MISMATCH",
                    message="Codex audit runner results did not match request identifiers.",
                    detail=(
                        f"result.review_id={result.review_id}, result.request_id={result.request_id}, "
                        f"result.task_id={result.task_id}"
                    ),
                    retryable=False,
                )

        return None

    def _failed_results(
        self,
        request: CodexReviewRequest,
        error: CodexReviewError,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> list[CodexReviewResult]:
        now = _utc_now()
        return [
            CodexReviewResult(
                review_id=f"codex-audit-{request.request_id}-{target.target_id}-failed",
                request_id=request.request_id,
                task_id=request.task_id,
                target=target,
                status=CodexReviewStatus.FAILED,
                error=error,
                created_at=now,
                completed_at=now,
                metadata={"service": "codex_audit", **(metadata or {})},
            )
            for target in request.targets
        ]


__all__ = ["CodexAuditService"]
