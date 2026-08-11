from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.inspection_group import InspectionItemGroup
from app.domain.ptr import PTRClause
from app.domain.ptr_comparison import (
    ClauseIdentityAlignment,
    ClauseIdentityCandidate,
    PTRAtomicComparisonRow,
    PTRClauseIdentity,
    ReportClauseIdentity,
    ReportSubclauseIndex,
)
from app.rules.ptr.report_result_index import (
    build_report_result_row_index,
    extract_report_clause_marker,
    normalize_semantic_title,
)
from app.rules.ptr.requirement_classifier import clause_local_text


_ALIAS_REPLACEMENTS = (
    ("脉宽", "脉冲宽度"),
    ("av间期", "房室间期"),
    ("pvarp", "室后房不应期"),
    ("输入电阻", "输入阻抗"),
)
_UNIT_RE = re.compile(
    r"(?<![A-Za-z])(?:μg/g|ug/g|EU/件|kΩ|MΩ|Ω|μs|ms|ns|min⁻¹|min-1|mJ|mV|V|A|Hz|%)(?![A-Za-z])",
    flags=re.IGNORECASE,
)
_TABLE_REFERENCE_RE = re.compile(r"表\s*([0-9一二三四五六七八九十]+(?:[-－][0-9]+)?)")
_PAGE_CLAUSE_HEADER_RE = re.compile(r"^\s*(2(?:\.\d+)+)\s+(.+?)\s*$")


def build_ptr_clause_identity(
    clause: PTRClause,
    requirements: Sequence[Any] = (),
) -> PTRClauseIdentity:
    local_text = clause_local_text(clause, include_title=False)
    table_row_labels = _dedupe(
        _clean_text(getattr(requirement, "table_row_label", None))
        or _clean_text(_metadata(requirement).get("table_row_label"))
        or _clean_text(getattr(requirement, "label", None))
        for requirement in requirements
        if str(getattr(requirement, "source", "")) == "ptr_table"
    )
    title = _clean_text(clause.title)
    parameter_terms = _dedupe([title, *table_row_labels])
    units = _dedupe(
        [
            *(_clean_text(getattr(requirement, "unit", None)) for requirement in requirements),
            *(
                unit
                for requirement in requirements
                for unit in _extract_units(
                    _clean_text(getattr(requirement, "expected_text", None))
                    or _clean_text(getattr(requirement, "expected", None))
                )
            ),
            *_extract_units(local_text),
        ]
    )
    return PTRClauseIdentity(
        clause_id=clause.clause_id,
        clause_number=str(clause.number),
        title=title,
        normalized_title=normalize_identity_text(title),
        local_text=local_text,
        parent_clause=str(clause.parent_number) if clause.parent_number else _parent_clause(str(clause.number)),
        referenced_tables=_dedupe(clause.get_all_table_numbers()),
        table_row_labels=table_row_labels,
        parameter_terms=parameter_terms,
        units=units,
        source_page=clause.location.page_number if clause.location else None,
    )


def build_report_subclause_index(
    groups: Sequence[InspectionItemGroup],
    *,
    page_text_by_page: Mapping[int, str] | None = None,
) -> ReportSubclauseIndex:
    raw_identities: list[ReportClauseIdentity] = []
    diagnostics: list[dict[str, Any]] = []
    for group in groups:
        raw_identities.extend(_report_identities_from_group_rows(group))
        raw_identities.extend(
            _report_identities_from_page_headers(group, page_text_by_page or {})
        )
        row_index = build_report_result_row_index(group, page_text_by_page=page_text_by_page or {})
        item_no = group.display_item_no or group.item_no
        for row in row_index.rows:
            title = _clean_text(row.report_clause_title) or _short_parameter_label(row.table_row_label)
            normalized_title = normalize_identity_text(title)
            if not row.report_clause_number and not normalized_title:
                continue
            standard_requirement = _clean_text(row.standard_requirement) or ""
            row_label = _clean_text(row.table_row_label) or title
            source_page = row.source_page
            source_row = row.source_row
            evidence_ref = f"report_subclause:{item_no}:p{source_page or 'unknown'}:r{source_row if source_row is not None else 'unknown'}"
            raw_identities.append(
                ReportClauseIdentity(
                    identity_id=evidence_ref,
                    item_no=item_no,
                    group_id=f"inspection-item-{item_no}",
                    clause_number=row.report_clause_number,
                    title=title,
                    normalized_title=normalized_title,
                    standard_requirement_text=standard_requirement,
                    row_label=row_label,
                    parent_clause=_parent_clause(row.report_clause_number),
                    referenced_tables=_extract_table_references(standard_requirement),
                    parameter_terms=_dedupe(
                        [title, _short_parameter_label(row_label), standard_requirement]
                    ),
                    units=_extract_units(
                        " ".join(
                            value
                            for value in (standard_requirement, row_label)
                            if value
                        )
                    ),
                    test_result=_clean_text(row.test_result),
                    conclusion=_clean_text(row.conclusion),
                    source_page=source_page,
                    source_row=source_row,
                    evidence_refs=[evidence_ref],
                )
            )
        diagnostics.extend(
            {
                "item_no": item_no,
                "code": str(diagnostic.get("code") or diagnostic),
            }
            for diagnostic in group.diagnostics
        )
    return ReportSubclauseIndex(identities=_merge_report_identities(raw_identities), diagnostics=diagnostics)


