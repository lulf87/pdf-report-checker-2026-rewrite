from __future__ import annotations

from datetime import datetime, timezone
import tempfile
from pathlib import Path
from typing import Any, Protocol

from app.application.codex_audit_finalization import (
    annotate_candidate_findings_with_codex_status,
    final_status_for_verdict,
    finalize_codex_audit,
)
from app.application.codex_audit_options import CodexAuditOptions
from app.application.codex_audit_scheduler import CodexAuditJob, CodexAuditScheduler
from app.application.codex_audit_targeting import priority_index
from app.application.performance_profile import PerformanceProfile
from app.application.report_codex_evidence_builder import REVIEWABLE_TARGET_TYPES, ReportCodexEvidenceBuilder
from app.application.task_service import TaskService
from app.domain.codex_review import CodexReviewError, CodexReviewRequest, CodexReviewResult, CodexReviewStatus
from app.domain.evidence_package import EvidencePackage
from app.domain.pdf import ParsedPdf
from app.domain.report import InspectionTable, ReportDocument
from app.domain.result import CheckResult
from app.domain.task import TaskState, TaskStatus, TaskType
from app.infrastructure.pdf.pymupdf_parser import PyMuPDFParser
from app.infrastructure.report.field_extractor import FieldExtractor
from app.infrastructure.report.inspection_table_extractor import InspectionTableExtractor
from app.infrastructure.report.photo_label_extractor import PhotoLabelExtractor
from app.infrastructure.report.sample_description_extractor import SampleDescriptionExtractor
from app.infrastructure.storage.local_file_store import LocalFileStore
from app.rules.report.context import CheckContext
from app.rules.report.runner import ReportRuleRunner


class PdfParser(Protocol):
    def parse(self, file_path: Path) -> ParsedPdf:
        ...


class ReportFieldExtractor(Protocol):
    def extract(self, parsed_pdf: ParsedPdf) -> ReportDocument:
        ...


class ReportInspectionTableExtractor(Protocol):
    def extract_table(self, parsed_pdf: ParsedPdf) -> InspectionTable | None:
        ...


class ReportSampleDescriptionExtractor(Protocol):
    def extract_rows(self, parsed_pdf: ParsedPdf) -> list:
        ...

    def extract_components(self, parsed_pdf: ParsedPdf) -> list:
        ...


class ReportPhotoLabelExtractor(Protocol):
    def extract_captions(self, parsed_pdf: ParsedPdf) -> list:
        ...

    def extract_labels(self, parsed_pdf: ParsedPdf) -> list:
        ...


class CodexAuditServiceProtocol(Protocol):
    def review(
        self,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
    ) -> list[CodexReviewResult]:
        ...


