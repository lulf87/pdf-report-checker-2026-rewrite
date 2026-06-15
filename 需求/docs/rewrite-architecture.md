# 重写架构设计（rewrite architecture）

> 目标：在保持旧项目技术栈不变的前提下，重新设计后端和前端结构。新架构保留旧项目业务规则、解析经验、测试资产和 UI 约定，但不沿用旧 Electron 结构，不把 router 写成业务编排层，不把运行时目录当成业务资产。

## 1. 架构原则

1. **后端分层清晰**：`api`、`application`、`domain`、`rules`、`infrastructure`。
2. **router 不写业务规则**：router 只做请求解析、鉴权/校验、调用 use case、返回 DTO。
3. **规则输出统一**：PTR 和 C01-C11 全部输出 `Finding`。
4. **PDF parser、OCR、extractor、rules、export 分离**：解析事实、业务抽取、规则判定、导出渲染互不耦合。
5. **领域模型纯净**：domain 不依赖 FastAPI、PyMuPDF、PaddleOCR、ReportLab、文件系统。
6. **基础设施可替换**：PDF/OCR/LLM/导出/文件存储通过接口适配。
7. **旧测试先行迁移**：先让核心规则测试可跑，再逐步迁移 API 与 UI。
8. **不引入旧 Electron 运行方式**：新前端仅基于 `frontend/` React/Vite 主线。

## 2. 后端总体结构

建议新后端目录：

```text
backend/app/
  api/
    main.py
    dependencies.py
    routers/
      health.py
      ptr.py
      report.py
    schemas/
      common.py
      jobs.py
      findings.py
      ptr.py
      report.py
  application/
    dto/
      ptr_dto.py
      report_dto.py
      export_dto.py
    jobs/
      job_service.py
      task_repository.py
      progress.py
    use_cases/
      compare_ptr.py
      check_report.py
      export_result.py
    services/
      finding_aggregator.py
      result_presenter.py
  domain/
    common/
      geometry.py
      text.py
      source_ref.py
    documents/
      pdf_document.py
      extracted_document.py
    findings.py
    report/
      report_document.py
      first_page.py
      third_page.py
      inspection_item.py
      sample_description.py
      label.py
      caption.py
    ptr/
      ptr_document.py
      clause.py
      table_reference.py
    tables/
      table.py
      canonical_table.py
      parameter_record.py
      table_diagnostics.py
  rules/
    base.py
    registry.py
    report/
      c01_first_third_consistency.py
      c02_third_page_label_fields.py
      c03_production_date.py
      c04_sample_description_label.py
      c05_photo_coverage.py
      c06_chinese_label_coverage.py
      c07_item_conclusion.py
      c08_required_fields.py
      c09_sequence_continuity.py
      c10_continuation_marker.py
      c11_page_number_continuity.py
    ptr/
      scope_filter.py
      clause_text_consistency.py
      clause_matcher.py
      table_reference_expansion.py
      table_parameter_consistency.py
  infrastructure/
    pdf/
      pymupdf_parser.py
      table_detector.py
      scanned_page_detector.py
    ocr/
      paddle_ocr_engine.py
      ocr_postprocessor.py
      label_ocr_extractor.py
      caption_extractor.py
    extraction/
      report_extractor.py
      ptr_extractor.py
      first_page_extractor.py
      third_page_extractor.py
      inspection_table_extractor.py
      sample_description_extractor.py
    normalize/
      text_normalizer.py
      table_normalizer.py
      table_semantics.py
    llm/
      llm_service.py
      vlm_service.py
    export/
      reportlab_exporter.py
      export_models.py
    storage/
      file_storage.py
      local_file_storage.py
    logging.py
```

说明：

- `domain` 是纯业务对象和值对象。
- `rules` 是纯规则判定，输入 domain 对象，输出 `Finding`。
- `infrastructure` 封装所有外部依赖和解析技术。
- `application` 编排流程，不包含具体规则判断。
- `api` 只暴露 HTTP contract。

