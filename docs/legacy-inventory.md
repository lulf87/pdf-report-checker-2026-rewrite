# 旧项目资产清单

盘点来源旧项目：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13`  
输出位置当前项目：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3/docs/legacy-inventory.md`

本文只记录旧项目当前可追溯的业务资产、代码资产、测试资产和废弃项，不提出未在旧项目文件中出现的新业务需求。旧项目中未检出的文件或目录均标为 `TODO`。

## 0. 盘点范围与证据缺口

已复核的旧项目文件包括：

- `README.md`
- `docs/superpowers/specs/2026-04-23-report-self-check-codex-judge-spec.md`
- `docs/superpowers/plans/2026-04-23-report-self-check-codex-judge.md`
- `backend/pyproject.toml`
- `backend/app/main.py`
- `backend/app/routers/report_self_check.py`
- `backend/app/models/report_self_check.py`
- `backend/app/services/`
- `backend/tests/`
- `frontend/src/`
- `frontend/package.json`
- `frontend/vite.config.ts`

用户点名但旧项目当前工作树未检出的文件或目录：

| 请求读取项 | 当前旧项目状态 | 处理 |
|---|---|---|
| `REPORT_CHECKER_SPEC.md` | 未检出 | `TODO`：不能引用为事实；本文只引用 `docs/superpowers/specs/...` 中可见规格。 |
| `CLAUDE.md` | 未检出 | `TODO`：无可追溯内容。 |
| 根目录 `package.json` | 未检出 | 不能确认当前旧项目仍有 Electron 根脚本。 |
| `start.sh` | 未检出 | 不能确认当前旧项目仍有启动脚本。 |
| `python_backend/` | 未检出 | 仅作为历史路径识别，不迁入新架构。 |
| `src/main/` | 未检出 | 仅作为历史 Electron 主进程路径识别，不迁入新架构。 |
| `src/renderer/` | 未检出 | 仅作为历史 Electron renderer 路径识别，不迁入新架构。 |
| `backend/app/models/common_models.py` | 未检出 | `TODO`：不能逐模型盘点。 |
| `backend/app/models/report_models.py` | 未检出 | `TODO`：不能逐模型盘点。 |
| `backend/app/models/ptr_models.py` | 未检出 | `TODO`：不能逐模型盘点。 |
| `backend/app/models/table_models.py` | 未检出 | `TODO`：不能逐模型盘点。 |

## 1. 项目现状摘要

### 当前主线功能

| 功能 | 当前事实 | 来源 |
|---|---|---|
| 报告自身核对 | 上传单个检验报告 PDF，检查报告内部字段、页码、结论、表格结果等一致性。 | `README.md`; `backend/app/routers/report_self_check.py`; `frontend/src/pages/ReportSelfCheckPage.tsx` |
| PTR 与报告核对 | 上传 PTR PDF 和检验报告 PDF，按报告首页“检验项目”范围核对 PTR 第 2 章要求是否被报告“标准要求”完整摘录。 | `README.md`; `backend/app/services/ptr_report_evidence_builder.py`; `backend/tests/test_ptr_report_evidence_builder.py` |
| 原始记录与报告核对 | 上传原始记录 PDF 和报告 PDF，支持 `GB 9706.1-2020` 与 `GB 9706.202-2021`，核对标准条款、判定和实测证据。 | `README.md`; `backend/app/services/record_report_evidence_builder.py`; `backend/app/services/record_report_check_service.py` |
| 结果分组展示 | 前端按 `error`、`warning`、`pass` 分组，展示优先处理项、执行日志、证据明细。 | `frontend/src/pages/ReportSelfCheckPage.tsx`; `frontend/src/components/report-self-check/` |
| PDF 导出 | 前端通过隐藏 iframe 生成打印 HTML 并调用浏览器打印。 | `frontend/src/export/reportPdfExport.ts`; `frontend/tests/reportPdfExport.test.mjs` |
| Codex 辅助判断 | 后端通过 Codex CLI 判断复杂语义或图文证据，并要求输出固定 JSON schema。 | `README.md`; `backend/app/services/codex_judge_client.py`; `backend/app/schemas/codex_check_result.schema.json` |

### 当前技术栈

| 层 | 技术 | 来源 |
|---|---|---|
| 后端 Web | FastAPI, Uvicorn, python-multipart | `backend/pyproject.toml`; `backend/app/main.py` |
| 后端模型 | Pydantic v2, pydantic-settings | `backend/pyproject.toml`; `backend/app/models/report_self_check.py`; `backend/app/config.py` |
| PDF 解析 | PyMuPDF (`fitz`), pdfplumber 依赖声明；当前 loader 主要使用 PyMuPDF 抽文本、词坐标、绘图和图片裁剪。 | `backend/pyproject.toml`; `backend/app/services/pdf_document_loader.py` |
| LLM/VLM | Codex CLI，支持附加图片、output schema、HTTP Responses provider 配置。 | `backend/app/services/codex_judge_client.py`; `backend/app/config.py`; `README.md` |
| 前端 | Vite, React 19, TypeScript | `frontend/package.json`; `frontend/src/main.tsx`; `frontend/src/App.tsx` |
| 前端 UI | 自定义 CSS，无组件库。 | `frontend/src/styles.css`; `frontend/package.json` |
| 测试 | pytest/httpx/pytest-asyncio，Node `node --test` 测 PDF 导出。 | `backend/pyproject.toml`; `backend/tests/`; `frontend/package.json`; `frontend/tests/reportPdfExport.test.mjs` |

### 当前新旧架构混杂问题

