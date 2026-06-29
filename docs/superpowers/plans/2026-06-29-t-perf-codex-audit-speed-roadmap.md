# T-PERF Codex Audit Speed Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quantify Codex audit runtime, restore full audit batch=5 as the default performance posture, and add bounded scheduler, advanced user overrides, and succeeded-review cache/resume support without changing final audit semantics.

**Architecture:** The implementation keeps deterministic rules and Codex finalization unchanged. Performance profile data is recorded in application orchestration and Codex infrastructure metadata; bounded scheduling sits between evidence package construction and `CodexAuditService.review`; cache is limited to schema-valid succeeded reviews and rebinds cached reviews to the current task/request.

**Tech Stack:** FastAPI, Pydantic, React + TypeScript + Vite, PyMuPDF, local Codex CLI.

---

## Implemented Tasks

- [x] **T-PERF-01: Quantify runtime and restore batch=5 visibility**
  - Added `PerformanceProfile` / `PerfStage`.
  - Report check records `parse_pdf`, `build_report_document`, `run_rules`, `codex_audit_total`, `finalize_codex_audit`, and `complete_task`.
  - `CodexAuditService`, `EvidencePackageWriter`, and `CodexCliRunner` record package, image, prompt, evidence, and execution statistics.
  - local E2E prints effective batch size and performance summaries when present.

- [x] **T-PERF-02: Automatic bounded scheduler**
  - Added `CodexAuditScheduler` with `CODEX_AUDIT_MAX_PARALLEL_JOBS`, default `1`.
  - Report and PTR use cases collect independent Codex packages and pass them through the scheduler.
  - Scheduler metadata records worker, queue wait, and parallel job settings.

- [x] **T-PERF-03: User-directed advanced audit controls**
  - Backend routes accept optional `included_check_ids`, `included_finding_codes`, `excluded_check_ids`, `max_targets_per_batch`, and `max_parallel_jobs`.
  - Task metadata records `audit_options_source` and effective audit options.
  - Report and PTR upload pages include collapsed advanced audit controls.

- [x] **T-PERF-04: Succeeded review cache / resume / incremental audit foundation**
  - Added filesystem cache at `runtime/codex_audit_cache`.
  - Cache keys include normalized request/evidence/prompt/schema/image hashes.
  - Only schema-valid succeeded reviews whose verdict is not `uncertain` are cached.
  - Cached reviews are rebound to the current request/task/target and keep audit trace metadata.

## Acceptance Notes

- Mandatory audit semantics are unchanged: failed/skipped required Codex reviews still fail the task.
- `finalize_codex_audit` and C01-C11/PTR deterministic rules were not changed for performance.
- Full audit default remains `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=5`.
- `CODEX_AUDIT_MAX_PARALLEL_JOBS=1` preserves previous serial behavior; higher values require explicit configuration.
- Cache does not reuse failed/skipped/uncertain reviews as a final pass basis.
- No real Codex CLI run is part of automated tests for this implementation.

## Verification Commands

- `cd backend && python -m pytest tests/application/test_performance_profile.py tests/application/test_codex_audit_scheduler.py -v`
- `cd backend && python -m pytest tests/application/test_report_check_usecase.py tests/application/test_ptr_compare_usecase.py -v`
- `cd backend && python -m pytest tests/application/test_codex_audit_service.py -v`
- `cd backend && python -m pytest tests/infrastructure/audit/test_evidence_package_writer.py tests/infrastructure/codex/test_codex_cli_runner.py -v`
- `cd backend && python -m pytest tests/integration/test_codex_audit_local_e2e_artifacts.py -v`
- `cd backend && python -m pytest tests/ -v`
- `bash -n scripts/run-codex-audit-local-e2e.sh`
- `cd frontend && npm run build`
- `git diff --check`

## Real Runtime Follow-up

Run one full mandatory audit with no include/exclude filters and effective `CODEX_AUDIT_MAX_TARGETS_PER_BATCH=5`, then compare against the observed batch=1 baseline:

- final audit status must remain `passed`.
- `confirmed_errors_count=0`.
- `manual_review_required_count=0`.
- `codex_runtime_failure_count=0`.
- package count and total wall-clock time should drop versus the batch=1 baseline.
