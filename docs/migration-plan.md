# 重做项目迁移计划

本文基于以下已确认文档生成：

- `docs/legacy-inventory.md`
- `docs/known-requirements.md`
- `docs/spec-code-test-gaps.md`
- `docs/rewrite-architecture.md`

目标是把旧项目中可追溯的业务资产迁入新架构，而不是延续旧项目的 router、service 大文件、临时 dict、Electron 主线或 Codex 直接裁决模式。迁移应按任务逐步执行，每个任务必须能单独测试和验收。任一任务测试失败时，不得继续执行后续任务。

## 1. 迁移目标

### 1.1 产品目标

重做后的报告核对工具应支持：

- 检验报告自身核对，按新编号 C01-C11 输出规则结果。
- PTR 与检验报告比对，按 PTR 第 2 章范围、条款文本、表格引用和参数表结构化比对输出结果。
- 统一任务创建、轮询、结果获取和导出流程。
- Web 前端展示 Dashboard、报告自检、PTR 比对、结果筛选、证据、diff 和导出入口。
- JSON、PDF、Excel 导出。
- Golden File 和端到端验收脚本。

### 1.2 架构目标

新项目采用以下边界：

- `api`：HTTP 路由、请求校验、响应 schema。
- `application`：用例编排、任务生命周期、规则调用、结果聚合。
- `domain`：稳定领域模型和值对象。
- `rules`：独立业务规则，每条规则单独测试。
- `infrastructure`：PDF、OCR、存储、导出、LLM/VLM 增强 adapter。

依赖方向：

```text
api -> application -> domain/rules -> domain
application -> infrastructure
```

`domain` 和 `rules` 不得依赖 FastAPI、PyMuPDF、PaddleOCR、React 或文件系统。

### 1.3 保留资产

迁移时保留以下旧项目资产：

- FastAPI、React、TypeScript、Vite 的基础技术栈。
- PyMuPDF 页面文本、词坐标、页面渲染、图片裁剪经验。
- OCR 字段别名、caption 主体名提取、中文标签字段识别思路。
- 旧 `Finding`、`EvidenceItem`、`MissingEvidence`、`CheckResult` 的结果契约思路。
- PTR 首页范围解析、括号排除项、PTR 第 2 章条款解析和 `PTR-SCOPE-COVERAGE` 经验。
- 旧 C08 标签字段抽取、旧 C14 非空字段、旧 C15 续表规则经验。
- 旧前端上传、轮询、结果分组、优先处理区、PTR 双栏对照和 PDF 导出信息架构。
- 旧测试中的高价值行为，转为受控 fixture 和 Golden File。

### 1.4 不迁移内容

以下内容不进入新架构：

- 旧 Electron 主线，包括历史 `src/main/`、`src/renderer/`、根 Electron `package.json`。
- 历史 `python_backend/`。
- 旧同步检查 API。
- 旧 `/api/report-self-check/*` 作为主 API。
- 旧 `TASKS` 全局 dict 作为跨模块状态。
- 旧 service 大文件中的混合职责边界。
- Codex/LLM/VLM 直接输出最终规则 verdict 的模式。
- 用户机器上的 `素材/`、`uploads/`、`temp/`、`logs/`、`node_modules/`、`dist/` 等运行时或原始输入目录。
- 未确认的旧 `C17`。

## 2. 规则编号迁移策略

旧项目启用编号为：

```text
C00, C01, C02, C03, C04, C06, C07, C08, C12, C13, C14, C15, C16
```

新项目按 `docs/known-requirements.md` 的 C01-C11 口径重建规则矩阵。旧编号只能作为迁移来源，不能作为新规则注册表。

| 新编号 | 新规则 | 旧资产来源 |
|---|---|---|
| C01 | 首页与第三页一致性 | 旧 C02 首页基础字段一致性相关资产。 |
| C02 | 第三页扩展字段 | 旧 C03 首页扩展字段一致性、旧 C08 标签字段抽取资产。 |
| C03 | 生产日期格式和值一致性 | 旧 C03/旧 C04 时间字段资产，需按新口径重写。 |
| C04 | 样品描述表格核对 | 旧 C06 样品描述字段、旧 C08 标签字段一致性资产。 |
| C05 | 照片覆盖性 | 旧 C07 照片覆盖性资产，需补确定性实现。 |
| C06 | 中文标签覆盖 | 旧 C08 标签页、caption、图片分批经验。 |
| C07 | 检验项目单项结论逻辑 | 旧 C12 检验结果与单项结论逻辑资产。 |
| C08 | 非空字段 | 旧 C14 非空字段核对资产。 |
| C09 | 序号连续性 | 旧 C15 的序号资产，需和续表拆分。 |
| C10 | 续表标记 | 旧 C15 续表候选抽取和确定性 finding。 |
| C11 | 页码连续性 | 旧 C16 页码连续性需求，需补确定性实现。 |

