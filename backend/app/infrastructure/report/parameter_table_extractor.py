from __future__ import annotations

from app.domain.pdf import ParsedPdf, PdfTable
from app.domain.table import CanonicalTable
from app.infrastructure.table.table_normalizer import TableNormalizer


class ReportParameterTableExtractor:
    """Normalize report-side parameter tables for PTR table comparison.

    The extractor only converts already parsed PDF tables into CanonicalTable
    evidence. It does not compare PTR/report values or emit rule findings.
    """

    def __init__(self, table_normalizer: TableNormalizer | None = None) -> None:
        self.table_normalizer = table_normalizer or TableNormalizer()

    def extract_tables(self, parsed_pdf: ParsedPdf) -> list[CanonicalTable]:
        tables: list[CanonicalTable] = []
        for table in self._pdf_tables(parsed_pdf):
            canonical = self.table_normalizer.normalize(table)
            if not canonical.parameter_records:
                continue
            canonical.metadata.setdefault("source", "report_parameter_table_extractor")
            tables.append(canonical)
        return tables

    def _pdf_tables(self, parsed_pdf: ParsedPdf) -> list[PdfTable]:
        candidates = list(parsed_pdf.tables)
        for page in parsed_pdf.pages:
            candidates.extend(page.tables)

        seen: set[str] = set()
        result: list[PdfTable] = []
        for table in candidates:
            if table.table_id in seen:
                continue
            seen.add(table.table_id)
            result.append(table)
        return result


__all__ = ["ReportParameterTableExtractor"]
