# Codex Audit Local E2E

更新时间：2026-06-23

本文记录 T-CODEX-11A 的本地业务端到端验收入口、T-CODEX-11B 的真实 codex-cli 本地业务验收结果，以及 T-CODEX-MANDATORY-01 后的 mandatory Codex CLI 运行语义。Codex CLI 是本地业务验收的 mandatory auditor；规则输出是 candidate，不是最终结论。

## 一、目的

- 验证本地后端默认通过 `CodexCliRunner` 调用本机 `codex exec`，并把结果写入 `codex_reviews`。
- 验证 Codex runtime failure 会让任务失败，而不是 completed 后只携带 failed review。
- 验证 Codex verdict=`uncertain` 是正常审核结果，任务 completed 但前端展示人工复核。
- 验证前端只展示后端返回的 `codex_reviews` 和 finding metadata，不重新计算 C01-C11 或 PTR 规则。

普通自动化测试仍不调用真实 Codex CLI；测试通过显式 fake dependency 注入完成。业务 E2E 脚本默认拒绝运行，只有设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1` 后才会联系后端，避免误触发真实 Codex CLI。

## 二、本地运行

产品运行路径不再提供用户层面的 disabled/fake/codex-cli 选择。本地 API 默认构建 `CodexAuditService + CodexCliRunner`；`FakeCodexRunner` 只用于 pytest 或显式测试依赖注入。

启动后端：

```bash
cd backend
CODEX_CLI_PATH=codex \
CODEX_AUDIT_RUNTIME_DIR=runtime/codex_audit \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=5 \
python -m uvicorn app.main:app --reload
```

启动前端：

```bash
cd frontend
npm run dev
```

业务验收：

1. 打开前端页面。
2. 上传 PTR + 报告，或上传单份报告自检。
3. 查看结果页和导出的 JSON。
4. 预期：`check_results[].codex_reviews` 包含 Codex 审核意见；如果 Codex CLI 不可用、超时、非零退出或输出无效，任务状态为 failed/error。

## 三、脚本验收

脚本路径：

```bash
bash scripts/run-codex-audit-local-e2e.sh
```

查看帮助：

```bash
bash scripts/run-codex-audit-local-e2e.sh --help
```

查看安全配置，不上传文件、不启动服务、不调用 Codex：

```bash
bash scripts/run-codex-audit-local-e2e.sh --print-config
```

报告自检：

```bash
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
TASK_TYPE=report-check \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

如需脚本代启后端：

```bash
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
START_BACKEND=1 \
TASK_TYPE=report-check \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

PTR 比对：

```bash
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
TASK_TYPE=ptr-compare \
PTR_FILE=/path/to/ptr.pdf \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

真实 Codex CLI 建议先用单 target / 小 batch 验收：

```bash
PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C07 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
TASK_TYPE=report-check \
REPORT_FILE=/path/to/report.pdf \
bash scripts/run-codex-audit-local-e2e.sh
```

脚本安全要求：

- 必须设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1` 才会运行上传/轮询流程。
- 未满足 gate 时，脚本拒绝运行，不调用后端，也不会触发真实 Codex CLI。
- `--help` 和 `--print-config` 不启动服务、不上传文件、不调用 Codex。

## 四、脚本参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `TASK_TYPE` | `ptr-compare` | `ptr-compare` 或 `report-check`。 |
| `BASE_URL` | `http://127.0.0.1:8000` | 已运行后端地址。 |
| `START_BACKEND` | `0` | 为 `1` 时脚本代启后端。 |
| `PYTHON_BIN` | `python` | 用于脚本 JSON 解析的 Python。 |
| `PTR_FILE` | 无 | PTR PDF，本地业务样本路径。 |
| `REPORT_FILE` | 无 | 报告 PDF，本地业务样本路径。 |
| `EXPECT_CODEX_REVIEWS` | `auto` | `auto`、`empty`、`nonempty` 或 `any`；mandatory 默认期望非空。 |
| `OUTPUT_DIR` | `runtime/codex_audit_local_e2e` | 保存 task/result JSON 的本地目录。 |
| `CODEX_CLI_PATH` | `codex` | 本机 Codex CLI 可执行文件。 |
| `CODEX_AUDIT_MAX_TARGETS_PER_BATCH` | `5` | 每个 batch 最多审核 targets；这是性能分批，不是漏审上限。 |
| `CODEX_AUDIT_INCLUDED_CHECK_IDS` | 空 | 只审核指定 check IDs，例如 `C07` 或 `C02,C03,C07`。 |
| `CODEX_AUDIT_INCLUDED_FINDING_CODES` | 空 | 只审核指定 finding codes，例如 `CONCLUSION_MISMATCH_001`。 |
| `CODEX_AUDIT_EXCLUDED_CHECK_IDS` | 空 | 排除指定 check IDs，例如 `C08,C09,C10,C11`。 |
| `CODEX_AUDIT_PRIORITY_CHECK_IDS` | `C02,C03,C07,C04,C05,C06` | 报告自检 target 优先级；PTR builder 使用 PTR finding code 默认优先级。 |
| `CODEX_AUDIT_TIMEOUT_SECONDS` | `300` | 真实 Codex CLI runner timeout。 |

脚本会：

1. 检查后端健康状态。
2. 上传 PTR/报告任务或报告自检任务。
3. 轮询 `/api/tasks/{task_id}`。
4. 下载 `/api/tasks/{task_id}/result`。
5. 统计 `check_results[].codex_reviews` 数量。
6. 打印 final audit summary：`audit_scope`、`full_audit`、`final_audit_status`、candidate/final/refuted/manual/out-of-scope/unreviewed/runtime failure 计数。
7. 单独打印 legacy deterministic counts：`fail_count`、`error_count`、`warn_count`。这些字段保留兼容，但不代表最终错误。
8. 按 `EXPECT_CODEX_REVIEWS` 校验 `codex_reviews` 是否符合预期。

脚本输出边界：

- 进度日志和任务状态输出到 stderr，格式为 `[codex-audit-local-e2e] ...`。
- 内部用于传递结果 JSON 路径的 stdout 保持为单行文件路径，避免 command substitution 捕获到日志。
- 脚本会校验结果路径非空、存在、不包含换行，并且以 `.json` 结尾。

## 五、任务结果语义

- deterministic rule findings 是候选项，不是最终结论。
- summary 中 `fail_count`、`error_count`、`warn_count` 是 legacy deterministic candidate 计数，保留兼容但不作为最终错误口径。
- summary 中 `confirmed_errors_count`、`manual_review_required_count`、`refuted_findings_count` 和 `final_audit_status` 才是 Codex final audit 口径。
- `final_audit_status=passed` 表示 confirmed error 为 0 且无人工复核项。
- `final_audit_status=needs_manual_review` 表示 confirmed error 为 0，但仍有人工复核项。
- `final_audit_status=failed` 表示存在 Codex confirmed final error。
- `final_audit_status=audit_failed` 表示 Codex runtime failure 或 required candidate 未完成审核。
- `findings` 字段为了兼容仍保留 candidate findings；后端会通过 metadata 写入 `codex_required`、`codex_verdict`、`final_status` 和 `codex_review_id`。
- Codex `confirm` 表示候选 finding 被确认。
- Codex `refute` 表示候选 finding 可能为误报，不应作为最终 ERROR 展示。
- Codex `uncertain` 表示任务可 completed，但该项需要人工复核。
- Codex runtime failure，例如 `CODEX_CLI_UNAVAILABLE`、`CODEX_TIMEOUT`、`CODEX_EXIT_NONZERO` 或输出 invalid，会让业务任务 failed。

## 六、前端展示验收点

前端只展示后端返回的 `codex_reviews`，不重新计算 C01-C11 或 PTR 规则。

代码入口：

- `frontend/src/features/codex-review/components/CodexReviewPanel.tsx`
- `frontend/src/features/ptr-compare/components/PTRResults.tsx`
- `frontend/src/features/report-check/components/ReportResults.tsx`

验收点：

- PTR 结果页会聚合 `result.check_results[].codex_reviews` 并显示 Codex 审核统计。
- 报告自检结果页会聚合 `result.check_results[].codex_reviews` 并显示 Codex 审核统计。
- Finding 关联展示只基于后端返回的 `finding_id`、`finding_code`、`check_id` 和 `codex_reviews`。
- 结果页会区分 candidate errors 与 Codex finalization：`confirmed_errors_count` 才是 Codex 已确认错误，`refuted_findings_count` 不计入最终错误，`manual_review_required_count` 进入人工复核，`out_of_scope_findings_count` 表示本次 targeted validation 未覆盖。
- `add_finding` 只作为 Codex 建议展示，不进入 deterministic findings。
- Codex runtime failed/skipped 不再作为 completed 结果展示；后端任务应失败，上传页显示错误信息。

## 七、安全边界

