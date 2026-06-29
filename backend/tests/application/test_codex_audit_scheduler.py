from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.application.codex_audit_scheduler import CodexAuditJob, CodexAuditScheduler
from app.domain.codex_review import (
    CodexReviewConfidence,
    CodexReviewRequest,
    CodexReviewResult,
    CodexReviewStatus,
    CodexReviewTarget,
    CodexReviewTargetType,
    CodexReviewVerdict,
)
from app.domain.evidence_package import EvidencePackage, EvidencePackageKind, EvidenceSourceType, EvidenceTarget, EvidenceItem


@dataclass
class _ConcurrencyProbe:
    active: int = 0
    max_active: int = 0
    calls: int = 0


def test_codex_audit_scheduler_respects_parallel_job_limit() -> None:
    probe = _ConcurrencyProbe()
    lock = threading.Lock()
    scheduler = CodexAuditScheduler(max_parallel_jobs=2)
    jobs = [_job(index) for index in range(5)]

    def review(job: CodexAuditJob) -> list[CodexReviewResult]:
        with lock:
            probe.calls += 1
            probe.active += 1
            probe.max_active = max(probe.max_active, probe.active)
        time.sleep(0.02)
        with lock:
            probe.active -= 1
        return [_review(job)]

    results = scheduler.run(jobs, review)

    assert probe.calls == 5
    assert probe.max_active <= 2
    assert [result.job.key for result in results] == [job.key for job in jobs]
    assert all(review.metadata["codex_scheduler_profile"]["parallel_jobs"] == 2 for result in results for review in result.reviews)
    assert all("queue_wait_seconds" in review.metadata["codex_scheduler_profile"] for result in results for review in result.reviews)


def test_codex_audit_scheduler_parallel_one_preserves_sequential_behavior() -> None:
    seen: list[str] = []
    scheduler = CodexAuditScheduler(max_parallel_jobs=1)
    jobs = [_job(index) for index in range(3)]

    def review(job: CodexAuditJob) -> list[CodexReviewResult]:
        seen.append(job.key)
        return [_review(job)]

    results = scheduler.run(jobs, review)

    assert seen == ["job-0", "job-1", "job-2"]
    assert [result.job.key for result in results] == seen
    assert all(review.metadata["codex_scheduler_profile"]["worker_id"] == 0 for result in results for review in result.reviews)


def test_codex_audit_scheduler_parallel_two_reduces_fake_runner_wall_time() -> None:
    jobs = [_job(index) for index in range(4)]

    def slow_review(job: CodexAuditJob) -> list[CodexReviewResult]:
        time.sleep(0.04)
        return [_review(job)]

    serial_started = time.perf_counter()
    serial_results = CodexAuditScheduler(max_parallel_jobs=1).run(jobs, slow_review)
    serial_seconds = time.perf_counter() - serial_started

    parallel_started = time.perf_counter()
    parallel_results = CodexAuditScheduler(max_parallel_jobs=2).run(jobs, slow_review)
    parallel_seconds = time.perf_counter() - parallel_started

    assert [result.job.key for result in serial_results] == [job.key for job in jobs]
    assert [result.job.key for result in parallel_results] == [job.key for job in jobs]
    assert parallel_seconds < serial_seconds
    assert all(
        review.metadata["codex_scheduler_profile"]["parallel_jobs"] == 2
        for result in parallel_results
        for review in result.reviews
    )


def _job(index: int) -> CodexAuditJob:
    target = CodexReviewTarget(
        target_id=f"target-{index}",
        target_type=CodexReviewTargetType.REPORT_RULE,
        check_id="C02",
        finding_id=f"finding-{index}",
        finding_code="C02_FIELD_MISMATCH",
    )
    request = CodexReviewRequest(
        request_id=f"request-{index}",
        task_id="task-1",
        task_type="report_check",
        targets=[target],
        schema_version="codex-review-output-v1",
    )
    package = EvidencePackage(
        package_id=f"pkg-{index}",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        targets=[
            EvidenceTarget(
                target_id=target.target_id,
                target_type=target.target_type.value,
                check_id=target.check_id,
                finding_id=target.finding_id,
                finding_code=target.finding_code,
                evidence_refs=[f"ev-{index}"],
            )
        ],
        items=[
            EvidenceItem(
                ref_id=f"ev-{index}",
                source_type=EvidenceSourceType.PDF_TEXT,
                text=f"evidence {index}",
            )
        ],
    )
    return CodexAuditJob(key=f"job-{index}", request=request, evidence_package=package, owner=index)


def _review(job: CodexAuditJob) -> CodexReviewResult:
    target = job.request.targets[0]
    return CodexReviewResult(
        review_id=f"{job.request.request_id}:{target.target_id}:fake",
        request_id=job.request.request_id,
        task_id=job.request.task_id,
        target=target,
        status=CodexReviewStatus.SUCCEEDED,
        verdict=CodexReviewVerdict.REFUTE,
        confidence=CodexReviewConfidence.HIGH,
        reasoning_summary="scheduler fake review",
    )
