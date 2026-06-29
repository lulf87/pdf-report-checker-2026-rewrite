# C08/C10/C07 Noise Reduction Plan

更新时间：2026-06-23

本文记录 T-QUALITY-01 的设计结论。范围仅限文档设计，不修改业务代码、不修改规则、不修改前端、不修改旧项目目录、不调用真实 Codex。

真实样本：

- `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf`

本次真实结果摘要来自用户提供的本地业务验收结果：

- `deterministic_findings_count: 5194`
- `C08: 4894`
- `C10: 130`
- `C07: 72`
- `C04: 70`
- `C05: 14`
- `C06: 12`
- Codex review 已对 1 条 C07 返回 `succeeded / confirm / high`

## 一、当前样本噪声分析

### C08 为什么会产生 4894 条

当前 `backend/app/rules/report/c08_non_empty.py` 对 `ReportDocument.inspection_items` 逐 `InspectionItem`、逐必填字段检查：

- `检验结果`
- `单项结论`
- `备注`

这意味着一个物理行最多可产生 3 条 C08 finding。真实报告是长检验报告，检验项目表包含大量跨行、跨页、合并单元格和“续 X”结构。抽取器 `backend/app/infrastructure/report/inspection_table_extractor.py` 明确保留“一源行一 item”的结构，并把空序号续行也作为 `InspectionItem` 输出，以便后续规则自行归组。

该设计对可追溯性有利，但 C08 直接消费 physical rows 时会放大噪声：

- 合并单元格如果未能稳定继承到每个子行，子行会被当成字段为空。
- 同一序号的多行检验项目中，只有首行或末行携带单项结论/备注时，其余子行会重复报空。
- `续 X` 跨页行本质属于同一检验项目，但目前 C08 会像普通行一样逐行报错。
- 测试中已有 `test_c08_checks_continuation_rows_instead_of_skipping_them` 锁定“续表行也检查”的旧口径；真实长报告表明该口径需要升级为 group-level effective field 判断。

因此 4894 条更像“物理行字段空白计数”，不等于 4894 个业务问题。

### C10 为什么会产生 130 条

当前 `backend/app/rules/report/c10_continuation.py` 按页码和页内行号排序后做两类判断：

- 新页第一行是否应出现 `续 X`。
- 本页第二行或更后行是否错误出现 `续 X`。

现有实现使用上一页最后一行与当前页第一行比较，但没有一个显式的 item group 边界模型来表达“上一页末尾这个序号是否尚未完成”以及“当前页哪些行实际属于同一序号”。在真实长表中，跨页续表往往伴随：

- 一页末尾拆到下一页的同序号多行。
- `续 X` 行之后还有多个同序号子行。
- 版式抽取把页内首个可见表格行、表头行、空白行、续行的 row index 表达得不够稳定。
- 某些重复 `续 X` 标记可能是同一 page boundary 问题的多个子行表现。

因此 130 条 C10 finding 很可能包含“同一跨页边界或同一序号被重复报错”的情况。C10 应从 physical row 检查升级为 item group 的 page boundary 检查。

### C07 为什么需要按序号 group 判断

当前 `backend/app/rules/report/c07_item_conclusion.py` 已经按序号归组，并支持 `续5` / `续 5` 归并到原序号。该方向是正确的，因为单项结论不是每个物理行的独立结论，而是同一检验项目序号的业务结论。

C07 的判断应基于同一 `item_no` 的所有检验结果：

- 任一有效结果为“不符合要求”时，期望单项结论为“不符合”。
- 所有结果均为 `/`、`——` 或空白占位时，期望为 `/`。
- 存在符合要求、数值或其他有效非空结果时，期望为“符合”。

真实验收中 Codex 对 1 条 C07 返回 `confirm / high`，说明 C07 的业务方向可成立：序号 3 的检验结果为“符合要求”，单项结论为“/”，rule context 期望“符合”，因此支持规则初判。

但 C07 仍应进一步使用统一 `InspectionItemGroup`：

- 跨页续表时聚合所有行。
- 使用合并单元格继承后的有效字段。
- 不因单个物理行的 `/` 或空白直接判错。
- 将 group evidence 提供给 Codex audit，而不是只给单行证据。

### C04/C05/C06 与 OCR/label/caption 的关系

C04/C05/C06 与样品描述、照片 caption、中文标签 OCR 的关系如下：

- C04 做样品描述表格字段与中文标签 OCR 字段一致性。
- C05 做样品描述部件是否有对应非标签照片 caption。
- C06 做样品描述部件是否有中文标签 caption/OCR 覆盖。

现有实现已经有一些降噪基础：

- C05/C06 会跳过备注包含“本次检测未使用”的部件。
- C04 对“本次检测未使用”部件的字段不一致降级为 WARN。
- C04 找不到匹配中文标签 OCR 时输出 WARN。
- C05/C06 对低置信 caption/OCR 有 WARN 路径。

但真实样本中 C04/C05/C06 仍有数量不小的 finding。后续应进一步明确 OCR gating：

