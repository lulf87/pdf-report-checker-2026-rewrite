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

- package_id: codex-report-ee21f597-1576-4008-835f-d81c89e0c107-C07-batch-5
- task_id: ee21f597-1576-4008-835f-d81c89e0c107
- task_type: report_check
- kind: report_rule_review
- schema_version: evidence-package-v1

## Targets

### Target report-codex-target-ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch
{"allowed_evidence_refs": ["finding:ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch", "rule_context:ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch", "inspection_item:ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch", "inspection_page_text:ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch", "page_text:ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch"], "check_id": "C07", "finding_code": "CONCLUSION_MISMATCH_001", "finding_id": "ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch", "metadata": {"actual": "符合", "complex_matrix_reason": null, "complex_matrix_table": false, "evidence_incomplete": false, "expected": "/", "finding_code": "CONCLUSION_MISMATCH_001", "finding_metadata": {"actual_conclusion": "符合", "continuation_markers": [], "decision_reason": "all_placeholders_or_blank", "display_item_no": "72", "effective_test_results": ["——"], "expected_conclusion": "/", "group_diagnostics": [], "group_row_count": 5, "item_no": "72", "normalized_item_no": "72", "pages": [58], "reasoning_basis": "all_placeholders_or_blank", "result_summary": {"conforming_or_non_empty_count": 0, "nonconforming_count": 0, "placeholder_count": 1, "total_count": 1}, "result_values": ["——"], "source_rows": [{"is_continuation": false, "page_number": 58, "remark": "/", "result_values": ["——"], "row_index": 7, "sequence": 72, "sequence_raw": "72", "single_conclusion": "符合", "source_index": 556, "test_result": "——"}, {"is_continuation": false, "page_number": 58, "remark": "", "result_values": [], "row_index": 8, "sequence": null, "sequence_raw": "b) 移动的 ME 设备应具备适当的措施（如锁定\n装置），以阻止在运输状态下 ME 设备或其部\n件发生任何不必要的运动。", "single_conclusion": "", "source_index": 557, "test_result": ""}, {"is_continuation": false, "page_number": 58, "remark": "", "result_values": [], "row_index": 9, "sequence": null, "sequence_raw": "c) 移动的 ME 设备应提供脚轮锁或制动系统，\n以避免其在 10°斜面上发生运输状态下不必\n要的运动。", "single_conclusion": "", "source_index": 558, "test_result": ""}, {"is_continuation": false, "page_number": 58, "remark": "", "result_values": [], "row_index": 10, "sequence": null, "sequence_raw": "9.4.3.2 非运输状态的不稳定性 \n要求如下： \na) 移动的 ME 设备应提供脚轮锁或制动系统，\n以避免其在 5°的斜面上发生任何非运输状态\n下的不必要的运动。", "single_conclusion": "", "source_index": 559, "test_result": ""}, {"is_continuation": false, "page_number": 58, "remark": "", "result_values": [], "row_index": 11, "sequence": null, "sequence_raw": "b) 移动的 ME 设备应提供脚轮锁或制动系统来\n避免来自外力的非预期的运动。", "single_conclusion": "", "source_index": 560, "test_result": ""}], "suppressed_physical_row_count": 4}, "page_number": 58, "rule_id": "C07", "severity": "error", "source": "report_codex_evidence_builder"}, "summary": "序号 72 的检验结果与单项结论逻辑不一致：检验结果全部为占位符或空白，期望单项结论为“/”，实际为“符合”。", "target_id": "report-codex-target-ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch", "target_type": "inspection_item", "title": "序号 72 的检验结果与单项结论逻辑不一致：检验结果全部为占位符或空白，期望单项结论为“/”，实际为“符合”。"}

## Evidence Items

