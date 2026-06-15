# Legacy Python Backend Inventory

状态：M50 迁移整理稿  
旧项目根目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13`  
新项目根目录：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3`

本文隔离旧 `python_backend/`。该目录是旧 Electron 桌面链路使用的独立 FastAPI 后端，不作为新项目主线入口，也不整体复制到新 `backend/`。其中可追溯的业务经验只能按新架构边界重写到 `application`、`domain`、`rules` 或 `infrastructure`。

## 1. 重要差异记录

新项目早期 `docs/legacy-inventory.md` 曾记录 `python_backend/` “未检出”。M49/M50 复查当前旧项目路径时，该目录实际存在，并且包含独立 API、模型、服务、测试和运行时目录：

- `python_backend/main.py`
- `python_backend/config.py`
- `python_backend/models/schemas.py`
- `python_backend/services/`
- `python_backend/tests/test_inspection_item_checker.py`
- `python_backend/test_third_page_checker.py`
- `python_backend/uploads/.gitkeep`
- `python_backend/temp/.gitkeep`

因此，后续不得继续按“无资产”处理该路径；应按本文件记录的结论处理：已识别，已隔离，废弃为新主线入口，少量规则经验和测试样例可作为后续迁移依据。

## 2. 总体判断

`python_backend/` 是旧桌面应用的后端服务，主要职责混在同一条链路中：

- HTTP API：上传、解析、OCR、核对、结果读取、导出。
- 文件存储：相对路径 `./uploads`、`./temp`。
- PDF/DOCX 解析：PyMuPDF、LibreOffice、python-docx、ReportLab。
- OCR 和 VLM fallback：PaddleOCR、OpenRouter/Anthropic/OpenAI 视觉模型。
- 报告自身核对：首页/第三页、样品描述、照片/标签、检验项目、页码。
- 导出：旧 `CheckResult` dict 到 PDF/XLSX/JSON。

这些职责与新架构冲突：router 不应编排业务，parser/OCR/export 不应输出规则 verdict，规则必须统一输出 `Finding`。所以 M50 不迁入任何 Python 源码，只保留资产清单和后续迁移建议。

## 3. 文件清单

