from __future__ import annotations

from datetime import datetime, timezone
import re
import tempfile
from pathlib import Path
from typing import Any, Protocol

from app.application.ptr_codex_evidence_builder import PtrCodexEvidenceBuilder
from app.application.task_service import TaskService
from app.domain.codex_review import CodexReviewError, CodexReviewRequest, CodexReviewResult, CodexReviewStatus
from app.domain.evidence_package import EvidencePackage
from app.domain.finding import Finding, FindingSeverity
from app.domain.pdf import ParsedPdf
from app.domain.ptr import PTRClause, PTRDocument
from app.domain.report import InspectionItem, InspectionTable, ReportDocument
from app.domain.result import CheckResult, CheckStatus
from app.domain.table import CanonicalTable
from app.domain.task import TaskStatus, TaskType
from app.infrastructure.pdf.pymupdf_parser import PyMuPDFParser
from app.infrastructure.ptr.ptr_extractor import PTRExtractor
from app.infrastructure.report.field_extractor import FieldExtractor
from app.infrastructure.report.inspection_table_extractor import InspectionTableExtractor
from app.infrastructure.report.parameter_table_extractor import ReportParameterTableExtractor
from app.infrastructure.storage.local_file_store import LocalFileStore
from app.rules.ptr.clause_text_compare import compare_clause_texts
from app.rules.ptr.parameter_compare import compare_parameter_tables
from app.rules.ptr.scope_filter import ScopeFilterResult, filter_ptr_scope
from app.rules.ptr.table_candidate_selector import TableCandidateSelection, select_report_table_candidate
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


class ReportParameterTableExtractorProtocol(Protocol):
    def extract_tables(self, parsed_pdf: ParsedPdf) -> list[CanonicalTable]:
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


class ParameterTableCompare(Protocol):
    def __call__(
        self,
        expected_table: CanonicalTable,
        actual_table: CanonicalTable | None,
        *,
        task_id: str,
        clause_number: str = "",
        table_number: str = "",
    ) -> list[Finding]:
        ...


class TableCandidateSelector(Protocol):
    def __call__(
        self,
        expected_table: CanonicalTable,
        report_tables: list[CanonicalTable],
        *,
        table_number: str,
        task_id: str,
        clause_number: str = "",
    ) -> TableCandidateSelection:
        ...


class CodexAuditServiceProtocol(Protocol):
    def review(
        self,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
    ) -> list[CodexReviewResult]:
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
        parameter_table_extractor: ReportParameterTableExtractorProtocol | None = None,
        scope_filter: ScopeFilter = filter_ptr_scope,
        clause_text_compare: ClauseTextCompare = compare_clause_texts,
        table_reference_compare: TableReferenceCompare = check_table_references,
        table_candidate_selector: TableCandidateSelector = select_report_table_candidate,
        parameter_compare: ParameterTableCompare = compare_parameter_tables,
        codex_audit_service: CodexAuditServiceProtocol | None = None,
        codex_audit_enabled: bool = False,
        ptr_codex_evidence_builder: PtrCodexEvidenceBuilder | None = None,
    ) -> None:
        self.task_service = task_service
        self.file_store = file_store or LocalFileStore(Path(tempfile.gettempdir()) / "report-checker-runtime")
        self.pdf_parser = pdf_parser or PyMuPDFParser()
        self.ptr_extractor = ptr_extractor or PTRExtractor()
        self.report_extractor = report_extractor or FieldExtractor()
        self.inspection_table_extractor = inspection_table_extractor or InspectionTableExtractor()
        self.parameter_table_extractor = parameter_table_extractor or ReportParameterTableExtractor()
        self.scope_filter = scope_filter
        self.clause_text_compare = clause_text_compare
        self.table_reference_compare = table_reference_compare
        self.table_candidate_selector = table_candidate_selector
        self.parameter_compare = parameter_compare
        self.codex_audit_service = codex_audit_service
        self.codex_audit_enabled = codex_audit_enabled
        self.ptr_codex_evidence_builder = ptr_codex_evidence_builder or PtrCodexEvidenceBuilder()

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
            table_findings.extend(
                self._parameter_table_findings(
                    ptr_doc=ptr_doc,
                    report_doc=report_doc,
                    clauses=included_clauses,
                    task_id=task.task_id,
                )
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
                    check_name="PTR 表格引用和参数一致性",
                    findings=table_findings,
                    pass_summary="PTR 表格引用和参数一致",
                    issue_summary="PTR 表格引用或参数存在差异或需复核",
                ),
            ]
            self._attach_codex_reviews(
                task_id=task.task_id,
                ptr_doc=ptr_doc,
                report_doc=report_doc,
                check_results=check_results,
            )
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
        self._attach_report_canonical_tables(document, parsed_pdf)
        return document

    def _attach_report_canonical_tables(self, document: ReportDocument, parsed_pdf: ParsedPdf) -> None:
        extracted_tables = self.parameter_table_extractor.extract_tables(parsed_pdf)
        existing_tables = self._report_canonical_tables(document)
        tables = _dedupe_tables([*existing_tables, *extracted_tables])
        if tables:
            document.metadata["canonical_tables"] = tables

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

    def _parameter_table_findings(
        self,
        *,
        ptr_doc: PTRDocument,
        report_doc: ReportDocument,
        clauses: list[PTRClause],
        task_id: str,
    ) -> list[Finding]:
        report_tables = self._report_canonical_tables(report_doc)
        findings: list[Finding] = []
        for clause in clauses:
            for table_number in self._table_reference_numbers(clause):
                ptr_candidates = ptr_doc.get_tables_by_number(table_number)
                if len(ptr_candidates) != 1:
                    continue
                expected_table = ptr_candidates[0].canonical_table
                if expected_table is None:
                    continue

                selection = self.table_candidate_selector(
                    expected_table,
                    report_tables,
                    table_number=table_number,
                    task_id=task_id,
                    clause_number=str(clause.number),
                )
                if selection.findings:
                    findings.extend(selection.findings)
                    continue
                findings.extend(
                    self.parameter_compare(
                        expected_table,
                        selection.selected_table,
                        task_id=task_id,
                        clause_number=str(clause.number),
                        table_number=table_number,
                    )
                )
        return findings

    def _table_reference_numbers(self, clause: PTRClause) -> list[str]:
        numbers = [reference.table_number for reference in clause.table_references]
        numbers.extend(clause.table_refs)
        return _dedupe(numbers)

    def _report_canonical_tables(self, report_doc: ReportDocument) -> list[CanonicalTable]:
        tables: list[CanonicalTable] = []
        for key in ("canonical_tables", "parameter_tables", "ptr_compare_tables"):
            tables.extend(_coerce_canonical_tables(report_doc.metadata.get(key)))
        return tables

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

    def _attach_codex_reviews(
        self,
        *,
        task_id: str,
        ptr_doc: PTRDocument,
        report_doc: ReportDocument,
        check_results: list[CheckResult],
    ) -> None:
        if not self.codex_audit_enabled or self.codex_audit_service is None:
            return

        bundle = self.ptr_codex_evidence_builder.build(
            task_id=task_id,
            task_type=TaskType.PTR_COMPARE.value,
            ptr_doc=ptr_doc,
            report_doc=report_doc,
            check_results=check_results,
        )
        if bundle is None:
            return

        try:
            reviews = self.codex_audit_service.review(bundle.request, bundle.evidence_package)
        except Exception as exc:
            reviews = _failed_codex_reviews_for_request(bundle.request, exc)

        _attach_reviews_to_check_results(check_results, reviews)


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


