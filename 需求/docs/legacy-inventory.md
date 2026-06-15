# 旧项目资产盘点（legacy inventory）

> 范围：基于旧仓库 `lulf87/pdf-report-checker` 当前主线中已公开的 `backend/`、`frontend/`、历史 Electron 路径，以及本项目来源中的 `素材.zip`。本文只做反向盘点，不提出新增业务，不删除或改动旧代码。

## 1. 项目结构判断

### 1.1 新主线资产

旧项目的可延续主线应理解为：

- `backend/`：FastAPI 后端，包含 PDF 解析、OCR、报告抽取、PTR 抽取、规则检查、比对、导出、API router 和测试。
- `frontend/`：React + TypeScript + Vite 前端，包含 Dashboard、PTR 核对页面、报告自身核对页面、结果展示、筛选和导出入口。
- `docs/`：旧项目已有文档资产，可作为背景材料。
- `素材/expected` 与本项目来源 `素材.zip`：样例 PDF、原始记录、golden/expected 资产，应作为测试和回归素材，而不是业务代码。

### 1.2 历史 / Electron 资产

旧项目同时保留了旧 Electron 路径：

- 根目录 `package.json`：面向 Electron + Python 桌面应用的旧入口。
- `src/main`：Electron 主进程相关旧代码。
- `src/renderer`：Electron renderer 相关旧 UI。
- `python_backend`：旧桌面应用绑定的 Python 后端路径。

这些路径不应进入新架构设计。新项目重写时只保留其中可抽取的业务知识、规则经验或测试样例；目录结构和运行方式不复用。

### 1.3 运行时目录

以下目录只应视为运行时、调试或临时产物：

- `uploads/`
- `temp/`
- `logs/`（如存在）
- 生成的导出文件、缓存文件、OCR 临时图片等

这些不应被当成核心业务资产，也不应作为新架构中的领域模型来源。

## 2. 功能资产清单

### 2.1 PTR 条款核对

已沉淀功能：

| 功能 | 旧实现位置 | 资产价值 | 备注 |
|---|---|---:|---|
| 双 PDF 上传：PTR PDF + 检验报告 PDF | `backend/app/routers/ptr_compare.py`、`frontend/src/pages/ptr-compare/*` | 中 | router 中混合了上传、保存、任务、业务编排，需拆分。 |
| 异步任务进度查询 | `backend/app/routers/ptr_compare.py` | 中 | 当前为内存字典任务，不适合长期生产使用。 |
| PTR PDF 解析 | `pdf_parser.py`、`ptr_extractor.py` | 高 | 解析经验可迁移，接口需重构。 |
| PTR 第 2 章定位 | `ptr_extractor.py` | 高 | 已按编号结构定位，而不是依赖固定标题。 |
| 条款层级识别 | `ptr_models.py`、`ptr_extractor.py` | 高 | 支持 `2`、`2.1`、`2.1.1`、`2.1.1.1` 等。 |
| 排除检验方法/说明/附录等信息性内容 | `ptr_extractor.py`、`comparator.py` | 高 | 规则应下沉到 domain/rules。 |
| 报告中检验项目/标准要求抽取 | `report_extractor.py` | 高 | 为 PTR 比对提供报告侧条款证据。 |
| 条款文本归一化 | `text_normalizer.py` | 高 | 包含全角半角、换行、空白、OCR 符号、科学计数法等归一化。 |
| 条款差异比较与高亮片段 | `comparator.py` | 高 | 可迁移算法；输出模型需统一为 Finding。 |
| `见表 X` 表格引用识别与展开 | `ptr_extractor.py`、`table_comparator.py` | 高 | 是 PTR 模块核心复杂资产。 |
| 表格 canonical representation | `table_models.py`、`table_normalizer.py`、`table_semantics.py` | 高 | 可保留思想和测试，建议重构边界。 |
| 多页表格、重复表号候选、参数/值比对 | `table_comparator.py`、`table_normalizer.py` | 高 | 旧实现复杂，需拆成小规则/服务。 |
| 结果筛选：全部/不一致 | `frontend/src/pages/ptr-compare/PTRResults.tsx` | 中 | UI 约定可保留，状态语义需统一。 |
| PTR 比对 PDF 导出 | `report_export_service.py` | 中 | ReportLab 导出可保留为 infrastructure/export。 |