- 不使用 GPT API client。
- 不调用 OpenAI Responses API 或 Chat API。
- 不把 Codex 审核逻辑写进 router。
- 不修改旧项目目录。
- 不修改 C01-C11 或 PTR 规则算法。
- 不让 Codex 读取项目源码。
- Codex audit 仍使用 `runtime/codex_audit/{task_id}/{package_id}/input/` 受控 workspace。
- `CodexCliRunner` 仍使用 read-only sandbox。
- 仍使用 `codex_review_output.schema.json`。
- `codex_review_output.schema.json` 只使用 Codex/OpenAI structured output 兼容子集；不使用 `uniqueItems`、`allOf`、`if/then/else` 等组合或高风险校验关键字。
- `add_finding` 必须包含 `suggested_finding`、evidence refs 必须存在且属于 target、重复 refs 等复杂 contract 由 `CodexReviewOutputParser` 校验。
- 默认每批最多生成 5 个 Codex audit targets；真实 codex-cli 业务验收建议先用 `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1` 和 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07` 缩小单批范围。
- batching 是性能策略，不是审核范围裁剪；后端 usecase 会继续发后续 batch，不能默认漏审。
- `CODEX_AUDIT_INCLUDED_CHECK_IDS`、`CODEX_AUDIT_INCLUDED_FINDING_CODES` 等筛选参数只用于本地 targeted validation / 调试；结果会标记 `audit_scope=targeted`、`full_audit=false`，不得作为完整产品审核结论。
- Codex runtime failure 会让任务 failed；deterministic findings 仍作为候选证据保留在可诊断链路中，但任务不得 completed。

## 八、T-CODEX-11B 真实验收记录

2026-06-23，用户显式启用真实 codex-cli 本地业务端到端验收，并使用 target 限流只审核 1 个 C07 target。

结果文件：

- `c26e1901-0173-49f5-abce-6a205d077bf3.result.json`

结果摘要：

- `codex_reviews_count: 1`
- `codex_status_counts: {"succeeded": 1}`
- `codex_verdict_counts: {"confirm": 1}`
- `codex_confidence_counts: {"high": 1}`
- `codex_target_type_counts: {"inspection_item": 1}`
- `codex_check_id_counts: {"C07": 1}`
- `codex_finding_code_counts: {"CONCLUSION_MISMATCH_002": 1}`
- `failed_reviews_count: 0`
- `deterministic_findings_count: 5194`

审核结论：

- Codex 确认 C07 规则初判，目标为 `inspection_item`，finding code 为 `CONCLUSION_MISMATCH_002`。
- 审核意见认为序号 3 的检验结果为“符合要求”，单项结论为“/”，而 `rule_context` 给出的期望结论为“符合”，因此支持规则初判。
- deterministic findings 保留，Codex review 没有覆盖原始 finding。

任务状态：

- T-CODEX-11B 验收通过。
- T-CODEX-11 整体完成。
- T-CODEX-12 已完成；本次结果证明单 target 限流可以用于真实 codex-cli report-check 业务验收。

后续风险：

- 当前样本 deterministic findings 数量很大，特别是 `C08=4894` 和 `C10=130`，需要后续单独收敛。
- 本次真实业务验收只覆盖 1 个 C07 target，扩大到更多规则或 PTR target 时仍建议小批量分步验收。

## 九、T-CODEX-MANDATORY-02 targeted validation 记录

2026-06-24，基于用户提供的真实本地结果 `runtime/codex_audit_local_e2e/4cc203b9-a2e5-4c0a-859d-b0aa2a73b069.result.json`，确认该次运行是 C07 targeted validation，不是 full audit。

运行特征：

- 使用 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07`。
- 使用 `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1`。
- `codex_reviews_count=22`，全部 `succeeded`。
- Codex runtime failed/skipped 为 0。
- C07 12 条 candidate 均有 review：`refute=9`、`uncertain=3`。

收口要求：

- 9 条被 Codex `refute` 的 C07 candidate 保留审计痕迹，但不计入 `confirmed_errors_count`。
- 3 条 Codex `uncertain` 的 C07 candidate 进入 `manual_review_required_count`。
- C04/C05/C06/C09 等被筛选排除的 candidate 必须标记为 `out_of_scope`，不能保持静默 `final_status=null`。
- full mandatory audit 不能使用 `included_check_ids` 作为产品默认范围；没有筛选时所有 required candidate 都必须被审核，否则任务应失败。

## 十、T-CODEX-MANDATORY-03 targeted validation 修复记录

2026-06-24，用户运行 C04/C05/C06/C09 targeted validation 后，任务完成且 Codex runtime 全部 succeeded，但暴露出 targeted summary 过滤和 C04/C06 证据语义问题。

本次有效结果：

- task: `35c85ce3-a9bd-4739-9844-456a26149a72`
- `audit_scope=targeted`
- `included_check_ids=["C04","C05","C06","C09"]`
- `unique_findings_count=61`
- `targeted_findings_count=49`
- `targeted_reviews_count=49`
- `codex_reviews_count=55`
- `codex_failed_or_skipped_count=0`
- `unreviewed_required_findings_count=0`
- `null_final_status_count=0`
- `findings_by_final_status`: `confirmed=11`、`refuted=13`、`manual_review_required=25`、`out_of_scope=12`

暴露问题：

- C01/C02/C03/C08/C10/C11 仍生成了 summary reviews，`unexpected_summary_reviews_count=6`。
- C04/C06 的部分 confirm 只确认 “OCR 未识别字段”，不能作为“中文标签本体缺字段或字段不一致”的 final business error。
- 备注为“本次检测未使用”的样品描述部件不应被 confirmed 为缺照片、缺中文标签或标签字段缺失。

修复口径：

- targeted 模式下 summary targets 也必须遵守 `CODEX_AUDIT_INCLUDED_CHECK_IDS`、`CODEX_AUDIT_EXCLUDED_CHECK_IDS` 和 `CODEX_AUDIT_INCLUDED_FINDING_CODES`。
- C04/C06 target metadata 会标记 `evidence_has_label_image_crop`、`evidence_has_full_label_text`、`evidence_has_structured_label_fields`、`evidence_can_verify_label_content`。
- OCR 未识别字段不等于标签缺字段；caption 能证明存在中文标签样张，但不能证明字段内容完整或缺失。
- 没有标签图像、完整标签正文 OCR 或结构化标签字段时，Codex 应返回 `uncertain`；如果返回 `confirm`，finalization 也会防御性降级为 `manual_review_required`。
- C04/C05/C06 中 `is_unused_component=true` 的部件即使被 Codex `confirm`，也不会进入 `confirmed_errors_count`；T-CODEX-EVIDENCE-01 后会记录 `CODEX_CONFIRMED_UNUSED_COMPONENT_GAP` 并标记为 `refuted`。

修复后建议重新运行 C04/C05/C06/C09 targeted validation：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C04,C05,C06,C09 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

重新验收的重点：

- `unexpected_summary_reviews_count` 应为 0。
- C04/C06 中仅 OCR 未识别但无法验证标签本体的项不应计入 `confirmed_errors_count`。
- `is_unused_component=true` 的 C04/C05/C06 项不应计入 `confirmed_errors_count`。
- `codex_failed_or_skipped_count` 仍应为 0；若出现 runtime failure，应按 mandatory audit 语义使任务 failed。

## 十一、T-CODEX-MANDATORY-04 C04 caption / matched OCR 修复记录

T-CODEX-MANDATORY-03 修复后，用户重新运行 C04/C05/C06/C09 targeted validation，主目标已经通过：

- `audit_scope=targeted`
- `included_check_ids=["C04","C05","C06","C09"]`
- `codex_reviews_count=39`
- `targeted_reviews_count=39`
- `unexpected_summary_reviews_count=0`
- `codex_failed_or_skipped_count=0`
- `null_final_status_count=0`
- `unreviewed_required_findings_count=0`
- `confirmed_errors_count=0`
- `confirmed_unverifiable_label_content_count=0`
- `confirmed_unused_component_count=0`

剩余问题是 2 条 C04 `SAMPLE_COMPONENT_LABEL_NOT_FOUND` confirmed WARN：

- sample-row-3：`心脏脉冲电场消融仪-推车`，真实 PDF 有 `№6 心脏脉冲电场消融仪-推车 中文标签样张`。
- sample-row-14：`心脏脉冲电场消融仪-触摸屏连接线缆（30m）（可选）`，真实 PDF 有 `№22 触摸屏连接线缆（30m）（可选） 中文标签样张`。

T-CODEX-MANDATORY-04 后的验收重点：

- C04 target metadata 应区分 `matching_label_caption_candidates` 与 `matching_label_ocr_candidates`。
- 中文标签样张 caption 能证明标签样张存在；caption 存在但缺 matched OCR 时，不应确认标签样张缺失。
- 只有 matched label OCR 属于当前 component 时，才可判断标签字段是否缺失或不一致。
- 如果 Codex 仍对 C04 `SAMPLE_COMPONENT_LABEL_NOT_FOUND` + matching caption + missing matched OCR 返回 `confirm`，finalization 应降级为 `manual_review_required`，并记录 `CODEX_CONFIRMED_LABEL_MISSING_BUT_CAPTION_EXISTS`。

真实 targeted validation 结果：

