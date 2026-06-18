from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

from app.application.codex_audit_service import CodexAuditService
from app.domain.codex_review import (
    CodexEvidenceRef,
    CodexReviewConfidence,
    CodexReviewError,
    CodexReviewRequest,
    CodexReviewResult,
    CodexReviewStatus,
    CodexReviewTarget,
    CodexReviewTargetType,
    CodexReviewVerdict,
    CodexSuggestedFinding,
)
from app.domain.evidence_package import (
    EvidenceItem,
    EvidencePackage,
    EvidencePackageKind,
    EvidenceSourceType,
    EvidenceTarget,
)
from app.infrastructure.audit.evidence_package_writer import EvidencePackageWriter
from app.infrastructure.codex.fake_codex_runner import FakeCodexRunner
from app.infrastructure.codex.prompt_builder import PromptBuilder
from app.infrastructure.codex.runner import CodexRunnerError


CREATED_AT = datetime(2026, 6, 17, 9, 0, tzinfo=timezone.utc)
OLD_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"


class TrackingRunner:
    def __init__(self, inner) -> None:
        self.inner = inner
        self.calls: list[dict] = []

    def run_review(
        self,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
        workspace_dir: Path,
        *,
        output_schema_path: Path | None = None,
        prompt_path: Path | None = None,
    ) -> list[CodexReviewResult]:
        self.calls.append(
            {
                "request": request,
                "evidence_package": evidence_package,
                "workspace_dir": workspace_dir,
                "output_schema_path": output_schema_path,
                "prompt_path": prompt_path,
            }
        )
        return self.inner.run_review(
            request,
            evidence_package,
            workspace_dir,
            output_schema_path=output_schema_path,
            prompt_path=prompt_path,
        )


class EmptyRunner:
    def run_review(self, *args, **kwargs) -> list[CodexReviewResult]:
        return []


class ExplodingRunner:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def run_review(self, *args, **kwargs) -> list[CodexReviewResult]:
        raise self.exc


class PartialRunner:
    def run_review(
        self,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
        workspace_dir: Path,
        *,
        output_schema_path: Path | None = None,
        prompt_path: Path | None = None,
    ) -> list[CodexReviewResult]:
        del evidence_package, workspace_dir, output_schema_path, prompt_path
        target = request.targets[0]
        return [
            CodexReviewResult(
                review_id="partial-review",
                request_id=request.request_id,
                task_id=request.task_id,
                target=target,
                status=CodexReviewStatus.SUCCEEDED,
                verdict=CodexReviewVerdict.CONFIRM,
                confidence=CodexReviewConfidence.MEDIUM,
                reasoning_summary="Only one target was returned.",
                evidence_refs=[ref.ref_id for ref in target.evidence_refs],
                created_at=CREATED_AT,
                completed_at=CREATED_AT,
            )
        ]


def _target(target_id: str = "target-1", *, evidence_refs: list[str] | None = None) -> CodexReviewTarget:
    refs = evidence_refs or [f"ev-{target_id}"]
    return CodexReviewTarget(
        target_id=target_id,
        target_type=CodexReviewTargetType.REPORT_RULE,
        check_id="C02",
        finding_id=f"finding-{target_id}",
        finding_code="C02_FIELD_MISMATCH",
        title=f"Review {target_id}",
        summary=f"复核 {target_id} 的规则初判。",
        evidence_refs=[CodexEvidenceRef(ref_id=ref_id, source_type="pdf_text") for ref_id in refs],
    )


def _request(
    *,
    targets: list[CodexReviewTarget] | None = None,
    task_id: str = "task-1",
    task_type: str = "report_check",
) -> CodexReviewRequest:
    return CodexReviewRequest(
        request_id="request-1",
        task_id=task_id,
        task_type=task_type,
        targets=targets or [_target()],
        prompt_version="codex-review-prompt-v1",
        schema_version="codex-review-output-v1",
        created_at=CREATED_AT,
    )


def _item(ref_id: str, *, text: str | None = None) -> EvidenceItem:
    return EvidenceItem(
        ref_id=ref_id,
        source_type=EvidenceSourceType.PDF_TEXT,
        title=f"Evidence {ref_id}",
        text=text or f"{ref_id}: 第三页型号规格 ABC-2",
        page_number=3,
        section="第三页",
    )


def _package(
    *,
    targets: list[CodexReviewTarget] | None = None,
    task_id: str = "task-1",
    task_type: str = "report_check",
    items: list[EvidenceItem] | None = None,
) -> EvidencePackage:
    review_targets = targets or [_target()]
    package_items = items or [_item(ref.ref_id) for target in review_targets for ref in target.evidence_refs]
    return EvidencePackage(
        package_id="pkg-1",
        task_id=task_id,
        task_type=task_type,
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        created_at=CREATED_AT,
        targets=[
            EvidenceTarget(
                target_id=target.target_id,
                target_type=target.target_type.value,
                check_id=target.check_id,
                finding_id=target.finding_id,
                finding_code=target.finding_code,
                summary=target.summary,
                evidence_refs=[ref.ref_id for ref in target.evidence_refs],
            )
            for target in review_targets
        ],
        items=package_items,
    )


def _service(tmp_path, runner) -> CodexAuditService:
    return CodexAuditService(
        evidence_writer=EvidencePackageWriter(tmp_path / "runtime" / "codex_audit"),
        prompt_builder=PromptBuilder(),
        runner=runner,
    )


def _assert_failed(results: list[CodexReviewResult], code: str, *, target_count: int = 1) -> None:
    assert len(results) == target_count
    assert {result.status for result in results} == {CodexReviewStatus.FAILED}
    assert {result.error.code for result in results if result.error is not None} == {code}


