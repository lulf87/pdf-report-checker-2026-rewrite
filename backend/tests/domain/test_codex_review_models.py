from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain.codex_review import (
    CodexEvidenceRef,
    CodexReviewConfidence,
    CodexReviewError,
    CodexReviewRequest,
    CodexReviewResult,
    CodexReviewStatus,
    CodexReviewTarget,
    CodexReviewTargetType,
    CodexReviewVerdict,
    CodexSuggestedFinding,
)
from app.domain.result import CheckResult, CheckStatus


CREATED_AT = datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc)
COMPLETED_AT = datetime(2026, 6, 15, 10, 1, tzinfo=timezone.utc)


def _evidence_ref(ref_id: str = "ev-label-1") -> CodexEvidenceRef:
    return CodexEvidenceRef(
        ref_id=ref_id,
        source_type="report",
        path="evidence/report/label-1.json",
        page_number=3,
        section="label_ocr",
        description="中文标签 OCR 字段证据",
        metadata={"field": "型号规格"},
    )


def _target(target_type: CodexReviewTargetType = CodexReviewTargetType.LABEL_OCR) -> CodexReviewTarget:
    return CodexReviewTarget(
        target_id="target-label-1",
        target_type=target_type,
        check_id="C02",
        finding_id="finding-c02-1",
        finding_code="C02_FIELD_MISMATCH",
        title="第三页型号规格与标签 OCR 复核",
        summary="规则初判标签字段不一致，需要 Codex 审核。",
        evidence_refs=[_evidence_ref()],
        metadata={"priority": "high"},
    )


def _review_result(
    *,
    verdict: CodexReviewVerdict = CodexReviewVerdict.CONFIRM,
    status: CodexReviewStatus = CodexReviewStatus.SUCCEEDED,
    target: CodexReviewTarget | None = None,
) -> CodexReviewResult:
    return CodexReviewResult(
        review_id="review-1",
        request_id="request-1",
        task_id="task-1",
        target=target or _target(),
        status=status,
        verdict=verdict,
        confidence=CodexReviewConfidence.HIGH,
        reasoning_summary="Evidence package supports the deterministic finding.",
        evidence_refs=["ev-label-1"],
        raw_output_path="runtime/codex_audit/task-1/review-1/output.json",
        created_at=CREATED_AT,
        completed_at=COMPLETED_AT,
    )


def test_codex_review_target_can_be_created_and_serialized() -> None:
    target = _target()

    payload = target.model_dump(mode="json")
    restored = CodexReviewTarget.model_validate(payload)

    assert payload["target_type"] == "label_ocr"
    assert payload["evidence_refs"][0]["page_number"] == 3
    assert payload["evidence_refs"][0]["metadata"] == {"field": "型号规格"}
    assert restored.target_type is CodexReviewTargetType.LABEL_OCR
    assert restored.evidence_refs[0].ref_id == "ev-label-1"


def test_codex_review_request_round_trips_through_json_payload() -> None:
    request = CodexReviewRequest(
        request_id="request-1",
        task_id="task-1",
        task_type="report_check",
        targets=[_target()],
        prompt_version="codex-review-prompt-v1",
        schema_version="codex-review-result-v1",
        created_at=CREATED_AT,
        metadata={"source": "unit-test"},
    )

    payload = request.model_dump(mode="json")
    restored = CodexReviewRequest.model_validate(payload)

    assert payload["mode"] == "verify"
    assert payload["targets"][0]["target_type"] == "label_ocr"
    assert isinstance(payload["created_at"], str)
    assert restored.request_id == "request-1"
    assert restored.targets[0].finding_code == "C02_FIELD_MISMATCH"


def test_codex_review_result_confirm_success_scenario() -> None:
    result = _review_result(verdict=CodexReviewVerdict.CONFIRM)

    payload = result.model_dump(mode="json")

    assert payload["status"] == "succeeded"
    assert payload["verdict"] == "confirm"
    assert payload["confidence"] == "high"
    assert payload["target"]["target_id"] == "target-label-1"
    assert payload["evidence_refs"] == ["ev-label-1"]


def test_codex_review_result_refute_can_suggest_severity_adjustment() -> None:
    result = CodexReviewResult(
        review_id="review-refute",
        request_id="request-1",
        task_id="task-1",
        target=_target(CodexReviewTargetType.PHOTO_CAPTION),
        status=CodexReviewStatus.SUCCEEDED,
        verdict=CodexReviewVerdict.REFUTE,
        confidence=CodexReviewConfidence.MEDIUM,
        reasoning_summary="Photo caption evidence indicates the candidate finding is likely a false positive.",
        suggested_severity="info",
        evidence_refs=["ev-photo-1"],
        created_at=CREATED_AT,
        completed_at=COMPLETED_AT,
    )

    payload = result.model_dump(mode="json")

    assert payload["verdict"] == "refute"
    assert payload["suggested_severity"] == "info"
    assert payload["target"]["target_type"] == "photo_caption"


