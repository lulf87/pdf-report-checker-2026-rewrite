# 重写项目架构设计

本文面向新项目初始化，依据：

- `docs/legacy-inventory.md`
- `docs/known-requirements.md`
- `docs/spec-code-test-gaps.md`

重写目标不是从零发明新产品，而是在保留旧项目高价值业务资产的前提下，重做职责边界、领域模型、规则模块、任务 API 与前端组织方式。

## 0. 范围与前提

### 0.1 保留的旧业务资产

以下能力应作为新架构的业务资产继续迁移：

- PTR 第 2 章解析与首页检验项目范围过滤。
- PTR 条款层级解析，支持 `2`、`2.1`、`2.1.1` 等层级和最细叶子条款核对。
- `见表 X`、`符合表 X`、`按表 X` 等表格引用展开，并进入结构化表格比对。
- `CanonicalTable` / 参数表结构化思路。
- 报告字段抽取、样品描述表抽取、照片 caption 抽取、中文标签 OCR 字段抽取。
- 新规则编号 C01-C11 对应的报告自检能力。
- OCR / VLM 增强，但只作为提取和证据增强，不作为最终业务判定层。
- Golden File 测试思路和旧测试中的高价值 fixture 行为。
- 深色玻璃拟态前端风格与面向核对人员的密集信息展示方式。

### 0.2 必须重做的旧架构问题

新项目不得继承以下旧架构形态：

- 不保留旧 Electron 主线，不恢复 `src/main`、`src/renderer`、根 Electron `package.json` 或历史 `python_backend`。
- 不让 FastAPI router 承担业务编排。
- 不让规则散落在 `services` 大类文件里。
- 不使用临时 `dict` 作为跨模块结果契约。
- 不让前端写业务判断；前端只展示后端给出的任务状态、Finding、证据、diff 和导出结果。

### 0.3 新旧规则编号前提

旧项目实现的检查编号不是本次新项目的目标编号。旧实现中存在 `C00/C12-C16` 等编号，新项目按 `docs/known-requirements.md` 的 C01-C11 口径重新建立规则矩阵。

旧编号只能作为业务资产来源，不能直接作为新规则注册表。

## 1. 架构原则

### 1.1 保留技术栈

新项目保持单体 Web 架构，不引入微服务和 Electron 主线。

| 层 | 保留技术 |
|---|---|
| 后端 Web | FastAPI |
| 后端 PDF | PyMuPDF |
| 后端 OCR | PaddleOCR |
| 前端 | React + TypeScript + Vite |
| 结果导出 | 初期支持 JSON/PDF，XLSX 通过导出 adapter 渐进补齐 |

LLM/VLM 可以作为 `infrastructure/llm` 下的增强 adapter，但不能成为最终规则裁决器。规则结果必须由 `rules/` 模块基于结构化领域模型输出。

### 1.2 重做职责边界

新架构采用五层边界：

- `api`：HTTP 输入输出、请求校验、响应 schema、文件上传入口。
- `application`：用例编排、任务生命周期、规则调用顺序、结果聚合。
- `domain`：稳定领域模型、值对象、结果契约、轻量领域语义。
- `rules`：独立业务规则，每条规则有明确输入模型和 Finding 输出。
- `infrastructure`：PDF、OCR、LLM/VLM、存储、导出、日志等外部能力 adapter。

依赖方向只允许从外层指向内层：

`api -> application -> domain/rules -> domain`

`application -> infrastructure` 用于调用外部资源，但 `domain` 和 `rules` 不依赖 FastAPI、PyMuPDF、PaddleOCR 或前端结构。

### 1.3 规则独立

每条规则必须独立成模块，至少具备：

- 固定 `check_id`。
- 中文规则名。
- 输入模型说明。
- 输出 Finding 约定。
- 依赖数据说明。
- 是否需要 OCR、ParsedPdf、ReportDocument。
- 单元测试和 Golden File 测试覆盖。

规则模块不得读取上传文件、不得调用 HTTP、不得直接渲染前端展示内容。

### 1.4 Finding 统一输出

所有业务问题、需复核项、系统诊断项统一输出为 `Finding`。不同规则不能自定义临时错误结构。

统一 Finding 的价值：

- 后端规则可以并行演进。
- 前端只需要一种问题展示模型。
- 导出 JSON/PDF/XLSX 可以复用同一结果契约。
- Golden File 可以稳定断言问题数量、编号、位置、证据和置信度。

### 1.5 测试先行

迁移任何旧规则前，先建立目标规则矩阵和测试样例：

- 规则注册表测试先锁定 C01-C11 的编号、名称、顺序和启用状态。
- 单条规则先写小样本单元测试，再迁移旧逻辑。
- 端到端 Golden File 只使用受控 fixture，不直接依赖用户机器上的原始素材目录。
- OCR/VLM/LLM 测试使用固定 fixture 或 fake adapter，不依赖 live 模型输出。

### 1.6 前端只展示结果

前端职责限定为：

- 上传 PDF。
- 创建任务并轮询任务状态。
- 展示 summary、Finding、证据、PTR diff、表格参数差异。
- 按后端提供的 severity/status 做筛选和排序。
- 调用导出 API 或展示导出结果。

前端不得重新判断字段是否一致、条款是否缺失、表格参数是否相等、页码是否连续。

## 2. 后端分层设计

### 2.1 目标目录

建议初始化结构：

