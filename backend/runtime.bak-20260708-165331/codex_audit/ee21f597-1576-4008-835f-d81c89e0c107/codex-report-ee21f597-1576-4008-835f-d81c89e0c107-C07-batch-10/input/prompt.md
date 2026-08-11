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

- package_id: codex-report-ee21f597-1576-4008-835f-d81c89e0c107-C07-batch-10
- task_id: ee21f597-1576-4008-835f-d81c89e0c107
- task_type: report_check
- kind: report_rule_review
- schema_version: evidence-package-v1

## Targets

### Target report-codex-target-ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch
{"allowed_evidence_refs": ["finding:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch", "rule_context:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch", "inspection_item:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch", "inspection_page_text:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch", "page_text:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch"], "check_id": "C07", "finding_code": "CONCLUSION_MISMATCH_001", "finding_id": "ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch", "metadata": {"actual": "符合", "complex_matrix_reason": null, "complex_matrix_table": false, "evidence_incomplete": false, "expected": "/", "finding_code": "CONCLUSION_MISMATCH_001", "finding_metadata": {"actual_conclusion": "符合", "continuation_markers": [], "decision_reason": "all_placeholders_or_blank", "display_item_no": "149", "effective_test_results": ["——"], "expected_conclusion": "/", "group_diagnostics": [], "group_row_count": 2, "item_no": "149", "normalized_item_no": "149", "pages": [100], "reasoning_basis": "all_placeholders_or_blank", "result_summary": {"conforming_or_non_empty_count": 0, "nonconforming_count": 0, "placeholder_count": 1, "total_count": 1}, "result_values": ["——"], "source_rows": [{"is_continuation": false, "page_number": 100, "remark": "/", "result_values": ["——"], "row_index": 5, "sequence": 149, "sequence_raw": "149", "single_conclusion": "符合", "source_index": 988, "test_result": "——"}, {"is_continuation": false, "page_number": 100, "remark": "", "result_values": [], "row_index": 6, "sequence": null, "sequence_raw": "——除了不产生功率输出的待机状态之外，原\n来选择的高频手术模式不应改变。", "single_conclusion": "", "source_index": 989, "test_result": ""}], "suppressed_physical_row_count": 1}, "page_number": 100, "rule_id": "C07", "severity": "error", "source": "report_codex_evidence_builder"}, "summary": "序号 149 的检验结果与单项结论逻辑不一致：检验结果全部为占位符或空白，期望单项结论为“/”，实际为“符合”。", "target_id": "report-codex-target-ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch", "target_type": "inspection_item", "title": "序号 149 的检验结果与单项结论逻辑不一致：检验结果全部为占位符或空白，期望单项结论为“/”，实际为“符合”。"}

## Evidence Items

