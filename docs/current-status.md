# 当前状态校准

校准日期：2026-06-15

本文件记录当前仓库任务状态、基线验收结果和后续任务完成情况。旧项目只读目录未被修改；任务状态同步仅更新文档状态，不实现新的 C01-C11 或 PTR 功能。

## 路径确认

- 旧项目只读目录存在：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13`
- 新项目写入目录存在：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3`

## T01-T12 状态

| 任务 | 当前状态 | 判断依据 |
| --- | --- | --- |
| T01 | 已完成 | `docs/rewrite-branch-notes.md` 已创建，明确新旧项目路径、旧项目只读、Web 主线、废弃 Electron/python_backend/src 历史主线、运行时目录、分层边界、统一 Finding、迁移依据和测试失败停止规则；T01 文档验收命令通过。 |
| T02 | 已完成 | `AGENTS.md` 已补齐旧项目只读、raw 数据边界、测试失败停止、前端不得写业务判断、后端五层职责、domain 不依赖 infrastructure、规则独立文件和 pytest、PTR scope/clause/table 拆分、统一 Finding 等强约束；T02 文档验收命令通过。 |
| T03 | 已完成 | `backend/app/api`、`application`、`domain`、`rules`、`infrastructure`、`tests` 等目录存在；`app.main` 可 import；后端测试通过。 |
| T04 | 已完成 | `frontend/src/app`、`entities`、`features`、`shared` 等结构存在；Vite React TypeScript build 通过。 |
| T05 | 已完成 | `backend/app/domain/common.py`、`finding.py`、`result.py`、`task.py` 提供统一模型；领域模型测试通过；import smoke 通过。 |
| T06 | 已完成 | `backend/app/application/task_repository.py` 已新增 `TaskRepository` 协议、`InMemoryTaskRepository`、`TaskResult` 和缺失异常；`TaskService` 已迁移为依赖 repository，支持 create/get/update/save result/get result/mark failed/list；新增 `backend/tests/application/test_task_repository.py` 并更新 `test_task_service.py`；后端全量测试通过。 |
| T07 | 已完成 | `LocalFileStore` 已支持保存上传文件、读取上传文件路径、保存/读取 `CheckResult` JSON、保存/读取导出文件，并自动创建 `runtime/uploads`、`runtime/results`、`runtime/exports`；`.gitignore` 已忽略 `runtime/`；`backend/tests/infrastructure/storage/test_local_file_store.py` 使用 `tmp_path` 覆盖存取、目录创建、缺失文件和路径安全。 |
| T08 | 已完成 | `GET /api/health` 在 `backend/app/api/routes_health.py` 实现并挂载；`backend/tests/api/test_health.py` 覆盖 200 和响应字段。 |
| T09 | 已完成 | 统一任务 API 路径已存在：报告核对、PTR 对比、任务查询、结果和导出；router 保持 HTTP 输入输出边界；API 测试通过。 |
| T10 | 已完成 | PDF parser 位于 `backend/app/infrastructure/pdf/pymupdf_parser.py`，输出 `ParsedPdf`/`PdfPage` 等结构，不直接做规则判定或 OCR；PDF infrastructure 测试通过。 |
| T11 | 已完成 | OCR adapter/parser 位于 `backend/app/infrastructure/ocr/`，支持注入 engine/fallback text、字段解析、caption 和 confidence；OCR infrastructure 测试通过。 |
| T12 | 已完成 | Report extractor 已拆到 `backend/app/infrastructure/report/` 的 page locator、field extractor、inspection table、sample description、photo/label extractor；usecase 组合为 `ReportDocument`；相关测试通过。 |

已同步 `docs/tasks.md`：T01、T02、T03、T04、T05、T06、T07、T08、T09、T10、T11、T12 标记为 `[x]`。

## 分层和越界检查

