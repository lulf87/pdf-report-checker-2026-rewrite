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

## C07 Visual Review Instructions

- C07 deterministic finding 是 candidate，不是最终事实。
- 请同时使用 textual evidence 和 C07 visual images。
- page/table/item group/result column/conclusion column/remark column images 是当前检验项目的视觉证据。
- result column images 用于核对当前 item_no 的所有检验结果。
- conclusion column images 用于核对单项结论。
- remark column images 用于核对备注。
- 必须结合首页符号说明：“——”表示此项不适用；“/”表示此项空白。
- 需要视觉核对当前 item_no 的所有检验结果、单项结论、备注、跨页续表行，以及 result token 是否被结构化抽取遗漏。
- 如果图片能清楚反驳 all-placeholder 判断，应 refute。
- 对 CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN，如果视觉证据足以判断结论合理时应 refute。
- 不能仅因结构化抽取遗漏存在就 confirm/manual；应区分抽取遗漏本身与最终候选是否仍需复核。
- 续行中的“符合要求”若属于同一 item group，应作为有效检验结果。
- 如果同一 item group 内视觉可见“符合要求”或其他有效检验结果，且单项结论为“符合”，应 refute extraction-uncertain candidate。
- 只有图像无法稳定读取对应行/列，或无法确认 result token 属于该 item group，才 uncertain。
- 如果图片证据仍不清楚，或复杂矩阵表无法稳定判读，应 uncertain。
- complex_matrix_table=true 时，不按普通 C07 直接 confirm；证据不足则 uncertain 或 specialized matrix review。
- 不要求 Codex 弥补缺失证据，不臆测图片外的结果、结论或备注。

## C07 Complex Matrix Review Instructions

- 当 complex_matrix_table=true 或 c07_complex_matrix_evidence.review_mode=complex_matrix_specialized 时，使用 complex matrix review 口径。
- 先识别矩阵结构，再判断单项结论。
- 必须查看 full page images、matrix table crops、row/column header crops、result matrix crops、conclusion column crops、cross-page continuation crops。
- 需要识别漏电流 / 患者辅助电流项目，以及正常状态 / 单一故障状态。
- 需要识别 B/BF/CF 或应用部分相关列、测量值、限值、占位符、单项结论列。
- 需要判断续页行是否属于同一个 item 59 matrix。
- 先根据矩阵视觉证据定位行标题、列标题、条件列、结果矩阵主体、结论列和跨页续表，再裁决原 candidate。
- 如果视觉证据足以确认符合结论由矩阵结果支持，应 refute 原 complex-matrix candidate。
- 如果视觉证据显示矩阵结果与“符合”冲突，可以 confirm。
- 如果列映射、跨页续表或矩阵结果仍不清楚，应 uncertain。
- 不要因为 rule_context 写了 complex_matrix_table=true 就自动 uncertain；需要先尝试使用 matrix visual evidence。
- 不要按普通 C07 all-placeholder 逻辑直接 confirm/refute。
- 不要把 item 59 硬编码为 refute 或 passed；必须基于提供的矩阵图像和 structured_matrix_hints 审核。

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

- package_id: codex-report-708694d3-6252-4ea4-9fe5-264466bb407c-C07-batch-0
- task_id: 708694d3-6252-4ea4-9fe5-264466bb407c
- task_type: report_check
- kind: report_rule_review
- schema_version: evidence-package-v1

## Targets

