# Legacy Electron Inventory

状态：M49 迁移整理稿  
旧项目根目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13`  
新项目根目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3`

本文隔离旧 Electron 架构。旧 `src/main`、`src/renderer`、根 `package.json` 和 Mac 打包说明只作为历史资产识别，不进入新 Web 主线。

## 1. 重要差异记录

新项目早期 `docs/legacy-inventory.md` 曾记录根 `package.json`、`src/main/`、`src/renderer/` 和 `python_backend/` “未检出”。M49 复查当前旧项目路径时，这些文件实际存在：

- `src/main/main.js`
- `src/main/preload.js`
- `src/renderer/`
- `package.json`
- `python_backend/`
- `打包说明.md`

因此，后续不得继续按“未检出”处理这些路径；应按本文件记录的结论处理：已识别，已隔离，废弃为新主线入口。

## 2. 旧 Electron 文件清单

| 路径 | 作用 | M49 处理 |
| --- | --- | --- |
| `src/main/main.js` | Electron 主进程；创建窗口；生产模式启动 Python 后端；提供 IPC；开发模式加载 Vite dev server。 | 废弃为主线；仅记录启动和耦合关系。 |
| `src/main/preload.js` | 通过 `contextBridge` 暴露 `electronAPI`。 | 废弃；新 Web 前端不依赖 Electron preload。 |
| `src/renderer/package.json` | 旧 renderer 的 React/Vite/Ant Design/Tailwind/Framer Motion 依赖。 | 不迁入；已由新 `frontend/package.json` 取代。 |
| `src/renderer/src/App-new.jsx` | 当前旧 renderer 入口使用的 App；连接旧 `/health`、`/api/upload`、`/api/check/{file_id}`。 | 不迁入；信息架构已在 M47 UI 文档中吸收。 |
| `src/renderer/src/App.jsx` | 旧 App 变体；同样连接旧 API。 | 不迁入。 |
| `src/renderer/src/components/upload/UploadZone.jsx` | 旧上传组件；支持 PDF/DOCX，50MB 前端限制，调用 `/api/upload`。 | 不迁入；上传交互思路可参考，新 API 已改为 `/api/tasks/*`。 |
| `src/renderer/src/components/result/` | 旧 C01-C11 结果组件、结果汇总、详情面板、导出按钮。 | 不直接迁入；只保留结果信息架构参考。 |
| `src/renderer/src/components/result-old/` | 更旧的一套结果组件。 | 废弃。 |
| `src/renderer/src/components/ui/` | 旧 UI 组件库。 | 不迁入；新前端已有 `frontend/src/shared/ui`。 |
| `src/renderer/src/components/ui-old/` | 更旧 UI 组件，含粒子背景和 Framer Motion 版本。 | 废弃。 |
| `package.json` | 旧根 Electron + Python 桌面应用脚本和 electron-builder 配置。 | 废弃为主线；已在 M48 脚本文档中记录。 |
| `打包说明.md` | PyInstaller + electron-builder / Platypus 的 Mac 打包说明。 | 废弃为当前发布方案；未来桌面壳需重新设计。 |

## 3. 旧启动链路

### 3.1 开发模式

根 `package.json` 的 `dev` 命令使用 `concurrently` 同时启动三段：

```text
npm run dev:python
npm run dev:renderer
npm run dev:electron
```

实际链路：

1. `dev:python` 进入 `python_backend`，运行 `uvicorn main:app --reload --port 8000`。
2. `dev:renderer` 进入 `src/renderer`，运行 Vite dev server。
3. `dev:electron` 使用 `wait-on tcp:8000 tcp:5173` 等待后端和 renderer，再运行 `electron .`。
4. `src/main/main.js` 在开发模式加载 `http://localhost:5173`，并打开 DevTools。

这条链路不进入新主线。新项目开发脚本已改为 `scripts/dev.sh`，直接启动 `backend/app/main.py` 和 `frontend/`，不启动 Electron。

### 3.2 生产模式

`src/main/main.js` 在非开发模式下：

1. 将 Python 后端路径设为 `process.resourcesPath/python_backend`。
2. 使用 `python` 或 `python3` 执行 `python -m uvicorn main:app --host 127.0.0.1 --port 8000`。
3. 加载 `src/renderer/dist/index.html`。
4. 应用退出时尝试停止 Python 子进程。

根 `package.json` 的 electron-builder 配置将 `python_backend/dist/**/*` 打入资源目录，并把它复制为运行时 `python_backend`。

这意味着旧桌面应用把后端生命周期交给 Electron 主进程管理。新架构不采用这种边界。

### 3.3 打包模式

旧 `打包说明.md` 建议：

1. `npm run build:react`
2. 进入 `python_backend`，用 PyInstaller 打包 `main.py`
3. `npm run build:electron`
4. 或使用 Platypus 包装启动脚本

该打包方式依赖旧 `python_backend`、Electron 和本机桌面应用假设，不作为新项目发布路径。

## 4. 与 python_backend 的耦合

旧 Electron 与 `python_backend` 是强耦合关系：

