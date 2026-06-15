# Open Questions

## C03：生产日期是否比较日期值

- 状态：待确认。
- 背景：旧 `REPORT_CHECKER_SPEC.md` 明确 C03 只比较第三页生产日期与中文标签 OCR 生产日期的格式模式，不比较日期值本身；`known-requirements.md` 和 `rewrite-architecture.md` 曾写为“格式和值一致性”。
- 当前实现：按旧规格与本次任务要求执行，只比较格式，`metadata.compare_value_enabled=false`。同格式但日期值不同暂不输出 `ERROR`。
- 待确认：是否需要启用日期值比较；若启用，是否作为 C03 的 `DATE_VALUE_MISMATCH_001`，还是交由 C02/C04 的字段值一致性规则覆盖。
- 影响测试：当前 `backend/tests/rules/report/test_c03_production_date.py` 锁定“同格式不同值 PASS”的临时口径。

## C03：中文日期与零填充格式

- 状态：待确认。
- 当前实现：支持 `YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY.MM.DD`、`YYYYMMDD`；同一分隔符下 `2026/01/08` 与 `2026/1/8` 视为同一格式。
- 待确认：`YYYY年MM月DD日` 是否纳入 C03 支持格式；若纳入，`2026年01月08日` 与 `2026年1月8日` 是否视为同一格式。

## C04：表格无值但标签有值的最终严重级别

- 状态：待确认。
- 背景：旧 `REPORT_CHECKER_SPEC.md` 6.3 明确 `/` 或空白 vs OCR 有值为表格漏填；`known-requirements.md` 又把该情形列为 TODO。旧 `report_checker.py` 曾对“失效日期仅标签有值”放行。
- 当前实现：按旧规格 6.3 和本次任务要求执行，输出 `SAMPLE_FIELD_MISSING_IN_TABLE`，严重级别为 `ERROR`。
- 待确认：是否所有字段都应按 ERROR 处理，还是某些字段（尤其 `失效日期`）允许 WARN 或通过。
- 影响测试：当前 `backend/tests/rules/report/test_c04_sample_description.py` 锁定 `/` + 标签有值为 ERROR。

## C04：`见实物` 是否作为无值等价

- 状态：待确认。
- 背景：旧 `REPORT_CHECKER_SPEC.md` 在占位/特殊值中列出 `见实物`，当前新项目公共 helper 也把 `见实物` 作为 no-value marker；但 `known-requirements.md` 对 C04 只明确 `/` 或空白。
- 当前实现：沿用公共 `is_no_value()`，因此 `见实物` 暂按无值处理。
- 待确认：C04 样品描述表字段是否允许 `见实物` 与标签字段缺失/空白等价。

## C04：`本次检测未使用` 部件是否跳过字段一致性

- 状态：待确认。
- 背景：旧规格 C05/C06 明确未使用部件无照片/无标签不报错；错误分级表又写“未使用部件字段不一致”为 WARN。`known-requirements.md` 也未确认 C04 是否跳过。
- 当前实现：不跳过 C04 字段一致性；字段不一致或漏填时输出 `SAMPLE_UNUSED_COMPONENT_FIELD_WARNING`，严重级别为 `WARN`。
- 待确认：最终口径是跳过 C04、保留 WARN，还是按普通部件输出 ERROR。

## C04/C06：同名多行部件的非空联合键字段

- 状态：待确认。
- 当前实现：C04 标签匹配优先使用 `规格型号`、`序列号批号`、`生产日期`、`失效日期` 的非空字段；名称只作为候选匹配信号。
- 待确认：联合键是否必须包含 `部件名称`，以及生产日期/失效日期是否都应参与 C04/C06 的同名多行区分。

## C05：同名多行部件是否可共享同一张照片

- 状态：待确认。
- 背景：旧 `REPORT_CHECKER_SPEC.md` 对 C06 中文标签明确提到同名多行使用“非空字段联合键”分别匹配，但 C05 照片覆盖只写“每个部件至少一张照片”，未明确同名多行普通照片是否必须逐行区分。
- 当前实现：C05 仅按部件名称与照片 caption 主体名判断覆盖；同名多行是否必须不同照片未写成 ERROR 口径。
- 待确认：同名多行部件是否允许共用同一张外观照片，还是需要结合型号/批号/生产日期等非空字段分别覆盖。

## C05：caption 不可靠时的最终等级

- 状态：待确认。
- 当前实现：照片 caption 能匹配但 OCR/提取置信度为 low，或 caption 主体名不可可靠解析时，输出 `PHOTO_CAPTION_UNCERTAIN`，严重级别为 `WARN`；若仍无法证明某部件有照片覆盖，则另输出 `PHOTO_COVERAGE_MISSING`。
- 待确认：caption 不可靠是否应始终 WARN，还是只写入 Finding.metadata 供人工查看。

