from app.domain.table import CanonicalTable, ParameterRecord
from app.rules.ptr.parameter_compare import compare_parameter_tables


def _table(table_id: str, records: list[ParameterRecord]) -> CanonicalTable:
    return CanonicalTable(
        table_id=table_id,
        caption="表 1 参数",
        parameter_name_column="参数",
        value_columns=["标准设置", "允许误差"],
        condition_columns=["型号"],
        parameter_records=records,
    )


def test_parameter_compare_reports_missing_parameter_and_value_mismatch() -> None:
    expected = _table(
        "ptr-table-1",
        [
            ParameterRecord(parameter_name="脉冲宽度(ms)", dimensions={"型号": "全部型号"}, values={"标准设置": "0.4"}),
            ParameterRecord(parameter_name="基础频率(bpm)", dimensions={"型号": "全部型号"}, values={"标准设置": "60"}),
        ],
    )
    actual = _table(
        "report-table-1",
        [
            ParameterRecord(parameter_name="脉冲宽度(ms)", dimensions={"型号": "全部型号"}, values={"标准设置": "0.5"}),
        ],
    )

    findings = compare_parameter_tables(
        expected,
        actual,
        task_id="task-ptr",
        clause_number="2.1.3",
        table_number="1",
    )

    codes = [finding.code for finding in findings]
    assert codes == ["PTR_TABLE_VALUE_MISMATCH", "PTR_TABLE_PARAM_MISSING"]
    assert findings[0].expected == "0.4"
    assert findings[0].actual == "0.5"
    assert findings[1].metadata["parameter_name"] == "基础频率(bpm)"


