# Codex Audit Local E2E

更新时间：2026-06-23

本文记录 T-CODEX-11A 的本地业务端到端验收入口、T-CODEX-11B 的真实 codex-cli 本地业务验收结果，以及 T-CODEX-MANDATORY-01 后的 mandatory Codex CLI 运行语义。Codex CLI 是本地业务验收的 mandatory auditor；规则输出是 candidate，不是最终结论。

## 一、目的

- 验证本地后端默认通过 `CodexCliRunner` 调用本机 `codex exec`，并把结果写入 `codex_reviews`。
- 验证 Codex runtime failure 会让任务失败，而不是 completed 后只携带 failed review。
- 验证 Codex verdict=`uncertain` 是正常审核结果，任务 completed 但前端展示人工复核。
- 验证前端只展示后端返回的 `codex_reviews` 和 finding metadata，不重新计算 C01-C11 或 PTR 规则。

普通自动化测试仍不调用真实 Codex CLI；测试通过显式 fake dependency 注入完成。业务 E2E 脚本默认拒绝运行，只有设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1` 后才会联系后端，避免误触发真实 Codex CLI。

## 二、本地运行

产品运行路径不再提供用户层面的 disabled/fake/codex-cli 选择。本地 API 默认构建 `CodexAuditService + CodexCliRunner`；`FakeCodexRunner` 只用于 pytest 或显式测试依赖注入。

启动后端：

```bash
cd backend
CODEX_CLI_PATH=codex \
CODEX_AUDIT_RUNTIME_DIR=runtime/codex_audit \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=5 \
python -m uvicorn app.main:app --reload
```

启动前端：

```bash
cd frontend
npm run dev
```

业务验收：

1. 打开前端页面。
2. 上传 PTR + 报告，或上传单份报告自检。
3. 查看结果页和导出的 JSON。
4. 预期：`check_results[].codex_reviews` 包含 Codex 审核意见；如果 Codex CLI 不可用、超时、非零退出或输出无效，任务状态为 failed/error。

## 三、脚本验收

脚本路径：

```bash
bash scripts/run-codex-audit-local-e2e.sh
```

查看帮助：

```bash
bash scripts/run-codex-audit-local-e2e.sh --help
```

查看安全配置，不上传文件、不启动服务、不调用 Codex：

```bash
bash scripts/run-codex-audit-local-e2e.sh --print-config
```

报告自检：

```bash
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
TASK_TYPE=report-check \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

如需脚本代启后端：

```bash
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
START_BACKEND=1 \
TASK_TYPE=report-check \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

PTR 比对：

```bash
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
TASK_TYPE=ptr-compare \
PTR_FILE=/path/to/ptr.pdf \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

真实 Codex CLI 建议先用单 target / 小 batch 验收：

```bash
PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C07 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
TASK_TYPE=report-check \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

脚本安全要求：

- 必须设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1` 才会运行上传/轮询流程。
- 未满足 gate 时，脚本拒绝运行，不调用后端，也不会触发真实 Codex CLI。
- `--help` 和 `--print-config` 不启动服务、不上传文件、不调用 Codex。

