from pathlib import Path

import pytest

from app.application.report_codex_evidence_builder import ReportCodexEvidenceBuilder
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


class MultipleReportRuleRunner:
    def __init__(self, results: list[tuple[str, list[Finding]]]) -> None:
        self.results = results
        self.documents: list[ReportDocument] = []

    def run(self, document: ReportDocument, context=None) -> ReportRuleRunResult:
        self.documents.append(document)
        task_id = context.task_id
        check_results = []
        findings_out: list[Finding] = []
        for check_id, findings in self.results:
            task_findings = [finding.model_copy(update={"task_id": task_id}) for finding in findings]
            findings_out.extend(task_findings)
            check_results.append(
                CheckResult(
                    task_id=task_id,
                    check_id=check_id,
                    check_name=f"{check_id} test check",
                    status=CheckStatus.FAIL if task_findings else CheckStatus.PASS,
                    findings=task_findings,
                    evidence=[evidence for finding in task_findings for evidence in finding.evidence],
                )
            )
        return ReportRuleRunResult(
            task_id=task_id,
            results=check_results,
            summary=CheckSummary.from_results(check_results),
            findings=findings_out,
        )


class ProgressAwareRuleRunner:
    def __init__(self) -> None:
        self.documents: list[ReportDocument] = []

    def run(self, document: ReportDocument, context=None) -> ReportRuleRunResult:
        self.documents.append(document)
        task_id = context.task_id
        results = [
            CheckResult(
                task_id=task_id,
                check_id="C01",
                check_name="首页与第三页一致性",
                status=CheckStatus.PASS,
            ),
            CheckResult(
                task_id=task_id,
                check_id="C03",
                check_name="生产日期格式一致性",
                status=CheckStatus.SKIP,
                summary="缺少可核对生产日期",
            ),
            CheckResult(
                task_id=task_id,
                check_id="C07",
                check_name="单项结论逻辑",
                status=CheckStatus.PASS,
            ),
        ]
        for result in results:
            context.on_check_start(result.check_id, result.check_name)
            context.on_check_complete(result)
        return ReportRuleRunResult(
            task_id=task_id,
            results=results,
            summary=CheckSummary.from_results(results),
            findings=[],
        )


class FakeReportAuditService:
    def __init__(
        self,
        *,
        verdict: CodexReviewVerdict = CodexReviewVerdict.CONFIRM,
        review_metadata: dict | None = None,
        failed: bool = False,
        exc: Exception | None = None,
    ) -> None:
        self.verdict = verdict
        self.review_metadata = review_metadata or {}
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
                    metadata=self.review_metadata,
                )
            )
        return results


class PartialReportAuditService(FakeReportAuditService):
    def review(self, request, evidence_package) -> list[CodexReviewResult]:
        reviews = super().review(request, evidence_package)
        return reviews[:1]


class TargetMetadataReportAuditService(FakeReportAuditService):
    def __init__(
        self,
        *,
        target_metadata: dict,
        verdict: CodexReviewVerdict,
        review_metadata: dict | None = None,
    ) -> None:
        super().__init__(verdict=verdict, review_metadata=review_metadata)
        self.target_metadata = target_metadata

    def review(self, request, evidence_package) -> list[CodexReviewResult]:
        request = request.model_copy(
            update={
                "targets": [
                    target.model_copy(update={"metadata": {**target.metadata, **self.target_metadata}})
                    for target in request.targets
                ]
            }
        )
        return super().review(request, evidence_package)


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
        codex_audit_service=FakeReportAuditService(),
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
    profile = result.metadata["performance_profile"]
    stage_names = [stage["name"] for stage in profile["stages"]]
    assert "parse_pdf" in stage_names
    assert "build_report_document" in stage_names
    assert "run_rules" in stage_names
    assert "codex_audit_total" in stage_names
    assert "finalize_codex_audit" in stage_names
    assert "complete_task" in stage_names
    assert "performance_profile" in result.metadata["codex_audit"]


