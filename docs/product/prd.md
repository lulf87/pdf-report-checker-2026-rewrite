# Report Checker Pro 产品需求基线

状态：M47 迁移整理稿  
来源：
- 旧 `docs/prd.md`
- 新 `docs/known-requirements.md`
- 新 `docs/rewrite-architecture.md`
- 新 `docs/migration-plan.md`
- 当前前端 API client 和类型定义

本文将旧 PRD 中可复用的产品需求合并到新架构口径。旧 PRD 中的旧 API 路径、旧任务拆分、未验证性能指标和实现细节不直接进入新主线。

## 1. 产品定位

Report Checker Pro 用于辅助检验报告复核，围绕 PDF 报告、PTR 产品技术要求和结构化核对结果，帮助用户发现字段不一致、证据缺失、条款遗漏、表格参数差异和需要人工复核的问题。

目标用户：

- 医疗器械检验报告编制、审核和复核人员。
- 需要在报告发布前检查 PTR 条款摘录和报告自身一致性的人员。

部署形态：

- 新主线为纯 Web 应用。
- 后端：FastAPI。
- 前端：React + TypeScript + Vite。
- PDF：PyMuPDF。
- OCR：PaddleOCR。
- 旧 Electron、`src/renderer` 和历史 `python_backend` 不进入新主线。

## 2. 功能模块

| 模块 | 输入 | 输出 |
| --- | --- | --- |
| 报告自身核对 | 检验报告 PDF | C01-C11 `CheckResult`、统一 `Finding`、证据、diagnostics、导出文件。 |
| PTR 条款核对 | PTR PDF + 检验报告 PDF | PTR 范围、条款正文、表格引用、参数差异、统一 `Finding`、导出文件。 |

原始记录与报告核对在旧项目中出现过，但不是 M47 迁移后的当前主线需求。是否纳入后续版本需单独确认。

## 3. 新 API 契约

新项目统一围绕 task 资源。旧 `/api/ptr/*`、`/api/report/*`、`/api/report-self-check/*` 不作为新主线接口。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查。 |
| `POST` | `/api/tasks/report-check` | 创建报告自身核对任务，multipart 字段 `report_file`，可选 `enable_llm`。 |
| `POST` | `/api/tasks/ptr-compare` | 创建 PTR 条款核对任务，multipart 字段 `ptr_file`、`report_file`。 |
| `GET` | `/api/tasks/{task_id}` | 查询任务状态，返回 `TaskStatus`。 |
| `GET` | `/api/tasks/{task_id}/result` | 获取任务结果，返回 `TaskResult`。 |
| `GET` | `/api/tasks/{task_id}/export?format=json\|pdf\|xlsx` | 导出结果。 |

前端通过 `TaskStatus`、`TaskResult`、`CheckResult`、`Finding` 类型消费结果，不依赖临时 dict。

## 4. 结果模型

统一输出要求：

- 所有核对问题输出 `Finding`。
- `Finding.check_id` 指向规则，如 `C01`、`C11`、`PTR_CLAUSE` 或 `PTR_TABLE`。
- `Finding.severity` 使用 `error`、`warn`、`info`。
- `Finding` 应尽量包含 `location`、`evidence`、`missing_evidence`、`diff_fragments`、`confidence`。
- 单条规则失败应成为 `CheckResult.status=system_error` 或诊断信息，不应直接让整个任务失败，除非任务无法继续。

## 5. PTR 条款核对需求

PTR 核对的主范围来自产品技术要求第 2 章，并结合报告首页或第三页的检验项目范围。

| 需求 | 新口径 |
| --- | --- |
| 章节范围 | PTR 第 2 章为主核对范围。 |
| 条款层级 | 保留 `2`、`2.1`、`2.1.1` 等层级和父子关系。 |
| 主统计排除 | 检验方法、附录、说明、图、外部标准解释等不进入主一致性统计。 |
| 条款正文 | in-scope 叶子要求条款应严格比对报告标准要求。 |
| 范围排除 | 保留首页范围和括号排除项经验，但具体语法仍需业务确认。 |
| 表格引用 | `见表 X`、`符合表 X`、`按表 X` 必须解析并展开对应表格参数比对。 |
| 证据 | 输出 PTR 来源、报告来源、页码、表格、行列、差异和诊断。 |

