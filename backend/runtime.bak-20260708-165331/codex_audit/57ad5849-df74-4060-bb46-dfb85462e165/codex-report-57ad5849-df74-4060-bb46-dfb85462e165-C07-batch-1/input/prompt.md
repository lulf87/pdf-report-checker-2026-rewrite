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

- package_id: codex-report-57ad5849-df74-4060-bb46-dfb85462e165-C07-batch-1
- task_id: 57ad5849-df74-4060-bb46-dfb85462e165
- task_type: report_check
- kind: report_rule_review
- schema_version: evidence-package-v1

## Targets

### Target report-codex-target-57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch
{"allowed_evidence_refs": ["finding:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch", "rule_context:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch", "inspection_item:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch", "inspection_page_text:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch", "page_text:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch"], "check_id": "C07", "finding_code": "CONCLUSION_MISMATCH_001", "finding_id": "57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch", "metadata": {"actual": "符合", "complex_matrix_reason": null, "complex_matrix_table": false, "evidence_incomplete": false, "expected": "/", "finding_code": "CONCLUSION_MISMATCH_001", "finding_metadata": {"actual_conclusion": "符合", "continuation_markers": [], "decision_reason": "all_placeholders_or_blank", "display_item_no": "27", "effective_test_results": ["——"], "expected_conclusion": "/", "group_diagnostics": [], "group_row_count": 2, "item_no": "27", "normalized_item_no": "27", "pages": [21], "reasoning_basis": "all_placeholders_or_blank", "result_summary": {"conforming_or_non_empty_count": 0, "nonconforming_count": 0, "placeholder_count": 1, "total_count": 1}, "result_values": ["——"], "source_rows": [{"is_continuation": false, "page_number": 21, "remark": "/", "result_values": ["——"], "row_index": 2, "sequence": 27, "sequence_raw": "27", "single_conclusion": "符合", "source_index": 70, "test_result": "——"}, {"is_continuation": false, "page_number": 21, "remark": "", "result_values": [], "row_index": 3, "sequence": null, "sequence_raw": "当查阅随附文件是强制动作时，ISO 7010- \nM002 的安全标志（参见附表 D.2，安全标志\n10）应替代 ISO 7000: 2004 的符号被使用。", "single_conclusion": "", "source_index": 71, "test_result": ""}], "suppressed_physical_row_count": 1}, "page_number": 21, "rule_id": "C07", "severity": "error", "source": "report_codex_evidence_builder"}, "summary": "序号 27 的检验结果与单项结论逻辑不一致：检验结果全部为占位符或空白，期望单项结论为“/”，实际为“符合”。", "target_id": "report-codex-target-57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch", "target_type": "inspection_item", "title": "序号 27 的检验结果与单项结论逻辑不一致：检验结果全部为占位符或空白，期望单项结论为“/”，实际为“符合”。"}

## Evidence Items

