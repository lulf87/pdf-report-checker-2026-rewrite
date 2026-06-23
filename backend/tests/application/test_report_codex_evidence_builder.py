from __future__ import annotations

import pytest

from app.application.report_codex_evidence_builder import ReportCodexEvidenceBuilder
from app.domain.codex_review import CodexReviewTargetType
from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.evidence_package import EvidencePackageKind, EvidenceSourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.pdf import ParsedPdf, PdfPage
from app.domain.report import (
    InspectionItem,
    LabelOCRField,
    LabelOCRResult,
    PhotoCaption,
    ReportDocument,
    ReportField,
    SampleComponent,
    ThirdPageInfo,
)
from app.domain.result import CheckResult, CheckStatus
from app.domain.task import TaskType


OLD_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"


@pytest.mark.parametrize(
    ("check_id", "target_type"),
    [
        ("C02", CodexReviewTargetType.LABEL_OCR),
        ("C03", CodexReviewTargetType.LABEL_OCR),
        ("C04", CodexReviewTargetType.SAMPLE_DESCRIPTION),
        ("C05", CodexReviewTargetType.PHOTO_CAPTION),
        ("C06", CodexReviewTargetType.LABEL_OCR),
        ("C07", CodexReviewTargetType.INSPECTION_ITEM),
    ],
)
def test_reviewable_report_findings_build_expected_target_types(
    check_id: str,
    target_type: CodexReviewTargetType,
) -> None:
    finding = _finding(check_id=check_id, metadata=_metadata_for_check(check_id))

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result(check_id, [finding]),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    assert bundle.evidence_package.kind is EvidencePackageKind.REPORT_RULE_REVIEW
    assert bundle.request.targets[0].target_type is target_type
    assert bundle.request.targets[0].target_id == f"report-codex-target-{finding.id}"
    assert bundle.request.targets[0].finding_id == finding.id


@pytest.mark.parametrize("check_id", ["C01", "C08", "C09", "C10", "C11"])
def test_non_priority_report_findings_build_check_summary_target(check_id: str) -> None:
    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result(check_id, [_finding(check_id=check_id)]),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    assert bundle.request.targets[0].target_type is CodexReviewTargetType.CHECK_RESULT
    assert bundle.request.targets[0].check_id == check_id
    assert bundle.evidence_package.metadata["summary_target"] is True


def test_no_findings_builds_check_summary_target() -> None:
    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C02", []),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    assert bundle.request.targets[0].target_type is CodexReviewTargetType.CHECK_RESULT
    assert bundle.evidence_package.items[0].ref_id == "check_result:C02"


def test_target_evidence_refs_exist_and_include_finding_and_rule_context() -> None:
    finding = _finding(check_id="C05", metadata=_metadata_for_check("C05"))

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C05", [finding]),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    target = bundle.evidence_package.targets[0]
    assert set(target.evidence_refs) <= set(items_by_ref)
    assert f"finding:{finding.id}" in items_by_ref
    assert items_by_ref[f"finding:{finding.id}"].source_type is EvidenceSourceType.FINDING
    assert f"rule_context:{finding.id}" in items_by_ref
    assert items_by_ref[f"rule_context:{finding.id}"].source_type is EvidenceSourceType.RULE_CONTEXT
    assert {ref.ref_id for ref in bundle.request.targets[0].evidence_refs} == set(target.evidence_refs)


def test_c02_and_c03_evidence_contains_expected_actual_field_and_ocr_context() -> None:
    findings = [
        _finding(check_id="C02", metadata=_metadata_for_check("C02"), expected="2025/01/02", actual="2025-01-02"),
        _finding(check_id="C03", metadata=_metadata_for_check("C03"), expected="YYYY/MM/DD", actual="YYYY-MM-DD"),
    ]

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C02", findings),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    field_items = [item for item in items_by_ref.values() if item.source_type is EvidenceSourceType.REPORT_FIELD]
    label_items = [item for item in items_by_ref.values() if item.source_type is EvidenceSourceType.LABEL_OCR]
    assert field_items
    assert label_items
    assert any(item.structured["expected"] == "2025/01/02" for item in field_items)
    assert any(item.structured["actual"] == "YYYY-MM-DD" for item in field_items)
    assert any("生产日期" in item.structured["label_fields"] for item in label_items)
    assert any("中文标签 OCR" in item.title for item in label_items)


