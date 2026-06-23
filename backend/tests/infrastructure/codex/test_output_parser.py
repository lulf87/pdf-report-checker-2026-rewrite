from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from app.domain.codex_review import (
    CodexEvidenceRef,
    CodexReviewConfidence,
    CodexReviewRequest,
    CodexReviewStatus,
    CodexReviewTarget,
    CodexReviewTargetType,
    CodexReviewVerdict,
)
from app.domain.evidence_package import (
    EvidenceItem,
    EvidencePackage,
    EvidencePackageKind,
    EvidenceSourceType,
    EvidenceTarget,
)
from app.infrastructure.codex.output_parser import CodexReviewOutputParser


CREATED_AT = datetime(2026, 6, 17, 9, 0, tzinfo=timezone.utc)


def _target(target_id: str = "target-1", refs: list[str] | None = None) -> CodexReviewTarget:
    evidence_refs = refs or [f"ev-{target_id[-1]}"]
    return CodexReviewTarget(
        target_id=target_id,
        target_type=CodexReviewTargetType.REPORT_RULE,
        check_id="C02",
        finding_id=f"finding-{target_id}",
        finding_code="C02_FIELD_MISMATCH",
        title=f"Review {target_id}",
        summary=f"规则初判 {target_id} 需要 Codex 审核。",
        evidence_refs=[CodexEvidenceRef(ref_id=ref_id, source_type="pdf_text") for ref_id in evidence_refs],
    )


def _request(targets: list[CodexReviewTarget] | None = None) -> CodexReviewRequest:
    return CodexReviewRequest(
        request_id="request-1",
        task_id="task-1",
        task_type="report_check",
        targets=targets or [_target("target-1", ["ev-1"])],
        prompt_version="codex-review-prompt-v1",
        schema_version="codex-review-output-v1",
        created_at=CREATED_AT,
    )


def _package(*, item_refs: list[str] | None = None) -> EvidencePackage:
    refs = item_refs or ["ev-1"]
    return EvidencePackage(
        package_id="pkg-1",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        created_at=CREATED_AT,
        targets=[
            EvidenceTarget(
                target_id="target-1",
                target_type="report_rule",
                check_id="C02",
                evidence_refs=["ev-1"],
            )
        ],
        items=[
            EvidenceItem(
                ref_id=ref_id,
                source_type=EvidenceSourceType.PDF_TEXT,
                text=f"Evidence text for {ref_id}",
            )
            for ref_id in refs
        ],
    )


def _review_payload(target_id: str = "target-1", **overrides) -> dict:
    payload = {
        "target_id": target_id,
        "status": "succeeded",
        "verdict": "confirm",
        "confidence": "medium",
        "reasoning_summary": "ev-1 supports the deterministic finding.",
        "evidence_refs": ["ev-1"],
        "suggested_severity": None,
        "suggested_finding": None,
        "metadata": {},
    }
    payload.update(overrides)
    return payload


def _output_payload(reviews: list[dict] | None = None, **overrides) -> dict:
    payload = {
        "schema_version": "codex-review-output-v1",
        "reviews": reviews or [_review_payload()],
    }
    payload.update(overrides)
    return payload


def _parse(payload: dict | str, request: CodexReviewRequest | None = None, package: EvidencePackage | None = None):
    output_text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return CodexReviewOutputParser().parse_output(output_text, request or _request(), package or _package())


def _assert_failed(results, code: str, target_count: int = 1) -> None:
    assert len(results) == target_count
    assert {result.status for result in results} == {CodexReviewStatus.FAILED}
    assert {result.error.code for result in results if result.error is not None} == {code}
    assert all(result.verdict is None for result in results)


