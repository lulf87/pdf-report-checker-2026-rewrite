# Codex CLI Model Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a server-default and per-task Codex CLI model selection for PTR compare and report-check, with a preset-plus-custom frontend control and model-aware cache isolation.

**Architecture:** Extend the existing typed `CodexAuditOptions` path instead of passing raw CLI arguments. `Settings` supplies the server default and option list, usecases clone the audit service with an immutable model-specific runner, and the review cache fingerprints the effective model. A narrow public config endpoint supplies non-sensitive options to a shared frontend selector.

**Tech Stack:** FastAPI, Pydantic Settings, Python dataclasses, pytest, React, TypeScript, Vite.

## Global Constraints

- Preserve API compatibility when new fields are omitted.
- Do not mutate global runner state or accept raw CLI argument lists from the frontend.
- Do not run real Codex CLI in tests.
- Do not change report-check C01-C11 or PTR business rules.
- Preserve all pre-existing uncommitted worktree changes.
- Do not create implementation commits because relevant files overlap existing uncommitted work.

---

### Task 1: Model Validation, Settings, And Typed Audit Options

**Files:**
- Create: `backend/app/application/codex_model_config.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/application/codex_audit_options.py`
- Test: `backend/tests/application/test_codex_runtime_factory.py`
- Test: `backend/tests/application/test_codex_audit_options.py`

**Interfaces:**
- Produces `normalize_codex_model(value: object) -> str | None` and `parse_codex_model_options(value: object) -> tuple[str, ...]`.
- Adds `Settings.codex_audit_model: str | None` and `Settings.codex_audit_model_options: str | None`.
- Adds `CodexAuditOptions.model: str | None`.

- [ ] **Step 1: Write failing tests for valid, empty, and invalid model identifiers**

```python
def test_codex_audit_options_accepts_safe_model_identifier() -> None:
    options = CodexAuditOptions.from_raw({"model": "gpt-5.4/custom"})
    assert options.model == "gpt-5.4/custom"

def test_codex_audit_options_rejects_cli_flag_as_model() -> None:
    with pytest.raises(ValueError, match="model"):
        CodexAuditOptions.from_raw({"model": "--dangerously-bypass-approvals"})
```

- [ ] **Step 2: Run the focused tests and verify the missing behavior fails**

Run: `cd backend && python -m pytest tests/application/test_codex_audit_options.py tests/application/test_codex_runtime_factory.py -v`

- [ ] **Step 3: Implement shared normalization and additive settings fields**

```python
CODEX_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")

def normalize_codex_model(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if CODEX_MODEL_PATTERN.fullmatch(text) is None:
        raise ValueError("Invalid Codex model identifier")
    return text
```

- [ ] **Step 4: Run focused tests until green**

Run: `cd backend && python -m pytest tests/application/test_codex_audit_options.py tests/application/test_codex_runtime_factory.py -v`

---

### Task 2: Immutable Runner Selection And Cache Isolation

**Files:**
- Modify: `backend/app/infrastructure/codex/codex_cli_runner.py`
- Modify: `backend/app/application/codex_audit_service.py`
- Modify: `backend/app/infrastructure/audit/codex_review_cache.py`
- Modify: `backend/app/application/codex_runtime_factory.py`
- Test: `backend/tests/infrastructure/codex/test_codex_cli_runner.py`
- Test: `backend/tests/application/test_codex_audit_service.py`
- Test: `backend/tests/application/test_codex_runtime_factory.py`

**Interfaces:**
- Adds `CodexCliRunnerConfig.model: str | None`.
- Adds `CodexCliRunner.with_model(model: str | None) -> CodexCliRunner`.
- Adds `CodexAuditService.with_model(model: str | None) -> CodexAuditService`.
- Adds `runtime_identity` to `CodexReviewCache.key_for(...)`.

- [ ] **Step 1: Write failing command, clone, and cache-key tests**

```python
def test_cli_runner_adds_selected_model_to_command() -> None:
    runner = CodexCliRunner(CodexCliRunnerConfig(model="gpt-5.4"))
    command = runner._build_command(...)
    assert command[command.index("--model") + 1] == "gpt-5.4"

def test_review_cache_key_changes_with_effective_model(...) -> None:
    assert cache.key_for(..., runtime_identity={"model": "a"}) != cache.key_for(..., runtime_identity={"model": "b"})
```

- [ ] **Step 2: Run tests and confirm they fail for absent model propagation**

Run: `cd backend && python -m pytest tests/infrastructure/codex/test_codex_cli_runner.py tests/application/test_codex_audit_service.py tests/application/test_codex_runtime_factory.py -v`

- [ ] **Step 3: Implement immutable model clones and cache identity**

```python
def with_model(self, model: str | None) -> "CodexCliRunner":
    return CodexCliRunner(replace(self.config, model=model), output_parser=self.output_parser)
```

`CodexAuditService.review()` passes `{"model": effective_model}` into `key_for`, and package/review metadata records the effective model.

- [ ] **Step 4: Run focused tests until green**

Run: `cd backend && python -m pytest tests/infrastructure/codex/test_codex_cli_runner.py tests/application/test_codex_audit_service.py tests/application/test_codex_runtime_factory.py -v`

---

### Task 3: Upload APIs, Public Options Endpoint, And Usecase Metadata

