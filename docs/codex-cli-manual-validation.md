# Codex CLI Manual Validation

更新时间：2026-06-18

本文记录 T-CODEX-09 的手动验收入口。当前阶段是 T-CODEX-09A：建立真实 Codex CLI 手动验收 harness，但默认不调用真实 Codex。

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

## 安全边界

- 使用 `read-only` sandbox。
- 使用 `--ephemeral`。
- 使用 `codex_review_output.schema.json` 约束输出 JSON。
- 使用 pytest `tmp_path` 创建受控临时 evidence workspace。
- 只提供最小合成 `EvidencePackage`，不提供真实私有 PDF 全文。
- 不读取旧项目目录。
- 不读取新项目源码目录作为 evidence。
- 不修改任何旧项目或新项目源码文件。
- Codex 输出异常、schema invalid、timeout 或非零退出都必须变为可审计 failed review。

## 运行命令

默认脚本会拒绝执行真实 Codex：

```bash
bash scripts/run-codex-cli-audit-smoke.sh
```

手动验收时显式开启：

```bash
ENABLE_CODEX_CLI_INTEGRATION=1 bash scripts/run-codex-cli-audit-smoke.sh
```

## 成功标准

- gated pytest 完成。
- `CodexCliRunner.run_review(...)` 返回至少一个 `CodexReviewResult`。
- `status=succeeded` 时，`verdict` 必须是 `confirm`、`refute`、`uncertain` 或 `add_finding`。
- `status=failed` 时，必须包含 `error.code` 和 `error.message`。
- 不出现未捕获异常泄漏。
- 不写入旧项目目录或新项目源码目录。

## 失败排查

- `CODEX_COMMAND_NOT_FOUND`：Codex CLI 未安装，或 `codex` 不在 `PATH`。
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

## 当前状态

- T-CODEX-09A 已提供默认 skip 的 manual integration pytest。
- T-CODEX-09A 已提供默认拒绝运行的脚本。
- 真实 Codex CLI 尚未执行。
- T-CODEX-09 整体仍未完成；需要 T-CODEX-09B 手动运行并记录结果。
