from __future__ import annotations

from app.domain.pdf import ParsedPdf, PdfPage
from app.domain.report import ReportDocument


def report_page_text_by_page(report_doc: ReportDocument) -> dict[int, str]:
    if report_doc.parsed_pdf is None:
        return {}
    return parsed_pdf_page_text_by_page(report_doc.parsed_pdf)


def parsed_pdf_page_text_by_page(parsed_pdf: ParsedPdf) -> dict[int, str]:
    return {
        page.page_number: text
        for page in parsed_pdf.pages
        if (text := _page_text(page))
    }


def _page_text(page: PdfPage) -> str:
    values: list[str] = []
    if page.text and page.text.strip():
        values.append(page.text.strip())
    for table in page.tables:
        table_values: list[str] = []
        if table.caption:
            table_values.append(table.caption)
        elif table.title:
            table_values.append(table.title)
        for row in table.rows:
            row_text = " ".join(str(cell or "").strip() for cell in row if str(cell or "").strip())
            if row_text:
                table_values.append(row_text)
        if table_values:
            values.append("\n".join(table_values))
    return "\n".join(values).strip()


__all__ = ["parsed_pdf_page_text_by_page", "report_page_text_by_page"]
