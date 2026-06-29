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
| T-CODEX-06 | 已完成 | `PTRCompareUseCase` 已接入 `CodexAuditService`；T-CODEX-MANDATORY-01 后产品 factory 默认注入 mandatory Codex CLI，测试通过 fake dependency 注入。 |
| T-CODEX-07 | 已完成 | `ReportCheckUseCase` 已接入 `CodexAuditService`；T-CODEX-MANDATORY-01 后产品 factory 默认注入 mandatory Codex CLI，并为无逐 finding target 的规则输出 check summary target。 |
| T-CODEX-08 | 已完成 | 前端类型已支持 `codex_reviews`；PTR 和报告自检结果页已展示 Codex review 总览、finding 关联意见和未关联审核意见；前端只展示后端结果，不重新计算业务规则。 |
| T-CODEX-09 | 已完成 | T-CODEX-09A 已建立 gated/manual harness；T-CODEX-09B 已由用户显式运行 gated manual harness 并记录结果。第一次脚本失败为 Python 解释器缺少 pytest，使用 `PYTHON_BIN=python` 后 smoke 脚本通过。 |
| T-CODEX-10 | 已完成 | 本地 API usecase 构造路径已通过 settings/factory 装配 Codex audit；T-CODEX-MANDATORY-01 后不再提供用户层面的 disabled/fake/codex-cli 模式，默认使用本机 Codex CLI。 |
| T-CODEX-11 | 已完成 | T-CODEX-11A 已建立本地业务 E2E 验收脚本和文档；T-CODEX-11B 已由用户显式运行真实 codex-cli report-check 本地业务验收，返回 1 条 succeeded/confirm/high 的 C07 review。 |
| T-CODEX-11A | 已完成 | 新增本地业务 E2E 验收文档和脚本；T-CODEX-MANDATORY-01 后脚本改为 mandatory Codex CLI harness，默认 gate 拒绝运行，`--print-config` 安全。 |
| T-CODEX-11B | 已完成 | 使用 target 限流只审核 1 个 C07 `inspection_item` target；真实 Codex CLI 返回 succeeded review，verdict 为 confirm，confidence 为 high，failed reviews 为 0，deterministic findings 保留。 |
| T-CODEX-12 | 已完成 | 已实现 Codex audit target 筛选和分批元数据；T-CODEX-MANDATORY-01 后 batch size 仅控制单批性能，usecase 会继续处理后续 batch，不作为漏审上限。 |
| T-CODEX-MANDATORY-01 | 已完成 | 产品运行路径已纠偏为 mandatory Codex CLI audit：factory 默认构建 `CodexCliRunner`，runtime failed/skipped review 会让 Report/PTR task failed，uncertain 作为 completed 人工复核项，fake 仅用于测试注入。 |
| T-CODEX-MANDATORY-02 | 已完成 | 已实现 Codex verdict finalization：候选 finding 会标记 `confirmed/refuted/manual_review_required/out_of_scope/summary_only`；C04/C05/C06/C09 已补逐 finding target；full mandatory audit 缺 required review 会失败，targeted validation 明确不是完整审核。 |
| T-CODEX-MANDATORY-03 | 已完成 | 已修复 C04/C05/C06/C09 targeted validation 暴露的 summary target 过滤、C04/C06 OCR 语义和未使用部件 finalization 问题；不可验证标签内容和未使用部件不会因 Codex confirm 计入 confirmed final error。 |
| T-CODEX-MANDATORY-04 | 已完成 | 已拆分 C04 label caption candidate 与 matched label OCR content；sample-row-3 推车和 sample-row-14 30m 线缆这类“caption 存在但 OCR 未匹配”的 label-not-found candidate 不会因 Codex confirm 进入 confirmed final issue。用户真实 C04/C05/C06/C09 targeted validation 已通过：39 条 targeted reviews 全部 succeeded，confirmed findings/errors 均为 0。 |
| T-CODEX-MANDATORY-05A | 已完成 | 用户已完成真实 full mandatory Codex audit 验收：未设置 include filters，`audit_scope=full`、`full_audit=true`，57 条 Codex review 全部 succeeded，required candidates 全部完成 finalization，无 runtime failure、无 null final_status、无 out_of_scope、无 confirmed final error。 |
| T-CODEX-MANDATORY-05B | 已完成 | 已收口 final audit summary/UI 语义：summary 暴露 `audit_scope/full_audit/final_audit_status`，local E2E 脚本打印 final audit counts，前端结果页优先显示 Codex 审核完成与确认错误/人工复核/已反驳候选/候选错误，不再把旧 deterministic `fail_count/error_count` 作为最终错误口径。 |
| T-CODEX-EVIDENCE-01 | 已完成 | 已增强 manual review evidence：C04 target 包含 matched label crop/page、matched OCR text、structured fields 和字段对比；caption-only/empty OCR 明确证据不足；unused C04/C05/C06 component 防御性 refute；C07 target 增加首页符号说明、完整 group rows、actual conclusion candidates/provenance、group pages full text，并标记 complex matrix table。 |
| T-CODEX-EVIDENCE-02 | 已完成 | 已修复 C07 result token recovery 与 compact evidence：InspectionItemGroup 可从 row/page excerpt 恢复 `符合要求` 等检验结果 token；C07 不再把 item 94 这类不完整 all-placeholder candidate 输出为普通 ERROR；C07 evidence 改为 compact rows 和 item 附近 page_text excerpt，不再重复整页文本和完整 finding evidence。 |
| T-CODEX-EVIDENCE-03 | 已完成 | 已修复 C07 extraction-uncertain finalization 与 complex matrix 语义，并已通过 C07 targeted validation：`final_audit_status=needs_manual_review`，`confirmed_errors_count=0`，12 条 C07 均为 `manual_review_required`。 |
| T-CODEX-EVIDENCE-03B | 已完成 | 已记录 EVIDENCE-03 后 full mandatory Codex audit 真实验收：`audit_scope=full`，`final_audit_status=needs_manual_review`，`confirmed_errors_count=0`，`manual_review_required_count=40`，`codex_runtime_failure_count=0`。 |
| T-CODEX-EVIDENCE-04 | 已完成 | 已增强 C04 label image crop / matched OCR evidence：C04 target 区分 caption、page image/crop、matched OCR text、structured fields 和 verification flags；caption-only 或 unrelated OCR 不会被标为可验证标签内容；prompt 要求无 matched OCR/crop/structured fields 时 `uncertain`。本次未运行真实 Codex。 |
| T-CODEX-EVIDENCE-04B | 已完成 | 已修正 C04 metadata 假阳性并通过用户真实 C04 targeted validation `4ec18d39-7dab-4478-b6c0-d6bc464fd2e7`：`final_audit_status=needs_manual_review`，35 条 C04 review 无 runtime failure、无 confirmed error；照片页/page text 不再写入 `matched_label_ocr_text`，`evidence_has_matched_label_ocr_count` 和 `evidence_can_verify_label_content_count` 均从旧的 28 降为 0；sample-row-14 30m 线缆 caption selector 正确匹配 `№22`，不再误匹配 `№8`。 |
| T-CODEX-EVIDENCE-05 | 已完成 | 已实现 C04 中文标签样张视觉 evidence 链路，并通过真实 C04 targeted visual validation `c1f421db-4757-4041-8b19-c88b8835a941`：`audit_scope=targeted`、`included_check_ids=C04`、`final_audit_status=passed`，35 条 C04 review 全部 succeeded，35 条 C04 candidate 全部 refuted，无 confirmed error、无 manual review、无 runtime failure。 |
| T-CODEX-EVIDENCE-05A | 已完成 | 已修复 C04 visual review 输出 schema 的 strict mode 问题：`observed_label_fields` 以及 review `metadata` 中的视觉字段现在满足 OpenAI/Codex structured output 要求，所有有 `properties` 的 object 都要求完整 `required`；`7b20f4a4` 失败记录为 `invalid_json_schema`，不是报告业务错误。05A 后 C04 targeted visual audit 尝试已不再复现 schema 拒绝，但因 Codex usage limit 中断，未生成 final result。 |
| T-CODEX-EVIDENCE-05B | 已完成 | 已记录 EVIDENCE-05 后 full mandatory audit 真实验收 `1958c184-567f-4c56-aaac-4a8c45913d1c`：未设置 include filters，`audit_scope=full`、`full_audit=true`、`final_audit_status=needs_manual_review`，57 条 Codex review 无 runtime failure，51 条 candidate 中 39 条 refuted、12 条 manual review，confirmed findings/errors 均为 0；C04/C05/C06/C09 全部 refuted，剩余仅 C07 12 条需人工复核。 |
| T-CODEX-EVIDENCE-06 | 已完成 | C07 visual evidence 链路已完成 targeted 与 full audit 复验：targeted C07 审核 `2e7bbb93-3e7b-4477-8a5f-b1b25487fef0` 中 12 条 C07 有 11 条 refuted、1 条 manual；full mandatory audit 复验 `8e23d5bc-64f5-43c1-a0c5-2e02597840f6` 中 C04/C05/C06/C09 全部 refuted，C07 12 条中 11 条 refuted，仅剩 item 33 manual review，confirmed findings/errors 均为 0，runtime failure 为 0。 |
| T-CODEX-EVIDENCE-06E | 已完成 | 已记录真实 C07 targeted validation `a39b2841-e44d-4efd-a004-ae3147a2c1d6` 和后续 full mandatory audit 复验 `bf36101c-71a4-4f69-9df9-907ced1000cb`：item 33 residual manual review 已收口；当前 full audit 没有 confirmed final error，C04/C05/C06/C09 全部 refuted，C07 普通视觉复核项已基本收口，唯一剩余为 C07 item 59 complex matrix `manual_review_required`，保留人工复核符合安全口径。 |
| T-CODEX-EVIDENCE-07 | 已完成 | item 59 complex matrix specialized review 已完成 targeted 与 full audit 最终复验：targeted item 59 任务 `4b15adbb-6e4e-4a66-99e7-9170843b3646` 中 complex matrix candidate 被 Codex `refute/high`；随后 full mandatory audit `8e84b3e7-e079-4e6f-ac7f-b99348f18ffa` 达到 `final_audit_status=passed`，51 条 deterministic candidate 全部 refuted，confirmed/manual/runtime failure 均为 0。 |
| T-CODEX-EVIDENCE-07A | 已完成 | 已新增 `C07ComplexMatrixEvidenceBuilder` 并接入 `ReportCodexEvidenceBuilder`：C07 item 59 complex matrix target 现在带 `c07_complex_matrix_evidence`、matrix page/table/header/body/result/conclusion/continuation image refs 和 `structured_matrix_hints`；普通 C07 不带该 metadata。本阶段仅构建 EvidenceItem refs，不写 runtime 图片、不运行真实 Codex。 |
| T-CODEX-EVIDENCE-07B | 已完成 | 已完成 item 59 complex matrix materialization/handoff/prompt contract：writer 可将 matrix image items 写入 workspace-local PNG，service 可收集 matrix PNG paths，runner 会以 `--image items/...` 传递多张 matrix 图片，prompt 仅对 complex matrix target 注入 matrix-first 审核说明；未改 output schema/finalization，未运行真实 Codex。 |
| T-CODEX-EVIDENCE-07C | 已完成 | 已记录 item 59 targeted validation 与 T-CODEX-EVIDENCE-07 后 full mandatory audit 最终复验：full audit 未设置 include filters，`audit_scope=full`、`full_audit=true`、`final_audit_status=passed`、`codex_reviews_count=57`、`candidate_findings_count=51`、`confirmed_errors_count=0`、`manual_review_required_count=0`、`refuted_findings_count=51`、`codex_runtime_failure_count=0`。 |
| T-CODEX-RUNTIME-01B | 已完成 | 已修复 local E2E 失败摘要解析：当 task JSON 缺 `task_id` 时，可从 `runtime/codex_audit/{task_id}/{package_id}/input` 反推 task_id/package/check/batch；stderr 出现 usage limit 时归类为 `CODEX_USAGE_LIMIT_EXCEEDED` 并写入 `retry_after_text`。mandatory Codex runtime failure 仍保持 task failed。 |

验证命令：

| 命令 | 结果 |
| --- | --- |
| `git diff --check` | 通过 |

## Mandatory Codex CLI 运行架构纠偏记录

完成日期：2026-06-23

本次执行 T-CODEX-MANDATORY-01，将报告核对工具从“Codex audit 可选启用”纠偏为“产品运行路径必须通过本机 Codex CLI 审核”。

本次实现：

- `Settings` 新增 mandatory 配置：`CODEX_CLI_PATH=codex`、`CODEX_AUDIT_TIMEOUT_SECONDS=300`、`CODEX_AUDIT_RUNTIME_DIR=runtime/codex_audit`、`CODEX_AUDIT_MAX_TARGETS_PER_BATCH=5`、`CODEX_AUDIT_SANDBOX=read-only`、`CODEX_AUDIT_EPHEMERAL=true`。
- 旧 `CODEX_AUDIT_ENABLED`、`CODEX_AUDIT_BACKEND`、`CODEX_AUDIT_ALLOW_REAL_EXECUTION` 仅保留为 deprecated 兼容字段，产品 factory 不再把它们作为用户运行模式。
- `build_codex_audit_service(...)` 默认构建 `CodexCliRunner(enabled=True, allow_real_execution=True)`；API dependency 构造 usecase 时默认带 `CodexAuditService`，但构造阶段不调用 subprocess。
- `ReportCheckUseCase` 和 `PTRCompareUseCase` 不再把 Codex runtime failed/skipped review 吞进 completed 结果；失败 review 或 audit service exception 会让 task 进入 failed/error。
- Codex `uncertain` 属于正常 succeeded review，任务可 completed，前端展示为人工复核。
- `ReportCodexEvidenceBuilder` 对没有逐 finding target 的规则结果生成 `check_result` summary target，避免“无可审核 finding”被误解为无需 Codex。
- Report/PTR audit batching 改为 `target_offset + max_targets_per_batch` 循环处理；batch size 只限制单批性能，不再作为任务级漏审上限。
- `PromptBuilder` 明确 Codex 是 mandatory final auditor，deterministic rule output / rule_context 只是 candidate，不是最终事实；证据冲突应 refute，证据不足应 uncertain。
- `CodexCliRunner` command-not-found 错误码改为 `CODEX_CLI_UNAVAILABLE`。
- 前端 finding 行读取后端 `final_status` / Codex review 并显示 `Codex 已确认`、`Codex 已反驳`、`人工复核` 等状态；refute 不再渲染为危险色。
- 本地业务 E2E 脚本不再提供 disabled/fake/codex-cli 用户模式；脚本默认 gate 拒绝运行，设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1` 后才会上传并可能触发本机 Codex CLI。

任务结果语义：

- 规则 findings 是 candidate findings；兼容期仍保留在 `CheckResult.findings`。
- 被 Codex review 关联的 finding 会写入 metadata：`codex_required=true`、`codex_review_id`、`codex_verdict`、`final_status`。
- `confirm` 对应 `final_status=confirmed`；`refute` 对应 `final_status=refuted`；`uncertain` 对应 `final_status=manual_review_required`。
- Codex runtime failure 包括 `CODEX_CLI_UNAVAILABLE`、`CODEX_TIMEOUT`、`CODEX_EXIT_NONZERO`、`CODEX_OUTPUT_*` 等，产品 usecase 必须使 task failed。

验证结果：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/integration/test_codex_audit_local_e2e_artifacts.py -v` | 通过，`7 passed`。 |
| `cd backend && python -m pytest tests/application/test_codex_runtime_factory.py tests/application/test_codex_audit_service.py -v` | 通过，`15 passed`。 |
| `cd backend && python -m pytest tests/application/test_report_check_usecase.py tests/application/test_ptr_compare_usecase.py -v` | 通过，`42 passed`。 |
| `cd backend && python -m pytest tests/api -v` | 先失败于 API PTR e2e fixture 未注入 fake Codex audit service；修复测试 fixture 后通过，`14 passed`。 |
| `cd backend && python -m pytest tests/infrastructure/codex -v` | 通过，`67 passed`。 |
| `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py -v` | 通过，`28 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`557 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `bash -n scripts/run-codex-audit-local-e2e.sh` | 通过。 |
| `git diff --check` | 通过。 |

