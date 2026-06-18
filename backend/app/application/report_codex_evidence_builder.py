from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

from pydantic import BaseModel

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
from app.domain.pdf import ParsedPdf
from app.domain.report import InspectionItem, LabelOCRResult, PhotoCaption, ReportDocument, ReportField, SampleComponent
from app.domain.result import CheckResult


OLD_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"
REDACTED_PATH = "[redacted-path]"

REVIEWABLE_TARGET_TYPES = {
    "C02": CodexReviewTargetType.LABEL_OCR,
    "C03": CodexReviewTargetType.LABEL_OCR,
    "C04": CodexReviewTargetType.SAMPLE_DESCRIPTION,
    "C05": CodexReviewTargetType.PHOTO_CAPTION,
    "C06": CodexReviewTargetType.LABEL_OCR,
    "C07": CodexReviewTargetType.INSPECTION_ITEM,
}

RULE_CONTEXT_SUMMARY = {
    "C02": "第三页扩展字段与中文标签 OCR 字段的规则初判上下文。",
    "C03": "第三页生产日期与中文标签生产日期格式的规则初判上下文。",
    "C04": "样品描述表格字段与中文标签 OCR 字段的规则初判上下文。",
    "C05": "样品描述部件与照片 caption 覆盖关系的规则初判上下文。",
    "C06": "样品描述部件与中文标签 caption/OCR 覆盖关系的规则初判上下文。",
    "C07": "根据检验结果推导期望单项结论的规则初判上下文。",
}


@dataclass(frozen=True)
class ReportCodexAuditBundle:
    request: CodexReviewRequest
    evidence_package: EvidencePackage