- label caption 存在但 OCR 字段不足时，不应直接按字段缺失输出 ERROR。
- 缺 OCR、低置信 OCR、caption 能证明标签存在但字段无法抽取时，应输出 WARN / NEEDS_REVIEW。
- 复杂图文判断交给 Codex/VLM runtime auditor 复核，而不是让 deterministic rule 把 OCR 缺失当成确定错误。

## 二、InspectionItemGroup 设计

建议新增稳定领域模型或应用层值对象 `InspectionItemGroup`，作为 C07/C08/C10 的共同输入。它不应放在 router 或前端中，也不应混入 PDF parser 的规则判断。

建议字段：

| 字段 | 说明 |
| --- | --- |
| `item_no` | 归一化序号，例如 `5`。`续5`、`续 5`、同序号普通行归到同一个 group。 |
| `display_item_no` | 优先保留首个源序号文本，例如 `5`；续页可记录 `续5` 为 marker。 |
| `rows` | 原始 `InspectionItem` 列表，保留物理行顺序。 |
| `pages` | 该 group 覆盖的页码集合，按出现顺序。 |
| `continuation_markers` | 每个 `续 X` 或 logical continuation 的页码、行号、原文。 |
| `effective_test_results` | 合并后用于 C07/C08 的检验结果列表，排除纯结构行，保留 `/`、`——` 等占位符。 |
| `effective_single_conclusion` | group-level 单项结论，按可信来源选择，例如首个非空结论或显式结论单元格。 |
| `effective_remark` | group-level 备注，按非空继承和合并单元格来源选择。 |
| `inherited_merged_fields` | 记录哪些字段来自合并单元格继承，包括 anchor row、target rows、provenance。 |
| `source_evidence` | group evidence，包含所有相关行的页码、行号、字段值、field provenance、原始 evidence。 |
| `diagnostics` | 无法可靠归组、跨页边界不确定、字段继承冲突等非 finding 诊断。 |

构建原则：

- 只做结构归组和有效字段聚合，不做 C07/C08/C10 的最终业务判断。
- 保留所有源行，保证 finding 能追溯回原 PDF 行。
- 空序号但有 payload 的行，如果跟随有效序号并满足 continuation 特征，应归入当前 group。
- `is_continuation=True`、`sequence_raw=续X`、`metadata.logical_continuation=True` 都应成为归组信号。
- `field_provenance=merge_inferred` 表明该字段可继承，不应作为 physical row 空白重复报错。

## 三、C08 新策略

C08 应从 physical row-level 改为 group-level effective field 判断。

新策略：

1. 不再逐 physical row、逐字段直接输出 finding。
2. 基于 `InspectionItemGroup` 判断每个序号的有效字段：
   - `effective_test_results`
   - `effective_single_conclusion`
   - `effective_remark`
3. `/` 和 `——` 继续视为非空占位符。
4. 合并单元格空白子行应继承 anchor 或 group effective value。
5. 如果 group 内确实没有有效值，再输出 grouped finding。
6. 每个 group/字段最多一条 C08 finding，避免同一业务问题按子行重复报错。
7. 原始空白明细放入 `CheckResult.diagnostics` 或 finding metadata，不作为多条 ERROR 展示。

建议 finding metadata：

- `item_no`
- `field_key`
- `field_name`
- `group_row_count`
- `pages`
- `empty_physical_rows`
- `inherited_rows`
- `source_row_locations`

建议错误码：

- 保留 `INSPECTION_FIELD_EMPTY` 表示 group-level 确认空。
- 保留或收敛 `INSPECTION_MERGED_FIELD_EMPTY`，只在合并 anchor 自身为空且 group 无有效值时输出。
- 对结构不确定的情况使用 WARN，例如 `INSPECTION_GROUP_FIELD_UNCERTAIN`。

预期效果：

- C08 finding 数量应从“物理行空字段数”降为“序号组缺有效字段数”。
- 对 QW2025-2795 Draft.pdf，C08 raw count 应显著下降。

实现与验收更新（2026-06-23）：

- T-QUALITY-03 已将 C08 改为消费 `InspectionItemGroup` 的 group-level effective fields，真实样本 C08 从 4894 降到 140。
- T-QUALITY-03B 修复“标准要求正文被当作 item_no”的污染问题后，真实样本 C08 降到 2。
- T-QUALITY-03C 修复 item 126 右侧 `符合 /` 中备注 `/` 占位符丢失后，用户重新验收 QW2025-2795 Draft.pdf，最新 `C08 count: 0`。
- C08 group-level 降噪闭环完成；后续噪声收敛重点转向 C10 page-boundary 与 C07 group-level。

## 四、C10 新策略

C10 应只检查跨页 item group 的 page boundary。

新策略：

1. 先构建 `InspectionItemGroup`，识别每个序号覆盖哪些页。
2. 只对跨页 group 检查 page boundary。
3. 每页/每序号最多一条 finding。
4. `续 X` 只应出现在新页第一条相关行：
   - “相关行”是属于该 `item_no` group 的第一条行。
   - 不应简单等同于整页所有表格行的第一行，因为页首可能有表头、空白行或上一组尾部。
