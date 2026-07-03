from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import FindingSeverity
from app.domain.report import FirstPageInfo, ReportDocument, ReportField, ThirdPageInfo
from app.domain.result import CheckStatus
from app.rules.report.c01_home_vs_third import CheckContext, check_c01_home_vs_third


def _field(name: str, value: str, *, page_number: int, attr: str | None = None) -> ReportField:
    location = Location(
        source_id="report-fixture",
        source_type=SourceType.REPORT,
        page_number=page_number,
        column_name=name,
    )
    return ReportField(
        name=name,
        raw_value=value,
        value=value,
        location=location,
        evidence=[
            Evidence(
                id=f"ev-{page_number}-{attr or name}",
                source_type=SourceType.REPORT,
                location=location,
                raw_text=f"{name}：{value}",
                value=value,
                method=EvidenceMethod.PDF_TEXT,
            )
        ],
    )


def _document(
    *,
    first_client: str | None = "苏州元科医疗器械有限公司",
    third_client: str | None = "苏州元科医疗器械有限公司",
    first_sample_name: str | None = "一次性使用消化道脉冲电场消融导管",
    third_sample_name: str | None = "一次性使用消化道脉冲电场消融导管",
    first_model_spec: str | None = "RMC01",
    third_model_spec: str | None = "RMC01",
    first_inspection_type: str | None = "委托检验",
    third_inspection_type: str | None = "委托检验",
) -> ReportDocument:
    first_fields: list[ReportField] = []
    third_fields: list[ReportField] = []

    first = FirstPageInfo()
    third = ThirdPageInfo()

    if first_client is not None:
        first.client = _field("委托方", first_client, page_number=1, attr="first-client")
        first_fields.append(first.client)
    if first_sample_name is not None:
        first.sample_name = _field("样品名称", first_sample_name, page_number=1, attr="first-sample")
        first_fields.append(first.sample_name)
    if first_model_spec is not None:
        first.model_spec = _field("型号规格", first_model_spec, page_number=1, attr="first-model")
        first_fields.append(first.model_spec)
    if first_inspection_type is not None:
        first_fields.append(_field("检验类别", first_inspection_type, page_number=1, attr="first-inspection-type"))
    first.fields = first_fields
    first.evidence = [evidence for field in first_fields for evidence in field.evidence]

    if third_client is not None:
        third.client = _field("委托方", third_client, page_number=3, attr="third-client")
        third_fields.append(third.client)
    if third_sample_name is not None:
        third_sample_field = _field("样品名称", third_sample_name, page_number=3, attr="third-sample")
        third_fields.append(third_sample_field)
    if third_model_spec is not None:
        third.model_spec = _field("型号规格", third_model_spec, page_number=3, attr="third-model")
        third_fields.append(third.model_spec)
    if third_inspection_type is not None:
        third_fields.append(_field("检验类别", third_inspection_type, page_number=3, attr="third-inspection-type"))
    third.fields = third_fields
    third.evidence = [evidence for field in third_fields for evidence in field.evidence]

    return ReportDocument(first_page=first, third_page=third, page_map={"first_page": 1, "third_page": 3})


def test_c01_passes_when_home_and_third_page_identity_fields_match() -> None:
    result = check_c01_home_vs_third(_document(), CheckContext(task_id="task-c01"))

    assert result.check_id == "C01"
    assert result.check_name == "首页与第三页一致性"
    assert result.status == CheckStatus.PASS
    assert result.severity == FindingSeverity.INFO
    assert result.findings == []
    assert result.metadata["field_results"] == [
        {"field": "委托方", "matched": True},
        {"field": "样品名称", "matched": True},
        {"field": "型号规格", "matched": True},
    ]


def test_c01_pass_result_includes_comparison_details_for_user_explanation() -> None:
    result = check_c01_home_vs_third(_document(), CheckContext(task_id="task-c01"))

    details = result.metadata["comparison_details"]

    assert details["title"] == "首页与报告首页一致性"
    assert details["overall_status"] == "match"
    assert "均一致" in details["overall_reason"]
    assert details["sources"] == [
        {
            "source_key": "cover_page",
            "label": "封面页",
            "page_number": 1,
            "display_page_label": "PDF 第 1 页",
            "section": "报告封面",
        },
        {
            "source_key": "report_home_page",
            "label": "报告首页",
            "page_number": 3,
            "display_page_label": "PDF 第 3 页 / 报告第 1 页",
            "section": "检验报告首页",
        },
    ]
    fields_by_label = {field["field_label"]: field for field in details["fields"]}
    assert {"委托方", "样品名称", "型号规格", "检验类别"}.issubset(fields_by_label)
    assert fields_by_label["委托方"]["left"]["raw_text"] == "苏州元科医疗器械有限公司"
    assert fields_by_label["委托方"]["right"]["raw_text"] == "苏州元科医疗器械有限公司"
    assert fields_by_label["委托方"]["status"] == "match"
    assert fields_by_label["检验类别"]["status"] == "match"
    assert "/Users/" not in str(details)


