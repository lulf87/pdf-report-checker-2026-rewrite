# Rewrite 分支边界说明

本文用于冻结旧项目资产、明确当前重写工作的执行边界，并作为后续任务继续迁移前的入口约束。本文只描述边界和流程，不实现新功能，不迁移 C01-C11 或 PTR 规则。

## 项目目录

- 新项目目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3`
- 旧项目目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13`

旧项目目录只读。后续任务只能读取、分析和对照旧项目资产，不允许在旧项目目录中直接修改、移动、删除或生成文件。所有新增代码、测试、fixture、文档和运行配置都必须写入新项目目录。

## 新主线

新项目是 Web 主线，不延续旧桌面启动链路：

- `backend`：FastAPI。
- `frontend`：React + TypeScript + Vite。

旧 Electron、`python_backend`、`src/main`、`src/renderer` 不进入新主线。若后续在旧项目或历史备份中发现这些目录的可用业务素材，也只能先作为 legacy 资产登记，再抽取可追溯的业务规则、测试样例或交互经验，不能直接搬入新架构。

## 运行时与生成物边界

以下目录或产物不作为源码资产，不应提交或纳入业务模型：

- `uploads`
- `temp`
- `logs`
- `node_modules`
- `dist`
- `.venv`
- `__pycache__`

旧项目中的上传文件、临时图像、运行日志、构建产物和依赖目录只能作为运行时痕迹识别。需要迁移样例或 Golden File 时，必须先确认来源，再复制到新项目受控 fixture 目录，并说明用途和来源。

## 分层边界

新项目必须遵守以下后端分层：

- `api` 层只处理 HTTP 输入输出、请求校验、状态码和响应序列化。
- `application` 层负责编排 usecase、任务生命周期、规则调用和结果聚合。
- `domain` 层定义稳定领域模型、枚举、值对象和结果契约。
- `rules` 层定义并实现 C01-C11 和 PTR 等确定性规则。
- `infrastructure` 层处理 PDF、OCR、文件、导出、LLM/VLM、日志等外部能力适配。

不得把业务规则写进 router。不得在 PDF parser、OCR adapter、文件存储、导出适配器或前端组件中混入 C01-C11 或 PTR 最终判定。LLM/VLM 只能作为 infrastructure 能力或辅助解释能力，不能替代确定性规则输出最终结论。

## 规则输出契约

所有业务问题、证据不足、需人工复核项和系统诊断项统一输出 `Finding`。不同规则不得自由拼接临时错误结构。

`Finding` 必须保留可追溯信息，包括规则编号、严重级别、问题代码、中文消息、期望值、实际值、位置、证据和必要 metadata。前端、导出和 Golden File 均应消费统一 `Finding`，不得重新计算业务结论。

## 迁移依据

C01-C11 和 PTR 迁移必须基于可追溯资产：

- 旧项目代码和测试。
- 旧项目规格文档或当前 `docs/known-requirements.md`。
- `docs/legacy-inventory.md`、`docs/rewrite-architecture.md`、`docs/migration-plan.md`。
- `docs/spec-code-test-gaps.md` 中记录的规格、代码和测试差异。
- 用户明确给出的任务提示和业务口径。

如果旧规格、旧实现、旧测试或新需求存在不一致，不得自行拍脑袋决定。必须先记录到 `docs/spec-code-test-gaps.md` 或 `docs/open-questions.md`，再按已确认口径实现。

## 执行顺序和停止规则

后续迁移应按 `docs/tasks.md` 的任务顺序逐项执行。每次只执行一个任务，并在当前任务完成、验收命令通过、文档状态同步后，才进入下一项。

任一任务测试失败、构建失败、验收命令失败或发现未裁决的业务规则冲突时，应停止继续迁移，先记录失败原因、受影响文件和待确认问题。测试失败时不得继续下一个任务，也不得通过削弱规则、跳过测试或隐藏错误来推进状态。

本文完成后，T01 仅表示 rewrite 边界说明已补齐，不表示 T02-T12 或后续 C01-C11/PTR 迁移自动完成。
