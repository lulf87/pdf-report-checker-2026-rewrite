from pathlib import Path
from collections.abc import Callable

import fitz
import pytest

from app.domain.pdf import ParsedPdf, PdfTable, PdfTextBlock
from app.infrastructure.pdf.pymupdf_parser import InvalidPdfError, PyMuPDFParser, parse_pdf


def _save_pdf(path: Path, pages: list[Callable[[fitz.Page], None]]) -> Path:
    doc = fitz.open()
    try:
        for build_page in pages:
            page = doc.new_page(width=240, height=180)
            build_page(page)
        doc.save(path)
    finally:
        doc.close()
    return path


def test_parse_pdf_extracts_pages_dimensions_text_blocks_and_words(tmp_path: Path) -> None:
    pdf_path = _save_pdf(
        tmp_path / "report.pdf",
        [
            lambda page: page.insert_text(
                (24, 36),
                "Report Header\nSample Name ABC-1",
                fontsize=11,
            )
        ],
    )

    parsed = PyMuPDFParser(text_density_threshold=5).parse(pdf_path)

    assert isinstance(parsed, ParsedPdf)
    assert parsed.file_name == "report.pdf"
    assert parsed.page_count == 1
    assert parsed.text_digest
    assert parsed.diagnostics == []

    page = parsed.pages[0]
    assert page.page_number == 1
    assert page.width == pytest.approx(240)
    assert page.height == pytest.approx(180)
    assert "Sample Name ABC-1" in page.text
    assert page.is_textless is False
    assert page.text_blocks
    assert isinstance(page.text_blocks[0], PdfTextBlock)
    assert page.text_blocks[0].bbox is not None
    assert any(word.text == "Sample" for word in page.words)


def test_low_text_page_is_marked_for_future_ocr_without_running_ocr(tmp_path: Path) -> None:
    pdf_path = _save_pdf(
        tmp_path / "scan-like.pdf",
        [lambda page: page.insert_text((24, 36), "x", fontsize=11)],
    )

    parsed = PyMuPDFParser(text_density_threshold=20).parse(pdf_path)

    page = parsed.pages[0]
    assert page.is_textless is True
    assert any("OCR not run" in diagnostic for diagnostic in page.diagnostics)
    assert any("low text density" in diagnostic for diagnostic in parsed.diagnostics)


def test_table_candidates_are_extracted_as_pdf_tables(tmp_path: Path) -> None:
    def build_table_page(page: fitz.Page) -> None:
        page.insert_text((24, 36), "Param", fontsize=11)
        page.insert_text((118, 36), "Value", fontsize=11)
        page.insert_text((24, 58), "Voltage", fontsize=11)
        page.insert_text((118, 58), "220V", fontsize=11)

    pdf_path = _save_pdf(tmp_path / "table.pdf", [build_table_page])

    parsed = PyMuPDFParser(text_density_threshold=5).parse(pdf_path)

    assert parsed.tables
    table = parsed.tables[0]
    assert isinstance(table, PdfTable)
    assert table.page_numbers == [1]
    assert table.extraction_method in {"pymupdf", "text_line_heuristic"}
    assert ["Param", "Value"] in table.rows
    assert ["Voltage", "220V"] in table.rows
    assert table.bbox is not None


def test_page_drawings_are_summarized_without_rule_judgement(tmp_path: Path) -> None:
    def build_drawn_page(page: fitz.Page) -> None:
        page.insert_text((24, 36), "Drawn layout", fontsize=11)
        page.draw_rect(fitz.Rect(24, 60, 160, 120), width=1)

    pdf_path = _save_pdf(tmp_path / "drawings.pdf", [build_drawn_page])

    parsed = PyMuPDFParser(text_density_threshold=5).parse(pdf_path)

    assert parsed.pages[0].drawings
    assert parsed.pages[0].drawings[0]["bbox"] is not None
    assert "finding" not in parsed.pages[0].drawings[0]


def test_parse_pdf_convenience_function_uses_pymupdf_parser(tmp_path: Path) -> None:
    pdf_path = _save_pdf(
        tmp_path / "convenience.pdf",
        [lambda page: page.insert_text((24, 36), "Convenience parser", fontsize=11)],
    )

    parsed = parse_pdf(pdf_path, text_density_threshold=5)

    assert isinstance(parsed, ParsedPdf)
    assert parsed.pages[0].text.strip()


def test_missing_non_pdf_and_invalid_pdf_errors_are_readable(tmp_path: Path) -> None:
    parser = PyMuPDFParser()

    with pytest.raises(FileNotFoundError):
        parser.parse(tmp_path / "missing.pdf")

    text_path = tmp_path / "not-pdf.txt"
    text_path.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(ValueError, match="Only PDF files are supported"):
        parser.parse(text_path)

    invalid_path = tmp_path / "broken.pdf"
    invalid_path.write_bytes(b"%PDF-1.7\nnot really a pdf")
    with pytest.raises(InvalidPdfError, match="Invalid PDF file"):
        parser.parse(invalid_path)


def test_empty_page_keeps_document_parseable_with_page_diagnostic(tmp_path: Path) -> None:
    pdf_path = _save_pdf(tmp_path / "empty-page.pdf", [lambda page: None])

    parsed = PyMuPDFParser(text_density_threshold=5).parse(pdf_path)

    assert parsed.page_count == 1
    assert parsed.pages[0].text == ""
    assert parsed.pages[0].is_textless is True
    assert any("empty page" in diagnostic for diagnostic in parsed.pages[0].diagnostics)
