from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.pdf import ParsedPdf, PdfPage
from app.domain.report import FirstPageInfo, ReportDocument, ReportField, ThirdPageInfo
from app.infrastructure.report.page_locator import LocatedPage, PageLocator


@dataclass(frozen=True)
class FieldSpec:
    name: str
    attr: str | None
    pattern: re.Pattern[str]
    aliases: tuple[str, ...] = ()
    metadata: Callable[[str], dict[str, object]] | None = None


FIRST_PAGE_FIELD_SPECS = (
    FieldSpec("委托方", "client", re.compile(r"委\s*托\s*方\s*(?:[:：]\s*)?([^\n]+)")),
    FieldSpec("样品名称", "sample_name", re.compile(r"样\s*品\s*名\s*称\s*(?:[:：]\s*)?([^\n]+)")),
    FieldSpec(
        "型号规格",
        "model_spec",
        re.compile(r"(?:型\s*号\s*规\s*格|规\s*格\s*型\s*号)\s*(?:[:：]\s*)?([^\n]+)"),
        aliases=("规格型号",),
    ),
)

THIRD_PAGE_FIELD_SPECS = (
    FieldSpec(
        "委托方",
        "client",
        re.compile(r"委\s*托\s*方(?!\s*地\s*址)\s*(?:[:：]\s*)?([^\n]+)"),
    ),
    FieldSpec("样品名称", None, re.compile(r"样\s*品\s*名\s*称\s*(?:[:：]\s*)?([^\n]+)")),
    FieldSpec(
        "型号规格",
        "model_spec",
        re.compile(r"(?:型\s*号\s*规\s*格|规\s*格\s*型\s*号)\s*(?:[:：]\s*)?([^\n]+)"),
        aliases=("规格型号",),
    ),
    FieldSpec("生产日期", "production_date", re.compile(r"生\s*产\s*日\s*期\s*(?:[:：]\s*)?([^\n]+)")),
    FieldSpec(
        "产品编号/批号",
        "batch_or_serial",
        re.compile(
            r"(?:产\s*品\s*编\s*号\s*[/／]?\s*批\s*号|产品编号|批号)"
            r"\s*(?:[:：]\s*)?([^\n]+)"
        ),
        aliases=("产品编号", "批号", "序列号", "批号/序列号"),
    ),
    FieldSpec(
        "委托方地址",
        "client_address",
        re.compile(r"(?:委\s*托\s*方\s*地\s*址|委托方地址)\s*(?:[:：]\s*)?([^\n]+)"),
    ),
    FieldSpec(
        "检验项目",
        None,
        re.compile(r"检\s*验\s*项\s*目\s*(?:[:：]\s*)?([^\n]+)"),
        metadata=lambda value: {"items": split_inspection_items(value)},
    ),
)