本次验证未运行真实 Codex CLI；API 和 usecase 测试通过 fake dependency 或 monkeypatch 保持可重复。

## Mandatory Codex verdict finalization 与全候选 target 覆盖修复记录

完成日期：2026-06-24

本次执行 T-CODEX-MANDATORY-02，收口 mandatory Codex audit 的最终结果语义，并修复真实 C07 targeted validation 暴露的 `final_status=null` 与候选错误误读问题。

真实结果背景：

- 用户本次有效结果文件为 `runtime/codex_audit_local_e2e/4cc203b9-a2e5-4c0a-859d-b0aa2a73b069.result.json`。
- 该次运行设置了 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07` 和 `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1`，因此属于 C07 targeted validation，不是 full audit。
- Codex runtime 成功：`codex_reviews_count=22`，`succeeded=22`，runtime failed/skipped 为 0。
- C07 12 条 candidate 全部被审核：`refute=9`、`uncertain=3`。
- 原结果仍显示候选 `error=54`，且 C04/C05/C06/C09 共 49 条未覆盖 finding `final_status=null`，需要在结果语义上拆分候选错误与最终确认错误。

本次实现：

- 新增统一 finalization helper：`confirm -> confirmed`、`refute -> refuted`、`uncertain -> manual_review_required`、`add_finding -> suggested_additional_finding`。
- `CheckSummary` 新增 candidate/final/refuted/manual/out-of-scope/summary-only/unreviewed/Codex runtime 计数；兼容保留原 `findings` 为 candidate findings。
- `ReportCheckUseCase` 和 `PTRCompareUseCase` 在附加 `codex_reviews` 后统一执行 finalization，并把 `codex_audit` 元数据写入 task result。
- full mandatory audit 下，required candidate finding 缺少 `codex_review_id` 或 `final_status` 会抛出 `CODEX_AUDIT_INCOMPLETE` 并使任务 failed。
- 使用 include/exclude filters 时，结果标记 `audit_scope=targeted`、`full_audit=false`；未覆盖候选标记 `final_status=out_of_scope`，不得误认为完整产品审核。
- `ReportCodexEvidenceBuilder` 将 C04 target 改为 `label_ocr`，并为 C09 添加逐 finding `inspection_item` target；C04/C05/C06/C09 candidate 都可生成逐条 Codex target。
- C01/C08/C10/C11 等 summary target 标记 `summary_only=true`，不参与 required candidate completeness。
- 前端报告/PTR 结果页新增候选错误、Codex 确认错误、人工复核、已反驳候选、本次未覆盖等展示，避免把 candidate error 误读为 final error。

结果语义：

- `confirmed_errors_count` 才表示 Codex 已确认的最终错误数。
- `refuted_findings_count` 仍保留原 candidate 和审计痕迹，但不计入最终错误。
- `manual_review_required_count` 表示 Codex 正常完成但证据不足或判断不确定，需要人工复核。
- `out_of_scope_findings_count` 只应出现在 targeted validation / 本地调试筛选场景。
- `included_check_ids` 是本地验收/调试工具，不是产品默认审核范围；产品默认应为 full mandatory audit。

验证结果：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/application/test_report_check_usecase.py tests/application/test_ptr_compare_usecase.py -v` | 通过，`44 passed`。 |
| `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py tests/application/test_ptr_codex_evidence_builder.py -v` | 通过，`45 passed`。 |
| `cd backend && python -m pytest tests/api -v` | 通过，`14 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`560 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `git diff --check` | 通过。 |

本次未运行真实 Codex CLI；所有验证均使用 fake dependency、monkeypatch 或普通前端构建。

## Mandatory Codex targeted summary / OCR 语义 / 未使用部件修复记录

完成日期：2026-06-24

本次执行 T-CODEX-MANDATORY-03，修复用户 C04/C05/C06/C09 targeted validation 后暴露的三类问题。本次不运行真实 Codex CLI，不调用 GPT/OpenAI API，不修改旧项目目录，也不继续扩展 C04/C05/C06 业务规则清理。

真实结果背景：

- 用户本次有效结果 task 为 `35c85ce3-a9bd-4739-9844-456a26149a72`。
- 该次运行设置了 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C04,C05,C06,C09`、`CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1`、`CODEX_AUDIT_TIMEOUT_SECONDS=300`，属于 targeted validation，不是 full audit。
- 任务完成，`codex_reviews_count=55`，Codex runtime failed/skipped 为 0。
- 49 条 targeted findings 均有 review，`unreviewed_required_findings_count=0`、`null_final_status_count=0`。
- 结果暴露 6 条非目标 summary reviews：C01/C02/C03/C08/C10/C11，不应进入 C04/C05/C06/C09 targeted validation。
- 部分 C04/C06 confirm 实际是在确认 “OCR 未识别字段”，不是确认中文标签本体缺字段或字段不一致。
- 样品描述中备注为“本次检测未使用”的部件不应被最终确认为缺照片或缺标签。

本次实现：

- `ReportCodexEvidenceBuilder` 的 summary target 生成现在同样遵守 include/exclude/finding-code filters；`CODEX_AUDIT_INCLUDED_CHECK_IDS=C04,C05,C06,C09` 时不会再为 C01/C02/C03/C08/C10/C11 生成 Codex summary targets。
- C04/C06 target metadata 和 rule context 增加标签内容可验证性字段：`evidence_has_label_image_crop`、`evidence_has_full_label_text`、`evidence_has_structured_label_fields`、`evidence_can_verify_label_content`。
- `PromptBuilder` 明确提示：OCR 未识别字段不等于标签缺字段；caption 能证明存在中文标签样张，但不能证明字段完整或缺失；没有标签图像、完整标签正文 OCR 或结构化标签字段时应 `uncertain`。
- `component_not_used` 归一化 whitespace/newline 后识别“本次检测未使用”；C04/C05/C06 target metadata 和 component evidence 标记 `is_unused_component`、`unused_reason`。
- `annotate_candidate_findings_with_codex_status` 增加防御性 finalization：如果 Codex 对不可验证标签内容返回 `confirm`，仍保留 `codex_verdict=confirm` 审计痕迹，但 `final_status` 降级为 `manual_review_required`，并记录 `CODEX_CONFIRMED_UNVERIFIABLE_LABEL_CONTENT`。T-CODEX-EVIDENCE-01 后，未使用部件 gap 返回 `confirm` 时改为 `final_status=refuted`，并记录 `CODEX_CONFIRMED_UNUSED_COMPONENT_GAP`。

修复后的语义：

- targeted validation 的 summary reviews 必须严格服从本次筛选范围。
- `confirmed_errors_count` 不应包含仅能证明 OCR 未识别、但不能证明标签本体缺字段的 C04/C06 candidate。
- `confirmed_errors_count` 不应包含备注为“本次检测未使用”的部件缺照片/缺标签 candidate。
- `codex_verdict` 保留 Codex 原始审核意见；`final_status` 是产品最终展示和统计口径。

下一步真实 targeted validation 建议重新运行：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C04,C05,C06,C09 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

## Mandatory Codex C04 label caption 与 matched OCR 语义修复记录

完成日期：2026-06-24

本次执行 T-CODEX-MANDATORY-04，修复 T-CODEX-MANDATORY-03 后真实 C04/C05/C06/C09 targeted validation 剩余的 C04 label-not-found 语义问题。本次不运行真实 Codex CLI，不调用 GPT/OpenAI API，不修改旧项目目录，也不修改 C05/C06/C09 业务规则。

真实结果背景：

- T-CODEX-MANDATORY-03 修复后，用户重新运行 C04/C05/C06/C09 targeted validation，主目标已达成：
  - task completed。
  - `audit_scope=targeted`。
  - `included_check_ids=["C04","C05","C06","C09"]`。
  - `codex_reviews_count=39`，`targeted_reviews_count=39`。
  - `unexpected_summary_reviews_count=0`。
  - `codex_failed_or_skipped_count=0`。
  - `null_final_status_count=0`。
  - `unreviewed_required_findings_count=0`。
  - `confirmed_errors_count=0`。
  - `confirmed_unverifiable_label_content_count=0`。
  - `confirmed_unused_component_count=0`。
- 剩余 2 条 C04 confirmed WARN 均为 `SAMPLE_COMPONENT_LABEL_NOT_FOUND`：
  - `sample-row-3`：部件 `心脏脉冲电场消融仪-推车`，真实 PDF 有 `№6 心脏脉冲电场消融仪-推车 中文标签样张`。
  - `sample-row-14`：部件 `心脏脉冲电场消融仪-触摸屏连接线缆（30m）（可选）`，真实 PDF 有 `№22 触摸屏连接线缆（30m）（可选） 中文标签样张`。
- Codex confirm 的实际依据是 label OCR 中未出现对应部件字段；这只能证明 matched OCR 缺失或未匹配，不能证明中文标签样张不存在。

本次实现：

- `ReportCodexEvidenceBuilder` 对 C04/C06 target metadata 明确拆分：
  - `matching_label_caption_candidates`
  - `matching_label_ocr_candidates`
  - `matched_label_id`
  - `matched_label_caption`
  - `matched_label_text`
  - `matched_label_fields`
  - `evidence_has_matching_label_caption`
  - `evidence_has_matched_label_ocr`
  - `evidence_has_matched_label_image_crop`
  - `evidence_has_matched_full_label_text`
  - `evidence_has_matched_structured_label_fields`
  - `evidence_can_verify_label_content`
- C04 branch 会把匹配当前 component 的中文标签样张 caption 作为 `label_caption:*` evidence item 交给 Codex；caption candidate 与 OCR content 不再混为一谈。
- `_label_for_finding` 对 C04/C06 不再在缺 matched label id 时退回 `report.labels[0]`，避免把无关 OCR 当作当前部件 matched OCR。
- 只有显式 label id 或确实按当前 component 匹配到的 label OCR 才会进入 `matching_label_ocr_candidates`；无关 OCR 即使有 raw blocks / structured fields，也不会让 `evidence_can_verify_label_content=true`。
- `PromptBuilder` 新增约束：
  - 中文标签样张 caption 能证明标签样张存在。
  - caption 存在但缺 matched OCR 时，不应确认标签样张缺失。
  - 未找到 OCR 字段不等于未找到标签样张。
  - 只有 matched label OCR 属于当前 component 时，才可判断标签字段是否缺失或不一致。
  - 如果只有 caption，没有标签正文或结构化字段，应 uncertain；如果 finding 是 label-not-found，caption 存在时应 refute。
- `annotate_candidate_findings_with_codex_status` 增加 defensive finalization：C04 `SAMPLE_COMPONENT_LABEL_NOT_FOUND` + `evidence_has_matching_label_caption=true` + `evidence_has_matched_label_ocr=false` 时，即使 Codex 返回 `confirm`，也降级为 `final_status=manual_review_required`，并记录 `CODEX_CONFIRMED_LABEL_MISSING_BUT_CAPTION_EXISTS`。

修复后的语义：

- `SAMPLE_COMPONENT_LABEL_NOT_FOUND` 不再等价于“没有中文标签样张”；它可能只是没有 matched label OCR body / structured fields。
- matching caption 可以 refute “标签样张缺失” candidate，但不能直接证明字段内容完整。
- 字段缺失或字段不一致的最终确认，必须基于属于当前 component 的 matched label OCR 或可核验标签图像证据。
- deterministic finding 仍保留；Codex 和 finalization 只改变最终展示/统计口径，不删除原始 candidate。

新增测试覆盖：

- sample-row-3 推车：caption candidates 包含 `№6 心脏脉冲电场消融仪-推车 中文标签样张`，无 matched OCR 时 `evidence_can_verify_label_content=false`。
- sample-row-14 30m 线缆：caption candidates 包含 `№22 触摸屏连接线缆（30m）（可选） 中文标签样张`，无 matched OCR 时 `evidence_can_verify_label_content=false`。
- 只有不相关 OCR 时，`matching_label_ocr_candidates=[]`，不会生成 C04 `label_ocr:*` evidence item，也不会视为可核验标签内容。
- matched label OCR 存在且属于当前 component 时，才设置 `evidence_has_matched_label_ocr=true` 和 `evidence_can_verify_label_content=true`。
- Codex 对 C04 label-not-found + matching caption 返回 `confirm` 时，finalization 进入 `manual_review_required`，并记录 `CODEX_CONFIRMED_LABEL_MISSING_BUT_CAPTION_EXISTS`。

真实 targeted validation 验收结果：

- 用户已基于真实样本 `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf` 重新运行 C04/C05/C06/C09 targeted validation。
- 结果文件：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3/runtime/codex_audit_local_e2e/9a50ae34-f7d6-4dbe-a7ed-9ffb1de0a40d.result.json`。
- 本轮使用 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C04,C05,C06,C09`，因此是 targeted validation，不是 full audit。
- 关键结果：
  - task status: `completed`
  - `audit_scope=targeted`
  - `included_check_ids=C04,C05,C06,C09`
  - `unique_findings_count=51`
  - `codex_reviews_count=39`
  - `targeted_findings_count=39`
  - `targeted_reviews_count=39`
  - `codex_by_status={"succeeded": 39}`
  - `codex_failed_or_skipped_count=0`
  - `unexpected_summary_reviews_count=0`
  - `null_final_status_count=0`
  - `unreviewed_required_findings_count=0`
  - `confirmed_findings_count=0`
  - `confirmed_errors_count=0`
  - `confirmed_unverifiable_label_content_count=0`
  - `confirmed_unused_component_count=0`
  - `confirmed_c04_label_not_found_count=0`
  - targeted findings by final status: `manual_review_required=28`、`refuted=11`
- 验收结论：
  - T-CODEX-MANDATORY-04 targeted validation 通过。
  - targeted summary filter 已生效，未产生非目标 summary reviews。
  - C04/C06 中仅 OCR 不足或标签内容不可验证的 candidate 没有再进入 confirmed。
  - “本次检测未使用”部件没有再进入 confirmed。
  - 当前仍未做 full audit。

后续如需重复该 targeted validation，可运行：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C04,C05,C06,C09 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

## Full mandatory Codex audit 真实验收记录

完成日期：2026-06-25

本次记录 T-CODEX-MANDATORY-05A。用户已基于真实样本运行 full mandatory Codex audit，本轮只记录用户提供的真实验收结果；本次文档更新不运行真实 Codex CLI，不调用 GPT/OpenAI API，不修改 backend/frontend/router，不修改旧项目目录，也不继续证据增强或规则细化。

真实样本：

- `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf`

结果文件：

- `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3/runtime/codex_audit_local_e2e/11417700-a536-4ae0-81ec-a4e74c22c19e.result.json`

运行口径：

- 本轮没有设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`。
- 因此本轮是 full audit，不是 targeted validation。
- `task_id=11417700-a536-4ae0-81ec-a4e74c22c19e`
- `task_type=report_check`
- task status: `completed`
- `audit_scope=full`
- `full_audit=true`
- `included_check_ids=[]`

关键结果：

