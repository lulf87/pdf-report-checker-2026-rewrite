from app.domain.ptr import PTRClause, PTRDocument, PTRTable, TableReference
from app.rules.ptr.table_reference_compare import check_table_references


def _clause(number: str) -> PTRClause:
    return PTRClause(
        clause_id=f"ptr-{number}",
        number=number,
        title="脉冲宽度",
        body_text="脉冲宽度应符合表1中的数值。",
        table_references=[TableReference(table_number="1", reference_text="表1")],
    )


def test_table_reference_compare_reports_missing_table() -> None:
    findings = check_table_references(PTRDocument(clauses=[_clause("2.1.3")]), task_id="task-ptr")

    assert len(findings) == 1
    assert findings[0].check_id == "PTR_TABLE"
    assert findings[0].code == "PTR_TABLE_MISSING"
    assert findings[0].metadata["clause_number"] == "2.1.3"
    assert findings[0].metadata["table_number"] == "1"


def test_table_reference_compare_reports_ambiguous_duplicate_candidates() -> None:
    document = PTRDocument(
        clauses=[_clause("2.1.3")],
        tables=[
            PTRTable(table_id="table-1-a", table_number="1", title="表1 MRI说明", page_span=(1, 1)),
            PTRTable(table_id="table-1-b", table_number="1", title="表1 参数", page_span=(3, 4)),
        ],
    )

    findings = check_table_references(document, task_id="task-ptr")

    assert len(findings) == 1
    assert findings[0].code == "PTR_TABLE_CANDIDATE_AMBIGUOUS"
    assert findings[0].actual == ["table-1-a", "table-1-b"]


def test_child_clause_inherits_table_defined_in_parent_clause_text() -> None:
    parent = PTRClause(
        clause_id="ptr-2.1",
        number="2.1",
        title="基本电性能指标",
        body_text="2.1 基本电性能指标\n表2 基本参数\n表3 功能参数\n起搏模式 VVI DDD",
    )
    child = PTRClause(
        clause_id="ptr-2.1.1",
        number="2.1.1",
        title="起搏模式",
        body_text="心脏起搏器的起搏模式应符合表3的要求。",
        table_references=[TableReference(table_number="3", reference_text="表3", clause_id="ptr-2.1.1")],
    )

    findings = check_table_references(PTRDocument(clauses=[parent, child]), task_id="task-ptr")

    assert findings == []


def test_child_clause_inherits_table_defined_before_it_in_same_parent_section() -> None:
    parent = PTRClause(
        clause_id="ptr-2.1",
        number="2.1",
        title="基本电性能指标",
        body_text="基本电性能指标。",
    )
    sibling = PTRClause(
        clause_id="ptr-2.1.0",
        number="2.1.0",
        title="表格说明",
        body_text="表2 基本参数\n参数 A B C",
    )
    child = PTRClause(
        clause_id="ptr-2.1.12",
        number="2.1.12",
        title="产品物理特性及参数",
        body_text="产品物理特性及参数应符合表2的要求。",
        table_references=[TableReference(table_number="2", reference_text="表2", clause_id="ptr-2.1.12")],
    )

    findings = check_table_references(PTRDocument(clauses=[parent, sibling, child]), task_id="task-ptr")

    assert findings == []
