from app.domain.report import InspectionItem
from app.domain.report_scope import ExternalStandardRange, ReportInspectionScope, ReportScopeRange
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


def test_report_scope_consistency_marks_excluded_placeholder_without_finding() -> None:
    result = check_report_scope_consistency(
        _scope_5780(),
        [
            InspectionItem(
                sequence_raw="164",
                sequence=164,
                standard_clause="2.6",
                standard_requirement="电磁兼容性",
                test_result="/",
                conclusion="/",
                remark="/",
                source_page=66,
            ),
        ],
        task_id="task-5780-excluded-placeholder",
    )

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    scope_consistency = result.metadata["scope_consistency"]
    assert scope_consistency["actual_report_scope"] == []
    assert scope_consistency["excluded_placeholders"] == [
        {
            "item_no": "164",
            "clause_number": "2.6",
            "excluded_topic": "电磁兼容性",
            "standard_requirement": "电磁兼容性",
            "test_result": "/",
            "single_conclusion": "/",
            "remark": "/",
            "reason": "报告首页已排除电磁兼容性，实际检验表仅保留空白占位行。",
        }
    ]


def test_report_scope_consistency_accepts_external_report_reference_placeholder_with_passing_conclusion() -> None:
    result = check_report_scope_consistency(
        _scope_5780(),
        [
            InspectionItem(
                sequence_raw="164",
                sequence=164,
                standard_clause="2.6",
                standard_requirement="电磁兼容性",
                test_result="/",
                conclusion="符合",
                remark="/",
                source_page=66,
            ),
        ],
        task_id="task-excluded-external-reference",
    )

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    scope_consistency = result.metadata["scope_consistency"]
    assert scope_consistency["actual_report_scope"] == []
    assert scope_consistency["excluded_placeholders"][0]["single_conclusion"] == "符合"
    assert "外部报告引用占位行" in scope_consistency["excluded_placeholders"][0]["reason"]


def test_report_scope_consistency_reports_excluded_topic_when_placeholder_has_result() -> None:
    result = check_report_scope_consistency(
        _scope_5780(),
        [
            InspectionItem(
                sequence_raw="164",
                sequence=164,
                standard_clause="2.6",
                standard_requirement="电磁兼容性",
                test_result="符合要求",
                conclusion="符合",
                remark="/",
                source_page=66,
            ),
        ],
        task_id="task-5780-excluded-substantive",
    )

    assert result.status == CheckStatus.FAIL
    assert [finding.code for finding in result.findings] == ["PTR_SCOPE_EXCLUDED_TOPIC_PRESENT"]
    assert result.findings[0].metadata["excluded_topic"] == "电磁兼容性"
    assert result.findings[0].metadata["test_result"] == "符合要求"
    assert result.findings[0].metadata["single_conclusion"] == "符合"


def test_report_scope_consistency_does_not_treat_passing_conclusion_as_placeholder_without_external_reference() -> None:
    result = check_report_scope_consistency(
        _scope(),
        [
            *_items(),
            InspectionItem(
                sequence_raw="160",
                sequence=160,
                standard_clause="2.5.2.2",
                standard_requirement="电磁兼容性",
                test_result="/",
                conclusion="符合",
                remark="/",
                source_page=100,
            ),
        ],
        task_id="task-excluded-no-external-reference",
    )

    assert result.status == CheckStatus.FAIL
    assert [finding.code for finding in result.findings] == ["PTR_SCOPE_EXCLUDED_TOPIC_PRESENT"]


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


def test_report_scope_consistency_preserves_pm3562_exact_subclauses() -> None:
    result = check_report_scope_consistency(
        ReportInspectionScope(
            declared_scope_items=["2.2.2", "2.3", "2.6", "2.7", "2.8.2"],
            declared_scope_ranges=[ReportScopeRange(start="2.1.1", end="2.1.12", source_text="2.1.1～2.1.12")],
            source_page=1,
            source_text="2.1.1～2.1.12、2.2.2、2.3（仅检 PVC 反应）、2.6、2.7、2.8.2",
            external_standard_ranges=[
                ExternalStandardRange(
                    start_item_no="1",
                    end_item_no="24",
                    standard="GB 16174.1-2024",
                    source_page=5,
                    source_text="序号 1～24 为 GB 16174.1-2024 标准的内容",
                ),
                ExternalStandardRange(
                    start_item_no="25",
                    end_item_no="37",
                    standard="GB 16174.2-2024",
                    source_page=5,
                    source_text="序号 25～37 为 GB 16174.2-2024 标准的内容",
                ),
            ],
            ptr_direct_content_starts_after="37",
        ),
        [
            InspectionItem(sequence_raw="1", sequence=1, standard_clause="GB 16174.1-2024", standard_requirement="通用标准起点", source_page=6),
            InspectionItem(sequence_raw="24", sequence=24, standard_clause="GB 16174.1-2024", standard_requirement="通用标准终点", source_page=12),
            InspectionItem(sequence_raw="25", sequence=25, standard_clause="GB 16174.2-2024", standard_requirement="专用标准起点", source_page=13),
            InspectionItem(sequence_raw="37", sequence=37, standard_clause="GB 16174.2-2024", standard_requirement="专用标准终点", source_page=19),
            *[
                InspectionItem(
                    sequence_raw=str(item_no),
                    sequence=item_no,
                    standard_clause=f"2.1.{item_no - 37}",
                    standard_requirement=f"2.1.{item_no - 37} 项",
                    test_result="符合要求",
                    conclusion="符合",
                    source_page=20,
                )
                for item_no in range(38, 50)
            ],
            InspectionItem(sequence_raw="50", sequence=50, standard_clause="2.2.2", standard_requirement="紧急起搏模式", source_page=21),
            InspectionItem(sequence_raw="51", sequence=51, standard_clause="2.3", standard_requirement="PVC 反应 / PVC Response", remark="仅检 PVC 反应", source_page=21),
            InspectionItem(sequence_raw="52", sequence=52, standard_clause="2.6", standard_requirement="通用要求，见序号 1～24", source_page=21),
            InspectionItem(sequence_raw="53", sequence=53, standard_clause="2.7", standard_requirement="专用要求，见序号 25～37", source_page=21),
            InspectionItem(sequence_raw="54", sequence=54, standard_clause="2.8.2", standard_requirement="扭矩扳手尺寸", test_result="A=0.884，B=0.993", source_page=21),
        ],
        task_id="task-pm3562-scope",
    )

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["scope_consistency"]["actual_report_scope"] == [
        "2.1.1",
        "2.1.2",
        "2.1.3",
        "2.1.4",
        "2.1.5",
        "2.1.6",
        "2.1.7",
        "2.1.8",
        "2.1.9",
        "2.1.10",
        "2.1.11",
        "2.1.12",
        "2.2.2",
        "2.3",
        "2.6",
        "2.7",
        "2.8.2",
    ]


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


def _scope_5780() -> ReportInspectionScope:
    return ReportInspectionScope(
        declared_scope_ranges=[ReportScopeRange(start="2.1", end="2.6", source_text="2.1～2.6")],
        excluded_topics=["生物相容性", "电磁兼容性"],
        source_page=1,
        source_text="2.1～2.6（除生物相容性、电磁兼容性）。电磁兼容性检验见国医检(磁)字 QW2025 第 5781 号",
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