| 旧路径 | 主要内容 | 与主线关系 | M50 决策 |
| --- | --- | --- | --- |
| `python_backend/main.py` | 独立 FastAPI app；`/health`、`/api/upload`、`/api/parse/{file_id}`、`/api/ocr/*`、`/api/check/{file_id}`、`/api/result/{file_id}`、`/api/export/{file_id}`；全局初始化 parser/OCR/checker；写 `uploads` 和 `temp`。 | 被旧 `backend/app/main.py`、`backend/app/routers/report_check.py` 和新项目 `/api/tasks/*` 取代。 | 废弃为入口；不迁移旧 API。 |
| `python_backend/config.py` | `UPLOAD_DIR`、`TEMP_DIR`、OpenRouter/Anthropic/OpenAI/Azure keys、LLM/VLM 开关、Gemini/OpenRouter 默认模型、fallback 阈值。 | 旧 `backend/app/config.py` 已有另一套后端配置；新项目应由 `backend/app/core/config.py` 管理。 | 不复制；仅记录可选 LLM/VLM 配置经验。 |
| `python_backend/models/schemas.py` | 旧 Pydantic 模型：`HealthResponse`、`UploadResponse`、`PageInfo`、`TableData`、`OCRResult`、`FieldComparison`、`ComponentCheck`、`ErrorItem`、`InspectionItemCheckResult`、`CheckResult` 等。 | 与新项目统一 `Finding`、`CheckResult`、`TaskStatus` 契约冲突。 | 废弃旧结果结构；字段含义可作为模型迁移参考。 |
| `python_backend/requirements.txt` | FastAPI、PyMuPDF、python-docx、Pillow、OpenCV、PaddleOCR、LLM SDK、ReportLab、openpyxl。 | 依赖大多已由后端/前端分包管理；DOCX 是明显差异。 | 不迁移为包规格；若恢复 DOCX 单独设计依赖。 |
| `python_backend/services/docx_parser.py` | DOCX 转 PDF；优先 `soffice --headless --convert-to pdf`，失败后用 python-docx + ReportLab 生成简化 PDF；可提取 DOCX 文本和表格。 | 旧 `backend/app` 主线未见同等 DOCX parser；新报告/PTR 主线目前以 PDF 为主。 | 唯一明显独特能力；标为后续产品确认，不直接恢复。 |
| `python_backend/services/pdf_parser.py` | PyMuPDF 文本、页眉、表格、图片、首页字段、页面转图片。 | 旧 `backend/app/services/pdf_parser.py` 更完整；新项目已有 `infrastructure/pdf/pymupdf_parser.py`。 | 重复且已被新基础设施取代。 |
| `python_backend/services/ocr_service.py` | PaddleOCR lazy init、图片预处理、标签区域裁剪、字段正则、UDI/GS1 过滤、日期 OCR 纠错、VLM fallback、标签字段比对。 | 旧 `backend/app/services/ocr_service.py` 和新 `infrastructure/ocr/*` 已拆分 caption、label field、OCR adapter。 | 不迁移大类；个别字段正则和 OCR 纠错可作为后续 OCR 增强参考。 |
| `python_backend/services/report_checker.py` | 单体报告核对流程：首页/第三页字段、样品描述表、照片页、中文标签、部件字段、第三页扩展字段、页码汇总、保存结果。 | 旧 `backend/app/services/report_checker.py` 已有主线版本；新项目已按 C01-C11 拆到 `rules/report/*`。 | 废弃单体 service；仅保留 caption/样品表解析经验参考。 |
| `python_backend/services/third_page_checker.py` | 第三页扩展字段：型号规格、生产日期、产品编号/批号；`见"样品描述"栏` 口径；标签匹配；日期格式检测。 | 对应旧主线 `backend/app/services/third_page_checker.py`，新项目对应 C01-C03/C02/C03 规则。 | 重复；测试样例可抽取补充新 C02/C03。 |
| `python_backend/services/inspection_item_checker.py` | 检验项目表格检测、跨页续表、单项结论、非空字段、序号连续、续表标记；含旧错误码枚举。 | 对应旧主线 `backend/app/services/inspection_item_checker.py`，新项目对应 C07-C10 规则和 `inspection_table_extractor`。 | 重复；边界测试价值高，需与新 C07-C10 测试逐项比对。 |
| `python_backend/services/page_number_checker.py` | 从第三页开始抽取“第 X 页 共 Y 页”等页码格式，检查缺页、重复、总页数和连续性。 | 对应旧主线 `backend/app/services/page_number_checker.py`，新项目对应 C11。 | 重复；页码格式样例可作为 C11 回归补充。 |
| `python_backend/services/report_export_service.py` | ReportLab PDF 和 openpyxl Excel 导出；包含中文字体查找/注册；按旧 result dict 输出。 | 旧 `backend/app/services/report_export_service.py` 和新 `infrastructure/export/*` 已取代。 | 不迁移旧 dict 导出；中文字体 fallback 可供 PDF exporter 加固。 |
| `python_backend/services/llm_service.py` | OpenRouter/Anthropic/OpenAI 文本 LLM，用于表格重建、OCR 纠错、结构化字段抽取。 | 旧 `backend/app/services/llm_service.py` 已有更明确 provider/mode；新项目在 `infrastructure/llm/`。 | 不迁移为规则裁决；仅作为 infrastructure 辅助能力参考。 |
| `python_backend/services/llm_vision_service.py` | 视觉模型 OCR；图片转 base64；OpenRouter/Anthropic/OpenAI 调用；标签字段 JSON 归一。 | 旧 `backend/app/services/llm_vision_service.py` 和新 `infrastructure/llm/vision_service.py` 已取代。 | 不迁移为主判定；可作 VLM fallback prompt 参考。 |
| `python_backend/utils/comparison_logger.py` | 比对步骤日志、输入输出和耗时记录。 | 新项目应使用统一 logging/diagnostics，不应绑旧 result dict。 | 不迁移；可参考“比对步骤可追溯”思想。 |
| `python_backend/tests/test_inspection_item_checker.py` | 旧检验项目表格测试，覆盖表格检测、列索引、续表识别、单项结论、非空字段、跨页、序号连续和续表位置。 | 新项目已有 C07-C10 与表格抽取测试，但需确认是否覆盖全部旧边界。 | 作为后续回归样例池，不直接复制旧测试结构。 |
| `python_backend/test_third_page_checker.py` | 第三页字段、`见样品描述`、字母数字检测、日期格式、标签字段映射、值比较、全流程测试。 | 新项目已有 C02/C03 与字段抽取测试，但需确认特殊格式覆盖。 | 作为后续 C02/C03 回归样例池。 |
| `python_backend/uploads/.gitkeep`、`python_backend/temp/.gitkeep` | 旧运行时目录占位。 | 新项目禁止把 `uploads`、`temp` 作为源码主线资产。 | 废弃；不迁移。 |

## 4. 旧 API 清单

旧 `python_backend/main.py` 提供同步 file_id 风格 API：

