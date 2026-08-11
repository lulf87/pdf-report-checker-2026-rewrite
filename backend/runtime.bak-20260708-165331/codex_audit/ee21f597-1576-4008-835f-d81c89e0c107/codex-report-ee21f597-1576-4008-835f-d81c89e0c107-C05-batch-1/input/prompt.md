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

- package_id: codex-report-ee21f597-1576-4008-835f-d81c89e0c107-C05-batch-1
- task_id: ee21f597-1576-4008-835f-d81c89e0c107
- task_type: report_check
- kind: report_rule_review
- schema_version: evidence-package-v1

## Targets

### Target report-codex-target-ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing
{"allowed_evidence_refs": ["finding:ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing", "rule_context:ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing", "component:ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing", "photo_caption:ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing", "page_text:ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing"], "check_id": "C05", "finding_code": "PHOTO_COVERAGE_MISSING", "finding_id": "ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing", "metadata": {"actual": "未匹配到照片", "evidence_incomplete": false, "expected": "至少一张照片", "finding_code": "PHOTO_COVERAGE_MISSING", "finding_metadata": {"candidate_captions": [{"caption_id": "caption-1", "caption_subject": ".101用于以地为基准的患者电路的符号", "caption_text": "图 201.101 用于以地为基准的患者电路的符号", "is_uncertain": false, "ocr_confidence": null, "page_number": 86, "uncertainty_reason": null}, {"caption_id": "caption-2", "caption_subject": ".102用于高频绝缘的患者电路的符号", "caption_text": "图 201.102 用于高频绝缘的患者电路的符号", "is_uncertain": false, "ocr_confidence": null, "page_number": 86, "uncertainty_reason": null}, {"caption_id": "caption-3", "caption_subject": "心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车", "caption_text": "№1 心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车 正面", "is_uncertain": false, "ocr_confidence": null, "page_number": 107, "uncertainty_reason": null}, {"caption_id": "caption-4", "caption_subject": "心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车", "caption_text": "№2 心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车 背面", "is_uncertain": false, "ocr_confidence": null, "page_number": 107, "uncertainty_reason": null}, {"caption_id": "caption-5", "caption_subject": "心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车左面", "caption_text": "№3 心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车 左面", "is_uncertain": false, "ocr_confidence": null, "page_number": 108, "uncertainty_reason": null}, {"caption_id": "caption-6", "caption_subject": "心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车右面", "caption_text": "№4 心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车 右面", "is_uncertain": false, "ocr_confidence": null, "page_number": 108, "uncertainty_reason": null}, {"caption_id": "caption-9", "caption_subject": "心脏脉冲电场消融仪-触摸屏", "caption_text": "№7 心脏脉冲电场消融仪-触摸屏", "is_uncertain": false, "ocr_confidence": null, "page_number": 110, "uncertainty_reason": null}, {"caption_id": "caption-11", "caption_subject": "心脏脉冲电场消融仪-ECG主线缆", "caption_text": "№9 心脏脉冲电场消融仪-ECG 主线缆", "is_uncertain": false, "ocr_confidence": null, "page_number": 111, "uncertainty_reason": null}, {"caption_id": "caption-13", "caption_subject": "心脏脉冲电场消融仪-不可透射线ECG导联线（可选）", "caption_text": "№11 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选）", "is_uncertain": false, "ocr_confidence": null, "page_number": 112, "uncertainty_reason": null}, {"caption_id": "caption-15", "caption_subject": "光纤（15m）（可选）", "caption_text": "№13 光纤（15m）（可选）", "is_uncertain": false, "ocr_confidence": null, "page_number": 113, "uncertainty_reason": null}, {"caption_id": "caption-17", "caption_subject": "光接收器", "caption_text": "№15 光接收器", "is_uncertain": false, "ocr_confidence": null, "page_number": 114, "uncertainty_reason": null}, {"caption_id": "caption-19", "caption_subject": "电源电缆（可选）", "caption_text": "№17 电源电缆（可选）", "is_uncertain": false, "ocr_confidence": null, "page_number": 115, "uncertainty_reason": null}, {"caption_id": "caption-21", "caption_subject": "等电位线缆（3m）（可选）", "caption_text": "№19 等电位线缆 （3m）（可选）", "is_uncertain": false, "ocr_confidence": null, "page_number": 116, "uncertainty_reason": null}, {"caption_id": "caption-23", "caption_subject": "触摸屏连接线缆（30m）（可选）", "caption_text": "№21 触摸屏连接线缆（30m）（可选）", "is_uncertain": false, "ocr_confidence": null, "page_number": 117, "uncertainty_reason": null}, {"caption_id": "caption-25", "caption_subject": "心脏脉冲电场消融仪-触摸屏电源适配器（可选）", "caption_text": "№23 心脏脉冲电场消融仪-触摸屏电源适配器（可选）", "is_uncertain": false, "ocr_confidence": null, "page_number": 118, "uncertainty_reason": null}, {"caption_id": "caption-27", "caption_subject": "脉冲导管连接电缆（可选）", "caption_text": "№25 脉冲导管连接电缆（可选）", "is_uncertain": false, "ocr_confidence": null, "page_number": 119, "uncertainty_reason": null}, {"caption_id": "caption-29", "caption_subject": "软件版本", "caption_text": "№27 软件版本", "is_uncertain": false, "ocr_confidence": null, "page_number": 120, "uncertainty_reason": null}], "component_key": "心脏脉冲电场消融仪-触\n摸屏连接线缆（30m）\n（可选）|PFA-GEN-\nCBL30|/|/", "component_name": "心脏脉冲电场消融仪-触\n摸屏连接线缆（30m）\n（可选）", "is_unused_component": false, "matched_captions": [], "matching_strategy": null}, "is_unused_component": false, "page_number": 4, "rule_id": "C05", "severity": "error", "source": "report_codex_evidence_builder", "unused_reason": null}, "summary": "样品描述部件「心脏脉冲电场消融仪-触\n摸屏连接线缆（30m）\n（可选）」缺少对应照片", "target_id": "report-codex-target-ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing", "target_type": "photo_caption", "title": "样品描述部件「心脏脉冲电场消融仪-触\n摸屏连接线缆（30m）\n（可选）」缺少对应照片"}

