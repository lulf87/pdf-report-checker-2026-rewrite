from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

import fitz

from app.application.codex_audit_service import CodexAuditService
from app.infrastructure.audit.codex_review_cache import CodexReviewCache
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
        image_paths: list[Path] | None = None,
    ) -> list[CodexReviewResult]:
        self.calls.append(
            {
                "request": request,
                "evidence_package": evidence_package,
                "workspace_dir": workspace_dir,
                "output_schema_path": output_schema_path,
                "prompt_path": prompt_path,
                "image_paths": image_paths or [],
            }
        )
        return self.inner.run_review(
            request,
            evidence_package,
            workspace_dir,
            output_schema_path=output_schema_path,
            prompt_path=prompt_path,
            image_paths=image_paths,
        )


class EmptyRunner:
    def run_review(self, *args, **kwargs) -> list[CodexReviewResult]:
        return []


class CountingRunner:
    def __init__(self, *, verdict: CodexReviewVerdict = CodexReviewVerdict.REFUTE) -> None:
        self.calls = 0
        self.verdict = verdict

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
        self.calls += 1
        return FakeCodexRunner(verdicts_by_target={target.target_id: self.verdict for target in request.targets}).run_review(
            request,
            evidence_package,
            workspace_dir,
            output_schema_path=output_schema_path,
            prompt_path=prompt_path,
            image_paths=image_paths,
        )


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
        image_paths: list[Path] | None = None,
    ) -> list[CodexReviewResult]:
        del evidence_package, workspace_dir, output_schema_path, prompt_path, image_paths
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


class MissingThenRecoverRunner:
    def __init__(self, *, missing_target_id: str, recover: bool = True) -> None:
        self.missing_target_id = missing_target_id
        self.recover = recover
        self.calls: list[list[str]] = []

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
        del evidence_package, workspace_dir, output_schema_path, prompt_path, image_paths
        self.calls.append([target.target_id for target in request.targets])
        if len(self.calls) == 1:
            return [
                _successful_review(request, target)
                for target in request.targets
                if target.target_id != self.missing_target_id
            ]
        if not self.recover:
            return []
        return [_successful_review(request, target) for target in request.targets]


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


def _service_with_cache(tmp_path, runner) -> CodexAuditService:
    return CodexAuditService(
        evidence_writer=EvidencePackageWriter(tmp_path / "runtime" / "codex_audit"),
        prompt_builder=PromptBuilder(),
        runner=runner,
        review_cache=CodexReviewCache(tmp_path / "runtime" / "codex_audit_cache"),
    )


def _assert_failed(results: list[CodexReviewResult], code: str, *, target_count: int = 1) -> None:
    assert len(results) == target_count
    assert {result.status for result in results} == {CodexReviewStatus.FAILED}
    assert {result.error.code for result in results if result.error is not None} == {code}


def _successful_review(request: CodexReviewRequest, target: CodexReviewTarget) -> CodexReviewResult:
    return CodexReviewResult(
        review_id=f"{request.request_id}:{target.target_id}:success",
        request_id=request.request_id,
        task_id=request.task_id,
        target=target,
        status=CodexReviewStatus.SUCCEEDED,
        verdict=CodexReviewVerdict.REFUTE,
        confidence=CodexReviewConfidence.MEDIUM,
        reasoning_summary="Synthetic review.",
        evidence_refs=[ref.ref_id for ref in target.evidence_refs],
        created_at=CREATED_AT,
        completed_at=CREATED_AT,
    )


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
    profile = results[0].metadata["codex_package_profile"]
    assert profile["package_id"] == "pkg-1"
    assert profile["check_id"] == "C02"
    assert profile["target_count"] == 1
    assert profile["evidence_write_seconds"] >= 0
    assert profile["prompt_build_seconds"] >= 0
    assert profile["schema_prepare_seconds"] >= 0
    assert profile["codex_exec_seconds"] >= 0
    assert profile["result_validation_seconds"] >= 0
    assert profile["prompt_size_bytes"] > 0
    assert profile["evidence_package_size_bytes"] > 0
    assert profile["image_count"] == 0
    assert profile["image_bytes"] == 0


