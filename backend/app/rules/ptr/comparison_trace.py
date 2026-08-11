from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.finding import Finding
from app.domain.inspection_group import InspectionItemGroup
from app.domain.ptr import PTRClause, PTRDocument, PTRTable
from app.domain.ptr_comparison import (
    ClauseIdentityAlignment,
    PTRAtomicComparisonRow,
    PTRAtomicRequirement,
    PTRClauseStatement,
    PTRComparisonTrace,
    PTREffectiveRequirement,
    PTRReportRequirementMatch,
    PTRRequirementAlignment,
    PTRResultCompliance,
    PTRTechnicalEvidence,
    PTRTraceResultComparison,
)
from app.rules.ptr.clause_identity import gate_atomic_rows_by_clause_identity
from app.rules.ptr.report_item_grouping import (
    ptr_group_single_conclusion,
    ptr_group_standard_requirement,
    ptr_group_test_result,
    ptr_group_text,
)
from app.rules.ptr.requirement_classifier import clause_local_text


PASSING_TEXT_RE = re.compile(r"符合(?:要求)?")
NUMERIC_ACTUAL_RE = re.compile(r"[<>≤≥＜＞]?[+\-－＋−]?\d+(?:\.\d+)?")
CLAUSE_MARKER_RE = re.compile(r"(?<![\d.])2(?:\.\d+)+(?![\d.])")
LOAD_RE = re.compile(r"@\s*\d+(?:\.\d+)?\s*(?:Ω|Ω)", flags=re.IGNORECASE)


def build_comparison_trace(
    *,
    clause: PTRClause,
    ptr_doc: PTRDocument,
    report_matches: Sequence[InspectionItemGroup],
    atomic_requirements: Sequence[PTRAtomicRequirement],
    atomic_rows: Sequence[PTRAtomicComparisonRow],
    findings: Sequence[Finding],
    external_coverages: Sequence[dict[str, Any]],
    scope_modifiers: Sequence[dict[str, Any]] = (),
    clause_identity_alignment: ClauseIdentityAlignment | None = None,
) -> PTRComparisonTrace:
    statement = PTRClauseStatement(
        clause_id=str(clause.number),
        title=_clean_text(clause.title),
        local_text=clause_local_text(clause, include_title=False),
        page=clause.location.page_number if clause.location else None,
    )
    effective_requirements = _effective_requirements(clause, ptr_doc, atomic_requirements, statement)
    effective_requirements = _apply_only_scope_modifier(
        effective_requirements,
        report_matches,
        clause_number=str(clause.number),
        scope_modifiers=scope_modifiers,
    )
    identity_gated_rows = (
        gate_atomic_rows_by_clause_identity(atomic_rows, clause_identity_alignment)
        if clause_identity_alignment is not None
        else list(atomic_rows)
    )
    identity_blocks_binding = bool(
        clause_identity_alignment is not None
        and clause_identity_alignment.status in {"identity_mismatch", "ambiguous", "missing"}
    )
    annotated_rows = _annotated_active_rows(identity_gated_rows)
    annotated_rows = _rows_for_effective_requirements(annotated_rows, effective_requirements)
    report_requirement_matches = [] if identity_blocks_binding else _report_requirement_matches(
        clause,
        report_matches,
        annotated_rows,
        effective_requirements,
        external_coverages,
    )
    result_comparisons = [] if identity_blocks_binding else _result_comparisons(effective_requirements, annotated_rows)
    if not result_comparisons and not identity_blocks_binding:
        result_comparisons = _group_result_comparisons(
            effective_requirements,
            report_requirement_matches,
            report_matches,
        )
    if identity_blocks_binding:
        requirement_alignment = PTRRequirementAlignment(
            status="needs_review",
            reason="条款身份尚未确认，未执行 PTR 要求与报告标准要求的一致性判断。",
        )
        result_compliance = PTRResultCompliance(
            status="needs_review",
            reason="条款身份尚未确认，未使用报告结果进行符合性判断。",
        )
    elif clause.children_ids:
        requirement_alignment = PTRRequirementAlignment(
            status="not_applicable",
            reason="该条为父级分组，实际要求由已单独比对的子条款承载。",
        )
        result_compliance = PTRResultCompliance(
            status="not_applicable",
            reason="父级分组不重复汇总子条款结果。",
        )
    else:
        requirement_alignment = _requirement_alignment(effective_requirements, report_requirement_matches, external_coverages)
        result_compliance = _result_compliance(
            effective_requirements,
            result_comparisons,
            report_matches,
            external_coverages,
            all_atomic_rows_not_applicable=bool(atomic_rows) and all(row.status == "not_applicable" for row in atomic_rows),
        )
    technical_evidence = _technical_evidence(
        clause=clause,
        ptr_doc=ptr_doc,
        report_matches=report_matches,
        findings=findings,
        effective_requirements=effective_requirements,
        report_requirement_matches=report_requirement_matches,
    )
    return PTRComparisonTrace(
        ptr_clause_statement=statement,
        clause_identity_alignment=clause_identity_alignment,
        effective_requirements=effective_requirements,
        report_requirement_matches=report_requirement_matches,
        result_comparisons=result_comparisons,
        requirement_alignment=requirement_alignment,
        result_compliance=result_compliance,
        technical_evidence=technical_evidence,
    )