| 问题 | 现状 | 影响 | 来源 |
|---|---|---|---|
| 单 router 承载多业务 | `report_self_check.py` 同时暴露报告自身、PTR-report、record-report、任务查询。 | API 命名和业务边界混在一起，用户提到的 `report_check`、`ptr_compare` 文件在当前旧项目中不存在。 | `backend/app/routers/report_self_check.py` |
| 任务状态在内存中 | `TASKS` 全局 dict + `Lock`，后台任务写入同一结构。 | 进程重启即丢失；无任务过期/持久化；不利于重做项目。 | `backend/app/routers/report_self_check.py` |
| 领域模型散落 | 只有 `report_self_check.py` 是独立模型文件；PTR/原始记录结果模型定义在 service 文件中。 | 难以形成清晰 domain/application/api 分层。 | `backend/app/models/report_self_check.py`; `backend/app/services/ptr_report_check_service.py`; `backend/app/services/record_report_check_service.py` |
| 规则、证据构建和 Codex 提示耦合 | evidence builder 既抽证据、写规则说明、又决定图片附加范围。 | 规则资产可保留，但新架构需要拆分为 extractor、rule、judge prompt adapter。 | `backend/app/services/report_evidence_builder.py`; `backend/app/services/ptr_report_evidence_builder.py` |
| 规格与实现不一致 | 规格文档提到 14 个检查项含 `C17`，当前代码和测试明确只启用 13 个且排除 `C17`。 | 重写前必须确认最终检查项编号体系。 | `docs/superpowers/specs/...`; `backend/app/services/report_evidence_builder.py`; `backend/tests/test_report_evidence_builder.py` |
| 历史 Electron 路径不可见 | 用户点名的 `python_backend/`、`src/main/`、`src/renderer/`、根 `package.json` 在当前旧项目未检出。 | 不能把这些路径视为可迁移代码资产，只能作为废弃历史路径处理。 | 文件系统检查 |

## 2. 功能资产清单

### 2.1 PTR 条款核对

| 资产 | 当前能力 | 保留/迁移建议 | 来源 |
|---|---|---|---|
| 首页范围解析 | 从报告首页“检验项目”抽取 `2.x`、范围表达、括号排除项。 | 保留业务规则；迁移到 `domain/ptr/scope` 或 `application/ptr_compare/scope_parser`。 | `backend/app/services/ptr_report_evidence_builder.py`; `backend/tests/test_ptr_report_evidence_builder.py` |
| PTR 第 2 章条款证据 | 抽取 PTR 第 2 章条款，并按首页声明范围生成 `PTR-<prefix>` evidence package。 | 保留抽取思路；重写为清晰 parser + DTO。 | `backend/app/services/ptr_report_evidence_builder.py` |
| 最细条款核对 | 要求 Codex 按 `leaf_clause_reviews` 逐条比较 PTR 内容和报告内容。 | 保留 required details 与判断粒度。 | `backend/app/services/ptr_report_evidence_builder.py`; `backend/app/services/codex_judge_client.py` |
| 范围覆盖总览 | 后端插入 `PTR-SCOPE-COVERAGE` 确定性结果，识别缺漏和额外条款。 | 保留为 deterministic rule；迁移到 domain rule。 | `backend/app/services/ptr_report_check_service.py`; `backend/tests/test_ptr_report_check_service.py` |
| 纯图片 PTR 页 | 无文本页记录为 `ptr_textless_pages` 并把图片附给 Codex。 | 保留为扫描件证据策略；新架构需明确 OCR/VLM fallback。 | `backend/app/services/ptr_report_evidence_builder.py`; `backend/tests/test_ptr_report_evidence_builder.py` |

### 2.2 报告自身核对 C01-C11

用户要求盘点 `C01-C11`，但旧项目当前实现不是连续的 `C01-C11`。当前 `APPROVED_CHECK_IDS` 为：

`C00, C01, C02, C03, C04, C06, C07, C08, C12, C13, C14, C15, C16`

因此本文只保留可追溯的检查项，不补造不存在的 `C05`、`C09`、`C10`、`C11`。

| 检查项 | 当前名称 | 当前资产 | 迁移建议 | 来源 |
|---|---|---|---|---|
| C00 | 文档结构完整性 | 证据包要求 `detected_sections`、`missing_sections`、`section_order_ok`。 | 是否保留需产品确认；当前业务要求未点名。 | `backend/app/services/report_evidence_builder.py` |
| C01 | 报告编号与样品编号一致性 | 比较报告编号、样品编号、尾号匹配。 | 保留为独立 deterministic/LLM rule。 | `backend/app/services/report_evidence_builder.py`; `backend/tests/test_report_evidence_builder.py` |
| C02 | 首页基础字段一致性 | 输出 `field_comparisons`。 | 保留字段对比输出契约；字段集合需从新需求确认。 | 同上 |
| C03 | 首页扩展字段一致性 | 涉及 `见样品描述栏` 与图片/标签证据。 | 保留规则概念；实现需重写为显式规则。 | `docs/superpowers/specs/...`; `backend/app/services/report_evidence_builder.py` |
| C04 | 时间逻辑一致性 | 只核对到样/检验流程时间，不核对签发日期。 | 保留“签发日期 out of scope”规则。 | `backend/app/services/report_evidence_builder.py`; `backend/tests/test_report_evidence_builder.py` |
| C06 | 样品描述字段一致性 | required details 为 `rows`；附加图片证据。 | 保留为样品描述抽取/字段核对规则。 | `backend/app/services/report_evidence_builder.py` |
| C07 | 照片覆盖性 | required details 为 `components`；使用照片页证据。 | 保留功能意图；当前确定性实现不足，需重写。 | `backend/app/services/report_evidence_builder.py` |
| C08 | 样品描述与照片标签一致性 | 抽样品描述行、标签页字段、候选匹配页；可分批附图给 Codex。 | 高价值保留；重写为 label extractor + matcher + judge adapter。 | `backend/app/services/report_evidence_builder.py`; `backend/app/services/report_self_check_service.py`; `backend/tests/test_report_evidence_builder.py` |
| C12 | 检验结果与单项结论逻辑 | 包含无菌语境和 `/`、`——` 规则。 | 保留规则，但需明确与新编号 C01-C11 的映射。 | `docs/superpowers/specs/...`; `backend/app/services/report_evidence_builder.py`; `backend/tests/fixtures/codex_c12_error.json` |
| C13 | 单项结论与总结论逻辑 | required details 为 `overall_conclusion_text`、`nonconforming_sequences`、`overall_consistent`。 | 保留业务规则；当前主要靠 Codex。 | `backend/app/services/report_evidence_builder.py` |
| C14 | 非空字段核对 | 检验结果表中 `检验结果/单项结论/备注` 非空，含 layout 候选。 | 保留确定性候选算法；新架构应作为 table rule。 | `backend/app/services/report_evidence_builder.py`; `backend/app/services/report_self_check_service.py` |
| C15 | 序号连续性与续表正确性 | 提取序号和 `续` 标记，确定性生成续表候选。 | 保留规则和测试；拆成 sequence rule + continuation rule。 | 同上 |
| C16 | 页码连续性 | required details 为 `page_infos`、`missing_pages`、`duplicate_pages`、`total_consistent`、`final_page_match`。 | 保留规则意图；当前未读到强确定性实现，需补实现。 | `backend/app/services/report_evidence_builder.py`; `docs/superpowers/specs/...` |
| C05/C09/C10/C11 | 未实现于当前 `APPROVED_CHECK_IDS` | 当前旧项目不可追溯。 | `TODO`：重写前确认是否来自更早版本或新需求。 | 文件系统与代码检查 |

