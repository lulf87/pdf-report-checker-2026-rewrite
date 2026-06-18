from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.domain.codex_review import CodexReviewStatus, CodexReviewVerdict
from app.infrastructure.audit.evidence_package_writer import EvidencePackageWriter
from app.infrastructure.codex.codex_cli_runner import CodexCliRunner, CodexCliRunnerConfig
from app.infrastructure.codex.prompt_builder import PromptBuilder
from app.infrastructure.codex.schemas import (
    CODEX_REVIEW_OUTPUT_SCHEMA_FILENAME,
    get_codex_review_output_schema_path,
)
from tests.fixtures.codex_cli_manual_smoke import build_manual_codex_cli_smoke_fixture


pytestmark = pytest.mark.skipif(
    os.getenv("ENABLE_CODEX_CLI_INTEGRATION") != "1",
    reason="Set ENABLE_CODEX_CLI_INTEGRATION=1 to run the real Codex CLI manual smoke test.",
)


def test_real_codex_cli_manual_smoke_returns_auditable_result(tmp_path: Path) -> None:
    fixture = build_manual_codex_cli_smoke_fixture()
    writer = EvidencePackageWriter(tmp_path / "codex_audit")
    manifest = writer.write_package(fixture.evidence_package)
    workspace = Path(manifest.root_dir).resolve()

    prompt = PromptBuilder().build_review_prompt(fixture.request, fixture.evidence_package)
    prompt_path = workspace / "prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    source_schema_path = get_codex_review_output_schema_path()
    schema_data = json.loads(source_schema_path.read_text(encoding="utf-8"))
    schema_path = workspace / CODEX_REVIEW_OUTPUT_SCHEMA_FILENAME
    schema_path.write_text(json.dumps(schema_data, ensure_ascii=False, indent=2), encoding="utf-8")

    runner = CodexCliRunner(
        CodexCliRunnerConfig(
            enabled=True,
            allow_real_execution=True,
            sandbox="read-only",
            ephemeral=True,
            timeout_seconds=90,
        )
    )

    results = runner.run_review(
        fixture.request,
        fixture.evidence_package,
        workspace,
        output_schema_path=schema_path,
        prompt_path=prompt_path,
    )

    assert results
    assert workspace.is_relative_to(tmp_path)
    for result in results:
        assert result.status in {CodexReviewStatus.SUCCEEDED, CodexReviewStatus.FAILED}
        if result.status is CodexReviewStatus.SUCCEEDED:
            assert result.verdict in {
                CodexReviewVerdict.CONFIRM,
                CodexReviewVerdict.REFUTE,
                CodexReviewVerdict.UNCERTAIN,
                CodexReviewVerdict.ADD_FINDING,
            }
        else:
            assert result.error is not None
            assert result.error.code
            assert result.error.message
