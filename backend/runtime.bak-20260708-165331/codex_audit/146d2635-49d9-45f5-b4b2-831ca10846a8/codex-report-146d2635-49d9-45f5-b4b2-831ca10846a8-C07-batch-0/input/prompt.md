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

- package_id: codex-report-146d2635-49d9-45f5-b4b2-831ca10846a8-C07-batch-0
- task_id: 146d2635-49d9-45f5-b4b2-831ca10846a8
- task_type: report_check
- kind: report_rule_review
- schema_version: evidence-package-v1

## Targets

### Target report-codex-target-146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch
{"allowed_evidence_refs": ["finding:146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch", "rule_context:146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch", "inspection_item:146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch", "inspection_page_text:146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch"], "check_id": "C07", "finding_code": "CONCLUSION_MISMATCH_002", "finding_id": "146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch", "metadata": {"actual": "/", "complex_matrix_reason": null, "complex_matrix_table": false, "evidence_incomplete": false, "expected": "符合", "finding_code": "CONCLUSION_MISMATCH_002", "finding_metadata": {"actual_conclusion": "/", "continuation_markers": [{"normalized_item_no": "3", "page_number": 17, "raw_text": "续\n3", "row_index": 1, "source_index": 8}], "decision_reason": "has_conforming_or_non_empty_result", "display_item_no": "3", "effective_test_results": ["符合要求", "符合要求"], "expected_conclusion": "符合", "group_diagnostics": [{"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "在正常状态和单一故障状态下，从完整的功能\n到丧失全部确定的性能，制造商应规定性能限\n值。", "source_index": 7, "source_page": 16, "source_row_index": 8, "source_text_excerpt": "在正常状态和单一故障状态下，从完整的功能\n到丧失全部确定的性能，制造商应规定性能限\n值。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "制造商应实施风险控制措施以减少已识别性能\n的丧失或降低而导致的风险，使其达到可接受\n水平。", "source_index": 9, "source_page": 17, "source_row_index": 2, "source_text_excerpt": "制造商应实施风险控制措施以减少已识别性能\n的丧失或降低而导致的风险，使其达到可接受\n水平。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "制造商应规定用于验证风险控制措施效果的方\n法。", "source_index": 10, "source_page": 17, "source_row_index": 3, "source_text_excerpt": "制造商应规定用于验证风险控制措施效果的方\n法。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "应包括所有用于确定是否需要验证的评估。", "source_index": 11, "source_page": 17, "source_row_index": 4, "source_text_excerpt": "应包括所有用于确定是否需要验证的评估。 符合要求", "standard_clause": ""}, {"code": "CONFLICTING_EFFECTIVE_CONCLUSION", "item_no": "3", "values": ["/", "符合"]}], "item_no": "3", "normalized_item_no": "3", "original_effective_test_results": ["符合要求", "符合要求"], "pages": [16, 17], "reasoning_basis": "has_conforming_or_non_empty_result", "recovered_effective_test_results": ["符合要求", "符合要求"], "recovered_result_tokens": [], "result_summary": {"conforming_or_non_empty_count": 2, "nonconforming_count": 0, "placeholder_count": 0, "total_count": 2}, "result_token_recovery_applied": false, "result_token_recovery_confidence": "uncertain", "result_token_recovery_diagnostics": [{"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "在正常状态和单一故障状态下，从完整的功能\n到丧失全部确定的性能，制造商应规定性能限\n值。", "source_index": 7, "source_page": 16, "source_row_index": 8, "source_text_excerpt": "在正常状态和单一故障状态下，从完整的功能\n到丧失全部确定的性能，制造商应规定性能限\n值。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "制造商应实施风险控制措施以减少已识别性能\n的丧失或降低而导致的风险，使其达到可接受\n水平。", "source_index": 9, "source_page": 17, "source_row_index": 2, "source_text_excerpt": "制造商应实施风险控制措施以减少已识别性能\n的丧失或降低而导致的风险，使其达到可接受\n水平。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "制造商应规定用于验证风险控制措施效果的方\n法。", "source_index": 10, "source_page": 17, "source_row_index": 3, "source_text_excerpt": "制造商应规定用于验证风险控制措施效果的方\n法。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "应包括所有用于确定是否需要验证的评估。", "source_index": 11, "source_page": 17, "source_row_index": 4, "source_text_excerpt": "应包括所有用于确定是否需要验证的评估。 符合要求", "standard_clause": ""}], "suppressed_physical_row_count": 5}, "page_number": 16, "rule_id": "C07", "severity": "error", "source": "report_codex_evidence_builder"}, "summary": "序号 3 的检验结果与单项结论逻辑不一致：存在符合要求或其他非空检验结果，期望单项结论为“符合”，实际为“/”。", "target_id": "report-codex-target-146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch", "target_type": "inspection_item", "title": "序号 3 的检验结果与单项结论逻辑不一致：存在符合要求或其他非空检验结果，期望单项结论为“符合”，实际为“/”。"}

