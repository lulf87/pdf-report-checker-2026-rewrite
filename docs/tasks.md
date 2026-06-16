# 重做项目任务清单

执行规则：

- 每次只执行一个任务。
- 每个任务必须先补测试或验收检查，再实现最小代码。
- 当前任务测试失败时，不得继续下一个任务。
- 完成任务后才可把对应 `完成状态` 改为 `[x]`。
- 不修改旧项目原文件，不修改 raw/original/source_data 等不可变输入目录。
- 旧项目根目录为 `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13`。
- 当前项目根目录为 `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3`。

## T-CODEX 系列：Codex CLI 运行时审核链路

本系列纠偏当前重写方向：确定性规则负责 evidence package 和 candidate findings，Codex CLI 作为产品运行时 auditor / judge 参与复杂语义、图文证据和歧义复核。最终结果必须同时保留 deterministic finding 与 Codex review。

### T-CODEX-00：架构文档和 AGENTS 修正
- 目标：明确 Codex CLI 是产品运行时受控审核员，不是普通开发工具，也不只是 evidence-only LLM adapter。
- 背景：旧项目事实显示复杂语义或图文判断会调用 Codex CLI 辅助复核；新项目此前文档过度强调“LLM 不得裁决”，需要改为双层证据链。
- 涉及旧文件：旧项目只读；参考当前 `docs/legacy-inventory.md`、`docs/spec-code-test-gaps.md` 和用户本次纠偏指令。
- 新文件位置：`docs/codex-cli-auditor-strategy.md`，并更新 `AGENTS.md`、`docs/tasks.md`、`docs/current-status.md`。
- 需要实现：写明旧项目事实、新定位、后端模块设计、运行时安全边界、数据模型、`CheckResult` 集成、PTR 优先接入点、报告自检优先接入点和 T-CODEX 任务拆分。
- 不允许做：不实现业务代码；不调用真实 Codex；不修改 router；不修改前端；不修改旧项目目录；不继续扩展 numeric semantic。
- 测试要求：运行 `git diff --check`。
- 验收标准：Done when 文档明确 Codex CLI runtime auditor 链路，AGENTS 不再使用“LLM 不得替代确定性核对规则”的绝对表述。
- 完成状态：[x]

### T-CODEX-01：CodexReview domain model
- 目标：新增 `backend/app/domain/codex_review.py`。
- 背景：Codex review 必须是一等领域模型，不能继续用临时 dict 或 prompt 返回结构散落在 usecase 中。
- 涉及旧文件：旧项目 Codex judge schema 和当前 `docs/codex-cli-auditor-strategy.md`。
- 新文件位置：`backend/app/domain/codex_review.py`、`backend/tests/domain/test_codex_review_models.py`。
- 需要实现：`CodexReviewRequest`、`CodexReviewTarget`、`CodexReviewResult`、`CodexReviewVerdict`、`CodexReviewStatus`、`CodexReviewError`，并定义序列化和必填字段。
- 不允许做：不调用 Codex CLI；不把 review model 放到 infrastructure；不使用裸 dict 作为跨层契约。
- 测试要求：运行 `cd backend && python -m pytest tests/domain/test_codex_review_models.py -v`。
- 验收标准：Done when Codex review 模型可独立序列化、校验 failed/completed/skipped 场景，并能关联 finding IDs。
- 完成状态：[x]

### T-CODEX-02：EvidencePackage model 和 writer
- 目标：新增 evidence package 模型和写入器。
- 背景：Codex 只能接收最小证据包，不能读取整个项目或上传目录。
- 新文件位置：`backend/app/domain/codex_review.py`、`backend/app/infrastructure/audit/evidence_package_writer.py`、`backend/tests/infrastructure/audit/test_evidence_package_writer.py`。
- 需要实现：`EvidencePackage`，每个任务写入 `runtime/codex_audit/{task_id}/`，只包含 candidate findings、check result 摘要、evidence、允许的原文片段和必要 asset refs。
- 不允许做：不写入旧项目目录；不暴露整个源码树；不修改原始上传文件；不把 raw PDF 作为默认 evidence package 交给 Codex。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/audit/test_evidence_package_writer.py -v`。
- 验收标准：Done when writer 使用 `tmp_path` 测试通过，路径被限制在 audit runtime 目录，输出 JSON schema 稳定。
- 完成状态：[ ]

### T-CODEX-03：FakeCodexRunner / CodexCliRunner 接口
- 目标：建立可替换 runner 接口和 fake/real 两种实现。
- 背景：单元测试不能调用真实 Codex；真实 CLI 只能在受控运行时和手动验收中启用。
- 新文件位置：`backend/app/infrastructure/codex/fake_codex_runner.py`、`backend/app/infrastructure/codex/codex_cli_runner.py`、`backend/tests/infrastructure/codex/test_codex_runner.py`。
- 需要实现：runner protocol、`FakeCodexRunner` 固定输出、`CodexCliRunner` 命令构造、read-only sandbox、工作目录、timeout、stdout/stderr 保存和 exit code 处理。
- 不允许做：不在测试中调用真实 Codex；不允许 runner 接收项目根目录作为默认上下文；不允许写源码文件。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/codex/test_codex_runner.py -v`。
- 验收标准：Done when fake runner 可注入，real runner 命令参数可测试，timeout/nonzero 能转成错误结果。
- 完成状态：[ ]

### T-CODEX-04：PromptBuilder 和 JSON schema
- 目标：为 Codex review 生成受控 prompt 和 output schema。
- 背景：Codex 只能基于 evidence package 输出 JSON，不得补造标准、字段含义或文件路径。
- 新文件位置：`backend/app/infrastructure/codex/prompt_builder.py`、`backend/app/infrastructure/codex/schemas/`、`backend/tests/infrastructure/codex/test_prompt_builder.py`。
- 需要实现：按 review target 生成 prompt，声明 allowed evidence refs、输出 `confirm/refute/uncertain/add_finding` schema，禁止自由文本作为最终结构。
- 不允许做：不把整个 CheckResult JSON 原样无限制塞入 prompt；不包含项目源码；不允许 prompt 要求 Codex 修改文件。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/codex/test_prompt_builder.py -v`。
- 验收标准：Done when prompt 包含安全边界、schema、target 和 evidence refs，且不包含未授权路径。
- 完成状态：[ ]

### T-CODEX-05：OutputParser 和失败 fallback
- 目标：解析 Codex JSON 输出并提供失败降级。
- 背景：Codex 输出不可直接信任，必须 schema validate；失败不能阻断主核对流程。
- 新文件位置：`backend/app/infrastructure/codex/output_parser.py`、`backend/tests/infrastructure/codex/test_output_parser.py`。
- 需要实现：解析 stdout/raw JSON，校验 `CodexReviewResult`，处理 invalid JSON、schema invalid、timeout、stderr、非零退出，统一产生 `CodexReviewStatus.failed`。
- 不允许做：不吞掉失败原因；不把解析失败伪装成 `uncertain`；不删除 deterministic finding。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/codex/test_output_parser.py -v`。
- 验收标准：Done when completed/failed/skipped 路径均有测试，错误中保留 stdout/stderr/raw output ref。
- 完成状态：[ ]

### T-CODEX-06：PTRCompareUseCase 接入 CodexAuditService
- 目标：在 PTR 比对用例中接入运行时 Codex 审核。
- 背景：PTR clause/table/parameter/scope 复杂语义需要 auditor 复核，但不能替代规则候选 findings。
- 新文件位置：`backend/app/application/codex_audit_service.py`、`backend/app/application/ptr_compare_usecase.py`、`backend/tests/application/test_ptr_compare_codex_audit.py`。
- 需要实现：对 PTR clause semantic review、table candidate ambiguity review、parameter semantic review、numeric/segmented threshold review、scope filter review 生成 evidence package 并附加 `codex_reviews`。
- 不允许做：不继续扩展 numeric semantic；不调用真实 Codex；不在 router 中写审核逻辑；不删除原始 PTR findings。
- 测试要求：运行 `cd backend && python -m pytest tests/application/test_ptr_compare_codex_audit.py -v`，并按影响范围运行 PTR usecase 测试。
- 验收标准：Done when FakeCodexRunner 可确认/refute/uncertain/add_finding，最终 `CheckResult` 同时保留 deterministic finding 和 Codex review。
- 完成状态：[ ]

