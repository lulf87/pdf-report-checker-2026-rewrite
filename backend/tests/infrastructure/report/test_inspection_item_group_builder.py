from app.domain.report import InspectionItem
from app.infrastructure.report.inspection_item_group_builder import (
    InspectionItemGroupBuilder,
    build_inspection_item_groups,
)

from tests.rules.report.helpers import item


def _blank_row(*, page: int = 5, row: int = 0) -> InspectionItem:
    return InspectionItem(
        sequence_raw="",
        source_page=page,
        row_index_in_page=row,
    )


def test_groups_plain_sequence_numbers_into_separate_groups() -> None:
    result = build_inspection_item_groups(
        [
            item(1, raw="1", page=1, row=0),
            item(2, raw="2", page=1, row=1),
            item(3, raw="3", page=1, row=2),
        ]
    )

    assert [group.item_no for group in result.groups] == ["1", "2", "3"]
    assert [group.display_item_no for group in result.groups] == ["1", "2", "3"]
    assert result.ungrouped_rows == []


def test_groups_multiple_physical_rows_with_same_sequence() -> None:
    result = build_inspection_item_groups(
        [
            item(2, raw="2", result="——", page=4, row=0),
            item(2, raw="2", result="符合要求", conclusion="", remark="", page=4, row=1),
        ]
    )

    group = result.groups[0]
    assert group.item_no == "2"
    assert len(group.rows) == 2
    assert group.effective_test_results == ["——", "符合要求"]


def test_groups_continuation_marker_variants_into_normalized_item_number() -> None:
    result = build_inspection_item_groups(
        [
            item(3, raw="3", page=14, row=10),
            item(3, raw="续3", continued=True, page=15, row=0),
            item(3, raw="续 3", continued=True, page=16, row=0),
            item(3, raw="续\n3", continued=True, page=17, row=0),
        ]
    )

    assert [group.item_no for group in result.groups] == ["3"]
    group = result.groups[0]
    assert [marker.raw_text for marker in group.continuation_markers] == ["续3", "续 3", "续\n3"]
    assert [marker.normalized_item_no for marker in group.continuation_markers] == ["3", "3", "3"]
    assert group.pages == [14, 15, 16, 17]


def test_groups_blank_sequence_payload_row_into_active_group() -> None:
    result = build_inspection_item_groups(
        [
            item(4, raw="4", result="——", conclusion="符合", page=8, row=0),
            item(None, raw="", result="符合要求", conclusion="", remark="", page=8, row=1, name="a) 补充要求"),
        ]
    )

    group = result.groups[0]
    assert group.item_no == "4"
    assert len(group.rows) == 2
    assert group.effective_test_results == ["——", "符合要求"]
    assert group.diagnostics == []


def test_groups_blank_continuation_signal_rows_into_active_group() -> None:
    continued = item(None, raw="", result="符合要求", conclusion="", remark="", page=8, row=1, continued=True)
    logical = item(None, raw="", result="100", conclusion="", remark="", page=8, row=2).model_copy(
        update={"metadata": {"logical_continuation": True}}
    )

    result = build_inspection_item_groups(
        [
            item(4, raw="4", result="——", conclusion="符合", page=8, row=0),
            continued,
            logical,
        ]
    )

    group = result.groups[0]
    assert group.item_no == "4"
    assert len(group.rows) == 3
    assert group.effective_test_results == ["——", "符合要求", "100"]


def test_keeps_blank_sequence_empty_row_out_of_groups_with_diagnostic() -> None:
    result = build_inspection_item_groups([item(5, raw="5", page=8, row=0), _blank_row(page=8, row=1)])

    assert [group.item_no for group in result.groups] == ["5"]
    assert len(result.ungrouped_rows) == 1
    assert result.diagnostics[0]["code"] == "EMPTY_ROW_WITHOUT_PAYLOAD"


def test_cross_page_group_records_pages_and_continuation_marker() -> None:
    result = build_inspection_item_groups(
        [
            item(3, raw="3", result="符合要求", conclusion="/", page=14, row=20),
            item(3, raw="续 3", result="符合要求", conclusion="", remark="", continued=True, page=15, row=0),
        ]
    )

    group = result.groups[0]
    assert group.pages == [14, 15]
    assert len(group.continuation_markers) == 1
    assert group.continuation_markers[0].page_number == 15
    assert group.continuation_markers[0].row_index == 0