def test_report_check_usecase_submit_creates_processing_task_without_parsing(tmp_path: Path) -> None:
    task_service = TaskService()
    file_store = LocalFileStore(tmp_path)
    parser = FakePdfParser()

    usecase = ReportCheckUseCase(
        task_service=task_service,
        file_store=file_store,
        pdf_parser=parser,
        field_extractor=FakeFieldExtractor(),
        inspection_table_extractor=FakeInspectionTableExtractor(),
        sample_description_extractor=FakeSampleDescriptionExtractor(),
        photo_label_extractor=FakePhotoLabelExtractor(),
        rule_runner=FakeReportRuleRunner(),
        codex_audit_service=FakeReportAuditService(),
    )

    status = usecase.submit(file_name="report.pdf", content=b"%PDF-1.4 report", content_type="application/pdf")

    assert status.status == TaskState.PROCESSING
    assert status.progress == 1
    assert status.current_step == "queued report check"
    assert status.input_files[0].file_name == "report.pdf"
    assert file_store.get_upload_path(task_id=status.task_id, file_name="report.pdf").exists()
    assert parser.paths == []


def test_report_check_usecase_process_submitted_task_updates_progress_and_completes(tmp_path: Path) -> None:
    task_service = TaskService()
    file_store = LocalFileStore(tmp_path)
    parser = FakePdfParser()
    field_extractor = FakeFieldExtractor()
    runner = FakeReportRuleRunner()

    usecase = ReportCheckUseCase(
        task_service=task_service,
        file_store=file_store,
        pdf_parser=parser,
        field_extractor=field_extractor,
        inspection_table_extractor=FakeInspectionTableExtractor(),
        sample_description_extractor=FakeSampleDescriptionExtractor(),
        photo_label_extractor=FakePhotoLabelExtractor(),
        rule_runner=runner,
        codex_audit_service=FakeReportAuditService(),
    )
    submitted = usecase.submit(file_name="report.pdf", content=b"%PDF-1.4 report", content_type="application/pdf")

    status = usecase.process_task(submitted.task_id)

    assert status.status == TaskState.COMPLETED
    assert status.progress == 100
    assert status.result_ref == submitted.task_id
    assert parser.paths and parser.paths[0].name == "report.pdf"
    assert field_extractor.parsed[0].file_id == "parsed-report"
    assert runner.documents[0].inspection_table is not None

    result = task_service.get_result(submitted.task_id)
    assert result.task_id == submitted.task_id
    assert result.summary.fail_count == 1
    assert result.check_results[0].check_id == "C01"


def test_report_check_usecase_records_progress_details_for_rule_checklist(tmp_path: Path) -> None:
    task_service = TaskService()
    usecase = ReportCheckUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=FakePdfParser(),
        field_extractor=FakeFieldExtractor(),
        inspection_table_extractor=FakeInspectionTableExtractor(),
        sample_description_extractor=FakeSampleDescriptionExtractor(),
        photo_label_extractor=FakePhotoLabelExtractor(),
        rule_runner=ProgressAwareRuleRunner(),
        codex_audit_service=FakeReportAuditService(),
    )

    status = usecase.run(file_name="report.pdf", content=b"%PDF-1.4 report", content_type="application/pdf")

    assert status.status == TaskState.COMPLETED
    assert status.progress_details is not None
    assert status.progress_details.phase == "completed"
    checks = {item.check_id: item for item in status.progress_details.checks}
    assert checks["C01"].status == "passed"
    assert checks["C03"].status == "skipped"
    assert checks["C07"].status == "passed"
    assert status.metadata["progress_details"]["checks"][2]["check_id"] == "C03"
    assert status.metadata["progress_details"]["checks"][2]["status"] == "skipped"


def test_report_check_usecase_records_codex_audit_progress_totals(tmp_path: Path) -> None:
    audit_service = FakeReportAuditService()
    findings = [_report_finding(check_id="C04", id_suffix=f"c04-{index}") for index in range(3)]

    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C04", findings=findings),
        codex_audit_service=audit_service,
        report_codex_evidence_builder=ReportCodexEvidenceBuilder(max_targets_per_batch=2),
    )

    assert status.status == TaskState.COMPLETED
    assert status.progress_details is not None
    codex_progress = status.progress_details.codex_audit
    assert codex_progress is not None
    assert codex_progress.status == "completed"
    assert codex_progress.total_reviews_count == 3
    assert codex_progress.completed_reviews_count == 3
    assert codex_progress.total_batches_count == 2
    assert codex_progress.completed_batches_count == 2
    assert codex_progress.max_targets_per_batch == 2
    result = task_service.get_result(status.task_id)
    assert result.metadata["progress_details"]["codex_audit"]["completed_reviews_count"] == 3