## 四、脚本参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `TASK_TYPE` | `ptr-compare` | `ptr-compare` 或 `report-check`。 |
| `BASE_URL` | `http://127.0.0.1:8000` | 已运行后端地址。 |
| `START_BACKEND` | `0` | 为 `1` 时脚本代启后端。 |
| `PYTHON_BIN` | `python` | 用于脚本 JSON 解析的 Python。 |
| `PTR_FILE` | 无 | PTR PDF，本地业务样本路径。 |
| `REPORT_FILE` | 无 | 报告 PDF，本地业务样本路径。 |
| `EXPECT_CODEX_REVIEWS` | `auto` | `auto`、`empty`、`nonempty` 或 `any`；mandatory 默认期望非空。 |
| `OUTPUT_DIR` | `runtime/codex_audit_local_e2e` | 保存 task/result JSON 的本地目录。 |
| `CODEX_CLI_PATH` | `codex` | 本机 Codex CLI 可执行文件。 |
| `CODEX_AUDIT_MAX_TARGETS_PER_BATCH` | `5` | 每个 batch 最多审核 targets；这是性能分批，不是漏审上限。 |
| `CODEX_AUDIT_INCLUDED_CHECK_IDS` | 空 | 只审核指定 check IDs，例如 `C07` 或 `C02,C03,C07`。 |
| `CODEX_AUDIT_INCLUDED_FINDING_CODES` | 空 | 只审核指定 finding codes，例如 `CONCLUSION_MISMATCH_001`。 |
| `CODEX_AUDIT_EXCLUDED_CHECK_IDS` | 空 | 排除指定 check IDs，例如 `C08,C09,C10,C11`。 |
| `CODEX_AUDIT_PRIORITY_CHECK_IDS` | `C02,C03,C07,C04,C05,C06` | 报告自检 target 优先级；PTR builder 使用 PTR finding code 默认优先级。 |
| `CODEX_AUDIT_TIMEOUT_SECONDS` | `300` | 真实 Codex CLI runner timeout。 |

脚本会：

1. 检查后端健康状态。
2. 上传 PTR/报告任务或报告自检任务。
3. 轮询 `/api/tasks/{task_id}`。
4. 下载 `/api/tasks/{task_id}/result`。
5. 统计 `check_results[].codex_reviews` 数量。
6. 按 `EXPECT_CODEX_REVIEWS` 校验 `codex_reviews` 是否符合预期。

脚本输出边界：

- 进度日志和任务状态输出到 stderr，格式为 `[codex-audit-local-e2e] ...`。
- 内部用于传递结果 JSON 路径的 stdout 保持为单行文件路径，避免 command substitution 捕获到日志。
- 脚本会校验结果路径非空、存在、不包含换行，并且以 `.json` 结尾。

## 五、任务结果语义

- deterministic rule findings 是候选项，不是最终结论。
- `findings` 字段为了兼容仍保留 candidate findings；后端会通过 metadata 写入 `codex_required`、`codex_verdict`、`final_status` 和 `codex_review_id`。
- Codex `confirm` 表示候选 finding 被确认。
- Codex `refute` 表示候选 finding 可能为误报，不应作为最终 ERROR 展示。
- Codex `uncertain` 表示任务可 completed，但该项需要人工复核。
- Codex runtime failure，例如 `CODEX_CLI_UNAVAILABLE`、`CODEX_TIMEOUT`、`CODEX_EXIT_NONZERO` 或输出 invalid，会让业务任务 failed。

## 六、前端展示验收点

前端只展示后端返回的 `codex_reviews`，不重新计算 C01-C11 或 PTR 规则。

代码入口：

- `frontend/src/features/codex-review/components/CodexReviewPanel.tsx`
- `frontend/src/features/ptr-compare/components/PTRResults.tsx`
- `frontend/src/features/report-check/components/ReportResults.tsx`

验收点：

- PTR 结果页会聚合 `result.check_results[].codex_reviews` 并显示 Codex 审核统计。
- 报告自检结果页会聚合 `result.check_results[].codex_reviews` 并显示 Codex 审核统计。
- Finding 关联展示只基于后端返回的 `finding_id`、`finding_code`、`check_id` 和 `codex_reviews`。
- `add_finding` 只作为 Codex 建议展示，不进入 deterministic findings。
- Codex runtime failed/skipped 不再作为 completed 结果展示；后端任务应失败，上传页显示错误信息。

## 七、安全边界

