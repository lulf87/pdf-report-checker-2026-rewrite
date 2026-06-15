# 核对结果 UI 设计

状态：M47 迁移整理稿  
适用范围：报告自身核对、PTR 条款核对的结果展示  
来源：
- 旧 `docs/CHECKLIST_UI_DESIGN.md`
- 旧 `docs/check-result-ui-design.md`
- 新 `docs/known-requirements.md`
- 新 `docs/rewrite-architecture.md`
- 新 `frontend/src/entities/*/types.ts`

本文保留旧文档中“摘要、分组、筛选、问题详情、证据展示、差异高亮”的产品价值，但不迁移旧组件路径、Ant Design 示例或旧 API。

## 1. 数据契约

结果页只消费新任务 API 返回的数据：

| 类型 | 关键字段 | UI 用途 |
| --- | --- | --- |
| `TaskStatus` | `task_id`、`task_type`、`status`、`progress`、`current_step`、`logs` | 上传后进度、任务状态和错误展示。 |
| `TaskResult` | `summary`、`check_results`、`findings`、`diagnostics`、`metadata` | 结果页总数据源。 |
| `CheckResult` | `check_id`、`check_name`、`status`、`severity`、`summary`、`findings`、`evidence` | 核对项列表和分组展示。 |
| `Finding` | `id`、`check_id`、`severity`、`code`、`message`、`location`、`evidence`、`missing_evidence`、`diff_fragments`、`confidence` | 问题详情、证据和定位。 |

前端不重新计算核对结论。若后端未返回 `Finding` 或证据，前端只能展示“无结构化证据”或 diagnostics，不能自行补充业务判断。

## 2. 页面状态

| 状态 | 展示内容 |
| --- | --- |
| 未上传 | 上传控件、模块说明、历史任务入口若后端支持。 |
| 上传中 | 文件卡片、禁用主操作、上传错误。 |
| 处理中 | `TaskStatus.progress`、`current_step`、日志片段、取消或返回入口。 |
| 已完成 | 摘要、筛选、核对项列表、Finding 详情、导出。 |
| 任务失败 | `error_message`、可重试入口、可复制 diagnostics。 |

## 3. 结果页结构

推荐从上到下：

1. 任务标题栏：模块名、任务 ID、状态、导出按钮。
2. 摘要区：总核对项、通过、失败、需复核、系统错误、Finding 数量。
3. 筛选区：严重级别、规则编号、状态、仅显示问题。
4. 核对项列表：按报告规则分组或按 PTR 类型分组。
5. 详情区：Finding、证据、缺失证据、diff、诊断信息。

摘要卡片和筛选器是操作区，不应埋入多层卡片。

## 4. 报告自身核对

报告自身核对固定围绕 C01-C11 展示。分组可沿用旧清单文档的产品结构，但最终名称和状态来自后端 `CheckResult`。

| 分组 | 规则 | 展示重点 |
| --- | --- | --- |
| 基础字段一致性 | C01-C03 | 首页与第三页字段、第三页扩展字段、生产日期格式和值一致性。 |
| 视觉与附件覆盖 | C04-C06 | 样品描述表格、照片覆盖、中文标签覆盖。 |
| 检验项目表 | C07-C10 | 单项结论、非空字段、序号连续性、续表标记。 |
| 页码 | C11 | 页码缺失、跳号、总页数不一致、末页不匹配。 |

### 4.1 核对项行

每条 `CheckResult` 行展示：

- `check_id`：如 `C01`。
- `check_name`：由后端返回。
- `status`：通过、失败、需复核、跳过或系统错误。
- `severity`：若存在 Finding，展示最高严重级别。
- `summary`：短摘要。
- Finding 计数和证据计数。

### 4.2 展开详情

展开后优先展示：

1. Finding message 和 code。
2. 位置：页码、表格、行列、字段、文本 span 或描述。
3. expected/actual：若后端提供，按字段展示。
4. evidence：原文、归一化文本、方法、置信度。
5. missing evidence：缺失来源、原因、期望位置。
6. diff fragments：按后端片段渲染。

若某条规则 `status=system_error`，详情区展示错误摘要和 diagnostics，不把系统错误混成业务不一致。

## 5. PTR 条款核对

PTR 结果展示重点是“范围、条款、表格、差异、证据”。前端不判断 PTR 第 2 章范围，也不展开 `见表 X`，只展示后端解析和比对结果。

推荐分组：

| 分组 | 对应内容 |
| --- | --- |
| 范围解析 | 首页/第三页检验项目范围、排除项、无法解析 selector。 |
| 条款正文 | PTR 第 2 章 in-scope leaf clauses 与报告标准要求对照。 |
| 表格引用 | `见表 X`、`符合表 X`、`按表 X` 引用解析状态。 |
| 参数差异 | 参数名、值、单位、条件、允许误差等结构化差异。 |
| 诊断 | 无文本页、OCR 低置信、表格不可解析、候选项歧义。 |

### 5.1 PTR 对照行

PTR 对照行建议展示：

- PTR 条款号和标题。
- 条款 taxonomy，如 requirement、group_heading、method、appendix、note、table_reference。
- 报告侧匹配位置或缺失说明。
- 差异摘要和 Finding 数。
- 展开后双栏显示 PTR 内容与报告内容。

### 5.2 仅显示问题

PTR 页面必须提供“仅显示不一致/需复核项”。通过项可以留在 JSON 和完整视图中，用于审计。

## 6. 筛选和排序

基础筛选：

| 筛选项 | 数据来源 |
| --- | --- |
| 规则编号 | `CheckResult.check_id` 或 `Finding.check_id`。 |
| 状态 | `CheckResult.status`。 |
| 严重级别 | `Finding.severity`。 |
| 置信度 | `Finding.confidence` 或 evidence confidence。 |
| 仅显示问题 | `status in fail/review/system_error` 或存在 error/warn Finding。 |

排序建议：

1. `severity=error`
2. `severity=warn`
3. `system_error`
4. `info`
5. `pass`

排序只是展示层行为，不改变后端结果。

## 7. 导出

结果页导出入口统一使用：

```text
GET /api/tasks/{task_id}/export?format=json|pdf|xlsx
```

导出按钮应在没有结果时禁用。导出失败时展示 API 错误，不生成前端自定义报告替代后端导出。

## 8. 废弃的旧实现细节

以下旧文档内容不作为新项目实现契约：

- 旧 `CheckResult.jsx`、`src/renderer`、旧 Electron 组件路径。
- 旧 Ant Design 主题配置和组件拆分建议。
- 旧 `/api/ptr/*`、`/api/report/*` 或 `/api/report-self-check/*` 作为新主线接口。
- 前端根据临时数据结构自行判断 C01-C11 或 PTR 结论。

## 9. 验收清单

修改结果页时检查：

- 每个 C01-C11 规则都有展示入口。
- PTR 范围、条款、表格和参数差异都有展示入口。
- Finding 的 evidence、missing evidence、location、diff fragments 不被丢弃。
- 筛选和排序只改变展示，不改变业务结论。
- 任务失败、单规则系统错误、证据不足三类状态有不同展示。
- 若改动前端代码，运行 `cd frontend && npm run build`。
