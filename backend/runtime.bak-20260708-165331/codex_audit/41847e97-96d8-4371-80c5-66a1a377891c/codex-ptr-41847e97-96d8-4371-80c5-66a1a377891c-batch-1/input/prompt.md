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

- package_id: codex-ptr-41847e97-96d8-4371-80c5-66a1a377891c-batch-1
- task_id: 41847e97-96d8-4371-80c5-66a1a377891c
- task_type: ptr_compare
- kind: ptr_parameter_review
- schema_version: evidence-package-v1

## Targets

### Target ptr_review:41847e97-96d8-4371-80c5-66a1a377891c:PTR_ATOMIC:2.2.6:2.2.6:max_energy:unbound
{"allowed_evidence_refs": ["finding:41847e97-96d8-4371-80c5-66a1a377891c:PTR_ATOMIC:2.2.6:2.2.6:max_energy:unbound", "rule_context:41847e97-96d8-4371-80c5-66a1a377891c:PTR_ATOMIC:2.2.6:2.2.6:max_energy:unbound", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.2.6", "report_inspection_group:157"], "check_id": "PTR_TABLE", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "finding_id": "41847e97-96d8-4371-80c5-66a1a377891c:PTR_ATOMIC:2.2.6:2.2.6:max_energy:unbound", "metadata": {"clause_number": "2.2.6", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "parameter_name": null, "severity": "warn", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_ATOMIC_RESULT_UNBOUND；check_id=PTR_TABLE；clause=2.2.6", "target_id": "ptr_review:41847e97-96d8-4371-80c5-66a1a377891c:PTR_ATOMIC:2.2.6:2.2.6:max_energy:unbound", "target_type": "ptr_parameter", "title": "PTR 条款 2.2.6 的参数 单个脉冲最大输出能量 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告结果未能稳定抽取，需复核。"}

## Evidence Items

### Evidence finding:41847e97-96d8-4371-80c5-66a1a377891c:PTR_ATOMIC:2.2.6:2.2.6:max_energy:unbound
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"check_id\": \"PTR_TABLE\", \"finding_code\": \"PTR_ATOMIC_RESULT_UNBOUND\", \"finding_id\": \"41847e97-96d8-4371-80c5-66a1a377891c:PTR_ATOMIC:2.2.6:2.2.6:max_energy:unbound\", \"severity\": \"warn\"}", "page_number": 4, "ref_id": "finding:41847e97-96d8-4371-80c5-66a1a377891c:PTR_ATOMIC:2.2.6:2.2.6:max_energy:unbound", "section": "chapter_2", "source_type": "finding", "structured": "{\"actual\": null, \"check_id\": \"PTR_TABLE\", \"code\": \"PTR_ATOMIC_RESULT_UNBOUND\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"ptr-atomic-2.2.6:max_energy\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"2.2.6 最大输出能量\\n最大输出能量\\n脉冲宽度\\n1 个脉冲\\n1 次脉冲\\n正峰值\\n脉冲宽度×5\\n负峰值\\n相间间隔\\n在 12 个脉冲串中共输送 1500 次脉冲。\\n脉冲串间存在时间延迟。\\n脉冲组间隔\\natomic=2.2.6:max_energy; expected=<258 mJ\", \"source_type\": \"ptr\", \"value\": null}, {\"confidence\": null, \"id\": \"report-atomic-2.2.6:max_energy\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 99, \"row_index\": null, \"section\": null, \"source_id\": null, \"source_type\": \"report\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"157；心脏脉冲\\n电场消融\\n仪；2.2；2.2.1 心脏脉冲电场消融仪输出 \\n心脏脉冲电场消融仪应至少能够提供： \\n电压：3333V（峰值） \\n单位：V\\n𝑝；3375；符合；/；157 心脏脉冲\\n电场消融\\n仪 2.2 2.2.1 心脏脉冲电场消融仪输出 \\n心脏脉冲电场消融仪应至少能够提供： \\n电压：3333V（峰值） \\n单位：V\\n𝑝 3375 符合 /；电流：57A（峰值） \\n单位：A\\n𝑝；59；电流：57A（峰值） \\n单位：A\\n𝑝 59 /；2.2.2 心脏脉冲电场消融仪输出波形图和波形参数 \\n心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满\\n足表 6 的要求。 \\n图 1 是心脏脉冲电场消融仪输出波形图。；2.2.2 心脏脉冲电场消融仪输出波形图和波形参数 \\n心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满\\n足表 6 的要求。 \\n图 1 是心脏脉冲电场消融仪输出波形图。 /；续\\n157；脉冲相\\n间隔；1μsec±20%；-13%～-8%；续\\n157 心脏脉冲\\n电场消融\\n仪 2.2 脉冲相\\n间隔 1μsec±20% -13%～-8% 符合 /；2.2.3 脉冲上升时间 \\n脉冲上升时间应不超过 700ns。 \\n单位：ns；430；PULSE3 预\\n设；2.2.3 脉冲上升时间 \\n脉冲上升时间应不超过 700ns。 \\n单位：ns 430 PULSE3 预\\n设；2.2.5 脉冲衰减 \\n稳定输出后（第一个脉冲组之后），每个脉冲\\n组开始时的电压相比前一组脉冲组结束时电压\\n衰减应在 10%内。；1%；续\\n157 心脏脉冲\\n电场消融\\n仪 2.2 2.2.5 脉冲衰减 \\n稳定输出后（第一个脉冲组之后），每个脉冲\\n组开始时的电压相比前一组脉冲组结束时电压\\n衰减应在 10%内。 1% 符合 /；2.2.6 最大输出能量 \\n单个脉冲最大输出能量应小于 258mJ。 \\n单位：mJ；159；2.2.6 最大输出能量 \\n单个脉冲最大输出能量应小于 258mJ。 \\n单位：mJ 159 /；2.2.7 保护功能 \\n2.2.7.1 温度超限保护 \\n心脏脉冲电场消融仪应具有温度超限报警功能\\n并自动切断脉冲电场能量输出。；符合要求；2.2.7 保护功能 \\n2.2.7.1 温度超限保护 \\n心脏脉冲电场消融仪应具有温度超限报警功能\\n并自动切断脉冲电场能量输出。 符合要求 /；2.2.7.2 过流保护 \\n如果测量的脉冲电场输出电流高于“最大限\\n值”超过 50ms 时，则应生成错误提示。；2.2.7.2 过流保护 \\n如果测量的脉冲电场输出电流高于“最大限\\n值”超过 50ms 时，则应生成错误提示。 符合要求 /\", \"source_type\": \"report\", \"value\": null}], \"expected\": \"<258 mJ\", \"id\": \"41847e97-96d8-4371-80c5-66a1a377891c:PTR_ATOMIC:2.2.6:2.2.6:max_energy:unbound\", \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"message\": \"PTR 条款 2.2.6 的参数 单个脉冲最大输出能量 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告结果未能稳定抽取，需复核。\", \"metadata\": {\"actual\": null, \"atomic_id\": \"2.2.6:max_energy\", \"atomic_label\": \"单个脉冲最大输出能量\", \"candidate_actuals\": [], \"clause_number\": \"2.2.6\", \"codex_required\": true, \"expected\": \"<258 mJ\", \"item_no\": \"157\", \"preset\": null, \"report_page\": 99, \"review_hint\": \"请在报告序号 157 的 page 101 行中查找最大输出能量 159 mJ。\"}, \"missing_evidence\": [], \"severity\": \"warn\", \"task_id\": \"41847e97-96d8-4371-80c5-66a1a377891c\"}", "text": null, "title": "PTR 条款 2.2.6 的参数 单个脉冲最大输出能量 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告结果未能稳定抽取，需复核。"}