## Evidence Items

### Evidence finding:146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 16, \"row_index\": 7, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p16-t1\", \"text_span\": null}", "metadata": "{\"check_id\": \"C07\", \"finding_code\": \"CONCLUSION_MISMATCH_002\", \"finding_id\": \"146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch\", \"severity\": \"error\"}", "page_number": 16, "ref_id": "finding:146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch", "section": null, "source_type": "finding", "structured": "{\"actual\": \"/\", \"check_id\": \"C07\", \"code\": \"CONCLUSION_MISMATCH_002\", \"expected\": \"符合\", \"id\": \"146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch\", \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 16, \"row_index\": 7, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p16-t1\", \"text_span\": null}, \"message\": \"序号 3 的检验结果与单项结论逻辑不一致：存在符合要求或其他非空检验结果，期望单项结论为“符合”，实际为“/”。\", \"metadata\": {\"actual_conclusion\": \"/\", \"continuation_markers\": [{\"normalized_item_no\": \"3\", \"page_number\": 17, \"raw_text\": \"续\\n3\", \"row_index\": 1, \"source_index\": 8}], \"decision_reason\": \"has_conforming_or_non_empty_result\", \"display_item_no\": \"3\", \"effective_test_results\": [\"符合要求\", \"符合要求\"], \"expected_conclusion\": \"符合\", \"group_diagnostics\": [{\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"在正常状态和单一故障状态下，从完整的功能\\n到丧失全部确定的性能，制造商应规定性能限\\n值。\", \"source_index\": 7, \"source_page\": 16, \"source_row_index\": 8, \"source_text_excerpt\": \"在正常状态和单一故障状态下，从完整的功能\\n到丧失全部确定的性能，制造商应规定性能限\\n值。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"制造商应实施风险控制措施以减少已识别性能\\n的丧失或降低而导致的风险，使其达到可接受\\n水平。\", \"source_index\": 9, \"source_page\": 17, \"source_row_index\": 2, \"source_text_excerpt\": \"制造商应实施风险控制措施以减少已识别性能\\n的丧失或降低而导致的风险，使其达到可接受\\n水平。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"制造商应规定用于验证风险控制措施效果的方\\n法。\", \"source_index\": 10, \"source_page\": 17, \"source_row_index\": 3, \"source_text_excerpt\": \"制造商应规定用于验证风险控制措施效果的方\\n法。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"应包括所有用于确定是否需要验证的评估。\", \"source_index\": 11, \"source_page\": 17, \"source_row_index\": 4, \"source_text_excerpt\": \"应包括所有用于确定是否需要验证的评估。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"CONFLICTING_EFFECTIVE_CONCLUSION\", \"item_no\": \"3\", \"values\": [\"/\", \"符合\"]}], \"item_no\": \"3\", \"normalized_item_no\": \"3\", \"original_effective_test_results\": [\"符合要求\", \"符合要求\"], \"pages\": [16, 17], \"reasoning_basis\": \"has_conforming_or_non_empty_result\", \"recovered_effective_test_results\": [\"符合要求\", \"符合要求\"], \"recovered_result_tokens\": [], \"result_summary\": {\"conforming_or_non_empty_count\": 2, \"nonconforming_count\": 0, \"placeholder_count\": 0, \"total_count\": 2}, \"result_token_recovery_applied\": false, \"result_token_recovery_confidence\": \"uncertain\", \"result_token_recovery_diagnostics\": [{\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"在正常状态和单一故障状态下，从完整的功能\\n到丧失全部确定的性能，制造商应规定性能限\\n值。\", \"source_index\": 7, \"source_page\": 16, \"source_row_index\": 8, \"source_text_excerpt\": \"在正常状态和单一故障状态下，从完整的功能\\n到丧失全部确定的性能，制造商应规定性能限\\n值。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"制造商应实施风险控制措施以减少已识别性能\\n的丧失或降低而导致的风险，使其达到可接受\\n水平。\", \"source_index\": 9, \"source_page\": 17, \"source_row_index\": 2, \"source_text_excerpt\": \"制造商应实施风险控制措施以减少已识别性能\\n的丧失或降低而导致的风险，使其达到可接受\\n水平。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"制造商应规定用于验证风险控制措施效果的方\\n法。\", \"source_index\": 10, \"source_page\": 17, \"source_row_index\": 3, \"source_text_excerpt\": \"制造商应规定用于验证风险控制措施效果的方\\n法。 符合要求\", \"standard_clause\": \"\"}, {\"c\n[truncated]", "text": null, "title": "序号 3 的检验结果与单项结论逻辑不一致：存在符合要求或其他非空检验结果，期望单项结论为“符合”，实际为“/”。"}

