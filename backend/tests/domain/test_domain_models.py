from pydantic import ValidationError

from app.domain.common import BoundingBox, Evidence, EvidenceMethod, Location, SourceType
from app.domain.findings import DiffFragment, Finding, MissingEvidence, Severity
from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument, PTRScopeType, TableReference
from app.domain.report import (
    ComponentKey,
    FirstPageInfo,
    InspectionItem,
    InspectionTable,
    LabelOCRField,
    LabelOCRResult,
    PageNumberEvidence,
    PhotoEvidence,
    ReportDocument,
    ReportField,
    SampleDescriptionRow,
    ThirdPageInfo,
)
from app.domain.table import CanonicalTable, ParameterRecord, Table, TableCell


def test_common_finding_models_serialize_stable_json() -> None:
    bbox = BoundingBox(x0=10, y0=20, x1=30, y1=45)
    location = Location(
        source_id="report-1",
        source_type=SourceType.REPORT,
        page_number=3,
        bbox=bbox,
        section="third_page",
        table_id="sample-desc",
        row_index=1,
        column_name="型号规格",
        text_span=(4, 12),
    )
    evidence = Evidence(
        id="ev-1",
        source_type=SourceType.REPORT,
        location=location,
        raw_text="型号规格：ABC-1",
        normalized_text="ABC-1",
        value="ABC-1",
        method=EvidenceMethod.PDF_TEXT,
        confidence="high",
    )
    finding = Finding(
        id="finding-1",
        task_id="task-1",
        check_id="C01",
        severity=Severity.ERROR,
        code="C01_FIELD_MISMATCH",
        message="首页与第三页型号规格不一致",
        location=location,
        expected="ABC-1",
        actual="ABC-2",
        evidence=[evidence],
        missing_evidence=[
            MissingEvidence(
                label="第三页委托方",
                reason="PDF 文本层未抽取到字段",
                expected_source=SourceType.REPORT,
            )
        ],
        diff_fragments=[
            DiffFragment(kind="equal", text="ABC-"),
            DiffFragment(kind="delete", text="1"),
            DiffFragment(kind="insert", text="2"),
        ],
    )

    payload = finding.model_dump(mode="json")

    assert payload["severity"] == "error"
    assert payload["location"]["bbox"] == {"x0": 10.0, "y0": 20.0, "x1": 30.0, "y1": 45.0}
    assert payload["evidence"][0]["method"] == "pdf_text"
    assert payload["missing_evidence"][0]["expected_source"] == "report"
    assert payload["diff_fragments"][1] == {"kind": "delete", "text": "1", "source": None}
    assert bbox.width == 20
    assert bbox.height == 25


def test_location_rejects_invalid_page_and_bbox_order() -> None:
    with pytest_raises_validation_error("page_number"):
        Location(page_number=0)

    with pytest_raises_validation_error("x1"):
        BoundingBox(x0=10, y0=10, x1=5, y1=20)


def test_report_domain_models_keep_raw_and_normalized_values() -> None:
    first_page = FirstPageInfo(
        client=ReportField(name="委托方", raw_value=" 北京医院 ", normalized_value="北京医院"),
        sample_name=ReportField(name="样品名称", raw_value="样品 A", normalized_value="样品A"),
        model_spec=ReportField(name="型号规格", raw_value="ABC - 1", normalized_value="ABC-1"),
    )
    third_page = ThirdPageInfo(
        model_spec=ReportField(name="型号规格", raw_value='见"样品描述"栏', normalized_value="见样品描述栏"),
        production_date=ReportField(name="生产日期", raw_value="2026/01/08", normalized_value="2026-01-08"),
        batch_or_serial=ReportField(name="产品编号/批号", raw_value="SN 001", normalized_value="SN001"),
    )
    component_key = ComponentKey(name="主机", model="ABC-1", batch_or_serial="SN001")
    sample_row = SampleDescriptionRow(
        row_id="sample-1",
        sequence_raw="1",
        sequence=1,
        component_key=component_key,
        component_name=ReportField(name="部件名称", raw_value="主机", normalized_value="主机"),
        model=ReportField(name="规格型号", raw_value="ABC-1", normalized_value="ABC-1"),
        batch_or_serial=ReportField(name="序列号批号", raw_value="SN001", normalized_value="SN001"),
        production_date=ReportField(name="生产日期", raw_value="2026/01/08", normalized_value="2026-01-08"),
        expiration_date=ReportField(name="失效日期", raw_value="2028/01/08", normalized_value="2028-01-08"),
    )
    label = LabelOCRResult(
        label_id="label-1",
        fields=[
            LabelOCRField(
                name="型号规格",
                raw_value="型号规格：ABC-1",
                normalized_value="ABC-1",
                aliases=["型号", "规格型号"],
            )
        ],
        raw_blocks=["型号规格：ABC-1"],
        language="zh",
    )
    document = ReportDocument(
        first_page=first_page,
        third_page=third_page,
        sample_description_rows=[sample_row],
        inspection_table=InspectionTable(
            table_id="inspection",
            items=[
                InspectionItem(
                    sequence_raw="续1",
                    sequence=1,
                    is_continuation=True,
                    result_values=["符合要求"],
                    conclusion="符合",
                )
            ],
        ),
        photo_evidence=[PhotoEvidence(photo_id="photo-1", subject_name="主机", caption_text="图1 主机照片")],
        labels=[label],
        page_numbers=[PageNumberEvidence(page_number=1, displayed_number="1/10", total_pages=10)],
    )

    payload = document.model_dump(mode="json")

    assert payload["first_page"]["client"]["raw_value"] == " 北京医院 "
    assert payload["third_page"]["production_date"]["normalized_value"] == "2026-01-08"
    assert payload["sample_description_rows"][0]["expiration_date"]["raw_value"] == "2028/01/08"
    assert payload["sample_description_rows"][0]["component_key"]["identity"] == "主机|ABC-1|SN001"
    assert payload["inspection_table"]["items"][0]["is_continuation"] is True
    assert payload["labels"][0]["fields"][0]["aliases"] == ["型号", "规格型号"]