### T-CODEX-07：ReportCheckUseCase 接入 CodexAuditService
- 目标：在报告自检用例中接入运行时 Codex 审核。
- 背景：C02/C03/C04/C05/C06/C07 的标签、照片、日期和特殊检验结果语境需要 auditor 复核。
- 新文件位置：`backend/app/application/report_check_usecase.py`、`backend/tests/application/test_report_check_codex_audit.py`。
- 需要实现：对 C02 标签字段、C03 日期格式和值、C04 样品描述 vs 标签、C05 照片 caption、C06 中文标签 caption、C07 特殊检验结果语境生成审核目标并附加 `codex_reviews`。
- 不允许做：不修改 C01-C11 规则文件职责；不在前端做复核；不调用真实 Codex；不删除原始 finding。
- 测试要求：运行 `cd backend && python -m pytest tests/application/test_report_check_codex_audit.py -v`，并按影响范围运行报告 usecase 测试。
- 验收标准：Done when 报告自检结果能展示规则初判和 Codex 审核意见两层证据。
- 完成状态：[ ]

### T-CODEX-08：前端展示 Codex review
- 目标：前端展示“规则初判 + Codex 审核意见”。
- 背景：前端只能展示后端结果，不能重新计算审核结论。
- 新文件位置：`frontend/src/entities/finding/types.ts`、`frontend/src/features/report-check/components/ReportResults.tsx`、`frontend/src/features/ptr-compare/components/PTRResults.tsx`、相关类型和组件测试。
- 需要实现：类型支持 `codex_reviews`，Finding 卡片展示 Codex verdict/status/summary，失败 review 显示诊断但不阻断结果。
- 不允许做：不在前端调用 Codex；不根据前端字段重新判断 severity；不隐藏 deterministic finding。
- 测试要求：运行 `cd frontend && npm run build`，并运行相关组件/typecheck 测试。
- 验收标准：Done when UI 能区分规则初判、Codex confirm/refute/uncertain/add_finding 和 failed review。
- 完成状态：[ ]

### T-CODEX-09：真实 Codex CLI 手动验收
- 目标：在受控样例上手动验收真实 Codex CLI runtime auditor。
- 背景：真实 Codex 不进入单元测试，只能在专门验收任务中启用。
- 新文件位置：`docs/codex-cli-manual-acceptance.md` 或等价验收记录。
- 需要实现：选择受控 fixture，生成 `runtime/codex_audit/{task_id}/`，运行真实 `codex exec` read-only sandbox，保存 evidence package、prompt、JSON 输出、timeout、stdout/stderr 和 fallback 结果。
- 不允许做：不修改旧项目或新项目源码；不使用未审查原始素材；不把真实 Codex 输出写入稳定 Golden expected；不声称自动化测试已覆盖真实 Codex。
- 测试要求：手动运行并记录命令、输入、输出和结果；自动化仍只依赖 fake runner。
- 验收标准：Done when 手动记录证明真实 Codex CLI 能在只读 sandbox 中基于 evidence package 产出 schema JSON，失败时可降级。
- 完成状态：[ ]

## T01：冻结旧项目并创建 rewrite 分支说明
- 目标：明确旧项目资产只读，建立本次重写的执行边界和分支说明。
- 背景：`docs/legacy-inventory.md` 已记录旧项目可追溯资产和废弃项，新项目不能继续在旧 Electron、旧 service 大文件或旧同步 API 上叠加。
- 涉及旧文件：旧项目整体只读；重点参考旧项目 `README.md`、`backend/app/routers/report_self_check.py`、`backend/app/services/`、`frontend/src/`。
- 新文件位置：`docs/rewrite-branch-notes.md`。
- 需要实现：写明旧项目路径、当前项目路径、旧资产读取来源、禁止原地修改旧项目、禁止修改原始素材、迁移执行顺序、测试失败停止规则、旧 Electron 和历史 `python_backend/` 不进入新架构。
- 不允许做：不创建或删除旧项目文件；不移动旧素材；不把未检出的旧文件写成已确认事实；不开始迁移代码。
- 测试要求：运行 `test -f docs/rewrite-branch-notes.md`；运行 `rg "只读|测试失败|Electron|python_backend" docs/rewrite-branch-notes.md`。
- 验收标准：Done when 文档存在，清楚说明旧项目只读、当前重写边界、废弃主线和失败停止规则。
- 完成状态：[x]

## T02：生成 AGENTS.md
- 目标：在当前项目根目录生成项目级 `AGENTS.md`，约束后续 Codex 执行。
- 背景：全局规则要求不编造、不改 raw、最小有效变更、复杂任务先计划、验证后汇报；当前项目需要把这些约束固化到仓库级入口。
- 涉及旧文件：无直接旧代码迁移；参考 `docs/legacy-inventory.md` 的废弃清单和 `docs/migration-plan.md` 的数据安全规则。
- 新文件位置：`AGENTS.md`。
- 需要实现：包含适用范围、迁移优先级、原始数据不可改、旧项目只读、规则逐条迁移、测试失败停止、结果必须可追溯、前端不得做业务判断、导出不得编造结果等约束。
- 不允许做：不覆盖用户已有更具体的子目录规则；不加入与当前项目无关的团队流程；不要求一次性重写全部。
- 测试要求：运行 `test -f AGENTS.md`；运行 `rg "旧项目只读|raw|测试失败|前端不得" AGENTS.md`。
- 验收标准：Done when `AGENTS.md` 存在，并能指导后续所有 T03-T42 任务。
- 完成状态：[x]

## T03：初始化新后端目录结构
- 目标：创建新 FastAPI 后端骨架和分层目录。
- 背景：旧后端的 `backend/app/routers/report_self_check.py` 和 `backend/app/services/*` 职责混合，新架构需要 `api/application/domain/rules/infrastructure` 分层。
- 涉及旧文件：旧项目 `backend/pyproject.toml`、`backend/app/main.py`、`backend/app/routers/report_self_check.py`、`backend/app/models/report_self_check.py`。
- 新文件位置：`backend/pyproject.toml`、`backend/app/main.py`、`backend/app/api/`、`backend/app/application/`、`backend/app/domain/`、`backend/app/rules/`、`backend/app/infrastructure/`、`backend/tests/`。
- 需要实现：最小 Python 包结构、FastAPI app 工厂或 app 实例、测试依赖、空包 `__init__.py`、基础 pytest 配置。
- 不允许做：不迁移业务规则；不复制旧 service 大文件；不保留旧 `/api/report-self-check` 作为主路由；不引入数据库。
- 测试要求：运行 `cd backend && python -m pytest`；若尚无测试，应至少有一个 app import smoke test。
- 验收标准：Done when 后端包可 import，pytest 可运行，目录符合 `docs/migration-plan.md` 的分层结构。
- 完成状态：[x]