- API 层主要处理上传校验、依赖注入、任务状态和响应序列化；未发现把 C01-C11 规则直接写进 router。
- PDF parser 输出结构化 PDF 内容和诊断；未发现直接输出 C 规则或 PTR 业务判定。
- OCR adapter 输出 OCR 结构、字段候选、caption 和 confidence；未发现直接决定 PASS/FAIL。
- 前端仅使用后端返回的 `Finding`、`check_id`、任务状态和结果类型做展示分组；未发现重新计算 C01-C11 或 PTR 结论。
- 当前仓库已经存在 `backend/app/rules/report/c01...c11`、`backend/tests/rules/report/test_c01...c11`、`backend/app/rules/ptr/*` 和 PTR usecase/rules 测试。这不是本次校准新增内容，但相对 `docs/tasks.md` 的 T13+、PTR 后续任务顺序属于状态漂移，需要后续单独验收或回填任务状态，不建议继续叠加迁移前跳过该确认。

## 基线验证结果

| 命令 | 结果 |
| --- | --- |
| `test -d /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13 && test -d /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3` | 通过 |
| `cd backend && python -m pytest tests/ -v` | 通过，`289 passed` |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功 |
| `bash scripts/test.sh` | 通过，后端 `280 passed`，前端 build 成功 |
| `bash scripts/build.sh` | 通过，后端 `compileall` 和前端 build 成功 |
| 后端 import smoke | 通过，`app.main`、domain、task service、LocalFileStore、PDF/OCR/report extractor 关键模块可 import |
| `test -f docs/rewrite-branch-notes.md` | 通过 |
| `rg "只读\|测试失败\|Electron\|python_backend" docs/rewrite-branch-notes.md` | 通过 |
| `test -f AGENTS.md` | 通过 |
| `rg "旧项目只读\|raw\|测试失败\|前端不得" AGENTS.md` | 通过 |
| `cd backend && python -m pytest tests/application/test_task_repository.py tests/application/test_task_service.py -v` | 通过，`9 passed` |
| `cd backend && python -m pytest tests/infrastructure/storage/test_local_file_store.py -v` | 通过，`14 passed` |
| `git diff --check` | 通过 |

一次手写 import smoke 初稿引用了不存在的 `parse_ocr_text` 函数，修正为实际导出的 `OCRParser`/`correct_text_symbols` 后通过；这属于校验脚本笔误，不是项目测试失败。

## 失败测试

无。基线要求的后端测试、前端构建、`scripts/test.sh`、`scripts/build.sh` 均已通过。

## 需要先修复的问题

1. T29/T30 后续深层语义：报告侧 `canonical_tables` 已由 `ReportParameterTableExtractor` 接入 `PTRCompareUseCase`，PTR 双文件上传 API 已有受控 fixture/golden 端到端保护，报告侧候选表选择、条件/允许误差 Finding、基础 numeric semantic 和分段阈值防错匹配已补强；但 diff 结构、scope finding 暴露口径、复杂数学满足判断、旧 measurement bundle 展示结构和真实可公开样本 golden 仍需后续补强。

## 规则与 PTR 状态漂移审计

- 审计文档：`docs/rule-ptr-implementation-audit.md`
- 审计日期：2026-06-15
- 验证命令：`cd backend && python -m pytest tests/rules/report tests/rules/ptr tests/infrastructure/table tests/infrastructure/ptr tests/application/test_report_check_usecase.py tests/application/test_ptr_compare_usecase.py -v`
- 验证结果：通过，`158 passed`
- 结论摘要：C01-C11 均已有独立实现和 pytest；PTR scope、clause、table reference、parameter compare、CanonicalTable/TableNormalizer 均存在。C02/C03/C05/C07/C10 的业务口径或真实样本覆盖仍待确认。PTR `parameter_compare.py` 已在 2026-06-15 接入 `PTRCompareUseCase`；报告侧 `canonical_tables` 主 key 已由 `ReportParameterTableExtractor` 从 `ParsedPdf` 表格生成并传入 usecase。

## 任务状态同步记录

同步日期：2026-06-15

本次只根据 `docs/rule-ptr-implementation-audit.md` 的明确证据更新 `docs/tasks.md`，未修改业务代码、前端代码、规则代码、PTR 代码或测试。

本次标记完成的任务：

