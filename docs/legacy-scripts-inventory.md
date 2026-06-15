# Legacy Scripts Inventory

状态：M48 迁移整理稿  
旧项目根目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13`  
新项目根目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3`

本清单整理旧启动脚本、发布脚本和根 `package.json` 的可复用思路。旧脚本没有被原样迁入；新项目只保留 Web 主线脚本：

- `scripts/dev.sh`
- `scripts/test.sh`
- `scripts/build.sh`

## 1. 迁移矩阵

| 旧文件 | 主要内容 | 新处理 | 决策 | 说明 |
| --- | --- | --- | --- | --- |
| `start.sh` | 启动后端 `backend`、前端 `frontend`，检查 `.venv` 和 `node_modules`，写入 `logs/`，杀掉 8000/5173 端口进程。 | 提取“统一启动后端 + 前端”的思路到 `scripts/dev.sh`。 | 合并 / 重写 | 新脚本不自动杀端口，不写入 `logs/`，不创建 pid 文件；端口和 host 通过环境变量配置。 |
| `scripts/auto_publish.sh` | 检查 `.env`、运行测试、前端 build、可选 Playwright、自动 git add/commit/push。 | 不迁移为主线脚本。 | 废弃为发布入口 / 仅参考 | 自动提交和推送风险较高；M48 只建立本地 dev/test/build，不实现发布自动化。 |
| `scripts/clean_env_from_history.sh` | 从 git index 和历史中移除 env 文件，可能执行 `git filter-repo`、`git filter-branch` 和 force push。 | 不迁移。 | 废弃 / 安全敏感 | 涉及重写历史和强推，必须由单独安全任务人工确认后执行。 |
| `package.json` | Electron + Python 桌面应用入口，`src/main`、`src/renderer`、`python_backend`、electron-builder。 | 不迁移根 package。 | 废弃为新主线 | 新项目无根 npm workspace；前端 package 位于 `frontend/package.json`，后端由 `backend/pyproject.toml` 管理。 |
| `package-lock.json` | 旧 Electron 根依赖锁，包括 `electron`、`electron-builder`、`wait-on`、`concurrently`。 | 不迁移。 | 废弃 | 新项目不引入根 Electron 依赖，也不新增 concurrently/wait-on。 |
| `启动工具.sh` | 硬编码本机路径 `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.2.9`，安装旧根依赖和 renderer 依赖，然后 `npm run dev`。 | 不迁移。 | 废弃 / 记录 | 路径绑定旧本机目录，且进入旧 Electron renderer 链路。 |
| `启动报告核对工具.command` | 启动 `python_backend`、`src/renderer` 和 Electron，等待端口并用 AppleScript 激活应用。 | 不迁移。 | 废弃 / 记录 | 依赖旧桌面链路和 macOS 前台激活，不符合新 Web 主线。 |
| `打包说明.md` | 使用 PyInstaller 打包 `python_backend`，再用 electron-builder 或 Platypus 打包 Mac app。 | 不迁移。 | 废弃 / 仅参考 | 新项目当前不打包 Electron 应用；后续发布方式需另开任务设计。 |

## 2. 新脚本说明

| 新脚本 | 用途 | 关键行为 |
| --- | --- | --- |
| `scripts/dev.sh` | 本地开发启动。 | 同时启动 FastAPI 和 Vite；支持 `BACKEND_HOST`、`BACKEND_PORT`、`FRONTEND_HOST`、`FRONTEND_PORT`、`PYTHON_BIN`；按 Ctrl+C 停止两个进程。 |
| `scripts/test.sh` | 本地验证。 | 运行 `cd backend && python -m pytest tests/ -v`，然后运行 `cd frontend && npm run build`。 |
| `scripts/build.sh` | 构建检查。 | 运行后端 Python 语法编译检查和前端 Vite build。 |

新脚本刻意不做：

- 不自动安装依赖。
- 不自动删除、移动或清理旧文件。
- 不自动杀掉占用端口的进程。
- 不写入 `logs/`、`temp/`、`dist/` 以外的运行资产。
- 不自动 git add/commit/push。
- 不执行 git history rewrite。
- 不启动 Electron。

## 3. 与新架构对齐

- 后端入口固定为 `backend/app/main.py` 中的 FastAPI app。
- 前端入口固定为 `frontend/package.json` 的 Vite 脚本。
- 新 API 使用 `/api/tasks/*`，不恢复旧 `/api/report-self-check/*` 或旧 Electron renderer 调用链。
- 规则、业务编排、领域模型、基础设施边界仍按 `docs/rewrite-architecture.md` 执行。
- 所有核对问题继续统一输出 `Finding`；脚本只负责启动、测试和构建。

## 4. 待确认

- 新项目必读清单中的 `docs/open-questions.md` 当前不存在，本次未创建该文件。
- 是否需要根 `package.json` 作为 npm workspace 或脚本代理仍需确认；M48 按用户要求只新增 shell 脚本。
- 是否需要发布脚本、Docker、桌面打包或签名流程，应另开发布任务设计。
- 是否需要脚本自动安装依赖或自动检测端口占用，需要结合团队开发习惯确认。

## 5. 验证

M48 要求的验证命令：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3
bash scripts/test.sh
```

若本地缺少 Python、pytest、FastAPI、Node、npm 或前端依赖，该脚本会失败并显示对应命令输出；不得把失败环境声明为已通过。
