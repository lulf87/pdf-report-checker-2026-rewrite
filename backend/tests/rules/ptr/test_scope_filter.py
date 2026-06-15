from app.domain.ptr import PTRClause, PTRDocument, PTRScopeType
from app.rules.ptr.scope_filter import filter_ptr_scope


def _clause(number: str, body: str, *, scope_type: PTRScopeType = PTRScopeType.REQUIREMENT) -> PTRClause:
    return PTRClause(clause_id=f"ptr-{number}", number=number, title=body[:8], body_text=body, scope_type=scope_type)


def test_scope_filter_includes_declared_range_and_explains_exclusions() -> None:
    document = PTRDocument(
        clauses=[
            _clause("2.1.1", "外观应平整。"),
            _clause("2.2.1", "电磁兼容性应符合YY 9706.102-2021要求。"),
            _clause("2.3.1", "检验方法按图1进行。", scope_type=PTRScopeType.TEST_METHOD),
            _clause("2.4.1", "GB 9706.1-2020 4.2 风险管理过程。"),
            _clause("2.9.1", "未声明项目应符合要求。"),
        ]
    )

    result = filter_ptr_scope(document, ["检验项目：2.1.1～2.4.1（除电磁兼容性）"])

    assert result.included_clause_ids == ["ptr-2.1.1"]
    decisions = {decision.clause_number: decision for decision in result.decisions}
    assert decisions["2.1.1"].included is True
    assert decisions["2.2.1"].included is False
    assert decisions["2.2.1"].reason == "excluded_topic"
    assert decisions["2.3.1"].reason == "scope_type_excluded"
    assert decisions["2.4.1"].reason == "external_standard"
    assert decisions["2.9.1"].reason == "outside_declared_scope"


def test_scope_filter_keeps_report_present_clause_when_third_page_range_missed_it() -> None:
    document = PTRDocument(
        clauses=[
            _clause("2.1.2", "脉冲幅度应符合表1中的数值。"),
        ]
    )

    result = filter_ptr_scope(
        document,
        ["检验项目：2.1.3～2.1.15"],
        report_clause_numbers={"2.1.2"},
    )

    assert result.included_clause_ids == ["ptr-2.1.2"]
    assert result.decisions[0].reason == "report_clause_present"