| 任务 | 证据来源 |
| --- | --- |
| T13 | 审计文档确认 C01 真实实现，覆盖首页/第三页委托方、样品名称、型号规格严格一致性，缺失和不一致输出统一 Finding，独立 pytest 已覆盖核心路径。 |
| T16 | 审计文档确认 C04 已实现样品描述五字段比对、字段同义词、同名多行 identity 匹配、空值规则和未使用部件 WARN，独立 pytest 覆盖。 |
| T18 | 审计文档确认 C06 已实现中文标签关键词、非空字段联合键、同名多行区分、普通照片不误判、低置信 WARN，边界符合 AGENTS.md。 |
| T20 | 审计文档确认 C08 已实现检验结果、单项结论、备注非空检查，占位符、合并单元格、续表行均有测试。 |
| T21 | 审计文档确认 C09 已实现从 1 开始、跳号、重复、空白序号、续号归属和续号引用异常等序号连续性检查。 |
| T23 | 审计文档确认 C11 已实现第三页起内部页码解析、连续性、重复、末页 Y=XXX、总页数一致、缺失和无法解析错误。 |
| T24 | 审计文档确认 `default_report_rules()` 注册 C01-C11，runner 汇总和单规则异常隔离有测试。 |
| T26 | 审计文档确认 PTRExtractor 已按编号定位第 2 章，抽取层级、表引用、scope_type，并覆盖跨页续表合并和拒绝。 |
| T28 | 审计文档确认 CanonicalTable/TableNormalizer 已有领域模型、表头路径、角色识别、维度 fill-down、续表诊断和参数记录构建测试。 |

保持未完成或部分完成的任务：

| 任务 | 保持原因 |
| --- | --- |
| T14 | C02 三个核心字段完成，但委托方/委托方地址是否进入 ERROR/WARN、第三页字段缺失等级仍需人工确认。 |
| T15 | C03 当前只比较日期格式，未启用日期值比较；与“格式和值一致性”的任务表述仍有口径冲突。 |
| T17 | C05 核心照片覆盖完成，但同名多部件照片覆盖策略和真实 caption fixture 覆盖不足。 |
| T19 | C07 主逻辑完成，但“无菌生长”等语义和空白检验结果最终口径仍需确认。 |
| T22 | C10 续表位置规则完成，但缺少显式“上一页末尾未完成”的模型字段，真实 extractor 支撑还需验收。 |
| T27 | PTR scope 和条款正文比对已有核心能力，但额外条款、2.4 suppression 审计化、旧 comparator 深层语义仍待补齐。 |
| T29 | table reference、table candidate selector 和 parameter compare 均存在，参数 finding 已能进入 usecase 结果，报告侧 canonical 表也已由 extractor 写入主 key，条件/允许误差 Finding、基础 numeric semantic 和 segment-safe matching 已补强；但 diff 结构、复杂数学满足判断、旧 measurement/segmented threshold bundle 展示语义和真实样本复杂表格仍未完全闭环。 |
| T30 | PTRCompareUseCase 已有双文件流程，已调用 `compare_parameter_tables`，并能从报告 `ParsedPdf` 表格抽取 canonical tables；但完整 PTR API 真实样本端到端验收和 scope finding 暴露仍需补强。 |

T29/T30 的最大端到端漂移点已修复：规则层已有的 `parameter_compare.py` 现在会被 `PTRCompareUseCase` 调用，`见表 X` 的参数值、单位、条件、允许误差或缺失差异可进入最终 `PTR_TABLE` CheckResult。报告侧 canonical 表也已能从 `ParsedPdf` 表格进入 usecase。基础 numeric semantic 和 segment-safe matching 已补强；由于完整任务验收还涉及 diff 结构、复杂数学满足判断、旧 measurement bundle 展示和真实样本 golden，本次没有把 T29/T30 标记为完成。

## PTR parameter_compare 接入记录

接入日期：2026-06-15

本次实现：