5. 如果同一 page boundary 有多个子行表现出同一错误，只输出一个 grouped finding。
6. 如果页码、row index 或 group 边界不足以确认，输出 WARN / diagnostics，不批量输出 ERROR。

建议 finding metadata：

- `item_no`
- `previous_page`
- `current_page`
- `boundary_rows`
- `expected_marker`
- `actual_marker`
- `is_first_related_row_on_page`
- `duplicate_suppressed_count`

建议错误码：

- `CONTINUATION_MARK_ERROR_001`：跨页 continuation 缺少 `续 X`。
- `CONTINUATION_MARK_ERROR_002`：`续 X` 不在新页第一条相关行。
- `CONTINUATION_MARK_MISMATCH`：`续 X` 与 group item_no 不一致。
- `CONTINUATION_BOUNDARY_UNCERTAIN`：结构证据不足，WARN。

预期效果：

- C10 duplicate finding 应显著下降。
- 对 QW2025-2795 Draft.pdf，不应再对同一跨页序号的每个子行重复报错。

实现与验收更新（2026-06-23）：

- T-QUALITY-04 已将 C10 切换为基于 `InspectionItemGroup` 的 group page-boundary 判断。
- 用户重新验收 QW2025-2795 Draft.pdf 后，最新 `C10 unique count: 0`，`by_code={}`、`by_boundary=[]`、`by_item=[]`、`by_page=[]`。
- C10 已从此前 `130` 条 `CONTINUATION_MARK_MISMATCH` 降到 0，page-boundary 降噪闭环完成。
- C08 同步保持 `C08 count: 0`；后续噪声收敛重点转向 T-QUALITY-05：C07 group-level 重构。

## 五、C07 新策略

C07 应继续按序号 group 判断，并切换为消费 `InspectionItemGroup`。

新策略：

1. 使用同一 `item_no` 的所有结果推导 expected conclusion。
2. 跨页续表合并到同一个 group。
3. 使用合并继承后的 `effective_test_results` 和 `effective_single_conclusion`。
4. 不以单个物理行的 `/` 或空白直接判错。
5. 只有 group-level actual conclusion 与 expected conclusion 不一致时输出 finding。
6. 如果 group 内检验结果全为空，C07 可记录 diagnostics，由 C08 负责必填字段；是否输出 C07 WARN 需后续确认。
7. Codex audit 使用 group evidence，包括：
   - group summary
   - 所有 result tokens
   - authoritative conclusion
   - source rows
   - page boundary / continuation markers

现有 C07 测试已覆盖同序号多行、`续5` 归并和 `/`、`——`、空白推导。后续重构应保持这些测试通过，同时新增真实 extractor fixture 或更接近真实 PDF 的合成 group fixture。

实现与验收更新（2026-06-23）：

- T-QUALITY-05 已将 C07 切换为消费 `InspectionItemGroup` 的 `effective_test_results`、`effective_single_conclusion`、`pages`、`source_evidence` 和 `continuation_markers`。
- C07 保留既有 finding code 和 expected conclusion 推导优先级；每个 `item_no` 最多输出一条 group-level mismatch finding。
- Finding metadata 现在包含 `expected_conclusion`、`actual_conclusion`、`effective_test_results`、`group_row_count`、`pages`、`continuation_markers`、`source_rows`、`result_summary`、`reasoning_basis` 和 `suppressed_physical_row_count`。
- `ReportCodexEvidenceBuilder` 已为 C07 `inspection_item` target 输出 group-level `inspection_item_group` evidence，Codex audit 后续可直接使用 grouped evidence，而不是单个 physical row。
- 真实样本验收已完成：首次 8000 端口运行命中旧后端进程，不作为有效验收；随后使用 `BASE_URL=http://127.0.0.1:8011 BACKEND_PORT=8011` 启动当前工作区代码重跑，QW2025-2795 Draft.pdf 最新 `C07=12`、`C08=0`、`C10=0`。
- T-QUALITY-05 主目标达成：C07 从 72 降到 12，且每个 item_no 最多 1 条。剩余 12 条拆为 T-QUALITY-05B：item 3 actual conclusion 冲突选择、item 59 复杂矩阵表 extractor/列映射、其余 `/ -> 符合` 的 effective result 聚合或业务口径确认。

## 六、C04/C05/C06 后续策略

C04/C05/C06 的后续降噪重点不是 item group，而是 OCR/caption gating 和证据等级。

建议：

1. “本次检测未使用”部件继续跳过 C05/C06 覆盖性规则；C04 字段一致性建议默认 WARN 或跳过，最终口径需确认。
2. label caption 存在但 OCR 字段不足时，不应直接 ERROR：
   - C06 可认为“标签覆盖存在，但 OCR 字段不足”，输出 WARN / NEEDS_REVIEW。
   - C04 不应把缺 OCR 字段直接等同于标签字段为空。