def test_c04_evidence_contains_sample_description_and_label_context() -> None:
    finding = _finding(check_id="C04", metadata=_metadata_for_check("C04"))

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    sample_item = next(item for item in items_by_ref.values() if item.ref_id.startswith("sample_description:"))
    label_item = next(item for item in items_by_ref.values() if item.source_type is EvidenceSourceType.LABEL_OCR)
    assert sample_item.structured["component_name"] == "输注泵"
    assert sample_item.structured["model"] == "RMC-1"
    assert sample_item.structured["expiration_date"] == "2027-01-02"
    assert label_item.structured["label_id"] == "label-1"


def test_c05_and_c06_evidence_contains_component_and_caption_context() -> None:
    findings = [
        _finding(check_id="C05", metadata=_metadata_for_check("C05")),
        _finding(check_id="C06", metadata=_metadata_for_check("C06")),
    ]

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C05", findings),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    component_items = [item for item in items_by_ref.values() if item.ref_id.startswith("component:")]
    caption_items = [item for item in items_by_ref.values() if item.source_type is EvidenceSourceType.IMAGE_CAPTION]
    label_items = [item for item in items_by_ref.values() if item.source_type is EvidenceSourceType.LABEL_OCR]
    assert component_items
    assert any(item.structured["component_id"] == "component-1" for item in component_items)
    assert any(item.structured["caption_text"] == "图1 输注泵外观照片" for item in caption_items)
    assert any(item.structured["caption_text"] == "图2 输注泵中文标签样张" for item in label_items)