### Evidence finding:ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 58, \"row_index\": 7, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p58-t1\", \"text_span\": null}", "metadata": "{\"check_id\": \"C07\", \"finding_code\": \"CONCLUSION_MISMATCH_001\", \"finding_id\": \"ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch\", \"severity\": \"error\"}", "page_number": 58, "ref_id": "finding:ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch", "section": null, "source_type": "finding", "structured": "{\"actual\": \"符合\", \"check_id\": \"C07\", \"code\": \"CONCLUSION_MISMATCH_001\", \"confidence\": \"high\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": \"high\", \"id\": \"c07-72-group-summary\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 58, \"row_index\": 7, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p58-t1\", \"text_span\": null}, \"metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [], \"decision_reason\": \"all_placeholders_or_blank\", \"display_item_no\": \"72\", \"effective_test_results\": [\"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [], \"group_row_count\": 5, \"item_no\": \"72\", \"normalized_item_no\": \"72\", \"pages\": [58], \"reasoning_basis\": \"all_placeholders_or_blank\", \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 1, \"total_count\": 1}, \"result_values\": [\"——\"], \"source_rows\": [{\"is_continuation\": false, \"page_number\": 58, \"remark\": \"/\", \"result_values\": [\"——\"], \"row_index\": 7, \"sequence\": 72, \"sequence_raw\": \"72\", \"single_conclusion\": \"符合\", \"source_index\": 556, \"test_result\": \"——\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 8, \"sequence\": null, \"sequence_raw\": \"b) 移动的 ME 设备应具备适当的措施（如锁定\\n装置），以阻止在运输状态下 ME 设备或其部\\n件发生任何不必要的运动。\", \"single_conclusion\": \"\", \"source_index\": 557, \"test_result\": \"\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 9, \"sequence\": null, \"sequence_raw\": \"c) 移动的 ME 设备应提供脚轮锁或制动系统，\\n以避免其在 10°斜面上发生运输状态下不必\\n要的运动。\", \"single_conclusion\": \"\", \"source_index\": 558, \"test_result\": \"\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 10, \"sequence\": null, \"sequence_raw\": \"9.4.3.2 非运输状态的不稳定性 \\n要求如下： \\na) 移动的 ME 设备应提供脚轮锁或制动系统，\\n以避免其在 5°的斜面上发生任何非运输状态\\n下的不必要的运动。\", \"single_conclusion\": \"\", \"source_index\": 559, \"test_result\": \"\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 11, \"sequence\": null, \"sequence_raw\": \"b) 移动的 ME 设备应提供脚轮锁或制动系统来\\n避免来自外力的非预期的运动。\", \"single_conclusion\": \"\", \"source_index\": 560, \"test_result\": \"\"}], \"suppressed_physical_row_count\": 4}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"序号：72；有效检验结果：——；期望单项结论：/；实际单项结论：符合\", \"source_type\": \"report\", \"value\": \"符合\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p58-t1:r7:c0:sequence_raw\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"序号\", \"description\": null, \"page_number\": 58, \"row_index\": 7, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p58-t1\", \"text_span\": null}, \"metadata\": {\"column_index\": 0, \"field_name\": \"sequence_raw\"}, \"method\": \"pdf_text\", \"normalized_text\": \"72\", \"raw_text\": \"72\", \"source_type\": \"report\", \"value\": \"72\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p58-t1:r7:c1:item_name\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"检验项目\", \"description\": null, \"page_number\": 58, \"row_index\": 7, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p58-t1\", \"text_span\": null}, \"metadata\": {\"column_index\": 1, \"field_name\": \"item_name\"}, \"method\": \"pdf_text\", \"normalized_text\": \"不必要的侧向运动（包括滑动）导致的不稳定性\", \"raw_text\": \"不必要的\\n侧向运动\\n（包括滑\\n动）导致\\n的不稳定\\n性\", \"source_type\": \"report\", \"value\": \"不必要的\\n侧向运动\\n（包括滑\\n动）导致\\n的不稳定\\n性\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p58-t1:r7:c2:standard_clause\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"标准条款\", \"description\": null, \"page_number\": 58, \"row_index\": 7, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p58-t1\", \"text_span\": null}, \"metadata\": {\"column_index\": 2, \"field_name\": \"standard_clause\"}, \"method\": \"pdf_text\", \"normalized_text\": \"9.4.3\", \"raw_text\": \"9.4.3\", \"source_type\": \"report\", \"value\": \"9.4.3\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p58-t1:r7:c3:standar\n[truncated]", "text": null, "title": "序号 72 的检验结果与单项结论逻辑不一致：检验结果全部为占位符或空白，期望单项结论为“/”，实际为“符合”。"}

