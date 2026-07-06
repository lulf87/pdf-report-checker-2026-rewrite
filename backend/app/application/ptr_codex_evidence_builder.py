from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

from pydantic import BaseModel

from app.application.codex_audit_targeting import (
    CodexAuditTargetSelection,
    DEFAULT_CODEX_AUDIT_MAX_TARGETS,
    DEFAULT_PTR_PRIORITY_FINDING_CODES,
    priority_index,
)
from app.application.report_page_texts import report_page_text_by_page
from app.domain.codex_review import (
    CodexEvidenceRef,
    CodexReviewRequest,
    CodexReviewTarget,
    CodexReviewTargetType,
)
from app.domain.evidence_package import (
    EvidenceItem,
    EvidencePackage,
    EvidencePackageKind,
    EvidenceSourceType,
    EvidenceTarget,
)
from app.domain.finding import Finding
from app.domain.inspection_group import InspectionItemGroup
from app.domain.ptr import PTRClause, PTRDocument, PTRTable
from app.domain.report import InspectionItem, ReportDocument
from app.domain.report_scope import ReportInspectionScope
from app.domain.result import CheckResult
from app.domain.table import CanonicalTable, ParameterRecord
from app.rules.ptr.report_item_grouping import (
    build_ptr_report_item_groups,
    ptr_group_compact_rows,
    ptr_group_for_clause,
    ptr_group_single_conclusion,
    ptr_group_standard_requirement,
    ptr_group_test_result,
)
from app.rules.ptr.atomic_compare import _clause_window, _group_full_text, build_report_atomic_results


OLD_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"
REDACTED_PATH = "[redacted-path]"

CLAUSE_CODES = {
    "PTR_CLAUSE_TEXT_MISMATCH",
    "PTR_CLAUSE_MISSING",
    "PTR_CLAUSE_INVALID_MATCH_CANDIDATE",
}
TABLE_CODES = {
    "PTR_TABLE_MISSING",
    "PTR_TABLE_CANDIDATE_AMBIGUOUS",
}
PARAMETER_CODES = {
    "PTR_ATOMIC_RESULT_NEEDS_REVIEW",
    "PTR_ATOMIC_RESULT_UNBOUND",
    "PTR_TABLE_VALUE_MISMATCH",
    "PTR_TABLE_UNIT_MISMATCH",
    "PTR_TABLE_PARAM_MISSING",
    "PTR_TABLE_CONDITION_MISMATCH",
    "PTR_TABLE_TOLERANCE_MISMATCH",
    "PTR_TABLE_SEGMENT_AMBIGUOUS",
}
REPORT_SCOPE_CODES = {
    "PTR_SCOPE_DECLARED_ITEM_MISSING_IN_REPORT",
    "PTR_SCOPE_UNDECLARED_REPORT_ITEM",
    "PTR_SCOPE_EXCLUDED_TOPIC_PRESENT",
    "PTR_SCOPE_STANDARD_RANGE_MISMATCH",
}


@dataclass(frozen=True)
class PtrCodexAuditBundle:
    request: CodexReviewRequest
    evidence_package: EvidencePackage


