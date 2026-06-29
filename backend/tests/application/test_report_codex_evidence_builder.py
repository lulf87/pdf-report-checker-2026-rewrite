from __future__ import annotations

from pathlib import Path

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
        ("C04", CodexReviewTargetType.LABEL_OCR),
        ("C05", CodexReviewTargetType.PHOTO_CAPTION),
        ("C06", CodexReviewTargetType.LABEL_OCR),
        ("C07", CodexReviewTargetType.INSPECTION_ITEM),
        ("C09", CodexReviewTargetType.INSPECTION_ITEM),
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


@pytest.mark.parametrize("check_id", ["C01", "C08", "C10", "C11"])
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
    assert bundle.request.targets[0].metadata["summary_only"] is True
    assert bundle.evidence_package.targets[0].metadata["summary_only"] is True


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


def test_targeted_filter_does_not_build_non_included_summary_target() -> None:
    bundle = ReportCodexEvidenceBuilder(included_check_ids="C04,C05,C06,C09").build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C01", []),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is None


def test_targeted_filter_can_build_included_summary_target() -> None:
    bundle = ReportCodexEvidenceBuilder(included_check_ids="C04,C05,C06,C09").build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", []),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    assert bundle.request.targets[0].target_type is CodexReviewTargetType.CHECK_RESULT
    assert bundle.request.targets[0].check_id == "C04"


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
    assert bundle.request.targets[0].metadata["evidence_has_structured_label_fields"] is True
    assert bundle.request.targets[0].metadata["evidence_can_verify_label_content"] is True


