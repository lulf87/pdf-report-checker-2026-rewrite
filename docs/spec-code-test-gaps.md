# 规格-实现-测试差异清单

## 总览
- 高风险不一致数量：11
- 中风险不一致数量：7
- 低风险不一致数量：2

说明：本清单只审计旧项目 `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13` 中可见的文档、代码和测试；输出到当前重做项目。旧项目中未找到用户点名的 `REPORT_CHECKER_SPEC.md`、`CLAUDE.md`、`comparator.py`、`ptr_extractor.py`、`table_comparator.py`，相关结论均标记为需人工确认。为辅助新项目处理，另参考了当前项目 `需求/2026.6.3/report_self_check_requirements_v0_1.md` 中的 C01-C11 草案口径，但该草案自身标注为“待业务确认”。

## 差异项

### GAP-001：旧项目关键规格文档缺失，无法完成 README / CLAUDE / REPORT_CHECKER_SPEC 三方一致性核对
- 涉及规则：全局规格来源、README、CLAUDE.md、REPORT_CHECKER_SPEC.md
- 规格描述：用户说明旧项目包含 `REPORT_CHECKER_SPEC.md` 和 `CLAUDE.md`，并要求检查 README、CLAUDE.md、REPORT_CHECKER_SPEC.md 是否互相矛盾。
- 当前代码实现：旧项目实际可见文档只有 `README.md` 和 `docs/superpowers/specs/2026-04-23-report-self-check-codex-judge-spec.md`；`find` 未发现 `REPORT_CHECKER_SPEC.md` 或 `CLAUDE.md`。
- 当前测试覆盖：无测试验证规格文档存在性或文档间一致性。
- 风险等级：HIGH
- 建议处理：
  - 以规格为准：不能直接以缺失文档为准；需先找回或确认这些文档是否已迁移、改名或被删除。
  - 以测试为准：不建议。测试只覆盖旧实现行为，不能替代业务规格。
  - 需要人工确认：确认 `REPORT_CHECKER_SPEC.md`、`CLAUDE.md` 的真实位置或是否废弃。
- 新项目处理建议：先建立唯一权威规格入口，例如 `docs/requirements/report-self-check-requirements.md`，并在 README 中明确其优先级；废弃文档要写迁移说明。
- 需要新增或修改的测试：新增文档完整性检查，至少校验 README 指向的规格文件存在；CI 可检查“权威规格路径”不为空。

### GAP-002：旧规格、旧实现、旧测试和新草案的规则编号体系不一致
- 涉及规则：C01-C11、C00、C12-C17
- 规格描述：旧 `docs/superpowers/specs/...` 验收标准要求返回 14 项：C00、C01、C02、C03、C04、C06、C07、C08、C12、C13、C14、C15、C16、C17，并明确缺 OCR/证据不确定时返回 warning。旧计划文档又写明不要实现 C05、C09、C10、C11、C18。当前 6.3 新需求草案建议 v1 聚焦 C01-C11。
- 当前代码实现：`backend/app/services/report_evidence_builder.py` 的 `APPROVED_CHECK_IDS` 返回 13 项，缺 C17；也没有 C05、C09、C10、C11。
- 当前测试覆盖：`backend/tests/test_report_evidence_builder.py` 明确断言 C05、C17、C18 不在结果中；`backend/tests/test_report_self_check_service.py` 和 API 测试均断言总数为 13。
- 风险等级：HIGH
- 建议处理：
  - 以规格为准：新项目若采纳 6.3 草案，应重建 C01-C11 规则矩阵，不沿用旧编号含义。
  - 以测试为准：只能用于复现旧系统，不适合作为重做项目业务口径。
  - 需要人工确认：确认新项目是否正式采用 C01-C11，还是保留旧项目 C00/C12-C17。
- 新项目处理建议：先冻结“规则编号、规则名称、输入、输出、状态”的单表；旧编号迁移要提供映射表，避免 C08 这类编号复用造成误读。
- 需要新增或修改的测试：新增 `test_rule_matrix_matches_spec`，直接从规则注册表断言 C01-C11 的数量、顺序、名称和状态集合。

### GAP-003：C01 在旧规格中是编号一致性，在新草案中是首页与第三页字段一致性
- 涉及规则：C01
- 规格描述：旧规格 C01 问题是报告编号、样品编号在封面、报告首页、页眉中是否一致，以及样品编号尾号是否对应报告编号尾号。6.3 草案 C01 则是首页与第三页的委托方、样品名称、型号规格严格一致。
- 当前代码实现：旧实现 C01 只准备通用页面文本与 required details，不存在确定性 C01 checker；字段比对主要落在旧 C02 语义中，并交给 Codex 判断。
- 当前测试覆盖：测试只断言 C01 的 `required_details` 为 `report_number`、`sample_number`、`tail_match`，没有覆盖首页/第三页字段严格一致，也没有覆盖“样品名称 OCR 尾字容错”。
- 风险等级：HIGH
- 建议处理：
  - 以规格为准：新项目应以 6.3 草案 C01 为候选口径，但“严格一致是否允许归一化例外”需先确认。
  - 以测试为准：不建议。旧测试固定的是旧 C01。
  - 需要人工确认：样品名称 OCR 尾字缺失、空格、全半角、标点差异是否允许容错。
