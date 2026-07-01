from __future__ import annotations

import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Callable

from app.domain.codex_review import (
    CodexReviewError,
    CodexReviewRequest,
    CodexReviewResult,
    CodexReviewStatus,
)
from app.domain.evidence_package import EvidencePackage
from app.infrastructure.audit.codex_review_cache import CodexReviewCache
from app.infrastructure.audit.evidence_package_writer import EvidencePackageWriter
from app.infrastructure.codex.prompt_builder import PromptBuilder
from app.infrastructure.codex.runner import CodexRunner, CodexRunnerError, CodexRunnerTimeout
from app.infrastructure.codex.schemas import (
    CODEX_REVIEW_OUTPUT_SCHEMA_FILENAME,
    get_codex_review_output_schema_path,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


ProgressCallback = Callable[[dict[str, Any]], None]


class CodexAuditService:
    """Application service that orchestrates a controlled Codex audit run."""

    def __init__(
        self,
        *,
        evidence_writer: EvidencePackageWriter,
        prompt_builder: PromptBuilder,
        runner: CodexRunner,
        output_schema_path: Path | None = None,
        review_cache: CodexReviewCache | None = None,
        missing_target_retry_batch_size: int = 1,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.evidence_writer = evidence_writer
        self.prompt_builder = prompt_builder
        self.runner = runner
        self.output_schema_path = output_schema_path
        self.review_cache = review_cache
        self.missing_target_retry_batch_size = max(1, missing_target_retry_batch_size)
        self.progress_callback = progress_callback

    def review(
        self,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
    ) -> list[CodexReviewResult]:
        mismatch_error = self._request_package_mismatch_error(request, evidence_package)
        if mismatch_error is not None:
            return self._failed_results(request, mismatch_error)

        package_profile: dict[str, Any] = {
            "package_id": evidence_package.package_id,
            "check_id": request.metadata.get("check_id") or _first_check_id(request),
            "target_count": len(request.targets),
        }

        started = time.perf_counter()
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
        package_profile["evidence_write_seconds"] = _elapsed(started)

        workspace_dir = Path(manifest.root_dir).resolve()
        package_json_path = workspace_dir / manifest.package_json_path
        package_profile["evidence_package_size_bytes"] = package_json_path.stat().st_size if package_json_path.is_file() else 0
        package_profile.update(_manifest_profile(manifest.metadata))

        started = time.perf_counter()
        image_paths = self._image_paths_from_manifest(workspace_dir, manifest.item_file_paths)
        package_profile["image_path_collection_seconds"] = _elapsed(started)
        package_profile["image_count"] = len(image_paths)
        package_profile["image_bytes"] = _file_size_total(image_paths)

        started = time.perf_counter()
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
        package_profile["prompt_build_seconds"] = _elapsed(started)
        package_profile["prompt_size_bytes"] = prompt_path.stat().st_size if prompt_path.is_file() else len(prompt.encode("utf-8"))

        started = time.perf_counter()
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
        package_profile["schema_prepare_seconds"] = _elapsed(started)
        schema_text = output_schema_path.read_text(encoding="utf-8")

        cache_key: str | None = None
        if self.review_cache is not None:
            cache_key = self.review_cache.key_for(
                request=request,
                evidence_package=evidence_package,
                prompt=prompt,
                schema_text=schema_text,
                image_paths=image_paths,
            )
            cached_results = self.review_cache.read(cache_key, request)
            if cached_results is not None:
                package_profile["codex_exec_seconds"] = 0.0
                package_profile["result_validation_seconds"] = 0.0
                package_profile["cache_hit"] = True
                package_profile["cache_key"] = cache_key
                return self._with_package_profile(cached_results, package_profile, cache_key=cache_key)

        started = time.perf_counter()
        try:
            results = self.runner.run_review(
                request,
                evidence_package,
                workspace_dir,
                output_schema_path=output_schema_path,
                prompt_path=prompt_path,
                image_paths=image_paths,
            )
        except CodexRunnerTimeout as exc:
            self._emit_progress(
                {
                    "status": "failed",
                    "error_code": "CODEX_TIMEOUT",
                    "last_retry_reason": "CODEX_TIMEOUT",
                    "request_id": request.request_id,
                    "package_id": evidence_package.package_id,
                    "target_count": len(request.targets),
                }
            )
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
        package_profile["codex_exec_seconds"] = _elapsed(started)

        missing_target_ids = self._missing_target_ids_for_retry(request, results)
        if missing_target_ids and not request.metadata.get("missing_target_retry"):
            self._emit_progress(
                {
                    "status": "retrying",
                    "last_retry_reason": "CODEX_OUTPUT_MISSING_TARGET",
                    "retry_count": 1,
                    "request_id": request.request_id,
                    "package_id": evidence_package.package_id,
                    "missing_target_ids": list(missing_target_ids),
                    "target_count": len(missing_target_ids),
                    "check_id": request.metadata.get("check_id") or _first_check_id(request),
                }
            )
            retry_results = self._retry_missing_targets(
                request=request,
                evidence_package=evidence_package,
                missing_target_ids=missing_target_ids,
            )
            results = self._merge_retry_results(
                request=request,
                initial_results=results,
                retry_results=retry_results,
                missing_target_ids=missing_target_ids,
            )
            remaining_missing_target_ids = self._unrecovered_missing_target_ids(
                results,
                missing_target_ids=missing_target_ids,
            )
            if remaining_missing_target_ids:
                return self._failed_results(
                    request,
                    CodexReviewError(
                        code="CODEX_OUTPUT_MISSING_TARGET",
                        message="Codex CLI output did not include reviews for all request targets.",
                        detail=f"missing target_ids={remaining_missing_target_ids}",
                        retryable=True,
                    ),
                    metadata={"codex_package_profile": package_profile},
                )

        started = time.perf_counter()
        validation_error = self._validate_runner_results(request, results)
        package_profile["result_validation_seconds"] = _elapsed(started)
        if validation_error is not None:
            return self._failed_results(request, validation_error, metadata={"codex_package_profile": package_profile})

        results = self._with_package_profile(results, package_profile, cache_key=cache_key)
        if self.review_cache is not None and cache_key is not None:
            self.review_cache.write(cache_key, results)
        return results

    def _image_paths_from_manifest(self, workspace_dir: Path, item_file_paths: list[str]) -> list[Path]:
        image_paths: list[Path] = []
        image_suffixes = {".png", ".jpg", ".jpeg", ".webp"}
        for file_path in item_file_paths:
            relative = Path(file_path)
            if relative.suffix.lower() not in image_suffixes:
                continue
            resolved = (workspace_dir / relative).resolve()
            if not resolved.is_relative_to(workspace_dir):
                raise ValueError("image evidence path must stay inside the Codex audit workspace")
            if not resolved.is_file():
                raise FileNotFoundError(resolved)
            image_paths.append(resolved)
        return image_paths

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
        missing_target_ids = [target_id for target_id in expected_target_ids if target_id not in set(actual_target_ids)]
        if missing_target_ids:
            return CodexReviewError(
                code="CODEX_OUTPUT_MISSING_TARGET",
                message="Codex CLI output did not include reviews for all request targets.",
                detail=f"missing target_ids={missing_target_ids}",
                retryable=True,
            )
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

    def _missing_target_ids_for_retry(
        self,
        request: CodexReviewRequest,
        results: list[CodexReviewResult],
    ) -> list[str]:
        expected_order = [target.target_id for target in request.targets]
        expected = set(expected_order)
        actual = {result.target.target_id for result in results}
        missing = expected - actual

        for result in results:
            error = result.error
            if error is None or error.code != "CODEX_OUTPUT_MISSING_TARGET":
                continue
            parsed = _parse_missing_target_ids(error.detail)
            if parsed:
                missing.update(target_id for target_id in parsed if target_id in expected)
            elif result.target.target_id in expected:
                missing.add(result.target.target_id)

        return [target_id for target_id in expected_order if target_id in missing]

    def _unrecovered_missing_target_ids(
        self,
        results: list[CodexReviewResult],
        *,
        missing_target_ids: list[str],
    ) -> list[str]:
        by_target = {result.target.target_id: result for result in results}
        return [
            target_id
            for target_id in missing_target_ids
            if by_target.get(target_id) is None or by_target[target_id].status is not CodexReviewStatus.SUCCEEDED
        ]

    def _retry_missing_targets(
        self,
        *,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
        missing_target_ids: list[str],
    ) -> list[CodexReviewResult]:
        retry_results: list[CodexReviewResult] = []
        for attempt, chunk in enumerate(_chunks(missing_target_ids, self.missing_target_retry_batch_size), start=1):
            retry_request = self._retry_request(request, target_ids=chunk, attempt=attempt)
            retry_package = self._retry_package(evidence_package, target_ids=chunk, attempt=attempt)
            chunk_results = self.review(retry_request, retry_package)
            retry_results.extend(
                self._mark_retry_result(
                    result,
                    original_request_id=request.request_id,
                    attempt=attempt,
                    retry_target_ids=chunk,
                )
                for result in chunk_results
            )
        return retry_results

    def _retry_request(
        self,
        request: CodexReviewRequest,
        *,
        target_ids: list[str],
        attempt: int,
    ) -> CodexReviewRequest:
        target_id_set = set(target_ids)
        return request.model_copy(
            update={
                "request_id": f"{request.request_id}-missing-target-retry-{attempt}",
                "targets": [target for target in request.targets if target.target_id in target_id_set],
                "metadata": {
                    **request.metadata,
                    "missing_target_retry": True,
                    "retry_of_request_id": request.request_id,
                    "retry_attempt": attempt,
                    "retry_target_ids": list(target_ids),
                },
            }
        )

    def _retry_package(
        self,
        evidence_package: EvidencePackage,
        *,
        target_ids: list[str],
        attempt: int,
    ) -> EvidencePackage:
        target_id_set = set(target_ids)
        return evidence_package.model_copy(
            update={
                "package_id": f"{evidence_package.package_id}-missing-target-retry-{attempt}",
                "targets": [target for target in evidence_package.targets if target.target_id in target_id_set],
                "metadata": {
                    **evidence_package.metadata,
                    "missing_target_retry": True,
                    "retry_of_package_id": evidence_package.package_id,
                    "retry_attempt": attempt,
                    "retry_target_ids": list(target_ids),
                },
            }
        )

    def _mark_retry_result(
        self,
        result: CodexReviewResult,
        *,
        original_request_id: str,
        attempt: int,
        retry_target_ids: list[str],
    ) -> CodexReviewResult:
        metadata = dict(result.metadata)
        metadata["missing_target_retry"] = {
            "attempt": attempt,
            "retry_request_id": result.request_id,
            "retry_target_ids": list(retry_target_ids),
        }
        return result.model_copy(update={"request_id": original_request_id, "metadata": metadata})

    def _merge_retry_results(
        self,
        *,
        request: CodexReviewRequest,
        initial_results: list[CodexReviewResult],
        retry_results: list[CodexReviewResult],
        missing_target_ids: list[str],
    ) -> list[CodexReviewResult]:
        missing = set(missing_target_ids)
        original_targets = {target.target_id: target for target in request.targets}
        by_target: dict[str, CodexReviewResult] = {}
        for result in initial_results:
            target_id = result.target.target_id
            if target_id in missing and _is_missing_target_failure(result):
                continue
            by_target[target_id] = result

        for result in retry_results:
            target_id = result.target.target_id
            if target_id not in missing:
                continue
            target = original_targets.get(target_id, result.target)
            by_target[target_id] = result.model_copy(update={"target": target})

        return [by_target[target.target_id] for target in request.targets if target.target_id in by_target]

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

    def _with_package_profile(
        self,
        results: list[CodexReviewResult],
        package_profile: dict[str, Any],
        *,
        cache_key: str | None = None,
    ) -> list[CodexReviewResult]:
        output: list[CodexReviewResult] = []
        for result in results:
            profile = dict(package_profile)
            runner_exec_seconds = result.metadata.get("codex_exec_seconds")
            if isinstance(runner_exec_seconds, (int, float)):
                profile["codex_exec_seconds"] = runner_exec_seconds
            metadata = dict(result.metadata)
            if "codex_package_profile" not in metadata:
                metadata["codex_package_profile"] = profile
            if cache_key is not None:
                metadata["cache_key"] = cache_key
            output.append(result.model_copy(update={"metadata": metadata}))
        return output

    def _emit_progress(self, event: dict[str, Any]) -> None:
        if self.progress_callback is None:
            return
        self.progress_callback(dict(event))


def _elapsed(started: float) -> float:
    return round(max(0.0, time.perf_counter() - started), 6)


def _file_size_total(paths: list[Path]) -> int:
    return sum(path.stat().st_size for path in paths if path.is_file())


def _first_check_id(request: CodexReviewRequest) -> str | None:
    for target in request.targets:
        if target.check_id:
            return target.check_id
    return None


def _manifest_profile(metadata: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "image_materialization_seconds",
        "image_items_count",
        "materialized_image_count",
        "materialized_image_bytes",
        "externalized_text_count",
        "externalized_text_bytes",
    }
    return {key: metadata[key] for key in keys if key in metadata}


def _chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _is_missing_target_failure(result: CodexReviewResult) -> bool:
    return (
        result.status is CodexReviewStatus.FAILED
        and result.error is not None
        and result.error.code == "CODEX_OUTPUT_MISSING_TARGET"
    )


def _parse_missing_target_ids(detail: str | None) -> list[str]:
    if not detail:
        return []
    start = detail.find("[")
    end = detail.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        parsed = ast.literal_eval(detail[start : end + 1])
    except (SyntaxError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, str) and item]


__all__ = ["CodexAuditService"]