def _effective_requirements(
    clause: PTRClause,
    ptr_doc: PTRDocument,
    requirements: Sequence[PTRAtomicRequirement],
    statement: PTRClauseStatement,
) -> list[PTREffectiveRequirement]:
    result: list[PTREffectiveRequirement] = []
    for requirement in requirements:
        metadata = requirement.metadata if isinstance(requirement.metadata, dict) else {}
        if metadata.get("not_applicable_by_model") is True:
            continue
        model = _clean_text(metadata.get("model_column"))
        preset = _clean_text(metadata.get("preset"))
        condition = _clean_text(metadata.get("condition") or requirement.condition)
        load = _load_from_text(condition or requirement.label or requirement.expected_text)
        if load and condition == load:
            condition = None
        selected_column = model or preset or load or condition
        source_page = _requirement_source_page(requirement, clause, ptr_doc)
        evidence_ref = _ptr_requirement_evidence_ref(requirement, clause, ptr_doc)
        result.append(
            PTREffectiveRequirement(
                requirement_id=requirement.atomic_id,
                label=_clean_text(requirement.label) or str(clause.title or clause.number),
                source_type="table_row" if requirement.source == "ptr_table" else "clause_text",
                requirement_type=_requirement_type(requirement),
                parent_clause=_clean_text(metadata.get("parent_clause")),
                table_number=requirement.table_number,
                table_title=_clean_text(requirement.table_title),
                table_row_label=_clean_text(metadata.get("table_row_label")),
                model=model,
                preset=preset,
                load=load,
                condition=condition,
                selected_column=selected_column,
                expected=_clean_text(requirement.expected_text),
                operator=requirement.operator,
                expected_value=requirement.expected_value,
                unit=_normalize_unit(requirement.unit, requirement.expected_text),
                source_page=source_page,
                evidence_ref=evidence_ref,
            )
        )
    if result or not statement.local_text:
        return result
    return [
        PTREffectiveRequirement(
            requirement_id=f"{clause.number}:local_statement",
            label=_clean_text(clause.title) or f"条款 {clause.number}",
            source_type="clause_text",
            requirement_type="direct_text",
            expected=statement.local_text,
            source_page=statement.page,
            evidence_ref=f"ptr_clause:{clause.clause_id}",
        )
    ]


def _annotated_active_rows(
    rows: Sequence[PTRAtomicComparisonRow],
) -> list[tuple[PTRAtomicComparisonRow, str | None, str | None]]:
    result: list[tuple[PTRAtomicComparisonRow, str | None, str | None]] = []
    current_chamber: str | None = None
    for row in rows:
        if row.status == "not_applicable":
            continue
        source_text = row.source_text or ""
        chamber = _specific_chamber(source_text) or _specific_chamber(row.condition or "")
        if chamber:
            current_chamber = chamber
        load = _load_from_text(row.condition or source_text)
        result.append((row, chamber or (current_chamber if load else None), load))
    return result


def _report_requirement_matches(
    clause: PTRClause,
    report_matches: Sequence[InspectionItemGroup],
    rows: Sequence[tuple[PTRAtomicComparisonRow, str | None, str | None]],
    effective_requirements: Sequence[PTREffectiveRequirement],
    external_coverages: Sequence[dict[str, Any]],
) -> list[PTRReportRequirementMatch]:
    result: list[PTRReportRequirementMatch] = []
    seen: set[tuple[Any, ...]] = set()
    for row, chamber, load in rows:
        standard_requirement = _focused_requirement_text(row)
        if not standard_requirement:
            continue
        matching_requirements = [
            requirement
            for requirement in effective_requirements
            if row.atomic_id.startswith(requirement.requirement_id)
            or requirement.requirement_id.startswith(row.atomic_id)
        ]
        if matching_requirements and not any(
            _report_text_supports_requirement(requirement, standard_requirement)
            for requirement in matching_requirements
        ):
            continue
        report_clause = row.report_clause_number or row.clause_id
        evidence_ref = _report_evidence_ref(row.report_item_no, row.report_page, row.report_source_row)
        match = PTRReportRequirementMatch(
            report_item_no=row.report_item_no,
            report_clause=report_clause,
            row_label=_clean_text(row.table_row_label or row.label),
            condition=chamber or (None if load else _clean_text(row.condition)),
            model=_clean_text(row.model_column),
            load=load,
            preset=_clean_text(row.preset),
            standard_requirement_text=standard_requirement,
            page=row.report_page,
            source_row=row.report_source_row,
            evidence_ref=evidence_ref,
        )
        key = (
            match.report_item_no,
            match.report_clause,
            match.row_label,
            match.condition,
            match.model,
            match.load,
            match.standard_requirement_text,
        )
        if key not in seen:
            seen.add(key)
            result.append(match)

    result.extend(_missing_group_requirement_matches(clause, report_matches, effective_requirements, result))
    if not result:
        result.extend(_direct_group_requirement_matches(clause, report_matches, effective_requirements))
    for coverage in external_coverages:
        source_text = _clean_text(coverage.get("source_text"))
        if not source_text:
            continue
        result.append(
            PTRReportRequirementMatch(
                report_item_no=_coverage_item_span(coverage),
                report_clause=str(clause.number),
                row_label=_clean_text(coverage.get("standard")) or _clean_text(clause.title),
                standard_requirement_text=source_text,
                page=_int_or_none(coverage.get("source_page")),
                evidence_ref=f"report_scope:external:{str(clause.number)}",
            )
        )
    return _dedupe_report_requirements(result)


def _direct_group_requirement_matches(
    clause: PTRClause,
    report_matches: Sequence[InspectionItemGroup],
    effective_requirements: Sequence[PTREffectiveRequirement],
) -> list[PTRReportRequirementMatch]:
    result: list[PTRReportRequirementMatch] = []
    for group in report_matches:
        requirement = _clause_window(ptr_group_standard_requirement(group), str(clause.number))
        if not requirement:
            continue
        if effective_requirements and not any(
            _report_text_supports_requirement(effective_requirement, requirement)
            for effective_requirement in effective_requirements
        ):
            continue
        item_no = group.display_item_no or group.item_no
        page = group.pages[0] if group.pages else None
        result.append(
            PTRReportRequirementMatch(
                report_item_no=item_no,
                report_clause=str(clause.number),
                row_label=_clean_text(clause.title),
                standard_requirement_text=requirement,
                page=page,
                evidence_ref=_report_evidence_ref(item_no, page, None),
            )
        )
    return result