- `PTRCompareUseCase` 新增可注入的 `parameter_compare` 依赖，默认复用 `app.rules.ptr.parameter_compare.compare_parameter_tables`。
- `PTRCompareUseCase` 在 `table_reference_compare` 之后，对每个已纳入范围且引用表唯一的 PTR clause 运行参数比对。
- 参数 finding 与表引用 finding 合并到统一 `PTR_TABLE` CheckResult，继续使用统一 `Finding`，summary 统计会包含参数 ERROR/WARN。
- PTR 表缺失或 PTR 表候选歧义时不强行参数比对，保留原有 `table_reference_compare` finding。
- 报告侧 canonical 表当前以 `ReportDocument.metadata["canonical_tables"]` 为推荐主 key；`parameter_tables` 和 `ptr_compare_tables` 仍作为兼容读取 key。`ReportParameterTableExtractor` 会从 `ParsedPdf.tables` 和 `PdfPage.tables` 归一化报告参数表，并由 `PTRCompareUseCase` 写入主 key。

新增/更新测试覆盖：

- PTR 和报告引用同一表但参数值不同，最终 `PTR_TABLE` findings 包含 `PTR_TABLE_VALUE_MISMATCH`。
- 单位不同，最终 findings 包含 `PTR_TABLE_UNIT_MISMATCH`。
- PTR 表有参数但报告表缺失该参数，最终 findings 包含 `PTR_TABLE_PARAM_MISSING`。
- PTR 表引用缺失或歧义时保留 table reference finding，且不会因参数比对导致任务失败。
- 表完全一致时不产生 parameter compare ERROR finding。
- 报告额外参数沿用当前 `parameter_compare` 既有口径，不额外产生 finding。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/rules/ptr tests/infrastructure/table tests/infrastructure/ptr tests/application/test_ptr_compare_usecase.py -v` | 通过，`30 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`296 passed` |

## 报告侧 canonical 表链路验收记录

验收日期：2026-06-15

本次实现：

- 新增 `ReportParameterTableExtractor`，位于 `backend/app/infrastructure/report/parameter_table_extractor.py`，负责把报告 `ParsedPdf` 中的 `PdfTable` 归一化为 `CanonicalTable`。
- `TableNormalizer` 现在会将表号写入 `CanonicalTable.table_number`，来源优先为 `PdfTable.metadata["table_number"]`，其次从 caption/title 中解析 `表 X`。
- `PTRCompareUseCase` 在构建报告 `ReportDocument` 时调用 `ReportParameterTableExtractor.extract_tables(parsed_pdf)`，并把结果写入推荐主 key `ReportDocument.metadata["canonical_tables"]`。
- `PTRCompareUseCase` 继续兼容读取 `canonical_tables`、`parameter_tables`、`ptr_compare_tables`，但后续新增 extractor 和测试应优先使用 `canonical_tables`。
- `parameter_compare` 算法未被重写；usecase 仍只做流程编排。

新增/更新测试覆盖：

- 接近真实报告表格结构可转换为 `CanonicalTable`，覆盖参数名、值、单位、条件、备注、表号和表题。
- `ReportDocument.metadata["canonical_tables"]` 序列化和反序列化后不丢失 table number、parameter records、unit 和 values。
- `PTRCompareUseCase` 从报告 `ParsedPdf` 表格进入链路，不再只依赖测试手工塞入 metadata，即可输出 `PTR_TABLE_VALUE_MISMATCH`、`PTR_TABLE_UNIT_MISMATCH` 和 `PTR_TABLE_PARAM_MISSING`。
- 报告侧无 canonical table 时任务不失败，当前沿用 `parameter_compare` 既有口径输出缺失参数 finding。
- 表完全一致时不产生 parameter compare ERROR。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/application/test_ptr_compare_usecase.py -v` | 通过，`10 passed` |
| `cd backend && python -m pytest tests/rules/ptr tests/infrastructure/table tests/infrastructure/ptr tests/application/test_ptr_compare_usecase.py -v` | 通过，`31 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`299 passed` |

## PTR 双文件 API fixture/golden 验收记录

验收日期：2026-06-15

本次完成：