### 2.3 OCR / LLM / VLM

| 资产 | 当前事实 | 保留/迁移建议 | 来源 |
|---|---|---|---|
| OCR | 当前依赖中没有 OCR 引擎；现有代码主要从 PDF 文本层和图片页文字中提取标签字段。规格/计划提到 OCR/vision artifacts，但不是当前依赖。 | 保留字段映射和标签页识别规则；OCR 引擎需在新架构作为可替换 adapter。 | `backend/pyproject.toml`; `backend/app/services/report_evidence_builder.py`; `docs/superpowers/specs/...` |
| LLM | Codex CLI 是当前判断器；所有复杂检查输出统一 `CheckResult` JSON。 | 保留 prompt contract 和 schema；重写为 `JudgeClient` 边界。 | `backend/app/services/codex_judge_client.py`; `backend/app/schemas/codex_check_result.schema.json` |
| VLM | 通过 `--image` 给 Codex CLI 附加整页图和图片块裁剪图；C08 支持图片分批。 | 保留“图片证据必须直接审阅”的业务要求；新架构需要稳定重试和证据日志。 | `backend/app/services/pdf_document_loader.py`; `backend/app/services/report_self_check_service.py` |

### 2.4 PDF 导出

| 资产 | 当前能力 | 保留/迁移建议 | 来源 |
|---|---|---|---|
| 结果标题 | 按模式生成文件名，如报告自身、PTR 与报告、原始记录与报告。 | 保留命名规则。 | `frontend/src/export/reportPdfExport.ts` |
| HTML 打印模板 | 包含封面、汇总、PTR 范围、问题清单、明细、系统诊断和页脚。 | 保留展示结构；重写为可测试 formatter。 | `frontend/src/export/reportPdfExport.ts`; `frontend/tests/reportPdfExport.test.mjs` |
| 打印方式 | 前端隐藏 iframe `window.print()`，不是后端生成 PDF。 | 可短期保留；新架构若需服务端 PDF，需另立导出 adapter。 | `frontend/src/export/reportPdfExport.ts` |

### 2.5 前端 Dashboard、上传、进度、结果展示

| 资产 | 当前能力 | 保留/迁移建议 | 来源 |
|---|---|---|---|
| 工作台页面 | `ReportSelfCheckPage` 是唯一主页面，承担 Dashboard、模式切换、上传、进度、结果。 | 保留流程概念；拆成页面 + feature components。 | `frontend/src/pages/ReportSelfCheckPage.tsx` |
| 上传 | 支持报告单文件、PTR+报告双文件、原始记录+报告双文件，支持 drag/drop。 | 保留交互。 | 同上 |
| 进度 | 每 2 秒轮询任务；localStorage 按模式恢复 last task。 | 保留用户体验；新架构应统一 task API。 | `frontend/src/pages/ReportSelfCheckPage.tsx`; `frontend/src/api/reportSelfCheck.ts` |
| 结果展示 | 总览、优先处理、错误/需复核/通过分组，check card 展示详情。 | 保留信息架构；重写组件边界和样式系统。 | `frontend/src/components/report-self-check/`; `frontend/src/styles.css` |

## 3. 业务规则资产清单

### 3.1 PTR 规则

| 规则 | 当前可追溯表述 | 保留/迁移 | 来源 |
|---|---|---|---|
| 只核对标准要求 | PTR-report 只判断 report 表格的“标准要求”，不核对检验结果/单项结论。 | 保留为 PTR 核对核心边界。 | `backend/app/services/ptr_report_evidence_builder.py` |
| `≥/≤` 与 `>/<` 不等价 | 差异按不一致处理。 | 保留为文本/符号比较规则。 | 同上；`backend/tests/test_ptr_report_evidence_builder.py` |
| 报告可展开 PTR 引用表格 | 只要标准要求完整覆盖对应 PTR 条款即可。 | 保留；新架构需表格引用解析。 | 同上 |
| 首页未声明不算缺失 | 未声明的 PTR 第 2 章条款不应作为问题。 | 保留范围控制规则。 | 同上 |
| 首页括号排除项 | “除/不含/不包括/排除”括号内容可排除生物相容性、电磁兼容性等项目。 | 保留；做成 scope exclusion parser。 | `backend/app/services/ptr_report_evidence_builder.py`; `backend/tests/test_ptr_report_evidence_builder.py` |
| 2.4 索引式摘要容忍 | 若 report 用“见序号1～序号118”、GB 标准号或附录索引概括安全要求，核心要求已覆盖时不应仅因此判问题。 | 保留，但需业务确认适用范围仅限当前规则。 | `backend/app/services/ptr_report_check_service.py`; `backend/tests/test_ptr_report_check_service.py` |
| 纯图片 PTR 页 | 文本为空的 PTR 页不伪造条款，作为图片证据交给 Codex。 | 保留为证据策略。 | `backend/app/services/ptr_report_evidence_builder.py` |