### 2.2 报告自身核对 C01-C11

已沉淀功能：

| 功能 | 旧实现位置 | 资产价值 | 备注 |
|---|---|---:|---|
| 单 PDF 上传 | `backend/app/routers/report_check.py`、`frontend/src/pages/report-check/*` | 中 | router 需变薄。 |
| 异步任务进度和结果查询 | `report_check.py` | 中 | 当前为内存任务。 |
| 首页字段抽取 | `report_extractor.py` | 高 | C01 依赖。 |
| 第三页字段抽取 | `report_extractor.py` | 高 | C01-C03 依赖。 |
| 图片页 Caption 抽取 | `report_check.py`、`ocr_service.py` | 中 | 目前一部分逻辑在 router，需要迁移到 extractor/application。 |
| 中文标签 OCR 字段抽取 | `ocr_service.py` | 高 | 包含字段别名、日期、批号、序列号 fallback。 |
| 样品描述表格抽取 | `report_check.py`、`report_checker.py`、`report_extractor.py` | 高 | 当前边界不清，需要重构。 |
| 检验项目表格抽取 | `report_extractor.py` | 高 | C07-C10 依赖。 |
| C01-C03 第三页规则 | `third_page_checker.py` | 高 | 规则可迁移，需核对“严格一致”与 OCR 容错边界。 |
| C04-C06 样品描述/照片/标签覆盖规则 | `report_checker.py` | 高 | 规则可迁移，需拆分为独立 rule。 |
| C07-C10 检验项目规则 | `inspection_item_checker.py` | 高 | 规则覆盖较完整，但 C07 空结果语义有已知冲突。 |
| C11 页码连续性 | `page_number_checker.py` | 高 | 独立性好，可迁移。 |
| 报告自身核对 PDF 导出 | `report_export_service.py` | 中 | 可迁移为导出适配器。 |

### 2.3 OCR / LLM / VLM 增强

| 功能 | 旧实现位置 | 资产价值 | 备注 |
|---|---|---:|---|
| PaddleOCR/RapidOCR 兼容 OCR 解析 | `ocr_parser.py`、`ocr_service.py` | 高 | 新架构应封装为 `OcrEngine`/`OcrService` 接口。 |
| 扫描件页面识别与 OCR fallback | `pdf_parser.py` | 高 | 应属于 infrastructure/pdf + infrastructure/ocr。 |
| OCR 符号纠错 | `ocr_parser.py`、`text_normalizer.py` | 中 | 需明确哪些归一化允许用于严格比对。 |
| LLM 文本增强 | `llm_service.py` | 中 | 可作为可选插件，不应作为规则事实来源。 |
| VLM 图片识别增强 | `llm_vision_service.py` | 中 | 需定义 fallback/enhance/disabled 模式的边界。 |

### 2.4 前端 UI 资产

| 功能 | 旧实现位置 | 资产价值 | 备注 |
|---|---|---:|---|
| Dashboard 入口 | `frontend/src/pages/Dashboard.tsx` | 中 | 可保留产品导航概念。 |
| PTR 上传页 | `frontend/src/pages/ptr-compare/PTRUpload.tsx` | 中 | 双文件上传与进度体验可保留。 |
| PTR 结果页 | `frontend/src/pages/ptr-compare/PTRResults.tsx` | 中 | 结果筛选、差异展示、导出入口可保留。 |
| 报告上传页 | `frontend/src/pages/report-check/ReportUpload.tsx` | 中 | 单文件上传、LLM 开关可重新设计。 |
| 报告结果页 | `frontend/src/pages/report-check/ReportResults.tsx` | 中 | C01-C11 展示可迁移到统一 Finding 视图。 |
| 深色玻璃拟态 UI | `frontend/src/styles/*`、Tailwind 配置 | 中 | 视觉约定保留，结构按 feature 重组。 |
| API service | `frontend/src/services/ptrApi.ts` | 低-中 | 旧命名可能混杂 PTR/报告接口，建议按 feature 拆分。 |

