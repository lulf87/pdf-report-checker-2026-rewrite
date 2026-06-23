import json
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.api.routes_ptr_compare import get_ptr_compare_usecase
from app.api.routes_tasks import get_task_service
from app.application.ptr_compare_usecase import PTRCompareUseCase
from app.application.task_service import TaskService
from app.domain.codex_review import CodexReviewConfidence, CodexReviewResult, CodexReviewStatus, CodexReviewVerdict
from app.domain.pdf import ParsedPdf, PdfPage
from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument, PTRTable, TableReference
from app.domain.report import InspectionItem, InspectionTable, ReportDocument, ReportField, ThirdPageInfo
from app.domain.table import CanonicalTable, ParameterRecord
from app.domain.task import TaskState, TaskType
from app.infrastructure.storage.local_file_store import LocalFileStore
from app.main import create_app
from tests.fixtures.table_fixture_builder import build_pdf_table


GOLDEN_EXPECTED = (
    Path(__file__).resolve().parents[3]
    / "fixtures"
    / "golden"
    / "api"
    / "ptr_compare_e2e.expected.json"
)


class FixturePdfParser:
    def __init__(self, parsed_by_name: dict[str, ParsedPdf]) -> None:
        self.parsed_by_name = parsed_by_name

    def parse(self, file_path: Path) -> ParsedPdf:
        return self.parsed_by_name.get(
            file_path.name,
            ParsedPdf(file_id=file_path.stem, file_name=file_path.name, page_count=1),
        )


class FixturePTRExtractor:
    def extract(self, parsed_pdf: ParsedPdf) -> PTRDocument:
        document = _ptr_document()
        document.parsed_pdf = parsed_pdf
        return document


class FixtureReportExtractor:
    def extract(self, parsed_pdf: ParsedPdf) -> ReportDocument:
        scope_field = ReportField(name="检验项目", value="2.1-2.3", metadata={"items": ["2.1", "2.2", "2.3"]})
        return ReportDocument(
            parsed_pdf=parsed_pdf,
            third_page=ThirdPageInfo(fields=[scope_field]),
            fields=[scope_field],
        )


class FixtureInspectionTableExtractor:
    def extract_table(self, parsed_pdf: ParsedPdf) -> InspectionTable:
        return InspectionTable(
            table_id="report-inspection-table",
            items=[
                InspectionItem(
                    sequence_raw="1",
                    sequence=1,
                    standard_clause="2.1",
                    standard_requirement="电阻值应<10Ω。",
                    source_page=4,
                ),
                InspectionItem(
                    sequence_raw="2",
                    sequence=2,
                    standard_clause="2.2",
                    standard_requirement="缺失表应符合表99。",
                    source_page=4,
                ),
                InspectionItem(
                    sequence_raw="3",
                    sequence=3,
                    standard_clause="2.3",
                    standard_requirement="脉冲参数应符合表1。",
                    source_page=4,
                ),
            ],
        )


class FakeMandatoryCodexAuditService:
    def review(self, request, evidence_package):  # noqa: ANN001
        del evidence_package
        return [
            CodexReviewResult(
                review_id=f"api-fixture-codex:{target.target_id}",
                request_id=request.request_id,
                task_id=request.task_id,
                target=target,
                status=CodexReviewStatus.SUCCEEDED,
                verdict=CodexReviewVerdict.CONFIRM,
                confidence=CodexReviewConfidence.MEDIUM,
                reasoning_summary="API fixture Codex audit confirm.",
                evidence_refs=[ref.ref_id for ref in target.evidence_refs],
            )
            for target in request.targets
        ]