### Evidence inspection_item:146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 16, \"row_index\": 7, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p16-t1\", \"text_span\": null}", "metadata": "{\"check_id\": \"C07\", \"evidence_level\": \"inspection_item_group\", \"finding_id\": \"146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch\", \"item_no\": \"3\"}", "page_number": 16, "ref_id": "inspection_item:146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch", "section": "inspection_item_group", "source_type": "table", "structured": "{\"finding_metadata\": {\"actual_conclusion\": \"/\", \"continuation_markers\": [{\"normalized_item_no\": \"3\", \"page_number\": 17, \"raw_text\": \"续\\n3\", \"row_index\": 1, \"source_index\": 8}], \"decision_reason\": \"has_conforming_or_non_empty_result\", \"display_item_no\": \"3\", \"effective_test_results\": [\"符合要求\", \"符合要求\"], \"expected_conclusion\": \"符合\", \"group_diagnostics\": [{\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"在正常状态和单一故障状态下，从完整的功能\\n到丧失全部确定的性能，制造商应规定性能限\\n值。\", \"source_index\": 7, \"source_page\": 16, \"source_row_index\": 8, \"source_text_excerpt\": \"在正常状态和单一故障状态下，从完整的功能\\n到丧失全部确定的性能，制造商应规定性能限\\n值。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"制造商应实施风险控制措施以减少已识别性能\\n的丧失或降低而导致的风险，使其达到可接受\\n水平。\", \"source_index\": 9, \"source_page\": 17, \"source_row_index\": 2, \"source_text_excerpt\": \"制造商应实施风险控制措施以减少已识别性能\\n的丧失或降低而导致的风险，使其达到可接受\\n水平。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"制造商应规定用于验证风险控制措施效果的方\\n法。\", \"source_index\": 10, \"source_page\": 17, \"source_row_index\": 3, \"source_text_excerpt\": \"制造商应规定用于验证风险控制措施效果的方\\n法。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"应包括所有用于确定是否需要验证的评估。\", \"source_index\": 11, \"source_page\": 17, \"source_row_index\": 4, \"source_text_excerpt\": \"应包括所有用于确定是否需要验证的评估。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"CONFLICTING_EFFECTIVE_CONCLUSION\", \"item_no\": \"3\", \"values\": [\"/\", \"符合\"]}], \"group_row_count\": 6, \"item_no\": \"3\", \"normalized_item_no\": \"3\", \"original_effective_test_results\": [\"符合要求\", \"符合要求\"], \"pages\": [16, 17], \"reasoning_basis\": \"has_conforming_or_non_empty_result\", \"recovered_effective_test_results\": [\"符合要求\", \"符合要求\"], \"recovered_result_tokens\": [], \"result_summary\": {\"conforming_or_non_empty_count\": 2, \"nonconforming_count\": 0, \"placeholder_count\": 0, \"total_count\": 2}, \"result_token_recovery_applied\": false, \"result_token_recovery_confidence\": \"uncertain\", \"result_token_recovery_diagnostics\": [{\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"在正常状态和单一故障状态下，从完整的功能\\n到丧失全部确定的性能，制造商应规定性能限\\n值。\", \"source_index\": 7, \"source_page\": 16, \"source_row_index\": 8, \"source_text_excerpt\": \"在正常状态和单一故障状态下，从完整的功能\\n到丧失全部确定的性能，制造商应规定性能限\\n值。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"制造商应实施风险控制措施以减少已识别性能\\n的丧失或降低而导致的风险，使其达到可接受\\n水平。\", \"source_index\": 9, \"source_page\": 17, \"source_row_index\": 2, \"source_text_excerpt\": \"制造商应实施风险控制措施以减少已识别性能\\n的丧失或降低而导致的风险，使其达到可接受\\n水平。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"制造商应规定用于验证风险控制措施效果的方\\n法。\", \"source_index\": 10, \"source_page\": 17, \"source_row_index\": 3, \"source_text_excerpt\": \"制造商应规定用于验证风险控制措施效果的方\\n法。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"应包括所有用于确定是否需要验证的评估。\", \"source_index\": 11, \"source_page\": 17, \"source_row_index\": 4, \"source_text_excerpt\": \"应包括所有用于确定是否需要验证的评估。 符合要求\", \"standard_clause\": \"\"}], \"result_values\": [\"符合要求\", \"符合要求\"], \"source_rows\": [{\"is_continuation\": false, \"page_nu\n[truncated]", "text": null, "title": "C07 检验项目 group evidence"}

