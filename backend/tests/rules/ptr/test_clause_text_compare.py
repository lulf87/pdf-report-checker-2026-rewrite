from app.domain.ptr import PTRClause
from app.domain.report import InspectionItem
from app.rules.ptr.clause_text_compare import compare_clause_texts


def _clause(number: str, body: str) -> PTRClause:
    return PTRClause(clause_id=f"ptr-{number}", number=number, title=body[:8], body_text=body)


def test_clause_text_compare_accepts_strict_normalized_match() -> None:
    findings = compare_clause_texts(
        [_clause("2.1.1", "导管外观\n应无杂质。")],
        [InspectionItem(standard_clause="2.1.1", standard_requirement="导管外观 应无杂质。")],
    )

    assert findings == []


def test_clause_text_compare_outputs_finding_for_strict_mismatch() -> None:
    findings = compare_clause_texts(
        [_clause("2.1.1", "电阻值应≤10Ω。")],
        [InspectionItem(standard_clause="2.1.1", standard_requirement="电阻值应<10Ω。")],
        task_id="task-ptr",
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "PTR_CLAUSE"
    assert finding.code == "PTR_CLAUSE_TEXT_MISMATCH"
    assert finding.expected == "电阻值应<=10Ω。"
    assert finding.actual == "电阻值应<10Ω。"
    assert finding.metadata["clause_number"] == "2.1.1"
    assert any(fragment.kind.value in {"delete", "insert", "replace"} for fragment in finding.diff_fragments)


def test_clause_text_compare_outputs_missing_finding() -> None:
    findings = compare_clause_texts(
        [_clause("2.1.9", "缺失条款应符合要求。")],
        [InspectionItem(standard_clause="2.1.1", standard_requirement="其他条款。")],
        task_id="task-ptr",
    )

    assert len(findings) == 1
    assert findings[0].code == "PTR_CLAUSE_MISSING"
    assert findings[0].missing_evidence[0].label == "报告标准要求"