- 新增 API 级端到端测试 `backend/tests/api/test_api_ptr_compare_e2e.py`，通过 `TestClient` 调用 `POST /api/tasks/ptr-compare` 上传 PTR PDF 和报告 PDF 两个 multipart 文件。
- 测试保留真实上传路径、真实 `TaskService`、真实 `PTRCompareUseCase` 编排、真实 PTR 规则和 JSON export；为稳定性只替换 PDF parser、PTR extractor、report extractor 和 inspection table extractor，输入为受控领域模型与接近真实的报告参数表 `PdfTable`。
- 新增 compact golden expected：`fixtures/golden/api/ptr_compare_e2e.expected.json`。该 golden 不固定完整大 JSON，而固定 `task_type`、severity 计数、finding code 集合和三类 parameter finding 是否存在，避免 task_id、时间戳和完整 diff 结构造成无意义漂移。
- API e2e 已验证 `GET /api/tasks/{task_id}`、`GET /api/tasks/{task_id}/result` 和 `GET /api/tasks/{task_id}/export?format=json` 均能拿到 PTR findings。

覆盖的 finding code：

- `PTR_CLAUSE_TEXT_MISMATCH`
- `PTR_TABLE_MISSING`
- `PTR_TABLE_VALUE_MISMATCH`
- `PTR_TABLE_UNIT_MISMATCH`
- `PTR_TABLE_PARAM_MISSING`

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/api/test_api_ptr_compare_e2e.py -v` | 先按 TDD 红灯失败于缺少 golden expected；补充 expected 后通过，`1 passed` |
| `cd backend && python -m pytest tests/api tests/application/test_ptr_compare_usecase.py tests/rules/ptr tests/infrastructure/table tests/infrastructure/ptr -v` | 通过，`44 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`300 passed` |

T29/T30 状态：

- 本次不把 T29/T30 标记完成。
- 已补强 T30 的双文件上传 API 端到端 fixture/golden 验收。
- 已补强 T29 的受控候选表选择策略：报告侧同表号多候选会按表号、归一化 caption、caption 候选内参数签名 overlap 和合并表优先级选择；无法唯一确定时输出 `PTR_TABLE_CANDIDATE_AMBIGUOUS` 并跳过 `parameter_compare`，避免误报。
- 剩余项仍包括：diff_builder 展示结构、复杂 numeric satisfaction 语义、旧 measurement/segmented threshold bundle 展示、scope finding 暴露口径，以及真实可公开样本的完整 golden 验收。

## PTR 表候选选择策略补强记录

验收日期：2026-06-15

本次实现：

- 新增 `backend/app/rules/ptr/table_candidate_selector.py`，将报告侧候选表选择放在规则层 helper，不写入 router，也不重写 `parameter_compare`。
- `PTRCompareUseCase` 仅调用 selector 并按结果编排：候选唯一时进入 `compare_parameter_tables`；selector 返回歧义 finding 时把 finding 合并到 `PTR_TABLE` CheckResult，并跳过参数比对。
- 候选策略按小步优先级实现：
  1. `table_number == 见表 X` 精确匹配。
  2. 同表号多个候选时，用 NFKC、去空白和标点后的 caption/title 精确归一化匹配。
  3. caption 命中多个候选时，参数名集合 overlap 只在 caption 命中的候选内作为 tie breaker；没有 caption 命中时，再在同表号候选内使用 overlap，且要求 top 分数与次高分数差距达到阈值。
  4. 仍然并列时，如果唯一候选带有 `merged` / `continuation_merged` 诊断或 metadata，则优先选择合并后的完整表。
  5. overlap 接近或仍不唯一时输出 `PTR_TABLE_CANDIDATE_AMBIGUOUS`/`WARN`，不强行进入参数比对。

新增/更新测试覆盖：

- 多个报告表中按表号精确匹配选择正确表。
- 同表号多候选按归一化 caption 选择正确表。
- 表号和 caption 不足时，按参数签名 overlap 明显更高选择正确表。
- caption 命中多个候选时，参数签名 tie breaker 不会越过 caption 去选择其他标题候选。
- overlap 接近时输出 `PTR_TABLE_CANDIDATE_AMBIGUOUS`，且不触发 `parameter_compare`。
- 合并后的表与片段表并列时优先选择合并表。
- `PTRCompareUseCase` 选中正确报告表后，`PTR_TABLE_VALUE_MISMATCH` 能进入最终 CheckResult。
- 选错候选会导致误报的场景已覆盖，正确 caption 候选匹配时不产生错误 finding。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/rules/ptr/test_table_candidate_selector.py tests/application/test_ptr_compare_usecase.py::test_ptr_compare_usecase_selects_report_table_by_caption_before_parameter_compare tests/application/test_ptr_compare_usecase.py::test_ptr_compare_usecase_avoids_false_parameter_error_from_wrong_same_number_table tests/application/test_ptr_compare_usecase.py::test_ptr_compare_usecase_reports_ambiguous_report_table_without_parameter_compare -v` | 通过，`9 passed` |
| `cd backend && python -m pytest tests/rules/ptr tests/application/test_ptr_compare_usecase.py tests/api/test_api_ptr_compare_e2e.py -v` | 通过，`29 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`309 passed` |
| `git diff --check` | 通过 |