class ReportCodexEvidenceBuilder:
    """Build minimal report self-check evidence packages for controlled Codex review."""

    def __init__(self, *, max_text_chars: int = 1200) -> None:
        if max_text_chars <= 0:
            raise ValueError("max_text_chars must be greater than zero")
        self.max_text_chars = max_text_chars

    def build(
        self,
        *,
        task_id: str,
        task_type: str,
        result: CheckResult,
        report: ReportDocument | None = None,
        parsed_pdf: ParsedPdf | None = None,
    ) -> ReportCodexAuditBundle | None:
        findings = [finding for finding in result.findings if finding.check_id in REVIEWABLE_TARGET_TYPES]
        if not findings:
            return None

        items_by_ref: dict[str, EvidenceItem] = {}
        targets: list[EvidenceTarget] = []
        review_targets: list[CodexReviewTarget] = []

        for finding in findings:
            target_type = REVIEWABLE_TARGET_TYPES[finding.check_id]
            evidence_refs = self._evidence_refs_for_finding(
                finding,
                result=result,
                report=report,
                parsed_pdf=parsed_pdf,
                items_by_ref=items_by_ref,
            )
            target_id = f"report-codex-target-{finding.id}"
            metadata = self._target_metadata(finding)
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
            package_id=f"codex-report-{task_id}-{self._safe_id(result.check_id)}",
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
            },
        )
        request = CodexReviewRequest(
            request_id=f"codex-request-{task_id}-report-{self._safe_id(result.check_id)}",
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
            },
        )
        return ReportCodexAuditBundle(request=request, evidence_package=package)

    def _evidence_refs_for_finding(
        self,
        finding: Finding,
        *,
        result: CheckResult,
        report: ReportDocument | None,
        parsed_pdf: ParsedPdf | None,
        items_by_ref: dict[str, EvidenceItem],
    ) -> list[str]:
        refs: list[str] = []
        self._add_item(items_by_ref, self._finding_item(finding), refs)
        self._add_item(items_by_ref, self._rule_context_item(finding, result), refs)

        if finding.check_id in {"C02", "C03"}:
            self._add_optional_item(items_by_ref, self._report_field_item(finding, report), refs)
            self._add_optional_item(items_by_ref, self._label_ocr_item(finding, report), refs)
        elif finding.check_id == "C04":
            self._add_optional_item(items_by_ref, self._sample_description_item(finding, report), refs)
            self._add_optional_item(items_by_ref, self._label_ocr_item(finding, report), refs)
        elif finding.check_id == "C05":
            self._add_optional_item(items_by_ref, self._component_item(finding, report), refs)
            self._add_optional_item(items_by_ref, self._photo_caption_item(finding, report), refs)
        elif finding.check_id == "C06":
            self._add_optional_item(items_by_ref, self._component_item(finding, report), refs)
            self._add_optional_item(items_by_ref, self._label_ocr_item(finding, report), refs)
            self._add_optional_item(items_by_ref, self._label_caption_item(finding, report), refs)
        elif finding.check_id == "C07":
            self._add_optional_item(items_by_ref, self._inspection_item(finding, report), refs)

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
        return EvidenceItem(
            ref_id=f"finding:{finding.id}",
            source_type=EvidenceSourceType.FINDING,
            title=self._sanitize_text(finding.message),
            structured=self._safe_payload(finding),
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

    def _rule_context_item(self, finding: Finding, result: CheckResult) -> EvidenceItem:
        return EvidenceItem(
            ref_id=f"rule_context:{finding.id}",
            source_type=EvidenceSourceType.RULE_CONTEXT,
            title=f"{finding.check_id} deterministic rule context",
            text=self._sanitize_text(RULE_CONTEXT_SUMMARY.get(finding.check_id, "报告自检规则初判上下文。")),
            structured=self._safe_payload(
                {
                    "check_id": finding.check_id,
                    "check_name": result.check_name,
                    "finding_id": finding.id,
                    "code": finding.code,
                    "severity": finding.severity.value,
                    "message": finding.message,
                    "expected": finding.expected,
                    "actual": finding.actual,
                    "finding_metadata": finding.metadata,
                    "result_metadata": result.metadata,
                    "audit_reason": "review deterministic report self-check candidate finding against focused evidence",
                    "evidence_incomplete": False,
                }
            ),
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

    def _label_ocr_item(self, finding: Finding, report: ReportDocument | None) -> EvidenceItem | None:
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

    def _inspection_item(self, finding: Finding, report: ReportDocument | None) -> EvidenceItem | None:
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

    def _target_metadata(self, finding: Finding) -> dict[str, Any]:
        return self._safe_payload(
            {
                "source": "report_codex_evidence_builder",
                "rule_id": finding.check_id,
                "severity": finding.severity.value,
                "expected": finding.expected,
                "actual": finding.actual,
                "page_number": self._page_number_for_finding(finding),
                "finding_code": finding.code,
                "evidence_incomplete": False,
                "finding_metadata": finding.metadata,
            }
        )

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
        label_id = self._metadata_str(finding, "label_id") or self._metadata_str(finding, "matched_label_key")
        if label_id:
            for label in report.labels:
                if label.label_id == label_id:
                    return label
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

    def _inspection_item_for_finding(self, finding: Finding, report: ReportDocument | None) -> InspectionItem | None:
        if report is None or not report.inspection_items:
            return None
        item_no = self._metadata_str(finding, "normalized_item_no") or self._metadata_str(finding, "item_no")
        if item_no:
            for item in report.inspection_items:
                if str(item.sequence or item.sequence_raw or "") == item_no:
                    return item
        return report.inspection_items[0]

    def _component_summary(self, component: SampleComponent, *, finding: Finding) -> dict[str, Any]:
        return {
            "component_id": component.component_id,
            "component_name": component.component_name,
            "model": component.model,
            "batch_or_serial": component.batch_or_serial,
            "production_date": component.production_date,
            "expiration_date": component.expiration_date,
            "remark": component.remark,
            "identity_key": component.identity_key,
            "expected": finding.expected,
            "actual": finding.actual,
            "finding_metadata": finding.metadata,
        }

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
