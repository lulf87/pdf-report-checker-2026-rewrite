from __future__ import annotations

import re
from pydantic import BaseModel


class CaptionInfo(BaseModel):
    raw_caption: str = ""
    caption_number: str = ""
    is_chinese_label: bool = False
    main_name: str = ""
    caption_type: str | None = None
    position: tuple[int, int, int, int] | None = None


class CaptionExtractor:
    label_keywords = ("中文标签", "标签样张", "中文标签样张", "铭牌", "标牌")

    def parse(self, caption_text: str | None) -> CaptionInfo:
        raw = str(caption_text or "").strip()
        info = CaptionInfo(raw_caption=raw)
        info.is_chinese_label = self.is_chinese_label(raw)
        if info.is_chinese_label:
            info.caption_type = "label"
        elif "照片" in raw or "外观" in raw or "图" in raw:
            info.caption_type = "photo"

        match = re.search(r"(?:图|№|No\.?|Photo|Fig|Fig\.)\s*(\d+)", raw, re.IGNORECASE)
        if match:
            info.caption_number = match.group(1)

        main_name = re.sub(r"^(?:图|№|No\.?|Photo|Plate|Fig|Fig\.)\s*\d+\s*[:：]?\s*", "", raw, flags=re.IGNORECASE)
        for pattern in [
            r"左侧显示", r"右侧显示", r"左图", r"右图", r"正面图", r"背面图",
            r"俯视图", r"仰视图", r"局部放大图", r"细节图", r"整体图",
        ]:
            main_name = re.sub(pattern, "", main_name)
        for pattern in [r"中文标签(?:样张)?\s*[:：]?", r"标签(?:样张)?\s*[:：]?", r"铭牌\s*[:：]?", r"标牌\s*[:：]?", r"照片\s*[:：]?"]:
            main_name = re.sub(pattern, "", main_name)
        main_name = re.sub(r"^[第一二三四五六七八九十\d]+(?:[\.、:：]|张)\s*", "", main_name)
        info.main_name = main_name.strip(" ：:")
        return info

    def extract_from_page_text(self, page_text: str | None) -> CaptionInfo | None:
        lines = [line.strip() for line in str(page_text or "").splitlines() if line.strip()]
        prefix_candidates = [
            line for line in lines if re.match(r"^(图|№|No\.?|Photo|Plate|Fig\.?)", line, re.IGNORECASE)
        ]
        for candidate in prefix_candidates:
            if self.is_chinese_label(candidate):
                return self.parse(candidate)
        if prefix_candidates:
            return self.parse(prefix_candidates[0])
        for line in lines:
            if self.is_chinese_label(line):
                return self.parse(line)
        return None

    def is_chinese_label(self, text: str | None) -> bool:
        value = str(text or "").lower()
        return any(keyword.lower() in value for keyword in self.label_keywords)


def parse_caption_main_name(caption_text: str | None) -> str:
    return CaptionExtractor().parse(caption_text).main_name