```text
backend/
  app/
    main.py
    api/
      routes_health.py
      routes_tasks.py
      routes_report_check.py
      routes_ptr_compare.py
      schemas/
    application/
      task_service.py
      report_check_usecase.py
      ptr_compare_usecase.py
    domain/
      common.py
      finding.py
      pdf.py
      report.py
      ptr.py
      table.py
      task.py
      result.py
    rules/
      report/
        c01_home_vs_third.py
        c02_third_page_extended_fields.py
        c03_production_date.py
        c04_sample_description.py
        c05_photo_coverage.py
        c06_label_coverage.py
        c07_item_conclusion.py
        c08_non_empty.py
        c09_sequence.py
        c10_continuation.py
        c11_page_number.py
      ptr/
        scope_filter.py
        clause_text_compare.py
        table_reference_compare.py
        parameter_compare.py
        diff_builder.py
    infrastructure/
      storage/
      pdf/
      ocr/
      llm/
      export/
      logging/
```

`parameter_compare.py` 是对用户要求的 PTR 参数表比对能力的补充，建议加入目标结构。

### 2.2 `api` 层职责

`api` 层只处理 HTTP 和 schema：

- 注册 FastAPI 路由。
- 接收 multipart PDF 文件和查询参数。
- 校验文件类型、必要文件、导出格式。
- 将 HTTP 请求转换成 application 层命令。
- 将 domain/application 输出转换成 API response schema。
- 返回统一错误响应。

`api` 层不得：

- 解析 PDF 文本。
- 调用 OCR。
- 判断业务规则。
- 聚合 C01-C11 或 PTR 比对逻辑。
- 写临时任务 `dict` 作为跨层状态。

### 2.3 `application` 层职责

`application` 层是用例编排层：

- `task_service.py` 负责创建任务、更新任务状态、读取结果、记录进度。
- `report_check_usecase.py` 负责编排报告自检流程。
- `ptr_compare_usecase.py` 负责编排 PTR 与报告比对流程。

报告自检用例的典型流程：

1. 保存上传文件到受控 workspace。
2. 调用 PDF adapter 生成 `ParsedPdf`。
3. 调用 OCR adapter 补充 `LabelOCR`、图片文字和低置信诊断。
4. 构造 `ReportDocument`。
5. 调用 C01-C11 规则模块。
6. 聚合 `Finding` 为 `CheckResult` 和任务级 summary。
7. 保存结构化结果并更新 `TaskStatus`。

PTR 比对用例的典型流程：

1. 分别解析 PTR PDF 和报告 PDF。
2. 构造 `PTRDocument` 和 `ReportDocument`。
3. 运行 `scope_filter` 确定本轮核对条款范围。
4. 运行条款文本、表格引用、参数表规则。
5. 运行 `diff_builder` 生成展示友好的差异结构。
6. 聚合 Finding 和 PTR 对照结果。

`application` 可以调用 `infrastructure`，但输出必须是领域模型或 API schema，不能把外部 adapter 的原始返回值透传给前端。

### 2.4 `domain` 层职责

`domain` 层定义稳定领域语言：

- PDF 页面、表格、位置和证据。
- 报告字段、样品组件、检验项目、照片 caption、标签 OCR。
- PTR 条款、PTR 表格、条款分类、范围 selector。
- CanonicalTable 参数表结构。
- Finding、CheckResult、TaskStatus。

`domain` 可以包含少量纯函数，例如值归一化、日期格式标签、占位符判断、序号规范化。但不得依赖 PyMuPDF、PaddleOCR、FastAPI 或本地文件路径。

### 2.5 `rules` 层职责

`rules` 层是业务判断层：

- 每条 C 规则单独一个模块。
- PTR 范围、条款文本、表格引用和参数比对单独模块。
- 规则输入必须是领域模型。
- 规则输出必须是 `Finding` 列表和必要的规则级诊断。
- 规则可以返回 PASS/FAIL/REVIEW/SKIP/SYSTEM_ERROR 状态建议，但不能直接写任务状态。

规则层不得：

- 调用 OCR/VLM/LLM 来决定 PASS/FAIL。
- 读取文件系统。
- 生成前端 HTML。
- 依赖 API request 或 response schema。

### 2.6 `infrastructure` 层职责

`infrastructure` 层封装外部技术能力：

| 模块 | 职责 |
|---|---|
| `storage/` | 上传文件保存、任务结果保存、导出文件保存、临时目录清理。初版可使用本地文件存储和轻量任务记录，不设计复杂数据库。 |
| `pdf/` | PyMuPDF 加载、页面文本、词坐标、图片、绘图、页面渲染、表格候选抽取。 |
| `ocr/` | PaddleOCR 调用、OCR block 标准化、字段候选输出、置信度记录。 |
| `llm/` | VLM/LLM 增强提取、图片审阅、候选说明。输出只进入 Evidence 或 diagnostics。 |
| `export/` | JSON/PDF/XLSX 导出 adapter。 |
| `logging/` | 结构化日志、任务日志、规则诊断日志。 |

旧项目中的 PyMuPDF 页面渲染、照片页识别、无文本 PTR 页图片策略可以迁移到 `infrastructure/pdf`，但要去掉业务规则判断。

## 3. 核心领域模型

本节描述模型职责和关键字段，不规定具体实现方式。实现时可用 Pydantic 或 dataclass，但跨模块传输不得使用临时 `dict`。

### 3.1 通用模型