3. 缺 OCR、OCR 低置信、OCR 与 caption 不一致时，输出 WARN / NEEDS_REVIEW，并保留 candidate evidence。
4. deterministic rule 只做候选 finding 和 evidence building。
5. 图文语义、caption 与部件是否同一对象、OCR 缺字容错等复杂判断交给受控审核链路处理；VLM 只能作为提取增强或证据补充，最终复验路径以本机 Codex CLI 为准。
6. T-CODEX-MANDATORY-01 后，规则 finding 是 candidate；Codex review 是 mandatory 审核意见和最终复验依据，但不删除原始 candidate finding 的审计痕迹。

建议新增元数据：

- `ocr_available`
- `label_caption_available`
- `label_image_available`
- `ocr_confidence`
- `evidence_completeness`
- `needs_codex_review`

实现与验收更新（2026-06-25）：

- T-CODEX-EVIDENCE-04 已先补强 C04 Codex evidence 的标签证据分层：`label_caption_candidate`、`matched_label_caption`、`label_page_number`、`label_image_ref`、`label_crop_ref`、`matched_label_text`、`matched_label_fields`、`matched_label_field_confidence`、`matched_label_ocr_source`、`unmatched_label_ocr_candidates` 和 `evidence_can_verify_label_content`。
- caption 能证明中文标签样张存在，但不能证明字段完整；caption-only、empty OCR 或 unrelated OCR 均不应让 `evidence_can_verify_label_content=true`。
- 如果 matched label fields 属于当前 component 且字段与样品描述一致，Codex 可 refute C04 candidate；如果 matched fields 缺失或冲突且证据可验证，Codex confirm 才可进入 confirmed final issue。
- T-CODEX-EVIDENCE-04 实现阶段未运行真实 Codex CLI；后续已通过 T-CODEX-EVIDENCE-04B 的 C04 targeted validation 补验 metadata 语义修复。
- T-CODEX-EVIDENCE-04B 已修正 04 后真实 C04 targeted validation 暴露的 metadata 假阳性：照片页/PDF page text 拆为 `matched_label_page_text`，真正标签本体 OCR 拆为 `matched_label_ocr_text`，`matched_label_text` 仅作为 OCR text 兼容别名；没有 `matched_label_ocr_text` 或 `matched_label_fields` 时，`evidence_can_verify_label_content=false`。
- T-CODEX-EVIDENCE-04B 同步修正 caption selector：完整 subject、型号、`30m`、`可选`、`连接线缆` 等特异 token 加权，sample-row-14 优先匹配 `№22 触摸屏连接线缆（30m）（可选） 中文标签样张`，分差不足时记录 `LABEL_CAPTION_MATCH_AMBIGUOUS` 而不设置 matched caption。
- T-CODEX-EVIDENCE-04B 后用户真实 C04 targeted validation `4ec18d39-7dab-4478-b6c0-d6bc464fd2e7` 已通过：`final_audit_status=needs_manual_review`、`codex_reviews_count=35`、`confirmed_errors_count=0`、`refuted_findings_count=7`、`manual_review_required_count=28`、`out_of_scope_findings_count=16`、`codex_runtime_failure_count=0`；`evidence_has_matched_label_ocr_count` 与 `evidence_can_verify_label_content_count` 均从旧的 `28` 降为 `0`，证明 page text 不再被误记为可验证 label OCR。
- 04B 后 C04 extract 显示 `has_matching_label_caption_count=35`、`has_matched_label_image_count=31`，但 `has_matched_label_crop_count=0`、`has_matched_label_ocr_count=0`、`has_matched_structured_fields_count=0`、`can_verify_label_content_count=0`；后续应进入 T-CODEX-EVIDENCE-05，补真实 label crop / OCR / VLM evidence。
- 后续展示/导出还应标准化 C04 metadata：`component_id`、`component_name`、`sample_field_key`、`sample_field_value`，避免直接依赖不稳定的 `component_name` / `sample_description_row` 文本。
- T-CODEX-EVIDENCE-05 已实现第一段视觉证据链：matched label caption 可从上传后的 source PDF 渲染为受控 workspace 内 `items/*.png`，并通过 Codex CLI `--image` 进入视觉审核；真实 C04 targeted visual validation `c1f421db-4757-4041-8b19-c88b8835a941` 已通过，35 条 C04 candidate 全部 `refuted`、`manual_review_required_count=0`。
- T-CODEX-EVIDENCE-05B 后 full mandatory audit `1958c184-567f-4c56-aaac-4a8c45913d1c` 已验证 C04 visual label audit 在 full audit 中生效：C04/C05/C06/C09 全部 `refuted`，当前没有 confirmed final error，剩余 12 条 `manual_review_required` 均为 C07 table/row extraction 复核项。
- T-CODEX-EVIDENCE-06A 已完成 C07 table visual evidence 的底层几何准备：PyMuPDF table `cells` 坐标进入 `PdfTable.metadata["cell_bboxes"]`，inspection item 在存在 cell bbox 时写入 `metadata.visual_geometry`，包含 table bbox、row bbox 和 result/conclusion/remark 等字段 bbox。该阶段尚未生成 C07 图片证据，也未接入 Codex CLI image input。
- T-CODEX-EVIDENCE-06B 已新增 `C07VisualEvidenceBuilder`，可将 06A 的 `visual_geometry` 转成 C07 page/table/item group/result/conclusion/remark 的 `EvidenceItem(source_type=IMAGE)` 与 target metadata；无 bbox 时降级为 page-only visual evidence，无 `source_pdf_path` 时只记录 `source_pdf_path_missing` 而不生成 image items；item 59 / complex matrix target 使用 `complex_matrix_table` 视觉模式。本阶段仍未修改 C07 prompt/schema/finalization，也未运行真实 Codex CLI。
- T-CODEX-EVIDENCE-06C 已补齐 C07 image evidence handoff 基础设施：`EvidencePackageWriter` 可将 C07 page/table/item group/result/conclusion/remark image items materialize 为 workspace-local PNG，`CodexAuditService` 可收集 C07 PNG paths 并传给 runner，`CodexCliRunner` 命令构造会传多个 `--image` 参数，`PromptBuilder` 已加入 C07 visual review instructions。本阶段仍未修改 output schema/finalization，也未运行真实 Codex CLI；下一步应做 C07 targeted visual audit 真实验收。
- T-CODEX-EVIDENCE-06D 真实 C07 targeted visual audit 已通过：结果文件 `runtime/codex_audit_local_e2e/2e7bbb93-3e7b-4477-8a5f-b1b25487fef0.result.json` 中 `audit_scope=targeted`、`included_check_ids=["C07"]`、`confirmed_errors_count=0`、`refuted_findings_count=11`、`manual_review_required_count=1`、`codex_runtime_failure_count=0`。C07 visual evidence 将 item 3、27、33、41、72、94、121、131、142、149、151 refute，唯一剩余 item 59 为 `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX` / `complex_matrix_table`，应进入 specialized matrix review。
- T-CODEX-EVIDENCE-06 full mandatory audit 复验已通过：结果文件 `runtime/codex_audit_local_e2e/8e23d5bc-64f5-43c1-a0c5-2e02597840f6.result.json` 中 `audit_scope=full`、`full_audit=true`、`confirmed_errors_count=0`、`refuted_findings_count=50`、`manual_review_required_count=1`、`codex_runtime_failure_count=0`。C04/C05/C06/C09 全部 refuted，C07 12 条中 11 条 refuted，当时全量唯一剩余为 C07 item 33 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN`。item 33 的视觉表格显示首行检验结果为“——”，其下续行结果列可见“符合要求”，结构化结果仅保留“——”确有遗漏；随后进入 T-CODEX-EVIDENCE-06E，比较 targeted C07 与 full audit 的 evidence/prompt/image refs 差异以提升稳定 refute。
- T-CODEX-EVIDENCE-06E 已完成代码侧 closeout 并通过真实 C07 targeted validation：诊断 helper 证明 targeted 与 full 的 item 33 `allowed_evidence_refs`、`c07_visual_evidence`、materialized image files 和 visual review mode 一致，旧 prompt 缺少 extraction-uncertain 的明确 refute 条件导致 verdict 漂移；修复 C07 item group crop 的续行字段 bbox union，并明确 prompt 中 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` 在视觉证据足以判断结论合理时应 `refute`。用户重跑 C07 targeted validation `a39b2841-e44d-4efd-a004-ae3147a2c1d6` 已通过：`final_audit_status=passed`、12 条 C07 candidate 全部 `refuted`、`confirmed_errors_count=0`、`manual_review_required_count=0`、`codex_runtime_failure_count=0`；item 33 residual manual review 已收口。
- T-CODEX-EVIDENCE-06E 后 full mandatory audit 复验 `bf36101c-71a4-4f69-9df9-907ced1000cb` 已完成：`audit_scope=full`、`full_audit=true`、`final_audit_status=needs_manual_review`、`codex_reviews_count=57`、`candidate_findings_count=51`、`confirmed_errors_count=0`、`refuted_findings_count=50`、`manual_review_required_count=1`、`codex_runtime_failure_count=0`。C04/C05/C06/C09 已全部 refuted，C07 普通视觉复核项已基本收口；唯一剩余是 C07 item 59 `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`，Codex verdict 为 `uncertain/medium`，原因是 8.7 漏电流多页复杂矩阵的跨页续表与矩阵列映射仍需专门判读。保留 `manual_review_required` 符合安全口径，不应通过 finalization 强行 passed；下一步应做 T-CODEX-EVIDENCE-07 specialized matrix review。
- T-CODEX-EVIDENCE-07 已完成规划文档：`docs/superpowers/plans/2026-06-28-t-codex-evidence-07-c07-complex-matrix-specialized-review.md`。规划覆盖 item 59 矩阵结构识别目标、full page/matrix table/header/result/conclusion/continuation visual evidence、item group rows/page numbers/table headers/condition columns/measured values/placeholder cells/conclusion candidates structured evidence、matrix-first prompt 设计、synthetic fixture / crop evidence / prompt contract 自动化测试和 targeted item 59 后 full audit 的真实验收顺序。本轮只规划，不实现代码，不修改 finalization，不运行真实 Codex。
- T-CODEX-EVIDENCE-07A 已完成 item 59 complex matrix specialized evidence builder contract：新增 `C07ComplexMatrixEvidenceBuilder`，将 complex matrix target 扩展为 `c07_complex_matrix_evidence`，包含 matrix page/table/header/body/result/conclusion/continuation image refs 和 structured matrix hints；普通 C07 不携带该 metadata。本阶段只构建 EvidenceItem refs 和 fallback reasons，不修改 prompt/schema/finalization，不运行真实 Codex。
- T-CODEX-EVIDENCE-07B 已完成 complex matrix materialization / handoff / prompt contract：matrix image EvidenceItem 可 materialize 为 workspace-local PNG，`CodexAuditService` 可收集 matrix PNG paths，`CodexCliRunner` 会以 `--image items/...` 传递多张 matrix 图片，PromptBuilder 已加入只对 complex matrix target 生效的 matrix-first instructions。本阶段仍不修改 output schema/finalization，也未运行真实 Codex；item 59 的最终口径仍需 07C targeted validation。
- T-CODEX-EVIDENCE-07C 与最终 full audit 复验已完成：targeted item 59 结果文件 `runtime/codex_audit_local_e2e/4b15adbb-6e4e-4a66-99e7-9170843b3646.result.json` 中 complex matrix candidate 被 Codex `refute/high`，final status 为 `refuted`；随后 full mandatory audit `runtime/codex_audit_local_e2e/8e84b3e7-e079-4e6f-ac7f-b99348f18ffa.result.json` 达到 `final_audit_status=passed`，51 条 candidate 全部 `refuted`，`confirmed_errors_count=0`、`manual_review_required_count=0`、`codex_runtime_failure_count=0`。报告自检主线在真实样本 `QW2025-2795 Draft.pdf` 上已收敛到无 confirmed final error、无 manual review。

