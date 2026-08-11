from __future__ import annotations

from app.domain.ptr import PTRClause, PTRClauseNumber, PTRClauseRole
from app.rules.ptr.clause_role import assign_clause_roles, classify_clause_role


def _clause(number: str, *, title: str, body: str, children: list[str] | None = None, table_refs: list[str] | None = None) -> PTRClause:
    return PTRClause(
        clause_id=f"ptr-{number}",
        number=PTRClauseNumber.from_string(number),
        title=title,
        body_text=body,
        children_ids=children or [],
        table_refs=table_refs or [],
    )


def test_parent_with_only_attached_tables_is_a_section_container() -> None:
    parent = _clause(
        "2.1",
        title="基本电性能指标",
        body="表2 基本参数\n表3 功能参数",
        children=["ptr-2.1.1", "ptr-2.1.2"],
    )

    assert classify_clause_role(parent) == PTRClauseRole.SECTION_CONTAINER
    assert assign_clause_roles([parent]) == ["ptr-2.1"]
    assert parent.is_section_container is True


def test_parent_with_independent_requirement_is_not_filtered() -> None:
    parent = _clause(
        "2.1",
        title="基本电性能指标",
        body="基本电性能指标应符合本标准要求。\n表2 基本参数",
        children=["ptr-2.1.1"],
        table_refs=["2"],
    )

    assert classify_clause_role(parent) == PTRClauseRole.TABLE_REQUIREMENT


def test_standard_clause_is_external_standard_requirement() -> None:
    clause = _clause(
        "2.10",
        title="通用安全要求",
        body="应符合 GB 16174.1-2015 的要求。",
    )

    assert classify_clause_role(clause) == PTRClauseRole.EXTERNAL_STANDARD_REQUIREMENT