- 新项目处理建议：将旧 C01 改名迁移为“报告编号/样品编号一致性”或放入单独规则；新 C01 独立实现首页 vs 第三页字段比较。
- C01 迁移记录：旧 `REPORT_CHECKER_SPEC.md` 明确“严格一致”为字符级完全一致，大小写、全半角、空格、标点敏感；旧 `backend/app/services/third_page_checker.py` 的样品名称尾字容错、`strip()`、委托方/型号 OCR 噪声容错与该规格冲突。本次 C01 按用户提示和旧规格执行严格一致，旧容错不进入 C01 规则。
- 需要新增或修改的测试：新增 C01 正常样本、委托方不一致、样品名称尾字 OCR 缺失、型号规格空格/标点差异、字段无法定位 ERROR 的测试。

### GAP-004：C02 / C03 对“委托方、委托方地址、标签比对”的边界混乱
- 涉及规则：C02、C03，委托方、委托方地址、标签 OCR
- 规格描述：旧规格 C02 是封面与报告首页的委托方、样品名称、型号规格、检验类别一致。旧规格 C03 又要求报告首页的型号规格、生产日期、产品编号/批号、委托方、委托方地址由主样品标签或样品描述支持。6.3 草案 C02 则只关注第三页型号规格、生产日期、产品编号/批号与中文标签一致，或统一为 `见"样品描述"栏`。
- 当前代码实现：`report_evidence_builder.py` 没有专门抽取委托方地址；C02/C03 只是把封面、报告首页、样品描述、照片页文本打包给 Codex，没有确定性字段映射。
- 当前测试覆盖：旧测试只断言 C02 包含 `cover_text` 和 `report_home_text`；没有覆盖委托方地址，也没有覆盖“委托方/委托方地址到底和标签比，还是首页 vs 第三页比”。
- 风险等级：HIGH
- 建议处理：
  - 以规格为准：新项目建议按 6.3 草案拆分：C01 处理首页 vs 第三页身份字段；C02 处理第三页扩展字段 vs 标签/样品描述引用。
  - 以测试为准：不建议。旧测试未覆盖关键业务分支。
  - 需要人工确认：委托方地址是否仍需与标签或其他来源比对；若需要，应作为哪条规则。
- 新项目处理建议：不要把委托方地址隐含在 C02/C03 的 LLM 判断中；显式定义字段来源 A/B 和失败/REVIEW 条件。
- C02 迁移记录：旧 `REPORT_CHECKER_SPEC.md` 的 C02 仅明确 `型号规格`、`生产日期`、`产品编号/批号` 三个核心字段；旧 `backend/app/services/third_page_checker.py` 和新 `known-requirements.md` 又包含 `委托方`、`委托方地址`，字段范围存在冲突。本次 C02 按用户任务和旧规格先把三个核心字段作为 ERROR/WARN 判定范围；`委托方`、`委托方地址` 仅写入 `metadata.optional_field_results` 作为未确认扩展观察项，不输出 ERROR/WARN。`docs/open-questions.md` 当前不存在，待确认问题暂记录在本 GAP。
- 需要新增或修改的测试：新增 C02 三字段全部 `见"样品描述"栏`、部分特殊值、标签字段缺失、第三页空值但标签有值、委托方地址存在/缺失的边界测试。

### GAP-005：C03 是“日期格式一致”还是“日期值/字段支持一致”未统一
- 涉及规则：C03，生产日期
- 规格描述：6.3 草案 C03 明确只比较第三页生产日期与标签生产日期的格式模式，不比较日期值本身；日期值一致性由 C02 或 C04 判断。旧规格 C03 是首页扩展字段是否由标签或样品描述支持，并没有限定为“只比格式”。
- 当前代码实现：旧实现没有 C03 确定性日期格式比较；C03 只附加标签页图片、通用文本和 required details 给 Codex。
- 当前测试覆盖：旧测试只覆盖 C03/C06 会附加标签页整图和裁剪图；没有日期格式、日期值不同但格式相同、格式不同但值相同的测试。
- 风险等级：HIGH
- 建议处理：
  - 以规格为准：建议以 6.3 草案“只比格式”为准，但需业务确认后冻结。
  - 以测试为准：不建议，测试没有覆盖该业务。
  - 需要人工确认：`2026.1.8` 与 `2026.01.08` 是否同格式；中文日期与斜杠日期是否等价。
- 新项目处理建议：实现独立的日期格式归一化器，输出 `raw_value`、`format_pattern`、`normalized_format`，不要让 LLM 裁决格式。
- C03 迁移记录：旧 `REPORT_CHECKER_SPEC.md` 明确 C03 “比较格式模式，不比较日期值本身，以标签格式为准”，而 `known-requirements.md`/`rewrite-architecture.md` 曾写为“格式和值一致性”。本次 C03 按用户任务要求和旧规格先实现“只比较格式”，`metadata.compare_value_enabled=false`；同格式但日期值不同不输出 ERROR。是否启用 `DATE_VALUE_MISMATCH_001` 已记录到 `docs/open-questions.md`，未确认前不固化为错误。
- 需要新增或修改的测试：新增 C03 格式相同值不同应 PASS、格式不同值相同应 FAIL、无法抽取应 REVIEW、低置信 OCR 应 REVIEW。

