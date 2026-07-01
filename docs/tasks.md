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
- 新文件位置：`backend/app/domain/evidence_package.py`、`backend/app/infrastructure/audit/evidence_package_writer.py`、`backend/tests/domain/test_evidence_package_models.py`、`backend/tests/infrastructure/audit/test_evidence_package_writer.py`。
- 需要实现：`EvidencePackage`，每个任务写入 `runtime/codex_audit/{task_id}/`，只包含 candidate findings、check result 摘要、evidence、允许的原文片段和必要 asset refs。
- 不允许做：不写入旧项目目录；不暴露整个源码树；不修改原始上传文件；不把 raw PDF 作为默认 evidence package 交给 Codex。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/audit/test_evidence_package_writer.py -v`。
- 验收标准：Done when writer 使用 `tmp_path` 测试通过，路径被限制在 audit runtime 目录，输出 JSON schema 稳定。
- 完成状态：[x]

### T-CODEX-03：FakeCodexRunner / CodexCliRunner 接口
- 目标：建立可替换 runner 接口和 fake/real 两种实现。
- 背景：单元测试不能调用真实 Codex；真实 CLI 只能在受控运行时和手动验收中启用。
- 新文件位置：`backend/app/infrastructure/codex/runner.py`、`backend/app/infrastructure/codex/fake_codex_runner.py`、`backend/app/infrastructure/codex/codex_cli_runner.py`、`backend/tests/infrastructure/codex/test_fake_codex_runner.py`、`backend/tests/infrastructure/codex/test_codex_cli_runner.py`。
- 需要实现：runner protocol、`FakeCodexRunner` 固定输出、`CodexCliRunner` 命令构造、read-only sandbox、工作目录、timeout、stdout/stderr 保存和 exit code 处理。
- 不允许做：不在测试中调用真实 Codex；不允许 runner 接收项目根目录作为默认上下文；不允许写源码文件。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/codex -v`。
- 验收标准：Done when fake runner 可注入，real runner 命令参数可测试，timeout/nonzero 能转成错误结果。
- 完成状态：[x]

### T-CODEX-04：PromptBuilder 和 JSON schema
- 目标：为 Codex review 生成受控 prompt 和 output schema。
- 背景：Codex 只能基于 evidence package 输出 JSON，不得补造标准、字段含义或文件路径。
- 新文件位置：`backend/app/infrastructure/codex/prompt_builder.py`、`backend/app/infrastructure/codex/schemas/`、`backend/tests/infrastructure/codex/test_prompt_builder.py`、`backend/tests/infrastructure/codex/test_codex_review_output_schema.py`。
- 需要实现：按 review target 生成 prompt，声明 allowed evidence refs、输出 `confirm/refute/uncertain/add_finding` schema，禁止自由文本作为最终结构。
- 不允许做：不把整个 CheckResult JSON 原样无限制塞入 prompt；不包含项目源码；不允许 prompt 要求 Codex 修改文件。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/codex/test_prompt_builder.py tests/infrastructure/codex/test_codex_review_output_schema.py -v`。
- 验收标准：Done when prompt 包含安全边界、schema、target 和 evidence refs，且不包含未授权路径。
- 完成状态：[x]

### T-CODEX-05：OutputParser 和失败 fallback
- 目标：解析 Codex JSON 输出并提供失败降级。
- 背景：Codex 输出不可直接信任，必须 schema validate；失败不能阻断主核对流程。
- 新文件位置：`backend/app/infrastructure/codex/output_parser.py`、`backend/tests/infrastructure/codex/test_output_parser.py`。
- 需要实现：解析 stdout/raw JSON，校验 `CodexReviewResult`，处理 invalid JSON、schema invalid、timeout、stderr、非零退出，统一产生 `CodexReviewStatus.failed`。
- 不允许做：不吞掉失败原因；不把解析失败伪装成 `uncertain`；不删除 deterministic finding。
- 测试要求：运行 `cd backend && python -m pytest tests/infrastructure/codex/test_output_parser.py tests/infrastructure/codex/test_codex_cli_runner.py -v`。
- 验收标准：Done when completed/failed/skipped 路径均有测试，错误中保留 stdout/stderr/raw output ref。
- 完成状态：[x]

### T-CODEX-06：PTRCompareUseCase 接入 CodexAuditService
- 目标：在 PTR 比对用例中接入运行时 Codex 审核。
- 背景：PTR clause/table/parameter/scope 复杂语义需要 auditor 复核，但不能替代规则候选 findings。
- 新文件位置：`backend/app/application/codex_audit_service.py`、`backend/app/application/ptr_compare_usecase.py`、`backend/tests/application/test_ptr_compare_codex_audit.py`。
- 需要实现：对 PTR clause semantic review、table candidate ambiguity review、parameter semantic review、numeric/segmented threshold review、scope filter review 生成 evidence package 并附加 `codex_reviews`。
- 不允许做：不继续扩展 numeric semantic；不调用真实 Codex；不在 router 中写审核逻辑；不删除原始 PTR findings。
- 测试要求：运行 `cd backend && python -m pytest tests/application/test_ptr_compare_codex_audit.py -v`，并按影响范围运行 PTR usecase 测试。
- 验收标准：Done when FakeCodexRunner 可确认/refute/uncertain/add_finding，最终 `CheckResult` 同时保留 deterministic finding 和 Codex review。
- 完成状态：[x]

### T-CODEX-07：ReportCheckUseCase 接入 CodexAuditService
- 目标：在报告自检用例中接入运行时 Codex 审核。
- 背景：C02/C03/C04/C05/C06/C07 的标签、照片、日期和特殊检验结果语境需要 auditor 复核。
- 新文件位置：`backend/app/application/report_check_usecase.py`、`backend/tests/application/test_report_check_codex_audit.py`。
- 需要实现：对 C02 标签字段、C03 日期格式和值、C04 样品描述 vs 标签、C05 照片 caption、C06 中文标签 caption、C07 特殊检验结果语境生成审核目标并附加 `codex_reviews`。
- 不允许做：不修改 C01-C11 规则文件职责；不在前端做复核；不调用真实 Codex；不删除原始 finding。
- 测试要求：运行 `cd backend && python -m pytest tests/application/test_report_check_codex_audit.py -v`，并按影响范围运行报告 usecase 测试。
- 验收标准：Done when 报告自检结果能展示规则初判和 Codex 审核意见两层证据。
- 完成状态：[x]

### T-CODEX-08：前端展示 Codex review
- 目标：前端展示“规则初判 + Codex 审核意见”。
- 背景：前端只能展示后端结果，不能重新计算审核结论。
- 新文件位置：`frontend/src/entities/finding/types.ts`、`frontend/src/features/report-check/components/ReportResults.tsx`、`frontend/src/features/ptr-compare/components/PTRResults.tsx`、相关类型和组件测试。
- 需要实现：类型支持 `codex_reviews`，Finding 卡片展示 Codex verdict/status/summary，失败 review 显示诊断但不阻断结果。
- 不允许做：不在前端调用 Codex；不根据前端字段重新判断 severity；不隐藏 deterministic finding。
- 测试要求：运行 `cd frontend && npm run build`，并运行相关组件/typecheck 测试。
- 验收标准：Done when UI 能区分规则初判、Codex confirm/refute/uncertain/add_finding 和 failed review。
- 完成状态：[x]

### T-CODEX-09：真实 Codex CLI 手动验收
- 目标：在受控样例上手动验收真实 Codex CLI runtime auditor。
- 背景：真实 Codex 不进入单元测试，只能在专门验收任务中启用。
- 新文件位置：`docs/codex-cli-manual-validation.md`、`scripts/run-codex-cli-audit-smoke.sh`、`backend/tests/integration/test_codex_cli_manual.py` 或等价验收记录。
- 需要实现：选择受控 fixture，生成 `runtime/codex_audit/{task_id}/`，运行真实 `codex exec` read-only sandbox，保存 evidence package、prompt、JSON 输出、timeout、stdout/stderr 和 fallback 结果。
- 不允许做：不修改旧项目或新项目源码；不使用未审查原始素材；不把真实 Codex 输出写入稳定 Golden expected；不声称自动化测试已覆盖真实 Codex。
- 测试要求：手动运行并记录命令、输入、输出和结果；自动化仍只依赖 fake runner。
- 验收标准：Done when 手动记录证明真实 Codex CLI 能在只读 sandbox 中基于 evidence package 产出 schema JSON，失败时可降级。
- 子任务状态：
  - T-CODEX-09A：建立 gated/manual harness，默认不调用真实 Codex。完成状态：[x]
  - T-CODEX-09B：用户显式运行真实 Codex CLI 并记录结果。完成状态：[x]
- 完成状态：[x]

### T-CODEX-10：Codex audit 本地运行时配置与依赖装配
- 目标：历史阶段为通过环境变量显式启用 fake 或真实 Codex CLI runtime auditor；T-CODEX-MANDATORY-01 后产品运行路径已改为 mandatory Codex CLI，此处保留为迁移记录。
- 背景：T-CODEX-09 已验证真实 Codex CLI manual smoke；本任务把 `CodexAuditService` 通过配置装配到本地 API usecase 路径中。
- 新文件位置：`backend/app/application/codex_runtime_factory.py`、`backend/tests/application/test_codex_runtime_factory.py`、`backend/tests/api/test_codex_audit_dependencies.py`，并更新 `backend/app/core/config.py` 和 API 依赖。
- 需要实现：历史阶段已实现过 optional runtime factory；当前有效实现以 T-CODEX-MANDATORY-01 为准，产品 factory 默认构建 `CodexCliRunner`，旧 optional env 仅保留 deprecated 兼容字段。
- 不允许做：不调用 GPT API；不引入 OpenAI Responses/Chat API；不修改旧项目目录；不把 Codex CLI 逻辑写进 router；不让 Codex 读取项目源码；不改变 deterministic findings。
- 测试要求：运行 `cd backend && python -m pytest tests/ -v`、`cd frontend && npm run build`、`git diff --check`。
- 验收标准：历史验收为可选装配通过；当前最终语义以 T-CODEX-MANDATORY-01 为准。
- 完成状态：[x]

### T-CODEX-11：Codex audit 本地业务端到端验收
- 目标：历史阶段验证本地 Web 工具的业务端到端链路；T-CODEX-MANDATORY-01 后脚本和文档已改为 mandatory Codex CLI harness，不再提供 disabled/fake/codex-cli 用户模式。
- 背景：T-CODEX-10 已完成本地运行时配置和依赖装配；T-CODEX-11A 建立 gated local E2E harness；T-CODEX-11B 由用户显式开启真实 codex-cli 模式完成业务验收。
- 不允许做：不默认启用真实 Codex；不修改旧项目目录；不修改规则逻辑；不修改 router 业务逻辑；不把 Codex 审核逻辑写进 router；不让 Codex 覆盖 deterministic findings。
- 子任务状态：
  - T-CODEX-11A：本地业务端到端验收脚本和文档。完成状态：[x]
  - T-CODEX-11B：真实 codex-cli 本地业务端到端验收并记录结果。完成状态：[x]
- 完成状态：[x]

### T-CODEX-11A：本地业务端到端验收脚本和文档
- 目标：新增本地业务端到端验收说明和脚本；T-CODEX-MANDATORY-01 后脚本不再提供 disabled/fake/codex-cli 用户模式，改为 gated mandatory Codex CLI 验收入口。
- 背景：T-CODEX-10 已完成 Codex audit 本地运行时配置与依赖装配；本任务提供业务验收入口，但不要求真实运行 Codex CLI。
- 新文件位置：`docs/codex-audit-local-e2e.md`、`scripts/run-codex-audit-local-e2e.sh`、`backend/tests/integration/test_codex_audit_local_e2e_artifacts.py`。
- 需要实现：文档覆盖 mandatory Codex CLI 本地业务验收、脚本参数、业务上传流程、`codex_reviews` 验收点、前端只展示不重算、安全边界和排查；脚本支持 `--help`、`--print-config`、上传 PTR/报告或报告自检任务、轮询结果并统计 `codex_reviews`。
- 不允许做：不调用真实 Codex；不修改旧项目目录；不修改规则逻辑；不修改 router 业务逻辑；不把 Codex 审核逻辑写进 router；不修改 C01-C11 或 PTR 规则算法。
- 测试要求：运行 `cd backend && python -m pytest tests/integration/test_codex_audit_local_e2e_artifacts.py -v`；按影响范围运行后端测试、前端 build 和 `git diff --check`。
- 验收标准：Done when 脚本默认安全、运行前需要显式 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1` gate、文档清楚说明 mandatory Codex CLI 业务验收和前端展示边界。
- 完成状态：[x]