def test_c04_target_marks_caption_only_or_empty_ocr_as_unverifiable_label_content() -> None:
    finding = _finding(check_id="C04", metadata=_metadata_for_check("C04"))
    report = _report_document().model_copy(
        update={
            "labels": [
                LabelOCRResult(
                    label_id="label-1",
                    page_number=5,
                    caption_id="label-caption-1",
                    caption_text="图2 输注泵中文标签样张",
                    fields=[],
                    raw_blocks=[],
                    confidence=Confidence.MEDIUM,
                )
            ]
        }
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    rule_context = next(item for item in bundle.evidence_package.items if item.ref_id.startswith("rule_context:"))
    assert target.metadata["evidence_has_label_image_crop"] is False
    assert target.metadata["evidence_has_full_label_text"] is False
    assert target.metadata["evidence_has_structured_label_fields"] is False
    assert target.metadata["evidence_can_verify_label_content"] is False
    assert target.metadata["evidence_incomplete"] is True
    assert target.metadata["expected_codex_when_label_content_missing"] == "uncertain"
    assert rule_context.structured["label_content_verification"]["evidence_can_verify_label_content"] is False


def test_c04_caption_only_label_evidence_has_page_reference_but_cannot_verify_content() -> None:
    component = SampleComponent(
        component_id="sample-row-3",
        component_name="心脏脉冲电场消融仪-推车",
        model="PFA-GEN-CART",
        remark="/",
        row_location=Location(source_type=SourceType.REPORT, page_number=3, table_id="sample-desc", row_index=3),
    )
    finding = _finding(
        check_id="C04",
        code="SAMPLE_FIELD_MISSING_IN_LABEL",
        metadata={"component_id": component.component_id, "field_name": "规格型号", "matched_label_key": "规格型号"},
    )
    report = _report_document().model_copy(
        update={
            "sample_components": [component],
            "photo_captions": [
                PhotoCaption(
                    caption_id="caption-cart-label",
                    text="№6 心脏脉冲电场消融仪-推车 中文标签样张",
                    subject_name="心脏脉冲电场消融仪-推车",
                    caption_type="label",
                    page_number=12,
                )
            ],
            "labels": [],
        }
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    image_item = next(item for item in bundle.evidence_package.items if item.ref_id.startswith("label_image:"))
    assert target.metadata["label_caption_candidate"]["caption_text"] == "№6 心脏脉冲电场消融仪-推车 中文标签样张"
    assert target.metadata["matched_label_caption"]["caption_text"] == "№6 心脏脉冲电场消融仪-推车 中文标签样张"
    assert target.metadata["label_page_number"] == 12
    assert target.metadata["label_page_image_ref"] == "report-page:12"
    assert target.metadata["label_image_ref"] is None
    assert target.metadata["label_crop_ref"] is None
    assert target.metadata["matched_label_ocr_source"] == "missing"
    assert target.metadata["evidence_has_matching_label_caption"] is True
    assert target.metadata["evidence_has_matched_label_image"] is True
    assert target.metadata["evidence_has_matched_label_crop"] is False
    assert target.metadata["evidence_has_matched_label_ocr"] is False
    assert target.metadata["evidence_has_matched_structured_label_fields"] is False
    assert target.metadata["evidence_can_verify_label_content"] is False
    assert image_item.structured["label_page_image_ref"] == "report-page:12"
    assert image_item.structured["crop_unavailable_reason"] == "caption_bbox_missing"


def test_c04_caption_with_source_pdf_creates_workspace_label_image_input(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake for builder metadata only\n")
    component = SampleComponent(
        component_id="sample-row-3",
        component_name="心脏脉冲电场消融仪-推车",
        model="PFA-GEN-CART",
        remark="/",
    )
    finding = _finding(
        check_id="C04",
        code="SAMPLE_FIELD_MISSING_IN_LABEL",
        metadata={"component_id": component.component_id, "field_name": "规格型号", "matched_label_key": "规格型号"},
    )
    report = _report_document().model_copy(
        update={
            "sample_components": [component],
            "photo_captions": [
                PhotoCaption(
                    caption_id="caption-cart-label",
                    text="№6 心脏脉冲电场消融仪-推车 中文标签样张",
                    subject_name="心脏脉冲电场消融仪-推车",
                    caption_type="label",
                    page_number=12,
                )
            ],
            "labels": [],
        }
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    image_item = next(item for item in bundle.evidence_package.items if item.ref_id.startswith("label_image:"))
    assert image_item.file_path == "items/task-1-C04-main-label-page.png"
    assert image_item.source_type is EvidenceSourceType.IMAGE
    assert image_item.metadata["codex_image_input"] is True
    assert image_item.metadata["render_page_number"] == 12
    assert image_item.metadata["render_source"] == "source_pdf"
    assert target.metadata["label_image_ref"] == "items/task-1-C04-main-label-page.png"
    assert target.metadata["label_page_image_ref"] == "items/task-1-C04-main-label-page.png"
    assert target.metadata["label_crop_ref"] is None
    assert target.metadata["evidence_has_visual_label_input"] is True
    assert target.metadata["evidence_can_verify_label_content"] is True
    assert str(source_pdf) == bundle.evidence_package.metadata["source_pdf_path"]


def test_c04_page_text_label_candidate_is_not_treated_as_matched_label_ocr() -> None:
    component = SampleComponent(
        component_id="sample-row-1",
        component_name="心脏脉冲电场消融仪-主机",
        model="PFA-GEN",
        batch_or_serial="10627716",
        production_date="2024-11-26",
        remark="/",
    )
    finding = _finding(
        check_id="C04",
        code="SAMPLE_FIELD_MISSING_IN_LABEL",
        metadata={"component_id": component.component_id, "field_name": "规格型号", "matched_label_key": "规格型号"},
    )
    page_text_label = LabelOCRResult(
        label_id="label-page-5",
        page_number=21,
        caption_id="caption-main-label",
        caption_text="№5 心脏脉冲电场消融仪-主机 中文标签样张",
        fields=[],
        raw_blocks=[
            "检验报告照片页",
            "照片和说明",
            "№5 心脏脉冲电场消融仪-主机 中文标签样张",
            "№6 心脏脉冲电场消融仪-推车 中文标签样张",
        ],
        confidence=Confidence.MEDIUM,
        metadata={"candidate_source": "pdf_text_label_page"},
    )
    report = _report_document().model_copy(
        update={
            "sample_components": [component],
            "photo_captions": [
                PhotoCaption(
                    caption_id="caption-main-label",
                    text="№5 心脏脉冲电场消融仪-主机 中文标签样张",
                    subject_name="心脏脉冲电场消融仪-主机",
                    caption_type="label",
                    page_number=21,
                )
            ],
            "labels": [page_text_label],
        }
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    label_item = next(item for item in bundle.evidence_package.items if item.ref_id.startswith("label_ocr:"))
    assert target.metadata["matched_label_page_text"] == "\n".join(page_text_label.raw_blocks)
    assert target.metadata["matched_label_caption_text"] == "№5 心脏脉冲电场消融仪-主机 中文标签样张"
    assert target.metadata["matched_label_ocr_text"] is None
    assert target.metadata["matched_label_fields"] == {}
    assert target.metadata["label_crop_ref"] is None
    assert target.metadata["evidence_has_matched_label_ocr"] is False
    assert target.metadata["evidence_has_matched_structured_label_fields"] is False
    assert target.metadata["evidence_can_verify_label_content"] is False
    assert label_item.structured["matched_label_page_text"] == target.metadata["matched_label_page_text"]
    assert label_item.structured["matched_label_ocr_text"] is None


def test_c04_label_caption_bbox_generates_crop_reference_without_ocr() -> None:
    component = SampleComponent(component_id="component-cart", component_name="推车", remark="/")
    finding = _finding(
        check_id="C04",
        code="SAMPLE_FIELD_MISSING_IN_LABEL",
        metadata={"component_id": component.component_id, "field_name": "部件名称", "matched_label_key": "部件名称"},
    )
    report = _report_document().model_copy(
        update={
            "sample_components": [component],
            "photo_captions": [
                PhotoCaption(
                    caption_id="caption-cart-label",
                    text="推车 中文标签样张",
                    subject_name="推车",
                    caption_type="label",
                    page_number=12,
                    bbox=(10.0, 20.0, 110.0, 160.0),
                )
            ],
            "labels": [],
        }
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    image_item = next(item for item in bundle.evidence_package.items if item.ref_id.startswith("label_image:"))
    assert target.metadata["label_crop_ref"] == "report-page:12#caption=caption-cart-label&bbox=10,20,110,160"
    assert target.metadata["evidence_has_matched_label_crop"] is True
    assert target.metadata["evidence_has_matched_label_ocr"] is False
    assert target.metadata["evidence_can_verify_label_content"] is False
    assert image_item.structured["label_crop_ref"] == target.metadata["label_crop_ref"]


def test_c04_label_crop_ocr_and_structured_fields_are_included_for_matched_component() -> None:
    finding = _finding(
        check_id="C04",
        code="SAMPLE_FIELD_MISSING_IN_LABEL",
        metadata={
            "component_id": "component-1",
            "label_id": "label-1",
            "field_name": "失效日期",
            "matched_label_key": "失效日期",
        },
    )
    label = LabelOCRResult(
        label_id="label-1",
        page_number=5,
        caption_id="caption-label-1",
        caption_text="图2 输注泵中文标签样张",
        fields=[
            LabelOCRField(name="部件名称", value="输注泵", raw_value="输注泵", confidence=Confidence.HIGH),
            LabelOCRField(name="失效日期", value="2027-01-02", raw_value="2027-01-02", confidence=Confidence.HIGH),
        ],
        raw_blocks=["部件名称：输注泵", "失效日期：2027-01-02"],
        confidence=Confidence.HIGH,
        image_ref="assets/labels/label-1.png",
    )
    report = _report_document().model_copy(update={"labels": [label]})

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    label_item = items_by_ref[f"label_ocr:{finding.id}"]
    image_item = items_by_ref[f"label_image:{finding.id}"]
    assert f"label_image:{finding.id}" in {ref.ref_id for ref in target.evidence_refs}
    assert image_item.file_path == "assets/labels/label-1.png"
    assert image_item.structured["image_ref"] == "assets/labels/label-1.png"
    assert target.metadata["evidence_has_label_image_crop"] is True
    assert target.metadata["evidence_has_matched_label_image"] is True
    assert target.metadata["evidence_has_matched_label_crop"] is True
    assert target.metadata["evidence_can_verify_label_content"] is True
    assert target.metadata["matched_label_ocr_source"] == "explicit_label_id"
    assert target.metadata["matched_label_field_confidence"] == "high"
    assert target.metadata["label_page_number"] == 5
    assert target.metadata["label_image_ref"] == "assets/labels/label-1.png"
    assert target.metadata["label_crop_ref"] == "assets/labels/label-1.png"
    assert target.metadata["matched_label_page_text"] is None
    assert target.metadata["matched_label_ocr_text"] == "部件名称：输注泵\n失效日期：2027-01-02"
    assert target.metadata["matched_label_fields"]["失效日期"]["value"] == "2027-01-02"
    assert target.metadata["label_field_comparison"]["sample_value"] == "2027-01-02"
    assert target.metadata["label_field_comparison"]["matched_label_value"] == "2027-01-02"
    assert target.metadata["label_field_comparison"]["comparison_hint"] == "field_matches_sample_description"
    assert label_item.structured["matched_label_text"] == "部件名称：输注泵\n失效日期：2027-01-02"
    assert label_item.structured["matched_label_ocr_text"] == "部件名称：输注泵\n失效日期：2027-01-02"
    assert label_item.structured["matched_label_fields"]["失效日期"]["value"] == "2027-01-02"


def test_c04_label_crop_ocr_field_mismatch_is_explicit_in_evidence() -> None:
    finding = _finding(
        check_id="C04",
        code="SAMPLE_FIELD_MISMATCH",
        metadata={
            "component_id": "component-1",
            "label_id": "label-1",
            "field_name": "失效日期",
            "matched_label_key": "失效日期",
        },
    )
    label = LabelOCRResult(
        label_id="label-1",
        page_number=5,
        caption_id="caption-label-1",
        caption_text="图2 输注泵中文标签样张",
        fields=[
            LabelOCRField(name="部件名称", value="输注泵", raw_value="输注泵", confidence=Confidence.HIGH),
            LabelOCRField(name="失效日期", value="2028-01-02", raw_value="2028-01-02", confidence=Confidence.HIGH),
        ],
        raw_blocks=["部件名称：输注泵", "失效日期：2028-01-02"],
        confidence=Confidence.HIGH,
        image_ref="assets/labels/label-1.png",
    )
    report = _report_document().model_copy(update={"labels": [label]})

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    assert target.metadata["label_field_comparison"]["sample_value"] == "2027-01-02"
    assert target.metadata["label_field_comparison"]["matched_label_value"] == "2028-01-02"
    assert target.metadata["label_field_comparison"]["comparison_hint"] == "field_mismatch"


@pytest.mark.parametrize(
    ("component", "caption_text", "expected_subject"),
    [
        (
            SampleComponent(
                component_id="sample-row-3",
                component_name="心脏脉冲电场消融仪-推车",
                model="PFA-GEN-CART",
                batch_or_serial="10627717",
                production_date="2024-11-26",
                remark="/",
                row_location=Location(source_type=SourceType.REPORT, page_number=3, table_id="sample-desc", row_index=3),
            ),
            "№6 心脏脉冲电场消融仪-推车 中文标签样张",
            "心脏脉冲电场消融仪-推车",
        ),
        (
            SampleComponent(
                component_id="sample-row-14",
                component_name="心脏脉冲电场消融仪-触摸屏连接线缆（30m）（可选）",
                model="PFA-GEN-CBL30",
                remark="/",
                row_location=Location(source_type=SourceType.REPORT, page_number=3, table_id="sample-desc", row_index=14),
            ),
            "№22 触摸屏连接线缆（30m）（可选） 中文标签样张",
            "触摸屏连接线缆（30m）（可选）",
        ),
    ],
)
def test_c04_missing_label_target_treats_matching_caption_as_label_sample_evidence(
    component: SampleComponent,
    caption_text: str,
    expected_subject: str,
) -> None:
    finding = _finding(
        check_id="C04",
        code="SAMPLE_COMPONENT_LABEL_NOT_FOUND",
        metadata={"component_id": component.component_id, "component_key": component.identity_key},
        id_suffix=component.component_id,
    )
    report = _report_document().model_copy(
        update={
            "sample_components": [component],
            "photo_captions": [
                PhotoCaption(
                    caption_id=f"{component.component_id}-caption",
                    text=caption_text,
                    subject_name=expected_subject,
                    caption_type="label",
                    page_number=12,
                )
            ],
            "labels": [],
        }
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(page_text=caption_text),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    rule_context = next(item for item in bundle.evidence_package.items if item.ref_id.startswith("rule_context:"))
    caption_item = next(item for item in bundle.evidence_package.items if item.ref_id.startswith("label_caption:"))
    assert target.metadata["evidence_has_matching_label_caption"] is True
    assert target.metadata["evidence_has_matched_label_ocr"] is False
    assert target.metadata["evidence_can_verify_label_content"] is False
    assert target.metadata["matched_label_id"] is None
    assert target.metadata["matching_label_caption_candidates"][0]["caption_text"] == caption_text
    assert rule_context.structured["label_content_verification"]["evidence_has_matching_label_caption"] is True
    assert rule_context.structured["label_content_verification"]["evidence_has_matched_label_ocr"] is False
    assert caption_item.structured["matching_label_caption_candidates"][0]["caption_text"] == caption_text


@pytest.mark.parametrize(
    ("component_name", "caption_text"),
    [
        ("心脏脉冲电场消融仪-主机", "主机 中文标签样张"),
        ("心脏脉冲电场消融仪-推车", "推车 中文标签样张"),
        ("心脏脉冲电场消融仪-触摸屏", "触摸屏 中文标签样张"),
        ("ECG 主线缆", "ECG 主线缆 中文标签样张"),
        ("不可透射线 ECG 导联线", "不可透射线 ECG 导联线 中文标签样张"),
        ("光接收器", "光接收器 中文标签样张"),
        ("电源电缆", "电源电缆 中文标签样张"),
        ("等电位线缆", "等电位线缆 中文标签样张"),
        ("心脏脉冲电场消融仪-触摸屏连接线缆（30m）（可选）", "触摸屏连接线缆（30m）（可选） 中文标签样张"),
        ("脉冲导管连接电缆", "脉冲导管连接电缆 中文标签样张"),
    ],
)
def test_c04_label_caption_matching_covers_real_sample_component_names(
    component_name: str,
    caption_text: str,
) -> None:
    component = SampleComponent(component_id="component-real", component_name=component_name, remark="/")
    finding = _finding(
        check_id="C04",
        code="SAMPLE_COMPONENT_LABEL_NOT_FOUND",
        metadata={"component_id": component.component_id},
    )
    report = _report_document().model_copy(
        update={
            "sample_components": [component],
            "photo_captions": [
                PhotoCaption(
                    caption_id="caption-real-label",
                    text=caption_text,
                    subject_name=caption_text.replace("中文标签样张", "").strip(),
                    caption_type="label",
                    page_number=20,
                )
            ],
            "labels": [],
        }
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    assert target.metadata["evidence_has_matching_label_caption"] is True
    assert target.metadata["matching_label_caption_candidates"][0]["caption_text"] == caption_text


def test_c04_label_caption_selector_prefers_30m_cable_over_touchscreen_short_match() -> None:
    component = SampleComponent(
        component_id="sample-row-14",
        component_name="心脏脉冲电场消融仪-触摸屏连接线缆（30m）（可选）",
        model="PFA-GEN-CBL30",
        remark="/",
    )
    finding = _finding(
        check_id="C04",
        code="SAMPLE_COMPONENT_LABEL_NOT_FOUND",
        metadata={"component_id": component.component_id},
    )
    report = _report_document().model_copy(
        update={
            "sample_components": [component],
            "photo_captions": [
                PhotoCaption(
                    caption_id="caption-touchscreen",
                    text="№8 心脏脉冲电场消融仪-触摸屏 中文标签样张",
                    subject_name="心脏脉冲电场消融仪-触摸屏",
                    caption_type="label",
                    page_number=18,
                ),
                PhotoCaption(
                    caption_id="caption-touchscreen-cable-30m",
                    text="№22 触摸屏连接线缆（30m）（可选） 中文标签样张",
                    subject_name="触摸屏连接线缆（30m）（可选）",
                    caption_type="label",
                    page_number=24,
                ),
            ],
            "labels": [],
        }
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    assert target.metadata["matched_label_caption"]["caption_id"] == "caption-touchscreen-cable-30m"
    assert target.metadata["matched_label_caption"]["caption_text"] == "№22 触摸屏连接线缆（30m）（可选） 中文标签样张"
    assert target.metadata["label_page_number"] == 24
    assert [candidate["caption_id"] for candidate in target.metadata["matching_label_caption_candidates"]][:2] == [
        "caption-touchscreen-cable-30m",
        "caption-touchscreen",
    ]


def test_c04_label_caption_selector_keeps_ambiguous_candidates_unmatched() -> None:
    component = SampleComponent(
        component_id="component-cart",
        component_name="推车",
        remark="/",
    )
    finding = _finding(
        check_id="C04",
        code="SAMPLE_COMPONENT_LABEL_NOT_FOUND",
        metadata={"component_id": component.component_id},
    )
    report = _report_document().model_copy(
        update={
            "sample_components": [component],
            "photo_captions": [
                PhotoCaption(
                    caption_id="caption-cart-a",
                    text="№6 推车 中文标签样张",
                    subject_name="推车",
                    caption_type="label",
                    page_number=12,
                ),
                PhotoCaption(
                    caption_id="caption-cart-b",
                    text="№7 推车 中文标签样张",
                    subject_name="推车",
                    caption_type="label",
                    page_number=13,
                ),
            ],
            "labels": [],
        }
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    assert target.metadata["label_caption_candidate"] is None
    assert target.metadata["matched_label_caption"] is None
    assert target.metadata["matching_label_caption_candidates"][0]["caption_id"] == "caption-cart-a"
    assert target.metadata["matching_label_caption_candidates"][1]["caption_id"] == "caption-cart-b"
    assert any(
        diagnostic["code"] == "LABEL_CAPTION_MATCH_AMBIGUOUS"
        for diagnostic in target.metadata["label_matching_diagnostics"]
    )


def test_c04_missing_label_target_does_not_treat_unrelated_label_ocr_as_matched_content() -> None:
    component = SampleComponent(
        component_id="sample-row-3",
        component_name="心脏脉冲电场消融仪-推车",
        model="PFA-GEN-CART",
        remark="/",
        row_location=Location(source_type=SourceType.REPORT, page_number=3, table_id="sample-desc", row_index=3),
    )
    unrelated_label = LabelOCRResult(
        label_id="label-unrelated",
        page_number=8,
        caption_id="caption-unrelated",
        caption_text="№9 心脏脉冲电场消融仪-主机 中文标签样张",
        fields=[
            LabelOCRField(name="部件名称", value="心脏脉冲电场消融仪-主机", raw_value="心脏脉冲电场消融仪-主机"),
            LabelOCRField(name="规格型号", value="PFA-GEN", raw_value="PFA-GEN"),
        ],
        raw_blocks=["部件名称：心脏脉冲电场消融仪-主机", "规格型号：PFA-GEN"],
        confidence=Confidence.HIGH,
    )
    finding = _finding(
        check_id="C04",
        code="SAMPLE_COMPONENT_LABEL_NOT_FOUND",
        metadata={"component_id": "sample-row-3"},
    )
    report = _report_document().model_copy(
        update={
            "sample_components": [component],
            "photo_captions": [],
            "labels": [unrelated_label],
        }
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    assert target.metadata["matching_label_ocr_candidates"] == []
    assert target.metadata["unmatched_label_ocr_candidates"][0]["label_id"] == "label-unrelated"
    assert target.metadata["unmatched_label_ocr_candidates"][0]["caption_text"] == "№9 心脏脉冲电场消融仪-主机 中文标签样张"
    assert target.metadata["evidence_has_matched_label_ocr"] is False
    assert target.metadata["evidence_has_matched_full_label_text"] is False
    assert target.metadata["evidence_has_matched_structured_label_fields"] is False
    assert target.metadata["evidence_can_verify_label_content"] is False
    assert not any(item.ref_id.startswith("label_ocr:") for item in bundle.evidence_package.items)


def test_c04_field_finding_with_matched_label_ocr_can_verify_label_content() -> None:
    finding = _finding(
        check_id="C04",
        code="SAMPLE_FIELD_MISSING_IN_LABEL",
        metadata={
            "component_id": "component-1",
            "label_id": "label-1",
            "field_name": "失效日期",
            "matched_label_key": "失效日期",
        },
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C04", [finding]),
        report=_report_document(),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    assert target.metadata["matched_label_id"] == "label-1"
    assert target.metadata["evidence_has_matched_label_ocr"] is True
    assert target.metadata["evidence_has_matched_full_label_text"] is True
    assert target.metadata["evidence_has_matched_structured_label_fields"] is True
    assert target.metadata["evidence_can_verify_label_content"] is True


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


def test_c06_target_marks_label_caption_without_label_content_as_unverifiable() -> None:
    finding = _finding(check_id="C06", metadata=_metadata_for_check("C06"))
    report = _report_document().model_copy(update={"labels": []})

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C06", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    assert target.metadata["evidence_has_label_image_crop"] is False
    assert target.metadata["evidence_has_full_label_text"] is False
    assert target.metadata["evidence_has_structured_label_fields"] is False
    assert target.metadata["evidence_can_verify_label_content"] is False


def test_unused_component_metadata_normalizes_whitespace_in_remark() -> None:
    finding = _finding(
        check_id="C06",
        metadata={**_metadata_for_check("C06"), "component_id": "component-unused"},
    )
    report = _report_document().model_copy(
        update={
            "sample_components": [
                SampleComponent(
                    component_id="component-unused",
                    component_name="触摸屏连接线缆 10m",
                    remark="本次检测未\n 使用",
                    row_location=Location(source_type=SourceType.REPORT, page_number=3, table_id="sample-desc", row_index=6),
                )
            ]
        }
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C06", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    component_item = next(item for item in bundle.evidence_package.items if item.ref_id.startswith("component:"))
    assert target.metadata["is_unused_component"] is True
    assert target.metadata["unused_reason"] == "本次检测未\n 使用"
    assert component_item.structured["is_unused_component"] is True


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
    assert inspection_item.structured["inspection_item_group"]["compact_rows"][0]["row_index"] == 2
    assert inspection_item.structured["inspection_item_group"]["actual_conclusion_candidates"][0]["value"] == "符合"
    assert inspection_item.structured["inspection_item_group"]["conclusion_candidate_provenance"][0]["page_number"] == 4
    assert "第三页生产日期" not in inspection_item.model_dump_json()


def test_c07_evidence_includes_homepage_symbol_note_and_group_page_text() -> None:
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_MISMATCH_002",
        expected="符合",
        actual="/",
        metadata={**_metadata_for_check("C07"), "item_no": "142", "normalized_item_no": "142"},
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=_report_document(
            inspection_items=[
                InspectionItem(
                    sequence_raw="142",
                    sequence=142,
                    item_name="报警功能",
                    standard_requirement="应符合要求",
                    test_result="",
                    result_values=[],
                    conclusion="/",
                    remark="/",
                    source_page=42,
                    row_index_in_page=1,
                    field_provenance={"test_result": "extracted_from_matrix_cell"},
                )
            ]
        ),
        parsed_pdf=_parsed_pdf(
            home_page_text="首页说明：“——”表示此项不适用；“/”表示此项空白。",
            extra_pages=[PdfPage(page_number=42, text="序号 142 报警功能 检验结果 符合要求 单项结论 /")],
        ),
    )

    assert bundle is not None
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    assert f"symbol_note:{finding.id}" in items_by_ref
    assert f"inspection_page_text:{finding.id}" in items_by_ref
    symbol_note = items_by_ref[f"symbol_note:{finding.id}"]
    page_text = items_by_ref[f"inspection_page_text:{finding.id}"]
    assert "——" in symbol_note.text
    assert "/" in symbol_note.text
    assert "符合要求" in page_text.text
    assert page_text.structured["pages"][0]["page_number"] == 42


def test_c07_complex_matrix_target_is_marked_as_complex_table_evidence() -> None:
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_MISMATCH_002",
        expected="符合",
        actual="/",
        metadata={
            **_metadata_for_check("C07"),
            "item_no": "59",
            "normalized_item_no": "59",
            "complex_matrix_table": True,
            "complex_matrix_reason": "矩阵表列映射需要人工复核",
        },
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=_report_document(
            inspection_items=[
                InspectionItem(
                    sequence_raw="59",
                    sequence=59,
                    item_name="复杂矩阵",
                    standard_requirement="矩阵列应符合要求",
                    test_result="",
                    conclusion="/",
                    source_page=20,
                    row_index_in_page=3,
                    metadata={"complex_matrix_table": True},
                )
            ]
        ),
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=20, text="序号 59 复杂矩阵表")]),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    inspection_item = next(item for item in bundle.evidence_package.items if item.ref_id.startswith("inspection_item:"))
    assert target.metadata["complex_matrix_table"] is True
    assert target.metadata["expected_codex_when_complex_matrix"] == "uncertain"
    assert inspection_item.structured["inspection_item_group"]["complex_matrix_table"] is True


def test_c07_visual_evidence_generates_page_table_group_and_column_images(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
        metadata={**_metadata_for_check("C07"), "item_no": "33", "normalized_item_no": "33"},
        id_suffix="c07",
    )
    report = _report_document(
        inspection_items=[
            InspectionItem(
                sequence_raw="33",
                sequence=33,
                item_name="分类标记",
                test_result="——",
                conclusion="符合",
                remark="/",
                source_page=22,
                row_index_in_page=10,
                metadata={
                    "visual_geometry": {
                        "table_id": "p22-t1",
                        "table_bbox": [10, 20, 210, 120],
                        "row_bbox": [10, 50, 210, 80],
                        "field_bboxes": {
                            "test_result": [110, 50, 150, 80],
                            "conclusion": [150, 50, 185, 80],
                            "remark": [185, 50, 210, 80],
                        },
                    }
                },
            )
        ]
    )

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=22, text="序号 33 分类标记")]),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    visual = target.metadata["c07_visual_evidence"]
    assert visual["has_visual_input"] is True
    assert visual["visual_review_mode"] == "inspection_item_group"
    assert visual["page_image_refs"] == ["items/task-1-C07-c07-c07-page-p22.png"]
    assert visual["table_image_refs"] == ["items/task-1-C07-c07-c07-table-p22.png"]
    assert visual["item_group_crop_refs"] == ["items/task-1-C07-c07-c07-item-group-p22.png"]
    assert visual["result_column_crop_refs"] == ["items/task-1-C07-c07-c07-result-p22.png"]
    assert visual["conclusion_column_crop_refs"] == ["items/task-1-C07-c07-c07-conclusion-p22.png"]
    assert visual["remark_column_crop_refs"] == ["items/task-1-C07-c07-c07-remark-p22.png"]
    assert visual["missing_visual_evidence_reasons"] == []
    assert target.metadata["evidence_has_c07_visual_input"] is True

    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    assert f"c07_visual_page:{finding.id}:p22" in items_by_ref
    assert f"c07_visual_table:{finding.id}:p22" in items_by_ref
    assert f"c07_visual_item_group:{finding.id}:p22" in items_by_ref
    assert f"c07_visual_result:{finding.id}:p22" in items_by_ref
    assert f"c07_visual_conclusion:{finding.id}:p22" in items_by_ref
    assert f"c07_visual_remark:{finding.id}:p22" in items_by_ref
    assert items_by_ref[f"c07_visual_page:{finding.id}:p22"].metadata["codex_image_input"] is True
    assert items_by_ref[f"c07_visual_table:{finding.id}:p22"].metadata["render_bbox"] == [6.0, 17.0, 214.0, 123.0]
    assert items_by_ref[f"c07_visual_table:{finding.id}:p22"].metadata["crop_bbox"] == [6.0, 17.0, 214.0, 123.0]
    assert items_by_ref[f"c07_visual_item_group:{finding.id}:p22"].metadata["render_bbox"] == [6.0, 47.0, 214.0, 83.0]
    assert items_by_ref[f"c07_visual_result:{finding.id}:p22"].metadata["render_bbox"] == [106.0, 47.0, 154.0, 83.0]
    assert all(
        ref_id in {ref.ref_id for ref in target.evidence_refs}
        for ref_id in [
            f"c07_visual_page:{finding.id}:p22",
            f"c07_visual_table:{finding.id}:p22",
            f"c07_visual_item_group:{finding.id}:p22",
            f"c07_visual_result:{finding.id}:p22",
            f"c07_visual_conclusion:{finding.id}:p22",
            f"c07_visual_remark:{finding.id}:p22",
        ]
    )
    dumped = bundle.evidence_package.model_dump_json()
    assert OLD_PROJECT_ROOT not in dumped
    assert all(not item.file_path.startswith("/") for item in bundle.evidence_package.items if item.file_path)


def test_c07_visual_evidence_item_group_crop_uses_continuation_field_bbox_union(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
        metadata={**_metadata_for_check("C07"), "item_no": "33", "normalized_item_no": "33"},
        id_suffix="c07",
    )
    report = _report_document(
        inspection_items=[
            InspectionItem(
                sequence_raw="33",
                sequence=33,
                item_name="分类标记",
                test_result="——",
                conclusion="符合",
                remark="/",
                source_page=22,
                row_index_in_page=10,
                metadata={
                    "visual_geometry": {
                        "table_id": "p22-t1",
                        "table_bbox": [10, 20, 210, 140],
                        "row_bbox": [10, 50, 210, 80],
                        "field_bboxes": {
                            "test_result": [110, 50, 150, 80],
                            "conclusion": [150, 50, 185, 80],
                            "remark": [185, 50, 210, 80],
                        },
                    }
                },
            ),
            InspectionItem(
                sequence_raw="分类是 IPX0 或 IP0X 的 ME 设备不需要标记。",
                standard_requirement="分类是 IPX0 或 IP0X 的 ME 设备不需要标记。",
                test_result="符合要求",
                source_page=22,
                row_index_in_page=11,
                metadata={
                    "visual_geometry": {
                        "table_id": "p22-t1",
                        "table_bbox": [10, 20, 210, 140],
                        "field_bboxes": {
                            "test_result": [110, 80, 150, 110],
                            "conclusion": [150, 80, 185, 110],
                            "remark": [185, 80, 210, 110],
                        },
                    }
                },
            ),
        ]
    )

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=22, text="序号 33 分类标记 符合要求")]),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    item_group = items_by_ref[f"c07_visual_item_group:{finding.id}:p22"]
    result_column = items_by_ref[f"c07_visual_result:{finding.id}:p22"]
    assert item_group.metadata["render_bbox"] == [6.0, 47.0, 214.0, 113.0]
    assert result_column.metadata["render_bbox"] == [106.0, 47.0, 154.0, 113.0]


def test_c07_visual_evidence_targeted_and_full_modes_keep_same_image_refs(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
        metadata={**_metadata_for_check("C07"), "item_no": "33", "normalized_item_no": "33"},
        id_suffix="c07",
    )
    report = _report_document(
        inspection_items=[
            InspectionItem(
                sequence_raw="33",
                sequence=33,
                test_result="——",
                conclusion="符合",
                remark="/",
                source_page=22,
                row_index_in_page=10,
                metadata={
                    "visual_geometry": {
                        "table_bbox": [10, 20, 210, 140],
                        "row_bbox": [10, 50, 210, 80],
                        "field_bboxes": {
                            "test_result": [110, 50, 150, 80],
                            "conclusion": [150, 50, 185, 80],
                            "remark": [185, 50, 210, 80],
                        },
                    }
                },
            )
        ]
    )
    result = _check_result("C07", [finding])

    targeted_bundle = ReportCodexEvidenceBuilder(included_check_ids="C07", max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=result,
        report=report,
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=22, text="序号 33 分类标记")]),
        source_pdf_path=source_pdf,
    )
    full_bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=result,
        report=report,
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=22, text="序号 33 分类标记")]),
        source_pdf_path=source_pdf,
    )

    assert targeted_bundle is not None
    assert full_bundle is not None
    targeted_target = targeted_bundle.request.targets[0]
    full_target = full_bundle.request.targets[0]
    targeted_visual = targeted_target.metadata["c07_visual_evidence"]
    full_visual = full_target.metadata["c07_visual_evidence"]
    assert targeted_visual == full_visual
    assert [ref.ref_id for ref in targeted_target.evidence_refs if ref.ref_id.startswith("c07_visual_")] == [
        ref.ref_id for ref in full_target.evidence_refs if ref.ref_id.startswith("c07_visual_")
    ]