def test_report_check_usecase_error_preserves_last_progress_details(tmp_path: Path) -> None:
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
    assert status.progress_details is not None
    assert status.progress_details.phase == "error"
    assert status.progress_details.error_code == "PROCESSING_ERROR"
    assert "/Users/" not in str(status.progress_details.model_dump())


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


def test_report_check_without_reviewable_findings_audits_check_summary_target(tmp_path: Path) -> None:
    finding = _report_finding(check_id="C08")
    audit_service = FakeReportAuditService()
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C08", findings=[finding]),
        codex_audit_service=audit_service,
    )

    result = task_service.get_result(status.task_id)
    assert result.check_results[0].findings[0].code == finding.code
    assert result.check_results[0].codex_reviews[0].target.target_type == "check_result"
    assert audit_service.calls[0]["request"].targets[0].check_id == "C08"


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
    assert check_result.findings[0].metadata["final_status"] == "confirmed"
    assert result.summary.candidate_errors_count == 1
    assert result.summary.confirmed_errors_count == 1
    assert result.summary.refuted_findings_count == 0
    assert result.summary.manual_review_required_count == 0
    assert result.summary.audit_scope == "full"
    assert result.summary.full_audit is True
    assert result.summary.final_audit_status == "failed"
    assert result.metadata["codex_audit"]["audit_scope"] == "full"
    assert result.metadata["codex_audit"]["full_audit"] is True
    assert result.metadata["codex_audit"]["final_audit_status"] == "failed"


def test_report_check_codex_audit_refute_review_preserves_deterministic_finding(tmp_path: Path) -> None:
    finding = _report_finding(check_id="C02")
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[finding]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.REFUTE),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    check_result = result.check_results[0]
    assert len(check_result.findings) == 1
    assert check_result.findings[0].code == finding.code
    assert check_result.codex_reviews[0].verdict is CodexReviewVerdict.REFUTE
    assert check_result.findings[0].metadata["final_status"] == "refuted"
    assert result.summary.candidate_errors_count == 1
    assert result.summary.confirmed_errors_count == 0
    assert result.summary.refuted_findings_count == 1
    assert result.summary.final_audit_status == "passed"
    assert result.metadata["codex_audit"]["final_audit_status"] == "passed"


def test_report_check_codex_audit_uncertain_review_is_attached(tmp_path: Path) -> None:
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[_report_finding(check_id="C02")]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.UNCERTAIN),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    check_result = result.check_results[0]
    assert check_result.codex_reviews[0].verdict is CodexReviewVerdict.UNCERTAIN
    assert check_result.findings[0].metadata["final_status"] == "manual_review_required"
    assert result.summary.confirmed_errors_count == 0
    assert result.summary.manual_review_required_count == 1
    assert result.summary.final_audit_status == "needs_manual_review"
    assert result.metadata["codex_audit"]["final_audit_status"] == "needs_manual_review"


def test_report_check_confirm_for_unverifiable_c04_label_content_becomes_manual_review(tmp_path: Path) -> None:
    finding = _report_finding(
        check_id="C04",
        metadata={
            "component_id": "component-1",
            "label_id": "label-1",
            "evidence_can_verify_label_content": False,
        },
    )
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C04", findings=[finding]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.CONFIRM),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["codex_verdict"] == "confirm"
    assert finding_result.metadata["final_status"] == "manual_review_required"
    assert finding_result.metadata["codex_finalization_diagnostic"] == "CODEX_CONFIRMED_UNVERIFIABLE_LABEL_CONTENT"
    assert result.summary.confirmed_errors_count == 0
    assert result.summary.manual_review_required_count == 1


