from pathlib import Path

from app.application.report_check_usecase import ReportCheckUseCase
from app.application.task_service import TaskService
from app.domain.codex_review import (
    CodexReviewConfidence,
    CodexReviewError,
    CodexReviewResult,
    CodexReviewStatus,
    CodexReviewVerdict,
    CodexSuggestedFinding,
)
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


class ConfigurableReportRuleRunner:
    def __init__(self, *, check_id: str, findings: list[Finding]) -> None:
        self.check_id = check_id
        self.findings = findings
        self.documents: list[ReportDocument] = []

    def run(self, document: ReportDocument, context=None) -> ReportRuleRunResult:
        self.documents.append(document)
        task_id = context.task_id
        findings = [finding.model_copy(update={"task_id": task_id}) for finding in self.findings]
        result = CheckResult(
            task_id=task_id,
            check_id=self.check_id,
            check_name=f"{self.check_id} test check",
            status=CheckStatus.FAIL if findings else CheckStatus.PASS,
            findings=findings,
            evidence=[evidence for finding in findings for evidence in finding.evidence],
        )
        return ReportRuleRunResult(
            task_id=task_id,
            results=[result],
            summary=CheckSummary.from_results([result]),
            findings=findings,
        )


class FakeReportAuditService:
    def __init__(
        self,
        *,
        verdict: CodexReviewVerdict = CodexReviewVerdict.CONFIRM,
        failed: bool = False,
        exc: Exception | None = None,
    ) -> None:
        self.verdict = verdict
        self.failed = failed
        self.exc = exc
        self.calls: list[dict[str, object]] = []

    def review(self, request, evidence_package) -> list[CodexReviewResult]:
        self.calls.append({"request": request, "evidence_package": evidence_package})
        if self.exc is not None:
            raise self.exc

        results: list[CodexReviewResult] = []
        for target in request.targets:
            if self.failed:
                results.append(
                    CodexReviewResult(
                        review_id=f"fake-report-review-{target.target_id}-failed",
                        request_id=request.request_id,
                        task_id=request.task_id,
                        target=target,
                        status=CodexReviewStatus.FAILED,
                        error=CodexReviewError(
                            code="FAKE_REPORT_AUDIT_FAILED",
                            message="Fake report audit failed.",
                        ),
                    )
                )
                continue

            suggested_finding = None
            if self.verdict is CodexReviewVerdict.ADD_FINDING:
                suggested_finding = CodexSuggestedFinding(
                    check_id=target.check_id,
                    severity="warn",
                    code="CODEX_SUGGESTED_REPORT_FINDING",
                    message="Codex 建议新增报告自检 finding。",
                    evidence_refs=[ref.ref_id for ref in target.evidence_refs[:1]],
                )

            results.append(
                CodexReviewResult(
                    review_id=f"fake-report-review-{target.target_id}",
                    request_id=request.request_id,
                    task_id=request.task_id,
                    target=target,
                    status=CodexReviewStatus.SUCCEEDED,
                    verdict=self.verdict,
                    confidence=CodexReviewConfidence.MEDIUM,
                    reasoning_summary="Fake report audit review.",
                    suggested_finding=suggested_finding,
                    evidence_refs=[ref.ref_id for ref in target.evidence_refs],
                )
            )
        return results


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


def test_report_check_codex_audit_disabled_keeps_reviews_empty_and_does_not_call_service(tmp_path: Path) -> None:
    finding = _report_finding(check_id="C02")
    audit_service = FakeReportAuditService()
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[finding]),
        codex_audit_service=audit_service,
        codex_audit_enabled=False,
    )

    result = task_service.get_result(status.task_id)
    assert result.check_results[0].findings[0].code == finding.code
    assert result.check_results[0].codex_reviews == []
    assert audit_service.calls == []


def test_report_check_codex_audit_confirm_review_is_attached_without_deleting_finding(tmp_path: Path) -> None:
    finding = _report_finding(check_id="C02")
    audit_service = FakeReportAuditService(verdict=CodexReviewVerdict.CONFIRM)
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[finding]),
        codex_audit_service=audit_service,
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    check_result = result.check_results[0]
    assert len(check_result.findings) == 1
    assert check_result.codex_reviews[0].verdict is CodexReviewVerdict.CONFIRM
    assert check_result.codex_reviews[0].target.target_type == "label_ocr"
    assert len(audit_service.calls) == 1


def test_report_check_codex_audit_refute_review_preserves_deterministic_finding(tmp_path: Path) -> None:
    finding = _report_finding(check_id="C02")
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[finding]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.REFUTE),
        codex_audit_enabled=True,
    )

    check_result = task_service.get_result(status.task_id).check_results[0]
    assert len(check_result.findings) == 1
    assert check_result.findings[0].code == finding.code
    assert check_result.codex_reviews[0].verdict is CodexReviewVerdict.REFUTE


def test_report_check_codex_audit_uncertain_review_is_attached(tmp_path: Path) -> None:
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[_report_finding(check_id="C02")]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.UNCERTAIN),
        codex_audit_enabled=True,
    )

    check_result = task_service.get_result(status.task_id).check_results[0]
    assert check_result.codex_reviews[0].verdict is CodexReviewVerdict.UNCERTAIN