## 3. 业务规则清单

### 3.1 报告自身核对 C01-C11

| 规则 | 名称 | 已知规则 | 旧实现/测试关注点 |
|---|---|---|---|
| C01 | 首页与第三页一致性核对 | 首页 vs 第三页；字段：委托方、样品名称、型号规格；严格一致；不一致 ERROR。 | `third_page_checker.py`，`test_third_page_checker.py`。需确认旧代码中的 OCR/缺字容错是否仍允许。 |
| C02 | 第三页扩展字段核对 | 第三页表格 vs 照片页中文标签 OCR；字段：型号规格、生产日期、产品编号/批号、委托方、委托方地址。前三字段需按“见样品描述栏”三态逻辑处理。 | `third_page_checker.py`、`ocr_service.py`。旧规则中字段别名和匹配启发式较多。 |
| C03 | 生产日期格式与值一致性核对 | 第三页生产日期 vs 中文标签 OCR 生产日期；生产日期不是“见样品描述栏”时触发；格式和值都要一致。 | 旧 SRS 文档曾写“只比格式不比值”，但当前代码/测试包含值比对；需以新规格确认。 |
| C04 | 样品描述表格核对 | 样品描述表格 vs 对应中文标签 OCR；字段：部件名称、规格型号、序列号批号、生产日期、失效日期；忽略序号、备注；空白/`/` 视为无值。 | `report_checker.py`，`test_report_checker.py`。需确认标签存在额外值而表格为空时的判定。 |
| C05 | 照片覆盖性核对 | 每个样品描述部件至少一张照片；根据 Caption 主体名匹配；支持精确/部分匹配；备注含“本次检测未使用”时无照片不报错。 | `report_checker.py`。Caption 主体名解析依赖 OCR/文本抽取。 |
| C06 | 中文标签覆盖核对 | 每个部件至少一张中文标签；Caption 包含中文标签相关关键词；单一部件至少一张；同名多行按非空字段联合键分别匹配；备注含“本次检测未使用”时无标签不报错。 | `report_checker.py`。同名多行匹配是关键。 |
| C07 | 检验项目单项结论逻辑核对 | 任意“不符合要求”→期望“不符合”；全部为 `——`、`/`、空白→期望 `/`；任意“符合要求”或非空文本/数字→期望“符合”；实际不一致 ERROR。 | `inspection_item_checker.py`。旧代码最后 fallback 为“不符合”，测试中存在空结果期望“不符合”的用例，需迁移时修正或确认。 |
| C08 | 检验项目非空字段核对 | 检验结果、单项结论、备注均不得为空；`/`、`——` 在语境中为非空占位符；合并单元格以合并区域首行值为准，首行为空则整块为空。 | `inspection_item_checker.py`、`report_extractor_merged_cells.py`。 |
| C09 | 检验项目序号连续性核对 | 序号从 1 开始连续递增；无跳号、重复、空白；“续 X”归属原序号，不作为普通重复序号。 | `inspection_item_checker.py`。 |
| C10 | 检验项目续表标记核对 | 同一序号跨页时，新页第一行序号前必须加“续”；“续”只能出现在本页第一行；缺少或位置错误 ERROR。 | `inspection_item_checker.py`。 |
| C11 | 页码连续性核对 | 从第三页开始读取右上角页码 `共 XXX 页 第 Y 页`；Y 从 1 连续；最后一页 Y=XXX；所有 XXX 一致。 | `page_number_checker.py`。 |

### 3.2 PTR 核对规则

