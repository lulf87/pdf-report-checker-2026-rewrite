from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.domain.codex_review import CodexReviewRequest, CodexReviewResult
from app.domain.evidence_package import EvidencePackage


class CodexRunnerError(Exception):
    """Base exception for Codex runner infrastructure failures."""


class CodexRunnerTimeout(CodexRunnerError):
    """Raised by fake/test runners when simulating timeout behavior."""


class CodexRunnerConfigurationError(CodexRunnerError, ValueError):
    """Raised for unsafe or inconsistent runner configuration."""


class CodexRunner(Protocol):
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
        """Run a Codex audit request against a controlled evidence workspace."""


__all__ = [
    "CodexRunner",
    "CodexRunnerConfigurationError",
    "CodexRunnerError",
    "CodexRunnerTimeout",
]