## 3. 后端分层职责

### 3.1 API 层

目录：`backend/app/api`

职责：

- 定义 FastAPI app 和 router。
- 接收文件上传和请求参数。
- 调用 application use case。
- 返回标准 DTO。
- 处理 HTTP 状态码。
- 不直接调用 `PDFParser`、`PTRExtractor`、`ReportChecker` 等具体实现。
- 不直接保存文件到 `uploads/`。
- 不拼装规则细节。

示例职责边界：

| 可以做 | 不可以做 |
|---|---|
| 校验是否上传 PDF | 解析 PDF 内容 |
| 调用 `ComparePtrUseCase.start()` | 判断条款是否一致 |
| 返回 `JobProgressResponse` | 维护全局 `tasks` dict |
| 返回 `FindingResponse` | 执行 C01-C11 规则 |

### 3.2 Application 层

目录：`backend/app/application`

职责：

- 编排完整业务用例。
- 管理任务生命周期。
- 调用 storage 保存上传文件。
- 调用 infrastructure parser/extractor 获取事实数据。
- 调用 rules registry 执行规则。
- 聚合 Findings、summary、导出 DTO。
- 负责异常转业务错误。

核心 use case：

| Use case | 职责 |
|---|---|
| `ComparePtrUseCase` | 执行 PTR PDF + 报告 PDF 的解析、抽取、条款/表格核对、结果聚合。 |
| `CheckReportUseCase` | 执行单报告 PDF 的 C01-C11 抽取和核对。 |
| `ExportResultUseCase` | 根据任务结果导出 PDF。 |

任务服务：

| 组件 | 职责 |
|---|---|
| `JobService` | 创建任务、更新进度、标记成功/失败、读取结果。 |
| `TaskRepository` | 任务状态持久化接口。开发期可内存实现，生产可 Redis/DB。 |
| `ProgressReporter` | 给 use case 更新阶段性进度。 |

### 3.3 Domain 层

目录：`backend/app/domain`

职责：

- 定义业务对象和值对象。
- 不依赖 FastAPI、PyMuPDF、PaddleOCR、ReportLab。
- 不访问文件系统。
- 不包含 OCR/LLM 调用。

核心领域对象：

| 对象 | 说明 |
|---|---|
| `PdfDocument` | PDF 抽取后的通用文本/表格/page 表示。 |
| `ReportDocument` | 检验报告领域对象。 |
| `PtrDocument` | PTR 领域对象。 |
| `InspectionItem` | 检验项目行。 |
| `SampleDescriptionRow` | 样品描述表格部件行。 |
| `LabelEvidence` | 中文标签 OCR 结构化结果。 |
| `Caption` | 照片页 caption 结构。 |
| `PtrClause` | PTR 条款。 |
| `PtrTableReference` | 条款内 `见表 X` 引用。 |
| `CanonicalTable` | 表格标准表示。 |
| `ParameterRecord` | 参数名/维度/值/单位记录。 |
| `Finding` | 所有规则统一输出。 |

### 3.4 Rules 层

目录：`backend/app/rules`

职责：

- 每条规则独立实现。
- 输入领域对象，输出 `list[Finding]`。
- 不读文件。
- 不调用 OCR/LLM。
- 不操作 HTTP。
- 不做导出渲染。

统一规则接口：

```text
RuleInput(domain objects + context) -> list[Finding]
```

规则分类：

| 分组 | 规则 |
|---|---|
| report | C01-C11。 |
| ptr | PTR 范围过滤、条款一致性、表格引用展开、参数表一致性。 |

### 3.5 Infrastructure 层

目录：`backend/app/infrastructure`

职责：

- 适配外部库与 IO。
- PyMuPDF 解析。
- PaddleOCR 调用。
- LLM/VLM 调用。
- ReportLab 导出。
- 文件存储。
- 日志与配置。

基础设施对上层暴露接口或 DTO，不把第三方对象泄露到 domain/rules。

