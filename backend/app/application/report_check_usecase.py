from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Protocol

from app.application.task_service import TaskService
from app.domain.pdf import ParsedPdf
from app.domain.report import InspectionTable, ReportDocument
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
    ) -> None:
        self.task_service = task_service
        self.file_store = file_store or LocalFileStore(Path(tempfile.gettempdir()) / "report-checker-runtime")
        self.pdf_parser = pdf_parser or PyMuPDFParser()
        self.field_extractor = field_extractor or FieldExtractor()
        self.inspection_table_extractor = inspection_table_extractor or InspectionTableExtractor()
        self.sample_description_extractor = sample_description_extractor or SampleDescriptionExtractor()
        self.photo_label_extractor = photo_label_extractor or PhotoLabelExtractor()
        self.rule_runner = rule_runner or ReportRuleRunner()

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


__all__ = ["ReportCheckUseCase"]
