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
| T-CODEX-02 | 已完成 | `backend/app/domain/evidence_package.py` 和 `backend/app/infrastructure/audit/evidence_package_writer.py` 已新增；domain/writer 测试和后端全量测试通过。 |
| T-CODEX-03 | 已完成 | `backend/app/infrastructure/codex/` 已新增 runner protocol、fake runner 和 Codex CLI skeleton；codex infrastructure 测试、相关 domain/audit/codex 测试和后端全量测试通过。 |
| T-CODEX-04 | 已完成 | `backend/app/infrastructure/codex/prompt_builder.py`、output schema 和 schema helper 已新增；prompt/schema contract 测试、codex infrastructure 测试、相关 domain/audit/codex 测试和后端全量测试通过。 |
| T-CODEX-05 | 已完成 | `backend/app/infrastructure/codex/output_parser.py` 已新增；`CodexCliRunner` 成功输出路径已接入 parser；output parser、codex infrastructure、相关 domain/audit/codex 测试和后端全量测试通过。 |
| T-CODEX-06 | 已完成 | `PTRCompareUseCase` 已支持可选 `CodexAuditService` 接入；`PtrCodexEvidenceBuilder` 已为 PTR clause/table/parameter/scope finding 构建受控 evidence package 和 review request；默认关闭，不调用真实 Codex。 |
| T-CODEX-07 | 已完成 | `ReportCheckUseCase` 已支持可选 `CodexAuditService` 接入；`ReportCodexEvidenceBuilder` 已为 C02/C03/C04/C05/C06/C07 deterministic findings 构建受控 evidence package 和 review request；默认关闭，不调用真实 Codex。 |
| T-CODEX-08 | 已完成 | 前端类型已支持 `codex_reviews`；PTR 和报告自检结果页已展示 Codex review 总览、finding 关联意见和未关联审核意见；前端只展示后端结果，不重新计算业务规则。 |
| T-CODEX-09 | 已完成 | T-CODEX-09A 已建立 gated/manual harness；T-CODEX-09B 已由用户显式运行 gated manual harness 并记录结果。第一次脚本失败为 Python 解释器缺少 pytest，使用 `PYTHON_BIN=python` 后 smoke 脚本通过。 |
| T-CODEX-10 | 已完成 | 本地 API usecase 构造路径已通过 settings/factory 装配 Codex audit；默认关闭；fake 模式可本地联调；codex-cli 模式必须显式允许真实执行才会调用 `codex exec`。 |
| T-CODEX-11 | 已完成 | T-CODEX-11A 已建立本地业务 E2E 验收脚本和文档；T-CODEX-11B 已由用户显式运行真实 codex-cli report-check 本地业务验收，返回 1 条 succeeded/confirm/high 的 C07 review。 |
| T-CODEX-11A | 已完成 | 新增本地业务 E2E 验收文档和脚本；脚本支持 disabled/fake/codex-cli 模式、上传业务样本、轮询结果并统计 `codex_reviews`；本阶段不运行真实 Codex CLI。 |
| T-CODEX-11B | 已完成 | 使用 target 限流只审核 1 个 C07 `inspection_item` target；真实 Codex CLI 返回 succeeded review，verdict 为 confirm，confidence 为 high，failed reviews 为 0，deterministic findings 保留。 |
| T-CODEX-12 | 已完成 | 已实现 Codex audit target 限流、规则筛选和当前 batch 元数据；默认最多 5 个 audit targets，脚本可用单 target 真实模式重新验收。 |

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

## EvidencePackage model 和 writer 完成记录

完成日期：2026-06-16

本次实现 T-CODEX-02，只新增 evidence package 领域模型、本地写入器和测试，不实现 CodexCliRunner、FakeCodexRunner、prompt builder、output parser，不接入 PTRCompareUseCase 或 ReportCheckUseCase，不调用真实 Codex，不修改 router、frontend 或旧项目目录。

本次实现：

- 新增 `backend/app/domain/evidence_package.py`，定义 `EvidencePackageKind`、`EvidenceSourceType`、`EvidenceItem`、`EvidenceTarget`、`EvidencePackage` 和 `EvidencePackageManifest`。
- `EvidencePackage` 要求至少包含一个 target 和一个 evidence item，校验 item `ref_id`、target `target_id` 唯一，并拒绝 target 引用不存在的 evidence ref。
- `EvidenceItem.file_path` 仅允许 evidence workspace 内的相对路径，拒绝绝对路径和 `..` 路径穿越。
- 新增轻量 helper：`evidence_item_from_finding`、`evidence_item_from_canonical_table`、`evidence_item_from_text`、`evidence_item_from_structured`；这些 helper 只做序列化包装，不做业务判断。
- 新增 `backend/app/infrastructure/audit/evidence_package_writer.py`，按 `audit_root/{task_id}/{package_id}/input/` 写入 `evidence_package.json` 和 `manifest.json`。
- writer 使用安全 `task_id` / `package_id` 校验，并保证所有写入和读取路径都位于 audit root 内。
- 长文本 evidence item 会写入 `items/{ref_id}.txt`，并在 package JSON 中留下相对 `file_path`；manifest 的 `item_file_paths` 也保存相对路径。
- `.gitignore` 已在早期任务中忽略 `runtime/` 和 `**/runtime/`，本次无需新增忽略规则。

新增测试：

- `backend/tests/domain/test_evidence_package_models.py` 覆盖 EvidenceItem / EvidencePackage 序列化、Finding 结构化证据、CanonicalTable 结构化证据、非法枚举、空 package、缺失 evidence ref 和 `file_path` 路径安全。
- `backend/tests/infrastructure/audit/test_evidence_package_writer.py` 使用 `tmp_path` 覆盖 audit workspace 创建、package/manifest 写入、manifest/package JSON 读回、相对 item 文件路径、自动创建目录、路径穿越拒绝、长文本单独文件和不调用 subprocess/Codex CLI。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/domain/test_evidence_package_models.py tests/infrastructure/audit/test_evidence_package_writer.py -v` | 先红灯失败于 `ModuleNotFoundError: No module named 'app.domain.evidence_package'`；实现后通过，`17 passed` |
| `cd backend && python -m pytest tests/domain tests/infrastructure/audit -v` | 通过，`61 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`356 passed` |
| `git diff --check` | 通过，详见本次 T-CODEX-02 验证记录。 |

## FakeCodexRunner / CodexCliRunner 接口完成记录

完成日期：2026-06-17

本次实现 T-CODEX-03，只新增 runner contract、FakeCodexRunner、CodexCliRunner skeleton 和测试，不实现 PromptBuilder、完整 OutputParser，不接入 PTRCompareUseCase 或 ReportCheckUseCase，不调用真实 Codex，不修改 router、frontend 或旧项目目录。

本次实现：

- 新增 `backend/app/infrastructure/codex/runner.py`，定义 `CodexRunner` 协议和轻量异常 `CodexRunnerError`、`CodexRunnerTimeout`、`CodexRunnerConfigurationError`。
- 新增 `backend/app/infrastructure/codex/fake_codex_runner.py`，支持默认 confirm、注入固定 results、按 `target_id` 生成 refute/uncertain/add_finding、模拟 failed result、模拟 timeout 或 runner exception，并校验注入结果与 request targets 对应。
- 新增 `backend/app/infrastructure/codex/codex_cli_runner.py`，定义 `CodexCliRunnerConfig` 和 `CodexCliRunner`。
- `CodexCliRunnerConfig` 默认 `enabled=False`、`allow_real_execution=False`、`sandbox="read-only"`、`ephemeral=True`，拒绝 `danger-full-access`、`workspace-write` 或通过 `extra_args` 覆盖 sandbox。
- `CodexCliRunner` 只接受受控 workspace；拒绝不存在的 workspace、新项目根目录、旧项目目录、后端源码/测试、前端、docs 和 `.git` 等源码上下文。
- CLI skeleton 组装 `codex exec --cd {workspace} --sandbox read-only --ephemeral ... -o {output}` 命令；测试中全部 monkeypatch `subprocess.run`，不真实调用 Codex。
- 失败路径会返回 `CodexReviewStatus.failed`，覆盖 workspace missing/forbidden、command not found、timeout、non-zero exit、malformed output；禁用或未允许真实执行时返回 `CodexReviewStatus.skipped`。
- 本阶段只做最小 JSON loading skeleton，接受 list 或 `{results: [...]}` 并用 `CodexReviewResult` 校验；完整 output schema parser 和更细 fallback 留给 T-CODEX-05。

