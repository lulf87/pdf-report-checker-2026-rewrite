from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domain.report import InspectionItem


class ContinuationMarker(BaseModel):
    raw_text: str
    normalized_item_no: str
    page_number: int | None = None
    row_index: int | None = None
    source_index: int


class InheritedField(BaseModel):
    field_name: str
    value: str
    source_row_index: int
    target_row_indexes: list[int] = Field(default_factory=list)
    reason: str


class InspectionItemGroup(BaseModel):
    item_no: str
    display_item_no: str | None = None
    rows: list[InspectionItem] = Field(default_factory=list)
    pages: list[int] = Field(default_factory=list)
    continuation_markers: list[ContinuationMarker] = Field(default_factory=list)
    effective_test_results: list[str] = Field(default_factory=list)
    original_effective_test_results: list[str] = Field(default_factory=list)
    recovered_result_tokens: list[str] = Field(default_factory=list)
    recovered_effective_test_results: list[str] = Field(default_factory=list)
    result_token_recovery_applied: bool = False
    result_token_recovery_diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    result_token_recovery_confidence: str | None = None
    effective_single_conclusion: str | None = None
    effective_remark: str | None = None
    inherited_merged_fields: list[InheritedField] = Field(default_factory=list)
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)


class InspectionItemGroupBuildResult(BaseModel):
    groups: list[InspectionItemGroup] = Field(default_factory=list)
    ungrouped_rows: list[InspectionItem] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "ContinuationMarker",
    "InheritedField",
    "InspectionItemGroup",
    "InspectionItemGroupBuildResult",
]
