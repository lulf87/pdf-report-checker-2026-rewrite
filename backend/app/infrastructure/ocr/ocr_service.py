from __future__ import annotations

from pathlib import Path
from typing import Any

from app.domain.common import Confidence
from app.domain.report import LabelOCRResult
from app.infrastructure.ocr.caption_extractor import CaptionExtractor
from app.infrastructure.ocr.label_field_extractor import LabelFieldExtractor
from app.infrastructure.ocr.ocr_parser import OCRParser


class OCRService:
    def __init__(
        self,
        *,
        engine: Any | None = None,
        language: str = "ch",
        use_angle_cls: bool = True,
        low_confidence_threshold: float = 0.6,
    ) -> None:
        self.engine = engine
        self.language = language
        self.use_angle_cls = use_angle_cls
        self.low_confidence_threshold = low_confidence_threshold
        self.parser = OCRParser(language=language, use_angle_cls=use_angle_cls, low_confidence_threshold=low_confidence_threshold)
        self.field_extractor = LabelFieldExtractor()
        self.caption_extractor = CaptionExtractor()

    def process_image(
        self,
        image_path: str | Path,
        *,
        extract_fields: bool = True,
        page_number: int | None = None,
        caption_text: str | None = None,
        label_id: str | None = None,
        fallback_text: str | None = None,
    ) -> LabelOCRResult:
        diagnostics: list[str] = []
        raw_text = ""
        confidence_value = 0.0
        raw_blocks: list[str] = []

        raw_result = None
        if self.engine is not None:
            raw_result = self.engine.ocr(str(image_path), cls=self.use_angle_cls)
            parsed = self.parser.parse_raw_result(raw_result, page_number=page_number or 1)
            raw_text = parsed.text
            raw_blocks = [block.text for block in parsed.blocks]
            confidence_value = parsed.confidence
            diagnostics.extend(parsed.diagnostics)

        if not raw_text.strip() and fallback_text:
            raw_text = fallback_text
            raw_blocks = [line.strip() for line in fallback_text.splitlines() if line.strip()]
            confidence_value = max(confidence_value, 0.75)
            diagnostics.append("OCR returned no usable text; fallback text used")

        fields = self.field_extractor.extract_fields(raw_text) if extract_fields else []
        confidence = self._confidence_enum(confidence_value)
        caption = self.caption_extractor.parse(caption_text or "")

        return LabelOCRResult(
            label_id=label_id or f"label-page-{page_number or 0}",
            page_number=page_number,
            caption_text=caption_text,
            fields=fields,
            raw_blocks=raw_blocks,
            language=self.language,
            ocr_engine=type(self.engine).__name__ if self.engine is not None else None,
            confidence=confidence,
            metadata={
                "numeric_confidence": confidence_value,
                "diagnostics": diagnostics,
                "ocr_engine": type(self.engine).__name__ if self.engine is not None else None,
                "caption": caption.model_dump(mode="json"),
                "raw_ocr_data": raw_result,
            },
        )

    def _confidence_enum(self, value: float) -> Confidence:
        if value >= 0.85:
            return Confidence.HIGH
        if value >= self.low_confidence_threshold:
            return Confidence.MEDIUM
        return Confidence.LOW


def extract_label_fields(image_path: str | Path) -> dict[str, str]:
    result = OCRService().process_image(image_path)
    return {field.name: field.value or "" for field in result.fields}
