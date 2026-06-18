from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pytest

from app.domain.codex_review import (
    CodexEvidenceRef,
    CodexReviewRequest,
    CodexReviewTarget,
    CodexReviewTargetType,
)
from app.domain.evidence_package import (
    EvidenceItem,
    EvidencePackage,
    EvidencePackageKind,
    EvidenceSourceType,
    EvidenceTarget,
)
from app.infrastructure.codex.runner import CodexRunnerConfigurationError


CREATED_AT = datetime(2026, 6, 17, 9, 0, tzinfo=timezone.utc)
OLD_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"


def _review_target(
    *,
    target_id: str = "target-1",
    target_type: CodexReviewTargetType = CodexReviewTargetType.REPORT_RULE,
    evidence_refs: list[str] | None = None,
) -> CodexReviewTarget:
    refs = evidence_refs or ["ev-1"]
    return CodexReviewTarget(
        target_id=target_id,
        target_type=target_type,
        check_id="C02" if target_type is CodexReviewTargetType.REPORT_RULE else "PTR_TABLE",
        finding_id=f"finding-{target_id}",
        finding_code="C02_FIELD_MISMATCH" if target_type is CodexReviewTargetType.REPORT_RULE else "PTR_TABLE_VALUE_MISMATCH",
        title=f"Review {target_id}",
        summary=f"审核 {target_id} 的规则初判。",
        evidence_refs=[CodexEvidenceRef(ref_id=ref_id, source_type="pdf_text") for ref_id in refs],
    )


def _request(targets: list[CodexReviewTarget] | None = None) -> CodexReviewRequest:
    return CodexReviewRequest(
        request_id="request-1",
        task_id="task-1",
        task_type="report_check",
        targets=targets or [_review_target()],
        prompt_version="codex-review-prompt-v1",
        schema_version="codex-review-output-v1",
        created_at=CREATED_AT,
    )


def _package(
    *,
    kind: EvidencePackageKind = EvidencePackageKind.REPORT_RULE_REVIEW,
    target_type: str = "report_rule",
    target_refs: list[str] | None = None,
    items: list[EvidenceItem] | None = None,
) -> EvidencePackage:
    refs = target_refs or ["ev-1"]
    return EvidencePackage(
        package_id="pkg-1",
        task_id="task-1",
        task_type="report_check",
        kind=kind,
        schema_version="evidence-package-v1",
        created_at=CREATED_AT,
        targets=[
            EvidenceTarget(
                target_id="target-1",
                target_type=target_type,
                check_id="C02" if target_type == "report_rule" else "PTR_TABLE",
                finding_id="finding-target-1",
                finding_code="C02_FIELD_MISMATCH" if target_type == "report_rule" else "PTR_TABLE_VALUE_MISMATCH",
                summary="规则初判需要 Codex 复核。",
                evidence_refs=refs,
            )
        ],
        items=items
        or [
            EvidenceItem(
                ref_id="ev-1",
                source_type=EvidenceSourceType.PDF_TEXT,
                title="第三页字段片段",
                text="第三页型号规格: ABC-2",
                page_number=3,
                section="第三页",
                metadata={"field": "型号规格"},
            )
        ],
    )


def test_build_prompt_contains_package_target_and_evidence_refs() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "task-1" in prompt
    assert "pkg-1" in prompt
    assert "target-1" in prompt
    assert "ev-1" in prompt
    assert "第三页型号规格: ABC-2" in prompt


def test_prompt_contains_auditor_role_safety_and_json_only_requirements() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "受控审核员" in prompt
    assert "只能基于提供的 evidence refs" in prompt
    assert "不能读取项目源码" in prompt
    assert "不能修改文件" in prompt
    assert "只输出 JSON" in prompt
    assert "JSON schema" in prompt
    assert "uncertain" in prompt
    assert "不要臆测" in prompt


def test_prompt_only_includes_target_referenced_evidence() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    package = _package(
        items=[
            EvidenceItem(
                ref_id="ev-1",
                source_type=EvidenceSourceType.PDF_TEXT,
                text="authorized evidence text",
            ),
            EvidenceItem(
                ref_id="ev-unused",
                source_type=EvidenceSourceType.PDF_TEXT,
                text="unused evidence text must stay out",
            ),
        ]
    )

    prompt = PromptBuilder().build_review_prompt(_request(), package)

    assert "authorized evidence text" in prompt
    assert "ev-unused" not in prompt
    assert "unused evidence text must stay out" not in prompt


