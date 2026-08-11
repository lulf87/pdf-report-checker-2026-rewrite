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

- package_id: codex-report-53bbeec9-998b-4868-9627-00d9cc3b7ab0-C06-batch-0
- task_id: 53bbeec9-998b-4868-9627-00d9cc3b7ab0
- task_type: report_check
- kind: report_rule_review
- schema_version: evidence-package-v1

## Targets

### Target report-codex-target-53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing
{"allowed_evidence_refs": ["finding:53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing", "rule_context:53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing", "component:53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing", "label_image:53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing", "page_text:53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing"], "check_id": "C06", "finding_code": "LABEL_COMPONENT_KEY_NOT_MATCHED", "finding_id": "53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing", "metadata": {"actual": "未匹配到中文标签", "evidence_can_verify_label_content": false, "evidence_has_full_label_text": false, "evidence_has_label_image_crop": false, "evidence_has_matched_full_label_text": false, "evidence_has_matched_label_image_crop": false, "evidence_has_matched_label_ocr": false, "evidence_has_matched_structured_label_fields": false, "evidence_has_matching_label_caption": true, "evidence_has_structured_label_fields": false, "evidence_incomplete": true, "expected": "至少一张中文标签", "expected_codex_when_label_content_missing": "uncertain", "expected_codex_when_label_not_found_but_caption_exists": null, "finding_code": "LABEL_COMPONENT_KEY_NOT_MATCHED", "finding_metadata": {"candidate_labels": [{"label_caption": "№5 心脏脉冲电场消融仪-主机 中文标签样张", "label_key": {"部件名称": "心脏脉冲电场消融仪-主机"}, "label_subject": "心脏脉冲电场消融仪-主机", "matched_label_key": "label-14", "ocr_confidence": "medium", "page_number": 109}, {"label_caption": "№8 心脏脉冲电场消融仪-触摸屏 中文标签样张", "label_key": {"部件名称": "心脏脉冲电场消融仪-触摸屏"}, "label_subject": "心脏脉冲电场消融仪-触摸屏", "matched_label_key": "label-15", "ocr_confidence": "medium", "page_number": 110}, {"label_caption": "№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张", "label_key": {"部件名称": "心脏脉冲电场消融仪-ECG主线缆"}, "label_subject": "心脏脉冲电场消融仪-ECG主线缆", "matched_label_key": "label-16", "ocr_confidence": "medium", "page_number": 111}, {"label_caption": "№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张", "label_key": {"部件名称": "心脏脉冲电场消融仪-不可透射线ECG导联线（可选）"}, "label_subject": "心脏脉冲电场消融仪-不可透射线ECG导联线（可选）", "matched_label_key": "label-17", "ocr_confidence": "medium", "page_number": 112}, {"label_caption": "№14 光纤（15m）（可选） 中文标签样张", "label_key": {"部件名称": "光纤（15m）（可选）"}, "label_subject": "光纤（15m）（可选）", "matched_label_key": "label-18", "ocr_confidence": "medium", "page_number": 113}, {"label_caption": "№16 光接收器（可选） 中文标签样张", "label_key": {"部件名称": "光接收器（可选）"}, "label_subject": "光接收器（可选）", "matched_label_key": "label-19", "ocr_confidence": "medium", "page_number": 114}, {"label_caption": "№18 电源电缆（可选） 中文标签样张", "label_key": {"部件名称": "电源电缆（可选）"}, "label_subject": "电源电缆（可选）", "matched_label_key": "label-20", "ocr_confidence": "medium", "page_number": 115}, {"label_caption": "№20 等电位线缆 （3m）（可选） 中文标签样张", "label_key": {"部件名称": "等电位线缆（3m）（可选）"}, "label_subject": "等电位线缆（3m）（可选）", "matched_label_key": "label-21", "ocr_confidence": "medium", "page_number": 116}, {"label_caption": "№22 触摸屏连接线缆（30m）（可选）  中文标签样张", "label_key": {"部件名称": "触摸屏连接线缆（30m）（可选）"}, "label_subject": "触摸屏连接线缆（30m）（可选）", "matched_label_key": "label-22", "ocr_confidence": "medium", "page_number": 117}, {"label_caption": "№24 心脏脉冲电场消融仪-触摸屏电源适配器（可选） 中文标签样张", "label_key": {"部件名称": "心脏脉冲电场消融仪-触摸屏电源适配器（可选）"}, "label_subject": "心脏脉冲电场消融仪-触摸屏电源适配器（可选）", "matched_label_key": "label-23", "ocr_confidence": "medium", "page_number": 118}, {"label_caption": "№26 脉冲导管连接电缆（可选） 中文标签样张", "label_key": {"部件名称": "脉冲导管连接电缆（可选）"}, "label_subject": "脉冲导管连接电缆（可选）", "matched_label_key": "label-24", "ocr_confidence": "medium", "page_number": 119}, {"label_caption": "№5 心脏脉冲电场消融仪-主机 中文标签样张", "label_key": {"部件名称": "心脏脉冲电场消融仪-主机"}, "label_subject": "心脏脉冲电场消融仪-主机", "matched_label_key": "caption:caption-7", "ocr_confidence": null, "page_number": 109}, {"label_caption": "№6 心脏脉冲电场消融仪-推车 中文标签样张", "label_key": {"部件名称": "心脏脉冲电场消融仪-推车"}, "label_subject": "心脏脉冲电场消融仪-推车", "matched_label_key": "caption:caption-8", "ocr_confidence": null, "page_number": 109}, {"label_caption": "№8 心脏脉冲电场消融仪-触摸屏 中文标签样张", "label_key": {"部件名称": "心脏脉冲电场消融仪-触摸屏"}, "label_subject": "心脏脉冲电场消融仪-触摸屏", "matched_label_key": "caption:caption-10", "ocr_confidence": null, "page_number": 110}, {"label_caption": "№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张", "label_key": {"部件名称": "心脏脉冲电场消融仪-ECG主线缆"}, "label_subject": "心脏脉冲电场消融仪-ECG主线缆", "matched_label_key": "caption:caption-12", "ocr_confidence": null, "page_number": 111}, {"label_caption": "№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张", "label_key": {"部件名称": "心脏脉冲电场消融仪-不可透射线ECG导联线（可选）"}, "label_subject": "心脏脉冲电场消融仪-不可透射线ECG导联线（可选）", "matched_label_key": "caption:caption-14", "ocr_confidence": null, "page_number": 112}, {"label_caption": "№14 光纤（15m）（可选） 中文标签样张", "label_key": {"部件名称": "光纤（15m）（可选）"}, "label_subject": "光纤（15m）（可选）", "matched_label_key": "caption:caption-16", "ocr_confidence": null, "page_number": 113}, {"label_caption": "№16 光接收器（可选） 中文标签样张", "label_key": {"部件名称": "光接收器（可选）"}, "label_subject": "光接收器（可选）", "matched_label_key": "caption:caption-18", "ocr_confidence": null, "page_number": 114}, {"label_caption": "№18 电源电缆（可选） 中文标签样张", "label_key": {"部件名称": "电源电缆（可选）"}, "label_subject": "电源电缆（可选）", "matched_label_key": "caption:caption-20", "ocr_confidence": null, "page_number": 115}, {"label_caption": "№20 等电位线缆 （3m）（可选） 中文标签样张", "label_key": {"部件名称": "等电位线缆（3m）（可选）"}, "label_subject": "等电位线缆（3m）（可选）", "matched_label_key": "caption:caption-22", "ocr_confidence": null, "page_number": 116}, {"label_caption": "№22 触摸屏连接线缆（30m）（可选）  中文标签样张", "label_key": {"部件名称": "触摸屏连接线缆（30m）（可选）"}, "label_subject": "触摸屏连接线缆（30m）（可选）", "matched_label_key": "caption:caption-24", "ocr_confidence": null, "page_number": 117}, {"label_caption": "№24 心脏脉冲电场消融仪-触摸屏电源适配器（可选） 中文标签样张", "label_key": {"部件名称": "心脏脉冲电场消融仪-触摸屏电源适配器（可选）"}, "label_subject": "心脏脉冲电场消融仪-触摸屏电源适配器（可选）", "matched_label_key": "caption:caption-26", "ocr_confidence": null, "page_number": 118}, {"label_caption": "№26 脉冲导管连接电缆（可选） 中文标签样张", "label_key": {"部件名称": "脉冲导管连接电缆（可选）"}, "label_subject": "脉冲导管连接电缆（可选）", "matched_label_key": "caption:caption-28", "ocr_confidence": null, "page_number": 119}], "component_id": "sample-row-14", "component_key": {"规格型号": "PFA-GEN-\nCBL30", "部件名称": "心脏脉冲电场消融仪-触\n摸屏连接线缆（30m）\n（可选）"}, "component_name": "心脏脉冲电场消融仪-触\n摸屏连接线缆（30m）\n（可选）", "is_unused_component": false, "matched_label_key": null, "matching_strategy": null}, "is_unused_component": false, "label_field_comparison": {"comparison_hint": "no_matched_label_ocr", "field_name": null, "matched_label_key": null, "matched_label_value": null, "sample_value": null}, "matched_label_caption": "№8 心脏脉冲电场消融仪-触摸屏 中文标签样张", "matched_label_fields": {}, "matched_label_id": null, "matched_label_text": null, "matching_label_caption_candidates": [{"caption_id": "caption-10", "caption_text": "№8 心脏脉冲电场消融仪-触摸屏 中文标签样张", "caption_type": "label", "component_id": "sample-row-14", "matched_component_ids": [], "metadata": {"is_chinese_label": true}, "page_number": 110, "subject_name": "心脏脉冲电场消融仪-触摸屏"}, {"caption_id": "caption-24", "caption_text": "№22 触摸屏连接线缆（30m）（可选）  中文标签样张", "caption_type": "label", "component_id": "sample-row-14", "matched_component_ids": [], "metadata": {"is_chinese_label": true}, "page_number": 117, "subject_name": "触摸屏连接线缆（30m）（可选）"}], "matching_label_ocr_candidates": [], "page_number": 4, "rule_id": "C06", "severity": "error", "source": "report_codex_evidence_builder", "unused_reason": null}, "summary": "样品描述部件「心脏脉冲电场消融仪-触\n摸屏连接线缆（30m）\n（可选）」存在中文标签候选，但非空字段联合键未匹配", "target_id": "report-codex-target-53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing", "target_type": "label_ocr", "title": "样品描述部件「心脏脉冲电场消融仪-触\n摸屏连接线缆（30m）\n（可选）」存在中文标签候选，但非空字段联合键未匹配"}