### T-CODEX-11B：真实 codex-cli 本地业务端到端验收
- 目标：在本地业务 report-check 样本上显式启用真实 Codex CLI，验证后端通过 Codex audit runtime 生成可审计 `codex_reviews`。
- 背景：首次真实业务验收先后暴露 structured output schema 不兼容和 84 targets 超时问题；T-CODEX-12 完成 target 限流后，本次使用单个 C07 target 完成真实验收。
- 记录位置：`docs/current-status.md`、`docs/codex-audit-local-e2e.md`。
- 验收结果：`codex_reviews_count=1`，`succeeded=1`，`verdict=confirm`，`confidence=high`，`target_type=inspection_item`，`check_id=C07`，`finding_code=CONCLUSION_MISMATCH_002`，`failed_reviews_count=0`。
- 不允许做：不把真实 Codex 输出写入 Golden expected；不删除或覆盖 deterministic findings；不提交 runtime 生成文件；不默认启用 API 真实 Codex。
- 验收标准：Done when 用户显式运行 gated codex-cli local E2E，真实 Codex CLI 返回 succeeded review，deterministic findings 保留且 Codex review 只作为审核意见。
- 完成状态：[x]

### T-CODEX-12：Codex audit target 限流、筛选和分批审核
- 目标：避免本地真实 Codex CLI 一次处理过多审核 target，支持 target 限流、规则筛选和当前 batch 元数据。
- 背景：T-CODEX-11B 真实 report-check 验收已触达真实 Codex CLI；schema 兼容性修复后，84 个 targets 仍导致 `CODEX_TIMEOUT`。
- 新文件位置：`backend/app/application/codex_audit_targeting.py`，并更新 `backend/app/core/config.py`、`backend/app/application/*codex_evidence_builder.py`、`backend/app/application/codex_runtime_factory.py`、`scripts/run-codex-audit-local-e2e.sh` 和相关测试/文档。
- 需要实现：`CODEX_AUDIT_MAX_TARGETS_PER_BATCH`、include/exclude check IDs、included finding codes、priority check IDs；Report/PTR evidence builder 按配置筛选、排序并按 batch 发出；metadata 记录 `total_candidate_targets`、`emitted_targets`、`truncated`、`omitted_targets_count`、`target_offset`、`batch_index`、`batch_size`。历史 `CODEX_AUDIT_MAX_TARGETS_PER_TASK` 字段仅作兼容，不应作为产品漏审上限。
- 不允许做：不调用真实 Codex；不修改 C01-C11 或 PTR 规则逻辑；不修改 router 业务逻辑；不修改旧项目目录；不改变 deterministic findings；T-CODEX-12 本身不替代 T-CODEX-11B 真实验收。
- 测试要求：运行 `cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py tests/application/test_ptr_codex_evidence_builder.py tests/application/test_codex_runtime_factory.py tests/integration/test_codex_audit_local_e2e_artifacts.py -v`，并运行后端全量、前端 build、脚本 bash 语法和 `git diff --check`。
- 验收标准：Done when 默认每批最多 5 个 audit targets，batching 不漏审，脚本可传递限流/筛选环境变量，真实模式可用单 target 命令重新验收。
- 完成状态：[x]

### T-CODEX-MANDATORY-01：Codex CLI 必须审核的运行架构
- 目标：将产品运行路径从 optional Codex audit 纠偏为 mandatory Codex CLI audit。
- 背景：T-CODEX-09/10/11/12 已证明真实 Codex CLI 可在受控 workspace、read-only sandbox、output schema 和 batch 限制下运行；但旧架构仍允许默认关闭、fake 用户模式和 runtime failure 后 completed。
- 涉及文件：`backend/app/core/config.py`、`backend/app/application/codex_runtime_factory.py`、`backend/app/application/report_check_usecase.py`、`backend/app/application/ptr_compare_usecase.py`、`backend/app/application/*codex_evidence_builder.py`、`backend/app/infrastructure/codex/*`、前端 Codex review 展示、脚本和文档。
- 需要实现：默认构建 `CodexCliRunner`；废弃产品路径的 `CODEX_AUDIT_ENABLED` / `CODEX_AUDIT_BACKEND` / `CODEX_AUDIT_ALLOW_REAL_EXECUTION`；Fake runner 仅用于测试注入；Codex runtime failure 使 task failed；uncertain 作为 completed 人工复核；规则 findings 明确为 candidate；batch size 不得导致漏审。
- 不允许做：不调用 GPT API；不引入 OpenAI Responses/Chat API；不调用真实 Codex CLI 做自动测试；不修改旧项目目录；不继续 C04/C05/C06/C07 业务规则细化。
- 测试要求：运行 targeted backend tests、`cd backend && python -m pytest tests/ -v`、`cd frontend && npm run build`、`git diff --check`。
- 验收标准：Done when API/product factory 默认装配 Codex CLI；Report/PTR usecase 遇到 failed/skipped review 或 service exception 会 task failed；Prompt 明确 Codex 是 mandatory final auditor；脚本和文档不再推荐 disabled/fake 用户模式。
- 完成状态：[x]

### T-CODEX-MANDATORY-02：Codex verdict finalization 与全候选 target 覆盖修复
- 目标：将 Codex verdict 收口为稳定 final status，并修复 mandatory audit 下 C04/C05/C06/C09 candidate target 覆盖不足的问题。
- 背景：用户真实运行 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07` 的本地业务验收后，Codex runtime 成功返回 22 条 succeeded review，但结果仍显示候选 `error=54`，且非 C07 finding `final_status=null`，容易误读为完整最终错误。
- 涉及文件：`backend/app/application/codex_audit_finalization.py`、`backend/app/application/report_check_usecase.py`、`backend/app/application/ptr_compare_usecase.py`、`backend/app/application/report_codex_evidence_builder.py`、`backend/app/domain/result.py`、前端结果展示和 Codex 文档。
- 需要实现：`confirm/refute/uncertain/add_finding` 映射到 `confirmed/refuted/manual_review_required/suggested_additional_finding`；summary 增加 candidate/final/refuted/manual/out-of-scope 计数；targeted validation 标记 `audit_scope=targeted`；full mandatory audit 不允许 required candidate 缺 review 或 `final_status`；C04/C05/C06/C09 生成逐条 finding target；summary target 标记 `summary_only`。
- 不允许做：不调用真实 Codex CLI；不调用 GPT/OpenAI API；不修改旧项目目录；不继续 C04/C05/C06/C07/C09 业务规则细化；不让前端重新计算规则。
- 测试要求：运行 application targeted tests、API tests、后端全量、前端 build 和 `git diff --check`。
- 验收标准：Done when refuted candidate 不计入 confirmed errors，uncertain 进入人工复核，targeted validation 的未覆盖候选被标记为 out-of-scope，full mandatory audit 缺少 required review 会 task failed。
- 完成状态：[x]

### T-CODEX-MANDATORY-03：targeted summary 过滤、C04/C06 OCR 语义和未使用部件 finalization
- 目标：修复 C04/C05/C06/C09 targeted validation 暴露的 summary target 越界、C04/C06 OCR 语义误读和未使用部件被 Codex confirm 后计入最终错误的问题。
- 背景：用户真实运行 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C04,C05,C06,C09` 后，任务完成且 Codex runtime 全部 succeeded，但结果中仍包含 C01/C02/C03/C08/C10/C11 summary reviews；部分 C04/C06 confirm 实际只确认“OCR 未识别字段”，不是确认标签本体缺字段；备注为“本次检测未使用”的部件不应被确认为缺照片/缺标签。
- 涉及文件：`backend/app/application/report_codex_evidence_builder.py`、`backend/app/application/codex_audit_finalization.py`、`backend/app/infrastructure/codex/prompt_builder.py`、`backend/app/rules/report/common.py`、相关 application/codex tests 和 Codex 文档。
- 需要实现：targeted 模式下 summary targets 也必须遵守 include/exclude/finding-code filters；C04/C06 target metadata 明确 `evidence_has_label_image_crop`、`evidence_has_full_label_text`、`evidence_has_structured_label_fields`、`evidence_can_verify_label_content`；prompt 明确 OCR 未识别字段不等于标签缺字段；未使用部件 metadata 可归一化识别；finalization 对 Codex confirm 的未使用部件和不可验证标签内容防御性降级为 `manual_review_required` 并记录 diagnostic。
- 不允许做：不调用真实 Codex CLI；不调用 GPT/OpenAI API；不修改旧项目目录；不继续 C04/C05/C06 业务规则清理；不让前端重新计算规则。
- 测试要求：运行 application targeted tests、Codex prompt tests、API tests、后端全量、前端 build 和 `git diff --check`。
- 验收标准：Done when C04/C05/C06/C09 targeted request 不再产生非 included summary reviews，C04/C06 无标签图像/完整正文 OCR/结构化字段时不会被 finalization 计为 confirmed business error，未使用部件即使被 Codex confirm 也不会进入 `confirmed_errors_count`。
- 完成状态：[x]