## 4. 统一 Finding 设计

### 4.1 Finding 状态

| status | 含义 |
|---|---|
| `pass` | 已核对且通过。 |
| `error` | 明确不符合规则。 |
| `warning` | 证据不足、抽取不完整或需人工复核。 |
| `skipped` | 因规则条件不触发而跳过，例如“见样品描述栏”。 |
| `not_applicable` | 不适用于当前文档或当前范围。 |

### 4.2 Finding 严重性

| severity | 含义 |
|---|---|
| `error` | 需要修正报告或 PTR/报告不一致。 |
| `warning` | 可能需要人工确认。 |
| `info` | 说明性结果或跳过信息。 |

### 4.3 Finding 字段

```text
Finding
  id
  module
  rule_code
  rule_name
  status
  severity
  message
  scope
    document_type
    page_number
    clause_number
    table_number
    sequence_number
    field_name
  expected
  actual
  evidence[]
    source_type
    document_type
    page_number
    bbox
    text
    table_id
    row_index
    column_index
    confidence
  diff[]
    type
    expected_text
    actual_text
    normalized_expected
    normalized_actual
  meta
```

### 4.4 Finding 聚合

Application 层负责把 Findings 聚合成：

- 总状态：只要存在 `error` 则整体失败；存在 `warning` 可显示为需复核。
- 规则 summary：按 rule_code 统计 pass/error/warning/skipped。
- UI summary：按字段、条款、表号、页码分组。
- 导出 DTO：由 exporter 消费，避免 exporter 依赖内部规则对象。

## 5. 报告自身核对流水线

```text
POST /api/report/upload
  -> Api router 校验文件
  -> CheckReportUseCase 创建任务
  -> FileStorage 保存 PDF
  -> PdfParser 解析 PDFDocument
  -> ReportExtractor 抽取：
       first_page_fields
       third_page_fields
       photo_pages
       captions
       label_ocr_results
       sample_description_table
       inspection_table
       page_numbers
  -> ReportRuleRegistry 执行 C01-C11
  -> FindingAggregator 聚合结果
  -> TaskRepository 保存结果
  -> 前端轮询 progress/result/export
```

### 5.1 Extractor 拆分建议

| 新 extractor | 旧来源 | 输出 |
|---|---|---|
| `FirstPageExtractor` | `report_extractor.py` | 首页字段。 |
| `ThirdPageExtractor` | `report_extractor.py` | 第三页字段。 |
| `CaptionExtractor` | `ocr_service.py` + `report_check.py` | 照片页 caption。 |
| `LabelOcrExtractor` | `ocr_service.py` | 标签结构化字段。 |
| `SampleDescriptionExtractor` | `report_checker.py` + `report_check.py` | 样品描述行。 |
| `InspectionTableExtractor` | `report_extractor.py` | 检验项目表。 |
| `PageNumberExtractor` | `page_number_checker.py` | 页码证据。 |

### 5.2 C01-C11 规则文件

| 规则 | 新文件 |
|---|---|
| C01 | `rules/report/c01_first_third_consistency.py` |
| C02 | `rules/report/c02_third_page_label_fields.py` |
| C03 | `rules/report/c03_production_date.py` |
| C04 | `rules/report/c04_sample_description_label.py` |
| C05 | `rules/report/c05_photo_coverage.py` |
| C06 | `rules/report/c06_chinese_label_coverage.py` |
| C07 | `rules/report/c07_item_conclusion.py` |
| C08 | `rules/report/c08_required_fields.py` |
| C09 | `rules/report/c09_sequence_continuity.py` |
| C10 | `rules/report/c10_continuation_marker.py` |
| C11 | `rules/report/c11_page_number_continuity.py` |

## 6. PTR 核对流水线