def test_c07_evidence_contains_inspection_result_actual_and_expected_conclusion() -> None:
    finding = _finding(
        check_id="C07",
        expected="不符合",
        actual="符合",
        metadata={
            **_metadata_for_check("C07"),
            "effective_test_results": ["符合要求", "不符合要求"],
            "pages": [4, 5],
            "source_rows": [
                {"source_index": 0, "page_number": 4, "row_index": 2},
                {"source_index": 1, "page_number": 5, "row_index": 0},
            ],
        },
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=_report_document(
            inspection_items=[
                InspectionItem(
                    sequence_raw="1",
                    sequence=1,
                    item_name="外观",
                    standard_clause="2.1",
                    standard_requirement="应符合要求",
                    test_result="符合要求",
                    result_values=["符合要求"],
                    conclusion="符合",
                    remark="/",
                    source_page=4,
                    row_index_in_page=2,
                ),
                InspectionItem(
                    sequence_raw="续 1",
                    sequence=1,
                    is_continuation=True,
                    item_name="外观",
                    standard_clause="2.1",
                    standard_requirement="应符合要求",
                    test_result="不符合要求",
                    result_values=["不符合要求"],
                    conclusion="",
                    remark="/",
                    source_page=5,
                    row_index_in_page=0,
                ),
            ]
        ),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    inspection_item = next(
        item for item in bundle.evidence_package.items if item.source_type is EvidenceSourceType.TABLE
    )
    assert inspection_item.ref_id.startswith("inspection_item:")
    assert inspection_item.structured["inspection_item_group"]["item_no"] == "1"
    assert inspection_item.structured["inspection_item_group"]["effective_test_results"] == [
        "符合要求",
        "不符合要求",
    ]
    assert inspection_item.structured["inspection_item_group"]["actual_conclusion"] == "符合"
    assert inspection_item.structured["inspection_item_group"]["expected_conclusion"] == "不符合"
    assert inspection_item.structured["inspection_item_group"]["pages"] == [4, 5]
    assert inspection_item.structured["inspection_item_group"]["group_row_count"] == 2
    assert inspection_item.structured["inspection_item_group"]["source_rows"][0]["row_index"] == 2
    assert "第三页生产日期" not in inspection_item.model_dump_json()


def test_package_sanitizes_old_new_and_user_absolute_paths() -> None:
    finding = _finding(
        check_id="C02",
        message=f"旧项目 {OLD_PROJECT_ROOT}/services/x.py 新项目 {NEW_PROJECT_ROOT}/backend/y.py",
        metadata={
            **_metadata_for_check("C02"),
            "local_path": f"{OLD_PROJECT_ROOT}/services/report_self_check_service.py",
            "new_path": f"{NEW_PROJECT_ROOT}/backend/app/rules/report/c02.py",
        },
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C02", [finding]),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    dumped = bundle.evidence_package.model_dump_json() if bundle else ""
    assert OLD_PROJECT_ROOT not in dumped
    assert NEW_PROJECT_ROOT not in dumped
    assert "/Users/" not in dumped


def test_multiple_findings_have_unique_ref_ids_and_aligned_targets() -> None:
    findings = [
        _finding(check_id="C02", metadata=_metadata_for_check("C02"), id_suffix="c02"),
        _finding(check_id="C04", metadata=_metadata_for_check("C04"), id_suffix="c04"),
        _finding(check_id="C07", metadata=_metadata_for_check("C07"), id_suffix="c07"),
    ]

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C02", findings),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    item_refs = [item.ref_id for item in bundle.evidence_package.items]
    assert len(item_refs) == len(set(item_refs))
    package_target_ids = [target.target_id for target in bundle.evidence_package.targets]
    request_target_ids = [target.target_id for target in bundle.request.targets]
    assert request_target_ids == package_target_ids
    assert bundle.request.task_id == bundle.evidence_package.task_id == "task-1"
    assert bundle.request.task_type == bundle.evidence_package.task_type == TaskType.REPORT_CHECK.value
    assert bundle.request.metadata["target_count"] == 3


def test_long_text_and_large_context_are_truncated() -> None:
    long_value = "异常文本" * 100
    finding = _finding(
        check_id="C07",
        expected="符合",
        actual=long_value,
        metadata={**_metadata_for_check("C07"), "long_note": long_value},
    )
    report = _report_document(
        inspection_items=[
            InspectionItem(
                sequence_raw="1",
                sequence=1,
                item_name="特殊检验",
                standard_requirement=long_value,
                test_result=long_value,
                conclusion=long_value,
                source_page=4,
                row_index_in_page=2,
            )
        ]
    )

    bundle = ReportCodexEvidenceBuilder(max_text_chars=80).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(page_text=long_value),
    )

    assert bundle is not None
    dumped = bundle.evidence_package.model_dump_json()
    assert "[truncated]" in dumped
    assert long_value not in dumped


def test_report_codex_evidence_builder_defaults_to_five_targets_and_records_truncation_metadata() -> None:
    findings = [
        _finding(check_id="C04", metadata=_metadata_for_check("C04"), id_suffix=f"c04-{index}")
        for index in range(6)
    ]

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", findings),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    assert len(bundle.request.targets) == 5
    assert bundle.evidence_package.metadata["total_candidate_targets"] == 6
    assert bundle.evidence_package.metadata["emitted_targets"] == 5
    assert bundle.evidence_package.metadata["truncated"] is True
    assert bundle.evidence_package.metadata["omitted_targets_count"] == 1
    assert bundle.evidence_package.metadata["batch_index"] == 0
    assert bundle.evidence_package.metadata["batch_size"] == 5


def test_report_codex_evidence_builder_can_limit_batch_to_one_target() -> None:
    findings = [
        _finding(check_id="C04", metadata=_metadata_for_check("C04"), id_suffix="c04"),
        _finding(check_id="C07", metadata=_metadata_for_check("C07"), id_suffix="c07"),
    ]

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", findings),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    assert len(bundle.request.targets) == 1
    assert bundle.evidence_package.metadata["emitted_targets"] == 1


def test_report_codex_evidence_builder_can_emit_later_batch_without_omitting_targets() -> None:
    findings = [
        _finding(check_id="C04", metadata=_metadata_for_check("C04"), id_suffix=f"c04-{index}")
        for index in range(6)
    ]

    first = ReportCodexEvidenceBuilder(max_targets_per_batch=5).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", findings),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
        target_offset=0,
    )
    second = ReportCodexEvidenceBuilder(max_targets_per_batch=5).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", findings),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
        target_offset=5,
    )

    assert first is not None
    assert second is not None
    assert len(first.request.targets) == 5
    assert len(second.request.targets) == 1
    assert second.evidence_package.metadata["batch_index"] == 1
    assert second.evidence_package.metadata["omitted_targets_count"] == 0
    assert second.request.targets[0].finding_id.endswith("c04-5")


