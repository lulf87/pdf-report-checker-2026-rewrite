from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Protocol

from app.application.task_service import TaskService
from app.domain.finding import Finding, FindingSeverity
from app.domain.pdf import ParsedPdf
from app.domain.ptr import PTRClause, PTRDocument
from app.domain.report import InspectionItem, InspectionTable, ReportDocument
from app.domain.result import CheckResult, CheckStatus
from app.domain.task import TaskStatus, TaskType
from app.infrastructure.pdf.pymupdf_parser import PyMuPDFParser
from app.infrastructure.ptr.ptr_extractor import PTRExtractor
from app.infrastructure.report.field_extractor import FieldExtractor
from app.infrastructure.report.inspection_table_extractor import InspectionTableExtractor
from app.infrastructure.storage.local_file_store import LocalFileStore
from app.rules.ptr.clause_text_compare import compare_clause_texts
from app.rules.ptr.scope_filter import ScopeFilterResult, filter_ptr_scope
from app.rules.ptr.table_reference_compare import check_table_references


CLAUSE_NUMBER_RE = re.compile(r"\d+(?:\.\d+)+")


class PdfParser(Protocol):
    def parse(self, file_path: Path) -> ParsedPdf:
        ...


class PTRDocumentExtractor(Protocol):
    def extract(self, parsed_pdf: ParsedPdf) -> PTRDocument:
        ...


class ReportExtractor(Protocol):
    def extract(self, parsed_pdf: ParsedPdf) -> ReportDocument:
        ...


class ReportInspectionTableExtractor(Protocol):
    def extract_table(self, parsed_pdf: ParsedPdf) -> InspectionTable | None:
        ...


class ScopeFilter(Protocol):
    def __call__(
        self,
        ptr_doc: PTRDocument,
        inspection_scope_texts: list[str],
        *,
        report_clause_numbers: set[str] | None = None,
    ) -> ScopeFilterResult:
        ...


class ClauseTextCompare(Protocol):
    def __call__(
        self,
        ptr_clauses: list[PTRClause],
        report_items: list[InspectionItem],
        *,
        task_id: str,
    ) -> list[Finding]:
        ...


class TableReferenceCompare(Protocol):
    def __call__(
        self,
        ptr_doc: PTRDocument,
        *,
        clauses: list[PTRClause] | None = None,
        task_id: str,
    ) -> list[Finding]:
        ...


