import json
from pathlib import Path
from types import SimpleNamespace

from app.application.codex_audit_service import CodexAuditService
from app.application.ptr_codex_evidence_builder import PtrCodexEvidenceBuilder
from app.application.ptr_compare_usecase import PTRCompareUseCase
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
from app.domain.evidence_package import EvidencePackage
from app.domain.finding import Finding, FindingSeverity
from app.domain.pdf import ParsedPdf, PdfPage, PdfTable
from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument, PTRScopeType, PTRTable, TableReference
from app.domain.report import InspectionItem, InspectionTable, ReportDocument, ReportField, ThirdPageInfo
from app.domain.result import CheckStatus
from app.domain.table import CanonicalTable, ParameterRecord
from app.domain.task import TaskState, TaskType
from app.infrastructure.audit.evidence_package_writer import EvidencePackageWriter
from app.infrastructure.codex.fake_codex_runner import FakeCodexRunner
from app.infrastructure.codex.prompt_builder import PromptBuilder
from app.infrastructure.storage.local_file_store import LocalFileStore
from app.rules.ptr.scope_filter import ScopeDecision, ScopeFilterResult
from tests.fixtures.table_fixture_builder import build_pdf_table


class FakePdfParser:
    def __init__(self, parsed_by_name: dict[str, ParsedPdf] | None = None) -> None:
        self.parsed_by_name = parsed_by_name or {}
        self.paths: list[Path] = []

    def parse(self, file_path: Path) -> ParsedPdf:
        self.paths.append(file_path)
        if file_path.name in self.parsed_by_name:
            return self.parsed_by_name[file_path.name]
        return ParsedPdf(file_id=file_path.stem, file_name=file_path.name, page_count=1)


class FakePTRExtractor:
    def __init__(self, document: PTRDocument | None = None) -> None:
        self.document = document
        self.parsed: list[ParsedPdf] = []

    def extract(self, parsed_pdf: ParsedPdf) -> PTRDocument:
        self.parsed.append(parsed_pdf)
        if self.document is not None:
            self.document.parsed_pdf = parsed_pdf
            return self.document
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
    def __init__(self, document: ReportDocument | None = None) -> None:
        self.document = document
        self.parsed: list[ParsedPdf] = []

    def extract(self, parsed_pdf: ParsedPdf) -> ReportDocument:
        self.parsed.append(parsed_pdf)
        if self.document is not None:
            self.document.parsed_pdf = parsed_pdf
            return self.document
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


class IncludeAllScopeFilter:
    def __call__(
        self,
        ptr_doc: PTRDocument,
        inspection_scope_texts: list[str],
        *,
        report_clause_numbers: set[str] | None = None,
    ) -> ScopeFilterResult:
        del inspection_scope_texts, report_clause_numbers
        decisions = [
            ScopeDecision(
                clause_id=clause.clause_id,
                clause_number=str(clause.number),
                included=True,
                reason="test_include_all",
            )
            for clause in ptr_doc.clauses
        ]
        return ScopeFilterResult(
            included_clause_ids=[clause.clause_id for clause in ptr_doc.clauses],
            excluded_clause_ids=[],
            decisions=decisions,
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


class NoopClauseCompare:
    def __call__(self, ptr_clauses: list[PTRClause], report_items: list[InspectionItem], *, task_id: str) -> list[Finding]:
        return []


class TrackingTableCompare:
    def __init__(self) -> None:
        self.calls: list[tuple[PTRDocument, list[PTRClause], str]] = []

    def __call__(self, ptr_doc: PTRDocument, *, clauses: list[PTRClause] | None = None, task_id: str) -> list[Finding]:
        self.calls.append((ptr_doc, clauses or [], task_id))
        return []


class FakePtrCodexAuditService:
    def __init__(
        self,
        *,
        verdict: CodexReviewVerdict = CodexReviewVerdict.CONFIRM,
        status: CodexReviewStatus = CodexReviewStatus.SUCCEEDED,
        suggested_finding: CodexSuggestedFinding | None = None,
        error: CodexReviewError | None = None,
        timeout_seconds: int = 900,
        calls: list[tuple] | None = None,
        timeout_overrides: list[int] | None = None,
    ) -> None:
        self.verdict = verdict
        self.status = status
        self.suggested_finding = suggested_finding
        self.error = error
        self.calls: list[tuple] = calls if calls is not None else []
        self.timeout_overrides = timeout_overrides if timeout_overrides is not None else []
        self.runner = SimpleNamespace(config=SimpleNamespace(timeout_seconds=timeout_seconds))

    def with_timeout_seconds(self, timeout_seconds: int) -> "FakePtrCodexAuditService":
        self.timeout_overrides.append(timeout_seconds)
        return FakePtrCodexAuditService(
            verdict=self.verdict,
            status=self.status,
            suggested_finding=self.suggested_finding,
            error=self.error,
            timeout_seconds=timeout_seconds,
            calls=self.calls,
            timeout_overrides=self.timeout_overrides,
        )

    def review(self, request, evidence_package: EvidencePackage) -> list[CodexReviewResult]:
        self.calls.append((request, evidence_package))
        results: list[CodexReviewResult] = []
        for target in request.targets:
            if self.status is CodexReviewStatus.FAILED:
                results.append(
                    CodexReviewResult(
                        review_id=f"fake-codex:{target.target_id}:failed",
                        request_id=request.request_id,
                        task_id=request.task_id,
                        target=target,
                        status=CodexReviewStatus.FAILED,
                        error=self.error
                        or CodexReviewError(
                            code="FAKE_CODEX_FAILED",
                            message="Fake PTR Codex audit failed.",
                        ),
                    )
                )
                continue
            results.append(
                CodexReviewResult(
                    review_id=f"fake-codex:{target.target_id}",
                    request_id=request.request_id,
                    task_id=request.task_id,
                    target=target,
                    status=CodexReviewStatus.SUCCEEDED,
                    verdict=self.verdict,
                    confidence=CodexReviewConfidence.MEDIUM,
                    reasoning_summary="Fake PTR Codex audit result.",
                    suggested_finding=self.suggested_finding,
                    evidence_refs=[ref.ref_id for ref in target.evidence_refs],
                )
            )
        return results


class ExplodingPtrCodexAuditService:
    def __init__(self) -> None:
        self.calls = 0

    def review(self, request, evidence_package: EvidencePackage) -> list[CodexReviewResult]:
        del request, evidence_package
        self.calls += 1
        raise RuntimeError("codex audit service exploded")


class ScopeAwareReportExtractor:
    def __init__(self, scope_text: str = "2.2、2.5、2.6（除生物相容性、电磁兼容性）") -> None:
        self.scope_text = scope_text

    def extract(self, parsed_pdf: ParsedPdf) -> ReportDocument:
        scope_field = ReportField(name="检验项目", value=self.scope_text, metadata={"items": [self.scope_text]})
        return ReportDocument(
            parsed_pdf=parsed_pdf,
            third_page=ThirdPageInfo(fields=[scope_field]),
            fields=[scope_field],
        )


class ScopeAwareInspectionTableExtractor:
    def __init__(self, items: list[InspectionItem] | None = None) -> None:
        self.items = items if items is not None else _scope_aware_report_items()

    def extract_table(self, parsed_pdf: ParsedPdf) -> InspectionTable:
        del parsed_pdf
        return InspectionTable(table_id="report-inspection-table", items=self.items)


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
        codex_audit_service=FakePtrCodexAuditService(),
    )

    status = usecase.run(
        ptr_file_name="ptr.pdf",
        ptr_content=b"%PDF-1.4 ptr",
        report_file_name="report.pdf",
        report_content=b"%PDF-1.4 report",
        content_type="application/pdf",
    )

    assert status.task_type == TaskType.PTR_COMPARE
    assert status.status == TaskState.COMPLETED, status.error_message
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
    assert result.check_results[1].codex_reviews[0].verdict is CodexReviewVerdict.CONFIRM
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


