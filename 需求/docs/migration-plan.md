# 迁移与重写阶段计划（migration plan）

> 原则：不直接删除旧代码；先建立新结构与测试防护，再逐步迁移业务能力。每一阶段都必须有测试和验收标准。旧 Electron 路径不迁入新架构。

## 阶段 0：冻结基线与资产确认

### 目标

建立旧项目可追溯基线，确认哪些资产可复用、哪些规则存在冲突、哪些素材作为 golden 输入。

### 迁移内容

- 固定旧仓库当前分支/commit 作为 legacy baseline。
- 记录 `backend/`、`frontend/`、`backend/tests/`、`素材.zip` 资产。
- 确认 `素材/expected` 与本项目 `素材.zip` 的对应关系。
- 标记冲突规则：尤其 C07 空结果、C03 日期值比较、C01/C02 严格一致与 OCR 容错。

### 新文件位置

- `docs/legacy-inventory.md`
- `docs/known-requirements.md`
- `docs/open-questions.md`
- `tests/fixtures/legacy/`（后续迁移时放样例索引，不复制大文件时可只保留说明）

### 废弃旧文件

本阶段不废弃、不删除任何旧文件，仅标记：

- 根目录 Electron `package.json`
- `src/main`
- `src/renderer`
- `python_backend`
- `uploads/`
- `temp/`

### 测试要求

- 能列出旧测试清单。
- 能列出素材 case 清单。
- Golden expected 来源明确，若不明确则进入 open questions。

### 验收标准

- 5 份文档完成并经人工确认。
- 所有旧测试文件均被记录，无遗漏。
- 规则冲突不被静默“修复”，均进入 open questions。

---

## 阶段 1：新后端骨架与统一 contract

### 目标

建立新后端分层目录、统一 API/job/Finding contract，但不迁移复杂业务规则。

### 迁移内容

- 创建 `api`、`application`、`domain`、`rules`、`infrastructure` 分层。
- 定义统一 `Finding`、`Evidence`、`DiffFragment`、`JobStatus`、`JobResultSummary`。
- 定义 `TaskRepository` 和 `FileStorage` 接口。
- 实现开发期 `InMemoryTaskRepository` 和 `LocalFileStorage`。
- 建立 `GET /api/health`。
- 建立空 use case 骨架：`ComparePtrUseCase`、`CheckReportUseCase`、`ExportResultUseCase`。

### 新文件位置

- `backend/app/api/main.py`
- `backend/app/api/routers/health.py`
- `backend/app/api/schemas/common.py`
- `backend/app/api/schemas/jobs.py`
- `backend/app/api/schemas/findings.py`
- `backend/app/application/jobs/job_service.py`
- `backend/app/application/jobs/task_repository.py`
- `backend/app/application/use_cases/compare_ptr.py`
- `backend/app/application/use_cases/check_report.py`
- `backend/app/application/use_cases/export_result.py`
- `backend/app/domain/findings.py`
- `backend/app/infrastructure/storage/file_storage.py`
- `backend/app/infrastructure/storage/local_file_storage.py`

### 废弃旧文件

暂不删除。标记后续替代：

- `backend/app/main.py`
- `backend/app/routers/ptr_compare.py`
- `backend/app/routers/report_check.py`

### 测试要求

- 新 `Finding` model 单元测试。
- `JobService` 状态流转测试。
- `FileStorage` 本地实现测试。
- `GET /api/health` API 测试。

### 验收标准

- 新 app 可启动。
- router 不包含业务规则。
- API contract 和 domain model 不互相污染。
- 所有新增测试通过。

---

## 阶段 2：通用 PDF、文本、表格基础设施迁移

### 目标

迁移 PDF 解析、文本归一化、表格 canonical 化能力，为报告和 PTR 两条主线提供基础设施。

### 迁移内容

- 迁移 `common_models.py` 到 domain 文档/表格模型。
- 迁移 `pdf_parser.py` 为 PyMuPDF adapter。
- 迁移 `text_normalizer.py`，并增加 profile 机制。
- 迁移 `table_models.py`、`table_normalizer.py`、`table_semantics.py`。
- 将 PyMuPDF 对象隔离在 infrastructure，不泄漏到 domain。