def test_review_passes_workspace_image_paths_to_runner(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no real Codex")))
    source_pdf = tmp_path / "source.pdf"
    document = fitz.open()
    page = document.new_page(width=200, height=120)
    page.insert_text((20, 40), "图2 输注泵中文标签样张")
    document.save(source_pdf)
    document.close()
    image_item = EvidenceItem(
        ref_id="label_image:finding-1",
        source_type=EvidenceSourceType.IMAGE,
        title="C04 label image",
        file_path="items/label-image.png",
        page_number=1,
        metadata={"codex_image_input": True, "render_page_number": 1},
    )
    target = _target("target-1", evidence_refs=["label_image:finding-1"])
    runner = TrackingRunner(FakeCodexRunner())
    service = _service(tmp_path, runner)
    package = _package(targets=[target], items=[image_item]).model_copy(
        update={"metadata": {"source_pdf_path": str(source_pdf)}}
    )

    results = service.review(_request(targets=[target]), package)

    input_dir = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    assert results[0].status is CodexReviewStatus.SUCCEEDED
    assert runner.calls[0]["image_paths"] == [input_dir / "items" / "label-image.png"]
    assert runner.inner.last_image_paths == [input_dir / "items" / "label-image.png"]


def test_review_passes_c07_visual_image_paths_to_runner(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no real Codex")))
    source_pdf = tmp_path / "source.pdf"
    document = fitz.open()
    page = document.new_page(width=260, height=180)
    page.insert_text((20, 40), "序号 33 检验结果 符合要求 单项结论 符合 备注 /")
    document.save(source_pdf)
    document.close()
    refs = [
        "c07_visual_page:finding-1:p1",
        "c07_visual_table:finding-1:p1",
        "c07_visual_item_group:finding-1:p1",
        "c07_visual_result:finding-1:p1",
        "c07_visual_conclusion:finding-1:p1",
        "c07_visual_remark:finding-1:p1",
    ]
    image_items = [
        EvidenceItem(
            ref_id=ref,
            source_type=EvidenceSourceType.IMAGE,
            title=ref,
            file_path=f"items/finding-1-{name}.png",
            page_number=1,
            metadata={
                "codex_image_input": True,
                "render_page_number": 1,
                **({"crop_bbox": bbox} if bbox is not None else {}),
            },
        )
        for ref, name, bbox in [
            (refs[0], "c07-page-p1", None),
            (refs[1], "c07-table-p1", [10, 10, 240, 140]),
            (refs[2], "c07-item-group-p1", [10, 40, 240, 90]),
            (refs[3], "c07-result-p1", [100, 40, 150, 90]),
            (refs[4], "c07-conclusion-p1", [150, 40, 190, 90]),
            (refs[5], "c07-remark-p1", [190, 40, 220, 90]),
        ]
    ]
    target = CodexReviewTarget(
        target_id="target-c07-1",
        target_type=CodexReviewTargetType.INSPECTION_ITEM,
        check_id="C07",
        finding_id="finding-1",
        finding_code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
        title="C07 visual review",
        evidence_refs=[CodexEvidenceRef(ref_id=ref, source_type="image") for ref in refs],
    )
    runner = TrackingRunner(FakeCodexRunner())
    service = _service(tmp_path, runner)
    package = _package(targets=[target], items=image_items).model_copy(
        update={"metadata": {"source_pdf_path": str(source_pdf)}}
    )

    results = service.review(_request(targets=[target]), package)

    input_dir = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    image_paths = runner.calls[0]["image_paths"]
    assert results[0].status is CodexReviewStatus.SUCCEEDED
    assert [path.name for path in image_paths] == [
        "finding-1-c07-page-p1.png",
        "finding-1-c07-table-p1.png",
        "finding-1-c07-item-group-p1.png",
        "finding-1-c07-result-p1.png",
        "finding-1-c07-conclusion-p1.png",
        "finding-1-c07-remark-p1.png",
    ]
    assert all(path.is_relative_to(input_dir) for path in image_paths)
    assert all(path.is_file() for path in image_paths)
    assert all(str(source_pdf) != str(path) for path in image_paths)


def test_review_passes_c07_complex_matrix_image_paths_to_runner(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no real Codex")))
    source_pdf = tmp_path / "source.pdf"
    document = fitz.open()
    for page_index in range(2):
        page = document.new_page(width=260, height=180)
        page.insert_text((20, 40), f"序号 59 漏电流矩阵 p{page_index + 1} 单项结论 符合")
    document.save(source_pdf)
    document.close()
    roles = [
        ("page", 1, None),
        ("table", 1, [10, 10, 240, 150]),
        ("header", 1, [10, 10, 240, 40]),
        ("body", 1, [10, 40, 240, 130]),
        ("result", 1, [110, 40, 180, 130]),
        ("conclusion", 1, [180, 40, 230, 130]),
        ("continuation", 2, [10, 10, 240, 150]),
    ]
    refs = [f"c07_complex_matrix_{role}:finding-59:p{page}" for role, page, _ in roles]
    image_items = [
        EvidenceItem(
            ref_id=ref,
            source_type=EvidenceSourceType.IMAGE,
            title=ref,
            file_path=f"items/finding-59-c07-matrix-{role}-p{page}.png",
            page_number=page,
            section="c07_complex_matrix_visual",
            metadata={
                "codex_image_input": True,
                "render_page_number": page,
                "matrix_evidence_role": role,
                **({"crop_bbox": bbox} if bbox is not None else {}),
            },
        )
        for ref, (role, page, bbox) in zip(refs, roles, strict=True)
    ]
    target = CodexReviewTarget(
        target_id="target-c07-matrix-59",
        target_type=CodexReviewTargetType.INSPECTION_ITEM,
        check_id="C07",
        finding_id="finding-59",
        finding_code="CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX",
        title="C07 complex matrix review",
        evidence_refs=[CodexEvidenceRef(ref_id=ref, source_type="image") for ref in refs],
        metadata={
            "complex_matrix_table": True,
            "c07_complex_matrix_evidence": {
                "review_mode": "complex_matrix_specialized",
                "item_no": "59",
            },
        },
    )
    runner = TrackingRunner(FakeCodexRunner())
    service = _service(tmp_path, runner)
    package = _package(targets=[target], items=image_items).model_copy(
        update={"metadata": {"source_pdf_path": str(source_pdf)}}
    )

    results = service.review(_request(targets=[target]), package)

    input_dir = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    image_paths = runner.calls[0]["image_paths"]
    assert results[0].status is CodexReviewStatus.SUCCEEDED
    assert [path.name for path in image_paths] == [
        "finding-59-c07-matrix-page-p1.png",
        "finding-59-c07-matrix-table-p1.png",
        "finding-59-c07-matrix-header-p1.png",
        "finding-59-c07-matrix-body-p1.png",
        "finding-59-c07-matrix-result-p1.png",
        "finding-59-c07-matrix-conclusion-p1.png",
        "finding-59-c07-matrix-continuation-p2.png",
    ]
    assert all(path.is_relative_to(input_dir) for path in image_paths)
    assert all(path.is_file() for path in image_paths)
    assert all(str(source_pdf) != str(path) for path in image_paths)


def test_review_returns_results_for_multiple_targets(tmp_path) -> None:
    targets = [_target("target-1"), _target("target-2")]
    runner = TrackingRunner(FakeCodexRunner())
    results = _service(tmp_path, runner).review(_request(targets=targets), _package(targets=targets))

    assert [result.target.target_id for result in results] == ["target-1", "target-2"]
    assert {result.status for result in results} == {CodexReviewStatus.SUCCEEDED}
    assert {result.verdict for result in results} == {CodexReviewVerdict.CONFIRM}


def test_review_retries_missing_target_and_merges_recovered_review(tmp_path) -> None:
    targets = [_target("target-1"), _target("target-2"), _target("target-3")]
    runner = MissingThenRecoverRunner(missing_target_id="target-2")
    service = _service(tmp_path, runner)

    results = service.review(_request(targets=targets), _package(targets=targets))

    assert [result.target.target_id for result in results] == ["target-1", "target-2", "target-3"]
    assert {result.status for result in results} == {CodexReviewStatus.SUCCEEDED}
    assert runner.calls == [["target-1", "target-2", "target-3"], ["target-2"]]
    recovered = next(result for result in results if result.target.target_id == "target-2")
    assert recovered.metadata["missing_target_retry"]["attempt"] == 1


def test_review_reports_missing_target_retry_progress(tmp_path) -> None:
    targets = [_target("target-1"), _target("target-2")]
    runner = MissingThenRecoverRunner(missing_target_id="target-2")
    events: list[dict] = []
    service = CodexAuditService(
        evidence_writer=EvidencePackageWriter(tmp_path / "runtime" / "codex_audit"),
        prompt_builder=PromptBuilder(),
        runner=runner,
        progress_callback=events.append,
    )

    results = service.review(_request(targets=targets), _package(targets=targets))

    assert {result.status for result in results} == {CodexReviewStatus.SUCCEEDED}
    retry_events = [event for event in events if event.get("status") == "retrying"]
    assert retry_events
    assert retry_events[0]["last_retry_reason"] == "CODEX_OUTPUT_MISSING_TARGET"
    assert retry_events[0]["retry_count"] == 1
    assert retry_events[0]["missing_target_ids"] == ["target-2"]
    assert retry_events[0]["target_count"] == 1


def test_review_returns_missing_target_error_when_retry_still_missing(tmp_path) -> None:
    targets = [_target("target-1"), _target("target-2")]
    runner = MissingThenRecoverRunner(missing_target_id="target-2", recover=False)
    service = _service(tmp_path, runner)

    results = service.review(_request(targets=targets), _package(targets=targets))

    _assert_failed(results, "CODEX_OUTPUT_MISSING_TARGET", target_count=2)
    assert runner.calls == [["target-1", "target-2"], ["target-2"]]
    assert all("target-2" in (result.error.detail or "") for result in results if result.error)


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


def test_review_cache_reuses_succeeded_reviews_without_calling_runner_again(tmp_path) -> None:
    runner = CountingRunner()
    service = _service_with_cache(tmp_path, runner)
    request = _request()
    package = _package()

    first = service.review(request, package)
    second = service.review(request, package)

    assert runner.calls == 1
    assert first[0].status is CodexReviewStatus.SUCCEEDED
    assert second[0].status is CodexReviewStatus.SUCCEEDED
    assert second[0].metadata["cache_hit"] is True
    assert second[0].metadata["cache_key"] == first[0].metadata["cache_key"]
    assert second[0].request_id == request.request_id
    assert second[0].task_id == request.task_id
    assert second[0].target.target_id == request.targets[0].target_id


def test_review_cache_miss_when_prompt_version_changes(tmp_path) -> None:
    runner = CountingRunner()
    service = _service_with_cache(tmp_path, runner)
    package = _package()

    service.review(_request().model_copy(update={"prompt_version": "prompt-v1"}), package)
    service.review(_request().model_copy(update={"prompt_version": "prompt-v2"}), package)

    assert runner.calls == 2


def test_review_cache_does_not_reuse_uncertain_reviews(tmp_path) -> None:
    runner = CountingRunner(verdict=CodexReviewVerdict.UNCERTAIN)
    service = _service_with_cache(tmp_path, runner)
    request = _request()
    package = _package()

    first = service.review(request, package)
    second = service.review(request, package)

    assert runner.calls == 2
    assert first[0].verdict is CodexReviewVerdict.UNCERTAIN
    assert second[0].verdict is CodexReviewVerdict.UNCERTAIN
    assert "cache_hit" not in second[0].metadata


def test_review_cache_rebinds_succeeded_review_to_new_task_id(tmp_path) -> None:
    runner = CountingRunner()
    service = _service_with_cache(tmp_path, runner)
    first_task_id = "11111111-1111-4111-8111-111111111111"
    second_task_id = "22222222-2222-4222-8222-222222222222"

    service.review(_request(task_id=first_task_id), _package(task_id=first_task_id))
    cached = service.review(_request(task_id=second_task_id), _package(task_id=second_task_id))

    assert runner.calls == 1
    assert cached[0].task_id == second_task_id
    assert cached[0].request_id == "request-1"
    assert cached[0].metadata["cache_hit"] is True


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

    _assert_failed(results, "CODEX_OUTPUT_MISSING_TARGET")


def test_runner_incomplete_target_results_are_recovered_by_missing_target_retry(tmp_path) -> None:
    targets = [_target("target-1"), _target("target-2")]

    results = _service(tmp_path, PartialRunner()).review(_request(targets=targets), _package(targets=targets))

    assert [result.target.target_id for result in results] == ["target-1", "target-2"]
    assert {result.status for result in results} == {CodexReviewStatus.SUCCEEDED}
    assert results[1].metadata["missing_target_retry"]["retry_target_ids"] == ["target-2"]


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