def _report_identities_from_page_headers(
    group: InspectionItemGroup,
    page_text_by_page: Mapping[int, str],
) -> list[ReportClauseIdentity]:
    roots = _group_clause_roots(group)
    if not roots:
        return []
    item_no = group.display_item_no or group.item_no
    identities: list[ReportClauseIdentity] = []
    for page_number in group.pages:
        lines = str(page_text_by_page.get(page_number) or "").splitlines()
        for source_row, line in enumerate(lines):
            match = _PAGE_CLAUSE_HEADER_RE.match(re.sub(r"\s+", " ", line).strip())
            if match is None:
                continue
            clause_number = match.group(1)
            if not any(
                clause_number == root or clause_number.startswith(f"{root}.")
                for root in roots
            ):
                continue
            title = _short_parameter_label(match.group(2))
            if not title:
                continue
            evidence_ref = f"report_subclause:{item_no}:p{page_number}:r{source_row}"
            identities.append(
                ReportClauseIdentity(
                    identity_id=evidence_ref,
                    item_no=item_no,
                    group_id=f"inspection-item-{item_no}",
                    clause_number=clause_number,
                    title=title,
                    normalized_title=normalize_identity_text(title),
                    row_label=title,
                    parent_clause=_parent_clause(clause_number),
                    parameter_terms=[title],
                    source_page=page_number,
                    source_row=source_row,
                    evidence_refs=[evidence_ref],
                )
            )
    return identities


def _group_clause_roots(group: InspectionItemGroup) -> list[str]:
    roots: list[str] = []
    for row in group.rows:
        value = str(row.standard_clause or "").strip()
        if re.fullmatch(r"2(?:\.\d+)+", value):
            roots.append(value)
    if not roots:
        return []
    shallowest_level = min(len(root.split(".")) for root in roots)
    return _dedupe(root for root in roots if len(root.split(".")) == shallowest_level)


def _report_identities_from_group_rows(group: InspectionItemGroup) -> list[ReportClauseIdentity]:
    """Index report clause headers even when their result cell was not extracted."""

    identities: list[ReportClauseIdentity] = []
    item_no = group.display_item_no or group.item_no
    for row in group.rows:
        clause_number, title = _report_row_clause_marker(row)
        if not clause_number:
            continue
        standard_requirement = _clean_text(row.standard_requirement) or ""
        row_label = title or _short_parameter_label(row.item_name) or _short_parameter_label(standard_requirement)
        normalized_title = normalize_identity_text(title or row_label)
        if not normalized_title and clause_number == str(row.standard_clause or "").strip():
            continue
        source_page = row.source_page
        source_row = row.row_index_in_page
        evidence_ref = (
            f"report_subclause:{item_no}:p{source_page or 'unknown'}:"
            f"r{source_row if source_row is not None else 'unknown'}"
        )
        result_values = [_clean_text(value) for value in row.result_values]
        test_result = " / ".join(value for value in result_values if value) or _clean_text(row.test_result)
        source_text = " ".join(
            value
            for value in (
                _clean_text(row.sequence_raw),
                _clean_text(row.item_name),
                _clean_text(row.standard_clause),
                standard_requirement,
            )
            if value
        )
        identities.append(
            ReportClauseIdentity(
                identity_id=evidence_ref,
                item_no=item_no,
                group_id=f"inspection-item-{item_no}",
                clause_number=clause_number,
                title=title or row_label,
                normalized_title=normalized_title,
                standard_requirement_text=standard_requirement,
                row_label=row_label,
                parent_clause=_parent_clause(clause_number),
                referenced_tables=_extract_table_references(" ".join([standard_requirement, source_text])),
                parameter_terms=_dedupe([title, row_label, standard_requirement]),
                units=_extract_units(" ".join([standard_requirement, source_text])),
                test_result=test_result,
                conclusion=_clean_text(row.conclusion),
                source_page=source_page,
                source_row=source_row,
                evidence_refs=[evidence_ref],
            )
        )
    return identities


