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

- package_id: codex-ptr-9c5a436f-17c5-412b-92a9-0de3d809a1a7-batch-0
- task_id: 9c5a436f-17c5-412b-92a9-0de3d809a1a7
- task_type: ptr_compare
- kind: ptr_table_review
- schema_version: evidence-package-v1

## Targets

### Target ptr_review:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_CLAUSE:2.2.1:mismatch
{"allowed_evidence_refs": ["finding:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_CLAUSE:2.2.1:mismatch", "rule_context:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_CLAUSE:2.2.1:mismatch", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.2.1"], "check_id": "PTR_CLAUSE", "finding_code": "PTR_CLAUSE_TEXT_MISMATCH", "finding_id": "9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_CLAUSE:2.2.1:mismatch", "metadata": {"clause_number": "2.2.1", "finding_code": "PTR_CLAUSE_TEXT_MISMATCH", "parameter_name": null, "severity": "error", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_CLAUSE_TEXT_MISMATCH；check_id=PTR_CLAUSE；clause=2.2.1", "target_id": "ptr_review:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_CLAUSE:2.2.1:mismatch", "target_type": "ptr_clause", "title": "PTR 条款 2.2.1 正文与报告标准要求不一致。"}

### Target ptr_review:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_REPORT_SCOPE:2.14:undeclared
{"allowed_evidence_refs": ["finding:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_REPORT_SCOPE:2.14:undeclared", "rule_context:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_REPORT_SCOPE:2.14:undeclared", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items"], "check_id": "PTR_REPORT_SCOPE", "finding_code": "PTR_SCOPE_UNDECLARED_REPORT_ITEM", "finding_id": "9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_REPORT_SCOPE:2.14:undeclared", "metadata": {"clause_number": "2.14", "finding_code": "PTR_SCOPE_UNDECLARED_REPORT_ITEM", "parameter_name": null, "severity": "error", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_SCOPE_UNDECLARED_REPORT_ITEM；check_id=PTR_REPORT_SCOPE；clause=2.14", "target_id": "ptr_review:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_REPORT_SCOPE:2.14:undeclared", "target_type": "inspection_item", "title": "实际检验表出现首页未声明的 PTR 检验项目 2.14。"}

## Evidence Items

### Evidence finding:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_CLAUSE:2.2.1:mismatch
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 3, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"check_id\": \"PTR_CLAUSE\", \"finding_code\": \"PTR_CLAUSE_TEXT_MISMATCH\", \"finding_id\": \"9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_CLAUSE:2.2.1:mismatch\", \"severity\": \"error\"}", "page_number": 3, "ref_id": "finding:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_CLAUSE:2.2.1:mismatch", "section": "chapter_2", "source_type": "finding", "structured": "{\"actual\": \"2.2.1心脏脉冲电场消融仪输出心脏脉冲电场消融仪应至少能够提供: 电压:3333V(峰值) 𝑝\", \"check_id\": \"PTR_CLAUSE\", \"code\": \"PTR_CLAUSE_TEXT_MISMATCH\", \"confidence\": \"medium\", \"diff_fragments\": [{\"kind\": \"insert\", \"source\": \"report\", \"text\": \"2.2.1\"}, {\"kind\": \"equal\", \"source\": \"both\", \"text\": \"心脏脉冲电场消融仪输出心脏脉冲电场消融仪应至少能够提供:电压:3333V(峰值)\"}, {\"kind\": \"replace\", \"source\": \"both\", \"text\": \"电流:57A(峰值) -> 𝑝\"}], \"evidence\": [{\"confidence\": null, \"id\": \"ptr-clause-2.2.1\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 3, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": \"心脏脉冲电场消融仪输出心脏脉冲电场消融仪应至少能够提供: 电压:3333V(峰值)电流:57A(峰值)\", \"raw_text\": \"心脏脉冲电场消融仪输出\\n心脏脉冲电场消融仪应至少能够提供：\\n电压：3333V（峰值）\\n电流：57A（峰值）\", \"source_type\": \"ptr\", \"value\": null}, {\"confidence\": null, \"id\": \"report-clause-2.2.1\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 99, \"row_index\": 3, \"section\": null, \"source_id\": \"e17bab159bcc09b0\", \"source_type\": \"report\", \"table_id\": \"p99-t1\", \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": \"2.2.1心脏脉冲电场消融仪输出心脏脉冲电场消融仪应至少能够提供: 电压:3333V(峰值) 𝑝\", \"raw_text\": \"2.2.1 心脏脉冲电场消融仪输出 \\n心脏脉冲电场消融仪应至少能够提供： \\n电压：3333V（峰值） \\n单位：V\\n𝑝\", \"source_type\": \"report\", \"value\": null}], \"expected\": \"心脏脉冲电场消融仪输出心脏脉冲电场消融仪应至少能够提供: 电压:3333V(峰值)电流:57A(峰值)\", \"id\": \"9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_CLAUSE:2.2.1:mismatch\", \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 3, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"message\": \"PTR 条款 2.2.1 正文与报告标准要求不一致。\", \"metadata\": {\"clause_number\": \"2.2.1\"}, \"missing_evidence\": [], \"severity\": \"error\", \"task_id\": \"9c5a436f-17c5-412b-92a9-0de3d809a1a7\"}", "text": null, "title": "PTR 条款 2.2.1 正文与报告标准要求不一致。"}

### Evidence finding:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_REPORT_SCOPE:2.14:undeclared
{"file_path": null, "location": null, "metadata": "{\"check_id\": \"PTR_REPORT_SCOPE\", \"finding_code\": \"PTR_SCOPE_UNDECLARED_REPORT_ITEM\", \"finding_id\": \"9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_REPORT_SCOPE:2.14:undeclared\", \"severity\": \"error\"}", "page_number": null, "ref_id": "finding:9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_REPORT_SCOPE:2.14:undeclared", "section": null, "source_type": "finding", "structured": "{\"actual\": \"2.14\", \"check_id\": \"PTR_REPORT_SCOPE\", \"code\": \"PTR_SCOPE_UNDECLARED_REPORT_ITEM\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"report-scope-declaration\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 3, \"row_index\": null, \"section\": null, \"source_id\": null, \"source_type\": \"report\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"2.2、 2.5、2.6 （除生物相容性、电磁兼容性）\", \"source_type\": \"report\", \"value\": null}, {\"confidence\": null, \"id\": \"report-inspection-item-续\\n129\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 85, \"row_index\": 1, \"section\": null, \"source_id\": \"e17bab159bcc09b0\", \"source_type\": \"report\", \"table_id\": \"p85-t1\", \"text_span\": null}, \"metadata\": {\"item_no\": \"续\\n129\", \"page\": 85, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"201.7.9.\\n2.14\", \"standard_requirement\": \"j) 对于手术电极和手术手柄，评估以下危险\\n情况的信息： \\n——手术电极杆与手术手柄连接处可见的外露\\n金属；\", \"test_result\": \"——\"}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"201.7.9.\\n2.14；j) 对于手术电极和手术手柄，评估以下危险\\n情况的信息： \\n——手术电极杆与手术手柄连接处可见的外露\\n金属；；——；符合\", \"source_type\": \"report\", \"value\": null}], \"expected\": [\"2.2\", \"2.5\", \"2.6\"], \"id\": \"9c5a436f-17c5-412b-92a9-0de3d809a1a7:PTR_REPORT_SCOPE:2.14:undeclared\", \"location\": null, \"message\": \"实际检验表出现首页未声明的 PTR 检验项目 2.14。\", \"metadata\": {\"clause_number\": \"2.14\", \"item_no\": \"续\\n129\"}, \"missing_evidence\": [], \"severity\": \"error\", \"task_id\": \"9c5a436f-17c5-412b-92a9-0de3d809a1a7\"}", "text": null, "title": "实际检验表出现首页未声明的 PTR 检验项目 2.14。"}