def test_parse_confirm_output_returns_codex_review_result() -> None:
    results = _parse(_output_payload())

    assert len(results) == 1
    result = results[0]
    assert result.review_id == "codex-review-request-1-target-1"
    assert result.request_id == "request-1"
    assert result.task_id == "task-1"
    assert result.target.target_id == "target-1"
    assert result.status is CodexReviewStatus.SUCCEEDED
    assert result.verdict is CodexReviewVerdict.CONFIRM
    assert result.confidence is CodexReviewConfidence.MEDIUM
    assert result.reasoning_summary == "ev-1 supports the deterministic finding."
    assert result.evidence_refs == ["ev-1"]
    assert result.error is None
    assert result.metadata["schema_version"] == "codex-review-output-v1"
    assert result.metadata["parser"] == "codex_review_output"
    assert result.completed_at is not None


def test_parse_refute_output_preserves_suggested_severity() -> None:
    results = _parse(
        _output_payload(
            [_review_payload(verdict="refute", confidence="low", suggested_severity="info")]
        )
    )

    assert results[0].verdict is CodexReviewVerdict.REFUTE
    assert results[0].confidence is CodexReviewConfidence.LOW
    assert results[0].suggested_severity == "info"


def test_parse_uncertain_output_allows_no_suggested_finding() -> None:
    results = _parse(_output_payload([_review_payload(verdict="uncertain", confidence="low")]))

    assert results[0].verdict is CodexReviewVerdict.UNCERTAIN
    assert results[0].suggested_finding is None


def test_parse_add_finding_output_builds_suggested_finding() -> None:
    results = _parse(
        _output_payload(
            [
                _review_payload(
                    verdict="add_finding",
                    suggested_finding={
                        "check_id": "C02",
                        "severity": "warn",
                        "code": "C02_LABEL_AMBIGUOUS",
                        "message": "Codex found an additional ambiguity.",
                        "expected": None,
                        "actual": None,
                        "evidence_refs": ["ev-1"],
                        "metadata": {},
                    },
                )
            ]
        )
    )

    assert results[0].verdict is CodexReviewVerdict.ADD_FINDING
    assert results[0].suggested_finding is not None
    assert results[0].suggested_finding.code == "C02_LABEL_AMBIGUOUS"
    assert results[0].suggested_finding.evidence_refs == ["ev-1"]


def test_parse_multiple_targets_requires_full_coverage() -> None:
    request = _request([_target("target-1", ["ev-1"]), _target("target-2", ["ev-2"])])
    package = _package(item_refs=["ev-1", "ev-2"])

    results = _parse(
        _output_payload(
            [
                _review_payload("target-1", evidence_refs=["ev-1"]),
                _review_payload("target-2", evidence_refs=["ev-2"]),
            ]
        ),
        request,
        package,
    )

    assert [result.target.target_id for result in results] == ["target-1", "target-2"]
    assert {result.status for result in results} == {CodexReviewStatus.SUCCEEDED}


def test_parse_sets_raw_output_path_on_success() -> None:
    results = CodexReviewOutputParser().parse_output(
        json.dumps(_output_payload(), ensure_ascii=False),
        _request(),
        _package(),
        raw_output_path="codex_review_output.json",
    )

    assert results[0].raw_output_path == "codex_review_output.json"


def test_empty_output_falls_back_to_failed_results_for_all_targets() -> None:
    request = _request([_target("target-1", ["ev-1"]), _target("target-2", ["ev-2"])])

    results = CodexReviewOutputParser().parse_output("", request, _package(item_refs=["ev-1", "ev-2"]))

    _assert_failed(results, "CODEX_OUTPUT_EMPTY", target_count=2)


def test_non_json_output_falls_back_to_failed_results() -> None:
    _assert_failed(_parse("not json"), "CODEX_OUTPUT_INVALID_JSON")


def test_missing_reviews_falls_back_to_schema_invalid() -> None:
    _assert_failed(_parse({"schema_version": "codex-review-output-v1"}), "CODEX_OUTPUT_SCHEMA_INVALID")


def test_schema_invalid_output_falls_back_to_failed_results() -> None:
    _assert_failed(
        _parse(_output_payload([_review_payload(verdict="maybe")])),
        "CODEX_OUTPUT_SCHEMA_INVALID",
    )


def test_unknown_target_id_falls_back_to_failed_results() -> None:
    _assert_failed(_parse(_output_payload([_review_payload("target-other")])), "CODEX_OUTPUT_UNKNOWN_TARGET")


