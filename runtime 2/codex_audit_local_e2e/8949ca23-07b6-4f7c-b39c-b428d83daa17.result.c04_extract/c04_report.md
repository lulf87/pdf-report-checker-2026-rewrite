# C04 Evidence Extract

```json
{
  "source_file": "8949ca23-07b6-4f7c-b39c-b428d83daa17.result.json",
  "c04_findings_count": 35,
  "by_code": {
    "SAMPLE_FIELD_MISSING_IN_LABEL": 28,
    "SAMPLE_COMPONENT_LABEL_NOT_FOUND": 7
  },
  "by_final_status": {
    "manual_review_required": 28,
    "refuted": 7
  },
  "by_codex_verdict": {
    "uncertain": 28,
    "refute": 7
  },
  "confirmed_count": 0,
  "confirmed_errors_count": 0,
  "manual_review_required_count": 28,
  "refuted_count": 7,
  "can_verify_label_content_count": 28,
  "has_matching_label_caption_count": 33,
  "has_matched_label_crop_count": 0,
  "has_matched_label_ocr_count": 28,
  "has_matched_structured_fields_count": 0,
  "unused_component_count": 5
}
```

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-1-序列号批号
- component: None
- field: 序列号批号
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-7", "caption_text": "№5 心脏脉冲电场消融仪-主机 中文标签样张", "subject_name": "心脏脉冲电场消融仪-主机", "caption_type": "label", "page_number": 109, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 107 页 
照片和说明 
№5 心脏脉冲电场消融仪-主机 中文标签样张 
№6 心脏脉冲电场消融仪-推车 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-主
机”序列号批号为“20539798”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出序列号批号 20539798，且 caption 证明存在“心脏脉冲电场消融仪-主机 中文标签样张”。但 matched label OCR 主要是照片页页眉和 caption，未提供标签正文结构化字段或可核验 crop；OCR 未识别该字段不足以证明标签本体缺字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-2-序列号批号
- component: None
- field: 序列号批号
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-28", "caption_text": "№26 脉冲导管连接电缆（可选） 中文标签样张", "subject_name": "脉冲导管连接电缆（可选）", "caption_type": "label", "page_number": 119, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 117 页 
照片和说明 
№25 脉冲导管连接电缆（可选） 
№26 脉冲导管连接电缆（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“脉冲导管连接电缆（可
选）”序列号批号为“850778817”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述中序列号批号为850778817，且存在当前部件中文标签样张caption；但matched OCR主要是照片页页眉和caption，未提供标签裁剪图或结构化标签字段，不能稳定判断标签本体缺少该字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-4-序列号批号
- component: None
- field: 序列号批号
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-12", "caption_text": "№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张", "subject_name": "心脏脉冲电场消融仪-ECG 主线缆", "caption_type": "label", "page_number": 111, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 109 页 
照片和说明 
№9 心脏脉冲电场消融仪-ECG 主线缆 
№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪- 
ECG 主线缆”序列号批号为“2024070069”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出该部件序列号批号为2024070069，匹配到中文标签样张caption；但提供的匹配OCR文本主要为照片页页眉和caption，缺少可核验的标签本体图像裁剪、结构化字段或清晰标签正文，不能稳定确认标签本体缺少该字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-5-序列号批号
- component: None
- field: 序列号批号
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-14", "caption_text": "№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张", "subject_name": "心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选）", "caption_type": "label", "page_number": 112, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 110 页 
照片和说明 
№11 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 
№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-不
可透射线 ECG 导联线（可
选）”序列号批号为“2024070063”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出序列号批号 2024070063，且有对应中文标签样张 caption；但 matched OCR 内容主要为照片页页眉和 caption，未提供可核验标签正文、裁剪图或结构化字段，不能稳定判断标签本体缺少该字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-8-序列号批号
- component: None
- field: 序列号批号
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-10", "caption_text": "№8 心脏脉冲电场消融仪-触摸屏 中文标签样张", "subject_name": "心脏脉冲电场消融仪-触摸屏", "caption_type": "label", "page_number": 110, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 108 页 
照片和说明 
№7 心脏脉冲电场消融仪-触摸屏 
№8 心脏脉冲电场消融仪-触摸屏 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-触
摸屏”序列号批号为“C24H006740”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述中序列号为 C24H006740，但可见的 matched label OCR 主要是照片页页眉和“№8 ... 中文标签样张”caption，未提供可核验标签本体字段、结构化字段或裁剪图；caption 只能证明标签样张存在，不能确认标签本体缺字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-9-序列号批号
- component: None
- field: 序列号批号
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-20", "caption_text": "№18 电源电缆（可选） 中文标签样张", "subject_name": "电源电缆（可选）", "caption_type": "label", "page_number": 115, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 113 页 
照片和说明 
№17 电源电缆（可选） 
№18 电源电缆（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“电源电缆（可选）”序列号批号为“10822757”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出序列号批号 10822757，且存在对应“电源电缆（可选）中文标签样张”caption；但 matched_label_fields 为空、无标签裁剪图，matched OCR 仅能看到报告照片页标题和caption，不能稳定证明标签本体缺少该字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-1-生产日期
- component: None
- field: 生产日期
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-7", "caption_text": "№5 心脏脉冲电场消融仪-主机 中文标签样张", "subject_name": "心脏脉冲电场消融仪-主机", "caption_type": "label", "page_number": 109, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 107 页 
照片和说明 
№5 心脏脉冲电场消融仪-主机 中文标签样张 
№6 心脏脉冲电场消融仪-推车 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-主
机”生产日期为“2025-04-19”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出生产日期2025-04-19，匹配到№5中文标签样张caption；但可用OCR主要证明caption/页面文本，缺少标签裁剪图或结构化标签字段，不能稳定判断标签本体是否缺少生产日期。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-2-生产日期
- component: None
- field: 生产日期
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-28", "caption_text": "№26 脉冲导管连接电缆（可选） 中文标签样张", "subject_name": "脉冲导管连接电缆（可选）", "caption_type": "label", "page_number": 119, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 117 页 
照片和说明 
№25 脉冲导管连接电缆（可选） 
№26 脉冲导管连接电缆（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“脉冲导管连接电缆（可
选）”生产日期为“2025-04-10”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述中生产日期为2025-04-10，且存在对应中文标签样张caption；但matched label OCR仅能看到照片页页眉和caption，未提供标签正文裁剪图或结构化字段，无法稳定判断标签本体是否缺少生产日期字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-4-生产日期
- component: None
- field: 生产日期
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-12", "caption_text": "№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张", "subject_name": "心脏脉冲电场消融仪-ECG 主线缆", "caption_type": "label", "page_number": 111, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 109 页 
照片和说明 
№9 心脏脉冲电场消融仪-ECG 主线缆 
№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪- 
ECG 主线缆”生产日期为“2024-07-13”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述包含生产日期 2024-07-13，且存在匹配的中文标签样张 caption；但匹配 OCR 主要为照片页页眉和 caption，未提供标签裁剪图或结构化标签字段，不能稳定判断标签本体缺少生产日期。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-5-生产日期
- component: None
- field: 生产日期
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-14", "caption_text": "№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张", "subject_name": "心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选）", "caption_type": "label", "page_number": 112, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 110 页 
照片和说明 
№11 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 
№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-不
可透射线 ECG 导联线（可
选）”生产日期为“2024-10-11”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述中生产日期为2024-10-11，但匹配到的标签证据主要是中文标签样张caption和页面OCR文本；label_image无裁剪图，label_ocr无结构化字段且未提供可核对标签正文内容，不能稳定确认标签本体缺少生产日期。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-8-生产日期
- component: None
- field: 生产日期
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-10", "caption_text": "№8 心脏脉冲电场消融仪-触摸屏 中文标签样张", "subject_name": "心脏脉冲电场消融仪-触摸屏", "caption_type": "label", "page_number": 110, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 108 页 
照片和说明 
№7 心脏脉冲电场消融仪-触摸屏 
№8 心脏脉冲电场消融仪-触摸屏 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-触
摸屏”生产日期为“2024-10-14”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: finding 给出样品描述生产日期为 2024-10-14；label_caption 仅证明 №8 中文标签样张存在，label_image 无裁剪图，label_ocr 未提供可稳定判断标签正文字段缺失的结构化字段或裁剪证据，不能仅因 OCR 未识别生产日期确认标签本体缺字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-9-生产日期
- component: None
- field: 生产日期
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-20", "caption_text": "№18 电源电缆（可选） 中文标签样张", "subject_name": "电源电缆（可选）", "caption_type": "label", "page_number": 115, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 113 页 
照片和说明 
№17 电源电缆（可选） 
№18 电源电缆（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“电源电缆（可选）”生产日期为“2017-10-15”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出生产日期2017-10-15，caption可证明存在“电源电缆（可选）中文标签样张”，但label_image无裁剪图，label_ocr仅显示照片页/标题文字且无结构化字段，不能稳定证明标签本体缺少生产日期。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-1-规格型号
- component: None
- field: 规格型号
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-7", "caption_text": "№5 心脏脉冲电场消融仪-主机 中文标签样张", "subject_name": "心脏脉冲电场消融仪-主机", "caption_type": "label", "page_number": 109, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 107 页 
照片和说明 
№5 心脏脉冲电场消融仪-主机 中文标签样张 
№6 心脏脉冲电场消融仪-推车 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-主
机”规格型号为“PFA-GEN-01”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述中规格型号为 PFA-GEN-01，且存在匹配的中文标签样张 caption；但 label_ocr 仅显示照片页文字和 caption，缺少标签正文、结构化字段或可核验 crop，不能稳定判断标签本体是否缺少规格型号字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-2-规格型号
- component: None
- field: 规格型号
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-28", "caption_text": "№26 脉冲导管连接电缆（可选） 中文标签样张", "subject_name": "脉冲导管连接电缆（可选）", "caption_type": "label", "page_number": 119, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 117 页 
照片和说明 
№25 脉冲导管连接电缆（可选） 
№26 脉冲导管连接电缆（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“脉冲导管连接电缆（可
选）”规格型号为“A-UNI-PF-CBL”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出规格型号 A-UNI-PF-CBL，且 label_caption/label_ocr 指向当前部件的中文标签样张；但可用 OCR 主要证明照片页标题和样张 caption，label_image 显示无 crop，且无结构化标签字段，不能稳定判断标签本体是否缺少规格型号字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-4-规格型号
- component: None
- field: 规格型号
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-12", "caption_text": "№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张", "subject_name": "心脏脉冲电场消融仪-ECG 主线缆", "caption_type": "label", "page_number": 111, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 109 页 
照片和说明 
№9 心脏脉冲电场消融仪-ECG 主线缆 
№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪- 
ECG 主线缆”规格型号为“PFA-ECG-CBL”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: label_caption 与 label_image 仅能证明第111页存在该部件中文标签样张；label_ocr 的 matched_label_text 主要为报告页眉和样张 caption，未提供可核对标签本体字段、结构化字段或裁剪图，不能稳定确认标签本体缺少规格型号 PFA-ECG-CBL。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-5-规格型号
- component: None
- field: 规格型号
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-14", "caption_text": "№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张", "subject_name": "心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选）", "caption_type": "label", "page_number": 112, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 110 页 
照片和说明 
№11 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 
№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-不
可透射线 ECG 导联线（可
选）”规格型号为“PFA-ECG-RNAM”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出规格型号 PFA-ECG-RNAM；匹配到的中文标签 caption 可证明标签样张存在，但 label_ocr 主要为照片页页眉和 caption，未提供可核验标签本体字段、结构化字段或裁剪图。按 C04 规则，不能仅因 OCR 未识别字段确认标签本体缺字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-8-规格型号
- component: None
- field: 规格型号
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-10", "caption_text": "№8 心脏脉冲电场消融仪-触摸屏 中文标签样张", "subject_name": "心脏脉冲电场消融仪-触摸屏", "caption_type": "label", "page_number": 110, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 108 页 
照片和说明 
№7 心脏脉冲电场消融仪-触摸屏 
№8 心脏脉冲电场消融仪-触摸屏 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-触
摸屏”规格型号为“PFA-GEN-TS”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出规格型号 PFA-GEN-TS，且存在 №8 中文标签样张 caption；但 matched OCR 仅显示报告照片页页眉和 caption，未提供可稳定判断标签本体字段的 crop、结构化字段或完整标签正文，因此不能确认标签本体缺少规格型号。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-9-规格型号
- component: None
- field: 规格型号
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-20", "caption_text": "№18 电源电缆（可选） 中文标签样张", "subject_name": "电源电缆（可选）", "caption_type": "label", "page_number": 115, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 113 页 
照片和说明 
№17 电源电缆（可选） 
№18 电源电缆（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“电源电缆（可选）”规格型号为“GEN-PWR-CH”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出规格型号 GEN-PWR-CH，且存在匹配的中文标签样张 caption；但匹配 OCR 主要证明 caption/页面文字，未提供标签裁剪图或结构化字段，不能稳定确认标签本体缺少规格型号。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-10-规格型号
- component: None
- field: 规格型号
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-22", "caption_text": "№20 等电位线缆 （3m）（可选） 中文标签样张", "subject_name": "等电位线缆 （3m）（可选）", "caption_type": "label", "page_number": 116, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 114 页 
照片和说明 
№19 等电位线缆 （3m）（可选） 
№20 等电位线缆 （3m）（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“等电位线缆（3m）（可
选）”规格型号为“S100003”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出规格型号 S100003，但匹配证据主要是第116页中文标签样张 caption；label_image 无裁剪图，label_ocr 未提供可核验标签正文结构化字段或裁剪内容，不能仅因未识别到字段确认标签本体缺少规格型号。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-11-规格型号
- component: None
- field: 规格型号
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-18", "caption_text": "№16 光接收器（可选） 中文标签样张", "subject_name": "光接收器（可选）", "caption_type": "label", "page_number": 114, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 112 页 
照片和说明 
№15 光接收器 
№16 光接收器（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“光接收器（可选）”规格型号为“S100018”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述中规格型号为 S100018，但匹配到的中文标签证据主要是 caption/page OCR，未提供标签裁剪图或结构化标签字段；现有 OCR 文本不足以稳定判断标签本体是否缺少规格型号字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-1-部件名称
- component: None
- field: 部件名称
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-7", "caption_text": "№5 心脏脉冲电场消融仪-主机 中文标签样张", "subject_name": "心脏脉冲电场消融仪-主机", "caption_type": "label", "page_number": 109, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 107 页 
照片和说明 
№5 心脏脉冲电场消融仪-主机 中文标签样张 
№6 心脏脉冲电场消融仪-推车 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-主
机”部件名称为“心脏脉冲电场消融仪-主
机”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述有部件名称，匹配 caption 只能证明第109页存在该部件中文标签样张；matched label OCR 主要为报告照片页页眉和 caption，未提供标签本体裁剪图或结构化字段，不能稳定判断标签本体缺少“部件名称”。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-2-部件名称
- component: None
- field: 部件名称
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-28", "caption_text": "№26 脉冲导管连接电缆（可选） 中文标签样张", "subject_name": "脉冲导管连接电缆（可选）", "caption_type": "label", "page_number": 119, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 117 页 
照片和说明 
№25 脉冲导管连接电缆（可选） 
№26 脉冲导管连接电缆（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“脉冲导管连接电缆（可
选）”部件名称为“脉冲导管连接电缆（可
选）”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述有该部件名称，且存在匹配的中文标签样张 caption；但可用 OCR 主要证明 caption 和页面文本，缺少标签裁剪图或结构化字段，不能稳定判断标签本体是否缺少“部件名称”字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-4-部件名称
- component: None
- field: 部件名称
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-12", "caption_text": "№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张", "subject_name": "心脏脉冲电场消融仪-ECG 主线缆", "caption_type": "label", "page_number": 111, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 109 页 
照片和说明 
№9 心脏脉冲电场消融仪-ECG 主线缆 
№10 心脏脉冲电场消融仪-ECG 主线缆  中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪- 
ECG 主线缆”部件名称为“心脏脉冲电场消融仪- 
ECG 主线缆”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述给出部件名称，且匹配到中文标签样张 caption；但 label OCR 仅显示报告照片页标题和样张 caption，未提供可核验标签本体字段的裁剪图或结构化字段。按 C04 要求，OCR 未识别字段不能等同于标签本体缺字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-5-部件名称
- component: None
- field: 部件名称
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-14", "caption_text": "№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张", "subject_name": "心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选）", "caption_type": "label", "page_number": 112, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 110 页 
照片和说明 
№11 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 
№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-不
可透射线 ECG 导联线（可
选）”部件名称为“心脏脉冲电场消融仪-不
可透射线 ECG 导联线（可
选）”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述中有该部件名称；匹配到的中文标签样张 caption 只能证明样张存在。label_ocr/label_image 未提供标签裁剪图或结构化标签字段，OCR 文本主要为照片页页眉和 caption，不能稳定判断标签本体是否缺少“部件名称”。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-8-部件名称
- component: None
- field: 部件名称
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-10", "caption_text": "№8 心脏脉冲电场消融仪-触摸屏 中文标签样张", "subject_name": "心脏脉冲电场消融仪-触摸屏", "caption_type": "label", "page_number": 110, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 108 页 
照片和说明 
№7 心脏脉冲电场消融仪-触摸屏 
№8 心脏脉冲电场消融仪-触摸屏 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“心脏脉冲电场消融仪-触
摸屏”部件名称为“心脏脉冲电场消融仪-触
摸屏”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: sample_description 显示 row 8 部件名称；label_caption 与 label_ocr 只能证明第110页存在№8中文标签样张及标题/页眉文本，label_image 无裁剪图且 matched_label_fields 为空，无法稳定判断标签本体缺少“部件名称”字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-9-部件名称
- component: None
- field: 部件名称
- severity: error
- codex: uncertain / medium
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-20", "caption_text": "№18 电源电缆（可选） 中文标签样张", "subject_name": "电源电缆（可选）", "caption_type": "label", "page_number": 115, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 113 页 
照片和说明 
№17 电源电缆（可选） 
№18 电源电缆（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“电源电缆（可选）”部件名称为“电源电缆（可选）”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品行显示部件名称为“电源电缆（可选）”，且有匹配中文标签样张 caption；但 matched OCR 主要为照片页页眉和 caption，未提供标签裁剪图或结构化标签字段，不能稳定判断标签本体缺少部件名称字段。

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-10-部件名称
- component: None
- field: 部件名称
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-22", "caption_text": "№20 等电位线缆 （3m）（可选） 中文标签样张", "subject_name": "等电位线缆 （3m）（可选）", "caption_type": "label", "page_number": 116, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 114 页 
照片和说明 
№19 等电位线缆 （3m）（可选） 
№20 等电位线缆 （3m）（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“等电位线缆（3m）（可
选）”部件名称为“等电位线缆（3m）（可
选）”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: matched caption proves the Chinese label sample exists, but the available OCR/crop evidence does not provide structured label fields or a label-body crop sufficient to verify that the 部件名称 field is truly absent; OCR non-recognition alone is insufficient.