| 模型 | 职责 | 建议字段 |
|---|---|---|
| `Location` | 描述证据或问题在源文件中的位置。 | `source_id`、`source_type`、`page_number`、`bbox`、`section`、`table_id`、`row_index`、`column_name`、`text_span`、`description` |
| `Evidence` | 描述支持 Finding 或规则判断的可追溯证据。 | `id`、`source_type`、`location`、`raw_text`、`normalized_text`、`value`、`method`、`confidence`、`image_ref`、`metadata` |
| `Finding` | 统一问题/复核/信息输出。 | 见第 4 节 |
| `CheckResult` | 单条规则或规则组的执行结果。 | `task_id`、`check_id`、`check_name`、`status`、`severity`、`summary`、`findings`、`evidence`、`metrics`、`metadata` |
| `TaskStatus` | 统一任务生命周期状态。 | `task_id`、`task_type`、`status`、`progress`、`current_step`、`input_files`、`result_ref`、`error_message`、`logs`、`created_at`、`updated_at` |

### 3.2 PDF 模型

| 模型 | 职责 | 建议字段 |
|---|---|---|
| `ParsedPdf` | 一个 PDF 的结构化解析结果。 | `file_id`、`file_name`、`page_count`、`pages`、`tables`、`text_digest`、`diagnostics` |
| `PdfPage` | 单页 PDF 解析结果。 | `page_number`、`width`、`height`、`text`、`words`、`images`、`drawings`、`is_textless`、`render_ref`、`diagnostics` |
| `PdfTable` | PDF 中抽取出的表格候选。 | `id`、`page_numbers`、`title`、`caption`、`bbox`、`columns`、`rows`、`continuation_of`、`extraction_method`、`confidence` |

### 3.3 报告模型

| 模型 | 职责 | 建议字段 |
|---|---|---|
| `ReportDocument` | 检验报告的领域聚合根。 | `parsed_pdf`、`fields`、`inspection_items`、`sample_components`、`photo_captions`、`labels`、`page_map`、`diagnostics` |
| `ReportField` | 首页、第三页、报告元信息中的字段。 | `name`、`value`、`normalized_value`、`location`、`evidence`、`confidence`、`aliases` |
| `InspectionItem` | 检验项目表中的一条或一个序号聚合项。 | `sequence_raw`、`sequence`、`is_continuation`、`item_name`、`standard_requirement`、`result_values`、`conclusion`、`remark`、`row_location`、`page_span`、`evidence` |
| `SampleComponent` | 样品描述表中的部件/组件。 | `component_id`、`component_name`、`model`、`batch_or_serial`、`production_date`、`expiration_date`、`remark`、`identity_key`、`row_location`、`evidence` |
| `PhotoCaption` | 照片页或标签页 caption。 | `caption_id`、`text`、`subject_name`、`caption_type`、`page_number`、`bbox`、`matched_component_ids`、`evidence` |
| `LabelOCR` | 中文标签 OCR 或 PDF 文本层标签字段结果。 | `label_id`、`page_number`、`caption_id`、`fields`、`raw_blocks`、`language`、`ocr_engine`、`confidence`、`image_ref`、`evidence` |

### 3.4 PTR 与表格模型

| 模型 | 职责 | 建议字段 |
|---|---|---|
| `PTRDocument` | PTR 的领域聚合根。 | `parsed_pdf`、`clauses`、`tables`、`chapter2_span`、`source_info`、`diagnostics` |
| `PTRClause` | PTR 条款节点。 | `clause_id`、`number`、`title`、`body_text`、`level`、`parent_id`、`children_ids`、`taxonomy`、`location`、`table_refs`、`evidence` |
| `PTRTable` | PTR 中被引用或可比对的表格。 | `table_id`、`table_number`、`title`、`canonical_table`、`page_span`、`referenced_by_clause_ids`、`diagnostics` |
| `CanonicalTable` | 抽象后的参数表结构，用于 PTR 表和报告表统一比对。 | `table_id`、`caption`、`columns`、`rows`、`parameter_name_column`、`value_columns`、`unit_column`、`condition_columns`、`source_locations`、`confidence`、`normalization_profile` |

`PTRClause.taxonomy` 建议至少支持：

- `requirement`
- `group_heading`
- `method`
- `note`
- `table_reference`
- `appendix`
- `external_standard`

只有 `requirement` 和明确被引用的 `table_reference` 进入主核对统计；其他类型默认作为上下文、INFO 或 out-of-scope 诊断。

## 4. 统一 Finding 模型

统一 Finding 必须包含以下字段：

| 字段 | 含义 | 约束 |
|---|---|---|
| `id` | Finding 唯一标识。 | 在单个任务内唯一，建议包含 `task_id/check_id/序号` 信息或稳定 hash。 |
| `task_id` | 所属任务 ID。 | 必填。 |
| `check_id` | 所属规则编号。 | 报告规则使用 `C01`-`C11`；PTR 规则使用 `PTR_SCOPE`、`PTR_CLAUSE` 等稳定编号。 |
| `severity` | 严重级别。 | `error`、`warn`、`info`；UI 可显示为 ERROR/WARN/INFO。 |
| `code` | 机器可读问题码。 | 例如 `C01_FIELD_MISMATCH`、`PTR_TABLE_PARAM_MISSING`。 |
| `message` | 面向用户的中文说明。 | 不得包含未经验证的推测结论。 |
| `location` | 问题主位置。 | 使用 `Location`；无法定位时也要说明原因。 |
| `expected` | 期望值或期望状态。 | 可为字符串、数值、结构化摘要；不得伪造。 |
| `actual` | 实际值或实际状态。 | 来自 PDF/OCR/规则输出。 |
| `evidence` | 支持该 Finding 的证据列表。 | 使用 `Evidence`；ERROR/WARN 应尽量提供原文、页码或缺失证据说明。 |
| `confidence` | 置信度。 | `high`、`medium`、`low` 或数值区间；OCR/VLM 低置信应体现在此处。 |
| `metadata` | 扩展信息。 | 存放 diff、字段名、表格行列、suppressed_reason、诊断信息等。 |