## PTR 条件/允许误差 Finding 补强记录

验收日期：2026-06-15

本次实现：

- `ParameterRecord.conditions` 现在参与 `parameter_compare`，但比较时会排除与 `dimensions` 完全相同的型号/分组键，避免把同名维度重复报成条件差异。
- 条件差异输出统一 Finding：`PTR_TABLE_CONDITION_MISMATCH`，包含 expected/actual 条件 dict、evidence、`field_name=conditions` metadata。
- `允许误差`、`允差`、`允许偏差`、`偏差`、`限值`、`阈值`、`标准要求` 等字段差异输出 `PTR_TABLE_TOLERANCE_MISMATCH`，不再落成 generic `PTR_TABLE_VALUE_MISMATCH`。
- `TableSemantics` 和 `TableNormalizer` 增加条件/允差同义词识别，报告侧 `PdfTable` 可把 `试验条件` 写入 `ParameterRecord.conditions`，把 `允差`、`限值` 写入 `values`。
- 本阶段未实现复杂 numeric satisfaction、单位换算、分段阈值 bundle 或容差带数学判断；基础数值表达式等价和 segment-safe matching 已在后续 numeric semantic 阶段补齐。

新增/更新测试覆盖：

- 条件完全一致不产生 condition mismatch。
- 条件文本不同产生 `PTR_TABLE_CONDITION_MISMATCH`。
- 条件空值 vs 有值产生 `PTR_TABLE_CONDITION_MISMATCH`。
- 允许误差完全一致不产生 tolerance mismatch。
- 允许误差不同产生 `PTR_TABLE_TOLERANCE_MISMATCH`。
- 表头同义词 `试验条件`、`检测条件`、`环境条件`、`允差`、`允许偏差`、`限值`、`阈值` 可进入语义识别和 `ParameterRecord`。
- `PTRCompareUseCase` 最终 `PTR_TABLE` CheckResult 能纳入 condition/tolerance findings。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/rules/ptr/test_parameter_compare.py tests/infrastructure/table/test_table_semantics.py tests/infrastructure/table/test_table_normalizer.py tests/application/test_ptr_compare_usecase.py::test_ptr_compare_usecase_includes_parameter_condition_and_tolerance_mismatches -v` | 先按 TDD 红灯失败于 condition 被忽略、允差落入 generic value mismatch、同义词未识别；实现后通过，`17 passed` |
| `cd backend && python -m pytest tests/rules/ptr tests/infrastructure/table tests/application/test_ptr_compare_usecase.py tests/api/test_api_ptr_compare_e2e.py -v` | 通过，`44 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`316 passed` |
| `git diff --check` | 通过 |

## PTR numeric semantic / segmented threshold 补强记录

验收日期：2026-06-15

本次实现：