### T-CODEX-MANDATORY-04：C04 label caption 与 matched label OCR 语义修复
- 目标：修复 C04 `SAMPLE_COMPONENT_LABEL_NOT_FOUND` 中 “中文标签样张 caption 存在，但当前 component 缺 matched label OCR 正文/结构化字段” 被 Codex confirm 后误进入最终问题的语义边界。
- 背景：T-CODEX-MANDATORY-03 后 C04/C05/C06/C09 targeted validation 主目标已达成，但真实样本仍有 2 条 C04 confirmed WARN：sample-row-3 推车和 sample-row-14 30m 触摸屏连接线缆都有中文标签样张 caption，Codex confirm 的实际是 OCR 未匹配字段，不是标签样张不存在。
- 涉及文件：`backend/app/application/report_codex_evidence_builder.py`、`backend/app/application/codex_audit_finalization.py`、`backend/app/infrastructure/codex/prompt_builder.py`、相关 application/codex tests 和 Codex 文档。
- 需要实现：C04/C06 evidence metadata 拆分 `matching_label_caption_candidates` 与 `matching_label_ocr_candidates`；只有当前 component 的 matched label OCR 有正文/结构化字段或图像证据时才允许 `evidence_can_verify_label_content=true`；C04 label-not-found 且 caption 存在但无 matched OCR 时即使 Codex confirm 也降级为 `manual_review_required`，记录 `CODEX_CONFIRMED_LABEL_MISSING_BUT_CAPTION_EXISTS`；prompt 明确 caption 存在不应确认标签样张缺失。
- 不允许做：不调用真实 Codex CLI；不调用 GPT/OpenAI API；不修改旧项目目录；不修改 C05/C06/C09 业务规则；不让前端重新计算规则。
- 测试要求：运行 application targeted tests、Codex prompt tests、API tests、后端全量、前端 build 和 `git diff --check`。
- 验收标准：Done when sample-row-3 / sample-row-14 caption-only fixture 不再被标记为可验证标签内容，无关 OCR 不会被当作 matched OCR，Codex confirm 的 C04 label-not-found + matching caption 不会得到 `final_status=confirmed`。
- 真实 targeted validation：用户已运行 C04/C05/C06/C09 targeted validation，结果 `task status=completed`、`targeted_reviews_count=39`、`codex_by_status={"succeeded": 39}`、`unexpected_summary_reviews_count=0`、`confirmed_findings_count=0`、`confirmed_errors_count=0`、`confirmed_c04_label_not_found_count=0`；本轮不是 full audit。
- 完成状态：[x]

### T-CODEX-MANDATORY-05A：Full mandatory audit 真实验收记录
- 目标：记录真实样本在未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS` 时的 full mandatory Codex audit 验收结果。
- 背景：T-CODEX-MANDATORY-01 至 04 已完成 mandatory audit 运行架构、finalization、targeted filtering、C04 caption/matched OCR 语义修复；需要确认 full audit 口径下所有 required candidate 都完成 Codex finalization。
- 涉及文件：`docs/current-status.md`、`docs/tasks.md`、`docs/codex-audit-local-e2e.md`、必要时更新 `docs/codex-cli-auditor-strategy.md`。
- 需要记录：真实样本、结果文件、未设置 include filters、`audit_scope=full`、`full_audit=true`、Codex review status/verdict 分布、candidate/finalization 计数、按 check_id 的 final status，以及旧 `summary.error_count` / `fail_count` 是 candidate 层统计。
- 不允许做：不修改 backend 业务代码；不修改 frontend；不调用真实 Codex；不修改旧项目目录；不继续证据增强或规则细化。
- 验收结果：用户已运行 full mandatory audit，结果 `task status=completed`、`audit_scope=full`、`full_audit=true`、`codex_reviews_count=57`、`codex_by_status={"succeeded":57}`、`codex_runtime_failure_count=0`、`null_final_status_count=0`、`unreviewed_required_findings_count=0`、`out_of_scope_findings_count=0`、`confirmed_errors_count=0`；仍有 `manual_review_required_count=34`。
- 完成状态：[x]

### T-CODEX-MANDATORY-05B：Final audit summary / UI 语义收口
- 目标：让后端 summary、前端标题区域和 local E2E 脚本优先展示 Codex final audit 语义，避免把旧 deterministic candidate 计数误读为最终错误。
- 背景：T-CODEX-MANDATORY-05A 的 full mandatory Codex audit 已真实跑通；当时 `confirmed_errors_count=0`、`manual_review_required_count=34`，但旧 `summary.error_count=44`、`fail_count=5` 容易被误读为最终失败。后续 T-CODEX-EVIDENCE-03B 已记录更新后的 full audit 结果。
- 涉及文件：`backend/app/domain/result.py`、`backend/app/application/codex_audit_finalization.py`、`backend/app/application/task_service.py`、报告/PTR 结果页类型和组件、`scripts/run-codex-audit-local-e2e.sh`、相关测试和文档。
- 需要实现：summary 增加 `audit_scope`、`full_audit`、`final_audit_status`；`final_audit_status` 支持 `passed`、`needs_manual_review`、`failed`、`audit_failed`；前端标题优先显示 Codex 审核完成/未完成，metric 使用确认错误、人工复核、已反驳候选、候选错误；local E2E 脚本打印 final audit counts 并把旧 `fail_count/error_count/warn_count` 标为 legacy deterministic counts。
- 不允许做：不删除旧字段；不调用真实 Codex；不修改旧项目目录；不继续 evidence enhancement 或规则细化；不让前端重新计算规则。
- 测试要求：运行 report/PTR usecase、API、后端全量、前端 build、脚本语法和 `git diff --check`。
- 验收标准：Done when 本轮 full audit 的 summary 可表达 `final_audit_status=needs_manual_review`，前端不会把 deterministic `fail_count=5` 显示为最终失败，脚本能输出 final audit counts。
- 完成状态：[x]

### T-CODEX-EVIDENCE-01：Manual review evidence enhancement
- 目标：增强 C04 标签样张 OCR 证据和 C07 full audit evidence，减少 full mandatory audit 中可由证据补齐解决的 `manual_review_required`。
- 背景：T-CODEX-MANDATORY-05A full audit 中仍有 34 条人工复核项，其中 C04=29，C07=5。人工核对确认 C04 多数不是 confirmed error，而是缺 matched label crop/OCR/structured fields；C07 item 142/149 targeted audit 可 refute，但 full audit 证据不完整。
- 涉及文件：`backend/app/application/report_codex_evidence_builder.py`、`backend/app/application/codex_audit_finalization.py`、`backend/app/infrastructure/codex/prompt_builder.py`、相关 application/codex tests 和状态文档。
- 需要实现：C04 target 包含 sample row、label caption、label crop/page ref、matched OCR text、structured fields 和 label field comparison；无 crop/OCR/structured fields 时标记证据不足并要求 Codex uncertain；unused C04/C05/C06 component 即使被 confirm 也 finalization 为 refuted；C07 target 包含首页符号说明、完整 InspectionItemGroup rows、actual conclusion candidates/provenance、group pages full text，并标记 complex matrix table 不按普通 C07 confirm。
- 不允许做：不修改旧项目目录；不调用真实 Codex CLI；不调用 GPT/OpenAI API；不改 UI；不把 C04/C07 重写为纯正则规则。
- 测试要求：运行 report evidence builder/report usecase、C07 rule、API、后端全量、前端 build 和 `git diff --check`。
- 验收标准：Done when C04 matched label evidence 和 C07 full group/page evidence 能进入 Codex evidence package，unused component 不进入 manual_review_required，complex matrix C07 confirm 被防御性降级为 manual review。
- 完成状态：[x]

### T-CODEX-EVIDENCE-02：C07 result token recovery 与 compact evidence 修复
- 目标：修复 C07 item 94 暴露出的 result token 抽取/归组不完整问题，并压缩 C07 evidence package，避免把 page_text 中已有“符合要求”的 target 继续作为普通 all-placeholder ERROR。
- 背景：T-CODEX-EVIDENCE-01 后 full audit 在 C07 item 94 batch 遇到 runtime failure，但 workspace 显示 item 94 的 `effective_test_results=["——","——"]` 与 page_text 中 12.4.2/12.4.4 的“符合要求”冲突；历史 targeted validation 已证明 item 94 应被 Codex refute。
- 涉及文件：`backend/app/domain/inspection_group.py`、`backend/app/infrastructure/report/inspection_item_group_builder.py`、`backend/app/infrastructure/report/inspection_table_extractor.py`、`backend/app/rules/report/c07_item_conclusion.py`、`backend/app/application/report_codex_evidence_builder.py`、`backend/app/infrastructure/codex/prompt_builder.py`、相关测试和文档。
- 需要实现：InspectionItemGroup 记录 original/recovered effective results、recovered token provenance 和 diagnostics；C07 使用 recovered results 重新推导 expected，无法稳定恢复时输出 WARN `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN`；C07 evidence 改为 compact rows、recovery metadata 和 item 附近 page_text excerpt。
- 不允许做：不处理 Codex usage limit；不新增 `CODEX_USAGE_LIMIT_EXCEEDED`；不调用真实 Codex CLI；不调用 GPT/OpenAI API；不修改旧项目目录；不改 C04/C05/C06；不改 UI。
- 测试要求：运行 inspection group builder、C07 rule、report evidence builder/report usecase、API、后端全量、前端 build 和 `git diff --check`。
- 验收标准：Done when item 94/33/41/149 fixtures 不再生成普通 all-placeholder C07 ERROR，uncertain recovery 输出 WARN，C07 evidence package 不再携带整页 page_text/source_rows/complete_rows 重复结构。
- 完成状态：[x]

### T-CODEX-EVIDENCE-03：C07 extraction-uncertain finalization 与 complex matrix 语义修复
- 目标：修复 C07 targeted validation 暴露的 finalization 语义问题：extraction uncertainty 被 Codex confirm 不应计为 confirmed finding；item 59 复杂矩阵表不应按普通 C07 confirmed error。
- 背景：用户运行 C07 targeted validation task `4380cdc8-ea82-4413-92ce-ba3370ec3f0e`，结果中 10 条 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` WARN 被 confirm 后误计为 confirmed；item 59 的 `CONCLUSION_MISMATCH_002` 被 confirm 为唯一 confirmed error，但历史 targeted validation 显示 item 59 属于多页复杂矩阵表/列映射歧义。
- 涉及文件：`backend/app/application/codex_audit_finalization.py`、`backend/app/rules/report/c07_item_conclusion.py`、`backend/app/application/report_codex_evidence_builder.py`、相关 tests 和文档。
- 需要实现：`CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` 在 Codex confirm/uncertain 时 final_status 进入 `manual_review_required`，保留 `codex_verdict` 审计痕迹并设置 `review_type=extraction_uncertainty`；C07 复杂漏电流/矩阵表输出 WARN `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX` 或被 target metadata 标记为 `complex_matrix_table=true`；普通 C07 business mismatch 仍可被 confirm 为 confirmed error。
- 不允许做：不调用真实 Codex CLI；不调用 GPT/OpenAI API；不修改旧项目目录；不改 C04/C05/C06/UI；不处理 usage limit。
- 测试要求：运行 C07 rule、report evidence builder/report usecase、API、后端全量、前端 build 和 `git diff --check`。
- 验收标准：Done when extraction uncertainty confirm 不计入 confirmed counts，item 59 complex matrix 不进入 confirmed error，simple C07 mismatch confirm 仍能进入 confirmed error。
- 真实 targeted validation：用户已运行结果文件 `runtime/codex_audit_local_e2e/004f23d9-bd93-4773-91c4-d1c72acf6208.result.json`，`CODEX_AUDIT_INCLUDED_CHECK_IDS=C07`，`final_audit_status=needs_manual_review`，`confirmed_findings_count=0`，`confirmed_errors_count=0`，`manual_review_required_count=12`，验证 extraction uncertainty 不再被归为 confirmed finding。
- 完成状态：[x]