- 结果文件：`runtime/codex_audit_local_e2e/9a50ae34-f7d6-4dbe-a7ed-9ffb1de0a40d.result.json`。
- 本轮使用 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C04,C05,C06,C09`，因此是 targeted validation，不是 full audit。
- task status: `completed`
- `audit_scope=targeted`
- `unique_findings_count=51`
- `codex_reviews_count=39`
- `targeted_findings_count=39`
- `targeted_reviews_count=39`
- `codex_by_status={"succeeded": 39}`
- `codex_failed_or_skipped_count=0`
- `unexpected_summary_reviews_count=0`
- `null_final_status_count=0`
- `unreviewed_required_findings_count=0`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `confirmed_unverifiable_label_content_count=0`
- `confirmed_unused_component_count=0`
- `confirmed_c04_label_not_found_count=0`
- targeted findings by final status: `manual_review_required=28`、`refuted=11`

结论：

- T-CODEX-MANDATORY-04 targeted validation 通过。
- targeted summary filter 已生效。
- C04/C06 中仅 OCR 不足或标签内容不可验证的 candidate 没有再进入 confirmed。
- “本次检测未使用”部件没有再进入 confirmed。
- 当前仍未做 full audit。

后续如需重复该 targeted validation，可运行：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C04,C05,C06,C09 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

## 十二、Full mandatory Codex audit 真实验收记录

2026-06-25，用户基于真实样本运行 full mandatory Codex audit，本轮未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`，因此不是 targeted validation。

样本与结果：

- 样本：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf`
- 结果文件：`runtime/codex_audit_local_e2e/11417700-a536-4ae0-81ec-a4e74c22c19e.result.json`
- `task_id=11417700-a536-4ae0-81ec-a4e74c22c19e`
- `task_type=report_check`

运行口径：

- task status: `completed`
- `audit_scope=full`
- `full_audit=true`
- `included_check_ids=[]`

关键结果：

- `unique_findings_count=51`
- `candidate_findings_count=51`
- `candidate_errors_count=44`
- `codex_reviews_count=57`
- `codex_by_status={"succeeded":57}`
- `codex_by_verdict={"uncertain":40,"refute":17}`
- `codex_runtime_failure_count=0`
- `null_final_status_count=0`
- `unreviewed_required_findings_count=0`
- `out_of_scope_findings_count=0`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=17`
- `manual_review_required_count=34`
- `final_audit_status=needs_manual_review`

按 check_id 的 final status：

| check_id | manual_review_required | refuted |
| --- | ---: | ---: |
| C04 | 29 | 6 |
| C05 | 0 | 2 |
| C06 | 0 | 1 |
| C07 | 5 | 7 |
| C09 | 0 | 1 |

结论：

- Full mandatory Codex audit 真实验收通过。
- 所有 required candidate 均已完成 Codex finalization。
- 没有 Codex runtime failure。
- 没有 null `final_status`。
- 没有 `out_of_scope`。
- 本轮没有 confirmed final error。
- 当时仍有 34 条 `manual_review_required`；该历史结果已被 T-CODEX-EVIDENCE-03B 的最新 full audit 记录更新。
- 旧 `summary.error_count=44` 和 `fail_count=5` 是 candidate 层统计，不应被理解为最终错误。

05B 收口：

- 后端 summary 会直接暴露 `audit_scope`、`full_audit` 和 `final_audit_status`，不需要前端从 metadata 重新推断。
- local E2E 脚本会打印 final audit counts，并把旧 `fail_count/error_count/warn_count` 输出为 legacy deterministic counts。
- 前端结果页优先显示“Codex 审核完成/未完成”和 final audit counts；`candidate_errors_count` 只作为候选错误展示。

## 十三、T-CODEX-EVIDENCE-01 evidence enhancement 记录

2026-06-25，完成 manual review evidence enhancement。本次不运行真实 Codex CLI，只补强下一轮 full audit 输入证据。

本次补强：

- C04 target 现在包含 sample description row、label caption、matched label crop/page reference、matched OCR text、structured fields 和字段对比。
- C04 caption-only 或 empty OCR 会显式标记证据不足，Codex 应输出 `uncertain`，不能确认标签本体缺字段。
- C04 label-not-found 但中文标签样张 caption 存在时，Codex 应 `refute` 该候选，而不是确认标签样张缺失。
- C04/C05/C06 unused component 防御性 finalization 为 `refuted`，不进入人工复核。
- C07 target 现在包含首页符号说明、完整 InspectionItemGroup rows、actual conclusion candidates/provenance、continuation rows 和 group pages full text。
- C07 item 59 这类 complex matrix table 标记为复杂矩阵表，不按普通 C07 直接 confirmed。

下一轮真实 full audit 建议命令：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

验收重点：

- `confirmed_errors_count` 仍应优先看 final audit 口径。
- C04 有 matched OCR 且字段匹配的 candidate 预计应更多转为 `refute`。
- C04/C05/C06 unused component 不应进入 `manual_review_required`。
- C07 item 142/149 预计应能看到 page_text 中的“符合要求”并更容易转为 `refute`。
- C07 item 59 应保持 complex matrix/manual review，不应普通 C07 confirmed。

## 十四、T-CODEX-EVIDENCE-02 C07 recovery / compact evidence 记录

2026-06-25，完成 C07 result token recovery 与 compact evidence 修复。本次不处理 Codex usage limit，不新增 `CODEX_USAGE_LIMIT_EXCEEDED`，不运行真实 Codex CLI。

背景：

- T-CODEX-EVIDENCE-01 后 full audit 尝试在 C07 item 94 所在 batch 中断。
- workspace 显示 item 94 的结构化 `effective_test_results` 只有 `["——","——"]`，导致 deterministic candidate 推导为 `expected="/"`、`actual="符合"`。
- 但历史 targeted validation 已证明 item 94 应被 Codex refute；page_text 中 12.4.2/12.4.4 附近有“符合要求”，说明根因是 result token 抽取/归组不完整。

本次修复：

- InspectionItemGroup 会记录 original/recovered effective results，并保留 recovery diagnostics/provenance。
- C07 使用 recovered results 重新推导 expected conclusion；item 94/33/41/149 这类已能从 row/page excerpt 恢复“符合要求”的 case 不再作为普通 `CONCLUSION_MISMATCH_001` ERROR。
- 无法稳定恢复但存在疑似 token 时，C07 输出 WARN `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN`，供 mandatory Codex audit 或人工复核继续判断。
- C07 evidence package 只发送 compact rows、recovery metadata 和 item 附近 page_text excerpt；不再重复发送整页 page_text、完整 finding evidence、`source_rows`/`complete_rows` 双份结构。

下一轮真实 full audit 仍使用 mandatory harness：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

验收重点：

- item 94 不应再作为普通 C07 ERROR。
- C07 item 33/41/149 等同类 residual mismatch 应减少或转 WARN。
- C07 evidence package 中应能看到 `recovered_result_tokens`、`compact_rows` 和 item 附近 page_text excerpt。
- 单个 C07 target evidence package 应明显小于此前约 1.4MB 的重复结构。

## 十五、T-CODEX-EVIDENCE-03 C07 finalization / complex matrix 记录

2026-06-25，完成 C07 extraction uncertainty finalization 与 complex matrix 语义修复。本次不运行真实 Codex CLI，不处理 usage limit。

背景：

- 用户运行 C07 targeted validation，task `4380cdc8-ea82-4413-92ce-ba3370ec3f0e`，`included_check_ids=C07`。
- 结果中 10 条 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` WARN 被 Codex `confirm` 后误计入 `confirmed_findings_count`。
- item 59 的 `CONCLUSION_MISMATCH_002` 被计为唯一 confirmed error，但该项是跨多页漏电流/复杂矩阵表，存在列映射和续表歧义。

本次修复：

- `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` 在 Codex verdict 为 `confirm` 或 `uncertain` 时，最终都进入 `manual_review_required`。
- 该类 finding 保留 `codex_verdict` 审计痕迹，并写入 `finalization_reason=CODEX_CONFIRMED_EXTRACTION_UNCERTAINTY`、`review_type=extraction_uncertainty`。
- C07 复杂矩阵/漏电流多页表会标记 `complex_matrix_table=true` 或输出 `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX` WARN，不按普通 `CONCLUSION_MISMATCH_002` confirmed error 处理。
- 简单 C07 business mismatch 不受影响；真实业务错误被 Codex `confirm` 时仍可进入 `confirmed` 和 `confirmed_errors_count`。

下一轮 C07 targeted validation 建议命令：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C07 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

验收重点：

- `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN` 的 Codex confirm 不再增加 `confirmed_findings_count`。
- item 59 不再作为 ordinary C07 confirmed error。
- 若没有新的业务 confirmed error，C07 targeted validation 的 `final_audit_status` 应从 `failed` 转为 `needs_manual_review`。

真实 C07 targeted validation 结果：

- 结果文件：`runtime/codex_audit_local_e2e/004f23d9-bd93-4773-91c4-d1c72acf6208.result.json`。
- 本轮设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07`，因此是 C07 targeted validation，不是 full audit。
- task status: `completed`
- `audit_scope=targeted`
- `full_audit=false`
- `final_audit_status=needs_manual_review`
- `codex_reviews_count=12`
- `codex_runtime_failure_count=0`
- `candidate_findings_count=51`
- `candidate_errors_count=33`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=0`
- `manual_review_required_count=12`
- `out_of_scope_findings_count=39`
- `unreviewed_required_findings_count=0`
- legacy deterministic counts: `fail_count=5`、`error_count=33`、`warn_count=18`

结论：

- T-CODEX-EVIDENCE-03 的 C07 targeted validation 通过。
- Extraction uncertainty 不再被归为 confirmed finding。
- C07 当前没有 confirmed final error。
- C07 的 12 条均为 `manual_review_required`，代表抽取/证据仍需复核，不代表报告错误。
- 之后已重新执行 full audit，结果见下方 T-CODEX-EVIDENCE-03B。

## 十六、T-CODEX-EVIDENCE-03B full mandatory audit 真实验收记录

本轮记录用户提供的真实 full mandatory Codex audit 结果；未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`，因此是 full audit，不是 targeted validation。