```text
POST /api/ptr/upload
  -> Api router 校验两个 PDF
  -> ComparePtrUseCase 创建任务
  -> FileStorage 保存 PTR PDF 和 report PDF
  -> PdfParser 解析两个 PDFDocument
  -> PtrExtractor 抽取：
       chapter_2 clauses
       clause hierarchy
       table references
       ptr tables
       canonical tables
  -> ReportExtractor 抽取报告侧：
       inspection table
       standard requirements
       standard-content exclusion ranges
       report tables/text evidence
  -> PtrScopeFilter 标记主范围/排除范围/外部标准
  -> ClauseMatcher 匹配 PTR 条款与报告证据
  -> ClauseTextConsistencyRule 输出文本 Findings
  -> TableReferenceExpansionRule 输出表格 Findings
  -> FindingAggregator 聚合结果
  -> TaskRepository 保存结果
```

### 6.1 PTR extractor 拆分建议

| 新组件 | 旧来源 | 输出 |
|---|---|---|
| `PtrChapterLocator` | `ptr_extractor.py` | 第 2 章页范围和边界。 |
| `PtrClauseParser` | `ptr_extractor.py`、`ptr_models.py` | 条款层级树。 |
| `PtrTableReferenceParser` | `ptr_extractor.py` | `见表 X` 引用。 |
| `PtrTableExtractor` | `pdf_parser.py`、`ptr_extractor.py` | PTR 表格。 |
| `CanonicalTableBuilder` | `table_normalizer.py` | canonical table。 |
| `TableSemanticsService` | `table_semantics.py` | 列角色和参数语义。 |

### 6.2 PTR rules 拆分建议

| 新规则/服务 | 职责 |
|---|---|
| `PtrScopeFilter` | 判断主范围、信息性内容、外部标准、报告标准内容排除。 |
| `ClauseMatcher` | 建立 PTR 条款和报告侧证据匹配。 |
| `ClauseTextConsistencyRule` | 条款正文一致性和 diff。 |
| `TableReferenceExpansionRule` | 对 `见表 X` 展开表格候选。 |
| `TableParameterConsistencyRule` | 参数名、维度和值一致性。 |
| `PresentationMapper` | 把内部状态映射到 UI 展示状态，不能影响规则事实。 |

## 7. 文本与表格归一化策略

### 7.1 Text normalization profile

旧 `text_normalizer.py` 能力较多，新架构不应在所有场景中无差别启用。

建议按 profile 配置：

| Profile | 使用场景 | 允许操作 |
|---|---|---|
| `strict_field` | C01/C02 严格字段比对 | trim、统一换行；是否全半角需确认。 |
| `ptr_clause` | PTR 条款正文比对 | 全半角、自然换行、多余空格。 |
| `ocr_label` | 标签 OCR 字段后处理 | OCR 符号纠错、字段别名、日期候选。 |
| `numeric_parameter` | 表格参数值 | 单位空格、科学计数法、符号变体；是否单位换算需确认。 |

### 7.2 Table normalization

表格 canonical 化步骤：

1. PDF 表格抽取为 dense matrix。
2. 删除重复表头/页眉页脚噪声。
3. 识别多行表头。
4. 物化列路径 `ColumnPath`。
5. 识别维度列、参数列、值列、单位列。
6. 生成 `ParameterRecord`。
7. 输出 diagnostics，包括置信度、未知列、合并单元格处理。

## 8. OCR / LLM / VLM 架构

### 8.1 OCR 接口

```text
OcrEngine
  recognize(image/page) -> OcrRawResult

LabelExtractor
  extract(raw_ocr, context) -> list[LabelEvidence]

CaptionExtractor
  extract(page_text, page_image_ocr) -> list[Caption]
```

### 8.2 LLM/VLM 插件

LLM/VLM 只能通过接口进入：

```text
RecognitionEnhancer
  mode: disabled | fallback | enhance
  enhance_label(raw_ocr, image, context) -> EnhancedLabelEvidence
```

约束：

