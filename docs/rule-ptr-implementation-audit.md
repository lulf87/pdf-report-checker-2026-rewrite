# C01-C11 与 PTR 状态漂移审计

审计日期：2026-06-15

## 审计范围

本次审计只检查当前新仓库中已经存在的规则、模型和测试，不实现新功能，不修改业务代码，不修改规则代码，不修改 PTR 代码。

已读取和对照：

- `AGENTS.md`
- `docs/tasks.md`
- `docs/current-status.md`
- `docs/known-requirements.md`
- `docs/spec-code-test-gaps.md`
- `docs/test-migration-matrix.md`
- `backend/app/rules/`
- `backend/app/domain/`
- `backend/tests/`

## 验证命令

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3/backend
python -m pytest tests/rules/report tests/rules/ptr tests/infrastructure/table tests/infrastructure/ptr tests/application/test_report_check_usecase.py tests/application/test_ptr_compare_usecase.py -v
```

结果：通过，`158 passed`。

## 总体结论

1. C01-C11 均存在独立规则文件和独立 pytest，不是空骨架；`ReportRuleRunner` 已按 C01-C11 顺序注册。
2. C01-C11 均输出统一 `Finding` / `CheckResult` 模型；领域模型要求 ERROR/WARN finding 必须包含 `evidence` 或 `missing_evidence`。
3. 多数 C 规则已经覆盖 known requirements 的核心语义，但 C02、C03、C05、C07、C10 仍有业务口径或真实样本覆盖不足，建议不要一次性全量打勾。
4. PTR 已存在 scope filter、clause text compare、table reference compare、parameter compare、PTR extractor、CanonicalTable 和 TableNormalizer。
5. PTR 原最大漂移点已在 2026-06-15 修复：`parameter_compare.py` 已接入 `PTRCompareUseCase`，参数值、单位和缺失参数 finding 可进入最终 `PTR_TABLE` CheckResult。报告侧 canonical 表来源也已由 `ReportParameterTableExtractor` 从 `ParsedPdf` 表格生成，并写入推荐主 key `ReportDocument.metadata["canonical_tables"]`。PTR 双文件上传 API 已补受控 fixture/golden 端到端保护，剩余风险是真实样本候选选择、diff 结构和旧 PTR 表格深层语义仍需补强。
6. `backend/app/rules/ptr/__init__.py` 中仍写着复杂 PTR 逻辑未迁移的旧注释，和当前已有 PTR rule 文件状态不一致；这是文档/注释漂移，不影响测试，但后续应清理。

## C01-C11 审计

| 规则 | 实现文件 | 测试文件 | 状态建议 | 审计结论 |
| --- | --- | --- | --- | --- |
| C01 首页与第三页一致性 | `backend/app/rules/report/c01_home_vs_third.py` | `backend/tests/rules/report/test_c01_home_vs_third.py` | 可标记完成 | 真实实现，严格比较委托方、样品名称、型号规格；缺失和不一致均输出 ERROR Finding，包含 expected/actual/evidence/location/missing_evidence。测试覆盖一致、不一致、缺失、多字段、空格/全半角/大小写/标点敏感。 |
| C02 第三页扩展字段 | `backend/app/rules/report/c02_third_page_extended_fields.py` | `backend/tests/rules/report/test_c02_third_page_extended_fields.py` | 部分完成，需要人工确认 | 核心三字段、`见样品描述栏` 全部/部分逻辑、标签同义词、OCR 缺失和低置信均已实现。委托方/委托方地址仅作为 `optional_field_results` 记录，不输出 ERROR/WARN；这符合 `spec-code-test-gaps.md` 的冲突处理，但未完全满足 `known-requirements.md` 中可能包含的字段范围。第三页核心字段缺失当前为 WARN，早期提示中也有 ERROR 口径，需确认。 |
| C03 生产日期格式 | `backend/app/rules/report/c03_production_date.py` | `backend/tests/rules/report/test_c03_production_date.py` | 部分完成，需要人工确认 | 已按 `spec-code-test-gaps.md` 采用 `compare_value_enabled=false`，只比格式，不比日期值；支持 `YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY.MM.DD`、`YYYYMMDD`、无前导零斜杠格式；缺第三页日期 ERROR，缺标签日期和低置信 WARN。与 `docs/tasks.md`/`known-requirements.md` 中“格式和值一致性”的表述仍冲突，需先裁决后再勾选。 |
| C04 样品描述表格核对 | `backend/app/rules/report/c04_sample_description.py` | `backend/tests/rules/report/test_c04_sample_description.py` | 可标记完成 | 已实现部件名称、规格型号、序列号批号、生产日期、失效日期五字段比对；支持 LOT/SN/MFG/MFD/EXP，同名多行 identity 匹配，`/` 和空白等价规则，备注“本次检测未使用”降级 WARN。找不到匹配中文标签当前为 WARN，符合待确认口径。仍建议后续补真实 extractor fixture。 |
| C05 照片覆盖 | `backend/app/rules/report/c05_photo_coverage.py` | `backend/tests/rules/report/test_c05_photo_coverage.py` | 部分完成，需要补测试 | 已实现 caption 主体名提取、编号/方位/类别词清理、允许连接符匹配、未使用部件跳过、中文标签 caption 不计入普通照片、低置信 WARN。缺口：同名多部件是否每个都需要照片仍未确认，测试未覆盖同名多行照片覆盖策略；真实旧 caption 样例覆盖仍偏少。 |
| C06 中文标签覆盖 | `backend/app/rules/report/c06_label_coverage.py` | `backend/tests/rules/report/test_c06_label_coverage.py` | 可标记完成 | 已实现中文标签关键词、非空字段联合键、同名多行区分、普通照片不误判、未使用部件跳过、低置信 WARN。规则只做覆盖，不做字段值比对，边界符合 AGENTS.md。 |
| C07 单项结论逻辑 | `backend/app/rules/report/c07_item_conclusion.py` | `backend/tests/rules/report/test_c07_item_conclusion.py` | 部分完成，需要补测试 | 已实现按序号聚合、`续X` 归并、任一不符合优先、全部 `/`/`——`/空白期望 `/`、非空数字/文本期望符合，并输出 ERROR Finding。缺口：`known-requirements.md` 和 `spec-code-test-gaps.md` 提到的“无菌生长”语境没有被确定性规则覆盖；空白检验结果由 C07 推导 `/` 是否最终确认仍需人工裁决。 |
| C08 非空字段 | `backend/app/rules/report/c08_non_empty.py` | `backend/tests/rules/report/test_c08_non_empty.py`、`test_c08_non_empty_fields.py` | 可标记完成 | 已实现检验结果、单项结论、备注逐字段非空；`/` 和 `——` 视为非空占位符；合并单元格继承/首行为空、续表行、空序号不归 C08 均有测试。`c08_non_empty_fields.py` 是兼容 shim，不是第二套业务规则。 |
| C09 序号连续性 | `backend/app/rules/report/c09_sequence.py` | `backend/tests/rules/report/test_c09_sequence.py` | 可标记完成 | 已实现从 1 开始、跳号、重复普通序号、空白序号、`续X` 不作为普通重复、续号引用不存在、跨页连续/跳号。支持全角阿拉伯数字；`续：X`、`续表X`、中文数字仍是待确认扩展。 |
| C10 续表标记 | `backend/app/rules/report/c10_continuation.py` | `backend/tests/rules/report/test_c10_continuation.py` | 部分完成，需要人工确认 | 已实现新页首行续表标记、非首行续字错误、续号与上一页末尾不一致、缺 page/row context 时 WARN。缺口：模型没有显式“上一页末尾未完成”字段，当前主要通过“新页首行普通序号等于上一页尾号”推断；真实 extractor 是否能稳定提供该结构还需验收。 |
| C11 页码连续性 | `backend/app/rules/report/c11_page_number.py` | `backend/tests/rules/report/test_c11_page_number.py` | 可标记完成 | 已实现第三页起内部页码、Y 连续、跳号、重复、末页 Y=XXX、XXX 一致、缺失/无法解析 ERROR；支持多种文本格式，并可从 `ParsedPdf.pages` 文本构造证据。未强制右上角坐标、未强制 XXX 等于 PDF 第三页后实际页数，这两点在需求中仍待确认。 |

## C01-C11 任务状态建议

| docs/tasks.md 任务 | 当前建议 | 原因 |
| --- | --- | --- |
| T13 C01 | 可标记完成 | 核心规则、runner 注册、独立测试和 Finding 证据齐全。 |
| T14 C02 | 部分完成 | 三核心字段完成；委托方/委托方地址和缺失等级仍未裁决。 |
| T15 C03 | 部分完成 | 当前只比格式；若最终要求格式和值都比，还需实现值 mismatch。 |
| T16 C04 | 可标记完成 | 五字段、空值规则、未使用部件 WARN 和同名匹配均有覆盖。 |
| T17 C05 | 部分完成 | 缺同名多部件照片覆盖口径和真实 caption fixture。 |
| T18 C06 | 可标记完成 | 中文标签覆盖职责清晰，联合键和同名多行有测试。 |
| T19 C07 | 部分完成 | 主逻辑完成；无菌语境和空白结果最终口径仍需确认。 |
| T20 C08 | 可标记完成 | 必填字段、占位符、合并单元格、续表行均覆盖。 |
| T21 C09 | 可标记完成 | 连续性、重复、空白、续号引用均覆盖。 |
| T22 C10 | 部分完成 | 续表位置规则完成；跨页“未完成”结构字段仍需验收。 |
| T23 C11 | 可标记完成 | 页码解析和连续性校验均有测试；坐标口径待确认但不阻塞当前规则。 |
| T24 ReportRuleRunner | 可标记完成 | `default_report_rules()` 注册 C01-C11，runner 汇总和单规则异常隔离有测试。 |
| T25 ReportCheckUseCase | 可标记完成/需端到端样本补强 | usecase 已保存、解析、抽取、运行规则并写任务结果；当前测试用 fake parser/extractor，真实 PDF 端到端可作为后续验收增强。 |

## PTR 审计

| 模块 | 实现文件 | 测试文件 | 状态建议 | 审计结论 |
| --- | --- | --- | --- | --- |
| PTR domain | `backend/app/domain/ptr.py` | `backend/tests/domain/test_ptr_models.py` | 可标记完成 | 已有 `PTRClauseNumber`、`PTRClause`、`PTRDocument`、`PTRTable`、`TableReference`、scope/taxonomy/type；支持层级、父子、表引用、表查询。 |
| PTR extractor | `backend/app/infrastructure/ptr/ptr_extractor.py` | `backend/tests/infrastructure/ptr/test_ptr_extractor.py`、`test_ptr_extractor_multidim.py` | 可标记完成 | 按编号定位第 2 章，不依赖固定标题；抽取层级、表引用、scope_type；支持跨页续表合并和拒绝。实现位置在 infrastructure，而不是 docs/tasks.md 中写的 application 路径，符合当前架构分层。 |
| Scope filter | `backend/app/rules/ptr/scope_filter.py` | `backend/tests/rules/ptr/test_scope_filter.py` | 部分完成 | 已支持范围、exact selector、括号排除、scope_type 排除、外部标准排除、report clause present 兜底。它返回 `ScopeFilterResult` 和 decisions，不直接输出 `Finding`；usecase 包装为 `PTR_SCOPE` CheckResult 且当前总是 PASS。若要求 scope 差异也以 Finding 暴露，还需补实现。 |
| Clause compare | `backend/app/rules/ptr/clause_text_compare.py` | `backend/tests/rules/ptr/test_clause_text_compare.py` | 部分完成 | 已输出 `PTR_CLAUSE` Finding，支持缺失、正文 mismatch、diff fragments、`≥/≤` 与 `>/<` 差异。缺口：额外条款、2.4 特定 warning suppression 的审计化、旧 comparator 中 numeric/bundle 语义仍在 `test-migration-matrix.md` 标为待补齐。 |
| Table reference compare | `backend/app/rules/ptr/table_reference_compare.py` | `backend/tests/rules/ptr/test_table_reference_compare.py` | 部分完成 | 已覆盖 `见表 X` 的缺表和重复候选 WARN，并输出统一 Finding。缺口：仅检查 PTR 文档内引用表存在性/歧义，未负责 PTR 表与报告表的参数差异。 |
| Parameter table compare | `backend/app/rules/ptr/parameter_compare.py` | `backend/tests/rules/ptr/test_parameter_compare.py`、`backend/tests/application/test_ptr_compare_usecase.py` | 部分完成，已接入 usecase | 已有参数缺失、值不一致、单位不一致逻辑，输出 `PTR_TABLE` Finding；多维 sibling 记录有测试。2026-06-15 已接入 `PTRCompareUseCase`，参数 finding 会进入最终 `PTR_TABLE` CheckResult。报告侧 `CanonicalTable` 已可由 `ReportParameterTableExtractor` 从 `ParsedPdf` 表格生成。剩余缺口：候选表选择、条件/允许误差差异、diff 结构和旧 PTR 表格深层语义仍需补强。 |
| CanonicalTable / TableNormalizer | `backend/app/domain/table.py`、`backend/app/infrastructure/table/table_normalizer.py`、`table_semantics.py` | `backend/tests/domain/test_table_models.py`、`backend/tests/infrastructure/table/test_table_normalizer.py`、`test_table_semantics.py` | 可标记完成 | 已有 CanonicalTable、ParameterRecord、TableCell、ColumnPath、表头路径、角色识别、维度 fill-down、续表诊断、参数记录构建。 |
| PTRCompareUseCase | `backend/app/application/ptr_compare_usecase.py` | `backend/tests/application/test_ptr_compare_usecase.py`、`backend/tests/api/test_api_ptr_compare_e2e.py` | 部分完成，参数表链路和受控 API e2e 已接入 | 已完成双文件保存、PDF parse、PTR/report extraction、scope filter、clause compare、table reference compare、parameter compare、任务结果聚合。新增测试覆盖值不一致、单位不一致、缺失参数、缺表/歧义跳过参数比对、一致表无 ERROR，以及报告 `ParsedPdf` 表格经 `ReportParameterTableExtractor` 进入 `ReportDocument.metadata["canonical_tables"]` 后参与参数比对。API 级受控 fixture/golden 已覆盖 multipart 上传、任务状态、任务结果、JSON export、条款差异、表引用缺失和三类 parameter finding。剩余缺口：真实可公开样本端到端验收、scope finding 暴露和 diff 结构。 |

## PTR 任务状态建议

| docs/tasks.md 任务 | 当前建议 | 原因 |
| --- | --- | --- |
| T26 PTRExtractor | 可标记完成 | 第 2 章编号定位、层级、表引用、分类和续表已有实现与测试。 |
| T27 ClauseComparator | 部分完成 | scope 和 clause text 已有核心能力；额外条款、2.4 suppression 审计化、旧 comparator 深水区仍需补。 |
| T28 TableNormalizer / CanonicalTable | 可标记完成 | domain 和 infrastructure 实现及测试较完整。 |
| T29 TableComparator | 部分完成 | table reference 与 parameter compare 均存在，参数比对已进入 usecase，报告侧 canonical 表已由 extractor 生成；候选表选择、条件/允许误差差异、diff 结构和旧 PTR 表格深层语义仍未完全闭环。 |
| T30 PTRCompareUseCase | 部分完成/需真实样本与深层语义验收 | 双文件任务闭环存在，PTR 表格参数比对已进入结果，报告 `ParsedPdf` 表格可进入参数比对；受控 API fixture/golden 已证明上传、结果和 JSON export 可携带条款、表引用和参数 finding。scope finding 暴露、真实可公开样本端到端和 diff 结构仍需补强。 |

## 旧项目语义覆盖情况

根据 `docs/test-migration-matrix.md`：

- 报告规则测试多数为“重写”，不是旧测试原样迁移；这符合新架构边界，但真实旧样本 Golden 覆盖仍需补强。
- PTR comparator 和 table comparator 明确标为“重写 / 待补齐”；高级 numeric semantic、segmented threshold、real-report table patterns 尚未完整迁移。
- 旧 Codex/LLM 作为最终 judge 的断言已废弃；新规则以确定性 Finding 为主，这符合 AGENTS.md，但也意味着部分旧语义需要通过新 fixture/golden 重新证明。

## 风险清单

1. C02 字段范围未裁决：委托方、委托方地址目前不作为 ERROR/WARN。
2. C03 日期值是否比较未裁决：当前只比格式。
3. C05 同名多部件照片覆盖口径未裁决。
4. C07 “无菌生长”等语义未进入确定性规则。
5. C10 依赖 page/row 和重复序号推断跨页续表，缺少显式“上一页未完成”模型字段。
6. C11 未校验右上角坐标来源，未校验 XXX 与 PDF 剩余页数一致。
7. PTR parameter compare 已接入 `PTRCompareUseCase`，报告侧 canonical 表也已由 extractor 接入，双文件上传 API 已有受控 fixture/golden 保护；候选选择、diff 结构和真实可公开样本端到端覆盖仍需补强。
8. `backend/app/rules/ptr/__init__.py` 注释陈旧，容易误导后续迁移状态判断。

## 推荐下一任务

推荐下一步不要批量勾选 `docs/tasks.md`，而是拆成小任务继续收敛剩余风险：

1. 继续补 T27/T29 的旧 PTR 深层语义：numeric semantic、segmented threshold、条件差异、允许误差差异、diff 结构和真实报告表候选选择。
2. 在受控 API fixture/golden 之外，补真实可公开样本或更接近生产 PDF 的端到端验收，继续证明双文件上传路径能稳定产出 PTR 表格参数 finding。
3. 继续处理 C02/C03/C05/C07/C10 的业务口径确认，不要在未裁决前批量标记完成。