### Evidence finding:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 21, \"row_index\": 2, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p21-t1\", \"text_span\": null}", "metadata": "{\"check_id\": \"C07\", \"finding_code\": \"CONCLUSION_MISMATCH_001\", \"finding_id\": \"57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch\", \"severity\": \"error\"}", "page_number": 21, "ref_id": "finding:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch", "section": null, "source_type": "finding", "structured": "{\"actual\": \"符合\", \"check_id\": \"C07\", \"code\": \"CONCLUSION_MISMATCH_001\", \"confidence\": \"high\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": \"high\", \"id\": \"c07-27-group-summary\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 21, \"row_index\": 2, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p21-t1\", \"text_span\": null}, \"metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [], \"decision_reason\": \"all_placeholders_or_blank\", \"display_item_no\": \"27\", \"effective_test_results\": [\"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [], \"group_row_count\": 2, \"item_no\": \"27\", \"normalized_item_no\": \"27\", \"pages\": [21], \"reasoning_basis\": \"all_placeholders_or_blank\", \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 1, \"total_count\": 1}, \"result_values\": [\"——\"], \"source_rows\": [{\"is_continuation\": false, \"page_number\": 21, \"remark\": \"/\", \"result_values\": [\"——\"], \"row_index\": 2, \"sequence\": 27, \"sequence_raw\": \"27\", \"single_conclusion\": \"符合\", \"source_index\": 70, \"test_result\": \"——\"}, {\"is_continuation\": false, \"page_number\": 21, \"remark\": \"\", \"result_values\": [], \"row_index\": 3, \"sequence\": null, \"sequence_raw\": \"当查阅随附文件是强制动作时，ISO 7010- \\nM002 的安全标志（参见附表 D.2，安全标志\\n10）应替代 ISO 7000: 2004 的符号被使用。\", \"single_conclusion\": \"\", \"source_index\": 71, \"test_result\": \"\"}], \"suppressed_physical_row_count\": 1}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"序号：27；有效检验结果：——；期望单项结论：/；实际单项结论：符合\", \"source_type\": \"report\", \"value\": \"符合\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p21-t1:r2:c0:sequence_raw\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"序号\", \"description\": null, \"page_number\": 21, \"row_index\": 2, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p21-t1\", \"text_span\": null}, \"metadata\": {\"column_index\": 0, \"field_name\": \"sequence_raw\"}, \"method\": \"pdf_text\", \"normalized_text\": \"27\", \"raw_text\": \"27\", \"source_type\": \"report\", \"value\": \"27\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p21-t1:r2:c1:item_name\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"检验项目\", \"description\": null, \"page_number\": 21, \"row_index\": 2, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p21-t1\", \"text_span\": null}, \"metadata\": {\"column_index\": 1, \"field_name\": \"item_name\"}, \"method\": \"pdf_text\", \"normalized_text\": \"查阅随附文件\", \"raw_text\": \"查阅随附\\n文件\", \"source_type\": \"report\", \"value\": \"查阅随附\\n文件\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p21-t1:r2:c2:standard_clause\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"标准条款\", \"description\": null, \"page_number\": 21, \"row_index\": 2, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p21-t1\", \"text_span\": null}, \"metadata\": {\"column_index\": 2, \"field_name\": \"standard_clause\"}, \"method\": \"pdf_text\", \"normalized_text\": \"7.2.3\", \"raw_text\": \"7.2.3\", \"source_type\": \"report\", \"value\": \"7.2.3\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p21-t1:r2:c3:standard_requirement\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"标准要求\", \"description\": null, \"page_number\": 21, \"row_index\": 2, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p21-t1\", \"text_span\": null}, \"metadata\": {\"column_index\": 3, \"field_name\": \"standard_requirement\"}, \"method\": \"pdf_text\", \"normalized_text\": \"在适当的时候，ISO7000:2004的符号（参见附表D.1，符号11)可用作提醒操作者查阅随附文件。\", \"raw_text\": \"在适当的时候，ISO  7000: 2004 的符号（参\\n见附表 D.1，符号 11)可用作提醒操作者查阅\\n随附文件。\", \"source_type\": \"report\", \"value\": \"在适当的时候，ISO  7000: 2004 的符号（参\\n见附表 D.1，符号 11)可用作提醒操作者查阅\\n随附文件。\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p21-t1:r2:c4:test_result\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"检验结果\", \"description\": null, \"page_number\": 21, \"row_index\": 2, \"section\": null, \"source_id\":\n[truncated]", "text": null, "title": "序号 27 的检验结果与单项结论逻辑不一致：检验结果全部为占位符或空白，期望单项结论为“/”，实际为“符合”。"}