| 旧接口 | 职责 | 新项目处理 |
| --- | --- | --- |
| `GET /health` | 旧桌面后端健康检查。 | 废弃；新健康检查是 `/api/health`。 |
| `POST /api/upload` | 上传 PDF 或 DOCX，保存到 `./uploads/{file_id}.pdf|docx`。 | 废弃；新主线使用任务 API，不恢复旧 file_id contract。 |
| `POST /api/parse/{file_id}` | 解析 PDF/DOCX 并返回 pages/table preview。 | 不作为主线 API；如需诊断工具，另开 developer-only API 任务。 |
| `POST /api/ocr/{file_id}/page/{page_num}` | 对某页 OCR。 | 不作为主线 API；OCR 属于 infrastructure，结果通过任务证据暴露。 |
| `POST /api/ocr/{file_id}/image` | 对指定图片路径 OCR。 | 废弃；不能让 HTTP 直接读取任意路径。 |
| `POST /api/check/{file_id}` | 执行报告核对，可临时开启 LLM；返回旧 `CheckResult`。 | 废弃；新主线由 application usecase 编排并输出统一 `Finding`。 |
| `GET /api/result/{file_id}` | 从 `./temp/{file_id}_result.json` 读取结果。 | 废弃；新主线通过 task service 管理状态和结果。 |
| `GET /api/export/{file_id}` | 基于旧 result dict 导出 JSON/PDF/XLSX。 | 废弃；新主线使用 `/api/tasks/{task_id}/export?format=...`。 |

旧 API 与 Electron 强耦合，也依赖本地相对 `uploads/temp`。这些接口不进入新 `api` 层。

## 5. 与旧 backend 主线对比

旧项目同时存在 `python_backend/` 和 `backend/app/`。对比结论如下：

| 功能 | `python_backend/` | 旧 `backend/app/` 主线 | 新项目处理 |
| --- | --- | --- | --- |
| API 入口 | 单文件 `main.py`，同步 file_id API，支持 PDF/DOCX。 | `app/main.py` include `ptr_compare`、`report_check` routers；`/api/report/upload`、progress、result、export。 | 新项目已改为 `api/routes_*` + application usecase + task service；旧 API 均废弃。 |
| PDF 解析 | `services/pdf_parser.py` 单类，提取文本、表格、图片、首页字段。 | `backend/app/services/pdf_parser.py` 更完整，含 `parse_pdf`、`is_scanned_pdf`。 | 新项目放在 `infrastructure/pdf/pymupdf_parser.py`。 |
| OCR | `services/ocr_service.py` 混合 OCR、字段抽取、纠错、VLM fallback、比对。 | `backend/app/services/ocr_service.py`、`ocr_parser.py` 拆分更多能力。 | 新项目拆到 `infrastructure/ocr/` 和 `infrastructure/llm/`；规则不依赖 OCR service verdict。 |
| 首页/第三页核对 | `report_checker.py` + `third_page_checker.py` 混合流程。 | `third_page_checker.py` 明确 C01-C03 结果模型。 | 新项目已拆 C01-C03 独立规则。 |
| 样品描述/照片/标签 | `report_checker.py` 中处理 caption、component、field comparisons。 | `report_checker.py` 有 C04-C06 相关模型。 | 新项目拆 C04-C06 独立规则和 report extractors。 |
| 检验项目 | `inspection_item_checker.py` 处理 C07-C10 候选逻辑，但输出旧 `ErrorItem`。 | `backend/app/services/inspection_item_checker.py` 有 C07-C10 结果模型。 | 新项目已有 C07-C10 rules；旧测试需做覆盖对账。 |
| 页码 | `page_number_checker.py` 处理第三页之后连续性。 | `backend/app/services/page_number_checker.py` 有 C11 结果模型。 | 新项目已有 C11 rule。 |
| 导出 | `report_export_service.py` 面向旧 `CheckResult` dict。 | `backend/app/services/report_export_service.py` 支持报告和 PTR 导出。 | 新项目已有 `infrastructure/export/json_exporter.py`、`pdf_exporter.py`、`excel_exporter.py`。 |
| LLM/VLM | 作为 OCR/字段增强和表格重建工具，存在可能替代确定性判断的风险。 | 旧主线已有 provider/mode 更清楚的服务。 | 新项目仅允许作为 infrastructure 辅助能力，不替代规则。 |
| DOCX | 有 `docx_parser.py`，支持 LibreOffice 和 python fallback。 | 未见同等 DOCX parser。 | 可能遗漏能力；需产品确认后另开任务。 |

## 6. 可能遗漏的业务资产

以下内容没有在 M50 迁入，仅记录为后续候选：