### 新文件位置

- `backend/app/domain/common/geometry.py`
- `backend/app/domain/documents/pdf_document.py`
- `backend/app/domain/tables/table.py`
- `backend/app/domain/tables/canonical_table.py`
- `backend/app/domain/tables/parameter_record.py`
- `backend/app/infrastructure/pdf/pymupdf_parser.py`
- `backend/app/infrastructure/normalize/text_normalizer.py`
- `backend/app/infrastructure/normalize/table_normalizer.py`
- `backend/app/infrastructure/normalize/table_semantics.py`

### 废弃旧文件

迁移完成并通过测试后标记为 legacy：

- `backend/app/models/common_models.py`
- `backend/app/models/table_models.py`
- `backend/app/services/pdf_parser.py`
- `backend/app/services/text_normalizer.py`
- `backend/app/services/table_normalizer.py`
- `backend/app/services/table_semantics.py`

### 测试要求

迁移并通过：

- `test_pdf_parser.py`
- `test_text_normalizer.py`
- `test_table_normalizer.py`
- `test_table_semantics.py`
- `test_report_extractor_merged_cells.py` 中与表格基础设施有关的用例

### 验收标准

- 新 parser 可从真实 PDF 输出 domain `PdfDocument`。
- 新 text normalizer 的 profile 可区分 PTR 文本和严格字段。
- 表格 canonical 测试全部通过或冲突点明确记录。

---

## 阶段 3：OCR、Caption、标签字段抽取迁移

### 目标

把 OCR 引擎、标签字段抽取、Caption 解析从旧 service/router 中拆出，形成可测试的基础设施与抽取组件。

### 迁移内容

- 迁移 `ocr_parser.py` 到 OCR engine adapter。
- 拆分 `ocr_service.py`：
  - OCR 原始识别。
  - Caption 主体名解析。
  - 中文标签字段抽取。
  - 日期/批号/序列号 fallback。
- 迁移 LLM/VLM 为可选 enhancer，不进入规则层。

### 新文件位置

- `backend/app/infrastructure/ocr/paddle_ocr_engine.py`
- `backend/app/infrastructure/ocr/ocr_postprocessor.py`
- `backend/app/infrastructure/ocr/caption_extractor.py`
- `backend/app/infrastructure/ocr/label_ocr_extractor.py`
- `backend/app/infrastructure/llm/llm_service.py`
- `backend/app/infrastructure/llm/vlm_service.py`
- `backend/app/domain/report/label.py`
- `backend/app/domain/report/caption.py`

### 废弃旧文件

迁移完成后标记：

- `backend/app/services/ocr_parser.py`
- `backend/app/services/ocr_service.py`
- `backend/app/services/llm_service.py`
- `backend/app/services/llm_vision_service.py`
- `report_check.py` 中 `_extract_labels_from_photos`、`_extract_photo_captions` 等 router helper

### 测试要求

迁移并通过：

- `test_ocr_parser.py`
- `test_ocr_service.py`
- `test_llm_service.py`
- Caption 主体名解析相关测试
- 标签字段同义词测试

### 验收标准

- 无需 FastAPI 即可测试 OCR/标签/Caption。
- LLM/VLM 未配置时流程不失败。
- 标签字段输出包含原始 OCR 证据和字段来源。

---

## 阶段 4：报告抽取模型与 C01-C03 迁移

### 目标

迁移报告首页/第三页抽取，以及 C01-C03 规则。

### 迁移内容

- 迁移 `report_models.py` 中首页、第三页相关模型。
- 拆分 `report_extractor.py`：首页字段抽取、第三页字段抽取。
- 迁移 `third_page_checker.py` 为三条独立规则。
- 将规则输出改为统一 Finding。
- 对 C01/C02 严格一致和 OCR 容错边界做配置或 TODO 测试标记。
- 对 C03 日期格式和值比较以当前规格落地，旧 SRS 冲突需人工确认。

### 新文件位置