- `unique_findings_count=51`
- `candidate_findings_count=51`
- `candidate_errors_count=44`
- `codex_reviews_count=57`
- `codex_by_status={"succeeded":57}`
- `codex_by_verdict={"uncertain":40,"refute":17}`
- `codex_runtime_failure_count=0`
- `null_final_status_count=0`
- `unreviewed_required_findings_count=0`
- `out_of_scope_findings_count=0`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=17`
- `manual_review_required_count=34`

按 check_id 的 final status：

| check_id | manual_review_required | refuted |
| --- | ---: | ---: |
| C04 | 29 | 6 |
| C05 | 0 | 2 |
| C06 | 0 | 1 |
| C07 | 5 | 7 |
| C09 | 0 | 1 |

验收结论：

- Full mandatory Codex audit 真实验收通过。
- 所有 required candidate 均已完成 Codex finalization。
- 没有 Codex runtime failure。
- 没有 null `final_status`。
- 没有 `out_of_scope`。
- 本轮没有 confirmed final error。
- 当时仍有 34 条 `manual_review_required`，需要后续按证据增强或规则细化任务处理；该历史结果已被 T-CODEX-EVIDENCE-03B 的最新 full audit 记录更新。
- 旧 `summary.error_count=44` 和 `fail_count=5` 是 candidate 层统计，不应被理解为最终错误；最终错误口径应看 `confirmed_errors_count=0` 和相关 finalization 计数。

## T-CODEX-MANDATORY-05B：Final audit summary / UI 语义收口

完成日期：2026-06-25

本次执行 T-CODEX-MANDATORY-05B，在不调用真实 Codex CLI、不修改旧项目目录、不继续证据增强或规则细化的前提下，收口 full mandatory audit 之后的 summary、UI 和 local E2E 输出语义。

本次实现：

- `CheckSummary` 新增 `audit_scope`、`full_audit`、`final_audit_status`，并由 task completion 将 `metadata.codex_audit` 中的审计口径同步到 summary。
- `final_audit_status` 四态语义：
  - `passed`：`confirmed_errors_count=0` 且 `manual_review_required_count=0`。
  - `needs_manual_review`：`confirmed_errors_count=0` 且 `manual_review_required_count>0`。
  - `failed`：`confirmed_errors_count>0`。
  - `audit_failed`：Codex runtime failure 或 required finding 缺少 review/finalization。
- 当时的 full audit 结果对应 `final_audit_status=needs_manual_review`，因为 confirmed final error 为 0，但仍有 34 条人工复核项；最新 full audit 记录见 T-CODEX-EVIDENCE-03B。
- 前端报告自检和 PTR 结果页优先展示 Codex final audit 口径：标题 badge 使用“Codex 审核完成/未完成”，metric 显示“确认错误”“人工复核”“已反驳候选”“候选错误”。
- 旧 `fail_count`、`error_count`、`warn_count` 保持兼容，但语义为 legacy deterministic candidate counts，不作为最终错误口径。
- local E2E 脚本在下载 result JSON 后打印 final audit counts，包括 `final_audit_status`、candidate/final/refuted/manual/out-of-scope/unreviewed/runtime failure 计数，并单独输出 legacy deterministic counts。

验收口径：

- 本轮 full audit 的最终状态应展示为 `needs_manual_review`。
- `candidate_errors_count=44` 可以继续展示为候选错误，但不得替代 `confirmed_errors_count=0`。
- 前端不根据旧 deterministic `fail_count=5` 显示最终失败。

## T-CODEX-EVIDENCE-01：Manual review evidence enhancement

完成日期：2026-06-25

本次执行 T-CODEX-EVIDENCE-01，在不调用真实 Codex CLI、不调用 GPT/OpenAI API、不修改旧项目目录、不改 UI 的前提下，补强 full mandatory audit 后仍停留在人工复核的 C04/C07 evidence package。

背景口径：

- T-CODEX-MANDATORY-05A 当时的 full audit：`confirmed_errors_count=0`、`manual_review_required_count=34`、`refuted_findings_count=17`。T-CODEX-EVIDENCE-03B 已记录更新后的 full audit 结果。
- 人工复核项分布：C04=29，C07=5。
- C04 的主要问题是标签样张 caption 存在，但缺 matched label crop/OCR/structured fields，导致 Codex 只能 uncertain。
- C07 的主要问题是 full audit evidence 缺首页符号说明、完整 group rows、group pages page_text 和 conclusion provenance；item 59 是复杂矩阵表列映射，不应按普通 C07 confirmed。

本次实现：

- C04 evidence package 现在包含：
  - sample description row。
  - matching label caption candidates。
  - matched label crop/page reference，若 `LabelOCRResult.image_ref` 是相对 evidence path，会作为 `label_image:*` evidence item 的 `file_path`。
  - matched OCR text。
  - matched structured fields。
  - `label_field_comparison`，记录 sample value、matched label value 和 comparison hint。
- C04/C06 caption-only 或 empty OCR 会标记 `evidence_incomplete=true`、`expected_codex_when_label_content_missing=uncertain`，避免把 OCR 不足确认为标签本体缺字段。
- C04 label-not-found 但 caption 存在时，metadata 记录 `expected_codex_when_label_not_found_but_caption_exists=refute`。
- C04/C05/C06 `is_unused_component=true` 即使 Codex 返回 `confirm`，finalization 也防御性转为 `refuted`，并保留 `CODEX_CONFIRMED_UNUSED_COMPONENT_GAP` 诊断，避免占用人工复核池。
- C07 evidence package 现在包含：
  - 首页符号说明 evidence：`——` 表示不适用，`/` 表示空白。
  - 完整 `InspectionItemGroup` rows。
  - `effective_test_results`。
  - `actual_conclusion_candidates`。
  - `conclusion_candidate_provenance`。
  - continuation rows / source rows。
  - group pages 的 full page text。
  - `complex_matrix_table` / `complex_matrix_reason`。
- C07 `complex_matrix_table=true` 即使 Codex 返回 `confirm`，finalization 也防御性降级为 `manual_review_required`，并保留 `CODEX_CONFIRMED_COMPLEX_MATRIX_TABLE` 诊断。
- Prompt 已同步：matched label fields 与样品描述一致时应 refute；字段确实缺失/不一致且有 OCR/crop/structured fields 时可 confirm；unused component 应 refute/not_applicable；complex matrix C07 不应按普通 C07 直接 confirm。

预计对下一轮真实 full audit 的影响：

- C04 caption-only 且无 matched OCR/crop/structured fields 的项仍应是 `uncertain`，但原因更清楚。
- C04 有 matched label OCR 且字段匹配的项预计可从 manual review 转为 `refute`。
- C04 有 matched label OCR 且字段确实缺失/不一致的项才可能 `confirm`。
- C04/C05/C06 unused component 不应继续进入 `manual_review_required`。
- C07 item 142/149 因 group page_text 可见“符合要求”，预计更容易从 `uncertain` 转为 `refute`。
- C07 item 59 会继续保留人工复核语义，因为它属于 complex matrix table 列映射问题，不应按普通 C07 confirmed。
- C07 item 151 现在会带首页符号说明和完整 group evidence，需下一轮真实 Codex audit 判断。

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

本次实现 T-CODEX-06 第二阶段，在 `PTRCompareUseCase` 中通过 `CodexAuditService` 接入 PTR clause/table/parameter/scope review。当时阶段性实现仍然默认关闭 Codex audit；该语义已被 T-CODEX-MANDATORY-01 取代。当前产品路径默认构建 mandatory `CodexCliRunner`，测试仍使用 fake audit service 或 `CodexAuditService + FakeCodexRunner`，不调用真实 Codex CLI，不修改 router、frontend 或旧项目目录，不重写 PTRExtractor、parameter_compare 或 table_reference_compare，不继续扩展 PTR numeric semantic / diff_builder。

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
- 历史阶段默认关闭 Codex audit；当前产品路径已改为通过 factory 默认注入 mandatory `CodexAuditService + CodexCliRunner`。
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

本次实现 T-CODEX-07 第二阶段，在 `ReportCheckUseCase` 中通过可选依赖接入 `CodexAuditService`。当时阶段性实现默认关闭 Codex audit；该语义已被 T-CODEX-MANDATORY-01 取代。当前产品路径默认构建 mandatory `CodexCliRunner`，测试使用 fake audit service，不调用真实 Codex CLI，不修改 router、frontend 或旧项目目录，不重写 C01-C11 规则，不改变 deterministic findings，不把 `add_finding` 自动追加为 deterministic finding。

本次实现：

- `ReportCheckUseCase` 新增可选依赖：
  - `codex_audit_service: CodexAuditServiceProtocol | None = None`
  - `codex_audit_enabled: bool = False`
  - `report_codex_evidence_builder: ReportCodexEvidenceBuilder | None = None`
- 历史阶段默认 `codex_audit_enabled=False`；当前产品路径已改为通过 factory 默认注入 mandatory `CodexAuditService + CodexCliRunner`。
- deterministic C01-C11 流程保持不变：PDF 解析、ReportDocument 构建、规则 runner 运行、`CheckResult` 聚合路径不变。
- 规则结果生成后，启用 Codex audit 且存在可审核 finding 时，usecase 调用 `ReportCodexEvidenceBuilder.build(...)` 构建 request/package，再调用 `CodexAuditService.review(...)`。
- `CodexReviewResult` 直接附加到对应 `CheckResult.codex_reviews`；`CheckResult.summary` 和任务级 summary 仍基于 deterministic findings。
- 历史阶段支持的运行时审核范围仅为 `C02/C03/C04/C05/C06/C07`；当前 mandatory 架构已为无逐 finding target 的规则补充 `check_result` summary target。
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
- 历史阶段 API 默认不启用真实 Codex；该说法已被 T-CODEX-MANDATORY-01 取代，当前产品路径默认构建 mandatory Codex CLI audit。

## Codex audit 本地运行时配置与依赖装配完成记录

完成日期：2026-06-18

本节是历史完成记录。T-CODEX-10 最初实现了可选装配；该语义已被 T-CODEX-MANDATORY-01 取代。当前产品运行路径不再提供用户层面的 disabled/fake/codex-cli 选择，`FakeCodexRunner` 只用于 pytest 或显式测试 dependency override。

当前有效语义：

- API route dependency 仍通过 application factory 构造 usecase，router 不承载 Codex CLI runner 逻辑。
- 产品 factory 默认构建 `CodexAuditService + CodexCliRunner(enabled=True, allow_real_execution=True)`。
- 当前有效配置为 `CODEX_CLI_PATH`、`CODEX_AUDIT_TIMEOUT_SECONDS`、`CODEX_AUDIT_RUNTIME_DIR`、`CODEX_AUDIT_MAX_TARGETS_PER_BATCH`、`CODEX_AUDIT_SANDBOX=read-only`、`CODEX_AUDIT_EPHEMERAL=true`。
- 旧 `CODEX_AUDIT_ENABLED`、`CODEX_AUDIT_BACKEND`、`CODEX_AUDIT_ALLOW_REAL_EXECUTION` 仅保留为 deprecated 兼容字段，产品 factory 不再读取它们作为运行模式。
- Codex audit workspace 仍由 `EvidencePackageWriter` 写入 `runtime/codex_audit/{task_id}/{package_id}/input/`，runner 仍使用 read-only sandbox、output schema 和 timeout。
- Codex runtime failure 会让业务 task failed；deterministic findings 作为 candidate 保留，并通过 Codex review metadata 标记最终审核状态。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/application/test_codex_runtime_factory.py tests/api/test_codex_audit_dependencies.py -v` | 先红灯失败于 `ModuleNotFoundError: No module named 'app.application.codex_runtime_factory'`；实现后通过，`6 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`485 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `git diff --check` | 通过。 |

## Codex audit 本地业务端到端验收脚本和文档完成记录

完成日期：2026-06-18

本节是历史完成记录。T-CODEX-11A 最初提供本地业务 E2E 脚本和文档；T-CODEX-MANDATORY-01 后，脚本已改为 mandatory Codex CLI harness，不再提供 disabled/fake/codex-cli 用户模式。

当前有效语义：

- `docs/codex-audit-local-e2e.md` 说明 mandatory Codex CLI 本地业务验收路径。
- `scripts/run-codex-audit-local-e2e.sh` 支持 `--help` 和 `--print-config`，这两个命令不启动服务、不上传文件、不调用 Codex。
- 真正上传/轮询前必须设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1`，避免误触发本机 Codex CLI。
- 脚本支持 `TASK_TYPE=ptr-compare|report-check`、`START_BACKEND=1`、`PTR_FILE` / `REPORT_FILE`、`EXPECT_CODEX_REVIEWS=auto|empty|nonempty|any`。
- 文档明确前端只展示后端返回的 `codex_reviews` 和 finding metadata，不重新计算 C01-C11 或 PTR 规则。
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
- T-CODEX-MANDATORY-01 后，脚本只保留 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1` 作为本地业务验收 gate；旧 optional env 会被 unset，避免污染 mandatory 产品运行配置。
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
- T-CODEX-MANDATORY-01 后，产品 API 构造路径默认启用本机 Codex CLI audit；真实业务 E2E 脚本仍需要 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1` gate，避免脚本误触发本机 Codex。

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
- T-QUALITY-03 已完成。
- T-QUALITY-04 已完成。
- T-QUALITY-05 仍未开始。
- C08 已切换为 group-level effective field 判断；C10 已切换为 group page-boundary 判断；C07 降噪尚未完成，现有 C07 规则仍保持原输出。

## C08 group-level 重构完成记录

完成日期：2026-06-23

本次实现 T-QUALITY-03，将 C08 从逐 physical row 的空字段判断改为消费 `InspectionItemGroup` 的 group-level effective fields。本阶段不修改 C07/C10，不修改 C04/C05/C06，不修改 `ReportCheckUseCase`、router 或 frontend，不调用真实 Codex，不修改旧项目目录，也不新增 `FindingGroup`。

背景：

- T-QUALITY-01 确认 QW2025-2795 Draft.pdf 中 `C08=4894` 的主要噪声来自合并单元格、续表行、空序号 payload 行和同一序号多 physical rows 被逐行报空。
- T-QUALITY-02 已提供 `InspectionItemGroupBuilder`，可输出 `effective_test_results`、`effective_single_conclusion`、`effective_remark`、pages、continuation markers、source evidence 和 diagnostics。

本次实现：

- `backend/app/rules/report/c08_non_empty.py` 现在先调用 `build_inspection_item_groups(document.inspection_items)`。
- C08 必填字段仍为“检验结果 / 单项结论 / 备注”，但判断对象改为：
  - `group.effective_test_results`
  - `group.effective_single_conclusion`
  - `group.effective_remark`
- `/` 和 `——` 继续作为有效占位符，不被判断为空。
- 每个 item group / field 最多输出 1 条 `INSPECTION_FIELD_EMPTY` finding；group 内空 physical rows 不再重复展开为主 findings。
- 纯空白 ungrouped row 不产生 C08 finding；builder diagnostics 和 ungrouped row count 写入 `CheckResult.metadata`。
- 原 physical row 明细进入 `Finding.metadata`，包括 `item_no`、`normalized_item_no`、`field_key`、`field_name`、`group_row_count`、`pages`、`source_rows`、`empty_physical_rows`、`inherited_fields`、`suppressed_physical_row_count`、`group_diagnostics` 和 `continuation_markers`。

测试覆盖：

- 多 physical rows 中只有部分行字段为空，但 group effective value 非空时不报 C08。
- 单项结论或备注只在 group 内某一行出现时，按 group-level 通过。
- group 全部检验结果 / 单项结论 / 备注为空时，每个字段只报 1 条 finding。
- 一个 group 三个必填字段都缺失时最多 3 条 findings。
- `/` 和 `——` 作为有效占位。
- `续3` / `续 3` 行归入原 group，不产生续表子行噪声。
- 空序号 payload 行归入 active group，不产生额外 row-level finding。
- ungrouped 纯空白行不产生 C08 finding。
- QW2025-2795 类似跨 page 14/15 的 mini fixture 不因子行空白产生 C08 噪声。
- `backend/app/rules/report/c08_non_empty_fields.py` 兼容入口仍复用新 C08 口径。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/rules/report/test_c08_non_empty.py tests/rules/report/test_c08_non_empty_fields.py -v` | TDD 红灯先失败于旧 row-level 行为；实现后通过，`24 passed`。 |
| `cd backend && python -m pytest tests/infrastructure/report/test_inspection_item_group_builder.py tests/rules/report/test_c07_item_conclusion.py tests/rules/report/test_c10_continuation.py tests/rules/report/test_c08_non_empty.py -v` | 通过，`59 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`530 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |

任务状态：