| 规则点 | 已知规则 | 旧实现/测试关注点 |
|---|---|---|
| 主范围 | PTR 第 2 章为主要核对范围。 | `ptr_extractor.py` 通过编号结构定位。 |
| 标题不固定 | 第 2 章标题可能为性能要求、性能指标、要求、规格、参数等，不能依赖固定标题。 | 需保留编号定位策略。 |
| 层级 | 支持 `2`、`2.1`、`2.1.1`、`2.1.1.1`。 | `PTRClauseNumber` 与 extractor 测试覆盖。 |
| 排除内容 | 检验方法、试验方法、检测方法、附录、说明、图等信息性内容不进入主一致性统计。 | 旧实现用启发式分类，需规则化。 |
| 标准条款排除 | GB、GB/T、YY、YY/T 等标准条款不属于 PTR 主核对范围。 | 比较器有外部标准/范围处理。 |
| 文本比对 | 条款正文严格匹配；比对前可做全角/半角统一、自然换行合并、多余空格去除。 | `text_normalizer.py` 包含更多归一化，需确定允许清单。 |
| 表格引用 | 条款中“见表 X”应解析被引用表格并展开比对。 | `ptr_extractor.py`、`table_comparator.py`。 |
| 表格比对 | 支持表号、表题、多页续接、重复表号候选、多行表头、参数名和值、canonical representation。 | `table_models.py`、`table_normalizer.py`、`table_semantics.py`、`test_table_comparator.py`。 |
| 报告侧范围 | 报告中“标准的内容”相关序号范围可能不参与核对。 | `report_models.py`、`report_extractor.py`、`comparator.py`。需确认规则来源。 |
| 结果展示 | 差异高亮、仅显示不一致项。 | 前端 `PTRResults.tsx` 与 export。 |

## 4. 数据模型清单

### 4.1 PDF 通用模型：`backend/app/models/common_models.py`

| 模型 | 用途 | 可迁移性 |
|---|---|---:|
| `BoundingBox` | 文本块、单元格坐标。 | 高 |
| `TextBlock` | PDF 文本块，包含文本、页码、坐标、字体信息。 | 高 |
| `CellData` | 表格单元格，包含行列、文本、坐标、合并信息。 | 高 |
| `TableData` | PDF 表格，包含单元格矩阵、表号、表题、页码等。 | 高 |
| `PDFPage` | 单页抽取结果：文本块、表格、尺寸、是否扫描页。 | 高 |
| `PDFDocument` | PDF 文档聚合，包含页面、元数据、便捷索引。 | 高 |

### 4.2 报告模型：`backend/app/models/report_models.py`

| 模型 | 用途 | 可迁移性 |
|---|---|---:|
| `InspectionItem` | 检验项目表格行，含序号、检验项目、标准条款、标准要求、检验结果、单项结论、备注。 | 高 |
| `InspectionTable` | 检验项目表格聚合，提供序号连续性、续表检查等辅助方法。 | 高 |
| `ReportField` | 报告字段及其位置/置信度。 | 中 |
| `ThirdPageFields` | 第三页字段集合，含委托方、样品名称、型号规格、生产日期、产品编号/批号、地址等。 | 高 |
| `ReportDocument` | 报告抽取结果聚合。 | 高 |

### 4.3 PTR 模型：`backend/app/models/ptr_models.py`

| 模型 | 用途 | 可迁移性 |
|---|---|---:|
| `PTRClauseNumber` | 条款编号值对象，支持解析、排序、层级、父级。 | 高 |
| `PTRSubItem` | 条款下的子项。 | 中 |
| `PTRTableReference` | 条款内表格引用。 | 高 |
| `PTRClause` | PTR 条款，含编号、标题、正文、引用表、类型等。 | 高 |
| `PTRTable` | PTR 表格，含表号、标题、行列。 | 高 |
| `PTRDocument` | PTR 文档聚合，提供条款/表格查找。 | 高 |

