# 新前端 UI 设计规范

状态：M47 迁移整理稿  
适用范围：新项目 `frontend/`，React + TypeScript + Vite 前端  
来源：
- 旧 `design-system/new-ui-spec.md`
- 旧 `design-system/报告核对工具/MASTER.md`
- 旧 `docs/ui-design-trends-research.md`
- 新 `docs/rewrite-architecture.md`
- 新 `frontend/src/shared/styles/design-tokens.css`

本文只保留可复用的 UI 原则和组件方向，不直接复制旧设计系统。旧 `MASTER.md` 中偏浅色医疗模板、营销化页面和社交证明的内容不作为新项目主线。

## 1. 设计目标

报告核对工具是面向检验报告复核的工作型界面。UI 应优先帮助用户快速完成上传、查看进度、定位问题、复核证据和导出结果。

核心原则：

| 原则 | 要求 |
| --- | --- |
| 数据优先 | 页面层级服务于核对结果、Finding、证据、页码、差异和导出，不做营销化首页。 |
| 专业克制 | 保留深色玻璃拟态方向，但减少装饰性渐变和无信息密度的视觉块。 |
| 结构化展示 | 前端只渲染后端返回的 `TaskStatus`、`TaskResult`、`CheckResult`、`Finding`。 |
| 可追溯 | 每个问题都应能展示 check id、严重级别、位置、证据、缺失证据或 diff。 |
| 可访问 | 状态不能只靠颜色表达；需要文字、图标、焦点状态和键盘可达。 |

## 2. 设计 Token

新项目已在 `frontend/src/shared/styles/design-tokens.css` 建立基础 token。迁移旧 UI 文档时，以当前 token 为准，旧文档中的蓝紫色、浅色医疗模板和 Ant Design 主题变量不直接采用。

| Token | 当前值 | 用途 |
| --- | --- | --- |
| `--color-bg` | `#101417` | 页面背景。 |
| `--color-bg-elevated` | `rgba(20, 28, 32, 0.82)` | 玻璃面板和主要工作区。 |
| `--color-bg-soft` | `rgba(255, 255, 255, 0.045)` | 次级表面、hover、局部强调。 |
| `--color-border` | `rgba(205, 229, 226, 0.14)` | 常规分隔线。 |
| `--color-border-strong` | `rgba(205, 229, 226, 0.24)` | 选中、聚焦和重点边框。 |
| `--color-text` | `#edf7f6` | 主文字。 |
| `--color-text-secondary` | `#b7cbc8` | 次级说明。 |
| `--color-text-muted` | `#8ea5a2` | 辅助元信息。 |
| `--color-accent` | `#74d7c8` | 主操作和品牌强调。 |
| `--color-accent-strong` | `#43b9aa` | 主操作 hover 或 active。 |
| `--color-success` | `#8fd0aa` | 通过、完成。 |
| `--color-danger` | `#f19a9a` | 错误、失败、严重 Finding。 |
| `--color-warn` | `#f2c078` | 需复核、证据不足。 |
| `--color-info` | `#8fb9f0` | 信息、跳过、提示。 |
| `--radius-sm` | `6px` | 小控件。 |
| `--radius-md` | `8px` | 卡片、按钮、输入框主圆角。 |
| `--shadow-glass` | `0 16px 48px rgba(0, 0, 0, 0.3)` | 玻璃面板阴影。 |
| `--transition-fast` | `140ms ease` | hover、focus。 |
| `--transition-normal` | `220ms ease` | 展开、切换、状态变化。 |

后续若新增 token，应优先扩展 `design-tokens.css`，避免在组件中散落一次性颜色。

## 3. 版式

### 3.1 页面骨架

推荐页面结构：

| 区域 | 说明 |
| --- | --- |
| 顶部导航 | 放置产品名、模块切换、健康状态或全局操作。 |
| 工作区标题 | 显示当前模块、任务状态和关键操作，不使用大幅营销 hero。 |
| 上传或任务面板 | 报告自检为单文件上传；PTR 核对为 PTR + 报告双文件上传。 |
| 结果区 | 摘要、筛选、核对项列表、Finding 详情、证据和导出。 |

界面应保持信息密度。卡片用于单个任务、单条核对项、单个 Finding 或上传控件，不把页面分区整体做成多层嵌套卡片。

### 3.2 响应式

- 桌面端优先展示双栏或三栏：摘要/筛选、核对列表、详情证据。
- 窄屏端使用单列堆叠：摘要、筛选、列表、展开详情。
- 表格和 diff 区应允许横向滚动或转换为字段列表，不能让文本溢出按钮或卡片。
- 固定格式控件使用稳定尺寸、`min-width`、`grid-template` 或 `aspect-ratio`，避免动态内容造成布局跳动。