def _report_row_clause_marker(row: Any) -> tuple[str | None, str | None]:
    marker = extract_report_clause_marker(row)
    if marker is None:
        return None, None
    number, title = marker
    return number, _short_parameter_label(title)


def build_clause_identity_findings(
    clause: PTRClause,
    alignment: ClauseIdentityAlignment,
    *,
    task_id: str,
) -> list[Finding]:
    if alignment.status in {"exact_match", "not_applicable"}:
        return []
    code, message = _finding_code_and_message(clause, alignment)
    report_identity = alignment.selected_report_identity or _candidate_identity_for_evidence(alignment)
    evidence = [_ptr_clause_evidence(clause)]
    if report_identity is not None:
        evidence.append(_report_clause_evidence(report_identity, clause_number=str(clause.number)))
    missing_evidence: list[MissingEvidence] = []
    if report_identity is None and alignment.status == "missing":
        missing_evidence.append(
            MissingEvidence(
                label="报告语义子条款",
                reason="未找到与 PTR 条款名称、参数或表格行语义一致的报告子条款。",
                expected_source=SourceType.REPORT,
            )
        )
    return [
        Finding(
            id=f"{task_id}:PTR_CLAUSE_IDENTITY:{clause.number}:{alignment.status}",
            task_id=task_id,
            check_id="PTR_CLAUSE",
            severity=FindingSeverity.WARN,
            code=code,
            message=message,
            location=clause.location,
            expected={"clause_number": str(clause.number), "title": clause.title, "local_text": clause_local_text(clause, include_title=False)},
            actual=report_identity.model_dump(mode="json") if report_identity is not None else None,
            evidence=evidence,
            missing_evidence=missing_evidence,
            metadata={
                "clause_number": str(clause.number),
                "ptr_title": clause.title,
                "clause_identity_status": alignment.status,
                "selected_report_clause_number": alignment.selected_report_clause_number,
                "selected_report_title": alignment.selected_report_title,
                "item_no": report_identity.item_no if report_identity is not None else None,
                "table_number": (clause.get_all_table_numbers() or [None])[0],
                "table_numbers": clause.get_all_table_numbers(),
                "codex_required": True,
                "user_facing_status": "needs_review",
                "clause_identity_alignment": alignment.model_dump(mode="json"),
                "identity_conflict": alignment.status == "identity_mismatch",
                "reliable_semantic_candidate": alignment.selected_report_identity is not None,
            },
        )
    ]


def build_clause_sequence_offset_aggregation(
    clauses: Sequence[PTRClause],
    alignments: Mapping[str, ClauseIdentityAlignment | dict[str, Any]],
    *,
    task_id: str,
) -> tuple[Finding | None, list[dict[str, Any]]]:
    """Collapse consecutive semantic matches that differ only by a fixed number offset."""
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for clause in clauses:
        alignment = alignments.get(str(clause.number))
        if isinstance(alignment, dict):
            alignment = ClauseIdentityAlignment.model_validate(alignment)
        if alignment is None or alignment.status != "semantic_match_number_mismatch":
            continue
        report_number = alignment.selected_report_clause_number
        ptr_parts = _number_parts(str(clause.number))
        report_parts = _number_parts(report_number)
        if not ptr_parts or not report_parts or len(ptr_parts) != len(report_parts):
            continue
        if ptr_parts[:-1] != report_parts[:-1]:
            continue
        offset = report_parts[-1] - ptr_parts[-1]
        if offset == 0:
            continue
        selected = alignment.selected_report_identity
        grouped.setdefault((".".join(str(part) for part in ptr_parts[:-1]), offset), []).append(
            {
                "ptr": str(clause.number),
                "report": report_number,
                "title": clause.title,
                "report_title": alignment.selected_report_title,
                "report_item_no": alignment.selected_report_item_no,
                "report_page": alignment.selected_report_page,
                "confidence": alignment.confidence,
                "_ptr_last": ptr_parts[-1],
                "_report_identity": selected,
                "_clause": clause,
            }
        )

    groups: list[dict[str, Any]] = []
    for (parent, offset), entries in grouped.items():
        entries.sort(key=lambda entry: entry["_ptr_last"])
        if len(entries) < 2 or not _consecutive(entries):
            continue
        # A stable three-or-more-clause fixed offset is stronger evidence than
        # any single title match, even when one individual alignment is medium.
        confidence = "high" if len(entries) >= 3 or all(entry["confidence"] == "high" for entry in entries) else "medium"
        groups.append(
            {
                "parent_clause": parent,
                "offset": offset,
                "confidence": confidence,
                "affected_clauses": [
                    {
                        key: value
                        for key, value in entry.items()
                        if key in {"ptr", "report", "title", "report_title", "report_item_no", "report_page"}
                    }
                    for entry in entries
                ],
            }
        )

    if not groups:
        return None, []

    group = max(groups, key=lambda item: len(item["affected_clauses"]))
    evidence: list[Evidence] = []
    for entry in group["affected_clauses"]:
        clause = next((clause for clause in clauses if str(clause.number) == entry["ptr"]), None)
        if clause is not None:
            evidence.append(_ptr_clause_evidence(clause))
        report_identity = next(
            (
                alignment.selected_report_identity
                for clause_number, alignment in alignments.items()
                if clause_number == entry["ptr"]
                and isinstance(alignment, ClauseIdentityAlignment)
                and alignment.selected_report_identity is not None
            ),
            None,
        )
        if report_identity is not None:
            evidence.append(_report_clause_evidence(report_identity, clause_number=entry["ptr"]))

    aggregate_id = f"{task_id}:PTR_CLAUSE_SEQUENCE_OFFSET:{group['parent_clause']}:{group['offset']}"
    finding = Finding(
        id=aggregate_id,
        task_id=task_id,
        check_id="PTR_CLAUSE",
        severity=FindingSeverity.WARN,
        code="PTR_CLAUSE_SEQUENCE_OFFSET",
        message=(
            f"报告 {group['parent_clause']} 章节存在条款编号整体偏移："
            f"报告条款相对 PTR 前移 {abs(group['offset'])} 位。"
        ),
        location=next(
            (clause.location for clause in clauses if str(clause.number) == group["affected_clauses"][0]["ptr"]),
            None,
        ),
        expected={"parent_clause": group["parent_clause"], "offset": 0},
        actual={"parent_clause": group["parent_clause"], "offset": group["offset"]},
        evidence=evidence,
        confidence=Confidence.HIGH if group["confidence"] == "high" else Confidence.MEDIUM,
        metadata={
            "clause_number": group["parent_clause"],
            "aggregate_id": aggregate_id,
            "is_aggregate_finding": True,
            "affected_clauses": group["affected_clauses"],
            "offset": group["offset"],
            "confidence": group["confidence"],
            "codex_required": False,
            "final_status": "confirmed_document_issue",
            "user_facing_status": "confirmed_document_issue",
            "document_issue": True,
        },
    )
    group["aggregate_id"] = aggregate_id
    return finding, groups


