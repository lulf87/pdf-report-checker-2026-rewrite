from app.domain.table import CanonicalTable, TableColumn
from app.infrastructure.table.table_semantics import TableSemantics


def test_column_role_synonyms_match_legacy_vocabulary() -> None:
    semantics = TableSemantics()

    cases = {
        ("参数",): "parameter",
        ("参数名称",): "parameter",
        ("适用型号",): "model",
        ("规格",): "model",
        ("型号",): "model",
        ("默认值",): "default",
        ("设置值",): "default",
        ("范围",): "value",
        ("检验结果",): "value",
        ("允许误差",): "tolerance",
        ("允差",): "tolerance",
        ("允许偏差",): "tolerance",
        ("限值",): "tolerance",
        ("阈值",): "tolerance",
        ("试验条件",): "condition",
        ("检测条件",): "condition",
        ("环境条件",): "condition",
        ("备注",): "remark",
    }

    for labels, expected_role in cases.items():
        assert semantics.infer_column_role(list(labels)) == expected_role


def test_unknown_role_is_counted_and_resettable() -> None:
    semantics = TableSemantics()

    assert semantics.infer_column_role(["未知字段"]) == "unknown"
    assert semantics.unknown_role_count == 1

    semantics.reset()
    assert semantics.unknown_role_count == 0


def test_split_path_semantics_detects_dimension_and_value_leaf() -> None:
    semantics = TableSemantics()

    dims, leaf_label, leaf_role = semantics.split_path_semantics(["心房", "标准设置"])

    assert dims == ["心房"]
    assert leaf_label == "标准设置"
    assert leaf_role == "default"


def test_analyze_canonical_table_returns_structured_roles() -> None:
    table = CanonicalTable(
        table_id="canonical-1",
        columns=[
            TableColumn(name="参数", column_index=0),
            TableColumn(name="心房 / 标准设置", column_index=1),
            TableColumn(name="允许误差", column_index=2),
        ],
    )

    result = TableSemantics().analyze_canonical_table(table)

    assert result.columns[0].role == "parameter"
    assert result.columns[1].dimension_labels == ["心房"]
    assert result.columns[1].leaf_role == "default"
    assert result.columns[2].role == "tolerance"
    assert result.unknown_role_count == 0
