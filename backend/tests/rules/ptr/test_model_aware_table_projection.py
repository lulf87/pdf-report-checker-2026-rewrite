from __future__ import annotations

from app.domain.common import Confidence, Location, SourceType
from app.domain.inspection_group import InspectionItemGroup
from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument, PTRTable, TableReference
from app.domain.report import FirstPageInfo, InspectionItem, ReportDocument, ReportField, SampleDescriptionRow
from app.domain.table import CanonicalTable, ParameterRecord
from app.rules.ptr.atomic_compare import build_atomic_comparison_rows, build_atomic_requirements
from app.rules.ptr.model_context import build_report_model_context
from app.rules.ptr.table_registry import build_ptr_table_registry, classify_table_axis


def test_report_model_context_extracts_single_primary_model_from_homepage_and_sample_description() -> None:
    report = ReportDocument(
        first_page=FirstPageInfo(
            model_spec=ReportField(
                name="型号规格",
                value="6232",
                normalized_value="6232",
                location=Location(source_type=SourceType.REPORT, page_number=1),
                confidence=Confidence.HIGH,
            )
        ),
        sample_description_rows=[
            SampleDescriptionRow(
                row_id="sample-1",
                model=ReportField(
                    name="规格型号",
                    value="6232",
                    normalized_value="6232",
                    location=Location(source_type=SourceType.REPORT, page_number=4),
                    confidence=Confidence.HIGH,
                ),
            )
        ],
    )

    context = build_report_model_context(report)

    assert context.primary_model == "6232"
    assert [candidate.value for candidate in context.model_candidates] == ["6232"]
    assert context.model_candidates[0].source == "report_homepage"
    assert context.model_candidates[0].page == 1
    assert context.model_candidates[0].confidence == "high"
    assert "/Users/" not in context.model_dump_json()


def test_report_model_context_keeps_multiple_models_without_guessing_primary() -> None:
    report = ReportDocument(
        fields=[
            ReportField(name="型号规格", value="6232", location=Location(source_type=SourceType.REPORT, page_number=1)),
            ReportField(name="型号规格", value="5826", location=Location(source_type=SourceType.REPORT, page_number=1)),
        ]
    )

    context = build_report_model_context(report)

    assert context.primary_model is None
    assert {candidate.value for candidate in context.model_candidates} == {"6232", "5826"}
    assert any("multiple_model_candidates" in diagnostic for diagnostic in context.diagnostics)


def test_table_axis_classifier_distinguishes_model_preset_and_load_axes() -> None:
    model_context = build_report_model_context(
        ReportDocument(fields=[ReportField(name="型号规格", value="6232")])
    )

    assert classify_table_axis(["6232", "5826"], model_context).axis_type == "model"
    assert classify_table_axis(["PULSE3", "PF Reversible"], model_context).axis_type == "preset"
    assert classify_table_axis(["@240Ω", "@500Ω", "@2000Ω"], model_context).axis_type == "load"
    assert classify_table_axis(["正常状态", "单一故障状态"], model_context).axis_type == "condition"


def test_table_axis_classifier_expands_grouped_model_column_labels() -> None:
    model_context = build_report_model_context(
        ReportDocument(fields=[ReportField(name="型号规格", value="6232")])
    )

    axis = classify_table_axis(["6232、6231", "6132、6131"], model_context)

    assert axis.axis_type == "model"
    assert axis.labels == ["6232", "6231", "6132", "6131"]


def test_ptr_table_registry_indexes_parent_table_with_model_axis() -> None:
    model_context = build_report_model_context(ReportDocument(fields=[ReportField(name="型号规格", value="6232")]))
    ptr_doc = _model_table_ptr_document()

    registry = build_ptr_table_registry(ptr_doc, model_context)

    entry = next(item for item in registry if item.table_number == "3")
    assert entry.parent_clause == "2.1"
    assert entry.table_title == "功能参数"
    assert entry.row_labels == ["起搏模式", "模式转换"]
    assert entry.column_axes[0].axis_type == "model"
    assert entry.column_axes[0].labels == ["6232", "5826"]
    assert entry.source_page == 3


def test_model_aware_table_projection_selects_report_model_column_and_marks_other_models_not_applicable() -> None:
    ptr_doc = _model_table_ptr_document()
    ptr_doc.metadata["report_model_context"] = build_report_model_context(
        ReportDocument(fields=[ReportField(name="型号规格", value="6232")])
    ).model_dump(mode="json")
    child = ptr_doc.get_clause_by_string("2.1.1")

    requirements = build_atomic_requirements(child, ptr_doc)

    selected = next(requirement for requirement in requirements if requirement.metadata.get("model_column") == "6232")
    other = next(requirement for requirement in requirements if requirement.metadata.get("model_column") == "5826")
    assert selected.atomic_id == "2.1.1:table3:起搏模式:6232"
    assert selected.expected_text == "VVI"
    assert selected.operator == "functional_or_equal"
    assert selected.metadata["parent_clause"] == "2.1"
    assert selected.metadata["table_row_label"] == "起搏模式"
    assert selected.metadata["axis_type"] == "model"
    assert other.metadata["not_applicable_by_model"] is True


