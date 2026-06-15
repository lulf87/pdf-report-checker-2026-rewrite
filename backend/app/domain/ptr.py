from enum import StrEnum
from functools import total_ordering
from typing import Any

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from app.domain.common import Evidence, Location
from app.domain.pdf import ParsedPdf
from app.domain.table import CanonicalTable


@total_ordering
class PTRClauseNumber(BaseModel):
    parts: tuple[int, ...]

    @model_validator(mode="before")
    @classmethod
    def parse_number(cls, value: Any) -> Any:
        if isinstance(value, str):
            raw_parts = value.strip().split(".")
            if not raw_parts or any(not item.isdigit() for item in raw_parts):
                raise ValueError("PTR clause number must contain dot-separated integers")
            return {"parts": tuple(int(item) for item in raw_parts)}
        if isinstance(value, (tuple, list)):
            return {"parts": tuple(int(item) for item in value)}
        return value

    @classmethod
    def from_string(cls, value: str) -> "PTRClauseNumber":
        return cls.model_validate(value)

    def __str__(self) -> str:
        return ".".join(str(item) for item in self.parts)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, PTRClauseNumber):
            return NotImplemented
        return self.parts < other.parts

    @property
    def level(self) -> int:
        return len(self.parts)

    @property
    def chapter(self) -> int:
        return self.parts[0]

    @property
    def is_chapter_2(self) -> bool:
        return self.parts == (2,)

    def parent(self) -> "PTRClauseNumber | None":
        if len(self.parts) <= 1:
            return None
        return PTRClauseNumber(parts=self.parts[:-1])

    def is_descendant_of(self, other: "PTRClauseNumber") -> bool:
        return len(self.parts) > len(other.parts) and self.parts[: len(other.parts)] == other.parts


class PTRScopeType(StrEnum):
    REQUIREMENT = "requirement"
    TEST_METHOD = "test_method"
    APPENDIX = "appendix"
    INFORMATIONAL = "informational"
    EXTERNAL_STANDARD = "external_standard"
    GROUP_CLAUSE = "group_clause"
    TABLE_REFERENCE = "table_reference"


class PTRClauseTaxonomy(StrEnum):
    REQUIREMENT = "requirement"
    GROUP_HEADING = "group_heading"
    METHOD = "method"
    NOTE = "note"
    TABLE_REFERENCE = "table_reference"
    APPENDIX = "appendix"
    EXTERNAL_STANDARD = "external_standard"


class PTRClauseType(StrEnum):
    MAIN_REQUIREMENT = "main_requirement"
    TEST_METHOD = "test_method"
    APPENDIX = "appendix"
    INFORMATIONAL = "informational"
    GROUP = "group"


class PTRSubItem(BaseModel):
    marker: str
    text: str
    position: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.marker} {self.text}".strip()


class TableReference(BaseModel):
    table_number: str
    context: str = ""
    position: int = 0
    raw_text: str | None = None
    reference_text: str | None = None
    clause_id: str | None = None
    location: Location | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("table_number", mode="before")
    @classmethod
    def normalize_table_number(cls, value: Any) -> str:
        return str(value)


PTRTableReference = TableReference


