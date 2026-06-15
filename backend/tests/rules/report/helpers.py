from __future__ import annotations

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.report import (
    FirstPageInfo,
    InspectionItem,
    LabelOCRField,
    LabelOCRResult,
    PageNumberEvidence,
    PhotoCaption,
    ReportDocument,
    ReportField,
    SampleComponent,
    ThirdPageInfo,
)


def location(page: int = 1, column: str | None = None, row: int | None = None) -> Location:
    return Location(
        source_id="report-fixture",
        source_type=SourceType.REPORT,
        page_number=page,
        column_name=column,
        row_index=row,
    )


def evidence(id_suffix: str, text: str, *, page: int = 1, column: str | None = None) -> Evidence:
    return Evidence(
        id=f"ev-{id_suffix}",
        source_type=SourceType.REPORT,
        location=location(page, column),
        raw_text=text,
        value=text,
        method=EvidenceMethod.PDF_TEXT,
        confidence=Confidence.HIGH,
    )


def field(name: str, value: str | None, *, page: int = 1) -> ReportField:
    raw_value = value
    return ReportField(
        name=name,
        raw_value=raw_value,
        value=value,
        location=location(page, name),
        evidence=[evidence(f"{page}-{name}", f"{name}：{value}", page=page, column=name)]
        if value is not None
        else [],
    )


def label_field(name: str, value: str, *, page: int = 8, aliases: list[str] | None = None) -> LabelOCRField:
    return LabelOCRField(
        name=name,
        raw_value=f"{name}：{value}",
        value=value,
        normalized_value=value,
        location=location(page, name),
        aliases=aliases or [],
        evidence=[evidence(f"label-{name}-{value}", f"{name}：{value}", page=page, column=name)],
    )


def label(
    label_id: str,
    *,
    caption_text: str,
    fields: list[LabelOCRField],
    page: int = 8,
    confidence: Confidence | str = Confidence.HIGH,
) -> LabelOCRResult:
    return LabelOCRResult(
        label_id=label_id,
        page_number=page,
        caption_text=caption_text,
        fields=fields,
        raw_blocks=[f.raw_value or "" for f in fields],
        language="zh",
        confidence=confidence,
        evidence=[evidence(f"{label_id}-caption", caption_text, page=page)],
    )


def base_document(*, labels: list[LabelOCRResult] | None = None) -> ReportDocument:
    first = FirstPageInfo(
        client=field("委托方", "苏州元科医疗器械有限公司", page=1),
        sample_name=field("样品名称", "一次性使用消化道脉冲电场消融导管", page=1),
        model_spec=field("型号规格", "RMC01", page=1),
    )
    third_sample = field("样品名称", "一次性使用消化道脉冲电场消融导管", page=3)
    third = ThirdPageInfo(
        client=field("委托方", "苏州元科医疗器械有限公司", page=3),
        client_address=field("委托方地址", "苏州工业园区星湖街328号", page=3),
        model_spec=field("型号规格", "RMC01", page=3),
        production_date=field("生产日期", "2025-12-10", page=3),
        batch_or_serial=field("产品编号/批号", "RMC251201", page=3),
        fields=[third_sample],
    )
    return ReportDocument(
        first_page=first,
        third_page=third,
        labels=labels or [],
        page_map={"first_page": 1, "third_page": 3},
    )


def component(
    component_id: str,
    name: str,
    *,
    model: str | None = "RMC01",
    batch: str | None = "RMC251201",
    production_date: str | None = "2025-12-10",
    expiration_date: str | None = "",
    remark: str | None = None,
    page: int = 4,
) -> SampleComponent:
    return SampleComponent(
        component_id=component_id,
        component_name=name,
        model=model,
        batch_or_serial=batch,
        production_date=production_date,
        expiration_date=expiration_date,
        remark=remark,
        row_location=location(page, "样品描述", 0),
        evidence=[evidence(f"component-{component_id}", name, page=page, column="部件名称")],
    )


def photo_caption(
    caption_id: str,
    text: str,
    *,
    subject: str | None = None,
    caption_type: str | None = "photo",
    page: int = 6,
) -> PhotoCaption:
    return PhotoCaption(
        caption_id=caption_id,
        text=text,
        subject_name=subject,
        caption_type=caption_type,
        page_number=page,
        evidence=[evidence(f"caption-{caption_id}", text, page=page)],
    )


def item(
    seq: int | None,
    *,
    raw: str | None = None,
    result: str | None = "符合要求",
    conclusion: str | None = "符合",
    remark: str | None = "/",
    page: int = 5,
    row: int = 0,
    continued: bool = False,
    name: str = "电气安全",
) -> InspectionItem:
    return InspectionItem(
        sequence=seq,
        sequence_raw=raw if raw is not None else (str(seq) if seq is not None else ""),
        is_continuation=continued,
        item_name=name,
        standard_requirement="应符合要求",
        test_result=result,
        conclusion=conclusion,
        remark=remark,
        source_page=page,
        row_index_in_page=row,
        row_location=location(page, "检验项目", row),
        evidence=[evidence(f"item-{page}-{row}", name, page=page, column="检验项目")],
    )


def page_number(page: int, current: int | None, total: int | None, raw: str | None = None) -> PageNumberEvidence:
    return PageNumberEvidence(
        page_number=page,
        displayed_number=raw or (f"共 {total} 页 第 {current} 页" if current and total else None),
        parsed_number=current,
        total_pages=total,
        location=location(page, "页码"),
        evidence=[evidence(f"page-{page}", raw or "", page=page, column="页码")] if raw else [],
    )