### GAP-006：旧 C04 时间逻辑规格要求签发日期，但实现提示明确排除签发日期
- 涉及规则：旧 C04，时间逻辑一致性
- 规格描述：旧规格 C04 要求生产日期 <= 到样日期 <= 检验开始日期 <= 检验结束日期，并在签发日期存在时要求检验结束日期 <= 签发日期。
- 当前代码实现：`CHECK_RULES["C04"]` 明确写“不要核对签发日期，也不要因为签发日期与检验日期之间的关系给出问题”，与旧规格直接冲突。
- 当前测试覆盖：`test_c04_and_c14_packages_include_current_business_rules` 明确断言 C04 包含“不要核对签发日期”，也就是说测试锁定了偏离旧规格的实现。
- 风险等级：HIGH
- 建议处理：
  - 以规格为准：若保留时间逻辑规则，应恢复签发日期关系或把旧规格改掉。
  - 以测试为准：只有在业务确认签发日期不纳入核对时才可保留。
  - 需要人工确认：签发日期是否进入新项目范围；若进入，是 FAIL 还是 REVIEW。
- 新项目处理建议：6.3 草案 C01-C11 不再单列旧 C04 时间线；若需要时间线规则，应单独编号，不混入样品描述表 C04。
- 需要新增或修改的测试：新增签发日期早于检验结束日期、签发日期缺失、签发日期格式异常的测试；若排除签发日期，也应有规格级测试确认排除。

### GAP-007：样品描述表字段实现未完整覆盖失效日期，无法判断“标签有值但表为空”
- 涉及规则：旧 C06、旧 C08、新 C04，失效日期、样品描述表、中文标签字段
- 规格描述：旧规格 C06 字段包括部件名称、型号/规格、批号/序列号、生产日期、失效日期。6.3 草案 C04 也包含失效日期，并建议表格空白或 `/` 但标签有值时 FAIL。
- 当前代码实现：`_extract_sample_items` 只提取 `component_name`、`model`、`batch_or_serial`、`production_date`，不提取 `expiration_date`；`_extract_label_fields` 可以识别 `失效日期`，但样品描述侧没有对应字段。
- 当前测试覆盖：C08 样品候选测试覆盖了名称、型号、批号/序列号、生产日期；没有失效日期测试。
- 风险等级：HIGH
- 建议处理：
  - 以规格为准：失效日期应进入样品描述表与标签字段比较。
  - 以测试为准：不建议，旧测试遗漏该字段。
  - 需要人工确认：失效日期标签有值但样品描述表为空时，是 FAIL、REVIEW 还是允许为空。
- 新项目处理建议：样品描述字段模型必须包含 `expiration_date`，并定义 `/`、空白、无标签字段、有标签值之间的判定表。
- C04 迁移记录：本次 C04 按旧 `REPORT_CHECKER_SPEC.md` 的 C04 与 6.3 “/ 与空白规则”实现五字段比对：`部件名称`、`规格型号`、`序列号批号`、`生产日期`、`失效日期`。`/` 或空白与标签字段缺失/空白等价；表格为 `/` 或空白但标签有值时输出 `SAMPLE_FIELD_MISSING_IN_TABLE`，当前按 `ERROR` 处理。旧 `report_checker.py` 曾对“失效日期仅标签有值”放行，也曾对日期分隔符和部分 OCR 码值做容错；本次按规格“严格一致比对”重写，未继承这些容错。备注包含“本次检测未使用”的部件不跳过 C04 字段比对，但字段不一致输出 `SAMPLE_UNUSED_COMPONENT_FIELD_WARNING`，按 WARN 处理；最终是否跳过字段一致性仍需人工确认。
- 需要新增或修改的测试：新增表格失效日期为空/`/` 且标签有值、表格有值标签缺失、两边格式不同、未使用部件失效日期不一致的测试。

### GAP-008：照片覆盖与中文标签覆盖在旧项目中编号和职责均偏移
- 涉及规则：旧 C07、旧 C08、新 C05、新 C06，照片覆盖、中文标签覆盖
- 规格描述：旧规格 C07 是每个样品描述组件是否有对应照片 caption；旧规格 C08 是每个组件是否有中文标签或标签样张 caption。6.3 草案对应为 C05 照片覆盖、C06 中文标签覆盖。
- 当前代码实现：旧 C07 只有通用证据包；旧 C08 已扩展为“样品描述与照片标签一致性”，要求核对名称、型号、批号/序列号，并进行图片分批处理，不只是覆盖性。
- 当前测试覆盖：测试大量覆盖旧 C08 的标签字段抽取、图片路径、分批合并和误报过滤；几乎没有 C07 照片覆盖业务测试，也没有新 C05/C06 编号测试。
- 风险等级：HIGH
- 建议处理：
  - 以规格为准：新项目应按 6.3 草案将 C05/C06 作为覆盖性规则，C04 才做字段一致性。
  - 以测试为准：不建议，旧测试会把 C08 锁成“字段一致性 + 图片分批”。
  - 需要人工确认：外观照片与中文标签照片是否都可算 C05 照片覆盖；caption 只有“标签”是否可算 C06 中文标签。
