from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.domain.common import Evidence
from app.domain.finding import Finding
from app.domain.result import CheckResult, CheckSummary, annotate_user_facing_statuses


def build_export_payload(
    results: Sequence[CheckResult],
    *,
    task_id: str | None = None,
    task_type: str | None = None,
    input_files: Sequence[str] | None = None,
    diagnostics: Sequence[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    export_results = [result.model_copy(deep=True) for result in results]
    annotate_user_facing_statuses(export_results)
    findings = flatten_findings(export_results)
    return {
        "task": {
            "task_id": task_id,
            "task_type": task_type,
            "input_files": list(input_files or []),
        },
        "summary": CheckSummary.from_results(export_results).model_dump(mode="json"),
        "check_results": [result.model_dump(mode="json") for result in export_results],
        "findings": [finding.model_dump(mode="json") for finding in findings],
        "evidence": [evidence.model_dump(mode="json") for evidence in flatten_evidence(export_results)],
        "diagnostics": list(diagnostics or []),
        "metadata": metadata or {},
    }


def flatten_findings(results: Sequence[CheckResult]) -> list[Finding]:
    findings: list[Finding] = []
    for result in results:
        findings.extend(result.findings)
    return findings


def flatten_evidence(results: Sequence[CheckResult]) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen_ids: set[str] = set()
    for result in results:
        for item in result.evidence:
            if item.id not in seen_ids:
                evidence.append(item)
                seen_ids.add(item.id)
        for finding in result.findings:
            for item in finding.evidence:
                if item.id not in seen_ids:
                    evidence.append(item)
                    seen_ids.add(item.id)
    return evidence


def evidence_page_label(evidence: Evidence) -> str:
    if evidence.location and evidence.location.page_number is not None:
        return str(evidence.location.page_number)
    return ""
