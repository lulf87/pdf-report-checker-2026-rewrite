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

## 六、C04/C05/C06 后续策略

C04/C05/C06 的后续降噪重点不是 item group，而是 OCR/caption gating 和证据等级。

建议：

1. “本次检测未使用”部件继续跳过 C05/C06 覆盖性规则；C04 字段一致性建议默认 WARN 或跳过，最终口径需确认。
2. label caption 存在但 OCR 字段不足时，不应直接 ERROR：
   - C06 可认为“标签覆盖存在，但 OCR 字段不足”，输出 WARN / NEEDS_REVIEW。
   - C04 不应把缺 OCR 字段直接等同于标签字段为空。
3. 缺 OCR、OCR 低置信、OCR 与 caption 不一致时，输出 WARN / NEEDS_REVIEW，并保留 candidate evidence。
4. deterministic rule 只做候选 finding 和 evidence building。
5. 图文语义、caption 与部件是否同一对象、OCR 缺字容错等复杂判断交给 Codex/VLM 审核。
6. Codex review 只作为审核意见，不覆盖原始 finding。

建议新增元数据：

- `ocr_available`
- `label_caption_available`
- `label_image_available`
- `ocr_confidence`
- `evidence_completeness`
- `needs_codex_review`

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

- C07 消费 `InspectionItemGroup` 的 effective results/conclusion。
- 保留现有推导优先级。
- Codex evidence builder 使用 group evidence。

### T-QUALITY-06：C04/C05/C06 OCR gating

- 明确 label caption、label OCR、label image 三层证据。
- label caption 存在但 OCR 不足时 WARN / NEEDS_REVIEW。
- “本次检测未使用”跳过或 WARN 口径统一。
- Codex/VLM 复核接入使用受控 evidence package。

### T-QUALITY-07：前端 grouped findings 展示

- 前端默认展示 grouped finding。
- 明细 raw rows / diagnostics 折叠展示。
- 展示 `suppressed_count`、pages、source rows。
- 不在前端重新计算 C07/C08/C10。

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