def test_parameter_compare_keeps_multidimension_sibling_records_separate() -> None:
    expected = _table(
        "ptr-table-1",
        [
            ParameterRecord(parameter_name="脉冲宽度(ms)", dimensions={"axis_1": "心房"}, values={"标准设置": "3.0"}),
            ParameterRecord(parameter_name="脉冲宽度(ms)", dimensions={"axis_1": "心室"}, values={"标准设置": "2.5"}),
        ],
    )
    actual = _table(
        "report-table-1",
        [
            ParameterRecord(parameter_name="脉冲宽度(ms)", dimensions={"axis_1": "心房"}, values={"标准设置": "3.0"}),
            ParameterRecord(parameter_name="脉冲宽度(ms)", dimensions={"axis_1": "心室"}, values={"标准设置": "2.4"}),
        ],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert len(findings) == 1
    assert findings[0].code == "PTR_TABLE_VALUE_MISMATCH"
    assert findings[0].metadata["dimensions"] == {"axis_1": "心室"}


def test_parameter_compare_does_not_report_condition_mismatch_when_conditions_match() -> None:
    expected = _table(
        "ptr-table-1",
        [
            ParameterRecord(
                parameter_name="输出幅度",
                dimensions={"型号": "全部型号"},
                conditions={"试验条件": "@240Ω"},
                values={"标准设置": "3.5"},
            )
        ],
    )
    actual = _table(
        "report-table-1",
        [
            ParameterRecord(
                parameter_name="输出幅度",
                dimensions={"型号": "全部型号"},
                conditions={"试验条件": "@240Ω"},
                values={"标准设置": "3.5"},
            )
        ],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert findings == []


def test_parameter_compare_reports_condition_mismatch() -> None:
    expected = _table(
        "ptr-table-1",
        [
            ParameterRecord(
                parameter_name="输出幅度",
                dimensions={"型号": "全部型号"},
                conditions={"试验条件": "@240Ω"},
                values={"标准设置": "3.5"},
            )
        ],
    )
    actual = _table(
        "report-table-1",
        [
            ParameterRecord(
                parameter_name="输出幅度",
                dimensions={"型号": "全部型号"},
                conditions={"试验条件": "@500Ω"},
                values={"标准设置": "3.5"},
            )
        ],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert [finding.code for finding in findings] == ["PTR_TABLE_CONDITION_MISMATCH"]
    assert findings[0].expected == {"试验条件": "@240Ω"}
    assert findings[0].actual == {"试验条件": "@500Ω"}
    assert findings[0].metadata["field_name"] == "conditions"


def test_parameter_compare_reports_condition_missing_on_one_side() -> None:
    expected = _table(
        "ptr-table-1",
        [
            ParameterRecord(
                parameter_name="输出幅度",
                dimensions={"型号": "全部型号"},
                conditions={"检测条件": "@240Ω"},
                values={"标准设置": "3.5"},
            )
        ],
    )
    actual = _table(
        "report-table-1",
        [ParameterRecord(parameter_name="输出幅度", dimensions={"型号": "全部型号"}, values={"标准设置": "3.5"})],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert [finding.code for finding in findings] == ["PTR_TABLE_CONDITION_MISMATCH"]
    assert findings[0].expected == {"检测条件": "@240Ω"}
    assert findings[0].actual == {}


def test_parameter_compare_reports_tolerance_mismatch_with_specific_code() -> None:
    expected = _table(
        "ptr-table-1",
        [ParameterRecord(parameter_name="脉冲宽度", dimensions={"型号": "全部型号"}, values={"标准设置": "0.4", "允许误差": "±20 μs"})],
    )
    actual = _table(
        "report-table-1",
        [ParameterRecord(parameter_name="脉冲宽度", dimensions={"型号": "全部型号"}, values={"标准设置": "0.4", "允许误差": "±30μs"})],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert [finding.code for finding in findings] == ["PTR_TABLE_TOLERANCE_MISMATCH"]
    assert findings[0].expected == "±20 μs"
    assert findings[0].actual == "±30μs"
    assert findings[0].metadata["value_key"] == "允许误差"


def test_parameter_compare_does_not_report_tolerance_mismatch_when_tolerance_matches() -> None:
    expected = _table(
        "ptr-table-1",
        [ParameterRecord(parameter_name="脉冲宽度", dimensions={"型号": "全部型号"}, values={"标准设置": "0.4", "允许误差": "±20 μs"})],
    )
    actual = _table(
        "report-table-1",
        [ParameterRecord(parameter_name="脉冲宽度", dimensions={"型号": "全部型号"}, values={"标准设置": "0.4", "允许误差": "±20μs"})],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert findings == []


def test_parameter_compare_treats_numeric_expression_variants_as_equivalent() -> None:
    expected = _table(
        "ptr-table-1",
        [
            ParameterRecord(parameter_name="输出幅度", dimensions={"型号": "全部型号"}, values={"标准设置": "1"}),
            ParameterRecord(parameter_name="阻抗", dimensions={"型号": "全部型号"}, values={"标准设置": "1,000"}),
            ParameterRecord(parameter_name="灵敏度", dimensions={"型号": "全部型号"}, values={"标准设置": "１．０"}),
        ],
    )
    actual = _table(
        "report-table-1",
        [
            ParameterRecord(parameter_name="输出幅度", dimensions={"型号": "全部型号"}, values={"标准设置": "1.0"}),
            ParameterRecord(parameter_name="阻抗", dimensions={"型号": "全部型号"}, values={"标准设置": "1000"}),
            ParameterRecord(parameter_name="灵敏度", dimensions={"型号": "全部型号"}, values={"标准设置": "1.0"}),
        ],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert findings == []


def test_parameter_compare_treats_comparator_range_and_tolerance_variants_as_equivalent() -> None:
    expected = _table(
        "ptr-table-1",
        [
            ParameterRecord(parameter_name="最小输出", dimensions={"型号": "全部型号"}, values={"限值": "不小于5"}),
            ParameterRecord(parameter_name="最大输出", dimensions={"型号": "全部型号"}, values={"限值": "≤10"}),
            ParameterRecord(parameter_name="工作范围", dimensions={"型号": "全部型号"}, values={"范围": "5~10"}),
            ParameterRecord(parameter_name="允许误差项", dimensions={"型号": "全部型号"}, values={"允许误差": "允许误差0.5"}),
        ],
    )
    actual = _table(
        "report-table-1",
        [
            ParameterRecord(parameter_name="最小输出", dimensions={"型号": "全部型号"}, values={"限值": "≥5"}),
            ParameterRecord(parameter_name="最大输出", dimensions={"型号": "全部型号"}, values={"限值": "<=10"}),
            ParameterRecord(parameter_name="工作范围", dimensions={"型号": "全部型号"}, values={"范围": "5-10"}),
            ParameterRecord(parameter_name="允许误差项", dimensions={"型号": "全部型号"}, values={"允许误差": "+/-0.5"}),
        ],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert findings == []


def test_parameter_compare_reports_clear_numeric_semantic_mismatches() -> None:
    expected = _table(
        "ptr-table-1",
        [
            ParameterRecord(parameter_name="最小输出", dimensions={"型号": "全部型号"}, values={"标准设置": "≥5"}),
            ParameterRecord(parameter_name="工作范围", dimensions={"型号": "全部型号"}, values={"标准设置": "5~10"}),
        ],
    )
    actual = _table(
        "report-table-1",
        [
            ParameterRecord(parameter_name="最小输出", dimensions={"型号": "全部型号"}, values={"标准设置": "≥6"}),
            ParameterRecord(parameter_name="工作范围", dimensions={"型号": "全部型号"}, values={"标准设置": "5~12"}),
        ],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert [finding.code for finding in findings] == ["PTR_TABLE_VALUE_MISMATCH", "PTR_TABLE_VALUE_MISMATCH"]
    assert [finding.metadata["parameter_name"] for finding in findings] == ["最小输出", "工作范围"]


def test_parameter_compare_matches_segmented_thresholds_by_dimensions() -> None:
    expected = _table(
        "ptr-table-1",
        [
            ParameterRecord(parameter_name="阈值", dimensions={"负载": "@240Ω"}, values={"限值": "≥5"}),
            ParameterRecord(parameter_name="阈值", dimensions={"负载": "@500Ω"}, values={"限值": "≥5"}),
        ],
    )
    actual = _table(
        "report-table-1",
        [
            ParameterRecord(parameter_name="阈值", dimensions={"负载": "@240Ω"}, values={"限值": "≥6"}),
            ParameterRecord(parameter_name="阈值", dimensions={"负载": "@500Ω"}, values={"限值": "≥5"}),
        ],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert [finding.code for finding in findings] == ["PTR_TABLE_TOLERANCE_MISMATCH"]
    assert findings[0].metadata["dimensions"] == {"负载": "@240Ω"}


def test_parameter_compare_reports_missing_segment_without_cross_condition_compare() -> None:
    expected = _table(
        "ptr-table-1",
        [
            ParameterRecord(parameter_name="阈值", dimensions={"型号": "全部型号"}, conditions={"负载": "@240Ω"}, values={"限值": "≥5"}),
            ParameterRecord(parameter_name="阈值", dimensions={"型号": "全部型号"}, conditions={"负载": "@500Ω"}, values={"限值": "≥5"}),
        ],
    )
    actual = _table(
        "report-table-1",
        [
            ParameterRecord(parameter_name="阈值", dimensions={"型号": "全部型号"}, conditions={"负载": "@500Ω"}, values={"限值": "≥5"}),
        ],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert [finding.code for finding in findings] == ["PTR_TABLE_PARAM_MISSING"]
    assert findings[0].metadata["conditions"] == {"负载": "@240Ω"}


def test_parameter_compare_warns_when_segment_key_is_ambiguous() -> None:
    expected = _table(
        "ptr-table-1",
        [ParameterRecord(parameter_name="阈值", dimensions={"型号": "全部型号"}, values={"限值": "≥5"})],
    )
    actual = _table(
        "report-table-1",
        [
            ParameterRecord(parameter_name="阈值", dimensions={"型号": "全部型号"}, conditions={"负载": "@240Ω"}, values={"限值": "≥5"}),
            ParameterRecord(parameter_name="阈值", dimensions={"型号": "全部型号"}, conditions={"负载": "@500Ω"}, values={"限值": "≥5"}),
        ],
    )

    findings = compare_parameter_tables(expected, actual, task_id="task-ptr", clause_number="2.1.3", table_number="1")

    assert [finding.code for finding in findings] == ["PTR_TABLE_SEGMENT_AMBIGUOUS"]
    assert findings[0].severity == "warn"
