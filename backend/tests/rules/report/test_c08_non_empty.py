from app.domain.finding import FindingSeverity
from app.domain.report import InspectionItem, ReportDocument
from app.domain.result import CheckStatus
from app.rules.report.c08_non_empty import check_c08_non_empty_fields, is_empty_required_field
from app.rules.report.context import CheckContext

from .helpers import item


def _run(document: ReportDocument):
    return check_c08_non_empty_fields(document, CheckContext(task_id="task-c08"))


def _item_with_provenance(
    seq: int | None,
    *,
    result: str | None = "符合要求",
    conclusion: str | None = "符合",
    remark: str | None = "/",
    provenance: dict[str, str] | None = None,
    raw: str | None = None,
    continued: bool = False,
    row: int = 0,
):
    return item(
        seq,
        raw=raw,
        result=result,
        conclusion=conclusion,
        remark=remark,
        continued=continued,
        row=row,
    ).model_copy(update={"field_provenance": provenance or {}})


def test_is_empty_required_field_treats_only_blank_text_as_empty() -> None:
    assert is_empty_required_field(None) is True
    assert is_empty_required_field("") is True
    assert is_empty_required_field("   \n\t") is True
    assert is_empty_required_field("/") is False
    assert is_empty_required_field("——") is False


def test_c08_passes_when_result_conclusion_and_remark_have_text() -> None:
    result = _run(ReportDocument(inspection_items=[item(1, result="符合要求", conclusion="符合", remark="正常")]))

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_reports_empty_test_result() -> None:
    result = _run(ReportDocument(inspection_items=[item(1, result="", conclusion="符合", remark="正常")]))

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "INSPECTION_FIELD_EMPTY"
    assert finding.severity == FindingSeverity.ERROR
    assert finding.expected == "非空值"
    assert finding.actual == ""
    assert finding.metadata["item_no"] == "1"
    assert finding.metadata["field_name"] == "检验结果"
    assert finding.metadata["field_key"] == "test_result"
    assert finding.metadata["group_row_count"] == 1
    assert finding.metadata["pages"] == [5]
    assert finding.metadata["suppressed_physical_row_count"] == 0
    assert finding.metadata["source_rows"][0]["row_index"] == 0


def test_c08_reports_empty_conclusion() -> None:
    result = _run(ReportDocument(inspection_items=[item(2, result="符合要求", conclusion="", remark="正常")]))

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    assert result.findings[0].code == "INSPECTION_FIELD_EMPTY"
    assert result.findings[0].metadata["field_name"] == "单项结论"


def test_c08_reports_empty_remark() -> None:
    result = _run(ReportDocument(inspection_items=[item(3, result="符合要求", conclusion="符合", remark="")]))

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    assert result.findings[0].code == "INSPECTION_FIELD_EMPTY"
    assert result.findings[0].metadata["field_name"] == "备注"


def test_c08_reports_one_finding_per_empty_required_field() -> None:
    result = _run(ReportDocument(inspection_items=[item(4, result="", conclusion="", remark="")]))

    assert result.status == CheckStatus.FAIL
    assert [finding.metadata["field_name"] for finding in result.findings] == ["检验结果", "单项结论", "备注"]
    assert all(finding.code == "INSPECTION_FIELD_EMPTY" for finding in result.findings)


def test_c08_treats_pure_spaces_as_empty() -> None:
    result = _run(ReportDocument(inspection_items=[item(5, result="  ", conclusion="\n", remark="\t")]))

    assert result.status == CheckStatus.FAIL
    assert [finding.metadata["field_name"] for finding in result.findings] == ["检验结果", "单项结论", "备注"]