### Evidence inspection_page_text:146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch
{"file_path": null, "location": null, "metadata": "{\"check_id\": \"C07\", \"finding_id\": \"146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch\", \"pages\": [16, 17]}", "page_number": 16, "ref_id": "inspection_page_text:146d2635-49d9-45f5-b4b2-831ca10846a8-c07-3-conclusion-mismatch", "section": "inspection_group_page_text", "source_type": "page_text", "structured": "{\"excerpt_scope\": \"around_inspection_item_only\", \"finding_metadata\": {\"actual_conclusion\": \"/\", \"continuation_markers\": [{\"normalized_item_no\": \"3\", \"page_number\": 17, \"raw_text\": \"续\\n3\", \"row_index\": 1, \"source_index\": 8}], \"decision_reason\": \"has_conforming_or_non_empty_result\", \"display_item_no\": \"3\", \"effective_test_results\": [\"符合要求\", \"符合要求\"], \"expected_conclusion\": \"符合\", \"group_diagnostics\": [{\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"在正常状态和单一故障状态下，从完整的功能\\n到丧失全部确定的性能，制造商应规定性能限\\n值。\", \"source_index\": 7, \"source_page\": 16, \"source_row_index\": 8, \"source_text_excerpt\": \"在正常状态和单一故障状态下，从完整的功能\\n到丧失全部确定的性能，制造商应规定性能限\\n值。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"制造商应实施风险控制措施以减少已识别性能\\n的丧失或降低而导致的风险，使其达到可接受\\n水平。\", \"source_index\": 9, \"source_page\": 17, \"source_row_index\": 2, \"source_text_excerpt\": \"制造商应实施风险控制措施以减少已识别性能\\n的丧失或降低而导致的风险，使其达到可接受\\n水平。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"制造商应规定用于验证风险控制措施效果的方\\n法。\", \"source_index\": 10, \"source_page\": 17, \"source_row_index\": 3, \"source_text_excerpt\": \"制造商应规定用于验证风险控制措施效果的方\\n法。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"应包括所有用于确定是否需要验证的评估。\", \"source_index\": 11, \"source_page\": 17, \"source_row_index\": 4, \"source_text_excerpt\": \"应包括所有用于确定是否需要验证的评估。 符合要求\", \"standard_clause\": \"\"}, {\"code\": \"CONFLICTING_EFFECTIVE_CONCLUSION
[truncated]