### 4.1 Finding 输出原则

- 明确规则失败输出 `severity=error`。
- 证据不足、OCR 低置信、表格候选不唯一输出 `severity=warn`。
- 范围说明、跳过原因、被排除条款可以输出 `severity=info`。
- 不要把系统异常伪装成业务不一致。系统异常应进入 `CheckResult.status=SYSTEM_ERROR` 或任务 `error`。
- 不要在 `metadata` 中塞入业务必须字段；业务必须字段应有明确模型字段。

## 5. API 设计

API 统一围绕 task 资源设计。报告自检和 PTR 比对都先创建任务，再查询任务状态、结果和导出。

### 5.1 目标 API

| Method | Path | 用途 | 输入 | 输出 |
|---|---|---|---|---|
| `GET` | `/api/health` | 健康检查。 | 无。 | 服务状态、版本、依赖可用性摘要。 |
| `POST` | `/api/tasks/report-check` | 创建报告自检任务。 | multipart `report_file`，可选 OCR/VLM 配置。 | `TaskStatus`，状态为 `pending` 或 `processing`。 |
| `POST` | `/api/tasks/ptr-compare` | 创建 PTR 与报告比对任务。 | multipart `ptr_file`、`report_file`，可选比对配置。 | `TaskStatus`。 |
| `GET` | `/api/tasks/{task_id}` | 查询任务状态。 | path `task_id`。 | `TaskStatus`，不强制返回完整结果。 |
| `GET` | `/api/tasks/{task_id}/result` | 获取任务结果。 | path `task_id`。 | 任务级 summary、`CheckResult[]`、Finding 列表、模式特有详情。 |
| `GET` | `/api/tasks/{task_id}/export?format=json\|pdf\|xlsx` | 导出结果。 | path `task_id` + query `format`。 | 文件下载或导出任务引用。 |

### 5.2 任务状态

统一状态：

| 状态 | 含义 |
|---|---|
| `pending` | 已创建，等待执行。 |
| `processing` | 正在解析、OCR、规则核对或导出。 |
| `completed` | 主流程完成，结果可获取。 |
| `error` | 任务级失败，例如 PDF 无法打开、必要文件缺失、任务结果无法保存。 |

单条规则的失败不应直接导致任务 `error`。例如 OCR 低置信、表格解析不稳定、某条规则证据不足，应输出 `Finding` 或 `CheckResult.status=REVIEW/SYSTEM_ERROR`，任务仍可 `completed`。

### 5.3 结果响应结构

任务结果建议包含：

- `task_id`
- `task_type`
- `overall_status`
- `summary`
- `check_results`
- `findings`
- `diagnostics`
- `input_files`
- `created_at`
- `completed_at`

PTR 结果额外包含：

- `homepage_scope`
- `scope_summary`
- `clause_comparisons`
- `table_comparisons`
- `diffs`

报告自检结果额外包含：

- `report_meta`
- `field_summary`
- `sample_components`
- `inspection_item_summary`

## 6. 旧 API 到新 API 的映射

### 6.1 用户点名旧 API 映射

| 旧 API | 新 API |
|---|---|
| `/api/report/upload` | `POST /api/tasks/report-check` |
| `/api/report/{task_id}/progress` | `GET /api/tasks/{task_id}` |
| `/api/report/{task_id}/result` | `GET /api/tasks/{task_id}/result` |
| `/api/report/{task_id}/export` | `GET /api/tasks/{task_id}/export?format=json\|pdf\|xlsx` |
| PTR 旧上传接口 | `POST /api/tasks/ptr-compare` |
| PTR 旧进度接口 | `GET /api/tasks/{task_id}` |
| PTR 旧结果接口 | `GET /api/tasks/{task_id}/result` |
| PTR 旧导出接口 | `GET /api/tasks/{task_id}/export?format=json\|pdf\|xlsx` |

### 6.2 旧项目实际 `/api/report-self-check` 映射

旧项目当前实际路径集中在 `/api/report-self-check` 下，新项目不沿用该命名。

| 旧项目实际 API | 新 API | 处理策略 |
|---|---|---|
| `GET /api/report-self-check/health` | `GET /api/health` | 直接替换。 |
| `POST /api/report-self-check/check` | `POST /api/tasks/report-check` | 同步接口废弃；统一异步任务。 |
| `POST /api/report-self-check/check/start` | `POST /api/tasks/report-check` | 创建报告自检任务。 |
| `GET /api/report-self-check/tasks/{task_id}` | `GET /api/tasks/{task_id}` | 统一任务查询。 |
| `POST /api/report-self-check/ptr-report/check` | `POST /api/tasks/ptr-compare` | 同步接口废弃；统一异步任务。 |
| `POST /api/report-self-check/ptr-report/check/start` | `POST /api/tasks/ptr-compare` | 创建 PTR 比对任务。 |
| `POST /api/report-self-check/record-report/check/start` | 暂不进入本次主线 | 原始记录核对作为二阶段模块，不能混入 report-check router。 |

