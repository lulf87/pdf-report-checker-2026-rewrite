from app.domain.finding import FindingSeverity
from app.domain.report import ReportDocument
from app.domain.result import CheckStatus
from app.rules.report.c08_non_empty_fields import check_c08_non_empty_fields, is_effectively_empty
from app.rules.report.context import CheckContext

from .helpers import item


def test_c08_treats_slash_and_em_dash_as_non_empty_placeholders() -> None:
    assert is_effectively_empty("") is True
    assert is_effectively_empty("   ") is True
    assert is_effectively_empty("/") is False
    assert is_effectively_empty("——") is False

    document = ReportDocument(inspection_items=[item(1, result="——", conclusion="/", remark="/")])
    result = check_c08_non_empty_fields(document, CheckContext(task_id="task-c08"))

    assert result.status == CheckStatus.PASS
    assert result.findings == []


def test_c08_reports_empty_result_conclusion_and_remark_fields() -> None:
    document = ReportDocument(inspection_items=[item(1, result="", conclusion="", remark="")])

    result = check_c08_non_empty_fields(document, CheckContext(task_id="task-c08"))

    assert result.status == CheckStatus.FAIL
    assert [finding.code for finding in result.findings] == [
        "INSPECTION_FIELD_EMPTY",
        "INSPECTION_FIELD_EMPTY",
        "INSPECTION_FIELD_EMPTY",
    ]
    assert all(finding.severity == FindingSeverity.ERROR for finding in result.findings)
    assert [finding.metadata["field_name"] for finding in result.findings] == ["检验结果", "单项结论", "备注"]


def test_c08_checks_each_row_instead_of_hiding_empty_continuation_fields() -> None:
    document = ReportDocument(
        inspection_items=[
            item(1, result="符合要求", conclusion="符合", remark="/", row=0),
            item(1, result="", conclusion="符合", remark="/", row=1),
        ]
    )

    result = check_c08_non_empty_fields(document, CheckContext(task_id="task-c08"))

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    assert result.findings[0].metadata["row_index"] == 1
    assert result.findings[0].metadata["field_name"] == "检验结果"
