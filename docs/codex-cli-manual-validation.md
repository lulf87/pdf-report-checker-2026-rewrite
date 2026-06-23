# Codex CLI Manual Validation

更新时间：2026-06-18

本文记录 T-CODEX-09 的手动验收入口和结果。T-CODEX-09A 已建立真实 Codex CLI 手动验收 harness；T-CODEX-09B 已由用户显式开启 gate 并完成手动验收。普通测试仍默认不调用真实 Codex。

## 目的

真实 Codex CLI 只用于产品运行时受控 auditor / judge 的手动验收。验收目标不是判断某个业务结论一定为 confirm 或 refute，而是证明真实 `codex exec` 可以在受控 evidence workspace 中运行，并产出符合 JSON schema 或可审计 failed fallback 的 `CodexReviewResult`。

## 为什么默认不运行

- 真实 Codex CLI 依赖本机登录状态、网络、模型可用性和外部进程行为。
- 普通单元测试和全量 pytest 必须稳定、可离线、可重复，不能默认调用真实 Codex。
- Codex runtime auditor 有严格安全边界：只有显式手动验收才允许真实执行。

## 前置条件

- 本机已安装 Codex CLI。
- 本机已登录 Codex CLI。
- 在终端中可以运行 `codex exec`。
- 后端测试依赖已安装，可运行 `python -m pytest`。
- 如果当前 shell 的 `python` 不是项目 Python，可以通过 `PYTHON_BIN=/path/to/python` 指定解释器。

## 安全边界

- 使用 `read-only` sandbox。
- 使用 `--ephemeral`。
- 使用 `codex_review_output.schema.json` 约束输出 JSON。
- `codex_review_output.schema.json` 只使用 Codex/OpenAI structured output 兼容的基础 JSON Schema 子集；跨字段和证据引用校验由 `CodexReviewOutputParser` 完成。
- 使用 pytest `tmp_path` 创建受控临时 evidence workspace。
- 只提供最小合成 `EvidencePackage`，不提供真实私有 PDF 全文。
- 不读取旧项目目录。
- 不读取新项目源码目录作为 evidence。
- 不修改任何旧项目或新项目源码文件。
- Codex 输出异常、schema invalid、timeout 或非零退出都必须变为可审计 failed review。

## Structured Output Schema 边界

真实 Codex CLI structured output 不支持完整 JSON Schema。为避免运行时被 response format 拒绝，`codex_review_output.schema.json` 不使用 `uniqueItems`、`allOf`、`if/then/else`、`not`、`dependentRequired`、`dependentSchemas`、`minLength`、`maxLength`、`pattern`、`format`、`minItems` 或 `maxItems`。

Schema 只约束基础结构、required 字段、enum、nullable 字段和 `additionalProperties: false`。以下规则不放在 schema 中，而由 `CodexReviewOutputParser` 解析后校验并降级为 failed review：

- `add_finding` 必须包含 `suggested_finding`。
- review 必须覆盖所有 request targets。
- target 不能未知或重复。
- `evidence_refs` 不能未知、不能越过 target 允许范围、不能重复。
- `suggested_finding.evidence_refs` 必须引用 evidence package 中存在的证据。

## 运行命令

默认脚本会拒绝执行真实 Codex：

```bash
bash scripts/run-codex-cli-audit-smoke.sh
```

手动验收时显式开启：

```bash
ENABLE_CODEX_CLI_INTEGRATION=1 bash scripts/run-codex-cli-audit-smoke.sh
```

如果系统 `python` 不是已安装 pytest 的项目环境，显式指定 Python：

```bash
PYTHON_BIN=/path/to/python ENABLE_CODEX_CLI_INTEGRATION=1 bash scripts/run-codex-cli-audit-smoke.sh
```

推荐在多 Python 环境中使用 `PYTHON_BIN` 指向带有 pytest 和后端 dev 依赖的解释器。

## 验收结果

验收日期：2026-06-18

