from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from app.infrastructure.codex.schemas import (
    get_codex_review_output_schema_path,
    load_codex_review_output_schema,
)


def _review_payload(**overrides):
    payload = {
        "target_id": "target-1",
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


def _output_payload(**overrides):
    payload = {
        "schema_version": "codex-review-output-v1",
        "reviews": [_review_payload()],
    }
    payload.update(overrides)
    return payload


def _validator() -> Draft202012Validator:
    schema = load_codex_review_output_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _collect_schema_keys(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _collect_schema_keys(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _collect_schema_keys(item)


def test_schema_file_exists_and_is_valid_json() -> None:
    schema_path = get_codex_review_output_schema_path()

    data = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(data)

    assert schema_path.name == "codex_review_output.schema.json"
    assert data["type"] == "object"


def test_schema_top_level_requires_schema_version_and_reviews() -> None:
    schema = load_codex_review_output_schema()

    assert set(schema["required"]) == {"schema_version", "reviews"}


def test_schema_uses_structured_output_compatible_subset() -> None:
    schema_keys = set(_collect_schema_keys(load_codex_review_output_schema()))

    assert not {
        "uniqueItems",
        "allOf",
        "if",
        "then",
        "else",
        "not",
        "dependentRequired",
        "dependentSchemas",
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "minItems",
        "maxItems",
    } & schema_keys


def test_schema_review_enums_match_domain_contract() -> None:
    schema = load_codex_review_output_schema()
    review_schema = schema["properties"]["reviews"]["items"]

    assert set(review_schema["properties"]["verdict"]["enum"]) == {
        "confirm",
        "refute",
        "uncertain",
        "add_finding",
    }
    assert set(review_schema["properties"]["confidence"]["enum"]) == {
        "high",
        "medium",
        "low",
    }
    assert review_schema["properties"]["status"]["enum"] == ["succeeded"]


def test_schema_disallows_unknown_top_level_fields() -> None:
    schema = load_codex_review_output_schema()

    assert schema["additionalProperties"] is False

    with pytest.raises(ValidationError):
        _validator().validate(_output_payload(extra="not allowed"))


def test_schema_accepts_legal_confirm_example() -> None:
    _validator().validate(_output_payload())


def test_schema_rejects_missing_reviews() -> None:
    with pytest.raises(ValidationError):
        _validator().validate({"schema_version": "codex-review-output-v1"})


def test_schema_rejects_invalid_verdict() -> None:
    with pytest.raises(ValidationError):
        _validator().validate(_output_payload(reviews=[_review_payload(verdict="maybe")]))


def test_schema_allows_add_finding_suggestion_to_be_parser_validated() -> None:
    _validator().validate(_output_payload(reviews=[_review_payload(verdict="add_finding")]))
    _validator().validate(
        _output_payload(
            reviews=[
                _review_payload(
                    verdict="add_finding",
                    suggested_finding={
                        "check_id": "C02",
                        "severity": "warn",
                        "code": "C02_LABEL_AMBIGUOUS",
                        "message": "Codex suggests an additional finding.",
                        "expected": None,
                        "actual": None,
                        "evidence_refs": ["ev-1"],
                        "metadata": {},
                    },
                )
            ]
        )
    )


def test_schema_does_not_contain_local_absolute_paths() -> None:
    schema_text = json.dumps(load_codex_review_output_schema(), ensure_ascii=False)

    assert "/Users/" not in schema_text
    assert "报告核对工具2026.4.13" not in schema_text
    assert "报告核对工具2026.6.3" not in schema_text
    assert "backend/app" not in schema_text
    assert "frontend/src" not in schema_text
