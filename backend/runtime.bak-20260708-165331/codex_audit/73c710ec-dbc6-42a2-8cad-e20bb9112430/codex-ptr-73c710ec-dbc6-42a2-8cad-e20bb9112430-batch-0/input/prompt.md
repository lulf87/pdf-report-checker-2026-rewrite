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
- 只有 matched label OCR 属于当前 component 时，才可判断字段缺失或不一致。
- 无 matched OCR/crop/structured fields 时应 uncertain。
- matched_label_page_text 只是照片页或 caption 周边文本，不能当作标签本体 OCR。
- matched_label_ocr_text 才是标签本体 OCR 文本；matched_label_fields 才是结构化标签字段。
- 如果提供 label image/crop image，请把它作为当前 component 的中文标签视觉证据，不要把 caption 文本当作标签本体字段。
- 请视觉读取标签图片中的部件名称、规格型号、序列号/批号、生产日期和其他可见字段。
- C04 视觉审核输出应在 metadata 中填写 observed_label_fields、field_comparisons 和 visual_evidence_quality。
- visual_evidence_quality 为 clear/partial 时，可结合图片字段 refute 或 confirm；图片不可读、crop 错误或字段看不清时，应 uncertain/manual_review_required。
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
            "properties": {
              "field_comparisons": {
                "items": {
                  "additionalProperties": false,
                  "properties": {
                    "evidence_ref": {
                      "type": [
                        "string",
                        "null"
                      ]
                    },
                    "expected_value": {
                      "type": [
                        "string",
                        "null"
                      ]
                    },
                    "field_name": {
                      "type": "string"
                    },
                    "observed_value": {
                      "type": [
                        "string",
                        "null"
                      ]
                    },
                    "reasoning": {
                      "type": "string"
                    },
                    "status": {
                      "enum": [
                        "match",
                        "missing",
                        "conflict",
                        "unreadable",
                        "not_applicable",
                        "unknown"
                      ],
                      "type": "string"
                    }
                  },
                  "required": [
                    "field_name",
                    "expected_value",
                    "observed_value",
                    "status",
                    "evidence_ref",
                    "reasoning"
                  ],
                  "type": "object"
                },
                "type": "array"
              },
              "observed_label_fields": {
                "additionalProperties": false,
                "properties": {
                  "batch_or_serial": {
                    "type": [
                      "string",
                      "null"
                    ]
                  },
                  "component_name": {
                    "type": [
                      "string",
                      "null"
                    ]
                  },
                  "expiration_date": {
                    "type": [
                      "string",
                      "null"
                    ]
                  },
                  "model": {
                    "type": [
                      "string",
                      "null"
                    ]
                  },
                  "production_date": {
                    "type": [
                      "string",
                      "null"
                    ]
                  },
                  "serial_number": {
                    "type": [
                      "string",
                      "null"
                    ]
                  }
                },
                "required": [
                  "component_name",
                  "model",
                  "serial_number",
                  "batch_or_serial",
                  "production_date",
                  "expiration_date"
                ],
                "type": "object"
              },
              "visual_evidence_quality": {
                "enum": [
                  "clear",
                  "partial",
                  "unreadable",
                  "wrong_crop",
                  "not_applicable",
                  "unknown",
                  null
                ],
                "type": [
                  "string",
                  "null"
                ]
              }
            },
            "required": [
              "observed_label_fields",
              "field_comparisons",
              "visual_evidence_quality"
            ],
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

- package_id: codex-ptr-73c710ec-dbc6-42a2-8cad-e20bb9112430-batch-0
- task_id: 73c710ec-dbc6-42a2-8cad-e20bb9112430
- task_type: ptr_compare
- kind: ptr_clause_review
- schema_version: evidence-package-v1

## Targets

