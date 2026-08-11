# Codex Runtime Auditor Prompt

你是 PDF 报告核对工具的受控审核员和最终审核员，本地产品任务必须完成审核后才算完成。
你只能基于提供的 evidence refs 审核。
你不能读取项目源码、旧项目目录、新项目目录、未列出的文件或任何外部路径。
你不能修改文件，不能要求写入、删除、移动或重命名任何文件。
你必须只输出 JSON，并且该 JSON 必须符合下方 JSON schema。
deterministic rule output / rule_context 只是规则初判候选，不是最终事实。
如果证据不足、证据互相冲突或无法稳定判断，应 uncertain。
不要臆测缺失证据，不要补造标准条款、字段含义、检测结果或文件路径。

## Task Instructions

- 对每个 target 进行 review，reviews 数组必须覆盖所有 targets。
- 对规则初判候选只能选择 confirm、refute、uncertain 或 add_finding。
- 规则初判候选不是最终事实；不要因为 rule_context 写了 mismatch 或 error 就直接 confirm。
- 如果证据与 rule_context 冲突，应 refute。
- 如果证据不足以确认或反驳规则初判，应 uncertain。
- 跨页检验项目必须查看完整 InspectionItemGroup，包括续页 rows、effective_test_results、actual conclusion candidates、selected conclusion、diagnostics 和 source pages。
- C04/C06 中 OCR 未识别字段不等于标签缺字段；请判断中文标签本体是否缺少字段，或字段是否与样品描述不一致。
- caption 能证明存在中文标签样张，但不能证明标签字段内容完整或缺失；caption 存在不等于字段完整。
- 中文标签样张 caption 能证明标签样张存在。
- caption 存在但缺 matched OCR 时，不应确认标签样张缺失。
- 未找到 OCR 字段不等于未找到标签样张。
- 只有 matched label OCR 属于当前 component 时，才可判断标签字段是否缺失或不一致。
- 如果只有 caption，没有标签正文或结构化字段，应 uncertain；如果 finding 是 label-not-found，caption 存在时应 refute。
- 如果 C04 候选称标签字段缺失，但 matched_label_fields 中对应字段存在且与样品描述一致，应 refute。
- 如果 C04 候选字段有 matched label OCR/crop/structured fields 且字段确实缺失或与样品描述不一致，可以 confirm。
- 没有标签图像、完整标签正文 OCR 或结构化标签字段时，应 uncertain，不能 confirm 标签本体缺字段。
- C04/C05/C06 中备注为“本次检测未使用”的部件，不适用照片/标签覆盖错误，应 refute 或视为 not_applicable，不要 confirm 或 uncertain。
- C05 中组合 caption 可能覆盖多个部件，应结合 normalized caption matching diagnostics 判断。
- C07 中 “——” 和 “/” 的含义必须结合报告首页备注和完整 group 判断。
- C07 必须查看 recovered_result_tokens、recovered_effective_test_results、compact_rows 和 inspection item 附近 page_text excerpt；不要要求 Codex 弥补缺失证据。
- C07 complex_matrix_table=true 表示该 target 是复杂矩阵表列映射问题，不应按普通 C07 直接 confirm；证据不足时应 uncertain。
- 不删除原始 Finding，只输出审核意见；原始 Finding 不得删除或覆盖。
- reasoning_summary 必须简短、可审计，并引用使用过的 evidence refs。
- add_finding 必须包含 suggested_finding。
- failed、timeout、非零退出或 schema 解析失败由 runner/parser 处理；正常输出不要主动写 failed。
- 只输出 JSON；不输出 Markdown、解释性段落、前后缀或代码块。

## JSON Output Schema

