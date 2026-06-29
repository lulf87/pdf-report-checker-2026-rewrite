from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Any, Callable

from app.domain.codex_review import CodexReviewRequest, CodexReviewResult
from app.domain.evidence_package import EvidencePackage


ReviewCallable = Callable[["CodexAuditJob"], list[CodexReviewResult]]


@dataclass(frozen=True)
class CodexAuditJob:
    key: str
    request: CodexReviewRequest
    evidence_package: EvidencePackage
    owner: Any = None


@dataclass(frozen=True)
class CodexAuditJobResult:
    job: CodexAuditJob
    reviews: list[CodexReviewResult]


class CodexAuditScheduler:
    """Bounded Codex audit package scheduler.

    The default max_parallel_jobs=1 preserves the previous serial execution
    semantics. Higher values only parallelize independent package reviews.
    """

    def __init__(self, *, max_parallel_jobs: int = 1) -> None:
        self.max_parallel_jobs = max(1, int(max_parallel_jobs or 1))

    def run(self, jobs: list[CodexAuditJob], review: ReviewCallable) -> list[CodexAuditJobResult]:
        if not jobs:
            return []
        queued_at = time.perf_counter()
        if self.max_parallel_jobs == 1 or len(jobs) == 1:
            return [
                self._run_one(index, job, review, queued_at=queued_at, worker_id=0)
                for index, job in enumerate(jobs)
            ]

        results_by_index: dict[int, CodexAuditJobResult] = {}
        with ThreadPoolExecutor(max_workers=self.max_parallel_jobs, thread_name_prefix="codex-audit") as executor:
            futures = {
                executor.submit(self._run_one, index, job, review, queued_at=queued_at, worker_id=index % self.max_parallel_jobs): index
                for index, job in enumerate(jobs)
            }
            for future in as_completed(futures):
                index = futures[future]
                results_by_index[index] = future.result()
        return [results_by_index[index] for index in range(len(jobs))]

    def _run_one(
        self,
        index: int,
        job: CodexAuditJob,
        review: ReviewCallable,
        *,
        queued_at: float,
        worker_id: int,
    ) -> CodexAuditJobResult:
        started_perf = time.perf_counter()
        started_at = _utc_now()
        reviews = review(job)
        completed_at = _utc_now()
        scheduler_profile = {
            "parallel_jobs": self.max_parallel_jobs,
            "worker_id": worker_id,
            "queue_index": index,
            "queue_wait_seconds": round(max(0.0, started_perf - queued_at), 6),
            "scheduler_total_seconds": round(max(0.0, time.perf_counter() - queued_at), 6),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }
        return CodexAuditJobResult(
            job=job,
            reviews=[_with_scheduler_profile(result, scheduler_profile) for result in reviews],
        )


def _with_scheduler_profile(result: CodexReviewResult, profile: dict[str, Any]) -> CodexReviewResult:
    metadata = dict(result.metadata)
    metadata["codex_scheduler_profile"] = profile
    return result.model_copy(update={"metadata": metadata})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = ["CodexAuditJob", "CodexAuditJobResult", "CodexAuditScheduler"]