### Evidence finding:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 100, \"row_index\": 5, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p100-t1\", \"text_span\": null}", "metadata": "{\"check_id\": \"C07\", \"finding_code\": \"CONCLUSION_MISMATCH_001\", \"finding_id\": \"ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch\", \"severity\": \"error\"}", "page_number": 100, "ref_id": "finding:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch", "section": null, "source_type": "finding", "structured": "{\"actual\": \"符合\", \"check_id\": \"C07\", \"code\": \"CONCLUSION_MISMATCH_001\", \"confidence\": \"high\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": \"high\", \"id\": \"c07-149-group-summary\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 100, \"row_index\": 5, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p100-t1\", \"text_span\": null}, \"metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [], \"decision_reason\": \"all_placeholders_or_blank\", \"display_item_no\": \"149\", \"effective_test_results\": [\"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [], \"group_row_count\": 2, \"item_no\": \"149\", \"normalized_item_no\": \"149\", \"pages\": [100], \"reasoning_basis\": \"all_placeholders_or_blank\", \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 1, \"total_count\": 1}, \"result_values\": [\"——\"], \"source_rows\": [{\"is_continuation\": false, \"page_number\": 100, \"remark\": \"/\", \"result_values\": [\"——\"], \"row_index\": 5, \"sequence\": 149, \"sequence_raw\": \"149\", \"single_conclusion\": \"符合\", \"source_index\": 988, \"test_result\": \"——\"}, {\"is_continuation\": false, \"page_number\": 100, \"remark\": \"\", \"result_values\": [], \"row_index\": 6, \"sequence\": null, \"sequence_raw\": \"——除了不产生功率输出的待机状态之外，原\\n来选择的高频手术模式不应改变。\", \"single_conclusion\": \"\", \"source_index\": 989, \"test_result\": \"\"}], \"suppressed_physical_row_count\": 1}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"序号：149；有效检验结果：——；期望单项结论：/；实际单项结论：符合\", \"source_type\": \"report\", \"value\": \"符合\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p100-t1:r5:c0:sequence_raw\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"序号\", \"description\": null, \"page_number\": 100, \"row_index\": 5, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p100-t1\", \"text_span\": null}, \"metadata\": {\"column_index\": 0, \"field_name\": \"sequence_raw\"}, \"method\": \"pdf_text\", \"normalized_text\": \"149\", \"raw_text\": \"149\", \"source_type\": \"report\", \"value\": \"149\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p100-t1:r5:c1:item_name\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"检验项目\", \"description\": null, \"page_number\": 100, \"row_index\": 5, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p100-t1\", \"text_span\": null}, \"metadata\": {\"column_index\": 1, \"field_name\": \"item_name\"}, \"method\": \"pdf_text\", \"normalized_text\": \"ME设备的供电电源/供电网中断\", \"raw_text\": \"ME 设备\\n的供电电\\n源/供电\\n网中断\", \"source_type\": \"report\", \"value\": \"ME 设备\\n的供电电\\n源/供电\\n网中断\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p100-t1:r5:c2:standard_clause\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"标准条款\", \"description\": null, \"page_number\": 100, \"row_index\": 5, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p100-t1\", \"text_span\": null}, \"metadata\": {\"column_index\": 2, \"field_name\": \"standard_clause\"}, \"method\": \"pdf_text\", \"normalized_text\": \"201.11.8\", \"raw_text\": \"201.11.8\", \"source_type\": \"report\", \"value\": \"201.11.8\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p100-t1:r5:c3:standard_requirement\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"标准要求\", \"description\": null, \"page_number\": 100, \"row_index\": 5, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p100-t1\", \"text_span\": null}, \"metadata\": {\"column_index\": 3, \"field_name\": \"standard_requirement\"}, \"method\": \"pdf_text\", \"normalized_text\": \"当高频手术设备电源关断再接通，或者供电网中断再恢复时：——输出控制器一个给定设定下的输出功率不应增加20%以上，并且\", \"raw_text\": \"当高频手术设备电源关断再接通，或者供电网\\n中断再恢复时： \\n——输出控制器一个给定设定下的输出功率不\\n应增加 20%以上，并且\", \"source_type\": \"report\", \"value\": \"当高频手术设备电源关断再接通，或者供电网\\n中断再恢复时： \\n——输出控制器一个给定设定下的输出功率不\\n应增加 20%以上，并且\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p100-t1:r5:c4:test_result\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"检验结果\", \"description\": null, \"page_number\":\n[truncated]", "text": null, "title": "序号 149 的检验结果与单项结论逻辑不一致：检验结果全部为占位符或空白，期望单项结论为“/”，实际为“符合”。"}