## T04：初始化新前端目录结构
- 目标：创建新 React + TypeScript + Vite 前端骨架。
- 背景：旧 `frontend/src/pages/ReportSelfCheckPage.tsx` 同时承担 Dashboard、上传、轮询、结果展示和导出，新前端需要按 feature 拆分。
- 涉及旧文件：旧项目 `frontend/package.json`、`frontend/src/main.tsx`、`frontend/src/App.tsx`、`frontend/src/pages/ReportSelfCheckPage.tsx`、`frontend/src/styles.css`。
- 新文件位置：`frontend/package.json`、`frontend/src/app/`、`frontend/src/api/`、`frontend/src/features/dashboard/`、`frontend/src/features/report-check/`、`frontend/src/features/ptr-compare/`、`frontend/src/features/results/`、`frontend/src/features/export/`、`frontend/src/shared/`。
- 需要实现：最小 Vite React TS app、入口渲染、基础样式入口、空白 Dashboard 占位视图、前端类型检查和 build 脚本。
- 不允许做：不把旧大页面直接复制进来；不在前端实现业务规则；不做营销落地页；不接真实 API。
- 测试要求：运行 `cd frontend && npm run build`；如果配置了类型检查，运行 `cd frontend && npm run typecheck`。
- 验收标准：Done when 前端能构建，目录按 feature 拆分，首屏是可运行工作台入口。
- 完成状态：[x]

## T05：定义统一领域模型和 Finding
- 目标：建立 `Location`、`Evidence`、`Finding`、`CheckResult`、`TaskStatus` 等统一模型。
- 背景：旧 `backend/app/models/report_self_check.py` 的 `Finding`、`EvidenceItem`、`MissingEvidence`、`CheckResult` 是高价值资产，但字段宽松且 evidence 可为空，新架构需要强类型契约。
- 涉及旧文件：旧项目 `backend/app/models/report_self_check.py`、`backend/app/schemas/codex_check_result.schema.json`。
- 新文件位置：`backend/app/domain/common.py`、`backend/app/domain/finding.py`、`backend/app/domain/result.py`、`backend/app/domain/task.py`、`backend/app/api/schemas/`、`backend/tests/domain/test_finding_models.py`。
- 需要实现：定义 severity、status、confidence、location、evidence、missing evidence、finding、check result、summary、task status；明确 ERROR/WARN/INFO 和 PASS/FAIL/REVIEW/SKIP/SYSTEM_ERROR 的关系。
- 不允许做：不使用裸 dict 作为模型；不允许 FAIL/REVIEW finding 缺少证据或缺失证据说明；不把 Codex schema 作为领域模型直接复用。
- 测试要求：运行 `cd backend && python -m pytest tests/domain/test_finding_models.py`，覆盖序列化、必填字段、缺失证据、summary 计数。
- 验收标准：Done when 模型测试通过，后续 API、规则、导出都能复用同一结果契约。
- 完成状态：[x]

## T06：实现统一任务模型和内存 TaskRepository
- 目标：实现可替换的任务仓储接口和初版内存实现。
- 背景：旧 `report_self_check.py` 使用全局 `TASKS` dict 和 `Lock`，状态不稳定且混入 router；新架构需要 application 层任务模型。
- 涉及旧文件：旧项目 `backend/app/routers/report_self_check.py`。
- 新文件位置：`backend/app/application/task_service.py`、`backend/app/domain/task.py`、`backend/tests/application/test_task_repository.py`。
- 需要实现：`TaskRepository` 协议或抽象类、`InMemoryTaskRepository`、任务创建、状态更新、日志追加、结果引用、错误记录、任务不存在错误。
- 不允许做：不把仓储放在 FastAPI router；不直接存上传文件 bytes；不引入数据库；不吞掉错误信息。
- 测试要求：运行 `cd backend && python -m pytest tests/application/test_task_repository.py`，覆盖 pending、processing、completed、error、not found。
- 验收标准：Done when 任务状态可独立测试，router 尚不存在也能使用 task service。
- 完成状态：[x]