## 七、Finding 聚合模型

有两种可选路径。

### 方案 A：新增 FindingGroup

新增领域模型 `FindingGroup`，用于把多个 raw row diagnostics 与一个 grouped finding 关联。

优点：

- 前端可天然展示“1 个业务问题 + N 条明细”。
- 后续 C08/C10/C07、PTR 表格参数分组也可复用。

风险：

- 需要更新 API schema、前端类型、导出逻辑。
- 范围较大，不适合作为第一步。

### 方案 B：先使用 CheckResult.diagnostics / metadata

保持 `Finding` 模型不变，把 suppressed raw details 放入：

- `Finding.metadata.raw_rows`
- `Finding.metadata.suppressed_count`
- `CheckResult.metadata.groups`
- `CheckResult.diagnostics`

优点：

- 最小改动。
- 不破坏现有 API 和前端展示。
- 可先验证真实样本降噪效果。

风险：

- 前端若要优雅展示明细，需要后续约定 metadata schema。

建议先采用方案 B。等 C08/C10/C07 降噪稳定后，再评估是否需要 `FindingGroup`。

前端展示建议：

- 默认展示 grouped finding。
- 在 finding 详情中折叠展示 raw rows / suppressed rows。
- summary 中展示 `suppressed_count`，例如“已合并 37 条物理行明细”。
- diagnostics 默认折叠，不进入主错误列表。