新增测试：

- `backend/tests/infrastructure/codex/test_fake_codex_runner.py` 覆盖默认 confirm、注入 refute/uncertain/add_finding、按 target 自动生成 verdict、add_finding suggested finding、failed result 和 target mismatch。
- `backend/tests/infrastructure/codex/test_codex_cli_runner.py` 覆盖 disabled/dry-run 不调用 subprocess、命令构造、workspace missing、项目根目录拒绝、旧项目目录拒绝、timeout、non-zero exit、command not found、malformed output 和 sandbox 安全校验。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/infrastructure/codex -v` | 先红灯失败于 `ModuleNotFoundError: No module named 'app.infrastructure.codex'`；实现后通过，`19 passed` |
| `cd backend && python -m pytest tests/domain tests/infrastructure/audit tests/infrastructure/codex -v` | 通过，`80 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`375 passed` |
| `git diff --check` | 通过，详见本次 T-CODEX-03 验证记录。 |

## PromptBuilder 和 JSON schema 完成记录

完成日期：2026-06-17

本次实现 T-CODEX-04，只新增 PromptBuilder、JSON output schema、schema helper 和 contract tests，不实现 OutputParser，不接入 PTRCompareUseCase 或 ReportCheckUseCase，不调用真实 Codex，不修改 router、frontend 或旧项目目录，不继续扩展 PTR numeric semantic / diff_builder。

本次实现：

- 新增 `backend/app/infrastructure/codex/prompt_builder.py`，定义 `PromptBuilder.build_review_prompt(request, evidence_package, max_item_text_chars=4000, max_total_chars=24000)`。
- Prompt 明确 Codex CLI 是产品运行时受控审核员，只能基于提供的 evidence refs 审核，不能读取项目源码、旧项目目录、新项目目录或未列出文件，不能修改文件，只能输出符合 JSON schema 的 JSON。
- Prompt 渲染 package summary、targets 和 evidence items；只包含 `CodexReviewRequest.targets[*].evidence_refs` 引用到的 evidence item，不默认泄露未引用证据。
- PromptBuilder 校验 request 与 evidence package 的 `task_id` / `task_type` 一致，拒绝 target 引用不存在的 evidence ref。
- PromptBuilder 对 evidence text、structured、metadata 中的本地绝对路径、`/Users/`、`file://`、`../`、源码目录片段做脱敏；对 `EvidenceItem.file_path` 只允许相对 evidence workspace 路径，发现绝对或路径穿越时抛出 `CodexRunnerConfigurationError`。
- PromptBuilder 支持 item 级文本截断和 total prompt 级截断，并保留 `[truncated]` 标记。
- 新增 `backend/app/infrastructure/codex/schemas/codex_review_output.schema.json`，定义 Codex 正常输出的最小 JSON schema：顶层只允许 `schema_version` 和 `reviews`，review status 仅允许 `succeeded`，verdict 允许 `confirm`、`refute`、`uncertain`、`add_finding`，confidence 允许 `high`、`medium`、`low`。
- Schema 要求每个 review 包含 `target_id`、`status`、`verdict`、`confidence`、`reasoning_summary`、`evidence_refs`、`suggested_severity`、`suggested_finding`、`metadata`；`add_finding` 已通过 JSON Schema `if/then` 要求 `suggested_finding` 非空。
- 新增 `backend/app/infrastructure/codex/schemas/__init__.py`，提供 `get_codex_review_output_schema_path()` 和 `load_codex_review_output_schema()`。
- `backend/pyproject.toml` 的 dev 依赖新增 `jsonschema>=4.0.0`，用于 schema contract tests。

新增测试：

- `backend/tests/infrastructure/codex/test_prompt_builder.py` 覆盖 package/target/evidence 渲染、安全边界、JSON-only 输出要求、只包含 target 引用 evidence、旧/新项目路径脱敏、绝对 `file_path` 拒绝、长文本/总 prompt 截断、unknown evidence ref 失败、`add_finding` 指令、PTR table/PTR clause/report_rule target 渲染，以及不调用 subprocess/真实 Codex。
- `backend/tests/infrastructure/codex/test_codex_review_output_schema.py` 覆盖 schema 文件存在和合法 JSON、顶层 required、verdict/confidence/status enum、顶层 additionalProperties=false、合法示例通过、缺少 reviews 失败、非法 verdict 失败、`add_finding` 缺 suggested_finding 失败、schema 不包含本地绝对路径。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/infrastructure/codex/test_prompt_builder.py tests/infrastructure/codex/test_codex_review_output_schema.py -v` | 先红灯失败于 `ModuleNotFoundError: No module named 'app.infrastructure.codex.schemas'`；实现后通过，`22 passed` |
| `cd backend && python -m pytest tests/infrastructure/codex -v` | 通过，`41 passed` |
| `cd backend && python -m pytest tests/domain tests/infrastructure/audit tests/infrastructure/codex -v` | 通过，`102 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`397 passed` |

## OutputParser 和失败 fallback 完成记录

完成日期：2026-06-17

本次实现 T-CODEX-05，只新增 OutputParser、输出级 fallback、CodexCliRunner 最小 parser 接入和测试，不接入 PTRCompareUseCase 或 ReportCheckUseCase，不调用真实 Codex，不修改 router、frontend 或旧项目目录，不继续扩展 PTR numeric semantic / diff_builder。

本次实现：

- 新增 `backend/app/infrastructure/codex/output_parser.py`，定义 `CodexReviewOutputParser`。
- `parse_output(...)` 支持从 Codex CLI 最终 JSON 字符串解析输出，流程为 JSON parse、`codex_review_output.schema.json` schema validation、项目自身 contract validation、成功结果转换。
- `parse_output_file(...)` 支持读取 Codex 输出文件；文件不存在或读取失败会降级为 failed review。
- 新增 `build_failed_results_for_request(...)`，统一为 request 中每个 target 构造 `CodexReviewStatus.failed` 的 `CodexReviewResult`，保留 `CodexReviewError.code/message/detail/retryable` 和 `raw_output_path`。
- 成功转换时，`target` 始终从 `CodexReviewRequest.targets` 中取完整对象，不信任 Codex 输出构造 target，避免伪造 target。
- 成功结果稳定生成 `review_id=codex-review-{request_id}-{target_id}`，写入 request/task/target/status/verdict/confidence/reasoning_summary/suggested_severity/suggested_finding/evidence_refs/raw_output_path/metadata。
- Parser contract validation 覆盖：reviews 必须覆盖所有 request targets、不得出现 unknown target、不得重复 target、review evidence refs 必须存在于 `EvidencePackage.items` 且属于该 target 允许 refs、`suggested_finding.evidence_refs` 必须存在于 evidence package。
- `add_finding` 缺 `suggested_finding` 已在 JSON Schema 层拒绝；parser 会把该 schema 失败映射为更具体的 `CODEX_OUTPUT_ADD_FINDING_MISSING_SUGGESTION`。
- `CodexCliRunner` 成功执行并写出 output file 后，改为调用 `CodexReviewOutputParser.parse_output_file(...)`；timeout、非零退出、command not found、workspace forbidden 等 runner 级错误仍由 runner 自己转 failed/skipped result。
- Runner 传给 result 的 `raw_output_path` 使用 `codex_review_output.json` 相对引用，不泄露本地临时 workspace 绝对路径。

失败 fallback code：

