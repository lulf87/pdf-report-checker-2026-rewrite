# Codex CLI 运行时审核员策略

校准日期：2026-06-15

本文用于纠偏当前重写项目的审核链路：Codex CLI 不是普通开发工具，也不只是离线辅助说明，而是产品运行时受控 auditor / judge。确定性规则仍负责构建证据和候选问题，Codex CLI 负责对复杂语义、图文证据和规则歧义做运行时复核。最终结果必须同时保留 deterministic finding 与 Codex review 两层证据。

## 1. 旧项目事实

- 旧项目不是单纯靠正则、表格规则或字段规则最终判定。
- 根据用户本次架构纠偏指令，以及当前仓库 `docs/legacy-inventory.md`、`docs/spec-code-test-gaps.md` 中对旧 Codex judge client / output schema / GAP-012 的记录，旧项目中 Codex CLI 是复杂语义或图文判断的辅助审核员。
- 旧项目事实显示，报告自身核对中存在 Codex judge 调用与结果聚合；复杂标签、照片、检验结果语义、PTR 条款语义等场景会进入 Codex 审核链路。
- 重做项目必须保留这个核心逻辑，但要重做边界：不复用旧 service 大文件，不让 router 承担业务编排，不让 Codex 直接读写项目源码。

## 2. 新定位

新项目采用两层证据链：

1. 确定性层：正则、OCR、PDF 解析、表格结构化、字段抽取和规则模块负责构建 `EvidencePackage`，并输出 C01-C11 / PTR candidate findings。
2. 审核层：Codex CLI 作为运行时 judge / auditor，只接收受控 evidence package，对候选 finding、证据不足、图文语义或复杂 PTR 语义做复核。

核心约束：

- 正则、OCR、表格结构化和规则负责 evidence building。
- C01-C11 / PTR rules 输出 candidate findings。
- Codex CLI 作为运行时 judge / auditor 做复核。
- 最终结果保留 deterministic finding 和 Codex review。
- Codex review 可以给出 `confirm`、`refute`、`uncertain`、`add_finding`。
- Codex review 不删除原始 `Finding`，也不静默覆盖规则结论；被 refute 的 finding 仍保留审计痕迹，并通过 `codex_review_id` 或 `metadata` 标记复核意见。
- Codex CLI 只能参与产品运行时审核链路，不作为前端业务判断，也不作为 router 内的即时逻辑。

## 3. 后端模块设计

新增模块应放入当前新项目目录，不修改旧项目目录。

| 模块 | 职责 |
| --- | --- |
| `backend/app/domain/codex_review.py` | 定义 Codex review 领域模型、状态、verdict、request/result/error/evidence package。 |
| `backend/app/infrastructure/codex/codex_cli_runner.py` | 封装真实 `codex exec` 调用、只读 sandbox、工作目录、timeout、stdout/stderr 捕获和退出码。 |
| `backend/app/infrastructure/codex/fake_codex_runner.py` | 单元测试和 usecase 测试使用的 fake runner，不调用真实 Codex。 |
| `backend/app/infrastructure/codex/prompt_builder.py` | 根据 `EvidencePackage` 和 review target 生成 prompt，禁止注入项目源码和无关文件。 |
| `backend/app/infrastructure/codex/output_parser.py` | 解析 Codex JSON 输出，校验 schema，失败时产生 `CodexReviewStatus.failed`。 |
| `backend/app/application/codex_audit_service.py` | 编排 evidence package 写入、prompt 构造、runner 调用、结果解析、fallback 和结果关联。 |
| `backend/app/infrastructure/audit/evidence_package_writer.py` | 为每个任务写入 `runtime/codex_audit/{task_id}/` 下的最小证据包和必要图片/裁剪图。 |

依赖方向：

- `domain/codex_review.py` 不依赖 infrastructure、FastAPI、文件系统或 Codex CLI。
- `application/codex_audit_service.py` 可以依赖 domain model、runner 协议和 writer 协议。
- `infrastructure/codex/*` 只处理外部进程、prompt、schema 和输出解析，不写 C01-C11 或 PTR 业务规则。
- `rules/` 不直接调用 Codex CLI；规则只输出 candidate findings 和 evidence。

## 4. 运行时安全边界

Codex CLI 运行必须默认最小权限：

