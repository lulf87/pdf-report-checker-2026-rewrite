from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

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


CREATED_AT = datetime(2026, 6, 18, 9, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ManualCodexCliSmokeFixture:
    request: CodexReviewRequest
    evidence_package: EvidencePackage


def build_manual_codex_cli_smoke_fixture() -> ManualCodexCliSmokeFixture:
    task_id = "manual-codex-cli-smoke"
    task_type = "ptr_compare"
    target_id = "manual-smoke-target-ptr-value"
    finding_id = "manual-smoke-finding-ptr-value"
    finding_code = "PTR_TABLE_VALUE_MISMATCH"
    evidence_refs = [
        "finding:manual-smoke-ptr-value",
        "rule_context:manual-smoke-ptr-value",
        "ptr_table:manual-smoke-resistance",
        "report_table:manual-smoke-resistance",
    ]

    package = EvidencePackage(
        package_id="manual-codex-cli-smoke-ptr-table",
        task_id=task_id,
        task_type=task_type,
        kind=EvidencePackageKind.PTR_PARAMETER_REVIEW,
        schema_version="evidence-package-v1",
        created_at=CREATED_AT,
        targets=[
            EvidenceTarget(
                target_id=target_id,
                target_type=CodexReviewTargetType.PTR_PARAMETER.value,
                check_id="PTR_PARAMETER",
                finding_id=finding_id,
                finding_code=finding_code,
                summary="PTR 表格参数值与报告表格参数值不一致，需要 Codex runtime auditor 复核。",
                evidence_refs=evidence_refs,
                metadata={"fixture": "manual_codex_cli_smoke"},
            )
        ],
        items=[
            EvidenceItem(
                ref_id="finding:manual-smoke-ptr-value",
                source_type=EvidenceSourceType.FINDING,
                title="PTR table value mismatch candidate finding",
                structured={
                    "id": finding_id,
                    "check_id": "PTR_PARAMETER",
                    "severity": "error",
                    "code": finding_code,
                    "message": "PTR 表 2 中绝缘电阻要求与报告检验结果表数值不一致。",
                    "expected": "绝缘电阻 >= 100 MΩ",
                    "actual": "绝缘电阻 >= 10 MΩ",
                    "metadata": {
                        "table_number": "2",
                        "parameter_name": "绝缘电阻",
                    },
                },
                page_number=5,
                section="PTR_PARAMETER",
                metadata={
                    "finding_id": finding_id,
                    "check_id": "PTR_PARAMETER",
                    "finding_code": finding_code,
                },
            ),
            EvidenceItem(
                ref_id="rule_context:manual-smoke-ptr-value",
                source_type=EvidenceSourceType.RULE_CONTEXT,
                title="Deterministic PTR parameter rule context",
                text=(
                    "确定性规则已构建候选 finding：PTR 标准表格要求绝缘电阻 >= 100 MΩ，"
                    "报告检验结果表提取为绝缘电阻 >= 10 MΩ。请只基于本 evidence package 判断规则初判是否成立。"
                ),
                section="PTR_PARAMETER",
                metadata={"audit_reason": "manual_codex_cli_smoke"},
            ),
            EvidenceItem(
                ref_id="ptr_table:manual-smoke-resistance",
                source_type=EvidenceSourceType.CANONICAL_TABLE,
                title="PTR 表 2 电气安全要求",
                structured={
                    "table_id": "ptr-table-2",
                    "table_number": "2",
                    "caption": "电气安全要求",
                    "records": [
                        {
                            "parameter_name": "绝缘电阻",
                            "condition": "常温",
                            "value": ">= 100",
                            "unit": "MΩ",
                            "source_page": 5,
                        }
                    ],
                },
                page_number=5,
                section="PTR table 2",
                metadata={"table_number": "2", "side": "ptr"},
            ),
            EvidenceItem(
                ref_id="report_table:manual-smoke-resistance",
                source_type=EvidenceSourceType.CANONICAL_TABLE,
                title="报告检验结果表电气安全项目",
                structured={
                    "table_id": "report-table-electrical",
                    "caption": "检验结果",
                    "records": [
                        {
                            "parameter_name": "绝缘电阻",
                            "condition": "常温",
                            "value": ">= 10",
                            "unit": "MΩ",
                            "source_page": 8,
                        }
                    ],
                },
                page_number=8,
                section="report inspection result",
                metadata={"side": "report"},
            ),
        ],
        metadata={
            "source": "manual_codex_cli_smoke_fixture",
            "contains_real_private_pdf_text": False,
            "contains_project_source": False,
        },
    )

    request = CodexReviewRequest(
        request_id="manual-codex-cli-smoke-request",
        task_id=task_id,
        task_type=task_type,
        mode="verify",
        targets=[
            CodexReviewTarget(
                target_id=target_id,
                target_type=CodexReviewTargetType.PTR_PARAMETER,
                check_id="PTR_PARAMETER",
                finding_id=finding_id,
                finding_code=finding_code,
                title="PTR table value mismatch manual smoke review",
                summary="复核 PTR 表格参数值候选 finding 是否成立。",
                evidence_refs=[
                    CodexEvidenceRef(ref_id=ref_id, source_type=package.items[index].source_type.value)
                    for index, ref_id in enumerate(evidence_refs)
                ],
                metadata={"fixture": "manual_codex_cli_smoke"},
            )
        ],
        prompt_version="manual-smoke-v1",
        schema_version="codex-review-output-v1",
        created_at=CREATED_AT,
        metadata={"source": "manual_codex_cli_smoke_fixture"},
    )
    return ManualCodexCliSmokeFixture(request=request, evidence_package=package)


__all__ = ["ManualCodexCliSmokeFixture", "build_manual_codex_cli_smoke_fixture"]