### 3.2 报告自身 C 规则

| 规则 | 当前可追溯表述 | 保留/迁移 | 来源 |
|---|---|---|---|
| C04 签发日期不核对 | C04 只核对到样日期、检验日期等流程时间逻辑，不核对签发日期。 | 保留为 out-of-scope 规则。 | `backend/app/services/report_evidence_builder.py`; `backend/tests/test_report_evidence_builder.py` |
| C08 名称容忍，型号/批号严格 | 名称允许合理换行或空格差异；型号、批号/序列号必须一致。 | 保留为 label match rule。 | `backend/app/services/report_evidence_builder.py` |
| C08 空字段含义 | `label_items.fields` 为空只表示 PDF 文本层未抽到图片内标签字段，不代表标签不存在；附图时必须审阅图片。 | 保留为 OCR/VLM 边界。 | 同上；`backend/app/services/report_self_check_service.py` |
| C12 无菌语境 | 在“无菌/应无菌”语境下，“无菌生长”可作为符合证据；不能泛化到有菌生长/阳性。 | 保留为领域语义规则。 | `backend/app/services/report_evidence_builder.py`; `backend/tests/test_report_evidence_builder.py` |
| C12 全 `/` 或 `——` | 规格文档和 fixture 表示全部检验结果为 `/` 或 `——` 时，期望单项结论为 `/`。 | 保留但需和新编号体系对齐。 | `docs/superpowers/specs/...`; `backend/tests/fixtures/codex_c12_error.json` |
| C14 非空范围 | C14 只检查检验结果表中的 `检验结果`、`单项结论`、`备注` 三类结果值列，不检查首页、签字栏、日期等。 | 保留为表格规则。 | `backend/app/services/report_evidence_builder.py` |
| C14 `/` 不是空 | 备注列填 `/` 属于正常空白标记；只要存在任何数字、字符、汉字或 `/`，都视为非空。 | 保留为 C14 专属规则；不要泛化为所有字段。 | 同上 |
| C15 续表 | 首次出现的序号不应写“续”；同一序号后续页或后续片段再次出现时应写“续+序号”。 | 保留为确定性规则。 | `backend/app/services/report_evidence_builder.py`; `backend/app/services/report_self_check_service.py` |
| C16 页码连续 | 规格要求页码信息、缺页、重复页、总页数一致、末页匹配。 | 保留规则意图；当前实现主要是 evidence required details，`TODO` 补确定性规则。 | `backend/app/services/report_evidence_builder.py`; `docs/superpowers/specs/...` |

### 3.3 用户点名规则逐项结论

| 点名规则 | 当前结论 | 新架构处理 |
|---|---|---|
| OCR 字段映射 | 现有 `_extract_label_fields` 从文本层识别：`产品名称`、`样品名称`、`部件名称`、`型号规格`、`规格型号`、`型号/规格`、`型号`、`产品编号/批号`、`批号/序列号`、`序列号/批号`、`批号`、`序列号`、`生产日期`、`失效日期`。 | 保留字段别名表；改成配置化 label field parser。 |
| Caption 主体名提取 | `_extract_label_caption` 优先取含“标签”且含 `№` 或 `No` 的行，否则取任意含“标签”的行。`_candidate_label_names` 会去掉 `№ 数字` 并规范化“标签样张”。 | 保留为 caption extractor；新增测试覆盖 No/№/中文标签样张。 |
| “见样品描述栏”规则 | 规格文档 C03 提到；当前 builder 只把 `see_sample_desc_consistent` 作为 required detail，未读到独立确定性实现。 | `TODO`：新架构必须显式定义何时允许、何时必须回到样品描述核对。 |
| “本次检测未使用”规则 | 规格文档 C07/C08 提到：备注含该文本时无照片/标签不失败；当前代码未读到确定性分支。 | `TODO`：作为 rule asset 保留，但需补实现和测试。 |
| “/ 与空白等价”规则 | 旧项目并无全局等价规则。C14 中 `/` 明确视为非空占位；record-report 中 `/` 可被规范为“不适用”；C12 中全 `/`/`——` 推导期望结论 `/`。 | 不做全局规则；按字段和检查项建立 value semantics。 |
| 非空字段联合键 | 当前 C14 去重 key 为 `(page, row_no, suspected_fields, nearby_text)`；C08 候选匹配使用样品名称、型号、批号/序列号组合。没有名为“非空字段联合键”的统一模型。 | 保留“多字段组合识别”的思路；`TODO`：在新领域模型中定义 row identity / sample identity。 |
| 页码规则 | C16 规格有页码连续性要求；当前代码只传 evidence details 给 Codex。 | 保留规则，重写为确定性 page-number parser。 |
| 续表规则 | C15 当前有布局词和文本两套抽取，并确定性生成 `missing_continuation_marker`、`unexpected_continuation_marker`。 | 高价值保留，迁移为 `domain/report/rules/continuation.py`。 |

## 4. 后端代码资产清单