## 4. 组件规范

### 4.1 Button

按钮只承载明确命令，如上传、开始核对、重试、导出。工具类按钮优先使用图标加 tooltip，关键命令可使用图标加文字。

状态：

| 状态 | 表现 |
| --- | --- |
| Primary | 使用 `--color-accent`，用于当前页面唯一主操作。 |
| Secondary | 透明或软背景，边框使用 `--color-border`。 |
| Danger | 使用 `--color-danger`，仅用于删除、取消任务等风险操作。 |
| Disabled | 降低透明度，保留原因提示或可见禁用文案。 |

### 4.2 Glass Surface

玻璃表面用于上传区、任务状态、核对项和详情面板。推荐：

- 背景使用 `--color-bg-elevated` 或 `--color-bg-soft`。
- 圆角使用 `--radius-md`。
- 边框使用 `--color-border`。
- 阴影使用 `--shadow-glass`，只在主要浮层或面板使用。
- 不叠加大量渐变块、装饰性光斑或低信息密度背景。

### 4.3 Upload Zone

上传区必须清楚区分：

| 模块 | 输入 |
| --- | --- |
| 报告自身核对 | 检验报告 PDF。 |
| PTR 条款核对 | PTR PDF + 检验报告 PDF。 |

上传控件应展示文件名、大小、状态、替换入口和错误信息。前端可做文件类型和空文件提示，但不得在前端实现 C01-C11 或 PTR 业务核对。

### 4.4 Status Badge

状态必须同时包含文字和颜色。

| 后端值 | 展示建议 |
| --- | --- |
| `pending` | 等待中，info。 |
| `processing` | 处理中，accent/info。 |
| `completed` | 已完成，success。 |
| `error` | 任务失败，danger。 |
| `pass` | 通过，success。 |
| `fail` | 失败，danger。 |
| `review` | 需复核，warn。 |
| `skip` | 跳过，info。 |
| `system_error` | 系统错误，danger。 |

### 4.5 Result Row

核对项和 Finding 列表应支持扫描式阅读：

- 左侧显示 `check_id` 或 Finding code。
- 中间显示核对名称、摘要、页码或位置。
- 右侧显示状态、严重级别和展开入口。
- 展开后展示证据、缺失证据、expected/actual、diff fragments 和 metadata 中的可读字段。

### 4.6 Diff

diff 只展示后端返回的 `diff_fragments`，不在前端重新计算业务差异。

推荐视觉：

| kind | 展示 |
| --- | --- |
| `equal` | 默认文本。 |
| `insert` | 信息色或成功色低透明背景。 |
| `delete` | 错误色低透明背景。 |
| `replace` | 警告色低透明背景。 |

### 4.7 Export

导出按钮按后端格式展示：`json`、`pdf`、`xlsx`。导出入口连接 `GET /api/tasks/{task_id}/export?format=json|pdf|xlsx`。

## 5. 动效

当前项目以 CSS transition 为主：

- `140ms`：hover、focus、图标状态。
- `220ms`：面板展开、筛选切换、列表状态变化。
- 复杂页面切换若引入 Framer Motion，应集中管理参数，不在组件中散落随机动画。
- 必须支持 `prefers-reduced-motion`，减少非必要动画。

动效服务于状态反馈，不能延迟用户读取核对结果。

## 6. 无障碍

- 所有可点击图标必须有可访问名称。
- 状态不能只靠颜色，必须有文字或图标。
- 上传、导出、筛选、展开详情必须键盘可达。
- 错误信息应靠近触发控件展示。
- 表格或列表中的长文本允许换行或展开，不能被截断到失去证据意义。

## 7. 前端实现边界

前端允许做：

- 上传文件、轮询任务、展示任务进度。
- 筛选、排序、分组、展开、折叠。
- 渲染 Finding、证据、diff、页码、字段名和导出入口。

前端不得做：

- 实现 C01-C11 判断。
- 实现 PTR 条款正文或表格参数比对。
- 根据旧临时 dict 自行推导最终 pass/fail。
- 依赖旧 Electron、`src/renderer` 或旧 router 路径。
- 把旧 Ant Design 示例当作新项目实现契约。

## 8. 验收清单

新增或修改前端 UI 时至少检查：

- 是否使用集中 token，而不是组件内散落硬编码颜色。
- 是否对齐 `TaskStatus`、`TaskResult`、`CheckResult`、`Finding` 类型。
- 是否在桌面和移动宽度下无文本重叠、按钮溢出或卡片嵌套过深。
- 是否保留证据和差异的结构化展示。
- 是否没有把业务规则写进组件。
- 若改动前端代码，运行 `cd frontend && npm run build`。