def test_missing_target_review_falls_back_to_failed_results() -> None:
    request = _request([_target("target-1", ["ev-1"]), _target("target-2", ["ev-2"])])

    results = _parse(_output_payload([_review_payload("target-1")]), request, _package(item_refs=["ev-1", "ev-2"]))

    _assert_failed(results, "CODEX_OUTPUT_MISSING_TARGET", target_count=2)


def test_duplicate_target_review_falls_back_to_failed_results() -> None:
    _assert_failed(
        _parse(_output_payload([_review_payload("target-1"), _review_payload("target-1")])),
        "CODEX_OUTPUT_DUPLICATE_TARGET",
    )


def test_unknown_evidence_ref_falls_back_to_failed_results() -> None:
    _assert_failed(
        _parse(_output_payload([_review_payload(evidence_refs=["ev-missing"])])),
        "CODEX_OUTPUT_UNKNOWN_EVIDENCE_REF",
    )


def test_duplicate_evidence_refs_falls_back_to_failed_results() -> None:
    _assert_failed(
        _parse(_output_payload([_review_payload(evidence_refs=["ev-1", "ev-1"])])),
        "CODEX_OUTPUT_DUPLICATE_EVIDENCE_REF",
    )


def test_disallowed_target_evidence_ref_falls_back_to_failed_results() -> None:
    request = _request([_target("target-1", ["ev-1"])])
    package = _package(item_refs=["ev-1", "ev-2"])

    results = _parse(_output_payload([_review_payload(evidence_refs=["ev-2"])]), request, package)

    _assert_failed(results, "CODEX_OUTPUT_DISALLOWED_EVIDENCE_REF")


def test_add_finding_without_suggested_finding_falls_back_with_specific_code() -> None:
    _assert_failed(
        _parse(_output_payload([_review_payload(verdict="add_finding", suggested_finding=None)])),
        "CODEX_OUTPUT_ADD_FINDING_MISSING_SUGGESTION",
    )


def test_suggested_finding_unknown_evidence_ref_falls_back_to_failed_results() -> None:
    _assert_failed(
        _parse(
            _output_payload(
                [
                    _review_payload(
                        verdict="add_finding",
                        suggested_finding={
                            "check_id": "C02",
                            "severity": "warn",
                            "code": "C02_LABEL_AMBIGUOUS",
                            "message": "Codex found an additional ambiguity.",
                            "expected": None,
                            "actual": None,
                            "evidence_refs": ["ev-missing"],
                            "metadata": {},
                        },
                    )
                ]
            )
        ),
        "CODEX_OUTPUT_UNKNOWN_EVIDENCE_REF",
    )


def test_parse_output_file_missing_path_falls_back_to_failed_results(tmp_path) -> None:
    results = CodexReviewOutputParser().parse_output_file(tmp_path / "missing.json", _request(), _package())

    _assert_failed(results, "CODEX_OUTPUT_FILE_NOT_FOUND")
    assert results[0].raw_output_path == str(tmp_path / "missing.json")


def test_parse_output_file_read_error_falls_back_to_failed_results(tmp_path) -> None:
    results = CodexReviewOutputParser().parse_output_file(tmp_path, _request(), _package())

    _assert_failed(results, "CODEX_OUTPUT_FILE_READ_ERROR")
    assert results[0].raw_output_path == str(tmp_path)


def test_build_failed_results_helper_preserves_error_details() -> None:
    results = CodexReviewOutputParser().build_failed_results_for_request(
        _request(),
        code="CODEX_OUTPUT_SCHEMA_INVALID",
        message="Schema validation failed.",
        detail="bad enum",
        retryable=True,
        raw_output_path="codex_review_output.json",
    )

    _assert_failed(results, "CODEX_OUTPUT_SCHEMA_INVALID")
    assert results[0].error is not None
    assert results[0].error.detail == "bad enum"
    assert results[0].error.retryable is True
    assert results[0].raw_output_path == "codex_review_output.json"