- 默认 `disabled` 或配置未就绪时不得影响主流程。
- `fallback`：仅在常规 OCR 无结果或低置信度时调用。
- `enhance`：可提供候选或纠错建议，但必须保留原始 OCR 证据。
- 所有 LLM/VLM 输出要记录来源、置信度、是否覆盖原值。

TODO：需要业务确认 LLM/VLM 是否可以直接覆盖字段值。

## 9. 导出架构

目录：`backend/app/infrastructure/export`

组件：

| 组件 | 职责 |
|---|---|
| `ExportResultUseCase` | 验证任务状态，准备导出 DTO。 |
| `ReportLabExporter` | 根据导出 DTO 生成 PDF bytes。 |
| `ExportTemplate` | PTR 和报告自身核对的布局模板。 |
| `FontResolver` | 中文字体与 fallback 管理。 |

导出层只消费统一 DTO，不直接读取 checker/comparator 内部对象。

## 10. API contract 建议

### 10.1 Job response

```text
UploadResponse
  job_id
  status
  message
```

```text
JobProgressResponse
  job_id
  status
  progress
  stage
  message
  error
```

### 10.2 Result response

```text
CheckResultResponse
  job_id
  status
  summary
    total
    pass_count
    error_count
    warning_count
    skipped_count
  findings[]
```

### 10.3 Endpoint

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查。 |
| POST | `/api/ptr/jobs` | 创建 PTR 核对任务。 |
| GET | `/api/ptr/jobs/{job_id}` | 获取任务进度。 |
| GET | `/api/ptr/jobs/{job_id}/result` | 获取结果。 |
| GET | `/api/ptr/jobs/{job_id}/export.pdf` | 导出 PDF。 |
| POST | `/api/report/jobs` | 创建报告自身核对任务。 |
| GET | `/api/report/jobs/{job_id}` | 获取任务进度。 |
| GET | `/api/report/jobs/{job_id}/result` | 获取结果。 |
| GET | `/api/report/jobs/{job_id}/export.pdf` | 导出 PDF。 |

兼容策略：可短期保留旧路径 `/api/ptr/upload`、`/api/report/upload` 作为 adapter，但新前端应使用新路径。

## 11. 前端架构

### 11.1 目录结构

```text
frontend/src/
  app/
    App.tsx
    router.tsx
    providers.tsx
  shared/
    api/
      httpClient.ts
      jobPolling.ts
    components/
      Button.tsx
      FileDropzone.tsx
      FindingList.tsx
      FindingCard.tsx
      StatusBadge.tsx
      ExportButton.tsx
    hooks/
      useJobPolling.ts
      useFileUpload.ts
    layout/
      DashboardLayout.tsx
      GlassPanel.tsx
    types/
      finding.ts
      job.ts
  features/
    ptr-compare/
      api/
        ptrCompareApi.ts
      components/
        PTRUpload.tsx
        PTRResults.tsx
        ClauseFindingCard.tsx
        TableFindingCard.tsx
      pages/
        PTRComparePage.tsx
      types/
        ptr.ts
    report-check/
      api/
        reportCheckApi.ts
      components/
        ReportUpload.tsx
        ReportResults.tsx
        RuleSummary.tsx
        ReportFindingCard.tsx
      pages/
        ReportCheckPage.tsx
      types/
        report.ts
  pages/
    Dashboard.tsx
  styles/
    globals.css
```

### 11.2 前端职责

| 层 | 职责 |
|---|---|
| `shared/api` | HTTP client、错误处理、job polling。 |
| `shared/components` | 通用 UI，不懂业务规则。 |
| `features/ptr-compare` | PTR 相关上传、结果展示、条款/表格 Finding 展示。 |
| `features/report-check` | C01-C11 上传、结果展示、规则 summary。 |
| `shared/types/finding.ts` | 与后端统一 Finding contract。 |

### 11.3 UI 状态

前端应围绕统一 Finding 展示：

- `error`：红色/错误态。
- `warning`：黄色/需人工复核态。
- `pass`：通过态。
- `skipped` / `not_applicable`：说明态。