- `CODEX_OUTPUT_EMPTY`
- `CODEX_OUTPUT_INVALID_JSON`
- `CODEX_OUTPUT_SCHEMA_INVALID`
- `CODEX_OUTPUT_UNKNOWN_TARGET`
- `CODEX_OUTPUT_MISSING_TARGET`
- `CODEX_OUTPUT_DUPLICATE_TARGET`
- `CODEX_OUTPUT_UNKNOWN_EVIDENCE_REF`
- `CODEX_OUTPUT_DISALLOWED_EVIDENCE_REF`
- `CODEX_OUTPUT_ADD_FINDING_MISSING_SUGGESTION`
- `CODEX_OUTPUT_FILE_NOT_FOUND`
- `CODEX_OUTPUT_FILE_READ_ERROR`

新增/更新测试：

- 新增 `backend/tests/infrastructure/codex/test_output_parser.py`，覆盖 confirm/refute/uncertain/add_finding、多 target 全覆盖、raw_output_path、空输出、非 JSON、缺 reviews、schema invalid、unknown target、missing target、duplicate target、unknown evidence ref、disallowed evidence ref、add_finding 缺 suggested_finding、suggested_finding unknown evidence ref、output file missing、output file read error 和 failed helper。
- 更新 `backend/tests/infrastructure/codex/test_codex_cli_runner.py`，让 subprocess 成功输出使用 T-CODEX-04 schema 的 `{schema_version, reviews}` 形态，并覆盖 malformed output、schema invalid output 均由 parser 处理为 failed result。
- `FakeCodexRunner` 未修改，继续作为 usecase/unit test 的 deterministic fake runner。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/infrastructure/codex/test_output_parser.py tests/infrastructure/codex/test_codex_cli_runner.py -v` | 先红灯失败于 `ModuleNotFoundError: No module named 'app.infrastructure.codex.output_parser'`；实现后通过，`32 passed` |
| `cd backend && python -m pytest tests/infrastructure/codex -v` | 通过，`62 passed` |
| `cd backend && python -m pytest tests/domain tests/infrastructure/audit tests/infrastructure/codex -v` | 通过，`123 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`418 passed` |

## CodexAuditService 核心服务第一阶段完成记录

完成日期：2026-06-17

本次实现 T-CODEX-06 的第一阶段，只新增 `CodexAuditService` 核心编排服务和应用层测试，不接入 `PTRCompareUseCase` 或 `ReportCheckUseCase`，不调用真实 Codex，不修改 router、frontend 或旧项目目录，不继续扩展 PTR numeric semantic / diff_builder。

本次实现：

- 新增 `backend/app/application/codex_audit_service.py`，定义 `CodexAuditService.review(request, evidence_package) -> list[CodexReviewResult]`。
- 服务先校验 `CodexReviewRequest.task_id/task_type` 与 `EvidencePackage.task_id/task_type` 一致；不一致时返回 failed review，不调用 writer、prompt builder 或 runner。
- 通过 `EvidencePackageWriter.write_package(...)` 将 evidence package 写入受控 workspace。
- 通过 `PromptBuilder.build_review_prompt(...)` 构建受控 auditor prompt，并写入 workspace 内的 `prompt.md`。
- 将 `codex_review_output.schema.json` 复制到 workspace 内，再把 workspace 内 schema 路径传给 runner，避免把项目源码路径暴露给运行时 Codex。
- 调用注入的 `CodexRunner.run_review(...)`；测试使用 `FakeCodexRunner` 和轻量 test runner，不调用真实 Codex CLI 或 subprocess。
- 捕获 writer、prompt/schema 准备和 runner 异常，统一返回 `CodexReviewStatus.failed`，不让异常冒泡到主核对流程。
- 校验 runner 结果必须覆盖 request targets 且 target 不重复；空结果或 target 不完整会整体降级为 failed review。
- 不创建业务 `Finding`，不判断 C01-C11 或 PTR 对错，不覆盖原始 deterministic finding。

workspace 写入结构：

```text
runtime/codex_audit/{task_id}/{package_id}/input/
  evidence_package.json
  manifest.json
  prompt.md
  codex_review_output.schema.json
```

失败 fallback code：

- `CODEX_AUDIT_REQUEST_PACKAGE_MISMATCH`
- `CODEX_AUDIT_PACKAGE_WRITE_FAILED`
- `CODEX_AUDIT_PROMPT_BUILD_FAILED`
- `CODEX_AUDIT_SCHEMA_PREPARE_FAILED`
- `CODEX_AUDIT_RUNNER_FAILED`
- `CODEX_AUDIT_RUNNER_EMPTY_RESULT`
- `CODEX_AUDIT_RESULT_TARGET_MISMATCH`

新增测试：

- 新增 `backend/tests/application/test_codex_audit_service.py`，覆盖正常 confirm 流程、多 target、refute/uncertain/add_finding、task mismatch 不调用 runner、PromptBuilder 失败、EvidencePackageWriter 失败、runner 异常、runner 空结果、runner target 不完整，以及 prompt 不包含旧项目或新项目绝对路径。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/application/test_codex_audit_service.py -v` | 先红灯失败于 `ModuleNotFoundError: No module named 'app.application.codex_audit_service'`；实现后通过，`10 passed` |
| `cd backend && python -m pytest tests/application/test_codex_audit_service.py tests/domain tests/infrastructure/audit tests/infrastructure/codex -v` | 通过，`133 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`428 passed` |

## PTRCompareUseCase Codex audit 接入完成记录

完成日期：2026-06-17

本次实现 T-CODEX-06 第二阶段，在 `PTRCompareUseCase` 中通过 `CodexAuditService` 接入 PTR clause/table/parameter/scope review。实现仍然默认关闭 Codex audit，测试使用 fake audit service 或 `CodexAuditService + FakeCodexRunner`，不调用真实 Codex CLI，不修改 router、frontend 或旧项目目录，不重写 PTRExtractor、parameter_compare 或 table_reference_compare，不继续扩展 PTR numeric semantic / diff_builder。

本次实现：

- 新增 `backend/app/application/ptr_codex_evidence_builder.py`，定义 `PtrCodexEvidenceBuilder` 和 `PtrCodexAuditBundle`。
- `PtrCodexEvidenceBuilder` 从 deterministic `CheckResult.findings` 构建 `EvidencePackage` 和 `CodexReviewRequest`，每个可审核 PTR finding 对应一个 review target。
- target 映射覆盖：
  - `PTR_CLAUSE_TEXT_MISMATCH` / `PTR_CLAUSE_MISSING` -> `ptr_clause`。
  - `PTR_TABLE_MISSING` / `PTR_TABLE_CANDIDATE_AMBIGUOUS` -> `ptr_table`。
  - `PTR_TABLE_VALUE_MISMATCH` / `PTR_TABLE_UNIT_MISMATCH` / `PTR_TABLE_PARAM_MISSING` / `PTR_TABLE_CONDITION_MISMATCH` / `PTR_TABLE_TOLERANCE_MISMATCH` / `PTR_TABLE_SEGMENT_AMBIGUOUS` -> `ptr_parameter`。
  - `PTR_SCOPE` finding -> `ptr_clause` target；当前 scope filter 仍不主动生成 finding，因此 pass-only scope 不会强行调用 Codex audit。
- evidence package 最小包含 finding evidence、rule context、相关 PTR clause、PTR canonical table summary、report canonical table summary；表格证据只保留 compact parameter record summary，避免塞入整表无限结构或整份 PDF 文本。
- evidence package 和 request 会脱敏旧项目、新项目和 `/Users/` 绝对路径。
- `PTRCompareUseCase` 新增可选依赖：
  - `codex_audit_service: CodexAuditServiceProtocol | None = None`
  - `codex_audit_enabled: bool = False`
  - `ptr_codex_evidence_builder: PtrCodexEvidenceBuilder | None = None`
