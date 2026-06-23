from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError as PydanticValidationError

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
from app.infrastructure.codex.schemas import load_codex_review_output_schema


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class _OutputContractError(ValueError):
    def __init__(self, code: str, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


class CodexReviewOutputParser:
    """Parse Codex CLI JSON output into audited CodexReviewResult objects."""

    def __init__(self, schema: dict[str, Any] | None = None) -> None:
        self.schema = schema or load_codex_review_output_schema()
        self.validator = Draft202012Validator(self.schema)

    def parse_output(
        self,
        output_text: str,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
        *,
        raw_output_path: str | None = None,
    ) -> list[CodexReviewResult]:
        if not output_text or not output_text.strip():
            return self.build_failed_results_for_request(
                request,
                code="CODEX_OUTPUT_EMPTY",
                message="Codex CLI output was empty.",
                raw_output_path=raw_output_path,
            )

        try:
            data = json.loads(output_text)
        except json.JSONDecodeError as exc:
            return self.build_failed_results_for_request(
                request,
                code="CODEX_OUTPUT_INVALID_JSON",
                message="Codex CLI output was not valid JSON.",
                detail=str(exc),
                raw_output_path=raw_output_path,
            )

        if not isinstance(data, dict):
            return self.build_failed_results_for_request(
                request,
                code="CODEX_OUTPUT_SCHEMA_INVALID",
                message="Codex CLI output JSON must be an object.",
                detail=f"top-level type={type(data).__name__}",
                raw_output_path=raw_output_path,
            )

        schema_errors = sorted(self.validator.iter_errors(data), key=lambda error: list(error.path))
        if schema_errors:
            code, message = self._schema_failure_code_and_message(data, schema_errors[0])
            return self.build_failed_results_for_request(
                request,
                code=code,
                message=message,
                detail=schema_errors[0].message,
                raw_output_path=raw_output_path,
            )

        try:
            self._validate_output_contract(data, request, evidence_package)
            return self._build_success_results(data, request, raw_output_path=raw_output_path)
        except _OutputContractError as exc:
            return self.build_failed_results_for_request(
                request,
                code=exc.code,
                message=exc.message,
                detail=exc.detail,
                raw_output_path=raw_output_path,
            )
        except PydanticValidationError as exc:
            return self.build_failed_results_for_request(
                request,
                code="CODEX_OUTPUT_SCHEMA_INVALID",
                message="Codex CLI output could not be converted to Codex review domain models.",
                detail=str(exc),
                raw_output_path=raw_output_path,
            )

    def parse_output_file(
        self,
        output_path: Path,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
        *,
        raw_output_path: str | None = None,
    ) -> list[CodexReviewResult]:
        output_ref = raw_output_path or str(output_path)
        if not output_path.exists():
            return self.build_failed_results_for_request(
                request,
                code="CODEX_OUTPUT_FILE_NOT_FOUND",
                message="Codex CLI output file does not exist.",
                detail=str(output_path),
                raw_output_path=output_ref,
            )

        try:
            output_text = output_path.read_text(encoding="utf-8")
        except OSError as exc:
            return self.build_failed_results_for_request(
                request,
                code="CODEX_OUTPUT_FILE_READ_ERROR",
                message="Codex CLI output file could not be read.",
                detail=str(exc),
                raw_output_path=output_ref,
            )

        return self.parse_output(
            output_text,
            request,
            evidence_package,
            raw_output_path=output_ref,
        )

    def build_failed_results_for_request(
        self,
        request: CodexReviewRequest,
        *,
        code: str,
        message: str,
        detail: str | None = None,
        retryable: bool = False,
        raw_output_path: str | None = None,
    ) -> list[CodexReviewResult]:
        now = _utc_now()
        error = CodexReviewError(
            code=code,
            message=message,
            detail=detail,
            retryable=retryable,
        )
        return [
            CodexReviewResult(
                review_id=f"codex-review-{request.request_id}-{target.target_id}-failed",
                request_id=request.request_id,
                task_id=request.task_id,
                target=target,
                status=CodexReviewStatus.FAILED,
                raw_output_path=raw_output_path,
                error=error,
                created_at=now,
                completed_at=now,
                metadata={"parser": "codex_review_output"},
            )
            for target in request.targets
        ]

    def _schema_failure_code_and_message(
        self,
        data: dict[str, Any],
        error: JsonSchemaValidationError,
    ) -> tuple[str, str]:
        for review in data.get("reviews", []):
            if isinstance(review, dict) and review.get("verdict") == "add_finding" and review.get("suggested_finding") is None:
                return (
                    "CODEX_OUTPUT_ADD_FINDING_MISSING_SUGGESTION",
                    "Codex add_finding output must include suggested_finding.",
                )
        return (
            "CODEX_OUTPUT_SCHEMA_INVALID",
            "Codex CLI output did not match codex_review_output schema.",
        )

    def _validate_output_contract(
        self,
        data: dict[str, Any],
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
    ) -> None:
        reviews = data["reviews"]
        target_by_id = {target.target_id: target for target in request.targets}
        expected_target_ids = set(target_by_id)
        seen_target_ids: set[str] = set()

        for review in reviews:
            target_id = review["target_id"]
            if target_id in seen_target_ids:
                raise _OutputContractError(
                    "CODEX_OUTPUT_DUPLICATE_TARGET",
                    "Codex CLI output contained duplicate target reviews.",
                    detail=f"duplicate target_id={target_id}",
                )
            seen_target_ids.add(target_id)

            if target_id not in target_by_id:
                raise _OutputContractError(
                    "CODEX_OUTPUT_UNKNOWN_TARGET",
                    "Codex CLI output referenced an unknown target.",
                    detail=f"unknown target_id={target_id}",
                )

            self._validate_review_evidence_refs(review, target_by_id[target_id], evidence_package)
            self._validate_suggested_finding_refs(review, evidence_package)

        missing_target_ids = expected_target_ids - seen_target_ids
        if missing_target_ids:
            raise _OutputContractError(
                "CODEX_OUTPUT_MISSING_TARGET",
                "Codex CLI output did not include reviews for all request targets.",
                detail=f"missing target_ids={sorted(missing_target_ids)}",
            )

    def _validate_review_evidence_refs(
        self,
        review: dict[str, Any],
        target: CodexReviewTarget,
        evidence_package: EvidencePackage,
    ) -> None:
        package_refs = {item.ref_id for item in evidence_package.items}
        allowed_refs = {evidence_ref.ref_id for evidence_ref in target.evidence_refs}
        evidence_refs = review["evidence_refs"]
        if len(evidence_refs) != len(set(evidence_refs)):
            raise _OutputContractError(
                "CODEX_OUTPUT_DUPLICATE_EVIDENCE_REF",
                "Codex CLI output contained duplicate evidence refs.",
                detail=f"target_id={target.target_id}",
            )
        for ref_id in evidence_refs:
            if ref_id not in package_refs:
                raise _OutputContractError(
                    "CODEX_OUTPUT_UNKNOWN_EVIDENCE_REF",
                    "Codex CLI output referenced an unknown evidence ref.",
                    detail=f"unknown evidence_ref={ref_id}",
                )
            if ref_id not in allowed_refs:
                raise _OutputContractError(
                    "CODEX_OUTPUT_DISALLOWED_EVIDENCE_REF",
                    "Codex CLI output referenced evidence not allowed for the target.",
                    detail=f"target_id={target.target_id}, evidence_ref={ref_id}",
                )

    def _validate_suggested_finding_refs(
        self,
        review: dict[str, Any],
        evidence_package: EvidencePackage,
    ) -> None:
        suggested_finding = review.get("suggested_finding")
        if suggested_finding is None:
            if review["verdict"] == CodexReviewVerdict.ADD_FINDING.value:
                raise _OutputContractError(
                    "CODEX_OUTPUT_ADD_FINDING_MISSING_SUGGESTION",
                    "Codex add_finding output must include suggested_finding.",
                    detail=f"target_id={review['target_id']}",
                )
            return

        package_refs = {item.ref_id for item in evidence_package.items}
        suggested_refs = suggested_finding.get("evidence_refs", [])
        if len(suggested_refs) != len(set(suggested_refs)):
            raise _OutputContractError(
                "CODEX_OUTPUT_DUPLICATE_EVIDENCE_REF",
                "Codex suggested finding contained duplicate evidence refs.",
                detail=f"target_id={review['target_id']}",
            )
        for ref_id in suggested_refs:
            if ref_id not in package_refs:
                raise _OutputContractError(
                    "CODEX_OUTPUT_UNKNOWN_EVIDENCE_REF",
                    "Codex suggested finding referenced an unknown evidence ref.",
                    detail=f"unknown suggested_finding evidence_ref={ref_id}",
                )

    def _build_success_results(
        self,
        data: dict[str, Any],
        request: CodexReviewRequest,
        *,
        raw_output_path: str | None,
    ) -> list[CodexReviewResult]:
        now = _utc_now()
        target_by_id = {target.target_id: target for target in request.targets}
        results: list[CodexReviewResult] = []
        for review in data["reviews"]:
            suggested_finding = None
            if review.get("suggested_finding") is not None:
                suggested_finding = CodexSuggestedFinding.model_validate(review["suggested_finding"])

            metadata = dict(review.get("metadata") or {})
            metadata["schema_version"] = data["schema_version"]
            metadata["parser"] = "codex_review_output"

            target_id = review["target_id"]
            results.append(
                CodexReviewResult(
                    review_id=f"codex-review-{request.request_id}-{target_id}",
                    request_id=request.request_id,
                    task_id=request.task_id,
                    target=target_by_id[target_id],
                    status=CodexReviewStatus.SUCCEEDED,
                    verdict=CodexReviewVerdict(review["verdict"]),
                    confidence=CodexReviewConfidence(review["confidence"]),
                    reasoning_summary=review["reasoning_summary"],
                    suggested_severity=review.get("suggested_severity"),
                    suggested_finding=suggested_finding,
                    evidence_refs=list(review["evidence_refs"]),
                    raw_output_path=raw_output_path,
                    created_at=now,
                    completed_at=now,
                    metadata=metadata,
                )
            )
        return results


__all__ = ["CodexReviewOutputParser"]
