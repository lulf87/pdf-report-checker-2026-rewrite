"""OCR adapters live here."""

from app.infrastructure.ocr.caption_extractor import CaptionExtractor, CaptionInfo
from app.infrastructure.ocr.label_field_extractor import LabelFieldExtractor
from app.infrastructure.ocr.ocr_parser import OCRParser, OCRParseResult, OCRTextBlock, OCRWarning
from app.infrastructure.ocr.ocr_service import OCRService

__all__ = [
    "CaptionExtractor",
    "CaptionInfo",
    "LabelFieldExtractor",
    "OCRParser",
    "OCRParseResult",
    "OCRService",
    "OCRTextBlock",
    "OCRWarning",
]