- 默认关闭 Codex audit；API 默认构造 `PTRCompareUseCase(task_service=...)`，不会创建真实 `CodexCliRunner`，不会读取环境变量启动真实 Codex。
- Codex audit 启用且存在可审核 finding 时，usecase 调用 builder 和 `CodexAuditService.review(...)`，并按 `review.target.check_id` 把 `CodexReviewResult` 附加到对应 `CheckResult.codex_reviews`。
- Codex review 不删除、不覆盖 deterministic `Finding`；`add_finding` 只保留在 `CodexReviewResult.suggested_finding`，不会自动追加为 deterministic finding。
- `CodexAuditService` 返回 failed review 或抛异常时，PTR usecase 不崩溃；service 抛异常会转换为 `CODEX_PTR_AUDIT_SERVICE_FAILED` 的 failed review。
- 没有 findings 或没有可审核 findings 时，不调用 audit service，`codex_reviews` 保持默认空列表。

新增/更新测试：

- 新增 `backend/tests/application/test_ptr_codex_evidence_builder.py`，覆盖 clause target、parameter target、scope finding target、finding evidence、PTR clause/table/report table evidence、target refs 完整性、旧/新项目路径脱敏、无 finding 返回 `None`、重复 evidence ref 去重、大表格 compact summary。
- 更新 `backend/tests/application/test_ptr_compare_usecase.py`，覆盖默认关闭时 `codex_reviews=[]`、fake service confirm/refute/add_finding/failed、`CodexAuditService + FakeCodexRunner` 正常链路、service exception fallback、parameter finding 生成 `ptr_parameter` target、clause finding 生成 `ptr_clause` target、无 finding 不调用 audit service。
- `backend/tests/api/test_api_ptr_compare_e2e.py` 未修改；默认 API 不启用真实 Codex，现有 API e2e 和 compact golden 继续通过。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/application/test_ptr_codex_evidence_builder.py tests/application/test_ptr_compare_usecase.py tests/application/test_codex_audit_service.py -v` | 先红灯失败于 `ModuleNotFoundError: No module named 'app.application.ptr_codex_evidence_builder'`；实现后通过，`46 passed` |
| `cd backend && python -m pytest tests/api/test_api_ptr_compare_e2e.py tests/infrastructure/codex tests/infrastructure/audit tests/domain -v` | 通过，`124 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`447 passed` |
| `git diff --check` | 通过 |

任务状态：

- `docs/tasks.md` 已将 T-CODEX-06 标记为 `[x]`。
- T-CODEX-07 当时保持未开始；现已完成第一阶段 `ReportCodexEvidenceBuilder`，但 `ReportCheckUseCase` 尚未接入，任务整体仍未完成。

## ReportCodexEvidenceBuilder 第一阶段完成记录

完成日期：2026-06-17

本次实现 T-CODEX-07 第一阶段，只新增 `ReportCodexEvidenceBuilder` 和应用层测试，不接入 `ReportCheckUseCase`，不调用 `CodexAuditService`，不调用真实 Codex CLI，不修改 router、frontend 或旧项目目录，不重写 C01-C11 规则，不改变 deterministic findings，也不把 Codex review 自动写入 `CheckResult`。

本次实现：

- 新增 `backend/app/application/report_codex_evidence_builder.py`，定义 `ReportCodexEvidenceBuilder` 和 `ReportCodexAuditBundle`。
- `ReportCodexEvidenceBuilder.build(...)` 从单个报告自检 `CheckResult.findings` 中筛选可审核 finding，并构建 `EvidencePackage` 与 `CodexReviewRequest`。
- 支持的 target 映射：
  - `C02` -> `label_ocr`
  - `C03` -> `label_ocr`
  - `C04` -> `sample_description`
  - `C05` -> `photo_caption`
  - `C06` -> `label_ocr`
  - `C07` -> `inspection_item`
- 默认跳过 `C01`、`C08`、`C09`、`C10`、`C11`，没有可审核 findings 时返回 `None`。
- 每个 target 至少包含 finding evidence 与 rule context evidence；在 `ReportDocument` / `ParsedPdf` 可用时补充第三页字段、标签 OCR、样品描述部件、照片 caption、中文标签 caption、检验项目行和相关页文本片段。
- evidence package 使用 `report_rule_review`，只包含与 finding 相关的最小证据，不读取旧项目目录，不读取项目源码，不塞入整份 PDF 文本。
- evidence package 和 request 会脱敏旧项目、新项目和 `/Users/` 绝对路径；长文本和大结构中的字符串按 `max_text_chars` 截断并标记 `[truncated]`。
- `request.targets` 与 `package.targets` 一一对齐，所有 target evidence refs 均指向已存在的 `EvidenceItem.ref_id`。

新增测试：

- 新增 `backend/tests/application/test_report_codex_evidence_builder.py`，覆盖 C02-C07 target type 映射、C01/C08/C09/C10/C11 跳过、无可审核 finding 返回 `None`、target refs 完整性、finding/rule context evidence、C02/C03 字段和 OCR 上下文、C04 样品描述和标签上下文、C05/C06 部件和 caption 上下文、C07 检验结果/实际单项结论/期望单项结论、路径脱敏、多 finding ref_id 去重、长文本截断、request/package task 对齐。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py -v` | 先红灯失败于 `ModuleNotFoundError: No module named 'app.application.report_codex_evidence_builder'`；实现后通过，`20 passed` |
| `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py tests/domain tests/infrastructure/audit tests/infrastructure/codex -v` | 通过，`143 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`467 passed` |
| `git diff --check` | 通过 |

任务状态：

- 第一阶段时 `docs/tasks.md` 未将 T-CODEX-07 标记为 `[x]`；第二阶段接入完成后已标记。
- T-CODEX-08 当时保持未开始；现已在前端展示任务中完成。

## ReportCheckUseCase Codex audit 接入完成记录

完成日期：2026-06-17

本次实现 T-CODEX-07 第二阶段，在 `ReportCheckUseCase` 中通过可选依赖接入 `CodexAuditService`。实现默认关闭 Codex audit，测试使用 fake audit service，不调用真实 Codex CLI，不修改 router、frontend 或旧项目目录，不重写 C01-C11 规则，不改变 deterministic findings，不把 `add_finding` 自动追加为 deterministic finding。

本次实现：

- `ReportCheckUseCase` 新增可选依赖：
  - `codex_audit_service: CodexAuditServiceProtocol | None = None`
  - `codex_audit_enabled: bool = False`
  - `report_codex_evidence_builder: ReportCodexEvidenceBuilder | None = None`
- 默认 `codex_audit_enabled=False`，API 默认构造 `ReportCheckUseCase(task_service=...)`，不会创建真实 `CodexCliRunner`，不会读取环境变量启动真实 Codex。
- deterministic C01-C11 流程保持不变：PDF 解析、ReportDocument 构建、规则 runner 运行、`CheckResult` 聚合路径不变。
- 规则结果生成后，启用 Codex audit 且存在可审核 finding 时，usecase 调用 `ReportCodexEvidenceBuilder.build(...)` 构建 request/package，再调用 `CodexAuditService.review(...)`。
- `CodexReviewResult` 直接附加到对应 `CheckResult.codex_reviews`；`CheckResult.summary` 和任务级 summary 仍基于 deterministic findings。
- 支持的运行时审核范围仍仅为 `C02/C03/C04/C05/C06/C07`；`C01/C08/C09/C10/C11` 默认不进入 Codex audit。
- Codex service 返回 `confirm/refute/uncertain/add_finding/failed` 都保留在 `codex_reviews`；原始 finding 不删除、不覆盖。
- Codex service 抛异常时，usecase 不崩溃，会基于已构建 request 为每个 target 生成 `CODEX_REPORT_AUDIT_SERVICE_FAILED` 的 failed review。
- 没有可审核 findings 或 builder 返回 `None` 时，不调用 audit service，`codex_reviews` 保持空列表。
- 报告 API 回归固定默认序列化 `codex_reviews: []`，默认路径不启用真实 Codex。

新增/更新测试：