### 4.4 表格 canonical 模型：`backend/app/models/table_models.py`

| 模型 | 用途 | 可迁移性 |
|---|---|---:|
| `CanonicalCell` | 标准化单元格。 | 高 |
| `ColumnPath` | 多行表头折叠后的列路径。 | 高 |
| `CanonicalTableDiagnostics` | 表格标准化过程诊断。 | 中 |
| `CanonicalTable` | canonical representation。 | 高 |
| `ParameterRecord` | 参数名、维度、值、单位、来源坐标等记录。 | 高 |

### 4.5 API/任务模型

现有任务与响应模型定义在 router 内：

- `TaskStatus`: `pending`、`processing`、`completed`、`error`。
- `ComparisonTask` / `ReportCheckTask`。
- `UploadResponse`。
- `ProgressResponse`。
- `ResultResponse`。
- `CheckStatus`: `pass`、`error`、`warning`、`skipped`。

问题：这些模型与路由强绑定，且 PTR、报告两套重复定义。新架构应统一迁移到 `api/schemas` 或 `application/dto`，规则输出统一为 `Finding`。

## 5. 服务模块清单

| 模块 | 当前职责 | 复用判断 | 重写/拆分建议 |
|---|---|---:|---|
| `pdf_parser.py` | PyMuPDF 解析文本、表格、元数据、扫描页判定、OCR fallback。 | 高 | 拆到 `infrastructure/pdf`，向上暴露纯 DTO。 |
| `ocr_parser.py` | OCR 引擎封装、符号纠错、OCR warning。 | 高 | 拆为 OCR 引擎适配器与后处理 normalizer。 |
| `ocr_service.py` | 图片 OCR、中文标签字段抽取、Caption 解析、字段 fallback。 | 高 | 分成 `LabelExtractor`、`CaptionExtractor`、`OcrEngine`。 |
| `report_extractor.py` | 首页/第三页/检验项目表格/标准内容范围抽取。 | 高 | 保留经验，按 report extractor 子模块拆分。 |
| `report_checker.py` | C04-C06。 | 高 | 拆为独立规则文件 `c04`、`c05`、`c06`。 |
| `third_page_checker.py` | C01-C03。 | 高 | 拆为独立规则文件 `c01`、`c02`、`c03`。 |
| `inspection_item_checker.py` | C07-C10。 | 高 | 拆为独立规则文件；先处理 C07 语义冲突。 |
| `page_number_checker.py` | C11。 | 高 | 基本可迁移为规则 + extractor 辅助。 |
| `ptr_extractor.py` | PTR 第 2 章、条款、表格引用、条款类型抽取。 | 高 | 拆为 `chapter_locator`、`clause_parser`、`ptr_table_linker`。 |
| `comparator.py` | PTR 条款比较、diff、高亮、范围/外部标准处理、结构化 bundle 比对。 | 高 | 拆成 scope filter、text comparator、clause matcher、diff service。 |
| `table_comparator.py` | 表格引用展开、候选选择、参数比较、报告证据匹配。 | 高 | 拆成 table reference resolver、candidate selector、parameter comparator。 |
| `table_normalizer.py` | 表格 canonical 化、多行表头、维度列、参数记录。 | 高 | 可迁移到 domain/tables + rules 支撑层。 |
| `table_semantics.py` | 列角色语义识别、同义词、未知列统计。 | 高 | 可迁移，词典需配置化。 |
| `text_normalizer.py` | 文本归一化与比较。 | 高 | 需明确按场景启用哪些归一化 profile。 |
| `report_export_service.py` | PTR/报告 PDF 导出。 | 中 | 迁移到 `infrastructure/export/reportlab_exporter.py`。 |
| `llm_service.py` | LLM 文本增强。 | 中 | 插件化，默认 disabled。 |
| `llm_vision_service.py` | VLM 图片识别增强。 | 中 | 插件化，必须保留人工可追溯证据。 |
| `golden_runner.py` | Golden 测试入口。 | 中 | 迁移为测试工具，不进入生产 application。 |
| `presentation_status.py` | 展示状态映射。 | 中 | 可迁移到 frontend/shared 或 application presenter。 |