### Evidence inspection_item:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 100, \"row_index\": 5, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p100-t1\", \"text_span\": null}", "metadata": "{\"check_id\": \"C07\", \"evidence_level\": \"inspection_item_group\", \"finding_id\": \"ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch\", \"item_no\": \"149\"}", "page_number": 100, "ref_id": "inspection_item:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch", "section": "inspection_item_group", "source_type": "table", "structured": "{\"finding_metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [], \"decision_reason\": \"all_placeholders_or_blank\", \"display_item_no\": \"149\", \"effective_test_results\": [\"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [], \"group_row_count\": 2, \"item_no\": \"149\", \"normalized_item_no\": \"149\", \"pages\": [100], \"reasoning_basis\": \"all_placeholders_or_blank\", \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 1, \"total_count\": 1}, \"result_values\": [\"——\"], \"source_rows\": [{\"is_continuation\": false, \"page_number\": 100, \"remark\": \"/\", \"result_values\": [\"——\"], \"row_index\": 5, \"sequence\": 149, \"sequence_raw\": \"149\", \"single_conclusion\": \"符合\", \"source_index\": 988, \"test_result\": \"——\"}, {\"is_continuation\": false, \"page_number\": 100, \"remark\": \"\", \"result_values\": [], \"row_index\": 6, \"sequence\": null, \"sequence_raw\": \"——除了不产生功率输出的待机状态之外，原\\n来选择的高频手术模式不应改变。\", \"single_conclusion\": \"\", \"source_index\": 989, \"test_result\": \"\"}], \"suppressed_physical_row_count\": 1}, \"inspection_item_group\": {\"actual_conclusion\": \"符合\", \"actual_conclusion_candidates\": [{\"field_provenance\": \"native\", \"normalized_value\": \"符合\", \"page_number\": 100, \"row_index\": 5, \"sequence_raw\": \"149\", \"value\": \"符合\"}], \"complete_rows\": [{\"conclusion\": \"符合\", \"field_provenance\": {\"conclusion\": \"native\", \"item_name\": \"native\", \"remark\": \"native\", \"sequence_raw\": \"native\", \"standard_clause\": \"native\", \"standard_requirement\": \"native\", \"test_result\": \"native\"}, \"is_continuation\": false, \"item_name\": \"ME 设备\\n的供电电\\n源/供电\\n网中断\", \"metadata\": {\"field_columns\": {\"conclusion\": 5, \"item_name\": 1, \"remark\": 6, \"sequence_raw\": 0, \"standard_clause\": 2, \"standard_requirement\": 3, \"test_result\": 4}, \"item_name\": \"ME 设备\\n的供电电\\n源/供电\\n网中断\", \"item_no\": \"149\", \"single_conclusion\": \"符合\", \"source_table_id\": \"p100-t1\"}, \"remark\": \"/\", \"row_index_in_page\": 5, \"sequence\": 149, \"sequence_raw\": \"149\", \"source_page\": 100, \"standard_clause\": \"201.11.8\", \"test_result\": \"——\"}, {\"conclusion\": \"\", \"field_provenance\": {\"conclusion\": \"native\", \"item_name\": \"native\", \"remark\": \"native\", \"sequence_raw\": \"native\", \"standard_clause\": \"native\", \"standard_requirement\": \"native\", \"test_result\": \"native\"}, \"is_continuation\": false, \"item_name\": \"符合要求\", \"metadata\": {\"field_columns\": {\"conclusion\": 5, \"item_name\": 1, \"remark\": 6, \"sequence_raw\": 0, \"standard_clause\": 2, \"standard_requirement\": 3, \"test_result\": 4}, \"item_name\": \"符合要求\", \"item_no\": \"——除了不产生功率输出的待机状态之外，原\\n来选择的高频手术模式不应改变。\", \"single_conclusion\": \"\", \"source_table_id\": \"p100-t1\"}, \"remark\": \"\", \"row_index_in_page\": 6, \"sequence\": null, \"sequence_raw\": \"——除了不产生功率输出的待机状态之外，原\\n来选择的高频手术模式不应改变。\", \"source_page\": 100, \"standard_clause\": \"\", \"test_result\": \"\"}], \"complex_matrix_reason\": null, \"complex_matrix_table\": false, \"conclusion_candidate_provenance\": [{\"page_number\": 100, \"raw_value\": \"符合\", \"row_index\": 5, \"sequence_raw\": \"149\", \"source\": \"native\"}], \"continuation_markers\": [], \"display_item_no\": \"149\", \"effective_remark\": \"/\", \"effective_single_conclusion\": \"符合\", \"effective_test_results\": [\"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [], \"group_row_count\": 2, \"item_no\": \"149\", \"pages\": [100], \"reasoning_basis\": \"all_placeholders_or_blank\", \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 1, \"total_count\": 1}, \"source_rows\": [{\"field_provenance\": {\"conclusion\": \"native\", \"item_name\": \"native\", \"remark\": \"native\", \"sequence_raw\": \"native\", \"standard_clause\": \"native\", \"standard_requirement\": \"native\", \"test_result\": \"native\"}, \"is_continuation\": false, \"item_name\": \"ME 设备\\n的供电电\\n源/供电\\n网中断\", \"item_no\": \"149\", \"metadata\": {\"field_columns\": {\"conclusion\": 5, \"item_name\": 1, \"remark\": 6, \"sequence_raw\": 0, \"standard_clause\": 2, \"standard_requirement\": 3, \"test_result\": 4}, \"item_name\": \"ME 设备\\n的供电电\\n源/供电\\n网中断\", \"item_no\": \"149\", \"single_conclusion\": \"符合\", \"source_table_id\": \"p100-t1\"}, \"normalized_item_no\": \"149\", \"page_number\": 100, \"rema\n[truncated]", "text": null, "title": "C07 检验项目 group evidence"}