- 新增 `backend/app/infrastructure/table/numeric_semantics.py`，提供 `normalize_numeric_expression` 与 `numeric_expressions_equivalent`，供 PTR 参数表比对复用。
- `parameter_compare` 在比较参数值、限值、范围、阈值、允许误差等字段前先进行安全 numeric semantic 归一化；语义等价时不输出 ERROR，明确不等价时沿用既有 mismatch Finding。
- 基础数值归一支持 `1` vs `1.0`、`1,000` vs `1000`、全角数字 vs 半角数字。
- 比较符号归一支持 `≥`/`>=`、`≤`/`<=`、`不小于`/`不少于`/`大于等于`、`不大于`/`不超过`/`小于等于`、`大于`、`小于`。
- 范围表达式归一支持 `5~10`、`5～10`、`5-10`、`5至10`、`5到10`，并避免把单个负数误解析为范围。
- 允许误差字段语境下支持 `±0.5`、`+/-0.5`、`允许误差0.5`、`误差0.5`、`允差0.5` 等表达式等价；不做数学容差带判断。
- 分段阈值比对按 `parameter_name + dimensions + conditions` 精确匹配 segment；不把 A 条件下的限值拿去和 B 条件比较。
- PTR 侧存在某个 segment 而报告缺失时复用 `PTR_TABLE_PARAM_MISSING`；PTR segment key 不明确且报告侧存在多个候选时输出 `PTR_TABLE_SEGMENT_AMBIGUOUS`/`WARN` 并跳过该参数比对，避免误报。

新增/复用 Finding code：

- 复用 `PTR_TABLE_VALUE_MISMATCH`：数值语义明确不等价的普通值差异。
- 复用 `PTR_TABLE_TOLERANCE_MISMATCH`：限值、阈值、范围、允许误差字段差异。
- 复用 `PTR_TABLE_PARAM_MISSING`：缺失参数或缺失 segment。
- 新增 `PTR_TABLE_SEGMENT_AMBIGUOUS`：分段条件无法唯一匹配，跳过参数比对。

本次未迁移或暂不支持：

- 不做复杂数学满足判断，例如旧项目中 `≤2.0mL` vs `1.1mL`、`100±20%` vs `120`、`2.5±0.1` vs `+0.03` 这类“报告实测值满足 PTR 约束”的判断。
- 不做复杂单位换算或量纲推断，例如 mL/ml、Ω/ohm 之外更广泛的单位语义换算。
- 不实现旧 measurement bundle / segmented threshold 的展示型 diff 结构。
- `≥/≤` 与 `>/<` 仍按 `known-requirements.md` 的口径视为不同语义，不做等价放宽。

新增/更新测试覆盖：

- 基础数值等价、比较符号等价、范围等价、允许误差表达式等价。
- `≥5` vs `≥6`、`5~10` vs `5~12` 明确产生 mismatch。
- 同一参数不同 dimensions/conditions 时按 segment 匹配，只报告差异 segment。
- PTR 缺失某个 segment 时输出缺失 finding；segment key 不明确时输出 WARN 并跳过强行比对。
- `PTRCompareUseCase` 中 numeric semantic 等价不会进入最终 findings，numeric mismatch 和 segmented threshold mismatch 会进入最终 `CheckResult`。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/infrastructure/table tests/rules/ptr tests/application/test_ptr_compare_usecase.py tests/api/test_api_ptr_compare_e2e.py -v` | 通过，`57 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`329 passed` |

## Codex CLI 运行时审核链路纠偏记录

校准日期：2026-06-15

本次只修改文档，不实现业务代码、不调用真实 Codex、不修改 router、不修改前端、不修改旧项目目录、不继续扩展 numeric semantic。

纠偏结论：

- Codex CLI 明确纳入产品运行时审核链路，定位为受控 auditor / judge。
- 确定性规则仍负责 evidence package 和 candidate findings。
- 最终结果必须同时保留 deterministic finding 与 Codex review 两层证据。
- Codex review 可以 `confirm`、`refute`、`uncertain`、`add_finding`，但不得删除原始 `Finding`。
- Codex runtime 必须使用临时目录、只读 sandbox、output schema、timeout 和失败 fallback；单元测试使用 `FakeCodexRunner`。

本次更新：

- 新增 `docs/codex-cli-auditor-strategy.md`，记录旧项目事实、新定位、后端模块设计、运行时安全边界、数据模型、`CheckResult` 集成、PTR/报告自检优先接入点和 T-CODEX 任务拆分。
- 更新 `AGENTS.md`，删除“LLM 不得替代确定性核对规则”的绝对表述，改为“规则初判 + Codex 审核意见”双层证据链，并补充 Codex CLI runtime 受控使用规则。
- 更新 `docs/tasks.md`，新增 T-CODEX-00 到 T-CODEX-09。
- 同步修正 `docs/known-requirements.md`、`docs/rewrite-architecture.md` 和 `docs/rule-ptr-implementation-audit.md` 中的 evidence-only / 不调用 Codex judge 历史表述，避免与本次纠偏冲突。
- 更新 `docs/current-status.md`，将推荐下一任务调整为 T-CODEX-01。