样本与结果：

- 样本：`/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf`
- 结果文件：`runtime/codex_audit_local_e2e/53bbeec9-998b-4868-9627-00d9cc3b7ab0.result.json`

关键结果：

- task status: `completed`
- `audit_scope=full`
- `full_audit=true`
- `final_audit_status=needs_manual_review`
- `candidate_findings_count=51`
- `candidate_errors_count=33`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=11`
- `manual_review_required_count=40`
- `out_of_scope_findings_count=0`
- `unreviewed_required_findings_count=0`
- `codex_reviews_count=57`
- `codex_runtime_failure_count=0`

按 final_status：

| check_id | manual_review_required | refuted |
| --- | ---: | ---: |
| C04 | 28 | 7 |
| C05 | 0 | 2 |
| C06 | 0 | 1 |
| C07 | 12 | 0 |
| C09 | 0 | 1 |

结论：

- Full mandatory Codex audit 运行通过。
- 当前没有 confirmed final error。
- 当前审核状态为 `needs_manual_review`。
- 剩余 40 条不是确认错误，而是待复核：C04 标签字段证据不足 28 条，C07 检验项目结构化抽取不确定 12 条。
- C05/C06/C09 当前候选均已被 Codex refute。
- 下一步应做 evidence enhancement，而不是继续改 finalization。

## 十七、T-CODEX-EVIDENCE-04 C04 evidence enhancement 记录

T-CODEX-EVIDENCE-04 已完成 C04 label image crop / matched OCR evidence 增强。本阶段不运行真实 Codex CLI；目标是让下一轮 C04 targeted validation 能基于更完整的分层证据判断。

语义边界：

- `label_caption_candidate` / `matched_label_caption`：证明存在或疑似存在中文标签样张，不证明字段完整。
- `label_page_image_ref` / `label_crop_ref`：提供标签页或 caption bbox crop 引用；如果没有 OCR/text/structured fields，仍不能直接确认字段缺失。
- `matched_label_page_text`：照片页 OCR / PDF page text / caption 周边文本，只能证明页面或 caption 上下文，不能证明标签字段完整。
- `matched_label_caption_text`：caption 文本。
- `matched_label_ocr_text` / `matched_label_fields`：属于当前 component 的标签本体 OCR 正文和结构化字段；这是 Codex 判断字段存在、一致、缺失或冲突的核心证据。
- `matched_label_text`：兼容字段，语义等同于 `matched_label_ocr_text`，不得再承载照片页文本。
- `unmatched_label_ocr_candidates`：保留不相关 OCR 作为诊断，但不得让 `evidence_can_verify_label_content=true`。
- `evidence_can_verify_label_content=false` 时，C04 `SAMPLE_FIELD_MISSING_IN_LABEL` 即使被 Codex `confirm`，finalization 也应进入 `manual_review_required`，而不是 confirmed final error。

下一步真实 C04 targeted validation 建议命令：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C04 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

验收解读：

- 如果 matched OCR/structured fields 证明字段存在且与样品描述一致，预期 Codex 可 `refute` 对应 candidate。
- 如果 matched OCR/structured fields 证明字段缺失或冲突，Codex `confirm` 才能进入 confirmed final issue。
- 如果仍只有 caption/page/crop 而没有可读 OCR 或结构化字段，预期继续 `uncertain` / `manual_review_required`，不代表报告 confirmed error。

## 十八、T-CODEX-EVIDENCE-04B C04 targeted validation 与 metadata 修正记录

用户已运行 C04 targeted validation：

- task_id: `8949ca23-07b6-4f7c-b39c-b428d83daa17`
- `audit_scope=targeted`
- `included_check_ids=C04`
- task status: `completed`
- `codex_reviews_count=35`
- `codex_runtime_failure_count=0`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=7`
- `manual_review_required_count=28`
- `out_of_scope_findings_count=16`

extract summary 显示：

- C04 findings: `35`
- `SAMPLE_FIELD_MISSING_IN_LABEL=28`
- `SAMPLE_COMPONENT_LABEL_NOT_FOUND=7`
- `manual_review_required=28`
- `refuted=7`
- `confirmed=0`
- `has_matching_label_caption_count=33`
- `has_matched_label_crop_count=0`
- `has_matched_label_ocr_count=28`
- `has_matched_structured_fields_count=0`
- `can_verify_label_content_count=28`
- `unused_component_count=5`

本轮结论：

- C04 targeted validation 运行通过，且 C04 当前没有 confirmed final error。
- 28 条 `manual_review_required` 主要是因为缺真正 label crop/OCR/structured fields。
- 04B 已修正 metadata 假阳性：照片页/page text 进入 `matched_label_page_text`，不再触发 `evidence_has_matched_label_ocr=true` 或 `evidence_can_verify_label_content=true`。
- sample-row-14 `触摸屏连接线缆（30m）（可选）` 的 selector 已固定优先匹配 `№22 触摸屏连接线缆（30m）（可选） 中文标签样张`，不再被 `№8 ... 触摸屏 中文标签样张` 短词抢占。

04B 修复后，用户已重新运行 C04 targeted validation：