- 每个任务创建 `runtime/codex_audit/{task_id}/` 临时目录。
- 只向 Codex 提供 evidence package，包括结构化 JSON、必要的页图或裁剪图、候选 finding、规则上下文和最小诊断。
- 不让 Codex 读取整个项目源码、测试目录、旧项目目录、上传原始目录或开发工作区。
- 不让 Codex 修改旧项目或新项目源码。
- `codex exec` 使用 read-only sandbox。
- prompt 明确要求只基于 evidence package 审核，不补造标准条款、字段含义、检测结果或文件路径。
- 使用 output schema 输出 JSON，不接受自由文本作为最终结构化结果。
- 设置 timeout；超时、非零退出、schema 解析失败、JSON 校验失败均降级为 `CodexReviewStatus.failed`。
- Codex 审核失败不阻断主核对流程；主流程继续返回 deterministic findings，并把失败 review 作为诊断证据。
- 单元测试和 usecase 测试必须使用 `FakeCodexRunner`，不得调用真实 Codex CLI。
- 真实 Codex CLI 仅在手动验收任务中启用，并记录输入 evidence package、输出 JSON、timeout 和失败 fallback。

## 5. 数据模型

### 5.1 `CodexReviewRequest`

| 字段 | 说明 |
| --- | --- |
| `request_id` | 单次审核请求 ID。 |
| `task_id` | 所属任务 ID。 |
| `target` | `CodexReviewTarget`，说明审核对象。 |
| `evidence_package` | `EvidencePackage`，只包含允许给 Codex 的证据。 |
| `schema_version` | 输出 schema 版本。 |
| `timeout_seconds` | 本次审核 timeout。 |
| `created_at` | 请求创建时间。 |
| `metadata` | 业务外扩展信息，不放必须字段。 |

### 5.2 `CodexReviewTarget`

| 字段 | 说明 |
| --- | --- |
| `target_id` | 审核对象 ID。 |
| `target_type` | 例如 `finding`、`check_result`、`ptr_clause`、`ptr_table`、`report_rule`、`evidence_package`。 |
| `check_id` | 关联规则编号，如 `C02`、`C07`、`PTR_CLAUSE`、`PTR_TABLE`。 |
| `finding_ids` | 关联的 candidate finding ID 列表。 |
| `reason` | 发起审核的原因，如 ambiguity、low_confidence、semantic_review。 |
| `priority` | 审核优先级，用于控制成本和任务顺序。 |
| `metadata` | 目标扩展信息。 |

### 5.3 `CodexReviewResult`

| 字段 | 说明 |
| --- | --- |
| `review_id` | 审核结果 ID。 |
| `request_id` | 对应请求 ID。 |
| `task_id` | 所属任务 ID。 |
| `target` | 被审核对象。 |
| `status` | `CodexReviewStatus`。 |
| `verdict` | `CodexReviewVerdict`，失败或跳过时可为空。 |
| `summary` | 面向用户或审核人员的中文摘要。 |
| `rationale` | 只基于 evidence package 的复核理由。 |
| `finding_ids` | 复核影响的原始 finding ID。 |
| `added_findings` | Codex 建议新增的 finding；进入最终结果前仍需按统一 `Finding` schema 校验。 |
| `confidence` | Codex 自评置信度，只作为审核证据，不单独替代规则证据。 |
| `evidence_refs` | Codex 使用的 evidence ID 或文件引用。 |
| `raw_output_ref` | 原始 JSON 输出文件引用，位于任务 audit 目录。 |
| `error` | `CodexReviewError`。 |
| `metadata` | 扩展信息。 |

### 5.4 `CodexReviewVerdict`

| 值 | 含义 |
| --- | --- |
| `confirm` | 确认 candidate finding 或规则判断成立。 |
| `refute` | 认为 candidate finding 不成立，但不删除原 finding，只保留复核意见。 |
| `uncertain` | 证据不足或语义不确定，需要人工复核。 |
| `add_finding` | Codex 基于 evidence package 发现规则未覆盖的问题，建议新增 finding。 |

### 5.5 `CodexReviewStatus`

| 值 | 含义 |
| --- | --- |
| `pending` | 已创建但未执行。 |
| `running` | 正在调用 Codex CLI。 |
| `completed` | JSON 输出通过 schema 校验。 |
| `failed` | timeout、进程失败、schema 失败或解析失败。 |
| `skipped` | 因配置、成本、证据不足或任务策略跳过。 |

### 5.6 `CodexReviewError`

| 字段 | 说明 |
| --- | --- |
| `code` | 机器可读错误码，如 `CODEX_TIMEOUT`、`CODEX_EXIT_NONZERO`、`CODEX_SCHEMA_INVALID`。 |
| `message` | 可读错误说明。 |
| `retryable` | 是否可重试。 |
| `exit_code` | 外部进程退出码。 |
| `stdout_ref` | stdout 保存位置。 |
| `stderr_ref` | stderr 保存位置。 |
| `timeout_seconds` | timeout 设置。 |
| `metadata` | 扩展诊断。 |

### 5.7 `EvidencePackage`