def test_model_aware_table_projection_functional_row_matches_report_group_conclusion() -> None:
    ptr_doc = _model_table_ptr_document()
    ptr_doc.metadata["report_model_context"] = build_report_model_context(
        ReportDocument(fields=[ReportField(name="型号规格", value="6232")])
    ).model_dump(mode="json")
    child = ptr_doc.get_clause_by_string("2.1.1")
    group = InspectionItemGroup(
        item_no="38",
        display_item_no="38",
        pages=[20],
        rows=[
            InspectionItem(
                sequence_raw="38",
                sequence=38,
                standard_clause="2.1",
                standard_requirement="2.1 基本电性能指标\n2.1.1 起搏模式",
                test_result="符合要求",
                conclusion="符合",
                source_page=20,
            )
        ],
    )

    rows = build_atomic_comparison_rows(child, ptr_doc, [group])
    selected = next(row for row in rows if row.atomic_id == "2.1.1:table3:起搏模式:6232")
    other = next(row for row in rows if row.atomic_id == "2.1.1:table3:起搏模式:5826")

    assert selected.expected == "VVI"
    assert selected.actual == "符合要求"
    assert selected.status == "match"
    assert selected.table_key == "2.1:表3:功能参数"
    assert "型号 6232" in (selected.reason or "")
    assert other.status == "not_applicable"


def test_model_aware_table_projection_maps_product_physical_clause_to_parent_table_rows() -> None:
    ptr_doc = _model_physical_table_ptr_document()
    ptr_doc.metadata["report_model_context"] = build_report_model_context(
        ReportDocument(fields=[ReportField(name="型号规格", value="6232")])
    ).model_dump(mode="json")
    child = ptr_doc.get_clause_by_string("2.1.12")

    requirements = build_atomic_requirements(child, ptr_doc)

    selected_rows = [requirement for requirement in requirements if requirement.metadata.get("model_column") == "6232"]
    other_rows = [requirement for requirement in requirements if requirement.metadata.get("model_column") == "5826"]
    assert [requirement.label for requirement in selected_rows] == ["尺寸", "重量"]
    assert selected_rows[0].table_key == "2.1:表2:基本参数"
    assert selected_rows[0].expected_text == "10 mm"
    assert selected_rows[1].expected_text == "20 g"
    assert all(requirement.metadata.get("not_applicable_by_model") is True for requirement in other_rows)


def test_model_projected_result_uses_page_of_matching_report_subrow() -> None:
    ptr_doc = _model_physical_table_ptr_document()
    ptr_doc.metadata["report_model_context"] = build_report_model_context(
        ReportDocument(fields=[ReportField(name="型号规格", value="6232")])
    ).model_dump(mode="json")
    child = ptr_doc.get_clause_by_string("2.1.12")
    group = InspectionItemGroup(
        item_no="38",
        display_item_no="38",
        pages=[20, 22],
        rows=[
            InspectionItem(
                sequence_raw="38",
                sequence=38,
                standard_clause="2.1",
                standard_requirement="2.1 基本电性能指标",
                conclusion="符合",
                source_page=20,
            ),
            InspectionItem(
                sequence_raw="尺寸：10 mm",
                item_name="尺寸",
                test_result="10 mm",
                source_page=22,
            ),
            InspectionItem(
                sequence_raw="重量：20 g",
                item_name="重量",
                test_result="20 g",
                source_page=22,
            ),
        ],
    )

    rows = build_atomic_comparison_rows(child, ptr_doc, [group])
    selected = [row for row in rows if row.model_column == "6232"]

    assert selected
    assert all(row.status == "match" for row in selected)
    assert all(row.report_page == 22 for row in selected)


