# 报告核对工具重写项目

本仓库用于医疗器械检验报告自动核对工具的新架构重写。新主线是纯 Web 应用：后端 FastAPI，前端 React + TypeScript + Vite。旧 Electron、历史 `python_backend/`、`src/main/`、`src/renderer/` 和旧根 `package.json` 启动链路只作为 legacy 资产，不进入新主线。

## 项目结构

```text
backend/
  app/
    api/
    application/
    domain/
    infrastructure/
    rules/
  tests/

frontend/
  src/
    app/
    entities/
    features/
    shared/

scripts/
  dev.sh
  test.sh
  build.sh
```

## 环境准备

后端需要 Python 3.11+：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

前端需要 Node.js 和 npm：

```bash
cd frontend
npm install
```

脚本会优先使用 `backend/.venv/bin/python`。如需指定 Python，可设置：

```bash
PYTHON_BIN=/path/to/python bash scripts/test.sh
```

## 统一脚本

启动开发环境：

```bash
bash scripts/dev.sh
```

默认地址：

- 后端：`http://127.0.0.1:8000`
- 前端：`http://127.0.0.1:5173`

可用环境变量调整端口和监听地址：

```bash
BACKEND_PORT=8010 FRONTEND_PORT=5174 bash scripts/dev.sh
```

Codex CLI 审核使用产品自己的显式运行配置，不继承个人
`~/.codex/config.toml` 中的模型或推理强度。默认配置为：

- 平衡：`gpt-5.6-terra` + `medium`，超时 600 秒，单批 3 项，并发 2。
- 快速：`gpt-5.6-luna` + `low`，超时 360 秒，单批 5 项，并发 2。
- 深度：`gpt-5.6-sol` + `high`，超时 900 秒，单批 2 项，并发 1。
- 自定义：可手动选择模型与 `low/medium/high/xhigh/max`；`xhigh/max` 建议只用于少量疑难单项。

服务端默认值和网页候选列表也可以通过环境变量调整：

```bash
CODEX_AUDIT_MODEL=gpt-5.6-terra \
CODEX_AUDIT_MODEL_OPTIONS=gpt-5.6-terra,gpt-5.6-luna,gpt-5.6-sol \
CODEX_AUDIT_REASONING_EFFORT=medium \
CODEX_AUDIT_REASONING_EFFORT_OPTIONS=low,medium,high,xhigh,max \
bash scripts/dev.sh
```

- 后端调用固定包含 `--ignore-user-config`、`--model` 和显式 `model_reasoning_effort`。
- `CODEX_AUDIT_MODEL_OPTIONS` 是网页高级审核设置中的预置模型列表。
- PTR 条款核对和报告自身核对都可以选择运行方案，任务级设置会覆盖服务端默认值。
- 模型、推理强度和运行配置版本共同参与审核缓存键，不会跨配置复用旧结果。

运行测试和前端构建：

```bash
bash scripts/test.sh
```

构建检查：

```bash
bash scripts/build.sh
```

`scripts/dev.sh` 不会自动杀掉占用端口的进程，也不会自动安装依赖。若端口占用或依赖缺失，请按终端提示处理。

## 后端

当前后端提供：

- `GET /api/health`
- `GET /api/runtime-config/codex`
- `POST /api/tasks/report-check`
- `POST /api/tasks/ptr-compare`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/result`
- `GET /api/tasks/{task_id}/export?format=json|pdf|xlsx`

单独启动后端：

```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

单独运行后端测试：

```bash
cd backend
python -m pytest tests/ -v
```

## 前端

前端只展示后端返回的 `TaskStatus`、`TaskResult`、`CheckResult` 和 `Finding`，不实现 C01-C11 或 PTR 业务判断。

单独启动前端：

```bash
cd frontend
npm run dev
```

单独构建前端：

```bash
cd frontend
npm run build
```

## 迁移约束

- 旧项目资产只作为业务依据，不直接复制旧 router 或 service 大文件。
- 不引入 Electron 作为主线。
- 不修改 raw / original / source_data 等原始输入目录。
- 前端只展示后端结果，不实现 C01-C11 或 PTR 判断。
- 所有规则输出统一 `Finding`。
- 每条规则需要独立模型输入、独立 pytest 和可追溯证据。
