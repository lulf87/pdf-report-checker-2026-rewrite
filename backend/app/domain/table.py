from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.domain.common import BoundingBox, Location

CellSource = Literal["native", "inferred", "vlm"]
CellRole = Literal["header", "body", "stub", "value", "unknown"]
ColumnRole = Literal["parameter", "model", "group", "condition", "value", "default", "tolerance", "remark", "unknown"]


class TableColumn(BaseModel):
    name: str
    normalized_name: str | None = None
    column_index: int | None = None
    aliases: list[str] = Field(default_factory=list)


class TableCell(BaseModel):
    cell_id: str | None = None
    raw_text: str | None = None
    normalized_text: str | None = None
    raw_value: str | None = None
    normalized_value: str | None = None
    row_index: int = Field(ge=0)
    column_index: int = Field(ge=0)
    row_span: int = Field(default=1, ge=1)
    column_span: int = Field(default=1, ge=1)
    is_header: bool = False
    page_number: int | None = Field(default=None, gt=0)
    bbox: BoundingBox | None = None
    location: Location | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_and_target_names(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        aliases = {
            "row": "row_index",
            "col": "column_index",
            "rowspan": "row_span",
            "colspan": "column_span",
        }
        for source, target in aliases.items():
            if source in data and target not in data:
                data[target] = data[source]
        if "raw_text" in data and "raw_value" not in data:
            data["raw_value"] = data["raw_text"]
        if "normalized_text" in data and "normalized_value" not in data:
            data["normalized_value"] = data["normalized_text"]
        return data

    @model_validator(mode="after")
    def sync_text_and_location(self) -> "TableCell":
        if self.raw_text is None:
            self.raw_text = self.raw_value
        if self.raw_value is None:
            self.raw_value = self.raw_text
        if self.normalized_text is None:
            self.normalized_text = self.normalized_value
        if self.normalized_value is None:
            self.normalized_value = self.normalized_text

        if self.location is None and (self.page_number is not None or self.bbox is not None):
            self.location = Location(page_number=self.page_number, bbox=self.bbox)
        if self.location is not None:
            if self.page_number is None:
                self.page_number = self.location.page_number
            if self.bbox is None:
                self.bbox = self.location.bbox
        return self


class TableHeader(BaseModel):
    rows: list[list[str]] = Field(default_factory=list)
    column_paths: list[list[str]] = Field(default_factory=list)
    source_cell_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def row_count(self) -> int:
        return len(self.rows)

    @computed_field
    @property
    def column_count(self) -> int:
        return max((len(row) for row in self.rows), default=0)


class Table(BaseModel):
    table_id: str
    table_number: str | None = None
    title: str | None = None
    cells: list[TableCell] = Field(default_factory=list)
    page_span: tuple[int, int] | None = None
    locations: list[Location] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TableRow(BaseModel):
    row_id: str | None = None
    values: dict[str, Any] = Field(default_factory=dict)
    location: Location | None = None
    source_cell_ids: list[str] = Field(default_factory=list)


class ParameterRecord(BaseModel):
    parameter_id: str | None = None
    parameter_name: str | None = None
    parameter_path: list[str] = Field(default_factory=list)
    raw_name: str | None = None
    normalized_name: str | None = None
    raw_value: str | None = None
    normalized_value: str | None = None
    unit: str | None = None
    dimensions: dict[str, str] = Field(default_factory=dict)
    values: dict[str, str] = Field(default_factory=dict)
    conditions: dict[str, str] = Field(default_factory=dict)
    source_rows: list[int] = Field(default_factory=list)
    source_cell_ids: list[str] = Field(default_factory=list)
    location: Location | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def populate_legacy_and_semantic_names(self) -> "ParameterRecord":
        if self.parameter_name is None:
            self.parameter_name = self.raw_name or self.normalized_name or self.parameter_id
        if self.raw_name is None:
            self.raw_name = self.parameter_name
        if self.parameter_id is None:
            self.parameter_id = self.normalized_name or self.raw_name or self.parameter_name
        if not self.conditions and self.dimensions:
            self.conditions = dict(self.dimensions)
        return self


class CanonicalCell(BaseModel):
    text: str
    row_index: int = Field(ge=0)
    column_index: int = Field(ge=0)
    row_span: int = Field(default=1, ge=1)
    column_span: int = Field(default=1, ge=1)
    bbox: BoundingBox | None = None
    is_header: bool = False
    source: CellSource = "native"
    role: CellRole = "unknown"
    propagated_from: tuple[int, int] | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_names(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        aliases = {
            "row": "row_index",
            "col": "column_index",
            "rowspan": "row_span",
            "colspan": "column_span",
        }
        for source, target in aliases.items():
            if source in data and target not in data:
                data[target] = data[source]
        return data

    @property
    def row(self) -> int:
        return self.row_index

    @property
    def col(self) -> int:
        return self.column_index


class ColumnPath(BaseModel):
    leaf_col: int = Field(ge=0)
    labels: list[str] = Field(default_factory=list)
    role: ColumnRole = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def key(self) -> str:
        return " / ".join(label for label in self.labels if label)


class CanonicalTableDiagnostics(BaseModel):
    header_row_count: int = Field(default=0, ge=0)
    inferred_rowspans: int = Field(default=0, ge=0)
    inferred_colspans: int = Field(default=0, ge=0)
    repeated_header_removed: int = Field(default=0, ge=0)
    continuation_merged: bool = False
    structure_confidence: float = 1.0
    notes: list[str] = Field(default_factory=list)


class CanonicalTable(BaseModel):
    table_id: str
    source_table_id: str | None = None
    page_start: int | None = Field(default=None, gt=0)
    page_end: int | None = Field(default=None, gt=0)
    caption: str | None = None
    table_number: str | None = None
    n_rows: int = Field(default=0, ge=0)
    n_cols: int = Field(default=0, ge=0)
    cells: list[CanonicalCell] = Field(default_factory=list)
    columns: list[TableColumn] = Field(default_factory=list)
    rows: list[TableRow] = Field(default_factory=list)
    headers: list[TableHeader] = Field(default_factory=list)
    header_rows: list[list[str]] = Field(default_factory=list)
    body_rows: list[int] = Field(default_factory=list)
    column_paths: list[ColumnPath] = Field(default_factory=list)
    dimension_columns: list[str] = Field(default_factory=list)
    parameter_records: list[ParameterRecord] = Field(default_factory=list)
    parameter_name_column: str | None = None
    value_columns: list[str] = Field(default_factory=list)
    unit_column: str | None = None
    condition_columns: list[str] = Field(default_factory=list)
    source_locations: list[Location] = Field(default_factory=list)
    confidence: str | None = None
    normalization_profile: str | None = None
    diagnostics: list[str] | CanonicalTableDiagnostics = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_numbers(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if data.get("table_number") is not None:
            data["table_number"] = str(data["table_number"])
        return data

    @model_validator(mode="after")
    def sync_header_views(self) -> "CanonicalTable":
        if self.headers and not self.header_rows:
            self.header_rows = self.headers[0].rows
        elif self.header_rows and not self.headers:
            self.headers = [TableHeader(rows=self.header_rows)]
        if self.n_rows == 0:
            if self.rows:
                self.n_rows = len(self.rows)
            elif self.cells:
                self.n_rows = max(cell.row_index for cell in self.cells) + 1
        if self.n_cols == 0:
            if self.columns:
                self.n_cols = len(self.columns)
            elif self.cells:
                self.n_cols = max(cell.column_index for cell in self.cells) + 1
        return self

    def get_cell(self, row: int, col: int) -> CanonicalCell | None:
        for cell in self.cells:
            if cell.row_index == row and cell.column_index == col:
                return cell
        return None


__all__ = [
    "CanonicalCell",
    "CanonicalTable",
    "CanonicalTableDiagnostics",
    "CellRole",
    "CellSource",
    "ColumnPath",
    "ColumnRole",
    "ParameterRecord",
    "Table",
    "TableCell",
    "TableColumn",
    "TableHeader",
    "TableRow",
]