def test_report_check_codex_audit_add_finding_does_not_append_to_deterministic_findings(tmp_path: Path) -> None:
    finding = _report_finding(check_id="C02")
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[finding]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.ADD_FINDING),
        codex_audit_enabled=True,
    )

    check_result = task_service.get_result(status.task_id).check_results[0]
    assert len(check_result.findings) == 1
    assert check_result.codex_reviews[0].verdict is CodexReviewVerdict.ADD_FINDING
    assert check_result.codex_reviews[0].suggested_finding is not None
    assert check_result.codex_reviews[0].suggested_finding.message == "Codex 建议新增报告自检 finding。"


def test_report_check_codex_audit_failed_review_does_not_break_usecase(tmp_path: Path) -> None:
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[_report_finding(check_id="C02")]),
        codex_audit_service=FakeReportAuditService(failed=True),
        codex_audit_enabled=True,
    )

    assert status.status == TaskState.COMPLETED
    review = task_service.get_result(status.task_id).check_results[0].codex_reviews[0]
    assert review.status is CodexReviewStatus.FAILED
    assert review.error is not None
    assert review.error.code == "FAKE_REPORT_AUDIT_FAILED"


def test_report_check_codex_audit_service_exception_is_converted_to_failed_review(tmp_path: Path) -> None:
    finding = _report_finding(check_id="C02")
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[finding]),
        codex_audit_service=FakeReportAuditService(exc=RuntimeError("audit boom")),
        codex_audit_enabled=True,
    )

    assert status.status == TaskState.COMPLETED
    check_result = task_service.get_result(status.task_id).check_results[0]
    assert len(check_result.findings) == 1
    assert check_result.codex_reviews[0].status is CodexReviewStatus.FAILED
    assert check_result.codex_reviews[0].error is not None
    assert check_result.codex_reviews[0].error.code == "CODEX_REPORT_AUDIT_SERVICE_FAILED"


def test_report_check_codex_audit_no_reviewable_findings_does_not_call_service(tmp_path: Path) -> None:
    audit_service = FakeReportAuditService()
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C08", findings=[_report_finding(check_id="C08")]),
        codex_audit_service=audit_service,
        codex_audit_enabled=True,
    )

    check_result = task_service.get_result(status.task_id).check_results[0]
    assert check_result.codex_reviews == []
    assert audit_service.calls == []


def test_report_check_codex_audit_c02_generates_label_ocr_target(tmp_path: Path) -> None:
    audit_service = FakeReportAuditService()
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[_report_finding(check_id="C02")]),
        codex_audit_service=audit_service,
        codex_audit_enabled=True,
    )

    review = task_service.get_result(status.task_id).check_results[0].codex_reviews[0]
    assert review.target.check_id == "C02"
    assert review.target.target_type == "label_ocr"
    assert audit_service.calls[0]["request"].targets[0].target_type == "label_ocr"


def test_report_check_codex_audit_c07_generates_inspection_item_target(tmp_path: Path) -> None:
    audit_service = FakeReportAuditService()
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C07", findings=[_report_finding(check_id="C07")]),
        codex_audit_service=audit_service,
        codex_audit_enabled=True,
    )

    review = task_service.get_result(status.task_id).check_results[0].codex_reviews[0]
    assert review.target.check_id == "C07"
    assert review.target.target_type == "inspection_item"
    assert audit_service.calls[0]["request"].targets[0].target_type == "inspection_item"


def _run_report_check(
    tmp_path: Path,
    *,
    rule_runner,
    codex_audit_service: FakeReportAuditService | None = None,
    codex_audit_enabled: bool = False,
) -> tuple[TaskService, object]:
    task_service = TaskService()
    usecase = ReportCheckUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=FakePdfParser(),
        field_extractor=FakeFieldExtractor(),
        inspection_table_extractor=FakeInspectionTableExtractor(),
        sample_description_extractor=FakeSampleDescriptionExtractor(),
        photo_label_extractor=FakePhotoLabelExtractor(),
        rule_runner=rule_runner,
        codex_audit_service=codex_audit_service,
        codex_audit_enabled=codex_audit_enabled,
    )
    status = usecase.run(file_name="report.pdf", content=b"%PDF-1.4 report", content_type="application/pdf")
    return task_service, status


def _report_finding(check_id: str) -> Finding:
    evidence = Evidence(
        id=f"ev-{check_id}",
        source_type=SourceType.REPORT,
        raw_text=f"{check_id} evidence",
        method=EvidenceMethod.PDF_TEXT,
    )
    metadata = {}
    if check_id in {"C02", "C03"}:
        metadata = {"field_name": "生产日期", "page_number": 3}
    elif check_id == "C07":
        metadata = {
            "item_no": "1",
            "normalized_item_no": "1",
            "result_values": ["不符合要求"],
            "actual_conclusion": "符合",
        }
    return Finding(
        id=f"task-placeholder-{check_id}-finding",
        task_id="task-placeholder",
        check_id=check_id,
        severity=FindingSeverity.ERROR,
        code=f"{check_id}_TEST_FINDING",
        message=f"{check_id} deterministic finding",
        expected="expected",
        actual="actual",
        evidence=[evidence],
        metadata=metadata,
    )
