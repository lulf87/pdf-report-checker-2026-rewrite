from __future__ import annotations

import re
from collections.abc import Iterable

from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.pdf import ParsedPdf, PdfPage, PdfTable
from app.domain.ptr import (
    PTRClause,
    PTRClauseNumber,
    PTRClauseTaxonomy,
    PTRDocument,
    PTRScopeType,
    PTRTable,
    TableReference,
)
from app.domain.table import CanonicalTable, ParameterRecord
from app.infrastructure.table.table_normalizer import TableNormalizer


CLAUSE_WITH_TITLE_RE = re.compile(r"^(2(?:\.\d+){0,3})(?:(?:[、。]\s*)|\s+)(.+?)\s*$")
CLAUSE_DOT_TITLE_RE = re.compile(r"^(2(?:\.\d+){0,3})[\.．]\s+(.+?)\s*$")
CLAUSE_NUMBER_ONLY_RE = re.compile(r"^(2(?:\.\d+){0,3})\s*$")
TOP_LEVEL_CHAPTER_RE = re.compile(r"^([1-9]\d*)\s*(?:[\.．、。]?\s*)([\u4e00-\u9fffA-Za-z].*)?$")
TABLE_REFERENCE_RE = re.compile(r"(?:见\s*表|符合\s*表|按\s*表|表)\s*([A-Za-z]?\d+(?:\s*[-‑－–—]\s*\d+)?)")
DIRECT_REQUIREMENT_MARKERS = ("应", "不应", "不得", "符合", "至少", "不低于", "不高于", "大于", "小于")


