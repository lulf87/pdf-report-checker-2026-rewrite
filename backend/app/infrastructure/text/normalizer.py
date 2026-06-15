"""Reusable text normalization for extraction and comparison.

The strict normalizer prepares PDF/OCR text for deterministic comparison.
The display normalizer keeps the raw text readable and does not apply symbol
rewrites that could hide OCR uncertainty.
"""

from __future__ import annotations

import re

FULL_WIDTH_TO_HALF = {
    "\u3000": " ",
    **{chr(code): chr(code - 0xFEE0) for code in range(0xFF01, 0xFF5F)},
}

SCRIPT_SYMBOL_MAP = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    "⁺": "+", "⁻": "-",
    "×": "x",
    "－": "-", "–": "-", "—": "-", "−": "-",
    "＜": "<", "＞": ">",
    "≤": "<=", "≦": "<=", "⩽": "<=", "≥": ">=", "≧": ">=", "⩾": ">=",
}

NATURAL_BREAK_PATTERN = re.compile(r"([^\n。！？；：\.\!\?;:])\n(?=[^\n\d])", re.MULTILINE)
MULTI_SPACE_PATTERN = re.compile(r"\s+")
CJK_INNER_SPACE_PATTERN = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")
UNIT_ANNOTATION_PATTERN = re.compile(r"(?:^|\s)单位\s*[：:]\s*[A-Za-z0-9μuΩΩ/%²³\-\.\(\)]+")