def test_c07_visual_evidence_without_bbox_uses_page_image_only(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
        metadata={**_metadata_for_check("C07"), "item_no": "94", "normalized_item_no": "94"},
        id_suffix="c07",
    )
    report = _report_document(
        inspection_items=[
            InspectionItem(
                sequence_raw="94",
                sequence=94,
                test_result="——",
                conclusion="符合",
                remark="/",
                source_page=72,
                row_index_in_page=10,
            )
        ]
    )

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=72, text="序号 94 电源输入")]),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    visual = bundle.request.targets[0].metadata["c07_visual_evidence"]
    assert visual["has_visual_input"] is True
    assert visual["visual_review_mode"] == "page_only"
    assert visual["page_image_refs"] == ["items/task-1-C07-c07-c07-page-p72.png"]
    assert visual["table_image_refs"] == []
    assert visual["item_group_crop_refs"] == []
    assert visual["result_column_crop_refs"] == []
    assert visual["conclusion_column_crop_refs"] == []
    assert visual["remark_column_crop_refs"] == []
    assert "table_bbox_missing" in visual["missing_visual_evidence_reasons"]
    assert "row_bbox_missing" in visual["missing_visual_evidence_reasons"]
    assert "field_bbox_missing" in visual["missing_visual_evidence_reasons"]


