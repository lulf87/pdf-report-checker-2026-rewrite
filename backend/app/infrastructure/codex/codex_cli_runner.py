from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
from typing import Any

from app.domain.codex_review import (
    CodexReviewError,
    CodexReviewRequest,
    CodexReviewResult,
    CodexReviewStatus,
)
from app.domain.evidence_package import EvidencePackage
from app.infrastructure.codex.output_parser import CodexReviewOutputParser
from app.infrastructure.codex.runner import CodexRunnerConfigurationError


OLD_PROJECT_ROOT = Path("/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_forbidden_exact_roots() -> tuple[Path, ...]:
    root = _project_root()
    return (root, _backend_root(), OLD_PROJECT_ROOT)


def _default_forbidden_parent_roots() -> tuple[Path, ...]:
    root = _project_root()
    return (
        OLD_PROJECT_ROOT,
        root / "backend" / "app",
        root / "backend" / "tests",
        root / "frontend",
        root / "docs",
        root / ".git",
    )


@dataclass(frozen=True)
class CodexCliRunnerConfig:
    executable: str = "codex"
    sandbox: str = "read-only"
    timeout_seconds: int = 300
    enabled: bool = True
    ephemeral: bool = True
    extra_args: list[str] = field(default_factory=list)
    allow_real_execution: bool = True
    forbidden_exact_roots: tuple[Path, ...] = field(default_factory=_default_forbidden_exact_roots)
    forbidden_parent_roots: tuple[Path, ...] = field(default_factory=_default_forbidden_parent_roots)

    def __post_init__(self) -> None:
        if self.sandbox != "read-only":
            raise CodexRunnerConfigurationError("Codex CLI runner only allows read-only sandbox")
        if self.timeout_seconds <= 0:
            raise CodexRunnerConfigurationError("Codex CLI timeout must be greater than zero")
        if not self.executable:
            raise CodexRunnerConfigurationError("Codex CLI executable is required")
        if any(arg in {"--sandbox", "danger-full-access", "workspace-write"} for arg in self.extra_args):
            raise CodexRunnerConfigurationError("Codex CLI extra_args must not override sandbox safety")

        object.__setattr__(
            self,
            "forbidden_exact_roots",
            tuple(Path(path).resolve() for path in self.forbidden_exact_roots),
        )
        object.__setattr__(
            self,
            "forbidden_parent_roots",
            tuple(Path(path).resolve() for path in self.forbidden_parent_roots),
        )


class CodexCliRunner:
    """Controlled wrapper for Codex CLI runtime auditor execution."""

    def __init__(
        self,
        config: CodexCliRunnerConfig | None = None,
        *,
        output_parser: CodexReviewOutputParser | None = None,
    ) -> None:
        self.config = config or CodexCliRunnerConfig()
        self.output_parser = output_parser or CodexReviewOutputParser()

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
        if not self.config.enabled:
            return self._skipped_results(request, reason="codex_cli_disabled", image_count=len(image_paths or []))
        if not self.config.allow_real_execution:
            return self._skipped_results(request, reason="real_execution_not_allowed", image_count=len(image_paths or []))

        workspace = Path(workspace_dir).resolve()
        workspace_error = self._validate_workspace(workspace)
        if workspace_error is not None:
            return self._failed_results(request, workspace_error, metadata={"image_count": len(image_paths or [])})

        schema = self._resolve_optional_workspace_file(
            output_schema_path,
            workspace,
            missing_code="CODEX_SCHEMA_MISSING",
            forbidden_code="CODEX_SCHEMA_FORBIDDEN",
        )
        if isinstance(schema, CodexReviewError):
            return self._failed_results(request, schema, metadata={"image_count": len(image_paths or [])})

        prompt = self._load_prompt(prompt_path, workspace)
        if isinstance(prompt, CodexReviewError):
            return self._failed_results(request, prompt, metadata={"image_count": len(image_paths or [])})

        resolved_image_paths = self._resolve_image_paths(image_paths or [], workspace)
        if isinstance(resolved_image_paths, CodexReviewError):
            return self._failed_results(request, resolved_image_paths, metadata={"image_count": len(image_paths or [])})

        output_path = (workspace / "codex_review_output.json").resolve()
        command = self._build_command(
            workspace=workspace,
            output_path=output_path,
            prompt=prompt,
            output_schema_path=schema,
            image_paths=resolved_image_paths,
        )

        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            return self._failed_results(
                request,
                CodexReviewError(
                    code="CODEX_CLI_UNAVAILABLE",
                    message="Codex CLI executable was not found.",
                    detail=str(exc),
                    retryable=False,
                ),
                metadata=self._runner_metadata(
                    started=started,
                    exit_code=None,
                    stdout="",
                    stderr=str(exc),
                    output_path=output_path,
                    image_count=len(resolved_image_paths),
                ),
            )
        except subprocess.TimeoutExpired as exc:
            return self._failed_results(
                request,
                CodexReviewError(
                    code="CODEX_TIMEOUT",
                    message="Codex CLI timed out.",
                    detail=f"Timed out after {exc.timeout} seconds.",
                    retryable=True,
                ),
                metadata=self._runner_metadata(
                    started=started,
                    exit_code=None,
                    stdout=exc.stdout if isinstance(exc.stdout, str) else "",
                    stderr=exc.stderr if isinstance(exc.stderr, str) else "",
                    output_path=output_path,
                    image_count=len(resolved_image_paths),
                ),
            )
        except OSError as exc:
            return self._failed_results(
                request,
                CodexReviewError(
                    code="CODEX_RUNNER_ERROR",
                    message="Codex CLI runner failed before producing output.",
                    detail=str(exc),
                    retryable=False,
                ),
                metadata=self._runner_metadata(
                    started=started,
                    exit_code=None,
                    stdout="",
                    stderr=str(exc),
                    output_path=output_path,
                    image_count=len(resolved_image_paths),
                ),
            )

        runner_metadata = self._runner_metadata(
            started=started,
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            output_path=output_path,
            image_count=len(resolved_image_paths),
        )
        if completed.returncode != 0:
            error_code = _nonzero_error_code(completed.stdout or "", completed.stderr or "")
            retry_after_text = _extract_retry_after_text(completed.stdout or "", completed.stderr or "")
            error_metadata = {
                **runner_metadata,
                "stderr_tail": _tail(completed.stderr or ""),
                "stdout_tail": _tail(completed.stdout or ""),
            }
            if retry_after_text:
                error_metadata["retry_after_text"] = retry_after_text
            self._write_runner_diagnostics(
                workspace=workspace,
                request=request,
                evidence_package=evidence_package,
                output_path=output_path,
                code=error_code,
                exit_code=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
                prompt_path=prompt_path,
                output_schema_path=schema,
                metadata=error_metadata,
            )
            return self._failed_results(
                request,
                CodexReviewError(
                    code=error_code,
                    message="Codex CLI exited with a non-zero status.",
                    detail=(
                        f"exit_code={completed.returncode}\n"
                        f"stdout_size_bytes={runner_metadata['stdout_size_bytes']}\n"
                        f"stderr_size_bytes={runner_metadata['stderr_size_bytes']}\n"
                        f"stdout_tail={_tail(completed.stdout or '')}\n"
                        f"stderr_tail={_tail(completed.stderr or '')}"
                    ),
                    retryable=True,
                ),
                raw_output_path=output_path.name,
                metadata=error_metadata,
            )

        return self._with_runner_metadata(
            self.output_parser.parse_output_file(
                output_path,
                request,
                evidence_package,
                raw_output_path=output_path.name,
            ),
            runner_metadata,
        )

    def _runner_metadata(
        self,
        *,
        started: float,
        exit_code: int | None,
        stdout: str,
        stderr: str,
        output_path: Path,
        image_count: int,
    ) -> dict[str, Any]:
        return {
            "codex_exec_seconds": round(max(0.0, time.perf_counter() - started), 6),
            "exit_code": exit_code,
            "stdout_size_bytes": len(stdout.encode("utf-8")),
            "stderr_size_bytes": len(stderr.encode("utf-8")),
            "output_size_bytes": output_path.stat().st_size if output_path.is_file() else 0,
            "image_count": image_count,
        }

    def _with_runner_metadata(
        self,
        results: list[CodexReviewResult],
        metadata: dict[str, Any],
    ) -> list[CodexReviewResult]:
        return [
            result.model_copy(update={"metadata": {**result.metadata, **metadata}})
            for result in results
        ]

    def _write_runner_diagnostics(
        self,
        *,
        workspace: Path,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
        output_path: Path,
        code: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        prompt_path: Path | None,
        output_schema_path: Path | None,
        metadata: dict[str, Any],
    ) -> None:
        try:
            (workspace / "codex_stdout.txt").write_text(stdout, encoding="utf-8")
            (workspace / "codex_stderr.txt").write_text(stderr, encoding="utf-8")
            package_json_path = workspace / "evidence_package.json"
            prompt_file = prompt_path.resolve() if prompt_path is not None else workspace / "prompt.md"
            diagnostics = {
                "code": code,
                "exit_code": exit_code,
                "retry_after_text": metadata.get("retry_after_text"),
                "workspace_dir": str(workspace),
                "prompt_path": str(prompt_file),
                "prompt_size_bytes": prompt_file.stat().st_size if prompt_file.is_file() else None,
                "evidence_package_path": str(package_json_path),
                "evidence_package_size_bytes": package_json_path.stat().st_size if package_json_path.is_file() else None,
                "output_path": str(output_path),
                "output_exists": output_path.is_file(),
                "output_schema_path": str(output_schema_path) if output_schema_path is not None else None,
                "stdout_size_bytes": metadata.get("stdout_size_bytes"),
                "stderr_size_bytes": metadata.get("stderr_size_bytes"),
                "output_size_bytes": metadata.get("output_size_bytes"),
                "stderr_tail": metadata.get("stderr_tail"),
                "stdout_tail": metadata.get("stdout_tail"),
                "target_ids": [target.target_id for target in request.targets],
                "package_id": evidence_package.package_id,
                "task_id": request.task_id,
            }
            (workspace / "codex_runner_error.json").write_text(
                json.dumps(diagnostics, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            return

    def _build_command(
        self,
        *,
        workspace: Path,
        output_path: Path,
        prompt: str,
        output_schema_path: Path | None,
        image_paths: list[Path],
    ) -> list[str]:
        command = [
            self.config.executable,
            "exec",
            "--cd",
            str(workspace),
            "--sandbox",
            self.config.sandbox,
        ]
        if self.config.ephemeral:
            command.append("--ephemeral")
        if output_schema_path is not None:
            command.extend(["--output-schema", str(output_schema_path)])
        for image_path in image_paths:
            command.extend(["--image", image_path.relative_to(workspace).as_posix()])
        command.extend(["-o", str(output_path)])
        command.extend(self.config.extra_args)
        command.append(prompt)
        return command

    def _validate_workspace(self, workspace: Path) -> CodexReviewError | None:
        if not workspace.exists() or not workspace.is_dir():
            return CodexReviewError(
                code="CODEX_WORKSPACE_MISSING",
                message="Codex CLI workspace directory does not exist.",
                detail=str(workspace),
                retryable=False,
            )

        for forbidden in self.config.forbidden_exact_roots:
            if workspace == forbidden:
                return self._forbidden_workspace_error(workspace)

        for forbidden in self.config.forbidden_parent_roots:
            if workspace == forbidden or workspace.is_relative_to(forbidden):
                return self._forbidden_workspace_error(workspace)

        return None

    def _forbidden_workspace_error(self, workspace: Path) -> CodexReviewError:
        return CodexReviewError(
            code="CODEX_WORKSPACE_FORBIDDEN",
            message="Codex CLI workspace must be a controlled evidence package directory.",
            detail=str(workspace),
            retryable=False,
        )

    def _resolve_optional_workspace_file(
        self,
        path: Path | None,
        workspace: Path,
        *,
        missing_code: str,
        forbidden_code: str,
    ) -> Path | CodexReviewError | None:
        if path is None:
            return None
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(workspace):
            return CodexReviewError(
                code=forbidden_code,
                message="Codex CLI support file must stay inside the evidence workspace.",
                detail=str(resolved),
                retryable=False,
            )
        if not resolved.is_file():
            return CodexReviewError(
                code=missing_code,
                message="Codex CLI support file does not exist.",
                detail=str(resolved),
                retryable=False,
            )
        return resolved

    def _load_prompt(self, prompt_path: Path | None, workspace: Path) -> str | CodexReviewError:
        if prompt_path is None:
            return "Review evidence_package.json in this workspace and output CodexReviewResult JSON."

        resolved = self._resolve_optional_workspace_file(
            prompt_path,
            workspace,
            missing_code="CODEX_PROMPT_MISSING",
            forbidden_code="CODEX_PROMPT_FORBIDDEN",
        )
        if isinstance(resolved, CodexReviewError):
            return resolved
        assert resolved is not None
        return resolved.read_text(encoding="utf-8")

    def _resolve_image_paths(self, image_paths: list[Path], workspace: Path) -> list[Path] | CodexReviewError:
        resolved_paths: list[Path] = []
        for image_path in image_paths:
            resolved = Path(image_path).resolve()
            if not resolved.is_relative_to(workspace):
                return CodexReviewError(
                    code="CODEX_IMAGE_INPUT_FORBIDDEN",
                    message="Codex CLI image input must stay inside the evidence workspace.",
                    detail=str(resolved),
                    retryable=False,
                )
            if not resolved.is_file():
                return CodexReviewError(
                    code="CODEX_IMAGE_INPUT_MISSING",
                    message="Codex CLI image input file does not exist.",
                    detail=str(resolved),
                    retryable=False,
                )
            if resolved.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                return CodexReviewError(
                    code="CODEX_IMAGE_INPUT_UNSUPPORTED",
                    message="Codex CLI image input must be a supported image file.",
                    detail=str(resolved),
                    retryable=False,
                )
            resolved_paths.append(resolved)
        return resolved_paths

    def _skipped_results(self, request: CodexReviewRequest, *, reason: str, image_count: int = 0) -> list[CodexReviewResult]:
        return [
            CodexReviewResult(
                review_id=f"{request.request_id}:{target.target_id}:codex-cli-skipped",
                request_id=request.request_id,
                task_id=request.task_id,
                target=target,
                status=CodexReviewStatus.SKIPPED,
                reasoning_summary="Codex CLI runner skipped execution.",
                created_at=_utc_now(),
                completed_at=_utc_now(),
                metadata={"runner": "codex_cli", "reason": reason, "image_count": image_count},
            )
            for target in request.targets
        ]

    def _failed_results(
        self,
        request: CodexReviewRequest,
        error: CodexReviewError,
        *,
        raw_output_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[CodexReviewResult]:
        return [
            CodexReviewResult(
                review_id=f"{request.request_id}:{target.target_id}:codex-cli-failed",
                request_id=request.request_id,
                task_id=request.task_id,
                target=target,
                status=CodexReviewStatus.FAILED,
                raw_output_path=raw_output_path,
                error=error,
                created_at=_utc_now(),
                completed_at=_utc_now(),
                metadata={"runner": "codex_cli", **(metadata or {})},
            )
            for target in request.targets
        ]


def _tail(text: str, limit: int = 1200) -> str:
    return text[-limit:]


def _nonzero_error_code(stdout: str, stderr: str) -> str:
    text = f"{stdout}\n{stderr}".lower()
    if "you've hit your usage limit" in text or ("usage limit" in text and "try again at" in text):
        return "CODEX_USAGE_LIMIT_EXCEEDED"
    return "CODEX_EXIT_NONZERO"


def _extract_retry_after_text(stdout: str, stderr: str) -> str | None:
    text = f"{stdout}\n{stderr}"
    marker = "try again at"
    lowered = text.lower()
    index = lowered.find(marker)
    if index < 0:
        return None
    start = index + len(marker)
    tail = text[start:].strip()
    for separator in ("\n", "."):
        if separator in tail:
            tail = tail.split(separator, 1)[0]
    return tail.strip() or None


__all__ = ["CodexCliRunner", "CodexCliRunnerConfig"]