| 候选资产 | 来源 | 建议归属 | 需要确认 |
| --- | --- | --- | --- |
| DOCX 输入支持 | `python_backend/services/docx_parser.py`、旧 `/api/upload` 支持 `.docx`。 | `infrastructure/document/` 或转换 adapter；API 仍走 task usecase。 | 新产品是否仍支持 DOCX；LibreOffice 是否作为部署依赖。 |
| 手动 parse/OCR 诊断接口 | 旧 `/api/parse/{file_id}`、`/api/ocr/*`。 | 只可作为 developer diagnostics，不进入业务主 API。 | 是否需要给运维/开发调试。 |
| OCR 日期纠错和 UDI/GS1 过滤 | `ocr_service.py` 中 `_filter_udis_from_result`、`_normalize_date_value`、`_correct_date_ocr_confusion` 等。 | `infrastructure/ocr/label_field_extractor.py` 或 OCR normalizer。 | 当前新 OCR 测试是否覆盖真实标签 OCR 噪声。 |
| 第三页日期格式样例 | `test_third_page_checker.py`。 | C03 tests。 | 新 C03 口径是否继续要求“格式和值一致性”。 |
| 检验项目跨页复杂场景 | `tests/test_inspection_item_checker.py` 中同序号跨多页、续表位置、空原始序号、`——` 与 `/` 的测试。 | C07-C10 tests 与 `inspection_table_extractor` tests。 | 新测试是否已覆盖旧边界；未覆盖则补测试，不搬旧结构。 |
| PDF 导出中文字体 fallback | `report_export_service.py` 的字体查找和注册。 | `infrastructure/export/pdf_exporter.py`。 | 当前导出在不同系统字体环境下是否稳定。 |
| LLM/VLM fallback 阈值 | `config.py`、`llm_service.py`、`llm_vision_service.py`。 | `infrastructure/llm/` 配置和 diagnostics。 | 是否仍需要 OpenRouter/Gemini 默认链路和 fallback 阈值。 |

## 7. 明确废弃内容

以下内容不进入新主线：

- `python_backend` 作为 Electron 内嵌后端。
- `python_backend/main.py` 的旧 FastAPI app。
- 旧 `/health`、`/api/upload`、`/api/parse/{file_id}`、`/api/ocr/*`、`/api/check/{file_id}`、`/api/result/{file_id}`、`/api/export/{file_id}` 接口。
- 旧 `UploadResponse`、`ErrorItem`、`FieldComparison`、`ComponentCheck`、宽松 `CheckResult` 作为新跨层契约。
- 相对路径 `./uploads`、`./temp` 作为源码或业务状态目录。
- 在 API 中临时修改全局 `ENABLE_LLM_COMPARISON` 的方式。
- HTTP 传入任意 `image_path` 并让后端直接读取的方式。
- LLM/VLM 直接替代 C01-C11 或 PTR 确定性规则输出 verdict。
- DOCX 链路在未确认前作为默认输入格式。

## 8. 与新架构对齐

后续若从 `python_backend/` 抽取资产，必须遵守：

- API 层只处理 HTTP 输入输出，不恢复旧同步 file_id 编排。
- application 层负责任务编排和跨基础设施调用。
- domain 层定义 `ReportDocument`、`InspectionItem`、`Finding` 等稳定契约。
- rules 层实现 C01-C11，每条规则独立测试并输出统一 `Finding`。
- infrastructure 层承接 PDF、OCR、DOCX 转换、LLM/VLM、导出。
- 测试迁移时优先抽行为样例，不复制旧 import 路径、旧大 service 或旧 result dict。

## 9. 待确认

- 新项目必读清单中的 `docs/open-questions.md` 当前不存在；M50 未创建该文件。
- `docs/legacy-inventory.md` 中 `python_backend/` “未检出”的历史记录是否需要后续统一修订。
- 是否恢复 DOCX 输入；如恢复，是否接受 LibreOffice 作为本地/部署依赖。
- 是否需要开发者专用 parse/OCR 诊断接口。
- `python_backend/tests/test_inspection_item_checker.py` 与 `python_backend/test_third_page_checker.py` 中哪些边界尚未被新项目 C02/C03/C07-C11 测试覆盖。
- 是否需要把旧 OCR 日期纠错、UDI/GS1 过滤、PDF 中文字体 fallback 转为明确后续任务。

## 10. 验证建议

本任务只新增文档，不修改后端或前端代码，因此不需要运行 pytest 或前端 build。文档级检查：

```bash
test -f docs/legacy-python-backend-inventory.md
rg "python_backend|backend/app|重复|废弃|遗漏|DOCX|/api/tasks|/api/upload|/api/check|Finding|open-questions|uploads|temp" docs/legacy-python-backend-inventory.md
rg "inspection_item_checker|third_page_checker|page_number_checker|report_checker|report_export_service|llm_service|llm_vision_service|pdf_parser|ocr_service|docx_parser" docs/legacy-python-backend-inventory.md
```