**Files:**
- Create: `backend/app/api/schemas/codex_runtime.py`
- Create: `backend/app/api/routes_runtime_config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/routes_ptr_compare.py`
- Modify: `backend/app/api/routes_report_check.py`
- Modify: `backend/app/application/ptr_compare_usecase.py`
- Modify: `backend/app/application/report_check_usecase.py`
- Test: `backend/tests/api/test_codex_runtime_config.py`
- Test: `backend/tests/api/test_ptr_compare_api.py`
- Test: `backend/tests/api/test_report_check_api.py`
- Test: `backend/tests/application/test_ptr_compare_usecase.py`
- Test: `backend/tests/application/test_report_check_usecase.py`

**Interfaces:**
- Adds `GET /api/runtime-config/codex` returning `default_model` and `model_options`.
- Adds optional multipart field `codex_model` to both upload endpoints.
- Extends effective audit metadata with `requested_model`, `effective_model`, and `model_source`.

- [ ] **Step 1: Write failing endpoint and per-task override tests**

```python
def test_ptr_compare_upload_passes_codex_model_override() -> None:
    response = client.post(..., data={"codex_model": "gpt-5.4"})
    assert response.status_code == 200
    assert fake_usecase.calls[0]["audit_options"]["model"] == "gpt-5.4"

def test_runtime_config_returns_only_model_configuration() -> None:
    assert client.get("/api/runtime-config/codex").json() == {
        "default_model": "gpt-5.4",
        "model_options": ["gpt-5.4", "gpt-5.3-codex"],
    }
```

- [ ] **Step 2: Run API and usecase tests and verify expected failures**

Run: `cd backend && python -m pytest tests/api/test_codex_runtime_config.py tests/api/test_ptr_compare_api.py tests/api/test_report_check_api.py tests/application/test_ptr_compare_usecase.py tests/application/test_report_check_usecase.py -v`

- [ ] **Step 3: Implement API fields, config endpoint, and service selection**

```python
active_service = base_service.with_timeout_seconds(options.timeout_seconds).with_model(
    options.model if options.model is not None else server_default_model
)
```

The factory-configured base runner already contains the server default; task overrides replace only the model on a cloned runner.

- [ ] **Step 4: Run the API and usecase tests until green**

Run: `cd backend && python -m pytest tests/api/test_codex_runtime_config.py tests/api/test_ptr_compare_api.py tests/api/test_report_check_api.py tests/application/test_ptr_compare_usecase.py tests/application/test_report_check_usecase.py -v`

---

### Task 4: Shared Frontend Model Selector

**Files:**
- Create: `frontend/src/features/codex-review/api.ts`
- Create: `frontend/src/features/codex-review/components/CodexModelSelector.tsx`
- Modify: `frontend/src/entities/task/types.ts`
- Modify: `frontend/src/features/ptr-compare/api.ts`
- Modify: `frontend/src/features/report-check/api.ts`
- Modify: `frontend/src/features/ptr-compare/components/PTRUpload.tsx`
- Modify: `frontend/src/features/report-check/components/ReportUpload.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Adds `AuditOptions.model?: string` and `CodexRuntimeConfig`.
- Adds `getCodexRuntimeConfig() -> Promise<CodexRuntimeConfig>`.
- Adds controlled `CodexModelSelector` accepting `value`, `onChange`, and `disabled`.

- [ ] **Step 1: Add frontend types and API serialization, then run build to expose missing component errors**

```ts
export interface CodexRuntimeConfig {
  default_model: string | null;
  model_options: string[];
}
```

Run: `cd frontend && npm run build`

- [ ] **Step 2: Implement the shared selector with server default, presets, and custom input**

```tsx
<select value={mode} onChange={handleModeChange}>
  <option value="">使用服务端默认</option>
  {config.model_options.map((model) => <option value={model}>{model}</option>)}
  <option value="__custom__">自定义模型</option>
</select>
```

- [ ] **Step 3: Integrate both upload forms and send `codex_model` only for overrides**

```ts
if (value.model.trim()) options.model = value.model.trim();
```

- [ ] **Step 4: Run production build until green**

Run: `cd frontend && npm run build`

---

### Task 5: Full Verification And Configuration Documentation

**Files:**
- Modify: `.env.example` if present, otherwise `README.md`
- Modify: `docs/superpowers/specs/2026-07-11-codex-cli-model-configuration-design.md` only if implementation reveals a contract correction.

- [ ] **Step 1: Document environment configuration and CLI-default behavior**

```env
CODEX_AUDIT_MODEL=gpt-5.4
CODEX_AUDIT_MODEL_OPTIONS=gpt-5.4,gpt-5.3-codex
```

- [ ] **Step 2: Run focused backend verification**

Run: `cd backend && python -m pytest tests/infrastructure/codex tests/application/test_codex_runtime_factory.py tests/application/test_codex_audit_service.py tests/api -v`

- [ ] **Step 3: Run full backend verification**

Run: `cd backend && python -m pytest tests/ -v`

- [ ] **Step 4: Run frontend build and repository checks**

Run: `cd frontend && npm run build`

Run: `git diff --check`

- [ ] **Step 5: Inspect the final diff for model provenance, cache separation, and absence of raw CLI argument exposure**

Run: `git diff -- backend/app frontend/src backend/tests README.md`