def mark_sequence_offset_children(
    findings: Sequence[Finding],
    groups: Sequence[dict[str, Any]],
) -> None:
    """Keep raw number-mismatch findings traceable without counting them twice."""
    affected: dict[str, dict[str, Any]] = {}
    for group in groups:
        aggregate_id = str(group.get("aggregate_id") or "")
        for entry in group.get("affected_clauses") or []:
            clause_number = str(entry.get("ptr") or "")
            if clause_number and aggregate_id:
                affected[clause_number] = {
                    "aggregate_id": aggregate_id,
                    "offset": group.get("offset"),
                    "parent_clause": group.get("parent_clause"),
                }
    for finding in findings:
        clause_number = str(finding.metadata.get("clause_number") or "")
        if finding.code != "PTR_REPORT_CLAUSE_NUMBER_MISMATCH" or clause_number not in affected:
            continue
        finding.metadata.update(
            {
                "aggregate_child": True,
                "aggregated_into": affected[clause_number]["aggregate_id"],
                "sequence_offset": affected[clause_number]["offset"],
                "sequence_offset_parent": affected[clause_number]["parent_clause"],
            }
        )


def _number_parts(value: str | None) -> tuple[int, ...]:
    parts = str(value or "").split(".")
    if not parts or any(not part.isdigit() for part in parts):
        return tuple()
    return tuple(int(part) for part in parts)


def _consecutive(entries: Sequence[dict[str, Any]]) -> bool:
    return all(
        right["_ptr_last"] == left["_ptr_last"] + 1
        for left, right in zip(entries, entries[1:], strict=False)
    )


