# Domain Model Migration Mapping

本文记录本轮 M01-M04 领域模型迁移的可追溯来源、处理方式和缺口。

## Evidence Sources

本轮已读取并作为依据的文件：

- `AGENTS.md`
- `docs/legacy-inventory.md`
- `docs/known-requirements.md`
- `docs/spec-code-test-gaps.md`
- `docs/rewrite-architecture.md`
- `docs/migration-plan.md`
- 旧项目 `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/backend/app/models/report_self_check.py`
- 当前项目 `backend/app/domain/*.py`
- 当前测试 `backend/tests/domain/test_domain_models.py`

早期 M01-M04 迁移时未能读取的文件：

- `docs/open-questions.md`：早期未检出；P01 复核时已存在，并确认当前无 PTR/Table domain model 专项待确认项。
- `backend/app/models/common_models.py`：当前项目和旧项目路径均未检出。
- `backend/app/models/report_models.py`：当前项目和旧项目路径均未检出。

因此，早期 M01-M04 没有声称完成“旧文件逐字段迁移”。实际处理方式是：基于已确认的旧 `report_self_check.py` 结果契约、项目需求文档和当前 `domain` 骨架，补齐新架构所需的稳定领域模型。

P01 复核更新：后续在旧项目根目录 `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13` 中已读取到 `backend/app/models/common_models.py`、`backend/app/models/ptr_models.py`、`backend/app/models/table_models.py`，并据此补齐 PTR 与表格 domain 模型的旧字段兼容入口。旧目录仍只读，所有修改均写入新项目。当前新项目 `docs/open-questions.md` 已存在；P01 未新增业务口径待确认项。

## M01 Common Models

| Requested / legacy concept | New model | Handling |
|---|---|---|
| `BoundingBox / Rect` | `backend/app/domain/common.py::BoundingBox`, alias `Rect` | 新增坐标值对象，包含 `x0/y0/x1/y1`、宽高属性和坐标顺序校验；不依赖 PyMuPDF。 |
| `PageLocation / Location` | `backend/app/domain/common.py::Location` | 扩展为可承载来源、页码、坐标、章节、表格、行列和文本 span；页码要求大于 0。 |
| `Evidence` | `backend/app/domain/common.py::Evidence` | 保留旧 `EvidenceItem` 的 source/page/label/value 思路，改为 source type + location + raw/normalized/value/method。 |
| `Severity` | `backend/app/domain/findings.py::Severity` | 按新架构统一为 `error/warn/info`，不同于旧 `FindingSeverity warning/error`。 |
| `Finding` | `backend/app/domain/findings.py::Finding` | 保留旧 finding 的 expected/actual/pages/related_fields 语义，改为统一 location/evidence/missing_evidence/diff_fragments。 |
| `DiffFragment` | `backend/app/domain/findings.py::DiffFragment` | 新增差异高亮结构，只建模 equal/insert/delete/replace，不实现 diff 算法。 |

废弃或未迁移：

- 未保留旧 `EvidenceItem.value = Any = None` 的宽松契约；新 evidence 的定位信息应进入 `Location`。
- 未把 Codex schema 直接作为 domain model。

## M02 Report Models

| Requested concept | New model | Handling |
|---|---|---|
| `ReportDocument` | `backend/app/domain/report.py::ReportDocument` | 聚合首页、第三页、检验项目、样品描述、照片、标签 OCR 和页码证据。 |
| `ReportField` | `backend/app/domain/report.py::ReportField` | 同时保留 `raw_value`、旧兼容 `value`、`normalized_value`、位置和证据。 |
| `FirstPageInfo` | `backend/app/domain/report.py::FirstPageInfo` | 建模委托方、样品名称、型号规格、报告编号、样品编号和扩展字段。 |
| `ThirdPageInfo` | `backend/app/domain/report.py::ThirdPageInfo` | 建模型号规格、生产日期、产品编号/批号、委托方、委托方地址和扩展字段。 |
| `InspectionItem` | `backend/app/domain/report.py::InspectionItem` | 保留序号、续表标记、标准要求、检验结果、单项结论、备注、页跨度和证据。 |
| `InspectionTable` | `backend/app/domain/report.py::InspectionTable` | 聚合检验项目行，供后续 C07-C10 规则使用。 |
| `SampleDescriptionRow` | `backend/app/domain/report.py::SampleDescriptionRow` | 建模部件名称、规格型号、序列号批号、生产日期、失效日期、备注。 |
| `ComponentKey` | `backend/app/domain/report.py::ComponentKey` | 建模部件 identity 的三元组，输出稳定 `identity` 字符串。 |
| `PhotoEvidence` | `backend/app/domain/report.py::PhotoEvidence` | 建模照片 caption、主体名、页码、图片引用和匹配的组件 key。 |
| `LabelOCRField / LabelOCRResult` | `backend/app/domain/report.py::LabelOCRField`, `LabelOCRResult` | 建模标签 OCR 字段、别名、raw blocks、语言、引擎、置信度和图片引用。 |
| `PageNumberEvidence` | `backend/app/domain/report.py::PageNumberEvidence` | 建模报告显示页码、解析页码和总页数证据。 |

业务逻辑处理：

- 未在模型中实现 C01-C11 判断。
- 未在模型中实现 `expected_conclusion` 或 C07 结论推导；该逻辑应迁移到 `rules/report`。
- `SampleComponent`、`PhotoCaption`、`LabelOCR` 保留为当前骨架兼容模型或别名，避免后续引用断裂。

## M03 PTR Models