- 新项目处理建议：拆成三层：C05 照片存在、C06 中文标签存在、C04 标签字段一致；不要让一个 C08 同时承担覆盖和字段一致性。
- C05 迁移记录：本次 C05 按旧 `REPORT_CHECKER_SPEC.md` 的 C05 口径实现为独立照片覆盖规则，只消费 `ReportDocument.sample_components` 与 `ReportDocument.photo_captions`。普通部件未匹配到非标签照片 caption 输出 `PHOTO_COVERAGE_MISSING`/`ERROR`；备注包含“本次检测未使用”的部件跳过照片覆盖，不输出 ERROR。Caption 主体名提取按旧规格移除编号前缀、方位词和照片类尾词；主体名匹配按旧规格的精确匹配与允许连接符部分匹配实现。包含“标签/中文标签/标签样张/铭牌/标牌”等 caption 默认不计入 C05，交由 C06 处理。低置信或主体名不可靠的 caption 输出 `PHOTO_CAPTION_UNCERTAIN`/`WARN` 或保留为 missing evidence 的候选证据。
- C06 迁移记录：本次 C06 按旧 `REPORT_CHECKER_SPEC.md` 的 C06 口径实现为独立中文标签覆盖规则，只消费 `ReportDocument.sample_components`、`ReportDocument.labels` 和标签类 `photo_captions`。中文标签候选由 caption/说明文字中的 `中文标签`、`中文标签样张`、`标签样张`、`标签` 判定；普通照片 caption 不计入 C06。对同名多行部件，按非空字段联合键（部件名称、规格型号、序列号批号、生产日期、失效日期，忽略空值、`/`、`见实物` 等）逐条匹配并消耗候选标签；候选存在但联合键无法匹配时输出 `LABEL_COMPONENT_KEY_NOT_MATCHED`/`ERROR`，无候选时输出 `LABEL_COVERAGE_MISSING`/`ERROR`。低置信标签输出 `LABEL_CAPTION_UNCERTAIN`/`WARN`，字段值一致性仍由 C04 负责。
- 需要新增或修改的测试：新增部件无照片、只有标签照片、只有英文标签、caption 无“中文”但 OCR 为中文、未使用部件无照片/无标签的测试。

### GAP-009：检验结果与单项结论逻辑从旧 C12 迁移到新 C07，空白结果口径未定
- 涉及规则：旧 C12、新 C07，检验结果、单项结论
- 规格描述：旧规格 C12 规则为：任一结果“不符合要求”则期望“不符合”；所有结果为 `/` 或 `——` 则期望 `/`；否则期望“符合”。6.3 草案 C07 增加“空白”也可进入第二优先级，但待确认又建议空白由 C08 判漏填，C07 可 REVIEW。
- 当前代码实现：旧实现没有确定性 C12 checker，只把规则交给 Codex；另加了“无菌生长”在无菌语境下可支持“符合”的提示。
- 当前测试覆盖：旧测试只测试“无菌生长”提示存在；没有覆盖 `/`、`——`、空白、`不符合要求`、非空数字、跨多行合并单项结论。新项目已新增 `backend/tests/rules/report/test_c07_item_conclusion.py`，覆盖 `/`、`——`、空白、任一不符合、非空数字、同序号多行聚合和 `续5` 归并。
- 风险等级：HIGH
- 建议处理：
  - 以规格为准：新项目 C07 应明确空白是期望 `/` 还是交由 C08 判 FAIL/REVIEW。
  - 以测试为准：不建议，旧测试覆盖面不足。
  - 需要人工确认：空检验结果到底期望 `/`、`不符合`，还是 C07 REVIEW 且 C08 FAIL。
- 新项目处理建议：C07 与 C08 分工要写清：C08 先判必填字段空；C07 只在检验结果可解析时推导期望单项结论。
- C07 迁移记录：本次 C07 按当前任务要求和 `known-requirements.md` 的优先级实现为独立规则，只消费 `ReportDocument.inspection_items`。按序号归组，`续5` / `续 5` 归并到原序号；任一结果包含“不符合”时期望“不符合”，全部为 `/`、`——` 或空白时期望 `/`，否则期望“符合”。实际单项结论为空时仍输出 `ERROR` Finding，不因 C08 也会报必填缺失而跳过。错误码按旧规格映射为 `CONCLUSION_MISMATCH_001/002/003`。本次未把旧实现中的表格列漂移启发式、无菌语境特殊解释和 Codex 判断链路迁入 C07；这些应由 extractor/domain 证据或后续确定性语义规则补足。
- 需要新增或修改的测试：C07 基础确定性测试已新增；后续仍需结合真实 extractor fixture 覆盖跨页合并单元格、列漂移、扫描表格 OCR 证据和“无菌生长”语境样例。