### Evidence inspection_item:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 21, \"row_index\": 2, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p21-t1\", \"text_span\": null}", "metadata": "{\"check_id\": \"C07\", \"evidence_level\": \"inspection_item_group\", \"finding_id\": \"57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch\", \"item_no\": \"27\"}", "page_number": 21, "ref_id": "inspection_item:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch", "section": "inspection_item_group", "source_type": "table", "structured": "{\"finding_metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [], \"decision_reason\": \"all_placeholders_or_blank\", \"display_item_no\": \"27\", \"effective_test_results\": [\"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [], \"group_row_count\": 2, \"item_no\": \"27\", \"normalized_item_no\": \"27\", \"pages\": [21], \"reasoning_basis\": \"all_placeholders_or_blank\", \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 1, \"total_count\": 1}, \"result_values\": [\"——\"], \"source_rows\": [{\"is_continuation\": false, \"page_number\": 21, \"remark\": \"/\", \"result_values\": [\"——\"], \"row_index\": 2, \"sequence\": 27, \"sequence_raw\": \"27\", \"single_conclusion\": \"符合\", \"source_index\": 70, \"test_result\": \"——\"}, {\"is_continuation\": false, \"page_number\": 21, \"remark\": \"\", \"result_values\": [], \"row_index\": 3, \"sequence\": null, \"sequence_raw\": \"当查阅随附文件是强制动作时，ISO 7010- \\nM002 的安全标志（参见附表 D.2，安全标志\\n10）应替代 ISO 7000: 2004 的符号被使用。\", \"single_conclusion\": \"\", \"source_index\": 71, \"test_result\": \"\"}], \"suppressed_physical_row_count\": 1}, \"inspection_item_group\": {\"actual_conclusion\": \"符合\", \"actual_conclusion_candidates\": [{\"field_provenance\": \"native\", \"normalized_value\": \"符合\", \"page_number\": 21, \"row_index\": 2, \"sequence_raw\": \"27\", \"value\": \"符合\"}], \"complete_rows\": [{\"conclusion\": \"符合\", \"field_provenance\": {\"conclusion\": \"native\", \"item_name\": \"native\", \"remark\": \"native\", \"sequence_raw\": \"native\", \"standard_clause\": \"native\", \"standard_requirement\": \"native\", \"test_result\": \"native\"}, \"is_continuation\": false, \"item_name\": \"查阅随附\\n文件\", \"metadata\": {\"field_columns\": {\"conclusion\": 5, \"item_name\": 1, \"remark\": 6, \"sequence_raw\": 0, \"standard_clause\": 2, \"standard_requirement\": 3, \"test_result\": 4}, \"item_name\": \"查阅随附\\n文件\", \"item_no\": \"27\", \"single_conclusion\": \"符合\", \"source_table_id\": \"p21-t1\"}, \"remark\": \"/\", \"row_index_in_page\": 2, \"sequence\": 27, \"sequence_raw\": \"27\", \"source_page\": 21, \"standard_clause\": \"7.2.3\", \"test_result\": \"——\"}, {\"conclusion\": \"\", \"field_provenance\": {\"conclusion\": \"native\", \"item_name\": \"native\", \"remark\": \"native\", \"sequence_raw\": \"native\", \"standard_clause\": \"native\", \"standard_requirement\": \"native\", \"test_result\": \"native\"}, \"is_continuation\": false, \"item_name\": \"符合要求\", \"metadata\": {\"field_columns\": {\"conclusion\": 5, \"item_name\": 1, \"remark\": 6, \"sequence_raw\": 0, \"standard_clause\": 2, \"standard_requirement\": 3, \"test_result\": 4}, \"item_name\": \"符合要求\", \"item_no\": \"当查阅随附文件是强制动作时，ISO 7010- \\nM002 的安全标志（参见附表 D.2，安全标志\\n10）应替代 ISO 7000: 2004 的符号被使用。\", \"single_conclusion\": \"\", \"source_table_id\": \"p21-t1\"}, \"remark\": \"\", \"row_index_in_page\": 3, \"sequence\": null, \"sequence_raw\": \"当查阅随附文件是强制动作时，ISO 7010- \\nM002 的安全标志（参见附表 D.2，安全标志\\n10）应替代 ISO 7000: 2004 的符号被使用。\", \"source_page\": 21, \"standard_clause\": \"\", \"test_result\": \"\"}], \"complex_matrix_reason\": null, \"complex_matrix_table\": false, \"conclusion_candidate_provenance\": [{\"page_number\": 21, \"raw_value\": \"符合\", \"row_index\": 2, \"sequence_raw\": \"27\", \"source\": \"native\"}], \"continuation_markers\": [], \"display_item_no\": \"27\", \"effective_remark\": \"/\", \"effective_single_conclusion\": \"符合\", \"effective_test_results\": [\"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [], \"group_row_count\": 2, \"item_no\": \"27\", \"pages\": [21], \"reasoning_basis\": \"all_placeholders_or_blank\", \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 1, \"total_count\": 1}, \"source_rows\": [{\"field_provenance\": {\"conclusion\": \"native\", \"item_name\": \"native\", \"remark\": \"native\", \"sequence_raw\": \"native\", \"standard_clause\": \"native\", \"standard_requirement\": \"native\", \"test_result\": \"native\"}, \"is_continuation\": false, \"item_name\": \"查阅随附\\n文件\", \"item_no\": \"27\", \"metadata\": {\"field_columns\": {\"conclusion\": 5, \"item_name\": 1, \"remark\": 6, \"sequence_raw\": 0, \"standard_clause\": 2, \"standard_requirement\": 3, \"test_result\": 4}, \"item_name\": \"查阅随附\\n文件\", \"item_no\": \"27\", \"single_conclusion\": \"符合\", \"source_table_id\": \"p21-t1\"}, \"normali\n[truncated]", "text": null, "title": "C07 检验项目 group evidence"}