- T-QUALITY-03 已完成。
- T-QUALITY-04 已完成。
- T-QUALITY-05 / T-QUALITY-06 / T-QUALITY-07 未完成。
- 未在本阶段直接跑完整 QW2025-2795 Draft.pdf；真实 PDF 的 C08 数量下降需要后续本地 e2e 或 T-QUALITY-03B 重新确认。

## C10 page-boundary 重构完成记录

完成日期：2026-06-23

本次实现 T-QUALITY-04，将 C10 从全局 page first / previous page tail 的弱判断改为消费 `InspectionItemGroup` 的 group page-boundary 检查。本阶段不修改 C07/C08，不修改 C04/C05/C06，不修改 `ReportCheckUseCase`、router 或 frontend，不调用真实 Codex，不修改旧项目目录，也不新增 `FindingGroup`。

背景：

- T-QUALITY-03 完成后，真实样本重新验收摘要显示 deterministic findings 从 5194 降到 440，其中 `C08=140`、`C10=130`、`C07=72`。
- C08 降噪证明 group-level 方案有效；C10 的 130 条仍提示续表标记可能按 page/row 维度重复报错。

本次实现：

- `backend/app/rules/report/c10_continuation.py` 现在先调用 `build_inspection_item_groups(document.inspection_items)`。
- C10 只对 group 内相邻 page boundary 做续表检查：
  - 当前页第一条相关行是 `续 X` 且 `X == group.item_no` 时通过。
  - 当前页第一条相关行不是续表 marker 且本页没有后续 marker 时，输出缺失续表标记 finding。
  - `续 X` 出现在当前页非第一条相关行时，输出位置错误 finding。
  - 页面第一行 marker 与上一页末尾序号不一致时，保留 `CONTINUATION_MARK_MISMATCH`。
- 每个 `item_no/current_page` boundary 最多输出 1 条 finding；同页多个空序号 payload 行、续表子行和结构行不重复展开为主 findings。
- 缺 page 或 row context 时仍只输出单条 `CONTINUATION_CONTEXT_MISSING` WARN，并在 `CheckResult.metadata.boundary_uncertain` 标记不确定。
- 保持旧 code 兼容：
  - `CONTINUATION_MARK_ERROR_001`
  - `CONTINUATION_MARK_ERROR_002`
  - `CONTINUATION_MARK_MISMATCH`
  - `CONTINUATION_CONTEXT_MISSING`

Finding metadata：

- `item_no`
- `previous_page`
- `current_page`
- `expected_marker`
- `actual_marker`
- `boundary_key`
- `first_related_row_index`
- `marker_row_index`
- `group_row_count`
- `group_pages`
- `continuation_markers`
- `duplicate_suppressed_count`
- `source_rows`
- `group_diagnostics`

测试覆盖：

- 跨页 group 当前页第一条相关行为 `续3` 时不报错。
- 跨页 group 当前页第一条相关行没有 `续3` 时只报 1 条 missing finding。
- 页面第一行 `续4` 但上一页末尾为 3 时输出 mismatch。
- `续3` 出现在 current page 第二条相关行时只报 1 条 misplaced finding。
- 同一 group 跨 3 页时分别按 page boundary 检查，不对页内子行重复检查。
- 空序号 payload 行和续表子行归入 active group，不导致重复 C10 finding。
- 缺 page/row context 只产生 WARN / diagnostics。
- QW2025-2795 类似 page 14/15 的 mini fixture：page 15 首行为 `续 3` 时通过；改成普通 `3` 时只报 1 条。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/rules/report/test_c10_continuation.py -v` | TDD 红灯先失败于旧 row/page-level 行为；2026-06-23 复验通过，`14 passed`。 |
| `cd backend && python -m pytest tests/infrastructure/report/test_inspection_item_group_builder.py tests/rules/report/test_c07_item_conclusion.py tests/rules/report/test_c08_non_empty.py tests/rules/report/test_c10_continuation.py -v` | 2026-06-23 复验通过，`78 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 2026-06-23 复验通过，`551 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |

任务状态：

- T-QUALITY-04 已完成。
- T-QUALITY-05 / T-QUALITY-06 / T-QUALITY-07 未完成。
- 用户已重新对 `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf` 运行本地 report-check 验收，最新结果为 `C10 unique count: 0`。
- C10 降噪路径已闭环：此前真实样本 `C10=130`，主要 code 为 `CONTINUATION_MARK_MISMATCH`；T-QUALITY-04 切换为 group page-boundary 后，`by_code={}`、`by_boundary=[]`、`by_item=[]`、`by_page=[]`。
- C10 page-boundary 降噪闭环完成；C08 仍保持 `C08 count: 0`。
- 下一推荐任务：T-QUALITY-05：C07 group-level 重构。

## C08 item_no 污染修复完成记录

完成日期：2026-06-23

本次实现 T-QUALITY-03B，修复 T-QUALITY-03 后 C08 剩余误报中的 `item_no` 污染问题。本阶段不修改 C07/C10，不修改 C04/C05/C06，不修改 `ReportCheckUseCase`、router 或 frontend，不调用真实 Codex，不修改旧项目目录。

背景：

- T-QUALITY-03 后真实样本重新统计为 `deterministic_findings_count=440`、`C08=140`。
- C08 剩余示例中 `item_no` 被污染为标准要求正文，例如：
  - `——所有其他 ME 设备和 ME 系统，500V。`
  - `当外壳的分类为 IPX0 时，保持 ME 设备和其部件在潮湿箱里 48h。`
  - `预期一次性使用的任何材料，元器件，附件或 ME 设备……`
  - `对于 SI 单位，单位的倍数和某些其他单位……`
- 这些文本属于“标准要求”列或其子行，不应作为检验项目序号创建新 group。

本次实现：

- `InspectionItemGroupBuilder` 强化序号合法性：
  - 合法序号只接受纯数字，例如 `1`、`10`、`118`。
  - 合法续表序号只接受 `续 + 数字`，例如 `续3`、`续 3`、`续\n3`。
  - `sequence_raw` 非空时优先校验 raw 文本；即使上游误填了 `InspectionItem.sequence`，非法 raw 也不会创建新 group。
- 非法 `sequence_raw` 处理：
  - 看起来像标准要求正文、`a)` / `b)` / `c)` 子项、标准条款号或长中文正文，且存在 active numeric group 时，作为 payload row 归入 active group。
  - 没有 active group 时进入 `ungrouped_rows`，并记录 `UNGROUPED_PAYLOAD_WITH_INVALID_SEQUENCE`。
  - 普通不可解析序号仍记录 `UNPARSEABLE_ITEM_NO`。
- `inspection_table_extractor.parse_sequence` 收紧为只接受纯数字或 `续 + 数字`，不再从 `500V`、`IPX0 ... 48h` 或 `4.10.2` 中抓取数字。
- C08 继续只消费 group-level effective fields；非法 item_no 行进入 diagnostics 或 active group 明细，不展开为 3 条主 ERROR。

测试覆盖：

- `sequence_raw="——所有其他 ME 设备和 ME 系统，500V。"` 且 `sequence=500` 时，不创建 `500` group，归入前一个合法 `10` group。
- `sequence_raw="当外壳的分类为 IPX0 时，保持 ME 设备和其部件在潮湿箱里 48h。"` 且 `sequence=48` 时，不创建 `48` group，归入前一个合法 `15` group。
- `a) 子项要求`、`4.10.2` 不创建新 group，有 active group 时归入 active group。
- 无 active group 的长中文非法序号进入 ungrouped diagnostics，不产生 C08 三字段 ERROR。
- 合法数字和 `续 118` 仍正常归组。
- C08 mini fixture 验证上述长文本不会作为 finding metadata 中的 `item_no` 产生主 finding。
- `parse_sequence` 验证不再从标准要求正文或标准条款号中抽取数字。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/infrastructure/report/test_inspection_item_group_builder.py tests/rules/report/test_c08_non_empty.py -v` | TDD 红灯先失败于旧 builder 误建 `500/48/4/1` group；实现后通过。 |
| `cd backend && python -m pytest tests/infrastructure/report/test_inspection_item_group_builder.py tests/infrastructure/report/test_inspection_table_extractor.py tests/rules/report/test_c08_non_empty.py -v` | 通过，`47 passed`。 |
| `cd backend && python -m pytest tests/rules/report/test_c07_item_conclusion.py tests/rules/report/test_c10_continuation.py tests/rules/report/test_c08_non_empty.py -v` | 通过，`52 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`543 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |

任务状态：

- T-QUALITY-03B 已完成。
- T-QUALITY-05 / T-QUALITY-06 / T-QUALITY-07 未完成。
- 未在本阶段直接跑完整 QW2025-2795 Draft.pdf；真实 PDF 的 C08 数量需要后续本地验收重新确认。

## C08 item 126 备注占位符误报修复完成记录

完成日期：2026-06-23

本次实现 T-QUALITY-03C，修复真实样本 QW2025-2795 Draft.pdf 中序号 126 的 C08 `remark` 空值误报。本阶段不修改 C07/C10，不修改 C04/C05/C06，不修改 `ReportCheckUseCase`、router 或 frontend，不调用真实 Codex，不修改旧项目目录。

背景：

- T-QUALITY-03 将真实样本 C08 从 4894 降到 140。
- T-QUALITY-03B 修复 `item_no` 污染后，真实样本 C08 统计变为 `C08 count=2`、`by_field={"remark": 2}`、`top_item_no={"126": 2}`。
- 两条 C08 finding 的 `id` 完全相同：`55ae8140-7108-4ea6-a015-f5648ce1be99-c08-group-125-remark-empty`，说明用户统计脚本递归遍历时同时收集了 top-level `findings` 和 `check_results[].findings`；按 `finding.id` 去重后 unique C08 实际为 1。
- 该 unique finding 的结构化证据显示 item 126 源行被解析为 `test_result="符合"`、`single_conclusion="/"`、`remark=""`，而真实报告右侧可见 `符合 /`；首页说明 `/` 表示空白占位符，应视为有效备注。

本次实现：

- `InspectionItemGroupBuilder` 在 group effective field 标准化层恢复右侧结论/备注组合：
  - `single_conclusion="符合 /"`、`不符合 /`、`/ /`、`—— /` 且 `remark` 为空时，拆分为前半部分的 `effective_single_conclusion` 和 `effective_remark="/"`。
  - 上游把组合值放进 `test_result="符合 /"`，且 `single_conclusion` / `remark` 为空时，也恢复为 `effective_single_conclusion="符合"`、`effective_remark="/"`。
  - 真实样本 item 126 的错位形态 `test_result="符合"`、`single_conclusion="/"`、`remark=""` 被恢复为 `effective_single_conclusion="符合"`、`effective_remark="/"`。
- 修复只读取右侧结构化字段 `test_result` / `conclusion` / `remark`，不从 `standard_requirement` 或正文里继承 `/`，避免把标准要求中的斜杠误判为备注。
- C08 继续消费 group-level effective fields；无任何 combined slash 证据时，`remark=""` 仍产生 `INSPECTION_FIELD_EMPTY`。
- `scripts/run-codex-audit-local-e2e.sh` 的本地统计 helper 改为递归收集并按 `review_id` 去重 `codex_reviews`，同时新增 `unique findings count`，按 `finding.id` 去重，避免同一个 finding 在多个结果层级重复计数。

新增/更新测试覆盖：

- builder：item 126，`single_conclusion="符合 /"`、`不符合 /`、`/ /`、`—— /` 且 `remark=""` 时，拆出 `effective_remark="/"`。
- builder：item 126，真实错位形态 `test_result="符合"`、`single_conclusion="/"`、`remark=""` 时，恢复为 `effective_single_conclusion="符合"`、`effective_remark="/"`。
- C08：combined conclusion/remark 为 `符合 /` 时不再产生 remark empty finding。
- C08：combined 值落在 `test_result="符合 /"` 且右侧字段为空时不产生 remark empty finding。
- C08：真实错位形态 `test_result="符合"`、`single_conclusion="/"`、`remark=""` 时不产生 remark empty finding。
- C08：`single_conclusion="符合"`、`remark=""` 且没有 combined slash 证据时仍产生 remark empty finding。
- C08：`standard_requirement` 中包含 `/`，但右侧 `remark` 为空时，仍产生 remark empty finding。
- local e2e artifact：同一 `finding.id` 和 `review_id` 重复出现时，脚本统计 unique count 为 1。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/infrastructure/report/test_inspection_item_group_builder.py tests/rules/report/test_c08_non_empty.py -v` | 通过，`49 passed`；新增测试先红灯失败于旧实现未拆分/恢复 item 126 右侧字段。 |
| `cd backend && python -m pytest tests/rules/report/test_c07_item_conclusion.py tests/rules/report/test_c10_continuation.py tests/rules/report/test_c08_non_empty.py -v` | 通过，`57 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`551 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `bash -n scripts/run-codex-audit-local-e2e.sh` | 通过。 |
| `git diff --check` | 通过。 |

真实样本验收：

- 用户已重新对 `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf` 运行本地 report-check 验收，最新结果为 `C08 count: 0`。
- C08 降噪路径已闭环：T-QUALITY-03 将 C08 从 4894 降到 140；T-QUALITY-03B 修复 `item_no` 污染后降到 2；T-QUALITY-03C 修复 item 126 备注 `/` 占位符后降到 0。
- C08 group-level 降噪闭环完成。
- 统计真实样本结果时应按 `finding.id` 去重，避免递归遍历 top-level `findings` 和 `check_results[].findings` 造成重复计数。

任务状态：

- T-QUALITY-03C 已完成。
- T-QUALITY-05 / T-QUALITY-06 / T-QUALITY-07 未完成。
- T-QUALITY-04 已完成并复验通过。
- 下一推荐任务：T-QUALITY-05：C07 group-level 重构。

## C07 group-level 重构完成记录

完成日期：2026-06-23

本次实现 T-QUALITY-05，将 C07 从规则内自建 physical row 归组切换为消费统一的 `InspectionItemGroup` group-level contract。本阶段不修改 C08/C10，不修改 C04/C05/C06，不修改 `ReportCheckUseCase`、router 或 frontend，不调用真实 Codex，不修改旧项目目录，也不新增 `FindingGroup`。

背景：

- T-QUALITY-02 已提供 `InspectionItemGroupBuilder`。
- T-QUALITY-03/03B/03C 已将真实样本 C08 从 4894 降到 0。
- T-QUALITY-04 已将真实样本 C10 从 130 降到 0。
- C07 此前真实样本为 72 条，业务方向已由 1 条真实 Codex CLI `confirm/high` review 证明可用，但 evidence 和规则判断仍需按 item group 收敛。

本次实现：

- `check_c07_item_conclusion` 现在使用 `build_inspection_item_groups(document.inspection_items)`，逐 `InspectionItemGroup` 推导 expected conclusion。
- Expected conclusion 继续保持原优先级：
  - 任一有效结果包含“不符合” -> `不符合`。
  - 全部有效结果为空、`/` 或 `——` -> `/`。
  - 其他非空有效结果，包括数值、百分比、`IPX0`、`CF 型` 等 -> `符合`。
- Actual conclusion 使用 `group.effective_single_conclusion`，保留 `/` 和 `——` 作为有效占位；当 expected 为 `符合` 而 actual 为 `/` 时仍输出 mismatch。
- 每个 `item_no` 最多输出一条 C07 finding；同一 group 内多 physical rows 作为 evidence 和 metadata，不重复展开为多条主 finding。
- C07 finding metadata 新增 group-level 证据摘要：
  - `expected_conclusion`
  - `actual_conclusion`
  - `effective_test_results`
  - `group_row_count`
  - `pages`
  - `continuation_markers`
  - `source_rows`
  - `result_summary`
  - `reasoning_basis`
  - `suppressed_physical_row_count`
- `CheckResult.metadata` 保留 groups 摘要，并记录 group builder diagnostics 与 ungrouped row count。
- `ReportCodexEvidenceBuilder` 的 C07 evidence 已适配 group-level：`inspection_item` target 现在携带 `inspection_item_group` summary，包括 effective results、expected/actual conclusion、pages、source rows 和 continuation markers；找不到 group 时保留旧单行 fallback。

新增/更新测试覆盖：

- C07：多行 `符合要求` 且实际 `符合` 时通过。
- C07：多行 `符合要求` 且实际 `/` 时只输出 1 条 group-level finding。
- C07：任一行 `不符合要求` 且实际 `符合` 时输出 expected `不符合`。
- C07：全部 `/` / `——` 且实际 `/` 时通过，实际 `符合` 时输出 mismatch。
- C07：跨页 `续 8`、空序号 payload 行归入 active group，不产生重复 finding。
- C07：标准要求正文如“当外壳的分类为 IPX0 时……”不再被当作独立 item_no。
- C07：数值、百分比、`IPX0`、`CF 型` 作为有效非空结果推导 expected `符合`。
- Codex evidence：C07 evidence 包含 `inspection_item_group` summary，不包含整份 PDF 文本。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/rules/report/test_c07_item_conclusion.py -v` | 通过，`17 passed`；新增测试先红灯失败于旧实现缺 group metadata、误把标准要求文本当 item_no。 |
| `cd backend && python -m pytest tests/infrastructure/report/test_inspection_item_group_builder.py tests/rules/report/test_c07_item_conclusion.py tests/rules/report/test_c08_non_empty.py tests/rules/report/test_c10_continuation.py -v` | 通过，`80 passed`。 |
| `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py -v` | 通过，`27 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`553 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `git diff --check` | 通过。 |

