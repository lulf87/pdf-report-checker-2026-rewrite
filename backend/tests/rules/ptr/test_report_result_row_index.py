from __future__ import annotations

from app.domain.inspection_group import InspectionItemGroup
from app.domain.report import InspectionItem
from app.rules.ptr.report_result_index import ReportResultRow, ReportResultRowIndex, build_report_result_row_index


def _group(rows: list[InspectionItem]) -> InspectionItemGroup:
    return InspectionItemGroup(item_no="38", display_item_no="38", pages=[28, 30], rows=rows)


def test_result_row_index_recovers_result_column_without_using_item_or_clause_numbers() -> None:
    index = build_report_result_row_index(
        _group(
            [
                InspectionItem(
                    sequence_raw="38",
                    sequence=38,
                    standard_clause="2.1",
                    standard_requirement="2.1.4.1 基本频率",
                    source_page=28,
                ),
                InspectionItem(
                    sequence_raw="允许误差：±2min⁻¹；单位：min⁻¹",
                    item_name="-0～+1",
                    source_page=28,
                    row_index_in_page=11,
                ),
            ]
        )
    )

    matches = index.find(clause_number="2.1.4.1", clause_title="基本频率", row_label="基本频率")

    assert matches
    assert matches[0].test_result == "-0～+1"
    assert matches[0].test_result not in {"38", "2.1.4.1", "28"}
    assert matches[0].source_page == 28
    assert matches[0].source_row == 11


def test_result_row_index_aligns_shifted_clause_number_by_normalized_title() -> None:
    index = build_report_result_row_index(
        _group(
            [
                InspectionItem(
                    sequence_raw="2.1.8 房室间期（只适用于双腔起搏器）",
                    item_name="",
                    source_page=30,
                    row_index_in_page=8,
                ),
                InspectionItem(
                    sequence_raw="起搏",
                    item_name="-1～+0",
                    source_page=30,
                    row_index_in_page=11,
                ),
                InspectionItem(
                    sequence_raw="感知",
                    item_name="+2～+10",
                    source_page=30,
                    row_index_in_page=12,
                ),
            ]
        )
    )

    matches = index.find(clause_number="2.1.9", clause_title="房室间期", row_label="房室间期")

    assert {row.test_result for row in matches} == {"-1～+0", "+2～+10"}
    assert all("clause_number_mismatch_but_title_match" in row.diagnostics for row in matches)


def test_result_row_index_keeps_actual_null_when_no_result_column_exists() -> None:
    index = build_report_result_row_index(
        _group(
            [
                InspectionItem(
                    sequence_raw="2.1.4.1 基本频率",
                    item_name="",
                    source_page=28,
                )
            ]
        )
    )

    assert index.find(clause_number="2.1.4.1", clause_title="基本频率", row_label="基本频率") == []


def test_result_row_index_recovers_missing_numeric_rows_from_report_page_text() -> None:
    group = _group(
        [
            InspectionItem(
                sequence_raw="38",
                sequence=38,
                standard_clause="2.1",
                standard_requirement="2.1.4.1 基本频率",
                test_result="符合",
                source_page=28,
            )
        ]
    )
    group.pages = [28]

    index = build_report_result_row_index(
        group,
        page_text_by_page={
            28: """
            2.1.4.1 基本频率
            基本频率应符合表3的要求
            允许误差：±2min⁻¹
            @500Ω
            -0～+1
            @240Ω
            -0～+1
            @2000Ω
            -0～+1
            2.1.4.2 磁频率
            允许误差：±2min⁻¹
            +0
            """
        },
    )

    matches = index.find(
        clause_number="2.1.4.1",
        clause_title="基本频率",
        row_label="基本频率",
        prefer_numeric=True,
    )

    assert {row.test_result for row in matches} == {"-0～+1"}
    assert {row.condition for row in matches} == {"@500Ω", "@240Ω", "@2000Ω"}
    assert all("recovered_from_page_text" in row.diagnostics for row in matches)


def test_result_row_index_page_fallback_stays_within_group_clause_root() -> None:
    group = InspectionItemGroup(
        item_no="40",
        display_item_no="40",
        pages=[32],
        rows=[
            InspectionItem(
                sequence_raw="40",
                sequence=40,
                standard_clause="2.6",
                standard_requirement="环氧乙烷残留量应不超过10μg/g。",
                source_page=32,
            )
        ],
    )

    index = build_report_result_row_index(
        group,
        page_text_by_page={
            32: "2.1.12 产品物理特性及参数\n+0.2\n2.6 环氧乙烷残留量\n符合要求",
        },
    )

    assert not any(row.report_clause_number == "2.1.12" for row in index.rows)
    assert any(row.report_clause_number == "2.6" for row in index.rows)


def test_result_row_index_page_text_keeps_shifted_title_and_subconditions() -> None:
    index = build_report_result_row_index(
        _group([]),
        page_text_by_page={
            30: """
            2.1.8 房室间期（只适用于双腔起搏器）
            允许误差：-10/+15ms
            单位：min
            −1
            起搏
            -1～+0
            感知
            +2～+10
            2.1.9 室后房不应期（PVARP）
            -7～+1
            """
        },
    )

    matches = index.find(
        clause_number="2.1.9",
        clause_title="房室间期（只适用于双腔起搏器）",
        row_label="房室间期",
        expected_text="-10/+15ms",
        prefer_numeric=True,
    )

    assert {row.test_result for row in matches} == {"-1～+0", "+2～+10"}
    assert {row.condition for row in matches} == {"起搏", "感知"}
    assert all("clause_number_mismatch_but_title_match" in row.diagnostics for row in matches)