筛选建议：

- 全部。
- 仅错误。
- 错误 + 警告。
- 按规则编号。
- PTR 特有：按条款/表格。
- 报告特有：按 C01-C11。

## 12. 测试架构

### 12.1 后端测试目录

```text
backend/tests/
  unit/
    domain/
    rules/
      report/
      ptr/
    normalize/
    tables/
  integration/
    extraction/
    pdf_parser/
    ocr/
    export/
  api/
    test_ptr_jobs.py
    test_report_jobs.py
  golden/
    test_report_golden.py
    test_ptr_golden.py
  fixtures/
    builders/
    pdf_samples/
```

### 12.2 旧测试迁移策略

| 旧测试 | 新位置 |
|---|---|
| `test_third_page_checker.py` | `tests/unit/rules/report/test_c01_c02_c03.py` |
| `test_report_checker.py` | `tests/unit/rules/report/test_c04_c05_c06.py` |
| `test_inspection_item_checker.py` | `tests/unit/rules/report/test_c07_c08_c09_c10.py` |
| `test_page_number_checker.py` | `tests/unit/rules/report/test_c11.py` |
| `test_ptr_extractor.py` | `tests/integration/extraction/test_ptr_extractor.py` |
| `test_table_comparator.py` | `tests/unit/rules/ptr/test_table_reference_expansion.py` |
| `test_comparator.py` | `tests/unit/rules/ptr/test_clause_text_consistency.py` |
| `test_export.py` | `tests/integration/export/test_pdf_export.py` |
| `test_api_ptr.py` | `tests/api/test_ptr_jobs.py` |
| `test_api_report.py` | `tests/api/test_report_jobs.py` |

### 12.3 验收分层

| 层 | 验收标准 |
|---|---|
| Domain/rules | 无 FastAPI/PyMuPDF 依赖，单元测试快速稳定。 |
| Infrastructure | 对真实 PDF/OCR 有集成测试，失败可诊断。 |
| Application | 可用 fake parser/rules/storage 测试任务编排。 |
| API | 不依赖真实 OCR 即可测试 HTTP contract。 |
| Golden | 使用真实素材跑端到端回归。 |
| Frontend | 上传/轮询/结果/导出入口交互可测。 |

## 13. 配置与部署

### 13.1 配置项

| 配置 | 说明 |
|---|---|
| `MAX_FILE_SIZE_MB` | 默认沿用 50MB，需确认。 |
| `MAX_PDF_PAGES` | 默认沿用 200，需确认。 |
| `OCR_ENGINE` | PaddleOCR/RapidOCR 等。 |
| `LLM_MODE` | `disabled` / `fallback` / `enhance`。 |
| `VLM_MODE` | `disabled` / `fallback` / `enhance`。 |
| `TASK_BACKEND` | `memory` / `redis` / `database`。 |
| `FILE_STORAGE_BACKEND` | `local` / `object_storage`。 |
| `RESULT_RETENTION_HOURS` | 结果保留时长。 |

### 13.2 部署边界

- 后端无状态化目标：任务状态和文件存储抽象化后，可横向扩展。
- OCR 资源较重，应支持单独 worker 或队列化。
- LLM/VLM 为可选增强，不应阻断核心规则。

## 14. 禁止事项

1. 不在 router 内写 C01-C11 或 PTR 规则。
2. 不在 rules 内调用 OCR、LLM、ReportLab 或文件系统。
3. 不在 domain 内引用 FastAPI/PyMuPDF/PaddleOCR。
4. 不把 `uploads/`、`temp/`、`logs/` 纳入业务目录。
5. 不把旧 Electron `src/main`、`src/renderer`、`python_backend` 带入新架构。
6. 不用 LLM/VLM 输出覆盖原始证据而不留痕。
7. 不在导出层重新计算规则结果。
8. 不在前端硬编码规则判断逻辑；前端只展示后端 Finding。