## Evidence Items

### Evidence component:ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": 1, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}", "metadata": "{\"check_id\": \"C05\", \"component_id\": \"sample-row-1\", \"finding_id\": \"ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing\"}", "page_number": 4, "ref_id": "component:ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing", "section": "sample_component", "source_type": "report_field", "structured": "{\"actual\": \"未匹配到照片\", \"batch_or_serial\": \"20539798\", \"component_id\": \"sample-row-1\", \"component_name\": \"心脏脉冲电场消融仪-主\\n机\", \"expected\": \"至少一张照片\", \"expiration_date\": null, \"finding_metadata\": {\"candidate_captions\": [{\"caption_id\": \"caption-1\", \"caption_subject\": \".101用于以地为基准的患者电路的符号\", \"caption_text\": \"图 201.101 用于以地为基准的患者电路的符号\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 86, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-2\", \"caption_subject\": \".102用于高频绝缘的患者电路的符号\", \"caption_text\": \"图 201.102 用于高频绝缘的患者电路的符号\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 86, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-3\", \"caption_subject\": \"心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车\", \"caption_text\": \"№1 心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车 正面\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 107, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-4\", \"caption_subject\": \"心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车\", \"caption_text\": \"№2 心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车 背面\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 107, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-5\", \"caption_subject\": \"心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车左面\", \"caption_text\": \"№3 心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车 左面\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 108, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-6\", \"caption_subject\": \"心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车右面\", \"caption_text\": \"№4 心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车 右面\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 108, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-9\", \"caption_subject\": \"心脏脉冲电场消融仪-触摸屏\", \"caption_text\": \"№7 心脏脉冲电场消融仪-触摸屏\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 110, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-11\", \"caption_subject\": \"心脏脉冲电场消融仪-ECG主线缆\", \"caption_text\": \"№9 心脏脉冲电场消融仪-ECG 主线缆\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 111, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-13\", \"caption_subject\": \"心脏脉冲电场消融仪-不可透射线ECG导联线（可选）\", \"caption_text\": \"№11 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选）\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 112, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-15\", \"caption_subject\": \"光纤（15m）（可选）\", \"caption_text\": \"№13 光纤（15m）（可选）\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 113, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-17\", \"caption_subject\": \"光接收器\", \"caption_text\": \"№15 光接收器\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 114, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-19\", \"caption_subject\": \"电源电缆（可选）\", \"caption_text\": \"№17 电源电缆（可选）\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 115, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-21\", \"caption_subject\": \"等电位线缆（3m）（可选）\", \"caption_text\": \"№19 等电位线缆 （3m）（可选）\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 116, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-23\", \"caption_subject\": \"触摸屏连接线缆（30m）（可选）\", \"caption_text\": \"№21 触摸屏连接线缆（30m）（可选）\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 117, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-25\", \"caption_subject\": \"心脏脉冲电场消融仪-触摸屏电源适配器（可选）\", \"caption_text\": \"№23 心脏脉冲电场消融仪-触摸屏电源适配器（可选）\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 118, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-27\", \"caption_subject\": \"脉冲导管连接电缆（可选）\", \"caption_text\": \"№25 脉冲导管连接电缆（可选）\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 119, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-29\", \"caption_subject\": \"软件版本\", \"caption_text\": \"№27 软件版本\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 120, \"uncertainty_reason\": null}], \"component_key\": \"心脏脉冲电场消融仪-触\\n摸屏连接线缆（30m）\\n（可选）|PFA-GEN-\\nCBL30|/|/\", \"component_name\": \"心脏脉冲电场消融仪-触\\n摸屏连接线缆（30m）\\n（可选）\", \"is_unused_component\": false, \"matched_captions\": [], \"matching_strategy\": null}, \"identity_key\": \"心脏脉冲电场消融仪-主\\n机|PFA-GEN-01|20539798|2025-04-19\", \"is_unused_\n[truncated]", "text": null, "title": "C05 样品部件 evidence"}

