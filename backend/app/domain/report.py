from typing import Any

from pydantic import BaseModel, Field, computed_field, model_validator

from app.domain.common import Confidence, Evidence, Location
from app.domain.pdf import ParsedPdf


class ReportField(BaseModel):
    name: str
    raw_value: str | None = None
    value: str | None = None
    normalized_value: str | None = None
    location: Location | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence | None = None
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FirstPageInfo(BaseModel):
    client: ReportField | None = None
    sample_name: ReportField | None = None
    model_spec: ReportField | None = None
    report_number: ReportField | None = None
    sample_number: ReportField | None = None
    fields: list[ReportField] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class ThirdPageInfo(BaseModel):
    model_spec: ReportField | None = None
    production_date: ReportField | None = None
    batch_or_serial: ReportField | None = None
    client: ReportField | None = None
    client_address: ReportField | None = None
    fields: list[ReportField] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class ComponentKey(BaseModel):
    name: str | None = None
    model: str | None = None
    batch_or_serial: str | None = None

    @computed_field
    @property
    def identity(self) -> str:
        parts = [self.name or "", self.model or "", self.batch_or_serial or ""]
        return "|".join(parts)


class SampleDescriptionRow(BaseModel):
    row_id: str
    sequence_raw: str | None = None
    sequence: int | None = None
    component_key: ComponentKey | None = None
    component_name: ReportField | None = None
    model: ReportField | None = None
    batch_or_serial: ReportField | None = None
    production_date: ReportField | None = None
    expiration_date: ReportField | None = None
    remark: ReportField | None = None
    row_location: Location | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InspectionItem(BaseModel):
    sequence_raw: str | None = None
    sequence: int | None = None
    is_continuation: bool = False
    item_name: str | None = None
    standard_clause: str | None = None
    standard_requirement: str | None = None
    test_result: str | None = None
    result_values: list[str] = Field(default_factory=list)
    conclusion: str | None = None
    remark: str | None = None
    source_page: int | None = Field(default=None, gt=0)
    row_index_in_page: int | None = Field(default=None, ge=0)
    field_provenance: dict[str, str] = Field(default_factory=dict)
    row_location: Location | None = None
    page_span: tuple[int, int] | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InspectionTable(BaseModel):
    table_id: str
    items: list[InspectionItem] = Field(default_factory=list)
    page_span: tuple[int, int] | None = None
    header_fields: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class SampleComponent(BaseModel):
    component_id: str
    component_name: str | None = None
    model: str | None = None
    batch_or_serial: str | None = None
    production_date: str | None = None
    expiration_date: str | None = None
    remark: str | None = None
    identity_key: str | None = None
    row_location: Location | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def populate_identity_key(self) -> "SampleComponent":
        if self.identity_key:
            return self

        parts = [
            self.component_name,
            self.model,
            self.batch_or_serial,
            self.production_date,
            self.expiration_date,
        ]
        non_empty_parts = [part.strip() for part in parts if part and part.strip()]
        self.identity_key = "|".join(non_empty_parts) if non_empty_parts else self.component_id
        return self


class PhotoCaption(BaseModel):
    caption_id: str
    text: str
    subject_name: str | None = None
    caption_type: str | None = None
    page_number: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    matched_component_ids: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PhotoEvidence(BaseModel):
    photo_id: str
    caption_text: str | None = None
    subject_name: str | None = None
    caption_type: str | None = None
    page_number: int | None = None
    location: Location | None = None
    image_ref: str | None = None
    matched_component_keys: list[ComponentKey] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LabelOCRField(ReportField):
    pass


class LabelOCRResult(BaseModel):
    label_id: str
    page_number: int | None = None
    caption_id: str | None = None
    caption_text: str | None = None
    fields: list[LabelOCRField] = Field(default_factory=list)
    raw_blocks: list[str] = Field(default_factory=list)
    language: str | None = None
    ocr_engine: str | None = None
    confidence: Confidence | None = None
    image_ref: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


LabelOCR = LabelOCRResult


class PageNumberEvidence(BaseModel):
    page_number: int
    displayed_number: str | None = None
    parsed_number: int | None = None
    total_pages: int | None = None
    location: Location | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportDocument(BaseModel):
    parsed_pdf: ParsedPdf | None = None
    first_page: FirstPageInfo | None = None
    third_page: ThirdPageInfo | None = None
    fields: list[ReportField] = Field(default_factory=list)
    inspection_table: InspectionTable | None = None
    inspection_items: list[InspectionItem] = Field(default_factory=list)
    sample_description_rows: list[SampleDescriptionRow] = Field(default_factory=list)
    sample_components: list[SampleComponent] = Field(default_factory=list)
    photo_captions: list[PhotoCaption] = Field(default_factory=list)
    photo_evidence: list[PhotoEvidence] = Field(default_factory=list)
    labels: list[LabelOCR] = Field(default_factory=list)
    page_numbers: list[PageNumberEvidence] = Field(default_factory=list)
    page_map: dict[str, int] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