| 字段 | 说明 |
| --- | --- |
| `package_id` | 证据包 ID。 |
| `task_id` | 所属任务 ID。 |
| `package_type` | `report_check`、`ptr_compare` 或更细分的 review 类型。 |
| `target` | 本证据包服务的审核目标。 |
| `deterministic_findings` | 规则层 candidate findings。 |
| `check_results` | 相关 `CheckResult` 摘要。 |
| `evidence_items` | 结构化 `Evidence` 列表。 |
| `source_snippets` | 允许给 Codex 的原文片段，不包含整项目源码。 |
| `asset_refs` | 允许给 Codex 的图片、裁剪图或表格 JSON 引用。 |
| `schema_version` | 证据包 schema 版本。 |
| `metadata` | 页码、表格、规则诊断等扩展信息。 |

## 6. `CheckResult` 集成

`CheckResult` 需要新增：

- `codex_reviews: list[CodexReviewResult] = []`

`Finding` 关联方式：

- 首选：新增或使用 `codex_review_id` 字段关联审核结果。
- 兼容方式：在 `Finding.metadata` 中写入 `codex_review_ids`、`codex_verdict`、`codex_status`、`codex_summary`。

展示和导出要求：

- 前端展示“规则初判 + Codex 审核意见”。
- deterministic finding 不因 Codex refute 被删除；UI 可以显示为“规则初判：ERROR，Codex 审核：refute/uncertain/confirm”。
- Codex `add_finding` 必须进入统一 `Finding` 校验和 evidence 关联后才能展示。
- JSON/PDF/XLSX 导出必须保留 deterministic findings、Codex reviews、失败 review 诊断和 raw output 引用。

## 7. PTR 优先接入点

优先把 CodexAuditService 接入 PTR 中确定性规则最容易产生候选但语义仍复杂的地方：

- PTR clause semantic review：条款正文严格差异后的语义复核。
- table candidate ambiguity review：报告侧候选表歧义、续表合并不稳或 caption 不唯一。
- parameter semantic review：参数名、条件、单位、允差字段存在语义等价或别名风险。
- numeric / segmented threshold review：复杂数学满足判断、分段阈值、measurement bundle 语义。
- scope filter review：首页范围、括号排除、外部标准、method/appendix/group heading 排除的复核。

## 8. 报告自检优先接入点

报告自身核对优先接入：

- C02 标签字段审核：第三页扩展字段、中文标签 OCR、`见样品描述栏` 证据链。
- C03 日期格式和值审核：格式和值冲突、OCR 低置信、日期表达歧义。
- C04 样品描述 vs 标签审核：同名多行、LOT/SN、MFG/MFD/EXP、失效日期、空值与 `/`。
- C05 照片 caption 审核：照片主体名、方位词、编号、普通照片与标签照片边界。
- C06 中文标签 caption 审核：中文标签/英文标签/包装标签/铭牌语义。
- C07 特殊检验结果语境审核：无菌语境、`/`、`--`、空白结果、特殊检验结果与单项结论。

## 9. 任务拆分

| 任务 | 目标 |
| --- | --- |
| T-CODEX-00 | 架构文档和 AGENTS 修正。新增本文，更新 `AGENTS.md`、`docs/tasks.md`、`docs/current-status.md`。 |
| T-CODEX-01 | 实现 `CodexReview` domain model，包括 request、target、result、verdict、status、error。 |
| T-CODEX-02 | 实现 `EvidencePackage` model 和 `evidence_package_writer`，写入 `runtime/codex_audit/{task_id}/`。 |
| T-CODEX-03 | 实现 `FakeCodexRunner` / `CodexCliRunner` 接口，单元测试只使用 fake runner。 |
| T-CODEX-04 | 实现 `PromptBuilder` 和 JSON output schema，明确只基于 evidence package。 |
| T-CODEX-05 | 实现 `OutputParser` 和失败 fallback，覆盖 timeout、非零退出、invalid JSON、schema invalid。 |
| T-CODEX-06 | `PTRCompareUseCase` 接入 `CodexAuditService`，优先覆盖 PTR clause/table/parameter/scope review。 |
| T-CODEX-07 | `ReportCheckUseCase` 接入 `CodexAuditService`，优先覆盖 C02/C03/C04/C05/C06/C07。 |
| T-CODEX-08 | 前端展示 Codex review，展示“规则初判 + Codex 审核意见”。 |
| T-CODEX-09 | 真实 Codex CLI 手动验收，记录 evidence package、JSON 输出、timeout 和 fallback。 |

## 10. 非目标

- 本策略文档不实现业务代码。
- 不调用真实 Codex CLI。
- 不修改 router。
- 不修改前端。
- 不修改旧项目目录。
- 不继续扩展 numeric semantic。
- 不把 Codex CLI 描述为普通开发工具；它是产品运行时受控审核员。
