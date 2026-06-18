from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.evidence_package import (
    EvidenceItem,
    EvidencePackage,
    EvidencePackageKind,
    EvidenceSourceType,
    EvidenceTarget,
    evidence_item_from_canonical_table,
    evidence_item_from_finding,
)
from app.domain.finding import Finding, FindingSeverity
from app.domain.table import CanonicalCell, CanonicalTable, ParameterRecord


CREATED_AT = datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc)


def _finding() -> Finding:
    return Finding(
        id="finding-c02-1",
        task_id="task-1",
        check_id="C02",
        severity=FindingSeverity.ERROR,
        code="C02_FIELD_MISMATCH",
        message="第三页型号规格与标签 OCR 不一致。",
        location=Location(source_type=SourceType.REPORT, page_number=3, section="第三页"),
        expected="ABC-1",
        actual="ABC-2",
        evidence=[
            Evidence(
                id="evidence-label-1",
                source_type=SourceType.REPORT,
                location=Location(source_type=SourceType.REPORT, page_number=3),
                raw_text="型号规格: ABC-2",
                method=EvidenceMethod.OCR,
            )
        ],
        metadata={"field": "型号规格"},
    )


def _canonical_table() -> CanonicalTable:
    return CanonicalTable(
        table_id="table-1",
        table_number="1",
        caption="表 1 性能指标",
        page_start=5,
        page_end=5,
        cells=[
            CanonicalCell(text="参数", row_index=0, column_index=0, is_header=True),
            CanonicalCell(text="电压", row_index=1, column_index=0),
        ],
        parameter_records=[
            ParameterRecord(
                parameter_id="voltage",
                parameter_name="电压",
                raw_value="5 V",
                normalized_value="5 V",
                unit="V",
                source_rows=[1],
            )
        ],
    )


def _target() -> EvidenceTarget:
    return EvidenceTarget(
        target_id="target-c02-1",
        target_type="label_ocr",
        check_id="C02",
        finding_id="finding-c02-1",
        finding_code="C02_FIELD_MISMATCH",
        summary="复核第三页型号规格与标签 OCR 是否真的不一致。",
        evidence_refs=["finding-c02-1"],
        metadata={"priority": "high"},
    )


def test_evidence_item_can_be_created_and_serialized() -> None:
    item = EvidenceItem(
        ref_id="ev-text-1",
        source_type=EvidenceSourceType.PDF_TEXT,
        title="第三页字段片段",
        text="型号规格: ABC-2",
        page_number=3,
        section="第三页",
        metadata={"field": "型号规格"},
    )

    payload = item.model_dump(mode="json")
    restored = EvidenceItem.model_validate(payload)

    assert payload["source_type"] == "pdf_text"
    assert payload["page_number"] == 3
    assert restored.ref_id == "ev-text-1"
    assert restored.source_type is EvidenceSourceType.PDF_TEXT


def test_evidence_package_round_trips_through_json_payload() -> None:
    package = EvidencePackage(
        package_id="pkg-1",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        created_at=CREATED_AT,
        targets=[_target()],
        items=[evidence_item_from_finding(_finding())],
        metadata={"reason": "unit-test"},
    )

    payload = package.model_dump(mode="json")
    restored = EvidencePackage.model_validate(payload)

    assert payload["kind"] == "report_rule_review"
    assert payload["targets"][0]["evidence_refs"] == ["finding-c02-1"]
    assert isinstance(payload["created_at"], str)
    assert restored.package_id == "pkg-1"
    assert restored.items[0].source_type is EvidenceSourceType.FINDING


def test_evidence_package_can_contain_finding_structured_evidence() -> None:
    item = evidence_item_from_finding(_finding())

    assert item.ref_id == "finding-c02-1"
    assert item.source_type is EvidenceSourceType.FINDING
    assert item.structured is not None
    assert item.structured["code"] == "C02_FIELD_MISMATCH"
    assert item.metadata["finding_id"] == "finding-c02-1"
    assert item.metadata["check_id"] == "C02"


def test_evidence_package_can_contain_canonical_table_structured_evidence() -> None:
    item = evidence_item_from_canonical_table(_canonical_table())

    assert item.ref_id == "canonical-table-table-1"
    assert item.source_type is EvidenceSourceType.CANONICAL_TABLE
    assert item.structured is not None
    assert item.structured["table_number"] == "1"
    assert item.structured["parameter_records"][0]["parameter_name"] == "电压"
    assert item.metadata["table_id"] == "table-1"


def test_evidence_package_rejects_invalid_kind_and_source_type() -> None:
    with pytest.raises(ValidationError):
        EvidencePackage(
            package_id="pkg-1",
            task_id="task-1",
            task_type="report_check",
            kind="not_a_kind",
            schema_version="evidence-package-v1",
            targets=[_target()],
            items=[evidence_item_from_finding(_finding())],
        )

    with pytest.raises(ValidationError):
        EvidenceItem(ref_id="ev-1", source_type="not_a_source")


def test_evidence_item_ref_id_can_be_referenced_by_target() -> None:
    package = EvidencePackage(
        package_id="pkg-1",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        targets=[_target()],
        items=[evidence_item_from_finding(_finding())],
    )

    item_ref_ids = {item.ref_id for item in package.items}

    assert set(package.targets[0].evidence_refs) <= item_ref_ids


def test_evidence_package_rejects_empty_targets_or_items() -> None:
    item = evidence_item_from_finding(_finding())

    with pytest.raises(ValidationError, match="at least one target"):
        EvidencePackage(
            package_id="pkg-1",
            task_id="task-1",
            task_type="report_check",
            kind=EvidencePackageKind.REPORT_RULE_REVIEW,
            schema_version="evidence-package-v1",
            targets=[],
            items=[item],
        )

    with pytest.raises(ValidationError, match="at least one evidence item"):
        EvidencePackage(
            package_id="pkg-1",
            task_id="task-1",
            task_type="report_check",
            kind=EvidencePackageKind.REPORT_RULE_REVIEW,
            schema_version="evidence-package-v1",
            targets=[_target()],
            items=[],
        )


def test_evidence_package_rejects_target_refs_missing_from_items() -> None:
    with pytest.raises(ValidationError, match="unknown evidence ref"):
        EvidencePackage(
            package_id="pkg-1",
            task_id="task-1",
            task_type="report_check",
            kind=EvidencePackageKind.REPORT_RULE_REVIEW,
            schema_version="evidence-package-v1",
            targets=[_target()],
            items=[
                EvidenceItem(
                    ref_id="other-ref",
                    source_type=EvidenceSourceType.PDF_TEXT,
                    text="unrelated",
                )
            ],
        )


def test_evidence_item_rejects_absolute_or_parent_relative_file_path() -> None:
    with pytest.raises(ValidationError, match="relative"):
        EvidenceItem(
            ref_id="ev-1",
            source_type=EvidenceSourceType.PDF_TEXT,
            file_path="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3/secret.txt",
        )

    with pytest.raises(ValidationError, match="path traversal"):
        EvidenceItem(
            ref_id="ev-1",
            source_type=EvidenceSourceType.PDF_TEXT,
            file_path="../secret.txt",
        )