def test_ptr_compare_usecase_submit_creates_processing_task_without_parsing(tmp_path: Path) -> None:
    task_service = TaskService()
    file_store = LocalFileStore(tmp_path)
    parser = FakePdfParser()
    usecase = PTRCompareUseCase(
        task_service=task_service,
        file_store=file_store,
        pdf_parser=parser,
        ptr_extractor=FakePTRExtractor(),
        report_extractor=FakeReportFieldExtractor(),
        inspection_table_extractor=FakeInspectionTableExtractor(),
        scope_filter=TrackingScopeFilter(),
        clause_text_compare=TrackingClauseCompare(),
        table_reference_compare=TrackingTableCompare(),
        codex_audit_service=FakePtrCodexAuditService(),
    )

    status = usecase.submit(
        ptr_file_name="ptr.pdf",
        ptr_content=b"%PDF-1.4 ptr",
        report_file_name="report.pdf",
        report_content=b"%PDF-1.4 report",
        content_type="application/pdf",
    )

    assert status.status == TaskState.PROCESSING
    assert status.progress == 1
    assert status.current_step == "queued ptr compare"
    assert {file.file_name for file in status.input_files} == {"ptr.pdf", "report.pdf"}
    assert file_store.get_upload_path(task_id=status.task_id, file_name="ptr.pdf", category="ptr").exists()
    assert file_store.get_upload_path(task_id=status.task_id, file_name="report.pdf", category="report").exists()
    assert parser.paths == []


def test_ptr_compare_usecase_process_submitted_task_updates_progress_and_completes(tmp_path: Path) -> None:
    task_service = TaskService()
    parser = FakePdfParser()
    ptr_extractor = FakePTRExtractor()
    report_extractor = FakeReportFieldExtractor()
    usecase = PTRCompareUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=parser,
        ptr_extractor=ptr_extractor,
        report_extractor=report_extractor,
        inspection_table_extractor=FakeInspectionTableExtractor(),
        scope_filter=TrackingScopeFilter(),
        clause_text_compare=TrackingClauseCompare(),
        table_reference_compare=TrackingTableCompare(),
        codex_audit_service=FakePtrCodexAuditService(),
    )
    submitted = usecase.submit(
        ptr_file_name="ptr.pdf",
        ptr_content=b"%PDF-1.4 ptr",
        report_file_name="report.pdf",
        report_content=b"%PDF-1.4 report",
        content_type="application/pdf",
    )

    status = usecase.process_task(submitted.task_id)

    assert status.status == TaskState.COMPLETED, status.error_message
    assert status.progress == 100
    assert status.result_ref == submitted.task_id
    assert [path.name for path in parser.paths] == ["ptr.pdf", "report.pdf"]
    assert ptr_extractor.parsed[0].file_name == "ptr.pdf"
    assert report_extractor.parsed[0].file_name == "report.pdf"
    result = task_service.get_result(submitted.task_id)
    assert result.task_id == submitted.task_id
    assert result.task_type == TaskType.PTR_COMPARE
    assert result.check_results[0].check_id == "PTR_SCOPE"


def test_ptr_compare_usecase_includes_parameter_value_mismatch_in_final_result(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度(ms)", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度(ms)", "0.5")])],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.status == CheckStatus.FAIL
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_VALUE_MISMATCH"]
    assert ptr_table_result.findings[0].expected == "0.4"
    assert ptr_table_result.findings[0].actual == "0.5"
    assert result.summary.error_count == 1
    assert result.metadata["source"] == "ptr_compare_usecase"


def test_ptr_compare_usecase_attaches_ptr_comparison_details_for_covered_and_missing_items(tmp_path: Path) -> None:
    task_service = TaskService()
    ptr_doc = PTRDocument(
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

    usecase = PTRCompareUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=FakePdfParser(),
        ptr_extractor=FakePTRExtractor(ptr_doc),
        report_extractor=FakeReportFieldExtractor(),
        inspection_table_extractor=FakeInspectionTableExtractor(),
        scope_filter=IncludeAllScopeFilter(),
        table_reference_compare=TrackingTableCompare(),
        codex_audit_service=FakePtrCodexAuditService(verdict=CodexReviewVerdict.CONFIRM),
    )

    status = usecase.run(
        ptr_file_name="ptr.pdf",
        ptr_content=b"%PDF-1.4 ptr",
        report_file_name="report.pdf",
        report_content=b"%PDF-1.4 report",
        content_type="application/pdf",
    )

    result = task_service.get_result(status.task_id)
    details = result.metadata["ptr_comparison_details"]
    items = {item["ptr_clause_id"]: item for item in details["items"]}

    assert details["requirements_count"] == 2
    assert details["covered_count"] == 0
    assert details["missing_count"] == 1
    assert details["needs_review_count"] == 1
    assert items["2.1"]["user_facing_status"] == "coverage_only_needs_review"
    assert items["2.1"]["ptr_requirement_text"] == "外观应平整"
    assert items["2.1"]["report_matches"][0]["item_no"] == "1"
    assert items["2.1"]["report_matches"][0]["standard_requirement"] == "外观应平整"
    assert items["2.1"]["atomic_comparison_rows"] == []
    assert items["2.2"]["rule_status"] == "missing_in_report"
    assert items["2.2"]["user_facing_status"] == "confirmed_error"
    assert items["2.2"]["final_status"] == "confirmed_error"
    assert "报告中未找到" in items["2.2"]["reason"]
    assert "/Users/" not in json.dumps(details, ensure_ascii=False)


def test_ptr_compare_usecase_ptr_comparison_details_map_codex_verdicts(tmp_path: Path) -> None:
    expectations = [
        (CodexReviewVerdict.CONFIRM, "confirmed_error", "confirmed_error"),
        (CodexReviewVerdict.REFUTE, "refuted", "refuted"),
        (CodexReviewVerdict.UNCERTAIN, "needs_review", "manual_review_required"),
    ]

    for verdict, user_status, final_status in expectations:
        result = _run_parameter_compare_usecase(
            tmp_path,
            ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
            report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.5")])],
            codex_audit_enabled=True,
            codex_audit_service=FakePtrCodexAuditService(verdict=verdict),
        )

        item = result.metadata["ptr_comparison_details"]["items"][0]
        assert item["user_facing_status"] == user_status
        assert item["final_status"] == final_status


def test_ptr_compare_usecase_ptr_comparison_details_include_numeric_expected_actual_operator_and_unit(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table(
            "ptr-table-1",
            "1",
            [_record("输入功率", "≤110%", values={"限值": "≤110%"})],
        ),
        report_tables=[
            _canonical_table(
                "report-table-1",
                "1",
                [_record("输入功率", "120%", values={"限值": "120%"})],
            )
        ],
        codex_audit_enabled=True,
        codex_audit_service=FakePtrCodexAuditService(verdict=CodexReviewVerdict.UNCERTAIN),
    )

    comparison = result.metadata["ptr_comparison_details"]["items"][0]["normalized_comparison"]
    assert comparison == {
        "requirement_type": "numeric_limit",
        "expected": "≤110%",
        "actual": "120%",
        "unit": "%",
        "operator": "≤",
        "status": "mismatch",
    }