def test_report_codex_evidence_builder_included_check_ids_filter_to_c07() -> None:
    findings = [
        _finding(check_id="C04", metadata=_metadata_for_check("C04"), id_suffix="c04"),
        _finding(check_id="C07", metadata=_metadata_for_check("C07"), id_suffix="c07"),
    ]

    bundle = ReportCodexEvidenceBuilder(included_check_ids="C07").build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", findings),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    assert [target.check_id for target in bundle.request.targets] == ["C07"]


def test_report_codex_evidence_builder_sorts_by_priority_check_ids() -> None:
    findings = [
        _finding(check_id="C04", metadata=_metadata_for_check("C04"), id_suffix="c04"),
        _finding(check_id="C07", metadata=_metadata_for_check("C07"), id_suffix="c07"),
    ]

    bundle = ReportCodexEvidenceBuilder(included_check_ids="C04,C07").build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", findings),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    assert [target.check_id for target in bundle.request.targets] == ["C07", "C04"]


def test_report_codex_evidence_builder_excluded_check_ids_filter_out_rule() -> None:
    findings = [
        _finding(check_id="C04", metadata=_metadata_for_check("C04"), id_suffix="c04"),
        _finding(check_id="C07", metadata=_metadata_for_check("C07"), id_suffix="c07"),
    ]

    bundle = ReportCodexEvidenceBuilder(excluded_check_ids="C04").build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", findings),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    assert [target.check_id for target in bundle.request.targets] == ["C07"]


def test_report_codex_evidence_builder_included_finding_codes_filter_exact_codes() -> None:
    findings = [
        _finding(check_id="C04", code="SAMPLE_FIELD_MISSING_IN_LABEL", metadata=_metadata_for_check("C04"), id_suffix="c04"),
        _finding(check_id="C07", code="CONCLUSION_MISMATCH_001", metadata=_metadata_for_check("C07"), id_suffix="c07"),
    ]

    bundle = ReportCodexEvidenceBuilder(included_finding_codes="CONCLUSION_MISMATCH_001").build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", findings),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    assert [target.finding_code for target in bundle.request.targets] == ["CONCLUSION_MISMATCH_001"]


def test_report_codex_evidence_builder_zero_max_targets_returns_none() -> None:
    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=0).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [_finding(check_id="C07", metadata=_metadata_for_check("C07"))]),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is None


def _check_result(check_id: str, findings: list[Finding]) -> CheckResult:
    return CheckResult(
        task_id="task-1",
        check_id=check_id,
        check_name=check_id,
        status=CheckStatus.FAIL if findings else CheckStatus.PASS,
        findings=findings,
    )


def _finding(
    *,
    check_id: str,
    code: str | None = None,
    expected: str = "expected",
    actual: str = "actual",
    metadata: dict | None = None,
    message: str = "报告自检 finding 需要 Codex 复核。",
    id_suffix: str = "main",
) -> Finding:
    return Finding(
        id=f"task-1:{check_id}:{id_suffix}",
        task_id="task-1",
        check_id=check_id,
        severity=FindingSeverity.ERROR,
        code=code or f"{check_id}_FINDING",
        message=message,
        expected=expected,
        actual=actual,
        evidence=[
            Evidence(
                id=f"ev-{check_id}-{id_suffix}",
                source_type=SourceType.REPORT,
                location=Location(source_type=SourceType.REPORT, page_number=3, section=check_id),
                raw_text="规则证据",
                value=actual,
                method=EvidenceMethod.PDF_TEXT,
            )
        ],
        metadata=metadata or {},
    )