def test_generic_referenced_tables_expand_chamber_and_condition_rows() -> None:
    sensed_clause = PTRClause(
        clause_id="ptr-2.1.6.1",
        number=PTRClauseNumber.from_string("2.1.6.1"),
        title="感知不应期",
        body_text="感知不应期应符合表4的要求。",
        table_references=[TableReference(table_number="4", reference_text="表4", clause_id="ptr-2.1.6.1")],
    )
    blanking_clause = PTRClause(
        clause_id="ptr-2.1.11",
        number=PTRClauseNumber.from_string("2.1.11"),
        title="空白期/最短不应期",
        body_text="空白期/最短不应期应符合表6的要求。",
        table_references=[TableReference(table_number="6", reference_text="表6", clause_id="ptr-2.1.11")],
    )
    document = PTRDocument(
        clauses=[sensed_clause, blanking_clause],
        tables=[
            PTRTable(
                table_id="ptr-table-4",
                table_number="4",
                title="表4 感知不应期",
                canonical_table=CanonicalTable(table_id="canonical-table-4"),
                referenced_by_clause_ids=["ptr-2.1.6.1"],
                metadata={
                    "raw_rows": [
                        ["腔室", "模式", "感知不应期"],
                        ["心室", "VVI", "95 ms ±10 ms"],
                        ["心房", "AAI", "345 ms -10/+15 ms"],
                    ]
                },
            ),
            PTRTable(
                table_id="ptr-table-6",
                table_number="6",
                title="表6 空白期/最短不应期",
                canonical_table=CanonicalTable(table_id="canonical-table-6"),
                referenced_by_clause_ids=["ptr-2.1.11"],
                metadata={
                        "raw_rows": [
                            ["事件", "心房", "心室"],
                            ["心房感知", "80 ms ±10 ms", "-"],
                            ["心室感知", "可程控(PVAB-55ms) ±10 ms", "95 ms ±10 ms"],
                            ["模式", "事件", "心房"],
                            ["DDTA、DDTAV", "心房感知", "205 ms -10/+15 ms"],
                        ]
                },
            ),
        ],
    )

    sensed = build_atomic_requirements(sensed_clause, document)
    blanking = build_atomic_requirements(blanking_clause, document)

    assert {(row.label, row.condition, row.expected_text) for row in sensed} == {
        ("心室 / VVI", "心室 / VVI", "95 ms ±10 ms"),
        ("心房 / AAI", "心房 / AAI", "345 ms -10/+15 ms"),
    }
    assert {(row.label, row.condition, row.expected_text) for row in blanking} >= {
        ("心房感知", "心房", "80 ms ±10 ms"),
        ("心室感知", "心房", "可程控(PVAB-55ms) ±10 ms"),
        ("心室感知", "心室", "95 ms ±10 ms"),
        ("DDTA、DDTAV / 心房感知", "DDTA、DDTAV / 心房感知", "205 ms -10/+15 ms"),
    }
    assert all(row.label != "模式" for row in blanking)


def _model_table_ptr_document() -> PTRDocument:
    table = CanonicalTable(
        table_id="ptr-table-3",
        table_number="3",
        caption="表3 功能参数",
        page_start=3,
        value_columns=["6232", "5826"],
        parameter_records=[
            ParameterRecord(parameter_name="起搏模式", values={"6232": "VVI", "5826": "DDD"}),
            ParameterRecord(parameter_name="模式转换", values={"6232": "具备", "5826": "具备"}),
        ],
    )
    return PTRDocument(
        clauses=[
            PTRClause(
                clause_id="ptr-2.1",
                number=PTRClauseNumber.from_string("2.1"),
                title="基本电性能指标",
                body_text="表2 基本参数\n表3 功能参数",
            ),
            PTRClause(
                clause_id="ptr-2.1.1",
                number=PTRClauseNumber.from_string("2.1.1"),
                title="起搏模式",
                body_text="心脏起搏器的起搏模式应符合表3的要求。",
                table_references=[TableReference(table_number="3", reference_text="表3", clause_id="ptr-2.1.1")],
            ),
        ],
        tables=[
            PTRTable(
                table_id="ptr-table-3",
                table_number="3",
                title="表3 功能参数",
                page=3,
                canonical_table=table,
                referenced_by_clause_ids=["ptr-2.1"],
            )
        ],
    )


def _model_physical_table_ptr_document() -> PTRDocument:
    table = CanonicalTable(
        table_id="ptr-table-2",
        table_number="2",
        caption="表2 基本参数",
        page_start=3,
        value_columns=["6232", "5826"],
        parameter_records=[
            ParameterRecord(parameter_name="尺寸", values={"6232": "10 mm", "5826": "12 mm"}),
            ParameterRecord(parameter_name="重量", values={"6232": "20 g", "5826": "24 g"}),
        ],
    )
    return PTRDocument(
        clauses=[
            PTRClause(
                clause_id="ptr-2.1",
                number=PTRClauseNumber.from_string("2.1"),
                title="基本电性能指标",
                body_text="表2 基本参数\n表3 功能参数",
            ),
            PTRClause(
                clause_id="ptr-2.1.12",
                number=PTRClauseNumber.from_string("2.1.12"),
                title="产品物理特性及参数",
                body_text="产品物理特性及参数应符合表2的要求。",
                table_references=[TableReference(table_number="2", reference_text="表2", clause_id="ptr-2.1.12")],
            ),
        ],
        tables=[
            PTRTable(
                table_id="ptr-table-2",
                table_number="2",
                title="表2 基本参数",
                page=3,
                canonical_table=table,
                referenced_by_clause_ids=["ptr-2.1"],
            )
        ],
    )