def test_effective_test_results_keep_placeholders_and_drop_blank_values() -> None:
    result = build_inspection_item_groups(
        [
            item(6, raw="6", result="符合要求", page=4, row=0),
            item(6, raw="6", result="——", page=4, row=1),
            item(6, raw="6", result="/", page=4, row=2),
            item(6, raw="6", result="100", page=4, row=3),
            item(6, raw="6", result="   ", page=4, row=4),
        ]
    )

    assert result.groups[0].effective_test_results == ["符合要求", "——", "/", "100"]


def test_effective_single_conclusion_prefers_first_non_blank_unique_value() -> None:
    conforming = build_inspection_item_groups(
        [
            item(7, raw="7", conclusion="", page=4, row=0),
            item(7, raw="7", conclusion="符合", page=4, row=1),
            item(7, raw="7", conclusion="符合", page=4, row=2),
        ]
    )
    slash = build_inspection_item_groups([item(8, raw="8", conclusion="/", page=4, row=0)])

    assert conforming.groups[0].effective_single_conclusion == "符合"
    assert slash.groups[0].effective_single_conclusion == "/"


def test_splits_combined_conclusion_and_remark_placeholder() -> None:
    cases = [
        ("符合 /", "符合"),
        ("不符合 /", "不符合"),
        ("/ /", "/"),
        ("—— /", "——"),
    ]

    for raw_conclusion, expected_conclusion in cases:
        result = build_inspection_item_groups(
            [
                item(
                    126,
                    raw="126",
                    result="符合要求",
                    conclusion=raw_conclusion,
                    remark="",
                    page=87,
                    row=3,
                    name="指示灯颜色",
                )
            ]
        )

        group = result.groups[0]
        assert group.effective_single_conclusion == expected_conclusion
        assert group.effective_remark == "/"


def test_recovers_shifted_remark_placeholder_from_conclusion_column() -> None:
    result = build_inspection_item_groups(
        [
            item(
                126,
                raw="126",
                result="符合",
                conclusion="/",
                remark="",
                page=87,
                row=3,
                name="指示灯颜色",
            )
        ]
    )

    group = result.groups[0]
    assert group.effective_single_conclusion == "符合"
    assert group.effective_remark == "/"


def test_effective_remark_treats_slash_and_dash_as_valid_values() -> None:
    slash = build_inspection_item_groups([item(9, raw="9", remark="/", page=4, row=0)])
    dash = build_inspection_item_groups([item(10, raw="10", remark="——", page=4, row=0)])
    blank = build_inspection_item_groups([item(11, raw="11", remark="   ", page=4, row=0)])

    assert slash.groups[0].effective_remark == "/"
    assert dash.groups[0].effective_remark == "——"
    assert blank.groups[0].effective_remark is None


def test_records_inherited_fields_without_mutating_original_rows() -> None:
    rows = [
        item(12, raw="12", result="符合要求", conclusion="符合", remark="/", page=4, row=0),
        item(12, raw="12", result="", conclusion="", remark="", page=4, row=1),
    ]

    result = InspectionItemGroupBuilder().build(rows)

    inherited = result.groups[0].inherited_merged_fields
    assert {field.field_name for field in inherited} == {"test_result", "conclusion", "remark"}
    assert all(field.source_row_index == 0 for field in inherited)
    assert all(field.target_row_indexes == [1] for field in inherited)
    assert rows[1].test_result == ""
    assert rows[1].conclusion == ""
    assert rows[1].remark == ""


def test_source_evidence_contains_row_summaries_without_absolute_paths() -> None:
    result = build_inspection_item_groups([item(13, raw="13", result="符合要求", conclusion="符合", remark="/", page=4, row=2)])

    evidence = result.groups[0].source_evidence[0]
    assert evidence["page_number"] == 4
    assert evidence["row_index"] == 2
    assert evidence["item_no"] == "13"
    assert evidence["test_result"] == "符合要求"
    assert evidence["single_conclusion"] == "符合"
    assert evidence["remark"] == "/"
    assert "/Users/" not in str(evidence)


def test_records_diagnostics_for_missing_context_and_unparseable_sequence() -> None:
    result = build_inspection_item_groups(
        [
            item(14, raw="14", page=4, row=0),
            item(15, raw="15", page=5, row=1).model_copy(update={"source_page": None}),
            item(None, raw="abc", page=5, row=2),
        ]
    )

    codes = [diagnostic["code"] for diagnostic in result.diagnostics]
    assert "ROW_CONTEXT_MISSING" in codes
    assert "UNPARSEABLE_ITEM_NO" in codes
    assert len(result.ungrouped_rows) == 1


