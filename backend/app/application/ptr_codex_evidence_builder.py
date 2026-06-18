from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

from pydantic import BaseModel

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
from app.domain.ptr import PTRClause, PTRDocument, PTRTable
from app.domain.report import ReportDocument
from app.domain.result import CheckResult
from app.domain.table import CanonicalTable, ParameterRecord


OLD_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"
REDACTED_PATH = "[redacted-path]"

CLAUSE_CODES = {
    "PTR_CLAUSE_TEXT_MISMATCH",
    "PTR_CLAUSE_MISSING",
}
TABLE_CODES = {
    "PTR_TABLE_MISSING",
    "PTR_TABLE_CANDIDATE_AMBIGUOUS",
}
PARAMETER_CODES = {
    "PTR_TABLE_VALUE_MISMATCH",
    "PTR_TABLE_UNIT_MISMATCH",
    "PTR_TABLE_PARAM_MISSING",
    "PTR_TABLE_CONDITION_MISMATCH",
    "PTR_TABLE_TOLERANCE_MISMATCH",
    "PTR_TABLE_SEGMENT_AMBIGUOUS",
}


@dataclass(frozen=True)
class PtrCodexAuditBundle:
    request: CodexReviewRequest
    evidence_package: EvidencePackage


class PtrCodexEvidenceBuilder:
    """Build minimal PTR evidence packages for controlled Codex review."""

    def __init__(self, *, max_table_records: int = 8) -> None:
        if max_table_records <= 0:
            raise ValueError("max_table_records must be greater than zero")
        self.max_table_records = max_table_records

    def build(
        self,
        *,
        task_id: str,
        task_type: str,
        ptr_doc: PTRDocument,
        report_doc: ReportDocument,
        check_results: list[CheckResult],
    ) -> PtrCodexAuditBundle | None:
        findings = self._reviewable_findings(check_results)
        if not findings:
            return None

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
                    },
                )
            )

        package = EvidencePackage(
            package_id=f"codex-ptr-{task_id}",
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
            },
        )
        request = CodexReviewRequest(
            request_id=f"codex-request-{task_id}-ptr",
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
            },
        )
        return PtrCodexAuditBundle(request=request, evidence_package=package)

    def _reviewable_findings(self, check_results: list[CheckResult]) -> list[Finding]:
        findings: list[Finding] = []
        for result in check_results:
            for finding in result.findings:
                if finding.check_id not in {"PTR_CLAUSE", "PTR_TABLE", "PTR_SCOPE"}:
                    continue
                findings.append(finding)
        return findings

    def _target_type_for_finding(self, finding: Finding) -> CodexReviewTargetType:
        if finding.code in PARAMETER_CODES:
            return CodexReviewTargetType.PTR_PARAMETER
        if finding.code in TABLE_CODES:
            return CodexReviewTargetType.PTR_TABLE
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

        clause = self._clause_for_finding(finding, ptr_doc)
        if clause is not None:
            self._add_item(items_by_ref, self._clause_item(clause), refs)

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
        if item.ref_id not in refs:
            refs.append(item.ref_id)

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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = ["PtrCodexAuditBundle", "PtrCodexEvidenceBuilder"]