def test_report_check_confirm_for_c04_label_not_found_with_matching_caption_becomes_manual_review(
    tmp_path: Path,
) -> None:
    finding = _report_finding(
        check_id="C04",
        metadata={
            "component_id": "sample-row-3",
            "evidence_has_matching_label_caption": True,
            "evidence_has_matched_label_ocr": False,
        },
    ).model_copy(
        update={
            "code": "SAMPLE_COMPONENT_LABEL_NOT_FOUND",
            "severity": FindingSeverity.WARN,
            "message": "未找到与样品描述部件匹配的中文标签 OCR",
        }
    )
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C04", findings=[finding]),
        codex_audit_service=TargetMetadataReportAuditService(
            verdict=CodexReviewVerdict.CONFIRM,
            target_metadata={"evidence_can_verify_label_content": True},
        ),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["codex_verdict"] == "confirm"
    assert finding_result.metadata["final_status"] == "manual_review_required"
    assert (
        finding_result.metadata["codex_finalization_diagnostic"]
        == "CODEX_CONFIRMED_LABEL_MISSING_BUT_CAPTION_EXISTS"
    )
    assert result.summary.confirmed_findings_count == 0
    assert result.summary.manual_review_required_count == 1


def test_report_check_refute_for_c04_matched_fields_marks_candidate_refuted(tmp_path: Path) -> None:
    finding = _report_finding(
        check_id="C04",
        metadata={
            "component_id": "component-1",
            "field_name": "序列号批号",
            "matched_label_fields": {"序列号批号": {"value": "LOT-1"}},
            "label_field_comparison": {
                "field_name": "序列号批号",
                "sample_value": "LOT-1",
                "matched_label_value": "LOT-1",
                "comparison_hint": "field_matches_sample_description",
            },
            "evidence_can_verify_label_content": True,
        },
    ).model_copy(update={"code": "SAMPLE_FIELD_MISSING_IN_LABEL"})
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C04", findings=[finding]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.REFUTE),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["final_status"] == "refuted"
    assert result.summary.refuted_findings_count == 1
    assert result.summary.confirmed_errors_count == 0


def test_report_check_c04_visual_observed_fields_match_refutes_candidate(tmp_path: Path) -> None:
    finding = _report_finding(
        check_id="C04",
        metadata={
            "component_id": "component-1",
            "field_name": "序列号批号",
            "label_image_ref": "items/task-1-C04-main-label-page.png",
            "evidence_has_visual_label_input": True,
            "evidence_can_verify_label_content": True,
        },
    ).model_copy(update={"code": "SAMPLE_FIELD_MISSING_IN_LABEL"})
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C04", findings=[finding]),
        codex_audit_service=TargetMetadataReportAuditService(
            verdict=CodexReviewVerdict.REFUTE,
            target_metadata={"evidence_can_verify_label_content": True},
            review_metadata={
                "observed_label_fields": {"component_name": "输注泵", "batch_or_serial": "LOT-1"},
                "field_comparisons": [
                    {
                        "field_name": "序列号/批号",
                        "expected_value": "LOT-1",
                        "observed_value": "LOT-1",
                        "status": "match",
                        "evidence_ref": "label_image:finding-1",
                        "reasoning": "视觉读取字段与样品描述一致。",
                    }
                ],
                "visual_evidence_quality": "clear",
            },
        ),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["final_status"] == "refuted"
    assert finding_result.metadata["codex_observed_label_fields"]["batch_or_serial"] == "LOT-1"
    assert finding_result.metadata["codex_field_comparisons"][0]["status"] == "match"
    assert finding_result.metadata["codex_visual_evidence_quality"] == "clear"
    assert result.summary.refuted_findings_count == 1
    assert result.summary.confirmed_errors_count == 0


def test_report_check_c04_visual_missing_field_can_be_confirmed(tmp_path: Path) -> None:
    finding = _report_finding(
        check_id="C04",
        metadata={
            "component_id": "component-1",
            "field_name": "序列号批号",
            "label_image_ref": "items/task-1-C04-main-label-page.png",
            "evidence_has_visual_label_input": True,
            "evidence_can_verify_label_content": True,
        },
    ).model_copy(update={"code": "SAMPLE_FIELD_MISSING_IN_LABEL"})
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C04", findings=[finding]),
        codex_audit_service=TargetMetadataReportAuditService(
            verdict=CodexReviewVerdict.CONFIRM,
            target_metadata={"evidence_can_verify_label_content": True},
            review_metadata={
                "observed_label_fields": {"component_name": "输注泵", "batch_or_serial": None},
                "field_comparisons": [
                    {
                        "field_name": "序列号/批号",
                        "expected_value": "LOT-1",
                        "observed_value": None,
                        "status": "missing",
                        "evidence_ref": "label_image:finding-1",
                        "reasoning": "视觉证据可读，但没有看到序列号/批号。",
                    }
                ],
                "visual_evidence_quality": "clear",
            },
        ),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["final_status"] == "confirmed"
    assert finding_result.metadata["codex_observed_label_fields"]["batch_or_serial"] is None
    assert finding_result.metadata["codex_field_comparisons"][0]["status"] == "missing"
    assert finding_result.metadata["codex_visual_evidence_quality"] == "clear"
    assert result.summary.confirmed_errors_count == 1