### Evidence ptr_clause:ptr-2.2.6
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"clause_id\": \"ptr-2.2.6\", \"clause_number\": \"2.2.6\"}", "page_number": 4, "ref_id": "ptr_clause:ptr-2.2.6", "section": "2.2.6", "source_type": "ptr_clause", "structured": "{\"body_text\": \"最大输出能量\\n脉冲宽度\\n1 个脉冲\\n1 次脉冲\\n正峰值\\n脉冲宽度×5\\n负峰值\\n相间间隔\\n在 12 个脉冲串中共输送 1500 次脉冲。\\n脉冲串间存在时间延迟。\\n脉冲组间隔\", \"clause_id\": \"ptr-2.2.6\", \"number\": \"2.2.6\", \"scope_type\": \"requirement\", \"table_numbers\": [], \"taxonomy\": \"requirement\", \"title\": \"最大输出能量\"}", "text": "最大输出能量\n脉冲宽度\n1 个脉冲\n1 次脉冲\n正峰值\n脉冲宽度×5\n负峰值\n相间间隔\n在 12 个脉冲串中共输送 1500 次脉冲。\n脉冲串间存在时间延迟。\n脉冲组间隔", "title": "PTR clause 2.2.6"}

### Evidence report_inspection_group:157
{"file_path": null, "location": null, "metadata": "{\"item_no\": \"157\", \"source\": \"report_inspection_table\"}", "page_number": 99, "ref_id": "report_inspection_group:157", "section": "inspection_item_group", "source_type": "table", "structured": "{\"inspection_item_group\": {\"compact_rows\": [{\"item_name\": \"心脏脉冲\\n电场消融\\n仪\", \"page_number\": 99, \"remark\": \"/\", \"row_index\": 3, \"sequence_raw\": \"157\", \"single_conclusion\": \"符合\", \"standard_clause\": \"2.2\", \"standard_requirement\": \"2.2.1 心脏脉冲电场消融仪输出 \\n心脏脉冲电场消融仪应至少能够提供： \\n电压：3333V（峰值） \\n单位：V\\n𝑝\", \"test_result\": \"3375\"}, {\"item_name\": \"59\", \"page_number\": 99, \"remark\": \"\", \"row_index\": 4, \"sequence_raw\": \"电流：57A（峰值） \\n单位：A\\n𝑝\", \"single_conclusion\": \"\", \"standard_clause\": \"/\", \"standard_requirement\": \"\", \"test_result\": \"\"}, {\"item_name\": \"/\", \"page_number\": 99, \"remark\": \"\", \"row_index\": 5, \"sequence_raw\": \"2.2.2 心脏脉冲电场消融仪输出波形图和波形参数 \\n心脏脉冲电场消融仪的输出波形图见图 1，波形参数应满\\n足表 6 的要求。 \\n图 1 是心脏脉冲电场消融仪输出波形图。\", \"single_conclusion\": \"\", \"standard_clause\": \"\", \"standard_requirement\": \"\", \"test_result\": \"\"}, {\"item_name\": \"心脏脉冲\\n电场消融\\n仪\", \"page_number\": 100, \"remark\": \"符合\", \"row_index\": 1, \"sequence_raw\": \"续\\n157\", \"single_conclusion\": \"-13%～-8%\", \"standard_clause\": \"2.2\", \"standard_requirement\": \"脉冲相\\n间隔\", \"test_result\": \"1μsec±20%\"}, {\"item_name\": \"430\", \"page_number\": 100, \"remark\": \"\", \"row_index\": 15, \"sequence_raw\": \"2.2.3 脉冲上升时间 \\n脉冲上升时间应不超过 700ns。 \\n单位：ns\", \"single_conclusion\": \"\", \"standard_clause\": \"PULSE3 预\\n设\", \"standard_requirement\": \"\", \"test_result\": \"\"}, {\"item_name\": \"心脏脉冲\\n电场消融\\n仪\", \"page_number\": 101, \"remark\": \"/\", \"row_index\": 1, \"sequence_raw\": \"续\\n157\", \"single_conclusion\": \"符合\", \"standard_clause\": \"2.2\", \"standard_requirement\": \"2.2.5 脉冲衰减 \\n稳定输出后（第一个脉冲组之后），每个脉冲\\n组开始时的电压相比前一组脉冲组结束时电压\\n衰减应在 10%内。\", \"test_result\": \"1%\"}, {\"item_name\": \"159\", \"page_number\": 101, \"remark\": \"\", \"row_index\": 2, \"sequence_raw\": \"2.2.6 最大输出能量 \\n单个脉冲最大输出能量应小于 258mJ。 \\n单位：mJ\", \"single_conclusion\": \"\", \"standard_clause\": \"/\", \"standard_requirement\": \"\", \"test_result\": \"\"}, {\"item_name\": \"符合要求\", \"page_number\": 101, \"remark\": \"\", \"row_index\": 3, \"sequence_raw\": \"2.2.7 保护功能 \\n2.2.7.1 温度超限保护 \\n心脏脉冲电场消融仪应具有温度超限报警功能\\n并自动切断脉冲电场能量输出。\", \"single_conclusion\": \"\", \"standard_clause\": \"/\", \"standard_requirement\": \"\", \"test_result\": \"\"}, {\"item_name\": \"符合要求\", \"page_number\": 101, \"remark\": \"\", \"row_index\": 4, \"sequence_raw\": \"2.2.7.2 过流保护 \\n如果测量的脉冲电场输出电流高于“最大限\\n值”超过 50ms 时，则应生成错误提示。\", \"single_conclusion\": \"\", \"standard_clause\": \"/\", \"standard_requirement\": \"\", \"test_result\": \"\"}], \"diagnostics\": [{\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"2.2.7 保护功能 \\n2.2.7.1 温度超限保护 \\n心脏脉冲电场消融仪应具有温度超限报警功能\\n并自动切断脉冲电场能量输出。\", \"source_index\": 1057, \"source_page\": 101, \"source_row_index\": 3, \"source_text_excerpt\": \"2.2.7 保护功能 \\n2.2.7.1 温度超限保护 \\n心脏脉冲电场消融仪应具有温度超限报警功能\\n并自动切断脉冲电场能量输出。 符合要求 /\", \"standard_clause\": \"/\"}, {\"code\": \"RESULT_TOKEN_RECOVERY_UNCERTAIN\", \"confidence\": \"uncertain\", \"possible_result_tokens\": [\"符合要求\", \"符合\"], \"recovery_method\": \"row_text_ambiguous_result\", \"sequence_raw\": \"2.2.7.2 过流保护 \\n如果测量的脉冲电场输出电流高于“最大限\\n值”超过 50ms 时，则应生成错误提示。\", \"source_index\": 1058, \"source_page\": 101, \"source_row_index\": 4, \"source_text_excerpt\": \"2.2.7.2 过流保护 \\n如果测量的脉冲电场输出电流高于“最大限\\n值”超过 50ms 时，则应生成错误提示。 符合要求 /\", \"standard_clause\": \"/\"}, {\"code\": \"CONFLICTING_EFFECTIVE_CONCLUSION\", \"item_no\": \"157\", \"values\": [\"符合\", \"-13%～-8%\", \"符合\"]}], \"display_item_no\": \"157\", \"group_row_count\": 9, \"item_no\": \"157\", \"pages\": [99, 100, 101], \"report_atomic_results\": [{\"actual\": \"3375\", \"atomic_id\": \"2.2.1:voltage\", \"candidate_actuals\": [], \"clause_id\": \"2.2.1\", \"confidence\": \"high\", \"diagnostics\": [{\"confidence\": \"high\", \"method\": \"row_text_voltage\", \"source_text_excerpt\": \"157 心脏脉冲 电场消融 仪 2.2 2.2.1 心脏脉冲电场消融仪输出 心脏脉冲电场消融仪应至少能够提供： 电压：3333V（峰值） 单位：V 𝑝 3375 符合 / 157 心脏脉冲 电场消融 仪 2.2 2.2.1 心脏脉冲电场消融仪输出 心脏脉冲电场消融仪应至少能够提供： 电压：3333V（峰值） 单位：V 𝑝 3375 符合 /\"}], \"label\": \"电压\", \"preset\": null, \"report_item_no\": \"157\", \"report_page\": 99, \"source_text\": \"157 心脏脉冲 电场消融 仪 2.2 2.2.1 心脏脉冲电场消融仪输出 心脏脉冲电场消融仪应至少能够提供： 电压：3333V（峰值） 单位：V 𝑝 3375 符合 / 157 心脏脉冲 电场消融 仪 2.2 2.2.1 心脏脉冲电场消融仪输出 心脏脉冲电场消融仪应至少能够提供： 电压：\n[truncated]", "text": null, "title": "Report inspection item group 157"}

