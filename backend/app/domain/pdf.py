from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.domain.common import BoundingBox


class PdfWord(BaseModel):
    text: str
    bbox: BoundingBox | None = None
    block_index: int | None = None
    line_index: int | None = None
    word_index: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_tuple_bbox(cls, value: Any) -> Any:
        if isinstance(value, dict) and isinstance(value.get("bbox"), (tuple, list)):
            data = dict(value)
            data["bbox"] = BoundingBox.model_validate(data["bbox"])
            return data
        return value


class PdfTextBlock(BaseModel):
    text: str
    bbox: BoundingBox | None = None
    page_number: int | None = Field(default=None, gt=0)
    font_size: float | None = None
    font_name: str | None = None
    is_bold: bool = False
    block_index: int | None = None
    line_index: int | None = None
    span_index: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_tuple_bbox(cls, value: Any) -> Any:
        if isinstance(value, dict) and isinstance(value.get("bbox"), (tuple, list)):
            data = dict(value)
            data["bbox"] = BoundingBox.model_validate(data["bbox"])
            return data
        return value

    def is_empty(self) -> bool:
        return not self.text.strip()


class PdfTable(BaseModel):
    table_id: str
    page_numbers: list[int] = Field(default_factory=list)
    title: str | None = None
    caption: str | None = None
    bbox: BoundingBox | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    continuation_of: str | None = None
    extraction_method: str = "pymupdf"
    confidence: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_tuple_bbox(cls, value: Any) -> Any:
        if isinstance(value, dict) and isinstance(value.get("bbox"), (tuple, list)):
            data = dict(value)
            data["bbox"] = BoundingBox.model_validate(data["bbox"])
            return data
        return value


class PdfPage(BaseModel):
    page_number: int
    width: float | None = None
    height: float | None = None
    text: str = ""
    text_blocks: list[PdfTextBlock] = Field(default_factory=list)
    words: list[PdfWord] = Field(default_factory=list)
    tables: list[PdfTable] = Field(default_factory=list)
    images: list[dict[str, Any]] = Field(default_factory=list)
    drawings: list[dict[str, Any]] = Field(default_factory=list)
    is_textless: bool = False
    render_ref: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


class ParsedPdf(BaseModel):
    file_id: str
    file_name: str
    page_count: int = 0
    pages: list[PdfPage] = Field(default_factory=list)
    tables: list[PdfTable] = Field(default_factory=list)
    text_digest: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