如需要短期兼容旧前端，可在 `api` 层提供薄兼容路由，但兼容路由只能转发到新 usecase，不能保留旧业务编排。

## 7. C01-C11 新规则模块设计

### 7.1 规则总契约

每个报告规则模块输出：

- `check_id`
- `check_name`
- `status`
- `findings`
- `evidence`
- `diagnostics`

状态建议：

| 状态 | 含义 |
|---|---|
| `PASS` | 规则完成，未发现问题。 |
| `FAIL` | 存在至少一个 `severity=error` Finding。 |
| `REVIEW` | 存在证据不足、OCR 低置信或需人工复核的 `severity=warn` Finding。 |
| `SKIP` | 规则因明确业务条件跳过，例如部件备注“本次检测未使用”。 |
| `SYSTEM_ERROR` | 规则执行异常或必要结构缺失，且无法降级为普通 REVIEW。 |

### 7.2 规则矩阵

| 规则模块 | 输入模型 | 输出 Finding | 依赖数据 | 需要 OCR | 需要 ParsedPdf | 需要 ReportDocument | 测试策略 |
|---|---|---|---|---|---|---|---|
| `c01_home_vs_third.py` | `ReportDocument.fields` 中首页与第三页字段。 | `C01_FIELD_MISMATCH`、`C01_FIELD_MISSING`。 | 委托方、样品名称、型号规格；字段位置和原文证据。 | 否，除非字段只在扫描页中。 | 是。 | 是。 | 覆盖三字段一致、不一致、缺失、自然换行/空格归一边界。 |
| `c02_third_page_extended_fields.py` | 第三页 `ReportField`、`LabelOCR`、`SampleComponent`。 | `C02_FIELD_MISMATCH`、`C02_LABEL_MISSING`、`C02_SEE_SAMPLE_DESC_INCONSISTENT`。 | 型号规格、生产日期、产品编号/批号、委托方、委托方地址；标签字段别名；“见样品描述栏”一致性。 | 是。 | 是。 | 是。 | 覆盖全部为“见样品描述栏”、部分为该值、标签缺失 WARN、字段别名映射。 |
| `c03_production_date.py` | 第三页生产日期字段、标签 OCR 生产日期字段。 | `C03_DATE_FORMAT_MISMATCH`、`C03_DATE_VALUE_MISMATCH`、`C03_DATE_MISSING`。 | 日期原文、日期格式模式、归一化日期值、OCR 置信度。 | 是。 | 是。 | 是。 | 参数化测试 `YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY.MM.DD`、`YYYYMMDD`、中文日期待确认样例；覆盖值同格式异、值异格式同。 |
| `c04_sample_description.py` | `SampleComponent[]`、`LabelOCR[]`。 | `C04_SAMPLE_FIELD_MISMATCH`、`C04_SAMPLE_FIELD_MISSING`、`C04_LABEL_UNMATCHED`。 | 部件名称、规格型号、序列号/批号、生产日期、失效日期；字段同义词；非空联合键。 | 是。 | 是。 | 是。 | 覆盖失效日期、同名多行、`/` 与空白、标签有值但表格无值、备注“本次检测未使用”。 |
| `c05_photo_coverage.py` | `SampleComponent[]`、`PhotoCaption[]`。 | `C05_PHOTO_MISSING`、`C05_PHOTO_CAPTION_UNCERTAIN`。 | 样品描述部件、照片 caption 主体名、未使用备注。 | 可选；图片 caption 无文本层时需要。 | 是。 | 是。 | 覆盖每部件至少一张照片、只有标签照片是否计入、未使用部件跳过、caption 主体名清洗。 |
| `c06_label_coverage.py` | `SampleComponent[]`、`PhotoCaption[]`、`LabelOCR[]`。 | `C06_CHINESE_LABEL_MISSING`、`C06_LABEL_LOW_CONFIDENCE`。 | 中文标签 caption、标签 OCR 字段、部件联合键。 | 是。 | 是。 | 是。 | 覆盖中文标签、英文标签、包装标签、同名多行、OCR 低置信 WARN。 |
| `c07_item_conclusion.py` | `InspectionItem[]`。 | `C07_CONCLUSION_MISMATCH`、`C07_RESULT_UNPARSABLE`。 | 检验结果、单项结论、序号聚合、无菌语境词、`/`、`——`、空白语义。 | 否，除非检验表为扫描件。 | 是。 | 是。 | 覆盖任一不符合、全部 `/` 或 `——`、空白与 C08 分工、无菌生长语境、跨页同序号聚合。 |
| `c08_non_empty.py` | `InspectionItem[]`。 | `C08_REQUIRED_CELL_EMPTY`、`C08_CELL_LOCATION_UNCERTAIN`。 | 检验结果、单项结论、备注三列；合并单元格继承；占位符规则。 | 否，除非表格为扫描件。 | 是。 | 是。 | 参数化覆盖空字符串、空格、换行、`/`、`——`、合并单元格、PDF 文本断行。 |
| `c09_sequence.py` | 排序后的 `InspectionItem[]`。 | `C09_SEQUENCE_GAP`、`C09_SEQUENCE_DUPLICATE`、`C09_SEQUENCE_BLANK`。 | 序号原文、归一化序号、续表标记、页码和表格行顺序。 | 否。 | 是。 | 是。 | 覆盖从 1 开始、跳号、重复、空白、`续X` 不作为普通重复。 |
| `c10_continuation.py` | `InspectionItem[]` + 表格页内行序。 | `C10_CONTINUATION_MISSING`、`C10_CONTINUATION_UNEXPECTED`、`C10_CONTINUATION_WRONG_POSITION`。 | 跨页同序号、首次出现页、续表标记、页内第一行判断。 | 否。 | 是。 | 是。 | 覆盖 `续X`、`续 X`、首次误写续、跨页缺续、本页非第一行出现续。 |
| `c11_page_number.py` | `ParsedPdf.pages`、`ReportDocument.page_map`。 | `C11_PAGE_NUMBER_MISSING`、`C11_PAGE_NUMBER_GAP`、`C11_TOTAL_MISMATCH`、`C11_FINAL_PAGE_MISMATCH`。 | 打印页码文本、总页数、物理页号、第三页起始映射。 | 可选；扫描页页码需要。 | 是。 | 是。 | 覆盖缺页码、重复页码、总页数不一致、末页不等于总页数、第三页起始规则。 |