### Evidence inspection_item:ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 58, \"row_index\": 7, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p58-t1\", \"text_span\": null}", "metadata": "{\"check_id\": \"C07\", \"evidence_level\": \"inspection_item_group\", \"finding_id\": \"ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch\", \"item_no\": \"72\"}", "page_number": 58, "ref_id": "inspection_item:ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch", "section": "inspection_item_group", "source_type": "table", "structured": "{\"finding_metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [], \"decision_reason\": \"all_placeholders_or_blank\", \"display_item_no\": \"72\", \"effective_test_results\": [\"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [], \"group_row_count\": 5, \"item_no\": \"72\", \"normalized_item_no\": \"72\", \"pages\": [58], \"reasoning_basis\": \"all_placeholders_or_blank\", \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 1, \"total_count\": 1}, \"result_values\": [\"——\"], \"source_rows\": [{\"is_continuation\": false, \"page_number\": 58, \"remark\": \"/\", \"result_values\": [\"——\"], \"row_index\": 7, \"sequence\": 72, \"sequence_raw\": \"72\", \"single_conclusion\": \"符合\", \"source_index\": 556, \"test_result\": \"——\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 8, \"sequence\": null, \"sequence_raw\": \"b) 移动的 ME 设备应具备适当的措施（如锁定\\n装置），以阻止在运输状态下 ME 设备或其部\\n件发生任何不必要的运动。\", \"single_conclusion\": \"\", \"source_index\": 557, \"test_result\": \"\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 9, \"sequence\": null, \"sequence_raw\": \"c) 移动的 ME 设备应提供脚轮锁或制动系统，\\n以避免其在 10°斜面上发生运输状态下不必\\n要的运动。\", \"single_conclusion\": \"\", \"source_index\": 558, \"test_result\": \"\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 10, \"sequence\": null, \"sequence_raw\": \"9.4.3.2 非运输状态的不稳定性 \\n要求如下： \\na) 移动的 ME 设备应提供脚轮锁或制动系统，\\n以避免其在 5°的斜面上发生任何非运输状态\\n下的不必要的运动。\", \"single_conclusion\": \"\", \"source_index\": 559, \"test_result\": \"\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 11, \"sequence\": null, \"sequence_raw\": \"b) 移动的 ME 设备应提供脚轮锁或制动系统来\\n避免来自外力的非预期的运动。\", \"single_conclusion\": \"\", \"source_index\": 560, \"test_result\": \"\"}], \"suppressed_physical_row_count\": 4}, \"inspection_item_group\": {\"actual_conclusion\": \"符合\", \"actual_conclusion_candidates\": [{\"field_provenance\": \"native\", \"normalized_value\": \"符合\", \"page_number\": 58, \"row_index\": 7, \"sequence_raw\": \"72\", \"value\": \"符合\"}], \"complete_rows\": [{\"conclusion\": \"符合\", \"field_provenance\": {\"conclusion\": \"native\", \"item_name\": \"native\", \"remark\": \"native\", \"sequence_raw\": \"native\", \"standard_clause\": \"native\", \"standard_requirement\": \"native\", \"test_result\": \"native\"}, \"is_continuation\": false, \"item_name\": \"不必要的\\n侧向运动\\n（包括滑\\n动）导致\\n的不稳定\\n性\", \"metadata\": {\"field_columns\": {\"conclusion\": 5, \"item_name\": 1, \"remark\": 6, \"sequence_raw\": 0, \"standard_clause\": 2, \"standard_requirement\": 3, \"test_result\": 4}, \"item_name\": \"不必要的\\n侧向运动\\n（包括滑\\n动）导致\\n的不稳定\\n性\", \"item_no\": \"72\", \"single_conclusion\": \"符合\", \"source_table_id\": \"p58-t1\"}, \"remark\": \"/\", \"row_index_in_page\": 7, \"sequence\": 72, \"sequence_raw\": \"72\", \"source_page\": 58, \"standard_clause\": \"9.4.3\", \"test_result\": \"——\"}, {\"conclusion\": \"\", \"field_provenance\": {\"conclusion\": \"native\", \"item_name\": \"native\", \"remark\": \"native\", \"sequence_raw\": \"native\", \"standard_clause\": \"native\", \"standard_requirement\": \"native\", \"test_result\": \"native\"}, \"is_continuation\": false, \"item_name\": \"符合要求\", \"metadata\": {\"field_columns\": {\"conclusion\": 5, \"item_name\": 1, \"remark\": 6, \"sequence_raw\": 0, \"standard_clause\": 2, \"standard_requirement\": 3, \"test_result\": 4}, \"item_name\": \"符合要求\", \"item_no\": \"b) 移动的 ME 设备应具备适当的措施（如锁定\\n装置），以阻止在运输状态下 ME 设备或其部\\n件发生任何不必要的运动。\", \"single_conclusion\": \"\", \"source_table_id\": \"p58-t1\"}, \"remark\": \"\", \"row_index_in_page\": 8, \"sequence\": null, \"sequence_raw\": \"b) 移动的 ME 设备应具备适当的措施（如锁定\\n装置），以阻止在运输状态下 ME 设备或其部\\n件发生任何不必要的运动。\", \"source_page\": 58, \"standard_clause\": \"\", \"test_result\": \"\"}, {\"conclusion\": \"\", \"field_provenance\": {\"conclusion\": \"native\", \"item_name\": \"native\", \"remark\": \"native\", \"sequence_raw\": \"native\", \"standard_clause\": \"native\", \"standard_requirement\": \"native\", \"test_result\": \"native\"}, \"is_continuation\": false, \"item_name\": \"符合要求\", \"metadata\": {\"field_columns\": {\"conclusion\": 5, \"item_name\": 1, \"remark\": 6, \"sequence_raw\": 0, \"standard_clause\": 2, \"standard_requirement\n[truncated]", "text": null, "title": "C07 检验项目 group evidence"}