## 八、测试计划

测试应覆盖合成 fixture 与真实报告样本两层。

### 合成 fixture

新增或更新以下测试：

- `InspectionItemGroup builder`：
  - 同序号多行归组。
  - `续5` / `续 5` 归并。
  - 空序号 payload 行跟随上一序号归组。
  - merge inferred 字段继承。
  - 跨页 group 的 pages 和 continuation markers。
- C08：
  - group 内子行空白但 group 有有效值时 PASS。
  - group 无有效检验结果时只输出 1 条 grouped finding。
  - `/` 和 `——` 仍视为非空。
  - raw empty rows 进入 metadata/diagnostics。
- C10：
  - 跨页同序号首个相关行缺 `续 X` 时只输出 1 条。
  - `续 X` 在第二条相关行时只输出 1 条。
  - 同一 page boundary 多个子行不重复报错。
  - 缺 page/row context 输出 WARN。
- C07：
  - 同序号所有结果共同推导 expected conclusion。
  - 跨页续表合并。
  - 单个物理行 `/` 不直接导致 group mismatch。
  - 现有 C07 单元测试继续通过。
- C04/C05/C06：
  - “本次检测未使用”跳过或 WARN 口径固定。
  - label caption 存在但 OCR 不足时输出 WARN / NEEDS_REVIEW。
  - 低置信 OCR 不直接 ERROR。

### 真实样本

使用 QW2025-2795 Draft.pdf 或从其结构抽取出的稳定 fixture。

验收目标：

- C08 raw count 应显著下降，不再以 4894 条 physical-row field empties 展示。
- C10 duplicate finding 应显著下降，不再以 130 条重复 page-boundary 问题展示。
- C07 group-level 判断不破坏现有测试，并继续能解释 Codex confirm 的 C07 案例。
- Codex audit 仍能基于 grouped evidence 工作，target 仍可被限流到单个 C07 或小批量 C02/C03/C04/C05/C06。

如果真实 PDF 解析结果不稳定，不应直接把完整 PDF 输出作为 Golden expected；应生成最小合成 fixture 或固定的 parsed table fixture。

