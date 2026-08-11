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

- package_id: codex-ptr-d396f5d2-5d18-4956-834b-cfd7db5ab0dc-batch-3
- task_id: d396f5d2-5d18-4956-834b-cfd7db5ab0dc
- task_type: ptr_compare
- kind: inspection_item_review
- schema_version: evidence-package-v1

## Targets

### Target ptr_review:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.2:undeclared
{"allowed_evidence_refs": ["finding:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.2:undeclared", "rule_context:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.2:undeclared", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.2"], "check_id": "PTR_REPORT_SCOPE", "finding_code": "PTR_SCOPE_UNDECLARED_REPORT_ITEM", "finding_id": "d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.2:undeclared", "metadata": {"atomic_id": null, "clause_number": "2.2", "finding_code": "PTR_SCOPE_UNDECLARED_REPORT_ITEM", "parameter_name": null, "severity": "error", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_SCOPE_UNDECLARED_REPORT_ITEM；check_id=PTR_REPORT_SCOPE；clause=2.2", "target_id": "ptr_review:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.2:undeclared", "target_type": "inspection_item", "title": "实际检验表出现首页未声明的 PTR 检验项目 2.2。"}

### Target ptr_review:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.8:undeclared
{"allowed_evidence_refs": ["finding:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.8:undeclared", "rule_context:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.8:undeclared", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.8"], "check_id": "PTR_REPORT_SCOPE", "finding_code": "PTR_SCOPE_UNDECLARED_REPORT_ITEM", "finding_id": "d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.8:undeclared", "metadata": {"atomic_id": null, "clause_number": "2.8", "finding_code": "PTR_SCOPE_UNDECLARED_REPORT_ITEM", "parameter_name": null, "severity": "error", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_SCOPE_UNDECLARED_REPORT_ITEM；check_id=PTR_REPORT_SCOPE；clause=2.8", "target_id": "ptr_review:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.8:undeclared", "target_type": "inspection_item", "title": "实际检验表出现首页未声明的 PTR 检验项目 2.8。"}

## Evidence Items

### Evidence finding:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.2:undeclared
{"file_path": null, "location": null, "metadata": "{\"check_id\": \"PTR_REPORT_SCOPE\", \"finding_code\": \"PTR_SCOPE_UNDECLARED_REPORT_ITEM\", \"finding_id\": \"d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.2:undeclared\", \"severity\": \"error\"}", "page_number": null, "ref_id": "finding:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.2:undeclared", "section": null, "source_type": "finding", "structured": "{\"actual\": \"2.2\", \"check_id\": \"PTR_REPORT_SCOPE\", \"code\": \"PTR_SCOPE_UNDECLARED_REPORT_ITEM\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"report-scope-declaration\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 3, \"row_index\": null, \"section\": null, \"source_id\": null, \"source_type\": \"report\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"2.1.1～2.1.12、2.2.2、2.3（仅检 PVC 反应）、2.6、2.7、2.8.2（除有源植入式\", \"source_type\": \"report\", \"value\": null}, {\"confidence\": null, \"id\": \"report-inspection-item-50\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 32, \"row_index\": 1, \"section\": null, \"source_id\": \"ae22a2b4d9d479ae\", \"source_type\": \"report\", \"table_id\": \"p32-t1\", \"text_span\": null}, \"metadata\": {\"item_no\": \"50\", \"page\": 32, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"2.2.2\", \"standard_requirement\": \"起搏器应有在紧急情况下的安全起搏模式。 \\n参数 \\n应急 VVI 设置 \\n模式 \\nVVI \\n基本频率 \\n70min\\n−1\\n \\n右室/左室脉冲振幅 \\n7.5 V/7.5V \\n右室/左室脉宽 \\n0.6ms/0.6ms \\n心室不应期 \\n325ms* \\n*实际显示为 310ms。\", \"test_result\": \"符合要求\"}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"2.2.2；起搏器应有在紧急情况下的安全起搏模式。 \\n参数 \\n应急 VVI 设置 \\n模式 \\nVVI \\n基本频率 \\n70min\\n−1\\n \\n右室/左室脉冲振幅 \\n7.5 V/7.5V \\n右室/左室脉宽 \\n0.6ms/0.6ms \\n心室不应期 \\n325ms* \\n*实际显示为 310ms。；符合要求；符合\", \"source_type\": \"report\", \"value\": null}], \"expected\": [\"2.2.2\", \"2.3\", \"2.6\", \"2.7\", \"2.8.2\"], \"id\": \"d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.2:undeclared\", \"location\": null, \"message\": \"实际检验表出现首页未声明的 PTR 检验项目 2.2。\", \"metadata\": {\"clause_number\": \"2.2\", \"item_no\": \"50\"}, \"missing_evidence\": [], \"severity\": \"error\", \"task_id\": \"d396f5d2-5d18-4956-834b-cfd7db5ab0dc\"}", "text": null, "title": "实际检验表出现首页未声明的 PTR 检验项目 2.2。"}

### Evidence finding:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.8:undeclared
{"file_path": null, "location": null, "metadata": "{\"check_id\": \"PTR_REPORT_SCOPE\", \"finding_code\": \"PTR_SCOPE_UNDECLARED_REPORT_ITEM\", \"finding_id\": \"d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.8:undeclared\", \"severity\": \"error\"}", "page_number": null, "ref_id": "finding:d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.8:undeclared", "section": null, "source_type": "finding", "structured": "{\"actual\": \"2.8\", \"check_id\": \"PTR_REPORT_SCOPE\", \"code\": \"PTR_SCOPE_UNDECLARED_REPORT_ITEM\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"report-scope-declaration\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 3, \"row_index\": null, \"section\": null, \"source_id\": null, \"source_type\": \"report\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"2.1.1～2.1.12、2.2.2、2.3（仅检 PVC 反应）、2.6、2.7、2.8.2（除有源植入式\", \"source_type\": \"report\", \"value\": null}, {\"confidence\": null, \"id\": \"report-inspection-item-54\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 33, \"row_index\": 3, \"section\": null, \"source_id\": \"ae22a2b4d9d479ae\", \"source_type\": \"report\", \"table_id\": \"p33-t1\", \"text_span\": null}, \"metadata\": {\"item_no\": \"54\", \"page\": 33, \"remark\": \"\", \"single_conclusion\": \"/\", \"standard_clause\": \"2.8.2\", \"standard_requirement\": \"扭矩扳手金属杆头截面尺寸应符合以下要求： \\n \\n图 2-1 扭矩扳手示意图 \\n \\n注：A. 金属杆头端截面平口尺寸 \\nB. 金属杆头端截面尖端到尖端距离 \\n图 2-2 扭矩扳手尺寸测量示意图 \\n单位：mm\", \"test_result\": \"符合\"}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"2.8.2；扭矩扳手金属杆头截面尺寸应符合以下要求： \\n \\n图 2-1 扭矩扳手示意图 \\n \\n注：A. 金属杆头端截面平口尺寸 \\nB. 金属杆头端截面尖端到尖端距离 \\n图 2-2 扭矩扳手尺寸测量示意图 \\n单位：mm；符合；/\", \"source_type\": \"report\", \"value\": null}], \"expected\": [\"2.2.2\", \"2.3\", \"2.6\", \"2.7\", \"2.8.2\"], \"id\": \"d396f5d2-5d18-4956-834b-cfd7db5ab0dc:PTR_REPORT_SCOPE:2.8:undeclared\", \"location\": null, \"message\": \"实际检验表出现首页未声明的 PTR 检验项目 2.8。\", \"metadata\": {\"clause_number\": \"2.8\", \"item_no\": \"54\"}, \"missing_evidence\": [], \"severity\": \"error\", \"task_id\": \"d396f5d2-5d18-4956-834b-cfd7db5ab0dc\"}", "text": null, "title": "实际检验表出现首页未声明的 PTR 检验项目 2.8。"}

### Evidence ptr_clause:ptr-2.2
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"clause_id\": \"ptr-2.2\", \"clause_number\": \"2.2\"}", "page_number": 4, "ref_id": "ptr_clause:ptr-2.2", "section": "2.2", "source_type": "ptr_clause", "structured": "{\"body_text\": \"2\\n紧急起搏模式\\n起搏器应有在紧急情况下的安全起搏模式。\\n参数\\n应急 VVI 设置\\n模式\\nVVI\\n基本频率\\n70min-1\\n右室/左室脉冲振幅\\n7.5 V/7.5V\\n右室/左室脉宽\\n0.6ms/0.6ms\\n心室不应期\\n325ms*\\n*实际显示为 310ms。\", \"clause_id\": \"ptr-2.2\", \"number\": \"2.2\", \"scope_type\": \"requirement\", \"table_numbers\": [], \"taxonomy\": \"requirement\", \"title\": \"2\"}", "text": "2\n紧急起搏模式\n起搏器应有在紧急情况下的安全起搏模式。\n参数\n应急 VVI 设置\n模式\nVVI\n基本频率\n70min-1\n右室/左室脉冲振幅\n7.5 V/7.5V\n右室/左室脉宽\n0.6ms/0.6ms\n心室不应期\n325ms*\n*实际显示为 310ms。", "title": "PTR clause 2.2"}

### Evidence ptr_clause:ptr-2.8
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 6, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"clause_id\": \"ptr-2.8\", \"clause_number\": \"2.8\"}", "page_number": 6, "ref_id": "ptr_clause:ptr-2.8", "section": "2.8", "source_type": "ptr_clause", "structured": "{\"body_text\": \"2\\n扭矩扳手尺寸\\n扭矩扳手金属杆头截面尺寸应符合以下要求：\\n0.88 毫米≤ A ≤ 0.89 毫米\\n0.96 毫米≤ B ≤ 1 毫米\\n图 2-1 扭矩扳手示意图\", \"clause_id\": \"ptr-2.8\", \"number\": \"2.8\", \"scope_type\": \"requirement\", \"table_numbers\": [], \"taxonomy\": \"requirement\", \"title\": \"2\"}", "text": "2\n扭矩扳手尺寸\n扭矩扳手金属杆头截面尺寸应符合以下要求：\n0.88 毫米≤ A ≤ 0.89 毫米\n0.96 毫米≤ B ≤ 1 毫米\n图 2-1 扭矩扳手示意图", "title": "PTR clause 2.8"}

