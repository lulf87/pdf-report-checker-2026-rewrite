from app.domain.finding import FindingSeverity
from app.domain.report import ReportDocument
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
    assert finding.metadata["row_index"] == 0
    assert finding.metadata["field_name"] == "检验结果"
    assert finding.metadata["is_merged_cell"] is False


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


def test_c08_reports_each_affected_row_when_merged_anchor_is_empty() -> None:
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
    assert len(result.findings) == 2
    assert [finding.metadata["row_index"] for finding in result.findings] == [0, 1]
    assert [finding.metadata["field_name"] for finding in result.findings] == ["检验结果", "检验结果"]
    assert result.findings[0].code == "INSPECTION_MERGED_FIELD_EMPTY"
    assert result.findings[0].metadata["is_merged_cell"] is True
    assert result.findings[1].code == "INSPECTION_FIELD_EMPTY"


def test_c08_checks_continuation_rows_instead_of_skipping_them() -> None:
    document = ReportDocument(
        inspection_items=[
            item(10, result="符合要求", conclusion="符合", remark="/", row=0),
            item(10, raw="续10", result="", conclusion="符合", remark="/", continued=True, row=0, page=6),
        ]
    )

    result = _run(document)

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    assert result.findings[0].metadata["item_no"] == "续10"
    assert result.findings[0].metadata["field_name"] == "检验结果"


def test_c08_does_not_report_blank_sequence_number_because_c09_owns_sequence_continuity() -> None:
    result = _run(ReportDocument(inspection_items=[item(None, raw="", result="符合要求", conclusion="符合", remark="/")]))

    assert result.status == CheckStatus.PASS
    assert result.findings == []