## C05/C06：泛“标签”类 caption 的归属

- 状态：待确认。
- 背景：旧规格 C05 是普通照片覆盖，C06 是中文标签覆盖；旧 caption 主体名提取会移除 `标签` 尾词，但未明确只有“标签”而非“中文标签”的照片是否可算普通照片。
- 当前实现：包含 `标签`、`中文标签`、`标签样张`、`铭牌`、`标牌` 的 caption 默认不计入 C05，交由 C06 或人工确认。
- 待确认：英文标签、铭牌、包装标签或只有“标签”字样的 caption 是否全部属于 C06，还是部分可算作普通照片覆盖。

## C06：同名多行缺少身份字段时的匹配口径

- 状态：待确认。
- 当前实现：同名多行部件会优先使用规格型号、序列号批号、生产日期、失效日期等非空字段分别匹配并消耗中文标签候选；如果部件本身没有这些非空身份字段，则允许退回 caption 主体名匹配。
- 待确认：同名多行且缺少非空身份字段时，是否应直接输出 `LABEL_COMPONENT_KEY_NOT_MATCHED`，还是允许按 caption 主体名和候选数量匹配。

## C06：低置信中文标签的最终等级

- 状态：待确认。
- 当前实现：标签匹配成功但 OCR/标签置信度为 low 时，输出 `LABEL_CAPTION_UNCERTAIN`，严重级别为 `WARN`，不静默 PASS。
- 待确认：低置信标签是否始终 WARN，还是只在 Finding.metadata 中标记，由人工筛选阶段处理。

## C07：空白检验结果与 C08 非空字段的分工

- 状态：待确认。
- 背景：旧 `REPORT_CHECKER_SPEC.md` C07 写明全部检验结果为 `——` 或空白时期望单项结论 `/`；`known-requirements.md` 同时提示空白检验结果应由 C08 报非空字段问题，C07 是否仍推导 `/` 需人工确认。
- 当前实现：按本次 C07 迁移任务执行，空白检验结果参与 C07 优先级 2；若同序号下全部检验结果为空白、`/` 或 `——`，C07 期望单项结论为 `/`。C07 不因 C08 可能另报必填缺失而跳过。
- 待确认：最终产品口径是否接受 C07 和 C08 对同一空白检验结果分别输出“结论逻辑”和“字段必填”问题，还是 C07 应在全部空白时降级为 REVIEW/SKIP。
- 影响测试：当前 `backend/tests/rules/report/test_c07_item_conclusion.py` 锁定“空白 + 空白 -> 期望 `/`，空白不默认推导为 `不符合`”。

## C08：`/` 和 `——` 是否永远视为非空

- 状态：待确认。
- 背景：旧 `inspection_item_checker.py` 明确提示 C08 中 `/` 和 `——` 是非空占位符；`known-requirements.md` 仍把三列中 `/`、`——` 是否永远非空列为待确认。
- 当前实现：按旧实现提示和本次 C08 迁移任务执行，`检验结果`、`单项结论`、`备注` 三列中 `/` 和 `——` 均视为非空，不输出 C08 Finding。
- 待确认：最终业务口径是否允许某些列或某些项目中 `——` 仅代表未测/不适用，需要由 C07 或其它规则另行判断。
- 影响测试：当前 `backend/tests/rules/report/test_c08_non_empty.py` 锁定 `/` 和 `——` 为 C08 非空占位符。

## C09/C10：序号与续表标记可接受格式

- 状态：待确认。
- 背景：旧 `REPORT_CHECKER_SPEC.md` 明确 C09 检查序号从 1 开始连续、无跳号、无重复、无空白，C10 检查跨页续表标记；`known-requirements.md` 已把 `续：X`、`续表X`、中文数字序号列为 TODO。旧 `inspection_item_checker.py` 主要通过移除 `续` 后解析数字，未形成完整格式枚举。
- 当前实现：C09 接受普通数字、全角阿拉伯数字、`续X` 和 `续 X`；`续X` / `续 X` 归属原序号，不作为普通重复。C10 识别 `续X`、`续 X` 和 `续５` 这类全角阿拉伯数字写法，并据此判断续表标记缺失、错位或续号不匹配。`续：X`、`续表X`、中文数字序号暂不接受；在 C09 中会按空白或无法识别序号输出 `SERIAL_NUMBER_ERROR_002`，在 C10 中不会被视为合法续表标记。
- 待确认：是否需要接受 `续：X`、`续表X`、`续- X`、中文数字或其他 OCR 常见变体；若接受，应归 C09 的序号解析，还是归 C10 的续表标记解析。
- 影响测试：当前 `backend/tests/rules/report/test_c09_sequence.py` 和 `backend/tests/rules/report/test_c10_continuation.py` 锁定 `续X` / `续 X` 可识别，未把 `续：X`、`续表X`、中文数字写成通过用例。