第一次脚本运行：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3
ENABLE_CODEX_CLI_INTEGRATION=1 bash scripts/run-codex-cli-audit-smoke.sh
```

结果失败：

```text
/opt/homebrew/opt/python@3.14/bin/python3.14: No module named pytest
```

原因：脚本默认使用的 `python3` 指向 Homebrew Python 3.14，该环境没有安装 pytest。这不是 Codex CLI audit 链路失败，而是 Python 解释器选择问题。

随后确认当前 shell 的 Python 可用：

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

- T-CODEX-09B 验收通过。
- T-CODEX-09 整体完成。
- `tests/integration/test_codex_cli_manual.py` 在 gate 开启时显式使用 `CodexCliRunner(enabled=True, allow_real_execution=True, sandbox="read-only")` 并调用 `run_review(...)`。
- 普通未设置 `ENABLE_CODEX_CLI_INTEGRATION` 的测试仍默认 skip。
- smoke 使用受控 `tmp_path` evidence workspace。
- sandbox 为 read-only。
- 使用 `codex_review_output.schema.json`。
- 没有异常冒泡。
- 没有修改旧项目目录。
- 没有默认启用 API 真实 Codex。
- `PYTHON_BIN` 是推荐的脚本参数，用于指定带 pytest 的 Python 环境。

## 成功标准

- gated pytest 完成。
- `CodexCliRunner.run_review(...)` 返回至少一个 `CodexReviewResult`。
- `status=succeeded` 时，`verdict` 必须是 `confirm`、`refute`、`uncertain` 或 `add_finding`。
- `status=failed` 时，必须包含 `error.code` 和 `error.message`。
- 不出现未捕获异常泄漏。
- 不写入旧项目目录或新项目源码目录。

## 失败排查

- `No module named pytest` 或脚本提示 `pytest: not available`：安装后端 dev 依赖，运行 `cd backend && python -m pip install -e ".[dev]"`；或使用 `PYTHON_BIN=/path/to/python ENABLE_CODEX_CLI_INTEGRATION=1 bash scripts/run-codex-cli-audit-smoke.sh` 指向已有 pytest 的 Python。
- `CODEX_CLI_UNAVAILABLE`：Codex CLI 未安装，或 `codex` 不在 `PATH`；也可设置 `CODEX_CLI_PATH=/path/to/codex`。
- 登录失败或权限失败：确认本机 Codex CLI 已登录，并能独立执行 `codex exec`。
- `CODEX_TIMEOUT`：模型响应超过 timeout；可在测试中临时调大 timeout，但不要默认放宽普通测试。
- `CODEX_OUTPUT_SCHEMA_INVALID`：Codex 输出不符合 schema；检查 `codex_review_output.json` 和 prompt。
- `CODEX_OUTPUT_INVALID_JSON`：Codex 输出不是 JSON；确认 prompt 要求和 output schema 参数。
- `CODEX_WORKSPACE_FORBIDDEN`：workspace 指向了项目根、旧项目、源码目录或其他禁止路径。
- sandbox denied：确认 runner 使用 `--sandbox read-only`，且 evidence package 不要求 Codex 读取未授权文件。

## 不应做的事

- 不要使用 `danger-full-access`。
- 不要使用 `workspace-write`。
- 不要把项目根目录作为 `--cd`。
- 不要把旧项目目录作为 `--cd`。
- 不要把真实私有 PDF 全文塞入 prompt。
- 不要把真实 Codex 输出写入稳定 Golden expected。
- 不要默认启用 API 真实 Codex。
- 不要在普通 `pytest tests/ -v` 中真实调用 Codex CLI。

## 本地 API 运行时配置

T-CODEX-MANDATORY-01 后，产品运行路径默认构建 `CodexAuditService + CodexCliRunner`。不存在用户层面的 disabled/fake/codex-cli 模式选择；`FakeCodexRunner` 只允许在 pytest 或显式测试 dependency override 中使用。普通 pytest 仍通过 fake/monkeypatch 避免真实 Codex CLI。

当前环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `CODEX_CLI_PATH` | `codex` | 本机 Codex CLI 可执行文件。 |
| `CODEX_AUDIT_TIMEOUT_SECONDS` | `300` | Codex CLI runner timeout。 |
| `CODEX_AUDIT_RUNTIME_DIR` | `runtime/codex_audit` | 受控 evidence workspace 根目录。 |
| `CODEX_AUDIT_MAX_TARGETS_PER_BATCH` | `5` | 单批 target 数量；分批不是漏审上限。 |
| `CODEX_AUDIT_SANDBOX` | `read-only` | 固定只读 sandbox。 |
| `CODEX_AUDIT_EPHEMERAL` | `true` | 是否使用 `--ephemeral`。 |

启动本地后端：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3/backend
CODEX_CLI_PATH=codex \
CODEX_AUDIT_RUNTIME_DIR=runtime/codex_audit \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=5 \
python -m uvicorn app.main:app --reload
```

安全边界保持不变：

- 不使用 GPT API client。
- 不调用 OpenAI Responses API 或 Chat API。
- API 依赖只通过 factory 装配 usecase，不在 router 中写 Codex CLI 逻辑。
- Codex CLI workspace 仍由 `EvidencePackageWriter` 写入 `runtime/codex_audit/{task_id}/{package_id}/input/`。
- `CodexCliRunner` 仍使用 read-only sandbox、output schema 和 timeout。
- Codex runtime failure 会让业务任务 failed，不再 completed 后只携带 failed review。
- Codex review 写入 `codex_reviews`，不覆盖或删除 deterministic findings；deterministic findings 在兼容字段中作为 candidate 保留。
- 旧 `CODEX_AUDIT_ENABLED`、`CODEX_AUDIT_BACKEND`、`CODEX_AUDIT_ALLOW_REAL_EXECUTION` 字段仅为 deprecated 兼容，不作为产品运行模式。

## 当前状态

- T-CODEX-09A 已提供默认 skip 的 manual integration pytest。
- T-CODEX-09A 已提供默认拒绝运行的脚本。
- T-CODEX-09B 已由用户显式运行并记录结果。
- T-CODEX-09 整体已完成。
- T-CODEX-10 已完成本地运行时配置和依赖装配；T-CODEX-MANDATORY-01 已将产品运行路径纠偏为 mandatory Codex CLI audit。
