import pytest
from pydantic import ValidationError

from app.domain.common import Location, SourceType
from app.domain.table import (
    CanonicalCell,
    CanonicalTable,
    CanonicalTableDiagnostics,
    ColumnPath,
    ParameterRecord,
    Table,
    TableCell,
    TableHeader,
)


def test_table_cell_accepts_legacy_and_new_coordinate_names() -> None:
    cell = TableCell(
        cell_id="cell-r1c2",
        row=1,
        col=2,
        rowspan=2,
        colspan=3,
        page_number=4,
        bbox=(10, 20, 30, 45),
        raw_text="≤ 10 mA",
        normalized_text="<=10mA",
    )

    payload = cell.model_dump(mode="json")

    assert cell.row_index == 1
    assert cell.column_index == 2
    assert cell.row_span == 2
    assert cell.column_span == 3
    assert cell.location is not None
    assert payload["raw_text"] == "≤ 10 mA"
    assert payload["normalized_text"] == "<=10mA"
    assert payload["page_number"] == 4
    assert payload["bbox"] == {"x0": 10.0, "y0": 20.0, "x1": 30.0, "y1": 45.0}


def test_table_cell_rejects_invalid_indices_and_spans() -> None:
    with pytest.raises(ValidationError):
        TableCell(row=-1, col=0)

    with pytest.raises(ValidationError):
        TableCell(row=0, col=0, rowspan=0)


def test_table_header_preserves_multi_row_paths() -> None:
    header = TableHeader(
        rows=[
            ["参数", "心房", "", "心室", ""],
            ["", "常规数值", "标准设置", "常规数值", "标准设置"],
        ],
        column_paths=[
            ["参数"],
            ["心房", "常规数值"],
            ["心房", "标准设置"],
            ["心室", "常规数值"],
            ["心室", "标准设置"],
        ],
    )

    assert header.row_count == 2
    assert header.column_count == 5
    assert header.model_dump(mode="json")["column_paths"][2] == ["心房", "标准设置"]


def test_parameter_record_supports_dimensions_values_and_source_rows() -> None:
    record = ParameterRecord(
        parameter_name="脉冲宽度(ms)",
        dimensions={"型号": "全部型号"},
        values={"标准设置": "0.4", "允许误差": "±20μs"},
        source_rows=[1, 2],
        source_cell_ids=["cell-r1c0", "cell-r1c3"],
    )

    payload = record.model_dump(mode="json")

    assert record.parameter_id == "脉冲宽度(ms)"
    assert record.raw_name == "脉冲宽度(ms)"
    assert payload["dimensions"] == {"型号": "全部型号"}
    assert payload["values"]["标准设置"] == "0.4"
    assert payload["source_rows"] == [1, 2]


def test_canonical_table_serializes_header_cells_records_and_source_locations() -> None:
    location = Location(source_type=SourceType.PTR, page_number=5)
    table = Table(
        table_id="table-1",
        table_number="1",
        title="性能参数",
        cells=[TableCell(row=0, col=0, raw_text="参数", is_header=True, page_number=5)],
        page_span=(5, 6),
        locations=[location],
    )
    canonical = CanonicalTable(
        table_id="canonical-1",
        source_table_id=table.table_id,
        caption="表 1 性能参数",
        headers=[TableHeader(rows=[["参数", "型号", "标准设置"]])],
        parameter_name_column="参数",
        value_columns=["标准设置"],
        unit_column="单位",
        condition_columns=["型号"],
        source_locations=[location],
        parameter_records=[
            ParameterRecord(
                parameter_name="基础频率(bpm)",
                dimensions={"型号": "全部型号"},
                values={"标准设置": "60"},
                source_rows=[2],
            )
        ],
    )

    payload = canonical.model_dump(mode="json")

    assert payload["headers"][0]["rows"] == [["参数", "型号", "标准设置"]]
    assert payload["parameter_records"][0]["parameter_name"] == "基础频率(bpm)"
    assert payload["source_locations"][0]["page_number"] == 5


def test_legacy_canonical_cell_column_path_and_diagnostics_are_json_serializable() -> None:
    cell = CanonicalCell(
        text="标准设置",
        row=1,
        col=2,
        row_span=2,
        col_span=3,
        bbox=(1, 2, 3, 4),
        is_header=True,
        source="inferred",
        role="header",
        propagated_from=(0, 2),
        confidence=0.92,
    )
    path = ColumnPath(leaf_col=2, labels=["心房", "标准设置"], role="value")
    diagnostics = CanonicalTableDiagnostics(
        header_row_count=2,
        inferred_rowspans=1,
        inferred_colspans=1,
        repeated_header_removed=1,
        continuation_merged=True,
        structure_confidence=0.85,
        notes=["跨页续表已合并"],
    )

    assert cell.row_index == 1
    assert cell.column_index == 2
    assert path.key == "心房 / 标准设置"
    assert diagnostics.model_dump(mode="json")["continuation_merged"] is True
    assert '"structure_confidence":0.85' in diagnostics.model_dump_json()


def test_canonical_table_accepts_legacy_shape_with_column_paths_and_parameter_records() -> None:
    table = CanonicalTable(
        table_id="canonical-table-1",
        page_start=5,
        page_end=6,
        caption="表 2 输出参数",
        table_number=2,
        n_rows=4,
        n_cols=3,
        cells=[
            CanonicalCell(text="参数", row=0, col=0, is_header=True),
            CanonicalCell(text="标准设置", row=0, col=1, is_header=True),
            CanonicalCell(text="脉冲宽度", row=1, col=0),
            CanonicalCell(text="0.4 ms", row=1, col=1),
        ],
        header_rows=[["参数", "标准设置", "单位"]],
        body_rows=[1, 2, 3],
        column_paths=[ColumnPath(leaf_col=1, labels=["标准设置"], role="value")],
        diagnostics=CanonicalTableDiagnostics(header_row_count=1, structure_confidence=0.9),
        parameter_records=[
            ParameterRecord(parameter_name="脉冲宽度", values={"标准设置": "0.4 ms"}, source_rows=[1])
        ],
    )

    payload = table.model_dump(mode="json")

    assert table.page_start == 5
    assert table.page_end == 6
    assert table.table_number == "2"
    assert table.n_rows == 4
    assert table.n_cols == 3
    assert table.get_cell(1, 0).text == "脉冲宽度"
    assert table.column_paths[0].key == "标准设置"
    assert payload["cells"][3]["text"] == "0.4 ms"
    assert payload["diagnostics"]["structure_confidence"] == 0.9
    assert table.model_dump_json()