class PTRExtractor:
    """Extract PTR Chapter 2 clauses and table references from parsed PDF data."""

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict
        self.table_normalizer = TableNormalizer()

    def extract(self, parsed_pdf: ParsedPdf) -> PTRDocument:
        chapter_pages = self._find_chapter2_pages(parsed_pdf)
        if not chapter_pages:
            diagnostics = ["chapter_2_not_found"]
            metadata = self._textless_pdf_metadata(parsed_pdf)
            if metadata:
                diagnostics.append("PTR_TEXT_LAYER_MISSING")
            return PTRDocument(
                parsed_pdf=parsed_pdf,
                source_info=parsed_pdf.file_name,
                diagnostics=diagnostics,
                metadata=metadata,
            )

        clauses: list[PTRClause] = []
        page_by_number = {page.page_number: page for page in parsed_pdf.pages}
        previous_clause: PTRClause | None = None
        for page_number in chapter_pages:
            page = page_by_number.get(page_number)
            if page is None:
                continue
            leading_text = self._leading_text_before_first_clause(page)
            if previous_clause is not None and leading_text:
                self._append_clause_text(previous_clause, leading_text)
            page_clauses = self._extract_clauses_from_page(page)
            clauses.extend(page_clauses)
            if page_clauses:
                previous_clause = page_clauses[-1]

        clauses = self._deduplicate_clauses(clauses)
        self._link_hierarchy(clauses)
        self._classify_clauses(clauses)

        tables = self._extract_tables(parsed_pdf, allowed_pages=set(chapter_pages))
        tables = self._merge_continuation_tables(tables)
        self._assign_table_parent_clauses(clauses, tables)
        self._attach_referenced_table_text(clauses, tables)
        table_references = [ref for clause in clauses for ref in clause.table_references]

        return PTRDocument(
            parsed_pdf=parsed_pdf,
            clauses=clauses,
            tables=tables,
            table_references=table_references,
            chapter2_span=(min(chapter_pages), max(chapter_pages)),
            source_info=parsed_pdf.file_name,
        )

    def _find_chapter2_pages(self, parsed_pdf: ParsedPdf) -> list[int]:
        pages: list[int] = []
        started = False
        for page in parsed_pdf.pages:
            lines = [line.strip() for line in (page.text or "").splitlines() if line.strip()]
            has_chapter2 = any(self._is_chapter2_start(line) for line in lines[:12])
            has_deep_chapter2_clause = any(self._parse_clause_line(line) is not None for line in lines)
            has_next_top_chapter = any(self._is_later_top_level_chapter_at(lines, index) for index in range(len(lines)))

            if not started and (has_chapter2 or has_deep_chapter2_clause):
                started = True

            if started:
                pages.append(page.page_number)
                if has_next_top_chapter:
                    break

        return pages

    def _textless_pdf_metadata(self, parsed_pdf: ParsedPdf) -> dict[str, object]:
        if not parsed_pdf.pages:
            return {}
        empty_pages = [page for page in parsed_pdf.pages if not (page.text or "").strip()]
        if len(empty_pages) != len(parsed_pdf.pages):
            return {}
        has_textless_signal = any(
            page.is_textless or any("OCR not run" in diagnostic or "empty page" in diagnostic for diagnostic in page.diagnostics)
            for page in empty_pages
        )
        if not has_textless_signal:
            return {}
        pages_need_ocr = [page.page_number for page in empty_pages]
        return {
            "ptr_extraction_status": "ocr_required",
            "ptr_ocr_required": True,
            "ptr_pages_need_ocr": pages_need_ocr,
            "source_type": "image_only_pdf",
            "textless_page_count": len(empty_pages),
            "page_count": parsed_pdf.page_count or len(parsed_pdf.pages),
        }

    def _is_chapter2_start(self, line: str) -> bool:
        match = TOP_LEVEL_CHAPTER_RE.match(line)
        return bool(match and match.group(1) == "2")

    def _is_later_top_level_chapter(self, line: str) -> bool:
        match = TOP_LEVEL_CHAPTER_RE.match(line)
        if not match or not match.group(1).isdigit() or int(match.group(1)) <= 2:
            return False
        title = (match.group(2) or "").strip()
        if not title:
            return False
        compact = re.sub(r"\s+", "", title)
        return bool(any(keyword in compact for keyword in ("检验方法", "测试方法", "试验方法", "检验", "测试", "试验")))

    def _is_later_top_level_chapter_at(self, lines: list[str], index: int) -> bool:
        line = lines[index] if 0 <= index < len(lines) else ""
        if self._is_later_top_level_chapter(line):
            return True
        match = re.fullmatch(r"([3-9]\d*)", line or "")
        if not match:
            return False
        for next_line in lines[index + 1 : index + 4]:
            compact = re.sub(r"\s+", "", next_line or "")
            if not compact:
                continue
            return bool(any(keyword in compact for keyword in ("检验方法", "测试方法", "试验方法", "检验", "测试", "试验")))
        return False

    def _extract_clauses_from_page(self, page: PdfPage) -> list[PTRClause]:
        clauses: list[PTRClause] = []
        current_number: PTRClauseNumber | None = None
        current_line: str = ""
        current_content: str = ""
        current_buffer: list[str] = []
        current_start_line = 0
        current_refs: dict[str, TableReference] = {}
        pending_number: PTRClauseNumber | None = None
        pending_line = ""
        pending_start_line = 0
        pending_refs: dict[str, TableReference] = {}

        def flush() -> None:
            nonlocal current_number, current_line, current_content, current_buffer, current_refs
            if current_number is None:
                return
            body_text = "\n".join(part for part in current_buffer if part).strip()
            table_refs = list(current_refs.values())
            clauses.append(
                PTRClause(
                    clause_id=f"ptr-{current_number}",
                    number=current_number,
                    title=self._extract_title(current_content),
                    body_text=body_text,
                    normalized_text=None,
                    location=Location(source_type=SourceType.PTR, page_number=page.page_number, section="chapter_2"),
                    table_references=table_refs,
                    table_refs=[ref.table_number for ref in table_refs],
                    evidence=[
                        Evidence(
                            id=f"ptr-{current_number}:page-{page.page_number}:line-{current_start_line}",
                            source_type=SourceType.PTR,
                            location=Location(
                                source_type=SourceType.PTR,
                                page_number=page.page_number,
                                section="chapter_2",
                            ),
                            raw_text=current_line,
                            method=EvidenceMethod.PDF_TEXT,
                        )
                    ],
                )
            )

        lines = [(index, raw_line.strip()) for index, raw_line in enumerate((page.text or "").splitlines()) if raw_line.strip()]
        line_values = [line for _, line in lines]
        for ordinal, (line_index, line) in enumerate(lines):
            if self._is_page_marker(line):
                continue
            if self._is_later_top_level_chapter_at(line_values, ordinal):
                flush()
                current_number = None
                current_buffer = []
                current_refs = {}
                break

            parsed = self._parse_clause_line(line)
            if parsed is not None:
                flush()
                number_text, content, number_only = parsed
                current_number = None
                current_buffer = []
                current_refs = {}
                pending_number = None
                pending_refs = {}
                if number_only:
                    pending_number = PTRClauseNumber.from_string(number_text)
                    pending_line = line
                    pending_start_line = line_index
                    pending_refs = self._extract_table_references(line, pending_number, page.page_number)
                    continue
                current_number = PTRClauseNumber.from_string(number_text)
                current_content = content
                current_line = line
                current_start_line = line_index
                current_buffer = [current_content]
                current_refs = self._extract_table_references(line, current_number, page.page_number)
                continue

            if pending_number is not None:
                current_number = pending_number
                current_content = line
                current_line = f"{pending_line} {line}".strip()
                current_start_line = pending_start_line
                current_buffer = [current_content]
                current_refs = dict(pending_refs)
                for key, ref in self._extract_table_references(line, current_number, page.page_number).items():
                    current_refs.setdefault(key, ref)
                pending_number = None
                pending_refs = {}
                continue

            if current_number is not None:
                current_buffer.append(line)
                for key, ref in self._extract_table_references(line, current_number, page.page_number).items():
                    current_refs.setdefault(key, ref)

        flush()
        return clauses

    def _parse_clause_line(self, line: str) -> tuple[str, str, bool] | None:
        text = (line or "").strip()
        if not text or self._is_page_marker(text):
            return None

        match = CLAUSE_DOT_TITLE_RE.match(text) or CLAUSE_WITH_TITLE_RE.match(text)
        if match:
            number, content = match.group(1), match.group(2).strip()
            if self._looks_like_clause_title(content):
                return number, content, False
            return None

        match = CLAUSE_NUMBER_ONLY_RE.match(text)
        if match:
            return match.group(1), "", True
        return None

    def _looks_like_clause_title(self, value: str) -> bool:
        text = str(value or "").strip()
        compact = re.sub(r"\s+", "", text)
        if not compact:
            return False
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[A-Za-zμΩ°/%]+)?", compact):
            return False
        if re.fullmatch(r"[A-Za-zμΩ°/%]+", compact):
            return False
        return bool(re.search(r"[\u4e00-\u9fff]", text) or len(compact) >= 4)

    def _leading_text_before_first_clause(self, page: PdfPage) -> str:
        values: list[str] = []
        lines = [line.strip() for line in (page.text or "").splitlines() if line.strip()]
        for index, line in enumerate(lines):
            if self._is_page_marker(line):
                continue
            if self._is_later_top_level_chapter_at(lines, index):
                break
            if self._parse_clause_line(line) is not None:
                break
            values.append(line)
        return "\n".join(_unique_non_empty(values))

    def _append_clause_text(self, clause: PTRClause, text: str) -> None:
        addition = str(text or "").strip()
        if not addition or addition in (clause.body_text or ""):
            return
        clause.body_text = "\n".join(part for part in [clause.body_text, addition] if part).strip()
        clause.text_content = clause.body_text
        clause.full_text = f"{clause.number} {clause.body_text}".strip()
        clause.metadata["cross_page_leading_text_attached"] = True

    def _is_page_marker(self, line: str) -> bool:
        return bool(re.fullmatch(r"\d+\s*/\s*\d+", line or ""))

    def _extract_table_references(
        self,
        text: str,
        clause_number: PTRClauseNumber,
        page_number: int,
    ) -> dict[str, TableReference]:
        references: dict[str, TableReference] = {}
        for match in TABLE_REFERENCE_RE.finditer(text or ""):
            number = self._normalize_table_reference_number(match.group(1))
            references[number] = TableReference(
                table_number=number,
                raw_text=text,
                reference_text=f"表 {number}",
                clause_id=f"ptr-{clause_number}",
                location=Location(source_type=SourceType.PTR, page_number=page_number, section="chapter_2"),
            )
        return references

    def _extract_title(self, content: str) -> str:
        text = (content or "").strip()
        if not text:
            return ""
        text = re.split(r"[。；;]", text, maxsplit=1)[0]
        text = re.split(r"(?:应|不应|不得|符合|见表|按表)", text, maxsplit=1)[0]
        return text.strip(" ：:，,。") or (content or "").strip()

    def _normalize_table_reference_number(self, value: str) -> str:
        number = re.sub(r"\s+", "", value or "")
        return number.translate(str.maketrans({"‑": "-", "－": "-", "–": "-", "—": "-"}))

    def _deduplicate_clauses(self, clauses: list[PTRClause]) -> list[PTRClause]:
        best_by_number: dict[str, PTRClause] = {}
        order: list[str] = []
        for clause in clauses:
            key = str(clause.number)
            if key not in best_by_number:
                best_by_number[key] = clause
                order.append(key)
                continue
            if len(clause.body_text.strip()) > len(best_by_number[key].body_text.strip()):
                best_by_number[key] = clause
        return [best_by_number[key] for key in order]

    def _attach_referenced_table_text(self, clauses: list[PTRClause], tables: list[PTRTable]) -> None:
        if not clauses or not tables:
            return
        tables_by_number: dict[str, list[PTRTable]] = {}
        for table in tables:
            number = self._normalize_table_reference_number(table.table_number or "")
            if not number:
                continue
            tables_by_number.setdefault(number, []).append(table)

        for clause in clauses:
            chunks: list[str] = []
            attached_table_ids: list[str] = []
            for table_number in clause.get_all_table_numbers():
                normalized_number = self._normalize_table_reference_number(table_number)
                for table in tables_by_number.get(normalized_number, []):
                    table_text = self._table_text_for_clause_context(table)
                    if not table_text:
                        continue
                    if table_text in (clause.body_text or "") or table_text in chunks:
                        continue
                    chunks.append(table_text)
                    if table.table_id:
                        attached_table_ids.append(table.table_id)
                    if clause.clause_id not in table.referenced_by_clause_ids:
                        table.referenced_by_clause_ids.append(clause.clause_id)
            if not chunks:
                continue
            body_parts = [clause.body_text or "", *chunks]
            clause.body_text = "\n".join(part for part in body_parts if part).strip()
            clause.text_content = clause.body_text
            clause.full_text = f"{clause.number} {clause.body_text}".strip()
            clause.metadata["referenced_table_text_attached"] = True
            clause.metadata["referenced_table_ids"] = attached_table_ids

    def _table_text_for_clause_context(self, table: PTRTable) -> str:
        values: list[str] = []
        values.extend([table.caption, table.title])
        canonical = table.canonical_table
        if canonical is not None:
            for row in canonical.header_rows:
                values.append(" / ".join(cell for cell in row if cell))
            cell_rows: dict[int, list[tuple[int, str]]] = {}
            for cell in canonical.cells:
                text = str(cell.text or "").strip()
                if not text:
                    continue
                cell_rows.setdefault(cell.row_index, []).append((cell.column_index, text))
            for row_index in sorted(cell_rows):
                row_text = " / ".join(text for _, text in sorted(cell_rows[row_index]))
                if row_text:
                    values.append(row_text)
            for record in canonical.parameter_records:
                record_parts: list[str] = []
                record_parts.extend(record.parameter_path)
                record_parts.extend([record.parameter_name, record.raw_name, record.raw_value, record.normalized_value, record.unit])
                record_parts.extend(f"{key}:{value}" for key, value in record.dimensions.items())
                record_parts.extend(f"{key}:{value}" for key, value in record.conditions.items())
                record_parts.extend(f"{key}:{value}" for key, value in record.values.items())
                values.append(" / ".join(str(part) for part in record_parts if str(part or "").strip()))
        return "\n".join(_unique_non_empty(values))

    def _link_hierarchy(self, clauses: list[PTRClause]) -> None:
        by_number = {str(clause.number): clause for clause in clauses}
        for clause in clauses:
            clause.children_ids = []
            parent_number = clause.number.parent()
            if parent_number is None:
                clause.parent_id = None
                continue
            parent = by_number.get(str(parent_number))
            if parent is None:
                clause.parent_id = None
                continue
            clause.parent_id = parent.clause_id
            if clause.clause_id not in parent.children_ids:
                parent.children_ids.append(clause.clause_id)

    def _classify_clauses(self, clauses: list[PTRClause]) -> None:
        for clause in clauses:
            scope_type = self._infer_scope_type(clause)
            self._set_scope_type(clause, scope_type)

        for clause in clauses:
            if clause.children_ids and clause.scope_type == PTRScopeType.REQUIREMENT:
                compact = re.sub(r"\s+", "", clause.body_text or "")
                if not any(marker in compact for marker in DIRECT_REQUIREMENT_MARKERS):
                    self._set_scope_type(clause, PTRScopeType.GROUP_CLAUSE)

    def _infer_scope_type(self, clause: PTRClause) -> PTRScopeType:
        compact = re.sub(r"\s+", "", clause.body_text or clause.title or "")
        if str(clause.number) == "2":
            return PTRScopeType.INFORMATIONAL
        has_direct_requirement = any(marker in compact for marker in DIRECT_REQUIREMENT_MARKERS)
        if ("附录" in compact or "appendix" in compact.lower()) and not has_direct_requirement:
            return PTRScopeType.APPENDIX
        if compact.startswith(("注:", "注：", "说明:", "说明：", "图")) or "图示仅作参考" in compact:
            return PTRScopeType.INFORMATIONAL
        if any(keyword in compact for keyword in ("检验方法", "试验方法", "检测方法", "测试方法")):
            return PTRScopeType.TEST_METHOD
        if re.search(r"\b(?:GB|GB/T|YY|YY/T)\s*\d", compact, re.IGNORECASE) and not any(
            marker in compact for marker in ("应符合", "应满足", "应按")
        ):
            return PTRScopeType.EXTERNAL_STANDARD
        return PTRScopeType.REQUIREMENT

    def _set_scope_type(self, clause: PTRClause, scope_type: PTRScopeType) -> None:
        clause.scope_type = scope_type
        taxonomy_map = {
            PTRScopeType.REQUIREMENT: PTRClauseTaxonomy.REQUIREMENT,
            PTRScopeType.TEST_METHOD: PTRClauseTaxonomy.METHOD,
            PTRScopeType.APPENDIX: PTRClauseTaxonomy.APPENDIX,
            PTRScopeType.INFORMATIONAL: PTRClauseTaxonomy.NOTE,
            PTRScopeType.EXTERNAL_STANDARD: PTRClauseTaxonomy.EXTERNAL_STANDARD,
            PTRScopeType.GROUP_CLAUSE: PTRClauseTaxonomy.GROUP_HEADING,
            PTRScopeType.TABLE_REFERENCE: PTRClauseTaxonomy.TABLE_REFERENCE,
        }
        clause.taxonomy = taxonomy_map[scope_type]

    def _extract_tables(self, parsed_pdf: ParsedPdf, *, allowed_pages: set[int] | None = None) -> list[PTRTable]:
        raw_tables = list(parsed_pdf.tables)
        for page in parsed_pdf.pages:
            raw_tables.extend(page.tables)

        page_by_number = {page.page_number: page for page in parsed_pdf.pages}
        seen: set[str] = set()
        tables: list[PTRTable] = []
        for table in raw_tables:
            if table.table_id in seen:
                continue
            table_pages = set(table.page_numbers or [])
            if allowed_pages is not None and table_pages and not (table_pages & allowed_pages):
                continue
            seen.add(table.table_id)
            page_number = min(table.page_numbers) if table.page_numbers else None
            page = page_by_number.get(page_number) if page_number is not None else None
            tables.append(self._convert_pdf_table(table, page=page))
        return tables

    def _convert_pdf_table(self, table: PdfTable, *, page: PdfPage | None = None) -> PTRTable:
        caption = table.caption or table.title or self._nearby_table_caption(table, page)
        table_number = self._extract_table_number_from_text(caption) or self._extract_table_number(table)
        normalized_source = table.model_copy(
            update={
                "caption": caption,
                "title": caption or table.title,
                "metadata": {**dict(table.metadata or {}), "table_number": table_number},
            }
        )
        canonical = self.table_normalizer.normalize(normalized_source)
        canonical.parameter_records = self._merge_parameter_record_fragments(list(canonical.parameter_records))
        page_span = self._page_span_for_pdf_table(table)
        return PTRTable(
            table_id=table.table_id,
            table_number=table_number,
            title=caption,
            canonical_table=canonical,
            page_span=page_span,
            evidence=[
                Evidence(
                    id=f"{table.table_id}:table",
                    source_type=SourceType.PTR,
                    location=Location(source_type=SourceType.PTR, page_number=page_span[0], table_id=table.table_id),
                    raw_text=caption or table_number or "",
                    method=EvidenceMethod.PDF_LAYOUT,
                )
            ],
            metadata={
                "y0": table.bbox.y0 if table.bbox else 0.0,
                "y1": table.bbox.y1 if table.bbox else 0.0,
                "page_height": page.height if page is not None else None,
                "raw_rows": [list(row) for row in table.rows],
                "raw_columns": list(table.columns),
                "page_numbers": list(table.page_numbers),
                **dict(table.metadata or {}),
            },
        )

    def _nearby_table_caption(self, table: PdfTable, page: PdfPage | None) -> str | None:
        if page is None or table.bbox is None:
            return None
        blocks = [block for block in page.text_blocks if block.bbox is not None and block.text.strip()]
        blocks.sort(key=lambda block: (block.bbox.y0, block.bbox.x0))
        lines: list[list] = []
        for block in blocks:
            if not lines:
                lines.append([block])
                continue
            line_y = sum(item.bbox.y0 for item in lines[-1]) / len(lines[-1])
            if abs(block.bbox.y0 - line_y) <= 3:
                lines[-1].append(block)
            else:
                lines.append([block])

        candidates: list[tuple[float, str]] = []
        for line in lines:
            ordered = sorted(line, key=lambda item: item.bbox.x0)
            line_bottom = max(item.bbox.y1 for item in ordered)
            gap = table.bbox.y0 - line_bottom
            if gap < -1 or gap > 36:
                continue
            text = re.sub(r"\s+", " ", "".join(item.text for item in ordered)).strip()
            if re.search(r"(?:续\s*)?表\s*[A-Za-z]?\d+(?:\s*[-‑－–—]\s*\d+)?", text):
                candidates.append((gap, text))
        return min(candidates, key=lambda item: item[0])[1] if candidates else None

    def _extract_table_number_from_text(self, text: str | None) -> str | None:
        match = re.search(r"(?:续\s*)?表\s*([A-Za-z]?\d+(?:\s*[-‑－–—]\s*\d+)?)", text or "")
        return self._normalize_table_reference_number(match.group(1)) if match else None

    def _extract_table_number(self, table: PdfTable) -> str | None:
        raw = table.metadata.get("table_number") if table.metadata else None
        if raw is not None and str(raw).strip():
            return str(raw).strip()
        for text in (table.caption, table.title):
            match = re.search(r"表\s*([A-Za-z]?\d+)", text or "")
            if match:
                return match.group(1)
        return None

    def _assign_table_parent_clauses(self, clauses: list[PTRClause], tables: list[PTRTable]) -> None:
        for table in tables:
            table_number = self._normalize_table_reference_number(table.table_number or "")
            if not table_number:
                continue
            page = (table.page_span or (None, None))[0]
            candidates = []
            for clause in clauses:
                if clause.location is None or clause.location.page_number != page:
                    continue
                compact_body = re.sub(r"\s+", "", clause.body_text or "")
                if re.search(rf"表{re.escape(table_number)}(?:\D|$)", compact_body):
                    candidates.append(clause)
            if not candidates:
                continue
            parent = max(candidates, key=lambda clause: len(clause.number.parts))
            table.metadata["parent_clause"] = str(parent.number)
            table.metadata["parent_clause_id"] = parent.clause_id

    def _page_span_for_pdf_table(self, table: PdfTable) -> tuple[int, int]:
        pages = table.page_numbers or []
        if pages:
            return (min(pages), max(pages))
        return (1, 1)

    def _merge_continuation_tables(self, tables: list[PTRTable]) -> list[PTRTable]:
        if not tables:
            return []

        ordered = sorted(tables, key=lambda table: ((table.page_span or (0, 0))[0], float(table.metadata.get("y0", 0.0))))
        merged: list[PTRTable] = []
        for table in ordered:
            if not merged:
                merged.append(table)
                continue
            previous = merged[-1]
            is_continuation, reason = self._assess_table_continuation(previous, table)
            if is_continuation:
                self._merge_table_into(previous, table, reason)
                continue
            table.metadata["continuation_reject_reason"] = reason
            merged.append(table)
        return merged

    def _assess_table_continuation(self, previous: PTRTable, current: PTRTable) -> tuple[bool, str]:
        previous_span = previous.page_span or (0, 0)
        current_span = current.page_span or (0, 0)
        page_gap = current_span[0] - previous_span[1]
        if page_gap < 0 or page_gap > 1:
            return False, "page_gap_invalid"
        if previous.table_number and current.table_number and previous.table_number != current.table_number:
            return False, "table_number_conflict"
        if previous.table_number and current.table_number == previous.table_number:
            return True, "same_table_number"
        if current.table_number is not None:
            return False, "current_has_table_number"

        overlap = self._header_overlap(previous, current)
        previous_y1 = float(previous.metadata.get("y1", 0.0) or 0.0)
        previous_page_height = float(previous.metadata.get("page_height", 0.0) or 0.0)
        previous_near_bottom = (
            previous_y1 >= previous_page_height - 120.0
            if previous_page_height > 0
            else float(previous.metadata.get("y0", 0.0)) >= 450.0
        )
        position_bridge = previous_near_bottom and float(current.metadata.get("y0", 0.0)) <= 150.0
        if overlap >= 0.95:
            return True, "same_header_continuation"
        if position_bridge and overlap >= 0.55:
            return True, "top_bottom_with_header_overlap"
        previous_column_count = self._table_column_count(previous)
        current_column_count = self._table_column_count(current)
        if (
            position_bridge
            and previous.table_number
            and previous_column_count > 0
            and previous_column_count == current_column_count
        ):
            return True, "top_bottom_with_matching_column_count"
        if overlap < 0.35:
            return False, "header_mismatch"
        return False, "missing_table_number_without_strong_evidence"

    def _table_column_count(self, table: PTRTable) -> int:
        raw_rows = table.metadata.get("raw_rows")
        if isinstance(raw_rows, list):
            count = max((len(row) for row in raw_rows if isinstance(row, list)), default=0)
            if count > 0:
                return count
        canonical = table.canonical_table
        if canonical is None:
            return 0
        if canonical.header_rows:
            return max((len(row) for row in canonical.header_rows), default=0)
        if canonical.headers:
            return max((header.column_count for header in canonical.headers), default=0)
        return len(canonical.columns)

    def _header_overlap(self, previous: PTRTable, current: PTRTable) -> float:
        left = set(self._header_tokens(previous))
        right = set(self._header_tokens(current))
        if not left or not right:
            return 0.0
        return len(left & right) / min(len(left), len(right))

    def _header_tokens(self, table: PTRTable) -> list[str]:
        canonical = table.canonical_table
        if canonical is None:
            return []
        labels: list[str] = []
        if canonical.header_rows:
            for row in canonical.header_rows:
                labels.extend(row)
        elif canonical.headers:
            labels.extend(label for path in canonical.headers[0].column_paths for label in path)
        elif canonical.columns:
            labels.extend(column.name for column in canonical.columns)
        return [re.sub(r"\s+", "", label) for label in labels if re.sub(r"\s+", "", label)]

    def _merge_table_into(self, base: PTRTable, fragment: PTRTable, reason: str) -> None:
        base_start, base_end = base.page_span or (0, 0)
        frag_start, frag_end = fragment.page_span or (0, 0)
        base.page_span = (base_start or frag_start, max(base_end, frag_end))
        if base.table_number is None:
            base.table_number = fragment.table_number

        base_rows = [list(row) for row in base.metadata.get("raw_rows", []) if isinstance(row, list)]
        fragment_rows = [list(row) for row in fragment.metadata.get("raw_rows", []) if isinstance(row, list)]
        if base_rows and fragment_rows:
            if fragment_rows[0] == base_rows[0]:
                fragment_rows = fragment_rows[1:]
            combined_rows = [*base_rows, *fragment_rows]
            page_numbers = _unique_ints(
                [
                    *[int(page) for page in base.metadata.get("page_numbers", []) if str(page).isdigit()],
                    *[int(page) for page in fragment.metadata.get("page_numbers", []) if str(page).isdigit()],
                ]
            )
            normalized_source = PdfTable(
                table_id=base.table_id or "merged-ptr-table",
                page_numbers=page_numbers,
                title=base.title,
                caption=base.title,
                columns=list(base.metadata.get("raw_columns", [])),
                rows=combined_rows,
                extraction_method="pymupdf_merged_continuation",
                metadata={"table_number": base.table_number, "continuation_of": base.table_id},
            )
            base.canonical_table = self.table_normalizer.normalize(normalized_source)
            base.canonical_table.parameter_records = self._merge_parameter_record_fragments(
                list(base.canonical_table.parameter_records)
            )
            base.canonical_table.diagnostics.append(f"merged continuation table {fragment.table_id}")
            base.metadata["raw_rows"] = combined_rows
            base.metadata["page_numbers"] = page_numbers
        elif base.canonical_table is not None and fragment.canonical_table is not None:
            base_records = list(base.canonical_table.parameter_records)
            seen = {self._record_identity(record) for record in base_records}
            for record in fragment.canonical_table.parameter_records:
                key = self._record_identity(record)
                if key in seen:
                    continue
                base_records.append(record)
                seen.add(key)
            base.canonical_table.parameter_records = base_records
            base.canonical_table.diagnostics.append(f"merged continuation table {fragment.table_id}")

        base.metadata.setdefault("merged_from_tables", []).append(fragment.table_id)
        base.metadata.setdefault("continuation_merge_reasons", []).append({"table_id": fragment.table_id, "reason": reason})
        base.metadata["continuation_reason"] = reason

    def _record_identity(self, record: ParameterRecord) -> tuple[str, tuple[tuple[str, str], ...]]:
        return (
            re.sub(r"\s+", "", record.parameter_name or ""),
            tuple(sorted((str(key), str(value)) for key, value in record.dimensions.items())),
        )

    def _merge_parameter_record_fragments(self, records: list[ParameterRecord]) -> list[ParameterRecord]:
        merged: list[ParameterRecord] = []
        by_identity: dict[tuple[str, tuple[tuple[str, str], ...]], ParameterRecord] = {}
        for record in records:
            identity = self._record_identity(record)
            existing = by_identity.get(identity)
            if existing is None:
                copied = record.model_copy(deep=True)
                by_identity[identity] = copied
                merged.append(copied)
                continue
            for column, value in record.values.items():
                current = existing.values.get(column, "")
                if not current:
                    existing.values[column] = value
                elif value and value not in current:
                    existing.values[column] = f"{current}\n{value}"
            existing.source_rows = _unique_ints([*existing.source_rows, *record.source_rows])
        return merged


def _unique_non_empty(values: Iterable[str | None]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in result:
            continue
        result.append(text)
    return result


def _unique_ints(values: Iterable[int]) -> list[int]:
    result: list[int] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def extract_ptr(parsed_pdf: ParsedPdf) -> PTRDocument:
    return PTRExtractor().extract(parsed_pdf)
