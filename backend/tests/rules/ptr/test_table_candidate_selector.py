from app.domain.table import CanonicalTable, ParameterRecord
from app.rules.ptr.table_candidate_selector import select_report_table_candidate


def test_selector_prefers_single_exact_table_number_candidate() -> None:
    expected = _table("ptr-table-1", "1", "表 1 脉冲参数", ["脉冲宽度"])
    wrong_number = _table("report-table-2", "2", "表 2 尺寸参数", ["尺寸"])
    exact_number = _table("report-table-1", "1", "表 1 脉冲参数", ["脉冲宽度"])

    result = select_report_table_candidate(
        expected,
        [wrong_number, exact_number],
        table_number="1",
        task_id="task-ptr",
        clause_number="2.3",
    )

    assert result.selected_table == exact_number
    assert result.findings == []
    assert result.matching_strategy == "table_number_exact"


def test_selector_uses_normalized_caption_when_same_table_number_has_multiple_candidates() -> None:
    expected = _table("ptr-table-1", "1", "表 1 脉冲参数", ["脉冲宽度"])
    wrong_title = _table("report-table-size", "1", "表1 尺寸参数", ["尺寸"])
    normalized_title = _table("report-table-pulse", "1", "表 1：脉冲 参数", ["脉冲宽度"])

    result = select_report_table_candidate(
        expected,
        [wrong_title, normalized_title],
        table_number="1",
        task_id="task-ptr",
        clause_number="2.3",
    )

    assert result.selected_table == normalized_title
    assert result.findings == []
    assert result.matching_strategy == "caption_normalized"


def test_selector_uses_parameter_signature_overlap_as_tie_breaker() -> None:
    expected = _table("ptr-table-1", "1", "表 1 参数", ["脉冲宽度", "基础频率", "感知灵敏度"])
    weak_overlap = _table("report-table-size", "1", "表 1 参数", ["脉冲宽度", "尺寸"])
    strong_overlap = _table("report-table-pulse", "1", "表 1 参数", ["脉冲宽度", "基础频率", "感知灵敏度"])

    result = select_report_table_candidate(
        expected,
        [weak_overlap, strong_overlap],
        table_number="1",
        task_id="task-ptr",
        clause_number="2.3",
    )

    assert result.selected_table == strong_overlap
    assert result.findings == []
    assert result.matching_strategy == "parameter_signature_overlap"


def test_selector_limits_signature_tie_breaker_to_caption_matches() -> None:
    expected = _table("ptr-table-1", "1", "表 1 脉冲参数", ["脉冲宽度", "基础频率"])
    weak_caption_match = _table("report-table-fragment", "1", "表 1 脉冲参数", ["脉冲宽度"])
    strong_caption_match = _table("report-table-pulse", "1", "表1：脉冲 参数", ["脉冲宽度", "基础频率"])
    wrong_title_high_overlap = _table("report-table-size", "1", "表 1 尺寸参数", ["脉冲宽度", "基础频率"])

    result = select_report_table_candidate(
        expected,
        [weak_caption_match, wrong_title_high_overlap, strong_caption_match],
        table_number="1",
        task_id="task-ptr",
        clause_number="2.3",
    )

    assert result.selected_table == strong_caption_match
    assert result.findings == []
    assert result.matching_strategy == "parameter_signature_overlap"


def test_selector_reports_ambiguous_when_parameter_overlap_is_close() -> None:
    expected = _table("ptr-table-1", "1", "表 1 参数", ["脉冲宽度", "基础频率"])
    left = _table("report-table-left", "1", "表 1 参数", ["脉冲宽度", "输出电压"])
    right = _table("report-table-right", "1", "表 1 参数", ["基础频率", "输出电压"])

    result = select_report_table_candidate(
        expected,
        [left, right],
        table_number="1",
        task_id="task-ptr",
        clause_number="2.3",
    )

    assert result.selected_table is None
    assert result.matching_strategy == "ambiguous"
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.check_id == "PTR_TABLE"
    assert finding.code == "PTR_TABLE_CANDIDATE_AMBIGUOUS"
    assert finding.severity == "warn"
    assert finding.expected == "表1"
    assert finding.actual == [
        {"table_id": "report-table-left", "table_number": "1", "caption": "表 1 参数", "parameter_names": ["脉冲宽度", "输出电压"], "score": 0.5},
        {"table_id": "report-table-right", "table_number": "1", "caption": "表 1 参数", "parameter_names": ["基础频率", "输出电压"], "score": 0.5},
    ]
    assert finding.evidence
    assert finding.metadata["matching_strategy"] == "ambiguous"


def test_selector_prefers_merged_table_when_candidates_are_otherwise_tied() -> None:
    expected = _table("ptr-table-1", "1", "表 1 参数", ["脉冲宽度"])
    fragment = _table("report-table-fragment", "1", "表 1 参数", ["脉冲宽度"])
    merged = _table("report-table-merged", "1", "表 1 参数", ["脉冲宽度"], metadata={"merged": True})

    result = select_report_table_candidate(
        expected,
        [fragment, merged],
        table_number="1",
        task_id="task-ptr",
        clause_number="2.3",
    )

    assert result.selected_table == merged
    assert result.findings == []
    assert result.matching_strategy == "merged_table_preferred"


def _table(
    table_id: str,
    table_number: str,
    caption: str,
    parameter_names: list[str],
    *,
    metadata: dict[str, object] | None = None,
) -> CanonicalTable:
    return CanonicalTable(
        table_id=table_id,
        table_number=table_number,
        caption=caption,
        parameter_records=[
            ParameterRecord(parameter_name=name, dimensions={"型号": "全部型号"}, values={"标准设置": "1"})
            for name in parameter_names
        ],
        metadata=metadata or {},
    )