### Evidence ptr_clause:ptr-2.2.1
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 3, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"clause_id\": \"ptr-2.2.1\", \"clause_number\": \"2.2.1\"}", "page_number": 3, "ref_id": "ptr_clause:ptr-2.2.1", "section": "2.2.1", "source_type": "ptr_clause", "structured": "{\"body_text\": \"心脏脉冲电场消融仪输出\\n心脏脉冲电场消融仪应至少能够提供：\\n电压：3333V（峰值）\\n电流：57A（峰值）\", \"clause_id\": \"ptr-2.2.1\", \"number\": \"2.2.1\", \"scope_type\": \"requirement\", \"table_numbers\": [], \"taxonomy\": \"requirement\", \"title\": \"心脏脉冲电场消融仪输出\"}", "text": "心脏脉冲电场消融仪输出\n心脏脉冲电场消融仪应至少能够提供：\n电压：3333V（峰值）\n电流：57A（峰值）", "title": "PTR clause 2.2.1"}

### Evidence report_scope:declaration
{"file_path": null, "location": null, "metadata": "{\"field_name\": \"检验项目\", \"source\": \"report_homepage\"}", "page_number": 3, "ref_id": "report_scope:declaration", "section": "report_scope", "source_type": "report_field", "structured": "{\"declared_scope_items\": [\"2.2\", \"2.5\", \"2.6\"], \"declared_scope_ranges\": [], \"excluded_topics\": [\"生物相容性\", \"电磁兼容性\"], \"ptr_direct_content_starts_after\": \"156\", \"source_page\": 3, \"source_text\": \"2.2、 2.5、2.6 （除生物相容性、电磁兼容性）\"}", "text": "2.2、 2.5、2.6 （除生物相容性、电磁兼容性）", "title": "Report homepage inspection scope declaration"}