def test_ptr_compare_upload_result_and_json_export_include_clause_table_and_parameter_findings(tmp_path: Path) -> None:
    client = _client_with_fixture_usecase(tmp_path)

    create_response = client.post(
        "/api/tasks/ptr-compare",
        files={
            "ptr_file": ("ptr.pdf", b"%PDF-1.4\n% fixture ptr\n", "application/pdf"),
            "report_file": ("report.pdf", b"%PDF-1.4\n% fixture report\n", "application/pdf"),
        },
    )

    assert create_response.status_code == 200
    task_payload = create_response.json()
    task_id = task_payload["task_id"]
    assert task_payload["task_type"] == TaskType.PTR_COMPARE
    assert task_payload["status"] == TaskState.COMPLETED
    assert {item["file_name"] for item in task_payload["input_files"]} == {"ptr.pdf", "report.pdf"}

    status_response = client.get(f"/api/tasks/{task_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == TaskState.COMPLETED

    result_response = client.get(f"/api/tasks/{task_id}/result")
    assert result_response.status_code == 200
    result_payload = result_response.json()
    findings = result_payload["findings"]
    codes = {finding["code"] for finding in findings}

    assert result_payload["task_type"] == TaskType.PTR_COMPARE
    assert result_payload["summary"]["error_count"] == 5
    assert result_payload["summary"]["warn_count"] == 0
    assert "PTR_CLAUSE_TEXT_MISMATCH" in codes
    assert "PTR_TABLE_MISSING" in codes
    assert "PTR_TABLE_VALUE_MISMATCH" in codes
    assert "PTR_TABLE_UNIT_MISMATCH" in codes
    assert "PTR_TABLE_PARAM_MISSING" in codes

    clause_finding = _finding_by_code(findings, "PTR_CLAUSE_TEXT_MISMATCH")
    assert clause_finding["check_id"] == "PTR_CLAUSE"
    assert clause_finding["severity"] == "error"
    assert clause_finding["message"]
    assert clause_finding["expected"] == "电阻值应<=10Ω。"
    assert clause_finding["actual"] == "电阻值应<10Ω。"
    assert clause_finding["evidence"]

    table_finding = _finding_by_code(findings, "PTR_TABLE_MISSING")
    assert table_finding["check_id"] == "PTR_TABLE"
    assert table_finding["metadata"]["table_number"] == "99"
    assert table_finding["missing_evidence"]

    value_finding = _finding_by_code(findings, "PTR_TABLE_VALUE_MISMATCH")
    assert value_finding["expected"] == "0.4"
    assert value_finding["actual"] == "0.5"
    assert value_finding["evidence"]

    unit_finding = _finding_by_code(findings, "PTR_TABLE_UNIT_MISMATCH")
    assert unit_finding["expected"] == "ms"
    assert unit_finding["actual"] == "s"

    missing_param_finding = _finding_by_code(findings, "PTR_TABLE_PARAM_MISSING")
    assert missing_param_finding["metadata"]["parameter_name"] == "基础频率"

    export_response = client.get(f"/api/tasks/{task_id}/export", params={"format": "json"})
    assert export_response.status_code == 200
    export_payload = export_response.json()
    export_codes = {finding["code"] for finding in export_payload["findings"]}
    assert export_payload["task"]["task_type"] == TaskType.PTR_COMPARE
    assert {"PTR_TABLE_VALUE_MISMATCH", "PTR_TABLE_UNIT_MISMATCH", "PTR_TABLE_PARAM_MISSING"} <= export_codes

    expected_golden = json.loads(GOLDEN_EXPECTED.read_text(encoding="utf-8"))
    assert _compact_golden_summary(export_payload) == expected_golden


def _client_with_fixture_usecase(tmp_path: Path) -> TestClient:
    task_service = TaskService()
    app = create_app()
    app.dependency_overrides[get_task_service] = lambda: task_service
    app.dependency_overrides[get_ptr_compare_usecase] = lambda: PTRCompareUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=FixturePdfParser({"report.pdf": _report_pdf()}),
        ptr_extractor=FixturePTRExtractor(),
        report_extractor=FixtureReportExtractor(),
        inspection_table_extractor=FixtureInspectionTableExtractor(),
        codex_audit_service=FakeMandatoryCodexAuditService(),
    )
    return TestClient(app)


def _ptr_document() -> PTRDocument:
    return PTRDocument(
        clauses=[
            PTRClause(
                clause_id="ptr-2.1",
                number=PTRClauseNumber.from_string("2.1"),
                title="电阻",
                body_text="电阻值应≤10Ω。",
            ),
            PTRClause(
                clause_id="ptr-2.2",
                number=PTRClauseNumber.from_string("2.2"),
                title="缺失表",
                body_text="缺失表应符合表99。",
                table_references=[TableReference(table_number="99", reference_text="表99", clause_id="ptr-2.2")],
            ),
            PTRClause(
                clause_id="ptr-2.3",
                number=PTRClauseNumber.from_string("2.3"),
                title="脉冲参数",
                body_text="脉冲参数应符合表1。",
                table_references=[TableReference(table_number="1", reference_text="表1", clause_id="ptr-2.3")],
            ),
        ],
        tables=[
            PTRTable(
                table_id="ptr-table-1",
                table_number="1",
                title="表 1 脉冲参数",
                canonical_table=_ptr_canonical_table(),
            )
        ],
    )


def _ptr_canonical_table() -> CanonicalTable:
    return CanonicalTable(
        table_id="ptr-table-1",
        table_number="1",
        caption="表 1 脉冲参数",
        parameter_name_column="参数",
        value_columns=["标准设置"],
        condition_columns=["型号"],
        parameter_records=[
            _record("脉冲宽度", "0.4", unit="ms"),
            _record("基础频率", "60", unit="bpm"),
        ],
    )


def _report_pdf() -> ParsedPdf:
    return ParsedPdf(
        file_id="report-fixture",
        file_name="report.pdf",
        page_count=1,
        pages=[
            PdfPage(
                page_number=5,
                text="表 1 脉冲参数",
                tables=[
                    build_pdf_table(
                        rows=[
                            ["参数", "单位", "型号", "标准设置"],
                            ["脉冲宽度", "s", "全部型号", "0.5"],
                        ],
                        page=5,
                        table_id="report-table-1",
                        table_number="1",
                        caption="表 1 脉冲参数",
                    )
                ],
            )
        ],
    )


def _record(name: str, value: str, *, unit: str | None = None) -> ParameterRecord:
    return ParameterRecord(
        parameter_name=name,
        dimensions={"型号": "全部型号"},
        values={"标准设置": value},
        unit=unit,
    )


def _finding_by_code(findings: list[dict[str, Any]], code: str) -> dict[str, Any]:
    return next(finding for finding in findings if finding["code"] == code)


def _compact_golden_summary(export_payload: dict[str, Any]) -> dict[str, Any]:
    findings = export_payload["findings"]
    codes = sorted({finding["code"] for finding in findings})
    severity_counts = dict(sorted(Counter(finding["severity"] for finding in findings).items()))
    return {
        "task_type": export_payload["task"]["task_type"],
        "finding_code_count": len(codes),
        "finding_count_by_severity": severity_counts,
        "finding_codes": codes,
        "has_ptr_table_value_mismatch": "PTR_TABLE_VALUE_MISMATCH" in codes,
        "has_ptr_table_unit_mismatch": "PTR_TABLE_UNIT_MISMATCH" in codes,
        "has_ptr_table_param_missing": "PTR_TABLE_PARAM_MISSING" in codes,
    }