def test_report_check_c04_unreadable_visual_evidence_stays_manual_review(tmp_path: Path) -> None:
    finding = _report_finding(
        check_id="C04",
        metadata={
            "component_id": "component-1",
            "field_name": "序列号批号",
            "label_image_ref": "items/task-1-C04-main-label-page.png",
            "evidence_has_visual_label_input": True,
            "evidence_can_verify_label_content": True,
        },
    ).model_copy(update={"code": "SAMPLE_FIELD_MISSING_IN_LABEL"})
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C04", findings=[finding]),
        codex_audit_service=TargetMetadataReportAuditService(
            verdict=CodexReviewVerdict.CONFIRM,
            target_metadata={"evidence_can_verify_label_content": True},
            review_metadata={
                "observed_label_fields": {},
                "field_comparisons": [],
                "visual_evidence_quality": "unreadable",
            },
        ),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["final_status"] == "manual_review_required"
    assert finding_result.metadata["codex_finalization_diagnostic"] == "CODEX_CONFIRMED_UNREADABLE_LABEL_IMAGE"
    assert finding_result.metadata["codex_visual_evidence_quality"] == "unreadable"
    assert result.summary.confirmed_errors_count == 0
    assert result.summary.manual_review_required_count == 1


def test_report_check_confirm_for_c04_verifiable_missing_field_can_be_confirmed(
    tmp_path: Path,
) -> None:
    finding = _report_finding(
        check_id="C04",
        metadata={
            "component_id": "component-1",
            "field_name": "序列号批号",
            "matched_label_fields": {"部件名称": {"value": "输注泵"}},
            "label_field_comparison": {
                "field_name": "序列号批号",
                "sample_value": "LOT-1",
                "matched_label_value": None,
                "comparison_hint": "field_missing_in_matched_label",
            },
            "evidence_can_verify_label_content": True,
        },
    ).model_copy(update={"code": "SAMPLE_FIELD_MISSING_IN_LABEL"})
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C04", findings=[finding]),
        codex_audit_service=TargetMetadataReportAuditService(
            verdict=CodexReviewVerdict.CONFIRM,
            target_metadata={"evidence_can_verify_label_content": True},
        ),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["final_status"] == "confirmed"
    assert result.summary.confirmed_findings_count == 1
    assert result.summary.confirmed_errors_count == 1


@pytest.mark.parametrize("check_id", ["C04", "C05", "C06"])
def test_report_check_confirm_for_unused_component_does_not_become_confirmed_error(
    tmp_path: Path,
    check_id: str,
) -> None:
    finding = _report_finding(
        check_id=check_id,
        metadata={
            "component_id": "sample-row-6",
            "component_name": "可透射线 ECG 导联线",
            "is_unused_component": True,
            "unused_reason": "本次检测未使用",
        },
    )
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id=check_id, findings=[finding]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.CONFIRM),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["codex_verdict"] == "confirm"
    assert finding_result.metadata["final_status"] == "refuted"
    assert finding_result.metadata["codex_finalization_diagnostic"] == "CODEX_CONFIRMED_UNUSED_COMPONENT_GAP"
    assert result.summary.confirmed_errors_count == 0
    assert result.summary.manual_review_required_count == 0
    assert result.summary.refuted_findings_count == 1