def test_codex_review_result_uncertain_scenario() -> None:
    result = CodexReviewResult(
        review_id="review-uncertain",
        request_id="request-1",
        task_id="task-1",
        target=_target(CodexReviewTargetType.PTR_PARAMETER),
        status=CodexReviewStatus.SUCCEEDED,
        verdict=CodexReviewVerdict.UNCERTAIN,
        confidence=CodexReviewConfidence.LOW,
        reasoning_summary="Parameter evidence is insufficient for a stable judgement.",
        evidence_refs=["ev-table-1"],
        created_at=CREATED_AT,
        completed_at=COMPLETED_AT,
    )

    payload = result.model_dump(mode="json")

    assert payload["verdict"] == "uncertain"
    assert payload["confidence"] == "low"
    assert payload["error"] is None


def test_codex_review_result_add_finding_contains_suggested_finding() -> None:
    suggested = CodexSuggestedFinding(
        check_id="PTR_TABLE",
        severity="warn",
        code="PTR_TABLE_PARAMETER_AMBIGUOUS",
        message="Codex 发现报告参数表存在额外歧义。",
        expected="PTR 表 1 参数完整覆盖",
        actual="报告表存在多个同名参数候选",
        evidence_refs=["ev-table-1", "ev-table-2"],
        metadata={"table_number": "1"},
    )
    result = CodexReviewResult(
        review_id="review-add",
        request_id="request-1",
        task_id="task-1",
        target=_target(CodexReviewTargetType.PTR_TABLE),
        status=CodexReviewStatus.SUCCEEDED,
        verdict=CodexReviewVerdict.ADD_FINDING,
        confidence=CodexReviewConfidence.MEDIUM,
        reasoning_summary="Evidence package contains an ambiguity not reported by deterministic rules.",
        suggested_finding=suggested,
        evidence_refs=["ev-table-1", "ev-table-2"],
        created_at=CREATED_AT,
        completed_at=COMPLETED_AT,
    )

    payload = result.model_dump(mode="json")

    assert payload["verdict"] == "add_finding"
    assert payload["suggested_finding"]["code"] == "PTR_TABLE_PARAMETER_AMBIGUOUS"
    assert payload["suggested_finding"]["evidence_refs"] == ["ev-table-1", "ev-table-2"]


def test_codex_review_result_failed_contains_error() -> None:
    result = CodexReviewResult(
        review_id="review-failed",
        request_id="request-1",
        task_id="task-1",
        target=_target(CodexReviewTargetType.REPORT_RULE),
        status=CodexReviewStatus.FAILED,
        verdict=None,
        confidence=None,
        reasoning_summary=None,
        evidence_refs=[],
        error=CodexReviewError(
            code="CODEX_TIMEOUT",
            message="Codex CLI timed out.",
            detail="Timed out after 30 seconds.",
            retryable=True,
        ),
        created_at=CREATED_AT,
        completed_at=COMPLETED_AT,
    )

    payload = result.model_dump(mode="json")

    assert payload["status"] == "failed"
    assert payload["verdict"] is None
    assert payload["error"]["code"] == "CODEX_TIMEOUT"
    assert payload["error"]["retryable"] is True


def test_codex_review_enums_reject_invalid_values() -> None:
    with pytest.raises(ValidationError):
        CodexReviewTarget(
            target_id="target-invalid",
            target_type="not_a_target",
            evidence_refs=[],
        )

    with pytest.raises(ValidationError):
        CodexReviewResult(
            review_id="review-invalid",
            request_id="request-1",
            task_id="task-1",
            target=_target(),
            status="done",
            verdict=CodexReviewVerdict.CONFIRM,
            created_at=CREATED_AT,
        )


def test_check_result_defaults_to_empty_codex_reviews() -> None:
    result = CheckResult(
        task_id="task-1",
        check_id="C02",
        check_name="第三页扩展字段与中文标签 OCR",
        status=CheckStatus.PASS,
    )

    payload = result.model_dump(mode="json")

    assert result.codex_reviews == []
    assert payload["codex_reviews"] == []


def test_check_result_can_carry_codex_reviews_and_serialize_json() -> None:
    review = _review_result(verdict=CodexReviewVerdict.UNCERTAIN)
    result = CheckResult(
        task_id="task-1",
        check_id="C02",
        check_name="第三页扩展字段与中文标签 OCR",
        status=CheckStatus.REVIEW,
        codex_reviews=[review],
    )

    payload = result.model_dump(mode="json")
    restored = CheckResult.model_validate(payload)

    assert payload["codex_reviews"][0]["verdict"] == "uncertain"
    assert payload["codex_reviews"][0]["target"]["target_type"] == "label_ocr"
    assert restored.codex_reviews[0].verdict is CodexReviewVerdict.UNCERTAIN