def align_clause_identity(
    ptr_identity: PTRClauseIdentity,
    report_index: ReportSubclauseIndex,
) -> ClauseIdentityAlignment:
    candidates = [
        _score_candidate(ptr_identity, report_identity)
        for report_identity in report_index.identities
        if _candidate_relevant(ptr_identity, report_identity)
    ]
    candidates.sort(key=lambda candidate: (-candidate.score, candidate.report_identity_id))
    identities_by_id = {identity.identity_id: identity for identity in report_index.identities}
    valid = [candidate for candidate in candidates if candidate.rejected_reason is None and _has_semantic_support(candidate)]
    exact_conflicts = [
        candidate
        for candidate in candidates
        if candidate.number_relation == "exact" and candidate.rejected_reason == "exact_number_semantic_conflict"
    ]

    if not valid:
        if exact_conflicts:
            conflict = exact_conflicts[0]
            return _alignment(
                ptr_identity,
                status="identity_mismatch",
                reason=(
                    f"PTR 条款 {ptr_identity.clause_number} 为“{ptr_identity.title or '未命名'}”，"
                    f"报告同编号条款为“{conflict.report_title or '未命名'}”，条款身份不一致。"
                ),
                candidates=candidates,
                confidence="high",
            )
        return _alignment(
            ptr_identity,
            status="missing",
            reason="报告中未找到与本条 PTR 参数或功能语义一致的子条款。",
            candidates=candidates,
        )

    top_score = valid[0].score
    tied = [candidate for candidate in valid if top_score - candidate.score <= 5]
    if len(tied) > 1 and not _same_logical_report_clause(tied, identities_by_id):
        return _alignment(
            ptr_identity,
            status="ambiguous",
            reason="存在多个强度相近的报告语义候选，无法唯一绑定。",
            candidates=candidates,
            confidence="low",
        )

    selected_candidate = max(
        tied,
        key=lambda candidate: (
            candidate.score,
            len(
                normalize_identity_text(
                    identities_by_id[candidate.report_identity_id].title
                )
            ),
        ),
    )
    selected = identities_by_id[selected_candidate.report_identity_id]
    if selected_candidate.number_relation == "exact":
        return _alignment(
            ptr_identity,
            status="exact_match",
            reason="PTR 与报告子条款的编号、名称和参数语义一致。",
            candidates=candidates,
            selected=selected,
            selected_candidate=selected_candidate,
            confidence=_candidate_confidence(selected_candidate),
        )
    return _alignment(
        ptr_identity,
        status="semantic_match_number_mismatch",
        reason=(
            f"条款名称和参数语义一致，但 PTR 编号为 {ptr_identity.clause_number}，"
            f"报告编号为 {selected.clause_number or '未标注'}。"
        ),
        candidates=candidates,
        selected=selected,
        selected_candidate=selected_candidate,
        confidence=_candidate_confidence(selected_candidate),
    )


def gate_atomic_rows_by_clause_identity(
    rows: Sequence[PTRAtomicComparisonRow],
    alignment: ClauseIdentityAlignment,
) -> list[PTRAtomicComparisonRow]:
    blocked_statuses = {"identity_mismatch", "ambiguous", "missing"}
    if alignment.status in blocked_statuses:
        return [_clear_atomic_binding(row, "条款身份未确认，不能使用报告结果作为本条覆盖证据。") for row in rows]

    selected_number = alignment.selected_report_clause_number
    if not selected_number:
        return list(rows)
    result: list[PTRAtomicComparisonRow] = []
    for row in rows:
        report_number = str(row.report_clause_number or "").strip()
        if report_number and report_number != selected_number:
            result.append(_clear_atomic_binding(row, "报告结果来自非选中报告子条款，已拒绝绑定。"))
            continue
        if (
            alignment.status == "semantic_match_number_mismatch"
            and not report_number
            and row.actual
            and not _row_matches_selected_identity(row, alignment.selected_report_identity)
        ):
            result.append(_clear_atomic_binding(row, "报告结果缺少子条款编号，无法证明来自选中的语义条款。"))
            continue
        result.append(row)
    return result


def _row_matches_selected_identity(
    row: PTRAtomicComparisonRow,
    selected: ReportClauseIdentity | None,
) -> bool:
    if selected is None:
        return False
    row_terms = _dedupe([row.label, row.table_row_label, row.condition])
    selected_terms = _dedupe(
        [
            selected.title,
            selected.row_label,
            *selected.parameter_terms,
            selected.standard_requirement_text,
        ]
    )
    for row_term in row_terms:
        normalized_row = normalize_identity_text(row_term)
        if not normalized_row:
            continue
        for selected_term in selected_terms:
            normalized_selected = normalize_identity_text(selected_term)
            if normalized_selected and (
                normalized_row in normalized_selected or normalized_selected in normalized_row
            ):
                return True
    return False


def normalize_identity_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = re.sub(r"[（(][^）)]*(?:只适用|适用于)[^）)]*[）)]", "", text)
    text = re.sub(r"(?:心脏)?起搏器的", "", text)
    text = re.sub(r"产品物理特性及参数", "物理特性", text)
    for source, target in _ALIAS_REPLACEMENTS:
        text = text.replace(source, target)
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def _candidate_relevant(ptr: PTRClauseIdentity, report: ReportClauseIdentity) -> bool:
    if report.clause_number == ptr.clause_number:
        return True
    if ptr.parent_clause and report.parent_clause == ptr.parent_clause:
        return True
    ptr_title = normalize_identity_text(ptr.normalized_title or ptr.title)
    report_values = _dedupe(
        [
            report.normalized_title or report.title,
            report.row_label,
            *report.parameter_terms,
            report.standard_requirement_text,
        ]
    )
    return bool(
        ptr_title
        and any(
            (report_text := normalize_identity_text(value))
            and (ptr_title in report_text or report_text in ptr_title)
            for value in report_values
        )
    )


