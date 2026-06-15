from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from app.domain.ptr import PTRClause, PTRDocument, PTRScopeType


RANGE_RE = re.compile(r"(\d+(?:\.\d+)*)\s*[~～\-至到]+\s*(\d+(?:\.\d+)*)")
NUMBER_RE = re.compile(r"\d+(?:\.\d+)*")
EXCLUSION_PATTERNS = (
    re.compile(r"除([^）)。；;]+)"),
    re.compile(r"(?:不包括|不含|不检|排除)([^）)。；;]+)"),
)
EXTERNAL_STANDARD_RE = re.compile(r"(?:^|[^\w])(?:GB|GB/T|YY|YY/T)\s*\d", re.IGNORECASE)
EXCLUDED_SCOPE_TYPES = {
    PTRScopeType.TEST_METHOD,
    PTRScopeType.APPENDIX,
    PTRScopeType.INFORMATIONAL,
    PTRScopeType.EXTERNAL_STANDARD,
}


class ScopeRule(BaseModel):
    start: tuple[int, ...]
    end: tuple[int, ...]
    evidence: str = ""


class ScopeDecision(BaseModel):
    clause_id: str
    clause_number: str
    included: bool
    reason: str
    evidence: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScopeFilterResult(BaseModel):
    included_clause_ids: list[str] = Field(default_factory=list)
    excluded_clause_ids: list[str] = Field(default_factory=list)
    decisions: list[ScopeDecision] = Field(default_factory=list)
    findings: list[Any] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def filter_ptr_scope(
    ptr_doc: PTRDocument,
    inspection_scope_texts: list[str],
    *,
    report_clause_numbers: set[str] | None = None,
) -> ScopeFilterResult:
    rules, excluded_topics = _parse_scope(inspection_scope_texts)
    report_clause_numbers = report_clause_numbers or set()
    decisions: list[ScopeDecision] = []
    included_ids: list[str] = []
    excluded_ids: list[str] = []

    for clause in ptr_doc.clauses:
        decision = _decide_clause(clause, rules, excluded_topics, report_clause_numbers)
        decisions.append(decision)
        if decision.included:
            included_ids.append(clause.clause_id)
        else:
            excluded_ids.append(clause.clause_id)

    return ScopeFilterResult(
        included_clause_ids=included_ids,
        excluded_clause_ids=excluded_ids,
        decisions=decisions,
        metadata={
            "scope_rules": [rule.model_dump() for rule in rules],
            "excluded_topics": excluded_topics,
        },
    )


def _parse_scope(texts: list[str]) -> tuple[list[ScopeRule], list[str]]:
    rules: list[ScopeRule] = []
    excluded_topics: list[str] = []
    seen_rules: set[tuple[tuple[int, ...], tuple[int, ...], str]] = set()
    seen_topics: set[str] = set()

    for raw in texts:
        text = str(raw or "").strip()
        if not text:
            continue
        normalized = re.sub(r"\s+", "", text)

        for pattern in EXCLUSION_PATTERNS:
            for match in pattern.finditer(normalized):
                for topic in re.split(r"[、，,；;/及和]", match.group(1)):
                    topic = topic.strip("()（）")
                    if topic and topic not in seen_topics:
                        seen_topics.add(topic)
                        excluded_topics.append(topic)

        matched_numbers: set[str] = set()
        for match in RANGE_RE.finditer(normalized):
            start = _parse_number(match.group(1))
            end = _parse_number(match.group(2))
            if not start or not end:
                continue
            if start > end:
                start, end = end, start
            key = (start, end, text)
            if key not in seen_rules:
                rules.append(ScopeRule(start=start, end=end, evidence=text))
                seen_rules.add(key)
            matched_numbers.add(match.group(1))
            matched_numbers.add(match.group(2))

        for token in NUMBER_RE.findall(normalized):
            if token in matched_numbers:
                continue
            number = _parse_number(token)
            if not number:
                continue
            key = (number, number, text)
            if key not in seen_rules:
                rules.append(ScopeRule(start=number, end=number, evidence=text))
                seen_rules.add(key)

    return rules, excluded_topics


def _decide_clause(
    clause: PTRClause,
    rules: list[ScopeRule],
    excluded_topics: list[str],
    report_clause_numbers: set[str],
) -> ScopeDecision:
    clause_number = str(clause.number)
    body_compact = _compact(" ".join(part for part in [clause.title or "", clause.body_text or ""] if part))

    if clause.scope_type in EXCLUDED_SCOPE_TYPES:
        return ScopeDecision(clause_id=clause.clause_id, clause_number=clause_number, included=False, reason="scope_type_excluded")

    if EXTERNAL_STANDARD_RE.search(body_compact):
        return ScopeDecision(clause_id=clause.clause_id, clause_number=clause_number, included=False, reason="external_standard")

    for topic in excluded_topics:
        topic_compact = _compact(topic)
        reduced = topic_compact.rstrip("性")
        if topic_compact and (
            topic_compact in body_compact
            or (reduced and reduced in body_compact)
            or f"{topic_compact}性" in body_compact
        ):
            return ScopeDecision(
                clause_id=clause.clause_id,
                clause_number=clause_number,
                included=False,
                reason="excluded_topic",
                evidence=topic,
            )

    if clause_number in report_clause_numbers or any(
        clause_number.startswith(report_number + ".") or report_number.startswith(clause_number + ".")
        for report_number in report_clause_numbers
    ):
        return ScopeDecision(clause_id=clause.clause_id, clause_number=clause_number, included=True, reason="report_clause_present")

    if not rules:
        return ScopeDecision(clause_id=clause.clause_id, clause_number=clause_number, included=True, reason="no_explicit_scope")

    clause_tuple = _parse_number(clause_number)
    if any(_tuple_in_rule(clause_tuple, rule) for rule in rules):
        return ScopeDecision(clause_id=clause.clause_id, clause_number=clause_number, included=True, reason="declared_scope")

    return ScopeDecision(clause_id=clause.clause_id, clause_number=clause_number, included=False, reason="outside_declared_scope")


def _tuple_in_rule(clause: tuple[int, ...], rule: ScopeRule) -> bool:
    if not clause:
        return True
    start, end = rule.start, rule.end
    if start == end:
        return clause[: len(start)] == start

    common_prefix_len = 0
    for left, right in zip(start, end, strict=False):
        if left != right:
            break
        common_prefix_len += 1
    if common_prefix_len and clause[:common_prefix_len] != start[:common_prefix_len]:
        return False

    depth = min(len(start), len(end), len(clause))
    clause_prefix = clause[:depth]
    start_prefix = start[:depth]
    end_prefix = end[:depth]
    return start_prefix <= clause_prefix <= end_prefix


def _parse_number(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for token in str(value or "").split("."):
        if not token.isdigit():
            return tuple()
        parts.append(int(token))
    return tuple(parts)


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value or "")