## Evidence Items

### Evidence component:53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}", "metadata": "{\"check_id\": \"C06\", \"component_id\": \"sample-row-14\", \"finding_id\": \"53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing\"}", "page_number": 4, "ref_id": "component:53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing", "section": "sample_component", "source_type": "report_field", "structured": "{\"actual\": \"未匹配到中文标签\", \"batch_or_serial\": \"/\", \"component_id\": \"sample-row-14\", \"component_name\": \"心脏脉冲电场消融仪-触\\n摸屏连接线缆（30m）\\n（可选）\", \"expected\": \"至少一张中文标签\", \"expiration_date\": null, \"finding_metadata\": {\"candidate_labels\": [{\"label_caption\": \"№5 心脏脉冲电场消融仪-主机 中文标签样张\", \"label_key\": {\"部件名称\": \"心脏脉冲电场消融仪-主机\"}, \"label_subject\": \"心脏脉冲电场消融仪-主机\", \"matched_label_key\": \"label-14\", \"ocr_confidence\": \"medium\", \"page_number\": 109}, {\"label_caption\": \"№8 心脏脉冲电场消融仪-触摸屏 中文标签样张\", \"label_key\": {\"部件名称\": \"心脏脉冲电场消融仪-触摸屏\"}, \"label_subject\": \"心脏脉冲电场消融仪-触摸屏\", \"matched_label_key\": \"label-15\", \"ocr_confidence\": \"medium\", \"page_number\": 110}, {\"label_caption\": \"№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张\", \"label_key\": {\"部件名称\": \"心脏脉冲电场消融仪-ECG主线缆\"}, \"label_subject\": \"心脏脉冲电场消融仪-ECG主线缆\", \"matched_label_key\": \"label-16\", \"ocr_confidence\": \"medium\", \"page_number\": 111}, {\"label_caption\": \"№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张\", \"label_key\": {\"部件名称\": \"心脏脉冲电场消融仪-不可透射线ECG导联线（可选）\"}, \"label_subject\": \"心脏脉冲电场消融仪-不可透射线ECG导联线（可选）\", \"matched_label_key\": \"label-17\", \"ocr_confidence\": \"medium\", \"page_number\": 112}, {\"label_caption\": \"№14 光纤（15m）（可选） 中文标签样张\", \"label_key\": {\"部件名称\": \"光纤（15m）（可选）\"}, \"label_subject\": \"光纤（15m）（可选）\", \"matched_label_key\": \"label-18\", \"ocr_confidence\": \"medium\", \"page_number\": 113}, {\"label_caption\": \"№16 光接收器（可选） 中文标签样张\", \"label_key\": {\"部件名称\": \"光接收器（可选）\"}, \"label_subject\": \"光接收器（可选）\", \"matched_label_key\": \"label-19\", \"ocr_confidence\": \"medium\", \"page_number\": 114}, {\"label_caption\": \"№18 电源电缆（可选） 中文标签样张\", \"label_key\": {\"部件名称\": \"电源电缆（可选）\"}, \"label_subject\": \"电源电缆（可选）\", \"matched_label_key\": \"label-20\", \"ocr_confidence\": \"medium\", \"page_number\": 115}, {\"label_caption\": \"№20 等电位线缆 （3m）（可选） 中文标签样张\", \"label_key\": {\"部件名称\": \"等电位线缆（3m）（可选）\"}, \"label_subject\": \"等电位线缆（3m）（可选）\", \"matched_label_key\": \"label-21\", \"ocr_confidence\": \"medium\", \"page_number\": 116}, {\"label_caption\": \"№22 触摸屏连接线缆（30m）（可选）  中文标签样张\", \"label_key\": {\"部件名称\": \"触摸屏连接线缆（30m）（可选）\"}, \"label_subject\": \"触摸屏连接线缆（30m）（可选）\", \"matched_label_key\": \"label-22\", \"ocr_confidence\": \"medium\", \"page_number\": 117}, {\"label_caption\": \"№24 心脏脉冲电场消融仪-触摸屏电源适配器（可选） 中文标签样张\", \"label_key\": {\"部件名称\": \"心脏脉冲电场消融仪-触摸屏电源适配器（可选）\"}, \"label_subject\": \"心脏脉冲电场消融仪-触摸屏电源适配器（可选）\", \"matched_label_key\": \"label-23\", \"ocr_confidence\": \"medium\", \"page_number\": 118}, {\"label_caption\": \"№26 脉冲导管连接电缆（可选） 中文标签样张\", \"label_key\": {\"部件名称\": \"脉冲导管连接电缆（可选）\"}, \"label_subject\": \"脉冲导管连接电缆（可选）\", \"matched_label_key\": \"label-24\", \"ocr_confidence\": \"medium\", \"page_number\": 119}, {\"label_caption\": \"№5 心脏脉冲电场消融仪-主机 中文标签样张\", \"label_key\": {\"部件名称\": \"心脏脉冲电场消融仪-主机\"}, \"label_subject\": \"心脏脉冲电场消融仪-主机\", \"matched_label_key\": \"caption:caption-7\", \"ocr_confidence\": null, \"page_number\": 109}, {\"label_caption\": \"№6 心脏脉冲电场消融仪-推车 中文标签样张\", \"label_key\": {\"部件名称\": \"心脏脉冲电场消融仪-推车\"}, \"label_subject\": \"心脏脉冲电场消融仪-推车\", \"matched_label_key\": \"caption:caption-8\", \"ocr_confidence\": null, \"page_number\": 109}, {\"label_caption\": \"№8 心脏脉冲电场消融仪-触摸屏 中文标签样张\", \"label_key\": {\"部件名称\": \"心脏脉冲电场消融仪-触摸屏\"}, \"label_subject\": \"心脏脉冲电场消融仪-触摸屏\", \"matched_label_key\": \"caption:caption-10\", \"ocr_confidence\": null, \"page_number\": 110}, {\"label_caption\": \"№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张\", \"label_key\": {\"部件名称\": \"心脏脉冲电场消融仪-ECG主线缆\"}, \"label_subject\": \"心脏脉冲电场消融仪-ECG主线缆\", \"matched_label_key\": \"caption:caption-12\", \"ocr_confidence\": null, \"page_number\": 111}, {\"label_caption\": \"№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张\", \"label_key\": {\"部件名称\": \"心脏脉冲电场消融仪-不可透射线ECG导联线（可选）\"}, \"label_subject\": \"心脏脉冲电场消融仪-不可透射线ECG导联线（可选）\", \"matched_label_key\": \"caption:caption-14\", \"ocr_confidence\": null, \"page_number\": 112}, {\"label_caption\": \"№14 光纤（15m）（可选） 中文标签样张\", \"label_key\": {\"部件名称\": \"光纤（15m）（可选）\"}, \"label_subject\": \"光纤（15m）（可选）\", \"matched_label_key\": \"caption:caption-16\", \"ocr_confidence\": null, \"page_number\": 113}, {\"label_caption\": \"№16 光接收器（可选） 中文标签样张\", \"label_key\": {\"部件名称\": \"光接收器（可选）\"}, \"label_subject\": \"光接收器（可选）\", \"matched_label_key\": \"caption:caption-18\", \"ocr_confidence\": null, \"page_number\": 114}, {\"label_caption\": \"№18 电源电缆\n[truncated]", "text": null, "title": "C06 样品部件 evidence"}