## 九、分阶段实施任务

### T-QUALITY-02：InspectionItemGroup builder

- 新增 group builder 和测试。
- 不改变现有规则输出。
- 输出 group metadata、effective fields、source evidence 和 diagnostics。

### T-QUALITY-03：C08 group-level 重构

- C08 改为消费 `InspectionItemGroup`。
- 每个 group/field 最多一条 finding。
- raw row 明细进入 metadata/diagnostics。
- 更新现有 row-level 测试为 group-level 口径。

### T-QUALITY-04：C10 page-boundary 重构

- C10 改为基于 group page boundary。
- 每页/每序号最多一条 finding。
- 缺上下文时 WARN，不批量 ERROR。
- 新增真实跨页续表示例 fixture。

### T-QUALITY-05：C07 group-level 重构

- 已完成：C07 消费 `InspectionItemGroup` 的 effective results/conclusion。
- 已完成：保留现有推导优先级。
- 已完成：Codex evidence builder 使用 group evidence。
- 已验收：QW2025-2795 Draft.pdf 上 C07 从 72 降到 12，C08 保持 0，C10 保持 0。

### T-QUALITY-05B：C07 residual mismatch cleanup

- 分析并修复 item 3 的 actual conclusion 冲突选择问题。
- 分析 item 59 的复杂矩阵表 extractor/列映射问题。
- 确认剩余 `/ -> 符合` 的业务口径，区分 `——` 占位符、同 group 混合 `符合要求` 以及 effective result 聚合不完整。
- 保持 C08/C10 不回退，不调用真实 Codex。
- T-CODEX-EVIDENCE-02 已先完成 C07 result token recovery：item 94/33/41/149 这类 row/page excerpt 中可见“符合要求”的 all-placeholder candidate 不再输出普通 ERROR；不确定恢复会转为 WARN / needs Codex review。
- T-CODEX-EVIDENCE-02 同步压缩 C07 Codex evidence：使用 compact rows 和 item 附近 page_text excerpt，不再发送整页 page_text、完整 finding evidence、`source_rows` 与 `complete_rows` 双份重复结构。
- T-CODEX-EVIDENCE-03 已补齐 C07 finalization 语义：`CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` 即使被 Codex `confirm`，也表示确认“抽取不确定需要复核”，最终进入 `manual_review_required`，不计入 confirmed finding 或 confirmed error。
- T-CODEX-EVIDENCE-03 已补齐 item 59 complex matrix 保护：漏电流/电流多页矩阵表、row_count 很大且存在列映射/续表歧义时，输出 `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX` WARN 或在 Codex target 上标记 `complex_matrix_table=true`，不再按普通 C07 业务错误 confirmed。
- T-CODEX-EVIDENCE-03 真实 C07 targeted validation 已通过：结果文件 `runtime/codex_audit_local_e2e/004f23d9-bd93-4773-91c4-d1c72acf6208.result.json` 中 `final_audit_status=needs_manual_review`、`confirmed_errors_count=0`、`manual_review_required_count=12`。这 12 条代表抽取/证据仍需复核，不代表最终报告错误。
- T-CODEX-EVIDENCE-03B full mandatory audit 真实验收已记录：结果文件 `runtime/codex_audit_local_e2e/53bbeec9-998b-4868-9627-00d9cc3b7ab0.result.json` 中 `audit_scope=full`、`confirmed_errors_count=0`、`manual_review_required_count=40`、`refuted_findings_count=11`、`codex_runtime_failure_count=0`。剩余项集中在 C04 标签字段证据不足 28 条和 C07 抽取不确定 12 条，下一步应继续 evidence enhancement，而不是修改 finalization。
- T-CODEX-EVIDENCE-06D 已用真实 C07 targeted visual audit 验证 C07 table/page/row/column 图片证据有效：C07 `manual_review_required` 从 12 降到 1，11 条 row_text_ambiguous / actual conclusion conflict 候选被视觉证据 refute，剩余 item 59 complex matrix 按预期保留 manual/specialized matrix review。
- T-CODEX-EVIDENCE-06 full audit 复验进一步确认全量口径：51 条 candidate 中 50 条已 refuted，confirmed final error 为 0，唯一剩余 manual review 是 C07 item 33 的 extraction-uncertain 证据/结构化抽取复核；当前噪声收敛重点应从 C04/C05/C06/C09 转为 T-CODEX-EVIDENCE-06E：item 33 residual manual review closeout，重点比较 targeted/full audit 的 evidence、prompt、image refs 和续行视觉证据差异。
- T-CODEX-EVIDENCE-06E 已收口 item 33 的代码侧稳定性问题并通过真实 C07 targeted validation：targeted/full 证据链一致，根因是 prompt 没明确“抽取遗漏但视觉证据已解决候选时应 refute”；复验任务 `a39b2841-e44d-4efd-a004-ae3147a2c1d6` 中 C07 12 条 candidate 全部 `refuted`，无 confirmed error、无 manual review、无 runtime failure。随后 full mandatory audit `bf36101c-71a4-4f69-9df9-907ced1000cb` 确认当前无 confirmed final error，唯一剩余 manual review 为 item 59 complex matrix；当前下一步是 T-CODEX-EVIDENCE-07：item 59 complex matrix specialized review。
- T-CODEX-EVIDENCE-07 规划已落地：下一阶段应按计划实现 specialized matrix evidence，不应修改 finalization 或把 item 59 硬编码为 passed；如果专门矩阵证据仍无法稳定映射跨页列，应继续保留 `manual_review_required`。
- T-CODEX-EVIDENCE-07A 已落地第一层 specialized matrix evidence：item 59 可以携带矩阵专用 image refs 和 structured hints，但还没有 prompt/materialization/handoff 的 07B 验证，也没有真实 targeted validation；因此当前质量口径仍保留 item 59 manual review。
- T-CODEX-EVIDENCE-07B 已补齐 matrix image materialization、runner handoff 和 prompt contract：下一步不应再改 finalization，而应执行 T-CODEX-EVIDENCE-07C targeted item 59 真实验收；如果真实视觉矩阵证据仍无法稳定映射跨页列，继续保留 `manual_review_required` 是预期安全结果。
- T-CODEX-EVIDENCE-07C 已完成真实 targeted item 59 验收和 full mandatory audit 最终复验：item 59 complex matrix 被视觉矩阵证据 `refute/high`，full audit `8e84b3e7-e079-4e6f-ac7f-b99348f18ffa` 中 C04/C05/C06/C07/C09 共 51 条 deterministic candidate 全部 `refuted`，`final_audit_status=passed`，当前无 confirmed final error、无 manual review、无 runtime failure。该真实样本的质量降噪主线已从“候选误报收敛”进入“更多样本回归验证”阶段。