def _missing_group_requirement_matches(
    clause: PTRClause,
    report_matches: Sequence[InspectionItemGroup],
    requirements: Sequence[PTREffectiveRequirement],
    existing: Sequence[PTRReportRequirementMatch],
) -> list[PTRReportRequirementMatch]:
    result: list[PTRReportRequirementMatch] = []
    for requirement in requirements:
        current_candidates = [
            row
            for row in existing
            if _labels_compatible(requirement.label, row.row_label, row.standard_requirement_text)
        ]
        if any(_requirement_semantically_equivalent(requirement, row) for row in current_candidates) or _requirement_equivalent_across_rows(
            requirement,
            current_candidates,
        ):
            continue
        for group in report_matches:
            window = _semantic_label_window(ptr_group_standard_requirement(group), requirement.label)
            if not window:
                window = _semantic_label_window(ptr_group_standard_requirement(group), clause.title)
            if not window:
                continue
            item_no = group.display_item_no or group.item_no
            page = group.pages[0] if group.pages else None
            report_clause = _nearest_clause_number(ptr_group_standard_requirement(group), requirement.label) or str(clause.number)
            result.append(
                PTRReportRequirementMatch(
                    report_item_no=item_no,
                    report_clause=report_clause,
                    row_label=requirement.table_row_label or requirement.label,
                    condition=requirement.condition,
                    model=requirement.model,
                    load=requirement.load,
                    preset=requirement.preset,
                    standard_requirement_text=_focus_requirement_segment(window, requirement.label, requirement.expected),
                    page=page,
                    evidence_ref=_report_evidence_ref(item_no, page, None),
                )
            )
            break
    return result


def _result_comparisons(
    effective_requirements: Sequence[PTREffectiveRequirement],
    annotated_rows: Sequence[tuple[PTRAtomicComparisonRow, str | None, str | None]],
) -> list[PTRTraceResultComparison]:
    has_numeric_actual = any(_is_numeric_actual(row.actual) for row, _, _ in annotated_rows)
    result: list[PTRTraceResultComparison] = []
    for row, chamber, load in annotated_rows:
        if has_numeric_actual and row.model_column and _is_passing_text(row.actual):
            continue
        actual = _clean_text(row.actual)
        verification_basis = _verification_basis(actual, _row_is_numeric(row, effective_requirements))
        status = row.status
        reason = _clean_text(row.reason) or "报告结果需要复核。"
        if verification_basis == "pass_by_report_conclusion":
            status = "pass_by_report_conclusion"
            reason = "报告仅给出符合要求结论，未提供可用于数值验证的实测值。"
        result.append(
            PTRTraceResultComparison(
                comparison_id=row.atomic_id,
                label=_clean_text(row.label) or row.atomic_id,
                condition=chamber or (None if load else _clean_text(row.condition)),
                model=_clean_text(row.model_column),
                load=load,
                preset=_clean_text(row.preset),
                expected=_clean_text(row.expected),
                actual=actual,
                unit=_normalize_unit(row.unit or row.actual_unit or row.expected_unit, row.expected),
                status=status,
                reason=reason,
                verification_basis=verification_basis,
                page=row.report_page,
                item_no=row.report_item_no,
            )
        )
    return _dedupe_result_comparisons(result)


def _apply_only_scope_modifier(
    requirements: Sequence[PTREffectiveRequirement],
    report_matches: Sequence[InspectionItemGroup],
    *,
    clause_number: str,
    scope_modifiers: Sequence[dict[str, Any]],
) -> list[PTREffectiveRequirement]:
    only_values: list[str] = []
    for modifier in scope_modifiers:
        if str(modifier.get("clause") or "") != clause_number:
            continue
        values = modifier.get("only")
        if isinstance(values, list):
            only_values.extend(str(value).strip() for value in values if str(value).strip())
    group_text = " ".join(ptr_group_text(group) for group in report_matches)
    if not only_values:
        modifier = re.search(
            r"仅检\s*(?P<only>[A-Za-z][A-Za-z0-9_-]*(?:\s*[\u4e00-\u9fff]{1,8})?|[\u4e00-\u9fff]{1,12})",
            group_text,
            flags=re.IGNORECASE,
        )
        if modifier is not None:
            only_values.append(modifier.group("only"))
    if not only_values:
        return list(requirements)
    only_keys = [_semantic_label(value) for value in only_values if _semantic_label(value)]
    matched: list[PTREffectiveRequirement] = []
    for requirement in requirements:
        if not any(
            key in _semantic_label(requirement.label)
            or _semantic_label(requirement.label) in key
            or key in _semantic_label(requirement.expected)
            for key in only_keys
        ):
            continue
        focused_expected = _scope_requirement_segment(requirement.expected, only_values)
        label = " / ".join(dict.fromkeys(only_values))
        matched.append(
            requirement.model_copy(
                update={
                    "label": label,
                    "requirement_type": "functional",
                    "expected": focused_expected or requirement.expected,
                    "operator": "functional",
                }
            )
        )
    return matched or list(requirements)


def _scope_requirement_segment(value: str | None, aliases: Sequence[str]) -> str | None:
    text = str(value or "")
    starts = [text.lower().find(alias.lower()) for alias in aliases if alias and text.lower().find(alias.lower()) >= 0]
    if not starts:
        return _clean_text(text)
    start = min(starts)
    tail = text[start:]
    end = re.search(r"[。；;](?=\s*[A-Za-z\u4e00-\u9fff])", tail)
    return _clean_text(tail[: end.end() if end else len(tail)])


