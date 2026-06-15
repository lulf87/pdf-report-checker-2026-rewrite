from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import fitz

from app.domain.common import BoundingBox
from app.domain.pdf import ParsedPdf, PdfPage, PdfTable, PdfTextBlock, PdfWord

logger = logging.getLogger(__name__)

TEXT_DENSITY_THRESHOLD = 50


class PdfParserError(RuntimeError):
    """Base exception for infrastructure PDF parsing failures."""


class InvalidPdfError(PdfParserError):
    """Raised when a file has a PDF extension but PyMuPDF cannot open it."""


class PyMuPDFParser:
    """Extract structural PDF content into stable domain models.

    This adapter intentionally does not run OCR and does not evaluate report
    checking rules. Low-text pages are only marked with diagnostics so the
    application layer can decide whether an OCR adapter should be invoked.
    """

    def __init__(
        self,
        *,
        text_density_threshold: int = TEXT_DENSITY_THRESHOLD,
        extract_tables: bool = True,
    ) -> None:
        self.text_density_threshold = text_density_threshold
        self.extract_tables = extract_tables

    def parse(self, file_path: str | Path) -> ParsedPdf:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported")

        try:
            doc = fitz.open(str(path))
        except Exception as exc:  # pragma: no cover - exact PyMuPDF class varies
            raise InvalidPdfError(f"Invalid PDF file: {path.name}") from exc

        try:
            parsed = self._parse_document(path, doc)
        finally:
            doc.close()

        return parsed

    def _parse_document(self, path: Path, doc: fitz.Document) -> ParsedPdf:
        pages: list[PdfPage] = []
        tables: list[PdfTable] = []
        diagnostics: list[str] = []

        if doc.page_count == 0:
            diagnostics.append("PDF has no pages")

        for page_index in range(doc.page_count):
            page_number = page_index + 1
            page = doc[page_index]
            parsed_page = self._parse_page(page, page_number)
            pages.append(parsed_page)
            tables.extend(parsed_page.tables)

            if parsed_page.diagnostics:
                diagnostics.extend(
                    f"Page {page_number}: {diagnostic}" for diagnostic in parsed_page.diagnostics
                )

        full_text = "\n".join(page.text for page in pages)
        return ParsedPdf(
            file_id=self._file_digest(path),
            file_name=path.name,
            page_count=doc.page_count,
            pages=pages,
            tables=tables,
            text_digest=hashlib.sha256(full_text.encode("utf-8")).hexdigest() if full_text else None,
            diagnostics=diagnostics,
        )

    def _parse_page(self, page: fitz.Page, page_number: int) -> PdfPage:
        rect = page.rect
        text = page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) or ""
        text_blocks = self._extract_text_blocks(page, page_number)
        words = self._extract_words(page)
        images = self._extract_images(page)
        drawings = self._extract_drawings(page)

        diagnostics: list[str] = []
        stripped_len = len(text.strip())
        is_textless = stripped_len < self.text_density_threshold
        if not text.strip():
            diagnostics.append("empty page: no text extracted; OCR not run")
        elif is_textless:
            diagnostics.append(
                f"low text density ({stripped_len} chars < {self.text_density_threshold}); "
                "OCR not run"
            )

        tables: list[PdfTable] = []
        if self.extract_tables:
            tables = self._extract_tables(page, page_number, words, diagnostics)

        return PdfPage(
            page_number=page_number,
            width=rect.width,
            height=rect.height,
            text=text,
            text_blocks=text_blocks,
            words=words,
            tables=tables,
            images=images,
            drawings=drawings,
            is_textless=is_textless,
            diagnostics=diagnostics,
        )

    def _extract_text_blocks(self, page: fitz.Page, page_number: int) -> list[PdfTextBlock]:
        try:
            raw_blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get("blocks", [])
        except Exception as exc:
            logger.warning("Failed to extract text blocks on page %s: %s", page_number, exc)
            return []

        text_blocks: list[PdfTextBlock] = []
        for block_index, block in enumerate(raw_blocks):
            for line_index, line in enumerate(block.get("lines", [])):
                for span_index, span in enumerate(line.get("spans", [])):
                    text = str(span.get("text", ""))
                    if not text.strip():
                        continue
                    flags = int(span.get("flags", 0) or 0)
                    text_blocks.append(
                        PdfTextBlock(
                            text=text,
                            bbox=self._bbox_from_tuple(span.get("bbox")),
                            page_number=page_number,
                            font_size=float(span["size"]) if span.get("size") is not None else None,
                            font_name=str(span.get("font", "")),
                            is_bold=bool(flags & 2**4),
                            block_index=block_index,
                            line_index=line_index,
                            span_index=span_index,
                            metadata={"source": "pymupdf_span"},
                        )
                    )
        return text_blocks

    def _extract_words(self, page: fitz.Page) -> list[PdfWord]:
        words: list[PdfWord] = []
        for raw_word in page.get_text("words") or []:
            if len(raw_word) < 5:
                continue
            word_text = str(raw_word[4])
            if not word_text.strip():
                continue
            words.append(
                PdfWord(
                    text=word_text,
                    bbox=self._bbox_from_tuple(raw_word[:4]),
                    block_index=self._safe_int(raw_word, 5),
                    line_index=self._safe_int(raw_word, 6),
                    word_index=self._safe_int(raw_word, 7),
                )
            )
        return words

    def _extract_images(self, page: fitz.Page) -> list[dict[str, Any]]:
        images: list[dict[str, Any]] = []
        for image_index, image in enumerate(page.get_images(full=True) or []):
            images.append(
                {
                    "index": image_index,
                    "xref": image[0] if len(image) > 0 else None,
                    "width": image[2] if len(image) > 2 else None,
                    "height": image[3] if len(image) > 3 else None,
                    "bpc": image[4] if len(image) > 4 else None,
                    "colorspace": image[5] if len(image) > 5 else None,
                    "extension": image[7] if len(image) > 7 else None,
                }
            )
        return images

    def _extract_drawings(self, page: fitz.Page) -> list[dict[str, Any]]:
        drawings: list[dict[str, Any]] = []
        for drawing_index, drawing in enumerate(page.get_drawings() or []):
            rect = drawing.get("rect")
            drawings.append(
                {
                    "index": drawing_index,
                    "bbox": self._dump_bbox(self._bbox_from_rect(rect)),
                    "width": drawing.get("width"),
                    "fill": self._jsonable(drawing.get("fill")),
                    "color": self._jsonable(drawing.get("color")),
                    "item_count": len(drawing.get("items", []) or []),
                }
            )
        return drawings

    def _extract_tables(
        self,
        page: fitz.Page,
        page_number: int,
        words: list[PdfWord],
        diagnostics: list[str],
    ) -> list[PdfTable]:
        tables: list[PdfTable] = []
        try:
            table_finder = page.find_tables()
            found_tables = getattr(table_finder, "tables", []) or []
        except Exception as exc:
            diagnostics.append(f"table extraction unavailable: {exc}")
            found_tables = []

        for table_index, table in enumerate(found_tables):
            parsed_table = self._table_from_pymupdf(table, page_number, table_index)
            if parsed_table is not None:
                tables.append(parsed_table)

        if not tables:
            heuristic_table = self._table_from_text_lines(words, page_number)
            if heuristic_table is not None:
                tables.append(heuristic_table)

        return tables

    def _table_from_pymupdf(
        self,
        table: Any,
        page_number: int,
        table_index: int,
    ) -> PdfTable | None:
        extracted_rows = table.extract() if hasattr(table, "extract") else []
        if extracted_rows is None:
            extracted_rows = []

        rows = [
            [str(cell) if cell is not None else "" for cell in row]
            for row in extracted_rows
            if isinstance(row, list) and any(str(cell or "").strip() for cell in row)
        ]
        if not rows:
            return None

        header_names = getattr(getattr(table, "header", None), "names", None)
        if isinstance(header_names, list) and any(str(item or "").strip() for item in header_names):
            columns = [str(name) if name is not None else "" for name in header_names]
        else:
            columns = rows[0]

        return PdfTable(
            table_id=f"p{page_number}-t{table_index + 1}",
            page_numbers=[page_number],
            bbox=self._bbox_from_rect(getattr(table, "bbox", None)),
            columns=columns,
            rows=rows,
            extraction_method="pymupdf",
            confidence="medium",
            metadata={
                "row_count": len(rows),
                "column_count": max((len(row) for row in rows), default=0),
            },
        )

    def _table_from_text_lines(self, words: list[PdfWord], page_number: int) -> PdfTable | None:
        line_rows: list[tuple[list[str], list[BoundingBox]]] = []
        for line_words in self._group_words_by_visual_line(words):
            ordered = sorted(line_words, key=lambda word: word.bbox.x0 if word.bbox else 0)
            if len(ordered) < 2:
                continue
            bboxes = [word.bbox for word in ordered if word.bbox is not None]
            if len(bboxes) < 2:
                continue
            horizontal_span = max(box.x1 for box in bboxes) - min(box.x0 for box in bboxes)
            if horizontal_span < 40:
                continue
            line_rows.append(([word.text for word in ordered], bboxes))

        if len(line_rows) < 2:
            return None

        most_common_width = max(
            {len(row): sum(1 for candidate, _ in line_rows if len(candidate) == len(row)) for row, _ in line_rows},
            key=lambda width: sum(1 for candidate, _ in line_rows if len(candidate) == width),
        )
        rows = [row for row, _ in line_rows if len(row) == most_common_width]
        bboxes = [box for row, boxes in line_rows if len(row) == most_common_width for box in boxes]
        if len(rows) < 2 or not bboxes:
            return None

        bbox = BoundingBox(
            x0=min(box.x0 for box in bboxes),
            y0=min(box.y0 for box in bboxes),
            x1=max(box.x1 for box in bboxes),
            y1=max(box.y1 for box in bboxes),
        )
        return PdfTable(
            table_id=f"p{page_number}-text-table-1",
            page_numbers=[page_number],
            bbox=bbox,
            columns=rows[0],
            rows=rows,
            extraction_method="text_line_heuristic",
            confidence="low",
            diagnostics=["table candidate inferred from aligned text lines"],
            metadata={
                "row_count": len(rows),
                "column_count": most_common_width,
            },
        )

    def _group_words_by_visual_line(self, words: list[PdfWord]) -> list[list[PdfWord]]:
        positioned = [word for word in words if word.bbox is not None]
        positioned.sort(key=lambda word: (word.bbox.y0, word.bbox.x0))

        groups: list[list[PdfWord]] = []
        for word in positioned:
            if not groups:
                groups.append([word])
                continue

            current_group = groups[-1]
            current_y = sum(item.bbox.y0 for item in current_group if item.bbox is not None) / len(
                current_group
            )
            if abs(word.bbox.y0 - current_y) <= 3:
                current_group.append(word)
            else:
                groups.append([word])

        return groups

    def _file_digest(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()[:16]

    def _bbox_from_tuple(self, value: Any) -> BoundingBox | None:
        if value is None:
            return None
        try:
            x0, y0, x1, y1 = value[:4]
        except (TypeError, ValueError):
            return None
        return BoundingBox(x0=float(x0), y0=float(y0), x1=float(x1), y1=float(y1))

    def _bbox_from_rect(self, value: Any) -> BoundingBox | None:
        if value is None:
            return None
        if isinstance(value, BoundingBox):
            return value
        if isinstance(value, fitz.Rect):
            return BoundingBox(x0=value.x0, y0=value.y0, x1=value.x1, y1=value.y1)
        return self._bbox_from_tuple(value)

    def _dump_bbox(self, value: BoundingBox | None) -> dict[str, float] | None:
        if value is None:
            return None
        return value.model_dump(mode="json")

    def _jsonable(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (tuple, list)):
            return [self._jsonable(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._jsonable(item) for key, item in value.items()}
        return str(value)

    def _safe_int(self, values: Any, index: int) -> int | None:
        try:
            return int(values[index])
        except (IndexError, TypeError, ValueError):
            return None


def parse_pdf(file_path: str | Path, **parser_options: Any) -> ParsedPdf:
    return PyMuPDFParser(**parser_options).parse(file_path)