def test_result_row_index_carries_clause_context_across_continuation_pages() -> None:
    group = _group([])
    index = build_report_result_row_index(
        group,
        page_text_by_page={
            28: "2.1.3 脉冲宽度\n符合要求",
            30: "允许误差：±35μs\n心房\n@500Ω\n-23～+23\n2.1.4 基本频率",
        },
    )

    matches = index.find(
        clause_number="2.1.3",
        clause_title="脉冲宽度",
        row_label="脉冲宽度",
        prefer_numeric=True,
    )

    assert [row.test_result for row in matches] == ["-23～+23"]
    assert matches[0].condition == "@500Ω"


def test_result_row_index_deduplicates_native_and_page_text_rows_by_result_and_condition() -> None:
    group = _group(
        [
            InspectionItem(sequence_raw="2.1.6.1 感知不应期", source_page=28),
            InspectionItem(
                sequence_raw="心室：95 ms ±10 ms",
                item_name="+0",
                source_page=28,
                row_index_in_page=3,
            ),
        ]
    )
    group.pages = [28]
    index = build_report_result_row_index(
        group,
        page_text_by_page={28: "2.1.6.1 感知不应期\n心室：95 ms ±10 ms\n+0"},
    )

    matches = index.find(
        clause_number="2.1.6.1",
        clause_title="感知不应期",
        row_label="心室 / VVI",
        condition="心室 / VVI",
        expected_text="95 ms ±10 ms",
        prefer_numeric=True,
    )

    assert len(matches) == 1
    assert matches[0].test_result == "+0"
    assert "recovered_from_page_text" not in matches[0].diagnostics


def test_result_row_index_condition_does_not_match_chamber_word_in_row_label() -> None:
    index = ReportResultRowIndex(
        rows=[
            ReportResultRow(
                report_clause_number="2.1.10",
                report_clause_title="空白期/最短不应期",
                normalized_clause_title="空白期最短不应期",
                table_row_label="心室感知",
                condition="心房",
                standard_requirement="心室感知 心房 可程控(PVAB-55ms) ±10 ms",
                test_result="-4～+2",
            ),
            ReportResultRow(
                report_clause_number="2.1.10",
                report_clause_title="空白期/最短不应期",
                normalized_clause_title="空白期最短不应期",
                table_row_label="心室感知",
                condition="心室",
                standard_requirement="心室感知 心室 95 ms ±10 ms",
                test_result="+0",
            ),
        ]
    )

    matches = index.find(
        clause_number="2.1.11",
        clause_title="空白期/最短不应期",
        row_label="心室感知",
        condition="心室",
        expected_text="95 ms ±10 ms",
        prefer_numeric=True,
    )

    assert [row.test_result for row in matches] == ["+0"]
    assert matches[0].condition == "心室"


def test_result_row_index_expected_text_selects_matching_table_variant() -> None:
    index = ReportResultRowIndex(
        rows=[
            ReportResultRow(
                report_clause_number="2.1.10",
                report_clause_title="空白期/最短不应期",
                normalized_clause_title="空白期最短不应期",
                table_row_label="心房感知",
                condition="心房",
                standard_requirement="心房感知 心房 80 ms ±10 ms",
                test_result="+0",
            ),
            ReportResultRow(
                report_clause_number="2.1.10",
                report_clause_title="空白期/最短不应期",
                normalized_clause_title="空白期最短不应期",
                table_row_label="DDTA、DDTAV 心房感知",
                condition="心房",
                standard_requirement="DDTA、DDTAV 心房感知 心房 205 ms -10/+15 ms",
                test_result="-1",
            ),
        ]
    )

    matches = index.find(
        clause_number="2.1.11",
        clause_title="空白期/最短不应期",
        row_label="心房感知",
        condition="心房",
        expected_text="80 ms ±10 ms",
        prefer_numeric=True,
    )

    assert [row.test_result for row in matches] == ["+0"]


def test_result_row_index_deduplicates_equivalent_passing_results() -> None:
    index = ReportResultRowIndex(
        rows=[
            ReportResultRow(
                report_clause_number="2.1.1",
                report_clause_title="起搏模式",
                normalized_clause_title="起搏模式",
                table_row_label="起搏模式",
                standard_requirement="起搏模式 DDD、VVI",
                test_result="符合要求",
            ),
            ReportResultRow(
                report_clause_number="2.1.1",
                report_clause_title="起搏模式",
                normalized_clause_title="起搏模式",
                table_row_label="起搏模式",
                standard_requirement="起搏模式 DDD、VVI",
                test_result="符合",
                diagnostics=["recovered_from_page_text"],
            ),
        ]
    )

    matches = index.find(
        clause_number="2.1.1",
        clause_title="起搏模式",
        row_label="起搏模式",
        expected_text="DDD、VVI",
    )

    assert [row.test_result for row in matches] == ["符合要求"]