| 服务文件 | 当前职责 | 可复用逻辑 | 需要重写的原因 | 建议迁移位置 |
|---|---|---|---|---|
| `backend/app/services/pdf_document_loader.py` | 用 PyMuPDF 加载 PDF，抽取文本、页面尺寸、词坐标、绘图；识别照片页/无文本页并渲染整页图和图片块裁剪图。 | PDF 页面 DTO、layout words、drawings、照片页/无文本页渲染策略。 | 返回裸 dict；渲染、解析、业务照片页判断耦合；没有 OCR adapter。 | `infrastructure/pdf/pdf_document_loader.py`; DTO 放 `domain/pdf/models.py`。 |
| `backend/app/services/codex_judge_client.py` | 封装 Codex CLI 命令、output schema、图片参数、错误压缩、prompt 构造。 | `JudgeTransport` 协议、静态 transport 测试方式、schema 输出契约、图片数量限制。 | prompt 中混入 report/PTR/record 多业务角色；错误处理和业务降级耦合。 | `infrastructure/judge/codex_cli_client.py`; prompt adapter 放各 feature。 |
| `backend/app/services/report_evidence_builder.py` | 构建报告自身核对 13 个 evidence package；内含检查项清单、规则说明、C08 标签抽取、C14/C15 候选。 | `APPROVED_CHECK_IDS` 当前事实、C08 字段映射、C14 空字段候选、C15 续表候选。 | 单文件承担规则定义、证据抽取、图片策略和 prompt required details；编号与规格不一致。 | `application/report_self_check/evidence_builder.py`; 规则拆到 `domain/report/rules/`。 |
| `backend/app/services/report_self_check_service.py` | 编排报告自身核对：构建 packages、调用 Codex、C08 图片分批、合并结果、追加 C14/C15 确定性 findings。 | C08 分批合并、批次误报过滤、C14/C15 确定性补充结果。 | 业务流程、LLM 调用、确定性规则补丁混在一起；结果完全依赖 Pydantic API 模型。 | `application/report_self_check/service.py`; deterministic rules 独立。 |
| `backend/app/services/ptr_report_evidence_builder.py` | 解析报告首页范围、PTR 第 2 章条款、报告条款 entries、排除项、textless PTR pages、scope coverage。 | PTR 范围解析、括号排除、缺漏条款覆盖、textless 页策略。 | 复杂 regex/parser 都在单文件；模型为 dict；表格引用只作为文本证据交给 Codex。 | `domain/ptr/scope.py`; `domain/ptr/clause_parser.py`; `application/ptr_compare/evidence_builder.py`。 |
| `backend/app/services/ptr_report_check_service.py` | 编排 PTR-report 核对，插入 `PTR-SCOPE-COVERAGE` 确定性 package，抑制允许的 2.4 warning，返回结果子类。 | 范围覆盖 deterministic result、2.4 索引摘要抑制逻辑。 | 结果模型定义在 service；抑制规则 hardcode；task/API 边界不清。 | `application/ptr_compare/service.py`; `domain/ptr/rules/scope_coverage.py`。 |
| `backend/app/services/record_report_evidence_builder.py` | 抽取原始记录和报告行，支持 GB9706.1/9706.202；规范条款号、判定、勾选符号、实测值；构建序号级 comparisons。 | 条款号规范化、`/` 到“不适用”的语义、聚合判定优先级、9.6.2 数值比较、GB9706.202 映射。 | 文件很大，包含多个标准、多种解析策略、规则和比较；需要按标准拆分。 | `domain/record_report/gb9706_1/*`; `domain/record_report/gb9706_202/*`; shared normalizers。 |
| `backend/app/services/record_report_check_service.py` | 编排原始记录核对，支持 quick/full_codex、并发、Codex 缓存、确定性 pass 快路径。 | quick/full 模式、并发上限 8、judge cache、deterministic issues 到 finding 的转换。 | 不是本次重做重点清单但属于旧项目主线；service 中含结果模型和缓存全局状态。 | `application/record_report/service.py`; cache 放 `infrastructure/cache`。 |
| `backend/app/services/__init__.py` | 包初始化，无业务逻辑。 | 无。 | 不需要迁移业务资产。 | 新架构按包需要创建。 |

## 5. 数据模型资产清单

### 5.1 用户点名模型文件状态

| 文件 | 当前旧项目状态 | 结论 |
|---|---|---|
| `backend/app/models/common_models.py` | 未检出 | `TODO`：不能分析字段；若来自更早版本，需要先恢复文件。 |
| `backend/app/models/report_models.py` | 未检出 | `TODO`：不能分析字段；当前报告相关 DTO 多为 dict。 |
| `backend/app/models/ptr_models.py` | 未检出 | `TODO`：不能分析字段；当前 PTR 相关 DTO 多为 dict。 |
| `backend/app/models/table_models.py` | 未检出 | `TODO`：不能分析字段；当前表格模型未独立存在。 |

### 5.2 当前实际存在的 Pydantic 模型

来源：`backend/app/models/report_self_check.py`

| 模型 | 当前字段 | 用途 | 是否保留 | 是否改造成 Pydantic | 新架构位置 |
|---|---|---|---|---|---|
| `CheckStatus` | `pass`, `warning`, `error` | 统一检查状态。 | 保留。 | 已是 enum，可继续用于 Pydantic schema。 | `domain/common/status.py` 或 `api/schemas/check_result.py` |
| `Confidence` | `high`, `medium`, `low` | 表示判断置信度。 | 保留。 | 已可直接用于 Pydantic。 | 同上 |
| `FindingSeverity` | `warning`, `error` | finding 严重度。 | 保留。 | 已可直接用于 Pydantic。 | 同上 |
| `Finding` | `severity`, `title`, `detail`, `expected`, `actual`, `pages`, `related_fields` | 规则发现问题的统一结构。 | 高价值保留。 | 已是 Pydantic；建议作为领域输出/接口 DTO 双层映射。 | `domain/common/finding.py`; `api/schemas/finding.py` |
| `EvidenceItem` | `source`, `page`, `label`, `value` | 展示判定证据。 | 保留但字段需更严格。 | 已是 Pydantic。 | `domain/common/evidence.py` |
| `MissingEvidence` | `label`, `reason`, `expected_source` | 表示证据不足/缺失。 | 保留。 | 已是 Pydantic。 | `domain/common/evidence.py` |
| `FieldComparison` | `field`, `source_a_name`, `source_a_value`, `source_a_page`, `source_b_name`, `source_b_value`, `source_b_page`, `matched`, `judgement` | 字段对比明细。 | 保留。 | 已是 Pydantic；可用于报告字段核对。 | `domain/report/field_comparison.py` |
| `CheckResult` | `check_id`, `check_name`, `status`, `confidence`, `summary`, `details`, `findings`, `evidence`, `missing_evidence` | 所有核对模式的单项结果。 | 保留结构，重写 `details` 为类型化 union 或明确 schema。 | 已是 Pydantic。 | `api/schemas/check_result.py`; domain 可用更强类型。 |
| `ReportMeta` | `report_number`, `sample_number`, `sample_name`, `client` | 报告元信息。 | 保留但当前填充不足。 | 已是 Pydantic。 | `domain/report/models.py` |
| `SummaryCounts` | `total_checks`, `pass_count`, `warning_count`, `error_count` | 汇总计数。 | 保留。 | 已是 Pydantic。 | `api/schemas/summary.py` |
| `ReportSelfCheckResult` | `task_id`, `file_name`, `overall_status`, `report_meta`, `summary`, `check_results`, `refresh_summary()` | 报告自身核对结果基类；PTR/record 结果继承它。 | 保留结果概念；不要作为所有业务的基类硬套。 | 已是 Pydantic。 | `api/schemas/report_self_check.py` |