def test_c07_visual_evidence_without_source_pdf_records_missing_reason() -> None:
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
        metadata={**_metadata_for_check("C07"), "item_no": "94", "normalized_item_no": "94"},
        id_suffix="c07",
    )
    report = _report_document(
        inspection_items=[
            InspectionItem(
                sequence_raw="94",
                sequence=94,
                test_result="——",
                conclusion="符合",
                remark="/",
                source_page=72,
                row_index_in_page=10,
            )
        ]
    )

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=72, text="序号 94 电源输入")]),
        source_pdf_path=None,
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    visual = target.metadata["c07_visual_evidence"]
    assert visual["has_visual_input"] is False
    assert visual["page_image_refs"] == []
    assert visual["missing_visual_evidence_reasons"] == ["source_pdf_path_missing"]
    assert target.metadata["evidence_has_c07_visual_input"] is False
    assert not any(item.source_type is EvidenceSourceType.IMAGE for item in bundle.evidence_package.items)


def test_c07_visual_evidence_complex_matrix_uses_complex_mode(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX",
        metadata={**_metadata_for_check("C07"), "item_no": "59", "normalized_item_no": "59"},
        id_suffix="c07",
    )
    report = _report_document(
        inspection_items=[
            InspectionItem(
                sequence_raw="59",
                sequence=59,
                item_name="复杂矩阵",
                test_result="符合要求",
                conclusion="/",
                remark="/",
                source_page=42,
                row_index_in_page=3,
                metadata={
                    "visual_geometry": {
                        "table_id": "p42-t1",
                        "table_bbox": [10, 20, 250, 160],
                        "row_bbox": [10, 80, 250, 120],
                        "field_bboxes": {
                            "test_result": [150, 80, 190, 120],
                            "conclusion": [190, 80, 220, 120],
                            "remark": [220, 80, 250, 120],
                        },
                    }
                },
            )
        ]
    )

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=42, text="序号 59 复杂矩阵表")]),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    visual = target.metadata["c07_visual_evidence"]
    assert visual["has_visual_input"] is True
    assert visual["visual_review_mode"] == "complex_matrix_table"
    assert visual["expected_codex_when_complex_matrix"] == "uncertain_or_specialized_matrix_review"
    assert visual["table_image_refs"] == ["items/task-1-C07-c07-c07-table-p42.png"]
    assert target.metadata["complex_matrix_table"] is True
    assert target.metadata["expected_codex_when_complex_matrix"] == "uncertain"


