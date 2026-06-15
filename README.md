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
