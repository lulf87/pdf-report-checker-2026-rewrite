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

- package_id: codex-ptr-99ff98c8-af45-4302-b934-7327bc6529c0-batch-3
- task_id: 99ff98c8-af45-4302-b934-7327bc6529c0
- task_type: ptr_compare
- kind: ptr_parameter_review
- schema_version: evidence-package-v1

## Targets

### Target ptr_review:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:peak_ratio:pf_reversible:unbound
{"allowed_evidence_refs": ["finding:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:peak_ratio:pf_reversible:unbound", "rule_context:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:peak_ratio:pf_reversible:unbound", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.2.2", "report_inspection_group:157"], "check_id": "PTR_TABLE", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "finding_id": "99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:peak_ratio:pf_reversible:unbound", "metadata": {"atomic_id": "2.2.2:peak_ratio:pf_reversible", "clause_number": "2.2.2", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "parameter_name": null, "severity": "warn", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_ATOMIC_RESULT_UNBOUND；check_id=PTR_TABLE；clause=2.2.2", "target_id": "ptr_review:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:peak_ratio:pf_reversible:unbound", "target_type": "ptr_parameter", "title": "PTR 条款 2.2.2 的参数 正峰值/负峰值 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告序号 157 未稳定展开表格参数结果，需复核。"}

### Target ptr_review:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pulse3:unbound
{"allowed_evidence_refs": ["finding:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pulse3:unbound", "rule_context:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pulse3:unbound", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.2.2", "report_inspection_group:157"], "check_id": "PTR_TABLE", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "finding_id": "99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pulse3:unbound", "metadata": {"atomic_id": "2.2.2:current_level:pulse3", "clause_number": "2.2.2", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "parameter_name": null, "severity": "warn", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_ATOMIC_RESULT_UNBOUND；check_id=PTR_TABLE；clause=2.2.2", "target_id": "ptr_review:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pulse3:unbound", "target_type": "ptr_parameter", "title": "PTR 条款 2.2.2 的参数 电流水平 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告序号 157 未稳定展开表格参数结果，需复核。"}

### Target ptr_review:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pf_reversible:unbound
{"allowed_evidence_refs": ["finding:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pf_reversible:unbound", "rule_context:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pf_reversible:unbound", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.2.2", "report_inspection_group:157"], "check_id": "PTR_TABLE", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "finding_id": "99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pf_reversible:unbound", "metadata": {"atomic_id": "2.2.2:current_level:pf_reversible", "clause_number": "2.2.2", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "parameter_name": null, "severity": "warn", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_ATOMIC_RESULT_UNBOUND；check_id=PTR_TABLE；clause=2.2.2", "target_id": "ptr_review:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pf_reversible:unbound", "target_type": "ptr_parameter", "title": "PTR 条款 2.2.2 的参数 电流水平 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告序号 157 未稳定展开表格参数结果，需复核。"}

### Target ptr_review:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---功率监测:unbound
{"allowed_evidence_refs": ["finding:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---功率监测:unbound", "rule_context:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---功率监测:unbound", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.6", "report_inspection_group:159"], "check_id": "PTR_TABLE", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "finding_id": "99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---功率监测:unbound", "metadata": {"atomic_id": "2.6:table6:射频消融仪---功率监测", "clause_number": "2.6", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "parameter_name": null, "severity": "warn", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_ATOMIC_RESULT_UNBOUND；check_id=PTR_TABLE；clause=2.6", "target_id": "ptr_review:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---功率监测:unbound", "target_type": "ptr_parameter", "title": "PTR 条款 2.6 的参数 射频消融仪 - 功率监测 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告序号 159 未稳定展开表格功能明细需复核。"}

### Target ptr_review:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---控制应用启动和停止:unbound
{"allowed_evidence_refs": ["finding:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---控制应用启动和停止:unbound", "rule_context:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---控制应用启动和停止:unbound", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.6", "report_inspection_group:159"], "check_id": "PTR_TABLE", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "finding_id": "99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---控制应用启动和停止:unbound", "metadata": {"atomic_id": "2.6:table6:射频消融仪---控制应用启动和停止", "clause_number": "2.6", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "parameter_name": null, "severity": "warn", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_ATOMIC_RESULT_UNBOUND；check_id=PTR_TABLE；clause=2.6", "target_id": "ptr_review:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---控制应用启动和停止:unbound", "target_type": "ptr_parameter", "title": "PTR 条款 2.6 的参数 射频消融仪 - 控制应用启动和停止 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告序号 159 未稳定展开表格功能明细需复核。"}

## Evidence Items

### Evidence finding:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pf_reversible:unbound
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"check_id\": \"PTR_TABLE\", \"finding_code\": \"PTR_ATOMIC_RESULT_UNBOUND\", \"finding_id\": \"99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pf_reversible:unbound\", \"severity\": \"warn\"}", "page_number": 4, "ref_id": "finding:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pf_reversible:unbound", "section": "chapter_2", "source_type": "finding", "structured": "{\"actual\": null, \"check_id\": \"PTR_TABLE\", \"code\": \"PTR_ATOMIC_RESULT_UNBOUND\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"ptr-atomic-2.2.2:current_level:pf_reversible\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"2.2.2 心脏脉冲电场消融仪输出波形图和波形参数\\n心脏脉冲电场消融仪输出波形图和波形参数\\n心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满足表 6 的要求。\\n图 1 心脏脉冲电场消融仪 PULSE 3 预设输出波形图\\n表 6 波形参数\\n参数\\nPULSE 3 预设\\nPF Reversible 预设\\n脉冲个数\\n1500\\n1\\n脉冲组数\\n12\\n1\\n脉冲组间隔\\natomic=2.2.2:current_level:pf_reversible; expected=1-100%\", \"source_type\": \"ptr\", \"value\": null}, {\"confidence\": null, \"id\": \"report-atomic-2.2.2:current_level:pf_reversible\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 99, \"row_index\": null, \"section\": null, \"source_id\": null, \"source_type\": \"report\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"full_group_text:\\n157 心脏脉冲\\n电场消融\\n仪 2.2 2.2.1 心脏脉冲电场消融仪输出 \\n心脏脉冲电场消融仪应至少能够提供： \\n电压：3333V（峰值） \\n单位：V\\n𝑝 3375 符合 / 3375 157 心脏脉冲\\n电场消融\\n仪 2.2 2.2.1 心脏脉冲电场消融仪输出 \\n心脏脉冲电场消融仪应至少能够提供： \\n电压：3333V（峰值） \\n单位：V\\n𝑝 3375 符合 /\\n电流：57A（峰值） \\n单位：A\\n𝑝 59 / 电流：57A（峰值） \\n单位：A\\n𝑝 59 /\\n2.2.2 心脏脉冲电场消融仪输出波形图和波形参数 \\n心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满\\n足表 6 的要求。 \\n图 1 是心脏脉冲电场消融仪输出波形图。 / 2.2.2 心脏脉冲电场消融仪输出波形图和波形参数 \\n心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满\\n足表 6 的要求。 \\n图 1 是心脏脉冲电场消融仪输出波形图。 /\\n续\\n157 心脏脉冲\\n电场消融\\n仪 2.2 脉冲相\\n间隔 1μsec±20% -13%～-8% 符合 1μsec±20% 续\\n157 心脏脉冲\\n电场消融\\n仪 2.2 脉冲相\\n间隔 1μsec±20% -13%～-8% 符合 /\\n2.2.3 脉冲上升时间 \\n脉冲上升时间应不超过 700ns。 \\n单位：ns 430 PULSE3 预\\n设 2.2.3 脉冲上升时间 \\n脉冲上升时间应不超过 700ns。 \\n单位：ns 430 PULSE3 预\\n设\\n续\\n157 心脏脉冲\\n电场消融\\n仪 2.2 2.2.5 脉冲衰减 \\n稳定输出后（第一个脉冲组之后），每个脉冲\\n组开始时的电压相比前一组脉冲组结束时电压\\n衰减应在 10%内。 1% 符合 / 1% 续\\n157 心脏脉冲\\n电场消融\\n仪 2.2 2.2.5 脉冲衰减 \\n稳定输出后（第一个脉冲组之后），每个脉冲\\n组开始时的电压相比前一组脉冲组结束时电压\\n衰减应在 10%内。 1% 符合 /\\n2.2.6 最大输出能量 \\n单个脉冲最大输出能量应小于 258mJ。 \\n单位：mJ 159 / 2.2.6 最大输出能量 \\n单个脉冲最大输出能量应小于 258mJ。 \\n单位：mJ 159 /\\n2.2.7 保护功能 \\n2.2.7.1 温度超限保护 \\n心脏脉冲电场消融仪应具有温度超限报警功能\\n并自动切断脉冲电场能量输出。 符合要求 / 2.2.7 保护功能 \\n2.2.7.1 温度超限保护 \\n心脏脉冲电场消融仪应具有温度超限报警功能\\n并自动切断脉冲电场能量输出。 符合要求 /\\n2.2.7.2 过流保护 \\n如果测量的脉冲电场输出电流高于“最大限\\n值”超过 50ms 时，则应生成错误提示。 符合要求 / 2.2.7.2 过流保护 \\n如果测量的脉冲电场输出电流高于“最大限\\n值”超过 50ms 时，则应生成错误提示。 符合要求 /\\n157；心脏脉冲\\n电场消融\\n仪；2.2；2.2.1 心脏脉冲电场消融仪输出 \\n心脏脉冲电场消融仪应至少能够提供： \\n电压：3333V（峰值） \\n单位：V\\n𝑝；3375；符合；/；157 心脏脉冲\\n电场消融\\n仪 2.2 2.2.1 心脏脉冲电场消融仪输出 \\n心脏脉冲电场消融仪应至少能够提供： \\n电压：3333V（峰值） \\n单位：V\\n𝑝 3375 符合 /；电流：57A（峰值） \\n单位：A\\n𝑝；59；电流：57A（峰值） \\n单位：A\\n𝑝 59 /；2.2.2 心脏脉冲电场消融仪输出波形图和波形参数 \\n心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满\\n足表 6 的要求。 \\n图 1 是心脏脉冲电场消融仪输出波形图。；2.2.2 心脏脉冲电场消融仪输出波形图和波形参数 \\n心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满\\n足表 6 的要求。 \\n图 1 是心脏脉冲电场消融仪输出波形图。 /；续\\n157；脉冲相\\n间隔；1μsec±20%；-13%～-8%；续\\n157 心脏脉冲\\n电场消融\\n仪 2.2 脉冲相\\n间隔 1μsec±20% -13%～-8% 符合 /；2.2.3 脉冲上升时间 \\n脉冲上升时间应不超过 700ns。 \\n单位：ns；430；PULSE3 预\\n设；2.2.3 脉冲上升时间 \\n脉冲上升时间应不超过 700ns。 \\n单位：ns 430 PULSE3 预\\n设；2.2.5 脉冲衰减 \\n稳定输出后（第一个脉冲组之后），每个脉冲\\n组开始时的电压相比前一组脉冲组结束时电压\\n衰减应在 10%内。；1%；续\\n157 心脏脉冲\\n电场消融\\n仪 2.2 2.2.5 脉冲衰减 \\n稳定输出后（第一个脉冲组之后），每个脉冲\\n组开始时的电压相比前一组脉冲组结束时电压\\n衰减应在 10%内。 1% 符合 /；2.2.6 最大输出能量 \\n单个脉冲最大输出能量应小于 258mJ。 \\n单位：mJ；159；2.2.6 最大输出能量 \\n单个脉冲最大输出能量应小于 258mJ。 \\n单位：mJ 159 /；2.2.7 保护功能 \\n2.2.7.1 温度超限保护 \\n心脏脉冲电场消融仪应具有温度超限报警功能\\n并自动切断脉冲电场能量输出。；符合要求；2.2.7 保护功能 \\n2.2.7.1 温度超限保护 \\n心脏脉冲电场消融仪应具有温度超限报警功能\\n并自动切断脉冲电场能量输出。 符合要求 /；2.2.7.2 过流保护 \\n如果测量的脉冲电场输出电流高于“最大限\\n值”超过 50ms 时，则应生成错误提示。；2.2.7.2 过流保护 \\n如果测量的脉冲电场输出电流高于“最大限\\n值”超过 50ms 时，则应生成错误提示。 符合要求 /\\n上\\n海\\n市\\n医\\n疗\\n器\\n械\\n检\\n验\\n研\\n究\\n院 \\n检 验 报 告 \\n报告编号：国医检（设）字 QW2025 第 1539 号      样品编号：QW2025-1539       共 108 页 第 97 页 \\n \\n序\\n号 \\n检验 \\n项目 \\n标准 \\n条款 \\n标准要求 \\n检验结果 \\n单项 \\n结论 \\n备注 \\n156 医用电气\\n设备和医\\n用电气系\\n统中报警\\n系统的通\\n用要求、\\n试验和指\\n南 \\n208 \\n除以下内容外，YY 9706.108-2021 适用：  \\n修改：  \\n201.8.4.101 中描述的可听警报和红色警示灯\\n不应被认为是 YY9706.108-2021 中定义的报\\n警信号。 \\n符合要求 \\n符合 \\n/ \\n201.\n[truncated]", "text": null, "title": "PTR 条款 2.2.2 的参数 电流水平 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告序号 157 未稳定展开表格参数结果，需复核。"}

### Evidence finding:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pulse3:unbound
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"check_id\": \"PTR_TABLE\", \"finding_code\": \"PTR_ATOMIC_RESULT_UNBOUND\", \"finding_id\": \"99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pulse3:unbound\", \"severity\": \"warn\"}", "page_number": 4, "ref_id": "finding:99ff98c8-af45-4302-b934-7327bc6529c0:PTR_ATOMIC:2.2.2:2.2.2:current_level:pulse3:unbound", "section": "chapter_2", "source_type": "finding", "structured": "{\"actual\": null, \"check_id\": \"PTR_TABLE\", \"code\": \"PTR_ATOMIC_RESULT_UNBOUND\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"ptr-atomic-2.2.2:current_level:pulse3\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"2.2.2 心脏脉冲电场消融仪输出波形图和波形参数\\n心脏脉冲电场消融仪输出波形图和波形参数\\n心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满足表 6 的要求。\\n图 1 心脏脉冲电场消融仪 PULSE 3 预设输出波形图\\n表 6 波形参数\\n参数\\nPULSE 3 预设\\nPF Reversible 预设\\n脉冲个数\\n1500\\n1\\n脉冲组数\\n12\\n1\\n脉冲组间隔\\natomic=2.2.2:current_level:pulse3; expected=1-100%\", \"source_type\": \"ptr\", \"value\": null}, {\"confidence\": null, \"id\": \"report-atomic-2.2.2:current_level:pulse3\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 99, \"row_index\": null, \"section\": null, \"source_id\": null, \"source_type\": \"report\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"full_group_text:\\n157 心脏脉冲\\n电场消融\\n仪 2.2 2.2.1 心脏脉冲电场消融仪输出 \\n心脏脉冲电场消融仪应至少能够提供： \\n电压：3333V（峰值） \\n单位：V\\n𝑝 3375 符合 / 3375 157 心脏脉冲\\n电场消融\\n仪 2.2 2.2.1 心脏脉冲电场消融仪输出 \\n心脏脉冲电场消融仪应至少能够提供： \\n电压：3333V（峰值） \\n单位：V\\n𝑝 3375 符合 /\\n电流：57A（峰值） \\n单位：A\\n𝑝 59 / 电流：57A（峰值） \\n单位：A\\n𝑝 59 /\\n2.2.2 心脏脉冲电场消融仪输出波形图和波形参数 \\n心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满\\n足表 6 的要求。 \\n图 1 是心脏脉冲电场消融仪输出波形图。 /
[truncated]