### GAP-010：非空字段规则从旧 C14 迁移到新 C08，`——` 是否非空未被实现和测试稳定覆盖
- 涉及规则：旧 C14、新 C08，检验结果、单项结论、备注
- 规格描述：旧规格 C14 只判断值是否存在，不判断 `/` 或 `——` 是否合理。6.3 草案 C08 建议备注 `/` 视为非空，检验结果 `——` 视为非空。
- 当前代码实现：旧 C14 提示说明备注列 `/` 非空；文本候选逻辑 `_has_c14_conclusion_or_remark_evidence` 只识别“符合”和 `/`，未显式识别 `——`；版式词坐标路径可把任何词视为内容，但文本路径覆盖不完整。
- 当前测试覆盖：旧测试有备注 `/` 的版式测试；没有检验结果 `——`、单项结论 `——`、备注 `——`、纯空格/不可见字符的测试。新项目已新增 `backend/tests/rules/report/test_c08_non_empty.py`，覆盖普通文本、空字符串、纯空白、`/`、`——`、合并单元格继承、合并首行为空、续表行逐行检查和空序号不归 C08。
- 风险等级：MEDIUM
- 建议处理：
  - 以规格为准：新项目 C08 应明确 `/`、`——`、空格、换行、不可见字符的非空定义。
  - 以测试为准：不建议，旧测试只覆盖 `/` 的局部行为。
  - 需要人工确认：`——` 在检验结果、单项结论、备注三个字段中是否都算非空。
- 新项目处理建议：用统一 `is_effectively_empty(value)` helper，并把 `/`、`——` 作为“非空占位符”显式列入白名单。
- C08 迁移记录：本次 C08 按旧 `REPORT_CHECKER_SPEC.md` 的 C08 口径和旧 `inspection_item_checker.py` 中“`/`、`——` 为非空占位符”的实现提示，重写为独立规则 `backend/app/rules/report/c08_non_empty.py`。规则只消费 `ReportDocument.inspection_items`，逐行检查 `检验结果`、`单项结论`、`备注`，每个空字段输出一个 `ERROR` Finding，code 为 `INSPECTION_FIELD_EMPTY`；字段来源显示为合并单元格且为空时输出 `INSPECTION_MERGED_FIELD_EMPTY`。合并单元格继承由 extractor/domain 的 `field_provenance` 提供，C08 不重新解析 PDF；空序号/序号连续性不由 C08 判定，交给 C09。
- 需要新增或修改的测试：后续仍需结合真实 extractor fixture 覆盖 PDF 文本断行、不可见 Unicode 空白和版式坐标无法确认时的 WARN/ERROR 分级。

### GAP-011：序号连续、续表、页码规则在旧项目中合并或缺少确定性实现
- 涉及规则：旧 C15、旧 C16、新 C09、新 C10、新 C11
- 规格描述：6.3 草案将 C09 序号连续、C10 续表标记、C11 页码连续拆成三条；旧规格 C15 同时包含序号连续、唯一性和续表正确性，C16 是页码连续性。
- 当前代码实现：旧 C15 有确定性续表候选 `_extract_c15_continuation_marker_candidates`，但序号跳号/重复主要仍依赖 Codex 所需 details；旧 C16 无可见确定性页码 checker。旧 required details 要求 `sequence_list`，但证据实际提供 `sequence_markers`。
- 当前测试覆盖：旧 C15 只覆盖续表标记缺失/误标和忽略标准要求数字；缺少序号跳号、重复、从 0 开始、C11 总页数不一致、末页不等的测试。新项目已新增 `backend/tests/rules/report/test_c09_sequence.py`，覆盖 C09 正常连续、起始不是 1、跳号、重复普通序号、空白序号、`续2` 不作为重复、`续1` 位置交由 C10、`续4` 引用不存在、跨页连续和跨页跳号。
- 风险等级：HIGH
- 建议处理：
  - 以规格为准：新项目应按 C09/C10/C11 拆开，并由确定性规则引擎输出。
  - 以测试为准：不建议，旧测试只覆盖旧 C15 的一部分。
  - 需要人工确认：重复序号无“续”是否一定 FAIL，还是需判断上一页是否未完成。