### 7.3 C01-C11 迁移注意事项

- 旧 `C14` 的非空规则迁移到新 `C08`。
- 旧 `C15` 拆成新 `C09` 和 `C10`。
- 旧 `C16` 迁移到新 `C11`。
- 旧 `C12` 的检验结果与单项结论逻辑迁移到新 `C07`。
- 旧 `C08` 中的标签字段抽取和图片分批经验拆给新 `C04`、`C06`，不再让一个规则同时承担覆盖性和字段一致性。
- 旧项目中未确认或未实现的 `C05/C09/C10/C11` 编号不能原样迁移，必须按新规则矩阵重建。

## 8. PTR 新规则模块设计

### 8.1 `scope_filter.py`

职责：

- 从报告首页/第三页“检验项目”解析 PTR selector。
- 支持 exact selector 和 range selector，例如 `2.1.5`、`2.1～2.4`。
- 解析括号排除项，例如“除电磁兼容性”“不含生物相容性”。
- 将 PTR 第 2 章条款按范围过滤为本轮应核对集合。
- 输出被排除条款、排除原因和证据位置。

输入：

- `ReportDocument`
- `PTRDocument`

输出：

- `in_scope_clause_ids`
- `excluded_clause_ids`
- `scope_diagnostics`
- `Finding[]`，例如 `PTR_SCOPE_UNPARSED`、`PTR_SCOPE_EXCLUDED_INFO`

原则：

- 首页未声明的 PTR 条款不算缺失。
- group heading、method、appendix、note 默认不进入主统计。
- 排除逻辑必须保留原文、来源页和匹配理由，避免静默误伤。

### 8.2 `clause_text_compare.py`

职责：

- 对 in-scope 的 PTR 叶子要求条款与报告“标准要求”列进行文本比对。
- 保留 `≥/≤` 与 `>/<` 不等价规则。
- 支持空白、自然换行、全半角的有限归一化。
- 对缺失、额外、文本不一致输出 Finding。

输入：

- `PTRClause[]`
- `ReportDocument.inspection_items`
- `scope_filter` 输出

输出 Finding：

- `PTR_CLAUSE_MISSING`
- `PTR_CLAUSE_TEXT_MISMATCH`
- `PTR_CLAUSE_EXTRA`
- `PTR_CLAUSE_LOW_CONFIDENCE`

### 8.3 `table_reference_compare.py`

职责：

- 识别 PTR 条款正文中的 `见表 X`、`符合表 X`、`按表 X` 等引用。
- 找到对应 `PTRTable`。
- 将 PTR 表格和报告侧相关表格转换为 `CanonicalTable`。
- 在表格候选不唯一、多页续表无法可靠拼接、多行表头无法确认时输出 WARN。

输入：

- 含 `table_refs` 的 `PTRClause[]`
- `PTRDocument.tables`
- `ReportDocument` 中的报告表格候选

输出 Finding：

- `PTR_TABLE_REFERENCE_MISSING`
- `PTR_TABLE_CANDIDATE_AMBIGUOUS`
- `PTR_TABLE_UNPARSEABLE`

### 8.4 `parameter_compare.py`

职责：

- 比对 `CanonicalTable` 参数行。
- 覆盖参数名、参数值、单位、适用型号/条件、允许误差。
- 不只判断表号是否出现。
- 输出具体到行列的差异 Finding。

输入：

- PTR 侧 `CanonicalTable`
- 报告侧 `CanonicalTable`
- 表格引用上下文

输出 Finding：

- `PTR_PARAM_MISSING`
- `PTR_PARAM_VALUE_MISMATCH`
- `PTR_PARAM_UNIT_MISMATCH`
- `PTR_PARAM_CONDITION_MISMATCH`

### 8.5 `diff_builder.py`

职责：

- 将条款文本比对、表格引用比对、参数比对结果转换为前端可展示的 diff 结构。
- 生成文本差异片段、表格行列差异、证据定位。
- 不决定业务 severity。

输入：

- PTR 条款对照结果。
- 表格参数比对结果。
- Finding 列表。

输出：

- `clause_diffs`
- `table_diffs`
- `highlight_ranges`
- `display_groups`

`diff_builder` 是展示支持模块，不应删除、压制或改写 Finding。

## 9. 迁移策略

### 9.1 直接保留

