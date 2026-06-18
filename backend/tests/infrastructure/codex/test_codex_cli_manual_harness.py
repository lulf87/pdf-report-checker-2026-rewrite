from __future__ import annotations

import os
from pathlib import Path
import subprocess

from app.infrastructure.audit.evidence_package_writer import EvidencePackageWriter
from app.infrastructure.codex.prompt_builder import PromptBuilder
from tests.fixtures.codex_cli_manual_smoke import build_manual_codex_cli_smoke_fixture


PROJECT_ROOT = Path(__file__).resolve().parents[4]
OLD_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"


def test_manual_smoke_fixture_builds_controlled_evidence_workspace(tmp_path: Path) -> None:
    fixture = build_manual_codex_cli_smoke_fixture()
    writer = EvidencePackageWriter(tmp_path / "codex_audit")

    manifest = writer.write_package(fixture.evidence_package)
    workspace = Path(manifest.root_dir)
    prompt = PromptBuilder().build_review_prompt(fixture.request, fixture.evidence_package)

    assert workspace.is_relative_to(tmp_path)
    assert (workspace / "evidence_package.json").is_file()
    assert (workspace / "manifest.json").is_file()
    assert fixture.request.task_id == fixture.evidence_package.task_id
    assert fixture.request.task_type == "ptr_compare"
    assert fixture.request.targets[0].target_type == "ptr_parameter"
    assert fixture.request.targets[0].finding_code == "PTR_TABLE_VALUE_MISMATCH"
    assert {ref.ref_id for ref in fixture.request.targets[0].evidence_refs} == {
        item.ref_id for item in fixture.evidence_package.items
    }
    assert OLD_PROJECT_ROOT not in prompt
    assert NEW_PROJECT_ROOT not in prompt
    assert str(PROJECT_ROOT) not in prompt


def test_manual_smoke_script_refuses_by_default() -> None:
    script_path = PROJECT_ROOT / "scripts" / "run-codex-cli-audit-smoke.sh"
    env = os.environ.copy()
    env.pop("ENABLE_CODEX_CLI_INTEGRATION", None)

    result = subprocess.run(
        ["bash", str(script_path)],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "ENABLE_CODEX_CLI_INTEGRATION=1" in result.stderr
    assert "真实 codex exec" in result.stderr
