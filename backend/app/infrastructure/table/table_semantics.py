from __future__ import annotations

import re
from pydantic import BaseModel, Field

from app.domain.table import CanonicalTable


class ColumnSemantic(BaseModel):
    column_index: int
    labels: list[str] = Field(default_factory=list)
    role: str = "unknown"
    dimension_labels: list[str] = Field(default_factory=list)
    leaf_label: str = ""
    leaf_role: str = "unknown"


class TableSemanticResult(BaseModel):
    columns: list[ColumnSemantic] = Field(default_factory=list)
    unknown_role_count: int = 0
    diagnostics: list[str] = Field(default_factory=list)


class TableSemantics:
    _ROLE_ALIASES = {
        "parameter": ["参数", "参数名称", "检验项目", "项目", "条目"],
        "unit": ["单位", "计量单位"],
        "model": ["型号", "机型", "规格", "规格型号", "适用型号", "型号规格", "序号型号"],
        "group": ["分组", "类别", "腔室", "部位", "类型", "组别", "适用类型", "型号类型", "部件"],
        "condition": ["条件", "试验条件", "检测条件", "环境条件", "工况", "负载"],
        "default": ["标准设置", "默认设置", "默认值", "设置值", "目标值", "标准值"],
        "tolerance": ["允许误差", "容差", "误差", "允差", "允许偏差", "偏差", "公差", "范围上限", "范围下限", "限值", "阈值", "标准要求"],
        "value": ["常规数值", "数值", "范围", "检验结果", "值", "数值范围", "范围值"],
        "remark": ["备注", "说明", "解释"],
    }

    def __init__(self) -> None:
        self.unknown_role_count = 0

    def reset(self) -> None:
        self.unknown_role_count = 0

    @staticmethod
    def normalize_token(text: str | None) -> str:
        if not text:
            return ""
        value = re.sub(r"\s+", "", str(text))
        value = value.replace("／", "/").replace("（", "(").replace("）", ")")
        value = value.replace("—", "-").replace("–", "-").replace("－", "-")
        value = value.replace("％", "%")
        return value.strip()

    def infer_column_role(self, labels: list[str] | str | None) -> str:
        normalized = self._normalize_path(labels)
        if not normalized:
            self.unknown_role_count += 1
            return "unknown"

        joined = "/".join(normalized)
        for role, aliases in self._ROLE_ALIASES.items():
            if any(alias in joined for alias in aliases):
                return role

        if re.search(r"(?:V|mV|μV|A|Ω|KΩ|kΩ|ppm|ms|Hz|VA|W)\b", joined):
            return "value"

        self.unknown_role_count += 1
        return "unknown"

    def split_path_semantics(self, labels: list[str] | str | None) -> tuple[list[str], str, str]:
        normalized = self._normalize_path(labels)
        if not normalized:
            return [], "", "unknown"

        leaf_role = self.infer_column_role(normalized)
        if leaf_role in {"value", "default", "tolerance", "remark", "unit", "unknown"} and len(normalized) > 1:
            if leaf_role == "unknown":
                leaf_role = "value"
            return normalized[:-1], normalized[-1], leaf_role
        if leaf_role in {"parameter", "model", "group", "condition"}:
            return normalized, "", leaf_role
        return normalized[:-1], normalized[-1], leaf_role

    def infer_column_roles(self, labels_per_column: list[list[str]] | list[str]) -> list[str]:
        return [self.infer_column_role(labels) for labels in labels_per_column]

    def infer_value_leaf_label(self, label: str, role: str | None = None) -> str:
        normalized = self.normalize_token(label)
        if not normalized:
            return ""
        role = role or self.infer_column_role([normalized])
        if role == "unknown" and "检验结果" in normalized:
            return "检验结果"
        return normalized

    def analyze_canonical_table(self, table: CanonicalTable) -> TableSemanticResult:
        self.reset()
        label_paths = self._labels_from_canonical(table)
        columns: list[ColumnSemantic] = []
        for index, labels in enumerate(label_paths):
            role = self.infer_column_role(labels)
            dims, leaf_label, leaf_role = self.split_path_semantics(labels)
            columns.append(
                ColumnSemantic(
                    column_index=index,
                    labels=labels,
                    role=role,
                    dimension_labels=dims,
                    leaf_label=leaf_label,
                    leaf_role=leaf_role,
                )
            )
        diagnostics = []
        if self.unknown_role_count:
            diagnostics.append(f"unknown roles: {self.unknown_role_count}")
        return TableSemanticResult(
            columns=columns,
            unknown_role_count=self.unknown_role_count,
            diagnostics=diagnostics,
        )

    def _normalize_path(self, labels: list[str] | str | None) -> list[str]:
        if isinstance(labels, str):
            raw_labels = re.split(r"\s*/\s*", labels) if "/" in labels else [labels]
        else:
            raw_labels = list(labels or [])
        expanded: list[str] = []
        for label in raw_labels:
            parts = re.split(r"\s*/\s*", str(label)) if "/" in str(label) else [str(label)]
            expanded.extend(parts)
        return [token for token in (self.normalize_token(label) for label in expanded) if token]

    def _labels_from_canonical(self, table: CanonicalTable) -> list[list[str]]:
        if table.headers and table.headers[0].column_paths:
            return table.headers[0].column_paths
        if table.header_rows:
            width = max((len(row) for row in table.header_rows), default=0)
            return [
                [
                    str(row[column_index]).strip()
                    for row in table.header_rows
                    if column_index < len(row) and str(row[column_index]).strip()
                ]
                for column_index in range(width)
            ]
        return [[column.name] for column in table.columns]