### 5.3 Service 内衍生模型

| 模型 | 当前字段 | 用途 | 是否保留 | 新架构位置 |
|---|---|---|---|---|
| `PtrReportCheckResult` | 继承 `ReportSelfCheckResult`，新增 `ptr_file_name`, `report_file_name`, `homepage_scope`, `ptr_report_scope_summary`。 | PTR-report API 返回结构。 | 保留字段语义，单独建 schema。 | `api/schemas/ptr_compare.py` |
| `RecordReportCheckResult` | 继承 `ReportSelfCheckResult`，新增 `record_file_name`, `report_file_name`, `record_report_standard`, `record_report_mode`, `record_report_concurrency`, `record_report_summary`。 | 原始记录-report API 返回结构。 | 保留字段语义，单独建 schema。 | `api/schemas/record_report.py` |

## 6. API 资产清单

旧项目当前没有 `backend/app/routers/report_check.py` 或 `ptr_compare.py`，所有接口都在 `backend/app/routers/report_self_check.py`，并由 `backend/app/main.py` 挂载到 `/api/report-self-check`。

| 接口 | 请求参数 | 返回结构 | 当前问题 | 新接口建议 |
|---|---|---|---|---|
| `GET /api/report-self-check/health` | 无 | `{"status": "ok"}` | health 放在业务 router 下。 | 保留健康检查，可迁移为 `/api/health`。 |
| `POST /api/report-self-check/check` | multipart `file`，必须 PDF。 | `ReportSelfCheckResult` JSON。 | 同步执行可能耗时，且会直接调用 Codex。 | 改为只保留异步：`POST /api/report-checks` 创建任务。 |
| `POST /api/report-self-check/check/start` | multipart `file`。 | task dict：`task_id`, `file_name`, `status`, `current_check_id`, `current_check_name`, `completed_checks`, `total_checks`, `logs`, `result`, `error`。 | task in-memory；状态名与前端类型绑定；无过期/取消。 | `POST /api/report-checks` 返回 `task_id`；`GET /api/tasks/{id}` 查询。 |
| `POST /api/report-self-check/ptr-report/check` | multipart `ptr_file`, `report_file`。 | `PtrReportCheckResult` JSON。 | 同步执行；命名嵌在 report-self-check 下。 | `POST /api/ptr-comparisons`。 |
| `POST /api/report-self-check/ptr-report/check/start` | multipart `ptr_file`, `report_file`。 | task dict，含 `ptr_file_name`, `report_file_name`。 | 与报告自身任务结构重复但无统一 schema。 | `POST /api/ptr-comparisons` 创建任务。 |
| `POST /api/report-self-check/record-report/check` | multipart `record_file`, `report_file`; form `record_report_mode=quick`; `record_report_concurrency=4`; `record_report_standard=gb9706_1`。 | `RecordReportCheckResult` JSON。 | 原始记录不是用户本次核心点名 API，但已混入同一 router。 | 独立为 `POST /api/record-report-checks` 或暂缓迁移。 |
| `POST /api/report-self-check/record-report/check/start` | 同上。 | task dict，含 record-report 参数。 | 参数归一化在 router/service 间分散。 | 独立任务接口，参数 schema 化。 |
| `GET /api/report-self-check/tasks/{task_id}` | path `task_id`。 | task dict 或 404。 | 所有模式共用 dict；无持久化、鉴权、任务类型字段。 | `GET /api/tasks/{task_id}` 返回统一 `TaskStatus` schema，result 用 typed payload。 |

返回结构可复用资产：

- `CheckResult` 作为所有检查项统一结构。
- `Finding`、`EvidenceItem`、`MissingEvidence` 作为问题、证据、缺证据输出。
- `SummaryCounts` 用于 pass/warning/error 统计。
- `homepage_scope` 和 `ptr_report_scope_summary` 是 PTR-report 前端展示需要的业务摘要。

## 7. 测试资产清单

后端当前约 127 个 `test_` 函数，另有前端 PDF 导出测试。测试中引用 `素材/` 下本地样例；这些样例不应作为源代码迁移，但适合作为 golden fixture 的候选输入。

