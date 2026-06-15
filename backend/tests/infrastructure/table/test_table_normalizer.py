from app.domain.table import CanonicalTable
from app.infrastructure.table.table_normalizer import TableNormalizer
from tests.fixtures.table_fixture_builder import build_pdf_table


def test_double_header_generates_column_paths_and_legacy_headers() -> None:
    table = build_pdf_table(
        rows=[
            ["参数", "心房", "", "心室", ""],
            ["", "常规数值", "标准设置", "常规数值", "标准设置"],
            ["脉冲宽度(ms)", "0.1...(0.1)...1.5", "0.4", "0.1...(0.1)...1.5", "0.4"],
        ],
        table_number="1",
        caption="表 1 起搏参数",
    )

    canonical = TableNormalizer().normalize(table)

    assert isinstance(canonical, CanonicalTable)
    assert canonical.header_rows == [
        ["参数", "心房", "", "心室", ""],
        ["", "常规数值", "标准设置", "常规数值", "标准设置"],
    ]
    assert canonical.headers[0].column_paths == [
        ["参数"],
        ["心房", "常规数值"],
        ["心房", "标准设置"],
        ["心室", "常规数值"],
        ["心室", "标准设置"],
    ]
    assert TableNormalizer().to_legacy_headers(canonical) == [
        "参数",
        "心房 / 常规数值",
        "心房 / 标准设置",
        "心室 / 常规数值",
        "心室 / 标准设置",
    ]
    assert canonical.table_number == "1"
    assert canonical.metadata["table_number"] == "1"
    assert canonical.caption == "表 1 起搏参数"


def test_fill_down_applies_only_to_dimension_columns() -> None:
    table = build_pdf_table(
        rows=[
            ["参数", "型号", "常规数值", "标准设置", "允许误差"],
            ["脉冲宽度(ms)", "Edora 8 DR", "20...(5)...350", "180-170-160", "±20"],
            ["", "Edora 8 DR", "CLS模式下:20...(5)...350", "150-140-130", ""],
        ],
    )

    normalizer = TableNormalizer()
    canonical = normalizer.normalize(table)
    rows = normalizer.to_legacy_rows(canonical)

    assert rows[1][0] == "脉冲宽度(ms)"
    assert rows[1][4] == ""
    assert any("fill_down" in diagnostic for diagnostic in canonical.diagnostics)


def test_parameter_records_include_dimensions_values_and_units() -> None:
    table = build_pdf_table(
        rows=[
            ["参数", "单位", "型号", "标准设置", "允许误差"],
            ["脉冲宽度", "ms", "全部型号", "0.4", "±20μs"],
        ],
    )

    canonical = TableNormalizer().normalize(table)
    record = canonical.parameter_records[0]

    assert record.parameter_name == "脉冲宽度"
    assert record.unit == "ms"
    assert record.dimensions["型号"] == "全部型号"
    assert record.values["标准设置"] == "0.4"
    assert record.values["允许误差"] == "±20μs"


def test_parameter_records_include_condition_and_tolerance_synonym_fields() -> None:
    table = build_pdf_table(
        rows=[
            ["参数", "单位", "型号", "试验条件", "标准设置", "允差", "限值"],
            ["输出幅度", "V", "全部型号", "@240Ω", "3.5", "±10%", ">=2.0"],
        ],
    )

    canonical = TableNormalizer().normalize(table)
    record = canonical.parameter_records[0]

    assert "试验条件" in canonical.condition_columns
    assert record.dimensions["型号"] == "全部型号"
    assert record.conditions["试验条件"] == "@240Ω"
    assert record.values["允差"] == "±10%"
    assert record.values["限值"] == ">=2.0"


def test_continuation_table_preserves_source_and_diagnostics() -> None:
    first = build_pdf_table(
        rows=[["参数", "型号", "标准设置"], ["频率", "全部", "60"]],
        page=2,
        table_id="table-1a",
        table_number="1",
        caption="表 1 参数",
    )
    continuation = build_pdf_table(
        rows=[["参数", "型号", "标准设置"], ["脉宽", "全部", "0.4"]],
        page=3,
        table_id="table-1b",
        table_number="1",
        caption="续表 1 参数",
        metadata={"continuation_of": "table-1a"},
    )

    normalizer = TableNormalizer()
    normalized_first = normalizer.normalize(first)
    normalized_second = normalizer.normalize(continuation, continuation_of=normalized_first.table_id)

    assert normalized_first.source_locations[0].page_number == 2
    assert normalized_second.source_locations[0].page_number == 3
    assert normalized_second.metadata["continuation_of"] == normalized_first.table_id
    assert any("continuation" in diagnostic for diagnostic in normalized_second.diagnostics)