- `backend/app/domain/report/first_page.py`
- `backend/app/domain/report/third_page.py`
- `backend/app/infrastructure/extraction/first_page_extractor.py`
- `backend/app/infrastructure/extraction/third_page_extractor.py`
- `backend/app/rules/report/c01_first_third_consistency.py`
- `backend/app/rules/report/c02_third_page_label_fields.py`
- `backend/app/rules/report/c03_production_date.py`

### 废弃旧文件

迁移完成后标记：

- `backend/app/services/third_page_checker.py`
- `report_extractor.py` 中首页/第三页相关旧函数

### 测试要求

迁移并通过或明确更新：

- `test_third_page_checker.py`
- `test_report_extractor.py` 中首页/第三页部分
- 新 Finding 输出快照测试

冲突测试处理：

- C01/C02 OCR 容错相关用例先标记 `needs_business_decision` 或按人工确认更新。
- C03 “只比格式”旧文档冲突不作为新测试口径，除非业务另行确认。

### 验收标准

- C01-C03 每条规则可独立运行。
- 所有不一致输出 Finding。
- 找不到标签、生产日期缺失等情况状态明确。

---

## 阶段 5：样品描述、照片覆盖、中文标签覆盖 C04-C06 迁移

### 目标

迁移样品描述表格抽取与 C04-C06 规则。

### 迁移内容

- 定义 `SampleDescriptionRow`、`ComponentKey`、`PhotoEvidence`。
- 从旧 `report_checker.py` 和 `report_check.py` helper 中拆出样品描述抽取。
- 迁移 C04 样品描述 vs 中文标签字段核对。
- 迁移 C05 照片覆盖核对。
- 迁移 C06 中文标签覆盖核对。
- 实现同名多行按非空字段联合键匹配。
- 实现“本次检测未使用”例外。

### 新文件位置

- `backend/app/domain/report/sample_description.py`
- `backend/app/domain/report/photo.py`
- `backend/app/infrastructure/extraction/sample_description_extractor.py`
- `backend/app/rules/report/c04_sample_description_label.py`
- `backend/app/rules/report/c05_photo_coverage.py`
- `backend/app/rules/report/c06_chinese_label_coverage.py`

### 废弃旧文件

迁移完成后标记：

- `backend/app/services/report_checker.py`
- `backend/app/routers/report_check.py` 中 `_extract_sample_description_table`、照片/标签抽取 helper

### 测试要求

迁移并通过或明确更新：

- `test_report_checker.py`
- `test_ocr_service.py` 中标签字段相关部分
- 同名多行联合键测试
- “本次检测未使用”例外测试

冲突测试处理：

- 表格空值但标签存在额外字段值是否通过，需要业务确认后更新 C04 测试。

### 验收标准

- C04-C06 每条规则独立输出 Finding。
- Caption 匹配、中文标签关键词、联合键匹配均有测试。
- 未使用部件不因缺照片/缺标签报错。

---

## 阶段 6：检验项目规则 C07-C11 迁移

### 目标

迁移检验项目表格抽取、C07-C10、页码 C11。

### 迁移内容

- 定义 `InspectionItem`、`InspectionTable`、`PageNumberEvidence` 新 domain 模型。
- 拆分检验项目表格抽取。
- 迁移 C07 单项结论逻辑。
- 迁移 C08 非空字段。
- 迁移 C09 序号连续性。
- 迁移 C10 续表标记。
- 迁移 C11 页码连续性。
- 修正或确认 C07 空结果语义冲突。

### 新文件位置

- `backend/app/domain/report/inspection_item.py`
- `backend/app/domain/report/page_number.py`
- `backend/app/infrastructure/extraction/inspection_table_extractor.py`
- `backend/app/infrastructure/extraction/page_number_extractor.py`
- `backend/app/rules/report/c07_item_conclusion.py`
- `backend/app/rules/report/c08_required_fields.py`
- `backend/app/rules/report/c09_sequence_continuity.py`
- `backend/app/rules/report/c10_continuation_marker.py`
- `backend/app/rules/report/c11_page_number_continuity.py`

### 废弃旧文件

迁移完成后标记：