- 更新 `backend/tests/application/test_report_check_usecase.py`，覆盖默认关闭不调用 audit service、confirm/refute/uncertain/add_finding/failed 附加、service exception fallback、无可审核 findings 不调用 audit service、C02 生成 `label_ocr` target、C07 生成 `inspection_item` target。
- 更新 `backend/tests/api/test_report_check_api.py`，确认默认报告自检 API 结果中 `codex_reviews` 为空列表。
- `backend/tests/application/test_report_codex_evidence_builder.py` 和 `backend/tests/application/test_codex_audit_service.py` 保持回归通过。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/application/test_report_check_usecase.py -v` | 先红灯失败于 `TypeError: ReportCheckUseCase.__init__() got an unexpected keyword argument 'codex_audit_service'`；实现后通过，`12 passed` |
| `cd backend && python -m pytest tests/application/test_report_check_usecase.py tests/application/test_report_codex_evidence_builder.py tests/application/test_codex_audit_service.py -v` | 通过，`42 passed` |
| `cd backend && python -m pytest tests/api -v` | 通过，`13 passed` |
| `cd backend && python -m pytest tests/ -v` | 通过，`477 passed` |
| `git diff --check` | 通过 |

任务状态：

- `docs/tasks.md` 已将 T-CODEX-07 标记为 `[x]`。
- T-CODEX-08 已在后续前端展示任务中完成。

## 前端 Codex review 展示完成记录

完成日期：2026-06-17

本次实现 T-CODEX-08，只做前端展示和类型对齐，不修改后端业务逻辑，不调用真实 Codex CLI，不修改旧项目目录，不让前端重新计算 C01-C11 或 PTR 规则，也不根据 Codex review 删除、覆盖 deterministic finding。

本次实现：

- 新增前端 Codex review contract，覆盖 `CodexReviewVerdict`、`CodexReviewStatus`、`CodexReviewConfidence`、`CodexReviewTargetType`、`CodexEvidenceRef`、`CodexReviewTarget`、`CodexReviewError`、`CodexSuggestedFinding` 和 `CodexReviewResult`。
- `CheckResult` 前端类型新增可选 `codex_reviews?: CodexReviewResult[]`，旧 API 响应缺失该字段时通过 `normalizeCodexReviews(...)` 按空数组处理。
- 新增 `summarizeCodexReviews(...)` 和 `groupCodexReviewsByFinding(...)`，仅用于展示层统计和关联，不改变后端结果。
- 关联规则为：优先 `review.target.finding_id == finding.id`；其次读取 target metadata 中的 `finding_id` / `deterministic_finding_id`；再按 `finding_code` + `check_id` 弱关联；仅当同一 `check_id` 下只有一个 finding 时使用 `check_id` 弱关联；无法关联的 review 显示在“其他 Codex 审核意见”区域。
- 新增 Codex review 展示组件，展示 verdict/status/confidence/reasoning_summary/suggested_severity/suggested_finding/evidence_refs/error。
- PTR 结果页展示 Codex review 总览，并在展开的条款 finding 下显示关联 review；未关联 review 单独显示。
- 报告自检结果页展示 Codex review 总览，并在展开的规则 finding 下显示关联 review；`add_finding` 仅作为 Codex 建议显示，不进入 deterministic findings。
- JSON export/download 仍调用后端导出，不在前端丢弃 `codex_reviews`。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd frontend && npm run build` | 先红灯失败于缺少 `entities/codexReview/types`、`CheckResult.codex_reviews` 和 `PTRClauseViewModel.codexReviews`；实现后通过。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`477 passed` |
| `git diff --check` | 通过 |

任务状态：

- `docs/tasks.md` 已将 T-CODEX-08 标记为 `[x]`。
- T-CODEX-09 当时保持未开始；现已完成 T-CODEX-09A harness，真实 CLI 验收仍未执行。

## Codex CLI 手动验收 harness 完成记录

完成日期：2026-06-18

本次实现 T-CODEX-09A，只建立真实 Codex CLI 手动验收 harness，默认不调用真实 Codex CLI，不修改 router、frontend、旧项目目录或 C01-C11 / PTR 业务规则，不把真实 Codex 集成加入普通 pytest。

本次实现：

- 新增受控 smoke fixture，构造一个最小 PTR 表格参数值 mismatch evidence package 和 `CodexReviewRequest`。
- 新增 `backend/tests/integration/test_codex_cli_manual.py`，通过 `ENABLE_CODEX_CLI_INTEGRATION=1` gate 控制；默认普通测试只 skip，不调用 `codex exec`。
- 新增 `scripts/run-codex-cli-audit-smoke.sh`，默认拒绝运行；只有显式设置 `ENABLE_CODEX_CLI_INTEGRATION=1` 时才运行 gated integration pytest。
- 新增 `docs/codex-cli-manual-validation.md`，记录目的、默认不运行原因、前置条件、安全边界、运行命令、成功标准、失败排查和禁止事项。
- 新增普通 harness contract 测试，确认 smoke fixture 写入 tmp evidence workspace、prompt 不包含旧项目/新项目绝对路径，脚本默认拒绝真实 Codex。
- `CodexCliRunner` 检查结果：现有实现已满足 `enabled=True` + `allow_real_execution=True` 双开关、默认双 false、read-only sandbox、ephemeral、`-o` 输出文件、schema、timeout、unsafe workspace 拒绝和 danger/workspace-write 拒绝；本次未重构 runner。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/infrastructure/codex/test_codex_cli_manual_harness.py -v` | 先红灯失败于缺少 `tests.fixtures.codex_cli_manual_smoke`；实现后通过，`2 passed` |
| `cd backend && python -m pytest tests/integration/test_codex_cli_manual.py -v` | 未设置 `ENABLE_CODEX_CLI_INTEGRATION` 时通过收集并 skip，`1 skipped` |
| `cd backend && python -m pytest tests/infrastructure/codex tests/integration/test_codex_cli_manual.py -v` | 通过，`64 passed, 1 skipped` |
| `cd backend && python -m pytest tests/ -v` | 通过，`479 passed, 1 skipped` |
| `cd frontend && npm run build` | 通过 |
| `git diff --check` | 通过 |

任务状态：

- `docs/tasks.md` 已将 T-CODEX-09A 标记为 `[x]`。
- T-CODEX-09 整体后续已在 T-CODEX-09B 手动验收记录后标记为 `[x]`。
- T-CODEX-09B 后续已由用户显式运行并记录结果。

## 后续建议

推荐后续工作：根据业务优先级进入真实样例审计记录整理或继续既有非 Codex 未完成任务。

原因：T-CODEX-09A/09B 已完成，真实 Codex CLI manual harness 已通过用户手动验收；后续不需要继续扩展 T-CODEX-09，除非要增强日志断言或补充更多受控业务样例。

## Codex CLI smoke 脚本 Python 选择修复记录

完成日期：2026-06-18

本次只修复 T-CODEX-09B 前置手动脚本的 Python 解释器选择问题，不调用真实 Codex CLI，不设置 `ENABLE_CODEX_CLI_INTEGRATION=1`，不修改后端业务代码、frontend、runner、prompt builder、output parser 或旧项目目录。

本次修复：

- `scripts/run-codex-cli-audit-smoke.sh` 默认使用当前 shell 的 `python`，并支持通过 `PYTHON_BIN=/path/to/python` 显式指定解释器。
- 脚本会打印 Python 可执行路径、Python 版本和 pytest 可用性。
- 如果真实手动验收 gate 已开启但 pytest 不可用，脚本输出明确修复建议：安装 `cd backend && python -m pip install -e ".[dev]"`，或使用 `PYTHON_BIN=/path/to/python ENABLE_CODEX_CLI_INTEGRATION=1 bash scripts/run-codex-cli-audit-smoke.sh`。
- 保持原有 `ENABLE_CODEX_CLI_INTEGRATION=1` gate；未设置 gate 时仍拒绝运行真实 `codex exec`。
- `docs/codex-cli-manual-validation.md` 已记录 `PYTHON_BIN` 用法。

任务状态：

- 这是 T-CODEX-09B 前置脚本修复；真实验收结果已在后续记录中收口。
- T-CODEX-09B 后续已标记为 `[x]`。
- T-CODEX-09 整体后续已标记为 `[x]`。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `bash scripts/run-codex-cli-audit-smoke.sh` | 未设置 `ENABLE_CODEX_CLI_INTEGRATION`，按预期拒绝运行；打印 Python 路径、版本和 pytest 可用性。 |
| `PYTHON_BIN=python bash scripts/run-codex-cli-audit-smoke.sh` | 未设置 `ENABLE_CODEX_CLI_INTEGRATION`，按预期拒绝运行；使用当前 shell 的 `python`。 |
| `cd backend && python -m pytest tests/integration/test_codex_cli_manual.py -v` | 默认 skip，`1 skipped`。 |
| `git diff --check` | 通过。 |

## Codex CLI 真实手动验收完成记录

完成日期：2026-06-18

本记录收口 T-CODEX-09B。用户已显式开启 gated manual harness 并提供执行结果；本次文档记录不重新运行真实 Codex CLI，不修改后端业务代码、frontend、runner、prompt builder、output parser、router 或旧项目目录。

第一次脚本运行：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3
ENABLE_CODEX_CLI_INTEGRATION=1 bash scripts/run-codex-cli-audit-smoke.sh
```

