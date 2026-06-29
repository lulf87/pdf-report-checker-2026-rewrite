from pathlib import Path

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
from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument, PTRTable, TableReference
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
    ) -> None:
        self.verdict = verdict
        self.status = status
        self.suggested_finding = suggested_finding
        self.error = error
        self.calls: list[tuple] = []

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
        },
    )

    assert len(audit_service.calls) == 1
    assert audit_service.calls[0][0].targets[0].check_id == "PTR_TABLE"
    assert result.metadata["audit_options_source"] == "user_override"
    assert result.metadata["audit_options"]["included_check_ids"] == ["PTR_TABLE"]
    assert result.metadata["audit_options"]["included_finding_codes"] == ["PTR_TABLE_VALUE_MISMATCH"]
    assert result.metadata["audit_options"]["max_targets_per_batch"] == 1
    assert result.metadata["audit_options"]["max_parallel_jobs"] == 2
    assert result.metadata["effective_audit_options"]["included_check_ids"] == ["PTR_TABLE"]
    assert result.metadata["effective_audit_options"]["included_finding_codes"] == ["PTR_TABLE_VALUE_MISMATCH"]
    assert result.metadata["effective_audit_options"]["max_targets_per_batch"] == 1
    assert result.metadata["effective_audit_options"]["max_parallel_jobs"] == 2
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

    assert status.status == TaskState.COMPLETED
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