- `backend/app/services/inspection_item_checker.py`
- `backend/app/services/page_number_checker.py`
- `report_extractor.py` 中检验项目抽取旧函数

### 测试要求

迁移并通过或明确更新：

- `test_inspection_item_checker.py`
- `test_page_number_checker.py`
- `test_report_extractor.py` 中检验项目表相关部分
- `test_report_extractor_merged_cells.py`

冲突测试处理：

- `test_empty_test_result_should_be_non_compliant` 需根据当前规格改为期望 `/`，或等待人工确认后决定。

### 验收标准

- C07-C11 均以 Finding 输出。
- 合并单元格、占位符、续表、页码异常均有稳定测试。
- C07 口径明确，不再存在隐式 fallback。

---

## 阶段 7：报告自身核对 use case 与 API 迁移

### 目标

把 C01-C11 串成完整报告自身核对流程，并替换旧 `/api/report` router 的业务编排。

### 迁移内容

- 实现 `CheckReportUseCase` 完整流水线。
- 接入 PDF parser、report extractors、OCR、rules registry。
- 聚合 C01-C11 Findings 和 summary。
- 实现报告结果导出 DTO。
- 新建薄 router。
- 可短期保留旧接口 adapter。

### 新文件位置

- `backend/app/application/use_cases/check_report.py`
- `backend/app/application/services/finding_aggregator.py`
- `backend/app/api/routers/report.py`
- `backend/app/api/schemas/report.py`
- `backend/app/rules/registry.py`

### 废弃旧文件

迁移完成后标记：

- `backend/app/routers/report_check.py`

### 测试要求

迁移并通过：

- `test_api_report.py` 的 contract 用例
- C01-C11 端到端 use case 测试
- 真实素材报告 golden smoke test

### 验收标准

- `/api/report/jobs` 可创建任务。
- progress/result/export API 可用。
- router 中无规则逻辑、无 PDF 解析逻辑、无 OCR 细节。
- 输出全为统一 Finding contract。

---

## 阶段 8：PTR 领域模型、抽取与文本比对迁移

### 目标

迁移 PTR 第 2 章抽取、条款模型、报告侧标准要求抽取、基础文本比对。

### 迁移内容

- 迁移 `PTRClauseNumber`、`PTRClause`、`PTRDocument` 等模型。
- 拆分 `PTRExtractor`：章节定位、条款解析、表格引用解析。
- 迁移报告侧标准要求/标准内容排除范围抽取。
- 迁移 `comparator.py` 中基础条款匹配与 diff。
- 暂不迁移复杂表格展开，先输出文本条款 Findings。

### 新文件位置

- `backend/app/domain/ptr/clause.py`
- `backend/app/domain/ptr/ptr_document.py`
- `backend/app/domain/ptr/table_reference.py`
- `backend/app/infrastructure/extraction/ptr_chapter_locator.py`
- `backend/app/infrastructure/extraction/ptr_clause_parser.py`
- `backend/app/infrastructure/extraction/ptr_table_reference_parser.py`
- `backend/app/rules/ptr/scope_filter.py`
- `backend/app/rules/ptr/clause_matcher.py`
- `backend/app/rules/ptr/clause_text_consistency.py`

### 废弃旧文件

迁移完成后标记部分替代：

- `backend/app/models/ptr_models.py`
- `backend/app/services/ptr_extractor.py`
- `backend/app/services/comparator.py` 中基础文本比对部分

### 测试要求

迁移并通过：

- `test_ptr_extractor.py`
- `test_comparator.py` 中文本比对、条款匹配、scope、外部标准相关用例
- `test_report_extractor.py` 中标准内容排除范围用例

### 验收标准

- 能定位 PTR 第 2 章且不依赖固定标题。
- 能输出条款缺失/不一致/排除范围 Findings。
- 差异高亮可供前端展示和导出。

---

## 阶段 9：PTR 表格引用展开与表格比对迁移

### 目标

迁移 `见表 X` 引用解析、表格候选选择、canonical 表格参数比对。

### 迁移内容

