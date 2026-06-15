from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceType(StrEnum):
    REPORT = "report"
    PTR = "ptr"
    SYSTEM = "system"


class EvidenceMethod(StrEnum):
    PDF_TEXT = "pdf_text"
    PDF_LAYOUT = "pdf_layout"
    OCR = "ocr"
    VLM = "vlm"
    LLM = "llm"
    MANUAL = "manual"
    SYSTEM = "system"


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

    @model_validator(mode="before")
    @classmethod
    def parse_tuple(cls, value: Any) -> Any:
        if isinstance(value, (tuple, list)) and len(value) == 4:
            return {"x0": value[0], "y0": value[1], "x1": value[2], "y1": value[3]}
        return value

    @model_validator(mode="after")
    def validate_order(self) -> "BoundingBox":
        if self.x1 < self.x0:
            raise ValueError("x1 must be greater than or equal to x0")
        if self.y1 < self.y0:
            raise ValueError("y1 must be greater than or equal to y0")
        return self

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return self.width * self.height


Rect = BoundingBox


class Location(BaseModel):
    source_id: str | None = None
    source_type: SourceType | None = None
    page_number: int | None = Field(default=None, gt=0)
    bbox: BoundingBox | None = None
    section: str | None = None
    table_id: str | None = None
    row_index: int | None = Field(default=None, ge=0)
    column_name: str | None = None
    text_span: tuple[int, int] | None = None
    description: str | None = None

    @classmethod
    def from_legacy_bbox(
        cls,
        bbox: Any,
        *,
        source_id: str | None = None,
        source_type: SourceType | None = None,
        **overrides: Any,
    ) -> "Location":
        """Adapt the old dataclass BoundingBox shape without keeping its API."""
        if isinstance(bbox, Mapping):
            x0 = bbox["x0"]
            y0 = bbox["y0"]
            x1 = bbox["x1"]
            y1 = bbox["y1"]
            page_number = bbox.get("page") or bbox.get("page_number")
        else:
            x0 = getattr(bbox, "x0")
            y0 = getattr(bbox, "y0")
            x1 = getattr(bbox, "x1")
            y1 = getattr(bbox, "y1")
            page_number = getattr(bbox, "page", None) or getattr(bbox, "page_number", None)

        values = {
            "source_id": source_id,
            "source_type": source_type,
            "page_number": page_number,
            "bbox": BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
        }
        values.update(overrides)
        return cls(**values)

    @model_validator(mode="after")
    def validate_text_span_order(self) -> "Location":
        if self.text_span is not None:
            start, end = self.text_span
            if start < 0 or end < 0:
                raise ValueError("text_span values must be greater than or equal to 0")
            if end < start:
                raise ValueError("text_span end must be greater than or equal to start")
        return self


class Evidence(BaseModel):
    id: str
    source_type: SourceType
    location: Location | None = None
    raw_text: str | None = None
    normalized_text: str | None = None
    value: str | None = None
    method: EvidenceMethod | None = None
    confidence: Confidence | None = None
    image_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