class ReportCheckUseCase:
    """Application orchestration for report self-check tasks."""

    def __init__(
        self,
        *,
        task_service: TaskService,
        file_store: LocalFileStore | None = None,
        pdf_parser: PdfParser | None = None,
        field_extractor: ReportFieldExtractor | None = None,
        inspection_table_extractor: ReportInspectionTableExtractor | None = None,
        sample_description_extractor: ReportSampleDescriptionExtractor | None = None,
        photo_label_extractor: ReportPhotoLabelExtractor | None = None,
        rule_runner: ReportRuleRunner | None = None,
        codex_audit_service: CodexAuditServiceProtocol | None = None,
        codex_audit_enabled: bool = False,
        report_codex_evidence_builder: ReportCodexEvidenceBuilder | None = None,
        codex_audit_scheduler: CodexAuditScheduler | None = None,
    ) -> None:
        del codex_audit_enabled
        self.task_service = task_service
        self.file_store = file_store or LocalFileStore(Path(tempfile.gettempdir()) / "report-checker-runtime")
        self.pdf_parser = pdf_parser or PyMuPDFParser()
        self.field_extractor = field_extractor or FieldExtractor()
        self.inspection_table_extractor = inspection_table_extractor or InspectionTableExtractor()
        self.sample_description_extractor = sample_description_extractor or SampleDescriptionExtractor()
        self.photo_label_extractor = photo_label_extractor or PhotoLabelExtractor()
        self.rule_runner = rule_runner or ReportRuleRunner()
        self.codex_audit_service = codex_audit_service
        self.codex_audit_enabled = codex_audit_service is not None
        self.report_codex_evidence_builder = report_codex_evidence_builder or ReportCodexEvidenceBuilder()
        self.codex_audit_scheduler = codex_audit_scheduler or CodexAuditScheduler(max_parallel_jobs=1)

    def run(
        self,
        *,
        file_name: str,
        content: bytes,
        content_type: str = "application/pdf",
        audit_options: CodexAuditOptions | dict[str, Any] | None = None,
    ) -> TaskStatus:
        task = self.submit(file_name=file_name, content=content, content_type=content_type, audit_options=audit_options)
        if task.status != TaskState.PROCESSING:
            return task
        return self.process_task(task.task_id)

    def submit(
        self,
        *,
        file_name: str,
        content: bytes,
        content_type: str = "application/pdf",
        audit_options: CodexAuditOptions | dict[str, Any] | None = None,
    ) -> TaskStatus:
        options = CodexAuditOptions.from_raw(audit_options)
        task = self.task_service.create_task(
            TaskType.REPORT_CHECK,
            metadata={"audit_options": options.to_metadata(), "audit_options_source": "user_override" if options.has_user_override else "default"},
        )
        try:
            stored = self.file_store.save_upload(
                task_id=task.task_id,
                file_name=file_name,
                content=content,
                content_type=content_type,
            )
            self.task_service.set_input_files(task.task_id, [stored.input_file])
            return self.task_service.start_task(task.task_id, current_step="queued report check", progress=1)
        except Exception as exc:
            return self.task_service.fail_task(task.task_id, str(exc))

    def process_task(self, task_id: str) -> TaskStatus:
        try:
            source_pdf_path = self._source_pdf_path_for_task(task_id)
            return self._process_stored_upload(task_id=task_id, source_pdf_path=source_pdf_path)
        except Exception as exc:
            return self.task_service.fail_task(task_id, str(exc))

    def _source_pdf_path_for_task(self, task_id: str) -> Path:
        task = self.task_service.get_task(task_id)
        if not task.input_files:
            raise ValueError("Report check task has no input file.")
        return self.file_store.get_upload_path(task_id=task_id, file_name=task.input_files[0].file_name)

    def _process_stored_upload(self, *, task_id: str, source_pdf_path: Path) -> TaskStatus:
        profile = PerformanceProfile()
        task = self.task_service.get_task(task_id)
        audit_options = CodexAuditOptions.from_raw(task.metadata.get("audit_options"))
        audit_options_source = "user_override" if audit_options.has_user_override else "default"
        evidence_builder = self._builder_for_audit_options(audit_options)
        scheduler = self._scheduler_for_audit_options(audit_options)
        self.task_service.start_task(task_id, current_step="parsing report pdf", progress=5)

        with profile.measure("parse_pdf"):
            parsed_pdf = self.pdf_parser.parse(source_pdf_path)
        self.task_service.update_progress(task_id, progress=35, current_step="extracting report document")

        with profile.measure("build_report_document"):
            document = self._build_report_document(parsed_pdf)
        self.task_service.update_progress(task_id, progress=70, current_step="running report rules")

        with profile.measure("run_rules"):
            run_result = self.rule_runner.run(document, CheckContext(task_id=task_id))
        with profile.measure("codex_audit_total", parallel_jobs=scheduler.max_parallel_jobs):
            self._attach_codex_reviews(
                task_id=task_id,
                document=document,
                parsed_pdf=parsed_pdf,
                source_pdf_path=source_pdf_path,
                check_results=run_result.results,
                evidence_builder=evidence_builder,
                scheduler=scheduler,
            )
        profile.add_package_profiles(_codex_package_profiles(run_result.results))
        with profile.measure("finalize_codex_audit"):
            codex_audit_metadata = finalize_codex_audit(
                run_result.results,
                target_selection=evidence_builder.target_selection,
                is_reviewable_finding=lambda finding: finding.check_id in REVIEWABLE_TARGET_TYPES,
            )

        def result_metadata() -> dict[str, Any]:
            profile_payload = profile.to_dict()
            codex_payload = {
                **codex_audit_metadata,
                "performance_profile": {
                    "packages": profile_payload["packages"],
                    "package_totals": profile_payload["package_totals"],
                },
            }
            return {
                "source": "report_check_usecase",
                "audit_options_source": audit_options_source,
                "audit_options": audit_options.to_metadata(),
                "effective_audit_options": _effective_audit_options_metadata(evidence_builder, scheduler),
                "performance_profile": profile_payload,
                "codex_audit": codex_payload,
            }

        with profile.measure("complete_task"):
            status = self.task_service.complete_task(
                task_id,
                run_result.results,
                diagnostics=list(document.diagnostics) + list(parsed_pdf.diagnostics),
                metadata=result_metadata(),
            )
        self.task_service.update_result_metadata(task_id, result_metadata())
        return status

    def _build_report_document(self, parsed_pdf: ParsedPdf) -> ReportDocument:
        document = self.field_extractor.extract(parsed_pdf)
        document.parsed_pdf = parsed_pdf

        inspection_table = self.inspection_table_extractor.extract_table(parsed_pdf)
        if inspection_table is not None:
            document.inspection_table = inspection_table
            document.inspection_items = list(inspection_table.items)

        document.sample_description_rows = list(self.sample_description_extractor.extract_rows(parsed_pdf))
        document.sample_components = list(self.sample_description_extractor.extract_components(parsed_pdf))
        document.photo_captions = list(self.photo_label_extractor.extract_captions(parsed_pdf))
        document.labels = list(self.photo_label_extractor.extract_labels(parsed_pdf))
        document.diagnostics = list(document.diagnostics)
        return document

    def _attach_codex_reviews(
        self,
        *,
        task_id: str,
        document: ReportDocument,
        parsed_pdf: ParsedPdf,
        check_results: list[CheckResult],
        source_pdf_path: Path | None = None,
        evidence_builder: ReportCodexEvidenceBuilder | None = None,
        scheduler: CodexAuditScheduler | None = None,
    ) -> None:
        builder = evidence_builder or self.report_codex_evidence_builder
        active_scheduler = scheduler or self.codex_audit_scheduler
        jobs: list[CodexAuditJob] = []
        for result in self._ordered_codex_check_results(check_results, evidence_builder=builder):
            target_offset = 0
            while True:
                bundle = builder.build(
                    task_id=task_id,
                    task_type=TaskType.REPORT_CHECK.value,
                    result=result,
                    report=document,
                    parsed_pdf=parsed_pdf,
                    source_pdf_path=source_pdf_path,
                    target_offset=target_offset,
                )
                if bundle is None:
                    break
                if self.codex_audit_service is None:
                    raise RuntimeError("CODEX_AUDIT_REQUIRED: Codex audit service is required for reviewable report targets.")
                jobs.append(
                    CodexAuditJob(
                        key=bundle.request.request_id,
                        request=bundle.request,
                        evidence_package=bundle.evidence_package,
                        owner=result,
                    )
                )
                target_offset += len(bundle.request.targets)
                if not bundle.evidence_package.metadata.get("truncated"):
                    break
        job_results = active_scheduler.run(jobs, lambda job: self.codex_audit_service.review(job.request, job.evidence_package))
        for job_result in job_results:
            reviews = job_result.reviews
            _raise_for_required_codex_audit_failure(reviews)
            result = job_result.job.owner
            result.codex_reviews.extend(reviews)
        annotate_candidate_findings_with_codex_status(check_results, [review for job_result in job_results for review in job_result.reviews])

    def _ordered_codex_check_results(
        self,
        check_results: list[CheckResult],
        *,
        evidence_builder: ReportCodexEvidenceBuilder | None = None,
    ) -> list[CheckResult]:
        builder = evidence_builder or self.report_codex_evidence_builder
        priority = priority_index(builder.target_selection.priority_check_ids)
        fallback = len(priority)
        return [
            result
            for _, result in sorted(
                enumerate(check_results),
                key=lambda pair: (priority.get(pair[1].check_id, fallback), pair[0]),
            )
        ]

    def _builder_for_audit_options(self, options: CodexAuditOptions) -> ReportCodexEvidenceBuilder:
        selection = self.report_codex_evidence_builder.target_selection
        if not options.has_user_override:
            return self.report_codex_evidence_builder
        return ReportCodexEvidenceBuilder(
            max_text_chars=self.report_codex_evidence_builder.max_text_chars,
            max_targets_per_task=selection.max_targets_per_task,
            max_targets_per_batch=options.max_targets_per_batch or selection.max_targets_per_batch,
            included_check_ids=options.included_check_ids or selection.included_check_ids,
            included_finding_codes=options.included_finding_codes or selection.included_finding_codes,
            excluded_check_ids=options.excluded_check_ids or selection.excluded_check_ids,
            priority_check_ids=selection.priority_check_ids,
        )

    def _scheduler_for_audit_options(self, options: CodexAuditOptions) -> CodexAuditScheduler:
        if options.max_parallel_jobs is None:
            return self.codex_audit_scheduler
        return CodexAuditScheduler(max_parallel_jobs=options.max_parallel_jobs)