def _metadata_for_check(check_id: str) -> dict[str, object]:
    if check_id in {"C02", "C03"}:
        return {
            "field_name": "生产日期",
            "label_id": "label-1",
            "matched_label_key": "生产日期",
            "page_number": 3,
            "ocr_confidence": "high",
        }
    if check_id == "C04":
        return {
            "component_id": "component-1",
            "label_id": "label-1",
            "field_name": "失效日期",
            "matched_label_key": "失效日期",
        }
    if check_id == "C05":
        return {
            "component_id": "component-1",
            "caption_id": "photo-1",
            "matched_captions": ["图1 输注泵外观照片"],
            "caption_subject": "输注泵",
        }
    if check_id == "C06":
        return {
            "component_id": "component-1",
            "matched_label_key": "label-1",
            "label_caption": "图2 输注泵中文标签样张",
        }
    if check_id == "C07":
        return {
            "item_no": "1",
            "normalized_item_no": "1",
            "result_values": ["不符合要求"],
            "actual_conclusion": "符合",
            "decision_reason": "has_nonconforming_result",
        }
    return {}


def _report_document(inspection_items: list[InspectionItem] | None = None) -> ReportDocument:
    label = LabelOCRResult(
        label_id="label-1",
        page_number=5,
        caption_id="label-caption-1",
        caption_text="图2 输注泵中文标签样张",
        fields=[
            LabelOCRField(name="部件名称", value="输注泵", raw_value="输注泵", confidence=Confidence.HIGH),
            LabelOCRField(name="规格型号", value="RMC-1", raw_value="RMC-1", confidence=Confidence.HIGH),
            LabelOCRField(name="生产日期", value="2025/01/02", raw_value="2025/01/02", confidence=Confidence.HIGH),
            LabelOCRField(name="失效日期", value="2027-01-02", raw_value="2027-01-02", confidence=Confidence.HIGH),
        ],
        raw_blocks=["部件名称：输注泵", "生产日期：2025/01/02", "失效日期：2027-01-02"],
        confidence=Confidence.HIGH,
    )
    component = SampleComponent(
        component_id="component-1",
        component_name="输注泵",
        model="RMC-1",
        batch_or_serial="LOT-1",
        production_date="2025-01-02",
        expiration_date="2027-01-02",
        row_location=Location(source_type=SourceType.REPORT, page_number=3, table_id="sample-desc", row_index=1),
    )
    return ReportDocument(
        third_page=ThirdPageInfo(
            production_date=ReportField(
                name="生产日期",
                value="2025-01-02",
                raw_value="2025-01-02",
                location=Location(source_type=SourceType.REPORT, page_number=3, section="第三页"),
                confidence=Confidence.HIGH,
            ),
            fields=[
                ReportField(name="生产日期", value="2025-01-02", raw_value="2025-01-02", confidence=Confidence.HIGH)
            ],
        ),
        sample_components=[component],
        photo_captions=[
            PhotoCaption(
                caption_id="photo-1",
                text="图1 输注泵外观照片",
                subject_name="输注泵",
                caption_type="photo",
                page_number=6,
            ),
            PhotoCaption(
                caption_id="caption-label-1",
                text="图2 输注泵中文标签样张",
                subject_name="输注泵",
                caption_type="chinese_label",
                page_number=5,
            ),
        ],
        labels=[label],
        inspection_items=inspection_items
        or [
            InspectionItem(
                sequence_raw="1",
                sequence=1,
                item_name="外观",
                standard_clause="2.1",
                standard_requirement="应符合要求",
                test_result="不符合要求",
                result_values=["不符合要求"],
                conclusion="符合",
                remark="/",
                source_page=4,
                row_index_in_page=2,
            )
        ],
    )


def _parsed_pdf(page_text: str = "第三页生产日期：2025-01-02；中文标签：输注泵") -> ParsedPdf:
    return ParsedPdf(
        file_id="pdf-1",
        file_name="report.pdf",
        page_count=6,
        pages=[
            PdfPage(page_number=3, text=page_text),
            PdfPage(page_number=4, text="序号 1 检验结果 不符合要求 单项结论 符合"),
            PdfPage(page_number=5, text="图2 输注泵中文标签样张"),
            PdfPage(page_number=6, text="图1 输注泵外观照片"),
        ],
    )