def test_ptr_clause_number_orders_and_tracks_hierarchy() -> None:
    numbers = [
        PTRClauseNumber.from_string("2.1.1"),
        PTRClauseNumber.from_string("2"),
        PTRClauseNumber.from_string("2.1.1.1"),
        PTRClauseNumber.from_string("2.1"),
    ]

    assert [str(item) for item in sorted(numbers)] == ["2", "2.1", "2.1.1", "2.1.1.1"]
    assert PTRClauseNumber.from_string("2.1.1.1").parent() == PTRClauseNumber.from_string("2.1.1")
    assert PTRClauseNumber.from_string("2.1.1").is_descendant_of(PTRClauseNumber.from_string("2.1"))


def test_ptr_document_serializes_clauses_scope_and_table_references() -> None:
    clause = PTRClause(
        clause_id="ptr-2.1.1",
        number="2.1.1",
        title="性能要求",
        body_text="应符合表 1 的要求。",
        normalized_text="应符合表1的要求。",
        scope_type=PTRScopeType.REQUIREMENT,
        table_references=[
            TableReference(
                table_number="1",
                raw_text="表 1",
                reference_text="见表 1",
            )
        ],
    )
    document = PTRDocument(clauses=[clause], chapter2_span=(2, 8))

    payload = document.model_dump(mode="json")

    assert payload["clauses"][0]["number"] == "2.1.1"
    assert payload["clauses"][0]["level"] == 3
    assert payload["clauses"][0]["scope_type"] == "requirement"
    assert payload["clauses"][0]["table_references"][0]["table_number"] == "1"


def test_table_models_preserve_cells_headers_and_parameter_records() -> None:
    cell = TableCell(
        cell_id="cell-r1c2",
        raw_value="≤ 10 mA",
        normalized_value="<=10mA",
        row_index=1,
        column_index=2,
        row_span=1,
        column_span=2,
        is_header=False,
    )
    table = Table(table_id="table-1", table_number="1", title="性能参数", cells=[cell], page_span=(4, 5))
    parameter = ParameterRecord(
        parameter_id="param-1",
        parameter_path=["电气安全", "漏电流"],
        raw_name="漏电流",
        normalized_name="漏电流",
        raw_value="≤ 10 mA",
        normalized_value="<=10mA",
        unit="mA",
        conditions={"模式": "正常状态"},
        source_cell_ids=["cell-r1c2"],
    )
    canonical = CanonicalTable(
        table_id="canonical-1",
        source_table_id="table-1",
        caption="表 1 性能参数",
        header_rows=[["项目", "要求"]],
        dimension_columns=["模式"],
        parameter_records=[parameter],
    )

    payload = canonical.model_dump(mode="json")

    assert table.model_dump(mode="json")["cells"][0]["column_span"] == 2
    assert payload["source_table_id"] == "table-1"
    assert payload["header_rows"] == [["项目", "要求"]]
    assert payload["parameter_records"][0]["parameter_path"] == ["电气安全", "漏电流"]
    assert payload["parameter_records"][0]["conditions"] == {"模式": "正常状态"}


def pytest_raises_validation_error(field_name: str):
    class _ValidationErrorContext:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, traceback):
            assert exc_type is ValidationError
            assert field_name in str(exc)
            return True

    return _ValidationErrorContext()