结果失败：

```text
/opt/homebrew/opt/python@3.14/bin/python3.14: No module named pytest
```

原因确认：脚本当时默认使用的 `python3` 指向 Homebrew Python 3.14，该环境没有安装 pytest。这不是 Codex audit 链路失败，而是 Python 解释器选择问题。随后确认当前项目 shell 的 Python 可用：

```bash
python -m pytest --version
```

输出：

```text
pytest 9.0.2
```

直接运行 gated integration test：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3/backend
ENABLE_CODEX_CLI_INTEGRATION=1 python -m pytest tests/integration/test_codex_cli_manual.py -v
```

结果：

```text
tests/integration/test_codex_cli_manual.py::test_real_codex_cli_manual_smoke_returns_auditable_result PASSED
1 passed in 0.42s
```

使用脚本并显式指定 Python：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3
PYTHON_BIN=python ENABLE_CODEX_CLI_INTEGRATION=1 bash scripts/run-codex-cli-audit-smoke.sh
```

结果：

```text
Python executable: /Users/lulingfeng/miniforge3/bin/python
Python version: Python 3.12.12
pytest: available
tests/integration/test_codex_cli_manual.py::test_real_codex_cli_manual_smoke_returns_auditable_result PASSED
1 passed in 0.63s
```

验收结论：

- T-CODEX-09B 已由用户手动执行并通过。
- T-CODEX-09 整体完成。
- `tests/integration/test_codex_cli_manual.py` 在 gate 开启时显式使用 `CodexCliRunner(enabled=True, allow_real_execution=True, sandbox="read-only")` 并调用 `run_review(...)`。
- `PYTHON_BIN` 是推荐的脚本参数，用于指定带 pytest 的 Python 环境。
- 普通未设置 `ENABLE_CODEX_CLI_INTEGRATION` 的 integration test 仍默认 skip，不会在普通测试中调用真实 Codex CLI。
- smoke 使用 pytest `tmp_path` 创建受控临时 evidence workspace。
- runner 使用 read-only sandbox。
- 输出使用 `codex_review_output.schema.json`。
- Codex 输出或运行异常没有冒泡到主流程；验收测试返回可审计结果。
- 未修改旧项目目录。
- API 默认不启用真实 Codex，也不会因本次 harness 验收改变默认运行行为。

## Codex audit 本地运行时配置与依赖装配完成记录

完成日期：2026-06-18

本次实现 T-CODEX-10，把 `CodexAuditService` 通过配置和 application factory 装配到本地 API usecase 构造路径。默认仍关闭，不调用真实 Codex CLI，不修改旧项目目录，不修改前端业务判断，不把 Codex CLI 执行逻辑写进 router，不引入 GPT API、OpenAI Responses API 或 Chat API。

本次实现：

- `backend/app/core/config.py` 新增 Codex audit settings：
  - `CODEX_AUDIT_ENABLED`
  - `CODEX_AUDIT_BACKEND`
  - `CODEX_AUDIT_ALLOW_REAL_EXECUTION`
  - `CODEX_AUDIT_TIMEOUT_SECONDS`
  - `CODEX_AUDIT_RUNTIME_DIR`
- 新增 `backend/app/application/codex_runtime_factory.py`：
  - `build_codex_audit_service(settings)`
  - `build_ptr_compare_usecase(settings, task_service=...)`
  - `build_report_check_usecase(settings, task_service=...)`
- 默认 settings 下 `build_codex_audit_service(...)` 返回 `None`，PTR/Report usecase 的 `codex_audit_enabled=False`，普通 API 不启用 Codex audit。
- `CODEX_AUDIT_BACKEND=fake` 且 `CODEX_AUDIT_ENABLED=1` 时使用 `FakeCodexRunner`，可用于本地 UI 联调，写入 `codex_reviews`，不调用真实 Codex。
- `CODEX_AUDIT_BACKEND=codex-cli` 且 `CODEX_AUDIT_ENABLED=1` 时使用 `CodexCliRunner`；只有 `CODEX_AUDIT_ALLOW_REAL_EXECUTION=1` 才允许真实 `codex exec`。未允许真实执行时返回 skipped review，不调用 subprocess。
- API route dependency 改为调用 application factory：router 仍只处理 HTTP 输入输出、上传校验和依赖注入，不承载 Codex CLI runner 逻辑。
- Codex audit workspace 仍由 `EvidencePackageWriter` 写入 `runtime/codex_audit/{task_id}/{package_id}/input/`，runner 仍使用 read-only sandbox、output schema 和 timeout。
- Codex review 只附加在 `codex_reviews`，不会删除、覆盖或改写 deterministic findings。

新增测试：

- `backend/tests/application/test_codex_runtime_factory.py` 覆盖 settings 默认值/env 读取、默认关闭、fake backend 产出 confirm review、PTR/Report usecase 通过 factory 接收 audit service、codex-cli 未允许真实执行时不调用 subprocess 并返回 skipped、codex-cli 允许真实执行时可 monkeypatch subprocess 写入 schema 合法输出。
- `backend/tests/api/test_codex_audit_dependencies.py` 覆盖 API 默认依赖构造出的 PTR/Report usecase 不启用 Codex audit，且不会调用 subprocess。

本地 fake 模式：

```bash
cd backend
CODEX_AUDIT_ENABLED=1 \
CODEX_AUDIT_BACKEND=fake \
python -m uvicorn app.main:app --reload
```

本地真实 Codex CLI 模式：

```bash
cd backend
CODEX_AUDIT_ENABLED=1 \
CODEX_AUDIT_BACKEND=codex-cli \
CODEX_AUDIT_ALLOW_REAL_EXECUTION=1 \
CODEX_AUDIT_RUNTIME_DIR=runtime/codex_audit \
CODEX_AUDIT_TIMEOUT_SECONDS=120 \
python -m uvicorn app.main:app --reload
```

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/application/test_codex_runtime_factory.py tests/api/test_codex_audit_dependencies.py -v` | 先红灯失败于 `ModuleNotFoundError: No module named 'app.application.codex_runtime_factory'`；实现后通过，`6 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`485 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `git diff --check` | 通过。 |

## Codex audit 本地业务端到端验收脚本和文档完成记录

完成日期：2026-06-18

本次实现 T-CODEX-11A，只新增本地业务端到端验收脚本、文档和脚本/文档 contract test。本阶段不调用真实 Codex CLI，不修改旧项目目录，不修改规则逻辑，不修改 router 业务逻辑，不把 Codex 审核逻辑写进 router，不修改 C01-C11 或 PTR 规则算法。

本次实现：

- 新增 `docs/codex-audit-local-e2e.md`，说明本地 Web 工具在 disabled/fake/codex-cli 模式下如何验收 `codex_reviews`。
- 新增 `scripts/run-codex-audit-local-e2e.sh`，支持：
  - `--help`：显示用法，不启动服务，不调用 Codex。
  - `--print-config`：显示当前模式和 safety gate，不启动服务，不调用 Codex。
  - `MODE=disabled|fake|codex-cli`。
  - `TASK_TYPE=ptr-compare|report-check`。
  - `START_BACKEND=1` 可由脚本代启后端。
  - `PTR_FILE` / `REPORT_FILE` 上传本地业务样本。
  - 轮询 `/api/tasks/{task_id}`，下载 `/api/tasks/{task_id}/result`，统计 `check_results[].codex_reviews`。
  - `EXPECT_CODEX_REVIEWS=auto|empty|nonempty|any` 控制验收口径。
- codex-cli 模式脚本 gate：
  - 必须设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1`。
  - 必须设置 `CODEX_AUDIT_ALLOW_REAL_EXECUTION=1`。
  - 未满足 gate 时脚本拒绝运行，避免误调用真实 Codex CLI。