### Evidence finding:ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing
{"file_path": null, "location": "{\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}", "metadata": "{\"check_id\": \"C05\", \"finding_code\": \"PHOTO_COVERAGE_MISSING\", \"finding_id\": \"ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing\", \"severity\": \"error\"}", "page_number": 4, "ref_id": "finding:ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing", "section": null, "source_type": "finding", "structured": "{\"actual\": \"未匹配到照片\", \"check_id\": \"C05\", \"code\": \"PHOTO_COVERAGE_MISSING\", \"confidence\": \"high\", \"diff_fragments\": [], \"evidence\": [{\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p4-t2:sample:r14:c1:component_name\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"部件名称\", \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}, \"metadata\": {\"column_index\": 1, \"field_name\": \"component_name\"}, \"method\": \"pdf_text\", \"normalized_text\": \"心脏脉冲电场消融仪-触摸屏连接线缆（30m）（可选）\", \"raw_text\": \"心脏脉冲电场消融仪-触\\n摸屏连接线缆（30m）\\n（可选）\", \"source_type\": \"report\", \"value\": \"心脏脉冲电场消融仪-触\\n摸屏连接线缆（30m）\\n（可选）\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p4-t2:sample:r14:c2:model\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"规格型号\", \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}, \"metadata\": {\"column_index\": 2, \"field_name\": \"model\"}, \"method\": \"pdf_text\", \"normalized_text\": \"PFA-GEN-CBL30\", \"raw_text\": \"PFA-GEN-\\nCBL30\", \"source_type\": \"report\", \"value\": \"PFA-GEN-\\nCBL30\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p4-t2:sample:r14:c3:batch_or_serial\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"序列号批号\", \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}, \"metadata\": {\"column_index\": 3, \"field_name\": \"batch_or_serial\"}, \"method\": \"pdf_text\", \"normalized_text\": \"/\", \"raw_text\": \"/\", \"source_type\": \"report\", \"value\": \"/\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p4-t2:sample:r14:c4:production_date\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"生产日期\", \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}, \"metadata\": {\"column_index\": 4, \"field_name\": \"production_date\"}, \"method\": \"pdf_text\", \"normalized_text\": \"/\", \"raw_text\": \"/\", \"source_type\": \"report\", \"value\": \"/\"}, {\"confidence\": \"high\", \"id\": \"36628a34943d8df5:p4-t2:sample:r14:c5:remark\", \"image_ref\": null, \"location\": {\"bbox\": null, \"column_name\": \"备注\", \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}, \"metadata\": {\"column_index\": 5, \"field_name\": \"remark\"}, \"method\": \"pdf_text\", \"normalized_text\": \"/\", \"raw_text\": \"/\", \"source_type\": \"report\", \"value\": \"/\"}], \"expected\": \"至少一张照片\", \"id\": \"ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing\", \"location\": {\"bbox\": null, \"column_name\": null, \"description\": null, \"page_number\": 4, \"row_index\": 14, \"section\": null, \"source_id\": \"36628a34943d8df5\", \"source_type\": \"report\", \"table_id\": \"p4-t2\", \"text_span\": null}, \"message\": \"样品描述部件「心脏脉冲电场消融仪-触\\n摸屏连接线缆（30m）\\n（可选）」缺少对应照片\", \"metadata\": {\"candidate_captions\": [{\"caption_id\": \"caption-1\", \"caption_subject\": \".101用于以地为基准的患者电路的符号\", \"caption_text\": \"图 201.101 用于以地为基准的患者电路的符号\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 86, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-2\", \"caption_subject\": \".102用于高频绝缘的患者电路的符号\", \"caption_text\": \"图 201.102 用于高频绝缘的患者电路的符号\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 86, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-3\", \"caption_subject\": \"心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车\", \"caption_text\": \"№1 心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车 正面\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 107, \"uncertainty_reason\": null}, {\"caption_id\": \"caption-4\", \"caption_subject\": \"心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车\", \"caption_text\": \"№2 心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车 背面\", \"is_uncertain\": false, \"ocr_confidence\": null, \"page_number\": 107, \"uncertainty_reason\": null}, {\"caption_id\": \"capt\n[truncated]", "text": null, "title": "样品描述部件「心脏脉冲电场消融仪-触\n摸屏连接线缆（30m）\n（可选）」缺少对应照片"}

