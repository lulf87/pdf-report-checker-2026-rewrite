# Backend Test Migration Matrix

## Scope

- Old read-only source: `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/backend/tests`
- New writable target: `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3/backend/tests`
- This matrix treats old tests as behavior evidence. It does not preserve old router boundaries, old service mega-modules, Electron, `python_backend`, `uploads`, `temp`, or live raw sample paths as new mainline test assets.
- `docs/open-questions.md` was requested by M39 but is not present in the new repository at the time of this migration pass.

## Status Legend

| Status | Meaning |
|---|---|
| 保留 | The old behavior is represented in the new structure with equivalent or stronger tests. |
| 重写 | The old test intent is retained, but rewritten around new domain/application/rules/infrastructure boundaries. |
| 废弃 | The old assertion locks a deprecated boundary or implementation detail and should not enter the new architecture. |
| 待补齐 | The old suite contains useful edge cases that are only partially represented in the new controlled tests. |

## Matrix

| Old test asset | New test target(s) | Covered module(s) | Decision | Notes |
|---|---|---|---|---|
| `backend/tests/__init__.py` | `backend/tests/__init__.py`, package `__init__.py` files under new test layers | pytest package discovery | 保留 | Only package discovery behavior is needed. |
| `backend/tests/conftest.py` | `backend/tests/api/test_*_api.py`, usecase tests with local fakes | FastAPI app factory, dependency overrides, fake services | 重写 | Old global app/task fixtures are replaced by per-test `create_app()` and dependency overrides. |
| `backend/tests/table_fixture_builder.py` | `backend/tests/fixtures/table_fixture_builder.py` | canonical table fixtures | 保留 | Rehomed as a fixture helper instead of root-level helper. |
| `test_api_report.py` | `backend/tests/api/test_report_check_api.py`, `backend/tests/api/test_tasks_api.py`, `backend/tests/application/test_report_check_usecase.py`, `backend/tests/rules/report/test_report_rule_runner.py` | report upload API, task status/result/export API, report usecase, C01-C11 runner | 重写 | Old `/api/report-self-check/*` and global task dict assertions are deprecated. New API uses `/api/tasks/*` and application orchestration. |
| `test_api_ptr.py` | `backend/tests/api/test_ptr_compare_api.py`, `backend/tests/api/test_tasks_api.py`, `backend/tests/application/test_ptr_compare_usecase.py`, `backend/tests/rules/ptr/*.py`, `backend/tests/application/test_presentation_status.py` | PTR upload API, task API, PTR usecase, PTR rules, presentation summary | 重写 | Old PTR route registration and `build_comparison_result` UI payload assertions are not copied as router logic. Presentation status is covered separately. |
| `test_comparator.py` | `backend/tests/rules/ptr/test_clause_text_compare.py`, `backend/tests/rules/ptr/test_scope_filter.py`, `backend/tests/infrastructure/text/test_normalizer.py` | PTR clause text compare, scope filtering, text normalization | 重写 / 待补齐 | Strict text matching, out-of-scope exclusions, and group/method filtering are represented. Advanced numeric semantic/bundle cases from the old comparator remain future regression candidates. |
| `test_table_comparator.py` | `backend/tests/rules/ptr/test_table_reference_compare.py`, `backend/tests/rules/ptr/test_parameter_compare.py`, `backend/tests/infrastructure/table/test_table_normalizer.py`, `backend/tests/infrastructure/table/test_table_semantics.py` | table reference compare, parameter compare, table normalizer, table semantics | 重写 / 待补齐 | Core table expansion and duplicate candidate behavior are covered. Some old real-report numeric pattern and segmented threshold regressions are documented as not fully ported. |
| `test_ptr_extractor.py` | `backend/tests/domain/test_ptr_models.py`, `backend/tests/domain/test_table_models.py`, `backend/tests/infrastructure/ptr/test_ptr_extractor.py`, `backend/tests/infrastructure/table/test_table_normalizer.py`, `backend/tests/rules/ptr/*.py` | PTR domain models, chapter-2 extractor, table refs, PTR rules | 重写 | Extraction is kept in infrastructure; comparison is split into rules. Old mixed extractor/comparator expectations are separated. |
| `test_ptr_extractor_multidim.py` | `backend/tests/infrastructure/ptr/test_ptr_extractor_multidim.py`, `backend/tests/infrastructure/table/test_table_normalizer.py` | PTR cross-page table continuation, multi-row headers | 保留 / 重写 | Cross-page merge and rejection behavior is represented with controlled fixtures. |
| `test_report_checker.py` | `backend/tests/rules/report/test_c04_sample_description.py`, `test_c05_photo_coverage.py`, `test_c06_label_coverage.py`, `backend/tests/infrastructure/report/test_photo_label_extractor.py`, `test_sample_description_extractor.py` | sample description rule, photo coverage, label coverage, report extractors | 重写 | Old combined report checker responsibilities are split into extractors and independent C04-C06 rules. |
| `test_third_page_checker.py` | `backend/tests/rules/report/test_c01_home_vs_third.py`, `test_c02_third_page_extended_fields.py`, `test_c03_production_date.py`, `backend/tests/infrastructure/report/test_field_extractor.py`, `backend/tests/infrastructure/ocr/test_label_field_extractor.py` | first/third page field extraction, C01-C03 rules, OCR label fields | 重写 | New rules use the current C01-C03 meanings. Old permissive OCR tolerance behavior is not blindly carried into strict matching. |
| `test_inspection_item_checker.py` | `backend/tests/rules/report/test_c07_item_conclusion.py`, `test_c08_non_empty_fields.py`, `test_c09_sequence.py`, `test_c10_continuation.py`, `backend/tests/infrastructure/report/test_inspection_table_extractor.py` | inspection item extraction, C07-C10 rules | 重写 | Old C12/C14/C15 behavior is mapped to new C07-C10 and split by responsibility. |
| `test_page_number_checker.py` | `backend/tests/rules/report/test_c11_page_number.py` | C11 page number continuity | 保留 / 重写 | Old page parsing and continuity cases are represented under the new rule number. |
| `test_report_extractor.py` | `backend/tests/domain/test_report_models.py`, `backend/tests/infrastructure/report/test_page_locator.py`, `test_field_extractor.py`, `test_inspection_table_extractor.py`, `test_sample_description_extractor.py` | report document model and report extractors | 重写 | Old extractor logic is split by page location, field extraction, inspection table extraction, and sample description extraction. |
| `test_report_extractor_merged_cells.py` | `backend/tests/infrastructure/report/test_inspection_table_extractor.py` | merged-cell inspection table extraction | 保留 / 重写 | Merged anchor fill-down behavior is covered. Old real sample entrypoint remains optional and is not copied from raw sample paths. |
| `test_pdf_parser.py` | `backend/tests/domain/test_common_models.py`, `backend/tests/infrastructure/pdf/test_pymupdf_parser.py` | PDF domain/common models, PyMuPDF adapter | 重写 | Parser tests assert parsed structure and diagnostics only. Rule judgement stays out of PDF infrastructure. |
| `test_ocr_parser.py` | `backend/tests/infrastructure/ocr/test_ocr_parser.py`, `backend/tests/infrastructure/text/test_normalizer.py` | PaddleOCR output parsing, OCR symbol diagnostics, text normalization | 重写 | OCR warnings remain diagnostics/evidence and do not become rule verdicts. |
| `test_ocr_service.py` | `backend/tests/infrastructure/ocr/test_ocr_service.py`, `test_caption_extractor.py`, `test_label_field_extractor.py`, `backend/tests/infrastructure/llm/test_vision_service.py` | OCR service interface, caption extraction, label field extraction, VLM helper parsing | 重写 | Live OCR/VLM behavior is faked or parsed deterministically for unit tests. |
| `test_llm_service.py` | `backend/tests/infrastructure/llm/test_llm_service.py`, `test_vision_service.py` | LLM/VLM configuration and disabled-mode adapters | 重写 | LLM is retained as infrastructure capability only, not a final rule judge. |
| `test_table_normalizer.py` | `backend/tests/infrastructure/table/test_table_normalizer.py`, `backend/tests/domain/test_table_models.py` | canonical table model, multi-header normalization, parameter records | 保留 / 重写 | Old table normalization behavior is represented with new domain models. |
| `test_table_semantics.py` | `backend/tests/infrastructure/table/test_table_semantics.py` | table role semantics | 保留 | Synonyms, unknown roles, and path splitting remain covered. |
| `test_text_normalizer.py` | `backend/tests/infrastructure/text/test_normalizer.py` | strict/display normalization and comparison helpers | 保留 / 重写 | Old normalization helpers are split into strict compare and display normalization. |
| `test_export.py` | `backend/tests/infrastructure/export/test_json_exporter.py`, `test_pdf_exporter.py`, `test_excel_exporter.py`, `backend/tests/api/test_report_check_api.py`, `test_tasks_api.py` | JSON/PDF/XLSX exporters, task export API | 重写 / 部分废弃 | Export now consumes unified `CheckResult`. Old PDF color/font private-method assertions are implementation details and are not copied. |
| `test_golden_entrypoints.py` | `backend/tests/golden/test_golden_entrypoints.py` | expected asset inventory | 保留 | Golden inventory checks are retained against migrated expected assets. |
| `test_golden_expected.py` | `backend/tests/golden/test_golden_expected.py`, `backend/app/testing/golden_runner.py` | golden runner and normalized expected snapshots | 保留 / 重写 | Expected snapshots are validated as legacy snapshots; golden expected files were not modified in M39. |