PTR 规则应输出可定位的 Finding，例如：

- `PTR_SCOPE_UNPARSED`
- `PTR_CLAUSE_MISSING`
- `PTR_CLAUSE_TEXT_MISMATCH`
- `PTR_TABLE_REFERENCE_MISSING`
- `PTR_PARAM_VALUE_MISMATCH`
- `PTR_PARAM_UNIT_MISMATCH`

这些 code 是产品口径示例，最终以后端规则注册表为准。

## 6. 报告自身核对 C01-C11

新项目保留 C01-C11 编号和语义，不直接沿用旧项目旧编号含义。

| 编号 | 名称 | 核对目标 |
| --- | --- | --- |
| C01 | 首页与第三页字段一致性 | 委托方、样品名称、型号规格等字段在首页和第三页之间一致。 |
| C02 | 第三页扩展字段与中文标签 OCR | 第三页扩展字段与中文标签 OCR 或相关证据一致。 |
| C03 | 生产日期格式和值一致性 | 生产日期格式合规，报告字段、标签或表格中的值一致。 |
| C04 | 样品描述表格与中文标签 OCR | 样品描述表格的关键字段与中文标签 OCR 证据一致。 |
| C05 | 照片覆盖 | 报告照片覆盖关键样品、标签或需要留存的图像证据。 |
| C06 | 中文标签覆盖 | 中文标签证据覆盖所需字段。 |
| C07 | 单项结论逻辑 | 检验项目单项结论与判定规则、限值和结果一致。 |
| C08 | 非空字段 | 检验项目表中的必填字段不为空。 |
| C09 | 序号连续性 | 检验项目序号连续、无重复、无异常跳号。 |
| C10 | 续表标记 | 续表标记与跨页表格状态一致。 |
| C11 | 页码连续性 | 打印页码连续，总页数和末页一致。 |

C01-C11 每条规则必须独立，可单独启用、单独测试、单独输出 Finding。

## 7. 结果展示和导出

前端结果页应支持：

- 任务进度和当前步骤。
- 总览摘要：总核对项、通过、失败、需复核、系统错误、不同 severity Finding 数量。
- 报告自检 C01-C11 分组展示。
- PTR 结果按范围、条款、表格、参数差异分组展示。
- Finding 详情：位置、证据、缺失证据、expected/actual、diff。
- 筛选：规则编号、状态、severity、仅显示问题。
- 导出：JSON、PDF、XLSX。

前端只展示后端返回结果，不重新计算 C01-C11 或 PTR 核对结论。

## 8. 非功能需求

已纳入新项目口径：

- 旧输入文件不得被修改。
- API、application、domain、rules、infrastructure 分层清晰。
- LLM 只能作为 infrastructure 能力或辅助解释能力，不替代确定性规则。
- 所有规则输出统一 Finding。
- Golden File 测试是核心保障。

旧 PRD 中以下指标未在本次迁移中验证，暂不固化为验收标准：

- 单文件 50MB 限制。
- 200 页 PDF 限制。
- 固定处理耗时目标。
- OCR 准确率百分比。
- 旧推荐依赖和 Ant Design 主题配置。

若这些指标需要进入产品承诺，应补充测试样本、测量脚本和验收标准。

## 9. 不进入当前主线

- 旧 Electron 主进程和 renderer。
- 旧 `python_backend`。
- 旧同步接口作为新主线。
- 旧 `docs/tasks.md` 作为当前执行计划。
- 前端实现业务核对规则。
- 未确认的原始记录核对模块。

## 10. 待人工确认

以下问题来自新旧文档差异，不能在 M47 中自行定死：

- 旧 PRD 性能指标和文件限制是否需要恢复为产品验收标准。
- C01 严格一致是否允许全半角、空格、自然换行、标点等归一化例外。
- PTR 附录、说明、图和外部标准引用是隐藏、显示为 INFO，还是作为 out-of-scope 展示。
- PTR 首页范围排除语法是否仅限括号，还是支持跨句或表格声明。
- 原始记录与报告核对是否进入后续版本主导航。