def _coerce_canonical_tables(value: Any) -> list[CanonicalTable]:
    if value is None:
        return []
    if isinstance(value, CanonicalTable):
        return [value]
    if isinstance(value, dict):
        if "table_id" in value:
            return [CanonicalTable.model_validate(value)]
        return [table for item in value.values() for table in _coerce_canonical_tables(item)]
    if isinstance(value, (list, tuple)):
        return [table for item in value for table in _coerce_canonical_tables(item)]
    canonical_table = getattr(value, "canonical_table", None)
    if isinstance(canonical_table, CanonicalTable):
        return [canonical_table]
    return []


def _dedupe_tables(tables: list[CanonicalTable]) -> list[CanonicalTable]:
    seen: set[str] = set()
    result: list[CanonicalTable] = []
    for table in tables:
        key = table.table_id or table.source_table_id or f"{table.table_number}:{table.caption}"
        if key in seen:
            continue
        seen.add(key)
        result.append(table)
    return result


def _attach_reviews_to_check_results(
    check_results: list[CheckResult],
    reviews: list[CodexReviewResult],
) -> None:
    if not reviews:
        return
    result_by_check_id = {result.check_id: result for result in check_results}
    fallback = check_results[0] if check_results else None
    for review in reviews:
        check_id = review.target.check_id
        target_result = result_by_check_id.get(check_id or "") or fallback
        if target_result is None:
            continue
        target_result.codex_reviews.append(review)


def _failed_codex_reviews_for_request(
    request: CodexReviewRequest,
    exc: Exception,
) -> list[CodexReviewResult]:
    now = datetime.now(timezone.utc)
    error = CodexReviewError(
        code="CODEX_PTR_AUDIT_SERVICE_FAILED",
        message="PTR Codex audit service failed inside PTRCompareUseCase.",
        detail=str(exc),
        retryable=False,
    )
    return [
        CodexReviewResult(
            review_id=f"ptr-codex-audit:{request.request_id}:{target.target_id}:failed",
            request_id=request.request_id,
            task_id=request.task_id,
            target=target,
            status=CodexReviewStatus.FAILED,
            error=error,
            created_at=now,
            completed_at=now,
            metadata={"source": "ptr_compare_usecase"},
        )
        for target in request.targets
    ]


__all__ = ["PTRCompareUseCase"]