| 资产 | 保留方式 |
|---|---|
| FastAPI + React + TypeScript + Vite | 作为新项目基础栈。 |
| PyMuPDF 页面文本、词坐标、页面渲染经验 | 迁移到 `infrastructure/pdf`。 |
| PaddleOCR 作为 OCR 能力 | 迁移到 `infrastructure/ocr`，输出 `LabelOCR` 和 OCR Evidence。 |
| Finding / Evidence / CheckResult 思路 | 重建为强类型领域模型和 API schema。 |
| PTR 第 2 章、首页范围、排除项、scope coverage | 迁移为 `PTRDocument` + `scope_filter`。 |
| C08 标签字段别名、caption 主体名提取经验 | 拆给 `LabelOCR`、`PhotoCaption`、C04/C06。 |
| C14 非空字段、C15 续表规则经验 | 分别迁移到新 C08、C10。 |
| Golden File 测试思路 | 建立新 fixture 和 approved snapshot。 |
| 深色玻璃拟态风格 | 前端重做时保留为视觉方向。 |

### 9.2 改造后迁移

| 资产 | 改造要求 |
|---|---|
| 旧 `pdf_document_loader` | 去掉业务照片/标签判断，输出 `ParsedPdf`、`PdfPage`、`PdfTable`。 |
| 旧 `report_evidence_builder` | 拆成 report extractor、ReportDocument 构造、C01-C11 规则。 |
| 旧 `ptr_report_evidence_builder` | 拆成 PTR 条款解析、scope parser、表格解析、报告侧标准要求抽取。 |
| 旧 Codex judge client | 改为 `llm` adapter，只提供增强证据，不直接返回规则 verdict。 |
| 旧前端结果组件 | 改为渲染统一 Finding、CheckResult、diff；删除业务判断。 |
| 旧 PDF 导出 HTML 结构 | 改为基于新 result schema 的 export formatter。 |
| 旧 API 测试 | 重写为新 `/api/tasks/*` 契约测试。 |

### 9.3 重写

| 旧形态 | 重写原因 |
|---|---|
| 单 router 承载报告自检、PTR、原始记录 | 路由职责混乱，不能继续扩展。 |
| `TASKS` 全局 dict | 任务状态和结果契约不稳定，进程重启丢失。 |
| 大型 `services` 文件承载规则、证据、prompt、结果聚合 | 难以测试和定位规则问题。 |
| 临时 dict evidence/result | 无法保证前后端契约和 Golden File 稳定。 |
| 前端按字段自行解释业务状态 | 违反“前端只展示结果”。 |
| PTR 表格引用只靠文本或 LLM 语义判断 | 新需求要求结构化 `CanonicalTable` 与参数比对。 |

### 9.4 废弃

| 项 | 处理 |
|---|---|
| Electron 主进程与 renderer 主线 | 废弃，不进入新架构。 |
| 历史 `python_backend/` | 废弃；如后续找到，只抽业务规则和测试样例。 |
| 同步检查 API | 废弃，统一任务 API。 |
| 本地硬编码启动路径、端口、临时目录 | 废弃，改为环境配置和受控 runtime 目录。 |
| 未确认的旧 `C17` | 不进入 C01-C11 主线；如业务确认再作为新增规则设计。 |
| 原始素材目录直接作为测试输入 | 不迁入；只从中复制最小、可审查 fixture 到测试目录。 |

## 10. 测试策略

### 10.1 单元测试

覆盖对象：

- `Location`、`Evidence`、`Finding`、`CheckResult` schema。
- 日期格式归一化、占位符判断、序号规范化、caption 主体名提取。
- C01-C11 每条规则。
- PTR scope selector、exclusion parser、clause taxonomy、table reference parser、parameter comparer。
- `CanonicalTable` 行列归一化和参数匹配。

要求：

- 单元测试不读取真实大 PDF。
- OCR/VLM/LLM 均使用 fake output。
- 每个规则至少覆盖 PASS、ERROR、WARN/REVIEW 三类路径。

### 10.2 集成测试

覆盖对象：

- PDF adapter -> `ParsedPdf`。
- OCR adapter -> `LabelOCR`。
- report extractor -> `ReportDocument`。
- PTR extractor -> `PTRDocument`。
- usecase -> `CheckResult[]`。

要求：

- 使用小型受控 fixture。
- 测试任务进度和诊断日志。
- 不依赖 live Codex、外部 OCR 服务或用户本机素材路径。

### 10.3 API 测试

覆盖接口：