- 新项目处理建议：先实现独立表格行模型，含 `sequence_raw`、`sequence_normalized`、`is_continuation`、`page_number`，再分别跑 C09/C10。
- C09 迁移记录：本次 C09 按旧 `REPORT_CHECKER_SPEC.md` 和用户任务口径重写为独立规则 `backend/app/rules/report/c09_sequence.py`，只消费 `ReportDocument.inspection_items`，不解析 PDF、不检查 C08 必填字段、不判断 C10 续表位置。普通序号必须从 1 开始连续递增；普通重复输出 `SERIAL_NUMBER_DUPLICATED`；跳号或续号引用不存在的普通序号输出 `SERIAL_NUMBER_ERROR_001`；空白或无法识别的序号输出 `SERIAL_NUMBER_ERROR_002`。`续X` / `续 X` 归属原序号，不计入普通重复，位置合法性留给 C10；空序号归 C09，不归 C08。当前支持普通数字和全角阿拉伯数字；`续：X`、`续表X`、中文数字序号仍未确认，已记录到 `docs/open-questions.md`。
- C10 迁移记录：本次 C10 按旧 `REPORT_CHECKER_SPEC.md` 和旧 `inspection_item_checker.py` 的 C15/C10 续表经验重写为独立规则 `backend/app/rules/report/c10_continuation.py`，只消费 `ReportDocument.inspection_items` 中的 `source_page`、`row_index_in_page`、`sequence_raw`、`sequence`、`is_continuation`，不解析 PDF、不判断 C09 序号连续性、不推导 C07/C08 表格字段。规则按页码和页内行号分组：上一页末尾序号与新页首行普通序号相同且无“续”时输出 `CONTINUATION_MARK_ERROR_001`；“续”出现在本页第二行或更后行时输出 `CONTINUATION_MARK_ERROR_002`；新页首行 `续X` 与上一页末尾序号不一致时输出 `CONTINUATION_MARK_MISMATCH`。缺少页码或页内行号时输出 `CONTINUATION_CONTEXT_MISSING`/`WARN`，不臆造续表位置。当前 C10 支持 `续X`、`续 X` 和全角阿拉伯数字写法；`续：X`、`续表X`、中文数字仍待确认。
- C11 迁移记录：本次 C11 按旧 `REPORT_CHECKER_SPEC.md` 和用户任务口径重写为独立规则 `backend/app/rules/report/c11_page_number.py`，只消费 `ReportDocument.page_numbers` 或已抽取的 `ParsedPdf.pages` 文本，不直接打开 PDF。规则默认从 `ReportDocument.page_map["third_page"]` 开始，缺省为 PDF 排版第 3 页；第三页之前的页码证据不参与连续性判断。`parse_page_number_text` 支持 `共5页第1页`、`共 5 页 第 1 页`、`共005页 第001页`、`第1页/共5页`、`Page 1 of 5`、`1/5` 等格式。当前输出 `PAGE_NUMBER_ERROR_001`（Y 不连续/未从 1 开始）、`PAGE_NUMBER_DUPLICATED`、`PAGE_NUMBER_ERROR_002`（末页 Y 不等于 XXX）、`PAGE_NUMBER_ERROR_003`（XXX 不一致）、`PAGE_NUMBER_MISSING`、`PAGE_NUMBER_PARSE_FAILED`，缺失或无法解析按 ERROR 处理。当前不强制校验页码文本是否来自右上角坐标，也不额外强制 `XXX` 等于 PDF 第三页后的实际页数；这两项已记录到 `docs/open-questions.md`。
- 需要新增或修改的测试：C09/C10/C11 基础确定性测试已新增；后续仍需结合真实 extractor fixture 覆盖结构性空白行是否进入 `inspection_items`、跨页合并单元格是否提供稳定 `source_page`/`row_index_in_page`，以及 C11 页码坐标、扫描页 OCR 和真实 PDF 页码抽取链路。

### GAP-012：LLM/Codex 是否允许最终判定，旧规格、旧实现和新草案三者相反
- 涉及规则：所有规则，尤其 C01-C11、C14/C15、PTR
- 规格描述：旧规格明确“Codex is the judge”，程序只准备证据，不用正则做最终业务判断。6.3 草案明确 OCR/VLM/LLM 只能辅助抽取，最终判断由规则引擎完成。
- 当前代码实现：旧实现大多数报告自身规则由 Codex 返回最终 status；但 C14/C15 又在 Codex 后追加确定性 finding 并把 pass 改为 warning；PTR-SCOPE-COVERAGE 也直接由确定性结果生成。
- 当前测试覆盖：测试既锁定 Codex mock 的 13 项结果，也锁定 C14/C15 确定性候选会被提升为 warning。
- 风险等级：MEDIUM
- 建议处理：
  - 以规格为准：新项目若采用 6.3 草案，应禁止 LLM 直接输出规则 PASS/FAIL，只允许输出抽取候选。
  - 以测试为准：不建议，旧测试体现的是混合架构。
  - 需要人工确认：低置信 OCR/VLM 是 REVIEW 还是可由人工/LLM复判后转 PASS/FAIL。
- 新项目处理建议：设计 `Extractor -> Evidence -> RuleEngine -> Result`，LLM/VLM 输出只进入 evidence，并保留置信度。
- 需要新增或修改的测试：新增测试禁止规则引擎读取 LLM 的 verdict 字段；LLM 抽取失败只能产生 REVIEW/SYSTEM_ERROR。

### GAP-013：PTR 主统计是否排除 group clause、test method、appendix 未形成明确规格和测试
- 涉及规则：PTR 比对、group clause、test method、appendix、标准条款范围
- 规格描述：README 只说明按报告首页“检验项目”识别 PTR 第 2 章性能指标范围，核对报告“标准要求”是否完整摘录。用户关注 group clause、test method、appendix 是否排除主统计，但旧项目未见独立 PTR 规格文档。
- 当前代码实现：`ptr_report_evidence_builder.py` 只抽取 PTR 第 2 章，遇到第 3 章“检验方法/试验方法/测试方法”等停止；leaf clause 逻辑会把有子条款的父条款排除出 leaf reviews，但 scope coverage 仍可能统计父级声明；未见 appendix/附录或 group clause 的显式分类模型。
- 当前测试覆盖：测试覆盖第 3 章停止、子条款范围、父级精确声明、注释截断、文本空白页图片；没有 appendix、附录、group heading、方法条款混入主统计的测试。
- 风险等级：HIGH
- 建议处理：
  - 以规格为准：需要先补 PTR v2 规格，明确主统计范围与排除项。
  - 以测试为准：不建议，旧测试只覆盖部分启发式。
  - 需要人工确认：group clause 是否只作上下文、不计入缺失；appendix 引用是否计入摘录完整性；test method 是否完全排除。
- 新项目处理建议：PTR v2 建议建立 clause taxonomy：requirement、group_heading、method、appendix、note、table_reference，并在统计前过滤。
- 需要新增或修改的测试：新增含“附录 A”、第 3 章测试方法、只有标题无要求的 group clause、表格引用、注释的 PTR 样本。

