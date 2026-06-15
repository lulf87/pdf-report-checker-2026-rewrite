# Legacy Docs Inventory

状态：M47 迁移整理稿  
旧项目根目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13`  
新项目根目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3`

本清单只整理 M47 指定的旧 `design-system` 和 `docs` 文档资产。旧文档未被原样覆盖到新项目；本次新增的是经过新架构约束重写后的 UI 和产品基线。

## 1. 输出文件

| 新文件 | 来源 | 处理方式 |
| --- | --- | --- |
| `docs/ui/new-ui-spec.md` | 旧 `design-system/new-ui-spec.md`、`design-system/报告核对工具/MASTER.md`、`docs/ui-design-trends-research.md` | 合并并重写为新前端 UI 规范。 |
| `docs/ui/check-result-ui-design.md` | 旧 `docs/CHECKLIST_UI_DESIGN.md`、`docs/check-result-ui-design.md` | 合并并重写为新结果页设计。 |
| `docs/product/prd.md` | 旧 `docs/prd.md`，并对齐新 `known-requirements` 和 `rewrite-architecture` | 合并并重写为新产品需求基线。 |
| `docs/legacy-docs-inventory.md` | M47 旧文档盘点 | 新增迁移矩阵和取舍说明。 |

## 2. 迁移矩阵

| 旧文档 | 主要内容 | 新目标 / 处理 | 决策 | 说明 |
| --- | --- | --- | --- | --- |
| `design-system/new-ui-spec.md` | 深色 UI、玻璃面板、按钮、卡片、上传、结果页、动效、无障碍、token。 | `docs/ui/new-ui-spec.md` | 保留并合并 | 是本次最主要的 UI 来源；已按当前 `design-tokens.css` 和新前端边界重写。 |
| `design-system/报告核对工具/MASTER.md` | 轻量设计系统模板、浅色医疗配色、按钮/卡片/输入框/弹窗、页面模式和反模式。 | 不单独迁移，少量原则进入 `docs/ui/new-ui-spec.md` | 仅参考 / 局部废弃 | 与新项目深色玻璃拟态方向冲突；不采用其浅色 palette、营销化页面和模板式社交证明结构。 |
| `docs/CHECKLIST_UI_DESIGN.md` | C01-C11 清单、分组、核对项卡片、筛选、展开详情、旧数据结构建议。 | `docs/ui/check-result-ui-design.md` | 保留并合并 | 保留 C01-C11 分组和交互意图；旧组件路径和旧临时数据结构废弃。 |
| `docs/check-result-ui-design.md` | 结果摘要、问题面板、比对表、部件卡片、筛选器、响应式、Ant Design 主题示例。 | `docs/ui/check-result-ui-design.md` | 合并 / 局部废弃 | 保留摘要、问题面板、筛选和详情思路；不采用 Ant Design 作为新契约。 |
| `docs/prd.md` | 产品定位、Dashboard、PTR 核对、报告自身核对 C01-C11、旧 API、性能和准确性指标。 | `docs/product/prd.md` | 保留并对齐新架构 | 产品范围和 C01-C11/PTR 需求保留；旧 API 改为 `/api/tasks/*`；未验证指标标为待确认。 |
| `docs/tasks.md` | 旧项目开发阶段和任务清单。 | 不覆盖新 `docs/tasks.md` | 废弃为执行来源 / 保留追溯 | 与新迁移计划和任务编号冲突；仅作为历史产品计划参考。 |
| `docs/ui-design-trends-research.md` | 文档软件 UI 趋势、医疗软件专业性、数据密集表格、深色模式、状态反馈、动效建议。 | `docs/ui/new-ui-spec.md` | 原则合并 | 仅提取耐用原则；外部趋势链接和依赖建议不作为新项目需求。 |

## 3. 发现但未纳入 M47 的旧 docs

旧 `docs` 根目录还存在以下文件，但不在 M47 指定迁移清单内：

| 旧文档 | 本次处理 |
| --- | --- |
| `docs/INSPECTION_ITEM_ARCHITECTURE.md` | 未迁移。若后续涉及检验项目表架构，可在对应后端或产品任务中单独盘点。 |
| `docs/LLM_SETUP.md` | 未迁移。LLM 只能作为 infrastructure 能力，配置文档应在后续接入任务中按新架构重写。 |

## 4. 保留内容

- 深色、专业、数据优先的 UI 方向。
- 上传、进度、摘要、筛选、核对项列表、Finding 详情和导出流程。
- 报告自身核对 C01-C11 的页面入口和分组展示。
- PTR 第 2 章、条款层级、`见表 X`、范围排除、条款和表格差异的展示需求。
- 统一 `TaskStatus`、`TaskResult`、`CheckResult`、`Finding` 结果展示口径。

## 5. 重写内容

- 旧 UI token 改为当前 `frontend/src/shared/styles/design-tokens.css` 口径。
- 旧 PRD API 改为 `/api/tasks/*` 任务资源模型。
- 旧结果页的组件结构改为新类型驱动的展示说明。
- 旧产品需求中的架构职责改为 api/application/domain/rules/infrastructure 分层。
- 旧趋势文档中的依赖建议改为设计原则，不作为新增依赖依据。

## 6. 废弃或仅作历史参考

- 旧 Electron、`src/renderer`、旧桌面端职责边界。
- 旧 `/api/ptr/*`、`/api/report/*`、`/api/report-self-check/*` 作为新主线接口。
- 旧 Ant Design 主题和组件代码片段。
- 旧 `docs/tasks.md` 作为当前执行计划。
- 旧 `MASTER.md` 的浅色模板和营销化页面结构。
- 前端自行计算 C01-C11 或 PTR 业务结论的做法。

## 7. 差异和待确认

- 新项目必读清单中的 `docs/open-questions.md` 当前不存在；相关待确认项暂记录在本文件和 `docs/product/prd.md`。
- 旧 PRD 提到的文件大小、页数、耗时和 OCR 准确率指标未在本次验证，暂不作为产品验收标准。
- C01 的严格一致是否允许归一化例外，需要业务确认。
- PTR 附录、说明、图和外部标准引用在 UI 中如何展示，需要业务确认。
- 原始记录与报告核对是否进入后续产品主线，需要业务确认。

## 8. 验证建议

本任务是文档迁移整理，不修改前端样式或代码。若后续根据这些文档改动前端，应运行：

```bash
cd frontend && npm run build
```

本次文档级验证应检查：

- 四个目标文件存在。
- 旧主线接口没有被写成新主线。
- 文档包含 C01-C11、PTR、Finding、`/api/tasks/*`、保留/合并/废弃决策。