class TextNormalizer:
    def __init__(self, normalize_full_width: bool = True) -> None:
        self.normalize_full_width = normalize_full_width

    def normalize(self, text: str | None) -> str:
        if not text:
            return ""

        value = str(text)
        if self.normalize_full_width:
            value = self._convert_full_width(value)
        value = self._merge_natural_breaks(value)
        value = self._normalize_ocr_symbol_variants(value)
        value = self._normalize_repeated_heading_prefix(value)
        value = self._remove_format_annotations(value)
        value = self._remove_extra_whitespace(value)
        value = self._normalize_scientific_notation(value)
        value = self._normalize_cjk_spacing(value)
        value = self._normalize_punctuation_spacing(value)
        return value.strip()

    def normalize_for_display(self, text: str | None) -> str:
        if not text:
            return ""
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in str(text).splitlines()]
        compacted: list[str] = []
        for line in lines:
            if line or (compacted and compacted[-1]):
                compacted.append(line)
        while compacted and not compacted[0]:
            compacted.pop(0)
        while compacted and not compacted[-1]:
            compacted.pop()
        return "\n".join(line for line in compacted if line)

    def _convert_full_width(self, text: str) -> str:
        return "".join(FULL_WIDTH_TO_HALF.get(char, char) for char in text)

    def _merge_natural_breaks(self, text: str) -> str:
        return NATURAL_BREAK_PATTERN.sub(r"\1 ", text)

    def _remove_extra_whitespace(self, text: str) -> str:
        return MULTI_SPACE_PATTERN.sub(" ", text)

    def _normalize_cjk_spacing(self, text: str) -> str:
        return CJK_INNER_SPACE_PATTERN.sub("", text)

    def _remove_format_annotations(self, text: str) -> str:
        return UNIT_ANNOTATION_PATTERN.sub(" ", text)

    def _normalize_punctuation_spacing(self, text: str) -> str:
        value = re.sub(r"\s+([，。！？；：])", r"\1", text)
        value = re.sub(r"([，。！？；：])\s+", r"\1", value)
        value = re.sub(r"(?<=[\u4e00-\u9fffA-Za-z0-9\)])[:：](?=应符合)", "", value)
        return value

    def _normalize_ocr_symbol_variants(self, text: str) -> str:
        value = text.replace("Ω", "Ω")
        value = value.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")
        for src, dst in SCRIPT_SYMBOL_MAP.items():
            value = value.replace(src, dst)
        value = re.sub(r"(?<=\d)\s*士\s*(?=\d)", "±", value)
        value = re.sub(r"(?<=\d)MQ\b", "MΩ", value)
        value = re.sub(r"(?<=\d)M Q\b", "MΩ", value)
        return value

    def _normalize_scientific_notation(self, text: str) -> str:
        value = text.replace("µ", "μ")
        value = re.sub(r"ρ\s*(?=\()", "p", value)
        value = re.sub(r"(?<=[<>=≤≥])\s*[lI|](?=\s*(?:μ|u))", "1", value)
        value = re.sub(r"(\d(?:\.\d+)?)\s*(?:''|\"\"|″|“|”|＂)+", r'\1"', value)
        value = re.sub(r"KMnO\s+(\d)", r"KMnO\1", value)
        value = re.sub(r"Pb\s*(\d)\s*([+\-])", r"Pb\1\2", value)
        value = re.sub(r"([A-Za-z])\s+(\d)", r"\1\2", value)
        value = re.sub(r"(\d)\s+([+\-])", r"\1\2", value)
        value = re.sub(r"([cp])\s*\(\s*", r"\1(", value)
        value = re.sub(r"\s*\)", ")", value)
        value = re.sub(r"\s*=\s*", "=", value)
        value = re.sub(r"μ+\s*μ*\s*g\s*/\s*m\s*L", "μg/mL", value, flags=re.IGNORECASE)
        value = re.sub(r"\bu\s*g\s*/\s*m\s*L\b", "μg/mL", value, flags=re.IGNORECASE)
        value = re.sub(r"(?<=\d)\s*(?:μ|u)\s*(?:u\s*)?s(?=[^A-Za-z]|$)", "μs", value, flags=re.IGNORECASE)
        for unit in ["mL", "ms", "ns", "Hz", "V", "A", "Ω"]:
            value = re.sub(rf"(?<=\d)\s*{unit}\b", unit, value, flags=re.IGNORECASE)
        value = re.sub(r"([<>]=?)\s+(?=\d)", r"\1", value)
        value = re.sub(r"(?<=<)\s*=\s*", "=", value)
        value = re.sub(r"(?<=>)\s*=\s*", "=", value)
        value = re.sub(r"(?<=\d)\s*M(?:Q)?2\b", "MΩ", value)
        value = re.sub(r"(?<=\d)\s*K(?:Q)?2\b", "KΩ", value)
        value = re.sub(r"(?<=\d)\s*Q2\b", "Ω", value)
        value = re.sub(r"(?<=\d)\s*Q\b", "Ω", value)
        value = re.sub(r"KMnO\s*\)", "KMnO4)", value)
        value = re.sub(r"之\s*4\s*差", "之差", value)
        value = re.sub(r"(?<=[A-Za-z0-9μΩ/\]\)\+\-])\s+(?=[\u4e00-\u9fff])", "", value)
        value = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[A-Za-z0-9])", "", value)
        return value

    def _normalize_repeated_heading_prefix(self, text: str) -> str:
        pattern = re.compile(r"^([\u4e00-\u9fffA-Za-z0-9/（）()]{2,20}?)\s*\1(?=(?:应|[<>≤≥=]))")
        out: list[str] = []
        for line in text.split("\n"):
            previous = line
            while True:
                current = pattern.sub(r"\1", previous)
                if current == previous:
                    break
                previous = current
            out.append(previous)
        return "\n".join(out)

    def normalize_list(self, texts: list[str]) -> list[str]:
        return [self.normalize(text) for text in texts]

    def compare(self, text1: str | None, text2: str | None) -> bool:
        return self.normalize(text1) == self.normalize(text2)


_default_normalizer = TextNormalizer()


def normalize_text(text: str | None) -> str:
    return _default_normalizer.normalize(text)


def normalize_for_display(text: str | None) -> str:
    return _default_normalizer.normalize_for_display(text)


def compare_text(text1: str | None, text2: str | None) -> bool:
    return _default_normalizer.compare(text1, text2)


def are_text_equal_normalized(text1: str | None, text2: str | None) -> bool:
    return compare_text(text1, text2)