def _group_result_comparisons(
    requirements: Sequence[PTREffectiveRequirement],
    report_requirements: Sequence[PTRReportRequirementMatch],
    report_matches: Sequence[InspectionItemGroup],
) -> list[PTRTraceResultComparison]:
    if not requirements or not report_requirements:
        return []
    result: list[PTRTraceResultComparison] = []
    for requirement in requirements:
        candidates = [
            row
            for row in report_requirements
            if _labels_compatible(requirement.label, row.row_label, row.standard_requirement_text)
            or _expected_appears_in_report(requirement.expected, row.standard_requirement_text)
        ]
        if not candidates:
            continue
        group = next(
            (
                candidate_group
                for candidate_group in report_matches
                if (candidate_group.display_item_no or candidate_group.item_no) == candidates[0].report_item_no
            ),
            report_matches[0] if report_matches else None,
        )
        if group is None:
            continue
        actual = _clean_text(ptr_group_test_result(group))
        if not actual or actual in {"/", "——", "--"}:
            continue
        numeric = _is_numeric_requirement(requirement)
        verification_basis = _verification_basis(actual, numeric)
        status = "pass_by_report_conclusion" if verification_basis == "pass_by_report_conclusion" else "match"
        reason = (
            "报告仅给出符合要求结论，未提供可用于数值验证的实测值。"
            if status == "pass_by_report_conclusion"
            else "报告功能结果列给出符合要求，且对应标准要求与 PTR 语义一致。"
        )
        result.append(
            PTRTraceResultComparison(
                comparison_id=requirement.requirement_id,
                label=requirement.label,
                condition=requirement.condition,
                model=requirement.model,
                load=requirement.load,
                preset=requirement.preset,
                expected=requirement.expected,
                actual=actual,
                unit=requirement.unit,
                status=status,
                reason=reason,
                verification_basis=verification_basis,
                page=candidates[0].page,
                item_no=candidates[0].report_item_no,
            )
        )
    return result


def _rows_for_effective_requirements(
    rows: Sequence[tuple[PTRAtomicComparisonRow, str | None, str | None]],
    requirements: Sequence[PTREffectiveRequirement],
) -> list[tuple[PTRAtomicComparisonRow, str | None, str | None]]:
    if not requirements:
        return list(rows)
    requirement_ids = [requirement.requirement_id for requirement in requirements]
    matched = [entry for entry in rows if any(entry[0].atomic_id.startswith(requirement_id) for requirement_id in requirement_ids)]
    return matched or list(rows)


def _focused_requirement_text(row: PTRAtomicComparisonRow) -> str | None:
    text = _clean_text(row.source_text)
    if not text:
        return None
    label = _clean_text(row.table_row_label or row.label)
    expected = _clean_text(row.expected)
    if not label or not expected:
        return text
    return _focus_requirement_segment(text, label, expected)


def _requirement_alignment(
    requirements: Sequence[PTREffectiveRequirement],
    report_requirements: Sequence[PTRReportRequirementMatch],
    external_coverages: Sequence[dict[str, Any]],
) -> PTRRequirementAlignment:
    ptr_refs = [row.evidence_ref for row in requirements if row.evidence_ref]
    report_refs = [row.evidence_ref for row in report_requirements if row.evidence_ref]
    if not requirements:
        return PTRRequirementAlignment(
            status="needs_review",
            reason="未能稳定提取本条实际生效的 PTR 要求。",
            ptr_evidence_refs=ptr_refs,
            report_evidence_refs=report_refs,
        )
    standard_version_difference = _standard_version_difference(
        requirements,
        report_requirements,
        external_coverages,
    )
    if standard_version_difference is not None:
        ptr_standard, report_standard = standard_version_difference
        return PTRRequirementAlignment(
            status="needs_policy_review",
            reason=f"PTR 引用 {ptr_standard}，报告采用 {report_standard}；标准体系一致但年份版本不同，需按替代政策确认。",
            ptr_evidence_refs=ptr_refs,
            report_evidence_refs=report_refs,
        )
    if external_coverages and _external_coverages_pass(external_coverages):
        return PTRRequirementAlignment(
            status="equivalent",
            reason="PTR 外部标准要求与报告声明的检验范围及序号覆盖一致。",
            ptr_evidence_refs=ptr_refs,
            report_evidence_refs=report_refs,
        )
    if not report_requirements:
        return PTRRequirementAlignment(
            status="needs_review",
            reason="报告仅有检验项目覆盖，未定位到本条对应的标准要求行。",
            ptr_evidence_refs=ptr_refs,
            report_evidence_refs=report_refs,
        )

    unresolved: list[str] = []
    mismatched: list[str] = []
    for requirement in requirements:
        candidates = [
            row
            for row in report_requirements
            if _labels_compatible(requirement.label, row.row_label, row.standard_requirement_text)
            or _expected_appears_in_report(requirement.expected, row.standard_requirement_text)
        ]
        if not candidates:
            unresolved.append(requirement.label)
            continue
        if any(_requirement_semantically_equivalent(requirement, candidate) for candidate in candidates) or _requirement_equivalent_across_rows(
            requirement,
            candidates,
        ):
            continue
        if _has_clear_requirement_conflict(requirement, candidates):
            mismatched.append(requirement.label)
        else:
            unresolved.append(requirement.label)

    if mismatched:
        return PTRRequirementAlignment(
            status="mismatch",
            reason=f"报告标准要求与 PTR 的以下要求存在实质差异：{'、'.join(dict.fromkeys(mismatched))}。",
            ptr_evidence_refs=ptr_refs,
            report_evidence_refs=report_refs,
        )
    if unresolved:
        return PTRRequirementAlignment(
            status="needs_review",
            reason=f"以下 PTR 要求未找到足够精确的报告要求行：{'、'.join(dict.fromkeys(unresolved))}。",
            ptr_evidence_refs=ptr_refs,
            report_evidence_refs=report_refs,
        )
    return PTRRequirementAlignment(
        status="equivalent",
        reason="参数名称、适用条件、选定列、数值及允差与报告标准要求语义一致。",
        ptr_evidence_refs=ptr_refs,
        report_evidence_refs=report_refs,
    )