def test_c07_visual_evidence_refs_are_workspace_relative_and_do_not_leak_user_paths() -> None:
    source_pdf = Path("/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf")
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
        metadata={**_metadata_for_check("C07"), "item_no": "33", "normalized_item_no": "33"},
        id_suffix="c07",
    )
    report = _report_document(
        inspection_items=[
            InspectionItem(
                sequence_raw="33",
                sequence=33,
                test_result="——",
                conclusion="符合",
                remark="/",
                source_page=22,
                row_index_in_page=10,
                metadata={
                    "visual_geometry": {
                        "table_bbox": [10, 20, 210, 120],
                        "row_bbox": [10, 50, 210, 80],
                        "field_bboxes": {
                            "test_result": [110, 50, 150, 80],
                            "conclusion": [150, 50, 185, 80],
                            "remark": [185, 50, 210, 80],
                        },
                    }
                },
            )
        ]
    )

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=report,
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=22, text="序号 33 分类标记")]),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    target_dump = bundle.request.targets[0].model_dump_json()
    package_target_dump = bundle.evidence_package.targets[0].model_dump_json()
    allowed_refs = [ref.ref_id for ref in bundle.request.targets[0].evidence_refs]
    assert "/Users/" not in target_dump
    assert "/Users/" not in package_target_dump
    assert not any(ref.startswith("/") for ref in allowed_refs)
    assert all(not item.file_path.startswith("/") for item in bundle.evidence_package.items if item.file_path)