### Evidence inspection_page_text:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch
{"file_path": null, "location": null, "metadata": "{\"check_id\": \"C07\", \"finding_id\": \"57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch\", \"pages\": [21]}", "page_number": 21, "ref_id": "inspection_page_text:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch", "section": "inspection_group_page_text", "source_type": "page_text", "structured": "{\"finding_metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [], \"decision_reason\": \"all_placeholders_or_blank\", \"display_item_no\": \"27\", \"effective_test_results\": [\"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [], \"group_row_count\": 2, \"item_no\": \"27\", \"normalized_item_no\": \"27\", \"pages\": [21], \"reasoning_basis\": \"all_placeholders_or_blank\", \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 1, \"total_count\": 1}, \"result_values\": [\"——\"], \"source_rows\": [{\"is_continuation\": false, \"page_number\": 21, \"remark\": \"/\", \"result_values\": [\"——\"], \"row_index\": 2, \"sequence\": 27, \"sequence_raw\": \"27\", \"single_conclusion\": \"符合\", \"source_index\": 70, \"test_result\": \"——\"}, {\"is_continuation\": false, \"page_number\": 21, \"remark\": \"\", \"result_values\": [], \"row_index\": 3, \"sequence\": null, \"sequence_raw\": \"当查阅随附文件是强制动作时，ISO 7010- \\nM002 的安全标志（参见附表 D.2，安全标志\\n10）应替代 ISO 7000: 2004 的符号被使用。\", \"single_conclusion\": \"\", \"source_index\": 71, \"test_result\": \"\"}], \"suppressed_physical_row_count\": 1}, \"pages\": [{\"page_number\": 21, \"text\": \"上\\n海\\n市\\n医\\n疗\\n器\\n械\\n检\\n验\\n研\\n究\\n院 \\n检 验 报 告 \\n报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 19 页 \\n \\n序\\n号 \\n检验 \\n项目 \\n标准 \\n条款 \\n标准要求 \\n检验结果 \\n单项 \\n结论 \\n备注 \\n续\\n26 \\n标识 \\n7.2.2 \\n软件作为 PEMS 的一部分应确定唯一的标识\\n符。 \\n符合要求 \\n符合 \\n/ \\n27 \\n查阅随附\\n文件 \\n7.2.3 \\n在适当的时候，ISO  7000: 2004 的符号（参\\n见附表 D.1，符号 11)可用作提醒操作者查阅\\n随附文件。 \\n—— \\n符合 \\n/ \\n当查阅随附文件是强制动作时，ISO 7010- \\nM002 的安全标志（参见附表 D.2，安全标志\\n10）应替代 ISO 7000: 2004 的符号被使用。 \\n符合要求 \\n28 \\n附件 \\n7.2.4 \\n附件应标记： \\n——制造商的名称或商标以及联系信息； \\n——型号或类型参考号； \\n——序列号或批号或批次标识； \\n——制造年份或失效日期，若适用。 \\n符合要求 \\n符合 \\n/ \\n附件进行标记不可行时，这些标记可以贴在独\\n立的包装上。 \\n符合要求 \\n29 \\n预期接收\\n其他设备\\n电能的\\nME 设备 \\n7.2.5 \\n如果 ME 设备预期接收来自 ME 系统中其他电气\\n设备的电能，且依赖其他电气设备以符合本部\\n分的要求时，至少满足以下要求之一： \\n——在相关连接点附近，标记其他电气设备的\\n制造商名称或商标，以及该规定设备的型号或\\n类型参考号； \\n—— \\n/ \\n/ \\n——在相关连接点附近标记 ISO 7010-M002 的\\n安全标志（参见附表 D.2，安全标示 10），并\\n在使用说明书中列出详细要求；或 \\n—— \\n——使用通常市场上不能购得的特殊规格连接\\n器，并在使用说明书中列出详细要求。 \\n—— \\n30 \\n与供电网\\n的连接 \\n7.2.6 \\nME 设备应标记以下信息： \\n——可能连接的额定供电电压或额定电压范\\n围。额定供电电压范围应用连字符连接最小和\\n最大电压。 \\n符合要求 \\n符合 \\n/ \\n当有多个额定供电电压或额定供电电压范围给\\n出时，它们应用斜线分隔符(/)来分隔。 \\n—— \\n——供电方式，例如相数（单相供电除外）和\\n电流类型。参见附表 D.1 的符号 1～符号 5。 \\n符合要求 \\n——用赫兹表示的额定供电频率或额定频率范\\n围。 \\n符合要求 \\n——对于Ⅱ类 ME 设备，用 GB/T  5465.2 中\\n5172 的符号（参见附表 D.1，符号 9）。 \\n—— \\n除了永久性安装的 ME 设备，这些标记应出现\\n在包括供电网连接的部件外部，且最好靠近连\\n接点。 \\n符合要求 \\n\"}]}", "text": "[page 21]\n上\n海\n市\n医\n疗\n器\n械\n检\n验\n研\n究\n院 \n检 验 报 告 \n报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 19 页 \n \n序\n号 \n检验 \n项目 \n标准 \n条款 \n标准要求 \n检验结果 \n单项 \n结论 \n备注 \n续\n26 \n标识 \n7.2.2 \n软件作为 PEMS 的一部分应确定唯一的标识\n符。 \n符合要求 \n符合 \n/ \n27 \n查阅随附\n文件 \n7.2.3 \n在适当的时候，ISO  7000: 2004 的符号（参\n见附表 D.1，符号 11)可用作提醒操作者查阅\n随附文件。 \n—— \n符合 \n/ \n当查阅随附文件是强制动作时，ISO 7010- \nM002 的安全标志（参见附表 D.2，安全标志\n10）应替代 ISO 7000: 2004 的符号被使用。 \n符合要求 \n28 \n附件 \n7.2.4 \n附件应标记： \n——制造商的名称或商标以及联系信息； \n——型号或类型参考号； \n——序列号或批号或批次标识； \n——制造年份或失效日期，若适用。 \n符合要求 \n符合 \n/ \n附件进行标记不可行时，这些标记可以贴在独\n立的包装上。 \n符合要求 \n29 \n预期接收\n其他设备\n电能的\nME 设备 \n7.2.5 \n如果 ME 设备预期接收来自 ME 系统中其他电气\n设备的电能，且依赖其他电气设备以符合本部\n分的要求时，至少满足以下要求之一： \n——在相关连接点附近，标记其他电气设备的\n制造商名称或商标，以及该规定设备的型号或\n类型参考号； \n—— \n/ \n/ \n——在相关连接点附近标记 ISO 7010-M002 的\n安全标志（参见附表 D.2，安全标示 10），并\n在使用说明书中列出详细要求；或 \n—— \n——使用通常市场上不能购得的特殊规格连接\n器，并在使用说明书中列出详细要求。 \n—— \n30 \n与供电网\n的连接 \n7.2.6 \nME 设备应标记以下信息： \n——可能连接的额定供电电压或额定电压范\n围。额定供电电压范围应用连字符连接最小和\n最大电压。 \n符合要求 \n符合 \n/ \n当有多个额定供电电压或额定供电电压范围给\n出时，它们应用斜线分隔符(/)来分隔。 \n—— \n——供电方式，例如相数（单相供电除外）和\n电流类型。参见附表 D.1 的符号 1～符号 5。 \n符合要求 \n——用赫兹表示的额定供电频率或额定频率范\n围。 \n符合要求 \n——对于Ⅱ类 ME 设备，用 GB/T  5465.2 中\n5172 的符号（参见附表 D.1，符号 9）。 \n—— \n除了永久性安装的 ME 设备，这些标记应出现\n在包括供电网连接的部件外部，且最好靠近连\n接点。 \n符合要求 \n", "title": "C07 inspection item page text evidence"}