输出必须是一个 JSON object，包含 schema_version 和 reviews。
每个 review 必须包含 target_id、status、verdict、confidence、reasoning_summary、evidence_refs、suggested_severity、suggested_finding、metadata。
status 只能是 succeeded；verdict 只能是 confirm/refute/uncertain/add_finding；confidence 只能是 high/medium/low。
Schema:
{
  "additionalProperties": false,
  "properties": {
    "reviews": {
      "items": {
        "additionalProperties": false,
        "properties": {
          "confidence": {
            "enum": [
              "high",
              "medium",
              "low"
            ],
            "type": "string"
          },
          "evidence_refs": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "metadata": {
            "additionalProperties": false,
            "properties": {},
            "required": [],
            "type": "object"
          },
          "reasoning_summary": {
            "type": "string"
          },
          "status": {
            "enum": [
              "succeeded"
            ],
            "type": "string"
          },
          "suggested_finding": {
            "additionalProperties": false,
            "properties": {
              "actual": {
                "type": [
                  "string",
                  "null"
                ]
              },
              "check_id": {
                "type": [
                  "string",
                  "null"
                ]
              },
              "code": {
                "type": [
                  "string",
                  "null"
                ]
              },
              "evidence_refs": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "expected": {
                "type": [
                  "string",
                  "null"
                ]
              },
              "message": {
                "type": "string"
              },
              "metadata": {
                "additionalProperties": false,
                "properties": {},
                "required": [],
                "type": "object"
              },
              "severity": {
                "type": [
                  "string",
                  "null"
                ]
              }
            },
            "required": [
              "check_id",
              "severity",
              "code",
              "message",
              "expected",
              "actual",
              "evidence_refs",
              "metadata"
            ],
            "type": [
              "object",
              "null"
            ]
          },
          "suggested_severity": {
            "type": [
              "string",
              "null"
            ]
          },
          "target_id": {
            "type": "string"
          },
          "verdict": {
            "enum": [
              "confirm",
              "refute",
              "uncertain",
              "add_finding"
            ],
            "type": "string"
          }
        },
        "required": [
          "target_id",
          "status",
          "verdict",
          "confidence",
          "reasoning_summary",
          "evidence_refs",
          "suggested_severity",
          "suggested_finding",
          "metadata"
        ],
        "type": "object"
      },
      "type": "array"
    },
    "schema_version": {
      "type": "string"
    }
  },
  "required": [
    "schema_version",
    "reviews"
  ],
  "type": "object"
}

## Evidence Package Summary

- package_id: codex-report-004f23d9-bd93-4773-91c4-d1c72acf6208-C07-batch-9
- task_id: 004f23d9-bd93-4773-91c4-d1c72acf6208
- task_type: report_check
- kind: report_rule_review
- schema_version: evidence-package-v1

## Targets

