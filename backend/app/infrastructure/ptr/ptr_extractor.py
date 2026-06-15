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


CLAUSE_LINE_RE = re.compile(r"^(2(?:\.\d+){0,3})(?:[\.．、。]?\s*)(.+?)\s*$")
TOP_LEVEL_CHAPTER_RE = re.compile(r"^([1-9]\d*)\s*(?:[\.．、。]?\s*)([\u4e00-\u9fffA-Za-z].*)?$")
TABLE_REFERENCE_RE = re.compile(r"(?:见\s*表|符合\s*表|按\s*表|表)\s*([A-Za-z]?\d+(?:\s*[-－—]\s*\d+)?)")
DIRECT_REQUIREMENT_MARKERS = ("应", "不应", "不得", "符合", "至少", "不低于", "不高于", "大于", "小于")


class PTRExtractor:
    """Extract PTR Chapter 2 clauses and table references from parsed PDF data."""

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict
        self.table_normalizer = TableNormalizer()

    def extract(self, parsed_pdf: ParsedPdf) -> PTRDocument:
        chapter_pages = self._find_chapter2_pages(parsed_pdf)
        if not chapter_pages:
            return PTRDocument(parsed_pdf=parsed_pdf, source_info=parsed_pdf.file_name, diagnostics=["chapter_2_not_found"])

        clauses: list[PTRClause] = []
        page_by_number = {page.page_number: page for page in parsed_pdf.pages}
        for page_number in chapter_pages:
            page = page_by_number.get(page_number)
            if page is None:
                continue
            clauses.extend(self._extract_clauses_from_page(page))

        clauses = self._deduplicate_clauses(clauses)
        self._link_hierarchy(clauses)
        self._classify_clauses(clauses)

        tables = self._extract_tables(parsed_pdf)
        tables = self._merge_continuation_tables(tables)
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
            has_deep_chapter2_clause = any(re.match(r"^2\.\d+(?:\.\d+)*", line) for line in lines)
            has_next_top_chapter = any(self._is_later_top_level_chapter(line) for line in lines[:12])

            if not started and (has_chapter2 or has_deep_chapter2_clause):
                started = True

            if started:
                pages.append(page.page_number)
                if has_next_top_chapter:
                    break

        return pages

    def _is_chapter2_start(self, line: str) -> bool:
        match = TOP_LEVEL_CHAPTER_RE.match(line)
        return bool(match and match.group(1) == "2")

    def _is_later_top_level_chapter(self, line: str) -> bool:
        match = TOP_LEVEL_CHAPTER_RE.match(line)
        return bool(match and match.group(1).isdigit() and int(match.group(1)) > 2)

    def _extract_clauses_from_page(self, page: PdfPage) -> list[PTRClause]:
        clauses: list[PTRClause] = []
        current_number: PTRClauseNumber | None = None
        current_line: str = ""
        current_content: str = ""
        current_buffer: list[str] = []
        current_start_line = 0
        current_refs: dict[str, TableReference] = {}

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

        for line_index, raw_line in enumerate((page.text or "").splitlines()):
            line = raw_line.strip()
            if not line:
                continue
            if re.fullmatch(r"\d+\s*/\s*\d+", line):
                continue
            if self._is_later_top_level_chapter(line):
                flush()
                current_number = None
                current_buffer = []
                current_refs = {}
                continue

            match = CLAUSE_LINE_RE.match(line)
            if match:
                flush()
                current_number = PTRClauseNumber.from_string(match.group(1))
                current_content = match.group(2).strip()
                current_line = line
                current_start_line = line_index
                current_buffer = [current_content]
                current_refs = self._extract_table_references(line, current_number, page.page_number)
                continue

            if current_number is not None:
                current_buffer.append(line)
                for key, ref in self._extract_table_references(line, current_number, page.page_number).items():
                    current_refs.setdefault(key, ref)

        flush()
        return clauses

    def _extract_table_references(
        self,
        text: str,
        clause_number: PTRClauseNumber,
        page_number: int,
    ) -> dict[str, TableReference]:
        references: dict[str, TableReference] = {}
        for match in TABLE_REFERENCE_RE.finditer(text or ""):
            number = re.sub(r"\s+", "", match.group(1)).replace("－", "-").replace("—", "-")
            if "-" in number:
                number = number.split("-", maxsplit=1)[0]
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
        if "附录" in compact or "appendix" in compact.lower():
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

    def _extract_tables(self, parsed_pdf: ParsedPdf) -> list[PTRTable]:
        raw_tables = list(parsed_pdf.tables)
        for page in parsed_pdf.pages:
            raw_tables.extend(page.tables)

        seen: set[str] = set()
        tables: list[PTRTable] = []
        for table in raw_tables:
            if table.table_id in seen:
                continue
            seen.add(table.table_id)
            tables.append(self._convert_pdf_table(table))
        return tables

    def _convert_pdf_table(self, table: PdfTable) -> PTRTable:
        canonical = self.table_normalizer.normalize(table)
        table_number = self._extract_table_number(table)
        page_span = self._page_span_for_pdf_table(table)
        return PTRTable(
            table_id=table.table_id,
            table_number=table_number,
            title=table.caption or table.title,
            canonical_table=canonical,
            page_span=page_span,
            evidence=[
                Evidence(
                    id=f"{table.table_id}:table",
                    source_type=SourceType.PTR,
                    location=Location(source_type=SourceType.PTR, page_number=page_span[0], table_id=table.table_id),
                    raw_text=table.caption or table.title or table_number or "",
                    method=EvidenceMethod.PDF_LAYOUT,
                )
            ],
            metadata={"y0": table.bbox.y0 if table.bbox else 0.0, **dict(table.metadata or {})},
        )

    def _extract_table_number(self, table: PdfTable) -> str | None:
        raw = table.metadata.get("table_number") if table.metadata else None
        if raw is not None and str(raw).strip():
            return str(raw).strip()
        for text in (table.caption, table.title):
            match = re.search(r"表\s*([A-Za-z]?\d+)", text or "")
            if match:
                return match.group(1)
        return None

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
        position_bridge = float(previous.metadata.get("y0", 0.0)) >= 450.0 and float(current.metadata.get("y0", 0.0)) <= 150.0
        if overlap >= 0.95:
            return True, "same_header_continuation"
        if position_bridge and overlap >= 0.55:
            return True, "top_bottom_with_header_overlap"
        if overlap < 0.35:
            return False, "header_mismatch"
        return False, "missing_table_number_without_strong_evidence"

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

        if base.canonical_table is not None and fragment.canonical_table is not None:
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


def extract_ptr(parsed_pdf: ParsedPdf) -> PTRDocument:
    return PTRExtractor().extract(parsed_pdf)
