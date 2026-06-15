from app.domain.common import BoundingBox
from app.domain.pdf import PdfTable


def build_pdf_table(
    rows: list[list[str]],
    *,
    page: int = 1,
    table_id: str = "table-fixture",
    caption: str | None = None,
    table_number: str | None = None,
    extraction_method: str = "fixture",
    metadata: dict[str, object] | None = None,
) -> PdfTable:
    width = max((len(row) for row in rows), default=1)
    height = max(len(rows), 1)
    return PdfTable(
        table_id=table_id,
        page_numbers=[page],
        caption=caption,
        bbox=BoundingBox(x0=0, y0=0, x1=width * 100, y1=height * 20),
        columns=rows[0] if rows else [],
        rows=rows,
        extraction_method=extraction_method,
        metadata={
            "table_number": table_number,
            **dict(metadata or {}),
        },
    )
