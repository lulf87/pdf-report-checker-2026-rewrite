# Codex Audit Local E2E

更新时间：2026-06-18

本文记录 T-CODEX-11A 的本地业务端到端验收入口。目标是验证本地 Web 工具在 fake / codex-cli 模式下可以展示 Codex 审核意见，同时确认默认模式不启用 Codex audit。

## 一、目的

- 验证默认模式下，本地后端不调用 Codex，`codex_reviews` 为空或缺省为空数组。
- 验证 fake 模式下，上传 PTR/报告任务后，后端通过 `FakeCodexRunner` 生成 `codex_reviews`。
- 验证 codex-cli 模式下，本地后端通过 `CodexCliRunner` 调用 `codex exec`，并把结果写入 `codex_reviews`。
- 验证前端只展示后端返回的 `codex_reviews`，不重新计算 C01-C11 或 PTR 规则。

本阶段只新增验收脚本和文档，不要求真实运行 Codex CLI。

## 二、默认模式

默认不启用 Codex audit。

启动后端：

```bash
cd backend
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
4. 预期：`check_results[].codex_reviews` 为空数组，或由前端按空数组处理；页面不显示 Codex 审核意见面板。

可用脚本验证默认模式：

```bash
MODE=disabled \
TASK_TYPE=ptr-compare \
PTR_FILE=/path/to/ptr.pdf \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

报告自检：

```bash
MODE=disabled \
TASK_TYPE=report-check \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

脚本默认检查 `codex_reviews` 为空；如果只是想保存结果、不校验数量，可以追加 `EXPECT_CODEX_REVIEWS=any`。

## 三、Fake 模式

fake 模式用于本地 UI 联调，不调用真实 Codex CLI。

启动后端：

```bash
cd backend
CODEX_AUDIT_ENABLED=1 \
CODEX_AUDIT_BACKEND=fake \
python -m uvicorn app.main:app --reload
```

启动前端：

```bash
cd frontend
npm run dev
```

业务验收：

1. 选择会产生可审核 deterministic finding 的样本，例如 PTR 表格参数值差异，或报告 C02/C03/C04/C05/C06/C07 finding。
2. 上传样本。
3. 查看结果页。
4. 预期：后端结果中出现 `codex_reviews`；前端展示 Codex 审核统计、关联 finding 审核意见或其他 Codex 审核意见。
5. 原始 deterministic finding 仍保留，不被 fake review 删除或覆盖。

可用脚本验证 fake 模式：

```bash
MODE=fake \
TASK_TYPE=ptr-compare \
PTR_FILE=/path/to/ptr.pdf \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

如需脚本代启后端：

```bash
MODE=fake \
START_BACKEND=1 \
TASK_TYPE=ptr-compare \
PTR_FILE=/path/to/ptr.pdf \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

脚本默认要求 fake 模式下 `codex_reviews` 非空。若样本没有触发可审核 finding，会出现 0 条 review；这不是 runner 失败，需要换用能触发 C02/C03/C04/C05/C06/C07 或 PTR clause/table/parameter finding 的样本。

## 四、Codex CLI 模式

codex-cli 模式会调用真实 `codex exec`。只有显式设置 gate 时才允许真实执行。

启动后端：

```bash
cd backend
CODEX_AUDIT_ENABLED=1 \
CODEX_AUDIT_BACKEND=codex-cli \
CODEX_AUDIT_ALLOW_REAL_EXECUTION=1 \
CODEX_AUDIT_RUNTIME_DIR=runtime/codex_audit \
CODEX_AUDIT_TIMEOUT_SECONDS=120 \
python -m uvicorn app.main:app --reload
```

启动前端：

```bash
cd frontend
npm run dev
```

业务验收：

1. 确认本机 Codex CLI 已安装并登录。
2. 选择受控样本，不使用旧项目目录作为输入。
3. 上传 PTR + 报告或报告自检样本。
4. 查看结果页和 JSON。
5. 预期：`codex_reviews` 中出现 `succeeded`、`failed` 或 `skipped` 的可审计审核结果；即使 Codex 失败，deterministic findings 仍保留。

可用脚本验证 codex-cli 模式：

```bash
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
MODE=codex-cli \
CODEX_AUDIT_ALLOW_REAL_EXECUTION=1 \
TASK_TYPE=ptr-compare \
PTR_FILE=/path/to/ptr.pdf \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