### GAP-014：PTR 首页范围排除逻辑依赖括号关键词和标题/token 匹配，规格未确认
- 涉及规则：PTR 范围排除，生物相容性、电磁兼容性
- 规格描述：PTR 规则提示写“若首页已明确排除生物相容性、电磁兼容性等项目，对应 PTR 条款不纳入本轮缺失或不一致问题”。README 没有详细排除语法。
- 当前代码实现：只从首页检验项目括号中提取含“除/不含/不包括/排除”的文本，再用分词 token 与 PTR 条款 title/text 匹配；`性` 结尾会追加去掉“性”的 token。该逻辑可能漏掉非括号排除、同义词、跨句排除，也可能误伤正文含相同 token 的条款。
- 当前测试覆盖：测试覆盖“除电磁兼容性”可排除“电磁兼容”和整段 2.5；没有覆盖非括号排除、多个括号、同义表达、排除词只出现在说明段的情况。
- 风险等级：MEDIUM
- 建议处理：
  - 以规格为准：先明确排除语法和同义词范围。
  - 以测试为准：只能保留旧项目已覆盖的“括号内除...”场景。
  - 需要人工确认：排除逻辑是否允许模糊匹配，还是必须精确条款号/项目名。
- 新项目处理建议：范围解析输出结构化 selectors 和 exclusions，exclusion 应含原文、来源页、匹配到的条款、匹配理由。
- 需要新增或修改的测试：新增括号外排除、中文同义词、排除 2.5 但保留 2.5.1、排除文本误匹配正文 token 的回归测试。

### GAP-015：PTR 2.4 特定 warning 被服务层压制为 pass，可能掩盖真实差异
- 涉及规则：PTR-2.4，安全要求、附录索引、GB 标准号索引
- 规格描述：PTR 规则提示允许 report 使用“见序号1～序号118”等序号范围、GB 标准号或附录索引概括安全要求，不能仅因此判问题。
- 当前代码实现：`ptr_report_check_service.py` 的 `_suppress_allowed_ptr_warnings` 只对 `PTR-2.4` 特定文本模式生效，可能删除 Codex findings，并在无剩余 finding/missing_evidence 时把 warning 改成 pass。
- 当前测试覆盖：`test_ptr_service_suppresses_allowed_2_4_index_reference_warnings` 明确断言相关 warning 会被压制为 pass；没有测试“索引摘要同时存在实质遗漏”时是否保留 warning/error。
- 风险等级：MEDIUM
- 建议处理：
  - 以规格为准：允许索引摘要不等于允许所有 2.4 warning 被压制，应定义可压制条件。
  - 以测试为准：只适合旧项目 2.4 特例，不适合泛化。
  - 需要人工确认：哪些 2.4 索引式写法可视为完整覆盖，是否需要人工复核。
- 新项目处理建议：不要在服务层按文本删除 findings；应由规则引擎输出 `suppressed_reason` 和 `residual_risk`，保留原始 finding 供审计。
- 需要新增或修改的测试：新增 2.4 索引摘要但缺少关键安全要求、混入 EMC 尾部但不影响核心要求、混入非 PTR 文本导致误导的测试。

### GAP-016：API 路径和任务状态与新设计草案不一致，旧项目无独立 API 文档
- 涉及规则：API 文档、router、前端 API
- 规格描述：旧 README 只给启动和使用方式，没有列 API 路径。旧计划文档采用 `/api/report-self-check` 前缀。6.3 草案只定义业务 JSON 草案和任务状态 PENDING/PROCESSING/COMPLETED/SYSTEM_ERROR，不定义具体路径。用户特别关注旧版 `/api/report` 与新设计 `/api/tasks` 冲突。
- 当前代码实现：实际 FastAPI 挂载 `/api/report-self-check`，包括 `/check`、`/check/start`、`/ptr-report/check/start`、`/record-report/check/start`、`/tasks/{task_id}`；没有顶层 `/api/report` 或 `/api/tasks`。
- 当前测试覆盖：API 测试覆盖 `/api/report-self-check/...` 路径和 `running/completed/error` 状态；没有测试 `/api/tasks` 或 PENDING/PROCESSING/SYSTEM_ERROR。
- 风险等级：MEDIUM
- 建议处理：
  - 以规格为准：新项目应先出 API 契约文档，再写 router。
  - 以测试为准：旧路径可作为迁移参考，但不应默认为新设计。
  - 需要人工确认：新项目是否统一为 `/api/tasks/{id}`，报告自身上传是否为 `/api/report-checks` 或其他资源名。
- 新项目处理建议：统一任务资源模型，建议所有模式都创建 task，再通过 `/api/tasks/{task_id}` 查询；旧路径若保留，应作为兼容层。
- 需要新增或修改的测试：新增 OpenAPI snapshot 或契约测试，覆盖路径、方法、表单字段、任务状态枚举和错误响应。