## T07：实现文件存储 LocalFileStore
- 目标：建立上传文件、任务结果和导出文件的本地存储 adapter。
- 背景：旧项目运行时目录如 `uploads/`、`temp/` 不作为业务资产，新项目需要受控 workspace 和 cleanup 策略。
- 涉及旧文件：旧项目 `backend/app/routers/report_self_check.py` 的上传处理、`backend/app/services/pdf_document_loader.py` 的临时图片输出经验。
- 新文件位置：`backend/app/infrastructure/storage/local_file_store.py`、`backend/tests/infrastructure/test_local_file_store.py`、`backend/app/domain/task.py`。
- 需要实现：保存上传 PDF、生成安全 file id、保存 JSON 结果、保存导出文件、读取结果、拒绝路径穿越、配置 runtime 根目录。
- 不允许做：不写入 raw/original/source_data；不使用用户本机旧项目路径作为运行目录；不保留原始文件名作为唯一路径；不删除非本 adapter 创建的文件。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/test_local_file_store.py`，覆盖保存读取、路径穿越拒绝、文件名保留为 metadata。
- 验收标准：Done when 文件存储可独立使用，所有路径都在受控 runtime 根目录下。
- 完成状态：[x]

## T08：实现 GET /api/health
- 目标：提供新后端健康检查接口。
- 背景：旧健康检查位于 `/api/report-self-check/health`，新架构改为顶层 `/api/health`。
- 涉及旧文件：旧项目 `backend/app/routers/report_self_check.py`、`backend/app/main.py`。
- 新文件位置：`backend/app/api/routes_health.py`、`backend/app/main.py`、`backend/tests/api/test_health.py`。
- 需要实现：返回服务状态、版本或应用名、基础依赖摘要；挂载到 `/api/health`。
- 不允许做：不挂旧 `/api/report-self-check/health` 作为主接口；不在 health 中执行耗时 PDF/OCR 检查；不返回临时 dict 中的业务状态。
- 测试要求：运行 `cd backend && python -m pytest tests/api/test_health.py`，断言 200、JSON schema 和路径。
- 验收标准：Done when `GET /api/health` 可测且不依赖业务规则。
- 完成状态：[x]

## T09：实现统一任务 API 骨架
- 目标：建立任务创建、查询、结果和导出的 API skeleton。
- 背景：旧 API 分散在 `/api/report-self-check/check/start`、`/ptr-report/check/start`、`/tasks/{task_id}`，新 API 统一到 `/api/tasks/*`。
- 涉及旧文件：旧项目 `backend/app/routers/report_self_check.py`、`frontend/src/api/reportSelfCheck.ts`。
- 新文件位置：`backend/app/api/routes_tasks.py`、`backend/app/api/routes_report_check.py`、`backend/app/api/routes_ptr_compare.py`、`backend/tests/api/test_tasks_api.py`。
- 需要实现：`POST /api/tasks/report-check`、`POST /api/tasks/ptr-compare`、`GET /api/tasks/{task_id}`、`GET /api/tasks/{task_id}/result`、`GET /api/tasks/{task_id}/export` 的骨架；创建任务可先不执行真实业务，但必须返回统一 `TaskStatus`。
- 不允许做：不实现同步检查接口；不在 router 中解析 PDF；不把旧 task dict 暴露给前端；不接入 C01-C11。
- 测试要求：运行 `cd backend && python -m pytest tests/api/test_tasks_api.py`，覆盖 PDF 文件类型校验、缺少文件、任务不存在、导出格式非法。
- 验收标准：Done when 新 API 路径和状态契约稳定，业务 usecase 可后续接入。
- 完成状态：[x]

## T10：迁移 PDF parser 到 infrastructure/pdf
- 目标：把旧 PyMuPDF 解析经验迁移为 `ParsedPdf` adapter。
- 背景：旧 `pdf_document_loader.py` 同时承担页面解析、图片渲染、照片页/无文本页判断，新架构只在 PDF adapter 输出结构化 PDF 数据和诊断。
- 涉及旧文件：旧项目 `backend/app/services/pdf_document_loader.py`、`backend/tests/test_pdf_document_loader.py`。
- 新文件位置：`backend/app/infrastructure/pdf/pdf_document_loader.py`、`backend/app/domain/pdf.py`、`backend/tests/infrastructure/test_pdf_document_loader.py`。
- 需要实现：读取 PDF、页数、页面文本、词坐标、页面尺寸、图片/绘图摘要、textless 标记、可选页面渲染引用；输出 `ParsedPdf` 和 `PdfPage`。
- 不允许做：不在 PDF parser 中判断 C 规则；不识别照片覆盖是否通过；不调用 OCR；不修改输入 PDF。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/test_pdf_document_loader.py`，使用小 fixture 覆盖有效 PDF、损坏 PDF、页文本、words、textless 诊断。
- 验收标准：Done when parser 可独立输出 `ParsedPdf`，业务规则完全不在该模块内。
- 完成状态：[x]

## T11：迁移 OCR parser / OCR service 到 infrastructure/ocr
- 目标：建立 OCR adapter 和标签字段标准化输出。
- 背景：旧项目当前主要从 PDF 文本层抽标签字段，未稳定集成 OCR 引擎；新架构要求 PaddleOCR 或 fake OCR 输出进入 `LabelOCR` 和 Evidence。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中 `_extract_label_fields`、`_extract_label_caption`、C08 图片证据策略。
- 新文件位置：`backend/app/infrastructure/ocr/ocr_service.py`、`backend/app/infrastructure/ocr/label_field_parser.py`、`backend/app/domain/report.py`、`backend/tests/infrastructure/test_ocr_service.py`。
- 需要实现：OCR service 接口、fake OCR 实现、字段别名表、中文/英文冒号解析、caption 关联、confidence、raw blocks、`LabelOCR` 输出。
- 不允许做：不让 OCR 直接决定 PASS/FAIL；不把 OCR 空字段当成标签不存在；不依赖 live OCR 做稳定单元测试。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/test_ocr_service.py`，覆盖字段别名、低置信、无字段、中文冒号、英文冒号、fake adapter。
- 验收标准：Done when OCR 输出可作为证据输入规则，但规则判定仍在 rules 层。
- 完成状态：[x]

## T12：迁移 ReportExtractor，但拆成 page_locator、field_extractor、inspection_table_extractor、sample_description_extractor
- 目标：构建 `ReportDocument`，并把旧 report evidence builder 拆为多个 extractor。
- 背景：旧 `report_evidence_builder.py` 单文件承载字段抽取、样品描述、标签、C14/C15 候选和 prompt required details，新架构要先形成领域模型。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py`、`backend/app/services/report_self_check_service.py`、`backend/tests/test_report_evidence_builder.py`。
- 新文件位置：`backend/app/application/report_extraction/page_locator.py`、`field_extractor.py`、`inspection_table_extractor.py`、`sample_description_extractor.py`、`report_document_builder.py`、`backend/app/domain/report.py`、`backend/tests/application/test_report_extraction.py`。
- 需要实现：定位首页/第三页/照片页/标签页，抽取首页和第三页字段，抽取检验项目表，抽取样品描述表，生成 `ReportDocument`、`ReportField`、`InspectionItem`、`SampleComponent`、`PhotoCaption`。
- 不允许做：不实现任何 C01-C11 判定；不调用 Codex；不输出临时 dict；不把字段缺失写成业务错误。
- 测试要求：运行 `cd backend && python -m pytest tests/application/test_report_extraction.py`，覆盖字段、样品组件、检验项目、caption、缺失页面诊断。
- 验收标准：Done when report extractor 可由 `ParsedPdf` 和 `LabelOCR` 构建 `ReportDocument`，规则任务可独立消费。
- 完成状态：[x]

## T13：迁移 C01 规则
- 目标：实现新 C01 首页与第三页一致性。
- 背景：新 C01 对应首页和第三页的委托方、样品名称、型号规格一致性；旧 C01 是报告编号/样品编号一致性，不能直接沿用编号含义。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中旧 C02 相关 evidence；`backend/tests/test_report_evidence_builder.py` 中旧 C02 基础字段测试。
- 新文件位置：`backend/app/rules/report/c01_home_vs_third.py`、`backend/app/rules/report/registry.py`、`backend/tests/rules/report/test_c01_home_vs_third.py`。
- 需要实现：比较委托方、样品名称、型号规格；输出 `C01_FIELD_MISMATCH`、`C01_FIELD_MISSING`；保留字段页码、原文和归一化值。
- 不允许做：不迁入旧 C01 报告编号规则；不比较检验类别，除非后续业务确认；不调用 OCR/LLM 直接裁决。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/report/test_c01_home_vs_third.py`，覆盖三字段一致、不一致、缺失、空白归一。
- 验收标准：Done when C01 可单独运行，registry 中编号为 `C01`，失败只输出 C01 findings。
- 完成状态：[x]

## T14：迁移 C02 规则
- 目标：实现新 C02 第三页扩展字段核对。
- 背景：新 C02 处理第三页型号规格、生产日期、产品编号/批号、委托方、委托方地址与标签 OCR 或样品描述支持证据；旧 C03/C08 提供字段和标签抽取经验。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中旧 C03、旧 C08、`_extract_label_fields`。
- 新文件位置：`backend/app/rules/report/c02_third_page_extended_fields.py`、`backend/tests/rules/report/test_c02_third_page_extended_fields.py`。
- 需要实现：字段别名映射、`见样品描述栏` 三字段一致性、标签缺失 WARN、字段不一致 ERROR、证据输出。
- 不允许做：不把标签字段为空当成标签不存在；不同时实现 C03 日期规则；不在前端补判断。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/report/test_c02_third_page_extended_fields.py`，覆盖全部为“见样品描述栏”、部分为该值、标签缺失、字段 mismatch、委托方地址缺失。
- 验收标准：Done when C02 独立输出扩展字段 findings，不影响 C01/C03。
- 完成状态：[ ]

## T15：迁移 C03 规则
- 目标：实现新 C03 生产日期格式和值一致性。
- 背景：旧实现没有确定性日期格式比较，`docs/spec-code-test-gaps.md` 明确 C03 口径存在差异，新架构需将日期格式和值显式建模。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中旧 C03/旧 C04 时间字段证据。
- 新文件位置：`backend/app/rules/report/c03_production_date.py`、`backend/tests/rules/report/test_c03_production_date.py`。
- 需要实现：比较第三页生产日期与标签 OCR 生产日期；识别 `YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY.MM.DD`、`YYYYMMDD`；输出格式不一致、值不一致、日期缺失 findings。
- 不允许做：不核对签发日期；不实现 C02 字段支持；不把低置信 OCR 当高置信 ERROR。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/report/test_c03_production_date.py`，覆盖格式同值同、格式不同值同、格式同值不同、缺失、低置信。
- 验收标准：Done when C03 的日期判定可独立测试，未确认日期格式仅输出 WARN/REVIEW。
- 完成状态：[ ]

## T16：迁移 C04 规则
- 目标：实现新 C04 样品描述表格核对。
- 背景：旧 C06/C08 有样品描述和标签字段抽取经验，但失效日期未完整覆盖，新 C04 需要完整字段模型。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中旧 C06、旧 C08、`_extract_sample_items`、`_extract_label_fields`。
- 新文件位置：`backend/app/rules/report/c04_sample_description.py`、`backend/tests/rules/report/test_c04_sample_description.py`。
- 需要实现：比较部件名称、规格型号、序列号批号、生产日期、失效日期；支持字段同义词和非空 identity key；输出字段不一致、字段缺失、标签无法匹配。
- 不允许做：不实现照片覆盖；不实现中文标签覆盖；不把 `/` 与空白做全局等价；不忽略失效日期。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/report/test_c04_sample_description.py`，覆盖失效日期、同名多行、`/`、空白、标签有值但表格无值、未使用备注。
- 验收标准：Done when C04 只负责样品描述字段一致性，覆盖性规则留给 C05/C06。
- 完成状态：[x]

## T17：迁移 C05 规则
- 目标：实现新 C05 照片覆盖性。
- 背景：旧 C07 照片覆盖性实现不足，旧 C08 有 caption 与图片分批经验；新 C05 只判断每个样品描述部件是否有照片。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中旧 C07、旧 C08 caption 逻辑。
- 新文件位置：`backend/app/rules/report/c05_photo_coverage.py`、`backend/tests/rules/report/test_c05_photo_coverage.py`。
- 需要实现：按 `SampleComponent` 匹配 `PhotoCaption`，清洗 caption 主体名，跳过备注含“本次检测未使用”的部件，输出照片缺失或 caption 不确定。
- 不允许做：不核对标签字段值；不把中文标签覆盖合并进 C05；不使用 VLM verdict 直接通过。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/report/test_c05_photo_coverage.py`，覆盖有照片、无照片、只有标签照片、未使用跳过、caption 主体名清洗。
- 验收标准：Done when C05 findings 只描述照片覆盖问题。
- 完成状态：[ ]

## T18：迁移 C06 规则
- 目标：实现新 C06 中文标签覆盖。
- 背景：旧 C08 已有标签页 caption、标签字段抽取、图片证据策略，新 C06 只判断每个部件是否有中文标签证据。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中旧 C08、`_extract_label_fields`、`_extract_label_caption`；`backend/app/services/report_self_check_service.py` 的 C08 图片分批经验。
- 新文件位置：`backend/app/rules/report/c06_label_coverage.py`、`backend/tests/rules/report/test_c06_label_coverage.py`。
- 需要实现：按部件 identity key 匹配中文标签 caption/OCR；区分中文标签、英文标签、包装标签；低置信 OCR 输出 WARN。
- 不允许做：不比较标签字段值，字段一致性归 C04；不因标签 OCR 空字段直接判无标签；不调用前端逻辑。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/report/test_c06_label_coverage.py`，覆盖中文标签存在、英文标签、包装标签、同名多行、OCR 低置信、未使用跳过。
- 验收标准：Done when C06 独立判断中文标签覆盖并输出统一 Finding。
- 完成状态：[x]

## T19：迁移 C07 规则
- 目标：实现新 C07 检验项目单项结论逻辑。
- 背景：旧 C12 依赖 Codex 判断检验结果与单项结论，新架构要求规则引擎基于结构化 `InspectionItem` 输出最终判定。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中旧 C12 规则说明、`backend/tests/fixtures/codex_c12_error.json`。
- 新文件位置：`backend/app/rules/report/c07_item_conclusion.py`、`backend/tests/rules/report/test_c07_item_conclusion.py`。
- 需要实现：按序号聚合检验结果；任一不符合期望“不符合”；全部 `/` 或 `——` 期望 `/`；可解析非空结果期望“符合”；无法解析输出 WARN；保留无菌语境规则。
- 不允许做：C07 规则文件不直接调用 Codex；运行时语义复核由 T-CODEX-07 的 `CodexAuditService` 在 usecase 层接入；不处理非空字段空缺，空缺归 C08；不实现总结论规则。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/report/test_c07_item_conclusion.py`，覆盖不符合、全部 `/`、全部 `——`、数字/文本符合、无菌生长、空白转 WARN、跨页聚合。
- 验收标准：Done when C07 可确定性输出结论 mismatch findings。
- 完成状态：[ ]

## T20：迁移 C08 规则
- 目标：实现新 C08 非空字段规则。
- 背景：旧 C14 只检查检验项目表中的检验结果、单项结论、备注，且 `/` 在备注列视为非空；新 C08 需显式定义占位符语义。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中旧 C14、`backend/app/services/report_self_check_service.py` 的确定性 C14 findings。
- 新文件位置：`backend/app/rules/report/c08_non_empty.py`、`backend/tests/rules/report/test_c08_non_empty.py`。
- 需要实现：检查检验结果、单项结论、备注三列；实现 `is_effectively_empty`；明确 `/`、`——` 为非空占位符；合并单元格不确定输出 WARN。
- 不允许做：不检查首页、签字栏或日期栏；不推导单项结论；不把不可定位单元格直接写成 ERROR。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/report/test_c08_non_empty.py`，覆盖空字符串、空格、换行、`/`、`——`、合并单元格、缺 location。
- 验收标准：Done when C08 只输出必填单元格空缺或不确定 findings。
- 完成状态：[x]

## T21：迁移 C09 规则
- 目标：实现新 C09 序号连续性。
- 背景：旧 C15 同时处理序号和续表，新 C09 只负责序号起点、跳号、重复、空白。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中旧 C15 sequence/continuation evidence。
- 新文件位置：`backend/app/rules/report/c09_sequence.py`、`backend/tests/rules/report/test_c09_sequence.py`。
- 需要实现：规范化序号，`续X` 归属原序号，不作为普通重复；检查从 1 开始、连续、无跳号、无重复、无空白。
- 不允许做：不判断续表位置，归 C10；不读取 PDF 文件；不靠 Codex 推断序号。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/report/test_c09_sequence.py`，覆盖正常、从 0 开始、跳号、重复、空白、`续5`、`续 5`。
- 验收标准：Done when C09 只输出序号连续性 findings。
- 完成状态：[x]

## T22：迁移 C10 规则
- 目标：实现新 C10 续表标记规则。
- 背景：旧 C15 已有续表候选抽取和确定性补充 finding，新架构要把续表从序号连续性中拆出。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中 `_extract_c15_continuation_marker_candidates`；`backend/app/services/report_self_check_service.py` 的 C15 确定性 findings。
- 新文件位置：`backend/app/rules/report/c10_continuation.py`、`backend/tests/rules/report/test_c10_continuation.py`。
- 需要实现：检测跨页同一序号后续页第一行必须为“续X”；首次出现不应写续；续标记只能出现在本页第一行；位置不确定输出 WARN。
- 不允许做：不处理普通跳号；不要求 OCR/VLM 判定；不静默忽略错误续表。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/report/test_c10_continuation.py`，覆盖 `续X`、`续 X`、首次误写续、跨页缺续、非第一行续、位置不确定。
- 验收标准：Done when C10 findings 和 C09 findings 不重叠。
- 完成状态：[ ]

## T23：迁移 C11 规则
- 目标：实现新 C11 页码连续性。
- 背景：旧 C16 主要是 evidence required details，缺少确定性页码 checker；新规则需要直接检查第三页开始的打印页码。
- 涉及旧文件：旧项目 `backend/app/services/report_evidence_builder.py` 中旧 C16 规则说明。
- 新文件位置：`backend/app/rules/report/c11_page_number.py`、`backend/tests/rules/report/test_c11_page_number.py`。
- 需要实现：解析 `共 XXX 页 第 Y 页` 或等价格式；检查第三页起连续递增、总页数一致、末页等于总页数、缺失页码。
- 不允许做：不核对检验项目序号；不把全文任意数字当页码；不在无法定位时编造页码。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/report/test_c11_page_number.py`，覆盖正常、缺页码、重复页码、总页数不一致、末页不等于总页数、扫描页需 WARN。
- 验收标准：Done when C11 能独立输出页码 findings。
- 完成状态：[x]

## T24：实现 ReportRuleRunner
- 目标：统一运行 C01-C11 并聚合规则结果。
- 背景：旧 `report_self_check_service.py` 混合调用 Codex、合并批次、追加 C14/C15 findings，新架构需要独立 runner 顺序调用规则模块。
- 涉及旧文件：旧项目 `backend/app/services/report_self_check_service.py`、`backend/app/services/report_evidence_builder.py`。
- 新文件位置：`backend/app/application/report_rule_runner.py`、`backend/app/rules/report/registry.py`、`backend/tests/application/test_report_rule_runner.py`。
- 需要实现：按 registry 顺序运行 C01-C11；捕获单条规则异常为 SYSTEM_ERROR CheckResult；聚合 summary；保留每条规则日志和耗时指标。
- 不允许做：不解析 PDF；不调用 OCR；不把单条规则失败升级为任务 error；不跳过失败测试继续开发。
- 测试要求：运行 `cd backend && python -m pytest tests/application/test_report_rule_runner.py`，覆盖顺序、summary、单规则异常、空 findings pass。
- 验收标准：Done when C01-C11 可通过 runner 一次运行，仍能定位单条规则失败。
- 完成状态：[x]

## T25：实现 ReportCheckUseCase
- 目标：实现报告自检从上传文件到任务结果的 application 用例。
- 背景：旧报告自检流程在 router 和 service 中混合保存文件、解析 PDF、构建 evidence、调用 Codex 和写 task。
- 涉及旧文件：旧项目 `backend/app/routers/report_self_check.py`、`backend/app/services/report_self_check_service.py`、`backend/app/services/pdf_document_loader.py`。
- 新文件位置：`backend/app/application/report_check_usecase.py`、`backend/app/api/routes_report_check.py`、`backend/tests/application/test_report_check_usecase.py`、`backend/tests/api/test_report_check_api.py`。
- 需要实现：保存上传文件、调用 PDF parser、调用 OCR adapter、构建 `ReportDocument`、运行 `ReportRuleRunner`、保存结果、更新任务状态、接入 `POST /api/tasks/report-check`。
- 不允许做：本任务不接入 Codex runtime auditor，Codex 复核由 T-CODEX-07 单独完成；不暴露旧同步 API；不在前端做结果修正；不让规则异常吞掉任务日志。
- 测试要求：运行 `cd backend && python -m pytest tests/application/test_report_check_usecase.py tests/api/test_report_check_api.py`，覆盖成功、损坏 PDF、parser 失败、规则 REVIEW、结果查询。
- 验收标准：Done when 报告自检 API 可从上传到结果查询闭环通过测试。
- 完成状态：[ ]

## T26：迁移 PTRExtractor
- 目标：构建 `PTRDocument` 和 PTR 第 2 章条款模型。
- 背景：旧 `ptr_report_evidence_builder.py` 集中处理 PTR 第 2 章、leaf clause、textless pages 和首页范围，需先拆出 PTR parser。
- 涉及旧文件：旧项目 `backend/app/services/ptr_report_evidence_builder.py`、`backend/tests/test_ptr_report_evidence_builder.py`。
- 新文件位置：`backend/app/application/ptr_extraction/ptr_extractor.py`、`backend/app/domain/ptr.py`、`backend/tests/application/test_ptr_extractor.py`。
- 需要实现：按编号定位 PTR 第 2 章，解析 `2`、`2.1`、`2.1.1` 等层级，构建父子关系、leaf clause、taxonomy 初值、textless page diagnostics。
- 不允许做：不依赖固定标题“性能指标”作为唯一定位；不比较报告内容；不伪造 textless 页条款。
- 测试要求：运行 `cd backend && python -m pytest tests/application/test_ptr_extractor.py`，覆盖章节截止、父子层级、leaf clause、注释/方法排除诊断、textless 页。
- 验收标准：Done when PTRExtractor 可独立输出 `PTRDocument`。
- 完成状态：[x]

## T27：迁移 ClauseComparator
- 目标：实现 PTR 条款文本比对和首页范围过滤。
- 背景：旧 PTR 核对包含首页检验项目范围、括号排除、生物相容性/电磁兼容性排除、`≥/≤` 与 `>/<` 不等价等高价值规则。
- 涉及旧文件：旧项目 `backend/app/services/ptr_report_evidence_builder.py`、`backend/app/services/ptr_report_check_service.py`、`backend/tests/test_ptr_report_evidence_builder.py`、`backend/tests/test_ptr_report_check_service.py`。
- 新文件位置：`backend/app/rules/ptr/scope_filter.py`、`backend/app/rules/ptr/clause_text_compare.py`、`backend/tests/rules/ptr/test_scope_filter.py`、`backend/tests/rules/ptr/test_clause_text_compare.py`。
- 需要实现：解析 exact/range selector、括号排除项、in-scope leaf clauses；比较 PTR 条款正文与报告标准要求；输出缺失、额外、文本不一致和低置信 findings。
- 不允许做：不比较 PTR 表格参数，留给 T29；不在 service 层删除 findings；不把首页未声明条款算缺失。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/ptr/test_scope_filter.py tests/rules/ptr/test_clause_text_compare.py`，覆盖范围、排除、`≥/≤` 差异、缺失、额外、2.4 索引摘要保留审计信息。
- 验收标准：Done when 条款范围和文本比对可独立运行。
- 完成状态：[ ]

## T28：迁移 TableNormalizer / CanonicalTable
- 目标：实现统一表格模型和表格归一化。
- 背景：新架构要求 `CanonicalTable` 用于 PTR 表和报告表参数比对，旧项目未检出独立 `table_models.py`，需要按架构文档重建。
- 涉及旧文件：旧项目 `backend/app/services/pdf_document_loader.py` 的表格/词坐标经验；旧项目未检出的 `table_models.py` 仅作为缺口记录，不能当事实引用。
- 新文件位置：`backend/app/domain/table.py`、`backend/app/infrastructure/pdf/table_extractor.py`、`backend/app/rules/ptr/table_normalizer.py`、`backend/tests/domain/test_canonical_table.py`、`backend/tests/rules/ptr/test_table_normalizer.py`。
- 需要实现：定义 `PdfTable`、`CanonicalTable`、列角色、行位置、参数名列、值列、单位列、条件列；处理多行表头、续表、重复表号诊断。
- 不允许做：不直接用裸二维数组跨模块传递；不在 normalizer 中判断 PTR 参数是否一致；不把不可解析表格静默丢弃。
- 测试要求：运行 `cd backend && python -m pytest tests/domain/test_canonical_table.py tests/rules/ptr/test_table_normalizer.py`，覆盖表头归一、单位列、条件列、续表、候选不唯一 WARN。
- 验收标准：Done when 表格可归一为 `CanonicalTable` 并保留原始证据位置。
- 完成状态：[x]

## T29：迁移 TableComparator
- 目标：实现 PTR 表格参数比对。
- 背景：`docs/known-requirements.md` 要求 `见表 X` 展开并比对参数名、参数值、单位、适用型号/条件和允许误差，不能只看表号。
- 涉及旧文件：旧项目 `backend/app/services/ptr_report_evidence_builder.py` 中 PTR 表格引用文本证据；未检出的 `table_comparator.py` 只作为缺口记录。
- 新文件位置：`backend/app/rules/ptr/table_reference_compare.py`、`backend/app/rules/ptr/parameter_compare.py`、`backend/app/rules/ptr/diff_builder.py`、`backend/tests/rules/ptr/test_table_reference_compare.py`、`backend/tests/rules/ptr/test_parameter_compare.py`。
- 需要实现：识别 `见表 X`、`符合表 X`、`按表 X`；选择 PTR/报告候选表；比对参数名、值、单位、条件、允许误差；生成 diff 结构。
- 不允许做：不做单位换算，除非任务内有明确测试和规则；不只判断表号存在；不删除被压制的 finding。
- 测试要求：运行 `cd backend && python -m pytest tests/rules/ptr/test_table_reference_compare.py tests/rules/ptr/test_parameter_compare.py`，覆盖缺表、候选不唯一、参数缺失、值不一致、单位不一致、条件不一致。
- 验收标准：Done when 表格引用和参数差异能输出可展示 Finding 和 diff。
- 完成状态：[ ]

## T30：实现 PTRCompareUseCase
- 目标：实现 PTR 与报告比对从双文件上传到任务结果的完整用例。
- 背景：旧 PTR 流程在 `ptr_report_evidence_builder.py` 和 `ptr_report_check_service.py` 中，包含 scope coverage 和 2.4 warning suppression，新架构应由规则输出审计信息。
- 涉及旧文件：旧项目 `backend/app/services/ptr_report_evidence_builder.py`、`backend/app/services/ptr_report_check_service.py`、`backend/app/routers/report_self_check.py`。
- 新文件位置：`backend/app/application/ptr_compare_usecase.py`、`backend/app/api/routes_ptr_compare.py`、`backend/tests/application/test_ptr_compare_usecase.py`、`backend/tests/api/test_ptr_compare_api.py`。
- 需要实现：保存 PTR 和报告文件，解析 `PTRDocument` 和 `ReportDocument`，运行 scope、条款、表格、参数和 diff 规则，聚合结果，接入 `POST /api/tasks/ptr-compare`。
- 不允许做：不复活旧同步 PTR API；不在 service 层压制 findings；不把 report-check 结果模型硬套为 PTR 唯一模型。
- 测试要求：运行 `cd backend && python -m pytest tests/application/test_ptr_compare_usecase.py tests/api/test_ptr_compare_api.py`，覆盖成功、缺 PTR、缺报告、损坏 PDF、范围缺失、结果查询。
- 验收标准：Done when PTR 比对 API 可双文件上传、轮询、取结果。
- 完成状态：[ ]

## T31：实现 JSON 导出
- 目标：实现任务结果 JSON 导出。
- 背景：结构化 JSON 是必需输出，且应直接来自统一任务结果 schema。
- 涉及旧文件：旧项目 `backend/app/models/report_self_check.py`、旧前端 `frontend/src/types/reportSelfCheck.ts`。
- 新文件位置：`backend/app/infrastructure/export/json_exporter.py`、`backend/app/api/routes_tasks.py`、`backend/tests/infrastructure/test_json_exporter.py`、`backend/tests/api/test_export_api.py`。
- 需要实现：`GET /api/tasks/{task_id}/export?format=json`，返回任务结果 JSON 文件或 JSON response；包含 task、summary、check_results、findings、diagnostics、input_files。
- 不允许做：不重新计算业务结果；不隐藏 WARN/INFO；不导出临时内部对象；不修改任务结果。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/test_json_exporter.py tests/api/test_export_api.py`，覆盖报告任务、PTR 任务、任务不存在、未完成任务。
- 验收标准：Done when JSON 导出和结果查询内容一致。
- 完成状态：[ ]

## T32：实现 PDF 导出
- 目标：实现基于新 schema 的 PDF 导出。
- 背景：旧前端 `reportPdfExport.ts` 通过隐藏 iframe 打印 HTML，保留了封面、汇总、明细、系统诊断等信息架构；新架构先把该信息架构迁移为后端 export formatter，前端导出按钮在 T38 接入。
- 涉及旧文件：旧项目 `frontend/src/export/reportPdfExport.ts`、`frontend/tests/reportPdfExport.test.mjs`。
- 新文件位置：`backend/app/infrastructure/export/pdf_exporter.py`、`backend/tests/infrastructure/test_pdf_exporter.py`、`backend/app/api/routes_tasks.py`。
- 需要实现：基于 `CheckResult`、`Finding`、PTR diff 和 diagnostics 生成 PDF 文件；接入 `format=pdf`；输出中文标题、摘要、ERROR/WARN/INFO、证据和页码；保留可测试的中间 HTML 或文档结构。
- 不允许做：不在导出 formatter 中改变 severity；不只导出错误而丢失审计信息，除非有明确选项；不依赖浏览器手工操作作为唯一测试。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/test_pdf_exporter.py tests/api/test_export_api.py`，覆盖 PDF/HTML 关键文本、系统诊断、PTR scope、空 finding。
- 验收标准：Done when PDF 导出可重复测试，内容来自新结果 schema。
- 完成状态：[ ]

## T33：实现 Excel 导出
- 目标：实现 XLSX 导出。
- 背景：旧代码未发现 Excel 导出实现，但 `docs/known-requirements.md` 将其列为待实现/需确认输出；新任务按目标补齐导出 adapter。
- 涉及旧文件：无可迁移 Excel 旧实现；参考旧 `frontend/src/export/reportPdfExport.ts` 的章节结构和新 `Finding` schema。
- 新文件位置：`backend/app/infrastructure/export/excel_exporter.py`、`backend/tests/infrastructure/test_excel_exporter.py`、`backend/app/api/routes_tasks.py`。
- 需要实现：`format=xlsx`；至少包含 Summary、CheckResults、Findings、Evidence、PTRDiff 或 TableDiff sheet；保留中文列名、任务 ID、文件名、页码、expected/actual。
- 不允许做：不编造 Excel 旧实现；不把导出字段写死为某一条规则；不要求人工打开 Excel 作为唯一验收。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/test_excel_exporter.py tests/api/test_export_api.py`，用 openpyxl 或等价库读取 workbook 并断言 sheet 和关键单元格。
- 验收标准：Done when XLSX 可通过自动化测试读取，字段覆盖报告和 PTR 结果。
- 完成状态：[ ]

## T34：重做前端 Dashboard
- 目标：实现新前端工作台 Dashboard。
- 背景：旧 `ReportSelfCheckPage.tsx` 是单页工作台，新架构需要第一屏直接呈现可用功能入口，不做营销页。
- 涉及旧文件：旧项目 `frontend/src/pages/ReportSelfCheckPage.tsx`、`frontend/src/styles.css`。
- 新文件位置：`frontend/src/features/dashboard/DashboardPage.tsx`、`frontend/src/app/App.tsx`、`frontend/src/styles/`、`frontend/src/shared/components/`。
- 需要实现：报告自检入口、PTR 比对入口、最近任务占位、状态统计占位、深色玻璃拟态视觉方向、响应式布局。
- 不允许做：不展示虚假统计；不实现业务判断；不做大幅营销 hero；不把所有流程塞回一个巨型组件。
- 测试要求：运行 `cd frontend && npm run build`；若有组件测试，运行 Dashboard 渲染测试；用浏览器或截图检查桌面和窄屏无重叠。
- 验收标准：Done when Dashboard 可作为首屏工作台，入口清晰，构建通过。
- 完成状态：[ ]

## T35：重做报告自检页面
- 目标：实现报告自检上传和任务视图。
- 背景：旧页面支持单 PDF 上传、drag/drop、任务轮询和 localStorage 恢复；新页面应拆分组件并接新 API。
- 涉及旧文件：旧项目 `frontend/src/pages/ReportSelfCheckPage.tsx`、`frontend/src/api/reportSelfCheck.ts`。
- 新文件位置：`frontend/src/features/report-check/ReportCheckPage.tsx`、`ReportUploadPanel.tsx`、`ReportTaskProgress.tsx`、对应测试。
- 需要实现：单 PDF 选择、拖拽上传、创建 report-check 任务、展示 task id、进度、日志、错误和结果入口。
- 不允许做：不调用旧 `/api/report-self-check`；不在前端解析 PDF；不在上传前伪造结果。
- 测试要求：运行 `cd frontend && npm run build`；组件测试覆盖文件选择、非 PDF 提示、提交 disabled/loading、API 错误。
- 验收标准：Done when 报告自检页面能通过新 API client 创建任务并显示任务状态。
- 完成状态：[ ]

## T36：重做 PTR 比对页面
- 目标：实现 PTR 与报告双文件上传和任务视图。
- 背景：旧页面支持 PTR+报告双文件和 PTR 范围结果展示，新页面应独立为 feature。
- 涉及旧文件：旧项目 `frontend/src/pages/ReportSelfCheckPage.tsx`、`frontend/src/api/reportSelfCheck.ts`、旧结果组件中的 PTR scope 展示。
- 新文件位置：`frontend/src/features/ptr-compare/PtrComparePage.tsx`、`PtrUploadPanel.tsx`、`PtrTaskProgress.tsx`、对应测试。
- 需要实现：PTR PDF 和报告 PDF 双文件输入、提交校验、创建 ptr-compare 任务、显示任务状态、错误和结果入口。
- 不允许做：不允许缺任一文件提交；不调用旧 PTR API；不在前端做条款比对。
- 测试要求：运行 `cd frontend && npm run build`；组件测试覆盖缺 PTR、缺报告、非 PDF、API 错误、loading。
- 验收标准：Done when PTR 比对页面能通过新 API client 创建任务并进入轮询。
- 完成状态：[ ]

## T37：重做结果展示组件
- 目标：实现统一结果展示组件。
- 背景：旧 `CheckResultCard`、`FindingsList`、`OverallSummary` 等组件保留了信息架构，新结果模型变为统一 Finding 和 CheckResult。
- 涉及旧文件：旧项目 `frontend/src/components/report-self-check/CheckResultCard.tsx`、`CheckDetailsTable.tsx`、`FindingsList.tsx`、`OverallSummary.tsx`、`display.ts`。
- 新文件位置：`frontend/src/features/results/ResultSummary.tsx`、`FindingList.tsx`、`CheckResultCard.tsx`、`PtrDiffView.tsx`、`TableDiffView.tsx`、`frontend/src/shared/types/`。
- 需要实现：summary、ERROR/WARN/INFO 筛选、CheckResult 卡片、Finding 列表、证据页码、expected/actual、PTR 文本 diff、表格 diff。
- 不允许做：不根据前端字段重新判断 severity；不隐藏 SYSTEM_ERROR；不要求所有 metadata 都存在才渲染。
- 测试要求：运行 `cd frontend && npm run build`；组件测试覆盖 error/warn/info/pass、缺 metadata、PTR diff、表格 diff、空结果。
- 验收标准：Done when 统一结果组件能渲染报告自检和 PTR 比对结果。
- 完成状态：[ ]

## T38：重做导出按钮
- 目标：实现前端导出入口。
- 背景：旧前端有 PDF 导出按钮，新架构需要 JSON/PDF/XLSX 导出按钮调用统一 API。
- 涉及旧文件：旧项目 `frontend/src/export/reportPdfExport.ts`、旧 `ReportSelfCheckPage.tsx` 中导出按钮逻辑。
- 新文件位置：`frontend/src/features/export/ExportButtons.tsx`、`frontend/src/api/exportClient.ts`、对应测试。
- 需要实现：JSON、PDF、Excel 三个导出按钮；根据任务完成状态启用；下载文件；展示导出错误；支持报告和 PTR 任务。
- 不允许做：不在按钮内重新生成业务结果；不对未完成任务启用导出；不吞掉后端错误。
- 测试要求：运行 `cd frontend && npm run build`；组件测试覆盖 completed 启用、processing 禁用、下载 URL、API 错误。
- 验收标准：Done when 导出按钮仅依赖任务 ID 和格式调用新 API。
- 完成状态：[ ]

## T39：接入 API client 和轮询
- 目标：实现前端统一 API client 和任务轮询。
- 背景：旧前端每 2 秒轮询任务并按模式恢复 last task，新架构需要对 `/api/tasks/*` 做类型化封装。
- 涉及旧文件：旧项目 `frontend/src/api/reportSelfCheck.ts`、`frontend/src/types/reportSelfCheck.ts`、`frontend/src/pages/ReportSelfCheckPage.tsx`。
- 新文件位置：`frontend/src/api/tasksClient.ts`、`frontend/src/shared/types/task.ts`、`frontend/src/shared/hooks/useTaskPolling.ts`、对应测试。
- 需要实现：创建报告任务、创建 PTR 任务、查询任务、取结果、导出；轮询 pending/processing，completed/error 停止；错误归一化；可选 localStorage 恢复。
- 不允许做：不调用旧 API；不手写与后端冲突的状态枚举；不无限轮询已失败任务。
- 测试要求：运行 `cd frontend && npm run build`；hook/client 测试覆盖 pending 到 completed、error 停止、网络错误、轮询取消。
- 验收标准：Done when 报告自检和 PTR 页面都复用同一 task client。
- 完成状态：[ ]

## T40：Golden File 测试
- 目标：建立分层 Golden File 测试。
- 背景：旧测试引用本机 `素材/` 路径，不适合新项目复现；新架构需要受控 fixture 和 approved snapshot。
- 涉及旧文件：旧项目 `backend/tests/test_pdf_document_loader.py`、`test_report_evidence_builder.py`、`test_ptr_report_evidence_builder.py`、`test_report_self_check_service.py`、`test_ptr_report_check_service.py`、`frontend/tests/reportPdfExport.test.mjs`。
- 新文件位置：`backend/tests/golden/`、`backend/tests/fixtures/`、`docs/golden-files.md`、必要的测试工具脚本。
- 需要实现：定义 fixture 目录、snapshot 目录、fixture hash 记录、更新流程；覆盖 `ParsedPdf`、`ReportDocument`、`PTRDocument`、C01-C11 findings、PTR findings、导出结构。
- 不允许做：不直接依赖用户机器 `素材/`；不自动覆盖 golden；不把 live OCR/LLM 输出写入稳定 golden；不修改原始 PDF。
- 测试要求：运行 `cd backend && python -m pytest tests/golden`；故意变更 snapshot 时应失败并显示 diff。
- 验收标准：Done when golden 测试可复现，更新机制需要显式命令和人工 review。
- 完成状态：[ ]

## T41：端到端验收脚本
- 目标：提供报告自检和 PTR 比对的端到端验收。
- 背景：新项目需要验证上传、任务、轮询、结果、导出和前端展示闭环，不能只靠单元测试。
- 涉及旧文件：旧项目 `backend/tests/test_report_self_check_api.py`、`backend/tests/test_ptr_report_check_api.py`、旧前端上传与轮询代码。
- 新文件位置：`scripts/e2e-report-check.sh`、`scripts/e2e-ptr-compare.sh`、`frontend/e2e/` 或 `tests/e2e/`、`docs/e2e-acceptance.md`。
- 需要实现：启动后端和前端测试环境，上传受控 fixture，轮询任务完成，断言结果 schema，调用 JSON/PDF/XLSX 导出，前端页面基本浏览器验收。
- 不允许做：不使用生产旧素材路径；不依赖人工点击作为唯一验收；不在脚本里静默忽略失败；不修改 golden。
- 测试要求：运行 `bash scripts/e2e-report-check.sh` 和 `bash scripts/e2e-ptr-compare.sh`；前端 e2e 命令按项目实际配置执行。
- 验收标准：Done when 两条 e2e 路径均可一键运行并失败即返回非零退出码。
- 完成状态：[ ]

## T42：清理旧 Electron / python_backend / src/renderer 到 legacy 或废弃说明
- 目标：完成旧主线废弃或隔离说明。
- 背景：`docs/legacy-inventory.md` 已确认历史 Electron 和 `python_backend/` 未检出或不进入新架构，最后需要给后续维护者明确说明。
- 涉及旧文件：旧项目历史路径 `python_backend/`、`src/main/`、`src/renderer/`、根 Electron `package.json`、`start.sh`，当前可见状态以 `docs/legacy-inventory.md` 为准。
- 新文件位置：`docs/legacy-deprecation.md`，如当前项目存在 legacy 目录则更新 `legacy/README.md`。
- 需要实现：列出不迁移路径、不迁移原因、如后续找回旧文件应如何只抽业务规则和测试样例、旧 API 兼容策略、最终新入口。
- 不允许做：不删除当前项目重要文件；不声称未检出的旧文件已审计；不把废弃路径重新接入构建；不修改旧项目。
- 测试要求：运行 `test -f docs/legacy-deprecation.md`；运行 `rg "python_backend|src/main|src/renderer|Electron|/api/report-self-check" docs/legacy-deprecation.md`。
- 验收标准：Done when 旧主线去向清楚，后续任务不会误把 Electron 或历史 `python_backend` 当新架构入口。
- 完成状态：[ ]
