from __future__ import annotations

from datetime import datetime, timezone
import tempfile
from pathlib import Path
from typing import Protocol

from app.application.codex_audit_targeting import priority_index
from app.application.report_codex_evidence_builder import ReportCodexEvidenceBuilder
from app.application.task_service import TaskService
from app.domain.codex_review import CodexReviewError, CodexReviewRequest, CodexReviewResult, CodexReviewStatus
from app.domain.evidence_package import EvidencePackage
from app.domain.pdf import ParsedPdf
from app.domain.report import InspectionTable, ReportDocument
from app.domain.result import CheckResult
from app.domain.task import TaskStatus, TaskType
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

    def run(
        self,
        *,
        file_name: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> TaskStatus:
        task = self.task_service.create_task(TaskType.REPORT_CHECK)
        try:
            stored = self.file_store.save_upload(
                task_id=task.task_id,
                file_name=file_name,
                content=content,
                content_type=content_type,
            )
            self.task_service.set_input_files(task.task_id, [stored.input_file])
            self.task_service.start_task(task.task_id, current_step="parsing report pdf", progress=5)

            parsed_pdf = self.pdf_parser.parse(stored.path)
            self.task_service.update_progress(task.task_id, progress=35, current_step="extracting report document")

            document = self._build_report_document(parsed_pdf)
            self.task_service.update_progress(task.task_id, progress=70, current_step="running report rules")

            run_result = self.rule_runner.run(document, CheckContext(task_id=task.task_id))
            self._attach_codex_reviews(
                task_id=task.task_id,
                document=document,
                parsed_pdf=parsed_pdf,
                check_results=run_result.results,
            )
            return self.task_service.complete_task(
                task.task_id,
                run_result.results,
                diagnostics=list(document.diagnostics) + list(parsed_pdf.diagnostics),
                metadata={"source": "report_check_usecase"},
            )
        except Exception as exc:
            return self.task_service.fail_task(task.task_id, str(exc))

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
    ) -> None:
        for result in self._ordered_codex_check_results(check_results):
            target_offset = 0
            while True:
                bundle = self.report_codex_evidence_builder.build(
                    task_id=task_id,
                    task_type=TaskType.REPORT_CHECK.value,
                    result=result,
                    report=document,
                    parsed_pdf=parsed_pdf,
                    target_offset=target_offset,
                )
                if bundle is None:
                    break
                if self.codex_audit_service is None:
                    raise RuntimeError("CODEX_AUDIT_REQUIRED: Codex audit service is required for reviewable report targets.")
                reviews = self.codex_audit_service.review(bundle.request, bundle.evidence_package)
                _raise_for_required_codex_audit_failure(reviews)
                result.codex_reviews.extend(reviews)
                _annotate_candidate_findings_with_codex_status(result, reviews)
                target_offset += len(bundle.request.targets)
                if not bundle.evidence_package.metadata.get("truncated"):
                    break

    def _ordered_codex_check_results(self, check_results: list[CheckResult]) -> list[CheckResult]:
        priority = priority_index(self.report_codex_evidence_builder.target_selection.priority_check_ids)
        fallback = len(priority)
        return [
            result
            for _, result in sorted(
                enumerate(check_results),
                key=lambda pair: (priority.get(pair[1].check_id, fallback), pair[0]),
            )
        ]


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


def _annotate_candidate_findings_with_codex_status(result: CheckResult, reviews: list[CodexReviewResult]) -> None:
    findings_by_id = {finding.id: finding for finding in result.findings}
    for review in reviews:
        finding_id = review.target.finding_id
        if not finding_id or finding_id not in findings_by_id:
            continue
        finding = findings_by_id[finding_id]
        verdict = review.verdict.value if review.verdict is not None else None
        finding.metadata["codex_required"] = True
        finding.metadata["codex_review_id"] = review.review_id
        finding.metadata["codex_verdict"] = verdict
        finding.metadata["final_status"] = _final_status_for_verdict(verdict)


def _final_status_for_verdict(verdict: str | None) -> str:
    if verdict == "confirm":
        return "confirmed"
    if verdict == "refute":
        return "refuted"
    if verdict == "uncertain":
        return "manual_review_required"
    if verdict == "add_finding":
        return "suggested_additional_finding"
    return "pending"


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