- 文档明确前端只展示后端返回的 `codex_reviews`，不重新计算 C01-C11 或 PTR 规则；前端入口为 `CodexReviewPanel`、PTR 结果页和报告自检结果页。
- 文档明确安全边界：不使用 GPT API client，不调用 OpenAI Responses/Chat API，不让 Codex 读取项目源码，仍使用 `runtime/codex_audit`、read-only sandbox、output schema 和 timeout。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/integration/test_codex_audit_local_e2e_artifacts.py -v` | 先红灯失败于脚本和文档不存在；实现后通过，`3 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`488 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `git diff --check` | 通过。 |

## Codex audit 本地 E2E 脚本结果路径修复记录

完成日期：2026-06-18

本次修复 T-CODEX-11B 前置脚本问题，当时不标记 T-CODEX-11B 完成。本次不调用真实 Codex CLI，不修改后端业务代码、frontend、router、Codex runner/parser/prompt 或旧项目目录。

问题：

- `scripts/run-codex-audit-local-e2e.sh` 的 `poll_result` 被 command substitution 捕获时，任务状态日志和结果 JSON 路径同时写到 stdout。
- 调用方期望 stdout 只有结果 JSON 路径，实际得到多行字符串，导致 Python 把日志和路径拼成一个不存在的文件路径并抛出 `FileNotFoundError`。

本次修复：

- 脚本新增统一 `log()`，所有进度日志和任务状态输出都写入 stderr。
- `poll_result` 的 stdout 只输出最终结果 JSON 文件路径。
- `result_file` 捕获后会校验：非空、不包含换行、文件存在、以 `.json` 结尾。
- 保留 `PYTHON_BIN` 支持。
- 保留 codex-cli 安全 gate：必须同时设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1` 和 `CODEX_AUDIT_ALLOW_REAL_EXECUTION=1` 才允许真实 Codex CLI。
- fake 模式仍不调用真实 Codex。
- `docs/codex-audit-local-e2e.md` 已补充 stdout/stderr 输出边界说明。
- `backend/tests/integration/test_codex_audit_local_e2e_artifacts.py` 新增 fake `curl` 脚本级测试，覆盖上传、轮询、结果下载、日志走 stderr 和结果路径不被污染。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `bash -n scripts/run-codex-audit-local-e2e.sh` | 通过。 |
| `cd backend && python -m pytest tests/integration/test_codex_audit_local_e2e_artifacts.py -v` | 先红灯复现 `FileNotFoundError` 多行路径；修复后通过，`5 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`490 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `git diff --check` | 通过。 |

## Codex CLI structured output schema 兼容性修复记录

完成日期：2026-06-23

本次修复 T-CODEX-11B 前置阻塞点，当时不标记 T-CODEX-11B 完成。本次不调用真实 Codex CLI，不修改后端业务规则、router、frontend、旧项目目录或 Codex runner/prompt 业务内容。

真实 T-CODEX-11B report-check 业务验收已触发真实 Codex CLI，但结果全部 failed：

- `codex_reviews_count: 84`
- `codex_status_counts: {"failed": 84}`
- `deterministic_findings_count: 5194`
- failed `error_code: CODEX_EXIT_NONZERO`
- stderr 报 `invalid_json_schema`，核心错误为：`Invalid schema for response_format 'codex_output_schema': In context=('properties', 'evidence_refs'), 'uniqueItems' is not permitted.`

原因确认：

- `backend/app/infrastructure/codex/schemas/codex_review_output.schema.json` 使用了真实 Codex/OpenAI structured output 不支持的 JSON Schema 关键字。
- 已确认 `uniqueItems` 被真实 CLI 拒绝；`allOf`、`if`、`then` 等组合关键字也属于高风险 structured output 非兼容关键字。
- 复杂跨字段校验不应依赖 JSON Schema，而应放在 `CodexReviewOutputParser` 中做项目自身 contract validation。

本次修复：

- 将 `codex_review_output.schema.json` 收敛为 structured output 兼容的最小 schema，只保留基础结构、required 字段、enum、nullable 类型和 `additionalProperties: false`。
- 从 schema 中移除 `uniqueItems`、`allOf`、`if`、`then`、`else`、`not`、`dependentRequired`、`dependentSchemas`、`minLength`、`maxLength`、`pattern`、`format`、`minItems`、`maxItems`。
- 不再在 schema 层强制 `add_finding` 必须包含 `suggested_finding`；该规则由 parser 校验。
- `CodexReviewOutputParser` 新增重复 evidence ref 校验，输出 `CODEX_OUTPUT_DUPLICATE_EVIDENCE_REF`。
- `CodexReviewOutputParser` 继续校验 unknown evidence ref、disallowed evidence ref、duplicate/missing target、add_finding 缺 suggestion、suggested_finding evidence refs 不存在等 contract。
- schema 中 Codex 输出的 `metadata` 收紧为 `{}`；parser 仍会在成功结果 metadata 中追加 `schema_version` 和 `parser` 审计信息。
- `docs/codex-cli-manual-validation.md` 和 `docs/codex-audit-local-e2e.md` 已记录 structured output 兼容子集和 parser contract validation 边界。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/infrastructure/codex/test_codex_review_output_schema.py tests/infrastructure/codex/test_output_parser.py tests/infrastructure/codex/test_prompt_builder.py -v` | 通过，`44 passed`。 |
| `cd backend && python -m pytest tests/infrastructure/codex -v` | 通过，`66 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`492 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `git diff --check` | 通过。 |

任务状态：

- T-CODEX-11B 当时仍未标记完成；后续已通过真实业务验收收口。
- 后续已重新运行真实 codex-cli report-check 业务验收，并通过单 target 限流完成 T-CODEX-11B 收口。

## Codex audit target 限流和筛选完成记录

完成日期：2026-06-23

本次实现 T-CODEX-12，不调用真实 Codex CLI，不修改 C01-C11 或 PTR 规则逻辑，不修改 router 业务逻辑，不修改旧项目目录，不改变 deterministic findings；T-CODEX-11B 当时仍等待后续真实业务验收。

T-CODEX-11B 最新真实模式结果：

- structured output schema 已通过此前兼容性修复，不再出现 `invalid_json_schema`。
- report-check 真实 codex-cli 业务验收已触达真实 Codex CLI，但一次审核 84 个 targets 仍过重。
- `codex_reviews_count: 84`
- `codex_status_counts: {"failed": 84}`
- failed `error_code: CODEX_TIMEOUT`
- error detail: `Timed out after 120 seconds`
- `deterministic_findings_count: 5194`
- target 类型包括 C04/C05/C06/C07。

本次实现：

- 新增 `backend/app/application/codex_audit_targeting.py`，定义共享 `CodexAuditTargetSelection`、CSV 解析和默认优先级。
- `backend/app/core/config.py` 新增：
  - `CODEX_AUDIT_MAX_TARGETS_PER_TASK=5`
  - `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=5`
  - `CODEX_AUDIT_INCLUDED_CHECK_IDS`
  - `CODEX_AUDIT_INCLUDED_FINDING_CODES`
  - `CODEX_AUDIT_EXCLUDED_CHECK_IDS`
  - `CODEX_AUDIT_PRIORITY_CHECK_IDS=C02,C03,C07,C04,C05,C06`
- `ReportCodexEvidenceBuilder` 默认只从 C02/C03/C04/C05/C06/C07 中筛选，应用 include/exclude/finding code 过滤，按 priority 排序，同优先级保留原 finding 顺序，并截断到 max targets。
- `ReportCheckUseCase` 在多个 check results 之间累计 `emitted_targets`，确保单个报告自检任务总 Codex audit targets 不超过配置上限。
- `PtrCodexEvidenceBuilder` 支持同样的 check ID / finding code 筛选和 max targets，默认 PTR finding code 优先级为 `PTR_CLAUSE_TEXT_MISMATCH`、`PTR_TABLE_CANDIDATE_AMBIGUOUS`、`PTR_TABLE_VALUE_MISMATCH`、`PTR_TABLE_UNIT_MISMATCH`、`PTR_TABLE_PARAM_MISSING`、`PTR_TABLE_CONDITION_MISMATCH`、`PTR_TABLE_TOLERANCE_MISMATCH`。
- Evidence package 和 request metadata 记录 `total_candidate_targets`、`emitted_targets`、`truncated`、`omitted_targets_count`、`batch_index=0`、`batch_size`、`max_targets_per_task` 和 `max_targets_per_batch`。
- `backend/app/application/codex_runtime_factory.py` 将配置传入 Report/PTR evidence builders；fake 和 codex-cli 模式共享同一限流/筛选策略。
- `scripts/run-codex-audit-local-e2e.sh` 支持并展示 target 限流/筛选环境变量，仍保留 codex-cli 真实执行 gate。
- `docs/codex-audit-local-e2e.md` 已补充单 target 真实 Codex CLI 验收建议命令。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py tests/application/test_ptr_codex_evidence_builder.py tests/application/test_codex_runtime_factory.py tests/integration/test_codex_audit_local_e2e_artifacts.py -v` | 通过，`54 passed`。 |
| `cd backend && python -m pytest tests/application/test_report_check_usecase.py::test_report_check_codex_audit_limits_reviews_across_check_results -v` | 通过，`1 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`508 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `bash -n scripts/run-codex-audit-local-e2e.sh` | 通过。 |
| `git diff --check` | 通过。 |

