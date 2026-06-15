from __future__ import annotations

import re
from datetime import datetime

from app.domain.report import LabelOCRField

FIELD_PATTERNS = {
    "product_name": [
        r"产品\s*名称\s*(?:[：:]\s*)?([^\n]+)",
        r"器械\s*名称\s*(?:[：:]\s*)?([^\n]+)",
        r"品名\s*(?:[：:]\s*)?([^\n]+)",
    ],
    "model_spec": [
        r"规格\s*型号\s*(?:[：:]\s*)?([^\n]+)",
        r"型号\s*规格\s*(?:[：:]\s*)?([^\n]+)",
        r"(?<!产品)型号\s*(?:[：:]\s*)?([^\n]+)",
        r"Model\s*(?:[：:]\s*)?([^\n]+)",
        r"Spec\s*(?:[：:]\s*)?([^\n]+)",
    ],
    "production_date": [
        r"生产\s*日期\s*(?:[：:]\s*)?([^\n]+)",
        r"MFG\s*(?:[：:]\s*)?([^\n]+)",
        r"MFD\s*(?:[：:]\s*)?([^\n]+)",
        r"制造\s*日期\s*(?:[：:]\s*)?([^\n]+)",
    ],
    "expiration_date": [
        r"失效\s*日期\s*(?:[：:]\s*)?([^\n]+)",
        r"有效期至\s*(?:[：:]\s*)?([^\n]+)",
        r"EXP\s*(?:[：:]\s*)?([^\n]+)",
    ],
    "batch_number": [
        r"批号\s*(?:[：:]\s*)?([^\n]+)",
        r"LOT\s*(?:[：:]?\s*)?([^\n]+)",
        r"Batch Number\s*(?:[：:]\s*)?([^\n]+)",
    ],
    "serial_number": [
        r"序列号\s*(?:[：:]\s*)?([^\n]+)",
        r"\bSN\b\s*(?:[：:]\s*)?([^\n]+)",
        r"Serial Number\s*(?:[：:]\s*)?([^\n]+)",
    ],
    "registrant": [
        r"注册人\s*名称\s*[：:]\s*([^\n]+)",
        r"注册人\s*[：:]\s*([^\n]+)",
    ],
    "registrant_address": [
        r"注册人住所\s*(?:[：:]\s*)?([^\n]+)",
        r"注册人地址\s*(?:[：:]\s*)?([^\n]+)",
    ],
}