迁移约束：

- 不得把多个 C 规则塞进一个任务。
- 每条规则必须有单独模块、单独测试和单独验收标准。
- 未确认的业务口径不得写成 `ERROR`，应输出 `WARN/REVIEW/SKIP` 或在任务中标为待业务确认。
- `/`、`——`、空白值不得做全局等价，必须按字段和规则定义 value semantics。

## 3. 目标目录路线

### 3.1 后端目录

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
        registry.py
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

### 3.2 前端目录

```text
frontend/
  src/
    app/
    api/
    features/
      dashboard/
      report-check/
      ptr-compare/
      results/
      export/
    shared/
      components/
      types/
      utils/
    styles/
```

前端只消费后端输出的 `TaskStatus`、`CheckResult`、`Finding`、PTR diff 和导出状态。前端不得重新判断业务规则。

## 4. 分阶段路线

### 阶段 0：冻结旧项目资产

先固定旧项目读取来源、迁移边界和不迁移清单。旧目录只作为参考，不在旧项目上直接改代码。若需要使用旧 fixture，必须复制到当前项目受控测试目录后再处理。

完成条件：

- 当前项目有 `AGENTS.md`，明确 raw/original/source_data 不可原地修改。
- 有 rewrite 分支说明或等价文档，说明旧项目只读、重写项目逐步执行。
- 旧 Electron、历史 `python_backend` 和旧同步 API 已被列为废弃或 legacy。

### 阶段 1：初始化新项目骨架

建立后端、前端和最小可运行脚手架：

- 后端 FastAPI app。
- 前端 Vite React TypeScript app。
- 测试、lint、build 命令。
- `GET /api/health`。

完成条件：

- 后端 health 测试通过。
- 前端构建或类型检查通过。
- 还没有迁入任何业务规则。

### 阶段 2：锁定领域模型和任务契约

先实现统一模型，再实现业务：

- `Location`
- `Evidence`
- `Finding`
- `CheckResult`
- `TaskStatus`
- `TaskRepository`
- `LocalFileStore`
- 统一任务 API 骨架

完成条件：

- schema/model 单元测试通过。
- task 创建、查询、结果引用和错误状态测试通过。
- API 只返回强类型 schema，不返回临时 dict。

### 阶段 3：迁移解析基础设施

迁移旧 PDF 和 OCR 能力，但先只输出领域模型，不做业务判定：

- `ParsedPdf`
- `PdfPage`
- `PdfTable`
- OCR block 和 `LabelOCR`
- `ReportExtractor` 分拆为 page locator、field extractor、inspection table extractor、sample description extractor。

完成条件：

- PDF 小 fixture 可解析。
- OCR fake adapter 可产生稳定 `LabelOCR`。
- `ReportDocument` 可由 fixture 构建。
- 解析失败输出诊断或可读错误，不伪造字段。

### 阶段 4：逐条迁移 C01-C11

按 C01 到 C11 顺序逐条迁移，每条规则独立任务、独立测试、独立验收。

完成条件：

- 每条规则只依赖领域模型。
- 每条规则至少覆盖 PASS、ERROR、WARN/REVIEW 或 SKIP 路径。
- 每条规则输出统一 `Finding`。
- 任何规则测试失败时停止，不继续下一条规则。

### 阶段 5：实现报告自检编排

在 C01-C11 全部可独立运行后，再实现：

- `ReportRuleRunner`
- `ReportCheckUseCase`
- 报告自检任务 API 接入
- 结果 summary 聚合

完成条件：

- 单文件报告任务可以完成从上传、解析、规则执行到结果查询的闭环。
- 单条规则失败不导致任务级 error，除非 PDF 无法打开或必需文件缺失。

### 阶段 6：迁移 PTR 比对