### Evidence report_scope:external_standard_ranges
{"file_path": null, "location": null, "metadata": "{\"source\": \"report_model_spec_or_notes\"}", "page_number": null, "ref_id": "report_scope:external_standard_ranges", "section": "external_standard_ranges", "source_type": "metadata", "structured": "{\"external_standard_ranges\": [{\"end_item_no\": \"118\", \"item_count\": 118, \"passed_count\": 73, \"sample_items\": [{\"item_no\": \"1\", \"page\": 10, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"4.1\", \"standard_requirement\": \"除非另有规定，本部分的要求应适用于正常使\\n用和合理可预见的误用。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"2\", \"page\": 10, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"4.2\", \"standard_requirement\": \"4.2.2 风险管理的通用要求 \\n应执行符合 YY/T 0316 的风险管理过程。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"3\", \"page\": 10, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"4.3\", \"standard_requirement\": \"在风险分析中，除了与基本安全相关的性能\\n外，制造商还应识别 ME 设备或 ME 系统临床功\\n能的性能，这对于实现预期用途是必需的，或\\n者能够影响 ME 设备或 ME 系统的安全性。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"4\", \"page\": 11, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"4.4\", \"standard_requirement\": \"制造商应在风险管理文档中声明 ME 设备或 ME\\n系统的预期使用寿命。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"5\", \"page\": 11, \"remark\": \"/\", \"single_conclusion\": \"/\", \"standard_clause\": \"4.5\", \"standard_requirement\": \"制造商提供科学数据或临床意见或比较研究来\\n证明应用替代的风险控制措施或替代的试验方\\n法所得到的剩余风险仍然是可接受的，且与应\\n用本部分的要求所得到的剩余风险可比，则风\\n险控制替代的措施或试验方法是可接受。\", \"test_result\": \"——\"}, {\"item_no\": \"6\", \"page\": 11, \"remark\": \"/\", \"single_conclusion\": \"/\", \"standard_clause\": \"4.6\", \"standard_requirement\": \"对于那些接触患者但在应用部分定义之外的部\\n分，风险管理过程应评估其是否需要符合应用\\n部分的要求。除非评估确定需要适用 BF 型应\\n用部分或 CF 型应用部分的要求，否则有关的\\n部分应适用 B 型应用部分的要求。\", \"test_result\": \"——\"}, {\"item_no\": \"7\", \"page\": 11, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"4.7\", \"standard_requirement\": \"ME 设备应被设计和制造成保持单一故障安\\n全，或通过 4.2 的应用，确定风险仍然可接\\n受。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"8\", \"page\": 11, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"4.8\", \"standard_requirement\": \"除本部分中特殊规定的或通过风险管理过程控\\n制的特例外，其故障可能导致危险情况的所有\\n元器件，包括电线，应根据它们规定的额定值\\n使用。\", \"test_result\": \"符合要求\"}], \"source_page\": 5, \"source_text\": \"序号 1～序号 118 为 GB 9706.1-2020 标准的内容，序号 119～序号 156 为 GB 9706.202-2021 标准的内容。 3、本次检验，是与委托方提供的电生理三维导航系统（型号：AFR-00016，批号：25230007CW，生 产日期：2025/06/02，制造商：Medtronic, Inc.美敦力公司，软件版本为 2.1.17-0003）、台车 （型号：AFR-00013，批号：0231676121， 生产日期：2025/07/01，制造商：Medtronic, Inc.美敦 力公司）、灌注泵（型号：AFR-00005，批号：2521001CMO，生产日期：2025/05/19，制造商： Medtronic, Inc.美敦力公司，软件版本：1.1.2-0002）、泵管（型号：AFR-00002，批号： 0230958565，生产日期：2025/05/19，制造商：Medtronic, Inc.美敦力公司）、射频消融仪（型 号：AFR-00004，批号：2524004CRO，生产日期：2025/06/10，制造商：Medtronic, Inc.美敦力公 司，软件版本：1.3.1-0001，固件版本：5.01）、一次性使用磁定位三维标测射频脉冲晶格异形导管 （型号：AFR-00001，批号：0230752610，生产日期：2025-02-28，制造商：Medtronic, Inc.美敦 力公司）、导管延长线缆（型号：AFR-00006，批号：0230738609，生产日期：2025-02-20，制造 商：Medtronic, Inc.美敦力公司）、磁定位参考电极（型号：AFR-00021，批号：A11497，生产日 期：2024-11-30，制造商：Medtronic, Inc.美敦力公司）、阻抗定位参考电极（型号：AFR-00015， 批号：A11483，生产日期：2025-4-30，制造商：Medtronic, Inc.美敦力公司）配合使用时的检验 结果。 4、本次检验，电磁兼容性检验见国医检(磁)字 QW2025 第 1540 号。 5、本次检验，固件版本为 7.07。 6、本报告中有检验项目不涉及国家标准、行业标准，不能直接作为资质认定许可的依据，但本实 验室对报告涉及的检验项目具备相应的承检能力。\", \"standard\": \"GB 9706.1-2020\", \"start_item_no\": \"1\"}, {\"end_item_no\": \"156\", \"item_count\": 38, \"passed_count\": 28, \"sample_items\": [{\"item_no\": \"119\", \"page\": 79, \"remark\": \"/\", \"single_conclusion\": \"/\", \"standard_clause\": \"201.4.2.\\n3.101\", \"standard_requirement\": \"制造商在其风险分析中应包含高频手术设备和\\n/或高频附件在大电流模式下使用的可能性和\\n这会对中性电极下发热的影响。\", \"test_result\": \"——\"}, {\"item_no\": \"120\", \"page\": 79, \"remark\": \"/\", \"single_conclusion\": \"/\", \"standard_clause\": \"201.4.3\", \"standard_requirement\": \"增补： \\n201.8.4.101 的第三个连字符和\", \"test_result\": \"——\"}, {\"item_no\": \"121\", \"page\": 80, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"201.4.7.\\n101\", \"standard_requirement\": \"以下单一故障状态是本文件中特殊要求和测试\\n的项目： \\na) 可能引起不可接受的风险的连续性监测器\\n或接触质量监测器故障（见 201.8.4.101）；\", \"test_result\": \"符合要求\"}, {\"item_no\": \"122\", \"page\": 80, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"201.4.11\", \"standard_requirement\": \"替换符合性试验中的第一个破折号： \\n——高频手术设备应在输出模式下运行，并用\\n负载使设备产生最大稳态输入电流。测量输入\\n电流，并与标记和技术说明书的内容进行比\\n较。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"123\", \"page\": 80, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"201.7.2.\\n8.2\", \"standard_require\n[truncated]", "text": null, "title": "Report external standard sequence ranges"}

### Evidence report_scope:inspection_items
{"file_path": null, "location": null, "metadata": "{\"source\": \"report_inspection_table\"}", "page_number": null, "ref_id": "report_scope:inspection_items", "section": "inspection_items", "source_type": "table", "structured": "{\"item_count\": 5, \"items\": [{\"item_n
[truncated]