class LabelFieldExtractor:
    def extract_fields(self, text: str | None) -> list[LabelOCRField]:
        raw_fields = self.extract_as_dict(text)
        return [
            LabelOCRField(
                name=name,
                raw_value=f"{name}：{value}",
                value=value,
                normalized_value=re.sub(r"\s+", "", value),
                aliases=self.aliases_for(name),
            )
            for name, value in raw_fields.items()
            if value
        ]

    def extract_as_dict(self, text: str | None) -> dict[str, str]:
        value = str(text or "")
        fields: dict[str, str] = {}
        for field_name, patterns in FIELD_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, value, re.IGNORECASE)
                if match:
                    candidate = match.group(1).strip()
                    if self._is_valid_field_value(field_name, candidate):
                        fields[field_name] = self._clean_value(candidate)
                        break

        fields.update(self._next_line_values(value, fields))
        address = self._extract_multiline_value(
            value,
            label_patterns=[r"注册人住所", r"注册人地址"],
            stop_patterns=[r"注册人联系方式", r"受托生产企业", r"产品名称", r"型号规格", r"生产日期", r"失效日期"],
        )
        if address:
            fields["registrant_address"] = address

        dates = self._extract_date_candidates(value)
        if not fields.get("production_date") and dates:
            fields["production_date"] = dates[0]
        if not fields.get("expiration_date") and len(dates) >= 2:
            fields["expiration_date"] = dates[-1]
        if not fields.get("model_spec"):
            model = self._extract_model_spec_fallback(value)
            if model:
                fields["model_spec"] = model
        if not fields.get("batch_number"):
            batch = self._extract_batch_number_fallback(value)
            if batch:
                fields["batch_number"] = batch
        if not fields.get("serial_number") and not fields.get("batch_number"):
            serial = self._extract_standalone_serial_or_batch(value)
            if serial:
                fields["serial_number"] = serial
        return {key: self._clean_value(item) for key, item in fields.items() if item}

    def aliases_for(self, field_name: str) -> list[str]:
        return {
            "product_name": ["产品名称", "器械名称", "品名"],
            "model_spec": ["型号规格", "规格型号", "型号", "Model", "Spec", "REF"],
            "production_date": ["生产日期", "MFG", "MFD", "制造日期"],
            "expiration_date": ["失效日期", "有效期至", "EXP"],
            "batch_number": ["批号", "LOT", "Batch Number"],
            "serial_number": ["序列号", "SN", "Serial Number"],
            "registrant": ["注册人", "注册人名称"],
            "registrant_address": ["注册人住所", "注册人地址"],
        }.get(field_name, [])

    def _next_line_values(self, text: str, fields: dict[str, str]) -> dict[str, str]:
        additions: dict[str, str] = {}
        lines = [line.strip() for line in text.splitlines()]
        for idx, line in enumerate(lines[:-1]):
            next_value = next((candidate for candidate in lines[idx + 1:] if candidate), "")
            if not next_value:
                continue
            if ("规格型号" in line or "型号规格" in line or line.upper() == "REF") and not fields.get("model_spec"):
                if re.fullmatch(r"[A-Za-z][A-Za-z0-9.\-_/]{2,}", next_value):
                    additions["model_spec"] = next_value
            if any(key in line.upper() for key in ["SN", "序列号", "批号", "LOT"]) and not fields.get("serial_number") and not fields.get("batch_number"):
                if re.fullmatch(r"[A-Za-z0-9.\-_/]{4,}", next_value):
                    additions["serial_number"] = next_value
        return additions

    def _extract_date_candidates(self, text: str) -> list[str]:
        raw = re.findall(r"(20\d{2}[-/.年]?\d{1,2}[-/.月]?\d{1,2}日?)", text or "")
        parsed: list[tuple[datetime, str]] = []
        seen: set[str] = set()
        for item in raw:
            digits = re.sub(r"\D", "", item)
            if len(digits) != 8 or digits in seen:
                continue
            try:
                dt = datetime.strptime(digits, "%Y%m%d")
            except ValueError:
                continue
            seen.add(digits)
            parsed.append((dt, f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"))
        parsed.sort(key=lambda pair: pair[0])
        return [item for _, item in parsed]

    def _extract_model_spec_fallback(self, text: str) -> str:
        match = re.search(r"\bREF\b[^\nA-Za-z0-9]{0,6}([A-Za-z][A-Za-z0-9.\-_/]{3,})", text or "", re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _extract_batch_number_fallback(self, text: str) -> str:
        match = re.search(r"\bLOT\b[^\nA-Za-z0-9]{0,4}([A-Za-z0-9.\-_/]{3,})", text or "", re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _extract_standalone_serial_or_batch(self, text: str) -> str:
        candidates = re.findall(r"\b[A-Z]{2,8}\d{6,}[A-Z0-9\-_/]*\b", text or "")
        return sorted(candidates, key=len, reverse=True)[0] if candidates else ""

    def _extract_multiline_value(self, text: str, label_patterns: list[str], stop_patterns: list[str]) -> str:
        lines = [line.strip() for line in text.splitlines()]
        label_res = [re.compile(pattern) for pattern in label_patterns]
        stop_res = [re.compile(pattern) for pattern in stop_patterns]
        for index, line in enumerate(lines):
            if not any(regex.search(line) for regex in label_res):
                continue
            parts: list[str] = []
            same_line = re.split(r"[:：]", line, maxsplit=1)
            if len(same_line) == 2 and same_line[1].strip():
                parts.append(same_line[1].strip())
            for following in lines[index + 1:]:
                if not following:
                    continue
                if any(regex.search(following) for regex in stop_res):
                    break
                parts.append(following)
            return "".join(parts).strip()
        return ""

    def _is_valid_field_value(self, field_name: str, value: str) -> bool:
        cleaned = value.strip()
        if not cleaned or re.fullmatch(r"[【】\[\]()（）:：|/\\-]+", cleaned):
            return False
        if field_name in {"model_spec", "batch_number", "serial_number"} and len(re.sub(r"\s+", "", cleaned)) < 3:
            return False
        if field_name == "registrant" and re.search(r"(住所|住址|地址|联系方式)", cleaned):
            return False
        return True

    def _clean_value(self, value: str) -> str:
        return re.sub(r"^[：:]+", "", str(value or "")).strip()


def extract_label_fields_from_text(text: str | None) -> dict[str, str]:
    return LabelFieldExtractor().extract_as_dict(text)
