from app.domain.common import Location, SourceType
from app.domain.ptr import (
    PTRClause,
    PTRClauseNumber,
    PTRClauseTaxonomy,
    PTRDocument,
    PTRScopeType,
    PTRSubItem,
    PTRTableReference,
    PTRTable,
    TableReference,
)


def test_ptr_clause_number_orders_tracks_parent_and_chapter() -> None:
    number = PTRClauseNumber.from_string("2.1.1")

    assert number.parts == (2, 1, 1)
    assert str(number.parent()) == "2.1"
    assert number.is_descendant_of(PTRClauseNumber.from_string("2"))
    assert number.chapter == 2
    assert number.is_chapter_2 is False
    assert PTRClauseNumber.from_string("2").is_chapter_2 is True


def test_ptr_clause_number_parses_required_depths_and_json() -> None:
    numbers = [PTRClauseNumber.from_string(raw) for raw in ["2", "2.1", "2.1.1", "2.1.1.1"]]

    assert [number.parts for number in numbers] == [(2,), (2, 1), (2, 1, 1), (2, 1, 1, 1)]
    assert [number.level for number in numbers] == [1, 2, 3, 4]
    assert [str(number) for number in sorted(reversed(numbers))] == ["2", "2.1", "2.1.1", "2.1.1.1"]
    assert numbers[-1].model_dump(mode="json") == {"parts": [2, 1, 1, 1]}
    assert numbers[-1].model_dump_json() == '{"parts":[2,1,1,1]}'


def test_ptr_clause_accepts_legacy_fields_sub_items_and_table_references() -> None:
    clause = PTRClause(
        clause_id="ptr-2.1.1",
        number="2.1.1",
        full_text="2.1.1 性能应符合表 1，且包括 a) 要求。",
        text_content="性能应符合表 1，且包括 a) 要求。",
        parent_number="2.1",
        sub_items=[PTRSubItem(marker="a)", text="输出幅度应符合要求", position=12)],
        table_references=[PTRTableReference(table_number=1, context="见表 1", position=5)],
        position=(4, 120),
        raw_text="原始条款文本",
        clause_type="main_requirement",
    )

    payload = clause.model_dump(mode="json")

    assert clause.body_text == "性能应符合表 1，且包括 a) 要求。"
    assert clause.full_text == "2.1.1 性能应符合表 1，且包括 a) 要求。"
    assert clause.text_content == "性能应符合表 1，且包括 a) 要求。"
    assert str(clause.parent_number) == "2.1"
    assert clause.has_sub_items() is True
    assert clause.has_table_references() is True
    assert clause.get_all_table_numbers() == ["1"]
    assert clause.is_standard_clause() is True
    assert clause.is_main_requirement is True
    assert payload["sub_items"][0]["marker"] == "a)"
    assert payload["table_references"][0]["table_number"] == "1"


def test_ptr_clause_type_maps_legacy_allowed_values_to_new_taxonomy() -> None:
    assert PTRClause(clause_id="main", number="2.1", body_text="要求", clause_type="main_requirement").taxonomy == PTRClauseTaxonomy.REQUIREMENT
    assert PTRClause(clause_id="method", number="3.1", body_text="方法", clause_type="test_method").taxonomy == PTRClauseTaxonomy.METHOD
    assert PTRClause(clause_id="appendix", number="2.9", body_text="附录", clause_type="appendix").taxonomy == PTRClauseTaxonomy.APPENDIX
    assert PTRClause(clause_id="info", number="2.2", body_text="说明", clause_type="informational").taxonomy == PTRClauseTaxonomy.NOTE
    assert PTRClause(clause_id="group", number="2.3", body_text="分组", clause_type="group").taxonomy == PTRClauseTaxonomy.GROUP_HEADING


