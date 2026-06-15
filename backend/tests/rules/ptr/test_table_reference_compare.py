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