class PTRClause(BaseModel):
    clause_id: str
    number: PTRClauseNumber
    full_text: str | None = None
    text_content: str | None = None
    title: str | None = None
    body_text: str = ""
    normalized_text: str | None = None
    level: int = 0
    parent_number: PTRClauseNumber | None = None
    parent_id: str | None = None
    children_ids: list[str] = Field(default_factory=list)
    scope_type: PTRScopeType = PTRScopeType.REQUIREMENT
    taxonomy: PTRClauseTaxonomy = PTRClauseTaxonomy.REQUIREMENT
    clause_type: PTRClauseType = PTRClauseType.MAIN_REQUIREMENT
    sub_items: list[PTRSubItem] = Field(default_factory=list)
    location: Location | None = None
    table_refs: list[str] = Field(default_factory=list)
    table_references: list[TableReference] = Field(default_factory=list)
    position: tuple[int, int] | None = None
    raw_text: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_field_names(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if data.get("body_text") in (None, "") and data.get("text_content") not in (None, ""):
            data["body_text"] = data["text_content"]
        if data.get("text_content") in (None, "") and data.get("body_text") not in (None, ""):
            data["text_content"] = data["body_text"]
        return data

    @field_validator("parent_number", mode="before")
    @classmethod
    def parse_parent_number(cls, value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, PTRClauseNumber):
            return value
        return PTRClauseNumber.model_validate(value)

    @model_validator(mode="after")
    def populate_level_and_taxonomy(self) -> "PTRClause":
        self.level = self.number.level
        if self.parent_number is None:
            self.parent_number = self.number.parent()
        if self.text_content is None:
            self.text_content = self.body_text
        if self.full_text is None:
            self.full_text = f"{self.number} {self.body_text}".strip()

        if self.scope_type != PTRScopeType.REQUIREMENT or self.clause_type == PTRClauseType.MAIN_REQUIREMENT:
            self.clause_type, self.taxonomy = _clause_type_and_taxonomy_for_scope(self.scope_type)
        else:
            self.scope_type, self.taxonomy = _scope_and_taxonomy_for_clause_type(self.clause_type)
        if not self.table_refs and self.table_references:
            self.table_refs = [ref.table_number for ref in self.table_references]
        return self

    @property
    def is_leaf(self) -> bool:
        return len(self.children_ids) == 0

    @property
    def is_main_requirement(self) -> bool:
        return (
            self.clause_type == PTRClauseType.MAIN_REQUIREMENT
            and self.taxonomy == PTRClauseTaxonomy.REQUIREMENT
            and self.number.chapter == 2
        )

    def has_table_references(self) -> bool:
        return bool(self.table_refs or self.table_references)

    def has_sub_items(self) -> bool:
        return bool(self.sub_items)

    def get_all_table_numbers(self) -> list[str]:
        numbers = [*self.table_refs, *(ref.table_number for ref in self.table_references)]
        seen: set[str] = set()
        result: list[str] = []
        for number in numbers:
            if number in seen:
                continue
            seen.add(number)
            result.append(number)
        return result

    def is_standard_clause(self) -> bool:
        return self.number.chapter == 2

    @field_serializer("number")
    def serialize_number(self, value: PTRClauseNumber) -> str:
        return str(value)

    @field_serializer("parent_number")
    def serialize_parent_number(self, value: PTRClauseNumber | None) -> str | None:
        return str(value) if value else None


class PTRTable(BaseModel):
    table_id: str | None = None
    table_number: str | None = None
    caption: str | None = None
    title: str | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    page: int | None = Field(default=None, gt=0)
    page_end: int | None = Field(default=None, gt=0)
    position: tuple[int, int] | None = None
    bbox: tuple[float, float, float, float] | None = None
    header_rows: list[list[str]] = Field(default_factory=list)
    column_paths: list[list[str]] = Field(default_factory=list)
    structure_confidence: float | None = None
    canonical_table: CanonicalTable | None = None
    page_span: tuple[int, int] | None = None
    referenced_by_clause_ids: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("table_number", mode="before")
    @classmethod
    def normalize_table_number(cls, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    @model_validator(mode="after")
    def sync_legacy_fields(self) -> "PTRTable":
        if self.title is None and self.caption is not None:
            self.title = self.caption
        if self.caption is None and self.title is not None:
            self.caption = self.title
        if self.page_span is None and self.page is not None:
            self.page_span = (self.page, self.page_end or self.page)
        if self.page is None and self.page_span is not None:
            self.page = self.page_span[0]
            self.page_end = self.page_span[1]
        if self.table_id is None:
            number = self.table_number or "unknown"
            page = self.page or (self.page_span[0] if self.page_span else "unknown")
            self.table_id = f"ptr-table-{number}-p{page}"
        return self

    @property
    def num_rows(self) -> int:
        return len(self.rows)

    @property
    def num_cols(self) -> int:
        return len(self.headers) if self.headers else max((len(row) for row in self.rows), default=0)

    def get_cell(self, row: int, col: int) -> str | None:
        if 0 <= row < len(self.rows) and 0 <= col < len(self.rows[row]):
            return self.rows[row][col]
        return None

    def find_row_by_header(self, header_text: str) -> list[str] | None:
        for row in self.rows:
            if row and header_text in row[0]:
                return row
        return None


class PTRDocument(BaseModel):
    parsed_pdf: ParsedPdf | None = None
    clauses: list[PTRClause] = Field(default_factory=list)
    tables: list[PTRTable] = Field(default_factory=list)
    table_references: list[TableReference] = Field(default_factory=list)
    chapter2_start: int | None = Field(default=None, gt=0)
    chapter2_end: int | None = Field(default=None, gt=0)
    chapter2_span: tuple[int, int] | None = None
    source_info: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def sync_chapter2_span(self) -> "PTRDocument":
        if self.chapter2_span is None and self.chapter2_start is not None:
            self.chapter2_span = (self.chapter2_start, self.chapter2_end or self.chapter2_start)
        if self.chapter2_span is not None:
            if self.chapter2_start is None:
                self.chapter2_start = self.chapter2_span[0]
            if self.chapter2_end is None:
                self.chapter2_end = self.chapter2_span[1]
        return self

    def get_clause_by_number(self, number: PTRClauseNumber) -> PTRClause | None:
        for clause in self.clauses:
            if clause.number == number:
                return clause
        return None

    def get_clause_by_string(self, number: str) -> PTRClause | None:
        try:
            clause_number = PTRClauseNumber.from_string(number)
        except ValueError:
            return None
        return self.get_clause_by_number(clause_number)

    def get_clauses_at_level(self, level: int) -> list[PTRClause]:
        return [clause for clause in self.clauses if clause.level == level]

    def get_top_level_clauses(self) -> list[PTRClause]:
        return [clause for clause in self.clauses if clause.level == 2 and clause.number.chapter == 2]

    def get_table_by_number(self, table_number: str | int) -> PTRTable | None:
        normalized = str(table_number)
        for table in self.tables:
            if table.table_number == normalized:
                return table
        return None

    def get_tables_by_number(self, table_number: str | int) -> list[PTRTable]:
        normalized = str(table_number)
        return [table for table in self.tables if table.table_number == normalized]

    def get_main_requirement_clauses(self) -> list[PTRClause]:
        return [clause for clause in self.clauses if clause.is_main_requirement]

    def has_table_references(self) -> bool:
        return bool(self.get_all_referenced_table_numbers())

    def get_all_referenced_table_numbers(self) -> list[str]:
        numbers: set[str] = set()
        for clause in self.clauses:
            numbers.update(clause.table_refs)
            numbers.update(ref.table_number for ref in clause.table_references)
        numbers.update(ref.table_number for ref in self.table_references)

        def sort_key(value: str) -> tuple[int, str]:
            return (int(value), value) if value.isdigit() else (10**9, value)

        return sorted(numbers, key=sort_key)


def _scope_and_taxonomy_for_clause_type(clause_type: PTRClauseType) -> tuple[PTRScopeType, PTRClauseTaxonomy]:
    mapping = {
        PTRClauseType.MAIN_REQUIREMENT: (PTRScopeType.REQUIREMENT, PTRClauseTaxonomy.REQUIREMENT),
        PTRClauseType.TEST_METHOD: (PTRScopeType.TEST_METHOD, PTRClauseTaxonomy.METHOD),
        PTRClauseType.APPENDIX: (PTRScopeType.APPENDIX, PTRClauseTaxonomy.APPENDIX),
        PTRClauseType.INFORMATIONAL: (PTRScopeType.INFORMATIONAL, PTRClauseTaxonomy.NOTE),
        PTRClauseType.GROUP: (PTRScopeType.GROUP_CLAUSE, PTRClauseTaxonomy.GROUP_HEADING),
    }
    return mapping[clause_type]


def _clause_type_and_taxonomy_for_scope(scope_type: PTRScopeType) -> tuple[PTRClauseType, PTRClauseTaxonomy]:
    mapping = {
        PTRScopeType.REQUIREMENT: (PTRClauseType.MAIN_REQUIREMENT, PTRClauseTaxonomy.REQUIREMENT),
        PTRScopeType.TEST_METHOD: (PTRClauseType.TEST_METHOD, PTRClauseTaxonomy.METHOD),
        PTRScopeType.APPENDIX: (PTRClauseType.APPENDIX, PTRClauseTaxonomy.APPENDIX),
        PTRScopeType.INFORMATIONAL: (PTRClauseType.INFORMATIONAL, PTRClauseTaxonomy.NOTE),
        PTRScopeType.EXTERNAL_STANDARD: (PTRClauseType.INFORMATIONAL, PTRClauseTaxonomy.EXTERNAL_STANDARD),
        PTRScopeType.GROUP_CLAUSE: (PTRClauseType.GROUP, PTRClauseTaxonomy.GROUP_HEADING),
        PTRScopeType.TABLE_REFERENCE: (PTRClauseType.MAIN_REQUIREMENT, PTRClauseTaxonomy.TABLE_REFERENCE),
    }
    return mapping[scope_type]


__all__ = [
    "PTRClause",
    "PTRClauseNumber",
    "PTRClauseTaxonomy",
    "PTRClauseType",
    "PTRDocument",
    "PTRScopeType",
    "PTRSubItem",
    "PTRTable",
    "PTRTableReference",
    "TableReference",
]
