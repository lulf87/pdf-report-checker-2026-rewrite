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

- package_id: codex-ptr-04652795-754a-4ea2-b0b0-fa0fb9a42a02-batch-4
- task_id: 04652795-754a-4ea2-b0b0-fa0fb9a42a02
- task_type: ptr_compare
- kind: ptr_parameter_review
- schema_version: evidence-package-v1

## Targets

### Target ptr_review:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信:unbound
{"allowed_evidence_refs": ["finding:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信:unbound", "rule_context:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信:unbound", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.6", "report_inspection_group:159"], "check_id": "PTR_TABLE", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "finding_id": "04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信:unbound", "metadata": {"atomic_id": "2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信", "clause_number": "2.6", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "parameter_name": null, "severity": "warn", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_ATOMIC_RESULT_UNBOUND；check_id=PTR_TABLE；clause=2.6", "target_id": "ptr_review:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信:unbound", "target_type": "ptr_parameter", "title": "PTR 条款 2.6 的参数 射频消融仪 - 与心脏脉冲电场消融仪、导管接口单元CIU、灌注泵、控制器、三维导航通信 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告序号 159 未稳定展开表格功能明细需复核。"}

### Target ptr_review:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---阻抗监测:unbound
{"allowed_evidence_refs": ["finding:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---阻抗监测:unbound", "rule_context:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---阻抗监测:unbound", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.6", "report_inspection_group:159"], "check_id": "PTR_TABLE", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "finding_id": "04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---阻抗监测:unbound", "metadata": {"atomic_id": "2.6:table6:心脏脉冲电场消融仪---阻抗监测", "clause_number": "2.6", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "parameter_name": null, "severity": "warn", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_ATOMIC_RESULT_UNBOUND；check_id=PTR_TABLE；clause=2.6", "target_id": "ptr_review:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---阻抗监测:unbound", "target_type": "ptr_parameter", "title": "PTR 条款 2.6 的参数 心脏脉冲电场消融仪 - 阻抗监测 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告序号 159 未稳定展开表格功能明细需复核。"}

### Target ptr_review:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---温度监测:unbound
{"allowed_evidence_refs": ["finding:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---温度监测:unbound", "rule_context:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---温度监测:unbound", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.6", "report_inspection_group:159"], "check_id": "PTR_TABLE", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "finding_id": "04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---温度监测:unbound", "metadata": {"atomic_id": "2.6:table6:心脏脉冲电场消融仪---温度监测", "clause_number": "2.6", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "parameter_name": null, "severity": "warn", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_ATOMIC_RESULT_UNBOUND；check_id=PTR_TABLE；clause=2.6", "target_id": "ptr_review:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---温度监测:unbound", "target_type": "ptr_parameter", "title": "PTR 条款 2.6 的参数 心脏脉冲电场消融仪 - 温度监测 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告序号 159 未稳定展开表格功能明细需复核。"}

### Target ptr_review:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信:unbound
{"allowed_evidence_refs": ["finding:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信:unbound", "rule_context:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信:unbound", "report_scope:declaration", "report_scope:external_standard_ranges", "report_scope:inspection_items", "ptr_clause:ptr-2.6", "report_inspection_group:159"], "check_id": "PTR_TABLE", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "finding_id": "04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信:unbound", "metadata": {"atomic_id": "2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信", "clause_number": "2.6", "finding_code": "PTR_ATOMIC_RESULT_UNBOUND", "parameter_name": null, "severity": "warn", "source": "ptr_compare_usecase", "table_number": null}, "summary": "规则初判 PTR_ATOMIC_RESULT_UNBOUND；check_id=PTR_TABLE；clause=2.6", "target_id": "ptr_review:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信:unbound", "target_type": "ptr_parameter", "title": "PTR 条款 2.6 的参数 心脏脉冲电场消融仪 - 与射频消融仪、导管接口单元CIU通信 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告序号 159 未稳定展开表格功能明细需复核。"}

## Evidence Items

### Evidence finding:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信:unbound
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 6, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"check_id\": \"PTR_TABLE\", \"finding_code\": \"PTR_ATOMIC_RESULT_UNBOUND\", \"finding_id\": \"04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信:unbound\", \"severity\": \"warn\"}", "page_number": 6, "ref_id": "finding:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信:unbound", "section": "chapter_2", "source_type": "finding", "structured": "{\"actual\": null, \"check_id\": \"PTR_TABLE\", \"code\": \"PTR_ATOMIC_RESULT_UNBOUND\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"ptr-atomic-2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 6, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"2.6 软件功能\\n软件功能\\n射频脉冲电场消融系统软件应具备以下功能：\\n表 6 软件功能\\n组件\\n功能\\n射频消融仪\\n\\n功率监测\\n\\n阻抗监测\\n\\n温度监测\\n\\n控制射频消融或脉冲电场消融应用的启动和停止\\n\\n灌注泵流量监测\\n\\n射频消融或脉冲电场消融模式选择\\n\\n接触质量监测\\n\\n与脉冲电场消融仪、导管接口单元CIU、灌注泵、控制器和\\n电生理三维导航系统通信\\n\\n参数显示与控制，包括阻抗、流量、功率、时间、能量、\\n温度和电流水平\\n\\n显示能量输送状态\\n\\n显示消融图\\n\\n预设选择\\n心脏脉冲电场消融仪\\n\\n阻抗监测\\n\\n温度监测\\n\\n与射频消融仪、导管接口单元CIU通信\\n控制器\\n\\n参数显示与控制，包括阻抗、流量、功率、时间、能量、\\n温度和电流水平\\n\\n显示能量输送状态\\n\\n显示消融图\\n\\n预设选择\\n脚踏开关\\n\\n允许用户启用双击以切换消融预设的开关\\n\\n开始和停止能量输送\\n灌注泵\\n\\n气泡检测\\n\\n显示和控制流量\\n\\n声音提示、视觉提示和信息应能显示在触摸屏面板上\\n\\n警告管路中有空气、泵头门打开或其他操作\\natomic=2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信; expected=要求=具备\", \"source_type\": \"ptr\", \"value\": null}, {\"confidence\": null, \"id\": \"report-atomic-2.6:table6:射频消融仪---与心脏脉冲电场消融仪-导管接口单元CIU-灌注泵-控制器-三维导航通信\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 101, \"row_index\": null, \"section\": null, \"source_id\": null, \"source_type\": \"report\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"full_group_text:\\n159 软件功能 2.6 射频脉冲电场消融系统软件应具备以下功能： \\n表 6 软件功能 符合 / 符合 159 软件功能 2.6 射频脉冲电场消融系统软件应具备以下功能： \\n表 6 软件功能 符合 /\\n续\\n159 软件功能 2.6 射频消\\n融仪 控制射频消融或脉冲电场消融应用\\n的启动和停止 —— 符合 控制射频消融或脉冲电场消融应用\\n的启动和停止 续\\n159 软件功能 2.6 射频消\\n融仪 控制射频消融或脉冲电场消融应用\\n的启动和停止 —— 符合 /\\n射频消融或脉冲电场消融模式选择 —— 射频消融或脉冲电场消融模式选择 ——\\n与脉冲电场消融仪、导管接口单元\\nCIU、灌注泵、控制器和电生理三维\\n导航系统通信 —— 与脉冲电场消融仪、导管接口单元\\nCIU、灌注泵、控制器和电生理三维\\n导航系统通信 ——\\n参数显示与控制，包括阻抗、流\\n量、功率、时间、能量、温度和电\\n流水平 —— 参数显示与控制，包括阻抗、流\\n量、功率、时间、能量、温度和电\\n流水平 ——\\n与射频消融仪、导管接口单元 CIU\\n通信 符合要求 与射频消融仪、导管接口单元 CIU\\n通信 符合要求\\n声音提示、视觉提示和信息应能显\\n示在触摸屏面板上 —— 声音提示、视觉提示和信息应能显\\n示在触摸屏面板上 ——\\n警告管路中有空气、泵头门打开或\\n其他操作 —— 警告管路中有空气、泵头门打开或\\n其他操作 ——\\n159；软件功能；2.6；射频脉冲电场消融系统软件应具备以下功能： \\n表 6 软件功能；符合；/；159 软件功能 2.6 射频脉冲电场消融系统软件应具备以下功能： \\n表 6 软件功能 符合 /；续\\n159；射频消\\n融仪；控制射频消融或脉冲电场消融应用\\n的启动和停止；——；续\\n159 软件功能 2.6 射频消\\n融仪 控制射频消融或脉冲电场消融应用\\n的启动和停止 —— 符合 /；射频消融或脉冲电场消融模式选择；射频消融或脉冲电场消融模式选择 ——；与脉冲电场消融仪、导管接口单元\\nCIU、灌注泵、控制器和电生理三维\\n导航系统通信；与脉冲电场消融仪、导管接口单元\\nCIU、灌注泵、控制器和电生理三维\\n导航系统通信 ——；参数显示与控制，包括阻抗、流\\n量、功率、时间、能量、温度和电\\n流水平；参数显示与控制，包括阻抗、流\\n量、功率、时间、能量、温度和电\\n流水平 ——；与射频消融仪、导管接口单元 CIU\\n通信；符合要求；与射频消融仪、导管接口单元 CIU\\n通信 符合要求；声音提示、视觉提示和信息应能显\\n示在触摸屏面板上；声音提示、视觉提示和信息应能显\\n示在触摸屏面板上 ——；警告管路中有空气、泵头门打开或\\n其他操作；警告管路中有空气、泵头门打开或\\n其他操作 ——\\n上\\n海\\n市\\n医\\n疗\\n器\\n械\\n检\\n验\\n研\\n究\\n院 \\n检 验 报 告 \\n报告编号：国医检（设）字 QW2025 第 1539 号      样品编号：QW2025-1539       共 108 页 第 99 页 \\n \\n序\\n号 \\n检验 \\n项目 \\n标准 \\n条款 \\n标准要求 \\n检验结果 \\n单项 \\n结论 \\n备注 \\n续\\n157 \\n心脏脉冲\\n电场消融\\n仪 \\n2.2 \\n2.2.5 脉冲衰减 \\n稳定输出后（第一个脉冲组之后），每个脉冲\\n组开始时的电压相比前一组脉冲组结束时电压\\n衰减应在 10%内。 \\n1% \\n符合 \\n/ \\n2.2.6 最大输出能量 \\n单个脉冲最大输出能量应小于 258mJ。 \\n单位：mJ \\n159 \\n/ \\n2.2.7 保护功能 \\n2.2.7.1 温度超限保护 \\n心脏脉冲电场消融仪应具有温度超限报警功能\\n并自动切断脉冲电场能量输出。 \\n符合要求 \\n/ \\n2.2.7.2 过流保护 \\n如果测量的脉冲电场输出电流高于“最大限\\n值”超过 50ms 时，则应生成错误提示。 \\n符合要求 \\n/ \\n158 电气安全 2.5 \\n2.5.1 射频消融仪 \\n2.5.1.1 射频消融仪的电气安全应符合\\nGB9706.1-2020 和 GB9706.202-2021 的要求。 \\n—— \\n符合 \\n/ \\n2.5.1.2 射频消融仪的电磁兼容性能应符合\\nYY9706.102-2021 及 GB9706.202-2021 第 202\\n条的要求。 \\n/ \\n2.5.2 心脏脉冲电场消融仪 \\n2.5.2.1 心脏脉冲电场消融仪的电气安全应符\\n合 GB9706.1-2020 \\n见序号 1～\\n序号 118 \\n和 GB9706.202-2021 的要求。 \\n见序号\\n119～序号\\n156 \\n2.5.2.2 心脏脉冲电场消融仪的电磁兼容性能\\n应符合 YY9706.102-2021 及 GB9706.202-2021\\n第 202 条的要求。 \\n/ \\n2.5.3 灌注泵 \\n2.5.3.1 灌注泵的电气安全应符合 GB9706.1-\\n2020 的要求。 \\n—— \\n2.5.3.2 灌注泵的电磁兼容性能应符合\\nYY9706.102-2021 的要求。 \\n/ \\n159 软件功能 2.6 \\n射频脉冲电场消融系统软件应具备以下功能： \\n表 6 软件功能 \\n符合 \\n/ \\n组件 \\n功能 \\n \\n射频消\\n融仪 \\n功率监测 \\n—— \\n阻抗监测 \\n—— \\n温度监测 \\n——\\n序\\n号 检验 \\n项目 标准 \\n条款 标准要求 检验结果 单项 \\n结论 备注\\n续\\n157 心脏脉冲\\n电场消融\\n仪 2.2 2.2.5 脉冲衰减 \\n稳定输出后（第一个脉冲组之后），每个\n[truncated]", "text": null, "title": "PTR 条款 2.6 的参数 射频消融仪 - 与心脏脉冲电场消融仪、导管接口单元CIU、灌注泵、控制器、三维导航通信 未完成报告结果结构化绑定，需要 Codex/人工复核完整检验项证据。报告序号 159 未稳定展开表格功能明细需复核。"}

### Evidence finding:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信:unbound
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 6, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}", "metadata": "{\"check_id\": \"PTR_TABLE\", \"finding_code\": \"PTR_ATOMIC_RESULT_UNBOUND\", \"finding_id\": \"04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信:unbound\", \"severity\": \"warn\"}", "page_number": 6, "ref_id": "finding:04652795-754a-4ea2-b0b0-fa0fb9a42a02:PTR_ATOMIC:2.6:2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信:unbound", "section": "chapter_2", "source_type": "finding", "structured": "{\"actual\": null, \"check_id\": \"PTR_TABLE\", \"code\": \"PTR_ATOMIC_RESULT_UNBOUND\", \"confidence\": \"medium\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": null, \"id\": \"ptr-atomic-2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 6, \"row_index\": null, \"section\": \"chapter_2\", \"source_id\": null, \"source_type\": \"ptr\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"2.6 软件功能\\n软件功能\\n射频脉冲电场消融系统软件应具备以下功能：\\n表 6 软件功能\\n组件\\n功能\\n射频消融仪\\n\\n功率监测\\n\\n阻抗监测\\n\\n温度监测\\n\\n控制射频消融或脉冲电场消融应用的启动和停止\\n\\n灌注泵流量监测\\n\\n射频消融或脉冲电场消融模式选择\\n\\n接触质量监测\\n\\n与脉冲电场消融仪、导管接口单元CIU、灌注泵、控制器和\\n电生理三维导航系统通信\\n\\n参数显示与控制，包括阻抗、流量、功率、时间、能量、\\n温度和电流水平\\n\\n显示能量输送状态\\n\\n显示消融图\\n\\n预设选择\\n心脏脉冲电场消融仪\\n\\n阻抗监测\\n\\n温度监测\\n\\n与射频消融仪、导管接口单元CIU通信\\n控制器\\n\\n参数显示与控制，包括阻抗、流量、功率、时间、能量、\\n温度和电流水平\\n\\n显示能量输送状态\\n\\n显示消融图\\n\\n预设选择\\n脚踏开关\\n\\n允许用户启用双击以切换消融预设的开关\\n\\n开始和停止能量输送\\n灌注泵\\n\\n气泡检测\\n\\n显示和控制流量\\n\\n声音提示、视觉提示和信息应能显示在触摸屏面板上\\n\\n警告管路中有空气、泵头门打开或其他操作\\natomic=2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信; expected=要求=具备\", \"source_type\": \"ptr\", \"value\": null}, {\"confidence\": null, \"id\": \"report-atomic-2.6:table6:心脏脉冲电场消融仪---与射频消融仪-导管接口单元CIU通信\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 101, \"row_index\": null, \"section\": null, \"source_id\": null, \"source_type\": \"report\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"pdf_text\", \"normalized_text\": null, \"raw_text\": \"full_group_text:\\n159 软件功能 2.6 射频脉冲电场消融系统软件应具备以下功能： \\n表 6 软件功能 符合 / 符合 159 软件功能 2.6 射频脉冲电场消融系统软件应具备以下功能： \\n表 6 软件功能 符合 /\\n续\\n159 软件功能 2.6 射频消\\n融仪 控制射频消融或脉冲电场消融应用\\n的启动和停止 —— 符合 控制射频消融或脉冲电场消融应用\\n的启动和停止 续\\n159 软件功能 2.6 射频消\\n融仪 控制射频消融或脉冲电场消融应用\\n的启动和停止 —— 符合 /\\n射频消融或脉冲电场消融模式选择 —— 射频消融或脉冲电场消融模式选择 ——\\n与脉冲电场消融仪、导管接口单元\\nCIU、灌注泵、控制器和电生理三维\\n导航系统通信 —— 与脉冲电场消融仪、导管接口单元\\nCIU、灌注泵、控制器和电生理三维\\n导航系统通信 ——\\n参数显示与控制，包括阻抗、流\\n量、功率、时间、能量、温度和电\\n流水平 —— 参数显示与控制，包括阻抗、流\\n量、功率、时间、能量、温度和电\\n流水平 ——\\n与射频消融仪、导管接口单元 CIU\\n通信 符合要求 与射频消融仪、导管接口单元 CIU\\n通信 符合要求\\n声音提示、视觉提示和信息应能显\\n示在触摸屏面板上 —— 声音提示、视觉提示和信息应能显\\n示在触摸屏面板上 ——\\n警告管路中有空气、泵头门打开或\\n其他操作 —— 警告管路中有空气、泵头门打开或\\n其他操作 ——\\n159；软件功能；2.6；射频脉冲电场消融系统软件应具备以下功能： \\n表 6 软件功能；符合；/；159 软件功能 2.6 射频脉冲电场消融系统软件应具备以下功能： \\n表 6 软件功能 符合 /；
[truncated]