任务状态：

- T-CODEX-12 已完成。
- T-CODEX-11B 在 T-CODEX-12 实现时仍未完成；后续已通过单 target 真实 codex-cli 业务验收收口，见下一节记录。

## Codex audit 本地业务端到端真实验收收口记录

完成日期：2026-06-23

本记录收口 T-CODEX-11B 和 T-CODEX-11。用户已显式启用真实 codex-cli 本地业务端到端验收并提供结果；本次只记录文档，不重新运行真实 Codex，不修改后端业务代码、frontend、router、Codex runner/parser/prompt 或旧项目目录，也不提交 runtime 生成文件。

本次验收文件：

- `c26e1901-0173-49f5-abce-6a205d077bf3.result.json`

本次验收使用 T-CODEX-12 的 target 限流能力：

- 只审核 1 个 C07 target。
- `target_type=inspection_item`
- `check_id=C07`
- `finding_code=CONCLUSION_MISMATCH_002`

Codex review 结果：

- `codex_reviews_count: 1`
- `codex_status_counts: {"succeeded": 1}`
- `codex_verdict_counts: {"confirm": 1}`
- `codex_confidence_counts: {"high": 1}`
- `failed_reviews_count: 0`

Deterministic finding 结果仍保留：

- `deterministic_findings_count: 5194`
- `finding_severity_counts: {"error": 5180, "warn": 14}`
- `finding_check_counts: {"C04": 70, "C05": 14, "C06": 12, "C07": 72, "C08": 4894, "C09": 2, "C10": 130}`

审核意见摘要：

- Codex 确认了 C07 规则初判。
- 目标为 `inspection_item`，finding code 为 `CONCLUSION_MISMATCH_002`。
- Codex review 认为序号 3 的检验结果为“符合要求”，单项结论为“/”，而 `rule_context` 给出的期望结论为“符合”，因此支持规则初判。

验收结论：

- T-CODEX-11B 验收通过。
- T-CODEX-11 整体完成。
- T-CODEX-12 已完成，且本次真实模式结果证明 target 限流可以把 report-check 真实 Codex CLI 审核收敛到单 target。
- Codex review 没有覆盖原始 finding；deterministic findings 和 Codex review 两层证据并存。
- 默认 API 仍不会启用真实 Codex；真实 codex-cli 模式仍需要显式 gate。

后续风险：

- 当前样本 deterministic findings 数量仍很大，尤其 `C08=4894` 和 `C10=130`，需要后续单独收敛规则噪声或提取质量。
- 本次真实 Codex CLI 业务验收只覆盖单个 C07 target；后续扩大到 C02/C03/C04/C05/C06 或 PTR target 时，仍应保持小批量、分批验证。

## InspectionItemGroup builder 完成记录

完成日期：2026-06-23

本次实现 T-QUALITY-02，只新增 `InspectionItemGroup` 领域模型、独立 builder 和测试。本阶段不修改 C07/C08/C10 规则输出，不修改 C04/C05/C06，不修改 `ReportCheckUseCase`、router 或 frontend，不调用真实 Codex，不修改旧项目目录，也不改变现有 deterministic findings 数量。

背景：

- T-QUALITY-01 已确认 QW2025-2795 Draft.pdf 的 C08/C10/C07 噪声主要来自 physical row-level 判断。
- 本阶段先建立共同输入 contract，供后续 T-QUALITY-03/04/05 分别接入 C08/C10/C07。

本次实现：

- 新增 `backend/app/domain/inspection_group.py`：
  - `ContinuationMarker`
  - `InheritedField`
  - `InspectionItemGroup`
  - `InspectionItemGroupBuildResult`
- 新增 `backend/app/infrastructure/report/inspection_item_group_builder.py`：
  - `InspectionItemGroupBuilder.build(items)`
  - `build_inspection_item_groups(items)`
- Builder 只消费 `InspectionItem` 列表，不依赖 router/usecase，不运行 C07/C08/C10，不输出 `Finding`，不修改原始 rows。
- 支持普通序号归组、同序号多行归组、`续3` / `续 3` / `续\n3` 归组、空序号 payload 行归入 active group、空白行 diagnostics、跨页 pages 和 continuation markers。
- 输出 group-level `effective_test_results`、`effective_single_conclusion`、`effective_remark`，保留 `/` 和 `——` 作为有效占位符。
- 通过 `InheritedField` 记录 group 内字段继承关系，不修改原始 `InspectionItem`。
- `source_evidence` 仅包含每行页码、行号、字段值、field provenance 和 metadata 摘要，不包含完整 PDF 文本或绝对路径。
- 异常结构通过 diagnostics 记录，例如缺 page/row context、空白行无 payload、序号无法解析。

测试覆盖：

- 普通序号 1/2/3 分组。
- 同序号多 physical rows 合并。
- 续表 marker 多种空白形式归组。
- `is_continuation=True` 和 `metadata.logical_continuation=True` 的空序号续行归入 active group。
- 空序号空白行进入 diagnostics / ungrouped rows。
- 跨页 group 记录 `pages=[14, 15]` 和 page 15 的 `续 3` marker。
- effective test results 保留“符合要求”、`——`、`/` 和数值结果，剔除纯空白。
- effective conclusion / remark 选择非空有效值。
- inherited fields 记录继承来源和目标行，且不 mutate 原始 rows。
- source evidence 不泄露 `/Users/` 绝对路径。
- 真实样本结构 mini fixture 模拟序号 3 跨 page 14/15 的 C07 evidence。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/infrastructure/report/test_inspection_item_group_builder.py -v` | 先红灯失败于 `ModuleNotFoundError: No module named 'app.infrastructure.report.inspection_item_group_builder'`；实现后通过，`14 passed`。 |
| `cd backend && python -m pytest tests/rules/report/test_c07_item_conclusion.py tests/rules/report/test_c08_non_empty.py tests/rules/report/test_c10_continuation.py -v` | 通过，`37 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`522 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |

任务状态：

- T-QUALITY-02 已完成。
- T-QUALITY-03 / T-QUALITY-04 / T-QUALITY-05 仍未开始。
- C08/C10/C07 降噪尚未完成；现有规则仍保持原输出。