| 测试文件 | 覆盖模块 | 适合保留的测试 | 需要重写的测试 | Golden Test 候选 |
|---|---|---|---|---|
| `backend/tests/test_codex_judge_client.py` | Codex transport、schema、图片限制、错误处理。 | Static transport、schema validation、image limit。 | CLI 命令参数随新 adapter 重写。 | 否，偏 adapter contract。 |
| `backend/tests/test_pdf_document_loader.py` | PyMuPDF loader、照片页渲染、本地样例 PDF。 | 页面抽取、layout words、render 策略。 | 依赖本机 `素材/` 的路径要改成受控 fixture。 | 是：样例 PDF 渲染/抽取回归。 |
| `backend/tests/test_ptr_report_check_api.py` | PTR API、非法 PDF、真实样例、异步任务。 | 错误输入和 task contract 思路。 | endpoint 名称和 task schema 需重写。 | 是：3940 PTR/report 对照样例。 |
| `backend/tests/test_ptr_report_check_service.py` | PTR service、scope coverage、2.4 warning suppression。 | 范围覆盖、2.4 抑制规则。 | service 类名/位置变更后重写。 | 是：scope coverage 行为。 |
| `backend/tests/test_ptr_report_evidence_builder.py` | 首页范围、排除项、文本空页、PTR package。 | 高价值保留：范围解析、排除项、textless 页、`≥/≤` 规则。 | dict evidence 改强类型后重写断言。 | 是：PTR 规则 golden。 |
| `backend/tests/test_record_report_check_api.py` | 原始记录 API 参数、模式、并发、标准归一化。 | 参数归一化与并发上限。 | endpoint 和 schema 重写。 | 否，偏 API contract。 |
| `backend/tests/test_record_report_check_service.py` | quick/full_codex、cache、deterministic issues。 | quick pass fast path、cache、并发上限。 | service 拆分后重写。 | 是：deterministic issue matrix。 |
| `backend/tests/test_record_report_evidence_builder.py` | GB9706.1/202 条款、判定、实测值、映射。 | 高价值保留：`/` 不适用、聚合判定、9.6.2 数值比较、202 fallback。 | 大文件拆分后按标准分组重写。 | 是：原始记录规则 golden。 |
| `backend/tests/test_report_evidence_builder.py` | C 检查项、C08 标签抽取、C14/C15 候选、C17 排除。 | 高价值保留：C08/C14/C15、C17 不在当前实现的事实。 | 新 C01-C11 编号确认后重写。 | 是：报告规则 golden。 |
| `backend/tests/test_report_self_check_api.py` | health、非法 PDF、同步/异步报告核对、本地样例。 | API 错误处理和任务轮询。 | endpoint 和任务 schema 重写。 | 是：报告样例回归。 |
| `backend/tests/test_report_self_check_models.py` | Pydantic 模型、schema JSON。 | CheckResult/Finding schema contract。 | `details` 强类型化后重写。 | 否，偏 schema contract。 |
| `backend/tests/test_report_self_check_service.py` | C08 分批、C14/C15 确定性补充。 | 高价值保留：图片分批、误报过滤、确定性 finding。 | service 拆分后重写。 | 是：C08/C14/C15 行为。 |
| `frontend/tests/reportPdfExport.test.mjs` | PDF 导出 HTML、标题、系统诊断、iframe 打印。 | 导出标题、HTML section、iframe print 行为。 | 前端导出模块改造后重写 import/build 流程。 | 是：导出 HTML 快照/结构测试。 |

测试迁移原则：

- 保留业务规则测试，不保留旧 API 路径断言。
- 把本地 `素材/` 样例整理成受控 golden fixture；不直接依赖用户机器上的原始目录。
- 对 OCR/VLM/Codex 输出使用固定 JSON fixture 或 fake judge，不把 live Codex 结果作为稳定断言。

## 8. 前端资产清单

| 类别 | 当前文件 | 当前资产 | 可复用内容 | 需要重写内容 |
|---|---|---|---|---|
| 页面 | `frontend/src/pages/ReportSelfCheckPage.tsx` | 单页工作台，包含三种模式、上传、任务轮询、结果分组、PDF 导出。 | 模式切换、上传流程、进度体验、优先处理区。 | 文件过大；Dashboard/上传/任务/结果需拆组件；状态管理需简化。 |
| 根组件 | `frontend/src/App.tsx`, `frontend/src/main.tsx` | 直接渲染 `ReportSelfCheckPage`。 | 简单入口。 | 新架构若有路由需重写。 |
| API service | `frontend/src/api/reportSelfCheck.ts` | 封装 start/self/PTR/record API 和 task polling fetch。 | FormData 参数名、错误信息读取。 | API 路径需跟新后端重命名；类型化错误和 task client。 |
| types | `frontend/src/types/reportSelfCheck.ts` | `CheckStatus`、`Confidence`、`RecordReportCheckMode`、`ReportSelfCheckResult`、`ReportSelfCheckTask` 等。 | 结果/任务 shape 可作为新 schema 起点。 | 与后端 OpenAPI/Pydantic schema 对齐，避免手写漂移。 |
| 结果组件 | `CheckResultCard.tsx`, `CheckDetailsTable.tsx`, `FindingsList.tsx`, `OverallSummary.tsx` | 状态展示、详情表格、finding 列表、summary 统计、PTR scope summary。 | 结果信息架构。 | 需要适配 typed details；复杂字段展示应抽 formatter。 |
| display 工具 | `components/report-self-check/display.ts` | 状态 label、诊断信息折叠、Codex 错误友好化。 | 状态文案和诊断过滤经验。 | 移到 shared formatter，避免散落在组件。 |
| PDF export | `frontend/src/export/reportPdfExport.ts` | HTML 打印导出，支持三种模式。 | 导出章节结构和 label map。 | 与新 result schema 对齐；可考虑服务端导出。 |
| UI 设计系统 | `frontend/src/styles.css` | 自定义 CSS 变量，pass/warning/error 语义色，卡片、进度、上传区、表格、打印样式。 | 语义状态色和密集信息布局。 | 缺少组件库/设计 token 分层；页面样式耦合。 |
| 前端包 | `frontend/package.json` | Vite/React/TS scripts；`test:export` 使用 `/tmp/report-pdf-export-test`。 | 基础构建链。 | 硬编码 `/tmp` 测试输出需配置化。 |

当前没有独立 `Dashboard.tsx` 文件；`ReportSelfCheckPage.tsx` 承担 Dashboard/工作台功能。

## 9. 废弃清单