- `GET /api/health`
- `POST /api/tasks/report-check`
- `POST /api/tasks/ptr-compare`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/result`
- `GET /api/tasks/{task_id}/export?format=json|pdf|xlsx`

覆盖场景：

- 非 PDF 拒绝。
- 损坏 PDF 可读错误。
- 缺少 PTR 或报告文件。
- 任务状态从 `pending/processing` 到 `completed/error`。
- 结果 schema 稳定。
- 导出格式非法时返回明确错误。

### 10.4 Golden File 测试

Golden File 分层：

| 层 | Golden 内容 |
|---|---|
| PDF 解析 | `ParsedPdf` 的页数、关键文本片段、表格候选、无文本页诊断。 |
| 报告领域模型 | `ReportDocument` 的字段、样品组件、检验项目、caption、LabelOCR。 |
| PTR 领域模型 | `PTRDocument` 的第 2 章条款、taxonomy、表格引用。 |
| 规则结果 | C01-C11 和 PTR Finding JSON。 |
| 导出结果 | JSON/PDF/XLSX 的结构化内容或 HTML/PDF 关键段落。 |

Golden 更新机制：

- 不自动覆盖 golden。
- 更新时必须记录 fixture hash、更新原因、影响的规则编号。
- 更新 diff 必须人工 review。
- OCR/VLM 相关 golden 固定输入和 fake 输出，避免模型漂移导致无意义变更。

### 10.5 前端 build

前端必须至少验证：

- TypeScript 类型检查。
- Vite build。
- API client 类型与 OpenAPI/Pydantic schema 对齐。
- 结果组件能渲染 `PASS/FAIL/REVIEW/SKIP/SYSTEM_ERROR`。
- Finding 缺少非关键 metadata 时不崩溃。

### 10.6 前端浏览器实测

使用浏览器自动化验证：

- 报告自检上传流程。
- PTR 双文件上传流程。
- 任务轮询、进度和错误展示。
- ERROR/WARN/INFO 筛选。
- PTR 文本 diff 和表格 diff 展示。
- PDF/XLSX 导出按钮状态。
- 深色玻璃拟态界面在桌面和窄屏下无重叠、无文字溢出。

前端测试只验证展示行为，不重新断言业务规则。

## 11. 风险与处理策略

### 11.1 PDF 表格解析不稳定

风险：

- 合并单元格、多页续表、多行表头、扫描页表格会导致 `PdfTable` 不稳定。
- `见表 X` 可能有重复表号或表题不完整。

处理策略：

- 所有表格先转为 `CanonicalTable`，保留原始 `PdfTable` 证据。
- 表格候选不唯一时输出 WARN，不静默选择。
- 参数比对必须保留行列位置和原文。
- 建立表格 golden fixture，覆盖多页表、续表、重复表号、多行表头。
- 对无法可靠结构化的表格，输出 `PTR_TABLE_UNPARSEABLE` 或对应 C 规则 REVIEW。

### 11.2 OCR 不稳定

风险：

- 中文标签可能只有图片，无文本层。
- PaddleOCR 可能漏字、错字或低置信。
- 旧项目中字段为空不一定代表标签不存在。

处理策略：

- OCR 输出必须带 `confidence`、原始 block、图片引用和页码。
- 低置信字段不直接判 PASS；进入 WARN/REVIEW。
- 标签字段别名表配置化并有测试。
- OCR 失败只影响相关规则，不导致整份报告任务失败，除非该输入是任务级必需。
- VLM 只能补充 Evidence 或候选说明，不能覆盖规则判定。

### 11.3 业务规则歧义

风险：

- C01-C11 与旧编号不一致。
- `/`、`——`、空白在不同字段中语义不同。
- “本次检测未使用”到底跳过覆盖性还是跳过字段一致性，需要业务确认。
- PTR group clause、method、appendix、external standard 是否进入主统计存在边界。

处理策略：

- 建立规则矩阵文档和规则注册表测试。
- 对未确认口径输出 REVIEW 或 SKIP，不把假设写成 ERROR。
- 每条规则维护 value semantics，不做全局 `/` 与空白等价。
- 业务确认后更新规则测试，再改实现。

### 11.4 新旧结果结构迁移

风险：

- 旧前端和旧测试使用 `pass/warning/error`、旧 `Finding` 字段和临时 details。
- 新结果使用统一 `Finding`、`CheckResult`、`TaskStatus`。

处理策略：

- 新项目内部只使用新模型。
- 如果保留兼容层，由 API adapter 做旧字段映射，不让旧结构进入 application/rules/domain。
- 迁移期提供旧结果样例到新结果样例的 snapshot 测试。
- 前端类型从新 OpenAPI/schema 生成或同步校验，避免手写漂移。

### 11.5 Golden File 更新机制

风险：

- Golden File 可能被“顺手更新”掩盖回归。
- OCR/VLM 漂移会让 golden 不稳定。
- 原始素材如果直接使用，可能不可提交、不可复现。

处理策略：

- Golden 更新必须显式命令和人工 review。
- 每个 golden 记录 fixture hash、规则版本和更新原因。
- Live OCR/VLM 不进入稳定 golden；使用固定 OCR/VLM fixture。
- 原始 PDF 不在 raw/original/source_data 中原地修改，只复制最小 fixture 到测试目录。

## 12. 后续初始化顺序建议

为了让新项目能逐步迁移旧业务逻辑，建议按以下顺序初始化：

1. 建立 `backend/app/domain` 的核心模型和 schema 测试。
2. 建立 `backend/app/rules/report` 的 C01-C11 规则注册表，先用空实现或 fixture 驱动测试锁定编号和名称。
3. 建立 `TaskStatus`、`CheckResult`、`Finding` API schema，并完成 `/api/health`、`/api/tasks/*` 契约测试。
4. 迁移 PyMuPDF loader 到 `infrastructure/pdf`，输出 `ParsedPdf`。
5. 建立 `ReportDocument` 构造器，再逐条迁移 C01-C11。
6. 建立 `PTRDocument`、`scope_filter`、`clause_text_compare`。
7. 增加 `CanonicalTable`、`table_reference_compare`、`parameter_compare`。
8. 前端按 `app/features/entities/shared` 重建页面和组件，只消费新 API。
9. 引入 Golden File 测试并逐步扩大 fixture 覆盖。
10. 最后处理导出 PDF/XLSX 和旧 API 兼容层。

该顺序确保旧项目有价值的业务逻辑可以逐步迁移，同时避免把旧 router、service 大类和前端业务判断带入新架构。