### Target report-codex-target-708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain
{"allowed_evidence_refs": ["finding:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain", "rule_context:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain", "inspection_item:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain", "inspection_page_text:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain", "c07_visual_page:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p27", "c07_visual_table:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p27", "c07_visual_page:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p28", "c07_visual_table:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p28", "c07_visual_item_group:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p28", "c07_visual_result:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p28", "c07_visual_conclusion:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p28", "c07_visual_remark:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p28", "c07_visual_page:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p29", "c07_visual_table:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p29", "c07_visual_item_group:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p29", "c07_visual_result:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p29", "c07_visual_conclusion:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p29", "c07_visual_remark:708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain:p29"], "check_id": "C07", "finding_code": "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN", "finding_id": "708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain", "metadata": {"actual": "符合", "c07_visual_evidence": {"conclusion_column_crop_refs": ["items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-conclusion-p28.png", "items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-conclusion-p29.png"], "has_visual_input": true, "item_group_crop_refs": ["items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-item-group-p28.png", "items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-item-group-p29.png"], "missing_visual_evidence_reasons": ["field_bbox_missing", "row_bbox_missing"], "page_image_refs": ["items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-page-p27.png", "items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-page-p28.png", "items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-page-p29.png"], "remark_column_crop_refs": ["items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-remark-p28.png", "items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-remark-p29.png"], "result_column_crop_refs": ["items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-result-p28.png", "items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-result-p29.png"], "table_image_refs": ["items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-table-p27.png", "items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-table-p28.png", "items/708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain-c07-table-p29.png"], "visual_review_mode": "inspection_item_group"}, "complex_matrix_reason": null, "complex_matrix_table": false, "evidence_has_c07_visual_input": true, "evidence_incomplete": false, "expected": "/", "finding_code": "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN", "finding_metadata": {"actual_conclusion": "符合", "continuation_markers": [{"normalized_item_no": "46", "page_number": 28, "raw_text": "续\n46", "row_index": 1, "source_index": 127}, {"normalized_item_no": "46", "page_number": 29, "raw_text": "续\n46", "row_index": 1, "source_index": 138}], "decision_reason": "all_placeholders_or_blank", "display_item_no": "46", "effective_test_results": ["——", "——", "——"], "expected_conclusion": "/", "group_diagnostics": [{"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "7.3.4 熔断器，热断路器和过流释放器 \n仅使用工具才能触及的熔断器、可更换的热断\n路器和过流释放器，应在元器件的附近标识规\n格： \n——电压（V)和电流（A) \n——动作速度，尺寸和分断能力 \n或通过参考标记在随附文件中提供的资料。", "source_index": 129, "source_page": 28, "source_row_index": 3, "source_text_excerpt": "7.3.4 熔断器，热断路器和过流释放器 \n仅使用工具才能触及的熔断器、可更换的热断\n路器和过流释放器，应在元器件的附近标识规\n格： \n——电压（V)和电流（A) \n——动作速度，尺寸和分断能力 \n或通过参考标记在随附文件中提供的资料。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "7.3.5 保护接地端子 \n除非保护接地端子在符合 GB/T 17465.1 的器\n具输入插座中，保护接地端子应标记 GB/T \n5465.2 中 5019 的符号（参见附表 D.1，符号\n6）。", "source_index": 130, "source_page": 28, "source_row_index": 4, "source_text_excerpt": "7.3.5 保护接地端子 \n除非保护接地端子在符合 GB/T 17465.1 的器\n具输入插座中，保护接地端子应标记 GB/T \n5465.2 中 5019 的符号（参见附表 D.1，符号\n6）。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "标记在保护接地端子上或相邻处，不应贴在连\n接时需要拆除的部件上。在连接后其仍应可\n见。", "source_index": 131, "source_page": 28, "source_row_index": 5, "source_text_excerpt": "标记在保护接地端子上或相邻处，不应贴在连\n接时需要拆除的部件上。在连接后其仍应可\n见。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "若连接到三相电源的标记是必要的，应符合\nGB/T 4026 的要求。", "source_index": 136, "source_page": 28, "source_row_index": 10, "source_text_excerpt": "若连接到三相电源的标记是必要的，应符合\nGB/T 4026 的要求。 ——", "standard_clause": ""}], "item_no": "46", "needs_codex_review": true, "normalized_item_no": "46", "original_effective_test_results": ["——", "——", "——"], "pages": [27, 28, 29], "reasoning_basis": "all_placeholders_or_blank", "recovered_effective_test_results": ["——", "——", "——"], "recovered_result_tokens": [], "result_summary": {"conforming_or_non_empty_count": 0, "nonconforming_count": 0, "placeholder_count": 3, "total_count": 3}, "result_token_recovery_applied": false, "result_token_recovery_confidence": "uncertain", "result_token_recovery_diagnostics": [{"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "7.3.4 熔断器，热断路器和过流释放器 \n仅使用工具才能触及的熔断器、可更换的热断\n路器和过流释放器，应在元器件的附近标识规\n格： \n——电压（V)和电流（A) \n——动作速度，尺寸和分断能力 \n或通过参考标记在随附文件中提供的资料。", "source_index": 129, "source_page": 28, "source_row_index": 3, "source_text_excerpt": "7.3.4 熔断器，热断路器和过流释放器 \n仅使用工具才能触及的熔断器、可更换的热断\n路器和过流释放器，应在元器件的附近标识规\n格： \n——电压（V)和电流（A) \n——动作速度，尺寸和分断能力 \n或通过参考标记在随附文件中提供的资料。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "7.3.5 保护接地端子 \n除非保护接地端子在符合 GB/T 17465.1 的器\n具输入插座中，保护接地端子应标记 GB/T \n5465.2 中 5019 的符号（参见附表 D.1，符号\n6）。", "source_index": 130, "source_page": 28, "source_row_index": 4, "source_text_excerpt": "7.3.5 保护接地端子 \n除非保护接地端子在符合 GB/T 17465.1 的器\n具输入插座中，保护接地端子应标记 GB/T \n5465.2 中 5019 的符号（参见附表 D.1，符号\n6）。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合要求", "符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "标记在保护接地端子上或相邻处，不应贴在连\n接时需要拆除的部件上。在连接后其仍应可\n见。", "source_index": 131, "source_page": 28, "source_row_index": 5, "source_text_excerpt": "标记在保护接地端子上或相邻处，不应贴在连\n接时需要拆除的部件上。在连接后其仍应可\n见。 符合要求", "standard_clause": ""}, {"code": "RESULT_TOKEN_RECOVERY_UNCERTAIN", "confidence": "uncertain", "possible_result_tokens": ["符合"], "recovery_method": "row_text_ambiguous_result", "sequence_raw": "若连接到三相电源的标记是必要的，应符合\nGB/T 4026 的要求。", "source_index": 136, "source_page": 28, "source_row_index": 10, "source_text_excerpt": "若连接到三相电源的标记是必要的，应符合\nGB/T 4026 的要求。 ——", "standard_clause": ""}], "suppressed_physical_row_count": 17}, "page_number": 27, "rule_id": "C07", "severity": "warn", "source": "report_codex_evidence_builder"}, "summary": "序号 46 的结构化检验结果可能不完整，需结合原始表格或 Codex evidence 复核后再判断单项结论。", "target_id": "report-codex-target-708694d3-6252-4ea4-9fe5-264466bb407c-c07-46-result-token-recovery-uncertain", "target_type": "inspection_item", "title": "序号 46 的结构化检验结果可能不完整，需结合原始表格或 Codex evidence 复核后再判断单项结论。"}

### Target report-codex-target-708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review
{"allowed_evidence_refs": ["finding:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review", "rule_context:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review", "inspection_item:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review", "inspection_page_text:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review", "c07_visual_page:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p45", "c07_visual_table:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p45", "c07_visual_page:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p46", "c07_visual_table:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p46", "c07_visual_item_group:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p46", "c07_visual_result:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p46", "c07_visual_conclusion:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p46", "c07_visual_remark:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p46", "c07_visual_page:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p47", "c07_visual_table:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p47", "c07_visual_item_group:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p47", "c07_visual_result:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p47", "c07_visual_conclusion:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p47", "c07_visual_remark:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p47", "c07_visual_page:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p48", "c07_visual_table:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p48", "c07_visual_item_group:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p48", "c07_visual_result:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p48", "c07_visual_conclusion:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p48", "c07_visual_remark:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p48", "c07_complex_matrix_page:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p45", "c07_complex_matrix_table:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p45", "c07_complex_matrix_header:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p45", "c07_complex_matrix_page:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p46", "c07_complex_matrix_table:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-complex-matrix-review:p46", "c07_complex_matrix_header:708694d3-6252-4ea4-9fe5-264466bb407c-c07-59-comple
[truncated]