class FieldExtractor:
    """Extract first-page and third-page report fields as domain models.

    This extractor preserves raw field text alongside stripped values. It does
    not compare fields or emit C01-C03 findings.
    """

    def __init__(self, page_locator: PageLocator | None = None) -> None:
        self.page_locator = page_locator or PageLocator()

    def extract(self, parsed_pdf: ParsedPdf) -> ReportDocument:
        page_map = self.page_locator.locate(parsed_pdf)
        first_page_info: FirstPageInfo | None = None
        third_page_info: ThirdPageInfo | None = None
        fields: list[ReportField] = []
        report_page_map: dict[str, int] = {}

        if page_map.first_page is not None:
            page = self._page_for_location(parsed_pdf, page_map.first_page)
            if page is not None:
                first_page_info = self.extract_first_page_fields(parsed_pdf, page)
                fields.extend(first_page_info.fields)
                report_page_map["first_page"] = page.page_number

        if page_map.third_page is not None:
            page = self._page_for_location(parsed_pdf, page_map.third_page)
            if page is not None:
                third_page_info = self.extract_third_page_fields(parsed_pdf, page)
                fields.extend(third_page_info.fields)
                report_page_map["third_page"] = page.page_number

        return ReportDocument(
            parsed_pdf=parsed_pdf,
            first_page=first_page_info,
            third_page=third_page_info,
            fields=fields,
            page_map=report_page_map,
            diagnostics=page_map.diagnostics,
        )

    def extract_first_page_fields(self, parsed_pdf: ParsedPdf, page: PdfPage) -> FirstPageInfo:
        extracted_fields = self._extract_fields(parsed_pdf, page, FIRST_PAGE_FIELD_SPECS)
        info = FirstPageInfo(fields=extracted_fields)
        self._assign_fields(info, extracted_fields, FIRST_PAGE_FIELD_SPECS)
        info.evidence = [evidence for field in extracted_fields for evidence in field.evidence]
        return info

    def extract_third_page_fields(self, parsed_pdf: ParsedPdf, page: PdfPage) -> ThirdPageInfo:
        extracted_fields = self._extract_fields(parsed_pdf, page, THIRD_PAGE_FIELD_SPECS)
        address_field = self._extract_multiline_address(parsed_pdf, page, len(extracted_fields))
        if address_field is not None:
            extracted_fields = [
                field for field in extracted_fields if field.name != "委托方地址"
            ]
            extracted_fields.append(address_field)

        info = ThirdPageInfo(fields=extracted_fields)
        self._assign_fields(info, extracted_fields, THIRD_PAGE_FIELD_SPECS)
        info.evidence = [evidence for field in extracted_fields for evidence in field.evidence]
        return info

    def _extract_fields(
        self,
        parsed_pdf: ParsedPdf,
        page: PdfPage,
        specs: tuple[FieldSpec, ...],
    ) -> list[ReportField]:
        fields: list[ReportField] = []
        for spec in specs:
            match = spec.pattern.search(page.text or "")
            if not match:
                continue
            raw_value = match.group(1).rstrip("\r")
            metadata = spec.metadata(raw_value) if spec.metadata else {}
            fields.append(
                self._report_field(
                    parsed_pdf=parsed_pdf,
                    page=page,
                    spec=spec,
                    raw_value=raw_value,
                    value=raw_value.strip(),
                    raw_context=match.group(0),
                    sequence=len(fields) + 1,
                    metadata=metadata,
                )
            )
        return fields

    def _extract_multiline_address(
        self,
        parsed_pdf: ParsedPdf,
        page: PdfPage,
        sequence_offset: int,
    ) -> ReportField | None:
        raw_value = _extract_multiline_field_value(
            page.text,
            label_pattern=re.compile(r"委\s*托\s*方\s*地\s*址"),
            stop_label_patterns=[
                re.compile(pattern)
                for pattern in [
                    r"产\s*品\s*编\s*号",
                    r"批\s*号",
                    r"生\s*产\s*单\s*位",
                    r"受\s*检\s*单\s*位",
                    r"抽\s*样\s*单\s*编\s*号",
                    r"抽\s*样\s*单\s*位",
                    r"抽\s*样\s*地\s*点",
                    r"抽\s*样\s*日\s*期",
                    r"到\s*样\s*日\s*期",
                    r"检\s*验\s*项\s*目",
                    r"检\s*验\s*日\s*期",
                    r"检\s*验\s*地\s*点",
                    r"样\s*品\s*数\s*量",
                ]
            ],
        )
        if raw_value is None:
            return None

        spec = next(spec for spec in THIRD_PAGE_FIELD_SPECS if spec.name == "委托方地址")
        value = "".join(line.strip() for line in raw_value.splitlines() if line.strip())
        return self._report_field(
            parsed_pdf=parsed_pdf,
            page=page,
            spec=spec,
            raw_value=raw_value,
            value=value,
            raw_context=f"委托方地址\n{raw_value}",
            sequence=sequence_offset + 1,
            metadata={},
        )

    def _report_field(
        self,
        *,
        parsed_pdf: ParsedPdf,
        page: PdfPage,
        spec: FieldSpec,
        raw_value: str,
        value: str,
        raw_context: str,
        sequence: int,
        metadata: dict[str, object],
    ) -> ReportField:
        normalized_value = re.sub(r"\s+", "", value or "")
        evidence = Evidence(
            id=f"{parsed_pdf.file_id}:field:{page.page_number}:{sequence}:{_field_id(spec.name)}",
            source_type=SourceType.REPORT,
            location=Location(
                source_id=parsed_pdf.file_id,
                source_type=SourceType.REPORT,
                page_number=page.page_number,
                description=spec.name,
            ),
            raw_text=raw_context,
            normalized_text=normalized_value,
            value=value,
            method=EvidenceMethod.PDF_TEXT,
            confidence=Confidence.HIGH,
            metadata={"field_name": spec.name},
        )
        return ReportField(
            name=spec.name,
            raw_value=raw_value,
            value=value,
            normalized_value=normalized_value,
            location=evidence.location,
            evidence=[evidence],
            confidence=Confidence.HIGH,
            aliases=list(spec.aliases),
            metadata=metadata,
        )

    def _assign_fields(
        self,
        info: FirstPageInfo | ThirdPageInfo,
        fields: list[ReportField],
        specs: tuple[FieldSpec, ...],
    ) -> None:
        for field in fields:
            spec = self._spec_for_field(field.name, specs)
            if spec is None or spec.attr is None:
                continue
            setattr(info, spec.attr, field)

    def _spec_for_field(
        self,
        field_name: str,
        specs: tuple[FieldSpec, ...],
    ) -> FieldSpec | None:
        for spec in specs:
            if spec.name == field_name:
                return spec
        return None

    def _page_for_location(self, parsed_pdf: ParsedPdf, location: LocatedPage) -> PdfPage | None:
        for page in parsed_pdf.pages:
            if page.page_number == location.page_number:
                return page
        return None


def split_inspection_items(value: str) -> list[str]:
    text = (value or "").strip()
    if not text:
        return []

    items: list[str] = []
    current: list[str] = []
    depth = 0

    for char in text:
        if char in "（(":
            depth += 1
            current.append(char)
            continue
        if char in "）)" and depth > 0:
            depth -= 1
            current.append(char)
            continue
        if char in ",，、" and depth == 0:
            candidate = "".join(current).strip()
            if candidate:
                items.append(candidate)
            current = []
            continue
        current.append(char)

    candidate = "".join(current).strip()
    if candidate:
        items.append(candidate)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _extract_multiline_field_value(
    text: str,
    *,
    label_pattern: re.Pattern[str],
    stop_label_patterns: list[re.Pattern[str]],
) -> str | None:
    lines = (text or "").splitlines()
    for idx, line in enumerate(lines):
        compact_line = re.sub(r"\s+", "", line)
        if not label_pattern.search(compact_line):
            continue

        parts: list[str] = []
        for next_line in lines[idx + 1 :]:
            compact_next = re.sub(r"\s+", "", next_line)
            if not compact_next:
                continue
            if any(stop_re.search(compact_next) for stop_re in stop_label_patterns):
                break
            parts.append(next_line.rstrip("\r"))

        if parts:
            return "\n".join(parts)

    return None


def _field_id(field_name: str) -> str:
    return re.sub(r"\W+", "_", field_name).strip("_") or "field"
