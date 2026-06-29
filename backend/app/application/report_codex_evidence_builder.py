from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath
import re
from typing import Any

from pydantic import BaseModel

from app.application.c07_visual_evidence import C07VisualEvidenceBuilder, C07VisualEvidenceResult
from app.application.codex_audit_targeting import (
    CodexAuditTargetSelection,
    DEFAULT_CODEX_AUDIT_MAX_TARGETS,
    DEFAULT_REPORT_PRIORITY_CHECK_IDS,
    priority_index,
)
from app.domain.codex_review import (
    CodexEvidenceRef,
    CodexReviewRequest,
    CodexReviewTarget,
    CodexReviewTargetType,
)
from app.domain.evidence_package import (
    EvidenceItem,
    EvidencePackage,
    EvidencePackageKind,
    EvidenceSourceType,
    EvidenceTarget,
)
from app.domain.finding import Finding
from app.domain.inspection_group import InspectionItemGroup
from app.domain.pdf import ParsedPdf
from app.domain.report import InspectionItem, LabelOCRResult, PhotoCaption, ReportDocument, ReportField, SampleComponent
from app.domain.result import CheckResult
from app.infrastructure.report.inspection_item_group_builder import build_inspection_item_groups
from app.rules.report.common import (
    compact,
    component_matches_label,
    component_not_used,
    is_chinese_label,
    match_name,
)


OLD_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"
REDACTED_PATH = "[redacted-path]"

REVIEWABLE_TARGET_TYPES = {
    "C02": CodexReviewTargetType.LABEL_OCR,
    "C03": CodexReviewTargetType.LABEL_OCR,
    "C04": CodexReviewTargetType.LABEL_OCR,
    "C05": CodexReviewTargetType.PHOTO_CAPTION,
    "C06": CodexReviewTargetType.LABEL_OCR,
    "C07": CodexReviewTargetType.INSPECTION_ITEM,
    "C09": CodexReviewTargetType.INSPECTION_ITEM,
}

RULE_CONTEXT_SUMMARY = {
    "C02": "第三页扩展字段与中文标签 OCR 字段的规则初判上下文。",
    "C03": "第三页生产日期与中文标签生产日期格式的规则初判上下文。",
    "C04": "样品描述表格字段与中文标签 OCR 字段的规则初判上下文。",
    "C05": "样品描述部件与照片 caption 覆盖关系的规则初判上下文。",
    "C06": "样品描述部件与中文标签 caption/OCR 覆盖关系的规则初判上下文。",
    "C07": "根据检验结果推导期望单项结论的规则初判上下文。",
    "C09": "检验项目序号连续性规则初判上下文。",
}

LABEL_CAPTION_KEYWORDS = ("中文标签样张", "中文标签", "标签样张", "包装标签", "标签", "铭牌", "标牌")
LABEL_CAPTION_TYPES = {"label", "chinese_label", "ocr_label"}


@dataclass(frozen=True)
class ReportCodexAuditBundle:
    request: CodexReviewRequest
    evidence_package: EvidencePackage


@dataclass(frozen=True)
class _CaptionMatch:
    caption: PhotoCaption
    score: int
    diagnostics: tuple[str, ...] = ()