## C09：续号引用不存在的归属和等级

- 状态：待确认。
- 背景：C09 任务要求 `续X` 归属原序号且不作为重复普通序号，C10 负责续表位置合法性；但 `续4` 出现时若普通序号 4 不存在，同时涉及序号连续性和续表语义。
- 当前实现：`续4` 若没有对应普通序号 4，C09 输出 `SERIAL_NUMBER_ERROR_001`，metadata 记录 `invalid_continuation_numbers=[4]`；不判断该 `续4` 是否位于新页第一行。
- 待确认：续号引用不存在是否应保持 C09 `ERROR`，还是应改由 C10 输出 `ERROR/WARN`，C09 仅记录 metadata。
- 影响测试：当前 `backend/tests/rules/report/test_c09_sequence.py` 锁定“`1,2,续4,3` 产生 C09 `SERIAL_NUMBER_ERROR_001`”。

## C11：页码文本是否必须来自右上角坐标

- 状态：待确认。
- 背景：旧 `REPORT_CHECKER_SPEC.md` 写明 C11 核对“从第三页开始，每页右上角的页码文字”；`known-requirements.md` 也把“页码是否必须来自右上角坐标，还是全文正则命中即可”列为 TODO。
- 当前实现：C11 规则只消费 `ReportDocument.page_numbers` 或 `ParsedPdf.pages` 中已经抽取好的文本，不读取 PDF、不做坐标筛选。若 extractor 已提供 `PageNumberEvidence.location`，规则会把位置带入 Finding；若只从 `ParsedPdf` 文本 fallback，则只保证按页文本正则解析。
- 待确认：页码抽取阶段是否必须限定在右上角区域；若必须，应由 `infrastructure/pdf` 或 report extractor 产出带坐标和置信度的 `PageNumberEvidence`，C11 只校验该证据。
- 影响测试：当前 `backend/tests/rules/report/test_c11_page_number.py` 锁定 C11 可从 `ReportDocument.page_numbers` 或 `ParsedPdf.pages` 文本运行，但不测试坐标约束。

## C11：总页数 XXX 是否必须等于 PDF 第三页后的实际页数

- 状态：待确认。
- 背景：用户任务要求测试“总页数 XXX 与 PDF 实际剩余页数不一致是否报错，按 docs 口径；如果未确认，记录 open question”。旧 `REPORT_CHECKER_SPEC.md` 明确末页 `Y=XXX`、所有页 `XXX` 一致，但未明确 `XXX` 是否还要和 PDF 第三页后的实际页面数量逐项相等。
- 当前实现：C11 校验 Y 从 1 连续递增、无重复、末页 Y 等于该页 XXX、所有 XXX 一致；如果实际存在额外页面且无页码，会输出 `PAGE_NUMBER_MISSING`。但在只提供部分 `PageNumberEvidence`、且缺少完整 `ParsedPdf.pages` 的情况下，不根据 `XXX` 反推缺少的物理页。
- 待确认：是否需要在 `ParsedPdf.page_count` 或完整页映射可用时强制 `XXX == 从第三页开始的 PDF 实际页数`；如启用，错误码应使用现有 `PAGE_NUMBER_ERROR_002/003` 还是新增独立码。
- 影响测试：当前 `backend/tests/rules/report/test_c11_page_number.py` 不把 `XXX` 与 PDF 实际剩余页数不一致写成强制 ERROR，只覆盖末页 Y 与 XXX 不一致。

## C11：扫描页或 OCR 低置信页码的等级

- 状态：待确认。
- 背景：C11 页码缺失或无法解析可能来自扫描页 OCR 缺失、文本层缺失、页码区域裁剪失败或格式异常。旧 `REPORT_CHECKER_SPEC.md` 对 C11 三个核心校验项均列为 ERROR，但未单独定义 OCR 低置信页码。
- 当前实现：`PAGE_NUMBER_MISSING` 和 `PAGE_NUMBER_PARSE_FAILED` 均按 `ERROR` 输出；规则本身不调用 OCR，也不读取 OCR confidence。若后续 extractor 把 OCR 低置信度写入 `PageNumberEvidence.metadata`，C11 目前只保留 evidence/metadata，不单独降级为 WARN。
- 待确认：OCR 低置信但文本可解析时，C11 是否仍应 ERROR/PASS，还是输出 WARN；OCR 无法识别页码时是否保持 `PAGE_NUMBER_MISSING`/`ERROR`。