def _result_compliance(
    requirements: Sequence[PTREffectiveRequirement],
    comparisons: Sequence[PTRTraceResultComparison],
    report_matches: Sequence[InspectionItemGroup],
    external_coverages: Sequence[dict[str, Any]],
    *,
    all_atomic_rows_not_applicable: bool = False,
) -> PTRResultCompliance:
    if external_coverages and _external_coverages_pass(external_coverages):
        return PTRResultCompliance(status="match", reason="报告对应外部标准检验范围已覆盖且结论通过。")
    if not comparisons:
        if all_atomic_rows_not_applicable:
            return PTRResultCompliance(status="not_applicable", reason="本条报告结果均按适用范围标记为不适用。")
        reason = "报告存在项目级覆盖，但未绑定到本条可追溯的结果行。" if report_matches else "报告未返回本条对应结果。"
        return PTRResultCompliance(status="needs_review", reason=reason)
    if any(row.status == "mismatch" for row in comparisons):
        return PTRResultCompliance(status="mismatch", reason="至少一个报告实测结果明确不满足 PTR 要求。")
    conclusion_only_rows = [row for row in comparisons if row.status == "pass_by_report_conclusion"]
    if conclusion_only_rows and all(
        _report_conclusion_is_sufficient(requirement)
        for row in conclusion_only_rows
        for requirement in requirements
        if row.comparison_id.startswith(requirement.requirement_id)
    ):
        return PTRResultCompliance(
            status="match",
            reason="可编程设置列表与报告标准要求一致，报告结果及单项结论均为符合。",
        )
    if conclusion_only_rows:
        return PTRResultCompliance(
            status="needs_review",
            reason="数值型要求仅有报告符合结论，尚未完成实测值验证。",
        )
    if any(row.status in {"needs_review", "candidate_found_needs_mapping"} or row.actual is None for row in comparisons):
        return PTRResultCompliance(status="needs_review", reason="至少一个报告结果缺失或绑定不确定。")
    if all(row.status == "not_applicable" for row in comparisons):
        return PTRResultCompliance(status="not_applicable", reason="本条结果按适用范围判定为不适用。")
    if all(row.status in {"match", "not_applicable"} for row in comparisons):
        basis = "数值实测结果" if any(row.verification_basis == "numeric_verified" for row in comparisons) else "功能结果"
        return PTRResultCompliance(status="match", reason=f"全部{basis}均满足 PTR 要求。")
    return PTRResultCompliance(status="needs_review", reason="报告结果尚未形成完整、可追溯的符合性结论。")


def _technical_evidence(
    *,
    clause: PTRClause,
    ptr_doc: PTRDocument,
    report_matches: Sequence[InspectionItemGroup],
    findings: Sequence[Finding],
    effective_requirements: Sequence[PTREffectiveRequirement],
    report_requirement_matches: Sequence[PTRReportRequirementMatch],
) -> PTRTechnicalEvidence:
    selected_table_ids = {
        match.group("table_id")
        for row in effective_requirements
        if row.evidence_ref
        and (match := re.match(r"ptr_table:(?P<table_id>[^:]+):requirement:", row.evidence_ref)) is not None
    }
    tables = [table for table in ptr_doc.tables if table.table_id in selected_table_ids]
    if not tables and effective_requirements:
        table_numbers = {row.table_number for row in effective_requirements if row.table_number}
        table_titles = {_semantic_label(row.table_title) for row in effective_requirements if row.table_title}
        tables = [
            table
            for table in ptr_doc.tables
            if str(table.table_number or "") in table_numbers
            and (
                not table_titles
                or any(
                    title in _semantic_label(table.caption or table.title)
                    or _semantic_label(table.caption or table.title) in title
                    for title in table_titles
                )
            )
        ]
    report_groups = [
        {
            "item_no": group.display_item_no or group.item_no,
            "pages": list(group.pages),
            "standard_requirement": ptr_group_standard_requirement(group),
            "single_conclusion": ptr_group_single_conclusion(group),
            "full_text": ptr_group_text(group),
        }
        for group in report_matches
    ]
    refs = [row.evidence_ref for row in effective_requirements if row.evidence_ref]
    refs.extend(row.evidence_ref for row in report_requirement_matches if row.evidence_ref)
    return PTRTechnicalEvidence(
        ptr_full_text=_clean_text(clause.full_text or clause.text_content or clause.body_text),
        ptr_tables=[table.model_dump(mode="json") for table in tables],
        report_groups=report_groups,
        raw_finding_ids=[finding.id for finding in findings],
        evidence_refs=list(dict.fromkeys(refs)),
    )


def _requirement_semantically_equivalent(
    requirement: PTREffectiveRequirement,
    report_requirement: PTRReportRequirementMatch,
) -> bool:
    expected = _normalize_requirement_text(requirement.expected)
    report_text = _normalize_requirement_text(report_requirement.standard_requirement_text)
    if expected and expected in report_text:
        return True
    if requirement.operator in {"functional", "functional_or_equal"}:
        return _labels_compatible(requirement.label, report_requirement.row_label, report_requirement.standard_requirement_text)
    if requirement.requirement_type == "direct_text":
        expected_numbers = _numeric_tokens(requirement.expected)
        report_numbers = _numeric_tokens(report_requirement.standard_requirement_text)
        return _labels_compatible(requirement.label, report_requirement.row_label, report_requirement.standard_requirement_text) and (
            not expected_numbers or expected_numbers <= report_numbers
        )
    return False


