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

- package_id: codex-report-ae5253f4-fe78-4a91-bb49-1c840f4cbeda-C04-batch-1
- task_id: ae5253f4-fe78-4a91-bb49-1c840f4cbeda
- task_type: report_check
- kind: report_rule_review
- schema_version: evidence-package-v1

## Targets

### Target report-codex-target-ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient
{"allowed_evidence_refs": ["finding:ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient", "rule_context:ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient", "sample_description:ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient", "label_caption:ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient", "label_ocr:ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient", "label_image:ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient", "page_text:ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient"], "check_id": "C04", "finding_code": "OCR_EVIDENCE_INSUFFICIENT", "finding_id": "ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient", "metadata": {"actual": "仅找到中文标签样张 caption，结构化 OCR 字段为空", "evidence_can_verify_label_content": true, "evidence_has_full_label_text": false, "evidence_has_label_image_crop": false, "evidence_has_matched_full_label_text": false, "evidence_has_matched_label_crop": false, "evidence_has_matched_label_image": true, "evidence_has_matched_label_image_crop": false, "evidence_has_matched_label_ocr": false, "evidence_has_matched_structured_label_fields": false, "evidence_has_matching_label_caption": true, "evidence_has_structured_label_fields": false, "evidence_has_visual_label_input": true, "evidence_incomplete": false, "expected": "可读取的中文标签字段 OCR 或视觉证据", "expected_codex_when_label_content_missing": null, "expected_codex_when_label_not_found_but_caption_exists": null, "expected_label_fields": {"batch_or_serial": "10562228", "component_id": "sample-row-6", "component_name": "EnSite X 电\n源电缆", "expiration_date": null, "model": "ENSITE-\nPWRCP-CH-01", "production_date": "2017-03-15", "serial_number": "10562228"}, "finding_code": "OCR_EVIDENCE_INSUFFICIENT", "finding_metadata": {"component_id": "sample-row-6", "component_key": "EnSite X 电\n源电缆|ENSITE-\nPWRCP-CH-01|10562228|2017-03-15", "label_caption_exists": true, "label_caption_text": "№21 EnSite X 电源电缆 中文标签样张", "label_id": "label-23", "label_key": "label-23", "matched_label_key": null, "matched_ocr_field_count": 0, "matching_strategy": "name", "needs_visual_review": true, "user_facing_status": "needs_review"}, "is_unused_component": false, "label_caption_candidate": {"caption_id": "caption-23", "caption_text": "№21 EnSite X 电源电缆 中文标签样张", "caption_type": "label", "component_id": "sample-row-6", "matched_component_ids": [], "metadata": {"is_chinese_label": true}, "page_number": 130, "subject_name": "EnSite X 电源电缆"}, "label_crop_ref": null, "label_crop_unavailable_reason": "caption_bbox_missing", "label_field_comparison": {"comparison_hint": "field_missing_in_matched_label", "field_name": null, "matched_label_key": null, "matched_label_value": null, "sample_value": null}, "label_image_ref": "items/ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient-label-page.png", "label_matching_diagnostics": [{"caption_id": "caption-23", "code": "MATCHING_LABEL_CAPTION_FOUND"}, {"code": "UNMATCHED_LABEL_OCR_CANDIDATES_PRESENT", "label_ids": ["label-19", "label-20", "label-21", "label-22", "label-24", "label-25", "label-26", "label-27", "label-28", "label-29", "label-30", "label-31", "label-32", "label-33", "label-34", "label-35", "label-36", "label-37", "label-38", "label-39", "label-40", "label-41", "label-42", "label-43", "label-44", "label-45", "label-46", "label-47", "label-48", "label-49", "label-50", "label-51", "label-52", "label-53", "label-54", "label-55", "label-56", "label-57"]}, {"code": "MATCHED_LABEL_CROP_UNAVAILABLE", "reason": "caption_bbox_missing"}], "label_page_image_ref": "items/ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient-label-page.png", "label_page_number": 130, "label_visual_input_ref": "items/ae5253f4-fe78-4a91-bb49-1c840f4cbeda-c04-sample-row-6-ocr-evidence-insufficient-label-page.png", "matched_label_caption": {"caption_id": "caption-23", "caption_text": "№21 EnSite X 电源电缆 中文标签样张", "caption_type": "label", "matched_component_ids": [], "metadata": {"is_chinese_label": true}, "page_number": 130, "subject_name": "EnSite X 电源电缆"}, "matched_label_caption_text": "№21 EnSite X 电源电缆 中文标签样张", "matched_label_field_confidence": null, "matched_label_fields": {}, "matched_label_id": "label-23", "matched_label_ocr_source": "explicit_label_id", "matched_label_ocr_text": null, "matched_label_page_text": "上\n海\n市\n医\n疗\n器\n械\n检\n验\n研\n究\n院\n检 验 报 告 照 片 页\n报告编号：国医检（设）字 QW2025 第 2797 号      样品编号：QW2025-2797       共 174 页 第 128 页\n照片和说明\n№21 EnSite X 电源电缆 中文标签样张\n№22 EnSite X 隔离变压器 正面", "matched_label_text": null, "matching_label_caption_candidates": [{"caption_id": "caption-23", "caption_text": "№21 EnSite X 电源电缆 中文标签样张", "caption_type": "label", "component_id": "sample-row-6", "matched_component_ids": [], "metadata": {"is_chinese_label": true}, "page_number": 130, "subject_name": "EnSite X 电源电缆"}], "matching_label_ocr_candidates": [{"caption_id": "caption-23", "caption_text": "№21 EnSite X 电源电缆 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-23", "label_image_ref": null, "label_page_image_ref": "report-page:130", "page_number": 130}], "page_number": 4, "rule_id": "C04", "sample_description_row": {"actual": "仅找到中文标签样张 caption，结构化 OCR 字段为空", "batch_or_serial": "10562228", "component_id": "sample-row-6", "component_name": "EnSite X 电\n源电缆", "expected": "可读取的中文标签字段 OCR 或视觉证据", "expiration_date": null, "finding_metadata": {"component_id": "sample-row-6", "component_key": "EnSite X 电\n源电缆|ENSITE-\nPWRCP-CH-01|10562228|2017-03-15", "label_caption_exists": true, "label_caption_text": "№21 EnSite X 电源电缆 中文标签样张", "label_id": "label-23", "label_key": "label-23", "matched_label_key": null, "matched_ocr_field_count": 0, "matching_strategy": "name", "needs_visual_review": true, "user_facing_status": "needs_review"}, "identity_key": "EnSite X 电\n源电缆|ENSITE-\nPWRCP-CH-01|10562228|2017-03-15", "is_unused_component": false, "model": "ENSITE-\nPWRCP-CH-01", "production_date": "2017-03-15", "remark": "/", "unused_reason": null}, "severity": "warn", "source": "report_codex_evidence_builder", "unmatched_label_ocr_candidates": [{"caption_id": "caption-9", "caption_text": "№7 EnSite X 放大器 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-19", "label_image_ref": null, "label_page_image_ref": "report-page:123", "page_number": 123}, {"caption_id": "caption-12", "caption_text": "№10 EnSite X 放大器外部电源 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-20", "label_image_ref": null, "label_page_image_ref": "report-page:124", "page_number": 124}, {"caption_id": "caption-18", "caption_text": "№16 EnSite X 放大器推车 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-21", "label_image_ref": null, "label_page_image_ref": "report-page:127", "page_number": 127}, {"caption_id": "caption-21", "caption_text": "№19 EnSite X 配件包 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-22", "label_image_ref": null, "label_page_image_ref": "report-page:129", "page_number": 129}, {"caption_id": "caption-29", "caption_text": "№27 EnSite X 隔离变压器 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-24", "label_image_ref": null, "label_page_image_ref": "report-page:133", "page_number": 133}, {"caption_id": "caption-32", "caption_text": "№30 EnSite X 非磁导管 80 针连接器 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-25", "label_image_ref": null, "label_page_image_ref": "report-page:134", "page_number": 134}, {"caption_id": "caption-35", "caption_text": "№33 EnSite X 非磁导管 20 针连接器 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-26", "label_image_ref": null, "label_page_image_ref": "report-page:136", "page_number": 136}, {"caption_id": "caption-37", "caption_text": "№35 EnSite X 不可透射线 ECG 导联线 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-27", "label_image_ref": null, "label_page_image_ref": "report-page:137", "page_number": 137}, {"caption_id": "caption-40", "caption_text": "№38 EnSite X Surface Link 连接器 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-28", "label_image_ref": null, "label_page_image_ref": "report-page:138", "page_number": 138}, {"caption_id": "caption-46", "caption_text": "№44 演示工作站 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-29", "label_image_ref": null, "label_page_image_ref": "report-page:141", "page_number": 141}, {"caption_id": "caption-52", "caption_text": "№50 EnSite X 演示工作站推车 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-30", "label_image_ref": null, "label_page_image_ref": "report-page:144", "page_number": 144}, {"caption_id": "caption-55", "caption_text": "№53 EnSite X 显示器支架 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-31", "label_image_ref": null, "label_page_image_ref": "report-page:146", "page_number": 146}, {"caption_id": "caption-57", "caption_text": "№55 EnSite X 单显示器底座 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-32", "label_image_ref": null, "label_page_image_ref": "report-page:147", "page_number": 147}, {"caption_id": "caption-59", "caption_text": "№57 EnSite X 显示器 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-33", "label_image_ref": null, "label_page_image_ref": "report-page:148", "page_number": 148}, {"caption_id": "caption-62", "caption_text": "№60 EnSite X 磁场发生器 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-34", "label_image_ref": null, "label_page_image_ref": "report-page:149", "page_number": 149}, {"caption_id": "caption-63", "caption_text": "№61 固定式磁场发生器支架 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-35", "label_image_ref": null, "label_page_image_ref": "report-page:150", "page_number": 150}, {"caption_id": "caption-65", "caption_text": "№63 磁场发生器连接电缆 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-36", "label_image_ref": null, "label_page_image_ref": "report-page:151", "page_number": 151}, {"caption_id": "caption-67", "caption_text": "№65 可调式磁场发生器支架 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-37", "label_image_ref": null, "label_page_image_ref": "report-page:152", "page_number": 152}, {"caption_id": "caption-70", "caption_text": "№68 病床用支架 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-38", "label_image_ref": null, "label_page_image_ref": "report-page:153", "page_number": 153}, {"caption_id": "caption-72", "caption_text": "№70 病人参考背部传感器 (PRS3 头) 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-39", "label_image_ref": null, "label_page_image_ref": "report-page:154", "page_number": 154}, {"caption_id": "caption-74", "caption_text": "№72 病人参考正面传感器 (PRS1 头) 中文标签样张", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-40", "label_image_ref": null, "label_page_image_ref": "report-page:155", "page_number": 155}, {"caption_id": "caption-76", "caption_text": "№74  EnSite X 显示器 中文标签 2", "field_names": [], "has_full_text": false, "has_image_crop": false, "has_page_text": true, "has_structured_fields": false, "label_crop_ref": null, "label_id": "label-41", "label_image_ref": null, "label_page_image_ref": "report-page:156", "page_number": 156}, {"caption_id":
[truncated]
