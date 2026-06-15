from enum import StrEnum
import re

from pydantic import BaseModel, Field

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.pdf import ParsedPdf, PdfPage


class PageRole(StrEnum):
    FIRST_PAGE = "first_page"
    THIRD_PAGE = "third_page"
    PHOTO_PAGE = "photo_page"
    LABEL_PAGE = "label_page"
    SAMPLE_DESCRIPTION_PAGE = "sample_description_page"


class LocatedPage(BaseModel):
    role: PageRole
    page_number: int
    reason: str
    text_snippet: str = ""
    evidence: list[Evidence] = Field(default_factory=list)


class ReportPageMap(BaseModel):
    first_page: LocatedPage | None = None
    third_page: LocatedPage | None = None
    photo_pages: list[LocatedPage] = Field(default_factory=list)
    label_pages: list[LocatedPage] = Field(default_factory=list)
    sample_description_pages: list[LocatedPage] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class PageLocator:
    """Locate report page roles from parsed PDF text.

    The locator only reports page candidates and diagnostics. It does not judge
    C01-C11 outcomes and does not infer missing business evidence as failures.
    """

    def locate(self, parsed_pdf: ParsedPdf) -> ReportPageMap:
        page_map = ReportPageMap()

        if parsed_pdf.pages:
            first_page = self._page_by_number(parsed_pdf.pages, 1) or parsed_pdf.pages[0]
            page_map.first_page = self._located_page(
                parsed_pdf,
                first_page,
                PageRole.FIRST_PAGE,
                "physical_first_page",
            )
        else:
            page_map.diagnostics.append("first page not found: parsed PDF has no pages")

        for page in parsed_pdf.pages:
            compact_text = _compact(page.text)
            if page_map.third_page is None and "检验报告首页" in compact_text:
                page_map.third_page = self._located_page(
                    parsed_pdf,
                    page,
                    PageRole.THIRD_PAGE,
                    "title_match",
                )

            if self._is_sample_description_page(compact_text):
                page_map.sample_description_pages.append(
                    self._located_page(
                        parsed_pdf,
                        page,
                        PageRole.SAMPLE_DESCRIPTION_PAGE,
                        "sample_description_keyword",
                    )
                )

            if self._is_photo_page(page.text, compact_text):
                page_map.photo_pages.append(
                    self._located_page(
                        parsed_pdf,
                        page,
                        PageRole.PHOTO_PAGE,
                        "photo_keyword",
                    )
                )

            if self._is_label_page(page.text, compact_text):
                page_map.label_pages.append(
                    self._located_page(
                        parsed_pdf,
                        page,
                        PageRole.LABEL_PAGE,
                        "label_keyword",
                    )
                )

        if page_map.third_page is None:
            page_map.diagnostics.append("third page not found")

        return page_map

    def _located_page(
        self,
        parsed_pdf: ParsedPdf,
        page: PdfPage,
        role: PageRole,
        reason: str,
    ) -> LocatedPage:
        snippet = _snippet(page.text)
        evidence = Evidence(
            id=f"{parsed_pdf.file_id}:page:{role.value}:{page.page_number}",
            source_type=SourceType.REPORT,
            location=Location(
                source_id=parsed_pdf.file_id,
                source_type=SourceType.REPORT,
                page_number=page.page_number,
                description=reason,
            ),
            raw_text=snippet,
            normalized_text=_compact(snippet),
            value=str(page.page_number),
            method=EvidenceMethod.PDF_TEXT,
            confidence=Confidence.HIGH,
            metadata={"role": role.value, "reason": reason},
        )
        return LocatedPage(
            role=role,
            page_number=page.page_number,
            reason=reason,
            text_snippet=snippet,
            evidence=[evidence],
        )

    def _page_by_number(self, pages: list[PdfPage], page_number: int) -> PdfPage | None:
        for page in pages:
            if page.page_number == page_number:
                return page
        return None

    def _is_sample_description_page(self, compact_text: str) -> bool:
        if "样品描述" not in compact_text:
            return False
        table_keywords = [
            "部件名称",
            "样品名称",
            "产品名称",
            "规格型号",
            "型号规格",
            "生产日期",
            "失效日期",
            "序列号",
            "批号",
            "备注",
        ]
        return any(keyword in compact_text for keyword in table_keywords)

    def _is_photo_page(self, raw_text: str, compact_text: str) -> bool:
        if "检验报告照片页" in compact_text or "照片和说明" in compact_text:
            return True
        if "照片" not in compact_text:
            return False
        return any(keyword in compact_text for keyword in ["检品外观", "外观", "说明", "图片", "标签"])

    def _is_label_page(self, raw_text: str, compact_text: str) -> bool:
        if "标签" not in compact_text:
            return False
        return any(
            keyword in compact_text or keyword in raw_text
            for keyword in ["中文标签", "标签样张", "№", "No", "NO", "no"]
        )


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _snippet(text: str, *, limit: int = 240) -> str:
    collapsed = re.sub(r"\s+", " ", text or "").strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit].rstrip()