def _has_clear_requirement_conflict(
    requirement: PTREffectiveRequirement,
    candidates: Sequence[PTRReportRequirementMatch],
) -> bool:
    if requirement.expected_value is None and requirement.operator not in {"<", "<=", ">", ">="}:
        return False
    expected_numbers = _numeric_tokens(requirement.expected)
    if not expected_numbers:
        return False
    if not any(_has_requirement_constraint_text(candidate.standard_requirement_text) for candidate in candidates):
        return False
    report_numbers: set[str] = set()
    for candidate in candidates:
        report_numbers.update(_numeric_tokens(candidate.standard_requirement_text))
    return bool(report_numbers and not expected_numbers <= report_numbers)


def _has_requirement_constraint_text(value: str | None) -> bool:
    return bool(re.search(r"不超过|不大于|不小于|不少于|允差|允许误差|[<>≤≥±]", str(value or "")))


def _requirement_equivalent_across_rows(
    requirement: PTREffectiveRequirement,
    candidates: Sequence[PTRReportRequirementMatch],
) -> bool:
    expected_numbers = _numeric_tokens(requirement.expected)
    if not expected_numbers:
        return False
    report_numbers: set[str] = set()
    combined_text = " ".join(candidate.standard_requirement_text for candidate in candidates)
    for candidate in candidates:
        report_numbers.update(_numeric_tokens(candidate.standard_requirement_text))
    if not expected_numbers <= report_numbers:
        return False
    expected_units = _unit_tokens(" ".join(value for value in (requirement.unit, requirement.expected) if value))
    report_units = _unit_tokens(combined_text)
    return not expected_units or not report_units or expected_units <= report_units


def _report_text_supports_requirement(
    requirement: PTREffectiveRequirement,
    report_text: str,
) -> bool:
    label_key = _semantic_label(requirement.label)
    report_key = _semantic_label(report_text)
    if len(label_key) > 1 and label_key in report_key:
        return True
    expected_key = _normalize_requirement_text(requirement.expected)
    if expected_key and expected_key in _normalize_requirement_text(report_text):
        return True
    expected_numbers = _numeric_tokens(requirement.expected)
    return bool(expected_numbers and expected_numbers <= _numeric_tokens(report_text))


def _expected_appears_in_report(expected: str | None, report_text: str | None) -> bool:
    expected_key = _normalize_requirement_text(expected)
    return bool(expected_key and expected_key in _normalize_requirement_text(report_text))


def _labels_compatible(label: str | None, row_label: str | None, report_text: str | None) -> bool:
    label_key = _semantic_label(label)
    if not label_key:
        return True
    row_key = _semantic_label(row_label)
    report_key = _semantic_label(report_text)
    return label_key in row_key or row_key in label_key or label_key in report_key


def _requirement_source_page(requirement: PTRAtomicRequirement, clause: PTRClause, ptr_doc: PTRDocument) -> int | None:
    if requirement.table_number:
        table = _table_for_requirement(requirement, clause, ptr_doc)
        if table is not None:
            return table.page or (table.page_span[0] if table.page_span else None)
    return clause.location.page_number if clause.location else None


def _ptr_requirement_evidence_ref(requirement: PTRAtomicRequirement, clause: PTRClause, ptr_doc: PTRDocument) -> str:
    if requirement.table_number:
        table = _table_for_requirement(requirement, clause, ptr_doc)
        table_id = table.table_id if table is not None else f"table-{requirement.table_number}"
        return f"ptr_table:{table_id}:requirement:{requirement.atomic_id}"
    return f"ptr_clause:{clause.clause_id}:requirement:{requirement.atomic_id}"


def _table_for_requirement(
    requirement: PTRAtomicRequirement,
    clause: PTRClause,
    ptr_doc: PTRDocument,
) -> PTRTable | None:
    candidates = [table for table in ptr_doc.tables if str(table.table_number or "") == str(requirement.table_number or "")]
    if len(candidates) <= 1:
        return candidates[0] if candidates else None
    metadata = requirement.metadata if isinstance(requirement.metadata, dict) else {}
    target_title = _semantic_label(requirement.table_title)
    target_parent = _clean_text(metadata.get("parent_clause"))
    related_clause_ids = {clause.clause_id}
    parent_number = clause.number.parent()
    while parent_number is not None:
        parent = ptr_doc.get_clause_by_number(parent_number)
        if parent is not None:
            related_clause_ids.add(parent.clause_id)
        parent_number = parent_number.parent()

    def score(table: PTRTable) -> int:
        value = 0
        table_title = _semantic_label(table.caption or table.title)
        if target_title and (target_title in table_title or table_title in target_title):
            value += 8
        table_parent = _clean_text(table.metadata.get("parent_clause"))
        if target_parent and table_parent == target_parent:
            value += 6
        elif table_parent == str(clause.number):
            value += 4
        if related_clause_ids.intersection(table.referenced_by_clause_ids):
            value += 3
        return value

    ranked = sorted(candidates, key=score, reverse=True)
    return ranked[0] if score(ranked[0]) > 0 else None


def _report_evidence_ref(item_no: str | None, page: int | None, source_row: int | None) -> str:
    parts = ["report_requirement", str(item_no or "unknown")]
    if page is not None:
        parts.append(f"p{page}")
    if source_row is not None:
        parts.append(f"r{source_row}")
    return ":".join(parts)