class PTRCompareUseCase:
    """Application orchestration for PTR-vs-report comparison tasks."""

    def __init__(
        self,
        *,
        task_service: TaskService,
        file_store: LocalFileStore | None = None,
        pdf_parser: PdfParser | None = None,
        ptr_extractor: PTRDocumentExtractor | None = None,
        report_extractor: ReportExtractor | None = None,
        inspection_table_extractor: ReportInspectionTableExtractor | None = None,
        scope_filter: ScopeFilter = filter_ptr_scope,
        clause_text_compare: ClauseTextCompare = compare_clause_texts,
        table_reference_compare: TableReferenceCompare = check_table_references,
    ) -> None:
        self.task_service = task_service
        self.file_store = file_store or LocalFileStore(Path(tempfile.gettempdir()) / "report-checker-runtime")
        self.pdf_parser = pdf_parser or PyMuPDFParser()
        self.ptr_extractor = ptr_extractor or PTRExtractor()
        self.report_extractor = report_extractor or FieldExtractor()
        self.inspection_table_extractor = inspection_table_extractor or InspectionTableExtractor()
        self.scope_filter = scope_filter
        self.clause_text_compare = clause_text_compare
        self.table_reference_compare = table_reference_compare

    def run(
        self,
        *,
        ptr_file_name: str,
        ptr_content: bytes,
        report_file_name: str,
        report_content: bytes,
        ptr_content_type: str = "application/pdf",
        report_content_type: str = "application/pdf",
        content_type: str | None = None,
    ) -> TaskStatus:
        task = self.task_service.create_task(TaskType.PTR_COMPARE)
        try:
            ptr_stored = self.file_store.save_upload(
                task_id=task.task_id,
                file_name=ptr_file_name,
                content=ptr_content,
                content_type=ptr_content_type or content_type or "application/pdf",
                category="ptr",
            )
            report_stored = self.file_store.save_upload(
                task_id=task.task_id,
                file_name=report_file_name,
                content=report_content,
                content_type=report_content_type or content_type or "application/pdf",
                category="report",
            )
            self.task_service.set_input_files(task.task_id, [ptr_stored.input_file, report_stored.input_file])
            self.task_service.start_task(task.task_id, current_step="parsing ptr and report pdfs", progress=5)

            ptr_pdf = self.pdf_parser.parse(ptr_stored.path)
            report_pdf = self.pdf_parser.parse(report_stored.path)

            self.task_service.update_progress(task.task_id, progress=35, current_step="extracting ptr and report documents")
            ptr_doc = self.ptr_extractor.extract(ptr_pdf)
            report_doc = self._build_report_document(report_pdf)

            scope_texts = self._inspection_scope_texts(report_doc)
            report_clause_numbers = self._report_clause_numbers(report_doc.inspection_items)
            scope_result = self.scope_filter(
                ptr_doc,
                scope_texts,
                report_clause_numbers=report_clause_numbers,
            )
            included_clauses = self._included_main_requirement_clauses(ptr_doc, scope_result)

            self.task_service.update_progress(task.task_id, progress=70, current_step="running ptr comparison rules")
            clause_findings = self.clause_text_compare(
                included_clauses,
                report_doc.inspection_items,
                task_id=task.task_id,
            )
            table_findings = self.table_reference_compare(
                ptr_doc,
                clauses=included_clauses,
                task_id=task.task_id,
            )

            check_results = [
                self._scope_check_result(task.task_id, scope_result, included_clauses),
                self._finding_check_result(
                    task.task_id,
                    check_id="PTR_CLAUSE",
                    check_name="PTR 条款正文一致性",
                    findings=clause_findings,
                    pass_summary="PTR 条款正文一致",
                    issue_summary="PTR 条款正文存在差异或需复核",
                ),
                self._finding_check_result(
                    task.task_id,
                    check_id="PTR_TABLE",
                    check_name="PTR 表格引用完整性",
                    findings=table_findings,
                    pass_summary="PTR 表格引用完整",
                    issue_summary="PTR 表格引用存在缺失或需复核",
                ),
            ]
            return self.task_service.complete_task(
                task.task_id,
                check_results,
                diagnostics=list(ptr_doc.diagnostics)
                + list(report_doc.diagnostics)
                + list(ptr_pdf.diagnostics)
                + list(report_pdf.diagnostics),
                metadata={
                    "source": "ptr_compare_usecase",
                    "included_clause_count": len(included_clauses),
                    "scope": scope_result.model_dump(mode="json"),
                },
            )
        except Exception as exc:
            return self.task_service.fail_task(task.task_id, str(exc))

    def _build_report_document(self, parsed_pdf: ParsedPdf) -> ReportDocument:
        document = self.report_extractor.extract(parsed_pdf)
        document.parsed_pdf = parsed_pdf
        inspection_table = self.inspection_table_extractor.extract_table(parsed_pdf)
        if inspection_table is not None:
            document.inspection_table = inspection_table
            document.inspection_items = list(inspection_table.items)
        return document

    def _inspection_scope_texts(self, report_doc: ReportDocument) -> list[str]:
        values: list[str] = []
        fields = list(report_doc.fields)
        if report_doc.third_page is not None:
            fields.extend(report_doc.third_page.fields)
        for field in fields:
            if field.name != "检验项目":
                continue
            raw_items = field.metadata.get("items")
            if isinstance(raw_items, list):
                values.extend(str(item) for item in raw_items if str(item or "").strip())
            elif field.value and field.value.strip():
                values.append(field.value.strip())
        return _dedupe(values)

    def _report_clause_numbers(self, report_items: list[InspectionItem]) -> set[str]:
        numbers: set[str] = set()
        for item in report_items:
            for value in (item.standard_clause, item.standard_requirement):
                numbers.update(CLAUSE_NUMBER_RE.findall(value or ""))
        return numbers

    def _included_main_requirement_clauses(
        self,
        ptr_doc: PTRDocument,
        scope_result: ScopeFilterResult,
    ) -> list[PTRClause]:
        included = set(scope_result.included_clause_ids)
        return [
            clause
            for clause in ptr_doc.clauses
            if clause.clause_id in included and clause.is_main_requirement
        ]

    def _scope_check_result(
        self,
        task_id: str,
        scope_result: ScopeFilterResult,
        included_clauses: list[PTRClause],
    ) -> CheckResult:
        return CheckResult(
            task_id=task_id,
            check_id="PTR_SCOPE",
            check_name="PTR 第 2 章核对范围过滤",
            status=CheckStatus.PASS,
            summary=f"纳入 {len(included_clauses)} 个 PTR 主要求条款。",
            findings=[],
            metadata={
                "included_clause_ids": list(scope_result.included_clause_ids),
                "excluded_clause_ids": list(scope_result.excluded_clause_ids),
                "decisions": [decision.model_dump(mode="json") for decision in scope_result.decisions],
            },
        )

    def _finding_check_result(
        self,
        task_id: str,
        *,
        check_id: str,
        check_name: str,
        findings: list[Finding],
        pass_summary: str,
        issue_summary: str,
    ) -> CheckResult:
        return CheckResult(
            task_id=task_id,
            check_id=check_id,
            check_name=check_name,
            status=_status_for_findings(findings),
            summary=pass_summary if not findings else issue_summary,
            findings=findings,
            evidence=[evidence for finding in findings for evidence in finding.evidence],
        )


def _status_for_findings(findings: list[Finding]) -> CheckStatus:
    if any(finding.severity == FindingSeverity.ERROR for finding in findings):
        return CheckStatus.FAIL
    if any(finding.severity == FindingSeverity.WARN for finding in findings):
        return CheckStatus.REVIEW
    return CheckStatus.PASS


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


__all__ = ["PTRCompareUseCase"]