### Evidence report_scope:declaration
{"file_path": null, "location": null, "metadata": "{\"field_name\": \"检验项目\", \"source\": \"report_homepage\"}", "page_number": 3, "ref_id": "report_scope:declaration", "section": "report_scope", "source_type": "report_field", "structured": "{\"declared_scope_items\": [\"2.2\", \"2.5\", \"2.6\"], \"declared_scope_ranges\": [], \"excluded_topics\": [\"生物相容性\", \"电磁兼容性\"], \"ptr_direct_content_starts_after\": \"156\", \"source_page\": 3, \"source_text\": \"2.2、 2.5、2.6 （除生物相容性、电磁兼容性）\"}", "text": "2.2、 2.5、2.6 （除生物相容性、电磁兼容性）", "title": "Report homepage inspection scope declaration"}

### Evidence report_scope:external_standard_ranges
{"file_path": null, "location": null, "metadata": "{\"source\": \"report_model_spec_or_notes\"}", "page_number": null, "ref_id": "report_scope:external_standard_ranges", "section": "external_standard_ranges", "source_type": "metadata", "structured": "{\"external_standard_ranges\": [{\"end_item_no\": \"118\", \"item_count\": 118, \"passed_count\": 73, \"sample_items\": [{\"item_no\": \"1\", \"page\": 10, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"4.1\", \"standard_requirement\": \"除非另有规定，本部分的要求应适用于正常使\\n用和合理可预见的误用。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"2\", \"page\": 10, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"4.2\", \"standard_requirement\": \"4.2.2 风险管理的通用要求 \\n应执行符合 YY/T 0316 的风险管理过程。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"3\", \"page\": 10, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"4.3\", \"standard_requirement\": \"在风险分析中，除了与基本安全相关的性能\\n外，制造商还应识别 ME 设备或 ME 系统临床功\\n能的性能，这对于实现预期用途是必需的，或\\n者能够影响 ME 设备或 ME 系统的安全性。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"4\", \"page\": 11, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"4.4\", \"standard_requirement\": \"制造商应在风险管理文档中声明 ME 设备或 ME\\n系统的预期使用寿命。\", \"test_result\": \"符合要求\"}, {\"item_no\": \"5\", \"page\": 11, \"remark\": \"/\", \"single_conclusion\": \"/\", \"standard_clause\": \"4.5\", \"standard_requirement\": \"制造商提供科学数据或临床意见或比较研究来\\n证明应用替代的风险控制措施或替代的试验方\\n法所得到的剩余风险仍然是可接受的，且与应\\n用本部分的要求所得到的剩余风险可比，则风\\n险控制替代的措施或试验方法是可接受。\", \"test_result\": \"——\"}, {\"item_no\": \"6\", \"page\": 11, \"remark\": \"/\", \"single_conclusion\": \"/\", \"standard_clause\": \"4.6\", \"standard_requirement\": \"对于那些接触患者但在应用部分定义之外的部\\n分，风险管理过程应评估其是否需要符合应用\\n部分的要求。除非评估确定需要适用 BF 型应\\n用部分或 CF 型应用部分的要求，否则有关的\\n部分应适用 B 型应用部分的要求。\", \"test_result\": \"——\"}, {\"item_no\": \"7\", \"page\": 11, \"remark\": \"/\", \"single_conclusion\": \"符合\", \"standard_clause\": \"4.7\", \"standard_requirement\": \"ME 设备应被设计和制造成保持单一故障安\\n全，或通过 4.2 的应用，确定风险仍然可接\\n受。\", \"test_result\": \"符合要求\"}, {\"item_n
[truncated]