## New Coverage Entry Points

| Layer | New test entry points | Coverage |
|---|---|---|
| Domain | `backend/tests/domain/test_common_models.py`, `test_finding_models.py`, `test_report_models.py`, `test_ptr_models.py`, `test_table_models.py`, `test_domain_models.py` | `Location`, `Evidence`, `Finding`, `CheckResult`, `TaskStatus`, report/PTR/table models. |
| Infrastructure | `backend/tests/infrastructure/pdf/*`, `ocr/*`, `llm/*`, `report/*`, `ptr/*`, `table/*`, `text/*`, `export/*`, `storage/test_local_file_store.py` | PDF, OCR, LLM/VLM adapters, report/PTR extractors, table/text normalizers, exporters, local storage. |
| Rules | `backend/tests/rules/report/test_c01_*.py` through `test_c11_*.py`, `backend/tests/rules/ptr/*.py` | C01-C11 independent report rules and PTR scope, clause text, table reference, parameter comparisons. |
| Application | `backend/tests/application/test_report_check_usecase.py`, `test_ptr_compare_usecase.py`, `test_task_service.py`, `test_presentation_status.py` | usecase orchestration, task lifecycle, error conversion, presentation summaries. |
| API | `backend/tests/api/test_health.py`, `test_report_check_api.py`, `test_ptr_compare_api.py`, `test_tasks_api.py` | health, upload, status, result, export, invalid input, processing/error task responses. |
| Golden | `backend/tests/golden/test_golden_entrypoints.py`, `test_golden_expected.py` | migrated expected inventory and golden result normalization. |