如需脚本代启后端：

```bash
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
MODE=codex-cli \
CODEX_AUDIT_ALLOW_REAL_EXECUTION=1 \
START_BACKEND=1 \
TASK_TYPE=ptr-compare \
PTR_FILE=/path/to/ptr.pdf \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

脚本安全要求：

- `MODE=codex-cli` 必须设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1`。
- `MODE=codex-cli` 必须设置 `CODEX_AUDIT_ALLOW_REAL_EXECUTION=1`。
- 未满足 gate 时，脚本拒绝运行，不调用真实 Codex CLI。

## 五、脚本说明

脚本路径：

```bash
scripts/run-codex-audit-local-e2e.sh
```

查看帮助：

```bash
bash scripts/run-codex-audit-local-e2e.sh --help
```

查看安全配置，不上传文件、不启动服务、不调用 Codex：

```bash
MODE=codex-cli bash scripts/run-codex-audit-local-e2e.sh --print-config
```

常用参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `MODE` | `disabled` | `disabled`、`fake` 或 `codex-cli`。 |
| `TASK_TYPE` | `ptr-compare` | `ptr-compare` 或 `report-check`。 |
| `BASE_URL` | `http://127.0.0.1:8000` | 已运行后端地址。 |
| `START_BACKEND` | `0` | 为 `1` 时脚本代启后端。 |
| `PTR_FILE` | 无 | PTR PDF，本地业务样本路径。 |
| `REPORT_FILE` | 无 | 报告 PDF，本地业务样本路径。 |
| `EXPECT_CODEX_REVIEWS` | `auto` | `auto`、`empty`、`nonempty` 或 `any`。 |
| `OUTPUT_DIR` | `runtime/codex_audit_local_e2e` | 保存 task/result JSON 的本地目录。 |

脚本会：

1. 检查后端健康状态。
2. 上传 PTR/报告任务或报告自检任务。
3. 轮询 `/api/tasks/{task_id}`。
4. 下载 `/api/tasks/{task_id}/result`。
5. 统计 `check_results[].codex_reviews` 数量。
6. 按模式校验 `codex_reviews` 是否符合预期。

脚本输出边界：

- 进度日志和任务状态输出到 stderr，格式为 `[codex-audit-local-e2e] ...`。
- 内部用于传递结果 JSON 路径的 stdout 保持为单行文件路径，避免 command substitution 捕获到日志。
- 脚本会校验结果路径非空、存在、不包含换行，并且以 `.json` 结尾。

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
- `failed` / `skipped` review 显示诊断，不阻断 deterministic findings 展示。

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
- 失败时只写 `codex_reviews` failed/skipped，不影响 deterministic findings。

## 八、排查

- fake 模式没有 `codex_reviews`：确认样本是否产生可审核 deterministic finding。无 finding 或非优先接入规则不会触发 audit。
- codex-cli 模式被脚本拒绝：确认同时设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1` 和 `CODEX_AUDIT_ALLOW_REAL_EXECUTION=1`。
- `CODEX_COMMAND_NOT_FOUND`：确认本机安装 Codex CLI，且 `codex` 在 `PATH`。
- `CODEX_OUTPUT_SCHEMA_INVALID` 或 `CODEX_OUTPUT_INVALID_JSON`：查看 `runtime/codex_audit/{task_id}/.../input/codex_review_output.json` 和 `prompt.md`。
- 后端无法启动：确认已安装后端依赖，运行 `cd backend && python -m pip install -e ".[dev]"`。
- 前端无展示：确认后端 result JSON 中确实有 `codex_reviews`，前端只展示后端结果，不会自行生成审核意见。
