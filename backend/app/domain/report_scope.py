from __future__ import annotations

from pydantic import BaseModel, Field


class ReportScopeRange(BaseModel):
    start: str
    end: str
    source_text: str


class ExternalStandardRange(BaseModel):
    start_item_no: str
    end_item_no: str
    standard: str
    source_page: int | None = Field(default=None, gt=0)
    source_text: str


class ReportInspectionScope(BaseModel):
    declared_scope_items: list[str] = Field(default_factory=list)
    declared_scope_ranges: list[ReportScopeRange] = Field(default_factory=list)
    excluded_topics: list[str] = Field(default_factory=list)
    source_page: int | None = Field(default=None, gt=0)
    source_text: str | None = None
    external_standard_ranges: list[ExternalStandardRange] = Field(default_factory=list)
    ptr_direct_content_starts_after: str | None = None


__all__ = [
    "ExternalStandardRange",
    "ReportInspectionScope",
    "ReportScopeRange",
]
