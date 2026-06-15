from pathlib import Path

from app.application.ptr_compare_usecase import PTRCompareUseCase
from app.application.task_service import TaskService
from app.domain.common import Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.pdf import ParsedPdf
from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument
from app.domain.report import InspectionItem, InspectionTable, ReportDocument, ReportField, ThirdPageInfo
from app.domain.result import CheckStatus
from app.domain.task import TaskState, TaskType
from app.infrastructure.storage.local_file_store import LocalFileStore
from app.rules.ptr.scope_filter import ScopeDecision, ScopeFilterResult


class FakePdfParser:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    def parse(self, file_path: Path) -> ParsedPdf:
        self.paths.append(file_path)
        return ParsedPdf(file_id=file_path.stem, file_name=file_path.name, page_count=1)


class FakePTRExtractor:
    def __init__(self) -> None:
        self.parsed: list[ParsedPdf] = []

    def extract(self, parsed_pdf: ParsedPdf) -> PTRDocument:
        self.parsed.append(parsed_pdf)
        return PTRDocument(
            parsed_pdf=parsed_pdf,
            clauses=[
                PTRClause(
                    clause_id="ptr-2.1",
                    number=PTRClauseNumber.from_string("2.1"),
                    title="外观",
                    body_text="外观应平整",
                ),
                PTRClause(
                    clause_id="ptr-2.2",
                    number=PTRClauseNumber.from_string("2.2"),
                    title="尺寸",
                    body_text="尺寸应符合要求",
                ),
            ],
        )


class FakeReportFieldExtractor:
    def __init__(self) -> None:
        self.parsed: list[ParsedPdf] = []

    def extract(self, parsed_pdf: ParsedPdf) -> ReportDocument:
        self.parsed.append(parsed_pdf)
        scope_field = ReportField(name="检验项目", value="2.1", metadata={"items": ["2.1"]})
        return ReportDocument(
            parsed_pdf=parsed_pdf,
            third_page=ThirdPageInfo(fields=[scope_field]),
            fields=[scope_field],
        )


class FakeInspectionTableExtractor:
    def extract_table(self, parsed_pdf: ParsedPdf) -> InspectionTable:
        return InspectionTable(
            table_id="report-inspection-table",
            items=[
                InspectionItem(
                    sequence_raw="1",
                    sequence=1,
                    standard_clause="2.1",
                    standard_requirement="外观应平整",
                    source_page=4,
                )
            ],
        )


class TrackingScopeFilter:
    def __init__(self) -> None:
        self.calls: list[tuple[PTRDocument, list[str], set[str]]] = []

    def __call__(
        self,
        ptr_doc: PTRDocument,
        inspection_scope_texts: list[str],
        *,
        report_clause_numbers: set[str] | None = None,
    ) -> ScopeFilterResult:
        numbers = report_clause_numbers or set()
        self.calls.append((ptr_doc, inspection_scope_texts, numbers))
        return ScopeFilterResult(
            included_clause_ids=["ptr-2.1"],
            excluded_clause_ids=["ptr-2.2"],
            decisions=[
                ScopeDecision(
                    clause_id="ptr-2.1",
                    clause_number="2.1",
                    included=True,
                    reason="declared_scope",
                ),
                ScopeDecision(
                    clause_id="ptr-2.2",
                    clause_number="2.2",
                    included=False,
                    reason="outside_declared_scope",
                ),
            ],
        )


class TrackingClauseCompare:
    def __init__(self) -> None:
        self.calls: list[tuple[list[PTRClause], list[InspectionItem], str]] = []

    def __call__(self, ptr_clauses: list[PTRClause], report_items: list[InspectionItem], *, task_id: str) -> list[Finding]:
        self.calls.append((ptr_clauses, report_items, task_id))
        evidence = Evidence(
            id=f"{task_id}-ptr-clause-evidence",
            source_type=SourceType.PTR,
            raw_text="外观应平整",
            method=EvidenceMethod.PDF_TEXT,
        )
        return [
            Finding(
                id=f"{task_id}-ptr-clause-warning",
                task_id=task_id,
                check_id="PTR_CLAUSE",
                severity=FindingSeverity.WARN,
                code="PTR_CLAUSE_REVIEW",
                message="条款需要人工复核",
                evidence=[evidence],
            )
        ]


