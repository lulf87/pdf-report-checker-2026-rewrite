from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.domain.common import BoundingBox

SPECIAL_SYMBOL_CORRECTIONS = [
    (r"\+/-", "±", "plus-minus variations"),
    (r"<=|＜=", "≤", "less than or equal"),
    (r">=|＞=", "≥", "greater than or equal"),
    (r"(?<=\d)\s*Q\b", "Ω", "omega symbol"),
    (r"(?<=\d)\s*u(?=[AFsgm]|$)", "μ", "mu symbol"),
    (r"o\s*C|O\s*C|0\s*C", "℃", "degree celsius"),
]
WARNING_SYMBOLS = ["Ω", "±", "℃", "²", "³", "μ", "≤", "≥"]


@dataclass(frozen=True)
class OCRWarning:
    position: int
    original: str
    corrected: str
    symbol: str
    context: str = ""

    def __str__(self) -> str:
        return f"[WARNING] Position {self.position}: '{self.original}' -> '{self.corrected}' (symbol: {self.symbol})"


@dataclass
class OCRTextBlock:
    text: str
    bbox: BoundingBox | None = None
    confidence: float = 0.0
    page_number: int | None = None


@dataclass
class OCRParseResult:
    text: str = ""
    blocks: list[OCRTextBlock] = field(default_factory=list)
    warnings: list[OCRWarning] = field(default_factory=list)
    confidence: float = 0.0
    raw_ocr_data: Any = None
    field_candidates: dict[str, str] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)

    def has_warnings(self) -> bool:
        return bool(self.warnings)


class OCRParser:
    def __init__(self, language: str = "ch", use_angle_cls: bool = True, low_confidence_threshold: float = 0.6) -> None:
        self.language = language
        self.use_angle_cls = use_angle_cls
        self.low_confidence_threshold = low_confidence_threshold
        self._ocr_engine: Any = None

    def parse_raw_result(self, raw_result: Any, *, page_number: int = 1) -> OCRParseResult:
        result = OCRParseResult(raw_ocr_data=raw_result or [])
        lines = raw_result[0] if raw_result and isinstance(raw_result, list) and raw_result else []
        text_parts: list[str] = []
        confidences: list[float] = []

        for line in lines or []:
            if not line or len(line) < 2:
                continue
            points, text_info = line[0], line[1]
            if not text_info:
                continue
            text = str(text_info[0] or "").strip()
            if not text:
                continue
            confidence = float(text_info[1] if len(text_info) > 1 else 0.0)
            block = OCRTextBlock(
                text=text,
                bbox=self._bbox_from_points(points, page_number=page_number),
                confidence=confidence,
                page_number=page_number,
            )
            result.blocks.append(block)
            text_parts.append(text)
            confidences.append(confidence)
            if confidence < self.low_confidence_threshold:
                result.diagnostics.append(f"low confidence OCR block on page {page_number}: {confidence:.2f}")

        corrected, warnings = correct_text_symbols("\n".join(text_parts))
        result.text = corrected
        result.warnings = warnings
        result.confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

        from app.infrastructure.ocr.label_field_extractor import LabelFieldExtractor

        result.field_candidates = LabelFieldExtractor().extract_as_dict(result.text)
        return result

    def _bbox_from_points(self, points: Any, *, page_number: int) -> BoundingBox | None:
        try:
            x_values = [float(point[0]) for point in points]
            y_values = [float(point[1]) for point in points]
        except (TypeError, ValueError, IndexError):
            return None
        return BoundingBox(x0=min(x_values), y0=min(y_values), x1=max(x_values), y1=max(y_values))


def correct_text_symbols(text: str | None, output_warnings: bool = True) -> tuple[str, list[OCRWarning]]:
    if not text:
        return "", []
    corrected = str(text)
    warnings: list[OCRWarning] = []
    for pattern, replacement, _description in SPECIAL_SYMBOL_CORRECTIONS:
        for match in list(re.finditer(pattern, corrected)):
            original = match.group(0)
            rendered = match.expand(replacement)
            symbol = next((item for item in WARNING_SYMBOLS if item in rendered), rendered)
            if output_warnings and symbol in WARNING_SYMBOLS:
                start = max(0, match.start() - 20)
                end = min(len(corrected), match.end() + 20)
                warnings.append(
                    OCRWarning(
                        position=match.start(),
                        original=original,
                        corrected=rendered,
                        symbol=symbol,
                        context=corrected[start:end].strip(),
                    )
                )
        corrected = re.sub(pattern, replacement, corrected)
    return corrected, warnings if output_warnings else []


def parse_with_ocr(image_path: str | Path, language: str = "ch") -> OCRParseResult:
    raise RuntimeError("Live OCR engine invocation is provided by OCRService with an injected engine.")