| Requested concept | New model | Handling |
|---|---|---|
| `PTRClauseNumber` | `backend/app/domain/ptr.py::PTRClauseNumber` | 支持 `2`、`2.1`、`2.1.1`、`2.1.1.1` 的解析、排序、父级和后代判断；保留 `parts`、`level`、`is_chapter_2`、`parent()` 和 JSON 序列化。 |
| `PTRSubItem` | `backend/app/domain/ptr.py::PTRSubItem` | 迁移旧 `marker/text/position`，用于 P06 子项识别结果承载；不在模型中解析 a)、b)、`——`。 |
| `PTRTableReference / TableReference` | `backend/app/domain/ptr.py::TableReference`，别名 `PTRTableReference` | 建模 `table_number/context/position/raw_text/reference_text/clause_id/location/evidence`；表号统一序列化为字符串，便于表号带后缀或重复候选。 |
| `PTRClause` | `backend/app/domain/ptr.py::PTRClause` | 建模条款号、旧 `full_text/text_content/parent_number/sub_items/position/raw_text/clause_type`，以及新 `title/body_text/scope_type/taxonomy/location/table_refs/table_references/evidence`。旧 helper `has_table_references()`、`has_sub_items()`、`get_all_table_numbers()`、`is_standard_clause()` 已保留。 |
| `PTRClauseType` | `backend/app/domain/ptr.py::PTRClauseType` | P01 要求的旧 `clause_type` 枚举，允许 `main_requirement/test_method/appendix/informational/group`，并映射到现有 `PTRScopeType` 与 `PTRClauseTaxonomy`。 |
| `PTRTable` | `backend/app/domain/ptr.py::PTRTable` | 支持旧 `table_number/caption/headers/rows/page/page_end/position/bbox/header_rows/column_paths/structure_confidence/metadata`，并保留新 `table_id/title/canonical_table/page_span/referenced_by_clause_ids/diagnostics/evidence`。重复表号由 `PTRDocument.get_tables_by_number()` 返回全部候选。 |
| `PTRDocument` | `backend/app/domain/ptr.py::PTRDocument` | 聚合 PTR 条款、表格、表格引用、第 2 章页跨度和诊断；兼容旧 `chapter2_start/chapter2_end`，保留 `get_clause_by_number()`、`get_clause_by_string()`、`get_table_by_number()`、`get_tables_by_number()`、`get_clauses_at_level()`、`get_top_level_clauses()`、`get_main_requirement_clauses()`、`has_table_references()`、`get_all_referenced_table_numbers()`。 |
| `scope` | `backend/app/domain/ptr.py::PTRScopeType` | 建模 `requirement/test_method/appendix/informational/external_standard/group_clause/table_reference`。 |

业务逻辑处理：

- 未在模型中实现 PTR 第 2 章定位算法。
- 未在模型中实现条款比对、scope filtering 或表格展开比对。
- 旧 `PTRClauseTaxonomy` 保留作为当前代码兼容枚举，并由 `scope_type` 映射基础 taxonomy。

## M04 Table Models

| Requested concept | New model | Handling |
|---|---|---|
| `TableCell` | `backend/app/domain/table.py::TableCell` | 建模原始值、标准化值、行列位置、合并单元格跨度、表头标记和位置。 |
| `Table` | `backend/app/domain/table.py::Table` | 聚合原始单元格、表号、表题、页跨度、位置和诊断。 |
| `CanonicalCell` | `backend/app/domain/table.py::CanonicalCell` | 迁移旧 `text/row/col/row_span/col_span/bbox/is_header/source/role/propagated_from/confidence`，同时暴露新架构 `row_index/column_index`。 |
| `ColumnPath` | `backend/app/domain/table.py::ColumnPath` | 迁移旧多行表头 leaf column 语义，保留 `leaf_col/labels/role/key`。 |
| `CanonicalTableDiagnostics` | `backend/app/domain/table.py::CanonicalTableDiagnostics` | 迁移旧 normalizer 诊断结构，包含 header row、rowspan/colspan、重复表头移除、续表合并、结构置信度和 notes。 |
| `CanonicalTable` | `backend/app/domain/table.py::CanonicalTable` | 在原有 `columns/rows/headers/source_locations/parameter_records` 基础上补齐旧 `page_start/page_end/table_number/n_rows/n_cols/cells/body_rows/column_paths/diagnostics`。为兼容当前 normalizer，`diagnostics` 仍可为 `list[str]`，也可承载 `CanonicalTableDiagnostics`。 |
| `ParameterRecord` | `backend/app/domain/table.py::ParameterRecord` | 建模参数路径、原始/标准化参数名和值、单位、条件、来源单元格和位置；兼容旧 `parameter_name/dimensions/values/source_rows`。 |

业务逻辑处理：

- 未在 domain model 中实现候选表格选择。
- 未实现 PTR 专用表格比对算法。
- 未引入 PyMuPDF 对象或 PDF parser 依赖。
- 未把 `PTRTableReference.table_number` 保持为旧 int 类型；新模型统一为字符串，避免后续复杂表号和前端 JSON 契约出现类型漂移。
- `PTRClauseNumber` 仍只支持数字层级，不支持 `A.1` 这类附录编号；P01 只要求 2 系列数字层级，附录 taxonomy 通过 `clause_type/scope_type` 表达。

## Verification

新增测试：

- `backend/tests/domain/test_domain_models.py`
- `backend/tests/domain/test_ptr_models.py`
- `backend/tests/domain/test_table_models.py`

覆盖内容：

- `Finding / Evidence / Location / BoundingBox` 序列化和校验。
- 报告模型 raw/normalized value、样品描述、标签 OCR、照片和页码证据。
- PTR 条款号排序、父子层级、scope type 和表格引用序列化。
- 表格单元格、表头、维度列和参数记录序列化。
