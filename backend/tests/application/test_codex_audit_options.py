from __future__ import annotations

import pytest

from app.application.codex_audit_options import CodexAuditOptions, compact_audit_options_dict


def test_codex_audit_options_accepts_safe_model_identifier() -> None:
    options = CodexAuditOptions.from_raw({"model": "gpt-5.4/custom:model_1"})

    assert options.model == "gpt-5.4/custom:model_1"
    assert options.has_user_override is True
    assert options.to_metadata()["model"] == "gpt-5.4/custom:model_1"
    assert compact_audit_options_dict({"model": "gpt-5.4/custom:model_1"}) == {
        "model": "gpt-5.4/custom:model_1"
    }


def test_codex_audit_options_treats_blank_model_as_no_override() -> None:
    options = CodexAuditOptions.from_raw({"model": "   "})

    assert options.model is None
    assert options.has_user_override is False
    assert compact_audit_options_dict({"model": "   "}) is None


def test_codex_audit_options_expands_balanced_profile() -> None:
    options = CodexAuditOptions.from_raw({"profile": "balanced"})

    assert options.profile == "balanced"
    assert options.model == "gpt-5.6-terra"
    assert options.reasoning_effort == "medium"
    assert options.timeout_seconds == 600
    assert options.max_targets_per_batch == 3
    assert options.max_parallel_jobs == 2


def test_codex_audit_options_allows_custom_reasoning_effort() -> None:
    options = CodexAuditOptions.from_raw(
        {
            "profile": "custom",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
        }
    )

    assert options.profile == "custom"
    assert options.model == "gpt-5.6-sol"
    assert options.reasoning_effort == "xhigh"
    assert compact_audit_options_dict(options.to_metadata()) == {
        "profile": "custom",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
    }


@pytest.mark.parametrize("reasoning_effort", ("ultra", "maximum", "--high"))
def test_codex_audit_options_rejects_unknown_reasoning_effort(reasoning_effort: str) -> None:
    with pytest.raises(ValueError, match="reasoning effort"):
        CodexAuditOptions.from_raw({"reasoning_effort": reasoning_effort})


def test_codex_audit_options_rejects_unknown_profile() -> None:
    with pytest.raises(ValueError, match="runtime profile"):
        CodexAuditOptions.from_raw({"profile": "turbo"})


@pytest.mark.parametrize(
    "model",
    (
        "--dangerously-bypass-approvals",
        "gpt 5.4",
        "gpt-5.4\n--sandbox",
        "模型-5",
        "a" * 129,
    ),
)
def test_codex_audit_options_rejects_unsafe_model_identifier(model: str) -> None:
    with pytest.raises(ValueError, match="Codex model"):
        CodexAuditOptions.from_raw({"model": model})
