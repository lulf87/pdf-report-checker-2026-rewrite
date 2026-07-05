from app.domain.report import InspectionItem
from app.domain.report_scope import ExternalStandardRange, ReportInspectionScope
from app.domain.result import CheckStatus
from app.rules.ptr.report_scope_consistency import check_report_scope_consistency


def test_report_scope_consistency_passes_when_declared_scope_matches_actual_items() -> None:
    result = check_report_scope_consistency(
        _scope(),
        _items(),
        task_id="task-scope-pass",
    )

    assert result.check_id == "PTR_REPORT_SCOPE"
    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["scope_consistency"]["status"] == "passed"
    assert result.metadata["scope_consistency"]["actual_report_scope"] == ["2.2", "2.5", "2.6"]


def test_report_scope_consistency_reports_declared_item_missing() -> None:
    result = check_report_scope_consistency(
        _scope(),
        [item for item in _items() if item.standard_clause != "2.6"],
        task_id="task-scope-missing",
    )

    assert result.status == CheckStatus.FAIL
    assert [finding.code for finding in result.findings] == ["PTR_SCOPE_DECLARED_ITEM_MISSING_IN_REPORT"]
    assert result.findings[0].metadata["clause_number"] == "2.6"
    assert result.metadata["scope_consistency"]["status"] == "failed"


def test_report_scope_consistency_reports_undeclared_report_item() -> None:
    result = check_report_scope_consistency(
        _scope(),
        [
            *_items(),
            InspectionItem(sequence_raw="160", sequence=160, standard_clause="2.7", standard_requirement="额外项目", source_page=100),
        ],
        task_id="task-scope-extra",
    )

    assert [finding.code for finding in result.findings] == ["PTR_SCOPE_UNDECLARED_REPORT_ITEM"]
    assert result.findings[0].metadata["clause_number"] == "2.7"


def test_report_scope_consistency_reports_excluded_topic_present() -> None:
    result = check_report_scope_consistency(
        _scope(),
        [
            *_items(),
            InspectionItem(
                sequence_raw="160",
                sequence=160,
                standard_clause="2.5.2.2",
                standard_requirement="电磁兼容性应符合 YY 9706.102-2021。",
                source_page=100,
            ),
        ],
        task_id="task-scope-excluded",
    )

    assert [finding.code for finding in result.findings] == ["PTR_SCOPE_EXCLUDED_TOPIC_PRESENT"]
    assert result.findings[0].metadata["excluded_topic"] == "电磁兼容性"


def test_report_scope_consistency_reports_external_standard_range_mismatch() -> None:
    result = check_report_scope_consistency(
        _scope(),
        [item for item in _items() if item.sequence != 118],
        task_id="task-scope-range",
    )

    assert [finding.code for finding in result.findings] == ["PTR_SCOPE_STANDARD_RANGE_MISMATCH"]
    assert result.findings[0].metadata["standard"] == "GB 9706.1-2020"


def test_report_scope_consistency_accepts_external_range_declared_standard_without_repeated_item_standard_names() -> None:
    result = check_report_scope_consistency(
        _scope(),
        [
            InspectionItem(sequence_raw="1", sequence=1, standard_clause=None, standard_requirement="通用安全项目起点", source_page=6),
            InspectionItem(sequence_raw="118", sequence=118, standard_clause=None, standard_requirement="通用安全项目终点", source_page=45),
            InspectionItem(sequence_raw="119", sequence=119, standard_clause=None, standard_requirement="专用安全项目起点", source_page=46),
            InspectionItem(sequence_raw="156", sequence=156, standard_clause=None, standard_requirement="专用安全项目终点", source_page=98),
            InspectionItem(sequence_raw="157", sequence=157, standard_clause="2.2", standard_requirement="心脏脉冲电场消融仪输出", source_page=99),
            InspectionItem(sequence_raw="158", sequence=158, standard_clause="2.5", standard_requirement="电气安全", source_page=99),
            InspectionItem(sequence_raw="159", sequence=159, standard_clause="2.6", standard_requirement="软件功能", source_page=99),
        ],
        task_id="task-scope-range-declared-standard",
    )

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["scope_consistency"]["actual_report_scope"] == ["2.2", "2.5", "2.6"]