class PtrCodexEvidenceBuilder:
    """Build minimal PTR evidence packages for controlled Codex review."""

    def __init__(
        self,
        *,
        max_table_records: int = 8,
        max_targets_per_task: int = DEFAULT_CODEX_AUDIT_MAX_TARGETS,
        max_targets_per_batch: int = DEFAULT_CODEX_AUDIT_MAX_TARGETS,
        included_check_ids: str | list[str] | tuple[str, ...] | None = None,
        included_finding_codes: str | list[str] | tuple[str, ...] | None = None,
        excluded_check_ids: str | list[str] | tuple[str, ...] | None = None,
        priority_check_ids: str | list[str] | tuple[str, ...] | None = DEFAULT_PTR_PRIORITY_FINDING_CODES,
    ) -> None:
        if max_table_records <= 0:
            raise ValueError("max_table_records must be greater than zero")
        self.max_table_records = max_table_records
        self.target_selection = CodexAuditTargetSelection.from_raw(
            max_targets_per_task=max_targets_per_task,
            max_targets_per_batch=max_targets_per_batch,
            included_check_ids=included_check_ids,
            included_finding_codes=included_finding_codes,
            excluded_check_ids=excluded_check_ids,
            priority_check_ids=priority_check_ids or DEFAULT_PTR_PRIORITY_FINDING_CODES,
        )

    def build(
        self,
        *,
        task_id: str,
        task_type: str,
        ptr_doc: PTRDocument,
        report_doc: ReportDocument,
        check_results: list[CheckResult],
        target_offset: int = 0,
    ) -> PtrCodexAuditBundle | None:
        candidate_findings = self._candidate_findings(check_results)
        findings = self._limit_findings(candidate_findings, target_offset=target_offset)
        if not findings:
            return None

        total_candidate_targets = len(candidate_findings)
        selection_metadata = self.target_selection.selection_metadata(
            total_candidate_targets=total_candidate_targets,
            emitted_targets=len(findings),
            target_offset=target_offset,
        )
        items_by_ref: dict[str, EvidenceItem] = {}
        targets: list[EvidenceTarget] = []
        review_targets: list[CodexReviewTarget] = []

        for finding in findings:
            target_type = self._target_type_for_finding(finding)
            evidence_refs = self._evidence_refs_for_finding(
                finding,
                ptr_doc=ptr_doc,
                report_doc=report_doc,
                items_by_ref=items_by_ref,
            )
            target_id = f"ptr_review:{finding.id}"
            targets.append(
                EvidenceTarget(
                    target_id=target_id,
                    target_type=target_type.value,
                    check_id=finding.check_id,
                    finding_id=finding.id,
                    finding_code=finding.code,
                    summary=self._sanitize_text(finding.message),
                    evidence_refs=evidence_refs,
                    metadata={
                        "source": "ptr_compare_usecase",
                    "finding_code": finding.code,
                    "clause_number": finding.metadata.get("clause_number"),
                    "table_number": finding.metadata.get("table_number"),
                    "parameter_name": finding.metadata.get("parameter_name"),
                    "atomic_id": finding.metadata.get("atomic_id"),
                },
            )
            )
            review_targets.append(
                CodexReviewTarget(
                    target_id=target_id,
                    target_type=target_type,
                    check_id=finding.check_id,
                    finding_id=finding.id,
                    finding_code=finding.code,
                    title=self._sanitize_text(finding.message),
                    summary=self._sanitize_text(self._target_summary(finding)),
                    evidence_refs=[
                        CodexEvidenceRef(ref_id=ref_id, source_type=items_by_ref[ref_id].source_type.value)
                        for ref_id in evidence_refs
                    ],
                    metadata={
                        "source": "ptr_compare_usecase",
                        "finding_code": finding.code,
                        "severity": finding.severity.value,
                        "clause_number": finding.metadata.get("clause_number"),
                        "table_number": finding.metadata.get("table_number"),
                        "parameter_name": finding.metadata.get("parameter_name"),
                        "atomic_id": finding.metadata.get("atomic_id"),
                    },
                )
            )

        package = EvidencePackage(
            package_id=f"codex-ptr-{task_id}-batch-{selection_metadata['batch_index']}",
            task_id=task_id,
            task_type=task_type,
            kind=self._package_kind_for_targets(review_targets),
            schema_version="evidence-package-v1",
            created_at=_utc_now(),
            targets=targets,
            items=list(items_by_ref.values()),
            metadata={
                "source": "ptr_compare_usecase",
                "deterministic_finding_count": sum(len(result.findings) for result in check_results),
                "target_count": len(review_targets),
                **selection_metadata,
            },
        )
        request = CodexReviewRequest(
            request_id=f"codex-request-{task_id}-ptr-batch-{selection_metadata['batch_index']}",
            task_id=task_id,
            task_type=task_type,
            mode="verify",
            targets=review_targets,
            prompt_version="ptr-review-v1",
            schema_version="codex-review-output-v1",
            created_at=_utc_now(),
            metadata={
                "source": "ptr_compare_usecase",
                "deterministic_finding_count": sum(len(result.findings) for result in check_results),
                "target_count": len(review_targets),
                **selection_metadata,
            },
        )
        return PtrCodexAuditBundle(request=request, evidence_package=package)

    def _candidate_findings(self, check_results: list[CheckResult]) -> list[Finding]:
        findings: list[Finding] = []
        for result in check_results:
            for finding in result.findings:
                if finding.check_id not in {"PTR_CLAUSE", "PTR_TABLE", "PTR_SCOPE", "PTR_REPORT_SCOPE"}:
                    continue
                if not self.target_selection.allows(finding):
                    continue
                findings.append(finding)
        return self._sort_findings(findings)

    def _limit_findings(self, findings: list[Finding], *, target_offset: int) -> list[Finding]:
        limit = self.target_selection.effective_limit()
        if limit <= 0:
            return []
        return findings[target_offset : target_offset + limit]

    def _sort_findings(self, findings: list[Finding]) -> list[Finding]:
        priority = priority_index(self.target_selection.priority_check_ids)
        fallback = len(priority)
        return [
            item
            for _, item in sorted(
                enumerate(findings),
                key=lambda pair: (
                    priority.get(pair[1].code, priority.get(pair[1].check_id, fallback)),
                    pair[0],
                ),
            )
        ]

    def _target_type_for_finding(self, finding: Finding) -> CodexReviewTargetType:
        if finding.code in PARAMETER_CODES:
            return CodexReviewTargetType.PTR_PARAMETER
        if finding.code in TABLE_CODES:
            return CodexReviewTargetType.PTR_TABLE
        if finding.check_id == "PTR_REPORT_SCOPE" or finding.code in REPORT_SCOPE_CODES:
            return CodexReviewTargetType.INSPECTION_ITEM
        if finding.code in CLAUSE_CODES or finding.check_id in {"PTR_CLAUSE", "PTR_SCOPE"}:
            return CodexReviewTargetType.PTR_CLAUSE
        if finding.check_id == "PTR_TABLE":
            return CodexReviewTargetType.PTR_TABLE
        return CodexReviewTargetType.PTR_CLAUSE

    def _evidence_refs_for_finding(
        self,
        finding: Finding,
        *,
        ptr_doc: PTRDocument,
        report_doc: ReportDocument,
        items_by_ref: dict[str, EvidenceItem],
    ) -> list[str]:
        refs: list[str] = []
        self._add_item(
            items_by_ref,
            self._finding_item(finding),
            refs,
        )
        self._add_item(
            items_by_ref,
            self._rule_context_item(finding),
            refs,
        )

        for item in self._report_scope_items_for_finding(finding, report_doc):
            self._add_item(items_by_ref, item, refs)

        clause = self._clause_for_finding(finding, ptr_doc)
        if clause is not None:
            self._add_item(items_by_ref, self._clause_item(clause), refs)

        group_item = self._report_inspection_group_item_for_finding(finding, report_doc)
        if group_item is not None:
            self._add_item(items_by_ref, group_item, refs)

        for ptr_table in self._ptr_tables_for_finding(finding, ptr_doc):
            item = self._ptr_table_item(ptr_table)
            if item is not None:
                self._add_item(items_by_ref, item, refs)

        for report_table in self._report_tables_for_finding(finding, report_doc):
            self._add_item(items_by_ref, self._report_table_item(report_table), refs)

        return refs

    def _add_item(self, items_by_ref: dict[str, EvidenceItem], item: EvidenceItem, refs: list[str]) -> None:
        if item.ref_id not in items_by_ref:
            items_by_ref[item.ref_id] = item
        else:
            items_by_ref[item.ref_id] = self._merge_evidence_item(items_by_ref[item.ref_id], item)
        if item.ref_id not in refs:
            refs.append(item.ref_id)

    def _merge_evidence_item(self, existing: EvidenceItem, incoming: EvidenceItem) -> EvidenceItem:
        existing_group = _inspection_group_payload(existing)
        incoming_group = _inspection_group_payload(incoming)
        if existing_group is None or incoming_group is None:
            return existing

        existing_windows = dict(existing_group.get("clause_windows") or {})
        incoming_windows = dict(incoming_group.get("clause_windows") or {})
        merged_group = {
            **existing_group,
            "clause_windows": {**existing_windows, **incoming_windows},
        }
        return existing.model_copy(
            update={
                "structured": {
                    **(existing.structured or {}),
                    "inspection_item_group": merged_group,
                }
            }
        )

    def _finding_item(self, finding: Finding) -> EvidenceItem:
        return EvidenceItem(
            ref_id=f"finding:{finding.id}",
            source_type=EvidenceSourceType.FINDING,
            title=self._sanitize_text(finding.message),
            structured=self._safe_payload(finding),
            page_number=finding.location.page_number if finding.location else None,
            section=finding.location.section if finding.location else None,
            location=self._safe_payload(finding.location) if finding.location else None,
            metadata={
                "finding_id": finding.id,
                "check_id": finding.check_id,
                "finding_code": finding.code,
                "severity": finding.severity.value,
            },
        )

    def _rule_context_item(self, finding: Finding) -> EvidenceItem:
        return EvidenceItem(
            ref_id=f"rule_context:{finding.id}",
            source_type=EvidenceSourceType.RULE_CONTEXT,
            title="PTR deterministic finding context",
            structured=self._safe_payload(
                {
                    "finding_id": finding.id,
                    "check_id": finding.check_id,
                    "code": finding.code,
                    "severity": finding.severity.value,
                    "message": finding.message,
                    "expected": finding.expected,
                    "actual": finding.actual,
                    "metadata": finding.metadata,
                    "audit_reason": "review deterministic PTR candidate finding against focused evidence",
                }
            ),
            metadata={
                "finding_id": finding.id,
                "check_id": finding.check_id,
                "finding_code": finding.code,
            },
        )

    def _clause_item(self, clause: PTRClause) -> EvidenceItem:
        return EvidenceItem(
            ref_id=f"ptr_clause:{clause.clause_id}",
            source_type=EvidenceSourceType.PTR_CLAUSE,
            title=self._sanitize_text(f"PTR clause {clause.number}"),
            text=self._sanitize_text(clause.body_text or clause.text_content or clause.full_text or ""),
            page_number=clause.location.page_number if clause.location else None,
            section=str(clause.number),
            location=self._safe_payload(clause.location) if clause.location else None,
            structured=self._safe_payload(
                {
                    "clause_id": clause.clause_id,
                    "number": str(clause.number),
                    "title": clause.title,
                    "body_text": clause.body_text,
                    "table_numbers": clause.get_all_table_numbers(),
                    "scope_type": clause.scope_type.value,
                    "taxonomy": clause.taxonomy.value,
                }
            ),
            metadata={"clause_id": clause.clause_id, "clause_number": str(clause.number)},
        )

    def _ptr_table_item(self, table: PTRTable) -> EvidenceItem | None:
        if table.canonical_table is None:
            return EvidenceItem(
                ref_id=f"ptr_table:{table.table_id}",
                source_type=EvidenceSourceType.CANONICAL_TABLE,
            title=self._sanitize_text(table.caption or table.title or ""),
                structured=self._safe_payload(
                    {
                        "table_id": table.table_id,
                        "table_number": table.table_number,
                        "caption": table.caption or table.title,
                        "has_canonical_table": False,
                    }
                ),
                page_number=table.page,
                metadata={"table_id": table.table_id, "table_number": table.table_number, "source": "ptr"},
            )
        return EvidenceItem(
            ref_id=f"ptr_table:{table.canonical_table.table_id}",
            source_type=EvidenceSourceType.CANONICAL_TABLE,
            title=self._sanitize_text(table.canonical_table.caption or ""),
            structured=self._safe_payload(self._table_summary(table.canonical_table, source="ptr")),
            page_number=table.canonical_table.page_start or table.page,
            section="ptr_table",
            metadata={
                "table_id": table.canonical_table.table_id,
                "table_number": table.canonical_table.table_number,
                "source": "ptr",
            },
        )

    def _report_table_item(self, table: CanonicalTable) -> EvidenceItem:
        return EvidenceItem(
            ref_id=f"report_table:{table.table_id}",
            source_type=EvidenceSourceType.CANONICAL_TABLE,
            title=self._sanitize_text(table.caption or ""),
            structured=self._safe_payload(self._table_summary(table, source="report")),
            page_number=table.page_start,
            section="report_table",
            metadata={"table_id": table.table_id, "table_number": table.table_number, "source": "report"},
        )

    def _report_scope_items_for_finding(self, finding: Finding, report_doc: ReportDocument) -> list[EvidenceItem]:
        report_scope = self._report_inspection_scope(report_doc)
        if report_scope is None:
            return []
        return [
            self._report_scope_declaration_item(report_scope),
            self._report_scope_external_ranges_item(report_scope, report_doc),
            self._report_scope_inspection_items_item(finding, report_doc),
        ]

    def _report_scope_declaration_item(self, report_scope: ReportInspectionScope) -> EvidenceItem:
        return EvidenceItem(
            ref_id="report_scope:declaration",
            source_type=EvidenceSourceType.REPORT_FIELD,
            title="Report homepage inspection scope declaration",
            text=self._sanitize_text(report_scope.source_text or ""),
            structured=self._safe_payload(
                {
                    "declared_scope_items": report_scope.declared_scope_items,
                    "declared_scope_ranges": [item.model_dump(mode="json") for item in report_scope.declared_scope_ranges],
                    "scope_modifiers": list(report_scope.scope_modifiers),
                    "clause_exclusions": list(report_scope.clause_exclusions),
                    "excluded_topics": report_scope.excluded_topics,
                    "source_page": report_scope.source_page,
                    "source_text": report_scope.source_text,
                    "ptr_direct_content_starts_after": report_scope.ptr_direct_content_starts_after,
                }
            ),
            page_number=report_scope.source_page,
            section="report_scope",
            metadata={"source": "report_homepage", "field_name": "检验项目"},
        )

    def _report_scope_external_ranges_item(
        self,
        report_scope: ReportInspectionScope,
        report_doc: ReportDocument,
    ) -> EvidenceItem:
        ranges = []
        for item in report_scope.external_standard_ranges:
            range_items = self._inspection_items_in_range(report_doc.inspection_items, item.start_item_no, item.end_item_no)
            ranges.append(
                {
                    **item.model_dump(mode="json"),
                    "item_count": len(range_items),
                    "passed_count": sum(1 for report_item in range_items if self._inspection_item_passed(report_item)),
                    "sample_items": [self._inspection_item_summary(report_item) for report_item in range_items[: self.max_table_records]],
                }
            )
        return EvidenceItem(
            ref_id="report_scope:external_standard_ranges",
            source_type=EvidenceSourceType.METADATA,
            title="Report external standard sequence ranges",
            structured=self._safe_payload({"external_standard_ranges": ranges}),
            section="external_standard_ranges",
            metadata={"source": "report_model_spec_or_notes"},
        )

    def _report_scope_inspection_items_item(self, finding: Finding, report_doc: ReportDocument) -> EvidenceItem:
        items = self._inspection_scope_items_for_finding(finding, report_doc)
        truncated = len(items) > self.max_table_records and finding.check_id != "PTR_REPORT_SCOPE"
        displayed_items = items if finding.check_id == "PTR_REPORT_SCOPE" else items[: self.max_table_records]
        return EvidenceItem(
            ref_id="report_scope:inspection_items",
            source_type=EvidenceSourceType.TABLE,
            title="Report inspection table items relevant to scope",
            structured=self._safe_payload(
                {
                    "items": [self._inspection_item_summary(item) for item in displayed_items],
                    "item_count": len(items),
                    "truncated": truncated,
                    "scope_evidence_mode": "full_actual_scope" if finding.check_id == "PTR_REPORT_SCOPE" else "focused",
                }
            ),
            section="inspection_items",
            metadata={"source": "report_inspection_table"},
        )

    def _report_inspection_group_item_for_finding(
        self,
        finding: Finding,
        report_doc: ReportDocument,
    ) -> EvidenceItem | None:
        if not _finding_can_use_report_group(finding) or not report_doc.inspection_items:
            return None
        group = self._report_inspection_group_for_finding(finding, report_doc)
        if group is None:
            return None
        item_no = group.display_item_no or group.item_no
        clause_number = str(finding.metadata.get("clause_number") or "")
        page_text_by_page = report_page_text_by_page(report_doc)
        return EvidenceItem(
            ref_id=f"report_inspection_group:{self._sanitize_text(item_no)}",
            source_type=EvidenceSourceType.TABLE,
            title=self._sanitize_text(f"Report inspection item group {item_no}"),
            structured=self._safe_payload(
                {
                    "inspection_item_group": self._report_inspection_group_summary(
                        group,
                        clause_number=clause_number,
                        page_text_by_page=page_text_by_page,
                    ),
                }
            ),
            page_number=group.pages[0] if group.pages else None,
            section="inspection_item_group",
            metadata={"source": "report_inspection_table", "item_no": item_no},
        )

    def _report_inspection_group_for_finding(
        self,
        finding: Finding,
        report_doc: ReportDocument,
    ) -> InspectionItemGroup | None:
        groups = build_ptr_report_item_groups(report_doc.inspection_items)
        item_no = str(finding.metadata.get("item_no") or "")
        if item_no:
            for group in groups:
                if group.item_no == item_no or group.display_item_no == item_no:
                    return group
        clause_number = str(finding.metadata.get("clause_number") or "")
        if clause_number:
            return ptr_group_for_clause(clause_number, groups)
        return None

    def _report_inspection_group_summary(
        self,
        group: InspectionItemGroup,
        *,
        clause_number: str | None = None,
        page_text_by_page: dict[int, str] | None = None,
    ) -> dict[str, Any]:
        full_group_text = _group_full_text(group, page_text_by_page=page_text_by_page)
        clause_window_text = _clause_window(full_group_text, clause_number) if clause_number else ""
        return {
            "item_no": group.item_no,
            "display_item_no": group.display_item_no,
            "pages": list(group.pages),
            "group_row_count": len(group.rows),
            "full_group_text": full_group_text,
            "clause_window_clause_number": clause_number or None,
            "clause_window_text": clause_window_text,
            "clause_windows": {clause_number: clause_window_text} if clause_number else {},
            "standard_requirement": ptr_group_standard_requirement(group),
            "test_result": ptr_group_test_result(group),
            "single_conclusion": ptr_group_single_conclusion(group),
            "compact_rows": ptr_group_compact_rows(group),
            "source_rows": self._report_inspection_group_source_rows(group),
            "report_atomic_results": self._safe_payload(build_report_atomic_results(group, page_text_by_page=page_text_by_page)),
            "diagnostics": self._safe_payload(group.diagnostics),
        }

    def _report_inspection_group_source_rows(self, group: InspectionItemGroup) -> list[dict[str, Any]]:
        return [
            {
                "page_number": row.source_page,
                "row_index": row.row_index_in_page,
                "sequence_raw": row.sequence_raw,
                "row_text": row.metadata.get("row_text") or _inspection_row_text(row),
                "source_text": row.metadata.get("source_text") or _inspection_row_text(row),
                "table_row_text": row.metadata.get("table_row_text"),
                "combined_row_text": row.metadata.get("combined_row_text") or _inspection_row_text(row),
            }
            for row in group.rows
        ]

    def _clause_for_finding(self, finding: Finding, ptr_doc: PTRDocument) -> PTRClause | None:
        clause_number = str(finding.metadata.get("clause_number") or "")
        if clause_number:
            return ptr_doc.get_clause_by_string(clause_number)
        return None

    def _ptr_tables_for_finding(self, finding: Finding, ptr_doc: PTRDocument) -> list[PTRTable]:
        table_number = str(finding.metadata.get("table_number") or "")
        if not table_number:
            return []
        return ptr_doc.get_tables_by_number(table_number)

    def _report_tables_for_finding(self, finding: Finding, report_doc: ReportDocument) -> list[CanonicalTable]:
        tables = self._report_canonical_tables(report_doc)
        candidate_ids = finding.metadata.get("candidate_ids")
        if isinstance(candidate_ids, list) and candidate_ids:
            ids = {str(candidate_id) for candidate_id in candidate_ids}
            matched = [table for table in tables if table.table_id in ids]
            if matched:
                return matched
        table_number = str(finding.metadata.get("table_number") or "")
        if table_number:
            return [table for table in tables if str(table.table_number or "") == table_number]
        return []

    def _report_canonical_tables(self, report_doc: ReportDocument) -> list[CanonicalTable]:
        tables: list[CanonicalTable] = []
        for key in ("canonical_tables", "parameter_tables", "ptr_compare_tables"):
            tables.extend(_coerce_canonical_tables(report_doc.metadata.get(key)))
        return tables

    def _report_inspection_scope(self, report_doc: ReportDocument) -> ReportInspectionScope | None:
        raw_scope = report_doc.metadata.get("inspection_scope")
        if isinstance(raw_scope, ReportInspectionScope):
            return raw_scope
        if isinstance(raw_scope, dict):
            return ReportInspectionScope.model_validate(raw_scope)
        return None

    def _inspection_items_for_scope_finding(
        self,
        finding: Finding,
        report_items: list[InspectionItem],
    ) -> list[InspectionItem]:
        item_no = str(finding.metadata.get("item_no") or "")
        clause_number = str(finding.metadata.get("clause_number") or "")
        if item_no:
            matched = [item for item in report_items if self._inspection_item_no(item) == item_no]
            if matched:
                return matched
        if clause_number:
            matched = [
                item
                for item in report_items
                if clause_number in " ".join([item.standard_clause or "", item.standard_requirement or ""])
            ]
            if matched:
                return matched
        return list(report_items)

    def _inspection_scope_items_for_finding(
        self,
        finding: Finding,
        report_doc: ReportDocument,
    ) -> list[InspectionItem]:
        if finding.check_id != "PTR_REPORT_SCOPE":
            return self._inspection_items_for_scope_finding(finding, report_doc.inspection_items)
        report_scope = self._report_inspection_scope(report_doc)
        if report_scope is None:
            return list(report_doc.inspection_items)
        items = self._actual_scope_inspection_items(report_scope, report_doc.inspection_items)
        return items or list(report_doc.inspection_items)

    def _actual_scope_inspection_items(
        self,
        report_scope: ReportInspectionScope,
        report_items: list[InspectionItem],
    ) -> list[InspectionItem]:
        direct_starts_after = self._safe_int(report_scope.ptr_direct_content_starts_after)
        items: list[InspectionItem] = []
        for item in report_items:
            item_no = self._safe_int(self._inspection_item_no(item))
            if item_no is not None and direct_starts_after is not None:
                if item_no > direct_starts_after:
                    items.append(item)
                continue
            if item_no is not None and self._item_no_in_external_ranges(item_no, report_scope):
                continue
            if _first_ptr_clause_number(item):
                items.append(item)
        return items

    def _item_no_in_external_ranges(self, item_no: int, report_scope: ReportInspectionScope) -> bool:
        for standard_range in report_scope.external_standard_ranges:
            start = self._safe_int(standard_range.start_item_no)
            end = self._safe_int(standard_range.end_item_no)
            if start is None or end is None:
                continue
            if start <= item_no <= end:
                return True
        return False

    def _inspection_items_in_range(
        self,
        report_items: list[InspectionItem],
        start_item_no: str,
        end_item_no: str,
    ) -> list[InspectionItem]:
        start = self._safe_int(start_item_no)
        end = self._safe_int(end_item_no)
        if start is None or end is None:
            return []
        return [
            item
            for item in report_items
            if (item_no := self._safe_int(self._inspection_item_no(item))) is not None and start <= item_no <= end
        ]

    def _inspection_item_summary(self, item: InspectionItem) -> dict[str, Any]:
        return {
            "item_no": self._inspection_item_no(item),
            "page": item.source_page,
            "standard_clause": item.standard_clause,
            "standard_requirement": item.standard_requirement,
            "test_result": item.test_result,
            "single_conclusion": item.conclusion,
            "remark": item.remark,
        }

    def _inspection_item_passed(self, item: InspectionItem) -> bool:
        text = " ".join([item.test_result or "", item.conclusion or "", *item.result_values])
        return "符合" in text and "不符合" not in text

    def _inspection_item_no(self, item: InspectionItem) -> str | None:
        return item.sequence_raw or (str(item.sequence) if item.sequence is not None else None)

    def _safe_int(self, value: str | None) -> int | None:
        if value is None:
            return None
        text = str(value).strip()
        return int(text) if text.isdigit() else None

    def _table_summary(self, table: CanonicalTable, *, source: str) -> dict[str, Any]:
        records = [self._record_summary(record) for record in table.parameter_records[: self.max_table_records]]
        return {
            "source": source,
            "table_id": table.table_id,
            "table_number": table.table_number,
            "caption": table.caption,
            "page_start": table.page_start,
            "page_end": table.page_end,
            "parameter_name_column": table.parameter_name_column,
            "value_columns": list(table.value_columns),
            "condition_columns": list(table.condition_columns),
            "parameter_record_count": len(table.parameter_records),
            "parameter_records": records,
            "truncated": len(table.parameter_records) > self.max_table_records,
        }

    def _record_summary(self, record: ParameterRecord) -> dict[str, Any]:
        return {
            "parameter_id": record.parameter_id,
            "parameter_name": record.parameter_name,
            "raw_name": record.raw_name,
            "unit": record.unit,
            "dimensions": record.dimensions,
            "conditions": record.conditions,
            "values": record.values,
            "source_rows": record.source_rows,
        }

    def _package_kind_for_targets(self, targets: list[CodexReviewTarget]) -> EvidencePackageKind:
        target_types = {target.target_type for target in targets}
        if target_types == {CodexReviewTargetType.PTR_CLAUSE}:
            return EvidencePackageKind.PTR_CLAUSE_REVIEW
        if target_types == {CodexReviewTargetType.PTR_PARAMETER}:
            return EvidencePackageKind.PTR_PARAMETER_REVIEW
        if target_types == {CodexReviewTargetType.INSPECTION_ITEM}:
            return EvidencePackageKind.INSPECTION_ITEM_REVIEW
        return EvidencePackageKind.PTR_TABLE_REVIEW

    def _target_summary(self, finding: Finding) -> str:
        parts = [
            f"规则初判 {finding.code}",
            f"check_id={finding.check_id}",
        ]
        if finding.metadata.get("clause_number"):
            parts.append(f"clause={finding.metadata['clause_number']}")
        if finding.metadata.get("table_number"):
            parts.append(f"table={finding.metadata['table_number']}")
        if finding.metadata.get("parameter_name"):
            parts.append(f"parameter={finding.metadata['parameter_name']}")
        return "；".join(parts)

    def _safe_payload(self, value: Any) -> Any:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        if isinstance(value, dict):
            return {self._sanitize_text(str(key)): self._safe_payload(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._safe_payload(item) for item in value]
        if isinstance(value, tuple):
            return [self._safe_payload(item) for item in value]
        if isinstance(value, str):
            return self._sanitize_text(value)
        return value

    def _sanitize_text(self, value: str) -> str:
        sanitized = str(value)
        for exact in (OLD_PROJECT_ROOT, NEW_PROJECT_ROOT):
            sanitized = sanitized.replace(exact, REDACTED_PATH)
        sanitized = sanitized.replace("file://", REDACTED_PATH)
        sanitized = sanitized.replace("../", REDACTED_PATH)
        sanitized = sanitized.replace("..\\", REDACTED_PATH)
        sanitized = re.sub(r"/Users/[^\s\"'，,；;\)\]\}]+", REDACTED_PATH, sanitized)
        return sanitized


def _inspection_group_payload(item: EvidenceItem) -> dict[str, Any] | None:
    structured = item.structured if isinstance(item.structured, dict) else {}
    group = structured.get("inspection_item_group")
    return group if isinstance(group, dict) else None


def _coerce_canonical_tables(value: Any) -> list[CanonicalTable]:
    if value is None:
        return []
    if isinstance(value, CanonicalTable):
        return [value]
    if isinstance(value, dict):
        if "table_id" in value:
            return [CanonicalTable.model_validate(value)]
        return [table for item in value.values() for table in _coerce_canonical_tables(item)]
    if isinstance(value, (list, tuple)):
        return [table for item in value for table in _coerce_canonical_tables(item)]
    canonical_table = getattr(value, "canonical_table", None)
    if isinstance(canonical_table, CanonicalTable):
        return [canonical_table]
    return []


def _inspection_row_text(row: InspectionItem) -> str:
    values = [
        row.sequence_raw,
        row.item_name,
        row.standard_clause,
        row.standard_requirement,
        row.test_result,
        row.conclusion,
        row.remark,
    ]
    return " ".join(str(value).strip() for value in values if str(value or "").strip())


def _finding_can_use_report_group(finding: Finding) -> bool:
    return finding.check_id == "PTR_CLAUSE" or finding.code in {
        "PTR_ATOMIC_RESULT_NEEDS_REVIEW",
        "PTR_ATOMIC_RESULT_UNBOUND",
    }


def _first_ptr_clause_number(item: InspectionItem) -> str:
    text = " ".join([item.standard_clause or "", item.standard_requirement or ""])
    match = re.search(r"(?<![\d.])2(?:\.\d+)+(?![\d.])", text)
    return match.group(0) if match else ""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = ["PtrCodexAuditBundle", "PtrCodexEvidenceBuilder"]