### Target ptr_review:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.1:missing
{"allowed_evidence_refs": ["finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.1:missing", "rule_context:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.1:missing", "ptr_clause:ptr-2.1.1"], "check_id": "PTR_CLAUSE", "finding_code": "PTR_CLAUSE_MISSING", "finding_id": "73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.1:missing", "metadata": {"clause_number": "2.1.1", "finding_code": "PTR_CLAUSE_MISSING", "parameter_name": null, "severity": "error", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_CLAUSE_MISSING；check_id=PTR_CLAUSE；clause=2.1.1", "target_id": "ptr_review:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.1:missing", "target_type": "ptr_clause", "title": "报告标准要求中未找到 PTR 条款 2.1.1。"}

### Target ptr_review:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.2:missing
{"allowed_evidence_refs": ["finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.2:missing", "rule_context:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.2:missing", "ptr_clause:ptr-2.1.2"], "check_id": "PTR_CLAUSE", "finding_code": "PTR_CLAUSE_MISSING", "finding_id": "73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.2:missing", "metadata": {"clause_number": "2.1.2", "finding_code": "PTR_CLAUSE_MISSING", "parameter_name": null, "severity": "error", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_CLAUSE_MISSING；check_id=PTR_CLAUSE；clause=2.1.2", "target_id": "ptr_review:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.2:missing", "target_type": "ptr_clause", "title": "报告标准要求中未找到 PTR 条款 2.1.2。"}

### Target ptr_review:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.3:missing
{"allowed_evidence_refs": ["finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.3:missing", "rule_context:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.3:missing", "ptr_clause:ptr-2.1.3"], "check_id": "PTR_CLAUSE", "finding_code": "PTR_CLAUSE_MISSING", "finding_id": "73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.3:missing", "metadata": {"clause_number": "2.1.3", "finding_code": "PTR_CLAUSE_MISSING", "parameter_name": null, "severity": "error", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_CLAUSE_MISSING；check_id=PTR_CLAUSE；clause=2.1.3", "target_id": "ptr_review:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.3:missing", "target_type": "ptr_clause", "title": "报告标准要求中未找到 PTR 条款 2.1.3。"}

### Target ptr_review:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.4:missing
{"allowed_evidence_refs": ["finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.4:missing", "rule_context:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.4:missing", "ptr_clause:ptr-2.1.4"], "check_id": "PTR_CLAUSE", "finding_code": "PTR_CLAUSE_MISSING", "finding_id": "73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.4:missing", "metadata": {"clause_number": "2.1.4", "finding_code": "PTR_CLAUSE_MISSING", "parameter_name": null, "severity": "error", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_CLAUSE_MISSING；check_id=PTR_CLAUSE；clause=2.1.4", "target_id": "ptr_review:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.4:missing", "target_type": "ptr_clause", "title": "报告标准要求中未找到 PTR 条款 2.1.4。"}

### Target ptr_review:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.5:missing
{"allowed_evidence_refs": ["finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.5:missing", "rule_context:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.5:missing", "ptr_clause:ptr-2.1.5"], "check_id": "PTR_CLAUSE", "finding_code": "PTR_CLAUSE_MISSING", "finding_id": "73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.5:missing", "metadata": {"clause_number": "2.1.5", "finding_code": "PTR_CLAUSE_MISSING", "parameter_name": null, "severity": "error", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_CLAUSE_MISSING；check_id=PTR_CLAUSE；clause=2.1.5", "target_id": "ptr_review:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.5:missing", "target_type": "ptr_clause", "title": "报告标准要求中未找到 PTR 条款 2.1.5。"}

## Evidence Items

### Evidence finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.1:missing
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"check_id\": \"PTR_CLAUSE\", \"finding_code\": \"PTR_CLAUSE_MISSING\", \"finding_id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.1:missing\", \"severity\": \"error\"}", "page_number": 2, "ref_id": "finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.1:missing", "section": "chapter_2", "source_type": "finding", "structured": "{\"actual\": null, \"check_id\": \"PTR_CLAUSE\", \"code\": \"PTR_CLAUSE_MISSING\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"ptr-clause-2.1.1\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": \"工作频率应为488 kHz ± 1 kHz。\", \"raw_text\": \"工作频率\\n工作频率应为 488 kHz ± 1 kHz。\", \"source_type\": \"ptr\", \"value\": null}], \"expected\": \"工作频率应为488 kHz ± 1 kHz。\", \"id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.1:missing\", \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"message\": \"报告标准要求中未找到 PTR 条款 2.1.1。\", \"metadata\": {\"clause_number\": \"2.1.1\"}, \"missing_evidence\": [{\"expected_source\": \"report\", \"label\": \"报告标准要求\", \"location\": null, \"metadata\": {}, \"reason\": \"未找到标准条款 2.1.1 对应的报告条款正文。\"}], \"severity\": \"error\", \"task_id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430\"}", "text": null, "title": "报告标准要求中未找到 PTR 条款 2.1.1。"}

### Evidence finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.2:missing
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"check_id\": \"PTR_CLAUSE\", \"finding_code\": \"PTR_CLAUSE_MISSING\", \"finding_id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.2:missing\", \"severity\": \"error\"}", "page_number": 2, "ref_id": "finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.2:missing", "section": "chapter_2", "source_type": "finding", "structured": "{\"actual\": null, \"check_id\": \"PTR_CLAUSE\", \"code\": \"PTR_CLAUSE_MISSING\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"ptr-clause-2.1.2\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": \"最大输出电压应至少为240 Vrms。\", \"raw_text\": \"最大输出电压\\n最大输出电压应至少为 240 Vrms。\", \"source_type\": \"ptr\", \"value\": null}], \"expected\": \"最大输出电压应至少为240 Vrms。\", \"id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.2:missing\", \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"message\": \"报告标准要求中未找到 PTR 条款 2.1.2。\", \"metadata\": {\"clause_number\": \"2.1.2\"}, \"missing_evidence\": [{\"expected_source\": \"report\", \"label\": \"报告标准要求\", \"location\": null, \"metadata\": {}, \"reason\": \"未找到标准条款 2.1.2 对应的报告条款正文。\"}], \"severity\": \"error\", \"task_id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430\"}", "text": null, "title": "报告标准要求中未找到 PTR 条款 2.1.2。"}

### Evidence finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.3:missing
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"check_id\": \"PTR_CLAUSE\", \"finding_code\": \"PTR_CLAUSE_MISSING\", \"finding_id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.3:missing\", \"severity\": \"error\"}", "page_number": 2, "ref_id": "finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.3:missing", "section": "chapter_2", "source_type": "finding", "structured": "{\"actual\": null, \"check_id\": \"PTR_CLAUSE\", \"code\": \"PTR_CLAUSE_MISSING\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"ptr-clause-2.1.3\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": \"输出功率输出功率在0-800 W内的准确度应为标称值(±10%,2 W),两者取大值。\", \"raw_text\": \"输出功率\\n输出功率在 0-800 W 内的准确度应为标称值（±10%，2 W），两者取大值。\", \"source_type\": \"ptr\", \"value\": null}], \"expected\": \"输出功率输出功率在0-800 W内的准确度应为标称值(±10%,2 W),两者取大值。\", \"id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.3:missing\", \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"message\": \"报告标准要求中未找到 PTR 条款 2.1.3。\", \"metadata\": {\"clause_number\": \"2.1.3\"}, \"missing_evidence\": [{\"expected_source\": \"report\", \"label\": \"报告标准要求\", \"location\": null, \"metadata\": {}, \"reason\": \"未找到标准条款 2.1.3 对应的报告条款正文。\"}], \"severity\": \"error\", \"task_id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430\"}", "text": null, "title": "报告标准要求中未找到 PTR 条款 2.1.3。"}

### Evidence finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.4:missing
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"check_id\": \"PTR_CLAUSE\", \"finding_code\": \"PTR_CLAUSE_MISSING\", \"finding_id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.4:missing\", \"severity\": \"error\"}", "page_number": 2, "ref_id": "finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.4:missing", "section": "chapter_2", "source_type": "finding", "structured": "{\"actual\": null, \"check_id\": \"PTR_CLAUSE\", \"code\": \"PTR_CLAUSE_MISSING\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"ptr-clause-2.1.4\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": \"温度测量范围及准确度系统应在以下范围内测量温度,并达到规定的准确度:\", \"raw_text\": \"温度测量范围及准确度\\n系统应在以下范围内测量温度，并达到规定的准确度：\", \"source_type\": \"ptr\", \"value\": null}], \"expected\": \"温度测量范围及准确度系统应在以下范围内测量温度,并达到规定的准确度:\", \"id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.4:missing\", \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"message\": \"报告标准要求中未找到 PTR 条款 2.1.4。\", \"metadata\": {\"clause_number\": \"2.1.4\"}, \"missing_evidence\": [{\"expected_source\": \"report\", \"label\": \"报告标准要求\", \"location\": null, \"metadata\": {}, \"reason\": \"未找到标准条款 2.1.4 对应的报告条款正文。\"}], \"severity\": \"error\", \"task_id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430\"}", "text": null, "title": "报告标准要求中未找到 PTR 条款 2.1.4。"}

### Evidence finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.5:missing
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"check_id\": \"PTR_CLAUSE\", \"finding_code\": \"PTR_CLAUSE_MISSING\", \"finding_id\": \"73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.5:missing\", \"severity\": \"error\"}", "page_number": 2, "ref_id": "finding:73c710ec-dbc6-42a2-8cad-e20bb9112430:PTR_CLAUSE:2.1.5:missing", "section": "chapter_2", "source_type": "finding", "structured": "{\"actual\": null, \"check_id\": \"PTR_CLAUSE\", \"code\": \"PTR_CLAUSE_MISSING\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"ptr-clause-2.1.5\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 2, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": \"阻抗测量射频消融仪在阻抗工作范围为20至120Ω的准确度应为
[truncated]