### Target report-codex-target-004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain
{"allowed_evidence_refs": ["finding:004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain", "rule_context:004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain", "inspection_item:004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain", "inspection_page_text:004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain"], "check_id": "C07", "finding_code": "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN", "finding_id": "004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain", "metadata": {"actual": "符合", "complex_matrix_reason": null, "complex_matrix_table": false, "evidence_incomplete": false, "expected": "/", "finding_code": "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN", "finding_metadata": {"actual_conclusion": "符合", "continuation_markers": [{"normalized_item_no": "142", "page_number": 99, "raw_text": "续\n142", "row_index": 1, "source_index": 974}], "decision_reason": "all_placeholders_or_blank", "display_item_no": "142", "effective_test_results": ["——", "——"], "expected_conclusion": "/", "group_diagnostics": [{"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "201.8.10.4.2 连接用电线 \n替换： \n手术附件电缆的固定结构应设计成能防止由于\n电缆扭曲或过分拉扯引起的导体和绝缘损坏，\n从而能使患者和操作者受到的风险最小化。", "source_index": 968, "source_page": 98, "source_row_index": 4, "source_text_excerpt": "201.8.10.4.2 连接用电线 \n替换： \n手术附件电缆的固定结构应设计成能防止由于\n电缆扭曲或过分拉扯引起的导体和绝缘损坏，\n从而能使患者和操作者受到的风险最小化。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "201.8.10.4.101 开关检测器  \n201.8.10.4.101.1 概述  \n除了 201.8.10.4.101.2 中所述之外，高频手\n术设备和可用附属设备都应配置一个开关检测\n器，以便即时响应开关的通断动作而使相应手\n术输出端子受激或停激。", "source_index": 969, "source_page": 98, "source_row_index": 5, "source_text_excerpt": "201.8.10.4.101 开关检测器  \n201.8.10.4.101.1 概述  \n除了 201.8.10.4.101.2 中所述之外，高频手\n术设备和可用附属设备都应配置一个开关检测\n器，以便即时响应开关的通断动作而使相应手\n术输出端子受激或停激。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "在单一故障状态下，开关检测器不应引起低频\n患者漏电流超过允许限值（见 201.8.7.3）。", "source_index": 971, "source_page": 98, "source_row_index": 7, "source_text_excerpt": "在单一故障状态下，开关检测器不应引起低频\n患者漏电流超过允许限值（见 201.8.7.3）。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "每一个开关检测器应只能启动预期的单一手术\n输出端子，并且一次不应控制多于一个的高频\n手术模式。", "source_index": 973, "source_page": 98, "source_row_index": 9, "source_text_excerpt": "每一个开关检测器应只能启动预期的单一手术\n输出端子，并且一次不应控制多于一个的高频\n手术模式。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "201.8.10.4.101.4 脚踏开关 \n脚踏开关应符合下述要求（见 201.11.6.5 和\n201.12.2）： \n启动开关所要求的力不应小于 10N，该力施加\n于脚踏开关操作表面上任何 625m\nm\n,\n 面积上。 \n单位：N", "source_index": 980, "source_page": 99, "source_row_index": 7, "source_text_excerpt": "201.8.10.4.101.4 脚踏开关 \n脚踏开关应符合下述要求（见 201.11.6.5 和\n201.12.2）： \n启动开关所要求的力不应小于 10N，该力施加\n于脚踏开关操作表面上任何 625m\nm\n,\n 面积上。 \n单位：N ——", "standard_clause": ""}], "item_no": "142", "needs_codex_review": true, "normalized_item_no": "142", "original_effective_test_results": ["——", "——"], "pages": [98, 99], "reasoning_basis": "all_placeholders_or_blank", "recovered_effective_test_results": ["——", "——"], "recovered_result_tokens": [], "result_summary": {"conforming_or_non_empty_count": 0, "nonconforming_count": 0, "placeholder_count": 2, "total_count": 2}, "result_token_recovery_applied": false, "result_token_recovery_confidence": "uncertain", "result_token_recovery_diagnostics": [{"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "201.8.10.4.2 连接用电线 \n替换： \n手术附件电缆的固定结构应设计成能防止由于\n电缆扭曲或过分拉扯引起的导体和绝缘损坏，\n从而能使患者和操作者受到的风险最小化。", "source_index": 968, "source_page": 98, "source_row_index": 4, "source_text_excerpt": "201.8.10.4.2 连接用电线 \n替换： \n手术附件电缆的固定结构应设计成能防止由于\n电缆扭曲或过分拉扯引起的导体和绝缘损坏，\n从而能使患者和操作者受到的风险最小化。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "201.8.10.4.101 开关检测器  \n201.8.10.4.101.1 概述  \n除了 201.8.10.4.101.2 中所述之外，高频手\n术设备和可用附属设备都应配置一个开关检测\n器，以便即时响应开关的通断动作而使相应手\n术输出端子受激或停激。", "source_index": 969, "source_page": 98, "source_row_index": 5, "source_text_excerpt": "201.8.10.4.101 开关检测器  \n201.8.10.4.101.1 概述  \n除了 201.8.10.4.101.2 中所述之外，高频手\n术设备和可用附属设备都应配置一个开关检测\n器，以便即时响应开关的通断动作而使相应手\n术输出端子受激或停激。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "在单一故障状态下，开关检测器不应引起低频\n患者漏电流超过允许限值（见 201.8.7.3）。", "source_index": 971, "source_page": 98, "source_row_index": 7, "source_text_excerpt": "在单一故障状态下，开关检测器不应引起低频\n患者漏电流超过允许限值（见 201.8.7.3）。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "每一个开关检测器应只能启动预期的单一手术\n输出端子，并且一次不应控制多于一个的高频\n手术模式。", "source_index": 973, "source_page": 98, "source_row_index": 9, "source_text_excerpt": "每一个开关检测器应只能启动预期的单一手术\n输出端子，并且一次不应控制多于一个的高频\n手术模式。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "201.8.10.4.101.4 脚踏开关 \n脚踏开关应符合下述要求（见 201.11.6.5 和\n201.12.2）： \n启动开关所要求的力不应小于 10N，该力施加\n于脚踏开关操作表面上任何 625m\nm\n,\n 面积上。 \n单位：N", "source_index": 980, "source_page": 99, "source_row_index": 7, "source_text_excerpt": "201.8.10.4.101.4 脚踏开关 \n脚踏开关应符合下述要求（见 201.11.6.5 和\n201.12.2）： \n启动开关所要求的力不应小于 10N，该力施加\n于脚踏开关操作表面上任何 625m\nm\n,\n 面积上。 \n单位：N ——", "standard_clause": ""}], "suppressed_physical_row_count": 13}, "page_number": 98, "rule_id": "C07", "severity": "warn", "source": "report_codex_evidence_builder"}, "summary": "序号 142 的结构化检验结果可能不完整，需结合原始表格或 Codex evidence 复核后再判断单项结论。", "target_id": "report-codex-target-004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain", "target_type": "inspection_item", "title": "序号 142 的结构化检验结果可能不完整，需结合原始表格或 Codex evidence 复核后再判断单项结论。"}

