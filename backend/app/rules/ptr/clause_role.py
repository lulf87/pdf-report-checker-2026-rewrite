from __future__ import annotations

import re

from app.domain.ptr import PTRClause, PTRClauseRole, PTRScopeType
from app.rules.ptr.requirement_classifier import clause_local_text


DIRECT_REQUIREMENT_MARKERS = (
    "应符合",
    "应满足",
    "应按",
    "应具有",
    "应有",
    "不得",
    "不应",
    "至少",
    "不超过",
    "不小于",
    "允许误差",
    "允差",
    "应为",
    "应在",
)
TABLE_CAPTION_RE = re.compile(r"(?:^|\n)\s*表\s*[0-9一二三四五六七八九十]+(?:[-－]\d+)?")
STANDARD_RE = re.compile(r"(?:GB|GB/T|YY|YY/T|IEC|ISO)\s*\d", flags=re.IGNORECASE)


def classify_clause_role(clause: PTRClause) -> PTRClauseRole:
    """Classify a clause from its local requirement, hierarchy, and references.

    Table text may be attached to a parent clause by the extractor. The text
    before the first table caption is therefore used to decide whether the
    parent has an independent requirement of its own.
    """
    if clause.scope_type in {
        PTRScopeType.TEST_METHOD,
        PTRScopeType.APPENDIX,
        PTRScopeType.INFORMATIONAL,
        PTRScopeType.EXTERNAL_STANDARD,
    }:
        return PTRClauseRole.EXTERNAL_STANDARD_REQUIREMENT if clause.scope_type == PTRScopeType.EXTERNAL_STANDARD else PTRClauseRole.TEST_REQUIREMENT

    if clause.children_ids and not _has_independent_requirement(clause):
        return PTRClauseRole.SECTION_CONTAINER

    if clause.has_table_references() or clause.metadata.get("referenced_table_text_attached") is True:
        return PTRClauseRole.TABLE_REQUIREMENT

    local_text = _compact(clause_local_text(clause, include_title=False))
    if STANDARD_RE.search(local_text):
        return PTRClauseRole.EXTERNAL_STANDARD_REQUIREMENT
    return PTRClauseRole.TEST_REQUIREMENT


def assign_clause_roles(clauses: list[PTRClause]) -> list[str]:
    """Annotate clauses in place and return the section-container ids."""
    section_container_ids: list[str] = []
    for clause in clauses:
        role = classify_clause_role(clause)
        clause.clause_role = role
        clause.metadata["clause_role"] = role.value
        if role == PTRClauseRole.SECTION_CONTAINER:
            section_container_ids.append(clause.clause_id)
    return section_container_ids


def _has_independent_requirement(clause: PTRClause) -> bool:
    text = clause_local_text(clause, include_title=False)
    if not text:
        return False
    before_table = TABLE_CAPTION_RE.split(text, maxsplit=1)[0]
    compact = _compact(before_table)
    if not compact:
        return False
    return any(marker in compact for marker in DIRECT_REQUIREMENT_MARKERS)


def _compact(value: str | None) -> str:
    return re.sub(r"\s+", "", str(value or ""))


__all__ = ["assign_clause_roles", "classify_clause_role"]