### Evidence page_text:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch
{"file_path": null, "location": null, "metadata": "{\"check_id\": \"C07\", \"file_id\": \"36628a34943d8df5\", \"finding_id\": \"57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch\"}", "page_number": 21, "ref_id": "page_text:57ad5849-df74-4060-bb46-dfb85462e165-c07-27-conclusion-mismatch", "section": "page_text", "source_type": "page_text", "structured": "{\"page_number\": 21, \"text\": \"上\\n海\\n市\\n医\\n疗\\n器\\n械\\n检\\n验\\n研\\n究\\n院 \\n检 验 报 告 \\n报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 19 页 \\n \\n序\\n号 \\n检验 \\n项目 \\n标准 \\n条款 \\n标准要求 \\n检验结果 \\n单项 \\n结论 \\n备注 \\n续\\n26 \\n标识 \\n7.2.2 \\n软件作为 PEMS 的一部分应确定唯一的标识\\n符。 \\n符合要求 \\n符合 \\n/ \\n27 \\n查阅随附\\n文件 \\n7.2.3 \\n在适当的时候，ISO  7000: 2004 的符号（参\\n见附表 D.1，符号 11)可用作提醒操作者查阅\\n随附文件。 \\n—— \\n符合 \\n/ \\n当查阅随附文件是强制动作时，ISO 7010- \\nM002 的安全标志（参见附表 D.2，安全标志\
[truncated]