### T-CODEX-EVIDENCE-03B：Full audit 真实验收记录
- 目标：记录 T-CODEX-EVIDENCE-03 后 full mandatory Codex audit 的真实验收结果，确认 finalization 语义在 full audit 口径下成立。
- 背景：T-CODEX-EVIDENCE-03 的 C07 targeted validation 已通过；需要确认未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS` 的 full audit 不再产生 confirmed final error。
- 结果文件：`runtime/codex_audit_local_e2e/53bbeec9-998b-4868-9627-00d9cc3b7ab0.result.json`。
- 验收结果：`task status=completed`、`audit_scope=full`、`full_audit=true`、`final_audit_status=needs_manual_review`、`candidate_findings_count=51`、`candidate_errors_count=33`、`confirmed_findings_count=0`、`confirmed_errors_count=0`、`refuted_findings_count=11`、`manual_review_required_count=40`、`out_of_scope_findings_count=0`、`unreviewed_required_findings_count=0`、`codex_reviews_count=57`、`codex_runtime_failure_count=0`。
- 结论：full mandatory Codex audit 运行通过，当前没有 confirmed final error；剩余 40 条为待复核项，其中 C04 标签字段证据不足 28 条、C07 检验项目结构化抽取不确定 12 条；C05/C06/C09 当前候选均已被 Codex refute。
- 下一步：做 evidence enhancement，而不是继续改 finalization。
- 完成状态：[x]

### T-CODEX-EVIDENCE-04：C04 label image crop / matched OCR evidence 增强
- 目标：增强 C04 Codex evidence，明确区分 label caption、label page image/crop、matched OCR text、structured fields 和是否足以验证当前 component 的标签字段内容。
- 背景：T-CODEX-EVIDENCE-03B full audit 后剩余 C04 `manual_review_required=28`；这些项不是 confirmed error，而是缺 matched label crop/OCR/structured fields，Codex 无法核验标签本体字段。
- 涉及文件：`backend/app/application/report_codex_evidence_builder.py`、`backend/app/application/codex_audit_finalization.py`、`backend/app/infrastructure/codex/prompt_builder.py`、相关 application/codex tests 和状态文档。
- 需要实现：C04 evidence 输出 `label_caption_candidate`、`matched_label_caption`、`label_page_number`、`label_image_ref`、`label_crop_ref`、`matched_label_text`、`matched_label_fields`、`matched_label_field_confidence`、`matched_label_ocr_source`、`unmatched_label_ocr_candidates` 和 verification flags；caption matching 覆盖真实样本部件名；只有 matched OCR/text/structured fields 足以验证当前 component 时才设置 `evidence_can_verify_label_content=true`；prompt 要求无 matched OCR/crop/structured fields 时 `uncertain`。
- 不允许做：不调用真实 Codex CLI；不调用 GPT/OpenAI API；不修改旧项目目录；不修改 C07；不修改 C05/C06 规则算法；不修改 router/frontend/UI；不提交 runtime crop 文件。
- 测试要求：运行 report evidence builder/report usecase、PromptBuilder、API、后端全量、前端 build 和 `git diff --check`。
- 验收标准：Done when caption-only、caption+bbox no OCR、matched OCR fields match/missing/unrelated OCR、unverifiable confirm defensive finalization 和 prompt guidance 均有测试覆盖；本任务不要求真实 Codex validation。
- 完成状态：[x]

### T-CODEX-EVIDENCE-04B：C04 matched label OCR 语义、verification 判定和 caption selector 修正
- 目标：修正 T-CODEX-EVIDENCE-04 后 C04 targeted validation 暴露的 metadata 假阳性，避免把照片页/page text 当成 matched label OCR，并修复 30m 触摸屏连接线缆 caption 误匹配。
- 背景：用户运行 C04 targeted validation task `8949ca23-07b6-4f7c-b39c-b428d83daa17`，结果 `completed`、`codex_reviews_count=35`、`confirmed_errors_count=0`、`refuted_findings_count=7`、`manual_review_required_count=28`。extract 显示 `has_matched_label_ocr_count=28`、`can_verify_label_content_count=28`，但 matched text 多为“检验报告照片页 / 照片和说明 / №5... / №6...”这类照片页文本，不是标签本体 OCR。
- 涉及文件：`backend/app/application/report_codex_evidence_builder.py`、`backend/app/infrastructure/codex/prompt_builder.py`、相关 application/codex tests 和 Codex 文档。
- 需要实现：拆分 `matched_label_page_text`、`matched_label_caption_text`、`matched_label_ocr_text`、`matched_label_fields`；`pdf_text_label_page` 等来源不得触发 `evidence_has_matched_label_ocr=true`；`evidence_can_verify_label_content=true` 只在真正标签本体 OCR 或 structured fields 可用时成立；caption selector 对完整 subject、型号、`30m`、`可选`、`连接线缆` 等特异 token 加权，分差不足时标记 `LABEL_CAPTION_MATCH_AMBIGUOUS`。
- 不允许做：不调用真实 Codex CLI；不调用 GPT/OpenAI API；不修改旧项目目录；不改 C07/C05/C06/UI；不接入新 OCR 服务。
- 测试要求：运行 report evidence builder/report usecase、PromptBuilder、API、后端全量、前端 build 和 `git diff --check`。
- 验收标准：Done when page text only 不再被视为 matched label OCR，真实 label OCR/fields 仍可验证，sample-row-14 选择 `№22 触摸屏连接线缆（30m）（可选） 中文标签样张`，ambiguous selector 不设置 matched caption，finalization 防御保持不变。
- 真实验收：用户已运行 C04 targeted validation task `4ec18d39-7dab-4478-b6c0-d6bc464fd2e7`，结果文件为 `runtime/codex_audit_local_e2e/4ec18d39-7dab-4478-b6c0-d6bc464fd2e7.result.json`；本轮 `audit_scope=targeted`、`final_audit_status=needs_manual_review`、`codex_reviews_count=35`、`confirmed_errors_count=0`、`refuted_findings_count=7`、`manual_review_required_count=28`、`out_of_scope_findings_count=16`、`unreviewed_required_findings_count=0`、`codex_runtime_failure_count=0`。C04 extract 显示 `has_matching_label_caption_count=35`、`has_matched_label_image_count=31`、`has_matched_label_crop_count=0`、`has_matched_label_ocr_count=0`、`has_matched_structured_fields_count=0`、`can_verify_label_content_count=0`；`evidence_has_matched_label_ocr_count` 与 `evidence_can_verify_label_content_count` 均从旧的 `28` 降为 `0`，sample-row-14 正确匹配 `№22` 30m 线缆标签样张，不再误匹配 `№8` 触摸屏。
- 完成状态：[x]

### T-CODEX-EVIDENCE-05：C04 label crop / OCR / VLM evidence
- 目标：为 C04 剩余 `manual_review_required` 提供真实 label crop、matched OCR、structured fields 或 VLM evidence，使标签字段缺失候选能进一步收敛到 `refute`、`confirm` 或更明确的人工复核原因。
- 背景：T-CODEX-EVIDENCE-04B 已证明 caption/page text 不再被误当成 matched OCR；当前 28 条 C04 `manual_review_required` 主要因为 `has_matched_label_crop_count=0`、`has_matched_label_ocr_count=0`、`has_matched_structured_fields_count=0`。
- 需要实现：定位中文标签样张区域，生成可审计 crop/page image reference，接入或复用 OCR/VLM evidence，输出稳定的 matched label text、structured fields、field provenance 和 confidence。
- 已实现：matched label caption 可根据上传后 source PDF 渲染 workspace 内 `items/*.png`；`EvidencePackageWriter` 写入 PNG 但不把 source PDF 绝对路径落入 `evidence_package.json`；`CodexAuditService` 将 image paths 传给 runner；`CodexCliRunner` 用 `codex exec --image items/...png` 提供图片输入；output schema 支持 `observed_label_fields`、`field_comparisons`、`visual_evidence_quality`；finalization 会保留视觉 metadata，并将 unreadable/wrong crop 的 confirm 防御性降级为 `manual_review_required`。
- 展示/导出后续问题：`c04_extract` 中 `component_name` / `sample_description_row` 仍不稳定；后续应补标准 metadata，例如 `component_id`、`component_name`、`sample_field_key`、`sample_field_value`。
- 测试要求：运行 report evidence builder/report usecase、Codex CLI runner/output parser/prompt builder、API、后端全量、前端 build 和 `git diff --check`。
- 验收说明：代码链路和 fake/monkeypatch 测试已完成；用户随后运行真实 C04 targeted visual validation `c1f421db-4757-4041-8b19-c88b8835a941`，`final_audit_status=passed`，35 条 C04 candidate 全部 refuted，confirmed/manual review/runtime failure 均为 0。
- 完成状态：[x]

### T-CODEX-EVIDENCE-05A：C04 visual review 输出 JSON Schema strict mode 修复
- 目标：修复 C04 visual audit 触发的 OpenAI/Codex structured output `invalid_json_schema`，让视觉 metadata schema 满足 strict required-property 约束。
- 背景：用户运行 C04 visual audit 任务 `7b20f4a4-e99e-42c3-9151-3d00b16c259c`，stderr 显示 `Invalid schema for response_format 'codex_output_schema'`，原因是 `observed_label_fields.properties` 包含 `batch_or_serial`，但 `required` 未覆盖全部 properties key。
- 涉及文件：`backend/app/infrastructure/codex/schemas/codex_review_output.schema.json`、`backend/app/infrastructure/codex/output_parser.py` 相关测试、`docs/current-status.md`、`docs/codex-audit-local-e2e.md`。
- 需要实现：所有带 `properties` 的 object 都满足 strict schema 要求，`metadata.required` 覆盖 `observed_label_fields`、`field_comparisons`、`visual_evidence_quality`；`observed_label_fields.required` 覆盖 `component_name`、`model`、`serial_number`、`batch_or_serial`、`production_date`、`expiration_date`；optional 值用 null union 表达。
- 不允许做：不处理 C04/C07 业务规则；不处理 usage limit；不调用真实 Codex CLI；不调用 GPT/OpenAI API；不修改旧项目目录。
- 测试要求：运行 Codex schema/parser/prompt tests、report usecase、API、后端全量、前端 build 和 `git diff --check`。
- 验收说明：Done when strict schema contract 测试通过，C04 visual review valid output 可被 schema/parser 接受；`7b20f4a4` 记录为 schema 合法性失败，不作为报告业务错误。
- 后续真实尝试记录：用户在 05A 后运行 C04 targeted visual audit，extract package 为 `runtime/codex_audit_local_e2e/extract_runs/20260626-225213-C04.tar.gz`；本轮未 completed，failed workspace 为 `backend/runtime/codex_audit/0ece4dd1-c2db-48b1-8cfa-efd21ea01a80/codex-report-0ece4dd1-c2db-48b1-8cfa-efd21ea01a80-C04-batch-6/input`，stderr 显示 Codex usage limit，非 `invalid_json_schema`，因此不能判断 C04 manual review 是否下降。
- 完成状态：[x]

### T-CODEX-EVIDENCE-05B：EVIDENCE-05 后 full mandatory audit 真实验收记录
- 目标：记录 C04 visual label audit 在 full mandatory audit 口径下的真实验收结果，确认 full audit 不再因 C04 标签证据不足停留在人工复核。
- 背景：T-CODEX-EVIDENCE-05 已通过 C04 targeted visual validation；需要确认未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS` 的 full audit 中，C04 视觉证据链同样生效，且 finalization 语义保持稳定。
- 涉及文件：`docs/current-status.md`、`docs/tasks.md`、`docs/codex-audit-local-e2e.md`、必要时更新 `docs/codex-cli-auditor-strategy.md`。
- 不允许做：不修改 backend 业务代码；不修改 frontend；不调用真实 Codex；不修改旧项目目录；不继续 C04 或 finalization 改动。
- 验收结果：用户已运行 full mandatory audit，结果文件为 `runtime/codex_audit_local_e2e/1958c184-567f-4c56-aaac-4a8c45913d1c.result.json`；本轮未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`，`audit_scope=full`、`full_audit=true`、`included_check_ids=[]`、`final_audit_status=needs_manual_review`、`unique_findings_count=51`、`codex_reviews_count=57`、`confirmed_findings_count=0`、`confirmed_errors_count=0`、`refuted_findings_count=39`、`manual_review_required_count=12`、`out_of_scope_findings_count=0`、`codex_runtime_failure_count=0`、`unreviewed_required_findings_count=0`。
- 结论：full mandatory Codex audit 运行通过；C04 35 条 candidate、C05 2 条、C06 1 条、C09 1 条均已 refuted；当前没有 confirmed final error，唯一剩余为 C07 12 条 `manual_review_required`。下一步应进入 C07 table visual evidence / row crop review，不应继续改 C04 或 finalization。
- 完成状态：[x]

### T-CODEX-EVIDENCE-06A：C07 table visual geometry provenance
- 目标：为 C07 table visual evidence 准备底层几何信息，只完成 table/cell/row/field bbox provenance。
- 背景：T-CODEX-EVIDENCE-05 后 full audit 已证明 C04/C05/C06/C09 均可被 refute，唯一剩余为 C07 12 条 `manual_review_required`，下一阶段需要让 Codex CLI 能看到检验项目表图像；06A 先打通几何来源，不生成图片。
- 涉及文件：`backend/app/infrastructure/pdf/pymupdf_parser.py`、`backend/app/infrastructure/report/inspection_table_extractor.py`、对应 infrastructure tests 和状态文档。
- 需要实现：PyMuPDF table 的 `cells` 坐标保存到 `PdfTable.metadata["cell_bboxes"]`；inspection item metadata 在存在 `cell_bboxes` 时写入 `visual_geometry.table_bbox`、`row_bbox` 和 `field_bboxes`，至少覆盖 `test_result`、`conclusion`、`remark`。
- 不允许做：不生成 C07 image evidence；不接入 `CodexAuditService`；不修改 prompt/schema/finalization；不运行真实 Codex CLI；不调用 GPT/OpenAI API；不修改旧项目目录；不修改 frontend/router；不改变 C07/C08/C10 规则输出。
- 测试要求：运行 PyMuPDF parser 目标测试、inspection table extractor 目标测试、两组 infrastructure tests、后端全量和 `git diff --check`。
- 验收标准：Done when 有 cell bbox 时 `PdfTable` 保留二维 bbox，有 cell bbox 的 `InspectionItem` 带 `visual_geometry`，无 bbox 时抽取行为保持不变。
- 完成状态：[x]

### T-CODEX-EVIDENCE-06B：C07VisualEvidenceBuilder 与 C07 图像证据生成
- 目标：基于 06A 的 `visual_geometry` 生成 C07 page/table/item group/result/conclusion/remark 图片 evidence，并交给现有 writer materialization 链路。
- 背景：06A 只准备几何 provenance；后续需要把这些 bbox 转成受控 workspace 内的 image refs，供 Codex CLI image input 视觉审核。
- 涉及文件：`backend/app/application/c07_visual_evidence.py`、`backend/app/application/report_codex_evidence_builder.py`、`backend/tests/application/test_report_codex_evidence_builder.py`、状态文档。
- 需要实现：新增 `C07VisualEvidenceBuilder`，从 `InspectionItemGroup.rows[].metadata.visual_geometry` 生成 page/table/item group/result/conclusion/remark 的 `EvidenceItem(source_type=IMAGE)`；C07 target metadata 写入 `c07_visual_evidence`、`evidence_has_c07_visual_input`、`visual_review_mode` 和 missing bbox reasons；无 bbox 时降级为 page-only image evidence；无 `source_pdf_path` 时不生成 image items 且记录 `source_pdf_path_missing`；item 59 或复杂矩阵标记使用 `complex_matrix_table` 视觉模式。
- 不允许做：不修改 prompt/schema/finalization；不改变 finalization 语义；不把 visual uncertainty 当 confirmed error；不调用真实 Codex CLI 自动测试；不调用 GPT/OpenAI API；不修改旧项目目录；不修改 frontend/router。
- 测试要求：运行 C07 visual target tests、report evidence builder tests、report check usecase、evidence package writer、Codex audit service tests、后端全量和 `git diff --check`。
- 验收标准：Done when C07 target 带 workspace-local image refs，image items 带 `codex_image_input=true` 与 `render_page_number/render_bbox` metadata，无 bbox 时仍可 page-only fallback，无 PDF 时只记录缺失原因，complex matrix 不被当作普通 row-only target，且不改变 C07 deterministic/finalization 语义。
- 完成状态：[x]

### T-CODEX-EVIDENCE-06C：C07 visual prompt guidance / fake validation
- 目标：让 06B 生成的 C07 image evidence 能 materialize 为 workspace-local PNG，确认 `CodexAuditService` 能收集 C07 PNG paths，确认 `CodexCliRunner` 会通过 `--image` handoff，并让 PromptBuilder 明确指导 Codex 使用 C07 page/table/row/column 图片 evidence 复核检验结果、单项结论、备注和续页行。
- 背景：06B 已生成 C07 image evidence items 和 target metadata；本阶段补齐 writer/service/runner/prompt 的基础设施测试，之后再做真实 C07 targeted validation。
- 涉及文件：`backend/app/infrastructure/audit/evidence_package_writer.py`、`backend/app/application/codex_audit_service.py`、`backend/app/infrastructure/codex/codex_cli_runner.py`、`backend/app/infrastructure/codex/prompt_builder.py`、相关 tests 和状态文档。
- 需要实现：C07 page/crop image item materialization；manifest relative image paths；缺 source PDF / invalid bbox diagnostics；service 将 C07 PNG 传给 runner；runner 多 `--image` 参数与缺失/越界图片拒绝；C07 visual prompt instructions；C04 prompt 不包含 C07 visual instructions。
- 不允许做：不改变 C07 finalization 语义；不运行真实 Codex CLI 自动测试；不运行 local E2E；不调用 GPT/OpenAI API；不修改 output schema；不修改旧项目目录；不修改 frontend/router；不修改 C04。
- 测试要求：运行 evidence writer、Codex audit service、Codex CLI runner、PromptBuilder、report evidence builder、report check usecase、后端全量和 `git diff --check`。
- 验收标准：Done when C07 image evidence 可写入 workspace-local PNG，service/runner/fake tests 证明 image paths 到达 runner 和 `codex exec --image` command，prompt 包含 C07 visual review instructions，且不改变 finalization。
- 完成状态：[x]

### T-CODEX-EVIDENCE-06D：C07 targeted visual audit 真实验收
- 目标：在真实样本上只跑 C07 targeted visual audit，验证 06A/06B/06C 的 C07 图像证据是否能降低 C07 `manual_review_required`。
- 背景：06C 已完成 C07 image evidence materialization、image-path handoff 和 prompt guidance；下一步需要用户显式运行真实 Codex CLI targeted validation。
- 建议命令口径：设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07`，不要先跑 full audit。
- 关注指标：C07 `manual_review_required` 是否从 12 下降，C07 `refute` 是否增加，`confirmed_errors_count` 是否仍为 0，`codex_runtime_failure_count` 是否为 0，image paths 是否进入 Codex run workspace。
- 重点 item：27、33、41、72、94、121、131、142、149、151，以及 item 3 / item 59 的特殊结构。
- 不允许做：不修改业务代码；不修改 finalization；不修改旧项目目录；不把 runtime 生成图片提交 git。
- 验收结果：用户已运行 C07 targeted visual audit，结果文件为 `runtime/codex_audit_local_e2e/2e7bbb93-3e7b-4477-8a5f-b1b25487fef0.result.json`，导出包为 `runtime/codex_audit_local_e2e/c07_visual_runs/20260628-122940.tar.gz`；本轮 `audit_scope=targeted`、`included_check_ids=["C07"]`、`final_audit_status=needs_manual_review`、`c07_findings_count=12`、`c07_reviews_count=12`、`confirmed_findings_count=0`、`confirmed_errors_count=0`、`refuted_findings_count=11`、`manual_review_required_count=1`、`codex_runtime_failure_count=0`、`unreviewed_required_findings_count=0`。
- 结论：C07 visual evidence 链路真实生效，item 3、27、33、41、72、94、121、131、142、149、151 被 Codex visual evidence refute；唯一剩余 manual review 是 item 59 `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX` / `complex_matrix_table`。真实 `codex exec` 已携带 C07 page/table/item-group/result/conclusion/remark `--image items/...` 输入，06A/06B/06C 的 geometry、PNG materialization 和 image handoff 被 targeted audit 验证。
- full audit 复验：用户随后运行 full mandatory audit，结果文件为 `runtime/codex_audit_local_e2e/8e23d5bc-64f5-43c1-a0c5-2e02597840f6.result.json`；本轮 `audit_scope=full`、`full_audit=true`、`included_check_ids=[]`、`final_audit_status=needs_manual_review`、`codex_reviews_count=57`、`confirmed_findings_count=0`、`confirmed_errors_count=0`、`refuted_findings_count=50`、`manual_review_required_count=1`、`codex_runtime_failure_count=0`、`unreviewed_required_findings_count=0`。
- full audit 结论：T-CODEX-EVIDENCE-06 full audit 复验通过；C04/C05/C06/C09 全部 refuted，C07 12 条中 11 条 refuted，当前全量审核仅剩 C07 item 33 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` 待人工复核，没有 confirmed final error。item 33 的视觉表格显示首行检验结果为“——”，其下续行“分类是 IPX0 或 IP0X 的 ME 设备不需要标记。”对应检验结果列可见“符合要求”；结构化结果仅保留“——”确有遗漏，需人工/视觉复核后判断，且单项结论“符合”与可见非空合格结果一致。
- 完成状态：[x]

### T-CODEX-EVIDENCE-06E：item 33 residual manual review closeout
- 目标：收口 full mandatory audit 中唯一剩余的 C07 item 33 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` manual review，提升视觉证据 refute 稳定性。
- 背景：T-CODEX-EVIDENCE-06 full audit 复验 `8e23d5bc-64f5-43c1-a0c5-2e02597840f6` 已证明当前没有 confirmed final error，51 条 candidate 中 50 条已 refuted；唯一剩余 item 33 是结构化抽取遗漏“符合要求”导致的 extraction-uncertain。
- 建议工作：比较 C07 targeted audit 与 full audit 中 item 33 的 evidence、prompt、image refs、row crop / continuation crop 和视觉裁决差异，确认是否缺少续行 crop、结果列 crop 或符号说明上下文。
- 不允许做：不改变 mandatory 原则；不把 extraction-uncertain 强行降级为通过；不调用 GPT/OpenAI API；真实 Codex 运行需用户显式触发；不修改旧项目目录。
- 诊断结果：新增 `scripts/compare-codex-c07-item-evidence.py` 后对比 targeted `2e7bbb93-3e7b-4477-8a5f-b1b25487fef0` 与 full `8e23d5bc-64f5-43c1-a0c5-2e02597840f6`，item 33 的 `allowed_evidence_refs`、`c07_visual_evidence`、materialized image files 和 visual review mode 归一化后一致；旧 prompt 缺少 extraction-uncertain refute 条件，verdict 漂移为 targeted `refute`、full `confirm`。
- 修复结果：C07 visual item group crop 可从续行字段 bbox fallback 取 union，不再只覆盖首行；C07 visual prompt 明确 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` 在视觉证据足以判断结论合理时应 `refute`，不能仅因结构化抽取遗漏存在就 `confirm/manual`，同一 group 续行“符合要求”应作为有效检验结果。
- 真实 targeted validation：用户已运行 C07 targeted validation，结果文件为 `runtime/codex_audit_local_e2e/a39b2841-e44d-4efd-a004-ae3147a2c1d6.result.json`，摘要文件为 `runtime/codex_audit_local_e2e/c07_06e_runs/20260628-182451/paste_to_chatgpt.md`；本轮 `audit_scope=targeted`、`included_check_ids=["C07"]`、`final_audit_status=passed`、`c07_findings_count=12`、`c07_reviews_count=12`、`confirmed_findings_count=0`、`confirmed_errors_count=0`、`manual_review_required_count=0`、`refuted_findings_count=12`、`codex_runtime_failure_count=0`、`unreviewed_required_findings_count=0`。
- 真实验收结论：T-CODEX-EVIDENCE-06E targeted validation 验收通过，item 33 residual manual review 已收口，C07 12 条 candidate 全部被 Codex visual evidence refute；当前 C07 targeted audit 无 confirmed error、无 manual review、无 runtime failure。当时下一步是执行 full mandatory audit 复验，目标为 `confirmed_errors_count=0`、`manual_review_required_count=0`、`refuted_findings_count=51`、`final_audit_status=passed`；实际 full audit 复验结果见下一条。
- full audit 复验：用户随后运行 full mandatory audit，结果文件为 `runtime/codex_audit_local_e2e/bf36101c-71a4-4f69-9df9-907ced1000cb.result.json`；本轮 `audit_scope=full`、`full_audit=true`、`final_audit_status=needs_manual_review`、`codex_reviews_count=57`、`candidate_findings_count=51`、`confirmed_findings_count=0`、`confirmed_errors_count=0`、`refuted_findings_count=50`、`manual_review_required_count=1`、`codex_runtime_failure_count=0`、`unreviewed_required_findings_count=0`。
- full audit 结论：当前没有 confirmed final error；C04/C05/C06/C09 已全部 refuted；C07 普通视觉复核项已基本收口；唯一剩余为 C07 item 59 `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX` / `warn`，Codex verdict 为 `uncertain`、confidence 为 `medium`。视觉证据显示 item 59 为 8.7 漏电流多页复杂矩阵，页内可见多项数值/占位结果且单项结论列为“符合”，但跨页续表与矩阵列映射仍需专门判读；`rule_context` 也标记 `complex_matrix_table=true`，因此不按普通 C07 直接裁决。保留 `manual_review_required` 符合安全口径，不应通过修改 finalization 强行让 item 59 passed。
- 验收标准：Done when 诊断 helper 可复用、row/field crop union 与 prompt 语义测试通过，且真实 C07 targeted validation 中 12 条 C07 candidate 全部 refuted、无 confirmed error、无 manual review、无 runtime failure。
- 完成状态：[x]

### T-CODEX-EVIDENCE-07：item 59 complex matrix specialized review
- 目标：为 C07 item 59 的 8.7 漏电流多页复杂矩阵表建立 specialized matrix review，复核矩阵列映射和跨页续表结构。
- 背景：T-CODEX-EVIDENCE-06E 后 full mandatory audit `bf36101c-71a4-4f69-9df9-907ced1000cb` 已没有 confirmed final error，51 条 candidate 中 50 条 refuted；唯一剩余为 C07 item 59 `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`，Codex 视觉审核返回 `uncertain/medium`，说明普通 C07 row-level 逻辑不适合该复杂矩阵。
- 规划文档：`docs/superpowers/plans/2026-06-28-t-codex-evidence-07-c07-complex-matrix-specialized-review.md`。
- 本轮规划结果：已设计 complex matrix specialized review 的 evidence contract、structured evidence、prompt contract、自动化测试计划和真实验收计划；本轮只规划，不实现代码、不修改 finalization、不运行真实 Codex。
- 07A 实现结果：已新增 `C07ComplexMatrixEvidenceBuilder`，并接入 `ReportCodexEvidenceBuilder`。C07 item 59 complex matrix target 现在会额外携带 `c07_complex_matrix_evidence`，包括 matrix page/table/header/body/result/conclusion/continuation image refs、`structured_matrix_hints` 和 fallback reasons；普通 C07 不携带该 metadata。本阶段只生成 EvidenceItem refs，不 materialize 图片，不改 prompt/schema/finalization，不运行真实 Codex。
- 07B 实现结果：已补 complex matrix image materialization / service collection / runner handoff / prompt contract。Matrix image items 可 materialize 为 workspace-local PNG，`CodexAuditService` 会把 matrix PNG paths 传给 runner，`CodexCliRunner` 以 `--image items/...` 传递多图，PromptBuilder 仅对 complex matrix target 增加 matrix-first 审核说明。本阶段不改 output schema/finalization，不运行真实 Codex。
- 07C targeted validation：用户已运行 item 59 complex matrix targeted validation，结果文件为 `runtime/codex_audit_local_e2e/4b15adbb-6e4e-4a66-99e7-9170843b3646.result.json`；本轮设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07` 与 `CODEX_AUDIT_INCLUDED_FINDING_CODES=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`，`audit_scope=targeted`、`final_audit_status=passed`、`codex_reviews_count=1`、`confirmed_errors_count=0`、`manual_review_required_count=0`、`refuted_findings_count=1`、`codex_runtime_failure_count=0`。item 59 `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX` 被 Codex `refute/high`，final status 为 `refuted`。
- full mandatory audit 最终复验：用户随后运行 full mandatory audit，结果文件为 `runtime/codex_audit_local_e2e/8e84b3e7-e079-4e6f-ac7f-b99348f18ffa.result.json`；本轮未设置 include/exclude filters，`audit_scope=full`、`full_audit=true`、`final_audit_status=passed`、`codex_reviews_count=57`、`candidate_findings_count=51`、`confirmed_findings_count=0`、`confirmed_errors_count=0`、`refuted_findings_count=51`、`manual_review_required_count=0`、`out_of_scope_findings_count=0`、`unreviewed_required_findings_count=0`、`codex_runtime_failure_count=0`。
- full audit 结论：C04 35 条、C05 2 条、C06 1 条、C07 12 条、C09 1 条全部 `refuted`；真实样本 `QW2025-2795 Draft.pdf` 当前无 confirmed final error、无 manual review，报告自检主线达到 `final_audit_status=passed`。
- 建议工作：生成完整矩阵表图像 evidence，保留跨页续表、列标题、行标题、单位/限值/测量值/占位符、单项结论和页内上下文；构建专门 prompt 要求复核矩阵列映射、结果归属和续表结构；必要时增加 matrix review metadata，不修改普通 C07 finalization。
- visual evidence 范围：full page images、matrix table crops、row/column header crops、result matrix crops、conclusion column crops、cross-page continuation crops。
- structured evidence 范围：item group rows、page numbers、table headers、condition columns、measured values、placeholder cells、conclusion candidates。
- prompt 设计：先识别矩阵表结构，再判断“符合”结论是否由矩阵结果支持；如果列映射或跨页续表仍不清楚，应返回 `uncertain`。
- 测试计划：synthetic complex matrix fixture、page/table crop evidence fixture、prompt contract tests；自动化测试只使用 fake/spy runner，不调用真实 Codex。
- 真实验收计划：先 targeted item 59，再 full audit。
- 不允许做：不通过 finalization 强行 passed；不把 complex matrix 硬编码为 refuted；不修改旧项目目录；不调用 GPT/OpenAI API；真实 Codex 运行需用户显式触发。
- 验收标准：Done when item 59 有 specialized matrix evidence 和受控审核口径；证据足够时可 refute/confirm，证据不足时继续 `manual_review_required`；不影响 C04/C05/C06/C09 和普通 C07 visual audit。
- 完成状态：[x]

### T-CODEX-EVIDENCE-07A：complex matrix specialized evidence builder
- 目标：先为 item 59 complex matrix 建立专门 evidence contract、image EvidenceItem refs 和 structured hints，不改变审核裁决语义。
- 涉及文件：`backend/app/application/c07_complex_matrix_evidence.py`、`backend/app/application/c07_visual_evidence.py`、`backend/app/application/report_codex_evidence_builder.py`、`backend/tests/application/test_report_codex_evidence_builder.py`。
- 完成内容：`c07_complex_matrix_evidence` 包含 `has_complex_matrix_input`、`review_mode=complex_matrix_specialized`、`item_no`、`pages`、`matrix_table_image_refs`、`matrix_header_image_refs`、`matrix_body_image_refs`、`result_matrix_image_refs`、`conclusion_column_image_refs`、`continuation_page_image_refs`、`structured_matrix_hints`、`missing_complex_matrix_evidence_reasons`。
- fallback：无 `source_pdf_path` 时不生成 image items，并记录 `source_pdf_path_missing`；无 bbox 时保留 page input 并记录 `matrix_bbox_missing` / `column_bbox_missing`。
- 明确未做：未修改 PromptBuilder；未修改 Codex output schema；未修改 finalization；未运行真实 Codex；未修改旧项目目录。
- 下一步：T-CODEX-EVIDENCE-07B：complex matrix prompt instructions 和 materialization/handoff 测试。
- 完成状态：[x]

### T-CODEX-EVIDENCE-07B：complex matrix materialization/handoff/prompt contract
- 目标：验证并补齐 item 59 complex matrix image evidence 从 `EvidenceItem` 到 workspace PNG、runner image paths、Codex CLI `--image` 参数和 prompt instruction 的基础设施。
- 涉及文件：`backend/app/infrastructure/audit/evidence_package_writer.py`、`backend/app/application/codex_audit_service.py`、`backend/app/infrastructure/codex/codex_cli_runner.py`、`backend/app/infrastructure/codex/prompt_builder.py` 及对应测试。
- 完成内容：新增 matrix materialization 测试覆盖 page/table/header/body/result/conclusion/continuation PNG；新增 service spy runner 测试确认 matrix PNG paths 进入 runner；新增 CLI runner 测试确认多张 matrix PNG 以 `--image items/...` 相对路径传入；新增 prompt contract，要求先识别矩阵结构再判断单项结论。
- prompt 口径：视觉证据支持“符合”结论时 refute 原 candidate；视觉证据明确冲突时 confirm；列映射、跨页续表或矩阵结果不清楚时 uncertain；不因 `complex_matrix_table=true` 自动 uncertain，也不按普通 C07 all-placeholder 逻辑直接裁决。
- 明确未做：未修改 output schema；未修改 finalization；未修改 C07 deterministic rule；未运行真实 Codex；未修改旧项目目录。
- 下一步：T-CODEX-EVIDENCE-07C：targeted item 59 complex matrix 真实验收。
- 完成状态：[x]

### T-CODEX-EVIDENCE-07C：targeted item 59 complex matrix 真实验收
- 目标：使用真实样本对 C07 item 59 complex matrix specialized review 进行 targeted validation。
- 建议运行范围：优先 targeted C07 / item 59，确认 matrix image paths 已进入 Codex run workspace，关注 `confirmed_errors_count`、`manual_review_required_count`、`refuted_findings_count` 和 `codex_runtime_failure_count`。
- 预期安全口径：如果视觉矩阵证据足够支持“符合”结论，应 refute item 59 candidate；如果矩阵列映射仍不稳定，应保留 `manual_review_required`；只有视觉证据明确证明业务错误时才可 confirmed。
- 不允许做：不通过 finalization 强行 passed；不把 item 59 硬编码 refute；不修改旧项目目录。
- targeted validation 结果：`runtime/codex_audit_local_e2e/4b15adbb-6e4e-4a66-99e7-9170843b3646.result.json` 中 `audit_scope=targeted`、`final_audit_status=passed`、`codex_reviews_count=1`、`confirmed_errors_count=0`、`manual_review_required_count=0`、`refuted_findings_count=1`、`codex_runtime_failure_count=0`；item 59 final status 为 `refuted`。
- full mandatory audit 最终复验：`runtime/codex_audit_local_e2e/8e84b3e7-e079-4e6f-ac7f-b99348f18ffa.result.json` 中 `audit_scope=full`、`full_audit=true`、`final_audit_status=passed`、`candidate_findings_count=51`、`codex_reviews_count=57`、`confirmed_errors_count=0`、`manual_review_required_count=0`、`refuted_findings_count=51`、`codex_runtime_failure_count=0`。
- 完成状态：[x]

### T-CODEX-RUNTIME-01B：local E2E failed error summary 解析修复
- 目标：修复 `scripts/run-codex-audit-local-e2e.sh` 在 task error 时的错误摘要提取，避免 task JSON 字段缺失导致 `task_id`、`check_id`、`batch_id` 和 usage limit 分类丢失。
- 背景：C04 failed extract 中 task JSON 行解析不到 `task_id/task_status/progress/current_step`，但 workspace path 包含 `runtime/codex_audit/{task_id}/codex-report-{task_id}-C04-batch-6/input`；stderr 明确出现 `You've hit your usage limit` 时也应归类为 `CODEX_USAGE_LIMIT_EXCEEDED`。
- 涉及文件：`scripts/run-codex-audit-local-e2e.sh`、`backend/tests/integration/test_codex_audit_local_e2e_artifacts.py`、`docs/current-status.md`、`docs/codex-audit-local-e2e.md`。
- 需要实现：任务失败时写入 `error_summary.json`；从 workspace path 反推 `task_id` 和 `package_id`；从 package_id 提取 `check_id` 与 `batch_id`；从 stderr 提取 `retry_after_text`；usage limit 错误归类为 `CODEX_USAGE_LIMIT_EXCEEDED`。
- 不允许做：不改变 mandatory 原则；不把 Codex runtime failure 改为 completed；不调用真实 Codex CLI；不修改后端业务代码、router、frontend 或旧项目目录。
- 测试要求：运行 local E2E artifact tests、bash syntax 和 `git diff --check`。
- 完成状态：[x]

### T-QUALITY-01：C08/C10/C07 降噪设计
- 目标：基于真实报告样本分析 C08/C10/C07 噪声来源，设计 group-level 降噪路线。
- 背景：QW2025-2795 Draft.pdf 真实结果显示 `C08=4894`、`C10=130`、`C07=72`，physical row-level 判断噪声明显。
- 新文件位置：`docs/quality-noise-reduction-plan.md`。
- 需要实现：记录当前样本噪声分析、`InspectionItemGroup` 设计、C08/C10/C07 group-level 新策略、C04/C05/C06 OCR gating、Finding 聚合模型、测试计划和 T-QUALITY-02 到 T-QUALITY-07 分阶段任务。
- 不允许做：不修改业务代码；不修改规则；不修改前端；不调用真实 Codex。
- 完成状态：[x]

### T-QUALITY-02：InspectionItemGroup builder
- 目标：实现独立 `InspectionItemGroup` builder，将 `ReportDocument.inspection_items` 中的 physical row `InspectionItem` 归并为业务级 item group，作为后续 C08/C10/C07 降噪共同输入。
- 背景：T-QUALITY-01 确认 C08/C10/C07 的主要噪声来自 physical row-level 判断；本阶段只建立 group contract，不接入现有规则。
- 新文件位置：`backend/app/domain/inspection_group.py`、`backend/app/infrastructure/report/inspection_item_group_builder.py`、`backend/tests/infrastructure/report/test_inspection_item_group_builder.py`。
- 需要实现：普通序号归组、`续 X` 归组、空序号 payload 行归入 active group、空白行 diagnostics、跨页 pages/continuation markers、effective test results/conclusion/remark、inherited merged fields、source evidence 和 diagnostics。
- 不允许做：不修改 C07/C08/C10 规则输出；不修改 C04/C05/C06；不修改 usecase/router/frontend；不调用真实 Codex；不改变现有 deterministic findings 数量。
- 测试要求：运行 group builder 测试、C07/C08/C10 规则回归、后端全量、前端 build 和 `git diff --check`。
- 验收标准：Done when builder 可独立把 physical rows 归组为可追溯 item groups，现有 C07/C08/C10 测试不受影响。
- 完成状态：[x]

### T-QUALITY-03：C08 group-level 重构
- 目标：让 C08 消费 `InspectionItemGroup`，从 physical row-level 空字段报错收敛为 group-level effective field finding。
- 背景：T-QUALITY-02 已提供 group builder；C08 当前仍逐 physical row、逐字段输出 finding。
- 不允许做：不修改 C07/C10；不让前端重新计算 C08；不删除原始诊断明细。
- 完成状态：[x]

### T-QUALITY-03B：C08 item_no 污染和表类型过滤修复
- 目标：修复 C08 group-level 后剩余误报中“标准要求正文被当作 item_no”的污染问题。
- 背景：真实样本 T-QUALITY-03 后 `C08=140`，剩余示例中 `item_no` 出现“——所有其他 ME 设备和 ME 系统，500V。”、“当外壳的分类为 IPX0 时……”等标准要求正文，说明 extractor/builder 需要强化序号合法性。
- 需要实现：`InspectionItemGroupBuilder` 只接受纯数字序号和 `续 + 数字`；非法 `sequence_raw` 不创建新 group，有 active group 时作为 payload row 归入 active group，无 active group 时进入 diagnostics/ungrouped；`parse_sequence` 不再从正文或标准条款号中抓数字。
- 不允许做：不修改 C07/C10；不修改 C04/C05/C06；不修改 `ReportCheckUseCase`、router、frontend；不调用真实 Codex；不修改旧项目目录。
- 验收标准：Done when 标准要求文本、a)/b)/c) 子项、标准条款号和长中文正文不会作为 C08 item_no 生成主 finding，C07/C10/C08 回归和全量测试通过。
- 完成状态：[x]

### T-QUALITY-03C：C08 item 126 备注占位符误报修复
- 目标：修复真实样本 QW2025-2795 Draft.pdf 中序号 126 的 C08 `remark` 空值误报。
- 背景：T-QUALITY-03B 后真实样本 C08 剩余为 `remark` 字段 2 条重复统计，按 `finding.id` 去重后实际只有 item 126 一条；结构化证据显示右侧 `符合 /` 被解析成 `test_result="符合"`、`single_conclusion="/"`、`remark=""`，导致备注占位符丢失。
- 需要实现：在 `InspectionItemGroupBuilder` 的 effective field 标准化层，处理 `single_conclusion="符合 /"`、`不符合 /`、`/ /`、`—— /`，以及 `test_result="符合"` + `single_conclusion="/"` + `remark=""` 这类右侧字段错位；只使用右侧结构化字段证据，不把 `standard_requirement` 中的 `/` 当作备注。
- 本地 e2e 统计应按 `finding.id` / `review_id` 去重，避免 top-level `findings` 和 `check_results[].findings` 被重复计数。
- 真实样本验收：QW2025-2795 Draft.pdf 最新 `C08 count=0`；C08 已完成从 4894 -> 140 -> 2 -> 0 的 group-level 降噪闭环。
- 不允许做：不修改 C07/C10；不修改 router/frontend；不调用真实 Codex；不修改旧项目目录。
- 验收标准：Done when item 126 的 effective fields 为 `effective_single_conclusion="符合"`、`effective_remark="/"`，C08 不再产生 remark empty finding；无 slash 证据的空备注仍然报错；C07/C10/C08 回归、后端全量、前端 build、脚本语法和 `git diff --check` 通过。
- 完成状态：[x]

### T-QUALITY-04：C10 page-boundary 重构
- 目标：让 C10 基于 `InspectionItemGroup` 的跨页边界检查续表标记，避免同一 page boundary 重复报错。
- 背景：T-QUALITY-02 已提供 group builder；C10 当前仍以页内 physical row 为主要判断单位。
- 真实样本验收：QW2025-2795 Draft.pdf 最新 `C10 unique count=0`，`by_code={}`、`by_boundary=[]`、`by_item=[]`、`by_page=[]`；C10 已完成从 130 -> 0 的 page-boundary 降噪闭环，C08 仍保持 0。
- 不允许做：不修改 C07/C08；不改变 C09 序号连续性职责。
- 完成状态：[x]

### T-QUALITY-05：C07 group-level 重构
- 目标：让 C07 消费 `InspectionItemGroup` 的 effective results/conclusion，并为 Codex audit 提供 group evidence。
- 背景：C07 已有序号归组雏形，但仍未复用统一 group contract。
- 真实样本验收：首次 8000 端口运行命中旧后端进程，不作为有效验收；随后使用 `BASE_URL=http://127.0.0.1:8011 BACKEND_PORT=8011` 启动当前工作区代码重跑，QW2025-2795 Draft.pdf 最新 `C07=12`、`C08=0`、`C10=0`。C07 已从 72 降到 12，且每个 item_no 最多 1 条。
- 不允许做：不修改 C08/C10；不调用真实 Codex；不让 Codex 覆盖 deterministic finding。
- 完成状态：[x]

### T-QUALITY-05B：C07 residual mismatch cleanup
- 目标：收敛 T-QUALITY-05 后真实样本剩余 12 条 C07 mismatch，区分 actual conclusion 冲突选择、复杂矩阵表 extractor/列映射、以及 `——` 与 `符合要求` 混合时 effective result 聚合不完整或业务口径问题。
- 背景：T-QUALITY-05 有效验收中 C07 剩余 item_no 为 `3, 27, 33, 41, 59, 72, 94, 121, 131, 142, 149, 151`；其中 item 3 主要是 actual conclusion 冲突选择，item 59 主要是复杂矩阵表列映射，其余 `/ -> 符合` 需要进一步确认业务口径和 result token 聚合。
- 不允许做：不回退 C07 group-level；不修改 C08/C10；不调用真实 Codex；不修改旧项目目录。
- 完成状态：[ ]

### T-QUALITY-06：C04/C05/C06 OCR gating
- 目标：明确 label caption、label OCR 和 label image 三层证据，缺 OCR 或低置信 OCR 时优先 WARN / NEEDS_REVIEW。
- 背景：真实样本 C04/C05/C06 仍有噪声，OCR/caption 证据不足时不应直接扩大 ERROR。
- 完成状态：[ ]

### T-QUALITY-07：前端 grouped findings 展示
- 目标：前端展示 grouped finding，并折叠展示 raw rows / diagnostics / suppressed count。
- 背景：C08/C10/C07 降噪后需要让用户看到“业务问题 + 明细”的层次，而不是物理行噪声列表。
- 不允许做：不在前端重新计算 C07/C08/C10。
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

## T-PERF：Codex audit speed roadmap

### T-PERF-01：Codex audit speed profile + batch=5 visibility
- 目标：量化 report-check / Codex audit 各阶段耗时，并明确 full audit 默认 batch 为 5。
- 完成状态：[x]
- 实现记录：
  - 新增 `backend/app/application/performance_profile.py`，记录阶段耗时和 package 汇总。
  - `ReportCheckUseCase` 记录 `parse_pdf`、`build_report_document`、`run_rules`、`codex_audit_total`、`finalize_codex_audit`、`complete_task`。
  - `CodexAuditService`、`EvidencePackageWriter`、`CodexCliRunner` 记录 package、image、prompt、evidence 和 codex exec 统计。
  - `scripts/run-codex-audit-local-e2e.sh` 输出 effective batch size、performance summary，并在 full audit batch=1 时提示 debug/slow mode。
- 约束：不修改 deterministic rules，不修改 finalization，不运行真实 Codex CLI。

### T-PERF-02：automatic Codex audit scheduler + concurrency cap
- 目标：支持系统自动分配独立 Codex audit packages，并通过 `CODEX_AUDIT_MAX_PARALLEL_JOBS` 控制并发。
- 完成状态：[x]
- 实现记录：
  - 新增 `backend/app/application/codex_audit_scheduler.py`。
  - 默认 `CODEX_AUDIT_MAX_PARALLEL_JOBS=1`，保持旧串行行为。
  - Report/PTR usecase 先收集 packages，再交给 bounded scheduler 执行。
  - review metadata 记录 `codex_scheduler_profile`，包含 parallel jobs、worker、queue wait 和 scheduler total。
- 约束：任一 required Codex review failed/skipped 仍会让 mandatory task failed。

### T-PERF-03：user-directed advanced audit controls
- 目标：支持用户指定 targeted audit、高级 batch 和并发参数，但默认 UI 仍保持简单。
- 完成状态：[x]
- 实现记录：
  - 新增 `backend/app/application/codex_audit_options.py`。
  - Report/PTR API 接收 `included_check_ids`、`included_finding_codes`、`excluded_check_ids`、`max_targets_per_batch`、`max_parallel_jobs`。
  - `TaskStatus.metadata` 保存 `audit_options` 和 `audit_options_source`。
  - 前端 Report/PTR 上传页新增默认折叠的“高级审核设置”。
- 约束：前端只传参和展示，不重新计算 C01-C11 或 PTR 判断。

### T-PERF-04：succeeded review cache / resume / incremental audit foundation
- 目标：避免完全相同 evidence/prompt/schema/image 的 succeeded Codex reviews 重复执行，并为 resume/incremental audit 打基础。
- 完成状态：[x]
- 实现记录：
  - 新增 `backend/app/infrastructure/audit/codex_review_cache.py`。
  - 默认 cache root 为 `runtime/codex_audit_cache`。
  - cache key 归一化 task UUID，并包含 request/evidence/prompt/schema/image hashes。
  - 只缓存 `status=succeeded`、parser/schema 已验证且 verdict 不是 `uncertain` 的 review。
  - cache hit 会把 review 重新绑定到当前 request/task/target，并标记 `cache_hit=true`。
- 约束：不缓存 failed/skipped/uncertain；runtime failure 仍导致 mandatory task failed。

### T-PERF-05：batch=5 full mandatory audit 真实对比
- 目标：在真实样本上用 full audit、无 include/exclude filters、effective batch=5 复跑，对比 batch=1 慢跑基线。
- 完成状态：[ ]
- 验收关注：
  - `final_audit_status=passed`
  - `confirmed_errors_count=0`
  - `manual_review_required_count=0`
  - `codex_runtime_failure_count=0`
  - package count 和总 wall-clock time 较 batch=1 基线下降。

## T-RULE：真实样本规则语义校正

### T-RULE-2797-01：2797 报告自检结果语义校正与规则适用性修复
- 目标：基于 2797 样本修正 report-check 用户层语义，避免未经 Codex final audit 的 deterministic `error_count` 被误读为确认不符合。
- 完成状态：[x]
- 实现记录：
  - 新增 finding/check `user_facing_status`：`confirmed_error`、`needs_review`、`candidate_issue`、`refuted`、`passed`。
  - C04 caption-only / OCR fields empty 改为 `OCR_EVIDENCE_INSUFFICIENT` WARN / `needs_review`。
  - 样品描述抽取识别“本次检验配合使用”上下文，标记 `sample_role=supporting_equipment`。
  - C05/C06 默认跳过 `supporting_equipment`，不作为主样品照片/标签覆盖 error。
  - Report 前端和 PDF/XLSX 导出区分候选问题、需复核、确认错误和 legacy deterministic counts。
- 约束：未运行真实 Codex CLI；未调用 GPT/OpenAI API；未修改旧项目目录。

### T-CODEX-ROBUST-01：Codex missing target retry + C04 supporting equipment scope fix
- 目标：修复 2797 网页运行中 `CODEX_OUTPUT_MISSING_TARGET` 造成的 mandatory audit 失败，并避免 C04 将“本次检验配合使用”设备当作主样品标签缺失 target。
- 完成状态：[x]
- 实现记录：
  - C04 现在消费 `sample_role=supporting_equipment` / `supporting_equipment=true` 标记，对配合使用设备写入 coverage `supporting_equipment_skipped`，不输出 `SAMPLE_COMPONENT_LABEL_NOT_FOUND` 或 `SAMPLE_FIELD_MISSING_IN_LABEL`。
  - `CodexReviewOutputParser` 在 `CODEX_OUTPUT_MISSING_TARGET` 时保留已成功解析的 target reviews，只为缺失 target 生成 failed review。
  - `CodexAuditService` 首次发现 missing target 时自动构建 retry request/package，仅重试缺失 target；默认 `CODEX_AUDIT_MISSING_TARGET_RETRY_BATCH_SIZE=1`。
  - retry 成功后合并 reviews 并继续 finalization；retry 失败或仍缺 target 时返回 `CODEX_OUTPUT_MISSING_TARGET`，mandatory task 仍 failed。
  - 前端将 `CODEX_OUTPUT_MISSING_TARGET` 显示为中文“LLM 复核未完成”提示，并说明这不是报告确认错误；原始 target ids 放入高级详情。
- 约束：未运行真实 Codex CLI；未调用 GPT/OpenAI API；未修改旧项目目录或用户上传 PDF。

## T-UX：任务进度与错误体验

### T-UX-PROGRESS-01：report-check C01-C11 + Codex target 细粒度进度展示
- 目标：把 report-check 从长期停留 `70% / running report rules` 的粗粒度状态，改为可解释的阶段、C01-C11 checklist 和 Codex target/batch/retry 进度。
- 完成状态：[x]
- 实现记录：
  - `TaskStatus` 新增可选 `progress_details`，并同步写入 `TaskStatus.metadata["progress_details"]` 作为兼容展示元数据。
  - 新增 `ReportCheckProgressReporter`，按 upload/parse/extract/rules/evidence/codex_audit/finalize/completed/error 阶段更新任务状态。
  - `ReportRuleRunner` 通过 `CheckContext` 回调在每条 C01-C11 前后更新 running/passed/failed/skipped/needs_review/error；C03 skip 也会显示为 skipped。
  - `ReportCheckUseCase` 在 Codex audit 构建 target 后记录 total reviews/batches，并在每个 package 开始/完成时更新 completed reviews/batches。
  - `CodexAuditService` 在 missing-target retry 时发出 progress event，前端可显示 retrying 和 `CODEX_OUTPUT_MISSING_TARGET`。
  - 前端 `ProgressOverlay` 展示当前阶段、C01-C11 checklist、Codex 当前 check/target type、review/batch 计数和 retry 状态。
  - 前端补充 `CODEX_TIMEOUT`、`CODEX_CLI_UNAVAILABLE`、`CODEX_OUTPUT_MISSING_TARGET` 中文错误文案，并把原始错误留在高级详情。
- 约束：未修改 C01-C11 业务判断；未修改 Codex finalization；未运行真实 Codex CLI；未调用 GPT/OpenAI API；未修改旧项目目录。