def _score_candidate(ptr: PTRClauseIdentity, report: ReportClauseIdentity) -> ClauseIdentityCandidate:
    number_relation = _number_relation(ptr, report)
    title_relation = _text_relation([ptr.normalized_title or ptr.title], [report.normalized_title or report.title])
    table_row_relation = _text_relation(ptr.table_row_labels, [report.row_label])
    parameter_relation = _text_relation(ptr.parameter_terms, report.parameter_terms)
    parent_relation = "same" if ptr.parent_clause and ptr.parent_clause == report.parent_clause else "different"
    positive: list[str] = []
    negative: list[str] = []
    score = 0

    score += _relation_score(title_relation, exact=100, alias=90, similar=60, positive=positive, name="title")
    score += _relation_score(table_row_relation, exact=90, alias=80, similar=55, positive=positive, name="table_row")
    score += _relation_score(parameter_relation, exact=80, alias=70, similar=45, positive=positive, name="parameter")
    if set(ptr.referenced_tables) & set(report.referenced_tables):
        score += 50
        positive.append("referenced_table_match")
    if number_relation == "exact":
        score += 30
        positive.append("exact_clause_number")
    if parent_relation == "same":
        score += 15
        positive.append("same_parent_clause")
    if _units_compatible(ptr.units, report.units):
        score += 10
        if ptr.units and report.units:
            positive.append("compatible_units")
    elif ptr.units and report.units:
        score -= 40
        negative.append("incompatible_units")

    rejected_reason: str | None = None
    if number_relation == "exact" and title_relation == "conflict" and parameter_relation == "conflict":
        score -= 200
        negative.extend(["title_conflict", "parameter_conflict"])
        rejected_reason = "exact_number_semantic_conflict"
    elif table_row_relation == "conflict":
        negative.append("table_row_conflict")

    return ClauseIdentityCandidate(
        report_identity_id=report.identity_id,
        ptr_clause_number=ptr.clause_number,
        report_clause_number=report.clause_number,
        report_item_no=report.item_no,
        report_title=report.title,
        report_page=report.source_page,
        report_source_row=report.source_row,
        number_relation=number_relation,
        title_relation=title_relation,
        table_row_relation=table_row_relation,
        parameter_relation=parameter_relation,
        parent_relation=parent_relation,
        score=score,
        positive_signals=positive,
        negative_signals=negative,
        rejected_reason=rejected_reason,
    )


def _number_relation(ptr: PTRClauseIdentity, report: ReportClauseIdentity) -> str:
    if not report.clause_number:
        return "missing"
    if report.clause_number == ptr.clause_number:
        return "exact"
    if report.clause_number == ptr.parent_clause:
        return "parent_only"
    return "different"


def _text_relation(left_values: Sequence[str | None], right_values: Sequence[str | None]) -> str:
    left = {normalize_identity_text(value) for value in left_values if normalize_identity_text(value)}
    right = {normalize_identity_text(value) for value in right_values if normalize_identity_text(value)}
    if not left or not right:
        return "missing"
    if left & right:
        return "exact"
    if any(left_value in right_value or right_value in left_value for left_value in left for right_value in right):
        return "similar"
    return "conflict"


def _relation_score(
    relation: str,
    *,
    exact: int,
    alias: int,
    similar: int,
    positive: list[str],
    name: str,
) -> int:
    values = {"exact": exact, "alias": alias, "similar": similar}
    if relation in values:
        positive.append(f"{name}_{relation}")
    return values.get(relation, 0)


def _has_semantic_support(candidate: ClauseIdentityCandidate) -> bool:
    return any(
        relation in {"exact", "alias", "similar"}
        for relation in (candidate.title_relation, candidate.table_row_relation, candidate.parameter_relation)
    )


def _same_logical_report_clause(
    candidates: Sequence[ClauseIdentityCandidate],
    identities_by_id: Mapping[str, ReportClauseIdentity],
) -> bool:
    identities = [identities_by_id[candidate.report_identity_id] for candidate in candidates]
    logical_keys = {
        (identity.group_id, identity.item_no, identity.clause_number)
        for identity in identities
    }
    if len(logical_keys) != 1 or identities[0].clause_number is None:
        return False

    normalized_titles = {
        normalize_identity_text(identity.title or identity.row_label)
        for identity in identities
        if normalize_identity_text(identity.title or identity.row_label)
    }
    if not normalized_titles:
        return False
    longest = max(normalized_titles, key=len)
    return all(title in longest for title in normalized_titles)