def _raise_for_required_codex_audit_failure(reviews: list[CodexReviewResult]) -> None:
    failed = [review for review in reviews if review.status in {CodexReviewStatus.FAILED, CodexReviewStatus.SKIPPED}]
    if not failed:
        return
    error = next((review.error for review in failed if review.error is not None), None)
    code = error.code if error is not None else "CODEX_AUDIT_FAILED"
    message = error.message if error is not None else "Mandatory Codex audit did not produce a succeeded review."
    detail = error.detail if error is not None else None
    if detail:
        raise RuntimeError(f"{code}: {message} {detail}")
    raise RuntimeError(f"{code}: {message}")


def _codex_package_profiles(check_results: list[CheckResult]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in check_results:
        for review in result.codex_reviews:
            profile = review.metadata.get("codex_package_profile")
            if not isinstance(profile, dict):
                continue
            key = str(profile.get("package_id") or review.request_id)
            if key in seen:
                continue
            seen.add(key)
            profiles.append(profile)
    return profiles


def _effective_audit_options_metadata(
    evidence_builder: ReportCodexEvidenceBuilder,
    scheduler: CodexAuditScheduler,
) -> dict[str, Any]:
    selection = evidence_builder.target_selection
    return {
        "included_check_ids": sorted(selection.included_check_ids),
        "included_finding_codes": sorted(selection.included_finding_codes),
        "excluded_check_ids": sorted(selection.excluded_check_ids),
        "max_targets_per_task": selection.max_targets_per_task,
        "max_targets_per_batch": selection.max_targets_per_batch,
        "priority_check_ids": list(selection.priority_check_ids),
        "max_parallel_jobs": scheduler.max_parallel_jobs,
    }


def _final_status_for_verdict(verdict: str | None) -> str:
    return final_status_for_verdict(verdict)


def _failed_codex_reviews_for_request(
    request: CodexReviewRequest,
    exc: Exception,
) -> list[CodexReviewResult]:
    now = datetime.now(timezone.utc)
    error = CodexReviewError(
        code="CODEX_REPORT_AUDIT_SERVICE_FAILED",
        message="Report Codex audit service failed inside ReportCheckUseCase.",
        detail=str(exc),
        retryable=False,
    )
    return [
        CodexReviewResult(
            review_id=f"report-codex-audit:{request.request_id}:{target.target_id}:failed",
            request_id=request.request_id,
            task_id=request.task_id,
            target=target,
            status=CodexReviewStatus.FAILED,
            error=error,
            created_at=now,
            completed_at=now,
            metadata={"source": "report_check_usecase"},
        )
        for target in request.targets
    ]


__all__ = ["ReportCheckUseCase"]
