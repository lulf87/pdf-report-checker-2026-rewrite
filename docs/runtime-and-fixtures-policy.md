# Runtime And Fixtures Policy

状态：M51 迁移整理稿  
旧项目根目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13`  
新项目根目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3`

本文明确运行时目录和测试素材的归属，避免把 `uploads`、`temp`、`logs` 当作源码资产，也避免继续依赖用户机器上的旧 `素材/` 目录。

## 1. 读取范围

M51 只读检查了旧项目以下路径：

| 旧路径 | 当前内容 | 处理结论 |
| --- | --- | --- |
| `.gitignore` | 忽略 `.DS_Store`、`logs/`、`output/`、`uploads/`、`backend/uploads/`、依赖、构建和缓存；允许提交 `素材/expected/`。 | 迁移忽略思路，不复制旧 Electron/Python runtime 边界。 |
| `uploads/` | 仅发现 `.gitkeep`。 | 运行时目录，不迁移。 |
| `temp/` | 仅发现 `.gitkeep`。 | 运行时目录，不迁移。 |
| `python_backend/uploads/` | 仅发现 `.gitkeep`。 | 旧 Electron 后端运行时目录，不迁移。 |
| `python_backend/temp/` | 仅发现 `.gitkeep`。 | 旧 Electron 后端运行时目录，不迁移。 |
| `素材/expected/` | 5 个样本目录，每个目录含 `report_check.expected.json` 和 `ptr_compare.expected.json`；另有 `.DS_Store`。 | Golden expected 资产已托管到 `fixtures/golden/expected`；`.DS_Store` 不迁移。 |

## 2. Runtime 目录政策

以下目录和文件只能作为本地运行时、上传缓存、临时导出或调试输出，不得作为业务代码、测试输入或 Golden expected 提交：

- `uploads/`
- `**/uploads/`
- `temp/`
- `**/temp/`
- `tmp/`
- `**/tmp/`
- `logs/`
- `**/logs/`
- `output/`
- `**/output/`
- `*.log`
- `.playwright-cli/`
- `node_modules/`
- `dist/`
- `.venv/`
- `__pycache__/`

后端如果需要写入运行时文件，应通过 application 或 infrastructure 中的受控 storage adapter 管理路径。API 层不得把旧 `python_backend/main.py` 的 `./uploads`、`./temp` 同步 file_id 约定带入新主线。

## 3. Golden expected 归属

旧 `素材/expected` 中的 Golden expected 属于可复现测试资产，目标路径为：

```text
fixtures/golden/expected
```

M51 检查到新项目已存在以下受控 expected 文件，并与旧 `素材/expected` 中对应 JSON 的 SHA-256 哈希一致：

| 样本 | 文件 |
| --- | --- |
| `1539` | `ptr_compare.expected.json`, `report_check.expected.json` |
| `2795` | `ptr_compare.expected.json`, `report_check.expected.json` |
| `3940` | `ptr_compare.expected.json`, `report_check.expected.json` |
| `5780` | `ptr_compare.expected.json`, `report_check.expected.json` |
| `5782` | `ptr_compare.expected.json`, `report_check.expected.json` |

这些 JSON 是旧结果快照，不等同于新架构的最终输出契约。新测试可以用它们做 legacy snapshot inventory 和迁移回归参考，但不能为了让测试通过而静默覆盖 expected。

## 4. 不迁移内容

以下旧资产不进入新项目源码主线：

- 旧项目根 `uploads/.gitkeep` 和 `temp/.gitkeep`。
- 旧 `python_backend/uploads/.gitkeep` 和 `python_backend/temp/.gitkeep`。
- 旧 `素材/expected/.DS_Store`。
- 旧 `素材/` 下 expected 之外的原始样本、上传文件或本机路径引用。
- 旧 Electron / `python_backend` 依赖的同步上传、临时文件和结果 JSON 读取约定。

如需增加新的 Golden input fixture，应先确认该素材可提交、可脱敏、可复现，并记录来源、hash、用途和更新原因。

## 5. `.gitignore` 规则

新项目 `.gitignore` 已按以下类别整理：

- macOS 元数据。
- Python cache、本地虚拟环境和覆盖率输出。
- Node/Vite 依赖和构建产物。
- 本地 `.env` 文件。
- runtime artifacts：`uploads`、`temp`、`tmp`、`logs`、`output`、`*.log`。
- 显式保留 `fixtures/golden/expected/**` 作为受控测试资产。

该规则的意图是：runtime 默认不可提交，Golden expected 可提交但必须人工审查。

## 6. 更新 Golden 的约束

更新 `fixtures/golden/expected` 必须满足：

- 不能从 live OCR、live LLM 或未固定外部服务结果自动生成稳定 expected。
- 不能用更新 expected 掩盖规则失败。
- 修改 expected 前必须说明业务原因、旧行为、新行为和差异范围。
- 不修改原始旧项目 `素材/expected`。
- 不引入 `.DS_Store`、临时日志、上传样本、PDF 渲染缓存或本机绝对路径。

如果旧 expected 与新 `Finding` 契约不一致，应记录迁移差异或补充转换测试，不自行把旧结构当成新 API 契约。

## 7. 待确认

- 新项目必读清单中的 `docs/open-questions.md` 当前不存在；M51 未创建该文件。
- 新项目目录当前没有 `.git` 元数据，`git status --ignored --short` 无法在本地完成；若后续以 Git 仓库形式打开，应重新运行该检查。
- `fixtures/golden/expected` 当前只有 expected JSON，没有原始 PDF 或固定 OCR/VLM 输入。是否补充最小可提交 input fixture，需要单独确认。
- 旧 `素材/expected` 的 legacy snapshot 是否长期保留原格式，还是后续转换成新 `Finding` 契约快照，需要业务和测试策略确认。

## 8. 验证命令

文档和 fixture 级检查：

```bash
find fixtures/golden/expected -maxdepth 2 -type f | sort
find fixtures/golden/expected -name '.DS_Store' -print
find /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/expected -type f ! -name '.DS_Store' -print0 | sort -z | xargs -0 shasum -a 256
find fixtures/golden/expected -type f ! -name '.DS_Store' -print0 | sort -z | xargs -0 shasum -a 256
```

Git 仓库检查：

```bash
git status --ignored --short
```