### T-QUALITY-06：C04/C05/C06 OCR gating

- 明确 label caption、label OCR、label image 三层证据。
- label caption 存在但 OCR 不足时 WARN / NEEDS_REVIEW。
- “本次检测未使用”跳过或 WARN 口径统一。
- Codex/VLM 复核接入使用受控 evidence package。
- T-CODEX-EVIDENCE-04B 已完成 C04 evidence package 层的 caption/page text/crop/matched OCR/structured fields 分层；T-QUALITY-06 若继续推进，应聚焦 deterministic C04/C05/C06 rule gating 口径、真实 label crop/OCR 接入和 OCR 质量，而不是重复修改 finalization。

### T-QUALITY-07：前端 grouped findings 展示

- 前端默认展示 grouped finding。
- 明细 raw rows / diagnostics 折叠展示。
- 展示 `suppressed_count`、pages、source rows。
- 不在前端重新计算 C07/C08/C10。

### T-PERF：Codex audit speed roadmap 与质量主线关系

- T-PERF-01 至 T-PERF-04 已完成基础设施：性能画像、batch=5 可见性、bounded scheduler、高级 task options、以及 succeeded review cache/resume foundation。
- 这些任务不修改 deterministic rules、不修改 Codex finalization，也不降低 mandatory Codex audit 的失败口径。
- 性能数据会记录在 task result `metadata.performance_profile` 和 `metadata.codex_audit.performance_profile` 中，后续质量噪声复验应同时关注结论与运行成本。
- Cache 只用于 schema/parser valid、`status=succeeded` 且 verdict 非 `uncertain` 的 review；failed/skipped/uncertain/manual review 不作为最终通过依据缓存。
- 下一步 T-PERF-05 应用真实样本进行 full mandatory audit batch=5 对比；验收仍以 `final_audit_status=passed`、`confirmed_errors_count=0`、`manual_review_required_count=0`、`codex_runtime_failure_count=0` 为前提。

### T-RULE-2797-01：2797 语义校正与规则适用性

- 2797 附件结果中 `error_count=36`、`warn_count=14`、`review_count=0` 未经过 Codex final audit，不应在用户层解释为 36 个确认不符合。
- 本次新增 `user_facing_status`，将未审 deterministic ERROR 显示为 `candidate_issue`，将 OCR/表格抽取不确定显示为 `needs_review`，将 Codex/finalization refute/confirm 分别显示为 `refuted` / `confirmed_error`。
- C04 caption-only 标签样张不再逐字段输出 `SAMPLE_FIELD_MISSING_IN_LABEL` error；结构化 OCR 字段为空时输出 `OCR_EVIDENCE_INSUFFICIENT` WARN，等待视觉/OCR 复核。
- 第 8 页“本次检验配合使用”样品描述表会被标记为 `supporting_equipment`；C05/C06 默认不对这些配合使用设备输出主样品照片/标签覆盖 error。
- C07 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` 与 `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX` 在前端展示为抽取/视觉复核问题，不作为逻辑错误文案展示。

## 十、当前任务边界

T-QUALITY-01 只完成设计文档：

- 不实现 `InspectionItemGroup`。
- 不修改 C07/C08/C10 规则。
- 不修改 C04/C05/C06。
- 不修改 API/router。
- 不修改前端。
- 不修改旧项目目录。
- 不调用真实 Codex。
- 不标记 T-QUALITY-02 或后续任务完成。