PTR 比对按 parser、comparator、table normalizer、usecase 的顺序迁移：

- `PTRExtractor`
- `ClauseComparator`
- `TableNormalizer`
- `CanonicalTable`
- `TableComparator`
- `PTRCompareUseCase`

完成条件：

- 首页范围、括号排除、PTR 第 2 章和 leaf clause 解析可测。
- `≥/≤` 与 `>/<` 不等价。
- `见表 X` 可追踪到 `CanonicalTable`。
- 参数名、参数值、单位、适用条件和允许误差差异能输出 Finding。

### 阶段 7：导出

先导出 JSON，再导出 PDF，最后导出 Excel：

- JSON 导出使用任务结果原始 schema。
- PDF 导出使用 formatter，不由前端重新判断业务。
- Excel 导出按 Finding、CheckResult、PTR diff 和表格参数差异分 sheet。

完成条件：

- 导出内容来自同一结果模型。
- 导出失败有可读错误。
- 导出测试不依赖 live OCR、LLM 或用户本机素材。

### 阶段 8：前端重做

前端按页面和组件逐步重做：

- Dashboard。
- 报告自检页面。
- PTR 比对页面。
- 结果展示组件。
- 导出按钮。
- API client 和轮询。

完成条件：

- 前端只展示后端返回结果。
- 错误、WARN、INFO、PASS/FAIL/REVIEW/SKIP/SYSTEM_ERROR 均可展示。
- PTR 文本 diff 和表格 diff 能展示。
- 桌面和窄屏无文字溢出、遮挡和重叠。

### 阶段 9：验收与清理

最后做全局验收：

- Golden File 测试。
- 端到端验收脚本。
- legacy/废弃说明。

完成条件：

- Golden 更新需要人工 review。
- 端到端脚本覆盖报告自检和 PTR 比对。
- 旧 Electron、`python_backend`、`src/renderer` 等路径已有明确废弃说明或隔离到 legacy。

## 5. API 迁移路线

新 API 围绕 task 资源：

| Method | Path | 用途 |
|---|---|---|
| `GET` | `/api/health` | 健康检查。 |
| `POST` | `/api/tasks/report-check` | 创建报告自检任务。 |
| `POST` | `/api/tasks/ptr-compare` | 创建 PTR 比对任务。 |
| `GET` | `/api/tasks/{task_id}` | 查询任务状态。 |
| `GET` | `/api/tasks/{task_id}/result` | 获取任务结果。 |
| `GET` | `/api/tasks/{task_id}/export?format=json|pdf|xlsx` | 导出结果。 |

旧 `/api/report-self-check/*` 不作为新项目主 API。若短期需要兼容旧前端，只允许在 `api` 层建立薄转发，不得把旧业务编排带入 `application` 或 `rules`。

## 6. 测试门禁

每个任务都必须说明：

- 目标测试文件。
- 运行命令。
- 预期结果。
- Done when。

迁移期间按以下顺序设置门禁：

1. 单元测试：领域模型、helper、单条规则。
2. 集成测试：PDF/OCR adapter、ReportDocument、PTRDocument、usecase。
3. API 测试：health、task、result、export。
4. 前端测试：类型检查、build、组件渲染、API client。
5. Golden File：报告、PTR、规则结果、导出结构。
6. 端到端：上传、轮询、结果、导出。

任何门禁失败时：

- 停止后续任务。
- 不更新 golden 来掩盖失败。
- 不把系统异常改写成业务 ERROR。
- 不修改原始输入文件。

## 7. 数据与文件安全

- `raw/`、`original/`、`source_data/` 或等价目录不可原地修改。
- 用户本机旧项目和旧素材只读。
- 测试 fixture 必须复制到当前项目受控目录后使用。
- 导出文件、上传文件和临时文件写入受控 runtime/output 目录。
- 不删除旧内容，除非用户明确要求。
- 不编造 OCR 字段、PTR 条款、表格参数、页码、测试结果或执行结果。

## 8. 完成判定

迁移路线完成的判定：

- `docs/tasks.md` 中 T01-T42 均有完成状态。
- 每个任务都能单独执行、单独测试、单独验收。
- 所有规则和用例测试通过。
- API、前端、导出、Golden 和端到端验收通过。
- 旧项目资产有明确去向：迁移、改造后迁移、重写或废弃。

