from __future__ import annotations

from datetime import datetime
import re

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.pdf import ParsedPdf, PdfPage
from app.domain.report import LabelOCR, LabelOCRField, PhotoCaption
from app.infrastructure.report.page_locator import PageLocator


FIELD_PATTERNS = {
    "product_name": [
        r"产品\s*名称\s*(?:[：:]\s*)?([^\n]+)",
        r"器械\s*名称\s*(?:[：:]\s*)?([^\n]+)",
        r"品名\s*(?:[：:]\s*)?([^\n]+)",
    ],
    "model_spec": [
        r"规格\s*型号\s*(?:[：:]\s*)?([^\n]+)",
        r"型号\s*规格\s*(?:[：:]\s*)?([^\n]+)",
        r"(?<!产品)型号\s*(?:[：:]\s*)?([^\n]+)",
        r"Model\s*(?:[：:]\s*)?([^\n]+)",
        r"Spec\s*(?:[：:]\s*)?([^\n]+)",
    ],
    "production_date": [
        r"生产\s*日期\s*(?:[：:]\s*)?([^\n]+)",
        r"MFG\s*(?:[：:]\s*)?([^\n]+)",
        r"MFD\s*(?:[：:]\s*)?([^\n]+)",
        r"制造\s*日期\s*(?:[：:]\s*)?([^\n]+)",
        r"Manufacturing Date\s*(?:[：:]\s*)?([^\n]+)",
    ],
    "expiration_date": [
        r"失效\s*日期\s*(?:[：:]\s*)?([^\n]+)",
        r"有效期至\s*(?:[：:]\s*)?([^\n]+)",
        r"有效期\s*(?:[：:]\s*)?([^\n]+)",
        r"Expiration Date\s*(?:[：:]\s*)?([^\n]+)",
        r"\bEXP\b\s*(?:[：:]\s*)?([^\n]+)",
    ],
    "batch_number": [
        r"批号\s*(?:[：:]\s*)?([^\n]+)",
        r"Lot Number\s*(?:[：:]\s*)?([^\n]+)",
        r"Batch Number\s*(?:[：:]\s*)?([^\n]+)",
        r"\bLOT\b\s*(?:[：:|]?\s*)?([^\n]+)",
    ],
    "serial_number": [
        r"序列号\s*(?:[：:]\s*)?([^\n]+)",
        r"\bSN\b\s*(?:[：:]\s*)?([^\n]+)",
        r"Serial Number\s*(?:[：:]\s*)?([^\n]+)",
    ],
    "registrant": [
        r"注册人\s*名称\s*[：:]\s*([^\n]+)",
        r"注册人\s*[：:]\s*([^\n]+)",
        r"[注註][^\n]{0,2}人\s*[：:]\s*([^\n]+)",
    ],
    "registrant_address": [
        r"注册人住所\s*(?:[：:]\s*)?([^\n]+)",
        r"注册人地址\s*(?:[：:]\s*)?([^\n]+)",
    ],
}