def test_c07_complex_matrix_target_is_detected_from_group_shape_without_finding_metadata() -> None:
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_MISMATCH_002",
        expected="符合",
        actual="/",
        metadata={**_metadata_for_check("C07"), "item_no": "59", "normalized_item_no": "59"},
    )
    matrix_rows = [
        InspectionItem(
            sequence_raw="59",
            sequence=59,
            item_name="漏电流",
            standard_requirement="漏电流矩阵表",
            test_result="符合要求",
            conclusion="/",
            source_page=42,
            row_index_in_page=0,
        )
    ]
    for index, text in enumerate(
        [
            "正常状态下≤0.05mA ＜0.01",
            "单一故障状态≤0.5mA ＜0.02",
            "直流漏电流 符合",
            "交流漏电流 符合",
            "患者辅助电流 正常状态下≤0.05mA",
            "外壳漏电流 单一故障状态≤0.5mA",
            "接地漏电流 ＜0.01mA",
            "mA 测量值 ＜0.01",
            "μA 测量值 ＜10",
            "电流限值 符合",
            "漏电流复核 符合",
        ],
        start=1,
    ):
        matrix_rows.append(
            InspectionItem(
                sequence_raw="",
                item_name="漏电流矩阵",
                standard_requirement=text,
                test_result=text,
                conclusion="",
                source_page=42 + min(3, index // 3),
                row_index_in_page=index,
                metadata={"row_text": text},
            )
        )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=_report_document(inspection_items=matrix_rows),
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=42, text="序号 59 漏电流矩阵表")]),
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    inspection_item = next(item for item in bundle.evidence_package.items if item.ref_id.startswith("inspection_item:"))
    assert target.metadata["complex_matrix_table"] is True
    assert "矩阵" in target.metadata["complex_matrix_reason"]
    assert inspection_item.structured["inspection_item_group"]["complex_matrix_table"] is True