def test_c01_returns_error_finding_for_each_strict_field_mismatch() -> None:
    result = check_c01_home_vs_third(
        _document(
            third_client="苏州元科医疗器械股份有限公司",
            third_model_spec="RMC02",
        ),
        CheckContext(task_id="task-c01"),
    )

    assert result.status == CheckStatus.FAIL
    assert result.severity == FindingSeverity.ERROR

    findings_by_field = {finding.metadata["field_name"]: finding for finding in result.findings}
    assert set(findings_by_field) == {"委托方", "型号规格"}

    client_finding = findings_by_field["委托方"]
    assert client_finding.check_id == "C01"
    assert client_finding.severity == FindingSeverity.ERROR
    assert client_finding.code == "C01_FIELD_MISMATCH"
    assert client_finding.expected == "苏州元科医疗器械有限公司"
    assert client_finding.actual == "苏州元科医疗器械股份有限公司"
    assert {evidence.location.page_number for evidence in client_finding.evidence} == {1, 3}

    details = result.metadata["comparison_details"]
    fields_by_label = {field["field_label"]: field for field in details["fields"]}
    assert details["overall_status"] == "mismatch"
    assert "委托方" in details["overall_reason"]
    assert "型号规格" in details["overall_reason"]
    assert fields_by_label["委托方"]["status"] == "mismatch"
    assert fields_by_label["委托方"]["reason"] == "两处摘录不一致"


def test_c01_returns_error_for_sample_name_mismatch() -> None:
    result = check_c01_home_vs_third(
        _document(third_sample_name="一次性使用消化道脉冲电场消融系统"),
        CheckContext(task_id="task-c01"),
    )

    assert result.status == CheckStatus.FAIL
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == FindingSeverity.ERROR
    assert finding.code == "C01_FIELD_MISMATCH"
    assert finding.metadata["field_name"] == "样品名称"
    assert finding.expected == "一次性使用消化道脉冲电场消融导管"
    assert finding.actual == "一次性使用消化道脉冲电场消融系统"


def test_c01_treats_spaces_fullwidth_case_and_punctuation_differences_as_mismatch() -> None:
    result = check_c01_home_vs_third(
        _document(
            first_client="苏州 元科医疗器械有限公司",
            third_client="苏州元科医疗器械有限公司",
            first_sample_name="A型-消融导管",
            third_sample_name="a型 消融导管",
            first_model_spec="RMC01-A",
            third_model_spec="ＲＭＣ０１－Ａ",
        ),
        CheckContext(task_id="task-c01"),
    )

    findings_by_field = {finding.metadata["field_name"]: finding for finding in result.findings}

    assert result.status == CheckStatus.FAIL
    assert set(findings_by_field) == {"委托方", "样品名称", "型号规格"}
    assert findings_by_field["委托方"].expected == "苏州 元科医疗器械有限公司"
    assert findings_by_field["委托方"].actual == "苏州元科医疗器械有限公司"
    assert findings_by_field["样品名称"].expected == "A型-消融导管"
    assert findings_by_field["样品名称"].actual == "a型 消融导管"
    assert findings_by_field["型号规格"].expected == "RMC01-A"
    assert findings_by_field["型号规格"].actual == "ＲＭＣ０１－Ａ"


def test_c01_reports_missing_third_page_field_as_error_with_missing_evidence() -> None:
    result = check_c01_home_vs_third(
        _document(third_sample_name=None),
        CheckContext(task_id="task-c01"),
    )

    assert result.status == CheckStatus.FAIL
    assert result.severity == FindingSeverity.ERROR
    assert len(result.findings) == 1

    finding = result.findings[0]
    assert finding.check_id == "C01"
    assert finding.code == "C01_FIELD_MISSING"
    assert finding.severity == FindingSeverity.ERROR
    assert finding.metadata["field_name"] == "样品名称"
    assert finding.expected == "一次性使用消化道脉冲电场消融导管"
    assert finding.actual is None
    assert finding.location is not None
    assert finding.location.page_number == 3
    assert finding.location.section == "third_page"
    assert finding.missing_evidence[0].label == "第三页样品名称"


def test_c01_reports_missing_home_page_field_as_error_with_missing_evidence() -> None:
    result = check_c01_home_vs_third(
        _document(first_client=None),
        CheckContext(task_id="task-c01"),
    )

    assert result.status == CheckStatus.FAIL
    assert result.severity == FindingSeverity.ERROR
    assert len(result.findings) == 1

    finding = result.findings[0]
    assert finding.check_id == "C01"
    assert finding.code == "C01_FIELD_MISSING"
    assert finding.severity == FindingSeverity.ERROR
    assert finding.metadata["field_name"] == "委托方"
    assert finding.expected is None
    assert finding.actual == "苏州元科医疗器械有限公司"
    assert finding.location is not None
    assert finding.location.page_number == 1
    assert finding.location.section == "first_page"
    assert finding.missing_evidence[0].label == "首页委托方"


def test_c01_reports_each_field_when_multiple_fields_are_missing_or_mismatched() -> None:
    result = check_c01_home_vs_third(
        _document(
            first_client=None,
            third_sample_name="一次性使用消化道脉冲电场消融系统",
            third_model_spec=None,
        ),
        CheckContext(task_id="task-c01"),
    )

    findings_by_field = {finding.metadata["field_name"]: finding for finding in result.findings}

    assert result.status == CheckStatus.FAIL
    assert set(findings_by_field) == {"委托方", "样品名称", "型号规格"}
    assert findings_by_field["委托方"].code == "C01_FIELD_MISSING"
    assert findings_by_field["样品名称"].code == "C01_FIELD_MISMATCH"
    assert findings_by_field["型号规格"].code == "C01_FIELD_MISSING"