def test_ptr_compare_scope_aware_1539_like_report_passes_and_explains_scope(tmp_path: Path) -> None:
    result = _run_scope_aware_usecase(tmp_path)

    scope_result = _check_result(result, "PTR_REPORT_SCOPE")
    assert scope_result.status == CheckStatus.PASS
    assert scope_result.findings == []
    assert scope_result.metadata["scope_consistency"]["status"] == "passed"
    assert scope_result.metadata["scope_consistency"]["declared_scope"] == ["2.2", "2.5", "2.6"]
    assert scope_result.metadata["scope_consistency"]["actual_report_scope"] == ["2.2", "2.5", "2.6"]
    assert scope_result.metadata["scope_consistency"]["excluded_topics"] == ["生物相容性", "电磁兼容性"]
    assert scope_result.metadata["scope_consistency"]["ptr_direct_content_starts_after"] == "156"

    details = result.metadata["ptr_comparison_details"]
    assert details["scope_consistency"]["status"] == "passed"
    assert details["requirements_count"] >= 9
    items = {item["ptr_clause_id"]: item for item in details["items"]}
    assert "2.5.2.2" not in items
    assert items["2.2.1"]["report_matches"][0]["item_no"] == "157"
    assert "3333V" in items["2.2.1"]["report_matches"][0]["standard_requirement"]
    assert "57A" in items["2.2.1"]["report_matches"][0]["standard_requirement"]
    assert "3375" in items["2.2.1"]["report_matches"][0]["test_result"]
    assert "59" in items["2.2.1"]["report_matches"][0]["test_result"]
    assert items["2.2.1"]["report_matches"][0]["single_conclusion"] == "符合"
    assert items["2.2.1"]["report_matches"][0]["report_pages"] == [99, 100, 101]
    assert items["2.2.1"]["coverage_status"] == "covered_passed"
    assert items["2.2.1"]["final_status"] != "confirmed_error"
    assert "报告序号 157" in items["2.2.1"]["reason"]
    atomic_by_id = {row["atomic_id"]: row for row in items["2.2.1"]["atomic_comparison_rows"]}
    assert set(atomic_by_id) == {"2.2.1:voltage", "2.2.1:current"}
    assert atomic_by_id["2.2.1:voltage"]["label"] == "电压"
    assert atomic_by_id["2.2.1:voltage"]["expected"] == "≥3333 V（峰值）"
    assert atomic_by_id["2.2.1:voltage"]["actual"] == "3375"
    assert atomic_by_id["2.2.1:voltage"]["status"] == "match"
    assert "3375 ≥ 3333" in atomic_by_id["2.2.1:voltage"]["reason"]
    assert atomic_by_id["2.2.1:current"]["expected"] == "≥57 A（峰值）"
    assert atomic_by_id["2.2.1:current"]["actual"] == "59"
    assert atomic_by_id["2.2.1:current"]["status"] == "match"
    assert "2.2.2" not in str(items["2.2.1"]["normalized_comparison"]["actual"])
    assert "2.2.7" not in str(items["2.2.1"]["normalized_comparison"]["actual"])
    waveform_rows = items["2.2.2"]["atomic_comparison_rows"]
    assert {row["table_key"] for row in waveform_rows} == {"2.2.2:表6:波形参数"}
    assert len(waveform_rows) >= 9
    assert {row["label"] for row in waveform_rows} >= {"脉冲个数", "脉冲组数", "脉冲组间隔", "脉冲对间隔", "脉冲宽度", "脉冲相间隔", "波形类型", "正峰值/负峰值", "电流水平"}
    assert items["2.2.2"]["coverage_status"] == "needs_review"
    for clause_number in ("2.2.2", "2.2.3", "2.2.4", "2.2.5", "2.2.6", "2.2.7.1", "2.2.7.2"):
        assert items[clause_number]["coverage_status"] in {"covered_passed", "needs_review"}
        assert items[clause_number]["report_matches"][0]["item_no"] == "157"
        assert items[clause_number]["report_matches"][0]["standard_clause"] == "2.2"
        assert items[clause_number]["report_matches"][0]["item_no"] not in {"52", "65"}
    group_157_result = items["2.2.1"]["report_matches"][0]["test_result"]
    for value in ("3375", "59", "1μsec±20%", "430", "455", "260", "205", "1%", "159"):
        assert value in group_157_result
    assert items["2.5.2.1"]["coverage_status"] == "covered_passed"
    external_coverages = items["2.5.2.1"]["external_standard_coverages"]
    assert [coverage["standard"] for coverage in external_coverages] == ["GB 9706.1-2020", "GB9706.202-2021"]
    assert "GB 9706.1-2020" in items["2.5.2.1"]["reason"]
    assert "GB9706.202-2021" in items["2.5.2.1"]["reason"]
    assert items["2.6"]["coverage_status"] in {"covered_passed", "needs_review"}
    assert items["2.6"]["report_matches"][0]["item_no"] == "159"
    assert items["2.6"]["report_matches"][0]["standard_clause"] == "2.6"
    assert "14" not in {match["item_no"] for match in items["2.6"]["report_matches"]}
    software_rows = items["2.6"]["atomic_comparison_rows"]
    assert software_rows
    assert {row["table_key"] for row in software_rows} == {"2.6:表6:软件功能"}
    assert any(row["label"] == "射频消融仪 - 功率监测" for row in software_rows)
    assert any(row["label"] == "心脏脉冲电场消融仪 - 温度监测" for row in software_rows)
    assert items["2.6"]["coverage_status"] == "needs_review"
    assert "表格功能明细需复核" in items["2.6"]["reason"]
    excluded = {item["ptr_clause_id"]: item for item in details["excluded_items"]}
    for clause_number in ("2.5.1.2", "2.5.2.2", "2.5.3.2"):
        assert excluded[clause_number]["status"] == "excluded_by_scope"
        assert "电磁兼容性" in excluded[clause_number]["reason"]
    assert "2.14" not in scope_result.metadata["scope_consistency"]["actual_report_scope"]
    assert "2.4" not in items
    assert "/Users/" not in json.dumps(details, ensure_ascii=False)
    for excluded_number in ("2.1", "2.3", "2.5.2.2", "2.7", "2.8"):
        assert excluded_number not in items
    assert not any(finding.metadata.get("clause_number") == "2.2.1" for finding in result.findings)


def test_ptr_compare_scope_consistency_reports_declared_item_missing(tmp_path: Path) -> None:
    report_items = [item for item in _scope_aware_report_items() if item.standard_clause != "2.6"]

    result = _run_scope_aware_usecase(
        tmp_path,
        inspection_table_extractor=ScopeAwareInspectionTableExtractor(report_items),
    )

    scope_result = _check_result(result, "PTR_REPORT_SCOPE")
    assert scope_result.status == CheckStatus.FAIL
    assert _finding_codes(scope_result) == ["PTR_SCOPE_DECLARED_ITEM_MISSING_IN_REPORT"]
    assert scope_result.findings[0].metadata["clause_number"] == "2.6"
    assert result.metadata["ptr_comparison_details"]["scope_consistency"]["status"] == "failed"


def test_ptr_compare_scope_consistency_reports_undeclared_report_item(tmp_path: Path) -> None:
    report_items = [
        *_scope_aware_report_items(),
        InspectionItem(
            sequence_raw="160",
            sequence=160,
            standard_clause="2.7",
            standard_requirement="额外项目",
            test_result="符合要求",
            conclusion="符合",
            source_page=100,
        ),
    ]

    result = _run_scope_aware_usecase(
        tmp_path,
        inspection_table_extractor=ScopeAwareInspectionTableExtractor(report_items),
    )

    scope_result = _check_result(result, "PTR_REPORT_SCOPE")
    assert scope_result.status == CheckStatus.FAIL
    assert _finding_codes(scope_result) == ["PTR_SCOPE_UNDECLARED_REPORT_ITEM"]
    assert scope_result.findings[0].metadata["clause_number"] == "2.7"