### Evidence inspection_page_text:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch
{"file_path": null, "location": null, "metadata": "{\"check_id\": \"C07\", \"finding_id\": \"ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch\", \"pages\": [100]}", "page_number": 100, "ref_id": "inspection_page_text:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch", "section": "inspection_group_page_text", "source_type": "page_text", "structured": "{\"finding_metadata\": {\"actual_conclusion\": \"符合\", \"continuation_markers\": [], \"decision_reason\": \"all_placeholders_or_blank\", \"display_item_no\": \"149\", \"effective_test_results\": [\"——\"], \"expected_conclusion\": \"/\", \"group_diagnostics\": [], \"group_row_count\": 2, \"item_no\": \"149\", \"normalized_item_no\": \"149\", \"pages\": [100], \"reasoning_basis\": \"all_placeholders_or_blank\", \"result_summary\": {\"conforming_or_non_empty_count\": 0, \"nonconforming_count\": 0, \"placeholder_count\": 1, \"total_count\": 1}, \"result_values\": [\"——\"], \"source_rows\": [{\"is_continuation\": false, \"page_number\": 100, \"remark\": \"/\", \"result_values\": [\"——\"], \"row_index\": 5, \"sequence\": 149, \"sequence_raw\": \"149\", \"single_conclusion\": \"符合\", \"source_index\": 988, \"test_result\": \"——\"}, {\"is_continuation\": false, \"page_number\": 100, \"remark\": \"\", \"result_values\": [], \"row_index\": 6, \"sequence\": null, \"sequence_raw\": \"——除了不产生功率输出的待机状态之外，原\\n来选择的高频手术模式不应改变。\", \"single_conclusion\": \"\", \"source_index\": 989, \"test_result\": \"\"}], \"suppressed_physical_row_count\": 1}, \"pages\": [{\"page_number\": 100, \"text\": \"上\\n海\\n市\\n医\\n疗\\n器\\n械\\n检\\n验\\n研\\n究\\n院 \\n检 验 报 告 \\n报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 98 页 \\n \\n序\\n号 \\n检验 \\n项目 \\n标准 \\n条款 \\n标准要求 \\n检验结果 \\n单项 \\n结论 \\n备注 \\n146 ME 设备\\n和 ME 系\\n统中的液\\n体泼洒 \\n201.11.6\\n.3 \\n替换： \\n高频手术设备和附属设备的外壳结构应制成在\\n正常使用时不会因液体泼洒而弄湿电气绝缘和\\n那些一旦弄湿可能影响高频手术设备和附属设\\n备安全的其他元器件。 \\n符合要求 \\n符合 \\n/ \\n147 水或颗粒\\n物质侵入\\nME 设备\\n和 ME 系\\n统 \\n201.11.6\\n.5 \\n增补： \\na) 预期在手术室中使用的高频手术设备和附\\n属设备的脚踏开关，其电气开关部件应防止液\\n体进入，可能引起应用部分意外激励的影响。 \\n—— \\n/ \\n/ \\nb) 指揿开关的电气部件应能防止进液影响，\\n进液可能引起应用部分被意外激励（还可参见\\n201.8.8.3.103）。 \\n—— \\n148 ME 设备\\n和 ME 系\\n统的灭菌 \\n201.11.6\\n.7 \\n增补： \\n除非标记为仅一次性使用，手术附件及其所有\\n可拆卸部件（不用工具可从电缆上拆卸下来的\\n手术连接器除外），经过通用标准该条款规定\\n的试验后，都应符合本文件的要求。 \\n符合要求 \\n符合 \\n/ \\n149 ME 设备\\n的供电电\\n源/供电\\n网中断 \\n201.11.8  当高频手术设备电源关断再接通，或者供电网\\n中断再恢复时： \\n——输出控制器一个给定设定下的输出功率不\\n应增加 20%以上，并且 \\n—— \\n符合 \\n/ \\n——除了不产生功率输出的待机状态之外，原\\n来选择的高频手术模式不应改变。 \\n符合要求 \\n150 控制器和\\n仪表的准\\n确性 \\n201.12.1 增补条款： \\n201.12.1.101 输出控制设定的准确性 \\n对于超过额定输出功率的 10%的输出功率，作\\n为负载电阻和输出控制设定函数的实际输出功\\n率与 201.7.9.3.1 所规定的图示值偏差不应超\\n出±20%。 \\n-5%～+4% \\n符合 \\n/ \\n201.12.1.102 输出控制设定的单调性 \\n输出功率不应随输出控制设定的下降而升高\\n（见 201.7.9.3.1、图 201.109 和图\\n201.110）。 \\n符合要求 \\n201.12.1.103 最大输出电压的准确性 \\n对于高频手术设备可用的每一个高频手术模\\n式，施加于手术输出端子上的最大输出电压不\\n应超过 201.7.9.3.1 中规定的值。 \\n符合要求 \\n151 ME 设备\\n的可用性 \\n201.12.2 增补： \\na) 如果使用一个双踏板脚踏开关组件来选择\\n切和凝输出模式，则应设计成：按操作者方向\\n观察，左踏板启动切，右踏板启动凝。 \\n——  [truncated]\"}]}", "text": "[page 100]\n上\n海\n市\n医\n疗\n器\n械\n检\n验\n研\n究\n院 \n检 验 报 告 \n报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 98 页 \n \n序\n号 \n检验 \n项目 \n标准 \n条款 \n标准要求 \n检验结果 \n单项 \n结论 \n备注 \n146 ME 设备\n和 ME 系\n统中的液\n体泼洒 \n201.11.6\n.3 \n替换： \n高频手术设备和附属设备的外壳结构应制成在\n正常使用时不会因液体泼洒而弄湿电气绝缘和\n那些一旦弄湿可能影响高频手术设备和附属设\n备安全的其他元器件。 \n符合要求 \n符合 \n/ \n147 水或颗粒\n物质侵入\nME 设备\n和 ME 系\n统 \n201.11.6\n.5 \n增补： \na) 预期在手术室中使用的高频手术设备和附\n属设备的脚踏开关，其电气开关部件应防止液\n体进入，可能引起应用部分意外激励的影响。 \n—— \n/ \n/ \nb) 指揿开关的电气部件应能防止进液影响，\n进液可能引起应用部分被意外激励（还可参见\n201.8.8.3.103）。 \n—— \n148 ME 设备\n和 ME 系\n统的灭菌 \n201.11.6\n.7 \n增补： \n除非标记为仅一次性使用，手术附件及其所有\n可拆卸部件（不用工具可从电缆上拆卸下来的\n手术连接器除外），经过通用标准该条款规定\n的试验后，都应符合本文件的要求。 \n符合要求 \n符合 \n/ \n149 ME 设备\n的供电电\n源/供电\n网中断 \n201.11.8  当高频手术设备电源关断再接通，或者供电网\n中断再恢复时： \n——输出控制器一个给定设定下的输出功率不\n应增加 20%以上，并且 \n—— \n符合 \n/ \n——除了不产生功率输出的待机状态之外，原\n来选择的高频手术模式不应改变。 \n符合要求 \n150 控制器和\n仪表的准\n确性 \n201.12.1 增补条款： \n201.12.1.101 输出控制设定的准确性 \n对于超过额定输出功率的 10%的输出功率，作\n为负载电阻和输出控制设定函数的实际输出功\n率与 201.7.9.3.1 所规定的图示值偏差不应超\n出±20%。 \n-5%～+4% \n符合 \n/ \n201.12.1.102 输出控制设定的单调性 \n输出功率不应随输出控制设定的下降而升高\n（见 201.7.9.3.1、图 201.109 和图\n201.110）。 \n符合要求 \n201.12.1.103 最大输出电压的准确性 \n对于高频手术设备可用的每一个高频手术模\n式，施加于手术输出端子上的最大输出电压不\n应超过 201.7.9.3.1 中规定的值。 \n符合要求 \n151 ME 设备\n的可用性 \n201.12.2 增补： \na) 如果使用一个双踏板脚踏开关组件来选择\n切和凝输出模式，则应设计成：按操作者方向\n观察，左踏板启动切，右 [truncated]", "title": "C07 inspection item page text evidence"}

### Evidence page_text:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch
{"file_path": null, "location": null, "metadata": "{\"check_id\": \"C07\", \"file_id\": \"36628a34943d8df5\", \"finding_id\": \"ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch\"}", "page_number": 100, "ref_id": "page_text:ee21f597-1576-4008-835f-d81c89e0c107-c07-149-conclusion-mismatch", "section": "page_text", "source_type": "page_text", "structured": "{\"page_number\": 100, \"text\": \"上\\n海\\n市\\n医\\n疗\\n器\\n械\\n检\\n验\\n研\\n究\\n院 \\n检 验 报 告 \\n报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 98 页 \\n \\n序\\n号 \\n检验 \\n项目 \\n标准 \\n条款 \\n标准要求 \\n检验结果 \\n单项 \\n结论 \\n备注 \\n146 ME 设备\\n和 ME 系\\n统中的液\\n体泼洒 \\n201.11.6\\n.3 \\n替换： \\n高频手术设备和附属设备的外壳结构应制成在\\n正常使用时不会因液体泼洒而弄湿电气绝缘和\\n那些一旦弄湿可能影响高频手术设备和附属设\\n备安全的其他元器件。 \\n
[truncated]