- result file: `runtime/codex_audit_local_e2e/4ec18d39-7dab-4478-b6c0-d6bc464fd2e7.result.json`
- task_id: `4ec18d39-7dab-4478-b6c0-d6bc464fd2e7`
- task status: `completed`
- `audit_scope=targeted`
- `included_check_ids=C04`
- `final_audit_status=needs_manual_review`
- `codex_reviews_count=35`
- `codex_runtime_failure_count=0`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=7`
- `manual_review_required_count=28`
- `out_of_scope_findings_count=16`
- `unreviewed_required_findings_count=0`

C04 extract 关键结果：

- C04 findings: `35`
- `SAMPLE_FIELD_MISSING_IN_LABEL=28`
- `SAMPLE_COMPONENT_LABEL_NOT_FOUND=7`
- `manual_review_required=28`
- `refuted=7`
- `confirmed=0`
- `has_matching_label_caption_count=35`
- `has_matched_label_image_count=31`
- `has_matched_label_crop_count=0`
- `has_matched_label_ocr_count=0`
- `has_matched_structured_fields_count=0`
- `can_verify_label_content_count=0`
- `unused_component_count=5`

关键修复验证：

- `evidence_has_matched_label_ocr_count` 从旧的 `28` 降为 `0`。
- `evidence_can_verify_label_content_count` 从旧的 `28` 降为 `0`。
- `has_matched_structured_fields_count=0`。
- `has_matched_label_crop_count=0`。
- sample-row-14 正确匹配 `№22 触摸屏连接线缆（30m）（可选）中文标签样张`，不再误匹配 `№8 触摸屏`。

本轮结论：

- T-CODEX-EVIDENCE-04B C04 evidence metadata 语义修复通过。
- 没有真实 OCR/fields 的 C04 项仍保持 `manual_review_required`，未被计为 confirmed error。
- 当前 28 条 `manual_review_required` 是因为仍缺真实 label crop / matched OCR / structured fields，不是 confirmed error。
- 后续应进入 T-CODEX-EVIDENCE-05：label crop / OCR / VLM evidence。
- 后续展示问题：`c04_extract` 中 `component_name` / `sample_description_row` 仍不稳定；前端展示或导出应补 `component_id`、`component_name`、`sample_field_key`、`sample_field_value` 等标准 metadata。

## 十九、T-CODEX-EVIDENCE-05 C04 image input 视觉审核链路

T-CODEX-EVIDENCE-05 已实现 C04 中文标签样张 caption 到 Codex CLI image input 的本地运行链路。本阶段未运行真实 Codex CLI。

运行时行为：

- 报告上传后，后端使用当前 runtime 中的 PDF 副本作为 source PDF，不读取旧项目目录。
- 如果 C04 target 已匹配中文标签样张 caption，evidence builder 会为标签页或 caption bbox 生成 workspace 相对图片路径。
- `EvidencePackageWriter` 会在 `runtime/codex_audit/{task_id}/{package_id}/input/items/` 下渲染 PNG。
- `evidence_package.json` 中只记录 `items/*.png` 等 workspace 相对路径，不记录 `/Users/...` source PDF 绝对路径。
- `CodexAuditService` 会把 workspace 内 PNG 路径传给 runner。
- `CodexCliRunner` 会调用 `codex exec --image items/...png`，并继续使用 read-only sandbox、output schema 和受控 workspace。

C04 target 关键 evidence 字段：

- `label_caption_text`
- `label_page_number`
- `label_image_ref`
- `label_crop_ref`
- `label_visual_input_ref`
- `sample_description_row`
- `expected_label_fields`
- `evidence_has_visual_label_input`

Codex review output metadata 可包含：

- `observed_label_fields`
- `field_comparisons`
- `visual_evidence_quality`

finalization 语义：

- 图片字段与样品描述一致时，Codex 可 `refute` 原 `SAMPLE_FIELD_MISSING_IN_LABEL` candidate。
- 图片清晰且确认字段缺失或冲突时，Codex 可 `confirm`。
- 图片不可读、crop 错误或字段看不清时，应 `uncertain`，最终进入 `manual_review_required`。
- 如果 `visual_evidence_quality=unreadable` 或 `wrong_crop` 但 Codex 返回 `confirm`，后端会防御性降级为 `manual_review_required`。

下一轮真实 C04 targeted validation 可继续使用：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C04 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

重点观察：

- `items/*.png` 是否在 failed/succeeded package workspace 中生成。
- Codex reviews 是否包含 `observed_label_fields`、`field_comparisons`、`visual_evidence_quality`。
- 28 条 C04 `manual_review_required` 是否收敛为 `refute`、`confirm` 或更明确的 `uncertain`。

## 二十、T-CODEX-EVIDENCE-05A strict schema 修复记录

用户运行 C04 visual audit 时，任务 `7b20f4a4-e99e-42c3-9151-3d00b16c259c` 在 Codex structured output schema 校验阶段失败，stderr 返回 `invalid_json_schema`：

- 失败点是 `reviews.items.metadata.observed_label_fields`。
- 该 object 的 `properties` 包含 `component_name`、`model`、`serial_number`、`batch_or_serial`、`production_date`、`expiration_date`，但原 schema 的 `required` 未覆盖所有 key。
- 这说明 Codex 没有完成 C04 视觉审核；该次失败不是报告业务错误，也不是标签图片内容缺失结论。

修复后 schema 使用 strict structured output 形态：

- 每个带 `properties` 的 object 都提供完整 `required`。
- `metadata.required` 包含 `observed_label_fields`、`field_comparisons`、`visual_evidence_quality`。
- `observed_label_fields.required` 包含 `component_name`、`model`、`serial_number`、`batch_or_serial`、`production_date`、`expiration_date`。
- optional 字段用 `type: ["string", "null"]` 或空数组表达，复杂 contract 仍由 `OutputParser` 校验。

当前 runner image input wiring 已存在：`CodexCliRunner` 会把 workspace 内 PNG 作为 `codex exec --image items/...png` 传入，不记录旧项目或本机绝对路径。

下一步应重新运行上一节的 C04 targeted validation 命令，确认不再出现 `invalid_json_schema`。

## 二十一、T-CODEX-EVIDENCE-05A 后 C04 targeted visual audit 尝试

本轮是 C04 targeted validation，设置了 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C04`。本记录只基于用户提供的运行结果；未重新运行真实 Codex CLI。

extract package：

- `runtime/codex_audit_local_e2e/extract_runs/20260626-225213-C04.tar.gz`

运行结果：

- task 未 completed
- `run_exit=1`
- `error_code=CODEX_EXIT_NONZERO`
- failed workspace：`backend/runtime/codex_audit/0ece4dd1-c2db-48b1-8cfa-efd21ea01a80/codex-report-0ece4dd1-c2db-48b1-8cfa-efd21ea01a80-C04-batch-6/input`
- `codex_review_output.schema.json` size：6958 bytes
- `evidence_package.json` size：79034 bytes
- `prompt.md` size：27900 bytes
- stderr tail：`ERROR: You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at 11:40 PM.`

结论：

- 这轮失败不是报告业务错误。
- 这轮失败不是 `invalid_json_schema`；说明 T-CODEX-EVIDENCE-05A 的 strict schema 修复至少没有在本轮复现 schema 拒绝。
- C04 visual evidence 已进入 target metadata，包括 `label_page_image_ref` / `label_visual_input_ref`。
- 由于 Codex usage limit，本轮没有生成最终 result，不能判断 C04 `manual_review_required` 是否下降。
- 后续需要在额度恢复后重新跑 C04 targeted validation。
- 脚本改进点：error extract 中 `task_id` 为 null 时，可从 `workspace_dir` 反推；该问题已由 local E2E error summary 解析记录覆盖。

## 二十二、T-CODEX-EVIDENCE-05 C04 visual targeted validation 通过

额度恢复后，用户重新运行 C04 targeted visual validation，本轮通过。

运行口径：

- task_id：`c1f421db-4757-4041-8b19-c88b8835a941`
- `audit_scope=targeted`
- `included_check_ids=C04`
- `final_audit_status=passed`

关键结果：

- `C04 findings=35`
- `C04 reviews=35`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `manual_review_required_count=0`
- `refuted_findings_count=35`
- `codex_runtime_failure_count=0`
- `failed_or_skipped_reviews_count=0`
- `unreviewed_required_findings_count=0`

结论：

- Codex CLI visual label review 已实际生效。
- C04 的 28 条 `SAMPLE_FIELD_MISSING_IN_LABEL` 均被视觉证据 refute。
- C04 的 7 条 `SAMPLE_COMPONENT_LABEL_NOT_FOUND` 均被视觉证据或 not_applicable 规则 refute。
- 当前 C04 无 confirmed error、无 manual review。

## 二十三、T-CODEX-EVIDENCE-05B 后 full mandatory audit 真实验收

2026-06-28，用户记录 T-CODEX-EVIDENCE-05 后 full mandatory Codex audit 真实验收结果。本轮没有设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`，因此是 full audit，不是 targeted validation。

结果文件：

- `runtime/codex_audit_local_e2e/1958c184-567f-4c56-aaac-4a8c45913d1c.result.json`

运行口径：

- `task_id=1958c184-567f-4c56-aaac-4a8c45913d1c`
- `audit_scope=full`
- `full_audit=true`
- `included_check_ids=[]`

关键结果：

- `final_audit_status=needs_manual_review`
- `unique_findings_count=51`
- `codex_reviews_count=57`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=39`
- `manual_review_required_count=12`
- `out_of_scope_findings_count=0`
- `codex_runtime_failure_count=0`
- `unreviewed_required_findings_count=0`

按 check_id 的最终状态：

| check_id | findings | final status |
| --- | ---: | --- |
| C04 | 35 | 全部 `refuted` |
| C05 | 2 | 全部 `refuted` |
| C06 | 1 | `refuted` |
| C07 | 12 | 全部 `manual_review_required` |
| C09 | 1 | `refuted` |

验收结论：

- Full mandatory Codex audit 运行通过。
- 当前没有 confirmed final error。
- C04 visual label audit 已在 full audit 中生效，35 条 C04 candidate 全部被 `refuted`。
- C05/C06/C09 candidate 也已被 `refuted`。
- 当前唯一剩余的是 C07 的 12 条 `manual_review_required`。
- 下一步不应继续改 C04 或 finalization，应进入 C07 table visual evidence / row crop review。

## 二十四、T-CODEX-EVIDENCE-06A/06B/06C C07 visual evidence 准备

2026-06-28，完成 C07 table visual evidence 的前三段实现。本阶段不运行真实 Codex CLI，不调用 GPT/OpenAI API，不修改 output schema/finalization。

06A 完成内容：

- PyMuPDF table `cells` 坐标进入 `PdfTable.metadata["cell_bboxes"]`。
- `InspectionTableExtractor` 在 `InspectionItem.metadata["visual_geometry"]` 中保存 `table_bbox`、`row_bbox` 和 `field_bboxes.test_result/conclusion/remark`。

06B 完成内容：

- 新增 `C07VisualEvidenceBuilder`。
- C07 target 在存在 `source_pdf_path` 时可生成以下 workspace-local image refs：
  - page image
  - table crop
  - item group crop
  - result column crop
  - conclusion column crop
  - remark column crop
- 无 bbox 时降级为 `visual_review_mode=page_only`，仍提供 page image，并记录 missing bbox reasons。
- 无 `source_pdf_path` 时不生成 image items，metadata 记录 `has_visual_input=false` 和 `source_pdf_path_missing`。
- item 59 或 complex matrix target 使用 `visual_review_mode=complex_matrix_table`，不按普通 row-only target 强判。
- image evidence items 使用 `metadata.codex_image_input=true`、`render_page_number` 和可选 `render_bbox`，由既有 `EvidencePackageWriter` 在 evidence workspace 中 materialize。

06C 完成内容：

- `EvidencePackageWriter` 可将 C07 page/table/item group/result/conclusion/remark image items 写入 workspace-local `items/*.png`。
- `EvidencePackageWriter` 支持 `render_bbox` / `crop_bbox` 裁剪；无 bbox 时渲染整页。
- 缺 `source_pdf_path`、无效页码或无效 bbox 会写入 image materialization diagnostics，不再静默跳过。
- `CodexAuditService` 可从 manifest 收集 C07 materialized PNG relative paths，并传给 runner。
- `CodexCliRunner` command construction 会把多个 C07 PNG 通过 `--image` 传给 `codex exec`，且继续拒绝缺失或越界 image path。
- `PromptBuilder` 已新增 C07 visual review instructions，要求 Codex 同时使用 textual evidence 和 C07 visual images，结合首页符号说明复核检验结果、单项结论、备注和续页行。

边界：

- 06C 本身未执行 C07 targeted real Codex validation。
- 06C 本身未改变 C07 finalization；visual uncertainty 仍不应被当作 confirmed error。

后续已通过 T-CODEX-EVIDENCE-06D 完成 C07 targeted real Codex validation，见下一节。

## 二十五、T-CODEX-EVIDENCE-06D C07 targeted visual audit 真实验收

2026-06-28，用户基于真实样本运行 C07 targeted visual audit，验证 06A/06B/06C 的几何 provenance、visual evidence planning、PNG materialization 和 `--image` handoff。

结果文件：

- `runtime/codex_audit_local_e2e/2e7bbb93-3e7b-4477-8a5f-b1b25487fef0.result.json`
- 导出包：`runtime/codex_audit_local_e2e/c07_visual_runs/20260628-122940.tar.gz`

运行口径：

- `task_id=2e7bbb93-3e7b-4477-8a5f-b1b25487fef0`
- `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07`
- `audit_scope=targeted`
- `included_check_ids=["C07"]`
- `full_audit=false`

关键结果：

- `final_audit_status=needs_manual_review`
- `c07_findings_count=12`
- `c07_reviews_count=12`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=11`
- `manual_review_required_count=1`
- `codex_runtime_failure_count=0`
- `unreviewed_required_findings_count=0`

C07 结果：

- item `3`、`27`、`33`、`41`、`72`、`94`、`121`、`131`、`142`、`149`、`151` 被 Codex visual evidence refute。
- 唯一剩余 manual review 是 item `59`，`code=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`，`visual_review_mode=complex_matrix_table`。
- 当前没有 C07 confirmed final error。
- 真实 `codex exec` 已携带 `--image items/...` 参数，包含 C07 page/table/item-group/result/conclusion/remark 图像输入；item `94` 使用 p72/p73 跨页多张图片。

验收结论：

- T-CODEX-EVIDENCE-06D 验收通过。
- C07 visual evidence 链路有效，`manual_review_required` 从 12 降到 1，`refuted_findings_count` 增加到 11。
- item `59` complex matrix 按预期保留为 manual/specialized matrix review。
- 后续已完成 full mandatory audit 回归复验，见下一节。

## 二十六、T-CODEX-EVIDENCE-06 full mandatory audit 复验

2026-06-28，用户在 T-CODEX-EVIDENCE-06 targeted audit 后重新运行 full mandatory audit。本轮未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`，因此是 full audit，不是 targeted validation。

结果文件：

- `runtime/codex_audit_local_e2e/8e23d5bc-64f5-43c1-a0c5-2e02597840f6.result.json`
- 摘要包：`runtime/codex_audit_local_e2e/full_audit_extract_runs/20260628-133403.summary.tar.gz`

运行口径：

- `task_id=8e23d5bc-64f5-43c1-a0c5-2e02597840f6`
- `audit_scope=full`
- `full_audit=true`
- `included_check_ids=[]`
- `final_audit_status=needs_manual_review`

关键结果：

- `unique_findings_count=51`
- `codex_reviews_count=57`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=50`
- `manual_review_required_count=1`
- `out_of_scope_findings_count=0`
- `codex_runtime_failure_count=0`
- `unreviewed_required_findings_count=0`

按 check_id 的最终状态：

| check_id | findings | final status |
| --- | ---: | --- |
| C04 | 35 | 全部 `refuted` |
| C05 | 2 | 全部 `refuted` |
| C06 | 1 | `refuted` |
| C07 | 12 | 11 条 `refuted`，1 条 `manual_review_required` |
| C09 | 1 | `refuted` |

唯一剩余人工复核：

- C07 item `33`
- `code=CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN`
- 原因：视觉表格显示 item 33 首行检验结果为“——”，其下续行“分类是 IPX0 或 IP0X 的 ME 设备不需要标记。”对应检验结果列可见“符合要求”；结构化结果仅保留“——”确有遗漏，需人工/视觉复核后判断，且单项结论“符合”与可见非空合格结果一致。
- 当前没有 confirmed final error。

复验结论：

- T-CODEX-EVIDENCE-06 full audit 复验通过。
- C04/C05/C06/C09 全部被 Codex refute。
- C07 12 条中 11 条被 refute。
- 当前全量审核仅剩 C07 item `33` 待人工复核。
- 当时下一步建议单独做 T-CODEX-EVIDENCE-06E：比较 targeted C07 与 full audit 对 item `33` 的 evidence、prompt、image refs 和视觉裁决差异，提升 extraction-uncertain 的 refute 稳定性；该 targeted validation 结果已记录在后续 06E 章节。

## 二十七、T-CODEX-EVIDENCE-06E item 33 closeout 诊断与修复

2026-06-28，完成 C07 item `33` residual manual review closeout 的代码侧修复。本阶段不运行真实 Codex CLI，不修改 finalization，不硬编码 item `33`。

本地诊断 helper：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

python scripts/compare-codex-c07-item-evidence.py \
  --targeted-task-id 2e7bbb93-3e7b-4477-8a5f-b1b25487fef0 \
  --full-task-id 8e23d5bc-64f5-43c1-a0c5-2e02597840f6 \
  --item-no 33
```

诊断结论：

- targeted 与 full 的 item `33` 均在 C07 batch `2`。
- `finding_code` 均为 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN`。
- `allowed_evidence_refs` 归一化后一致。
- `target.metadata.c07_visual_evidence` 归一化后一致。
- materialized image files 归一化后一致，均包含 page image 和 table image。
- 旧 prompt 缺少 extraction-uncertain 的明确 refute 条件。
- targeted verdict 为 `refute`，full verdict 为 `confirm`；full reasoning 仍说明视觉表格可见续行“符合要求”且单项结论“符合”一致，因此根因是 prompt 对 extraction-uncertain 的裁决语义不够稳定，不是 image refs 丢失。

本次修复：

- C07 item group crop 现在会用续行字段 bbox fallback 扩展 union，避免续行没有 `row_bbox` 时只裁首行。
- C07 visual prompt 明确：对 `CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN`，视觉证据足以判断结论合理时应 `refute`；不能仅因结构化抽取遗漏存在就 `confirm/manual`；同一 item group 续行中的“符合要求”应作为有效检验结果；只有图像无法稳定读取或无法确认 result token 属于该 group 时才 `uncertain`。

下一步真实验收建议先跑 C07 targeted visual audit：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C07 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8023 \
BASE_URL=http://127.0.0.1:8023 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

验收关注：

- item `33` 是否稳定 `refute`。
- C07 `manual_review_required_count` 是否保持 0 或仅剩有充分证据的专项复核项。
- `confirmed_errors_count` 是否仍为 0。
- `codex_runtime_failure_count` 是否为 0。

## 二十八、T-CODEX-EVIDENCE-06E C07 targeted validation 真实验收

2026-06-28，用户按 06E closeout 后的 C07 targeted validation 脚本重新运行真实 Codex CLI visual audit。本轮设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07`，因此是 targeted validation，不是 full audit。

本轮结果文件：

`runtime/codex_audit_local_e2e/a39b2841-e44d-4efd-a004-ae3147a2c1d6.result.json`

摘要文件：

`runtime/codex_audit_local_e2e/c07_06e_runs/20260628-182451/paste_to_chatgpt.md`

关键结果：

- `task_id=a39b2841-e44d-4efd-a004-ae3147a2c1d6`
- `audit_scope=targeted`
- `included_check_ids=["C07"]`
- `final_audit_status=passed`
- `c07_findings_count=12`
- `c07_reviews_count=12`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `manual_review_required_count=0`
- `refuted_findings_count=12`
- `codex_runtime_failure_count=0`
- `unreviewed_required_findings_count=0`

全部 C07 item 均已 refuted：

`3, 27, 33, 41, 59, 72, 94, 121, 131, 142, 149, 151`

结论：

- T-CODEX-EVIDENCE-06E targeted validation 验收通过。
- item `33` residual manual review 已收口。
- C07 targeted visual audit 当前无 confirmed error、无 manual review、无 runtime failure。
- 当时下一步应执行 full mandatory audit 复验，目标为 `confirmed_errors_count=0`、`manual_review_required_count=0`、`refuted_findings_count=51`、`final_audit_status=passed`；实际 full audit 复验结果见下一节。

## 二十九、T-CODEX-EVIDENCE-06E 后 full mandatory audit 复验

2026-06-28，用户在 T-CODEX-EVIDENCE-06E targeted validation 后重新运行 full mandatory audit。本轮未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`，因此是 full audit，不是 targeted validation。

本轮结果文件：

`runtime/codex_audit_local_e2e/bf36101c-71a4-4f69-9df9-907ced1000cb.result.json`

关键结果：

- `task_id=bf36101c-71a4-4f69-9df9-907ced1000cb`
- `audit_scope=full`
- `full_audit=true`
- `final_audit_status=needs_manual_review`
- `codex_reviews_count=57`
- `candidate_findings_count=51`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=50`
- `manual_review_required_count=1`
- `codex_runtime_failure_count=0`
- `unreviewed_required_findings_count=0`

唯一剩余 manual review：

- `check_id=C07`
- `code=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`
- `severity=warn`
- `item_no=59`
- `codex_verdict=uncertain`
- `confidence=medium`
- reasoning：视觉证据显示序号 `59` 为 8.7 漏电流多页复杂矩阵，页内可见多项数值/占位结果且单项结论列为“符合”，但跨页续表与矩阵列映射仍需专门判读；`rule_context` 也标记 `complex_matrix_table=true`，因此不按普通 C07 直接裁决。

结论：

- T-CODEX-EVIDENCE-06E 已收口 item `33` residual manual review。
- 当前 full audit 没有 confirmed final error。
- C04/C05/C06/C09 已全部 refuted。
- C07 普通视觉复核项已基本收口。
- 当前唯一剩余是 item `59` complex matrix，保留 `manual_review_required` 符合安全口径。
- 不应通过修改 finalization 强行让 item `59` passed。
- 下一步建议新增 T-CODEX-EVIDENCE-07：item 59 complex matrix specialized review。

## 三十、T-CODEX-EVIDENCE-07 item 59 complex matrix specialized review 规划

2026-06-28，新增 T-CODEX-EVIDENCE-07 规划文档：

`docs/superpowers/plans/2026-06-28-t-codex-evidence-07-c07-complex-matrix-specialized-review.md`

本轮只做规划，不实现代码，不修改 finalization，不运行真实 Codex CLI，不调用 GPT/OpenAI API，不修改旧项目目录。

规划目标：

- 为 C07 item `59` 的 8.7 漏电流多页复杂矩阵表建立 specialized matrix review。
- 不再用普通 C07 row-level 单项结论逻辑强判 complex matrix。
- 不把 item `59` 硬编码为 `refuted`。
- 不把 complex matrix `uncertain` 当作系统失败。

规划的 visual evidence：

- full page images
- matrix table crops
- row header crops
- column header crops
- result matrix crops
- conclusion column crops
- cross-page continuation crops

规划的 structured evidence：

- item group rows
- page numbers
- table headers
- condition columns
- measured values
- placeholder cells
- conclusion candidates

Prompt 设计：

- 先识别矩阵表结构。
- 再判断“符合”结论是否由矩阵结果支持。
- 如果列映射、续表归属或 result-to-conclusion 支持关系仍不清楚，应返回 `uncertain`。
- 只有视觉矩阵证据明确证明报告结论不被支持或不一致时才 `confirm`。

真实验收计划：

1. 先跑 targeted item `59`。
2. targeted 通过或形成稳定 manual 后，再跑 full mandatory audit。

targeted item `59` 建议命令口径：

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C07 \
CODEX_AUDIT_INCLUDED_FINDING_CODES=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8023 \
BASE_URL=http://127.0.0.1:8023 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

验收标准：

- 如果视觉矩阵证据足够并支持单项结论“符合”，可 refute 原 complex-matrix candidate。
- 如果矩阵列映射仍不稳定，应继续 `manual_review_required`。
- `confirmed_errors_count` 必须保持 0，除非视觉证据明确证明业务错误。
- `codex_runtime_failure_count` 必须为 0。

## 三十一、T-CODEX-EVIDENCE-07A complex matrix evidence contract

2026-06-28，完成 T-CODEX-EVIDENCE-07A 的代码侧 evidence contract，不运行真实 Codex CLI。

本次只做：

- 新增 `C07ComplexMatrixEvidenceBuilder`。
- 为 C07 item `59` / `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX` 这类 complex matrix target 构建 `c07_complex_matrix_evidence`。
- 生成 workspace-local relative image refs，例如：
  - `items/<safe-id>-c07-matrix-page-p42.png`
  - `items/<safe-id>-c07-matrix-table-p42.png`
  - `items/<safe-id>-c07-matrix-header-p42.png`
  - `items/<safe-id>-c07-matrix-body-p42.png`
  - `items/<safe-id>-c07-matrix-result-p42.png`
  - `items/<safe-id>-c07-matrix-conclusion-p42.png`
  - `items/<safe-id>-c07-matrix-continuation-p43.png`
- 在 image `EvidenceItem.metadata` 中记录 `codex_image_input=true`、`render_page_number`、`render_bbox/crop_bbox` 和 `matrix_evidence_role`。
- 提供 `structured_matrix_hints`：`item_no`、`pages`、`group_row_count`、`continuation_markers`、`source_rows`、`effective_test_results`、`actual_conclusion_candidates`、`complex_matrix_table`、`complex_matrix_reason`、`known_columns`、`placeholder_tokens`、`non_placeholder_tokens`、`candidate_conclusion`。

本次没有做：

- 没有修改 PromptBuilder。
- 没有修改 Codex output schema。
- 没有修改 finalization。
- 没有运行真实 Codex CLI。
- 没有调用 GPT/OpenAI API。
- 没有修改旧项目目录。

下一步应执行 T-CODEX-EVIDENCE-07B：complex matrix prompt instructions 和 materialization/handoff 测试；之后再做 targeted item 59 真实验收。

## 三十二、T-CODEX-EVIDENCE-07B complex matrix materialization / handoff / prompt contract

2026-06-28，完成 T-CODEX-EVIDENCE-07B 的代码侧 contract，不运行真实 Codex CLI，不运行 local E2E。

本次完成：

- Matrix image EvidenceItem materialization 测试：
  - `c07-matrix-page`
  - `c07-matrix-table`
  - `c07-matrix-header`
  - `c07-matrix-body`
  - `c07-matrix-result`
  - `c07-matrix-conclusion`
  - `c07-matrix-continuation`
- `EvidencePackageWriter` 会将这些 image items 渲染为 workspace-local `items/*.png`，manifest 只记录相对路径。
- 缺 source PDF 或 invalid bbox 时记录 `image_materialization_diagnostics`，不静默跳过。
- `CodexAuditService` 可从 manifest 收集 item 59 complex matrix PNG paths，并传给 runner；paths 位于 controlled workspace 内，不包含原始 source PDF 路径。
- `CodexCliRunner` 多图 handoff 已由测试验证，会用 `--image items/...` 传递 matrix PNG，相对路径不会泄露 workspace 绝对路径。
- `PromptBuilder` 增加 `C07 Complex Matrix Review Instructions`，只对 complex matrix target 生效。

Prompt 重点：

- 先识别矩阵结构，再判断单项结论。
- 必须查看 full page images、matrix table crops、row/column header crops、result matrix crops、conclusion column crops、cross-page continuation crops。
- 识别漏电流/患者辅助电流、正常状态/单一故障状态、B/BF/CF 或应用部分相关列、测量值、限值、占位符、单项结论列和续页归属。
- 视觉证据足以确认“符合”结论由矩阵结果支持时，应 `refute` 原 complex-matrix candidate。
- 视觉证据显示矩阵结果与“符合”冲突时，可以 `confirm`。
- 列映射、跨页续表或矩阵结果仍不清楚时，应 `uncertain`。
- 不因为 `rule_context` 写了 `complex_matrix_table=true` 就自动 `uncertain`。
- 不按普通 C07 all-placeholder 逻辑直接 `confirm/refute`。

本次没有做：

- 没有运行真实 Codex CLI。
- 没有运行 local E2E。
- 没有修改 output schema。
- 没有修改 finalization。
- 没有修改 C07 deterministic rule。
- 没有修改 frontend/router。
- 没有修改旧项目目录。

下一步：T-CODEX-EVIDENCE-07C，targeted item 59 complex matrix 真实验收。

## 三十三、T-CODEX-EVIDENCE-07C targeted item 59 与 full audit 最终复验

2026-06-29，用户已完成 item 59 complex matrix targeted validation，并随后完成 full mandatory audit 最终复验。本节只记录真实运行结果，不修改业务代码、不运行额外 Codex。

### Targeted item 59 validation

结果文件：

`runtime/codex_audit_local_e2e/4b15adbb-6e4e-4a66-99e7-9170843b3646.result.json`

运行范围：

- `CODEX_AUDIT_INCLUDED_CHECK_IDS=C07`
- `CODEX_AUDIT_INCLUDED_FINDING_CODES=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`
- `audit_scope=targeted`

关键结果：

- `task_id=4b15adbb-6e4e-4a66-99e7-9170843b3646`
- `task status=completed`
- `final_audit_status=passed`
- `codex_reviews_count=1`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=1`
- `manual_review_required_count=0`
- `codex_runtime_failure_count=0`

item 59 结论：

- `check_id=C07`
- `code=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`
- final status 为 `refuted`
- Codex review `status=succeeded`
- Codex verdict 为 `refute`
- Codex confidence 为 `high`

Codex reasoning 摘要：跨页矩阵视觉证据显示 item 59 为同一漏电流/患者辅助电流项目，检验结果列含有效数值与适用的“——”占位；单项结论列在该项目跨页区域可见为“符合”，备注列为“/”。规则候选把“/”当作实际结论，与视觉列位置冲突。

### Full mandatory audit final validation

结果文件：

`runtime/codex_audit_local_e2e/8e84b3e7-e079-4e6f-ac7f-b99348f18ffa.result.json`

运行范围：

- 未设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`
- 未设置 `CODEX_AUDIT_INCLUDED_FINDING_CODES`
- 未设置 `CODEX_AUDIT_EXCLUDED_CHECK_IDS`
- `audit_scope=full`
- `full_audit=true`

关键结果：

- `task_id=8e84b3e7-e079-4e6f-ac7f-b99348f18ffa`
- `task status=completed`
- `final_audit_status=passed`
- `candidate_findings_count=51`
- `codex_reviews_count=57`
- `confirmed_findings_count=0`
- `confirmed_errors_count=0`
- `refuted_findings_count=51`
- `manual_review_required_count=0`
- `out_of_scope_findings_count=0`
- `unreviewed_required_findings_count=0`
- `codex_runtime_failure_count=0`

按 check_id 最终状态：

- C04：`refuted=35`
- C05：`refuted=2`
- C06：`refuted=1`
- C07：`refuted=12`
- C09：`refuted=1`

结论：

1. T-CODEX-EVIDENCE-07 后 full mandatory Codex audit 最终复验通过。
2. 当前真实样本 `QW2025-2795 Draft.pdf` 没有 confirmed final error。
3. 当前没有 `manual_review_required`。
4. 51 条 deterministic candidate findings 全部被 Codex final audit refute。
5. C07 item 59 complex matrix specialized review 已在 full audit 中生效。
6. 报告自检主线在该真实样本上达到 `final_audit_status=passed`。

## 三十四、失败 error_summary 解析

任务进入 `status=error` 时，local E2E 脚本不会生成 result JSON。脚本会在 `OUTPUT_DIR` 写入 `error_summary.json`，用于记录失败恢复信息。

`error_summary.json` 包含：

- `task_id`
- `task_status`
- `progress`
- `current_step`
- `error_code`
- `retry_after_text`
- `workspace_dir`
- `package_id`
- `check_id`
- `batch_id`

解析策略：

- 如果 task status JSON 中没有 `task_id`，脚本会从 `runtime/codex_audit/{task_id}/{package_id}/input` 反推 task id。
- 如果 workspace 中的 package id 形如 `codex-report-{task_id}-C04-batch-6`，脚本会提取 `check_id=C04` 和 `batch_id=batch-6`。
- 如果 stderr 或 diagnostics 中包含 `You've hit your usage limit` / `usage limit` / `try again at`，脚本会把 `error_code` 归类为 `CODEX_USAGE_LIMIT_EXCEEDED`，并尽量提取 `retry_after_text`。
- mandatory 原则不变：Codex runtime failure 仍然让 task failed，`error_summary.json` 只用于诊断和重试提示。

usage limit 失败时终端只打印简洁提示：

- `Codex usage limit reached.`
- `Retry after: <retry_after_text>`
- `Failed workspace: <workspace_dir>`
- `Result JSON was not produced.`

## 三十五、性能画像与 batch/parallel 输出

2026-06-29，T-PERF-01 至 T-PERF-04 已补齐本地 E2E 的性能可观测字段和高级参数显示。本节记录脚本行为；不代表已经完成真实 Codex 性能对比。

`--print-config` 会输出：

- `codex_audit_max_targets_per_batch`
- `codex_audit_max_parallel_jobs`
- include/exclude check/finding filters
- timeout 和 Codex CLI path

默认推荐：

- full mandatory audit 默认 `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=5`。
- `CODEX_AUDIT_MAX_PARALLEL_JOBS` 默认 `1`，保持串行兼容；真实提速验证时再显式设为 `2`。
- 不设置 `CODEX_AUDIT_INCLUDED_CHECK_IDS`、`CODEX_AUDIT_INCLUDED_FINDING_CODES`、`CODEX_AUDIT_EXCLUDED_CHECK_IDS` 时才是 full audit。

脚本运行完成后，如果 result JSON 中存在 `metadata.performance_profile`，会打印简洁摘要：

- `performance total seconds`
- 每个主阶段耗时，例如 `codex_audit_total`
- package 汇总，例如 package count、target count、`codex_exec_seconds`、image count 和 image bytes
- `effective batch size`

如果 full audit 使用 `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1`，脚本会提示：

- `batch_size_warning: full audit batch=1 is debug/slow mode`

该提示只说明性能模式偏慢，不改变 mandatory audit 结论。真实性能对比应使用 full audit、无 include/exclude filters、effective batch=5，并继续要求：

- `final_audit_status=passed`
- `confirmed_errors_count=0`
- `manual_review_required_count=0`
- `codex_runtime_failure_count=0`

## 三十六、report-check 细粒度进度展示

2026-07-01，T-UX-PROGRESS-01 已补齐任务状态的前端可解释进度。本节记录展示字段；不代表已经运行真实 Codex CLI。

`GET /api/tasks/{task_id}` 的 `TaskStatus` 现在可包含：

- 顶层 `progress_details`
- 兼容副本 `metadata.progress_details`

`progress_details` 只用于展示，不参与 finalization。主要字段包括：

- `phase`：`upload`、`parse`、`extract`、`rules`、`evidence`、`codex_audit`、`finalize`、`completed`、`error`
- `phase_label`：中文阶段名
- `current_check_id` / `current_check_name`
- `checks[]`：C01-C11 checklist，含 `pending/running/passed/failed/skipped/needs_review/error`
- `codex_audit`：Codex 复核进度，含 current check、target type、completed/total reviews、completed/total batches、retry count、last retry reason、batch size

report-check 阶段进度建议口径：

- upload/task created：0-5
- parse PDF：5-15
- extract report structures：15-25
- deterministic rules C01-C11：25-45
- evidence build / image materialization：45-60
- Codex audit：60-95
- finalization：95-100

前端 `ProgressOverlay` 会优先展示 `progress_details`：

- 当前阶段。
- C01-C11 检查清单，包括 skipped。
- Codex 当前 check / target type。
- Codex review 进度和 batch 进度。
- missing-target retry 显示为“正在重试缺失复核项”。

错误文案：

- `CODEX_OUTPUT_MISSING_TARGET`：显示为“LLM 复核未完成”，并说明这不是报告确认错误。
- `CODEX_TIMEOUT`：显示为“LLM 复核超时”，并说明这不是报告确认错误。
- `CODEX_CLI_UNAVAILABLE`：显示为“本机 Codex CLI 不可用”，并说明这不是报告确认错误。
- 原始错误仍保留在高级详情。

## 二十八、排查

- 脚本被拒绝：确认已设置 `ENABLE_CODEX_AUDIT_LOCAL_E2E=1`。`--help` 和 `--print-config` 不需要 gate。
- `CODEX_CLI_UNAVAILABLE`：确认本机安装 Codex CLI，且 `CODEX_CLI_PATH` 或 `codex` 在 `PATH`。
- `CODEX_TIMEOUT`：优先降低 batch size，例如先设置 `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 CODEX_AUDIT_INCLUDED_CHECK_IDS=C07 CODEX_AUDIT_TIMEOUT_SECONDS=300`。
- `CODEX_EXIT_NONZERO` 且 stderr 出现 `invalid_json_schema`：优先检查 `codex_review_output.schema.json` 是否误用了 Codex structured output 不支持的 JSON Schema 关键字，或是否有 object 的 `required` 未覆盖所有 `properties` key。
- `CODEX_USAGE_LIMIT_EXCEEDED`：等待 `retry_after_text` 指定时间后重试；当前任务失败且不会生成 final audit result JSON。
- `CODEX_OUTPUT_SCHEMA_INVALID` 或 `CODEX_OUTPUT_INVALID_JSON`：查看 `runtime/codex_audit/{task_id}/.../input/codex_review_output.json` 和 `prompt.md`；复杂 contract 失败会由 OutputParser 转成 failed review，再由 usecase 上升为 task failed。
- 后端无法启动：确认已安装后端依赖，运行 `cd backend && python -m pip install -e ".[dev]"`。
- 前端无展示：确认后端 result JSON 中确实有 `codex_reviews`，前端只展示后端结果，不会自行生成审核意见。
