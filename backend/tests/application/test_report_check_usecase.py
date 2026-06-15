from pathlib import Path

from app.application.report_check_usecase import ReportCheckUseCase
from app.application.task_service import TaskService
from app.domain.common import Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.pdf import ParsedPdf
from app.domain.report import InspectionItem, InspectionTable, ReportDocument
from app.domain.result import CheckResult, CheckStatus, CheckSummary
from app.domain.task import TaskState, TaskType
from app.infrastructure.storage.local_file_store import LocalFileStore
from app.rules.report.runner import ReportRuleRunResult


class FakePdfParser:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    def parse(self, file_path: Path) -> ParsedPdf:
        self.paths.append(file_path)
        return ParsedPdf(file_id="parsed-report", file_name=file_path.name, page_count=1)


class FakeFieldExtractor:
    def __init__(self) -> None:
        self.parsed: list[ParsedPdf] = []

    def extract(self, parsed_pdf: ParsedPdf) -> ReportDocument:
        self.parsed.append(parsed_pdf)
        return ReportDocument(parsed_pdf=parsed_pdf, diagnostics=["field extractor diagnostic"])


class FakeInspectionTableExtractor:
    def extract_table(self, parsed_pdf: ParsedPdf) -> InspectionTable:
        return InspectionTable(
            table_id="inspection-table",
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


class FakeSampleDescriptionExtractor:
    def extract_rows(self, parsed_pdf: ParsedPdf) -> list:
        return []

    def extract_components(self, parsed_pdf: ParsedPdf) -> list:
        return []


class FakePhotoLabelExtractor:
    def extract_captions(self, parsed_pdf: ParsedPdf) -> list:
        return []

    def extract_labels(self, parsed_pdf: ParsedPdf) -> list:
        return []


class FakeReportRuleRunner:
    def __init__(self) -> None:
        self.documents: list[ReportDocument] = []

    def run(self, document: ReportDocument, context=None) -> ReportRuleRunResult:
        self.documents.append(document)
        task_id = context.task_id
        evidence = Evidence(
            id=f"{task_id}-c01-evidence",
            source_type=SourceType.REPORT,
            raw_text="首页/第三页字段",
            method=EvidenceMethod.PDF_TEXT,
        )
        finding = Finding(
            id=f"{task_id}-c01-finding",
            task_id=task_id,
            check_id="C01",
            severity=FindingSeverity.ERROR,
            code="C01_FIELD_MISMATCH",
            message="首页与第三页字段不一致",
            evidence=[evidence],
        )
        result = CheckResult(
            task_id=task_id,
            check_id="C01",
            check_name="首页与第三页一致性",
            status=CheckStatus.FAIL,
            findings=[finding],
            evidence=[evidence],
        )
        return ReportRuleRunResult(
            task_id=task_id,
            results=[result],
            summary=CheckSummary.from_results([result]),
            findings=[finding],
        )


def test_report_check_usecase_saves_parses_extracts_runs_rules_and_completes_task(tmp_path: Path) -> None:
    task_service = TaskService()
    file_store = LocalFileStore(tmp_path)
    parser = FakePdfParser()
    field_extractor = FakeFieldExtractor()
    inspection_extractor = FakeInspectionTableExtractor()
    runner = FakeReportRuleRunner()

    usecase = ReportCheckUseCase(
        task_service=task_service,
        file_store=file_store,
        pdf_parser=parser,
        field_extractor=field_extractor,
        inspection_table_extractor=inspection_extractor,
        sample_description_extractor=FakeSampleDescriptionExtractor(),
        photo_label_extractor=FakePhotoLabelExtractor(),
        rule_runner=runner,
    )

    status = usecase.run(file_name="report.pdf", content=b"%PDF-1.4 report", content_type="application/pdf")

    assert status.task_type == TaskType.REPORT_CHECK
    assert status.status == TaskState.COMPLETED
    assert status.progress == 100
    assert status.result_ref == status.task_id
    assert status.input_files[0].file_name == "report.pdf"
    assert parser.paths and parser.paths[0].exists()
    assert field_extractor.parsed[0].file_id == "parsed-report"
    assert runner.documents[0].inspection_table is not None
    assert runner.documents[0].inspection_table.table_id == "inspection-table"
    assert runner.documents[0].inspection_items[0].standard_clause == "2.1"

    result = task_service.get_result(status.task_id)
    assert result.task_id == status.task_id
    assert result.task_type == TaskType.REPORT_CHECK
    assert result.summary.fail_count == 1
    assert result.check_results[0].check_id == "C01"
    assert result.input_files[0].file_name == "report.pdf"


class FailingParser:
    def parse(self, file_path: Path) -> ParsedPdf:
        raise ValueError("Invalid PDF file: report.pdf")


def test_report_check_usecase_converts_processing_errors_to_task_error(tmp_path: Path) -> None:
    task_service = TaskService()
    usecase = ReportCheckUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=FailingParser(),
        field_extractor=FakeFieldExtractor(),
        inspection_table_extractor=FakeInspectionTableExtractor(),
        sample_description_extractor=FakeSampleDescriptionExtractor(),
        photo_label_extractor=FakePhotoLabelExtractor(),
        rule_runner=FakeReportRuleRunner(),
    )

    status = usecase.run(file_name="report.pdf", content=b"broken", content_type="application/pdf")

    assert status.status == TaskState.ERROR
    assert status.error_message == "Invalid PDF file: report.pdf"
    assert task_service.get_task(status.task_id).error_message == "Invalid PDF file: report.pdf"