### Evidence page_text:ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing
{"file_path": null, "location": null, "metadata": "{\"check_id\": \"C05\", \"file_id\": \"36628a34943d8df5\", \"finding_id\": \"ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing\"}", "page_number": 4, "ref_id": "page_text:ee21f597-1576-4008-835f-d81c89e0c107-c05-sample-row-14-photo-missing", "section": "page_text", "source_type": "page_text", "structured": "{\"page_number\": 4, \"text\": \"上\\n海\\n市\\n医\\n疗\\n器\\n械\\n检\\n验\\n研\\n究\\n院 \\n检 验 报 告 \\n报告编号：国医检（设）字 QW2025 第 2795 号     样品编号：QW2025-2795       共 118 页 第 2 页 \\n \\n样品描述 \\n被检样品主要部件包括： \\n序\\n号 \\n部件名称 \\n规格型号 \\n序列号/批号 \\n生产日期 \\n备注 \\n1 \\n心脏脉冲电场消融仪-主\\n机 \\nPFA-GEN-01 \\n20539798 \\n2025-04-19 \\n/ \\n2 \\n脉冲导管连接电缆（可\\n选） \\nA-UNI-PF-CBL \\n850778817 \\n2025-04-10 \\n/ \\n3 \\n心脏脉冲电场消融仪-推\\n车 \\nPFA-GEN-CART \\n10627717 \\n2024-11-26 \\n/ \\n4 \\n心脏脉冲电场消融仪- \\nECG 主线缆 \\nPFA-ECG-CBL \\n2024070069 \\n2024-07-13 \\n/ \\n5 \\n心脏脉冲电场消融仪-不\\n可透射线 ECG 导联线（可\\n选） \\nPFA-ECG-RNAM \\n2024070063 \\n2024-10-11 \\n/ \\n6 \\n心脏脉冲电场消融仪-可\\n透射线 ECG 导联线（可\\n选） \\nPFA-ECG-LNAM \\n/ \\n/ \\n本次检测未\\n使用 \\n7 \\n心脏脉冲电场消融仪-记\\n录系统连接线缆 \\nGEN-3RD-REC \\n/ \\n/ \\n本次检测未\\n使用 \\n8 \\n心脏脉冲电场消融仪-触\\n摸屏 \\nPFA-GEN-TS \\nC24H006740 \\n2024-10-14 \\n/ \\n9 \\n电源电缆（可选） \\nGEN-PWR-CH \\n10822757 \\n2017-10-15 \\n/ \\n10 \\n等电位线缆（3m）（可\\n选） \\nS100003 \\n/ \\n/ \\n/ \\n11 \\n光接收器（可选） \\nS100018 \\n/ \\n/ \\n/ \\n12 \\n心脏脉冲电场消融仪-触\\n摸屏连接线缆（10m）\\n（可选） \\nPFA-GEN-\\nCBL10 \\n/ \\n/ \\n本次检测未\\n使用 \\n13 \\n心脏脉冲电场消融仪-触\\n摸屏连接线缆（15m）\\n（可选） \\nPFA-GEN-\\nCBL15 \\n/ \\n/ \\n本次检测未\\n使用 \\n14 \\n心脏脉冲电场消融仪-触\\n摸屏连接线缆（30m）\\n（可选） \\nPFA-GEN-\\nCBL30 \\n/ \\n/ \\n/ \\n15 \\n光纤（10m）（可选） \\nH700179 \\n/ \\n/ \\n本次检测未\\n使用 \\n\"}", "text": "上\n海\n市\n医\n疗\n器\n械\n检\n验\n研\n究\n院 \n检 验 报 告 \n报告编号：国医检（设）字 QW2025 第 2795 号     样品编号：QW2025-2795       共 118 页 第 2 页 \n \n样品描述 \n被检样品主要部件包括： \n序\n号 \n部件名称 \n规格型号 \n序列号/批号 \n生产日期 \n备注 \n1 \n心脏脉冲电场消融仪-主\n机 \nPFA-GEN-01 \n20539798 \n2025-04-19 \n/ \n2 \n脉冲导管连接电缆（可\n选） \nA-UNI-PF-CBL \n850778817 \n2025-04-10 \n/ \n3 \n心脏脉冲电场消融仪-推\n车 \nPFA-GEN-CART \n10627717 \n2024-11-26 \n/ \n4 \n心脏脉冲电场消融仪- \nECG 主线缆 \nPFA-ECG-CBL \n2024070069 \n2024-07-13 \n/ \n5 \n心脏脉冲电场消融仪-不\n可透射线 ECG 导联线（可\n选） \nPFA-ECG-RNAM \n2024070063 \n2024-10-11 \n/ \n6 \n心脏脉冲电场消融仪-可\n透射线 ECG 导联线（可\n选） \nPFA-ECG-LNAM \n/ \n/ \n本次检测未\n使用 \n7 \n心脏脉冲电场消融仪-记\n录系统连接线缆 \nGEN-3RD-REC \n/ \n/ \n本次检测未\n使用 \n8 \n心脏脉冲电场消融仪-触\n摸屏 \nPFA-GEN-TS \nC24H006740 \n2024-10-14 \n/ \n9 \n电源电缆（可选） \nGEN-PWR-CH \n10822757 \n2017-10-15 \n/ \n10 \n等电位线缆（3m）（可\n选） \nS100003 \n/ \n/ \n/ \n11 \n光接收器（可选） \nS100018 \n/ \n/ \n/ \n12 \n心脏脉冲电场消融仪-触\n摸屏连接线缆（10m）\n（可选） \nPFA-GEN-\nCBL10 \n/ \n/ \n本次检测未\n使用 \n13 \n心脏脉冲电场消融仪-触\n摸屏连接线缆（15m）\n（可选） \nPFA-GEN-\nCBL15 \n/ \n/ \n本次检测未\n使用 \n1
[truncated]