- 不使用 GPT API client。
- 不调用 OpenAI Responses API 或 Chat API。
- 不把 Codex 审核逻辑写进 router。
- 不修改旧项目目录。
- 不修改 C01-C11 或 PTR 规则算法。
- 不让 Codex 读取项目源码。
- Codex audit 仍使用 `runtime/codex_audit/{task_id}/{package_id}/input/` 受控 workspace。
- `CodexCliRunner` 仍使用 read-only sandbox。
- 仍使用 `codex_review_output.schema.json`。
- `codex_review_output.schema.json` 只使用 Codex/OpenAI structured output 兼容子集；不使用 `uniqueItems`、`allOf`、`if/then/else` 等组合或高风险校验关键字。
- `add_finding` 必须包含 `suggested_finding`、evidence refs 必须存在且属于 target、重复 refs 等复杂 contract 由 `CodexReviewOutputParser` 校验。
- 默认每批最多生成 5 个 Codex audit targets；真实 codex-cli 业务验收建议先用 `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1` 和 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07` 缩小单批范围。
- batching 是性能策略，不是审核范围裁剪；后端 usecase 会继续发后续 batch，不能默认漏审。
- Codex runtime failure 会让任务 failed；deterministic findings 仍作为候选证据保留在可诊断链路中，但任务不得 completed。

## 八、T-CODEX-11B 真实验收记录

2026-06-23，用户显式启用真实 codex-cli 本地业务端到端验收，并使用 target 限流只审核 1 个 C07 target。

结果文件：

- `c26e1901-0173-49f5-abce-6a205d077bf3.result.json`

结果摘要：

- `codex_reviews_count: 1`
- `codex_status_counts: {"succeeded": 1}`
- `codex_verdict_counts: {"confirm": 1}`
- `codex_confidence_counts: {"high": 1}`
- `codex_target_type_counts: {"inspection_item": 1}`
- `codex_check_id_counts: {"C07": 1}`
- `codex_finding_code_counts: {"CONCLUSION_MISMATCH_002": 1}`
- `failed_reviews_count: 0`
- `deterministic_findings_count: 5194`

审核结论：

- Codex 确认 C07 规则初判，目标为 `inspection_item`，finding code 为 `CONCLUSION_MISMATCH_002`。
- 审核意见认为序号 3 的检验结果为“符合要求”，单项结论为“/”，而 `rule_context` 给出的期望结论为“符合”，因此支持规则初判。
- deterministic findings 保留，Codex review 没有覆盖原始 finding。

任务状态：

- T-CODEX-11B 验收通过。
- T-CODEX-11 整体完成。
- T-CODEX-12 已完成；本次结果证明单 target 限流可以用于真实 codex-cli report-check 业务验收。

后续风险：

- 当前样本 deterministic findings 数量很大，特别是 `C08=4894` 和 `C10=130`，需要后续单独收敛。
- 本次真实业务验收只覆盖 1 个 C07 target，扩大到更多规则或 PTR target 时仍建议小批量分步验收。

## 九、排查

- 脚本被拒绝：确认已设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1`。`--help` 和 `--print-config` 不需要 gate。
- `CODEX_CLI_UNAVAILABLE`：确认本机安装 Codex CLI，且 `CODEX_CLI_PATH` 或 `codex` 在 `PATH`。
- `CODEX_TIMEOUT`：优先降低 batch size，例如先设置 `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 CODEX_AUDIT_INCLUDED_CHECK_IDS=C07 CODEX_AUDIT_TIMEOUT_SECONDS=300`。
- `CODEX_EXIT_NONZERO` 且 stderr 出现 `invalid_json_schema`：优先检查 `codex_review_output.schema.json` 是否误用了 Codex structured output 不支持的 JSON Schema 关键字。
- `CODEX_OUTPUT_SCHEMA_INVALID` 或 `CODEX_OUTPUT_INVALID_JSON`：查看 `runtime/codex_audit/{task_id}/.../input/codex_review_output.json` 和 `prompt.md`；复杂 contract 失败会由 OutputParser 转成 failed review，再由 usecase 上升为 task failed。
- 后端无法启动：确认已安装后端依赖，运行 `cd backend && python -m pip install -e ".[dev]"`。
- 前端无展示：确认后端 result JSON 中确实有 `codex_reviews`，前端只展示后端结果，不会自行生成审核意见。
