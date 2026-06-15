from pathlib import Path

from app.application.ptr_compare_usecase import PTRCompareUseCase
from app.application.task_service import TaskService
from app.domain.common import Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.pdf import ParsedPdf, PdfPage, PdfTable
from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument, PTRTable, TableReference
from app.domain.report import InspectionItem, InspectionTable, ReportDocument, ReportField, ThirdPageInfo
from app.domain.result import CheckStatus
from app.domain.table import CanonicalTable, ParameterRecord
from app.domain.task import TaskState, TaskType
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


def _run_parameter_compare_usecase(
    tmp_path: Path,
    *,
    ptr_table: CanonicalTable | None,
    report_tables: list[CanonicalTable],
    extra_ptr_tables: list[PTRTable] | None = None,
):
    task_service = TaskService()
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
    )

    status = usecase.run(
        ptr_file_name="ptr.pdf",
        ptr_content=b"%PDF-1.4 ptr",
        report_file_name="report.pdf",
        report_content=b"%PDF-1.4 report",
        content_type="application/pdf",
    )

    assert status.status == TaskState.COMPLETED
    return task_service.get_result(status.task_id)


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


def _canonical_table(table_id: str, table_number: str, records: list[ParameterRecord]) -> CanonicalTable:
    return CanonicalTable(
        table_id=table_id,
        table_number=table_number,
        caption=f"表 {table_number} 参数",
        parameter_name_column="参数",
        value_columns=["标准设置"],
        condition_columns=["型号"],
        parameter_records=records,
    )


def _record(name: str, value: str, *, unit: str | None = None) -> ParameterRecord:
    return ParameterRecord(
        parameter_name=name,
        dimensions={"型号": "全部型号"},
        values={"标准设置": value},
        unit=unit,
    )


def _pdf_table_from_canonical(canonical_table: CanonicalTable) -> PdfTable:
    value_keys = _value_keys(canonical_table.parameter_records)
    rows = [["参数", "单位", "型号", *value_keys]]
    for record in canonical_table.parameter_records:
        rows.append(
            [
                record.parameter_name or "",
                record.unit or "",
                record.dimensions.get("型号", ""),
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