def test_prompt_redacts_old_and_new_project_absolute_paths_from_evidence_text() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    package = _package(
        items=[
            EvidenceItem(
                ref_id="ev-1",
                source_type=EvidenceSourceType.PDF_TEXT,
                text=f"旧路径 {OLD_PROJECT_ROOT}/backend/app/services/report_self_check_service.py；"
                f"新路径 {NEW_PROJECT_ROOT}/backend/app/domain/result.py",
                structured={"source": f"file://{NEW_PROJECT_ROOT}/frontend/src/App.tsx"},
                metadata={"note": f"{OLD_PROJECT_ROOT}/README.md"},
            )
        ]
    )

    prompt = PromptBuilder().build_review_prompt(_request(), package)

    assert OLD_PROJECT_ROOT not in prompt
    assert NEW_PROJECT_ROOT not in prompt
    assert "/Users/" not in prompt
    assert "file://" not in prompt
    assert "backend/app" not in prompt
    assert "frontend/src" not in prompt
    assert "[redacted-path]" in prompt


def test_prompt_builder_rejects_absolute_evidence_item_file_path() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    unsafe_item = EvidenceItem.model_construct(
        ref_id="ev-1",
        source_type=EvidenceSourceType.PDF_TEXT,
        text=None,
        structured=None,
        file_path=f"{NEW_PROJECT_ROOT}/runtime/codex_audit/task-1/pkg-1/input/items/ev-1.txt",
        page_number=None,
        section=None,
        location=None,
        metadata={},
    )
    package = EvidencePackage.model_construct(
        package_id="pkg-1",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        created_at=CREATED_AT,
        targets=[
            EvidenceTarget(
                target_id="target-1",
                target_type="report_rule",
                evidence_refs=["ev-1"],
            )
        ],
        items=[unsafe_item],
        metadata={},
    )

    with pytest.raises(CodexRunnerConfigurationError, match="file_path"):
        PromptBuilder().build_review_prompt(_request(), package)


def test_prompt_truncates_long_item_text() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    long_text = "A" * 200
    package = _package(
        items=[
            EvidenceItem(
                ref_id="ev-1",
                source_type=EvidenceSourceType.PDF_TEXT,
                text=long_text,
            )
        ]
    )

    prompt = PromptBuilder().build_review_prompt(
        _request(),
        package,
        max_item_text_chars=40,
    )

    assert "A" * 120 not in prompt
    assert "[truncated]" in prompt


def test_prompt_total_size_can_be_truncated() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(
        _request(),
        _package(),
        max_total_chars=900,
    )

    assert len(prompt) <= 900
    assert prompt.endswith("[truncated]\n")


def test_prompt_builder_fails_when_request_target_references_unknown_evidence() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    request = _request([_review_target(evidence_refs=["ev-missing"])])

    with pytest.raises(CodexRunnerConfigurationError, match="unknown evidence"):
        PromptBuilder().build_review_prompt(request, _package())


def test_prompt_instructs_add_finding_to_include_suggested_finding() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "add_finding" in prompt
    assert "suggested_finding" in prompt
    assert "原始 Finding" in prompt
    assert "不得删除" in prompt


@pytest.mark.parametrize(
    ("target_type", "kind", "package_target_type"),
    [
        (CodexReviewTargetType.PTR_TABLE, EvidencePackageKind.PTR_TABLE_REVIEW, "ptr_table"),
        (CodexReviewTargetType.PTR_CLAUSE, EvidencePackageKind.PTR_CLAUSE_REVIEW, "ptr_clause"),
        (CodexReviewTargetType.REPORT_RULE, EvidencePackageKind.REPORT_RULE_REVIEW, "report_rule"),
    ],
)
def test_prompt_renders_ptr_table_ptr_clause_and_report_rule_targets(
    target_type: CodexReviewTargetType,
    kind: EvidencePackageKind,
    package_target_type: str,
) -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    request = _request([_review_target(target_type=target_type)])
    package = _package(kind=kind, target_type=package_target_type)

    prompt = PromptBuilder().build_review_prompt(request, package)

    assert target_type.value in prompt
    assert kind.value in prompt
    assert package_target_type in prompt


def test_prompt_builder_does_not_call_subprocess_or_codex_cli_runner(monkeypatch) -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    def fail_if_called(*args, **kwargs):
        raise AssertionError("PromptBuilder must not call subprocess or real Codex")

    monkeypatch.setattr(subprocess, "run", fail_if_called)

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "pkg-1" in prompt
