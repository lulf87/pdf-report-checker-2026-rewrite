from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from app.infrastructure.codex.schemas import (
    get_codex_review_output_schema_path,
    load_codex_review_output_schema,
)


def _visual_metadata(
    *,
    observed_label_fields: dict | None = None,
    field_comparisons: list[dict] | None = None,
    visual_evidence_quality: str | None = None,
) -> dict:
    fields = {
        "component_name": None,
        "model": None,
        "serial_number": None,
        "batch_or_serial": None,
        "production_date": None,
        "expiration_date": None,
    }
    if observed_label_fields is not None:
        fields.update(observed_label_fields)
    return {
        "observed_label_fields": fields,
        "field_comparisons": field_comparisons or [],
        "visual_evidence_quality": visual_evidence_quality,
    }


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
        "metadata": _visual_metadata(),
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


def _iter_object_schemas(value, path="$"):
    if isinstance(value, dict):
        schema_type = value.get("type")
        is_object = schema_type == "object" or (isinstance(schema_type, list) and "object" in schema_type)
        if value.get("properties") is not None and is_object:
            yield path, value
        for key, nested in value.items():
            yield from _iter_object_schemas(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_object_schemas(item, f"{path}[{index}]")


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


def test_schema_strict_objects_require_every_declared_property() -> None:
    schema = load_codex_review_output_schema()

    for path, object_schema in _iter_object_schemas(schema):
        property_keys = set(object_schema["properties"])
        required_keys = set(object_schema.get("required", []))

        assert required_keys == property_keys, path


def test_schema_requires_all_visual_label_metadata_fields() -> None:
    schema = load_codex_review_output_schema()
    metadata_schema = schema["properties"]["reviews"]["items"]["properties"]["metadata"]
    observed_schema = metadata_schema["properties"]["observed_label_fields"]

    assert set(metadata_schema["required"]) == {
        "observed_label_fields",
        "field_comparisons",
        "visual_evidence_quality",
    }
    assert set(observed_schema["required"]) == {
        "component_name",
        "model",
        "serial_number",
        "batch_or_serial",
        "production_date",
        "expiration_date",
    }


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


def test_schema_allows_visual_label_metadata_fields() -> None:
    _validator().validate(
        _output_payload(
            reviews=[
                _review_payload(
                    metadata=_visual_metadata(
                        observed_label_fields={
                            "component_name": "输注泵",
                            "model": "RMC-1",
                            "batch_or_serial": "LOT-1",
                            "serial_number": "LOT-1",
                            "production_date": "2025-01-02",
                            "expiration_date": None,
                        },
                        field_comparisons=[
                            {
                                "field_name": "序列号/批号",
                                "expected_value": "LOT-1",
                                "observed_value": "LOT-1",
                                "status": "match",
                                "evidence_ref": "label_image:finding-1",
                                "reasoning": "视觉读取字段与样品描述一致。",
                            }
                        ],
                        visual_evidence_quality="clear",
                    ),
                )
            ]
        )
    )


def test_schema_allows_c04_visual_review_with_null_fields_and_empty_comparisons() -> None:
    _validator().validate(
        _output_payload(
            reviews=[
                _review_payload(
                    verdict="uncertain",
                    metadata=_visual_metadata(
                        observed_label_fields={
                            "component_name": "输注泵",
                            "model": None,
                            "serial_number": None,
                            "batch_or_serial": None,
                            "production_date": None,
                            "expiration_date": None,
                        },
                        field_comparisons=[],
                        visual_evidence_quality="unknown",
                    ),
                )
            ]
        )
    )

    _validator().validate(
        _output_payload(
            reviews=[
                _review_payload(
                    verdict="uncertain",
                    metadata=_visual_metadata(visual_evidence_quality=None),
                )
            ]
        )
    )


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