T-CODEX 状态：

| 任务 | 当前状态 | 判断依据 |
| --- | --- | --- |
| T-CODEX-00 | 已完成 | 架构策略文档、AGENTS 修正、任务清单和当前状态已更新；本任务只做文档纠偏。 |
| T-CODEX-01 | 已完成 | `backend/app/domain/codex_review.py` 已新增 CodexReview 领域模型；`CheckResult` 已向后兼容新增 `codex_reviews`；domain 测试和后端全量测试通过。 |
| T-CODEX-02 | 未开始 | 尚未新增 `EvidencePackage` model 和 writer。 |
| T-CODEX-03 | 未开始 | 尚未新增 `FakeCodexRunner` / `CodexCliRunner` 接口。 |
| T-CODEX-04 | 未开始 | 尚未新增 `PromptBuilder` 和 JSON schema。 |
| T-CODEX-05 | 未开始 | 尚未新增 `OutputParser` 和失败 fallback。 |
| T-CODEX-06 | 未开始 | `PTRCompareUseCase` 尚未接入 `CodexAuditService`。 |
| T-CODEX-07 | 未开始 | `ReportCheckUseCase` 尚未接入 `CodexAuditService`。 |
| T-CODEX-08 | 未开始 | 前端尚未展示 Codex review。 |
| T-CODEX-09 | 未开始 | 尚未执行真实 Codex CLI 手动验收。 |

验证命令：

| 命令 | 结果 |
| --- | --- |
| `git diff --check` | 通过 |

## CodexReview domain model 完成记录

完成日期：2026-06-15

本次实现 T-CODEX-01，只新增领域模型和测试，不实现 EvidencePackage writer、CodexCliRunner、FakeCodexRunner、prompt builder、output parser，不调用真实 Codex，不修改 router、application usecase、frontend 或旧项目目录。

本次实现：

- 新增 `backend/app/domain/codex_review.py`。
- 定义 `CodexReviewVerdict`：`confirm`、`refute`、`uncertain`、`add_finding`。
- 定义 `CodexReviewStatus`：`pending`、`running`、`succeeded`、`failed`、`skipped`。
- 定义 `CodexReviewConfidence`：`high`、`medium`、`low`。
- 定义 `CodexReviewTargetType`，覆盖 PTR、报告规则、标签 OCR、照片 caption、检验项目、样品描述和页码等审核目标。
- 定义 `CodexEvidenceRef`、`CodexReviewTarget`、`CodexReviewError`、`CodexReviewRequest`、`CodexSuggestedFinding`、`CodexReviewResult`。
- `CodexReviewResult` 对 `succeeded` 必须带 verdict、`failed` 必须带 error、`add_finding` 必须带 suggested finding 做基础领域校验。
- `backend/app/domain/result.py` 的 `CheckResult` 已新增 `codex_reviews: list[CodexReviewResult] = []`，默认空列表，不要求现有规则产生 Codex review。

新增测试：

- `backend/tests/domain/test_codex_review_models.py` 覆盖 target/request/result 序列化，confirm/refute/uncertain/add_finding/failed 场景，非法枚举校验，以及 `CheckResult.codex_reviews` 默认空列表和 JSON 序列化。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/domain/test_codex_review_models.py -v` | 先红灯失败于 `ModuleNotFoundError: No module named 'app.domain.codex_review'`；实现后通过，`10 passed` |
| `cd backend && python -m pytest tests/domain -v` | 通过，`44 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`339 passed` |

## 推荐下一任务

推荐下一任务编号：T-CODEX-02。

原因：CodexReview 领域模型和 `CheckResult.codex_reviews` 契约已经建立。下一步应实现 `EvidencePackage` model 和 `evidence_package_writer`，为后续 runner、prompt/schema、output parser 和 usecase 接入提供受控输入边界。