### Evidence report_scope:declaration
{"file_path": null, "location": null, "metadata": "{\"field_name\": \"检验项目\", \"source\": \"report_homepage\"}", "page_number": 3, "ref_id": "report_scope:declaration", "section": "report_scope", "source_type": "report_field", "structured": "{\"declared_scope_items\": [\"2.2.2\", \"2.3\", \"2.6\", \"2.7\", \"2.8.2\"], \"declared_scope_ranges\": [{\"end\": \"2.1.12\", \"source_text\": \"2.1.1～2.1.12、2.2.2、2.3（仅检 PVC 反应）、2.6、2.7、2.8.2（除有源植入式\", \"start\": \"2.1.1\"}], \"excluded_topics\": [\"有源植入式\"], \"ptr_direct_content_starts_after\": \"37\", \"source_page\": 3, \"source_text\": \"2.1.1～2.1.12、2.2.2、2.3（仅检 PVC 反应）、2.6、2.7、2.8.2（除有源植入式\"}", "text": "2.1.1～2.1.12、2.2.2、2.3（仅检 PVC 反应）、2.6、2.7、2.8.2（除有源植入式", "title": "Report homepage inspection scope declaration"}

### Evidence report_scope:external_standard_ranges
{"file_path": null, "location": null, "metadata": "{\"source\": \"report_model_spec_or_notes\"}", "page_number": null, "ref_id": "report_scope:external_standard_ranges", "section": "external_standard_ranges", "source_type": "metadata", "structured": "{\"external_standard_ranges\": [{\"end_item_no\": \"24\", \"item_count\": 24, \"passed_count\": 20, \"sample_items\": [{\"item_no\": \"1\", \"page\": 5, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"5\", \"standard_requirement\": \"5.1 非植入部分的通用要求 \\n除那些已被本文件或专用要求所取代的要求\\n外，连接到电源或配有电源的有源植入式医疗\\n器械的非植入部分应符合风险分析所确定的\\nGB 9706.1-2020 的适当要求。注：本文件的\\n其他子条款也要求遵守 GB 9706.1-2020 的某\\n些子条款，未通电的非植入部分也是如此。\", \"test_result\": \"——\"}, {\"item_no\": \"2\", \"page\": 6, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"6\", \"standard_requirement\": \"对特定有源植入式医疗器械，本文件没有详细\\n提出要求，但可在专用要求中规定。\", \"test_result\": \"见序号 25\"}, {\"item_no\": \"3\", \"page\": 6, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"7\", \"standard_requirement\": \"7.1 有源植入式医疗器械的植入部分应使用不\\n可重复使用包装（见 14.1）。 \\n注：不可重复使用包装的设计，使制造商对其\\n内容物进行灭菌和包装密封。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"4\", \"page\": 6, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"8\", \"standard_requirement\": \"8.1 本文件要求的任何警告均应突出显示。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"5\", \"page\": 6, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"9\", \"standard_requirement\": \"9.1 如果销售包装内装有任何放射性物质，则\\n销售包装上应有标记，注明放射性物质的类型\\n和活性。\", \"test_result\": \"——\"}, {\"item_no\": \"6\", \"page\": 7, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"10\", \"standard_requirement\": \"10.1 有源植入式医疗器械的销售包装，其构\\n造应能保护医疗器械，使其能经受住在制造商\\n规定的存储或处理期间可能发生的跌落（冲\\n击）、堆叠（加压）、振动和温度变化。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"7\", \"page\": 8, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"11\", \"standard_requirement\": \"11.1 无菌包装应有制造商的名称或商标，以\\n及制造商的地址（国家和城市）。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"8\", \"page\": 8, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"12\", \"standard_requirement\": \"12.1 不可重复使用包装应符合 GB/T \\n19633.1。\", \"test_result\": \"符合要求\"}], \"source_page\": 4, \"source_text\": \"序号 1～序号 24 为 GB 16174.1-2024 的内容； 4.\", \"standard\": \"GB 16174.1-2024\", \"start_item_no\": \"1\"}, {\"end_item_no\": \"37\", \"item_count\": 13, \"passed_count\": 10, \"sample_items\": [{\"item_no\": \"25\", \"page\": 17, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"6\", \"standard_requirement\": \"6.1 植入式脉冲发生器特性的测量 \\n6.1.2 脉冲幅度、脉冲宽度、脉冲间期和脉冲\\n频率的测量\", \"test_result\": \"见序号\\n38～序号\\n40\"}, {\"item_no\": \"26\", \"page\": 18, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"9\", \"standard_requirement\": \"9.4 \\n附录 B 中定义的模式代码可使用于标记和随附\\n文件中,用来指明植入式脉冲发生器缓慢性心\\n律失常的起搏模式,代替文字描述。 \\n9.4.1 如适用,包含植入式脉冲发生器的销售\\n包装应具有下列信息。 \\na)最全面的起搏模式和(如果不同)出厂时的起\\n搏模式。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"27\", \"page\": 19, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"11\", \"standard_requirement\": \"11.10 包含植入式脉冲发生器的无菌包装应具\\n备下列信息: \\na)可用的最全面的起搏模式和出厂时的起搏模\\n式(见 9.4):\", \"test_result\": \"符合要求\"}, {\"item_no\": \"28\", \"page\": 20, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"13\", \"standard_requirement\": \"13.1 GB 16174.1-2024 中 13.1 不适用。\", \"test_result\": \"——\"}, {\"item_no\": \"29\", \"page\": 21, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"16\", \"standard_requirement\": \"16.2 GB 16174.1-2024 规定了在任何电极上\\n的最大直流电流密度不大于 0.75μA/mm²。这\\n种限制适用于任何起搏/感知端口允许的任何\\n净直流电流与连接此类端口的电极导线导体的\\n电极面积的组合。由于电极导线的结构(以及\\n电极导线电极的面积)不受植入式脉冲发生器\\n制造商的控制,因此在假定电极面积足够大不\\n超过规定电流密度的情况下,通过限制净直流\\n电流可满足 GB 16174.1-2024 限制的意图。 \\n除了其设计功能之外
[truncated]
