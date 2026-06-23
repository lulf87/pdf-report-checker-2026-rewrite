from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import subprocess

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
    ) -> list[CodexReviewResult]:
        if not self.config.enabled:
            return self._skipped_results(request, reason="codex_cli_disabled")
        if not self.config.allow_real_execution:
            return self._skipped_results(request, reason="real_execution_not_allowed")

        workspace = Path(workspace_dir).resolve()
        workspace_error = self._validate_workspace(workspace)
        if workspace_error is not None:
            return self._failed_results(request, workspace_error)

        schema = self._resolve_optional_workspace_file(
            output_schema_path,
            workspace,
            missing_code="CODEX_SCHEMA_MISSING",
            forbidden_code="CODEX_SCHEMA_FORBIDDEN",
        )
        if isinstance(schema, CodexReviewError):
            return self._failed_results(request, schema)

        prompt = self._load_prompt(prompt_path, workspace)
        if isinstance(prompt, CodexReviewError):
            return self._failed_results(request, prompt)

        output_path = (workspace / "codex_review_output.json").resolve()
        command = self._build_command(
            workspace=workspace,
            output_path=output_path,
            prompt=prompt,
            output_schema_path=schema,
        )

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
            )

        if completed.returncode != 0:
            return self._failed_results(
                request,
                CodexReviewError(
                    code="CODEX_EXIT_NONZERO",
                    message="Codex CLI exited with a non-zero status.",
                    detail=(
                        f"exit_code={completed.returncode}\n"
                        f"stdout={completed.stdout or ''}\n"
                        f"stderr={completed.stderr or ''}"
                    ),
                    retryable=True,
                ),
                raw_output_path=output_path.name,
            )

        return self.output_parser.parse_output_file(
            output_path,
            request,
            evidence_package,
            raw_output_path=output_path.name,
        )

    def _build_command(
        self,
        *,
        workspace: Path,
        output_path: Path,
        prompt: str,
        output_schema_path: Path | None,
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

    def _skipped_results(self, request: CodexReviewRequest, *, reason: str) -> list[CodexReviewResult]:
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
                metadata={"runner": "codex_cli", "reason": reason},
            )
            for target in request.targets
        ]

    def _failed_results(
        self,
        request: CodexReviewRequest,
        error: CodexReviewError,
        *,
        raw_output_path: str | None = None,
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
                metadata={"runner": "codex_cli"},
            )
            for target in request.targets
        ]


__all__ = ["CodexCliRunner", "CodexCliRunnerConfig"]