- 迁移 `table_comparator.py` 中表格引用展开逻辑。
- 拆分为：
  - `TableReferenceResolver`
  - `PtrTableCandidateSelector`
  - `ReportEvidenceSelector`
  - `ParameterComparator`
- 接入 canonical table 和 table semantics。
- 处理多页表格、重复表号、多行表头、参数名和值比对。

### 新文件位置

- `backend/app/rules/ptr/table_reference_expansion.py`
- `backend/app/rules/ptr/table_parameter_consistency.py`
- `backend/app/application/services/ptr_table_candidate_selector.py`
- `backend/app/application/services/report_evidence_selector.py`
- `backend/app/domain/tables/parameter_record.py`

### 废弃旧文件

迁移完成后标记：

- `backend/app/services/table_comparator.py`
- `backend/app/services/comparator.py` 中表格/结构化 bundle 相关逻辑

### 测试要求

迁移并通过：

- `test_table_comparator.py`
- `test_ptr_extractor_multidim.py`
- `test_table_normalizer.py`
- `test_table_semantics.py`
- `test_comparator.py` 中结构化 bundle/数值/科学计数法相关用例

### 验收标准

- `见表 X` 能展开到表格 Findings。
- 重复表号候选选择可解释。
- 参数名、维度、值、单位均保留证据。
- 多页表格和多行表头有 regression 测试。

---

## 阶段 10：PTR use case、API 与导出迁移

### 目标

把 PTR 文本比对和表格比对串成完整流程，并替换旧 `/api/ptr` router 的业务编排。

### 迁移内容

- 实现 `ComparePtrUseCase` 完整流水线。
- 接入 PTR extractor、report extractor、scope filter、clause/text/table rules。
- 聚合 PTR Findings 和 summary。
- 迁移 PTR PDF 导出。
- 新建薄 router。
- 短期保留旧接口 adapter。

### 新文件位置

- `backend/app/application/use_cases/compare_ptr.py`
- `backend/app/api/routers/ptr.py`
- `backend/app/api/schemas/ptr.py`
- `backend/app/infrastructure/export/reportlab_exporter.py`

### 废弃旧文件

迁移完成后标记：

- `backend/app/routers/ptr_compare.py`
- `backend/app/services/report_export_service.py` 中旧 PTR 导出入口
- `backend/app/services/presentation_status.py` 可迁到 presenter 或前端

### 测试要求

迁移并通过：

- `test_api_ptr.py`
- `test_export.py` 中 PTR 导出相关用例
- PTR 真实素材 golden smoke test
- 5332/3940/5782 等旧回归样例

### 验收标准

- `/api/ptr/jobs` 可创建任务。
- progress/result/export API 可用。
- PTR 文本和表格 Findings 同一 contract 输出。
- router 中无业务编排和比对逻辑。

---

## 阶段 11：前端 feature 化重构

### 目标

将前端从页面/全局 service 结构重组为按 feature 组织，接入新 API contract 和统一 Finding 展示。

### 迁移内容

- 建立 `shared/api`、`shared/components`、`shared/types`。
- 建立 `features/ptr-compare`。
- 建立 `features/report-check`。
- 拆分旧 `ptrApi.ts` 为 `ptrCompareApi.ts` 和 `reportCheckApi.ts`。
- 结果展示从旧 result shape 改为 Finding contract。
- 保留 Dashboard、深色玻璃拟态、上传、进度、筛选、导出交互。

### 新文件位置

- `frontend/src/shared/api/httpClient.ts`
- `frontend/src/shared/api/jobPolling.ts`
- `frontend/src/shared/types/finding.ts`
- `frontend/src/shared/types/job.ts`
- `frontend/src/shared/components/FindingList.tsx`
- `frontend/src/features/ptr-compare/api/ptrCompareApi.ts`
- `frontend/src/features/ptr-compare/pages/PTRComparePage.tsx`
- `frontend/src/features/report-check/api/reportCheckApi.ts`
- `frontend/src/features/report-check/pages/ReportCheckPage.tsx`

### 废弃旧文件

迁移完成后标记：