def test_c08_treats_slash_as_non_empty_placeholder() -> None:
    result = _run(ReportDocument(inspection_items=[item(6, result="/", conclusion="/", remark="/")]))

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_treats_em_dash_as_non_empty_placeholder() -> None:
    result = _run(ReportDocument(inspection_items=[item(7, result="——", conclusion="——", remark="——")]))

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_treats_combined_conclusion_remark_as_non_empty_remark() -> None:
    document = ReportDocument(
        inspection_items=[
            item(
                126,
                raw="126",
                result="符合要求",
                conclusion="符合 /",
                remark="",
                page=87,
                row=3,
                name="指示灯颜色",
            )
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_treats_combined_test_result_as_conclusion_remark_when_right_fields_are_blank() -> None:
    document = ReportDocument(
        inspection_items=[
            item(
                126,
                raw="126",
                result="符合 /",
                conclusion="",
                remark="",
                page=87,
                row=3,
                name="指示灯颜色",
            )
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_treats_shifted_conclusion_slash_as_remark_placeholder() -> None:
    document = ReportDocument(
        inspection_items=[
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

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_still_reports_empty_remark_without_combined_slash_evidence() -> None:
    result = _run(ReportDocument(inspection_items=[item(126, raw="126", result="符合", conclusion="符合", remark="")]))

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    assert result.findings[0].metadata["field_key"] == "remark"


def test_c08_does_not_use_standard_requirement_slash_as_remark_evidence() -> None:
    row = item(126, raw="126", result="符合", conclusion="符合", remark="")
    row.standard_requirement = "将通用标准中的表 2 替换为表 201.101 / 附注。"
    result = _run(ReportDocument(inspection_items=[row]))

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    assert result.findings[0].metadata["field_key"] == "remark"


def test_c08_passes_when_merged_cell_values_are_inherited_by_extractor() -> None:
    document = ReportDocument(
        inspection_items=[
            _item_with_provenance(8, result="符合要求", conclusion="符合", remark="/", row=0),
            _item_with_provenance(
                None,
                result="符合要求",
                conclusion="符合",
                remark="/",
                provenance={
                    "test_result": "merge_inferred",
                    "conclusion": "merge_inferred",
                    "remark": "merge_inferred",
                },
                row=1,
            ),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_reports_group_level_empty_result_once_when_merged_anchor_is_empty() -> None:
    document = ReportDocument(
        inspection_items=[
            _item_with_provenance(
                9,
                result="",
                conclusion="符合",
                remark="/",
                provenance={"test_result": "merge_anchor_empty"},
                row=0,
            ),
            _item_with_provenance(
                None,
                result="",
                conclusion="符合",
                remark="/",
                provenance={"test_result": "native"},
                row=1,
            ),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "INSPECTION_FIELD_EMPTY"
    assert finding.metadata["field_name"] == "检验结果"
    assert finding.metadata["group_row_count"] == 2
    assert finding.metadata["empty_physical_rows"] == [
        {"source_index": 0, "page_number": 5, "row_index": 0, "sequence_raw": "9"},
        {"source_index": 1, "page_number": 5, "row_index": 1, "sequence_raw": ""},
    ]
    assert finding.metadata["suppressed_physical_row_count"] == 1


def test_c08_uses_group_effective_result_instead_of_repeating_empty_physical_rows() -> None:
    document = ReportDocument(
        inspection_items=[
            item(10, result="符合要求", conclusion="符合", remark="/", row=0),
            item(10, raw="10", result="", conclusion="", remark="", row=1),
            item(10, raw="10", result="", conclusion="", remark="", row=2),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_uses_group_effective_conclusion_when_only_one_row_has_conclusion() -> None:
    document = ReportDocument(
        inspection_items=[
            item(11, result="符合要求", conclusion="", remark="/", row=0),
            item(11, raw="11", result="——", conclusion="符合", remark="", row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_uses_group_effective_remark_when_only_one_row_has_slash_remark() -> None:
    document = ReportDocument(
        inspection_items=[
            item(12, result="符合要求", conclusion="符合", remark="", row=0),
            item(12, raw="12", result="——", conclusion="", remark="/", row=1),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_reports_group_level_empty_fields_once_per_field() -> None:
    document = ReportDocument(
        inspection_items=[
            item(13, result="", conclusion="", remark="", row=0),
            item(13, raw="13", result=" ", conclusion="\n", remark="\t", row=1),
            item(13, raw="13", result=None, conclusion=None, remark=None, row=2),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert [finding.metadata["field_key"] for finding in result.findings] == ["test_result", "conclusion", "remark"]
    assert len(result.findings) == 3
    assert all(finding.metadata["group_row_count"] == 3 for finding in result.findings)
    assert all(finding.metadata["suppressed_physical_row_count"] == 2 for finding in result.findings)


def test_c08_continuation_rows_are_grouped_without_row_level_noise() -> None:
    document = ReportDocument(
        inspection_items=[
            item(3, raw="3", result="符合要求", conclusion="符合", remark="/", row=0, page=5),
            item(3, raw="续3", result="", conclusion="", remark="", continued=True, row=0, page=6),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_blank_sequence_payload_row_is_grouped_without_extra_row_level_finding() -> None:
    document = ReportDocument(
        inspection_items=[
            item(14, result="符合要求", conclusion="符合", remark="/", row=0),
            item(None, raw="", result="", conclusion="", remark="", row=1, name="a) 子项要求"),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_ungrouped_blank_row_does_not_create_finding() -> None:
    blank_row = InspectionItem(sequence_raw="", source_page=7, row_index_in_page=1)

    result = _run(ReportDocument(inspection_items=[item(15, result="符合要求", conclusion="符合", remark="/"), blank_row]))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["ungrouped_row_count"] == 1


def test_c08_finding_metadata_contains_group_details() -> None:
    result = _run(
        ReportDocument(
            inspection_items=[
                item(16, result="", conclusion="符合", remark="/", page=8, row=0),
                item(16, raw="16", result="", conclusion="", remark="", page=8, row=1),
            ]
        )
    )

    finding = result.findings[0]
    assert finding.metadata["item_no"] == "16"
    assert finding.metadata["field_key"] == "test_result"
    assert finding.metadata["group_row_count"] == 2
    assert finding.metadata["pages"] == [8]
    assert finding.metadata["suppressed_physical_row_count"] == 1
    assert finding.metadata["source_rows"] == [
        {
            "source_index": 0,
            "page_number": 8,
            "row_index": 0,
            "sequence_raw": "16",
            "test_result": "",
            "single_conclusion": "符合",
            "remark": "/",
        },
        {
            "source_index": 1,
            "page_number": 8,
            "row_index": 1,
            "sequence_raw": "16",
            "test_result": "",
            "single_conclusion": "",
            "remark": "",
        },
    ]


def test_c08_qw2025_2795_like_cross_page_mini_fixture_does_not_emit_child_row_noise() -> None:
    document = ReportDocument(
        inspection_items=[
            item(3, raw="3", result="符合要求", conclusion="/", remark="/", page=14, row=31, name="检验项目 3"),
            item(None, raw="", result="", conclusion="", remark="", page=14, row=32, name="a) 子项目"),
            item(3, raw="续 3", result="符合要求", conclusion="", remark="", continued=True, page=15, row=0, name="检验项目 3 续"),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_does_not_report_requirement_text_that_polluted_item_no() -> None:
    document = ReportDocument(
        inspection_items=[
            item(10, raw="10", result="符合要求", conclusion="符合", remark="/", page=12, row=0),
            item(
                500,
                raw="——所有其他 ME 设备和 ME 系统，500V。",
                result="",
                conclusion="",
                remark="",
                page=12,
                row=1,
            ),
            item(15, raw="15", result="符合要求", conclusion="符合", remark="/", page=13, row=0),
            item(
                48,
                raw="当外壳的分类为 IPX0 时，保持 ME 设备和其部件在潮湿箱里 48h。",
                result="",
                conclusion="",
                remark="",
                page=13,
                row=1,
            ),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["group_count"] == 2
    assert any(
        diagnostic["code"] == "SEQUENCE_TEXT_LOOKS_LIKE_REQUIREMENT"
        for diagnostic in result.metadata["group_builder_diagnostics"]
    )


def test_c08_ungrouped_invalid_sequence_text_does_not_expand_to_three_errors() -> None:
    document = ReportDocument(
        inspection_items=[
            item(
                500,
                raw="——所有其他 ME 设备和 ME 系统，500V。",
                result="",
                conclusion="",
                remark="",
                page=12,
                row=1,
            )
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.PASS
    assert result.findings == []
    assert result.metadata["group_count"] == 0
    assert result.metadata["ungrouped_row_count"] == 1


def test_c08_does_not_report_blank_sequence_number_because_c09_owns_sequence_continuity() -> None:
    result = _run(ReportDocument(inspection_items=[item(None, raw="", result="符合要求", conclusion="符合", remark="/")]))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