## 6. API 清单

### 6.1 通用 API

| Method | Path | 当前职责 | 重构建议 |
|---|---|---|---|
| GET | `/api/health` | 健康检查。 | 保留。 |

### 6.2 PTR API：`backend/app/routers/ptr_compare.py`

| Method | Path | 输入 | 输出 | 当前问题 |
|---|---|---|---|---|
| POST | `/api/ptr/upload` | `ptr_file`、`report_file` | `task_id`、`status`、`message` | 保存文件、校验大小/页数、创建任务、启动处理均在 router。 |
| GET | `/api/ptr/{task_id}/progress` | `task_id` | `status`、`progress`、`message`、`error` | 使用内存 dict。 |
| GET | `/api/ptr/{task_id}/result` | `task_id` | 比对结果 | 结果模型为 dict，缺少统一 Finding contract。 |
| GET | `/api/ptr/{task_id}/export` | `task_id` | PDF bytes | 导出直接读取 task result。 |

当前隐含约束：

- 单文件最大 50MB。
- 单 PDF 最多 200 页。
- 上传文件写入 `uploads/`。
- 使用 `asyncio.create_task` 背景处理。
- 任务状态保存在进程内存中。

### 6.3 报告自身核对 API：`backend/app/routers/report_check.py`

| Method | Path | 输入 | 输出 | 当前问题 |
|---|---|---|---|---|
| POST | `/api/report/upload` | `report_file`、`enable_llm` | `task_id`、`status`、`message` | router 中混合文件保存、PDF 验证、任务创建、LLM 开关、业务处理。 |
| GET | `/api/report/{task_id}/progress` | `task_id` | `status`、`progress`、`message`、`error` | 使用内存 dict。 |
| GET | `/api/report/{task_id}/result` | `task_id` | C01-C11 结果 | 输出 shape 由 router 组装，规则结果不统一。 |
| GET | `/api/report/{task_id}/export` | `task_id` | PDF bytes | 导出耦合 task result。 |

## 7. 测试资产清单

旧项目后端测试总量约 11k 行，覆盖面较好。迁移时应把这些测试视为规则回归资产，并根据新规格修正冲突测试。