def test_report_scope_consistency_ignores_external_standard_clause_that_contains_embedded_2x_number() -> None:
    result = check_report_scope_consistency(
        _scope(),
        [
            InspectionItem(sequence_raw="1", sequence=1, standard_clause=None, standard_requirement="通用安全项目起点", source_page=6),
            InspectionItem(sequence_raw="118", sequence=118, standard_clause=None, standard_requirement="通用安全项目终点", source_page=45),
            InspectionItem(sequence_raw="119", sequence=119, standard_clause=None, standard_requirement="专用安全项目起点", source_page=46),
            InspectionItem(
                sequence_raw="续\n129",
                sequence=129,
                is_continuation=True,
                standard_clause="201.7.9.\n2.14",
                standard_requirement="使用说明书还可见 201.15.4.101.1 和 201.15.4.101.2。",
                source_page=85,
            ),
            InspectionItem(sequence_raw="156", sequence=156, standard_clause=None, standard_requirement="专用安全项目终点", source_page=98),
            InspectionItem(sequence_raw="157", sequence=157, standard_clause="2.2", standard_requirement="心脏脉冲电场消融仪输出", source_page=99),
            InspectionItem(sequence_raw="158", sequence=158, standard_clause="2.5", standard_requirement="电气安全", source_page=99),
            InspectionItem(sequence_raw="159", sequence=159, standard_clause="2.6", standard_requirement="软件功能", source_page=99),
        ],
        task_id="task-scope-ignore-external-201",
    )

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["scope_consistency"]["actual_report_scope"] == ["2.2", "2.5", "2.6"]


def _scope() -> ReportInspectionScope:
    return ReportInspectionScope(
        declared_scope_items=["2.2", "2.5", "2.6"],
        excluded_topics=["生物相容性", "电磁兼容性"],
        source_page=3,
        source_text="2.2、2.5、2.6（除生物相容性、电磁兼容性）",
        external_standard_ranges=[
            ExternalStandardRange(
                start_item_no="1",
                end_item_no="118",
                standard="GB 9706.1-2020",
                source_page=5,
                source_text="序号 1～序号 118 为 GB 9706.1-2020 标准的内容",
            ),
            ExternalStandardRange(
                start_item_no="119",
                end_item_no="156",
                standard="GB9706.202-2021",
                source_page=5,
                source_text="序号 119～156 为 GB9706.202-2021 标准的内容",
            ),
        ],
        ptr_direct_content_starts_after="156",
    )


def _items() -> list[InspectionItem]:
    return [
        InspectionItem(sequence_raw="1", sequence=1, standard_clause="GB 9706.1-2020", standard_requirement="GB 9706.1-2020", source_page=6),
        InspectionItem(sequence_raw="118", sequence=118, standard_clause="GB 9706.1-2020", standard_requirement="GB 9706.1-2020", source_page=45),
        InspectionItem(sequence_raw="119", sequence=119, standard_clause="GB9706.202-2021", standard_requirement="GB9706.202-2021", source_page=46),
        InspectionItem(sequence_raw="156", sequence=156, standard_clause="GB9706.202-2021", standard_requirement="GB9706.202-2021", source_page=98),
        InspectionItem(sequence_raw="157", sequence=157, standard_clause="2.2", standard_requirement="心脏脉冲电场消融仪输出", source_page=99),
        InspectionItem(sequence_raw="158", sequence=158, standard_clause="2.5", standard_requirement="电气安全", source_page=99),
        InspectionItem(sequence_raw="159", sequence=159, standard_clause="2.6", standard_requirement="软件功能", source_page=99),
    ]