def _units_compatible(ptr_units: Sequence[str], report_units: Sequence[str]) -> bool:
    if not ptr_units or not report_units:
        return True
    ptr = {_normalize_unit(unit) for unit in ptr_units}
    report = {_normalize_unit(unit) for unit in report_units}
    return bool(ptr & report)


def _normalize_unit(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).replace("µ", "μ").replace("Ω", "Ω").casefold()


def _candidate_confidence(candidate: ClauseIdentityCandidate) -> str:
    if candidate.title_relation == "exact" and candidate.parameter_relation in {"exact", "similar"}:
        return "high"
    if candidate.score >= 150:
        return "medium"
    return "low"


def _alignment(
    ptr: PTRClauseIdentity,
    *,
    status: str,
    reason: str,
    candidates: list[ClauseIdentityCandidate],
    selected: ReportClauseIdentity | None = None,
    selected_candidate: ClauseIdentityCandidate | None = None,
    confidence: str = "low",
) -> ClauseIdentityAlignment:
    return ClauseIdentityAlignment(
        status=status,
        ptr_clause_number=ptr.clause_number,
        ptr_title=ptr.title,
        selected_report_clause_number=selected.clause_number if selected else None,
        selected_report_title=selected.title if selected else None,
        selected_report_item_no=selected.item_no if selected else None,
        selected_report_page=selected.source_page if selected else None,
        selected_report_source_row=selected.source_row if selected else None,
        selected_report_identity=selected,
        number_matches=bool(selected and selected.clause_number == ptr.clause_number),
        title_matches=bool(selected_candidate and selected_candidate.title_relation in {"exact", "alias", "similar"}),
        parameter_matches=bool(selected_candidate and selected_candidate.parameter_relation in {"exact", "alias", "similar"}),
        table_row_matches=bool(selected_candidate and selected_candidate.table_row_relation in {"exact", "alias", "similar"}),
        confidence=confidence,
        reason=reason,
        candidate_count=len(candidates),
        candidates=candidates,
    )


def _clear_atomic_binding(row: PTRAtomicComparisonRow, reason: str) -> PTRAtomicComparisonRow:
    return row.model_copy(
        update={
            "actual": None,
            "actual_operator": None,
            "actual_value": None,
            "actual_unit": None,
            "report_conclusion": None,
            "candidate_actuals": [],
            "status": "needs_review",
            "reason": reason,
            "report_page": None,
            "report_item_no": None,
            "report_clause_number": None,
            "report_source_row": None,
        }
    )


def _merge_report_identities(identities: Sequence[ReportClauseIdentity]) -> list[ReportClauseIdentity]:
    grouped: dict[tuple[str | None, str | None, str], list[ReportClauseIdentity]] = {}
    order: list[tuple[str | None, str | None, str]] = []
    for identity in identities:
        key = (identity.item_no, identity.clause_number, identity.normalized_title or "")
        if key not in grouped:
            order.append(key)
        grouped.setdefault(key, []).append(identity)

    result: list[ReportClauseIdentity] = []
    for key in order:
        values = grouped[key]
        first = values[0]
        result.append(
            first.model_copy(
                update={
                    "identity_id": f"report_subclause:{first.item_no}:{first.clause_number or 'unknown'}:{first.normalized_title or 'untitled'}",
                    "standard_requirement_text": " / ".join(
                        _dedupe(value.standard_requirement_text for value in values)
                    ),
                    "row_label": " / ".join(_dedupe(value.row_label for value in values)),
                    "referenced_tables": _dedupe(
                        table for value in values for table in value.referenced_tables
                    ),
                    "parameter_terms": _dedupe(
                        term for value in values for term in value.parameter_terms
                    ),
                    "units": _dedupe(unit for value in values for unit in value.units),
                    "test_result": _join_or_none(value.test_result for value in values),
                    "conclusion": _join_or_none(value.conclusion for value in values),
                    "evidence_refs": _dedupe(
                        evidence_ref for value in values for evidence_ref in value.evidence_refs
                    ),
                }
            )
        )
    return result


