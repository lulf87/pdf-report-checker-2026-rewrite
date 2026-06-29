from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.finding import Finding
from app.domain.table import CanonicalTable


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidencePackageKind(StrEnum):
    PTR_CLAUSE_REVIEW = "ptr_clause_review"
    PTR_TABLE_REVIEW = "ptr_table_review"
    PTR_PARAMETER_REVIEW = "ptr_parameter_review"
    REPORT_RULE_REVIEW = "report_rule_review"
    LABEL_OCR_REVIEW = "label_ocr_review"
    PHOTO_CAPTION_REVIEW = "photo_caption_review"
    INSPECTION_ITEM_REVIEW = "inspection_item_review"
    SAMPLE_DESCRIPTION_REVIEW = "sample_description_review"


class EvidenceSourceType(StrEnum):
    PDF_TEXT = "pdf_text"
    OCR_TEXT = "ocr_text"
    IMAGE = "image"
    TABLE = "table"
    CANONICAL_TABLE = "canonical_table"
    PTR_CLAUSE = "ptr_clause"
    REPORT_FIELD = "report_field"
    FINDING = "finding"
    IMAGE_CAPTION = "image_caption"
    LABEL_OCR = "label_ocr"
    PAGE_TEXT = "page_text"
    RULE_CONTEXT = "rule_context"
    METADATA = "metadata"


class EvidenceItem(BaseModel):
    ref_id: str
    source_type: EvidenceSourceType
    title: str | None = None
    text: str | None = None
    structured: dict[str, Any] | None = None
    file_path: str | None = None
    page_number: int | None = Field(default=None, gt=0)
    section: str | None = None
    location: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("file_path")
    @classmethod
    def validate_relative_file_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        path = PurePosixPath(value)
        if path.is_absolute():
            raise ValueError("file_path must be a relative evidence workspace path")
        if ".." in path.parts:
            raise ValueError("file_path must not contain path traversal")
        if not path.parts or any(part in {"", "."} for part in path.parts):
            raise ValueError("file_path must be a normalized relative path")
        return value


class EvidenceTarget(BaseModel):
    target_id: str
    target_type: str
    check_id: str | None = None
    finding_id: str | None = None
    finding_code: str | None = None
    summary: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidencePackage(BaseModel):
    package_id: str
    task_id: str
    task_type: str
    kind: EvidencePackageKind
    schema_version: str
    created_at: datetime = Field(default_factory=_utc_now)
    targets: list[EvidenceTarget]
    items: list[EvidenceItem]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_package_references(self) -> "EvidencePackage":
        if not self.targets:
            raise ValueError("evidence package must contain at least one target")
        if not self.items:
            raise ValueError("evidence package must contain at least one evidence item")

        item_ref_ids = [item.ref_id for item in self.items]
        duplicate_item_refs = {ref_id for ref_id in item_ref_ids if item_ref_ids.count(ref_id) > 1}
        if duplicate_item_refs:
            duplicate_list = ", ".join(sorted(duplicate_item_refs))
            raise ValueError(f"evidence package contains duplicate evidence ref_id: {duplicate_list}")

        target_ids = [target.target_id for target in self.targets]
        duplicate_target_ids = {target_id for target_id in target_ids if target_ids.count(target_id) > 1}
        if duplicate_target_ids:
            duplicate_list = ", ".join(sorted(duplicate_target_ids))
            raise ValueError(f"evidence package contains duplicate target_id: {duplicate_list}")

        known_refs = set(item_ref_ids)
        for target in self.targets:
            for ref_id in target.evidence_refs:
                if ref_id not in known_refs:
                    raise ValueError(f"target {target.target_id} references unknown evidence ref: {ref_id}")
        return self


class EvidencePackageManifest(BaseModel):
    package_id: str
    task_id: str
    root_dir: str
    package_json_path: str
    item_file_paths: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


def evidence_item_from_finding(finding: Finding) -> EvidenceItem:
    return EvidenceItem(
        ref_id=finding.id,
        source_type=EvidenceSourceType.FINDING,
        title=finding.message,
        structured=finding.model_dump(mode="json"),
        page_number=finding.location.page_number if finding.location else None,
        section=finding.location.section if finding.location else None,
        location=finding.location.model_dump(mode="json") if finding.location else None,
        metadata={
            "finding_id": finding.id,
            "check_id": finding.check_id,
            "finding_code": finding.code,
            "severity": finding.severity.value,
        },
    )


def evidence_item_from_canonical_table(table: CanonicalTable) -> EvidenceItem:
    return EvidenceItem(
        ref_id=f"canonical-table-{table.table_id}",
        source_type=EvidenceSourceType.CANONICAL_TABLE,
        title=table.caption,
        structured=table.model_dump(mode="json"),
        page_number=table.page_start,
        section="canonical_table",
        metadata={
            "table_id": table.table_id,
            "table_number": table.table_number,
            "page_start": table.page_start,
            "page_end": table.page_end,
        },
    )


def evidence_item_from_text(
    *,
    ref_id: str,
    source_type: EvidenceSourceType,
    text: str,
    title: str | None = None,
    page_number: int | None = None,
    section: str | None = None,
    location: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        ref_id=ref_id,
        source_type=source_type,
        title=title,
        text=text,
        page_number=page_number,
        section=section,
        location=location,
        metadata=metadata or {},
    )


def evidence_item_from_structured(
    *,
    ref_id: str,
    source_type: EvidenceSourceType,
    structured: BaseModel | dict[str, Any],
    title: str | None = None,
    page_number: int | None = None,
    section: str | None = None,
    location: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> EvidenceItem:
    payload = structured.model_dump(mode="json") if isinstance(structured, BaseModel) else structured
    return EvidenceItem(
        ref_id=ref_id,
        source_type=source_type,
        title=title,
        structured=payload,
        page_number=page_number,
        section=section,
        location=location,
        metadata=metadata or {},
    )


__all__ = [
    "EvidenceItem",
    "EvidencePackage",
    "EvidencePackageKind",
    "EvidencePackageManifest",
    "EvidenceSourceType",
    "EvidenceTarget",
    "evidence_item_from_canonical_table",
    "evidence_item_from_finding",
    "evidence_item_from_structured",
    "evidence_item_from_text",
]