### Evidence finding:53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}", "metadata": "{\"check_id\": \"C06\", \"finding_code\": \"LABEL_COMPONENT_KEY_NOT_MATCHED\", \"finding_id\": \"53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing\", \"severity\": \"error\"}", "page_number": 4, "ref_id": "finding:53bbeec9-998b-4868-9627-00d9cc3b7ab0-c06-sample-row-14-label-missing", "section": null, "source_type": "finding", "structured": "{\"actual\": \"未匹配到中文标签\", \"check_id\": \"C06\", \"code\": \"LABEL_COMPONENT_KEY_NOT_MATCHED\", \"confidence\": \"high\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p4-t2:sample:r14:c1:component_name\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"部件名称\", \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}, \"metadata\": {\"column_index\": 1, \"field_name\": \"component_name\"}, \"method\": \"pdf_text\", \"normalized_text\": \"心脏脉冲电场消融仪-触摸屏连接线缆（30m）（可选）\", \"raw_text\": \"心脏脉冲电场消融仪-触\\n摸屏连接线缆（30m）\\n（可选）\", \"source_type\": \"report\", \"value\": \"心脏脉冲电场消融仪-触\\n摸屏连接线缆（30m）\\n（可选）\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p4-t2:sample:r14:c2:model\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"规格型号\", \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}, \"metadata\": {\"column_index\": 2, \"field_name\": \"model\"}, \"method\": \"pdf_text\", \"normalized_text\": \"PFA-GEN-CBL30\", \"raw_text\": \"PFA-GEN-\\nCBL30\", \"source_type\": \"report\", \"value\": \"PFA-GEN-\\nCBL30\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p4-t2:sample:r14:c3:batch_or_serial\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"序列号批号\", \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}, \"metadata\": {\"column_index\": 3, \"field_name\": \"batch_or_serial\"}, \"method\": \"pdf_text\", \"normalized_text\": \"/\", \"raw_text\": \"/\", \"source_type\": \"report\", \"value\": \"/\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p4-t2:sample:r14:c4:production_date\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"生产日期\", \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}, \"metadata\": {\"column_index\": 4, \"field_name\": \"production_date\"}, \"method\": \"pdf_text\", \"normalized_text\": \"/\", \"raw_text\": \"/\", \"source_type\": \"report\", \"value\": \"/\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p4-t2:sample:r14:c5:remark\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"备注\", \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}, \"metadata\": {\"column_index\": 5, \"field_name\": \"remark\"}, \"method\": \"pdf_text\", \"normalized_text\": \"/\", \"raw_text\": \"/\", \"source_type\": \"report\", \"value\": \"/\"}, {\"confidence\": \"medium\", \"id\": \"ev-label-label-14\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 109, \"row_index\": null, \"section\": null, \"source_id\": null, \"source_type\": \"report\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"ocr\", \"normalized_text\": null, \"raw_text\": \"№5 心脏脉冲电场消融仪-主机 中文标签样张\", \"source_type\": \"report\", \"value\": null}, {\"confidence\": \"medium\", \"id\": \"ev-label-label-15\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 110, \"row_index\": null, \"section\": null, \"source_id\": null, \"source_type\": \"report\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"ocr\", \"normalized_text\": null, \"raw_text\": \"№8 心脏脉冲电场消融仪-触摸屏 中文标签样张\", \"source_type\": \"report\", \"value\": null}, {\"confidence\": \"medium\", \"id\": \"ev-label-label-16\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 111, \"row_index\": null, \"section\": null, \"source_id\": null, \"source_type\": \"report\", \"table_id\": null, \"text_span\": null}, \"metadata\": {}, \"method\": \"ocr\", \"normali
[truncated]