| 测试文件 | 行数 | 覆盖内容 | 迁移建议 |
|---|---:|---|---|
| `backend/tests/conftest.py` | 22 | 测试基础配置。 | 保留并重写为新目录 fixture。 |
| `backend/tests/table_fixture_builder.py` | 86 | 表格 fixture builder。 | 迁移到 `tests/fixtures/builders`。 |
| `test_api_ptr.py` | 614 | PTR API、任务状态、进度、结果构造、真实样例回归。 | 拆成 API contract 测试 + application fake 测试 + golden 测试。 |
| `test_api_report.py` | 430 | 报告上传、LLM 开关、任务、结果计数、API 模型。 | 拆成 API contract 测试。 |
| `test_comparator.py` | 1228 | PTR 条款 diff、匹配/缺失、scope、外部标准、结构化 bundle、数值/科学计数法。 | 高优先级迁移。 |
| `test_export.py` | 467 | PDF 导出、标题、空结果、分类、截断、颜色/字体 fallback。 | 迁移到 export adapter 测试。 |
| `test_golden_entrypoints.py` | 17 | golden case 入口。 | 保留；重写路径发现逻辑。 |
| `test_golden_expected.py` | 101 | golden expected 对比。 | 保留；需确认 expected 来源。 |
| `test_inspection_item_checker.py` | 1025 | C07-C10：结论逻辑、非空、序号、续表、占位符、合并/错位。 | 高优先级迁移；C07 空结果用例需复核。 |
| `test_llm_service.py` | 405 | LLM/VLM 配置、mode、provider、未配置行为。 | 迁移为可选插件测试。 |
| `test_ocr_parser.py` | 305 | OCR 初始化、空图/简单图、符号纠错、warning。 | 保留为 infrastructure OCR 测试。 |
| `test_ocr_service.py` | 545 | Caption、LabelOCRResult、标签字段抽取、OCR fallback。 | 迁移为 label/caption extractor 测试。 |
| `test_page_number_checker.py` | 450 | C11 页码提取、连续性、重复/缺失/总页数错误。 | 高优先级迁移。 |
| `test_pdf_parser.py` | 381 | PDF 文档/页面/表格模型、解析、扫描页、元数据。 | 保留为 parser adapter 测试。 |
| `test_ptr_extractor.py` | 775 | PTR 第 2 章、条款层级、表格引用、子项。 | 高优先级迁移。 |
| `test_ptr_extractor_multidim.py` | 320 | 多维 PTR 表格和 canonical 化。 | 高优先级迁移。 |
| `test_report_checker.py` | 948 | C04-C06：样品描述、照片覆盖、中文标签覆盖、OCR 容错。 | 高优先级迁移；部分判定需确认。 |
| `test_report_extractor.py` | 504 | 报告字段、第三页、检验项目表、标准内容排除。 | 高优先级迁移。 |
| `test_report_extractor_merged_cells.py` | 105 | 合并单元格填充与空 anchor。 | 高优先级迁移。 |
| `test_table_comparator.py` | 1197 | 表格引用展开、候选选择、参数比对、报告证据、外部引用。 | 高优先级迁移。 |
| `test_table_normalizer.py` | 123 | 多行表头、维度列、参数记录、置信度。 | 高优先级迁移。 |
| `test_table_semantics.py` | 53 | 列角色同义词、未知列统计、路径语义。 | 迁移并配置化词典。 |
| `test_text_normalizer.py` | 310 | 全/半角、空白、换行、OCR 符号、单位、科学计数法、标题。 | 高优先级迁移。 |
| `test_third_page_checker.py` | 1050 | C01-C03、见样品描述栏、标签匹配、客户/地址/型号 OCR 容错、日期格式/值。 | 高优先级迁移；严格一致边界需确认。 |

## 8. `素材.zip` 资产清单

本次来源中的 `素材.zip` 解压后可作为 golden/sample 输入资产：

### 8.1 PTR PDF

| Case | 文件 |
|---|---|
| 1539 | `素材/ptr/1539/射频脉冲电场消融系统产品技术要求-20260102-Clean.pdf` |
| 2795 | `素材/ptr/2795/产品技术要求-心脏脉冲电场消融仪 - 1201.pdf` |
| 3940 | `素材/ptr/3940/3940 产品技术要求 Edora 8 改批注zx260218 260225更新.pdf` |
| 4788 | `素材/ptr/4788/CH3.4.1QuadraAllure3TMP技术要求_PM3562-1-0506最终.pdf` |
| 5332 | `素材/ptr/5332/TR-AP0105-001 Rev01一次性使用磁电定位心脏脉冲电场消融导管产品技术要求-0305V2.pdf` |
| 5780 | `素材/ptr/5780/消化道脉冲电场消融仪技术要求.pdf` |
| 5782 | `素材/ptr/5782/一次性使用消化道脉冲电场消融导管技术要求.pdf` |

### 8.2 报告 PDF

| Case | 文件 |
|---|---|
| 1347 | `素材/report/1347/QW2026-1347 Draft.pdf` |
| 1539 | `素材/report/1539/QW2025-1539 Draft.pdf` |
| 2795 | `素材/report/2795/QW2025-2795 Draft.pdf` |
| 2948 | `素材/report/2948/QW2025-2948 Draft.pdf` |
| 3940 | `素材/report/3940/3940.pdf` |
| 4788 | `素材/report/4788/4788draft.pdf` |
| 5332 | `素材/report/5332/QW2025-5332 Draft.pdf` |
| 5780 | `素材/report/5780/QW2025-5780 Draft.pdf` |
| 5782 | `素材/report/5782/QW2025-5782 Draft.pdf` |