def test_review_writes_workspace_prompt_and_returns_confirm_with_fake_runner(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no real Codex")))
    runner = TrackingRunner(FakeCodexRunner())
    service = _service(tmp_path, runner)

    results = service.review(_request(), _package())

    assert len(results) == 1
    assert results[0].status is CodexReviewStatus.SUCCEEDED
    assert results[0].verdict is CodexReviewVerdict.CONFIRM
    input_dir = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    assert (input_dir / "evidence_package.json").is_file()
    assert (input_dir / "manifest.json").is_file()
    assert (input_dir / "prompt.md").is_file()
    assert (input_dir / "codex_review_output.schema.json").is_file()
    assert runner.calls[0]["workspace_dir"] == input_dir
    assert runner.calls[0]["prompt_path"] == input_dir / "prompt.md"
    assert runner.calls[0]["output_schema_path"] == input_dir / "codex_review_output.schema.json"


def test_review_returns_results_for_multiple_targets(tmp_path) -> None:
    targets = [_target("target-1"), _target("target-2")]
    runner = TrackingRunner(FakeCodexRunner())
    results = _service(tmp_path, runner).review(_request(targets=targets), _package(targets=targets))

    assert [result.target.target_id for result in results] == ["target-1", "target-2"]
    assert {result.status for result in results} == {CodexReviewStatus.SUCCEEDED}
    assert {result.verdict for result in results} == {CodexReviewVerdict.CONFIRM}


def test_review_preserves_refute_uncertain_and_add_finding_results(tmp_path) -> None:
    targets = [_target("target-1"), _target("target-2"), _target("target-3")]
    suggested = CodexSuggestedFinding(
        check_id="C02",
        severity="warn",
        code="C02_LABEL_AMBIGUOUS",
        message="Codex 建议新增标签字段歧义 finding。",
        evidence_refs=["ev-target-3"],
    )
    runner = FakeCodexRunner(
        verdicts_by_target={
            "target-1": CodexReviewVerdict.REFUTE,
            "target-2": CodexReviewVerdict.UNCERTAIN,
            "target-3": CodexReviewVerdict.ADD_FINDING,
        },
        suggested_findings_by_target={"target-3": suggested},
    )

    results = _service(tmp_path, runner).review(_request(targets=targets), _package(targets=targets))

    assert [result.verdict for result in results] == [
        CodexReviewVerdict.REFUTE,
        CodexReviewVerdict.UNCERTAIN,
        CodexReviewVerdict.ADD_FINDING,
    ]
    assert results[2].suggested_finding == suggested


def test_task_id_mismatch_returns_failed_without_calling_runner(tmp_path) -> None:
    runner = TrackingRunner(FakeCodexRunner())

    results = _service(tmp_path, runner).review(_request(task_id="task-request"), _package(task_id="task-package"))

    _assert_failed(results, "CODEX_AUDIT_REQUEST_PACKAGE_MISMATCH")
    assert runner.calls == []


def test_prompt_builder_failure_returns_failed_without_calling_runner(tmp_path) -> None:
    request = _request(targets=[_target(evidence_refs=["ev-missing"])])
    package = _package(targets=[_target(evidence_refs=["ev-1"])])
    runner = TrackingRunner(FakeCodexRunner())

    results = _service(tmp_path, runner).review(request, package)

    _assert_failed(results, "CODEX_AUDIT_PROMPT_BUILD_FAILED")
    assert runner.calls == []


def test_evidence_package_writer_failure_returns_failed_without_calling_runner(tmp_path, monkeypatch) -> None:
    runner = TrackingRunner(FakeCodexRunner())
    service = _service(tmp_path, runner)

    def fail_write(package: EvidencePackage):
        raise OSError("disk full")

    monkeypatch.setattr(service.evidence_writer, "write_package", fail_write)

    results = service.review(_request(), _package())

    _assert_failed(results, "CODEX_AUDIT_PACKAGE_WRITE_FAILED")
    assert runner.calls == []


def test_runner_exception_returns_failed_result(tmp_path) -> None:
    service = _service(tmp_path, ExplodingRunner(CodexRunnerError("runner exploded")))

    results = service.review(_request(), _package())

    _assert_failed(results, "CODEX_AUDIT_RUNNER_FAILED")


def test_runner_empty_result_returns_failed_result(tmp_path) -> None:
    results = _service(tmp_path, EmptyRunner()).review(_request(), _package())

    _assert_failed(results, "CODEX_AUDIT_RUNNER_EMPTY_RESULT")


def test_runner_incomplete_target_results_return_failed_results(tmp_path) -> None:
    targets = [_target("target-1"), _target("target-2")]

    results = _service(tmp_path, PartialRunner()).review(_request(targets=targets), _package(targets=targets))

    _assert_failed(results, "CODEX_AUDIT_RESULT_TARGET_MISMATCH", target_count=2)


def test_prompt_does_not_include_old_or_new_project_absolute_paths(tmp_path) -> None:
    item = _item(
        "ev-target-1",
        text=f"旧项目 {OLD_PROJECT_ROOT}/services/report_self_check_service.py；"
        f"新项目 {NEW_PROJECT_ROOT}/backend/app/domain/result.py",
    )
    service = _service(tmp_path, FakeCodexRunner())

    service.review(_request(), _package(items=[item]))

    prompt = (
        tmp_path
        / "runtime"
        / "codex_audit"
        / "task-1"
        / "pkg-1"
        / "input"
        / "prompt.md"
    ).read_text(encoding="utf-8")
    assert OLD_PROJECT_ROOT not in prompt
    assert NEW_PROJECT_ROOT not in prompt
    assert "/Users/" not in prompt