## SAMPLE_FIELD_MISSING_IN_LABEL / manual_review_required / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-11-部件名称
- component: None
- field: 部件名称
- severity: error
- codex: uncertain / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: True
- has_structured_fields: False
- can_verify_label_content: True
- matched_label_caption: {"caption_id": "caption-18", "caption_text": "№16 光接收器（可选） 中文标签样张", "subject_name": "光接收器（可选）", "caption_type": "label", "page_number": 114, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_text: 上
海
市
医
疗
器
械
检
验
研
究
院 
检 验 报 告 照 片 页 
报告编号：国医检（设）字 QW2025 第 2795 号      样品编号：QW2025-2795       共 118 页 第 112 页 
照片和说明 
№15 光接收器 
№16 光接收器（可选） 中文标签样张 
- matched_label_fields: {}
- message: 样品描述部件“光接收器（可选）”部件名称为“光接收器（可选）”，但中文标签 OCR 未识别到对应字段
- codex_reasoning: 样品描述包含部件名称“光接收器（可选）”，且有匹配的中文标签样张 caption；但 matched label OCR 主要为页面标题和 caption，未提供标签本体裁剪图、结构化字段或可核验的标签正文，因此不能仅因未识别字段确认标签缺少部件名称。

## SAMPLE_COMPONENT_LABEL_NOT_FOUND / refuted / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-3-label-missing
- component: None
- field: None
- severity: warn
- codex: refute / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: False
- has_structured_fields: False
- can_verify_label_content: False
- matched_label_caption: {"caption_id": "caption-8", "caption_text": "№6 心脏脉冲电场消融仪-推车 中文标签样张", "subject_name": "心脏脉冲电场消融仪-推车", "caption_type": "label", "page_number": 109, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_fields: {}
- message: 未找到与样品描述部件匹配的中文标签 OCR
- codex_reasoning: page_text 显示样品行3为“心脏脉冲电场消融仪-推车”，备注为“/”；label_caption 和 label_image 显示第109页存在匹配的“№6 心脏脉冲电场消融仪-推车 中文标签样张”。缺 matched OCR/crop 不能证明标签样张缺失，因此反驳 label-not-found 候选。

## SAMPLE_COMPONENT_LABEL_NOT_FOUND / refuted / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-6-label-missing
- component: None
- field: None
- severity: warn
- codex: refute / high
- unused: True / 本次检测未
使用
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: False
- has_structured_fields: False
- can_verify_label_content: False
- matched_label_caption: {"caption_id": "caption-14", "caption_text": "№12 心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选） 中文标签样张", "subject_name": "心脏脉冲电场消融仪-不可透射线 ECG 导联线（可选）", "caption_type": "label", "page_number": 112, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_fields: {}
- message: 未找到与样品描述部件匹配的中文标签 OCR
- codex_reasoning: finding 与 page_text 均显示样品描述第6行备注为“本次检测未使用”；按 C04 指令，该部件不适用标签覆盖缺失错误，因此反驳该候选。

## SAMPLE_COMPONENT_LABEL_NOT_FOUND / refuted / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-7-label-missing
- component: None
- field: None
- severity: warn
- codex: refute / high
- unused: True / 本次检测未
使用
- has_matching_caption: False
- has_label_image: False
- has_label_crop: False
- has_label_ocr: False
- has_structured_fields: False
- can_verify_label_content: False
- matched_label_fields: {}
- message: 未找到与样品描述部件匹配的中文标签 OCR
- codex_reasoning: page_text 与 finding 证据均显示 sample-row-7 备注为“本次检测未使用”，rule_context 也标记 is_unused_component=true；按任务规则，该部件不适用中文标签覆盖错误，因此反驳该 label-not-found 候选。

## SAMPLE_COMPONENT_LABEL_NOT_FOUND / refuted / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-12-label-missing
- component: None
- field: None
- severity: warn
- codex: refute / high
- unused: True / 本次检测未
使用
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: False
- has_structured_fields: False
- can_verify_label_content: False
- matched_label_caption: {"caption_id": "caption-10", "caption_text": "№8 心脏脉冲电场消融仪-触摸屏 中文标签样张", "subject_name": "心脏脉冲电场消融仪-触摸屏", "caption_type": "label", "page_number": 110, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_fields: {}
- message: 未找到与样品描述部件匹配的中文标签 OCR
- codex_reasoning: page_text 与 finding 证据均显示第12行备注为“本次检测未使用”；该类部件不适用 C04 标签覆盖错误。且存在中文标签样张 caption，不能确认 label-not-found。

## SAMPLE_COMPONENT_LABEL_NOT_FOUND / refuted / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-13-label-missing
- component: None
- field: None
- severity: warn
- codex: refute / high
- unused: True / 本次检测未
使用
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: False
- has_structured_fields: False
- can_verify_label_content: False
- matched_label_caption: {"caption_id": "caption-10", "caption_text": "№8 心脏脉冲电场消融仪-触摸屏 中文标签样张", "subject_name": "心脏脉冲电场消融仪-触摸屏", "caption_type": "label", "page_number": 110, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_fields: {}
- message: 未找到与样品描述部件匹配的中文标签 OCR
- codex_reasoning: finding 和 page_text 均显示 sample-row-13 备注为“本次检测未使用”，按任务规则该部件不适用 C04 标签覆盖错误；且 label_caption/label_image 显示存在中文标签样张页引用但无可验证正文 OCR，不能确认标签缺失。

## SAMPLE_COMPONENT_LABEL_NOT_FOUND / refuted / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-14-label-missing
- component: None
- field: None
- severity: warn
- codex: refute / high
- unused: False / None
- has_matching_caption: True
- has_label_image: True
- has_label_crop: False
- has_label_ocr: False
- has_structured_fields: False
- can_verify_label_content: False
- matched_label_caption: {"caption_id": "caption-10", "caption_text": "№8 心脏脉冲电场消融仪-触摸屏 中文标签样张", "subject_name": "心脏脉冲电场消融仪-触摸屏", "caption_type": "label", "page_number": 110, "matched_component_ids": [], "metadata": {"is_chinese_label": true}}
- matched_label_fields: {}
- message: 未找到与样品描述部件匹配的中文标签 OCR
- codex_reasoning: page_text 确认样品 row 14 为触摸屏连接线缆（30m）（可选）；label_caption 提供匹配的“№22 触摸屏连接线缆（30m）（可选）中文标签样张”，caption 可证明中文标签样张存在。finding 属于 label-not-found，caption 存在时应 refute；未匹配 OCR 只能说明标签内容无法核对，不能确认标签缺失。

## SAMPLE_COMPONENT_LABEL_NOT_FOUND / refuted / 8949ca23-07b6-4f7c-b39c-b428d83daa17-c04-sample-row-15-label-missing
- component: None
- field: None
- severity: warn
- codex: refute / high
- unused: True / 本次检测未
使用
- has_matching_caption: False
- has_label_image: False
- has_label_crop: False
- has_label_ocr: False
- has_structured_fields: False
- can_verify_label_content: False
- matched_label_fields: {}
- message: 未找到与样品描述部件匹配的中文标签 OCR
- codex_reasoning: 页文本和 finding 证据显示 row 15 光纤（10m）（可选）备注为“本次检测未使用”，rule_context 也标记 is_unused_component=true；该类部件不适用中文标签覆盖缺失判定。