class TrackingTableCompare:
    def __init__(self) -> None:
        self.calls: list[tuple[PTRDocument, list[PTRClause], str]] = []

    def __call__(self, ptr_doc: PTRDocument, *, clauses: list[PTRClause] | None = None, task_id: str) -> list[Finding]:
        self.calls.append((ptr_doc, clauses or [], task_id))
        return []


def test_ptr_compare_usecase_saves_parses_filters_compares_and_completes_task(tmp_path: Path) -> None:
    task_service = TaskService()
    parser = FakePdfParser()
    ptr_extractor = FakePTRExtractor()
    report_extractor = FakeReportFieldExtractor()
    scope_filter = TrackingScopeFilter()
    clause_compare = TrackingClauseCompare()
    table_compare = TrackingTableCompare()

    usecase = PTRCompareUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=parser,
        ptr_extractor=ptr_extractor,
        report_extractor=report_extractor,
        inspection_table_extractor=FakeInspectionTableExtractor(),
        scope_filter=scope_filter,
        clause_text_compare=clause_compare,
        table_reference_compare=table_compare,
    )

    status = usecase.run(
        ptr_file_name="ptr.pdf",
        ptr_content=b"%PDF-1.4 ptr",
        report_file_name="report.pdf",
        report_content=b"%PDF-1.4 report",
        content_type="application/pdf",
    )

    assert status.task_type == TaskType.PTR_COMPARE
    assert status.status == TaskState.COMPLETED
    assert status.progress == 100
    assert [path.name for path in parser.paths] == ["ptr.pdf", "report.pdf"]
    assert ptr_extractor.parsed[0].file_name == "ptr.pdf"
    assert report_extractor.parsed[0].file_name == "report.pdf"
    assert scope_filter.calls[0][1] == ["2.1"]
    assert scope_filter.calls[0][2] == {"2.1"}
    assert [str(clause.number) for clause in clause_compare.calls[0][0]] == ["2.1"]
    assert [str(clause.number) for clause in table_compare.calls[0][1]] == ["2.1"]

    result = task_service.get_result(status.task_id)
    assert result.task_id == status.task_id
    assert result.task_type == TaskType.PTR_COMPARE
    assert result.summary.review_count == 1
    assert result.check_results[0].check_id == "PTR_SCOPE"
    assert result.check_results[1].check_id == "PTR_CLAUSE"
    assert result.check_results[1].status == CheckStatus.REVIEW
    assert {file.file_name for file in result.input_files} == {"ptr.pdf", "report.pdf"}


class FailingParser:
    def parse(self, file_path: Path) -> ParsedPdf:
        raise ValueError(f"Invalid PDF file: {file_path.name}")


def test_ptr_compare_usecase_converts_processing_errors_to_task_error(tmp_path: Path) -> None:
    task_service = TaskService()
    usecase = PTRCompareUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=FailingParser(),
        ptr_extractor=FakePTRExtractor(),
        report_extractor=FakeReportFieldExtractor(),
        inspection_table_extractor=FakeInspectionTableExtractor(),
        scope_filter=TrackingScopeFilter(),
        clause_text_compare=TrackingClauseCompare(),
        table_reference_compare=TrackingTableCompare(),
    )

    status = usecase.run(
        ptr_file_name="ptr.pdf",
        ptr_content=b"broken",
        report_file_name="report.pdf",
        report_content=b"broken",
        content_type="application/pdf",
    )

    assert status.status == TaskState.ERROR
    assert status.error_message == "Invalid PDF file: ptr.pdf"
    assert task_service.get_task(status.task_id).error_message == "Invalid PDF file: ptr.pdf"