### GAP-017：前端类型与后端旧返回基本对齐，但与新业务结果结构不一致
- 涉及规则：前端类型、后端返回结构、结果状态
- 规格描述：6.3 草案结果状态建议为 PASS/FAIL/REVIEW/SKIP/SYSTEM_ERROR，严重等级为 ERROR/WARN/INFO，并要求每条 FAIL/REVIEW 有 page_number、raw_text、normalized_text、source、confidence 等证据字段。
- 当前代码实现：后端模型和前端类型使用 `pass/warning/error`；summary 是 `total_checks/pass_count/warning_count/error_count`；task 状态是 `running/completed/error`。前端 `evidence` 和 `missing_evidence` 使用 `Record<string, unknown>`，未强约束证据字段。
- 当前测试覆盖：旧前端没有类型契约测试；后端模型测试只覆盖旧字段和旧状态。
- 风险等级：MEDIUM
- 建议处理：
  - 以规格为准：新项目应按新业务状态和证据模型重建前后端共享 schema。
  - 以测试为准：旧前端类型可帮助兼容旧 API，但不满足新草案。
  - 需要人工确认：是否保留 `warning/error` 命名，还是改成业务态 `REVIEW/FAIL` 加 severity。
- 新项目处理建议：用单一 JSON Schema 或 OpenAPI 生成前端类型，避免手写 TS 类型漂移。
- 需要新增或修改的测试：新增后端 JSON schema 与前端类型生成一致性测试；新增结果样例 fixture 的前端渲染测试。

### GAP-018：模型/Schema 对 evidence 的非空要求自相矛盾
- 涉及规则：数据模型、EvidenceItem、Codex prompt、JSON schema
- 规格描述：旧 Codex prompt 要求 evidence 非空时每项至少包含 source、page、label、value，且 value 必须是原 PDF 摘录，不要填 null。6.3 草案要求失败/复核证据必须有原文、页码、来源等。
- 当前代码实现：`EvidenceItem.value` 允许 `Any = None`；JSON schema 只要求 evidence item 有 `source`，`page/label/value` 都可缺失或为 null；服务层 `_enrich_evidence_values` 会尝试补 value，但不保证成功。
- 当前测试覆盖：`test_codex_check_result_accepts_nullable_evidence_fields` 明确接受 `page=None`、`label=None`、`value=None`。
- 风险等级：MEDIUM
- 建议处理：
  - 以规格为准：新项目应区分“原文证据”和“系统诊断证据”，原文证据必须有 raw_text/page/source。
  - 以测试为准：不建议，旧测试放宽了证据约束。
  - 需要人工确认：系统错误或解析失败时是否允许无 page/value 的 evidence，还是应放到 diagnostics。
- 新项目处理建议：定义强类型 `Evidence`，至少包括 `source_type`、`page_number`、`raw_text`；无法定位时用 `missing_evidence` 或 `diagnostics`，不要用 null evidence 代替。
- 需要新增或修改的测试：新增 schema 测试拒绝 FAIL/REVIEW finding 缺少证据；允许 SYSTEM_ERROR 使用 diagnostics 而非 evidence。

### GAP-019：README 的项目范围与报告自身旧规格的模块范围容易被误读为冲突
- 涉及规则：README、报告自身旧规格、PTR、原始记录
- 规格描述：旧 README 说项目包含报告自身核对、PTR 与报告核对、原始记录与报告核对。旧报告自身规格明确“本模块只做 report against itself，不做 PTR-to-report comparison”。
- 当前代码实现：实际 router 把三种模式都放在同一个 `report_self_check.py` router 下，路径也共享 `/api/report-self-check` 前缀。
- 当前测试覆盖：测试覆盖三种模式都走同一 app/router，但没有文档边界测试。
- 风险等级：LOW
- 建议处理：
  - 以规格为准：README 是项目级，旧 spec 是模块级，两者不必然冲突，但需要写清。
  - 以测试为准：测试不能说明文档边界。
  - 需要人工确认：新项目 v1 是否只做报告自身核对，PTR/原始记录是否移出主导航或隐藏。
- 新项目处理建议：README 按产品模块分章，报告自身/PTR/原始记录各自有独立需求和 API 命名空间。
- 需要新增或修改的测试：不需要业务测试；可新增文档链接检查，确保 README 指向各模块规格。

### GAP-020：用户预期的 PTR 组件文件不存在，实际实现集中在 evidence_builder/service 中
- 涉及规则：PTR comparator、ptr_extractor、table_comparator
- 规格描述：用户要求检查 comparator / ptr_extractor / table_comparator 实现与测试。
- 当前代码实现：旧项目未找到这些文件；PTR 逻辑集中在 `backend/app/services/ptr_report_evidence_builder.py` 和 `backend/app/services/ptr_report_check_service.py`。
- 当前测试覆盖：测试文件为 `test_ptr_report_evidence_builder.py`、`test_ptr_report_check_service.py`、`test_ptr_report_check_api.py`；没有 comparator/table_comparator 单元测试。
- 风险等级：LOW
- 建议处理：
  - 以规格为准：如果新架构需要 comparator/extractor/table_comparator 分层，应重新设计文件边界。
  - 以测试为准：旧测试可迁移为行为测试，但不代表目标模块结构。
  - 需要人工确认：这些文件名是旧旧版本遗留预期，还是新项目希望采用的架构命名。
- 新项目处理建议：PTR v2 可拆为 `ptr_scope_extractor`、`ptr_clause_extractor`、`report_table_extractor`、`ptr_report_comparator`，并让每层有独立输入输出模型。
- 需要新增或修改的测试：新增每层 parser/comparator 的小样本单元测试，再保留端到端 API 测试。
