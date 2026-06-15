from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.infrastructure.text.normalizer import normalize_text


def numeric_expressions_equivalent(left: str | None, right: str | None, *, field_kind: str = "value") -> bool:
    return normalize_numeric_expression(left, field_kind=field_kind) == normalize_numeric_expression(right, field_kind=field_kind)


def normalize_numeric_expression(value: str | None, *, field_kind: str = "value") -> str:
    compact = _compact(value)
    if not compact:
        return ""

    if field_kind == "tolerance":
        tolerance = _normalize_tolerance(compact)
        if tolerance is not None:
            return tolerance

    comparator = _normalize_comparator(compact)
    if comparator is not None:
        return comparator

    range_value = _normalize_range(compact)
    if range_value is not None:
        return range_value

    number = _normalize_number_token(compact)
    if number is not None:
        return f"num:{number}"

    return f"raw:{compact}"


def _compact(value: str | None) -> str:
    text = normalize_text(value or "")
    text = text.replace("＋／－", "+/-").replace("+／-", "+/-").replace("±", "±")
    text = text.replace("﹢", "+").replace("＋", "+")
    text = text.replace("−", "-").replace("－", "-").replace("—", "-").replace("–", "-")
    text = text.replace("～", "~").replace("至", "~").replace("到", "~")
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    text = re.sub(r"\s+", "", text)
    return text


def _normalize_tolerance(compact: str) -> str | None:
    text = re.sub(r"^(?:允许误差|误差|允差|允许偏差|偏差|公差)[:：]?", "", compact)
    text = text.replace("+/-", "±").replace("+-", "±")

    base_match = re.fullmatch(rf"({_NUMBER})([A-Za-zμΩ°/%套]*)±({_NUMBER})([A-Za-zμΩ°/%套]*)", text)
    if base_match:
        return (
            f"tol-base:{_decimal(base_match.group(1))}{_unit(base_match.group(2))}"
            f"±{_decimal(base_match.group(3))}{_unit(base_match.group(4))}"
        )

    delta_match = re.fullmatch(rf"±({_NUMBER})([A-Za-zμΩ°/%套]*)", text)
    if delta_match:
        return f"tol:±{_decimal(delta_match.group(1))}{_unit(delta_match.group(2))}"

    number = _normalize_number_token(text)
    if number is not None:
        return f"tol:±{number}"
    return None


def _normalize_comparator(compact: str) -> str | None:
    text = compact
    replacements = (
        ("不小于", ">="),
        ("不少于", ">="),
        ("大于等于", ">="),
        ("不大于", "<="),
        ("不超过", "<="),
        ("小于等于", "<="),
        ("大于", ">"),
        ("小于", "<"),
    )
    for source, target in replacements:
        if text.startswith(source):
            text = target + text[len(source):]
            break
    text = text.replace("≥", ">=").replace("≤", "<=")
    match = re.fullmatch(rf"(<=|>=|<|>)({_NUMBER})([A-Za-zμΩ°/%套]*)", text)
    if not match:
        return None
    return f"cmp:{match.group(1)}:{_decimal(match.group(2))}{_unit(match.group(3))}"


def _normalize_range(compact: str) -> str | None:
    match = re.fullmatch(rf"({_SIGNED_NUMBER})([A-Za-zμΩ°/%套]*)[~-]({_SIGNED_NUMBER})([A-Za-zμΩ°/%套]*)", compact)
    if not match:
        return None
    left = f"{_decimal(match.group(1))}{_unit(match.group(2))}"
    right = f"{_decimal(match.group(3))}{_unit(match.group(4))}"
    return f"range:{left}~{right}"


def _normalize_number_token(compact: str) -> str | None:
    match = re.fullmatch(rf"({_SIGNED_NUMBER})([A-Za-zμΩ°/%套]*)", compact)
    if not match:
        return None
    return f"{_decimal(match.group(1))}{_unit(match.group(2))}"


def _decimal(value: str) -> str:
    try:
        decimal = Decimal(value)
    except InvalidOperation:
        return value
    if decimal == 0:
        return "0"
    normalized = decimal.normalize()
    return format(normalized, "f").rstrip("0").rstrip(".") if "." in format(normalized, "f") else format(normalized, "f")


def _unit(value: str | None) -> str:
    return (value or "").replace("µ", "μ").replace("Ω", "Ω")


_NUMBER = r"\d+(?:\.\d+)?"
_SIGNED_NUMBER = rf"[-+]?{_NUMBER}"


__all__ = ["normalize_numeric_expression", "numeric_expressions_equivalent"]