任务状态：

- T-QUALITY-05 已完成。
- 用户已对 `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf` 运行本地 report-check 验收。首次使用 8000 端口命中旧后端进程，不作为有效验收；随后使用 `BASE_URL=http://127.0.0.1:8011 BACKEND_PORT=8011` 启动当前工作区代码重跑，结果有效。
- 有效结果文件：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3/runtime/codex_audit_local_e2e/b02deebe-7bc1-431a-8b9f-34e983be2703.result.json`。
- 有效验收当时运行在旧脚本 `MODE=disabled`，`codex_reviews count=0`，未调用真实 Codex；该脚本模式已被 T-CODEX-MANDATORY-01 废弃。
- 有效汇总：
  - `unique_findings_count=61`
  - `C04=35`
  - `C05=7`
  - `C06=6`
  - `C07=12`
  - `C09=1`
  - `C08=0`
  - `C10=0`
- C07 细分：
  - `CONCLUSION_MISMATCH_001=10`
  - `CONCLUSION_MISMATCH_002=2`
  - expected vs actual：`/ -> 符合` 为 10 条，`符合 -> /` 为 2 条。
  - 剩余 item_no：`3, 27, 33, 41, 59, 72, 94, 121, 131, 142, 149, 151`。
  - 每个 item_no 只剩 1 条，说明 group-level 去重已经生效。
- T-QUALITY-05 已达成主目标：C07 从 72 降到 12，且不再按 physical row 重复报；C08 保持 0，C10 保持 0。
- 剩余 C07 已拆为后续 T-QUALITY-05B：
  - item 3：actual conclusion 冲突选择问题。
  - item 59：复杂矩阵表 extractor/列映射问题。
  - 其余 `/ -> 符合`：多数可能是同 group 混合 `——` 与 `符合要求` 时 effective_test_results 聚合不完整，或需要进一步确认 `—— + 符合` 的业务口径。
- T-QUALITY-06 / T-QUALITY-07 未完成。
- 下一推荐任务：T-QUALITY-05B：C07 residual mismatch cleanup。

## T-CODEX-EVIDENCE-02：C07 result token recovery 与 compact evidence

完成日期：2026-06-25

本次执行 T-CODEX-EVIDENCE-02，只处理 C07 result token recovery 与 compact evidence，不处理 Codex usage limit，不新增 `CODEX_USAGE_LIMIT_EXCEEDED`，不调用真实 Codex CLI，不调用 GPT/OpenAI API，不修改旧项目目录，不改 C04/C05/C06，不改 UI。

背景：

- T-CODEX-EVIDENCE-01 后，用户重新跑 full mandatory audit，在 task `57ad5849-df74-4060-bb46-dfb85462e165` 的 C07 item 94 batch 中断。
- workspace 暴露的业务/evidence 问题是：item 94 的 rule context 显示 `expected="/"`、`actual="符合"`、`decision_reason=all_placeholders_or_blank`、`effective_test_results=["——","——"]`，但 page_text 中 12.4.2/12.4.4 附近有“符合要求”。
- 历史 C07 targeted validation 已证明 item 94 应被 Codex refute；因此 item 94 不应作为真实业务错误记录，也不应继续作为普通 C07 `CONCLUSION_MISMATCH_001` ERROR。

本次实现：

- `InspectionItemGroup` 新增 result token recovery contract：
  - `original_effective_test_results`
  - `recovered_result_tokens`
  - `recovered_effective_test_results`
  - `result_token_recovery_applied`
  - `result_token_recovery_diagnostics`
  - `result_token_recovery_confidence`
- `InspectionItemGroupBuilder` 会从 row/source/page excerpt 等上下文中恢复 `符合要求`、`不符合要求`、`符合`、`不符合` 和测量值 token；恢复 provenance 包含 page、row、source excerpt、method 和 confidence。
- `InspectionTableExtractor` 在 inspection item metadata 中保留 `row_text`，供 builder 做 C07 token recovery。
- `check_c07_item_conclusion` 使用 recovered effective results 重新推导 expected conclusion；item 94、33、41、149 这类 page_text/row_text 中已有“符合要求”的 all-placeholder candidate 不再输出普通 ERROR。
- 如果 recovery 只能发现疑似 token 但无法稳定确认来源，C07 输出 WARN `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN`，并设置 `metadata.needs_codex_review=true`，而不是输出普通 ERROR。
- item 151 这类完整 group 确实只有 `——` 且 actual 为 `符合` 的情况仍保留原候选，等待业务口径或 Codex 复核。
- `ReportCodexEvidenceBuilder` 的 C07 evidence 改为 compact：
  - 保留首页符号说明。
  - 保留 item_no、pages、expected/actual、original/recovered effective results、actual conclusion candidates、candidate provenance、continuation markers 和 diagnostics。
  - 保留 compact rows：page、row、sequence_raw、standard_clause、standard_requirement_excerpt、test_result、single_conclusion、remark、recovered_result_token、field_provenance。
  - page text 改为 item 附近 excerpt，不再附整页 page_text。
  - C07 不再重复携带完整 `finding.evidence`、`source_rows` 和 `complete_rows` 双份结构。
- `PromptBuilder` 明确提示 Codex：C07 必须查看 `recovered_result_tokens`、`recovered_effective_test_results`、`compact_rows` 和 item 附近 page_text excerpt；不要要求 Codex 弥补缺失证据。

预期影响：

- item 94 不应再进入普通 C07 ERROR；若真实解析能恢复 12.4.2/12.4.4 的“符合要求”，expected 应变为 `符合`，与 actual `符合` 一致。
- item 33、41、149 等类似“结构化结果全是占位符但原文有符合要求”的 residual C07，也应减少普通 all-placeholder ERROR。
- C07 evidence package 体积应明显小于此前单 target 约 1.4MB 的重复结构；本地 fixture 已验证单 C07 target package 小于 300KB。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/infrastructure/report/test_inspection_item_group_builder.py -v` | 通过，`24 passed`。 |
| `cd backend && python -m pytest tests/rules/report/test_c07_item_conclusion.py -v` | 通过，`21 passed`。 |
| `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py tests/application/test_report_check_usecase.py -v` | 通过，`65 passed`。 |
| `cd backend && python -m pytest tests/api -v` | 通过，`14 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`595 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `git diff --check` | 通过。 |

## T-CODEX-EVIDENCE-03：C07 extraction uncertainty finalization 与 complex matrix 语义

完成日期：2026-06-25

本次执行 T-CODEX-EVIDENCE-03，只修复 C07 finalization 语义和复杂矩阵识别；不处理 Codex usage limit，不调用真实 Codex CLI，不调用 GPT/OpenAI API，不修改旧项目目录，不改 C04/C05/C06，不改 UI。

背景：

- 用户重新运行 C07 targeted validation，task `4380cdc8-ea82-4413-92ce-ba3370ec3f0e`，`included_check_ids=C07`，`audit_scope=targeted`，`full_audit=false`。
- 本轮结果显示 `codex_reviews_count=12`、`confirmed_findings_count=11`、`confirmed_errors_count=1`、`manual_review_required_count=1`、`out_of_scope_findings_count=39`，`final_audit_status=failed`。
- 其中 10 条 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` 是 WARN。Codex `confirm` 的含义是确认“结构化抽取不确定，需要复核”，不是确认业务错误；因此不应计入 `confirmed_findings_count` 或导致最终失败。
- 唯一 confirmed error 是 item 59 的 `CONCLUSION_MISMATCH_002`。历史 targeted validation 已显示 item 59 属于跨 42-45 页复杂矩阵/漏电流表，存在列映射和续表歧义，不应按普通 C07 直接 confirmed。

本次实现：

- `annotate_candidate_findings_with_codex_status` 增加 extraction uncertainty finalization：
  - `finding.code == CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` 且 Codex verdict 为 `confirm` 或 `uncertain` 时，`final_status=manual_review_required`。
  - 保留 `codex_verdict`，并写入 `finalization_reason=CODEX_CONFIRMED_EXTRACTION_UNCERTAINTY`、`review_type=extraction_uncertainty`。
  - 不计入 `confirmed_findings_count` / `confirmed_errors_count`。
- `check_c07_item_conclusion` 增加 complex matrix guard：
  - 对跨多页、row_count 很大、含漏电流/电流/mA/μA/正常状态/单一故障/直流/交流等矩阵特征的 group，不输出普通 `CONCLUSION_MISMATCH_002` ERROR。
  - 改为 WARN `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`，metadata 包含 `complex_matrix_table=true`、`complex_matrix_reason`、`needs_codex_review=true`。
- `ReportCodexEvidenceBuilder` 同步增强 complex matrix 自动识别：
  - 即使 finding metadata 未显式带 `complex_matrix_table`，只要对应 `InspectionItemGroup` 呈现复杂漏电流/矩阵表特征，target metadata 也会标记 `complex_matrix_table=true`，用于 Codex prompt 和 finalization 防御。
- 保留普通 C07 业务错误路径：
  - 简单 item、`effective_test_results=["符合要求"]`、actual `/`、无 conclusion conflict、非复杂矩阵时，Codex confirm 仍会 `final_status=confirmed` 并计入 `confirmed_errors_count`。

预期影响：

- 4380cdc8 中 10 条 confirmed WARN 应在下一轮 targeted validation 中转为 `manual_review_required`，不再计入 confirmed。
- item 59 应转为 complex matrix manual review，不再作为 ordinary C07 confirmed error。
- 如果没有其他真实业务错误，C07 targeted validation 的 `final_audit_status` 应从 `failed` 变为 `needs_manual_review`。

验证命令：

| 命令 | 结果 |
| --- | --- |
| `cd backend && python -m pytest tests/rules/report/test_c07_item_conclusion.py -v` | 通过，`22 passed`。 |
| `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py tests/application/test_report_check_usecase.py -v` | 通过，`69 passed`。 |
| `cd backend && python -m pytest tests/api -v` | 通过，`14 passed`。 |
| `cd backend && python -m pytest tests/ -v` | 通过，`600 passed, 1 skipped`。 |
| `cd frontend && npm run build` | 通过，TypeScript 检查和 Vite build 成功。 |
| `bash -n scripts/run-codex-audit-local-e2e.sh` | 通过。 |
| `git diff --check` | 通过。 |

真实 C07 targeted validation：

- 结果文件：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3/runtime/codex_audit_local_e2e/004f23d9-bd93-4773-91c4-d1c72acf6208.result.json`。
- 本轮设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07`，因此是 C07 targeted validation，不是 full audit。
- task status: `completed`
- `audit_scope=targeted`
- `full_audit=false`
- `final_audit_status=needs_manual_review`
- `codex_reviews_count=12`
- `codex_runtime_failure_count=0`
- `candidate_findings_count=51`
- `candidate_errors_count=33`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=0`
- `manual_review_required_count=12`
- `out_of_scope_findings_count=39`
- `unreviewed_required_findings_count=0`
- legacy deterministic counts: `fail_count=5`、`error_count=33`、`warn_count=18`

结论：

- T-CODEX-EVIDENCE-03 的 C07 targeted validation 通过。
- Extraction uncertainty 不再被归为 confirmed finding。
- C07 当前没有 confirmed final error。
- C07 的 12 条均为 `manual_review_required`，代表抽取/证据仍需复核，不代表报告错误。
- 之后已重新执行 full audit，结果见下方 T-CODEX-EVIDENCE-03B。

## T-CODEX-EVIDENCE-03B：EVIDENCE-03 后 full mandatory audit 真实验收记录

完成日期：2026-06-25

本次只记录用户提供的真实 full mandatory Codex audit 结果，不修改业务代码，不运行真实 Codex CLI。

样本与结果：

- 样本：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf`
- 结果文件：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3/runtime/codex_audit_local_e2e/53bbeec9-998b-4868-9627-00d9cc3b7ab0.result.json`
- 本轮未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`，因此是 full audit，不是 targeted validation。

关键结果：

- task status: `completed`
- `audit_scope=full`
- `full_audit=true`
- `final_audit_status=needs_manual_review`
- `candidate_findings_count=51`
- `candidate_errors_count=33`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=11`
- `manual_review_required_count=40`
- `out_of_scope_findings_count=0`
- `unreviewed_required_findings_count=0`
- `codex_reviews_count=57`
- `codex_runtime_failure_count=0`

按 final_status：

| check_id | manual_review_required | refuted |
| --- | ---: | ---: |
| C04 | 28 | 7 |
| C05 | 0 | 2 |
| C06 | 0 | 1 |
| C07 | 12 | 0 |
| C09 | 0 | 1 |

结论：

- Full mandatory Codex audit 运行通过。
- 当前没有 confirmed final error。
- 当前审核状态为 `needs_manual_review`。
- 剩余 40 条不是确认错误，而是待复核：C04 标签字段证据不足 28 条，C07 检验项目结构化抽取不确定 12 条。
- C05/C06/C09 当前候选均已被 Codex refute。
- 下一步应做 evidence enhancement，而不是继续改 finalization。

## T-CODEX-EVIDENCE-04：C04 label image crop / matched OCR evidence 增强

完成日期：2026-06-25

本次只增强 C04 evidence package、prompt guidance 和对应测试，不运行真实 Codex CLI，不调用 GPT/OpenAI API，不修改旧项目目录，不修改 router/frontend/UI，不处理 C07。

背景与目标：

- T-CODEX-EVIDENCE-03B full audit 后仍有 40 条 `manual_review_required`，其中 C04 标签字段证据不足 28 条。
- 这些 C04 项不是 confirmed error，而是样品描述字段存在，但缺 matched label crop/OCR/structured fields，Codex 不能核验标签本体字段是否存在或一致。
- 本任务目标是让 C04 target 明确分层表达 caption、label image/crop、matched OCR text、structured fields 和是否足以验证标签内容。

实现记录：