def test_report_check_confirm_for_complex_matrix_c07_becomes_manual_review(tmp_path: Path) -> None:
    finding = _report_finding(
        check_id="C07",
        metadata={
            "item_no": "59",
            "normalized_item_no": "59",
            "complex_matrix_table": True,
            "complex_matrix_reason": "复杂矩阵表列映射需要人工复核",
        },
    )
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C07", findings=[finding]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.CONFIRM),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["codex_verdict"] == "confirm"
    assert finding_result.metadata["final_status"] == "manual_review_required"
    assert finding_result.metadata["codex_finalization_diagnostic"] == "CODEX_CONFIRMED_COMPLEX_MATRIX_TABLE"
    assert result.summary.confirmed_errors_count == 0
    assert result.summary.manual_review_required_count == 1


def test_report_check_confirm_for_c07_extraction_uncertainty_stays_manual_review(
    tmp_path: Path,
) -> None:
    finding = _report_finding(
        check_id="C07",
        metadata={
            "item_no": "94",
            "normalized_item_no": "94",
            "result_token_recovery_confidence": "uncertain",
            "needs_codex_review": True,
        },
    ).model_copy(
        update={
            "code": "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
            "severity": FindingSeverity.WARN,
            "message": "结构化检验结果可能不完整，需要复核。",
        }
    )
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C07", findings=[finding]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.CONFIRM),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["codex_verdict"] == "confirm"
    assert finding_result.metadata["final_status"] == "manual_review_required"
    assert finding_result.metadata["finalization_reason"] == "CODEX_CONFIRMED_EXTRACTION_UNCERTAINTY"
    assert finding_result.metadata["review_type"] == "extraction_uncertainty"
    assert result.summary.confirmed_findings_count == 0
    assert result.summary.confirmed_errors_count == 0
    assert result.summary.manual_review_required_count == 1
    assert result.summary.final_audit_status == "needs_manual_review"


def test_report_check_confirm_for_simple_c07_business_mismatch_stays_confirmed_error(
    tmp_path: Path,
) -> None:
    finding = _report_finding(
        check_id="C07",
        metadata={
            "item_no": "8",
            "normalized_item_no": "8",
            "effective_test_results": ["符合要求"],
            "actual_conclusion": "/",
        },
    ).model_copy(
        update={
            "code": "CONCLUSION_MISMATCH_002",
            "severity": FindingSeverity.ERROR,
            "expected": "符合",
            "actual": "/",
        }
    )
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C07", findings=[finding]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.CONFIRM),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["codex_verdict"] == "confirm"
    assert finding_result.metadata["final_status"] == "confirmed"
    assert result.summary.confirmed_findings_count == 1
    assert result.summary.confirmed_errors_count == 1
    assert result.summary.final_audit_status == "failed"


def test_report_check_uncertain_for_c07_extraction_uncertainty_stays_manual_review(
    tmp_path: Path,
) -> None:
    finding = _report_finding(check_id="C07").model_copy(
        update={
            "code": "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
            "severity": FindingSeverity.WARN,
        }
    )
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C07", findings=[finding]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.UNCERTAIN),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    finding_result = result.check_results[0].findings[0]
    assert status.status == TaskState.COMPLETED
    assert finding_result.metadata["final_status"] == "manual_review_required"
    assert finding_result.metadata["review_type"] == "extraction_uncertainty"
    assert result.summary.confirmed_findings_count == 0
    assert result.summary.confirmed_errors_count == 0
    assert result.summary.manual_review_required_count == 1


def test_report_check_codex_audit_add_finding_does_not_append_to_deterministic_findings(tmp_path: Path) -> None:
    finding = _report_finding(check_id="C02")
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[finding]),
        codex_audit_service=FakeReportAuditService(verdict=CodexReviewVerdict.ADD_FINDING),
        codex_audit_enabled=True,
    )

    result = task_service.get_result(status.task_id)
    check_result = result.check_results[0]
    assert len(check_result.findings) == 1
    assert check_result.codex_reviews[0].verdict is CodexReviewVerdict.ADD_FINDING
    assert check_result.codex_reviews[0].suggested_finding is not None
    assert check_result.codex_reviews[0].suggested_finding.message == "Codex 建议新增报告自检 finding。"
    assert result.summary.suggested_additional_findings_count == 1