### 8.3 原始记录 PDF

| Case | 文件 |
|---|---|
| 1347 | `素材/record/1347/Copy of GB9706.1-2020原始记录-2023-0915 2.pdf` |
| 1539 | `素材/record/1539/GB 9706.1/Copy of GB9706.1-2020原始记录-2023-0915 3.pdf` |
| 1539 | `素材/record/1539/GB 9706.202/GB9706.202-2021表2主机版250312（纸质表3版） 5.pdf` |
| 2795 | `素材/record/2795/GB 9706.202/Copy of GB9706.202-2021表2主机版250312（纸质表3版） 2.pdf` |
| 2948 | `素材/record/2948/GB 9706.1-2020/Copy of GB9706.1-2020原始记录-2023-0915 2.pdf` |
| 2948 | `素材/record/2948/GB 9706.202-2021/GB9706.202-2021表2主机版250312（纸质表3版） 3.pdf` |

## 9. 可复用资产

优先保留：

1. C01-C11 的规则知识、字段同义词、边界用例和测试资产。
2. PTR 第 2 章抽取、条款层级识别、表格引用识别经验。
3. 表格 canonical representation 及其测试。
4. 文本归一化经验，但需按业务场景分 profile。
5. OCR 字段提取、Caption 主体名解析和标签字段别名。
6. ReportLab 导出经验。
7. Golden 样例 PDF 和 expected 输出。
8. 前端结果展示、筛选、导出等产品交互约定。

## 10. 需要重写或大幅重构资产

| 资产 | 原因 | 重构方向 |
|---|---|---|
| `ptr_compare.py` router | 混合 API、文件保存、任务、业务编排、结果组装、导出。 | 只保留薄 router，迁移到 application use case。 |
| `report_check.py` router | 同上，且含照片页、Caption、样品描述抽取辅助函数。 | router 只接收请求和返回 DTO。 |
| task 管理 | 内存 dict、无持久化、无清理策略。 | `TaskRepository` + `JobService`。 |
| 上传文件保存 | 直接写 `uploads/`。 | `FileStorage` 抽象；本地/对象存储可替换。 |
| 规则输出模型 | 多个 dataclass/Pydantic result，shape 不统一。 | 统一 `Finding`。 |
| C01-C11 checker 聚合类 | 一个类内多个规则，状态模型重复。 | 每条规则独立文件，统一接口。 |
| PTR comparator | 单文件承担 scope、diff、bundle、状态映射过多。 | 拆成 matcher、normalizer、diff、scope、presenter。 |
| table comparator | 复杂职责聚合。 | 拆成 resolver、candidate selector、canonical comparator。 |
| OCR service | OCR 引擎、字段抽取、Caption、VLM 混在一起。 | 引擎/抽取/增强分离。 |
| 前端 services | `ptrApi.ts` 命名可能混用。 | 按 feature 拆为 `features/ptr-compare/api`、`features/report-check/api`。 |

## 11. 应废弃资产

| 资产 | 处理方式 | 说明 |
|---|---|---|
| 根目录 Electron `package.json` | 废弃，不迁入新架构 | 仅可作为历史参考。 |
| `src/main` | 废弃 | Electron 主进程不进入 Web 架构。 |
| `src/renderer` | 废弃 | 旧 renderer UI 不进入新 React/Vite 主线。 |
| `python_backend` | 废弃 | 不沿用旧桌面应用后端路径。 |
| `uploads/` | 运行时目录 | 不作为业务资产；新项目用 storage abstraction。 |
| `temp/` | 运行时目录 | 不作为业务资产。 |
| OCR 临时图片/缓存/日志 | 运行时产物 | 不纳入领域设计。 |
| 旧 router 中的业务编排写法 | 废弃 | 业务迁移到 application/rules。 |