| 项 | 当前状态 | 不进入新架构原因 | 处理 |
|---|---|---|---|
| `python_backend/` | 旧项目当前未检出。 | 无可追溯代码；即使来自更早 Electron 版本，也与当前 FastAPI 主线重复。 | 废弃；如后续找到，只抽业务规则和测试样例。 |
| `src/main/` | 旧项目当前未检出。 | Electron 主进程路径，不属于当前 Web/FastAPI 主线。 | 废弃。 |
| `src/renderer/` | 旧项目当前未检出。 | Electron renderer 路径，不属于当前 React/Vite 主线。 | 废弃。 |
| 根目录 Electron `package.json` 相关脚本 | 根目录 `package.json` 未检出；仅 `frontend/package.json` 存在。 | 当前无法追溯 Electron 脚本；新架构不应依赖历史桌面启动方式。 | 废弃；保留 `frontend/package.json` 中 Vite 脚本作为前端资产。 |
| `start.sh` | 未检出。 | 无可追溯内容。 | 不迁移。 |
| 硬编码本地路径脚本 | `README.md` 启动/测试命令使用 `/Users/lulingfeng/miniforge3/bin/python3`，且写的是后端 `8000`、前端 `5173`；`frontend/vite.config.ts` 实际默认 proxy 为 `http://127.0.0.1:8001`、dev server 为 `5174`；`frontend/package.json` 的 `test:export` 写入 `/tmp/report-pdf-export-test`。 | 绑定用户机器、本地临时目录或互相不一致的本地端口，不适合作为新架构脚本。 | 改为环境变量/相对工具链；当前不修改代码。 |
| `uploads/` | 旧项目当前未检出。 | 若存在应为上传运行时目录，不是业务资产。 | 不迁移。 |
| `temp/` | 旧项目当前未检出；后端实际使用 `mkdtemp(prefix="report-self-check-pages-")` 生成系统临时目录。 | 运行时临时图像/裁剪图，不是源资产。 | 不迁移；新架构需要明确 cleanup 策略。 |
| `logs/` | 旧项目当前未检出。 | 运行日志不应进入领域模型或业务规则。 | 不迁移。 |
| `tmp/`, `frontend/node_modules/`, `frontend/dist/`, `素材/` | README 明确这些目录不会提交到 GitHub；当前 `素材.zip` 也不应作为代码资产。 | 运行时/依赖/构建产物/原始样例，不进入应用架构。 | `素材/` 仅作为 golden fixture 来源候选，需复制到受控测试目录后使用。 |

## 10. 风险与不确定点

| 风险 | 当前证据 | 影响 | TODO |
|---|---|---|---|
| 业务规则编号歧义 | 用户要求 `C01-C11`，当前代码启用 `C00,C01,C02,C03,C04,C06,C07,C08,C12,C13,C14,C15,C16`。 | 新项目若直接按 C01-C11 设计会丢失或错配旧资产。 | 确认新编号与旧编号映射表。 |
| 规格与代码不一致 | 规格/计划提到 `C17` 和 14 项；当前代码和测试明确排除 `C17`。 | 迁移测试和需求会冲突。 | 确认 `C17` 是废弃、待实现还是旧规格残留。 |
| 点名模型文件缺失 | `common_models.py`、`report_models.py`、`ptr_models.py`、`table_models.py` 未检出。 | 不能迁移旧模型结构，只能从当前 dict/Pydantic 结果反推。 | 如有外部历史包，先恢复文件再二次盘点。 |
| OCR/VLM 不稳定 | 当前无 OCR 引擎依赖，标签字段为空可能只是文本层没抽到；Codex 图片判断受图片数量和模型可用性影响。 | 不应把 OCR/VLM 输出当确定事实。 | 新架构定义 OCR confidence、VLM fallback、人工复核边界。 |
| PDF 格式复杂 | 代码大量依赖 layout words、行列坐标、文本正则、照片页识别。 | 扫描件、合并单元格、多页续表、图片标签都会导致误判。 | 建立 golden PDF 集和可视化证据审查。 |
| API 任务不可靠 | 当前任务状态是进程内 dict，且同步接口仍存在。 | 任务丢失、并发/重启行为不可控。 | 新架构任务状态持久化或至少抽象 task store。 |
| 测试依赖本地样例 | 多个测试引用 `素材/report/3940`、`素材/ptr/3940` 等本机路径。 | CI 或新项目环境不可重复。 | 整理最小可提交 fixture；原始素材不直接改写。 |
| “/ 与空白等价”容易误用 | 旧代码中 `/` 在 C14 是非空，在 record-report 是“不适用”，在 C12 是期望结论。 | 全局归一化会破坏业务语义。 | 为每个字段定义 value semantics profile。 |
| PTR 表格引用能力不足 | 当前 PTR-report 规则说 report 可展开 PTR 引用表格，但未检出独立 `table_models.py` 或 table comparator。 | 新架构若需要严格表格比对，需额外实现。 | 确认当前版本是否只依赖 Codex 语义审阅，还是存在外部历史表格模块。 |

## 11. 建议迁移优先级

| 优先级 | 资产 | 原因 |
|---|---|---|
| P0 | `Finding`/`CheckResult`/`MissingEvidence` 输出契约 | 前后端和测试都围绕它组织，迁移后可稳定接口。 |
| P0 | C08 标签字段映射、C14 非空字段、C15 续表规则 | 旧代码已有可测确定性逻辑，业务价值高。 |
| P0 | PTR 首页范围、排除项、scope coverage | PTR-report 的核心业务边界，测试覆盖较清晰。 |
| P1 | Codex judge schema 和 fake transport 测试方式 | 可保证 LLM/VLM 输出可控，不依赖 live 模型测试。 |
| P1 | PDF loader 的页面/词坐标/图片裁剪 | 多个规则依赖，但需拆出业务判断。 |
| P1 | 前端结果分组和 PDF 导出结构 | 用户可见资产，适合作为新 UI 的信息架构参考。 |
| P2 | 原始记录 vs 报告规则 | README 当前主线功能之一，但用户本次重点是 PTR 与报告自身；建议二阶段迁移。 |