| 耦合点 | 证据 | 新项目处理 |
| --- | --- | --- |
| 后端路径 | `src/main/main.js` 开发模式使用 `../../python_backend`，生产模式使用 `process.resourcesPath/python_backend`。 | 废弃；新后端位于 `backend/`。 |
| 后端启动 | 主进程生产模式 spawn `python -m uvicorn main:app --host 127.0.0.1 --port 8000`。 | 废弃；新启动由 `scripts/dev.sh` 或部署系统管理。 |
| 健康检查 | 主进程 IPC `get-backend-status` 请求 `http://127.0.0.1:8000/health`。 | 废弃；新健康检查是 `/api/health`。 |
| API 路径 | renderer 调用 `/api/upload`、`/api/check/{file_id}`、`/api/export/{file_id}`。 | 废弃；新主线为 `/api/tasks/*`。 |
| 文件类型 | 旧上传支持 PDF 和 DOCX。 | 新报告/PTR 主线按当前需求以 PDF 为主；DOCX 不在 M49 中恢复。 |
| 文件目录 | `python_backend/main.py` 使用相对 `./uploads`、`./temp`。 | 新项目禁止把 uploads/temp 作为源码主线。 |
| 结果结构 | renderer 读取 `home_third_comparison`、`third_page_extended_check`、`sample_table_check`、`errors` 等旧临时结构。 | 废弃；新前端消费 `TaskResult`、`CheckResult`、`Finding`。 |
| 依赖 | `python_backend/requirements.txt` 包含 PaddleOCR、PyMuPDF、python-docx、ReportLab、openpyxl、LLM SDK。 | 可按后端分层任务迁移能力，不通过 Electron 入口迁移。 |

## 5. 旧 renderer 资产判断

旧 renderer 中有三类资产：

| 类型 | 示例 | 处理 |
| --- | --- | --- |
| 可参考的信息架构 | 上传区、进度、C01-C11 分组、结果详情、导出按钮。 | 已在 `docs/ui/check-result-ui-design.md` 和新前端结果组件方向中吸收。 |
| 不应迁移的业务判断 | `CheckResult.jsx` 在前端根据旧结果字段计算 C01-C11 pass/fail/errorCount。 | 废弃；新前端不得实现 C01-C11 判断。 |
| 旧实现绑定 | Ant Design 主题、旧 `/api/*` 路径、DOCX 上传、旧 result dict、Electron preload。 | 不进入新主线。 |

旧 renderer 的 UI 组件可以作为视觉和交互参考，但不能原样复制到 `frontend/`。若确需参考，应逐项改写为：

- TypeScript 类型。
- 新 `TaskStatus` / `TaskResult` / `CheckResult` / `Finding` 契约。
- 新 `frontend/src/shared/ui` 组件风格。
- 后端返回结构驱动，而非前端自行推导核对结论。

## 6. 废弃清单

以下内容明确不进入新主线：

- 根 Electron `package.json` 的 `dev:electron`、`build:electron`、`start`。
- `src/main/main.js` 中的 BrowserWindow、preload、IPC、Python 子进程管理。
- `src/main/preload.js` 暴露的 `window.electronAPI`。
- `src/renderer` 作为新前端源码入口。
- `python_backend` 作为 Electron 内嵌服务。
- `/health`、`/api/upload`、`/api/check/{file_id}`、`/api/export/{file_id}` 作为新主线接口。
- PyInstaller + electron-builder + Platypus 的旧 Mac app 打包路径。
- 前端根据旧 result dict 自行计算 C01-C11 状态。

## 7. 可保留但需重写的经验

| 旧经验 | 新归属 |
| --- | --- |
| 桌面窗口前台显示、文件选择 | 仅作为未来 desktop shell 参考，不进入当前 Web 主线。 |
| 上传拖拽和文件卡片交互 | `frontend/src/shared/ui/FileUpload` 或页面组件，按新 API 重写。 |
| C01-C11 分组展示 | 前端结果展示层，数据来自后端 `CheckResult`。 |
| 导出按钮和下载行为 | 前端调用 `GET /api/tasks/{task_id}/export?format=json\|pdf\|xlsx`。 |
| PDF/OCR/DOCX/导出经验 | 若仍有价值，分别进入 `infrastructure/pdf`、`infrastructure/ocr`、`infrastructure/export`，不经过 Electron。 |

## 8. 未来 desktop shell 规划

如未来确实需要桌面版，应作为独立“desktop shell”任务，不复活旧 Electron 主线。建议边界：

- desktop shell 只包装 Web UI，不实现 C01-C11、PTR、PDF/OCR/LLM、导出业务。
- 后端仍由 `backend/` 提供，并通过标准 HTTP API 访问。
- 不在 Electron 主进程中拼接业务结果、启动历史 `python_backend` 或读取 uploads/temp。
- 文件选择可作为 shell 能力，但上传仍走新 `/api/tasks/*`。
- 打包、签名、自动更新、安全策略和日志目录需单独设计。

## 9. 待确认

- `docs/open-questions.md` 当前不存在；M49 未创建该文件。
- 新项目是否需要桌面壳，尚未确认。
- DOCX 是否恢复为输入格式，尚未确认；当前报告/PTR 主线以 PDF 为主。
- `docs/legacy-inventory.md` 中 Electron 路径“未检出”的历史记录是否需要在后续任务统一修订。

## 10. 验证建议

本任务只新增文档，不修改代码和 README，因此不需要构建。文档级检查：

```bash
test -f docs/legacy-electron-inventory.md
rg "Electron|src/main|src/renderer|python_backend|/api/tasks|/api/upload|/api/check|desktop shell|废弃" docs/legacy-electron-inventory.md
```