## Evidence Items

### Evidence finding:004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 98, \"row_index\": 3, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p98-t1\", \"text_span\": null}", "metadata": "{\"check_id\": \"C07\", \"finding_code\": \"CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN\", \"finding_id\": \"004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain\", \"severity\": \"warn\"}", "page_number": 98, "ref_id": "finding:004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain", "section": null, "source_type": "finding", "structured": "{\"actual\": \"符合\", \"check_id\": \"C07\", \"code\": \"CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN\", \"expected\": \"/\", \"id\": \"004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain\", \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 98, \"row_index\": 3, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p98-t1\", \"text_span\": null}, \"message\": \"序号 142 的结构化检验结果可能不完整，需结合原始表格或 Codex evidence 复核后再判断单项结论。\", \"metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [{\"normalized_item_no\": \"142\", \"page_number\": 99, \"raw_text\": \"续\\n142\", \"row_index\": 1, \"source_index\": 974}], \"decision_reason\": \"all_placeholders_or_blank\", \"display_item_no\": \"142\", \"effective_test_results\": [\"——\", \"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [{\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"201.8.10.4.2 连接用电线 \\n替换： \\n手术附件电缆的固定结构应设计成能防止由于\\n电缆扭曲或过分拉扯引起的导体和绝缘损坏，\\n从而能使患者和操作者受到的风险最小化。\", \"source_index\": 968, \"source_page\": 98, \"source_row_index\": 4, \"source_text_excerpt\": \"201.8.10.4.2 连接用电线 \\n替换： \\n手术附件电缆的固定结构应设计成能防止由于\\n电缆扭曲或过分拉扯引起的导体和绝缘损坏，\\n从而能使患者和操作者受到的风险最小化。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"201.8.10.4.101 开关检测器  \\n201.8.10.4.101.1 概述  \\n除了 201.8.10.4.101.2 中所述之外，高频手\\n术设备和可用附属设备都应配置一个开关检测\\n器，以便即时响应开关的通断动作而使相应手\\n术输出端子受激或停激。\", \"source_index\": 969, \"source_page\": 98, \"source_row_index\": 5, \"source_text_excerpt\": \"201.8.10.4.101 开关检测器  \\n201.8.10.4.101.1 概述  \\n除了 201.8.10.4.101.2 中所述之外，高频手\\n术设备和可用附属设备都应配置一个开关检测\\n器，以便即时响应开关的通断动作而使相应手\\n术输出端子受激或停激。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"在单一故障状态下，开关检测器不应引起低频\\n患者漏电流超过允许限值（见 201.8.7.3）。\", \"source_index\": 971, \"source_page\": 98, \"source_row_index\": 7, \"source_text_excerpt\": \"在单一故障状态下，开关检测器不应引起低频\\n患者漏电流超过允许限值（见 201.8.7.3）。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"每一个开关检测器应只能启动预期的单一手术\\n输出端子，并且一次不应控制多于一个的高频\\n手术模式。\", \"source_index\": 973, \"source_page\": 98, \"source_row_index\": 9, \"source_text_excerpt\": \"每一个开关检测器应只能启动预期的单一手术\\n输出端子，并且一次不应控制多于一个的高频\\n手术模式。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"201.8.10.4.101.4 脚踏开关 \\n脚踏开关应符合下述要求（见 201.11.6.5 和\\n201.12.2）： \\n启动开关所要求的力不应小于 10N，该力施加\\n于脚踏开关操作表面上任何 625m\\nm\\n,\\n 面积上。 \\n单位：N\", \"source_index\": 980, \"source_page\": 99, \"source_row_index\": 7, \"source_text_excerpt\": \"201.8.10.4.101.4 脚踏开关 \\n脚踏开关应符合下述要求（见 201.11.6.5 和\\n201.12.2）： \\n启动开关所要求的力不应小于 10N，该力施加\\n于脚踏开关操作表面上任何 625m\\nm\\n,\\n 面积上。 \\n单位：N ——\", \"standard_clause\": \"\"}], \"item_no\": \"142\", \"needs_codex_review\": true, \"normalized_item_no\": \"142\", \"original_effective_test_results\": [\"——\", \"——\"], \"pages\": [98, 99], \"reasoning_basis\": \"all_placeholders_or_blank\", \"recovered_effective_test_results\": [\"——\", \"——\"], \"recovered_result_tokens\": [], \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 2, \"total_count\": 2}, \"result_token_recovery_applied\": false, \"result_token_recovery_confidence\": \"uncertain\", \"result_token_recovery_diagnostics\": [{\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"201.8.10.4.2 连接用电线 \\n替换： \\n手术附件电缆的固定结构应设计成能防止由于\\n电缆扭曲或过分拉扯引起的导体和绝缘损坏，\\n从而能使患者和操\n[truncated]", "text": null, "title": "序号 142 的结构化检验结果可能不完整，需结合原始表格或 Codex evidence 复核后再判断单项结论。"}