- C04 evidence 现在输出 `label_caption_candidate`、`matched_label_caption`、`label_page_number`、`label_image_ref`、`label_page_image_ref`、`label_crop_ref`、`matched_label_text`、`matched_label_fields`、`matched_label_field_confidence`、`matched_label_ocr_source`、`unmatched_label_ocr_candidates` 和 `label_matching_diagnostics`。
- caption matching 增强为结合 component name、normalized name、型号规格、括号/线缆长度等信息；已覆盖真实样本中的主机、推车、触摸屏、ECG 主线缆、不可透射线 ECG 导联线、光接收器、电源电缆、等电位线缆、30m 触摸屏连接线缆和脉冲导管连接电缆 caption。
- 有 caption/bbox 时可生成 `label_crop_ref`；没有 bbox 时保留 `label_page_image_ref=report-page:{page}` 并记录 `crop_unavailable_reason=caption_bbox_missing`。
- 有 matched OCR text 或 structured fields 时 `evidence_can_verify_label_content=true`；只有 caption、page ref、empty OCR 或 unrelated OCR 时保持 `false`，并把不相关 OCR 记录为 `unmatched_label_ocr_candidates`。
- PromptBuilder 已明确：caption 能证明标签样张存在，但不能证明字段完整；只有 matched label OCR 属于当前 component 时才可判断字段缺失或不一致；无 matched OCR/crop/structured fields 时应 `uncertain`。
- finalization 继续防御：C04 `SAMPLE_FIELD_MISSING_IN_LABEL` 在 `evidence_can_verify_label_content=false` 时，即使 Codex 返回 `confirm`，也进入 `manual_review_required` 并记录 `CODEX_CONFIRMED_UNVERIFIABLE_LABEL_CONTENT`；matched fields 一致时可由 Codex `refute`，matched fields 缺失/冲突且证据可验证时可由 Codex `confirm`。

验证结果：

- `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py tests/application/test_report_check_usecase.py -v`：通过，`83 passed`。
- `cd backend && python -m pytest tests/infrastructure/codex/test_prompt_builder.py -v`：通过，`17 passed`。
- `cd backend && python -m pytest tests/api -v`：通过，`14 passed`。
- `cd backend && python -m pytest tests/ -v`：通过，`614 passed, 1 skipped`。
- `cd frontend && npm run build`：通过。

下一步需要用户显式运行 C04 targeted validation，验证 28 条 C04 `manual_review_required` 是否因 matched crop/OCR/fields evidence 转为 `refute` 或更明确的人工复核：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C04 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

## T-CODEX-EVIDENCE-04B：C04 matched label OCR 语义和 caption selector 修正

完成日期：2026-06-26

用户已在 T-CODEX-EVIDENCE-04 后运行 C04 targeted validation，并由该轮结果暴露 04B 需要修复的 metadata 语义问题：

- task_id: `8949ca23-07b6-4f7c-b39c-b428d83daa17`
- `audit_scope=targeted`
- `included_check_ids=C04`
- task status: `completed`
- `codex_reviews_count=35`
- `codex_runtime_failure_count=0`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=7`
- `manual_review_required_count=28`
- `out_of_scope_findings_count=16`

extract summary：

- C04 findings: `35`
- `SAMPLE_FIELD_MISSING_IN_LABEL=28`
- `SAMPLE_COMPONENT_LABEL_NOT_FOUND=7`
- `manual_review_required=28`
- `refuted=7`
- `confirmed=0`
- `has_matching_label_caption_count=33`
- `has_matched_label_crop_count=0`
- `has_matched_label_ocr_count=28`
- `has_matched_structured_fields_count=0`
- `can_verify_label_content_count=28`
- `unused_component_count=5`

结论与问题：

- C04 targeted validation 运行通过，当前 C04 没有 confirmed final error。
- 28 条 `manual_review_required` 主要因为没有真正 label crop/OCR/structured fields。
- 发现 metadata 假阳性：`matched_label_text` 实际包含“检验报告照片页 / 照片和说明 / №5... / №6...”这类照片页文本，只能证明 caption/page text 存在，不能证明标签本体字段完整。
- 因此 `evidence_has_matched_label_ocr=true` 和 `evidence_can_verify_label_content=true` 不应由照片页 page text 触发。
- 另发现 sample-row-14 `触摸屏连接线缆（30m）（可选）` 的正确 candidate 为 `№22 触摸屏连接线缆（30m）（可选） 中文标签样张`，但 selector 误选了 `№8 心脏脉冲电场消融仪-触摸屏 中文标签样张`。

04B 修正：

- 新增语义字段：`matched_label_page_text` 表示照片页 OCR / PDF page text / caption 周边文本；`matched_label_caption_text` 表示 caption 文本；`matched_label_ocr_text` 表示真正标签本体 OCR；`matched_label_fields` 表示结构化标签字段。
- `matched_label_text` 兼容保留，但现在只等同于 `matched_label_ocr_text`，不再承载照片页文本。
- `pdf_text_label_page` 等来源的 raw blocks 进入 `matched_label_page_text`，不会让 `evidence_has_matched_label_ocr=true`。
- `evidence_can_verify_label_content=true` 仅在 `matched_label_ocr_text` 或 `matched_label_fields` 可用时成立；只有 page text/caption text、无 crop、无 structured fields 时为 false。
- caption selector 改为评分排序：完整 subject/name 优先，型号命中加权，`30m`、`可选`、`连接线缆` 等特异 token 加权；分差不足时不设置 `matched_label_caption`，记录 `LABEL_CAPTION_MATCH_AMBIGUOUS`。
- sample-row-14 fixture 已固定：`№22 触摸屏连接线缆（30m）（可选） 中文标签样张` 优先于 `№8 ... 触摸屏 中文标签样张`。

04B 修复后，用户已重新运行 C04 targeted validation：

- result_file: `runtime/codex_audit_local_e2e/4ec18d39-7dab-4478-b6c0-d6bc464fd2e7.result.json`
- task_id: `4ec18d39-7dab-4478-b6c0-d6bc464fd2e7`
- task status: `completed`
- `audit_scope=targeted`
- `included_check_ids=C04`
- `final_audit_status=needs_manual_review`
- `codex_reviews_count=35`
- `codex_runtime_failure_count=0`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=7`
- `manual_review_required_count=28`
- `out_of_scope_findings_count=16`
- `unreviewed_required_findings_count=0`

C04 extract 关键结果：

- C04 findings: `35`
- `SAMPLE_FIELD_MISSING_IN_LABEL=28`
- `SAMPLE_COMPONENT_LABEL_NOT_FOUND=7`
- `manual_review_required=28`
- `refuted=7`
- `confirmed=0`
- `has_matching_label_caption_count=35`
- `has_matched_label_image_count=31`
- `has_matched_label_crop_count=0`
- `has_matched_label_ocr_count=0`
- `has_matched_structured_fields_count=0`
- `can_verify_label_content_count=0`
- `unused_component_count=5`

04B 关键修复验证：

- `evidence_has_matched_label_ocr_count` 从旧的 `28` 降为 `0`，照片页/page text 不再被统计为 matched label OCR。
- `evidence_can_verify_label_content_count` 从旧的 `28` 降为 `0`，没有本体 OCR 或 structured fields 时不会被标为可验证标签内容。
- `has_matched_structured_fields_count=0`。
- `has_matched_label_crop_count=0`。
- sample-row-14 已正确匹配 `№22 触摸屏连接线缆（30m）（可选）中文标签样张`，不再误匹配 `№8 触摸屏`。

04B 验收结论：

- T-CODEX-EVIDENCE-04B 验收通过。
- C04 当前没有 confirmed final error。
- 28 条 `manual_review_required` 仍代表缺 matched label crop/OCR/structured fields，需要后续真实标签 crop/OCR evidence enhancement，不是确认报告错误。
- 后续应进入 T-CODEX-EVIDENCE-05：label crop / OCR / VLM evidence。
- 后续展示问题：`c04_extract` 中 `component_name` / `sample_description_row` 仍不稳定；前端展示或导出应补标准 metadata，例如 `component_id`、`component_name`、`sample_field_key`、`sample_field_value`。

## T-CODEX-EVIDENCE-05：C04 中文标签样张视觉审核链路

完成日期：2026-06-26

本阶段实现 C04 label caption 到 Codex CLI image input 的受控视觉证据链，未运行真实 Codex CLI。

实现内容：

- `ReportCheckUseCase` 将上传后保存在当前 runtime 的 PDF 路径传给 `ReportCodexEvidenceBuilder`；不读取旧项目目录。
- `ReportCodexEvidenceBuilder` 在 C04/C06 target 中保留 `label_caption_text`、`label_page_number`、`label_image_ref`、`label_crop_ref`、`sample_description_row` 和 `expected_label_fields`。
- 当存在 matched label caption 且有 source PDF 时，builder 为标签页或标签 crop 生成 workspace 相对目标路径，例如 `items/<finding-id>-label-page.png` 或 `items/<finding-id>-label-crop.png`，并设置 `evidence_has_visual_label_input=true`。
- `EvidencePackageWriter` 在受控 `runtime/codex_audit/{task_id}/{package_id}/input/items/` 下渲染 PNG，并在写入 `evidence_package.json` 前移除内存中的 `source_pdf_path`，避免暴露本机路径。
- `CodexAuditService` 从 manifest 收集 workspace 内 image paths，传给 runner。
- `FakeCodexRunner` 记录 `last_image_paths`，用于测试确认 fake runner 收到 image input。
- `CodexCliRunner` 校验 image input 必须在 evidence workspace 内且为图片文件，并以相对路径传给 `codex exec --image items/...png`。
- Prompt 明确要求 Codex 视觉读取标签图片中的部件名称、规格型号、序列号/批号、生产日期等字段。
- `codex_review_output.schema.json` 支持 review metadata 中的 `observed_label_fields`、`field_comparisons` 和 `visual_evidence_quality`。
- finalization 会把 Codex 视觉 metadata 复制到 finding metadata：`codex_observed_label_fields`、`codex_field_comparisons`、`codex_visual_evidence_quality`。
- 如果 Codex 在 `visual_evidence_quality=unreadable` 或 `wrong_crop` 时仍返回 `confirm`，finalization 防御性降级为 `manual_review_required`，诊断为 `CODEX_CONFIRMED_UNREADABLE_LABEL_IMAGE`。

已验证的行为：

- 有 source PDF 和 matched label caption 时，C04 target 生成 workspace 内 PNG 相对路径，并将 visual input 标为可由 Codex 复核。
- 没有 source PDF/crop/image 时，仍保持 `manual_review_required`，不会因为 caption/page text 被 confirm。
- fake Codex review 若视觉字段与样品描述一致，可 `refute` 原 `SAMPLE_FIELD_MISSING_IN_LABEL` candidate。
- fake Codex review 若视觉证据清晰且确认字段缺失，可 `confirm`。
- fake Codex review 若图片不可读，则进入 `manual_review_required`。
- output schema 和 parser 均保留视觉字段 metadata。

真实 C04 targeted visual validation：

- task_id：`c1f421db-4757-4041-8b19-c88b8835a941`
- `audit_scope=targeted`
- `included_check_ids=C04`
- `final_audit_status=passed`
- `C04 findings=35`
- `C04 reviews=35`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `manual_review_required_count=0`
- `refuted_findings_count=35`
- `codex_runtime_failure_count=0`
- `failed_or_skipped_reviews_count=0`
- `unreviewed_required_findings_count=0`

验收结论：

- Codex CLI visual label review 已实际生效。
- C04 的 28 条 `SAMPLE_FIELD_MISSING_IN_LABEL` 均被视觉证据 refute。
- C04 的 7 条 `SAMPLE_COMPONENT_LABEL_NOT_FOUND` 均被视觉证据或 not_applicable 规则 refute。
- 当前 C04 无 confirmed error、无 manual review。

## T-CODEX-EVIDENCE-05A：C04 visual review strict schema 修复

完成日期：2026-06-26

用户运行 C04 visual audit 时，任务 `7b20f4a4-e99e-42c3-9151-3d00b16c259c` 在 Codex CLI 调用前被 OpenAI structured output schema 拒绝：

- task status 为 `error`，current_step 为 `error`。
- 当前错误码表现为 `CODEX_EXIT_NONZERO`，stderr 中包含 `invalid_json_schema`。
- 关键错误为 `observed_label_fields` 的 `required` 未包含 `batch_or_serial`。

本次结论：

- 该失败是 `codex_review_output.schema.json` strict schema 不合法，不是 C04 业务错误，也不是视觉证据链本身的审核结论。
- C04 visual evidence 已进入 target metadata，并且 image input 链路已由 `CodexAuditService` 传给 runner。
- `CodexCliRunner` 已使用 `codex exec --image items/...png` 传递 workspace 内图片相对路径；本任务未发现需要单独做 image input wiring 的 05B。

本次修复：

- `metadata.required` 覆盖 `observed_label_fields`、`field_comparisons`、`visual_evidence_quality`。
- `observed_label_fields.required` 覆盖 `component_name`、`model`、`serial_number`、`batch_or_serial`、`production_date`、`expiration_date`。
- 每个视觉字段允许 `string` 或 `null`；`field_comparisons` 允许空数组；`visual_evidence_quality` 允许 `"unknown"` 或 `null`。
- 新增 strict schema contract 测试，递归检查所有带 `properties` 的 object 都有完整 `required`。

下一步应重新运行 C04 targeted validation，确认真实 Codex CLI 不再因 `invalid_json_schema` 退出。

## T-CODEX-EVIDENCE-05A 后 C04 targeted visual audit 尝试记录

记录日期：2026-06-26

本轮是 C04 targeted validation，设置了 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C04`。本次只记录用户提供的真实运行结果，不重新运行真实 Codex CLI。

输入与失败包：

- extract package：`runtime/codex_audit_local_e2e/extract_runs/20260626-225213-C04.tar.gz`
- task 未 completed，`run_exit=1`
- 当前错误码：`CODEX_EXIT_NONZERO`
- failed workspace：`backend/runtime/codex_audit/0ece4dd1-c2db-48b1-8cfa-efd21ea01a80/codex-report-0ece4dd1-c2db-48b1-8cfa-efd21ea01a80-C04-batch-6/input`
- `codex_review_output.schema.json` size：6958 bytes
- `evidence_package.json` size：79034 bytes
- `prompt.md` size：27900 bytes
- stderr tail：`ERROR: You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at 11:40 PM.`

结论：

- 本轮失败不是报告业务错误。
- 本轮失败不是 `invalid_json_schema`；说明 T-CODEX-EVIDENCE-05A 的 strict schema 修复至少没有在本轮复现 schema 拒绝。
- C04 visual evidence 已进入 target metadata，包括 `label_page_image_ref` / `label_visual_input_ref`。
- 由于 Codex usage limit，本轮没有生成最终 result，不能判断 C04 `manual_review_required` 是否下降。
- 后续需要在额度恢复后重新跑 C04 targeted validation。
- 脚本改进点：error extract 中 task_id 为 null 时，应从 `workspace_dir` 反推；该点已作为 T-CODEX-RUNTIME-01B 的 local E2E error summary 解析问题记录。

## T-CODEX-EVIDENCE-05B：EVIDENCE-05 后 full mandatory audit 真实验收记录

记录日期：2026-06-28

本次只记录用户提供的真实 full mandatory Codex audit 验收结果；不修改 backend/frontend/router，不运行真实 Codex CLI，不修改旧项目目录。

结果文件：

- `runtime/codex_audit_local_e2e/1958c184-567f-4c56-aaac-4a8c45913d1c.result.json`

运行口径：

- 未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`。
- `audit_scope=full`
- `full_audit=true`
- `included_check_ids=[]`

关键结果：