class PhotoLabelExtractor:
    """Extract photo captions, label captions, and text-layer OCR candidates."""

    def __init__(self, page_locator: PageLocator | None = None) -> None:
        self.page_locator = page_locator or PageLocator()

    def extract_captions(self, parsed_pdf: ParsedPdf) -> list[PhotoCaption]:
        captions: list[PhotoCaption] = []
        caption_counter = 0
        for page in parsed_pdf.pages:
            for line in self._caption_lines(page):
                caption_counter += 1
                captions.append(self._caption_from_line(parsed_pdf, page, line, caption_counter))
        return captions

    def extract_labels(self, parsed_pdf: ParsedPdf) -> list[LabelOCR]:
        labels: list[LabelOCR] = []
        label_counter = 0
        captions_by_page: dict[int, list[PhotoCaption]] = {}
        for caption in self.extract_captions(parsed_pdf):
            if caption.page_number is None:
                continue
            captions_by_page.setdefault(caption.page_number, []).append(caption)

        for page in parsed_pdf.pages:
            fields = extract_label_field_candidates(page.text)
            page_captions = captions_by_page.get(page.page_number, [])
            label_captions = [caption for caption in page_captions if caption.caption_type == "label"]
            if not fields and not label_captions:
                continue

            label_counter += 1
            caption = label_captions[0] if label_captions else (page_captions[0] if page_captions else None)
            label_id = f"label-{label_counter}"
            label_fields = [
                self._label_field(
                    parsed_pdf=parsed_pdf,
                    label_id=label_id,
                    page=page,
                    field_name=field_name,
                    raw_value=value,
                )
                for field_name, value in fields.items()
            ]
            labels.append(
                LabelOCR(
                    label_id=label_id,
                    page_number=page.page_number,
                    caption_id=caption.caption_id if caption else None,
                    caption_text=caption.text if caption else None,
                    fields=label_fields,
                    raw_blocks=[line for line in page.text.splitlines() if line.strip()],
                    language="zh",
                    ocr_engine="pdf_text",
                    confidence=Confidence.HIGH if fields else Confidence.MEDIUM,
                    evidence=[evidence for field in label_fields for evidence in field.evidence],
                    metadata={
                        "candidate_source": "pdf_text_label_page",
                        "subject_name": caption.subject_name if caption else None,
                    },
                )
            )
        return labels

    def _caption_lines(self, page: PdfPage) -> list[str]:
        result: list[str] = []
        for raw_line in (page.text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if re.match(r"^(图|№|No\.?|Photo|Plate|Fig\.?)\s*\d+", line, re.IGNORECASE):
                result.append(line)
                continue
            compact = _compact(line)
            if compact in {"检验报告照片页", "照片和说明"}:
                continue
            if "检品外观" in compact and "照片" in compact:
                result.append(line)
                continue
            if is_chinese_label(line) and not _looks_like_field_line(line):
                result.append(line)
        return result

    def _caption_from_line(
        self,
        parsed_pdf: ParsedPdf,
        page: PdfPage,
        line: str,
        counter: int,
    ) -> PhotoCaption:
        caption_type = "label" if is_chinese_label(line) else "photo"
        subject_name = parse_caption_subject(line)
        location = Location(
            source_id=parsed_pdf.file_id,
            source_type=SourceType.REPORT,
            page_number=page.page_number,
            description=caption_type,
        )
        evidence = Evidence(
            id=f"{parsed_pdf.file_id}:caption:{page.page_number}:{counter}",
            source_type=SourceType.REPORT,
            location=location,
            raw_text=line,
            normalized_text=_compact(line),
            value=subject_name,
            method=EvidenceMethod.PDF_TEXT,
            confidence=Confidence.HIGH,
            metadata={"caption_type": caption_type},
        )
        return PhotoCaption(
            caption_id=f"caption-{counter}",
            text=line,
            subject_name=subject_name,
            caption_type=caption_type,
            page_number=page.page_number,
            evidence=[evidence],
            metadata={"is_chinese_label": caption_type == "label"},
        )

    def _label_field(
        self,
        *,
        parsed_pdf: ParsedPdf,
        label_id: str,
        page: PdfPage,
        field_name: str,
        raw_value: str,
    ) -> LabelOCRField:
        value = (raw_value or "").strip()
        location = Location(
            source_id=parsed_pdf.file_id,
            source_type=SourceType.REPORT,
            page_number=page.page_number,
            description=field_name,
        )
        evidence = Evidence(
            id=f"{parsed_pdf.file_id}:{label_id}:{field_name}",
            source_type=SourceType.REPORT,
            location=location,
            raw_text=raw_value,
            normalized_text=_compact(value),
            value=value,
            method=EvidenceMethod.PDF_TEXT,
            confidence=Confidence.HIGH,
            metadata={"field_name": field_name},
        )
        return LabelOCRField(
            name=field_name,
            raw_value=raw_value,
            value=value,
            normalized_value=_compact(value),
            location=location,
            evidence=[evidence],
            confidence=Confidence.HIGH,
        )


def extract_label_field_candidates(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for field_name, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text or "", re.IGNORECASE)
            if not match:
                continue
            value = _clean_field_value(match.group(1))
            if value and _is_valid_field_value(field_name, value):
                fields[field_name] = value
                break

    fields = _fill_from_next_line_values(text, fields)
    multiline_address = _extract_multiline_value(
        text=text,
        label_patterns=[r"注册人住所", r"注册人地址"],
        stop_patterns=[
            r"注册人联系方式",
            r"受托生产企业名称",
            r"受托生产企业住所",
            r"受托生产企业生产地址",
            r"产品名称",
            r"型号规格",
            r"规格型号",
            r"生产日期",
            r"失效日期",
            r"生产批号",
        ],
    )
    if multiline_address:
        fields["registrant_address"] = multiline_address

    date_candidates = _date_candidates(text)
    if not fields.get("production_date") and date_candidates:
        fields["production_date"] = date_candidates[0]
    if not fields.get("expiration_date") and len(date_candidates) >= 2:
        fields["expiration_date"] = date_candidates[-1]

    if not fields.get("model_spec"):
        model_candidate = _model_spec_fallback(text)
        if model_candidate:
            fields["model_spec"] = model_candidate

    if not fields.get("batch_number"):
        batch_candidate = _batch_number_fallback(text)
        if batch_candidate:
            fields["batch_number"] = batch_candidate

    if not fields.get("serial_number") and not fields.get("batch_number"):
        serial_candidate = _standalone_serial_or_batch(text)
        if serial_candidate:
            fields["serial_number"] = serial_candidate

    return {key: _clean_field_value(value) for key, value in fields.items()}


def parse_caption_subject(caption_text: str) -> str:
    subject = (caption_text or "").strip()
    subject = re.sub(
        r"^(?:图|№|No\.?|Photo|Plate|Fig|Fig\.)\s*\d+\s*[:：]?\s*",
        "",
        subject,
        flags=re.IGNORECASE,
    )

    direction_patterns = [
        r"左侧显示",
        r"右侧显示",
        r"左图",
        r"右图",
        r"正面图",
        r"背面图",
        r"俯视图",
        r"仰视图",
        r"局部放大图",
        r"细节图",
        r"整体图",
        r"正面",
        r"背面",
        r"侧面",
        r"局部",
        r"整体",
    ]
    category_patterns = [
        r"中文标签样张",
        r"中文标签",
        r"包装标签样张",
        r"包装标签",
        r"标签样张",
        r"标签",
        r"铭牌",
        r"标牌",
        r"检品外观",
        r"外观",
        r"照片",
        r"图片",
    ]
    for pattern in direction_patterns + category_patterns:
        subject = re.sub(pattern, "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"^[第一二三四五六七八九十\d]+(?:[\.、:：]|张)\s*", "", subject)
    subject = re.sub(r"^[\s:：]+|[\s:：]+$", "", subject)
    return subject.strip()


def is_chinese_label(text: str) -> bool:
    compact = _compact(text)
    return any(keyword in compact for keyword in ["中文标签", "标签样张", "铭牌", "标牌"])


def _fill_from_next_line_values(text: str, fields: dict[str, str]) -> dict[str, str]:
    lines = [line.strip() for line in (text or "").splitlines()]

    def next_non_empty(start: int) -> str:
        for idx in range(start + 1, len(lines)):
            if lines[idx]:
                return lines[idx]
        return ""

    for idx, line in enumerate(lines):
        value = next_non_empty(idx)
        if not value:
            continue
        if any(key in line for key in ["产品名称", "器械名称", "品名"]) and not fields.get("product_name"):
            if len(value) >= 4:
                fields["product_name"] = value
        if ("规格型号" in line or "型号规格" in line) and not fields.get("model_spec"):
            compact = _compact(value)
            if re.fullmatch(r"[A-Za-z0-9.\-_/]+", compact):
                fields["model_spec"] = compact
        if any(key in line.upper() for key in ["SN", "序列号", "批号"]) and not (
            fields.get("serial_number") or fields.get("batch_number")
        ):
            compact = _compact(value)
            if re.fullmatch(r"[A-Za-z]{1,6}\d{6,}[A-Za-z0-9\-_/]*", compact):
                fields["serial_number"] = compact
        if any(key in line for key in ["生产日期", "制造日期"]) and not fields.get("production_date"):
            digits = re.sub(r"\D", "", value)
            if re.fullmatch(r"\d{8}", digits):
                fields["production_date"] = digits
    return fields


def _extract_multiline_value(
    *,
    text: str,
    label_patterns: list[str],
    stop_patterns: list[str],
) -> str:
    lines = [line.strip() for line in (text or "").splitlines()]
    label_res = [re.compile(pattern) for pattern in label_patterns]
    stop_res = [re.compile(pattern) for pattern in stop_patterns]

    for idx, line in enumerate(lines):
        if not line or not any(label_re.search(line) for label_re in label_res):
            continue
        parts: list[str] = []
        split_line = re.split(r"[:：]", line, maxsplit=1)
        if len(split_line) == 2 and split_line[1].strip():
            parts.append(split_line[1].strip())
        for next_line in lines[idx + 1 :]:
            current = next_line.strip()
            if not current:
                continue
            if any(stop_re.search(current) for stop_re in stop_res):
                break
            parts.append(current)
        if parts:
            return "".join(parts).strip()
    return ""


def _date_candidates(text: str) -> list[str]:
    raw_candidates = re.findall(r"(20\d{2}[-/.年]?\d{1,2}[-/.月]?\d{1,2}日?)", text or "")
    parsed: list[tuple[datetime, str]] = []
    seen: set[str] = set()
    for raw in raw_candidates:
        digits = re.sub(r"\D", "", raw)
        if len(digits) != 8 or digits in seen:
            continue
        try:
            parsed_date = datetime.strptime(digits, "%Y%m%d")
        except ValueError:
            continue
        seen.add(digits)
        parsed.append((parsed_date, f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"))
    parsed.sort(key=lambda item: item[0])
    return [value for _, value in parsed]


def _model_spec_fallback(text: str) -> str:
    match = re.search(r"\bREF\b[^\nA-Za-z0-9]{0,6}([A-Za-z][A-Za-z0-9.\-_/]{3,})", text or "", re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _batch_number_fallback(text: str) -> str:
    match = re.search(r"\bLOT[^\nA-Za-z0-9]{0,4}([A-Za-z0-9.\-_/]{3,})", text or "", re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _standalone_serial_or_batch(text: str) -> str:
    candidates = re.findall(r"\b[A-Z]{2,8}\d{6,}[A-Z0-9\-_/]*\b", text or "")
    return sorted(candidates, key=len, reverse=True)[0] if candidates else ""


def _is_valid_field_value(field_name: str, value: str) -> bool:
    cleaned = (value or "").strip()
    if not cleaned:
        return False
    if re.fullmatch(r"[【】\[\]()（）:：|/\\-]+", cleaned):
        return False
    if field_name in {"model_spec", "batch_number", "serial_number"}:
        if len(_compact(cleaned)) < 3:
            return False
    if field_name == "registrant" and re.search(r"(住所|住址|地址|联系方式)", cleaned):
        return False
    if field_name == "production_date":
        digits = re.sub(r"\D", "", cleaned)
        if digits and len(digits) != 8:
            return False
    return True


def _looks_like_field_line(text: str) -> bool:
    return bool(re.match(r"^[^：:]{1,12}[：:]", text or ""))


def _clean_field_value(value: str) -> str:
    return re.sub(r"^[：:]+", "", (value or "").strip()).strip()


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")