def test_ptr_compare_scope_consistency_reports_excluded_topic_present(tmp_path: Path) -> None:
    report_items = [
        *_scope_aware_report_items(),
        InspectionItem(
            sequence_raw="160",
            sequence=160,
            standard_clause="2.5.2.2",
            standard_requirement="电磁兼容性应符合 YY 9706.102-2021。",
            test_result="符合要求",
            conclusion="符合",
            source_page=100,
        ),
    ]

    result = _run_scope_aware_usecase(
        tmp_path,
        inspection_table_extractor=ScopeAwareInspectionTableExtractor(report_items),
    )

    scope_result = _check_result(result, "PTR_REPORT_SCOPE")
    assert scope_result.status == CheckStatus.FAIL
    assert _finding_codes(scope_result) == ["PTR_SCOPE_EXCLUDED_TOPIC_PRESENT"]
    assert scope_result.findings[0].metadata["excluded_topic"] == "电磁兼容性"


def test_ptr_compare_usecase_includes_parameter_unit_mismatch_in_final_result(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4", unit="ms")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.4", unit="s")])],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_UNIT_MISMATCH"]
    assert ptr_table_result.findings[0].expected == "ms"
    assert ptr_table_result.findings[0].actual == "s"


def test_ptr_compare_usecase_includes_parameter_condition_and_tolerance_mismatches(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table(
            "ptr-table-1",
            "1",
            [
                    _record(
                        "输出幅度",
                        "3.5",
                        unit="V",
                        conditions={"试验条件": "@240Ω"},
                        values={"标准设置": "3.5", "允许误差": "±10%"},
                    )
            ],
        ),
        report_tables=[
            _canonical_table(
                "report-table-1",
                "1",
                [
                    _record(
                        "输出幅度",
                        "3.5",
                        unit="V",
                        conditions={"试验条件": "@500Ω"},
                        values={"标准设置": "3.5", "允许误差": "±20%"},
                    )
                ],
            )
        ],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert _finding_codes(ptr_table_result) == [
        "PTR_TABLE_TOLERANCE_MISMATCH",
        "PTR_TABLE_CONDITION_MISMATCH",
    ]
    assert ptr_table_result.findings[0].expected == "±10%"
    assert ptr_table_result.findings[0].actual == "±20%"
    assert ptr_table_result.findings[1].expected == {"试验条件": "@240Ω"}
    assert ptr_table_result.findings[1].actual == {"试验条件": "@500Ω"}


def test_ptr_compare_usecase_suppresses_numeric_semantic_equivalent_values(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table(
            "ptr-table-1",
            "1",
            [_record("最小输出", "≥5", unit="V", values={"标准设置": "不小于5"})],
        ),
        report_tables=[
            _canonical_table(
                "report-table-1",
                "1",
                [_record("最小输出", ">=5", unit="V", values={"标准设置": ">=5"})],
            )
        ],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.status == CheckStatus.PASS
    assert ptr_table_result.findings == []


def test_ptr_compare_usecase_includes_numeric_semantic_value_mismatch(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table(
            "ptr-table-1",
            "1",
            [_record("最小输出", "≥5", unit="V", values={"标准设置": "≥5"})],
        ),
        report_tables=[
            _canonical_table(
                "report-table-1",
                "1",
                [_record("最小输出", "≥6", unit="V", values={"标准设置": "≥6"})],
            )
        ],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_VALUE_MISMATCH"]
    assert ptr_table_result.findings[0].expected == "≥5"
    assert ptr_table_result.findings[0].actual == "≥6"


def test_ptr_compare_usecase_includes_segmented_threshold_mismatch(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table(
            "ptr-table-1",
            "1",
            [
                _record("阈值", "≥5", unit="V", conditions={"负载": "@240Ω"}, values={"限值": "≥5"}),
                _record("阈值", "≥5", unit="V", conditions={"负载": "@500Ω"}, values={"限值": "≥5"}),
            ],
        ),
        report_tables=[
            _canonical_table(
                "report-table-1",
                "1",
                [
                    _record("阈值", "≥6", unit="V", conditions={"负载": "@240Ω"}, values={"限值": "≥6"}),
                    _record("阈值", "≥5", unit="V", conditions={"负载": "@500Ω"}, values={"限值": "≥5"}),
                ],
            )
        ],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_TOLERANCE_MISMATCH"]
    assert ptr_table_result.findings[0].metadata["conditions"] == {"负载": "@240Ω"}


def test_ptr_compare_usecase_includes_missing_parameter_in_final_result(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table(
            "ptr-table-1",
            "1",
            [_record("脉冲宽度(ms)", "0.4"), _record("基础频率(bpm)", "60")],
        ),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度(ms)", "0.4")])],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_PARAM_MISSING"]
    assert ptr_table_result.findings[0].metadata["parameter_name"] == "基础频率(bpm)"


def test_ptr_compare_usecase_preserves_missing_table_reference_and_skips_parameter_compare(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=None,
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度(ms)", "0.4")])],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.status == CheckStatus.FAIL
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_MISSING"]


def test_ptr_compare_usecase_preserves_ambiguous_table_reference_and_skips_parameter_compare(tmp_path: Path) -> None:
    expected = _canonical_table("ptr-table-1-a", "1", [_record("脉冲宽度(ms)", "0.4")])
    duplicate = _canonical_table("ptr-table-1-b", "1", [_record("脉冲宽度(ms)", "0.4")])
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=expected,
        extra_ptr_tables=[_ptr_table(duplicate)],
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度(ms)", "0.5")])],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.status == CheckStatus.REVIEW
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_CANDIDATE_AMBIGUOUS"]


def test_ptr_compare_usecase_completes_when_report_side_has_no_canonical_table(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度(ms)", "0.4")]),
        report_tables=[],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.status == CheckStatus.FAIL
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_PARAM_MISSING"]


def test_ptr_compare_usecase_does_not_emit_parameter_error_when_table_records_match(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度(ms)", "0.4", unit="ms")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度(ms)", "0.4", unit="ms")])],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.status == CheckStatus.PASS
    assert ptr_table_result.findings == []


def test_ptr_compare_usecase_keeps_report_extra_parameter_behavior_from_parameter_compare(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度(ms)", "0.4")]),
        report_tables=[
            _canonical_table(
                "report-table-1",
                "1",
                [_record("脉冲宽度(ms)", "0.4"), _record("报告额外参数", "99")],
            )
        ],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.status == CheckStatus.PASS
    assert ptr_table_result.findings == []


def test_ptr_compare_usecase_selects_report_table_by_caption_before_parameter_compare(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table(
            "ptr-table-1",
            "1",
            [_record("脉冲宽度", "0.4")],
            caption="表 1 脉冲参数",
        ),
        report_tables=[
            _canonical_table("report-table-size", "1", [_record("脉冲宽度", "0.4")], caption="表 1 尺寸参数"),
            _canonical_table("report-table-pulse", "1", [_record("脉冲宽度", "0.5")], caption="表 1 脉冲参数"),
        ],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.status == CheckStatus.FAIL
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_VALUE_MISMATCH"]
    assert ptr_table_result.findings[0].actual == "0.5"


def test_ptr_compare_usecase_avoids_false_parameter_error_from_wrong_same_number_table(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table(
            "ptr-table-1",
            "1",
            [_record("脉冲宽度", "0.4")],
            caption="表 1 脉冲参数",
        ),
        report_tables=[
            _canonical_table("report-table-size", "1", [_record("脉冲宽度", "9.9")], caption="表 1 尺寸参数"),
            _canonical_table("report-table-pulse", "1", [_record("脉冲宽度", "0.4")], caption="表 1 脉冲参数"),
        ],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.status == CheckStatus.PASS
    assert ptr_table_result.findings == []


def test_ptr_compare_usecase_reports_ambiguous_report_table_without_parameter_compare(tmp_path: Path) -> None:
    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table(
            "ptr-table-1",
            "1",
            [_record("脉冲宽度", "0.4"), _record("基础频率", "60")],
            caption="表 1 参数",
        ),
        report_tables=[
            _canonical_table("report-table-left", "1", [_record("脉冲宽度", "0.5"), _record("输出电压", "9")], caption="表 1 参数"),
            _canonical_table("report-table-right", "1", [_record("基础频率", "50"), _record("输出电压", "9")], caption="表 1 参数"),
        ],
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.status == CheckStatus.REVIEW
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_CANDIDATE_AMBIGUOUS"]
    assert ptr_table_result.findings[0].metadata["matching_strategy"] == "ambiguous"


def test_ptr_compare_without_reviewable_targets_completes_without_codex_call(tmp_path: Path) -> None:
    audit_service = FakePtrCodexAuditService()

    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.4")])],
        codex_audit_service=audit_service,
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert _finding_codes(ptr_table_result) == []
    assert ptr_table_result.codex_reviews == []
    assert audit_service.calls == []


def test_ptr_compare_codex_audit_confirm_review_is_attached_to_check_result(tmp_path: Path) -> None:
    audit_service = FakePtrCodexAuditService(verdict=CodexReviewVerdict.CONFIRM)

    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.5")])],
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.codex_reviews[0].verdict is CodexReviewVerdict.CONFIRM
    assert audit_service.calls
    assert result.summary.audit_scope == "full"
    assert result.summary.full_audit is True
    assert result.summary.final_audit_status == "failed"
    assert result.metadata["codex_audit"]["final_audit_status"] == "failed"


def test_ptr_compare_codex_audit_can_use_codex_audit_service_with_fake_runner(tmp_path: Path) -> None:
    audit_service = CodexAuditService(
        evidence_writer=EvidencePackageWriter(tmp_path / "runtime" / "codex_audit"),
        prompt_builder=PromptBuilder(),
        runner=FakeCodexRunner(),
    )

    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.5")])],
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.codex_reviews[0].status is CodexReviewStatus.SUCCEEDED
    assert ptr_table_result.codex_reviews[0].verdict is CodexReviewVerdict.CONFIRM
    input_dirs = list((tmp_path / "runtime" / "codex_audit" / result.task_id).glob("*/input"))
    assert input_dirs
    assert (input_dirs[0] / "prompt.md").is_file()


def test_ptr_compare_codex_audit_refute_does_not_delete_deterministic_finding(tmp_path: Path) -> None:
    audit_service = FakePtrCodexAuditService(verdict=CodexReviewVerdict.REFUTE)

    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.5")])],
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_VALUE_MISMATCH"]
    assert ptr_table_result.codex_reviews[0].verdict is CodexReviewVerdict.REFUTE
    assert result.summary.final_audit_status == "passed"
    assert result.metadata["codex_audit"]["final_audit_status"] == "passed"


def test_ptr_compare_codex_audit_uncertain_sets_final_status_to_manual_review(tmp_path: Path) -> None:
    audit_service = FakePtrCodexAuditService(verdict=CodexReviewVerdict.UNCERTAIN)

    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.5")])],
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert ptr_table_result.codex_reviews[0].verdict is CodexReviewVerdict.UNCERTAIN
    assert ptr_table_result.findings[0].metadata["final_status"] == "manual_review_required"
    assert result.summary.confirmed_errors_count == 0
    assert result.summary.manual_review_required_count == 1
    assert result.summary.final_audit_status == "needs_manual_review"


def test_ptr_compare_codex_audit_add_finding_does_not_append_to_deterministic_findings(tmp_path: Path) -> None:
    suggested = CodexSuggestedFinding(
        check_id="PTR_TABLE",
        severity="warn",
        code="PTR_TABLE_SEMANTIC_REVIEW",
        message="Codex 建议新增一个 PTR 表格语义复核项。",
        evidence_refs=[],
    )
    audit_service = FakePtrCodexAuditService(
        verdict=CodexReviewVerdict.ADD_FINDING,
        suggested_finding=suggested,
    )

    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.5")])],
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert _finding_codes(ptr_table_result) == ["PTR_TABLE_VALUE_MISMATCH"]
    assert ptr_table_result.codex_reviews[0].verdict is CodexReviewVerdict.ADD_FINDING
    assert ptr_table_result.codex_reviews[0].suggested_finding == suggested


def test_ptr_compare_codex_audit_failed_review_fails_task(tmp_path: Path) -> None:
    audit_service = FakePtrCodexAuditService(status=CodexReviewStatus.FAILED)

    _, status = _run_parameter_compare_task(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.5")])],
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
    )

    assert status.status == TaskState.ERROR
    assert "FAKE_CODEX_FAILED" in (status.error_message or "")


def test_ptr_compare_codex_audit_service_exception_fails_task(tmp_path: Path) -> None:
    audit_service = ExplodingPtrCodexAuditService()

    _, status = _run_parameter_compare_task(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.5")])],
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
    )

    assert status.status == TaskState.ERROR
    assert "codex audit service exploded" in (status.error_message or "")


def test_ptr_compare_codex_audit_parameter_finding_generates_ptr_parameter_target(tmp_path: Path) -> None:
    audit_service = FakePtrCodexAuditService()

    _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.5")])],
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
    )

    request, _ = audit_service.calls[0]
    assert request.targets[0].target_type.value == "ptr_parameter"


def test_ptr_compare_codex_audit_clause_finding_generates_ptr_clause_target(tmp_path: Path) -> None:
    task_service = TaskService()
    audit_service = FakePtrCodexAuditService()
    usecase = PTRCompareUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=FakePdfParser(),
        ptr_extractor=FakePTRExtractor(),
        report_extractor=FakeReportFieldExtractor(),
        inspection_table_extractor=ClauseMismatchInspectionTableExtractor(),
        scope_filter=TrackingScopeFilter(),
        table_reference_compare=TrackingTableCompare(),
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
    )

    status = usecase.run(
        ptr_file_name="ptr.pdf",
        ptr_content=b"%PDF-1.4 ptr",
        report_file_name="report.pdf",
        report_content=b"%PDF-1.4 report",
        content_type="application/pdf",
    )

    result = task_service.get_result(status.task_id)
    ptr_clause_result = _check_result(result, "PTR_CLAUSE")
    assert ptr_clause_result.codex_reviews[0].target.target_type.value == "ptr_clause"


def test_ptr_compare_codex_audit_no_findings_does_not_call_audit_service(tmp_path: Path) -> None:
    audit_service = FakePtrCodexAuditService()

    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.4")])],
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
    )

    assert _check_result(result, "PTR_TABLE").codex_reviews == []
    assert audit_service.calls == []


def test_ptr_compare_codex_audit_batches_without_omitting_targets(tmp_path: Path) -> None:
    audit_service = FakePtrCodexAuditService()
    report_records = [_record(f"参数{index}", f"actual-{index}") for index in range(6)]
    ptr_records = [_record(f"参数{index}", f"expected-{index}") for index in range(6)]

    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", ptr_records),
        report_tables=[_canonical_table("report-table-1", "1", report_records)],
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
        ptr_codex_evidence_builder=PtrCodexEvidenceBuilder(max_targets_per_batch=2),
    )

    ptr_table_result = _check_result(result, "PTR_TABLE")
    assert len(ptr_table_result.codex_reviews) == 6
    assert [len(request.targets) for request, _ in audit_service.calls] == [2, 2, 2]


def test_ptr_compare_task_audit_options_override_default_target_selection(tmp_path: Path) -> None:
    audit_service = FakePtrCodexAuditService()

    result = _run_parameter_compare_usecase(
        tmp_path,
        ptr_table=_canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")]),
        report_tables=[_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.5")])],
        codex_audit_enabled=True,
        codex_audit_service=audit_service,
        audit_options={
            "included_check_ids": "PTR_TABLE",
            "included_finding_codes": "PTR_TABLE_VALUE_MISMATCH",
            "max_targets_per_batch": 1,
            "max_parallel_jobs": 2,
            "timeout_seconds": 900,
        },
    )

    assert len(audit_service.calls) == 1
    assert audit_service.calls[0][0].targets[0].check_id == "PTR_TABLE"
    assert audit_service.timeout_overrides == [900]
    assert result.metadata["audit_options_source"] == "user_override"
    assert result.metadata["audit_options"]["included_check_ids"] == ["PTR_TABLE"]
    assert result.metadata["audit_options"]["included_finding_codes"] == ["PTR_TABLE_VALUE_MISMATCH"]
    assert result.metadata["audit_options"]["max_targets_per_batch"] == 1
    assert result.metadata["audit_options"]["max_parallel_jobs"] == 2
    assert result.metadata["audit_options"]["timeout_seconds"] == 900
    assert result.metadata["effective_audit_options"]["included_check_ids"] == ["PTR_TABLE"]
    assert result.metadata["effective_audit_options"]["included_finding_codes"] == ["PTR_TABLE_VALUE_MISMATCH"]
    assert result.metadata["effective_audit_options"]["max_targets_per_batch"] == 1
    assert result.metadata["effective_audit_options"]["max_parallel_jobs"] == 2
    assert result.metadata["effective_audit_options"]["timeout_seconds"] == 900
    assert result.metadata["codex_audit"]["audit_scope"] == "targeted"


class ClauseMismatchInspectionTableExtractor:
    def extract_table(self, parsed_pdf: ParsedPdf) -> InspectionTable:
        return InspectionTable(
            table_id="report-inspection-table",
            items=[
                InspectionItem(
                    sequence_raw="1",
                    sequence=1,
                    standard_clause="2.1",
                    standard_requirement="外观应粗糙",
                    source_page=4,
                )
            ],
        )


def _run_parameter_compare_usecase(
    tmp_path: Path,
    *,
    ptr_table: CanonicalTable | None,
    report_tables: list[CanonicalTable],
    extra_ptr_tables: list[PTRTable] | None = None,
    codex_audit_enabled: bool = False,
    codex_audit_service=None,
    ptr_codex_evidence_builder: PtrCodexEvidenceBuilder | None = None,
    audit_options=None,
):
    task_service, status = _run_parameter_compare_task(
        tmp_path,
        ptr_table=ptr_table,
        report_tables=report_tables,
        extra_ptr_tables=extra_ptr_tables,
        codex_audit_enabled=codex_audit_enabled,
        codex_audit_service=codex_audit_service,
        ptr_codex_evidence_builder=ptr_codex_evidence_builder,
        audit_options=audit_options,
    )

    assert status.status == TaskState.COMPLETED, status.error_message
    return task_service.get_result(status.task_id)


def _run_parameter_compare_task(
    tmp_path: Path,
    *,
    ptr_table: CanonicalTable | None,
    report_tables: list[CanonicalTable],
    extra_ptr_tables: list[PTRTable] | None = None,
    codex_audit_enabled: bool = False,
    codex_audit_service=None,
    ptr_codex_evidence_builder: PtrCodexEvidenceBuilder | None = None,
    audit_options=None,
):
    task_service = TaskService()
    if codex_audit_service is None:
        codex_audit_service = FakePtrCodexAuditService()
    report_pdf_tables = [_pdf_table_from_canonical(table) for table in report_tables]
    report_pdf = ParsedPdf(
        file_id="report-fixture",
        file_name="report.pdf",
        page_count=1,
        pages=[PdfPage(page_number=5, text="表 1 参数", tables=report_pdf_tables)],
    )
    usecase = PTRCompareUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=FakePdfParser({"report.pdf": report_pdf}),
        ptr_extractor=FakePTRExtractor(_ptr_document(ptr_table=ptr_table, extra_tables=extra_ptr_tables or [])),
        report_extractor=FakeReportFieldExtractor(_report_document()),
        inspection_table_extractor=FakeInspectionTableExtractor(),
        scope_filter=TrackingScopeFilter(),
        clause_text_compare=NoopClauseCompare(),
        codex_audit_enabled=codex_audit_enabled,
        codex_audit_service=codex_audit_service,
        ptr_codex_evidence_builder=ptr_codex_evidence_builder,
    )

    status = usecase.run(
        ptr_file_name="ptr.pdf",
        ptr_content=b"%PDF-1.4 ptr",
        report_file_name="report.pdf",
        report_content=b"%PDF-1.4 report",
        content_type="application/pdf",
        audit_options=audit_options,
    )

    return task_service, status


def _run_scope_aware_usecase(
    tmp_path: Path,
    *,
    report_extractor: ScopeAwareReportExtractor | None = None,
    inspection_table_extractor: ScopeAwareInspectionTableExtractor | None = None,
):
    task_service = TaskService()
    report_pdf = ParsedPdf(
        file_id="report-1539-like",
        file_name="report.pdf",
        page_count=100,
        pages=[
            PdfPage(page_number=3, text="检验项目：2.2、2.5、2.6（除生物相容性、电磁兼容性）"),
            PdfPage(
                page_number=5,
                text=(
                    "型号规格或其他说明\n"
                    "序号 1～序号 118 为 GB 9706.1-2020 标准的内容\n"
                    "序号 119～156 为 GB9706.\n"
                    "202-2021 标准的内容"
                ),
            ),
        ],
    )
    usecase = PTRCompareUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=FakePdfParser({"report.pdf": report_pdf}),
        ptr_extractor=FakePTRExtractor(_scope_aware_ptr_document()),
        report_extractor=report_extractor or ScopeAwareReportExtractor(),
        inspection_table_extractor=inspection_table_extractor or ScopeAwareInspectionTableExtractor(),
        table_reference_compare=TrackingTableCompare(),
        codex_audit_service=FakePtrCodexAuditService(verdict=CodexReviewVerdict.UNCERTAIN),
    )

    status = usecase.run(
        ptr_file_name="ptr.pdf",
        ptr_content=b"%PDF-1.4 ptr",
        report_file_name="report.pdf",
        report_content=b"%PDF-1.4 report",
        content_type="application/pdf",
    )

    assert status.status == TaskState.COMPLETED, status.error_message
    return task_service.get_result(status.task_id)


def _scope_aware_ptr_document() -> PTRDocument:
    return PTRDocument(
        clauses=[
            PTRClause(
                clause_id="ptr-2.1",
                number=PTRClauseNumber.from_string("2.1"),
                title="产品型号",
                body_text="产品型号应符合产品技术要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.2.1",
                number=PTRClauseNumber.from_string("2.2.1"),
                title="心脏脉冲电场消融仪输出",
                body_text="心脏脉冲电场消融仪输出电压、电流应符合产品技术要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.2.2",
                number=PTRClauseNumber.from_string("2.2.2"),
                title="心脏脉冲电场消融仪输出波形图和波形参数",
                body_text="心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满足表 6 的要求。",
                scope_type=PTRScopeType.REQUIREMENT,
                table_references=[
                    TableReference(
                        table_number="6",
                        reference_text="表 6",
                        context="波形参数",
                        clause_id="ptr-2.2.2",
                    )
                ],
            ),
            PTRClause(
                clause_id="ptr-2.2.3",
                number=PTRClauseNumber.from_string("2.2.3"),
                title="脉冲上升时间",
                body_text="脉冲上升时间应不超过 700ns。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.2.4",
                number=PTRClauseNumber.from_string("2.2.4"),
                title="脉冲宽度",
                body_text="脉冲宽度应符合产品技术要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.2.5",
                number=PTRClauseNumber.from_string("2.2.5"),
                title="脉冲衰减",
                body_text="脉冲衰减应在 10%内。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.2.6",
                number=PTRClauseNumber.from_string("2.2.6"),
                title="最大输出能量",
                body_text="单个脉冲最大输出能量应小于 258mJ。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.2.7",
                number=PTRClauseNumber.from_string("2.2.7"),
                title="保护功能",
                body_text="心脏脉冲电场消融仪应具有温度超限保护和过流保护功能。",
                scope_type=PTRScopeType.GROUP_CLAUSE,
            ),
            PTRClause(
                clause_id="ptr-2.2.7.1",
                number=PTRClauseNumber.from_string("2.2.7.1"),
                title="温度超限保护",
                body_text="心脏脉冲电场消融仪应具有温度超限保护功能。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.2.7.2",
                number=PTRClauseNumber.from_string("2.2.7.2"),
                title="过流保护",
                body_text="心脏脉冲电场消融仪应具有过流保护功能。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.3",
                number=PTRClauseNumber.from_string("2.3"),
                title="外观",
                body_text="外观应符合产品技术要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.4",
                number=PTRClauseNumber.from_string("2.4"),
                title="生物性能",
                body_text="生物性能和生物相容性应符合产品技术要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.5.1.1",
                number=PTRClauseNumber.from_string("2.5.1.1"),
                title="电气安全",
                body_text="电气安全应符合 GB 9706.1-2020 标准的要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.5.1.2",
                number=PTRClauseNumber.from_string("2.5.1.2"),
                title="电磁兼容性能",
                body_text="电磁兼容性能应符合 YY 9706.102-2021 标准的要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.5.2.1",
                number=PTRClauseNumber.from_string("2.5.2.1"),
                title="电气安全",
                body_text="应符合 GB 9706.1-2020 和 GB9706.202-2021 标准的要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.5.2.2",
                number=PTRClauseNumber.from_string("2.5.2.2"),
                title="电磁兼容性",
                body_text="电磁兼容性应符合 YY 9706.102-2021 标准的要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.5.3.1",
                number=PTRClauseNumber.from_string("2.5.3.1"),
                title="电气安全",
                body_text="电气安全应符合 GB 9706.1-2020 和 GB9706.202-2021 标准的要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.5.3.2",
                number=PTRClauseNumber.from_string("2.5.3.2"),
                title="电磁兼容性",
                body_text="电磁兼容性应符合 YY 9706.102-2021 标准的要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.6",
                number=PTRClauseNumber.from_string("2.6"),
                title="软件功能",
                body_text="软件功能应符合产品技术要求。",
                scope_type=PTRScopeType.REQUIREMENT,
                table_references=[
                    TableReference(
                        table_number="6",
                        reference_text="表 6",
                        context="软件功能",
                        clause_id="ptr-2.6",
                    )
                ],
            ),
            PTRClause(
                clause_id="ptr-2.7",
                number=PTRClauseNumber.from_string("2.7"),
                title="环境试验",
                body_text="环境试验应符合产品技术要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
            PTRClause(
                clause_id="ptr-2.8",
                number=PTRClauseNumber.from_string("2.8"),
                title="包装",
                body_text="包装应符合产品技术要求。",
                scope_type=PTRScopeType.REQUIREMENT,
            ),
        ],
        tables=[_scope_waveform_table(), _scope_software_table()],
    )


def _scope_waveform_table() -> PTRTable:
    return _ptr_table(
        CanonicalTable(
            table_id="ptr-2.2.2-table-6-waveform",
            table_number="6",
            caption="表 6 波形参数",
            parameter_name_column="参数",
            value_columns=["PULSE 3", "PF Reversible"],
            parameter_records=[
                ParameterRecord(parameter_name="脉冲个数", values={"PULSE 3": "1500", "PF Reversible": "1"}),
                ParameterRecord(parameter_name="脉冲组数", values={"PULSE 3": "12", "PF Reversible": "1"}),
                ParameterRecord(parameter_name="脉冲组间隔", values={"PULSE 3": "210±1 msec", "PF Reversible": "/"}),
                ParameterRecord(parameter_name="脉冲对间隔", values={"PULSE 3": "1.12msec±4μsec", "PF Reversible": "/"}),
                ParameterRecord(parameter_name="脉冲宽度", values={"PULSE 3": "0.9μsec±20%", "PF Reversible": "0.9μsec±20%"}),
                ParameterRecord(parameter_name="脉冲相间隔", values={"PULSE 3": "1μsec±20%", "PF Reversible": "1μsec±20%"}),
                ParameterRecord(parameter_name="波形类型", values={"PULSE 3": "三相", "PF Reversible": "双相"}),
                ParameterRecord(parameter_name="正峰值/负峰值", values={"PULSE 3": "5±20%", "PF Reversible": "1±0.1"}),
                ParameterRecord(parameter_name="电流水平", values={"PULSE 3": "1-100%", "PF Reversible": "1-100%"}),
            ],
        )
    ).model_copy(update={"referenced_by_clause_ids": ["ptr-2.2.2"]})


def _scope_software_table() -> PTRTable:
    return _ptr_table(
        CanonicalTable(
            table_id="ptr-2.6-table-6-software",
            table_number="6",
            caption="表 6 软件功能",
            parameter_name_column="功能",
            value_columns=["要求"],
            parameter_records=[
                ParameterRecord(parameter_name="功率监测", dimensions={"组件": "射频消融仪"}, values={"要求": "具备"}),
                ParameterRecord(parameter_name="阻抗监测", dimensions={"组件": "射频消融仪"}, values={"要求": "具备"}),
                ParameterRecord(parameter_name="阻抗监测", dimensions={"组件": "心脏脉冲电场消融仪"}, values={"要求": "具备"}),
                ParameterRecord(parameter_name="温度监测", dimensions={"组件": "心脏脉冲电场消融仪"}, values={"要求": "具备"}),
                ParameterRecord(
                    parameter_name="与射频消融仪、导管接口单元CIU通信",
                    dimensions={"组件": "心脏脉冲电场消融仪"},
                    values={"要求": "具备"},
                ),
            ],
        )
    ).model_copy(update={"referenced_by_clause_ids": ["ptr-2.6"]})


def _scope_aware_report_items() -> list[InspectionItem]:
    return [
        InspectionItem(
            sequence_raw="1",
            sequence=1,
            standard_clause="GB 9706.1-2020",
            standard_requirement="GB 9706.1-2020 标准通用安全要求。",
            test_result="符合要求",
            conclusion="符合",
            source_page=6,
        ),
        InspectionItem(
            sequence_raw="118",
            sequence=118,
            standard_clause="GB 9706.1-2020",
            standard_requirement="GB 9706.1-2020 标准通用安全要求。",
            test_result="符合要求",
            conclusion="符合",
            source_page=45,
        ),
        InspectionItem(
            sequence_raw="119",
            sequence=119,
            standard_clause="GB9706.202-2021",
            standard_requirement="GB9706.202-2021 标准专用安全要求。",
            test_result="符合要求",
            conclusion="符合",
            source_page=46,
        ),
        InspectionItem(
            sequence_raw="14",
            sequence=14,
            standard_clause="5.5",
            item_name="供电电压、电流类型、供电方式和频率",
            standard_requirement="2.6 软件功能相关供电项目摘录。",
            test_result="符合要求",
            conclusion="符合",
            source_page=50,
            row_index_in_page=1,
        ),
        InspectionItem(
            sequence_raw="52",
            sequence=52,
            standard_clause="7.9",
            item_name="随附文件",
            standard_requirement="外部标准随附文件中引用 2.2.3 脉冲上升时间。",
            test_result="符合要求",
            conclusion="符合",
            source_page=60,
            row_index_in_page=1,
        ),
        InspectionItem(
            sequence_raw="65",
            sequence=65,
            standard_clause="9.2.2",
            item_name="俘获区域",
            standard_requirement="外部标准俘获区域说明中引用 2.2.1、2.2.4、2.2.5、2.2.6。",
            test_result="符合要求",
            conclusion="符合",
            source_page=70,
            row_index_in_page=1,
        ),
        InspectionItem(
            sequence_raw="续\n129",
            sequence=129,
            is_continuation=True,
            standard_clause="201.7.9.\n2.14",
            standard_requirement="使用说明书还可见 201.15.4.101.1 和 201.15.4.101.2。",
            test_result="符合要求",
            conclusion="符合",
            source_page=85,
            row_index_in_page=1,
        ),
        InspectionItem(
            sequence_raw="156",
            sequence=156,
            standard_clause="GB9706.202-2021",
            standard_requirement="GB9706.202-2021 标准专用安全要求。",
            test_result="符合要求",
            conclusion="符合",
            source_page=98,
        ),
        InspectionItem(
            sequence_raw="157",
            sequence=157,
            standard_clause="2.2",
            standard_requirement="2.2.1 心脏脉冲电场消融仪输出\n电压：3333V（峰值）\n单位：V",
            test_result="3375",
            result_values=["3375"],
            conclusion="符合",
            source_page=99,
            row_index_in_page=3,
        ),
        InspectionItem(
            sequence_raw="电流：57A（峰值）\n单位：A",
            item_name="59",
            standard_clause="/",
            source_page=99,
            row_index_in_page=4,
        ),
        InspectionItem(
            sequence_raw="2.2.2 心脏脉冲电场消融仪输出波形图和波形参数",
            standard_requirement="心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满足表 6 的要求。",
            test_result="符合要求",
            conclusion="符合",
            source_page=99,
            row_index_in_page=5,
        ),
        InspectionItem(
            sequence_raw="续\n157",
            sequence=157,
            is_continuation=True,
            standard_clause="2.2",
            standard_requirement="2.2.3 脉冲上升时间\n脉冲上升时间应不超过 700ns。",
            test_result="430 / 455",
            result_values=["430", "455"],
            conclusion="符合",
            source_page=100,
            row_index_in_page=1,
        ),
        InspectionItem(
            sequence_raw="2.2.4 脉冲宽度",
            standard_requirement="脉冲宽度应符合产品技术要求。",
            test_result="260 / 205 / 1μsec±20%",
            result_values=["260", "205", "1μsec±20%"],
            conclusion="符合",
            source_page=100,
            row_index_in_page=2,
        ),
        InspectionItem(
            sequence_raw="续\n157",
            sequence=157,
            is_continuation=True,
            standard_clause="2.2",
            standard_requirement="2.2.5 脉冲衰减\n脉冲衰减应在 10%内。",
            test_result="1%",
            result_values=["1%"],
            conclusion="符合",
            source_page=101,
            row_index_in_page=1,
        ),
        InspectionItem(
            sequence_raw="2.2.6 最大输出能量",
            standard_requirement="单个脉冲最大输出能量应小于 258mJ。",
            test_result="159",
            result_values=["159"],
            conclusion="符合",
            source_page=101,
            row_index_in_page=2,
        ),
        InspectionItem(
            sequence_raw="2.2.7 保护功能",
            standard_requirement="温度超限保护和过流保护功能符合要求。",
            test_result="符合要求",
            conclusion="符合",
            source_page=101,
            row_index_in_page=3,
        ),
        InspectionItem(
            sequence_raw="158",
            sequence=158,
            standard_clause="2.5",
            standard_requirement="电气安全应符合产品技术要求。",
            test_result="符合要求",
            conclusion="符合",
            source_page=99,
            row_index_in_page=6,
        ),
        InspectionItem(
            sequence_raw="159",
            sequence=159,
            standard_clause="2.6",
            standard_requirement="软件功能应符合产品技术要求。",
            test_result="符合要求",
            conclusion="符合",
            source_page=99,
            row_index_in_page=7,
        ),
    ]


def _ptr_document(*, ptr_table: CanonicalTable | None, extra_tables: list[PTRTable]) -> PTRDocument:
    tables = []
    if ptr_table is not None:
        tables.append(_ptr_table(ptr_table))
    tables.extend(extra_tables)
    return PTRDocument(
        clauses=[
            PTRClause(
                clause_id="ptr-2.1",
                number=PTRClauseNumber.from_string("2.1"),
                title="脉冲参数",
                body_text="脉冲参数应符合表1。",
                table_references=[TableReference(table_number="1", reference_text="表1")],
            )
        ],
        tables=tables,
    )


def _ptr_table(canonical_table: CanonicalTable) -> PTRTable:
    return PTRTable(
        table_id=canonical_table.table_id,
        table_number=canonical_table.table_number,
        title=canonical_table.caption,
        canonical_table=canonical_table,
    )


def _report_document() -> ReportDocument:
    scope_field = ReportField(name="检验项目", value="2.1", metadata={"items": ["2.1"]})
    return ReportDocument(
        third_page=ThirdPageInfo(fields=[scope_field]),
        fields=[scope_field],
    )


def _canonical_table(
    table_id: str,
    table_number: str,
    records: list[ParameterRecord],
    *,
    caption: str | None = None,
) -> CanonicalTable:
    return CanonicalTable(
        table_id=table_id,
        table_number=table_number,
        caption=caption or f"表 {table_number} 参数",
        parameter_name_column="参数",
        value_columns=["标准设置"],
        condition_columns=["型号"],
        parameter_records=records,
    )


def _record(
    name: str,
    value: str,
    *,
    unit: str | None = None,
    conditions: dict[str, str] | None = None,
    values: dict[str, str] | None = None,
) -> ParameterRecord:
    return ParameterRecord(
        parameter_name=name,
        dimensions={"型号": "全部型号"},
        values=values or {"标准设置": value},
        unit=unit,
        conditions=conditions or {},
    )


def _pdf_table_from_canonical(canonical_table: CanonicalTable) -> PdfTable:
    condition_keys = _condition_keys(canonical_table.parameter_records)
    value_keys = _value_keys(canonical_table.parameter_records)
    rows = [["参数", "单位", "型号", *condition_keys, *value_keys]]
    for record in canonical_table.parameter_records:
        rows.append(
            [
                record.parameter_name or "",
                record.unit or "",
                record.dimensions.get("型号", ""),
                *[record.conditions.get(key, "") for key in condition_keys],
                *[record.values.get(key, "") for key in value_keys],
            ]
        )
    return build_pdf_table(
        rows=rows,
        page=5,
        table_id=canonical_table.table_id.replace("canonical:", ""),
        table_number=canonical_table.table_number,
        caption=canonical_table.caption,
    )


def _condition_keys(records: list[ParameterRecord]) -> list[str]:
    keys: list[str] = []
    for record in records:
        for key in record.conditions:
            if key in record.dimensions:
                continue
            if key not in keys:
                keys.append(key)
    return keys


def _value_keys(records: list[ParameterRecord]) -> list[str]:
    keys: list[str] = []
    for record in records:
        for key in record.values:
            if key not in keys:
                keys.append(key)
    return keys or ["标准设置"]


def _check_result(result, check_id: str):
    return next(check_result for check_result in result.check_results if check_result.check_id == check_id)


def _finding_codes(check_result) -> list[str]:
    return [finding.code for finding in check_result.findings]