def _finding_code_and_message(clause: PTRClause, alignment: ClauseIdentityAlignment) -> tuple[str, str]:
    clause_number = str(clause.number)
    title = clause.title or "未命名条款"
    if alignment.status == "semantic_match_number_mismatch":
        return (
            "PTR_REPORT_CLAUSE_NUMBER_MISMATCH",
            f"PTR 条款“{title}”编号为 {clause_number}，报告对应条款编号为 "
            f"{alignment.selected_report_clause_number or '未标注'}；内容可能对应，但条款编号不一致，需复核。",
        )
    if alignment.status == "identity_mismatch":
        exact = next(
            (
                candidate
                for candidate in alignment.candidates
                if candidate.number_relation == "exact" and candidate.rejected_reason
            ),
            None,
        )
        report_title = exact.report_title if exact is not None else alignment.selected_report_title
        return (
            "PTR_CLAUSE_IDENTITY_MISMATCH",
            f"PTR 条款 {clause_number} 为“{title}”，报告同编号条款为“{report_title or '未命名'}”，"
            "条款身份不一致，不能使用该报告条款作为覆盖证据。",
        )
    if alignment.status == "ambiguous":
        return (
            "PTR_CLAUSE_IDENTITY_AMBIGUOUS",
            f"PTR 条款 {clause_number}“{title}”存在多个语义相近的报告候选，无法唯一绑定。",
        )
    return (
        "PTR_CLAUSE_MISSING",
        f"报告中未找到与 PTR 条款 {clause_number}“{title}”语义一致的子条款。",
    )


def _candidate_identity_for_evidence(alignment: ClauseIdentityAlignment) -> ReportClauseIdentity | None:
    if not alignment.candidates:
        return None
    candidate = next(
        (
            item
            for item in alignment.candidates
            if item.number_relation == "exact" and item.rejected_reason is not None
        ),
        alignment.candidates[0],
    )
    return ReportClauseIdentity(
        identity_id=candidate.report_identity_id,
        item_no=candidate.report_item_no,
        group_id=f"inspection-item-{candidate.report_item_no or 'unknown'}",
        clause_number=candidate.report_clause_number,
        title=candidate.report_title,
        normalized_title=normalize_identity_text(candidate.report_title),
        source_page=candidate.report_page,
        source_row=candidate.report_source_row,
    )


def _ptr_clause_evidence(clause: PTRClause) -> Evidence:
    local_text = clause_local_text(clause, include_title=False)
    return Evidence(
        id=f"ptr-clause-identity-{clause.number}",
        source_type=SourceType.PTR,
        location=clause.location,
        raw_text=local_text,
        normalized_text=normalize_identity_text(local_text),
        method=EvidenceMethod.PDF_TEXT,
    )


def _report_clause_evidence(identity: ReportClauseIdentity, *, clause_number: str) -> Evidence:
    return Evidence(
        id=f"report-clause-identity-{clause_number}-{identity.identity_id}",
        source_type=SourceType.REPORT,
        location=Location(
            source_type=SourceType.REPORT,
            page_number=identity.source_page,
            row_index=identity.source_row,
        ),
        raw_text=" ".join(
            value
            for value in (identity.clause_number, identity.title, identity.standard_requirement_text, identity.test_result)
            if value
        ),
        normalized_text=normalize_identity_text(
            " ".join(value for value in (identity.title, identity.standard_requirement_text) if value)
        ),
        method=EvidenceMethod.PDF_TEXT,
    )


def _metadata(value: Any) -> dict[str, Any]:
    metadata = getattr(value, "metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def _parent_clause(value: str | None) -> str | None:
    parts = str(value or "").split(".")
    return ".".join(parts[:-1]) if len(parts) > 1 else None


def _extract_table_references(value: str | None) -> list[str]:
    return _dedupe(match.group(1).replace("－", "-") for match in _TABLE_REFERENCE_RE.finditer(str(value or "")))


def _extract_units(value: str | None) -> list[str]:
    return _dedupe(_display_unit(match.group(0)) for match in _UNIT_RE.finditer(str(value or "")))


def _display_unit(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).replace("µ", "μ").replace("Ω", "Ω")
    if normalized.casefold() == "ug/g":
        return "μg/g"
    return normalized


def _short_parameter_label(value: str | None) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    text = re.sub(r"^2(?:\.\d+)+\s*", "", text)
    text = re.split(r"应符合|的数值|允许误差|允差|单位[:：]|[；;。\n]", text, maxsplit=1)[0]
    text = re.sub(r"[（(].*$", "", text).strip(" ：:，,")
    return text or None


def _clean_text(value: Any) -> str | None:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or None


def _dedupe(values: Sequence[Any] | Any) -> list[str]:
    result: list[str] = []
    for value in values:
        text = _clean_text(value)
        if text and text not in result:
            result.append(text)
    return result


def _join_or_none(values: Sequence[Any] | Any) -> str | None:
    joined = " / ".join(_dedupe(values))
    return joined or None


__all__ = [
    "align_clause_identity",
    "build_clause_sequence_offset_aggregation",
    "build_clause_identity_findings",
    "build_ptr_clause_identity",
    "build_report_subclause_index",
    "gate_atomic_rows_by_clause_identity",
    "mark_sequence_offset_children",
    "normalize_identity_text",
]
