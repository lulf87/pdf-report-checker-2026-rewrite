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