def _requirement_type(requirement: PTRAtomicRequirement) -> str:
    if requirement.source == "ptr_table":
        return "table_driven"
    if requirement.operator in {"functional", "functional_or_equal"}:
        return "functional"
    if requirement.operator or requirement.expected_value is not None:
        return "numeric"
    return "direct_text"


def _is_numeric_requirement(requirement: PTREffectiveRequirement) -> bool:
    if requirement.operator in {"functional", "functional_or_equal"}:
        return False
    if requirement.requirement_type == "numeric" or requirement.operator in {
        "<",
        "<=",
        ">",
        ">=",
        "deviation_within_tolerance",
    }:
        return True
    expected = str(requirement.expected or "")
    return bool(
        re.search(r"\d", expected)
        and (
            re.search(r"[<>≤≥±]|不超过|不小于|允差|误差", expected)
            or _unit_tokens(expected)
        )
    )


def _report_conclusion_is_sufficient(requirement: PTREffectiveRequirement) -> bool:
    expected = str(requirement.expected or "")
    return bool(
        requirement.requirement_type == "table_driven"
        and requirement.operator is None
        and requirement.expected_value is None
        and re.search(r"\d", expected)
        and not re.search(r"[<>≤≥±]|不超过|不小于|允差|误差|至少|最小|最大", expected)
    )


def _standard_version_difference(
    requirements: Sequence[PTREffectiveRequirement],
    report_requirements: Sequence[PTRReportRequirementMatch],
    external_coverages: Sequence[dict[str, Any]],
) -> tuple[str, str] | None:
    ptr_standards = _standard_references(" ".join(str(row.expected or "") for row in requirements))
    report_text = " ".join(row.standard_requirement_text for row in report_requirements)
    report_text += " " + " ".join(str(row.get("standard") or "") for row in external_coverages)
    report_standards = _standard_references(report_text)
    for ptr_family, ptr_year, ptr_display in ptr_standards:
        for report_family, report_year, report_display in report_standards:
            if ptr_family == report_family and ptr_year and report_year and ptr_year != report_year:
                return ptr_display, report_display
    return None


def _standard_references(value: str) -> list[tuple[str, str | None, str]]:
    normalized = unicodedata.normalize("NFKC", value or "").upper().replace("－", "-")
    pattern = re.compile(
        r"(?P<prefix>GB|YY/T|YY|IEC|ISO)\s*(?P<number>\d+(?:\.\d+)*)\s*(?:[-—]\s*(?P<year>20\d{2}))?",
        flags=re.IGNORECASE,
    )
    result: list[tuple[str, str | None, str]] = []
    for match in pattern.finditer(normalized):
        prefix = re.sub(r"\s+", "", match.group("prefix")).upper()
        number = match.group("number")
        year = match.group("year")
        family = f"{prefix}{number}"
        display = f"{prefix} {number}{f'-{year}' if year else ''}"
        result.append((family, year, display))
    return result


def _row_is_numeric(
    row: PTRAtomicComparisonRow,
    requirements: Sequence[PTREffectiveRequirement],
) -> bool:
    matching = [requirement for requirement in requirements if row.atomic_id.startswith(requirement.requirement_id)]
    if matching:
        return any(_is_numeric_requirement(requirement) for requirement in matching)
    return bool(re.search(r"±|[<>≤≥]|\d+(?:\.\d+)?\s*(?:μs|ms|ns|mV|V|A|Ω|%|min)", str(row.expected or "")))


def _verification_basis(actual: str | None, numeric_requirement: bool) -> str:
    if _is_numeric_actual(actual):
        return "numeric_verified"
    if _is_passing_text(actual):
        return "pass_by_report_conclusion" if numeric_requirement else "functional_conclusion"
    if actual in {"/", "——", "--"}:
        return "not_applicable"
    return "unbound"


def _normalize_unit(value: str | None, fallback_text: str | None = None) -> str | None:
    text = unicodedata.normalize("NFKC", str(value or "")).replace("µ", "μ").replace("Ω", "Ω")
    for source in (text, fallback_text):
        units = _unit_token_list(source)
        if units:
            return units[0]
    return _clean_text(text) or None


def _unit_tokens(value: str | None) -> set[str]:
    return set(_unit_token_list(value))


def _unit_token_list(value: str | None) -> list[str]:
    text = unicodedata.normalize("NFKC", str(value or "")).replace("µ", "μ").replace("Ω", "Ω")
    text = text.replace("毫米", "mm").replace("立方厘米", "cm3")
    matches: list[tuple[int, str]] = []
    pattern = re.compile(
        r"μg/g|EU/件|MΩ|kΩ|mJ|μs|mV|ms|ns|mm|cm\s*(?:3|³)|min\s*[⁻-]?\s*1|Ω|%",
        flags=re.IGNORECASE,
    )
    canonical = {
        "μg/g": "μg/g",
        "eu/件": "EU/件",
        "mω": "MΩ",
        "kω": "kΩ",
        "mj": "mJ",
        "μs": "μs",
        "mv": "mV",
        "ms": "ms",
        "ns": "ns",
        "mm": "mm",
        "cm3": "cm3",
        "min-1": "min⁻¹",
        "ω": "Ω",
        "%": "%",
    }
    for match in pattern.finditer(text):
        key = re.sub(r"\s+", "", match.group(0)).lower().replace("⁻", "-").replace("Ω", "ω")
        matches.append((match.start(), canonical.get(key, match.group(0))))
    for match in re.finditer(
        r"(?:\d(?:\.\d+)?\s*|单位\s*[:：]\s*)(?P<unit>[VAg])(?=$|[\s,，;；。/+\-])",
        text,
    ):
        matches.append((match.start("unit"), match.group("unit")))
    result: list[str] = []
    for _position, unit in sorted(matches):
        if unit not in result:
            result.append(unit)
    return result