def test_standard_requirement_text_is_not_used_as_item_no_even_when_sequence_was_parsed() -> None:
    requirement_text = "——所有其他 ME 设备和 ME 系统，500V。"
    result = build_inspection_item_groups(
        [
            item(10, raw="10", result="符合要求", conclusion="符合", remark="/", page=12, row=0),
            item(500, raw=requirement_text, result="", conclusion="", remark="", page=12, row=1),
        ]
    )

    assert [group.item_no for group in result.groups] == ["10"]
    group = result.groups[0]
    assert len(group.rows) == 2
    assert group.rows[1].sequence_raw == requirement_text
    assert requirement_text not in [group.item_no for group in result.groups]
    assert result.ungrouped_rows == []
    assert any(diagnostic["code"] == "SEQUENCE_TEXT_LOOKS_LIKE_REQUIREMENT" for diagnostic in result.diagnostics)


def test_ipx0_requirement_text_is_grouped_into_active_item_not_new_item_no() -> None:
    requirement_text = "当外壳的分类为 IPX0 时，保持 ME 设备和其部件在潮湿箱里 48h。"
    result = build_inspection_item_groups(
        [
            item(15, raw="15", result="符合要求", conclusion="符合", remark="/", page=13, row=0),
            item(48, raw=requirement_text, result="", conclusion="", remark="", page=13, row=1),
        ]
    )

    assert [group.item_no for group in result.groups] == ["15"]
    assert len(result.groups[0].rows) == 2
    assert result.groups[0].effective_test_results == ["符合要求"]
    assert result.groups[0].effective_single_conclusion == "符合"
    assert result.groups[0].effective_remark == "/"


def test_alpha_subitem_and_standard_clause_sequence_text_join_active_group() -> None:
    result = build_inspection_item_groups(
        [
            item(20, raw="20", result="符合要求", conclusion="符合", remark="/", page=14, row=0),
            item(None, raw="a) 子项要求", result="", conclusion="", remark="", page=14, row=1),
            item(4, raw="4.10.2", result="", conclusion="", remark="", page=14, row=2),
        ]
    )

    assert [group.item_no for group in result.groups] == ["20"]
    assert [row.sequence_raw for row in result.groups[0].rows] == ["20", "a) 子项要求", "4.10.2"]
    assert result.ungrouped_rows == []


def test_long_chinese_sequence_without_active_group_is_ungrouped_with_diagnostic() -> None:
    raw = "预期一次性使用的任何材料，元器件，附件或 ME 设备均应符合适用要求。"
    result = build_inspection_item_groups([item(1, raw=raw, result="", conclusion="", remark="", page=15, row=0)])

    assert result.groups == []
    assert len(result.ungrouped_rows) == 1
    assert result.ungrouped_rows[0].sequence_raw == raw
    assert any(diagnostic["code"] == "UNGROUPED_PAYLOAD_WITH_INVALID_SEQUENCE" for diagnostic in result.diagnostics)


def test_legal_sequence_formats_still_create_groups() -> None:
    result = build_inspection_item_groups(
        [
            item(118, raw="118", page=16, row=0),
            item(118, raw="续 118", continued=True, page=17, row=0),
        ]
    )

    assert [group.item_no for group in result.groups] == ["118"]
    assert [marker.raw_text for marker in result.groups[0].continuation_markers] == ["续 118"]


def test_qw2025_2795_like_cross_page_mini_fixture_groups_c07_evidence() -> None:
    result = build_inspection_item_groups(
        [
            item(3, raw="3", result="符合要求", conclusion="/", remark="/", page=14, row=31, name="检验项目 3"),
            item(None, raw="", result="符合要求", conclusion="", remark="", page=14, row=32, name="a) 子项目"),
            item(3, raw="续 3", result="符合要求", conclusion="", remark="", continued=True, page=15, row=0, name="检验项目 3 续"),
        ]
    )

    group = result.groups[0]
    assert group.item_no == "3"
    assert group.pages == [14, 15]
    assert group.effective_test_results == ["符合要求", "符合要求", "符合要求"]
    assert group.effective_single_conclusion == "/"
    assert group.effective_remark == "/"
    assert group.continuation_markers[0].raw_text == "续 3"