- `frontend/src/services/ptrApi.ts`
- `frontend/src/pages/ptr-compare/*` 的旧 result shape 依赖版本
- `frontend/src/pages/report-check/*` 的旧 result shape 依赖版本

注意：旧文件先保留，待新路由和验收完成后再删除。

### 测试要求

- API client mock 测试。
- 上传表单测试。
- job polling 测试。
- Finding 筛选测试。
- 导出按钮状态测试。
- Dashboard 路由测试。

### 验收标准

- 前端只依赖新 API contract。
- PTR 和报告功能彼此隔离在 feature 中。
- UI 不硬编码业务规则判定。
- 深色玻璃拟态视觉保持。

---

## 阶段 12：Golden 回归、性能与清理

### 目标

用真实素材进行端到端回归，确认旧规则资产已迁移完成，最后清理 legacy 入口。

### 迁移内容

- 接入 `素材.zip` 中 PTR/report/record PDF。
- 接入 repo 中 `素材/expected` 或重新生成经人工确认的 expected。
- 跑报告自身核对 golden。
- 跑 PTR 核对 golden。
- 对 OCR 失败、PDF 解析异常、导出中文字体做稳定性测试。
- 标记旧代码为 deprecated，最终由人工确认后删除。

### 新文件位置

- `backend/tests/golden/test_report_golden.py`
- `backend/tests/golden/test_ptr_golden.py`
- `backend/tests/fixtures/materials_index.yaml`
- `backend/tests/fixtures/expected/*.json`
- `docs/test-strategy.md`（可选）

### 废弃旧文件

人工确认后可删除或移入 `legacy/`：

- `backend/app/routers/ptr_compare.py`
- `backend/app/routers/report_check.py`
- 被完全替代的 `backend/app/services/*` 旧实现
- 被完全替代的 `backend/app/models/*` 旧实现
- 根目录 Electron `package.json`
- `src/main`
- `src/renderer`
- `python_backend`

运行时目录仍不纳入版本：

- `uploads/`
- `temp/`
- `logs/`

### 测试要求

- 全量后端单元测试。
- 全量后端集成测试。
- Golden 测试。
- 前端 build/test。
- API smoke test。
- PDF 导出 smoke test。

### 验收标准

- C01-C11 全部完成并有 Finding 输出。
- PTR 文本与表格核对完成并有 Finding 输出。
- 旧测试全部迁移或有明确废弃理由。
- Golden 结果通过或差异经人工确认。
- 旧 Electron 路径不再参与构建、测试或文档主线。
- router 无业务规则。

## 跨阶段风险控制

| 风险 | 控制措施 |
|---|---|
| 旧测试与新规格冲突 | 先标记冲突测试，不静默改业务。由 open questions 驱动确认。 |
| OCR 不稳定导致测试 flaky | 单元测试 mock OCR；真实 OCR 放 integration/golden。 |
| PDF 表格抽取不稳定 | 保留 canonical diagnostics，golden 固定样例。 |
| 规则迁移遗漏 | 每条 C 规则独立文件、独立测试、Finding 快照。 |
| router 再次变胖 | code review checklist：router 不允许调用 parser/checker/comparator。 |
| 前端 result shape 变动大 | 先引入 adapter，将旧 result 转 Finding，再逐步切换。 |
| 导出与 UI 状态不一致 | 导出只消费同一 Finding DTO。 |
| LLM/VLM 结果不可追溯 | 每个增强值保留原始 OCR、增强来源、覆盖标记。 |

## 完成定义

重写完成需满足：

1. 后端目录按 `api/application/domain/rules/infrastructure` 分层。
2. 前端按 feature 组织。
3. 所有规则输出统一 Finding。
4. router 不含业务规则、PDF 解析、OCR、导出细节。
5. PDF parser、OCR、extractor、rules、export 完全分离。
6. C01-C11 需求均实现并通过测试。
7. PTR 第 2 章条款和 `见表 X` 表格展开比对均实现并通过测试。
8. 旧后端测试全部迁移或有书面废弃理由。
9. 旧 Electron 路径不进入新架构。
10. `uploads/`、`temp/`、`logs/` 不作为业务资产。