def test_ptr_clause_serializes_location_taxonomy_and_table_reference() -> None:
    clause = PTRClause(
        clause_id="ptr-2.1.1",
        number="2.1.1",
        title="性能要求",
        body_text="应符合表 1 的要求。",
        location=Location(source_type=SourceType.PTR, page_number=4, section="chapter_2"),
        table_references=[
            TableReference(table_number=1, raw_text="表 1", reference_text="见表 1"),
        ],
    )

    payload = clause.model_dump(mode="json")

    assert clause.level == 3
    assert clause.taxonomy == PTRClauseTaxonomy.REQUIREMENT
    assert clause.is_main_requirement is True
    assert clause.table_refs == ["1"]
    assert payload["number"] == "2.1.1"
    assert payload["location"]["page_number"] == 4
    assert payload["table_references"][0]["table_number"] == "1"


def test_ptr_clause_maps_scope_type_to_taxonomy_without_compare_algorithm() -> None:
    method_clause = PTRClause(
        clause_id="ptr-3.1",
        number="3.1",
        body_text="按图示方法测试。",
        scope_type=PTRScopeType.TEST_METHOD,
    )
    group_clause = PTRClause(
        clause_id="ptr-2.1",
        number="2.1",
        body_text="物理性能",
        children_ids=["ptr-2.1.1"],
        scope_type=PTRScopeType.GROUP_CLAUSE,
    )

    assert method_clause.taxonomy == PTRClauseTaxonomy.METHOD
    assert method_clause.is_main_requirement is False
    assert group_clause.taxonomy == PTRClauseTaxonomy.GROUP_HEADING
    assert group_clause.is_leaf is False


def test_ptr_clause_mutated_scope_survives_document_validation() -> None:
    clause = PTRClause(clause_id="ptr-2.2", number="2.2", body_text="说明：图示仅作参考。")

    clause.scope_type = PTRScopeType.INFORMATIONAL
    document = PTRDocument(clauses=[clause])

    assert document.clauses[0].scope_type == PTRScopeType.INFORMATIONAL
    assert document.clauses[0].taxonomy == PTRClauseTaxonomy.NOTE
    assert document.clauses[0].is_main_requirement is False


def test_ptr_document_supports_clause_table_and_reference_lookup() -> None:
    clause = PTRClause(
        clause_id="ptr-2.1.1",
        number="2.1.1",
        body_text="脉冲宽度应符合表 1。",
        table_references=[TableReference(table_number="1", clause_id="ptr-2.1.1")],
    )
    duplicate_table_a = PTRTable(table_id="table-1-a", table_number="1", title="性能参数", page_span=(5, 5))
    duplicate_table_b = PTRTable(table_id="table-1-b", table_number="1", title="续表", page_span=(6, 6))
    document = PTRDocument(clauses=[clause], tables=[duplicate_table_a, duplicate_table_b], chapter2_span=(3, 8))

    assert document.get_clause_by_number(PTRClauseNumber.from_string("2.1.1")) == clause
    assert document.get_clause_by_string("2.1.1") == clause
    assert document.get_clause_by_string("2.9") is None
    assert document.get_clauses_at_level(3) == [clause]
    assert document.get_table_by_number("1") == duplicate_table_a
    assert document.get_tables_by_number("1") == [duplicate_table_a, duplicate_table_b]
    assert document.get_all_referenced_table_numbers() == ["1"]


def test_ptr_document_legacy_helpers_return_top_level_main_requirements_and_table_refs() -> None:
    top = PTRClause(clause_id="ptr-2.1", number="2.1", body_text="性能", clause_type="group")
    main = PTRClause(
        clause_id="ptr-2.1.1",
        number="2.1.1",
        body_text="应符合表 2。",
        table_references=[PTRTableReference(table_number=2, context="符合表 2")],
    )
    method = PTRClause(clause_id="ptr-3.1", number="3.1", body_text="试验方法", clause_type="test_method")
    document = PTRDocument(clauses=[top, main, method])

    assert document.get_top_level_clauses() == [top]
    assert document.get_main_requirement_clauses() == [main]
    assert document.has_table_references() is True
    assert document.get_all_referenced_table_numbers() == ["2"]