## Deprecated Old Test Boundaries

- Old `/api/report-self-check/*`, `/ptr-report/check/start`, and old sync-style endpoints are not new mainline API contracts. New tests use `/api/tasks/*`.
- Old router-level global `TASKS` dict and lock behavior is not preserved. New tests cover `TaskService` as application state.
- Old service mega-modules that mixed extraction, comparison, prompt packaging, and verdicts are not copied. New tests split extractor, rule, usecase, and API responsibilities.
- Old Codex/LLM-as-final-verdict assertions are deprecated. LLM/VLM tests now cover infrastructure configuration and parsing only.
- Old runtime or raw sample paths under `素材/`, `uploads/`, `temp/`, and `logs/` were not copied into the new tests.
- Old PDF export private formatting/color assertions are not preserved as stable contracts; exporter tests now assert generated artifacts and unified result content.

## Remaining Gaps and Manual Confirmation

- `docs/open-questions.md` is missing, although M39 listed it as a required read target.
- Some old PTR comparator regressions around numeric semantics, segmented threshold bundles, and real-report table patterns are only partially represented by controlled unit tests. They should become dedicated golden or fixture tests once the business examples are approved for migration.
- Old real-sample entrypoints remain optional because raw/local sample directories are not source assets. No raw sample PDF was copied in M39.
- PTR taxonomy and scope details such as appendix, method clauses, group headings, and the old PTR 2.4 warning suppression still require business confirmation before being frozen as full regression coverage.
- Old report rule numbering differs from the new C01-C11 matrix. The new tests intentionally follow the new numbering from `docs/migration-plan.md` and `docs/known-requirements.md`.