def test_report_check_codex_audit_failed_review_fails_task(tmp_path: Path) -> None:
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[_report_finding(check_id="C02")]),
        codex_audit_service=FakeReportAuditService(failed=True),
        codex_audit_enabled=True,
    )

    assert status.status == TaskState.ERROR
    assert "FAKE_REPORT_AUDIT_FAILED" in (status.error_message or "")


def test_report_check_codex_audit_service_exception_fails_task(tmp_path: Path) -> None:
    finding = _report_finding(check_id="C02")
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C02", findings=[finding]),
        codex_audit_service=FakeReportAuditService(exc=RuntimeError("audit boom")),
        codex_audit_enabled=True,
    )

    assert status.status == TaskState.ERROR
    assert "audit boom" in (status.error_message or "")


def test_report_check_codex_audit_no_reviewable_findings_uses_summary_target(tmp_path: Path) -> None:
    audit_service = FakeReportAuditService()
    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C08", findings=[_report_finding(check_id="C08")]),
        codex_audit_service=audit_service,
        codex_audit_enabled=True,
    )

    check_result = task_service.get_result(status.task_id).check_results[0]
    assert check_result.codex_reviews[0].target.target_type == "check_result"
    assert audit_service.calls


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


def test_report_check_codex_audit_batches_without_omitting_targets(tmp_path: Path) -> None:
    audit_service = FakeReportAuditService()
    c04_findings = [_report_finding(check_id="C04", id_suffix=f"c04-{index}") for index in range(3)]
    c07_findings = [_report_finding(check_id="C07", id_suffix=f"c07-{index}") for index in range(3)]

    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=MultipleReportRuleRunner([("C04", c04_findings), ("C07", c07_findings)]),
        codex_audit_service=audit_service,
        codex_audit_enabled=True,
        report_codex_evidence_builder=ReportCodexEvidenceBuilder(max_targets_per_task=4),
    )

    result = task_service.get_result(status.task_id)
    assert status.status == TaskState.COMPLETED
    assert sum(len(check.codex_reviews) for check in result.check_results) == 6
    assert [len(call["request"].targets) for call in audit_service.calls] == [3, 3]
    assert [call["request"].targets[0].check_id for call in audit_service.calls] == ["C07", "C04"]


def test_report_check_codex_audit_batches_single_check_without_omitting_targets(tmp_path: Path) -> None:
    audit_service = FakeReportAuditService()
    findings = [_report_finding(check_id="C04", id_suffix=f"c04-{index}") for index in range(6)]

    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C04", findings=findings),
        codex_audit_service=audit_service,
        codex_audit_enabled=True,
        report_codex_evidence_builder=ReportCodexEvidenceBuilder(max_targets_per_batch=2),
    )

    result = task_service.get_result(status.task_id)
    assert status.status == TaskState.COMPLETED
    assert len(result.check_results[0].codex_reviews) == 6
    assert [len(call["request"].targets) for call in audit_service.calls] == [2, 2, 2]


def test_report_check_targeted_validation_marks_non_included_findings_out_of_scope(tmp_path: Path) -> None:
    audit_service = FakeReportAuditService()
    c04 = _report_finding(check_id="C04", id_suffix="c04")
    c07 = _report_finding(check_id="C07", id_suffix="c07")

    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=MultipleReportRuleRunner([("C04", [c04]), ("C07", [c07])]),
        codex_audit_service=audit_service,
        report_codex_evidence_builder=ReportCodexEvidenceBuilder(included_check_ids="C07"),
    )

    result = task_service.get_result(status.task_id)
    c04_result = next(check for check in result.check_results if check.check_id == "C04")
    c07_result = next(check for check in result.check_results if check.check_id == "C07")
    assert status.status == TaskState.COMPLETED
    assert result.metadata["codex_audit"]["audit_scope"] == "targeted"
    assert result.metadata["codex_audit"]["full_audit"] is False
    assert result.metadata["codex_audit"]["included_check_ids"] == ["C07"]
    assert c04_result.findings[0].metadata["final_status"] == "out_of_scope"
    assert c04_result.findings[0].metadata["codex_required"] is False
    assert c07_result.findings[0].metadata["final_status"] == "confirmed"
    assert sum(len(check.codex_reviews) for check in result.check_results) == 1
    assert result.summary.out_of_scope_findings_count == 1
    assert result.summary.confirmed_findings_count == 1