### Evidence inspection_item:004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 98, \"row_index\": 3, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p98-t1\", \"text_span\": null}", "metadata": "{\"check_id\": \"C07\", \"evidence_level\": \"inspection_item_group\", \"finding_id\": \"004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain\", \"item_no\": \"142\"}", "page_number": 98, "ref_id": "inspection_item:004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain", "section": "inspection_item_group", "source_type": "table", "structured": "{\"finding_metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [{\"normalized_item_no\": \"142\", \"page_number\": 99, \"raw_text\": \"续\\n142\", \"row_index\": 1, \"source_index\": 974}], \"decision_reason\": \"all_placeholders_or_blank\", \"display_item_no\": \"142\", \"effective_test_results\": [\"——\", \"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [{\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"201.8.10.4.2 连接用电线 \\n替换： \\n手术附件电缆的固定结构应设计成能防止由于\\n电缆扭曲或过分拉扯引起的导体和绝缘损坏，\\n从而能使患者和操作者受到的风险最小化。\", \"source_index\": 968, \"source_page\": 98, \"source_row_index\": 4, \"source_text_excerpt\": \"201.8.10.4.2 连接用电线 \\n替换： \\n手术附件电缆的固定结构应设计成能防止由于\\n电缆扭曲或过分拉扯引起的导体和绝缘损坏，\\n从而能使患者和操作者受到的风险最小化。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"201.8.10.4.101 开关检测器  \\n201.8.10.4.101.1 概述  \\n除了 201.8.10.4.101.2 中所述之外，高频手\\n术设备和可用附属设备都应配置一个开关检测\\n器，以便即时响应开关的通断动作而使相应手\\n术输出端子受激或停激。\", \"source_index\": 969, \"source_page\": 98, \"source_row_index\": 5, \"source_text_excerpt\": \"201.8.10.4.101 开关检测器  \\n201.8.10.4.101.1 概述  \\n除了 201.8.10.4.101.2 中所述之外，高频手\\n术设备和可用附属设备都应配置一个开关检测\\n器，以便即时响应开关的通断动作而使相应手\\n术输出端子受激或停激。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"在单一故障状态下，开关检测器不应引起低频\\n患者漏电流超过允许限值（见 201.8.7.3）。\", \"source_index\": 971, \"source_page\": 98, \"source_row_index\": 7, \"source_text_excerpt\": \"在单一故障状态下，开关检测器不应引起低频\\n患者漏电流超过允许限值（见 201.8.7.3）。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"每一个开关检测器应只能启动预期的单一手术\\n输出端子，并且一次不应控制多于一个的高频\\n手术模式。\", \"source_index\": 973, \"source_page\": 98, \"source_row_index\": 9, \"source_text_excerpt\": \"每一个开关检测器应只能启动预期的单一手术\\n输出端子，并且一次不应控制多于一个的高频\\n手术模式。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"201.8.10.4.101.4 脚踏开关 \\n脚踏开关应符合下述要求（见 201.11.6.5 和\\n201.12.2）： \\n启动开关所要求的力不应小于 10N，该力施加\\n于脚踏开关操作表面上任何 625m\\nm\\n,\\n 面积上。 \\n单位：N\", \"source_index\": 980, \"source_page\": 99, \"source_row_index\": 7, \"source_text_excerpt\": \"201.8.10.4.101.4 脚踏开关 \\n脚踏开关应符合下述要求（见 201.11.6.5 和\\n201.12.2）： \\n启动开关所要求的力不应小于 10N，该力施加\\n于脚踏开关操作表面上任何 625m\\nm\\n,\\n 面积上。 \\n单位：N ——\", \"standard_clause\": \"\"}], \"group_row_count\": 14, \"item_no\": \"142\", \"needs_codex_review\": true, \"normalized_item_no\": \"142\", \"original_effective_test_results\": [\"——\", \"——\"], \"pages\": [98, 99], \"reasoning_basis\": \"all_placeholders_or_blank\", \"recovered_effective_test_results\": [\"——\", \"——\"], \"recovered_result_tokens\": [], \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 2, \"total_count\": 2}, \"result_token_recovery_applied\": false, \"result_token_recovery_confidence\": \"uncertain\", \"result_token_recovery_diagnostics\": [{\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"201.8.10.4.2 连接用电线 \\n替换： \\n手术附件电缆的固定结构应设计成能防止由于\\n电缆扭曲或过分拉扯引起的导体和绝缘损坏，\\n从而能使患者和操作者受到的风险最小化。\", \"source_index\": 968, \"source_page\": 98, \"source_row_index\": 4, \"source_text_excerpt\": \"201.8.10.4.2 连接用电线 \\n替换： \\n手术附件电缆的固定结构应设计成能防止由于\\n电缆扭曲或过分拉扯引起的导体和绝缘损坏，\\n从而能使患者和操作者受到的风险最小化。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"201.8.10.4.101 开关检测器  \\n201.8.10.4.101.1 概述  \\n除了 201.8\n[truncated]", "text": null, "title": "C07 检验项目 group evidence"}

### Evidence inspection_page_text:004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain
{"file_path": null, "location": null, "metadata": "{\"check_id\": \"C07\", \"finding_id\": \"004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain\", \"pages\": [98, 99]}", "page_number": 98, "ref_id": "inspection_page_text:004f23d9-bd93-4773-91c4-d1c72acf6208-c07-142-result-token-recovery-uncertain", "section": "inspection_group_page_text", "source_type": "page_text", "structured": "{\"excerpt_scope\": \"around_inspection_item_only\", \"finding_metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [{\"normalized_item_no\"
[truncated]