class ReportCodexEvidenceBuilder:
    """Build minimal report self-check evidence packages for controlled Codex review."""

    def __init__(
        self,
        *,
        max_text_chars: int = 1200,
        max_targets_per_task: int = DEFAULT_CODEX_AUDIT_MAX_TARGETS,
        max_targets_per_batch: int = DEFAULT_CODEX_AUDIT_MAX_TARGETS,
        included_check_ids: str | list[str] | tuple[str, ...] | None = None,
        included_finding_codes: str | list[str] | tuple[str, ...] | None = None,
        excluded_check_ids: str | list[str] | tuple[str, ...] | None = None,
        priority_check_ids: str | list[str] | tuple[str, ...] | None = DEFAULT_REPORT_PRIORITY_CHECK_IDS,
    ) -> None:
        if max_text_chars <= 0:
            raise ValueError("max_text_chars must be greater than zero")
        self.max_text_chars = max_text_chars
        self.target_selection = CodexAuditTargetSelection.from_raw(
            max_targets_per_task=max_targets_per_task,
            max_targets_per_batch=max_targets_per_batch,
            included_check_ids=included_check_ids,
            included_finding_codes=included_finding_codes,
            excluded_check_ids=excluded_check_ids,
            priority_check_ids=priority_check_ids,
        )
        self.c07_visual_evidence_builder = C07VisualEvidenceBuilder()

    def build(
        self,
        *,
        task_id: str,
        task_type: str,
        result: CheckResult,
        report: ReportDocument | None = None,
        parsed_pdf: ParsedPdf | None = None,
        source_pdf_path: str | Path | None = None,
        target_limit: int | None = None,
        target_offset: int = 0,
    ) -> ReportCodexAuditBundle | None:
        findings = self._select_findings(
            result.findings,
            target_limit=target_limit,
            target_offset=target_offset,
        )
        if not findings:
            if target_offset > 0 or self.target_selection.effective_limit(override=target_limit) <= 0:
                return None
            if self.target_selection_has_filters() and not self._summary_allowed(result.check_id):
                return None
            return self._build_summary_bundle(
                task_id=task_id,
                task_type=task_type,
                result=result,
            )

        total_candidate_targets = self._total_candidate_targets(result.findings)
        selection_metadata = self.target_selection.selection_metadata(
            total_candidate_targets=total_candidate_targets,
            emitted_targets=len(findings),
            target_offset=target_offset,
        )
        items_by_ref: dict[str, EvidenceItem] = {}
        targets: list[EvidenceTarget] = []
        review_targets: list[CodexReviewTarget] = []
        source_pdf_path_text = str(source_pdf_path) if source_pdf_path is not None else None

        for finding in findings:
            target_type = REVIEWABLE_TARGET_TYPES[finding.check_id]
            evidence_refs = self._evidence_refs_for_finding(
                finding,
                result=result,
                report=report,
                parsed_pdf=parsed_pdf,
                source_pdf_path=source_pdf_path_text,
                items_by_ref=items_by_ref,
            )
            target_id = f"report-codex-target-{finding.id}"
            metadata = self._target_metadata(finding, report=report, source_pdf_path=source_pdf_path_text)
            targets.append(
                EvidenceTarget(
                    target_id=target_id,
                    target_type=target_type.value,
                    check_id=finding.check_id,
                    finding_id=finding.id,
                    finding_code=finding.code,
                    summary=self._sanitize_text(finding.message),
                    evidence_refs=evidence_refs,
                    metadata=metadata,
                )
            )
            review_targets.append(
                CodexReviewTarget(
                    target_id=target_id,
                    target_type=target_type,
                    check_id=finding.check_id,
                    finding_id=finding.id,
                    finding_code=finding.code,
                    title=self._sanitize_text(finding.message),
                    summary=self._sanitize_text(finding.message),
                    evidence_refs=[
                        CodexEvidenceRef(
                            ref_id=ref_id,
                            source_type=items_by_ref[ref_id].source_type.value,
                            page_number=items_by_ref[ref_id].page_number,
                            section=items_by_ref[ref_id].section,
                            description=items_by_ref[ref_id].title,
                        )
                        for ref_id in evidence_refs
                    ],
                    metadata=metadata,
                )
            )

        package = EvidencePackage(
            package_id=f"codex-report-{task_id}-{self._safe_id(result.check_id)}-batch-{selection_metadata['batch_index']}",
            task_id=task_id,
            task_type=task_type,
            kind=EvidencePackageKind.REPORT_RULE_REVIEW,
            schema_version="evidence-package-v1",
            created_at=_utc_now(),
            targets=targets,
            items=list(items_by_ref.values()),
            metadata={
                "source": "report_codex_evidence_builder",
                "check_id": result.check_id,
                "deterministic_finding_count": len(result.findings),
                "target_count": len(review_targets),
                **selection_metadata,
                **({"source_pdf_path": source_pdf_path_text} if source_pdf_path_text else {}),
            },
        )
        request = CodexReviewRequest(
            request_id=f"codex-request-{task_id}-report-{self._safe_id(result.check_id)}-batch-{selection_metadata['batch_index']}",
            task_id=task_id,
            task_type=task_type,
            mode="verify",
            targets=review_targets,
            prompt_version="report-review-v1",
            schema_version="codex-review-output-v1",
            created_at=_utc_now(),
            metadata={
                "source": "report_codex_evidence_builder",
                "check_id": result.check_id,
                "deterministic_finding_count": len(result.findings),
                "target_count": len(review_targets),
                **selection_metadata,
            },
        )
        return ReportCodexAuditBundle(request=request, evidence_package=package)

    def _build_summary_bundle(
        self,
        *,
        task_id: str,
        task_type: str,
        result: CheckResult,
    ) -> ReportCodexAuditBundle:
        ref_id = f"check_result:{self._safe_id(result.check_id)}"
        target_id = f"report-codex-check-summary-{self._safe_id(result.check_id)}"
        item = EvidenceItem(
            ref_id=ref_id,
            source_type=EvidenceSourceType.RULE_CONTEXT,
            title=f"{result.check_id} deterministic check summary",
            text=self._sanitize_text(RULE_CONTEXT_SUMMARY.get(result.check_id, "报告自检规则初判汇总上下文。")),
            structured=self._safe_payload(
                {
                    "check_id": result.check_id,
                    "check_name": result.check_name,
                    "status": result.status.value,
                    "summary": result.summary,
                    "deterministic_finding_count": len(result.findings),
                    "finding_codes": [finding.code for finding in result.findings],
                    "rule_output_role": "candidate_summary_not_final_conclusion",
                    "audit_reason": "review deterministic report check summary and decide whether evidence is sufficient",
                }
            ),
            section=result.check_id,
            metadata={"check_id": result.check_id, "target_kind": "check_result_summary", "summary_only": True},
        )
        selection_metadata = self.target_selection.selection_metadata(
            total_candidate_targets=1,
            emitted_targets=1,
            target_offset=0,
        )
        target = EvidenceTarget(
            target_id=target_id,
            target_type=CodexReviewTargetType.CHECK_RESULT.value,
            check_id=result.check_id,
            summary=self._sanitize_text(result.summary or f"{result.check_id} deterministic check summary"),
            evidence_refs=[ref_id],
            metadata={"source": "report_codex_evidence_builder", "target_kind": "check_result_summary", "summary_only": True},
        )
        review_target = CodexReviewTarget(
            target_id=target_id,
            target_type=CodexReviewTargetType.CHECK_RESULT,
            check_id=result.check_id,
            title=self._sanitize_text(result.check_name),
            summary=self._sanitize_text(result.summary or f"{result.check_id} deterministic check summary"),
            evidence_refs=[
                CodexEvidenceRef(
                    ref_id=ref_id,
                    source_type=item.source_type.value,
                    section=item.section,
                    description=item.title,
                )
            ],
            metadata={"source": "report_codex_evidence_builder", "target_kind": "check_result_summary", "summary_only": True},
        )
        package = EvidencePackage(
            package_id=f"codex-report-{task_id}-{self._safe_id(result.check_id)}-summary",
            task_id=task_id,
            task_type=task_type,
            kind=EvidencePackageKind.REPORT_RULE_REVIEW,
            schema_version="evidence-package-v1",
            created_at=_utc_now(),
            targets=[target],
            items=[item],
            metadata={
                "source": "report_codex_evidence_builder",
                "check_id": result.check_id,
                "deterministic_finding_count": len(result.findings),
                "target_count": 1,
                "summary_target": True,
                "summary_only": True,
                **selection_metadata,
            },
        )
        request = CodexReviewRequest(
            request_id=f"codex-request-{task_id}-report-{self._safe_id(result.check_id)}-summary",
            task_id=task_id,
            task_type=task_type,
            mode="verify",
            targets=[review_target],
            prompt_version="report-review-v1",
            schema_version="codex-review-output-v1",
            created_at=_utc_now(),
            metadata={
                "source": "report_codex_evidence_builder",
                "check_id": result.check_id,
                "deterministic_finding_count": len(result.findings),
                "target_count": 1,
                "summary_target": True,
                "summary_only": True,
                **selection_metadata,
            },
        )
        return ReportCodexAuditBundle(request=request, evidence_package=package)

    def target_selection_has_filters(self) -> bool:
        return bool(
            self.target_selection.included_check_ids
            or self.target_selection.included_finding_codes
            or self.target_selection.excluded_check_ids
        )

    def remaining_target_budget(self, emitted_targets: int) -> int:
        task_limit = self.target_selection.max_targets_per_task
        batch_limit = self.target_selection.max_targets_per_batch
        if task_limit <= 0 or batch_limit <= 0:
            return 0
        return max(0, min(task_limit - emitted_targets, batch_limit))

    def _select_findings(
        self,
        findings: list[Finding],
        *,
        target_limit: int | None,
        target_offset: int,
    ) -> list[Finding]:
        candidates = [
            finding
            for finding in findings
            if finding.check_id in REVIEWABLE_TARGET_TYPES and self.target_selection.allows(finding)
        ]
        candidates = self._sort_findings(candidates)
        limit = self.target_selection.effective_limit(override=target_limit)
        if limit <= 0:
            return []
        return candidates[target_offset : target_offset + limit]

    def _total_candidate_targets(self, findings: list[Finding]) -> int:
        return len(
            [
                finding
                for finding in findings
                if finding.check_id in REVIEWABLE_TARGET_TYPES and self.target_selection.allows(finding)
            ]
        )

    def _sort_findings(self, findings: list[Finding]) -> list[Finding]:
        priority = priority_index(self.target_selection.priority_check_ids)
        fallback = len(priority)
        return [
            item
            for _, item in sorted(
                enumerate(findings),
                key=lambda pair: (priority.get(pair[1].check_id, fallback), pair[0]),
            )
        ]

    def _evidence_refs_for_finding(
        self,
        finding: Finding,
        *,
        result: CheckResult,
        report: ReportDocument | None,
        parsed_pdf: ParsedPdf | None,
        source_pdf_path: str | None,
        items_by_ref: dict[str, EvidenceItem],
    ) -> list[str]:
        refs: list[str] = []
        self._add_item(items_by_ref, self._finding_item(finding), refs)
        self._add_item(
            items_by_ref,
            self._rule_context_item(finding, result, report=report, source_pdf_path=source_pdf_path),
            refs,
        )

        if finding.check_id in {"C02", "C03"}:
            self._add_optional_item(items_by_ref, self._report_field_item(finding, report), refs)
            self._add_optional_item(items_by_ref, self._label_ocr_item(finding, report), refs)
        elif finding.check_id == "C04":
            self._add_optional_item(items_by_ref, self._sample_description_item(finding, report), refs)
            self._add_optional_item(items_by_ref, self._matching_label_caption_item(finding, report), refs)
            self._add_optional_item(items_by_ref, self._label_ocr_item(finding, report, source_pdf_path=source_pdf_path), refs)
            self._add_optional_item(items_by_ref, self._label_image_item(finding, report, source_pdf_path=source_pdf_path), refs)
        elif finding.check_id == "C05":
            self._add_optional_item(items_by_ref, self._component_item(finding, report), refs)
            self._add_optional_item(items_by_ref, self._photo_caption_item(finding, report), refs)
        elif finding.check_id == "C06":
            self._add_optional_item(items_by_ref, self._component_item(finding, report), refs)
            self._add_optional_item(items_by_ref, self._label_ocr_item(finding, report, source_pdf_path=source_pdf_path), refs)
            self._add_optional_item(items_by_ref, self._label_image_item(finding, report, source_pdf_path=source_pdf_path), refs)
            self._add_optional_item(items_by_ref, self._label_caption_item(finding, report), refs)
        elif finding.check_id == "C07":
            self._add_optional_item(items_by_ref, self._inspection_item(finding, report), refs)
            self._add_optional_item(items_by_ref, self._inspection_symbol_note_item(finding, parsed_pdf), refs)
            self._add_optional_item(items_by_ref, self._inspection_group_page_text_item(finding, report, parsed_pdf), refs)
            visual_evidence = self._c07_visual_evidence(
                finding,
                report=report,
                source_pdf_path=source_pdf_path,
            )
            if visual_evidence is not None:
                for item in visual_evidence.items:
                    self._add_item(items_by_ref, item, refs)
        elif finding.check_id == "C09":
            self._add_optional_item(items_by_ref, self._sequence_context_item(finding, report), refs)

        if finding.check_id != "C07":
            self._add_optional_item(items_by_ref, self._page_text_item(finding, parsed_pdf), refs)
        return refs

    def _add_item(self, items_by_ref: dict[str, EvidenceItem], item: EvidenceItem, refs: list[str]) -> None:
        if item.ref_id not in items_by_ref:
            items_by_ref[item.ref_id] = item
        if item.ref_id not in refs:
            refs.append(item.ref_id)

    def _add_optional_item(
        self,
        items_by_ref: dict[str, EvidenceItem],
        item: EvidenceItem | None,
        refs: list[str],
    ) -> None:
        if item is not None:
            self._add_item(items_by_ref, item, refs)

    def _finding_item(self, finding: Finding) -> EvidenceItem:
        structured = (
            self._compact_finding_payload(finding) if finding.check_id == "C07" else self._safe_payload(finding)
        )
        return EvidenceItem(
            ref_id=f"finding:{finding.id}",
            source_type=EvidenceSourceType.FINDING,
            title=self._sanitize_text(finding.message),
            structured=structured,
            page_number=self._page_number_for_finding(finding),
            section=finding.location.section if finding.location else finding.check_id,
            location=self._safe_payload(finding.location) if finding.location else None,
            metadata={
                "finding_id": finding.id,
                "check_id": finding.check_id,
                "finding_code": finding.code,
                "severity": finding.severity.value,
            },
        )

    def _rule_context_item(
        self,
        finding: Finding,
        result: CheckResult,
        *,
        report: ReportDocument | None,
        source_pdf_path: str | None = None,
    ) -> EvidenceItem:
        structured = {
            "check_id": finding.check_id,
            "check_name": result.check_name,
            "finding_id": finding.id,
            "code": finding.code,
            "severity": finding.severity.value,
            "message": finding.message,
            "expected": finding.expected,
            "actual": finding.actual,
            "finding_metadata": (
                self._compact_c07_metadata(finding.metadata) if finding.check_id == "C07" else finding.metadata
            ),
            "result_metadata": (
                self._compact_c07_result_metadata(result.metadata) if finding.check_id == "C07" else result.metadata
            ),
            "audit_reason": "review deterministic report self-check candidate finding against focused evidence",
            "evidence_incomplete": False,
        }
        if finding.check_id in {"C04", "C06"}:
            structured["label_content_verification"] = self._label_content_verification(
                finding,
                report,
                source_pdf_path=source_pdf_path,
            )
        if finding.check_id in {"C04", "C05", "C06"}:
            component = self._component_for_finding(finding, report)
            structured["component_usage"] = {
                "is_unused_component": self._is_unused_component(finding, component),
                "unused_reason": self._unused_reason(finding, component),
            }
        return EvidenceItem(
            ref_id=f"rule_context:{finding.id}",
            source_type=EvidenceSourceType.RULE_CONTEXT,
            title=f"{finding.check_id} deterministic rule context",
            text=self._sanitize_text(RULE_CONTEXT_SUMMARY.get(finding.check_id, "报告自检规则初判上下文。")),
            structured=self._safe_payload(structured),
            page_number=self._page_number_for_finding(finding),
            section=finding.check_id,
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "finding_code": finding.code},
        )

    def _report_field_item(self, finding: Finding, report: ReportDocument | None) -> EvidenceItem | None:
        field_name = self._metadata_str(finding, "field_name") or "生产日期"
        field = self._third_page_field(report, field_name)
        label = self._label_for_finding(finding, report)
        label_field = self._label_field(label, self._metadata_str(finding, "matched_label_key") or field_name)
        structured = {
            "field_name": field_name,
            "expected": finding.expected,
            "actual": finding.actual,
            "third_page_value": self._field_value(field),
            "third_page_raw_value": field.raw_value if field else None,
            "third_page_confidence": field.confidence.value if field and field.confidence else None,
            "label_id": label.label_id if label else self._metadata_str(finding, "label_id"),
            "matched_label_key": label_field.name if label_field else self._metadata_str(finding, "matched_label_key"),
            "label_value": self._field_value(label_field),
            "label_raw_value": label_field.raw_value if label_field else None,
            "ocr_confidence": self._confidence_value(label_field, label),
            "finding_metadata": finding.metadata,
        }
        return EvidenceItem(
            ref_id=f"report_field:{finding.id}",
            source_type=EvidenceSourceType.REPORT_FIELD,
            title=f"{finding.check_id} 第三页字段 evidence",
            structured=self._safe_payload(structured),
            page_number=field.location.page_number if field and field.location else self._page_number_for_finding(finding),
            section="third_page",
            location=self._safe_payload(field.location) if field and field.location else None,
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "field_name": field_name},
        )

    def _label_ocr_item(
        self,
        finding: Finding,
        report: ReportDocument | None,
        *,
        source_pdf_path: str | None = None,
    ) -> EvidenceItem | None:
        label = self._label_for_finding(finding, report)
        if label is None:
            return None
        structured = {
            "label_id": label.label_id,
            "page_number": label.page_number,
            "caption_id": label.caption_id,
            "caption_text": label.caption_text,
            "language": label.language,
            "ocr_engine": label.ocr_engine,
            "confidence": label.confidence.value if label.confidence else None,
            "raw_blocks": label.raw_blocks,
            "label_fields": {
                field.name: {
                    "value": field.value,
                    "raw_value": field.raw_value,
                    "confidence": field.confidence.value if field.confidence else None,
                    "aliases": field.aliases,
                }
                for field in label.fields
            },
            "finding_metadata": finding.metadata,
        }
        if finding.check_id in {"C04", "C06"}:
            verification = self._label_content_verification(finding, report, source_pdf_path=source_pdf_path)
            structured["label_content_verification"] = verification
            structured["matched_label_page_text"] = verification["matched_label_page_text"]
            structured["matched_label_caption_text"] = verification["matched_label_caption_text"]
            structured["matched_label_ocr_text"] = verification["matched_label_ocr_text"]
            structured["matched_label_text"] = verification["matched_label_text"]
            structured["matched_label_fields"] = verification["matched_label_fields"]
            structured["label_field_comparison"] = verification.get("label_field_comparison")
        return EvidenceItem(
            ref_id=f"label_ocr:{finding.id}",
            source_type=EvidenceSourceType.LABEL_OCR,
            title=f"{finding.check_id} 中文标签 OCR evidence",
            text=self._sanitize_text("\n".join(label.raw_blocks)),
            structured=self._safe_payload(structured),
            page_number=label.page_number,
            section="label_ocr",
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "label_id": label.label_id},
        )

    def _label_image_item(
        self,
        finding: Finding,
        report: ReportDocument | None,
        *,
        source_pdf_path: str | None = None,
    ) -> EvidenceItem | None:
        label = self._label_for_finding(finding, report)
        caption = self._selected_label_caption(finding, report)
        if label is None and caption is None:
            return None

        refs = self._label_image_reference_payload(label=label, caption=caption, finding=finding, source_pdf_path=source_pdf_path)
        image_ref = refs["label_image_ref"]
        file_path = self._relative_file_path(image_ref)
        page_number = refs["label_page_number"]
        component = self._component_for_finding(finding, report)
        caption_text = label.caption_text if label and label.caption_text else caption.text if caption else None
        structured = {
            "label_id": label.label_id if label else None,
            "caption_id": label.caption_id if label and label.caption_id else caption.caption_id if caption else None,
            "caption_text": caption_text,
            "page_number": page_number,
            "label_page_number": page_number,
            "image_ref": image_ref,
            "label_image_ref": image_ref,
            "label_page_image_ref": refs["label_page_image_ref"],
            "label_crop_ref": refs["label_crop_ref"],
            "crop_unavailable_reason": refs["crop_unavailable_reason"],
            "label_caption_text": caption_text,
            "sample_description_row": self._component_summary(component, finding=finding) if component else None,
            "expected_label_fields": self._expected_label_fields(component),
            "has_image_crop": refs["evidence_has_matched_label_crop"],
            "has_visual_label_input": refs["evidence_has_visual_label_input"],
            "has_page_reference": page_number is not None,
            "caption_bbox": caption.bbox if caption else None,
            "finding_metadata": finding.metadata,
        }
        if refs["render_bbox"] is not None:
            structured["render_bbox"] = refs["render_bbox"]
        return EvidenceItem(
            ref_id=f"label_image:{finding.id}",
            source_type=EvidenceSourceType.IMAGE,
            title=f"{finding.check_id} matched label crop/page evidence",
            text=self._sanitize_text(caption_text or ""),
            structured=self._safe_payload(structured),
            file_path=file_path,
            page_number=page_number,
            section="label_image",
            metadata={
                "finding_id": finding.id,
                "check_id": finding.check_id,
                "label_id": label.label_id if label else None,
                "caption_id": caption.caption_id if caption else label.caption_id if label else None,
                "codex_image_input": refs["evidence_has_visual_label_input"],
                "render_source": refs["render_source"],
                "render_page_number": refs["render_page_number"],
                **({"render_bbox": refs["render_bbox"]} if refs["render_bbox"] is not None else {}),
            },
        )

    def _sample_description_item(self, finding: Finding, report: ReportDocument | None) -> EvidenceItem | None:
        component = self._component_for_finding(finding, report)
        if component is None:
            return None
        return EvidenceItem(
            ref_id=f"sample_description:{finding.id}",
            source_type=EvidenceSourceType.TABLE,
            title=f"{finding.check_id} 样品描述 evidence",
            structured=self._safe_payload(self._component_summary(component, finding=finding)),
            page_number=component.row_location.page_number if component.row_location else self._page_number_for_finding(finding),
            section="sample_description",
            location=self._safe_payload(component.row_location) if component.row_location else None,
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "component_id": component.component_id},
        )

    def _component_item(self, finding: Finding, report: ReportDocument | None) -> EvidenceItem | None:
        component = self._component_for_finding(finding, report)
        if component is None:
            return None
        return EvidenceItem(
            ref_id=f"component:{finding.id}",
            source_type=EvidenceSourceType.REPORT_FIELD,
            title=f"{finding.check_id} 样品部件 evidence",
            structured=self._safe_payload(self._component_summary(component, finding=finding)),
            page_number=component.row_location.page_number if component.row_location else self._page_number_for_finding(finding),
            section="sample_component",
            location=self._safe_payload(component.row_location) if component.row_location else None,
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "component_id": component.component_id},
        )

    def _photo_caption_item(self, finding: Finding, report: ReportDocument | None) -> EvidenceItem | None:
        caption = self._photo_caption_for_finding(finding, report)
        if caption is None:
            return None
        structured = {
            "caption_id": caption.caption_id,
            "caption_text": caption.text,
            "subject_name": caption.subject_name,
            "caption_type": caption.caption_type,
            "page_number": caption.page_number,
            "matched_component_ids": caption.matched_component_ids,
            "metadata": caption.metadata,
            "finding_metadata": finding.metadata,
        }
        return EvidenceItem(
            ref_id=f"photo_caption:{finding.id}",
            source_type=EvidenceSourceType.IMAGE_CAPTION,
            title=f"{finding.check_id} photo caption evidence",
            text=self._sanitize_text(caption.text),
            structured=self._safe_payload(structured),
            page_number=caption.page_number,
            section="photo_caption",
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "caption_id": caption.caption_id},
        )

    def _label_caption_item(self, finding: Finding, report: ReportDocument | None) -> EvidenceItem | None:
        caption_text = self._metadata_str(finding, "label_caption")
        caption = self._photo_caption_by_text(report, caption_text) if caption_text else None
        if caption is None:
            return None
        structured = {
            "caption_id": caption.caption_id,
            "caption_text": caption.text,
            "subject_name": caption.subject_name,
            "caption_type": caption.caption_type,
            "page_number": caption.page_number,
            "metadata": caption.metadata,
            "finding_metadata": finding.metadata,
        }
        return EvidenceItem(
            ref_id=f"label_caption:{finding.id}",
            source_type=EvidenceSourceType.IMAGE_CAPTION,
            title=f"{finding.check_id} label caption evidence",
            text=self._sanitize_text(caption.text),
            structured=self._safe_payload(structured),
            page_number=caption.page_number,
            section="label_caption",
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "caption_id": caption.caption_id},
        )

    def _matching_label_caption_item(self, finding: Finding, report: ReportDocument | None) -> EvidenceItem | None:
        candidates = self._matching_label_caption_candidates(finding, report)
        if not candidates:
            return None
        structured = {
            "matching_label_caption_candidates": [
                self._caption_summary(caption, finding=finding) for caption in candidates
            ],
            "finding_metadata": finding.metadata,
        }
        first = candidates[0]
        return EvidenceItem(
            ref_id=f"label_caption:{finding.id}",
            source_type=EvidenceSourceType.IMAGE_CAPTION,
            title=f"{finding.check_id} matching label caption evidence",
            text=self._sanitize_text("\n".join(caption.text for caption in candidates)),
            structured=self._safe_payload(structured),
            page_number=first.page_number,
            section="label_caption",
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "caption_id": first.caption_id},
        )

    def _inspection_item(self, finding: Finding, report: ReportDocument | None) -> EvidenceItem | None:
        group = self._inspection_item_group_for_finding(finding, report)
        if group is not None:
            structured = {
                "inspection_item_group": self._inspection_group_summary(group, finding=finding),
                "finding_metadata": finding.metadata,
            }
            return EvidenceItem(
                ref_id=f"inspection_item:{finding.id}",
                source_type=EvidenceSourceType.TABLE,
                title=f"{finding.check_id} 检验项目 group evidence",
                structured=self._safe_payload(structured),
                page_number=group.pages[0] if group.pages else self._page_number_for_finding(finding),
                section="inspection_item_group",
                location=self._safe_payload(group.rows[0].row_location) if group.rows and group.rows[0].row_location else None,
                metadata={
                    "finding_id": finding.id,
                    "check_id": finding.check_id,
                    "item_no": group.item_no,
                    "evidence_level": "inspection_item_group",
                },
            )

        item = self._inspection_item_for_finding(finding, report)
        if item is None:
            return None
        structured = {
            "sequence_raw": item.sequence_raw,
            "sequence": item.sequence,
            "item_name": item.item_name,
            "standard_clause": item.standard_clause,
            "standard_requirement": item.standard_requirement,
            "test_result": item.test_result,
            "result_values": item.result_values,
            "actual_conclusion": finding.metadata.get("actual_conclusion") or finding.actual or item.conclusion,
            "expected_conclusion": finding.expected,
            "conclusion": item.conclusion,
            "remark": item.remark,
            "source_page": item.source_page,
            "row_index_in_page": item.row_index_in_page,
            "field_provenance": item.field_provenance,
            "decision_reason": finding.metadata.get("decision_reason"),
            "finding_metadata": finding.metadata,
        }
        return EvidenceItem(
            ref_id=f"inspection_item:{finding.id}",
            source_type=EvidenceSourceType.TABLE,
            title=f"{finding.check_id} 检验项目 evidence",
            structured=self._safe_payload(structured),
            page_number=item.source_page or self._page_number_for_finding(finding),
            section="inspection_item",
            location=self._safe_payload(item.row_location) if item.row_location else None,
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "item_no": finding.metadata.get("item_no")},
        )

    def _inspection_symbol_note_item(
        self,
        finding: Finding,
        parsed_pdf: ParsedPdf | None,
    ) -> EvidenceItem | None:
        if parsed_pdf is None:
            return None
        page = next((candidate for candidate in parsed_pdf.pages if candidate.page_number == 1), None)
        if page is None:
            page = parsed_pdf.pages[0] if parsed_pdf.pages else None
        if page is None or not page.text:
            return None
        text = page.text
        if "——" not in text and "/" not in text:
            return None
        if "表示" not in text and "说明" not in text:
            return None
        return EvidenceItem(
            ref_id=f"symbol_note:{finding.id}",
            source_type=EvidenceSourceType.PAGE_TEXT,
            title=f"{finding.check_id} 首页符号说明 evidence",
            text=self._sanitize_text(text),
            structured=self._safe_payload(
                {
                    "page_number": page.page_number,
                    "symbol_note_text": text,
                    "dash_meaning_expected": "—— 表示此项不适用",
                    "slash_meaning_expected": "/ 表示此项空白",
                }
            ),
            page_number=page.page_number,
            section="homepage_symbol_note",
            metadata={"finding_id": finding.id, "check_id": finding.check_id},
        )

    def _inspection_group_page_text_item(
        self,
        finding: Finding,
        report: ReportDocument | None,
        parsed_pdf: ParsedPdf | None,
    ) -> EvidenceItem | None:
        if parsed_pdf is None:
            return None
        pages = self._inspection_group_pages_for_finding(finding, report)
        if not pages:
            page_number = self._page_number_for_finding(finding)
            pages = [page_number] if page_number else []
        wanted_pages = set(pages)
        page_payloads = [
            {
                "page_number": page.page_number,
                "text_excerpt": self._inspection_page_text_excerpt(page.text, finding=finding, report=report),
            }
            for page in parsed_pdf.pages
            if page.page_number in wanted_pages and page.text
        ]
        page_payloads = [payload for payload in page_payloads if payload["text_excerpt"]]
        if not page_payloads:
            return None
        text = "\n\n".join(f"[page {item['page_number']}]\n{item['text_excerpt']}" for item in page_payloads)
        return EvidenceItem(
            ref_id=f"inspection_page_text:{finding.id}",
            source_type=EvidenceSourceType.PAGE_TEXT,
            title=f"{finding.check_id} inspection item page text evidence",
            text=self._sanitize_text(text),
            structured=self._safe_payload(
                {
                    "pages": page_payloads,
                    "finding_metadata": self._compact_c07_metadata(finding.metadata),
                    "excerpt_scope": "around_inspection_item_only",
                }
            ),
            page_number=page_payloads[0]["page_number"],
            section="inspection_group_page_text",
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "pages": list(wanted_pages)},
        )

    def _sequence_context_item(self, finding: Finding, report: ReportDocument | None) -> EvidenceItem | None:
        if report is None or not report.inspection_items:
            return None
        item_no = self._metadata_str(finding, "normalized_item_no") or self._metadata_str(finding, "item_no")
        previous_item_no = self._metadata_str(finding, "previous_item_no")
        next_item_no = self._metadata_str(finding, "next_item_no")
        wanted = {value for value in (item_no, previous_item_no, next_item_no) if value}
        rows = [
            self._inspection_row_summary(item)
            for item in report.inspection_items
            if not wanted or str(item.sequence or item.sequence_raw or "") in wanted
        ]
        if not rows:
            rows = [self._inspection_row_summary(item) for item in report.inspection_items[:5]]
        structured = {
            "sequence_context": {
                "finding_item_no": item_no,
                "missing_sequence": finding.metadata.get("missing_sequence"),
                "previous_item_no": previous_item_no,
                "next_item_no": next_item_no,
                "neighbor_rows": rows[:8],
                "all_sequence_values_sample": [
                    item.sequence_raw or str(item.sequence or "")
                    for item in report.inspection_items[:20]
                    if item.sequence_raw or item.sequence is not None
                ],
                "finding_metadata": finding.metadata,
            }
        }
        return EvidenceItem(
            ref_id=f"sequence_context:{finding.id}",
            source_type=EvidenceSourceType.TABLE,
            title=f"{finding.check_id} 序号上下文 evidence",
            structured=self._safe_payload(structured),
            page_number=self._page_number_for_finding(finding),
            section="inspection_sequence_context",
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "item_no": item_no},
        )

    def _page_text_item(self, finding: Finding, parsed_pdf: ParsedPdf | None) -> EvidenceItem | None:
        page_number = self._page_number_for_finding(finding)
        if parsed_pdf is None or page_number is None:
            return None
        page = next((candidate for candidate in parsed_pdf.pages if candidate.page_number == page_number), None)
        if page is None or not page.text:
            return None
        return EvidenceItem(
            ref_id=f"page_text:{finding.id}",
            source_type=EvidenceSourceType.PAGE_TEXT,
            title=f"{finding.check_id} page text snippet",
            text=self._sanitize_text(page.text),
            structured=self._safe_payload({"page_number": page.page_number, "text": page.text}),
            page_number=page.page_number,
            section="page_text",
            metadata={"finding_id": finding.id, "check_id": finding.check_id, "file_id": parsed_pdf.file_id},
        )

    def _target_metadata(
        self,
        finding: Finding,
        *,
        report: ReportDocument | None,
        source_pdf_path: str | None = None,
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "source": "report_codex_evidence_builder",
            "rule_id": finding.check_id,
            "severity": finding.severity.value,
            "expected": finding.expected,
            "actual": finding.actual,
            "page_number": self._page_number_for_finding(finding),
            "finding_code": finding.code,
            "evidence_incomplete": False,
            "finding_metadata": (
                self._compact_c07_metadata(finding.metadata) if finding.check_id == "C07" else finding.metadata
            ),
        }
        if finding.check_id in {"C04", "C06"}:
            metadata.update(self._label_content_verification(finding, report, source_pdf_path=source_pdf_path))
        if finding.check_id in {"C04", "C05", "C06"}:
            component = self._component_for_finding(finding, report)
            metadata["is_unused_component"] = self._is_unused_component(finding, component)
            metadata["unused_reason"] = self._unused_reason(finding, component)
        if finding.check_id == "C07":
            metadata["complex_matrix_table"] = self._is_complex_matrix_table(finding, report)
            metadata["complex_matrix_reason"] = self._complex_matrix_reason(finding, report)
            if metadata["complex_matrix_table"]:
                metadata["expected_codex_when_complex_matrix"] = "uncertain"
            visual_evidence = self._c07_visual_evidence(
                finding,
                report=report,
                source_pdf_path=source_pdf_path,
            )
            if visual_evidence is not None:
                metadata["c07_visual_evidence"] = visual_evidence.metadata
                metadata["evidence_has_c07_visual_input"] = visual_evidence.metadata["has_visual_input"]
                complex_matrix_evidence = visual_evidence.metadata.get("c07_complex_matrix_evidence")
                if isinstance(complex_matrix_evidence, dict):
                    metadata["c07_complex_matrix_evidence"] = complex_matrix_evidence
        return self._safe_payload(metadata)

    def _c07_visual_evidence(
        self,
        finding: Finding,
        *,
        report: ReportDocument | None,
        source_pdf_path: str | None,
    ) -> C07VisualEvidenceResult | None:
        return self.c07_visual_evidence_builder.build(
            finding=finding,
            group=self._inspection_item_group_for_finding(finding, report),
            source_pdf_path=source_pdf_path,
            safe_id=self._safe_id,
        )

    def _summary_allowed(self, check_id: str) -> bool:
        if self.target_selection.included_check_ids and check_id not in self.target_selection.included_check_ids:
            return False
        if self.target_selection.excluded_check_ids and check_id in self.target_selection.excluded_check_ids:
            return False
        if self.target_selection.included_finding_codes:
            return False
        return True

    def _third_page_field(self, report: ReportDocument | None, field_name: str) -> ReportField | None:
        if report is None or report.third_page is None:
            return None
        fields = [
            report.third_page.model_spec,
            report.third_page.production_date,
            report.third_page.batch_or_serial,
            report.third_page.client,
            report.third_page.client_address,
            *report.third_page.fields,
        ]
        for field in fields:
            if field is None:
                continue
            if field.name == field_name or field_name in field.aliases:
                return field
        return None

    def _label_for_finding(self, finding: Finding, report: ReportDocument | None) -> LabelOCRResult | None:
        if report is None or not report.labels:
            return None
        matched_labels = self._matched_label_ocr_candidates(finding, report)
        if matched_labels:
            return matched_labels[0]
        if finding.check_id in {"C04", "C06"}:
            return None
        return report.labels[0]

    def _label_field(self, label: LabelOCRResult | None, field_name: str | None) -> ReportField | None:
        if label is None or not field_name:
            return None
        for field in label.fields:
            if field.name == field_name or field_name in field.aliases:
                return field
        return None

    def _component_for_finding(self, finding: Finding, report: ReportDocument | None) -> SampleComponent | None:
        if report is None or not report.sample_components:
            return None
        component_id = self._metadata_str(finding, "component_id")
        if component_id:
            for component in report.sample_components:
                if component.component_id == component_id:
                    return component
        return report.sample_components[0]

    def _photo_caption_for_finding(self, finding: Finding, report: ReportDocument | None) -> PhotoCaption | None:
        if report is None or not report.photo_captions:
            return None
        caption_id = self._metadata_str(finding, "caption_id")
        if caption_id:
            for caption in report.photo_captions:
                if caption.caption_id == caption_id:
                    return caption
        matched = finding.metadata.get("matched_captions")
        if isinstance(matched, list):
            for value in matched:
                caption = self._photo_caption_by_text(report, str(value))
                if caption is not None:
                    return caption
        return report.photo_captions[0]

    def _photo_caption_by_text(self, report: ReportDocument | None, text: str | None) -> PhotoCaption | None:
        if report is None or not text:
            return None
        for caption in report.photo_captions:
            if caption.text == text:
                return caption
        return None

    def _matching_label_caption_candidates(
        self,
        finding: Finding,
        report: ReportDocument | None,
    ) -> list[PhotoCaption]:
        return [match.caption for match in self._matching_label_caption_matches(finding, report)]

    def _selected_label_caption(
        self,
        finding: Finding,
        report: ReportDocument | None,
    ) -> PhotoCaption | None:
        matches = self._matching_label_caption_matches(finding, report)
        return self._selected_label_caption_from_matches(matches)

    def _selected_label_caption_from_matches(self, matches: list[_CaptionMatch]) -> PhotoCaption | None:
        if not matches:
            return None
        top = matches[0]
        if top.score < 40:
            return None
        if len(matches) > 1 and top.score - matches[1].score < 15:
            return None
        return top.caption

    def _matching_label_caption_matches(
        self,
        finding: Finding,
        report: ReportDocument | None,
    ) -> list[_CaptionMatch]:
        if report is None or not report.photo_captions:
            return []
        component = self._component_for_finding(finding, report)
        caption_text = self._metadata_str(finding, "label_caption")
        matches: list[_CaptionMatch] = []
        for caption in report.photo_captions:
            if not self._is_label_caption(caption):
                continue
            if caption_text and caption.text == caption_text:
                matches.append(_CaptionMatch(caption=caption, score=10_000, diagnostics=("explicit_label_caption",)))
                continue
            if component is None:
                continue
            match = self._caption_match_for_component(caption, component)
            if match is not None:
                matches.append(match)
        matches.sort(key=lambda item: item.score, reverse=True)
        return matches

    def _matched_label_ocr_candidates(
        self,
        finding: Finding,
        report: ReportDocument | None,
    ) -> list[LabelOCRResult]:
        if report is None or not report.labels:
            return []
        explicit = self._explicit_label_for_finding(finding, report)
        if explicit is not None:
            return [explicit]
        if finding.check_id not in {"C04", "C06"}:
            return []
        component = self._component_for_finding(finding, report)
        if component is None:
            return []
        return [
            label
            for label in report.labels
            if is_chinese_label(label) and component_matches_label(component, label)
        ]

    def _explicit_label_for_finding(
        self,
        finding: Finding,
        report: ReportDocument,
    ) -> LabelOCRResult | None:
        label_ids = [
            self._metadata_str(finding, "label_id"),
            self._metadata_str(finding, "label_key"),
            self._metadata_str(finding, "matched_label_key"),
        ]
        for label_id in label_ids:
            if not label_id:
                continue
            for label in report.labels:
                if label.label_id == label_id:
                    return label
        return None

    def _is_label_caption(self, caption: PhotoCaption) -> bool:
        caption_type = (caption.caption_type or "").strip().lower()
        text = f"{caption.text} {caption.subject_name or ''}"
        return caption_type in LABEL_CAPTION_TYPES or any(keyword in text for keyword in LABEL_CAPTION_KEYWORDS)

    def _caption_matches_component(self, caption: PhotoCaption, component: SampleComponent) -> bool:
        return self._caption_match_for_component(caption, component) is not None

    def _caption_match_for_component(self, caption: PhotoCaption, component: SampleComponent) -> _CaptionMatch | None:
        if component.component_id in caption.matched_component_ids:
            return _CaptionMatch(caption=caption, score=1_000, diagnostics=("explicit_component_id",))
        text = caption.subject_name or caption.text
        component_terms = self._component_caption_match_terms(component)
        caption_terms = [value for value in (text, caption.text, caption.subject_name) if value]
        diagnostics: list[str] = []
        score = 0
        for component_term in component_terms:
            for caption_term in caption_terms:
                left = compact(component_term).lower()
                right = compact(caption_term).lower()
                if not left or not right:
                    continue
                name_match = match_name(component_term, caption_term)
                if name_match == "exact":
                    score = max(score, 120)
                    diagnostics.append("exact_subject_match")
                elif left in right:
                    score = max(score, 95)
                    diagnostics.append("component_term_in_caption")
                elif right in left:
                    score = max(score, 60)
                    diagnostics.append("caption_term_in_component")
                elif name_match == "partial":
                    score = max(score, 45)
                    diagnostics.append("partial_subject_match")

        caption_text = compact(f"{caption.text} {caption.subject_name or ''}").lower()
        component_text = compact(f"{component.component_name or ''} {component.model or ''}").lower()
        for token in self._specific_caption_tokens(component.component_name):
            token_value = compact(token).lower()
            if not token_value:
                continue
            if token_value in caption_text:
                score += 18
                diagnostics.append(f"specific_token:{token}")
            elif token_value in component_text:
                score -= 14
                diagnostics.append(f"missing_specific_token:{token}")

        if component.model and compact(component.model).lower() in caption_text:
            score += 20
            diagnostics.append("model_match")

        return _CaptionMatch(caption=caption, score=score, diagnostics=tuple(diagnostics)) if score > 0 else None

    def _component_caption_match_terms(self, component: SampleComponent) -> list[str]:
        terms: list[str] = []
        for value in (component.component_name, component.model, component.batch_or_serial):
            if value and value not in terms:
                terms.append(value)
        if component.component_name:
            for separator in ("-", "－", "—", "–"):
                if separator in component.component_name:
                    tail = component.component_name.rsplit(separator, 1)[-1].strip()
                    if tail and tail not in terms:
                        terms.append(tail)
        return terms

    def _specific_caption_tokens(self, value: str | None) -> list[str]:
        text = value or ""
        tokens: list[str] = []
        for token in re.findall(r"\d+\s*m|[0-9]+米", text, flags=re.IGNORECASE):
            if token not in tokens:
                tokens.append(token)
        for token in re.findall(r"[（(]([^）)]+)[）)]", text):
            if token and token not in tokens:
                tokens.append(token)
        for token in (
            "触摸屏连接线缆",
            "触摸屏电源适配器",
            "连接线缆",
            "电源适配器",
            "导联线",
            "主线缆",
            "电源电缆",
            "等电位线缆",
            "脉冲导管连接电缆",
            "触摸屏",
            "推车",
            "主机",
        ):
            if token in text and token not in tokens:
                tokens.append(token)
        return tokens

    def _inspection_item_for_finding(self, finding: Finding, report: ReportDocument | None) -> InspectionItem | None:
        if report is None or not report.inspection_items:
            return None
        item_no = self._metadata_str(finding, "normalized_item_no") or self._metadata_str(finding, "item_no")
        if item_no:
            for item in report.inspection_items:
                if str(item.sequence or item.sequence_raw or "") == item_no:
                    return item
        return report.inspection_items[0]

    def _inspection_item_group_for_finding(
        self,
        finding: Finding,
        report: ReportDocument | None,
    ) -> InspectionItemGroup | None:
        if report is None or not report.inspection_items:
            return None
        item_no = self._metadata_str(finding, "normalized_item_no") or self._metadata_str(finding, "item_no")
        group_result = build_inspection_item_groups(list(report.inspection_items))
        if item_no:
            for group in group_result.groups:
                if group.item_no == item_no or group.display_item_no == item_no:
                    return group
        return group_result.groups[0] if group_result.groups else None

    def _inspection_group_summary(self, group: InspectionItemGroup, *, finding: Finding) -> dict[str, Any]:
        complex_matrix = self._group_is_complex_matrix(group, finding)
        complex_reason = (
            finding.metadata.get("complex_matrix_reason") or self._complex_matrix_reason_for_group(group)
            if complex_matrix
            else None
        )
        return {
            "item_no": group.item_no,
            "display_item_no": group.display_item_no,
            "effective_test_results": list(group.effective_test_results),
            "original_effective_test_results": list(group.original_effective_test_results),
            "recovered_result_tokens": list(group.recovered_result_tokens),
            "recovered_effective_test_results": list(group.recovered_effective_test_results),
            "result_token_recovery_applied": group.result_token_recovery_applied,
            "result_token_recovery_confidence": group.result_token_recovery_confidence,
            "result_token_recovery_diagnostics": list(group.result_token_recovery_diagnostics),
            "actual_conclusion": finding.metadata.get("actual_conclusion") or finding.actual or group.effective_single_conclusion,
            "expected_conclusion": finding.expected or finding.metadata.get("expected_conclusion"),
            "actual_conclusion_candidates": self._actual_conclusion_candidates(group, finding=finding),
            "conclusion_candidate_provenance": self._conclusion_candidate_provenance(group),
            "effective_single_conclusion": group.effective_single_conclusion,
            "effective_remark": group.effective_remark,
            "pages": list(group.pages),
            "continuation_markers": [marker.model_dump(mode="json") for marker in group.continuation_markers],
            "group_row_count": len(group.rows),
            "compact_rows": self._inspection_compact_rows(group),
            "result_summary": finding.metadata.get("result_summary"),
            "reasoning_basis": finding.metadata.get("reasoning_basis") or finding.metadata.get("decision_reason"),
            "suppressed_physical_row_count": finding.metadata.get("suppressed_physical_row_count"),
            "complex_matrix_table": complex_matrix,
            "complex_matrix_reason": complex_reason,
            "group_diagnostics": group.diagnostics,
        }

    def _inspection_row_summary(self, item: InspectionItem) -> dict[str, Any]:
        return {
            "sequence_raw": item.sequence_raw,
            "sequence": item.sequence,
            "is_continuation": item.is_continuation,
            "item_name": item.item_name,
            "standard_clause": item.standard_clause,
            "test_result": item.test_result,
            "conclusion": item.conclusion,
            "remark": item.remark,
            "source_page": item.source_page,
            "row_index_in_page": item.row_index_in_page,
            "field_provenance": item.field_provenance,
            "metadata": item.metadata,
        }

    def _inspection_compact_rows(self, group: InspectionItemGroup) -> list[dict[str, Any]]:
        recovered_by_row = {
            diagnostic.get("source_row_index"): diagnostic.get("token")
            for diagnostic in group.result_token_recovery_diagnostics
            if diagnostic.get("code") == "RESULT_TOKEN_RECOVERED" and diagnostic.get("source_row_index") is not None
        }
        rows: list[dict[str, Any]] = []
        for item in group.rows:
            rows.append(
                {
                    "page_number": item.source_page,
                    "row_index": item.row_index_in_page,
                    "sequence_raw": item.sequence_raw,
                    "standard_clause": item.standard_clause,
                    "standard_requirement_excerpt": self._truncate_for_evidence(item.standard_requirement, limit=160),
                    "test_result": item.test_result,
                    "single_conclusion": item.conclusion,
                    "remark": item.remark,
                    "recovered_result_token": recovered_by_row.get(item.row_index_in_page),
                    "field_provenance": dict(item.field_provenance),
                }
            )
        return rows

    def _component_summary(self, component: SampleComponent, *, finding: Finding) -> dict[str, Any]:
        is_unused = self._is_unused_component(finding, component)
        return {
            "component_id": component.component_id,
            "component_name": component.component_name,
            "model": component.model,
            "batch_or_serial": component.batch_or_serial,
            "production_date": component.production_date,
            "expiration_date": component.expiration_date,
            "remark": component.remark,
            "identity_key": component.identity_key,
            "is_unused_component": is_unused,
            "unused_reason": self._unused_reason(finding, component),
            "expected": finding.expected,
            "actual": finding.actual,
            "finding_metadata": finding.metadata,
        }

    def _label_content_verification(
        self,
        finding: Finding,
        report: ReportDocument | None,
        *,
        source_pdf_path: str | None = None,
    ) -> dict[str, Any]:
        label = self._label_for_finding(finding, report)
        matched_labels = self._matched_label_ocr_candidates(finding, report)
        unmatched_labels = self._unmatched_label_ocr_candidates(report, matched_labels)
        caption_matches = self._matching_label_caption_matches(finding, report)
        caption_candidates = [match.caption for match in caption_matches]
        caption = self._selected_label_caption_from_matches(caption_matches)
        image_refs = self._label_image_reference_payload(
            label=label,
            caption=caption,
            finding=finding,
            source_pdf_path=source_pdf_path,
        )
        matched_label_page_text = self._matched_label_page_text(label)
        matched_label_ocr_text = self._matched_label_ocr_text(label, image_refs=image_refs)
        has_structured_fields = bool(label and label.fields)
        has_matched_label_ocr = bool(matched_label_ocr_text)
        has_visual_label_input = image_refs["evidence_has_visual_label_input"]
        can_verify_label_content = has_matched_label_ocr or has_structured_fields or has_visual_label_input
        caption_text = label.caption_text if label and label.caption_text else (
            caption.text if caption else None
        )
        field_name = self._metadata_str(finding, "field_name") or self._metadata_str(finding, "matched_label_key")
        label_field = self._label_field(label, self._metadata_str(finding, "matched_label_key") or field_name)
        matched_caption_summary = self._matched_label_caption_summary(label=label, caption=caption)
        diagnostics = self._label_matching_diagnostics(
            label=label,
            caption=caption,
            caption_matches=caption_matches,
            matched_labels=matched_labels,
            unmatched_labels=unmatched_labels,
            image_refs=image_refs,
        )
        return {
            "label_caption_candidate": self._caption_summary(caption, finding=finding) if caption else None,
            "matching_label_caption_candidates": [
                self._caption_summary(caption, finding=finding) for caption in caption_candidates
            ],
            "matching_label_ocr_candidates": [self._label_summary(candidate) for candidate in matched_labels],
            "unmatched_label_ocr_candidates": [self._label_summary(candidate) for candidate in unmatched_labels],
            "matched_label_id": label.label_id if label else None,
            "matched_label_caption": matched_caption_summary,
            "matched_label_caption_text": caption_text,
            "label_page_number": image_refs["label_page_number"],
            "label_image_ref": image_refs["label_image_ref"],
            "label_page_image_ref": image_refs["label_page_image_ref"],
            "label_crop_ref": image_refs["label_crop_ref"],
            "label_crop_unavailable_reason": image_refs["crop_unavailable_reason"],
            "label_visual_input_ref": image_refs["visual_input_ref"],
            "matched_label_page_text": matched_label_page_text,
            "matched_label_ocr_text": matched_label_ocr_text,
            "matched_label_text": matched_label_ocr_text,
            "matched_label_fields": self._label_fields_summary(label) if label and has_structured_fields else {},
            "matched_label_field_confidence": label_field.confidence.value if label_field and label_field.confidence else None,
            "matched_label_ocr_source": self._matched_label_ocr_source(finding, label),
            "label_field_comparison": self._label_field_comparison(finding, report, label),
            "sample_description_row": self._component_summary(self._component_for_finding(finding, report), finding=finding)
            if self._component_for_finding(finding, report)
            else None,
            "expected_label_fields": self._expected_label_fields(self._component_for_finding(finding, report)),
            "evidence_has_matching_label_caption": bool(caption_candidates),
            "evidence_has_matched_label_image": image_refs["evidence_has_matched_label_image"],
            "evidence_has_matched_label_crop": image_refs["evidence_has_matched_label_crop"],
            "evidence_has_matched_label_ocr": has_matched_label_ocr,
            "evidence_has_visual_label_input": has_visual_label_input,
            "evidence_has_matched_label_image_crop": image_refs["evidence_has_matched_label_crop"],
            "evidence_has_matched_full_label_text": has_matched_label_ocr,
            "evidence_has_matched_structured_label_fields": has_structured_fields,
            "evidence_has_label_image_crop": image_refs["evidence_has_matched_label_crop"],
            "evidence_has_full_label_text": has_matched_label_ocr,
            "evidence_has_structured_label_fields": has_structured_fields,
            "evidence_can_verify_label_content": can_verify_label_content,
            "evidence_incomplete": not can_verify_label_content,
            "label_matching_diagnostics": diagnostics,
            "expected_codex_when_label_content_missing": "uncertain" if not can_verify_label_content else None,
            "expected_codex_when_label_not_found_but_caption_exists": (
                "refute"
                if finding.code == "SAMPLE_COMPONENT_LABEL_NOT_FOUND" and caption_candidates
                else None
            ),
        }

    def _label_image_reference_payload(
        self,
        *,
        label: LabelOCRResult | None,
        caption: PhotoCaption | None,
        finding: Finding | None = None,
        source_pdf_path: str | None = None,
    ) -> dict[str, Any]:
        page_number = label.page_number if label and label.page_number else caption.page_number if caption else None
        image_ref = self._relative_file_path(label.image_ref) if label and label.image_ref else None
        page_image_ref = (
            self._metadata_reference(label.metadata if label else {}, "page_image_ref")
            or self._metadata_reference(caption.metadata if caption else {}, "page_image_ref")
            or (f"report-page:{page_number}" if page_number is not None else None)
        )
        crop_ref = (
            self._metadata_reference(label.metadata if label else {}, "label_crop_ref")
            or self._metadata_reference(label.metadata if label else {}, "crop_ref")
            or self._metadata_reference(caption.metadata if caption else {}, "label_crop_ref")
            or self._metadata_reference(caption.metadata if caption else {}, "crop_ref")
            or image_ref
        )
        if crop_ref is None and caption and caption.bbox and page_number is not None:
            crop_ref = self._caption_bbox_crop_ref(page_number=page_number, caption=caption)

        render_source: str | None = None
        render_page_number: int | None = None
        render_bbox: list[float] | None = None
        visual_input_ref: str | None = None
        if source_pdf_path and page_number is not None and finding is not None:
            render_source = "source_pdf"
            render_page_number = page_number
            if caption and caption.bbox:
                render_bbox = [float(value) for value in caption.bbox]
                visual_input_ref = f"items/{self._safe_id(finding.id)}-label-crop.png"
                crop_ref = visual_input_ref
            else:
                visual_input_ref = f"items/{self._safe_id(finding.id)}-label-page.png"
            image_ref = visual_input_ref
            page_image_ref = visual_input_ref

        if crop_ref:
            crop_unavailable_reason = None
        elif caption and not caption.bbox:
            crop_unavailable_reason = "caption_bbox_missing"
        elif page_number is None:
            crop_unavailable_reason = "label_page_missing"
        else:
            crop_unavailable_reason = "label_crop_missing"

        return {
            "label_page_number": page_number,
            "label_image_ref": image_ref,
            "label_page_image_ref": page_image_ref,
            "label_crop_ref": crop_ref,
            "visual_input_ref": visual_input_ref,
            "render_source": render_source,
            "render_page_number": render_page_number,
            "render_bbox": render_bbox,
            "crop_unavailable_reason": crop_unavailable_reason,
            "evidence_has_matched_label_image": bool(image_ref or page_image_ref or crop_ref),
            "evidence_has_matched_label_crop": bool(crop_ref),
            "evidence_has_visual_label_input": bool(visual_input_ref),
        }

    def _caption_bbox_crop_ref(self, *, page_number: int, caption: PhotoCaption) -> str:
        bbox = ",".join(self._format_bbox_value(value) for value in caption.bbox or ())
        return f"report-page:{page_number}#caption={caption.caption_id}&bbox={bbox}"

    def _format_bbox_value(self, value: float) -> str:
        return str(int(value)) if float(value).is_integer() else f"{value:g}"

    def _metadata_reference(self, metadata: dict[str, Any], key: str) -> str | None:
        value = metadata.get(key)
        return self._relative_file_path(value) if isinstance(value, str) and value.strip() else None

    def _unmatched_label_ocr_candidates(
        self,
        report: ReportDocument | None,
        matched_labels: list[LabelOCRResult],
    ) -> list[LabelOCRResult]:
        if report is None or not report.labels:
            return []
        matched_ids = {label.label_id for label in matched_labels}
        return [
            label
            for label in report.labels
            if label.label_id not in matched_ids and is_chinese_label(label)
        ]

    def _matched_label_ocr_source(self, finding: Finding, label: LabelOCRResult | None) -> str:
        if label is None:
            return "missing"
        explicit_ids = {
            self._metadata_str(finding, "label_id"),
            self._metadata_str(finding, "label_key"),
            self._metadata_str(finding, "matched_label_key"),
        }
        return "explicit_label_id" if label.label_id in explicit_ids else "component_match"

    def _matched_label_page_text(self, label: LabelOCRResult | None) -> str | None:
        if label is None or not self._label_raw_text_is_page_text(label):
            return None
        return self._label_raw_text(label)

    def _matched_label_ocr_text(
        self,
        label: LabelOCRResult | None,
        *,
        image_refs: dict[str, Any],
    ) -> str | None:
        if label is None or self._label_raw_text_is_page_text(label):
            return None
        raw_text = self._label_raw_text(label)
        if not raw_text:
            return None
        if (
            image_refs["label_image_ref"]
            or image_refs["label_crop_ref"]
            or label.fields
            or (label.ocr_engine and label.ocr_engine != "pdf_text")
            or str(label.metadata.get("candidate_source") or "").lower()
            in {"label_crop_ocr", "label_image_ocr", "matched_label_ocr"}
        ):
            return raw_text
        return raw_text

    def _label_raw_text(self, label: LabelOCRResult | None) -> str | None:
        if label is None:
            return None
        text = "\n".join(block.strip() for block in label.raw_blocks if block and block.strip()).strip()
        return text or None

    def _label_raw_text_is_page_text(self, label: LabelOCRResult) -> bool:
        source = str(label.metadata.get("candidate_source") or "").strip().lower()
        if source in {"pdf_text_label_page", "page_text_label_page", "label_page_text", "caption_page_text"}:
            return True
        if label.ocr_engine == "pdf_text" and not (label.image_ref or self._metadata_reference(label.metadata, "crop_ref")):
            return True
        return False

    def _matched_label_caption_summary(
        self,
        *,
        label: LabelOCRResult | None,
        caption: PhotoCaption | None,
    ) -> dict[str, Any] | None:
        if caption is not None:
            return {
                "caption_id": caption.caption_id,
                "caption_text": caption.text,
                "subject_name": caption.subject_name,
                "caption_type": caption.caption_type,
                "page_number": caption.page_number,
                "matched_component_ids": caption.matched_component_ids,
                "metadata": caption.metadata,
            }
        if label is not None and label.caption_text:
            return {
                "caption_id": label.caption_id,
                "caption_text": label.caption_text,
                "subject_name": None,
                "caption_type": "label_ocr_caption",
                "page_number": label.page_number,
                "matched_component_ids": [],
                "metadata": label.metadata,
            }
        return None

    def _label_matching_diagnostics(
        self,
        *,
        label: LabelOCRResult | None,
        caption: PhotoCaption | None,
        caption_matches: list[_CaptionMatch],
        matched_labels: list[LabelOCRResult],
        unmatched_labels: list[LabelOCRResult],
        image_refs: dict[str, Any],
    ) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []
        if caption is not None:
            diagnostics.append({"code": "MATCHING_LABEL_CAPTION_FOUND", "caption_id": caption.caption_id})
        elif len(caption_matches) > 1 and caption_matches[0].score - caption_matches[1].score < 15:
            diagnostics.append(
                {
                    "code": "LABEL_CAPTION_MATCH_AMBIGUOUS",
                    "top_caption_ids": [match.caption.caption_id for match in caption_matches[:2]],
                    "top_scores": [match.score for match in caption_matches[:2]],
                }
            )
        elif caption_matches:
            diagnostics.append(
                {
                    "code": "LABEL_CAPTION_MATCH_BELOW_THRESHOLD",
                    "caption_id": caption_matches[0].caption.caption_id,
                    "score": caption_matches[0].score,
                }
            )
        if label is None:
            diagnostics.append({"code": "NO_MATCHED_LABEL_OCR"})
        elif not matched_labels:
            diagnostics.append({"code": "MATCHED_LABEL_FROM_EXPLICIT_REFERENCE", "label_id": label.label_id})
        if unmatched_labels:
            diagnostics.append(
                {
                    "code": "UNMATCHED_LABEL_OCR_CANDIDATES_PRESENT",
                    "label_ids": [candidate.label_id for candidate in unmatched_labels],
                }
            )
        if not image_refs["label_crop_ref"]:
            diagnostics.append(
                {
                    "code": "MATCHED_LABEL_CROP_UNAVAILABLE",
                    "reason": image_refs["crop_unavailable_reason"],
                }
            )
        return diagnostics

    def _label_field_comparison(
        self,
        finding: Finding,
        report: ReportDocument | None,
        label: LabelOCRResult | None,
    ) -> dict[str, Any]:
        field_name = self._metadata_str(finding, "field_name") or self._metadata_str(finding, "matched_label_key")
        component = self._component_for_finding(finding, report)
        label_field = self._label_field(label, self._metadata_str(finding, "matched_label_key") or field_name)
        sample_value = self._sample_component_field_value(component, field_name)
        label_value = self._field_value(label_field)
        if label is None:
            hint = "no_matched_label_ocr"
        elif label_field is None:
            hint = "field_missing_in_matched_label"
        elif sample_value is not None and label_value is not None and compact(sample_value) == compact(label_value):
            hint = "field_matches_sample_description"
        else:
            hint = "field_mismatch"
        return {
            "field_name": field_name,
            "matched_label_key": self._metadata_str(finding, "matched_label_key"),
            "sample_value": sample_value,
            "matched_label_value": label_value,
            "comparison_hint": hint,
        }

    def _caption_summary(self, caption: PhotoCaption, *, finding: Finding) -> dict[str, Any]:
        return {
            "caption_id": caption.caption_id,
            "caption_text": caption.text,
            "subject_name": caption.subject_name,
            "caption_type": caption.caption_type,
            "page_number": caption.page_number,
            "matched_component_ids": caption.matched_component_ids,
            "metadata": caption.metadata,
            "component_id": self._metadata_str(finding, "component_id"),
        }

    def _label_summary(self, label: LabelOCRResult) -> dict[str, Any]:
        refs = self._label_image_reference_payload(label=label, caption=None)
        matched_ocr_text = self._matched_label_ocr_text(label, image_refs=refs)
        page_text = self._matched_label_page_text(label)
        return {
            "label_id": label.label_id,
            "caption_text": label.caption_text,
            "caption_id": label.caption_id,
            "page_number": label.page_number,
            "label_image_ref": refs["label_image_ref"],
            "label_page_image_ref": refs["label_page_image_ref"],
            "label_crop_ref": refs["label_crop_ref"],
            "has_image_crop": refs["evidence_has_matched_label_crop"],
            "has_full_text": bool(matched_ocr_text),
            "has_page_text": bool(page_text),
            "has_structured_fields": bool(label.fields),
            "field_names": [field.name for field in label.fields],
        }

    def _label_fields_summary(self, label: LabelOCRResult) -> dict[str, Any]:
        return {
            field.name: {
                "value": field.value,
                "raw_value": field.raw_value,
                "confidence": field.confidence.value if field.confidence else None,
                "aliases": field.aliases,
            }
            for field in label.fields
        }

    def _expected_label_fields(self, component: SampleComponent | None) -> dict[str, Any]:
        if component is None:
            return {}
        return {
            "component_id": component.component_id,
            "component_name": component.component_name,
            "model": component.model,
            "batch_or_serial": component.batch_or_serial,
            "serial_number": component.batch_or_serial,
            "production_date": component.production_date,
            "expiration_date": component.expiration_date,
        }

    def _sample_component_field_value(self, component: SampleComponent | None, field_name: str | None) -> str | None:
        if component is None or not field_name:
            return None
        aliases = {
            "部件名称": component.component_name,
            "样品名称": component.component_name,
            "名称": component.component_name,
            "规格型号": component.model,
            "型号规格": component.model,
            "型号": component.model,
            "产品编号/批号": component.batch_or_serial,
            "序列号批号": component.batch_or_serial,
            "批号": component.batch_or_serial,
            "序列号": component.batch_or_serial,
            "生产日期": component.production_date,
            "失效日期": component.expiration_date,
            "有效期": component.expiration_date,
        }
        compact_field = compact(field_name)
        for key, value in aliases.items():
            if compact(key) == compact_field:
                return value
        return None

    def _is_unused_component(self, finding: Finding, component: SampleComponent | None) -> bool:
        if finding.metadata.get("is_unused_component") is True:
            return True
        if isinstance(finding.metadata.get("is_unused_component"), str):
            if str(finding.metadata["is_unused_component"]).strip().lower() in {"true", "1", "yes"}:
                return True
        return bool(component and component_not_used(component))

    def _unused_reason(self, finding: Finding, component: SampleComponent | None) -> str | None:
        reason = self._metadata_str(finding, "unused_reason")
        if reason:
            return reason
        if component and component_not_used(component):
            return component.remark
        return None

    def _inspection_group_pages_for_finding(
        self,
        finding: Finding,
        report: ReportDocument | None,
    ) -> list[int]:
        group = self._inspection_item_group_for_finding(finding, report)
        if group is not None and group.pages:
            return list(group.pages)
        raw_pages = finding.metadata.get("pages")
        if isinstance(raw_pages, list):
            pages: list[int] = []
            for value in raw_pages:
                if isinstance(value, int) and value > 0:
                    pages.append(value)
                elif isinstance(value, str) and value.isdigit() and int(value) > 0:
                    pages.append(int(value))
            return pages
        return []

    def _actual_conclusion_candidates(
        self,
        group: InspectionItemGroup,
        *,
        finding: Finding,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for item in group.rows:
            if item.conclusion is None or not str(item.conclusion).strip():
                continue
            candidates.append(
                {
                    "value": item.conclusion,
                    "normalized_value": compact(item.conclusion),
                    "page_number": item.source_page,
                    "row_index": item.row_index_in_page,
                    "sequence_raw": item.sequence_raw,
                    "field_provenance": item.field_provenance.get("conclusion"),
                }
            )
        if not candidates and (finding.actual or finding.metadata.get("actual_conclusion")):
            candidates.append(
                {
                    "value": finding.metadata.get("actual_conclusion") or finding.actual,
                    "normalized_value": compact(str(finding.metadata.get("actual_conclusion") or finding.actual or "")),
                    "page_number": self._page_number_for_finding(finding),
                    "row_index": None,
                    "sequence_raw": finding.metadata.get("item_no"),
                    "field_provenance": "finding_actual",
                }
            )
        return candidates

    def _conclusion_candidate_provenance(self, group: InspectionItemGroup) -> list[dict[str, Any]]:
        provenance: list[dict[str, Any]] = []
        for item in group.rows:
            if item.conclusion is None or not str(item.conclusion).strip():
                continue
            provenance.append(
                {
                    "page_number": item.source_page,
                    "row_index": item.row_index_in_page,
                    "sequence_raw": item.sequence_raw,
                    "source": item.field_provenance.get("conclusion") or "inspection_item.conclusion",
                    "raw_value": item.conclusion,
                }
            )
        return provenance

    def _is_complex_matrix_table(self, finding: Finding, report: ReportDocument | None) -> bool:
        if self._metadata_bool(finding, "complex_matrix_table"):
            return True
        group = self._inspection_item_group_for_finding(finding, report)
        return self._group_is_complex_matrix(group, finding) if group is not None else False

    def _complex_matrix_reason(self, finding: Finding, report: ReportDocument | None) -> str | None:
        reason = self._metadata_str(finding, "complex_matrix_reason")
        if reason:
            return reason
        group = self._inspection_item_group_for_finding(finding, report)
        if group is not None and self._group_is_complex_matrix(group, finding):
            return self._complex_matrix_reason_for_group(group)
        return None

    def _group_is_complex_matrix(self, group: InspectionItemGroup, finding: Finding) -> bool:
        if self._metadata_bool(finding, "complex_matrix_table"):
            return True
        if str(finding.metadata.get("normalized_item_no") or finding.metadata.get("item_no") or "").strip() == "59":
            return True
        if str(group.item_no or "").strip() == "59" or str(group.display_item_no or "").strip() == "59":
            return True
        for row in group.rows:
            value = row.metadata.get("complex_matrix_table") or row.metadata.get("is_complex_matrix_table")
            if value is True:
                return True
            if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}:
                return True
        return self._complex_matrix_reason_for_group(group) is not None

    def _complex_matrix_reason_for_group(self, group: InspectionItemGroup) -> str | None:
        if str(group.item_no or "").strip() == "59" or str(group.display_item_no or "").strip() == "59":
            return "item 59 复杂矩阵表需要专门矩阵审核，不按普通 C07 行级逻辑强判。"
        text = self._inspection_group_text_blob(group)
        compact_text = compact(text).lower()
        row_count = len(group.rows)
        page_count = len(group.pages)
        keyword_count = sum(
            1
            for keyword in (
                "矩阵",
                "漏电流",
                "电流",
                "ma",
                "μa",
                "ua",
                "正常状态",
                "单一故障",
                "直流",
                "交流",
            )
            if keyword.lower() in compact_text
        )
        has_measurement_limit = bool(re.search(r"[≤＜<]\s*\d+(?:\.\d+)?\s*(?:m?a|μa|ua)", compact_text))
        has_conflicting_conclusion = any(
            diagnostic.get("code") == "CONFLICTING_EFFECTIVE_CONCLUSION" for diagnostic in group.diagnostics
        )
        has_non_conclusion_candidate = any(
            row.conclusion
            and re.search(r"\d|≤|＜|<|mA|μA|uA|正常状态|单一故障", row.conclusion, re.IGNORECASE)
            for row in group.rows
        )
        if (
            row_count > 10
            and (page_count >= 3 or "续" in compact_text)
            and keyword_count >= 4
            and (has_measurement_limit or has_conflicting_conclusion or has_non_conclusion_candidate)
        ):
            return (
                "复杂矩阵表/漏电流多页表需要专门列映射复核；"
                f"row_count={row_count}, page_count={page_count}, matrix_keyword_count={keyword_count}"
            )
        return None

    def _inspection_group_text_blob(self, group: InspectionItemGroup) -> str:
        parts: list[str] = []
        for row in group.rows:
            parts.extend(
                str(value)
                for value in (
                    row.sequence_raw,
                    row.item_name,
                    row.standard_clause,
                    row.standard_requirement,
                    row.test_result,
                    row.conclusion,
                    row.remark,
                    row.metadata.get("row_text"),
                )
                if value
            )
            parts.extend(str(value) for value in row.result_values if value)
        return "\n".join(parts)

    def _inspection_page_text_excerpt(
        self,
        page_text: str,
        *,
        finding: Finding,
        report: ReportDocument | None,
    ) -> str:
        anchors = self._inspection_text_anchors(finding=finding, report=report)
        line_excerpt = self._inspection_page_line_excerpt(page_text, anchors=anchors, finding=finding)
        if line_excerpt:
            return line_excerpt

        compact_page = compact(page_text)
        start_indexes: list[int] = []
        for anchor in anchors:
            if not anchor:
                continue
            index = page_text.find(anchor)
            if index < 0:
                compact_index = compact_page.find(compact(anchor))
                if compact_index >= 0:
                    index = max(0, min(len(page_text), compact_index))
            if index >= 0:
                start_indexes.append(index)
        if not start_indexes:
            return self._truncate_for_evidence(page_text, limit=min(self.max_text_chars, 1200))

        start = max(0, min(start_indexes) - 240)
        end = min(len(page_text), max(start_indexes) + 760)
        excerpt = page_text[start:end].strip()
        if start > 0:
            excerpt = "[excerpt-start] " + excerpt
        if end < len(page_text):
            excerpt = excerpt + " [excerpt-end]"
        return self._truncate_for_evidence(excerpt, limit=min(self.max_text_chars, 1400))

    def _inspection_page_line_excerpt(
        self,
        page_text: str,
        *,
        anchors: list[str],
        finding: Finding,
    ) -> str | None:
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        if not lines:
            return None
        item_no = self._metadata_str(finding, "normalized_item_no") or self._metadata_str(finding, "item_no")
        start_index: int | None = None
        for index, line in enumerate(lines):
            compact_line = compact(line)
            if any(anchor and (anchor in line or compact(anchor) in compact_line) for anchor in anchors):
                start_index = index
                break
        if start_index is None:
            return None

        selected: list[str] = []
        for line in lines[start_index:]:
            line_has_new_item = bool(re.search(r"序号\s*\d+", line))
            line_has_current_item = bool(item_no and item_no in line)
            if selected and line_has_new_item and not line_has_current_item:
                break
            selected.append(line)
            if len(selected) >= 8:
                break
        return self._truncate_for_evidence("\n".join(selected), limit=min(self.max_text_chars, 1400))

    def _inspection_text_anchors(self, *, finding: Finding, report: ReportDocument | None) -> list[str]:
        anchors: list[str] = []
        for key in ("normalized_item_no", "item_no"):
            value = self._metadata_str(finding, key)
            if value and value not in anchors:
                anchors.append(value)

        group = self._inspection_item_group_for_finding(finding, report)
        if group is None:
            return anchors

        for row in group.rows:
            for value in (row.sequence_raw, row.standard_clause, row.item_name):
                if value and value not in anchors:
                    anchors.append(value)
        return anchors

    def _compact_finding_payload(self, finding: Finding) -> dict[str, Any]:
        return self._safe_payload(
            {
                "id": finding.id,
                "task_id": finding.task_id,
                "check_id": finding.check_id,
                "severity": finding.severity.value,
                "code": finding.code,
                "message": finding.message,
                "expected": finding.expected,
                "actual": finding.actual,
                "location": finding.location,
                "metadata": self._compact_c07_metadata(finding.metadata),
            }
        )

    def _compact_c07_result_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        groups = metadata.get("groups")
        compact_groups: list[dict[str, Any]] = []
        if isinstance(groups, list):
            for group in groups[:5]:
                if not isinstance(group, dict):
                    continue
                compact_groups.append(self._compact_c07_metadata(group))
        return self._safe_payload(
            {
                "groups": compact_groups,
                "group_builder_diagnostics": metadata.get("group_builder_diagnostics"),
                "ungrouped_row_count": metadata.get("ungrouped_row_count"),
            }
        )

    def _compact_c07_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        allowed_keys = (
            "item_no",
            "normalized_item_no",
            "display_item_no",
            "expected_conclusion",
            "actual_conclusion",
            "effective_test_results",
            "original_effective_test_results",
            "recovered_result_tokens",
            "recovered_effective_test_results",
            "result_token_recovery_applied",
            "result_token_recovery_confidence",
            "result_token_recovery_diagnostics",
            "result_summary",
            "reasoning_basis",
            "decision_reason",
            "pages",
            "continuation_markers",
            "suppressed_physical_row_count",
            "needs_codex_review",
            "complex_matrix_table",
            "complex_matrix_reason",
        )
        compact_metadata = {key: metadata.get(key) for key in allowed_keys if key in metadata}
        if "group_diagnostics" in metadata:
            compact_metadata["group_diagnostics"] = metadata["group_diagnostics"]
        return self._safe_payload(compact_metadata)

    def _truncate_for_evidence(self, value: str | None, *, limit: int) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if len(text) <= limit:
            return self._sanitize_text(text)
        return self._sanitize_text(f"{text[:limit]} [truncated]")

    def _field_value(self, field: ReportField | None) -> str | None:
        if field is None:
            return None
        return field.value if field.value is not None else field.raw_value

    def _confidence_value(self, field: ReportField | None, label: LabelOCRResult | None) -> str | None:
        confidence = field.confidence if field and field.confidence else label.confidence if label else None
        return confidence.value if confidence else None

    def _page_number_for_finding(self, finding: Finding) -> int | None:
        if finding.location and finding.location.page_number:
            return finding.location.page_number
        page_number = finding.metadata.get("page_number") or finding.metadata.get("source_page")
        if isinstance(page_number, int) and page_number > 0:
            return page_number
        if isinstance(page_number, str) and page_number.isdigit() and int(page_number) > 0:
            return int(page_number)
        return None

    def _metadata_str(self, finding: Finding, key: str) -> str | None:
        value = finding.metadata.get(key)
        return str(value) if value is not None and str(value) else None

    def _metadata_bool(self, finding: Finding, key: str) -> bool:
        value = finding.metadata.get(key)
        if value is True:
            return True
        if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}:
            return True
        return False

    def _relative_file_path(self, value: str | None) -> str | None:
        if not value:
            return None
        sanitized = self._sanitize_text(value)
        if sanitized != value:
            return None
        if value.startswith("~"):
            return None
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or any(part in {"", "."} for part in path.parts):
            return None
        return value

    def _safe_payload(self, value: Any) -> Any:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        if isinstance(value, dict):
            return {self._sanitize_text(str(key)): self._safe_payload(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._safe_payload(item) for item in value]
        if isinstance(value, tuple):
            return [self._safe_payload(item) for item in value]
        if isinstance(value, str):
            return self._sanitize_text(value)
        return value

    def _sanitize_text(self, value: str) -> str:
        sanitized = str(value)
        for exact in (OLD_PROJECT_ROOT, NEW_PROJECT_ROOT):
            sanitized = sanitized.replace(exact, REDACTED_PATH)
        sanitized = sanitized.replace("file://", REDACTED_PATH)
        sanitized = sanitized.replace("../", REDACTED_PATH)
        sanitized = sanitized.replace("..\\", REDACTED_PATH)
        sanitized = re.sub(r"/Users/[^\s\"'，,；;\)\]\}]+", REDACTED_PATH, sanitized)
        if len(sanitized) > self.max_text_chars:
            return f"{sanitized[: self.max_text_chars]} [truncated]"
        return sanitized

    def _safe_id(self, value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "report"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = ["ReportCodexAuditBundle", "ReportCodexEvidenceBuilder"]