def test_report_check_task_audit_options_override_default_target_selection(tmp_path: Path) -> None:
    audit_service = FakeReportAuditService()
    c04 = _report_finding(check_id="C04", id_suffix="c04")
    c07 = _report_finding(check_id="C07", id_suffix="c07")
    task_service = TaskService()
    usecase = ReportCheckUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=FakePdfParser(),
        field_extractor=FakeFieldExtractor(),
        inspection_table_extractor=FakeInspectionTableExtractor(),
        sample_description_extractor=FakeSampleDescriptionExtractor(),
        photo_label_extractor=FakePhotoLabelExtractor(),
        rule_runner=MultipleReportRuleRunner([("C04", [c04]), ("C07", [c07])]),
        codex_audit_service=audit_service,
        report_codex_evidence_builder=ReportCodexEvidenceBuilder(),
    )

    status = usecase.run(
        file_name="report.pdf",
        content=b"%PDF-1.4 report",
        content_type="application/pdf",
        audit_options={
            "included_check_ids": "C07",
            "max_targets_per_batch": 1,
            "max_parallel_jobs": 1,
        },
    )

    result = task_service.get_result(status.task_id)
    assert status.status == TaskState.COMPLETED
    assert [call["request"].targets[0].check_id for call in audit_service.calls] == ["C07"]
    assert result.metadata["audit_options_source"] == "user_override"
    assert result.metadata["audit_options"]["included_check_ids"] == ["C07"]
    assert result.metadata["audit_options"]["max_targets_per_batch"] == 1
    assert result.metadata["audit_options"]["max_parallel_jobs"] == 1
    assert result.metadata["effective_audit_options"]["included_check_ids"] == ["C07"]
    assert result.metadata["effective_audit_options"]["max_targets_per_batch"] == 1
    assert result.metadata["effective_audit_options"]["max_parallel_jobs"] == 1
    assert result.metadata["codex_audit"]["audit_scope"] == "targeted"
    assert result.metadata["codex_audit"]["included_check_ids"] == ["C07"]


def test_report_check_full_audit_fails_when_required_candidate_is_missing_review(tmp_path: Path) -> None:
    findings = [
        _report_finding(check_id="C04", id_suffix="c04-1"),
        _report_finding(check_id="C04", id_suffix="c04-2"),
    ]

    task_service, status = _run_report_check(
        tmp_path,
        rule_runner=ConfigurableReportRuleRunner(check_id="C04", findings=findings),
        codex_audit_service=PartialReportAuditService(),
    )

    assert status.status == TaskState.ERROR
    assert "CODEX_AUDIT_INCOMPLETE" in (status.error_message or "")


def _run_report_check(
    tmp_path: Path,
    *,
    rule_runner,
    codex_audit_service: FakeReportAuditService | None = None,
    codex_audit_enabled: bool = False,
    report_codex_evidence_builder: ReportCodexEvidenceBuilder | None = None,
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
        report_codex_evidence_builder=report_codex_evidence_builder,
    )
    status = usecase.run(file_name="report.pdf", content=b"%PDF-1.4 report", content_type="application/pdf")
    return task_service, status


def _report_finding(check_id: str, *, id_suffix: str = "finding", metadata: dict | None = None) -> Finding:
    evidence = Evidence(
        id=f"ev-{check_id}",
        source_type=SourceType.REPORT,
        raw_text=f"{check_id} evidence",
        method=EvidenceMethod.PDF_TEXT,
    )
    finding_metadata = {}
    if check_id in {"C02", "C03"}:
        finding_metadata = {"field_name": "生产日期", "page_number": 3}
    elif check_id == "C07":
        finding_metadata = {
            "item_no": "1",
            "normalized_item_no": "1",
            "result_values": ["不符合要求"],
            "actual_conclusion": "符合",
        }
    if metadata:
        finding_metadata.update(metadata)
    return Finding(
        id=f"task-placeholder-{check_id}-{id_suffix}",
        task_id="task-placeholder",
        check_id=check_id,
        severity=FindingSeverity.ERROR,
        code=f"{check_id}_TEST_FINDING",
        message=f"{check_id} deterministic finding",
        expected="expected",
        actual="actual",
        evidence=[evidence],
        metadata=finding_metadata,
    )