### Evidence inspection_page_text:ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch
{"file_path": null, "location": null, "metadata": "{\"check_id\": \"C07\", \"finding_id\": \"ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch\", \"pages\": [58]}", "page_number": 58, "ref_id": "inspection_page_text:ee21f597-1576-4008-835f-d81c89e0c107-c07-72-conclusion-mismatch", "section": "inspection_group_page_text", "source_type": "page_text", "structured": "{\"finding_metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [], \"decision_reason\": \"all_placeholders_or_blank\", \"display_item_no\": \"72\", \"effective_test_results\": [\"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [], \"group_row_count\": 5, \"item_no\": \"72\", \"normalized_item_no\": \"72\", \"pages\": [58], \"reasoning_basis\": \"all_placeholders_or_blank\", \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 1, \"total_count\": 1}, \"result_values\": [\"——\"], \"source_rows\": [{\"is_continuation\": false, \"page_number\": 58, \"remark\": \"/\", \"result_values\": [\"——\"], \"row_index\": 7, \"sequence\": 72, \"sequence_raw\": \"72\", \"single_conclusion\": \"符合\", \"source_index\": 556, \"test_result\": \"——\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 8, \"sequence\": null, \"sequence_raw\": \"b) 移动的 ME 设备应具备适当的措施（如锁定\\n装置），以阻止在运输状态下 ME 设备或其部\\n件发生任何不必要的运动。\", \"single_conclusion\": \"\", \"source_index\": 557, \"test_result\": \"\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 9, \"sequence\": null, \"sequence_raw\": \"c) 移动的 ME 设备应提供脚轮锁或制动系统，\\n以避免其在 10°斜面上发生运输状态下不必\\n要的运动。\", \"single_conclusion\": \"\", \"source_index\": 558, \"test_result\": \"\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 10, \"sequence\": null, \"sequence_raw\": \"9.4.3.2 非运输状态的不稳定性 \\n要求如下： \\na) 移动的 ME 设备应提供脚轮锁或制动系统，\\n以避免其在 5°的斜面上发生任何非运输状态\\n下的不必要的运动。\", \"single_conclusion\": \"\", \"source_index\": 559, \"test_result\": \"\"}, {\"is_continuation\": false, \"page_number\": 58, \"remark\": \"\", \"result_values\": [], \"row_index\": 11, \"sequence\": null, \"sequence_raw\": \"b) 移动的 ME 设备应提供脚轮锁或制动系统来\\n避免来自外力的非预期的运动。\", \"single_conclusion\": \"\", \"source_index\": 560, \"test_result\": \"\"}], \"suppressed_physical_row_count\": 4}, \"pages\": [{\"page_number\": 58, \"text\": \"上\\n海\\n市\\n医\\n疗\\n器\\n械\\n检\\n验\\n研\\n究\\n院 \\n检 验 报 告 \\n报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 56 页 \\n \\n序\\n号 \\n检验 \\n项目 \\n标准 \\n条款 \\n标准要求 \\n检验结果 \\n单项 \\n结论 \\n备注 \\n续\\n71 \\n不稳定性\\n-失衡 \\n9.4.2 \\nb) 除了固定的 ME 设备，那些预期会在地面或\\n桌面上使用的 ME 设备及其部件，应提供一个\\n永久贴牢的、清楚易认的警告标志，如适当使\\n用 ISO 7010-P018 或 ISO 7010-P019 中的安\\n全标识（参见附表 D.2，安全标识 6 和 \\n7）。 \\n—— \\n符合 \\n/ \\n如果因为 ME 设备失衡而提供了标识，在可能\\n发生坐或者踩踏的行为时，此标识应清晰可\\n见。 \\n—— \\n或不应由于坐或踩踏原因而发生失衡。 \\n—— \\n9.4.2.4 脚轮和轮子 \\n9.4.2.4.1 概述 \\n用于移动的 ME 设备运输的方法（如脚轮或轮\\n子），当移动的 ME 设备在正常使用时发生移\\n动或停止时，不应导致不可接受的风险。 \\n符合要求 \\n9.4.2.4.2 推动的力 \\n用于推动移动的 ME 设备在坚硬平坦水平面上\\n移动的外力不能超过 200N，除非使用说明书\\n中声明了需要多人才能推动。 \\n符合要求 \\n9.4.2.4.3 越过门槛的运动 \\n重量超过 45kg 的移动的 ME 设备应能够越过\\n10mm 的门槛且不应导致失衡。 \\n符合要求 \\n72 \\n不必要的\\n侧向运动\\n（包括滑\\n动）导致\\n的不稳定\\n性 \\n9.4.3 \\n9.4.3.1 运输状态中的不稳定性 \\n要求如下： \\na) 电动的移动的 ME 设备的制动器应设计成通\\n常为制动状态，并且只能通过对控制器的连续\\n开动来解除制动。 \\n—— \\n符合 \\n/ \\nb) 移动的 ME 设备应具备适当的措施（如锁定\\n装置），以阻止在运输状态下 ME 设备或其部\\n件发生任何不必要的运动。 \\n符合要求 \\nc) 移动的 ME 设备应提供脚轮锁或制动系统，\\n以避免其在 10°斜面上发生运输状态下不必\\n要的运动。 \\n符合要求 \\n9.4.3.2 非运输状态的不稳定性 \\n要求如下： \\na) 移动的 ME 设备应提供脚轮锁或制动系统，\\n以避免其在 5°的斜面上发生任何非运输状态\\n下的不必要的运动。 \\n符合要求 \\nb) 移动的 ME 设备应提供脚轮锁或制动系统来\\n避免来自外力的非预期的运动。 \\n符合要求 \\n\"}]}", "text": "[page 58]\n上\n海\n市\n医\n疗\n器\n械\n检\n验\n研\n究\n院 \n检 验 报 告 \n报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 56 页 \n \n序\n号 \n检验 \n项目 \n标准 \n条款 \n标准要求 \n检验结果 \n单项 \n结论 \n备注 \n续\n71 \n不稳定性\n-失衡 \n9.4.2 \nb) 除了固定的 ME 设备，那些预期会在地面或\n桌面上使用的 ME 设备及其部件，应提供一个\n永久贴牢的、清楚易认的警告标志，如适当使\n用 ISO 7010-P018 或 ISO 7010-P019 中的安\n全标识（参见附表 D.2，安全标识 6 和 \n7）。 \n—— \n符合 \n/ \n如果因为 ME 设备失衡而提供了标识，在可能\n发生坐或者踩踏的行为时，此标识应清晰可\n见。 \n—— \n或不应由于坐或踩踏原因而发生失衡。 \n—— \n9.4.2.4 脚轮和轮子 \n9.4.2.4.1 概述 \n用于移动的 ME 设备运输的方法（如脚轮或轮\n子），当移动的 ME 设备在正常使用时发生移\n动或停止时，不应导致不可接受的风险。 \n符合要求 \n9.4.2.4.2 推动的力 \n用于推动移动的 ME 设备在坚硬平坦水平面上\n移动的外力不能超过 200N，除非使用说明书\n中声明了需要多人才能推动。 \n符合要求 \n9.4.2.4.3 越过门槛的运动 \n重量超过 45kg 的移动的 ME 设备应能够越过\n10mm 的门槛且不应导致失衡。 \n符合要求 \n72 \n不必要的\n侧向运动\n（包括滑\n动）导致\n的不稳定\n性
[truncated]