def test_c07_complex_matrix_evidence_generates_matrix_image_refs(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _complex_matrix_finding()
    rows = _complex_matrix_rows_with_visual_geometry(pages=[42, 43, 44, 45])

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=_report_document(inspection_items=rows),
        parsed_pdf=_parsed_pdf(
            extra_pages=[PdfPage(page_number=page, text=f"序号 59 复杂矩阵 p{page}") for page in [42, 43, 44, 45]]
        ),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    matrix = target.metadata["c07_complex_matrix_evidence"]
    assert matrix["has_complex_matrix_input"] is True
    assert matrix["review_mode"] == "complex_matrix_specialized"
    assert matrix["item_no"] == "59"
    assert matrix["pages"] == [42, 43, 44, 45]
    assert matrix["matrix_table_image_refs"]
    assert matrix["matrix_header_image_refs"]
    assert matrix["matrix_body_image_refs"]
    assert matrix["result_matrix_image_refs"]
    assert matrix["conclusion_column_image_refs"]
    assert matrix["continuation_page_image_refs"]
    assert matrix["missing_complex_matrix_evidence_reasons"] == []

    item_refs = {item.file_path for item in bundle.evidence_package.items if item.source_type is EvidenceSourceType.IMAGE}
    assert set(matrix["matrix_table_image_refs"]) <= item_refs
    assert set(matrix["matrix_header_image_refs"]) <= item_refs
    assert set(matrix["matrix_body_image_refs"]) <= item_refs
    assert set(matrix["result_matrix_image_refs"]) <= item_refs
    assert set(matrix["conclusion_column_image_refs"]) <= item_refs
    assert set(matrix["continuation_page_image_refs"]) <= item_refs
    assert any(ref.endswith("-c07-matrix-page-p42.png") for ref in item_refs)
    assert any(ref.endswith("-c07-matrix-continuation-p43.png") for ref in item_refs)
    assert all(
        item.metadata.get("codex_image_input") is True
        for item in bundle.evidence_package.items
        if item.source_type is EvidenceSourceType.IMAGE
    )
    assert all(
        item.metadata.get("matrix_evidence_role")
        for item in bundle.evidence_package.items
        if item.source_type is EvidenceSourceType.IMAGE and item.section == "c07_complex_matrix_visual"
    )


def test_c07_complex_matrix_evidence_does_not_apply_to_regular_c07(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
        metadata={**_metadata_for_check("C07"), "item_no": "33", "normalized_item_no": "33"},
        id_suffix="c07-regular",
    )

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=_report_document(
            inspection_items=[
                InspectionItem(
                    sequence_raw="33",
                    sequence=33,
                    item_name="分类标记",
                    test_result="——",
                    conclusion="符合",
                    remark="/",
                    source_page=22,
                    row_index_in_page=10,
                    metadata={
                        "visual_geometry": {
                            "table_bbox": [10, 20, 210, 120],
                            "row_bbox": [10, 50, 210, 80],
                            "field_bboxes": {
                                "test_result": [110, 50, 150, 80],
                                "conclusion": [150, 50, 185, 80],
                                "remark": [185, 50, 210, 80],
                            },
                        }
                    },
                )
            ]
        ),
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=22, text="序号 33 分类标记")]),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    assert "c07_complex_matrix_evidence" not in target.metadata
    assert target.metadata["c07_visual_evidence"]["visual_review_mode"] == "inspection_item_group"


def test_c07_complex_matrix_without_source_pdf_records_missing_reason() -> None:
    finding = _complex_matrix_finding()

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=_report_document(inspection_items=_complex_matrix_rows_with_visual_geometry(pages=[42, 43])),
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=42, text="序号 59 复杂矩阵")]),
        source_pdf_path=None,
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    matrix = target.metadata["c07_complex_matrix_evidence"]
    assert matrix["has_complex_matrix_input"] is False
    assert matrix["review_mode"] == "complex_matrix_specialized"
    assert "source_pdf_path_missing" in matrix["missing_complex_matrix_evidence_reasons"]
    assert not any(item.source_type is EvidenceSourceType.IMAGE for item in bundle.evidence_package.items)


def test_c07_complex_matrix_paths_are_workspace_relative_and_sanitized() -> None:
    source_pdf = Path("/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf")
    finding = _complex_matrix_finding()

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=_report_document(inspection_items=_complex_matrix_rows_with_visual_geometry(pages=[42, 43])),
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=42, text="序号 59 复杂矩阵")]),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    target_dump = bundle.request.targets[0].model_dump_json()
    allowed_refs = [ref.ref_id for ref in bundle.request.targets[0].evidence_refs]
    matrix = bundle.request.targets[0].metadata["c07_complex_matrix_evidence"]
    assert "/Users/" not in target_dump
    assert OLD_PROJECT_ROOT not in target_dump
    assert not any(ref.startswith("/") for ref in allowed_refs)
    assert all(path.startswith("items/") for values in matrix.items() if isinstance(values, list) for path in values if isinstance(path, str) and path.endswith(".png"))
    assert all(not item.file_path.startswith("/") for item in bundle.evidence_package.items if item.file_path)
    assert OLD_PROJECT_ROOT not in bundle.evidence_package.targets[0].model_dump_json()