def _specific_chamber(value: str | None) -> str | None:
    text = re.sub(r"\s+", "", str(value or ""))
    if not text:
        return None
    near_load = re.findall(r"(?:/|单位[:：]?[^@]{0,12})?(心房|心室)(?=@)", text)
    if near_load:
        return near_load[-1]
    if "心房和心室" in text or "心房或心室" in text:
        remainder = text.replace("心房和心室", "").replace("心房或心室", "")
        matches = re.findall(r"心房|心室", remainder)
        return matches[-1] if matches else None
    matches = re.findall(r"心房|心室", text)
    return matches[-1] if matches else None


def _load_from_text(value: str | None) -> str | None:
    matches = LOAD_RE.findall(str(value or ""))
    if not matches:
        return None
    return re.sub(r"\s+", "", matches[-1]).replace("Ω", "Ω")


def _is_numeric_actual(value: str | None) -> bool:
    return bool(value and NUMERIC_ACTUAL_RE.search(value) and not _is_passing_text(value))


def _is_passing_text(value: str | None) -> bool:
    text = str(value or "")
    return bool(PASSING_TEXT_RE.search(text) and "不符合" not in text)


def _normalize_requirement_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    replacements = {
        "µ": "μ",
        "Ω": "ω",
        "Ω": "ω",
        "不超过": "<=",
        "不大于": "<=",
        "≤": "<=",
        "不小于": ">=",
        "至少": ">=",
        "≥": ">=",
        "－": "-",
        "−": "-",
        "＋": "+",
        "～": "~",
        "至": "~",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"[^0-9a-z\u4e00-\u9fffμω<>+=~./%*-]+", "", text)


def _semantic_label(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"[（(][^）)]*(?:只适用|适用于)[^）)]*[）)]", "", text)
    text = re.sub(r"(?:心脏)?起搏器的", "", text)
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


def _numeric_tokens(value: str | None) -> set[str]:
    text = unicodedata.normalize("NFKC", str(value or ""))
    result: set[str] = set()
    for token in re.findall(r"\d+(?:\.\d+)?", text):
        try:
            normalized = format(Decimal(token).normalize(), "f")
        except InvalidOperation:
            normalized = token
        result.add(normalized)
    return result


def _clause_window(value: str | None, clause_number: str) -> str | None:
    text = str(value or "")
    marker = re.search(rf"(?<![\d.]){re.escape(clause_number)}(?![\d.])", text)
    if marker is None:
        markers = list(CLAUSE_MARKER_RE.finditer(text))
        return _clean_text(text) if len({item.group(0) for item in markers}) <= 1 else None
    next_marker = CLAUSE_MARKER_RE.search(text, marker.end())
    return _clean_text(text[marker.start() : next_marker.start() if next_marker else len(text)])


def _semantic_label_window(value: str | None, label: str | None) -> str | None:
    text = str(value or "")
    core_label = re.split(r"[（(]", str(label or ""), maxsplit=1)[0]
    core_label = re.sub(r"\s+|\*\d*$", "", core_label).strip(" /：:")
    if not core_label:
        return None
    pattern = re.compile(r"\s*".join(re.escape(char) for char in core_label), flags=re.IGNORECASE)
    marker = pattern.search(text)
    if marker is None:
        return None
    next_clause = CLAUSE_MARKER_RE.search(text, marker.end())
    return _clean_text(text[marker.start() : next_clause.start() if next_clause else len(text)])


def _nearest_clause_number(value: str | None, label: str | None) -> str | None:
    text = str(value or "")
    core_label = re.split(r"[（(]", str(label or ""), maxsplit=1)[0]
    core_label = re.sub(r"\s+|\*\d*$", "", core_label).strip(" /：:")
    if not core_label:
        return None
    pattern = re.compile(r"\s*".join(re.escape(char) for char in core_label), flags=re.IGNORECASE)
    marker = pattern.search(text)
    if marker is None:
        return None
    previous = [match.group(0) for match in CLAUSE_MARKER_RE.finditer(text[: marker.start()])]
    return previous[-1] if previous else None


def _focus_requirement_segment(text: str, label: str | None, expected: str | None) -> str:
    if not label or not expected:
        return text
    label_index = text.lower().find(label.lower())
    expected_index = text.lower().find(expected.lower(), max(label_index, 0))
    if label_index >= 0 and expected_index >= label_index and expected_index - label_index <= 600:
        return text[label_index : expected_index + len(expected)]
    return text


def _external_coverages_pass(coverages: Sequence[dict[str, Any]]) -> bool:
    return bool(coverages) and all(
        int(item.get("passed_count") or 0) > 0 or int(item.get("review_count") or 0) == 0
        for item in coverages
    )


def _coverage_item_span(coverage: dict[str, Any]) -> str | None:
    start = _clean_text(coverage.get("start_item_no"))
    end = _clean_text(coverage.get("end_item_no"))
    if start and end:
        return f"{start}～{end}"
    return start or end


def _dedupe_report_requirements(rows: Sequence[PTRReportRequirementMatch]) -> list[PTRReportRequirementMatch]:
    result: list[PTRReportRequirementMatch] = []
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        key = (
            row.report_item_no,
            row.report_clause,
            row.row_label,
            row.condition,
            row.model,
            row.load,
            row.standard_requirement_text,
        )
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def _dedupe_result_comparisons(rows: Sequence[PTRTraceResultComparison]) -> list[PTRTraceResultComparison]:
    result: list[PTRTraceResultComparison] = []
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        key = (row.label, row.condition, row.model, row.load, row.preset, row.expected, row.actual)
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


__all__ = ["build_comparison_trace"]