- `task_id=1958c184-567f-4c56-aaac-4a8c45913d1c`
- `final_audit_status=needs_manual_review`
- `unique_findings_count=51`
- `codex_reviews_count=57`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=39`
- `manual_review_required_count=12`
- `out_of_scope_findings_count=0`
- `codex_runtime_failure_count=0`
- `unreviewed_required_findings_count=0`

按 check_id：

| check_id | findings | final status |
| --- | ---: | --- |
| C04 | 35 | 全部 `refuted` |
| C05 | 2 | 全部 `refuted` |
| C06 | 1 | `refuted` |
| C07 | 12 | 全部 `manual_review_required` |
| C09 | 1 | `refuted` |

验收结论：

- Full mandatory Codex audit 运行通过。
- 当前没有 confirmed final error。
- C04 visual label audit 已在 full audit 中生效，35 条 C04 candidate 全部被 `refuted`。
- C05/C06/C09 candidate 也已被 `refuted`。
- 当前唯一剩余的是 C07 的 12 条 `manual_review_required`。
- 下一步不应继续改 C04 或 finalization，应进入 C07 table visual evidence / row crop review。

## T-CODEX-EVIDENCE-06A：C07 table visual geometry provenance

完成日期：2026-06-28

本次只执行 C07 table visual evidence 计划中的底层几何准备：Task 1 `Preserve Table And Cell Geometry` 和 Task 2 `Attach C07 Visual Geometry To Inspection Items`。本阶段不生成 C07 image evidence，不接入 `CodexAuditService`，不修改 prompt/schema/finalization，不运行真实 Codex CLI，不调用 GPT/OpenAI API，不修改旧项目目录，也不修改 frontend/router。

实现内容：

- `PyMuPDFParser` 在 PyMuPDF table 暴露 `cells` 时，将单元格坐标保存为 `PdfTable.metadata["cell_bboxes"]`，结构为 `list[row][col] = null | [x0, y0, x1, y1]`。
- `InspectionTableExtractor` 在 inspection table 同时具备 `cell_bboxes` 和字段列映射时，为 `InspectionItem.metadata["visual_geometry"]` 写入：
  - `table_id`
  - `table_bbox`
  - `row_bbox`
  - `field_bboxes`，包含 `test_result`、`conclusion`、`remark` 等字段 bbox。
- 没有 `cells` 或没有 `cell_bboxes` 时保持原抽取行为：不写 `visual_geometry`，不改变 `InspectionItem` 字段值，不改变 C07/C08/C10 规则输出。

本阶段边界：

- 尚未生成 C07 page/table/row/field crop 图片。
- 尚未接入 Codex CLI image input。
- 尚未修改 C07 prompt、schema 或 finalization。

验证：

- 已按 TDD 先观察新增目标测试失败，再实现最小代码。
- `cd backend && python -m pytest tests/infrastructure/pdf/test_pymupdf_parser.py::test_pymupdf_table_preserves_cell_bboxes -v` 通过。
- `cd backend && python -m pytest tests/infrastructure/report/test_inspection_table_extractor.py::test_inspection_items_include_visual_geometry_for_c07_crops tests/infrastructure/report/test_inspection_table_extractor.py::test_inspection_items_without_cell_bboxes_keep_existing_behavior -v` 通过。
- `cd backend && python -m pytest tests/infrastructure/pdf/test_pymupdf_parser.py tests/infrastructure/report/test_inspection_table_extractor.py -v` 通过。
- `cd backend && python -m pytest tests/ -v` 通过，`636 passed, 1 skipped`。
- `git diff --check` 通过。

后续任务 T-CODEX-EVIDENCE-06B 已继续实现 C07 visual evidence item 生成。

## T-CODEX-EVIDENCE-06B：C07VisualEvidenceBuilder 与图像 evidence refs

完成日期：2026-06-28

本次只执行 C07 table visual evidence 计划中的 Task 3，并做最小 `ReportCodexEvidenceBuilder` wiring。未修改 prompt/schema/finalization，未调用真实 Codex CLI，未调用 GPT/OpenAI API，未修改旧项目目录，也未修改 frontend/router。

实现内容：

- 新增 `backend/app/application/c07_visual_evidence.py`：
  - 输入 C07 finding、`InspectionItemGroup`、`source_pdf_path` 和 safe id 函数。
  - 输出 C07 page/table/item group/result/conclusion/remark 的 `EvidenceItem(source_type=IMAGE)`。
  - 只构建 evidence item 和 metadata，不读取 PDF、不写 runtime 文件、不调用 Codex。
- `ReportCodexEvidenceBuilder` 在 C07 target 中最小接入 C07 visual evidence：
  - `target.metadata["c07_visual_evidence"]`
  - `target.metadata["evidence_has_c07_visual_input"]`
  - C07 visual image item refs 进入 target `evidence_refs`。
- 有完整 `visual_geometry` 时，输出：
  - page image
  - table crop
  - item group crop
  - result column crop
  - conclusion column crop
  - remark column crop
- 没有 bbox 时，仍输出 page image，并标记 `visual_review_mode=page_only` 以及 `table_bbox_missing`、`row_bbox_missing`、`field_bbox_missing`。
- `source_pdf_path` 缺失时不生成 image items，target metadata 记录 `has_visual_input=false` 和 `source_pdf_path_missing`。
- item 59 或复杂矩阵标记会保留 `visual_review_mode=complex_matrix_table`，并记录 `expected_codex_when_complex_matrix=uncertain_or_specialized_matrix_review`，但不改变 C07 finalization 语义。
- C07 image item 的 `file_path` 保持 workspace-local relative path，target metadata 和 allowed evidence refs 不暴露 `/Users/...` 绝对路径。

边界：

- 本阶段没有实际生成 PNG；图片由既有 `EvidencePackageWriter` 在后续写 evidence workspace 时 materialize。
- 本阶段没有新增 Codex prompt guidance，因此真实 Codex 是否使用这些 C07 图片 evidence 需要后续任务验证。
- 本阶段没有改变 C07 deterministic finding、final status 或 manual review 计数。

验证：

- 已按 TDD 先观察 C07 visual evidence builder 目标测试失败，再实现最小代码。
- `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py::test_c07_visual_evidence_generates_page_table_group_and_column_images tests/application/test_report_codex_evidence_builder.py::test_c07_visual_evidence_without_bbox_uses_page_image_only -v` 通过。
- `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py::test_c07_visual_evidence_without_source_pdf_records_missing_reason tests/application/test_report_codex_evidence_builder.py::test_c07_visual_evidence_complex_matrix_uses_complex_mode tests/application/test_report_codex_evidence_builder.py::test_c07_visual_evidence_refs_are_workspace_relative_and_do_not_leak_user_paths -v` 通过。
- `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py -v` 通过，`65 passed`。
- `cd backend && python -m pytest tests/application/test_report_check_usecase.py -v` 通过，`30 passed`。
- `cd backend && python -m pytest tests/infrastructure/audit/test_evidence_package_writer.py -v` 通过，`9 passed`。
- `cd backend && python -m pytest tests/ -v` 通过，`641 passed, 1 skipped`。
- `git diff --check` 通过。

后续任务 T-CODEX-EVIDENCE-06C 已继续完成 C07 image evidence materialization、image-path handoff 和 prompt 指令验证。

## T-CODEX-EVIDENCE-06C：C07 image materialization / prompt / handoff 验证

完成日期：2026-06-28

本次只执行 C07 table visual evidence 计划中的 image materialization、PromptBuilder visual instructions 和 Codex CLI image-path handoff 验证。未运行真实 Codex CLI，未运行 local E2E，未调用 GPT/OpenAI API，未修改 output schema / finalization / C07 deterministic rule，也未修改旧项目目录、frontend 或 router。

实现内容：

- `EvidencePackageWriter` 已能 materialize C07 image evidence items：
  - `EvidenceItem.source_type=IMAGE`
  - `metadata.codex_image_input=true`
  - `metadata.render_page_number` 指定页码
  - 无 bbox 时渲染整页 page image
  - `metadata.render_bbox` 或 `metadata.crop_bbox` 存在时裁剪对应区域
  - 输出到 evidence workspace 的 `items/*.png`
- `EvidencePackageWriter` 对无法 materialize 的 image item 写入可审计 diagnostics：
  - 无 `source_pdf_path` 时记录 `SOURCE_PDF_MISSING`
  - 无效页码记录 `INVALID_IMAGE_PAGE_NUMBER`
  - 无效 bbox 记录 `INVALID_IMAGE_BBOX`
  - diagnostics 同步写入 `manifest.metadata["image_materialization_diagnostics"]` 和 item metadata。
- `CodexAuditService` 已验证可从 manifest 的 relative `item_file_paths` 收集 C07 PNG，并将 workspace-local `image_paths` 传给 runner。
- `CodexCliRunner` 已验证多张 C07 PNG 会通过多个 `--image` 参数传给 `codex exec`，并继续拒绝缺失图片或越界图片路径。
- `PromptBuilder` 新增 C07 visual target-specific instructions：
  - 说明 C07 deterministic finding 是 candidate。
  - 要求同时使用 textual evidence 和 C07 visual images。
  - 明确 page/table/item group/result column/conclusion column/remark column images 的用途。
  - 要求结合首页符号说明：“——”表示此项不适用，“/”表示此项空白。
  - 要求视觉核对 item_no 的检验结果、单项结论、备注、跨页续表行和可能遗漏的 result token。
  - 对 all-placeholder 反驳、证据不清和 complex matrix 均给出 safe verdict 指引。

边界：

- 尚未运行真实 C07 targeted visual audit。
- 尚未运行 full audit。
- 尚未改变 C07 finalization 语义；visual uncertainty 仍不应被当作 confirmed error。
- 尚未修改 frontend/type contract。

验证：

- 已按 TDD 先观察新增 06C 目标测试失败，再实现最小代码。
- 新增目标测试组合通过：writer C07 page/crop/diagnostics、service C07 image paths、runner multiple/missing images、prompt C07 visual instructions 和 C04 非污染。
- `cd backend && python -m pytest tests/infrastructure/audit/test_evidence_package_writer.py -v` 通过，`13 passed`。
- `cd backend && python -m pytest tests/application/test_codex_audit_service.py -v` 通过，`12 passed`。
- `cd backend && python -m pytest tests/infrastructure/codex/test_codex_cli_runner.py tests/infrastructure/codex/test_prompt_builder.py -v` 通过，`36 passed`。
- `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py tests/application/test_report_check_usecase.py -v` 通过，`95 passed`。
- `cd backend && python -m pytest tests/ -v` 通过，`650 passed, 1 skipped`。

下一推荐任务：T-CODEX-EVIDENCE-06D，只跑 C07 targeted visual audit 真实验收，观察 C07 `manual_review_required` 是否从 12 下降、`refute` 是否增加、`confirmed_errors_count` 是否仍为 0、`codex_runtime_failure_count` 是否为 0。

## T-CODEX-EVIDENCE-06D：C07 targeted visual audit 真实验收

完成日期：2026-06-28

本次只记录用户显式运行的 C07 targeted visual audit 真实验收结果。未修改 backend/frontend/router，未运行新的 Codex CLI 任务，未修改旧项目目录。

结果文件：

- `runtime/codex_audit_local_e2e/2e7bbb93-3e7b-4477-8a5f-b1b25487fef0.result.json`
- 导出包：`runtime/codex_audit_local_e2e/c07_visual_runs/20260628-122940.tar.gz`

运行口径：

- `task_id=2e7bbb93-3e7b-4477-8a5f-b1b25487fef0`
- `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07`
- `audit_scope=targeted`
- `included_check_ids=["C07"]`
- `full_audit=false`

关键结果：

- `final_audit_status=needs_manual_review`
- `c07_findings_count=12`
- `c07_reviews_count=12`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=11`
- `manual_review_required_count=1`
- `codex_runtime_failure_count=0`
- `unreviewed_required_findings_count=0`

C07 结果：

- Codex visual evidence 已 refute item `3`、`27`、`33`、`41`、`72`、`94`、`121`、`131`、`142`、`149`、`151`。
- 唯一剩余 manual review 是 item `59`，`code=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`，`visual_review_mode=complex_matrix_table`。
- 当前 C07 没有 confirmed final error。
- 真实 `codex exec` 已携带 `--image items/...` 参数，包含 C07 page/table/item-group/result/conclusion/remark 图像输入；item `94` 使用 p72/p73 跨页多张图片。

验收结论：

- T-CODEX-EVIDENCE-06D 验收通过。
- C07 visual evidence 链路有效，C07 `manual_review_required` 从 12 降到 1，`refuted_findings_count` 增加到 11。
- 06A/06B/06C 的几何 provenance、visual evidence planning、PNG materialization 和 `--image` handoff 已被真实 targeted audit 验证。
- item `59` complex matrix 按预期保留为 manual/specialized matrix review。

下一推荐任务：规划 item `59` complex matrix 专门审核链路，或在记录完成后再做 full mandatory audit 回归验收。

## T-CODEX-EVIDENCE-06 full mandatory audit 复验记录

完成日期：2026-06-28

本次记录用户显式运行的 T-CODEX-EVIDENCE-06 后 full mandatory audit 复验结果。该轮没有设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`，因此是 full audit，不是 targeted validation。本次文档更新不修改 backend/frontend/router，不运行新的 Codex CLI，不修改旧项目目录。

结果文件：

- `runtime/codex_audit_local_e2e/8e23d5bc-64f5-43c1-a0c5-2e02597840f6.result.json`
- 摘要包：`runtime/codex_audit_local_e2e/full_audit_extract_runs/20260628-133403.summary.tar.gz`

运行口径：

- `task_id=8e23d5bc-64f5-43c1-a0c5-2e02597840f6`
- `audit_scope=full`
- `full_audit=true`
- `included_check_ids=[]`

关键结果：

- `final_audit_status=needs_manual_review`
- `unique_findings_count=51`
- `codex_reviews_count=57`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=50`
- `manual_review_required_count=1`
- `out_of_scope_findings_count=0`
- `codex_runtime_failure_count=0`
- `unreviewed_required_findings_count=0`

复验结论：

- C04/C05/C06/C09 全部被 Codex refute。
- C07 12 条中 11 条被 refute。
- 当前全量审核仅剩 C07 item `33` 待人工复核，code 为 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN`。
- item `33` 的人工复核原因：视觉表格显示 item 33 首行检验结果为“——”，其下续行“分类是 IPX0 或 IP0X 的 ME 设备不需要标记。”对应检验结果列可见“符合要求”；结构化结果仅保留“——”确有遗漏，需人工/视觉复核后判断，且单项结论“符合”与可见非空合格结果一致。
- 当前没有 confirmed final error。
- T-CODEX-EVIDENCE-06 full audit 复验通过。

当时下一推荐任务为 T-CODEX-EVIDENCE-06E：item 33 residual manual review closeout。该任务已在下一节完成代码侧 closeout，并已通过真实 C07 targeted validation；当前下一步以 06E 结论中的 full mandatory audit 复验为准。

## T-CODEX-EVIDENCE-06E：C07 item 33 residual manual review closeout

完成日期：2026-06-28

本次修复 C07 item `33` 在 targeted C07 visual audit 中被 refute、但 full mandatory audit 中仍为 `manual_review_required` 的稳定性问题。本任务不修改 finalization，不硬编码 item `33`，不改变 C07 deterministic rule 的业务语义，不运行真实 Codex CLI，不修改旧项目目录。

诊断工具：

- 新增 `scripts/compare-codex-c07-item-evidence.py`，可对比两个 Codex audit run 中同一 C07 item 的 target、finding、allowed refs、`c07_visual_evidence`、materialized image files、prompt flags 和 Codex review verdict/reasoning。
- 该工具输出 JSON，路径使用 workspace-relative 或脱敏形式，不输出 `/Users/...` 绝对路径。

item `33` targeted vs full 诊断：

- 对比对象：
  - targeted C07 visual audit：`2e7bbb93-3e7b-4477-8a5f-b1b25487fef0`
  - full mandatory audit：`8e23d5bc-64f5-43c1-a0c5-2e02597840f6`
- 两轮均为 C07 batch `2`。
- `finding_code` 均为 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN`。
- `allowed_evidence_refs` 归一化后一致。
- `target.metadata.c07_visual_evidence` 归一化后一致。
- materialized image files 归一化后一致，均包含 page image 和 table image。
- 旧 prompt 均缺少 extraction-uncertain 的明确 refute 条件。
- 唯一关键差异是 Codex verdict：targeted 为 `refute`，full 为 `confirm`；full 的 reasoning 仍承认视觉表格可见续行“符合要求”且单项结论“符合”一致，因此属于 prompt 语义稳定性问题，不是证据丢失或 finalization 问题。

本次修复：

- `C07VisualEvidenceBuilder` 在构造 item group crop 时，如果续行缺 `row_bbox` 但存在字段 bbox，会用字段 bbox union 作为 row fallback，再与已有 row bbox 取 union，避免 item group crop 只覆盖首行。
- `PromptBuilder` 的 C07 visual instructions 明确 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` 语义：
  - 视觉证据足以判断结论合理时应 `refute`。
  - 不能仅因结构化抽取遗漏存在就 `confirm/manual`。
  - 同一 item group 续行中的“符合要求”应作为有效检验结果。
  - 只有图像无法稳定读取对应行/列，或无法确认 result token 属于该 group 时才 `uncertain`。
- 新增 targeted/full consistency 测试，证明同一 C07 item 在 targeted 与 full builder mode 下生成相同的 C07 visual metadata 和 image refs。

当前结论：

- item `33` 不是 confirmed final error。
- T-CODEX-EVIDENCE-06E 的 C07 targeted validation 已由用户真实运行通过：
  - 结果文件：`runtime/codex_audit_local_e2e/a39b2841-e44d-4efd-a004-ae3147a2c1d6.result.json`
  - 摘要文件：`runtime/codex_audit_local_e2e/c07_06e_runs/20260628-182451/paste_to_chatgpt.md`
  - `task_id=a39b2841-e44d-4efd-a004-ae3147a2c1d6`
  - `audit_scope=targeted`
  - `included_check_ids=["C07"]`
  - `final_audit_status=passed`
  - `c07_findings_count=12`
  - `c07_reviews_count=12`
  - `confirmed_findings_count=0`
  - `confirmed_errors_count=0`
  - `manual_review_required_count=0`
  - `refuted_findings_count=12`
  - `codex_runtime_failure_count=0`
  - `unreviewed_required_findings_count=0`
- 全部 C07 item 均已 refuted：`3, 27, 33, 41, 59, 72, 94, 121, 131, 142, 149, 151`。
- item `33` residual manual review 已收口；当前 C07 targeted audit 无 confirmed error、无 manual review、无 runtime failure。

T-CODEX-EVIDENCE-06E 后 full mandatory audit 复验已由用户真实运行：

- 结果文件：`runtime/codex_audit_local_e2e/bf36101c-71a4-4f69-9df9-907ced1000cb.result.json`
- `task_id=bf36101c-71a4-4f69-9df9-907ced1000cb`
- `audit_scope=full`
- `full_audit=true`
- `final_audit_status=needs_manual_review`
- `codex_reviews_count=57`
- `candidate_findings_count=51`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=50`
- `manual_review_required_count=1`
- `codex_runtime_failure_count=0`
- `unreviewed_required_findings_count=0`

唯一剩余 manual review：

- `check_id=C07`
- `code=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`
- `severity=warn`
- `item_no=59`
- `codex_verdict=uncertain`
- `confidence=medium`
- reasoning：视觉证据显示序号 `59` 为 8.7 漏电流多页复杂矩阵，页内可见多项数值/占位结果且单项结论列为“符合”，但跨页续表与矩阵列映射仍需专门判读；`rule_context` 也标记 `complex_matrix_table=true`，因此不按普通 C07 直接裁决。

复验结论：

- T-CODEX-EVIDENCE-06E 已收口 item `33` residual manual review。
- 当前 full audit 没有 confirmed final error。
- C04/C05/C06/C09 已全部 refuted。
- C07 普通视觉复核项已基本收口。
- 当前唯一剩余是 item `59` complex matrix，保留 `manual_review_required` 符合安全口径。
- 不应通过修改 finalization 强行让 item `59` passed。

下一推荐任务：T-CODEX-EVIDENCE-07：item 59 complex matrix specialized review。

## T-CODEX-EVIDENCE-07：item 59 complex matrix specialized review

状态：规划完成，未实现

规划文档：

- `docs/superpowers/plans/2026-06-28-t-codex-evidence-07-c07-complex-matrix-specialized-review.md`

本轮只新增规划文档，不修改 backend/frontend/router，不运行真实 Codex，不调用 GPT/OpenAI API，不修改旧项目目录。

建议目标：

- 针对 C07 item `59` 的 8.7 漏电流多页复杂矩阵表，建立 specialized matrix review。
- 提供完整矩阵表图像、跨页续表、列标题、行标题、单位/限值/测量值/占位符和单项结论的专门 evidence。
- 让 Codex 复核矩阵列映射和续表结构，而不是套用普通 C07 row-level 逻辑。
- 保持安全口径：证据不足时继续 `manual_review_required`，不通过 finalization 强行通过。

规划覆盖：

- visual evidence：full page images、matrix table crops、row/column header crops、result matrix crops、conclusion column crops、cross-page continuation crops。
- structured evidence：item group rows、page numbers、table headers、condition columns、measured values、placeholder cells、conclusion candidates。
- prompt：先识别矩阵结构，再判断“符合”结论是否由矩阵结果支持；若列映射或跨页续表仍不清楚，应 `uncertain`。
- 测试计划：synthetic complex matrix fixture、page/table crop evidence fixture、prompt contract tests，自动化测试不调用真实 Codex。
- 真实验收：先 targeted item `59`，再 full audit。

## T-CODEX-EVIDENCE-07A：complex matrix specialized evidence builder

状态：已完成代码侧 evidence contract，不代表真实 Codex 验收完成

本次实现：

- 新增 `backend/app/application/c07_complex_matrix_evidence.py`。
- `C07ComplexMatrixEvidenceBuilder` 为 C07 complex matrix target 构建 `c07_complex_matrix_evidence` metadata。
- metadata 包含 `has_complex_matrix_input`、`review_mode=complex_matrix_specialized`、`item_no`、`pages`、matrix table/header/body/result/conclusion/continuation image refs、`structured_matrix_hints` 和 `missing_complex_matrix_evidence_reasons`。
- matrix image `EvidenceItem` 使用 workspace-local relative `items/*.png` file path，并标记 `metadata.codex_image_input=true`、`render_page_number`、`render_bbox/crop_bbox` 和 `matrix_evidence_role`。
- `ReportCodexEvidenceBuilder` 保留现有 `c07_visual_evidence`，并额外把 `c07_complex_matrix_evidence` 写入 target metadata；普通 C07 item 不生成该 metadata。

约束确认：

- 未修改 PromptBuilder。
- 未修改 Codex output schema。
- 未修改 finalization。
- 未修改 C07 deterministic rule。
- 未运行真实 Codex CLI。
- 未调用 GPT/OpenAI API。
- 未修改旧项目目录。

下一推荐任务：T-CODEX-EVIDENCE-07B：complex matrix prompt instructions 和 materialization/handoff 测试。

## T-CODEX-EVIDENCE-07B：complex matrix materialization / handoff / prompt contract

状态：已完成代码侧 contract，不代表真实 Codex 验收完成

本次实现：

- `EvidencePackageWriter` 现有 IMAGE materialization 能覆盖 07A 生成的 matrix page/table/header/body/result/conclusion/continuation `EvidenceItem`；本轮补充 matrix 专项测试。
- `CodexAuditService` 可从 manifest 收集 item 59 complex matrix PNG paths，并传给 runner；paths 均在 controlled workspace 内，不包含原始 source PDF 绝对路径。
- `CodexCliRunner` 多图 handoff 已用 matrix PNG 测试覆盖，命令使用 `--image items/...` 相对路径；missing/unsafe image path 仍由既有 `CODEX_IMAGE_INPUT_MISSING` / `CODEX_IMAGE_INPUT_FORBIDDEN` 保护。
- `PromptBuilder` 新增 `C07 Complex Matrix Review Instructions`，只在 C07 target 带 `c07_complex_matrix_evidence.review_mode=complex_matrix_specialized`、`complex_matrix_table=true` 或 `visual_review_mode=complex_matrix_table` 时注入。

Prompt 语义：

- 先识别矩阵结构，再判断单项结论。
- 必须查看 full page images、matrix table crops、row/column header crops、result matrix crops、conclusion column crops、cross-page continuation crops。
- 需要识别漏电流/患者辅助电流、正常状态/单一故障状态、B/BF/CF 或应用部分相关列、测量值、限值、占位符和单项结论列。
- 视觉证据足以确认“符合”结论由矩阵结果支持时，应 refute 原 complex-matrix candidate。
- 视觉证据显示矩阵结果与“符合”冲突时，可以 confirm。
- 列映射、跨页续表或矩阵结果仍不清楚时，应 uncertain。
- 不因 `rule_context` 写了 `complex_matrix_table=true` 就自动 uncertain；也不按普通 C07 all-placeholder 逻辑直接 confirm/refute。

约束确认：

- 未修改 output schema。
- 未修改 finalization。
- 未修改 C07 deterministic rule。
- 未修改 frontend/router。
- 未运行真实 Codex CLI。
- 未调用 GPT/OpenAI API。
- 未修改旧项目目录。

## T-CODEX-EVIDENCE-07C：targeted item 59 与 full mandatory audit 最终复验

完成日期：2026-06-29

targeted item 59 complex matrix validation：

- 结果文件：`runtime/codex_audit_local_e2e/4b15adbb-6e4e-4a66-99e7-9170843b3646.result.json`。
- 本轮设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07` 与 `CODEX_AUDIT_INCLUDED_FINDING_CODES=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`。
- `audit_scope=targeted`，`final_audit_status=passed`，`codex_reviews_count=1`。
- item 59 `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX` 的 final status 为 `refuted`。
- Codex review `status=succeeded`、`verdict=refute`、`confidence=high`，reasoning 指出跨页矩阵视觉证据显示 item 59 为同一漏电流/患者辅助电流项目，结果列包含有效数值与适用占位，单项结论列可见“符合”，规则候选将备注列“/”误作实际结论。

full mandatory audit 最终复验：

- 结果文件：`runtime/codex_audit_local_e2e/8e84b3e7-e079-4e6f-ac7f-b99348f18ffa.result.json`。
- 本轮未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`、`CODEX_AUDIT_INCLUDED_FINDING_CODES` 或 `CODEX_AUDIT_EXCLUDED_CHECK_IDS`。
- `task status=completed`，`audit_scope=full`，`full_audit=true`，`final_audit_status=passed`。
- `candidate_findings_count=51`，`codex_reviews_count=57`。
- `confirmed_findings_count=0`，`confirmed_errors_count=0`。
- `refuted_findings_count=51`，`manual_review_required_count=0`。
- `out_of_scope_findings_count=0`，`unreviewed_required_findings_count=0`，`codex_runtime_failure_count=0`。

按 check_id 最终状态：

- C04：`refuted=35`
- C05：`refuted=2`
- C06：`refuted=1`
- C07：`refuted=12`
- C09：`refuted=1`

结论：

- T-CODEX-EVIDENCE-07 后 full mandatory Codex audit 最终复验通过。
- 当前真实样本 `QW2025-2795 Draft.pdf` 没有 confirmed final error。
- 当前没有 `manual_review_required`。
- 51 条 deterministic candidate findings 全部被 Codex final audit refute。
- C07 item 59 complex matrix specialized review 已在 full audit 中生效。
- 报告自检主线在该真实样本上达到 `final_audit_status=passed`。

下一推荐任务：整理阶段性交付说明，并考虑增加更多真实样本的 gated regression。

## T-CODEX-RUNTIME-01B：local E2E error summary 解析修复

完成日期：2026-06-26

本次修复 local E2E 脚本失败摘要解析，不调用真实 Codex CLI，不改变 mandatory audit 原则。

背景：

- C04 failed extract 中 `task_id`、`task_status`、`progress`、`current_step` 可能从 task JSON 行解析不到。
- 失败 workspace path 中仍包含 task id，例如 `runtime/codex_audit/0ece4dd1-c2db-48b1-8cfa-efd21ea01a80/codex-report-0ece4dd1-c2db-48b1-8cfa-efd21ea01a80-C04-batch-6/input`。
- stderr 可能包含 `You've hit your usage limit` 和 `try again at ...`，此前摘要只表现为泛化 `CODEX_EXIT_NONZERO`。

本次修复：

- `scripts/run-codex-audit-local-e2e.sh` 在任务 `status=error` 时写入 `error_summary.json`。
- 如果 task JSON 缺少 `task_id`，脚本会从 `runtime/codex_audit/{task_id}/{package_id}/input` 反推出 `task_id`。
- 从 `package_id=codex-report-{task_id}-C04-batch-6` 中提取 `check_id=C04` 和 `batch_id=batch-6`。
- stderr 或 diagnostics 中出现 usage limit 时，`error_code` 归类为 `CODEX_USAGE_LIMIT_EXCEEDED`，并提取 `retry_after_text`。
- 终端只打印简洁恢复提示，例如 usage limit reached、retry after、failed workspace 和 error summary 路径，不再依赖原始 status JSON 大段输出。

约束：

- Codex runtime failure 仍然让 task failed。
- 本次不修改后端业务代码、router、frontend 或旧项目目录。
- 本次不运行真实 Codex CLI。

## T-PERF-01 至 T-PERF-04：Codex audit speed roadmap 基础能力

完成日期：2026-06-29

状态：代码侧基础能力已完成；尚未运行真实 batch=5 性能对比。

本次实现：

- T-PERF-01：新增 `PerformanceProfile` / `PerfStage`，在 report-check 主流程记录 `parse_pdf`、`build_report_document`、`run_rules`、`codex_audit_total`、`finalize_codex_audit`、`complete_task`；Codex package 侧记录 evidence write、image collection、prompt/schema、codex exec、validation、prompt/evidence/image size 等统计。
- T-PERF-01：`EvidencePackageWriter` manifest 记录 image materialization、materialized image bytes、externalized text count/bytes；`CodexCliRunner` 成功/失败 review metadata 记录 exec、exit code、stdout/stderr/output size 和 image count。
- T-PERF-01：确认 `codex_audit_max_targets_per_batch` 默认仍为 `5`；local E2E `--print-config` 和运行输出会显示 effective batch size，full audit 且 batch=1 时提示 debug/slow mode。
- T-PERF-02：新增 `CodexAuditScheduler`，支持 application 层自动把 Codex packages 交给 bounded worker 执行；默认 `CODEX_AUDIT_MAX_PARALLEL_JOBS=1`，保持串行兼容。review metadata 记录 `codex_scheduler_profile`，包含 parallel jobs、worker、queue wait、started/completed 和 scheduler total。
- T-PERF-03：新增 task 级 `CodexAuditOptions`；Report/PTR API 支持可选 `included_check_ids`、`included_finding_codes`、`excluded_check_ids`、`max_targets_per_batch`、`max_parallel_jobs`。前端 Report/PTR 上传页新增默认折叠的“高级审核设置”，默认不影响普通 full mandatory audit。
- T-PERF-03：task result metadata 记录 `audit_options_source`、用户输入 `audit_options` 和实际生效 `effective_audit_options`，便于区分 default 与 user override。
- T-PERF-04：新增 filesystem cache `runtime/codex_audit_cache/{cache_key}.json`。cache key 包含 task type、request/evidence、prompt/schema、image hash，并归一化 task UUID，支持相同 evidence/prompt/schema/image 的 repeat run 复用。
- T-PERF-04：只缓存 `status=succeeded`、schema/parser valid 且 verdict 不是 `uncertain` 的 review；不缓存 failed/skipped/uncertain review。cache hit 会重新绑定到当前 request/task/target，并在 metadata 标记 `cache_hit=true`，不会静默删除 deterministic finding。
- 保持既有 runtime 诊断：Codex CLI nonzero exit 如果 stderr/stdout 包含 usage limit，会归类为 `CODEX_USAGE_LIMIT_EXCEEDED`，写入 `retry_after_text` 和 runner diagnostics；mandatory runtime failure 仍使 task failed。

约束确认：

- 未修改 deterministic C01-C11 / PTR 规则。
- 未修改 Codex finalization 语义。
- 未运行真实 Codex CLI。
- 未调用 GPT/OpenAI API。
- 未修改旧项目目录。

下一推荐任务：T-PERF-05，使用真实样本执行 full mandatory audit，确保无 include/exclude filters、effective `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=5`，对比 batch=1 基线的 package 数、wall-clock、`codex_exec_seconds`、image bytes 和最终审核结论。