def test_c07_complex_matrix_structured_hints_include_rows_and_continuations(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _complex_matrix_finding()

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=_report_document(inspection_items=_complex_matrix_rows_with_structured_cells()),
        parsed_pdf=_parsed_pdf(
            extra_pages=[PdfPage(page_number=page, text=f"序号 59 复杂矩阵 p{page}") for page in [42, 43, 44, 45]]
        ),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    matrix = bundle.request.targets[0].metadata["c07_complex_matrix_evidence"]
    hints = matrix["structured_matrix_hints"]
    assert hints["item_no"] == "59"
    assert hints["pages"] == [42, 43, 44, 45]
    assert hints["group_row_count"] == 4
    assert hints["continuation_markers"]
    assert hints["effective_test_results"]
    assert hints["actual_conclusion_candidates"]
    assert hints["complex_matrix_table"] is True
    assert hints["complex_matrix_reason"]
    assert hints["known_columns"]
    assert "——" in hints["placeholder_tokens"]
    assert "0.05 mA" in hints["non_placeholder_tokens"]
    assert hints["candidate_conclusion"] == "符合"
    assert len(hints["source_rows"]) == 4


def test_c07_item_94_evidence_is_compact_and_contains_recovered_result_context() -> None:
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_MISMATCH_001",
        expected="/",
        actual="符合",
        metadata={
            **_metadata_for_check("C07"),
            "item_no": "94",
            "normalized_item_no": "94",
            "decision_reason": "all_placeholders_or_blank",
        },
    )
    unrelated_text = "无关页面全文 " * 4000
    item_excerpt = (
        "序号 94 电源输入 12.4.1 检验结果 —— 单项结论 符合\n"
        "12.4.2 控制器保护 检验结果：符合要求\n"
        "12.4.4 防止误动作 检验结果 符合要求\n"
        "序号 95 后续项目 检验结果 ——"
    )

    bundle = ReportCodexEvidenceBuilder(max_text_chars=1000).build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C07", [finding]),
        report=_report_document(
            inspection_items=[
                InspectionItem(
                    sequence_raw="94",
                    sequence=94,
                    item_name="电源输入",
                    standard_clause="12.4.1",
                    standard_requirement="应记录电源输入结果" * 40,
                    test_result="——",
                    result_values=["——"],
                    conclusion="符合",
                    remark="/",
                    source_page=72,
                    row_index_in_page=10,
                ),
                InspectionItem(
                    sequence_raw="续 94",
                    sequence=94,
                    is_continuation=True,
                    item_name="电源输入",
                    standard_clause="12.4.1",
                    standard_requirement="续表占位",
                    test_result="——",
                    result_values=["——"],
                    conclusion="",
                    remark="/",
                    source_page=73,
                    row_index_in_page=0,
                ),
                InspectionItem(
                    sequence_raw="12.4.2",
                    item_name="12.4.2 控制器保护",
                    standard_clause="12.4.2",
                    standard_requirement="控制器保护要求",
                    test_result="",
                    conclusion="",
                    remark="",
                    source_page=73,
                    row_index_in_page=1,
                    metadata={"row_text": "12.4.2 控制器保护 检验结果：符合要求"},
                ),
                InspectionItem(
                    sequence_raw="12.4.4",
                    item_name="12.4.4 防止误动作",
                    standard_clause="12.4.4",
                    standard_requirement="防止误动作要求",
                    test_result="",
                    conclusion="",
                    remark="",
                    source_page=73,
                    row_index_in_page=2,
                    metadata={"row_text": "12.4.4 防止误动作 检验结果 符合要求"},
                ),
            ]
        ),
        parsed_pdf=_parsed_pdf(
            extra_pages=[
                PdfPage(page_number=72, text=unrelated_text + "\n" + item_excerpt),
                PdfPage(page_number=73, text=item_excerpt + "\n" + unrelated_text),
            ]
        ),
    )

    assert bundle is not None
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    inspection_item = items_by_ref[f"inspection_item:{finding.id}"]
    page_text = items_by_ref[f"inspection_page_text:{finding.id}"]
    group = inspection_item.structured["inspection_item_group"]

    assert group["original_effective_test_results"] == ["——", "——"]
    assert group["recovered_result_tokens"] == ["符合要求", "符合要求"]
    assert group["recovered_effective_test_results"] == ["——", "——", "符合要求", "符合要求"]
    assert "compact_rows" in group
    assert "source_rows" not in group
    assert "complete_rows" not in group
    assert group["compact_rows"][0]["standard_requirement_excerpt"].endswith("[truncated]")
    assert "12.4.2" in page_text.text
    assert "12.4.4" in page_text.text
    assert "符合要求" in page_text.text
    assert "无关页面全文" not in page_text.text
    assert f"page_text:{finding.id}" not in items_by_ref
    assert len(bundle.evidence_package.model_dump_json()) < 300_000


def test_c09_evidence_contains_sequence_context_and_neighbor_rows() -> None:
    finding = _finding(
        check_id="C09",
        code="SEQUENCE_GAP",
        metadata={
            "item_no": "4",
            "missing_sequence": 3,
            "previous_item_no": "2",
            "next_item_no": "4",
            "page_number": 4,
        },
    )

    bundle = ReportCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.REPORT_CHECK.value,
        result=_check_result("C09", [finding]),
        report=_report_document(
            inspection_items=[
                InspectionItem(sequence_raw="2", sequence=2, item_name="项目 2", source_page=4, row_index_in_page=1),
                InspectionItem(sequence_raw="4", sequence=4, item_name="项目 4", source_page=4, row_index_in_page=2),
            ]
        ),
        parsed_pdf=_parsed_pdf(),
    )

    assert bundle is not None
    assert bundle.request.targets[0].target_type is CodexReviewTargetType.INSPECTION_ITEM
    sequence_item = next(item for item in bundle.evidence_package.items if item.ref_id.startswith("sequence_context:"))
    assert sequence_item.structured["sequence_context"]["finding_item_no"] == "4"
    assert sequence_item.structured["sequence_context"]["previous_item_no"] == "2"
    assert sequence_item.structured["sequence_context"]["next_item_no"] == "4"
    assert [row["sequence_raw"] for row in sequence_item.structured["sequence_context"]["neighbor_rows"]] == ["2", "4"]


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


def _complex_matrix_finding(*, item_no: str = "59") -> Finding:
    return _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX",
        metadata={
            **_metadata_for_check("C07"),
            "item_no": item_no,
            "normalized_item_no": item_no,
            "complex_matrix_table": True,
            "complex_matrix_reason": "8.7 漏电流多页复杂矩阵需要专门矩阵审核",
        },
        id_suffix="c07-matrix",
        message=f"序号 {item_no} 为复杂矩阵表，普通 C07 单项结论逻辑无法稳定判断。",
    )


def _complex_matrix_rows_with_visual_geometry(*, pages: list[int]) -> list[InspectionItem]:
    rows: list[InspectionItem] = []
    for index, page in enumerate(pages):
        y0 = 150.0 + index * 24.0
        sequence_raw = "59" if index == 0 else "续 59"
        rows.append(
            InspectionItem(
                sequence_raw=sequence_raw,
                sequence=59 if index == 0 else None,
                is_continuation=index > 0,
                item_name="8.7 漏电流" if index == 0 else "8.7 漏电流（续）",
                standard_requirement="漏电流矩阵列应符合要求" if index == 0 else "续表条件与测量值",
                test_result="0.05 mA" if index == 0 else "——",
                result_values=["0.05 mA"] if index == 0 else ["——"],
                conclusion="符合" if index == len(pages) - 1 else "",
                remark="/",
                source_page=page,
                row_index_in_page=index + 1,
                field_provenance={"test_result": "synthetic matrix cell"},
                metadata={
                    "complex_matrix_table": True,
                    "condition": "正常状态" if index == 0 else "续表条件",
                    "row_text": "检验结果：0.05 mA 单项结论 符合" if index == 0 else "检验结果：——",
                    "visual_geometry": {
                        "table_id": f"p{page}-matrix",
                        "table_bbox": [20.0, 80.0, 560.0, 720.0],
                        "row_bbox": [20.0, y0, 560.0, y0 + 24.0],
                        "field_bboxes": {
                            "test_result": [260.0, y0, 460.0, y0 + 24.0],
                            "conclusion": [460.0, y0, 520.0, y0 + 24.0],
                            "remark": [520.0, y0, 560.0, y0 + 24.0],
                        },
                    },
                },
            )
        )
    return rows


def _complex_matrix_rows_with_structured_cells() -> list[InspectionItem]:
    return _complex_matrix_rows_with_visual_geometry(pages=[42, 43, 44, 45])


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
    if check_id == "C09":
        return {
            "item_no": "4",
            "missing_sequence": 3,
            "previous_item_no": "2",
            "next_item_no": "4",
            "page_number": 4,
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


def _parsed_pdf(
    page_text: str = "第三页生产日期：2025-01-02；中文标签：输注泵",
    *,
    home_page_text: str = "首页说明：“——”表示此项不适用；“/”表示此项空白。",
    extra_pages: list[PdfPage] | None = None,
) -> ParsedPdf:
    return ParsedPdf(
        file_id="pdf-1",
        file_name="report.pdf",
        page_count=6,
        pages=[
            PdfPage(page_number=1, text=home_page_text),
            PdfPage(page_number=3, text=page_text),
            PdfPage(page_number=4, text="序号 1 检验结果 不符合要求 单项结论 符合"),
            PdfPage(page_number=5, text="图2 输注泵中文标签样张"),
            PdfPage(page_number=6, text="图1 输注泵外观照片"),
            *(extra_pages or []),
        ],
    )
