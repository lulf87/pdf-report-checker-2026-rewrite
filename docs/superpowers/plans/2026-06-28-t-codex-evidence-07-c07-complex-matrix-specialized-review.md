# T-CODEX-EVIDENCE-07 C07 Complex Matrix Specialized Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a specialized C07 complex matrix review path for item 59 so Codex can audit the 8.7 leakage-current multi-page matrix with matrix-aware image and structured evidence instead of ordinary row-level C07 logic.

**Architecture:** Keep deterministic C07 responsible for emitting `CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX` as a candidate/manual-review finding. Add matrix-specific evidence planning, image crops, structured matrix metadata, and prompt instructions while preserving existing finalization semantics: `refute` can clear the candidate, `confirm` can only become a confirmed error when visual evidence clearly proves a business error, and unresolved matrix mapping remains `manual_review_required`.

**Tech Stack:** FastAPI backend, existing `Finding` / `EvidencePackage` / `CodexReviewTarget` models, PyMuPDF-rendered image evidence, existing Codex CLI runner and prompt builder, pytest with fake/monkeypatched runners only.

---

## Scope And Non-Goals

- Do not modify Codex finalization semantics.
- Do not hard-code item 59 as `refuted`.
- Do not treat complex matrix `uncertain` as a system failure.
- Do not modify `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13`.
- Do not call real Codex CLI in automated tests.
- Do not call GPT/OpenAI API.
- Do not change C04/C05/C06/C09.
- Do not make ordinary C07 row-level review responsible for complex matrix logic.

## Current State

- Latest full mandatory audit `bf36101c-71a4-4f69-9df9-907ced1000cb` has no confirmed final error.
- `refuted_findings_count=50`, `manual_review_required_count=1`.
- The only remaining manual review is C07 item 59:
  - `code=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX`
  - `severity=warn`
  - Codex verdict `uncertain`, confidence `medium`
  - Reasoning says item 59 is an 8.7 leakage-current multi-page complex matrix; cross-page continuation and matrix column mapping need specialized interpretation.
- Existing `C07VisualEvidenceBuilder` can mark `visual_review_mode=complex_matrix_table`, but the image contract is still page/table/row/column oriented and does not explicitly crop row headers, column headers, result matrix body, or cross-page continuation areas.

## File Map

- Create `backend/app/application/c07_complex_matrix_evidence.py`
  - Matrix-specific evidence planner.
  - Builds `EvidenceItem(source_type=IMAGE)` refs for matrix pages, matrix tables, row headers, column headers, result matrix body, conclusion columns, and continuation crops.
  - Builds structured `c07_complex_matrix_evidence` metadata.
- Modify `backend/app/application/c07_visual_evidence.py`
  - Delegate `complex_matrix_table` targets to `C07ComplexMatrixEvidenceBuilder`.
  - Keep current ordinary C07 visual evidence behavior unchanged.
- Modify `backend/app/application/report_codex_evidence_builder.py`
  - Add matrix-specific structured evidence refs and target metadata for C07 complex matrix findings.
  - Preserve existing `complex_matrix_table=true` and `expected_codex_when_complex_matrix` audit trace.
- Modify `backend/app/infrastructure/codex/prompt_builder.py`
  - Add C07 complex matrix instructions that run only when target metadata contains `c07_complex_matrix_evidence` or `visual_review_mode=complex_matrix_table`.
  - Do not change the output schema.
- Modify tests:
  - `backend/tests/application/test_report_codex_evidence_builder.py`
  - `backend/tests/infrastructure/audit/test_evidence_package_writer.py`
  - `backend/tests/application/test_codex_audit_service.py`
  - `backend/tests/infrastructure/codex/test_prompt_builder.py`
  - `backend/tests/application/test_report_check_usecase.py`
  - `backend/tests/rules/report/test_c07_item_conclusion.py`
- Update docs:
  - `docs/current-status.md`
  - `docs/tasks.md`
  - `docs/codex-audit-local-e2e.md`
  - `docs/quality-noise-reduction-plan.md`

## Target Evidence Contract

For a complex matrix C07 target, attach a new metadata object:

```json
{
  "c07_complex_matrix_evidence": {
    "has_complex_matrix_visual_input": true,
    "matrix_review_mode": "leakage_current_multi_page_matrix",
    "page_image_refs": [
      "items/<finding-id>-c07-matrix-page-p42.png",
      "items/<finding-id>-c07-matrix-page-p43.png"
    ],
    "matrix_table_crop_refs": [
      "items/<finding-id>-c07-matrix-table-p42.png",
      "items/<finding-id>-c07-matrix-table-p43.png"
    ],
    "row_header_crop_refs": [
      "items/<finding-id>-c07-matrix-row-headers-p42.png"
    ],
    "column_header_crop_refs": [
      "items/<finding-id>-c07-matrix-column-headers-p42.png"
    ],
    "result_matrix_crop_refs": [
      "items/<finding-id>-c07-matrix-results-p42.png",
      "items/<finding-id>-c07-matrix-results-p43.png"
    ],
    "conclusion_column_crop_refs": [
      "items/<finding-id>-c07-matrix-conclusion-p45.png"
    ],
    "cross_page_continuation_crop_refs": [
      "items/<finding-id>-c07-matrix-continuation-p43.png",
      "items/<finding-id>-c07-matrix-continuation-p44.png"
    ],
    "missing_complex_matrix_evidence_reasons": []
  }
}
```

Attach structured matrix metadata:

```json
{
  "c07_complex_matrix_structured_evidence": {
    "item_no": "59",
    "item_title": "8.7 漏电流",
    "page_numbers": [42, 43, 44, 45],
    "table_headers": ["检验项目", "检验要求", "检验结果", "单项结论"],
    "condition_columns": ["试验条件", "测量部位", "正常状态", "单一故障状态"],
    "measured_values": [
      {"page": 42, "row_label": "对地漏电流", "condition": "正常状态", "value": "0.05 mA", "provenance": "row 2 col 检验结果"}
    ],
    "placeholder_cells": [
      {"page": 43, "row_label": "不适用分支", "value": "——", "meaning": "not_applicable"}
    ],
    "conclusion_candidates": [
      {"page": 45, "value": "符合", "source": "conclusion column"}
    ],
    "continuation_pages": [43, 44, 45],
    "matrix_mapping_confidence": "unknown"
  }
}
```

The exact measured values in tests must come from synthetic fixtures. Real item 59 values must come from parsed output or visual evidence, never from invented data.

## Shared Synthetic Test Helpers

Add these helpers to `backend/tests/application/test_report_codex_evidence_builder.py` before the first new complex-matrix test. They use existing local helpers `_finding`, `_check_result`, `_report_document`, `_parsed_pdf`, `InspectionItem`, `PdfPage`, and `TaskType`.

```python
def _complex_matrix_finding(*, item_no: str = "59") -> Finding:
    return _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX",
        metadata={
            **_metadata_for_check("C07"),
            "item_no": item_no,
            "normalized_item_no": item_no,
            "complex_matrix_table": True,
            "complex_matrix_reason": "8.7 漏电流多页复杂矩阵需要专门矩阵审核",
        },
        id_suffix="c07-matrix",
        message=f"序号 {item_no} 为复杂矩阵表，普通 C07 单项结论逻辑无法稳定判断。",
    )


def _complex_matrix_rows_with_visual_geometry(*, pages: list[int]) -> list[InspectionItem]:
    rows: list[InspectionItem] = []
    for index, page in enumerate(pages):
        rows.append(
            InspectionItem(
                sequence_raw="59" if index == 0 else "",
                sequence=59 if index == 0 else None,
                item_name="8.7 漏电流" if index == 0 else "8.7 漏电流（续）",
                test_result="0.05 mA" if index == 0 else "——",
                conclusion="符合" if index == len(pages) - 1 else "",
                remark="/",
                source_page=page,
                row_index_in_page=index + 1,
                metadata={
                    "complex_matrix_table": True,
                    "condition": "正常状态" if index == 0 else "续表条件",
                    "field_provenance": {"test_result": "synthetic matrix cell"},
                    "visual_geometry": {
                        "table_id": f"p{page}-matrix",
                        "table_bbox": [20.0, 80.0, 560.0, 720.0],
                        "row_bbox": [20.0, 150.0 + index * 24.0, 560.0, 174.0 + index * 24.0],
                        "field_bboxes": {
                            "test_result": [260.0, 150.0 + index * 24.0, 460.0, 174.0 + index * 24.0],
                            "conclusion": [460.0, 150.0 + index * 24.0, 520.0, 174.0 + index * 24.0],
                            "remark": [520.0, 150.0 + index * 24.0, 560.0, 174.0 + index * 24.0],
                        },
                    },
                },
            )
        )
    return rows


def _complex_matrix_rows_with_structured_cells() -> list[InspectionItem]:
    return _complex_matrix_rows_with_visual_geometry(pages=[42, 43, 44, 45])
```

## Codex Prompt Contract

When `complex_matrix_table=true`, prompt instructions must require this order:

1. Identify the matrix table structure before judging the finding.
2. Locate row headers, column headers, condition columns, result matrix body, conclusion column, and continuation pages.
3. Decide whether the visible matrix results support the visible single-item conclusion `符合`.
4. Treat `——` according to the homepage symbol note and matrix context.
5. If column mapping, continuation ownership, or result-to-conclusion support remains unclear, return `uncertain`.
6. If matrix evidence clearly supports the conclusion, return `refute` for the original complex-matrix candidate.
7. Return `confirm` only when the visual matrix evidence clearly proves the report conclusion is unsupported or inconsistent.

Prompt text must also say:

```text
Do not refute or confirm by ordinary C07 row-level rules when complex_matrix_table=true.
First reconstruct the matrix structure from visual evidence. If the matrix cannot be read or mapped across pages, use uncertain.
```

## Task 1: Define Complex Matrix Evidence Builder Contract

**Files:**
- Create: `backend/app/application/c07_complex_matrix_evidence.py`
- Modify: `backend/tests/application/test_report_codex_evidence_builder.py`

- [ ] **Step 1: Write failing metadata contract test**

Add this test to `backend/tests/application/test_report_codex_evidence_builder.py`:

```python
def test_c07_complex_matrix_specialized_evidence_contract(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _complex_matrix_finding(item_no="59")
    rows = _complex_matrix_rows_with_visual_geometry(pages=[42, 43, 44, 45])
    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-c07-matrix",
        task_type=TaskType.REPORT_CHECK.value,
        report=_report_document(inspection_items=rows),
        result=_check_result("C07", [finding]),
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=page, text=f"序号 59 复杂矩阵 p{page}") for page in [42, 43, 44, 45]]),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    target = bundle.request.targets[0]
    matrix = target.metadata["c07_complex_matrix_evidence"]

    assert target.metadata["complex_matrix_table"] is True
    assert matrix["has_complex_matrix_visual_input"] is True
    assert matrix["matrix_review_mode"] == "leakage_current_multi_page_matrix"
    assert matrix["matrix_table_crop_refs"]
    assert matrix["row_header_crop_refs"]
    assert matrix["column_header_crop_refs"]
    assert matrix["result_matrix_crop_refs"]
    assert matrix["conclusion_column_crop_refs"]
    assert matrix["cross_page_continuation_crop_refs"]
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py::test_c07_complex_matrix_specialized_evidence_contract -v
```

Expected: FAIL because `c07_complex_matrix_evidence` is not produced.

- [ ] **Step 3: Create `C07ComplexMatrixEvidenceBuilder` skeleton**

Create `backend/app/application/c07_complex_matrix_evidence.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.domain.evidence_package import EvidenceItem, EvidenceSourceType
from app.domain.finding import Finding
from app.domain.inspection_group import InspectionItemGroup


@dataclass(frozen=True)
class C07ComplexMatrixEvidenceResult:
    items: list[EvidenceItem]
    metadata: dict[str, Any]
    structured_metadata: dict[str, Any]


class C07ComplexMatrixEvidenceBuilder:
    def build(
        self,
        *,
        finding: Finding,
        group: InspectionItemGroup,
        source_pdf_path: str | None,
        safe_id: Callable[[str], str],
    ) -> C07ComplexMatrixEvidenceResult:
        base_id = safe_id(finding.id)
        if not source_pdf_path:
            return C07ComplexMatrixEvidenceResult(
                items=[],
                metadata={
                    "has_complex_matrix_visual_input": False,
                    "matrix_review_mode": "unavailable",
                    "page_image_refs": [],
                    "matrix_table_crop_refs": [],
                    "row_header_crop_refs": [],
                    "column_header_crop_refs": [],
                    "result_matrix_crop_refs": [],
                    "conclusion_column_crop_refs": [],
                    "cross_page_continuation_crop_refs": [],
                    "missing_complex_matrix_evidence_reasons": ["source_pdf_path_missing"],
                },
                structured_metadata=self._structured_metadata(finding=finding, group=group),
            )
        return self._build_from_geometry(finding=finding, group=group, base_id=base_id)
```

- [ ] **Step 4: Run the targeted test again**

Run:

```bash
cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py::test_c07_complex_matrix_specialized_evidence_contract -v
```

Expected: FAIL until Task 2 wires image refs and Task 3 wires builder output into report evidence.

## Task 2: Generate Matrix-Specific Image Evidence Items

**Files:**
- Modify: `backend/app/application/c07_complex_matrix_evidence.py`
- Modify: `backend/tests/application/test_report_codex_evidence_builder.py`

- [ ] **Step 1: Add image item assertions**

Extend the Task 1 test:

```python
items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
matrix_refs = [
    ref.ref_id
    for ref in target.evidence_refs
    if ref.ref_id.startswith("c07_complex_matrix_")
]

assert f"c07_complex_matrix_page:{finding.id}:p42" in matrix_refs
assert f"c07_complex_matrix_table:{finding.id}:p42" in matrix_refs
assert f"c07_complex_matrix_row_headers:{finding.id}:p42" in matrix_refs
assert f"c07_complex_matrix_column_headers:{finding.id}:p42" in matrix_refs
assert f"c07_complex_matrix_results:{finding.id}:p42" in matrix_refs
assert f"c07_complex_matrix_conclusion:{finding.id}:p45" in matrix_refs
assert f"c07_complex_matrix_continuation:{finding.id}:p43" in matrix_refs

for ref_id in matrix_refs:
    item = items_by_ref[ref_id]
    assert item.source_type.value == "image"
    assert item.metadata["codex_image_input"] is True
    assert item.file_path.startswith("items/")
    assert "/Users/" not in item.file_path
```

- [ ] **Step 2: Implement image item helpers**

Add helpers to `C07ComplexMatrixEvidenceBuilder`:

```python
def _image_item(
    self,
    *,
    finding: Finding,
    base_id: str,
    page_number: int,
    kind: str,
    bbox: list[float] | None,
    title: str,
) -> EvidenceItem:
    metadata: dict[str, Any] = {
        "finding_id": finding.id,
        "check_id": "C07",
        "codex_image_input": True,
        "render_source": "source_pdf",
        "source_pdf_ref": "package.metadata.source_pdf_path",
        "render_page_number": page_number,
        "crop_kind": f"complex_matrix_{kind}",
    }
    if bbox is not None:
        metadata["render_bbox"] = self._pad_bbox(bbox)
        metadata["crop_bbox"] = self._pad_bbox(bbox)
    return EvidenceItem(
        ref_id=f"c07_complex_matrix_{kind}:{finding.id}:p{page_number}",
        source_type=EvidenceSourceType.IMAGE,
        title=title,
        file_path=f"items/{base_id}-c07-complex-matrix-{kind}-p{page_number}.png",
        page_number=page_number,
        section=f"c07_complex_matrix_{kind}",
        metadata=metadata,
    )
```

- [ ] **Step 3: Derive crop bboxes from available geometry**

Use existing `visual_geometry` fields:

```python
def _page_geometries(self, group: InspectionItemGroup, page_number: int) -> list[dict[str, Any]]:
    return [
        geometry
        for row in group.rows
        if row.source_page == page_number
        for geometry in [row.metadata.get("visual_geometry")]
        if isinstance(geometry, dict)
    ]

def _matrix_table_bbox(self, geometries: list[dict[str, Any]]) -> list[float] | None:
    return self._union_bboxes([g.get("table_bbox") for g in geometries])

def _result_matrix_bbox(self, geometries: list[dict[str, Any]]) -> list[float] | None:
    return self._union_bboxes([
        (g.get("field_bboxes") or {}).get("test_result")
        for g in geometries
    ])

def _conclusion_bbox(self, geometries: list[dict[str, Any]]) -> list[float] | None:
    return self._union_bboxes([
        (g.get("field_bboxes") or {}).get("conclusion")
        for g in geometries
    ])
```

Row and column header crops can initially use table bbox subdivisions only when table bbox exists:

```python
def _row_header_bbox(self, table_bbox: list[float] | None) -> list[float] | None:
    if table_bbox is None:
        return None
    x0, y0, x1, y1 = table_bbox
    return [x0, y0, x0 + (x1 - x0) * 0.35, y1]

def _column_header_bbox(self, table_bbox: list[float] | None) -> list[float] | None:
    if table_bbox is None:
        return None
    x0, y0, x1, y1 = table_bbox
    return [x0, y0, x1, y0 + (y1 - y0) * 0.22]
```

- [ ] **Step 4: Run targeted evidence tests**

Run:

```bash
cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py::test_c07_complex_matrix_specialized_evidence_contract -v
```

Expected: PASS after Task 3 wiring is complete.

## Task 3: Wire Complex Matrix Evidence Into ReportCodexEvidenceBuilder

**Files:**
- Modify: `backend/app/application/c07_visual_evidence.py`
- Modify: `backend/app/application/report_codex_evidence_builder.py`
- Modify: `backend/tests/application/test_report_codex_evidence_builder.py`

- [ ] **Step 1: Add target metadata assertions**

Extend the test:

```python
assert target.metadata["complex_matrix_table"] is True
assert target.metadata["c07_complex_matrix_evidence"]["has_complex_matrix_visual_input"] is True
assert target.metadata["c07_complex_matrix_structured_evidence"]["item_no"] == "59"
assert target.metadata["c07_visual_evidence"]["visual_review_mode"] == "complex_matrix_table"
```

- [ ] **Step 2: Delegate from C07 visual builder for complex matrix**

In `backend/app/application/c07_visual_evidence.py`, import and use the specialized builder:

```python
from app.application.c07_complex_matrix_evidence import C07ComplexMatrixEvidenceBuilder

class C07VisualEvidenceBuilder:
    def __init__(self, complex_matrix_builder: C07ComplexMatrixEvidenceBuilder | None = None) -> None:
        self.complex_matrix_builder = complex_matrix_builder or C07ComplexMatrixEvidenceBuilder()
```

Inside `build()` before ordinary row crop planning:

```python
if self._is_complex_matrix(finding, group):
    matrix_result = self.complex_matrix_builder.build(
        finding=finding,
        group=group,
        source_pdf_path=source_pdf_path,
        safe_id=safe_id,
    )
    visual_metadata = self._metadata(
        has_visual_input=matrix_result.metadata["has_complex_matrix_visual_input"],
        visual_review_mode="complex_matrix_table",
        page_image_refs=matrix_result.metadata["page_image_refs"],
        table_image_refs=matrix_result.metadata["matrix_table_crop_refs"],
        item_group_crop_refs=[],
        result_column_crop_refs=matrix_result.metadata["result_matrix_crop_refs"],
        conclusion_column_crop_refs=matrix_result.metadata["conclusion_column_crop_refs"],
        remark_column_crop_refs=[],
        missing_reasons=set(matrix_result.metadata["missing_complex_matrix_evidence_reasons"]),
    )
    visual_metadata["expected_codex_when_complex_matrix"] = "uncertain_or_specialized_matrix_review"
    visual_metadata["c07_complex_matrix_evidence"] = matrix_result.metadata
    visual_metadata["c07_complex_matrix_structured_evidence"] = matrix_result.structured_metadata
    return C07VisualEvidenceResult(items=matrix_result.items, metadata=visual_metadata)
```

- [ ] **Step 3: Copy nested metadata to target metadata**

In `ReportCodexEvidenceBuilder._target_metadata_for_finding()` after assigning `c07_visual_evidence`:

```python
matrix_visual = visual_evidence.metadata.get("c07_complex_matrix_evidence")
if isinstance(matrix_visual, dict):
    metadata["c07_complex_matrix_evidence"] = matrix_visual
matrix_structured = visual_evidence.metadata.get("c07_complex_matrix_structured_evidence")
if isinstance(matrix_structured, dict):
    metadata["c07_complex_matrix_structured_evidence"] = matrix_structured
```

- [ ] **Step 4: Run report evidence tests**

Run:

```bash
cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py -v
```

Expected: PASS.

## Task 4: Add Structured Matrix Evidence

**Files:**
- Modify: `backend/app/application/c07_complex_matrix_evidence.py`
- Modify: `backend/tests/application/test_report_codex_evidence_builder.py`

- [ ] **Step 1: Add structured evidence assertions**

Add this test:

```python
def test_c07_complex_matrix_structured_evidence_includes_rows_headers_values_and_conclusions(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _complex_matrix_finding(item_no="59")
    rows = _complex_matrix_rows_with_structured_cells()
    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-c07-matrix-structured",
        task_type=TaskType.REPORT_CHECK.value,
        report=_report_document(inspection_items=rows),
        result=_check_result("C07", [finding]),
        parsed_pdf=_parsed_pdf(extra_pages=[PdfPage(page_number=page, text=f"序号 59 复杂矩阵 p{page}") for page in [42, 43, 44, 45]]),
        source_pdf_path=source_pdf,
    )

    assert bundle is not None
    structured = bundle.request.targets[0].metadata["c07_complex_matrix_structured_evidence"]

    assert structured["item_no"] == "59"
    assert structured["page_numbers"] == [42, 43, 44, 45]
    assert "检验结果" in structured["table_headers"]
    assert structured["condition_columns"]
    assert structured["measured_values"]
    assert structured["placeholder_cells"]
    assert structured["conclusion_candidates"] == [{"page": 45, "value": "符合", "source": "conclusion column"}]
```

- [ ] **Step 2: Implement `_structured_metadata()`**

Use group rows and existing row structured metadata:

```python
def _structured_metadata(self, *, finding: Finding, group: InspectionItemGroup) -> dict[str, Any]:
    return {
        "item_no": str(finding.metadata.get("item_no") or group.item_no),
        "item_title": group.item_name,
        "page_numbers": sorted(set(group.pages)),
        "table_headers": self._table_headers(group),
        "condition_columns": self._condition_columns(group),
        "measured_values": self._measured_values(group),
        "placeholder_cells": self._placeholder_cells(group),
        "conclusion_candidates": self._conclusion_candidates(group),
        "continuation_pages": self._continuation_pages(group),
        "matrix_mapping_confidence": "unknown",
    }
```

Measured values must come from `InspectionItem.structured`, row text, or existing metadata. The helper must not invent values:

```python
def _measured_values(self, group: InspectionItemGroup) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for row in group.rows:
        value = row.test_result
        if not value or value.strip() in {"——", "/", "-"}:
            continue
        values.append({
            "page": row.source_page,
            "row_label": row.item_name,
            "condition": row.metadata.get("condition") or row.metadata.get("matrix_condition") or "",
            "value": value,
            "provenance": row.metadata.get("field_provenance", {}).get("test_result") or "inspection row test_result",
        })
    return values
```

- [ ] **Step 3: Run structured evidence test**

Run:

```bash
cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py::test_c07_complex_matrix_structured_evidence_includes_rows_headers_values_and_conclusions -v
```

Expected: PASS.

## Task 5: Verify Image Materialization And Handoff

**Files:**
- Modify: `backend/tests/infrastructure/audit/test_evidence_package_writer.py`
- Modify: `backend/tests/application/test_codex_audit_service.py`

- [ ] **Step 1: Add writer materialization test**

Add a test that creates a matrix image `EvidenceItem` with `metadata.codex_image_input=true`, `render_page_number`, and `render_bbox`.

```python
def test_c07_complex_matrix_image_items_materialize_to_workspace_png(tmp_path: Path) -> None:
    package = _package_with_image_item(
        ref_id="c07_complex_matrix_results:finding-59:p42",
        file_path="items/finding-59-c07-complex-matrix-results-p42.png",
        metadata={
            "codex_image_input": True,
            "render_source": "source_pdf",
            "render_page_number": 42,
            "render_bbox": [80.0, 120.0, 480.0, 620.0],
            "crop_kind": "complex_matrix_results",
        },
    )

    manifest = EvidencePackageWriter(tmp_path).write(package)

    assert "items/finding-59-c07-complex-matrix-results-p42.png" in manifest.item_file_paths
    assert all(not path.startswith("/Users/") for path in manifest.item_file_paths)
```

- [ ] **Step 2: Add audit service image path collection test**

Add a fake runner spy test:

```python
def test_review_passes_c07_complex_matrix_image_paths_to_runner(tmp_path: Path, monkeypatch) -> None:
    runner = SpyCodexRunner()
    service = _service_with_runner(runner, workspace_root=tmp_path)
    package = _complex_matrix_package_with_materialized_images(tmp_path)

    service.review(package.request, package.package)

    assert any("c07-complex-matrix-results" in path for path in runner.image_paths)
    assert any("c07-complex-matrix-column-headers" in path for path in runner.image_paths)
    assert all(str(tmp_path) in path for path in runner.image_paths)
```

- [ ] **Step 3: Run writer and service tests**

Run:

```bash
cd backend && python -m pytest tests/infrastructure/audit/test_evidence_package_writer.py tests/application/test_codex_audit_service.py -v
```

Expected: PASS.

## Task 6: Add PromptBuilder Complex Matrix Instructions

**Files:**
- Modify: `backend/app/infrastructure/codex/prompt_builder.py`
- Modify: `backend/tests/infrastructure/codex/test_prompt_builder.py`

- [ ] **Step 1: Add prompt contract test**

Add this test:

```python
def test_prompt_instructs_c07_complex_matrix_specialized_review() -> None:
    request, package = _c07_complex_matrix_request_and_package()

    prompt = PromptBuilder().build_prompt(request=request, package=package)

    assert "C07 Complex Matrix Review Instructions" in prompt
    assert "identify the matrix table structure" in prompt
    assert "row headers" in prompt
    assert "column headers" in prompt
    assert "result matrix" in prompt
    assert "cross-page continuation" in prompt
    assert "If column mapping" in prompt
    assert "use uncertain" in prompt
    assert "Do not refute or confirm by ordinary C07 row-level rules" in prompt
    assert "/Users/" not in prompt
```

- [ ] **Step 2: Implement prompt section**

Add a matrix-specific section:

```python
def _render_c07_complex_matrix_instructions(self) -> str:
    return "\n".join([
        "## C07 Complex Matrix Review Instructions",
        "- This target has complex_matrix_table=true and must not be judged by ordinary C07 row-level logic.",
        "- First identify the matrix table structure from visual evidence: row headers, column headers, condition columns, result matrix, conclusion column, and cross-page continuation.",
        "- Use c07_complex_matrix_structured_evidence only as extracted support; visual matrix images are the authority when extraction is incomplete.",
        "- Decide whether the visible matrix results support the visible single-item conclusion.",
        "- Treat '——' and '/' using the homepage symbol note and the matrix row/column context.",
        "- If column mapping, continuation ownership, or result-to-conclusion support remains unclear, use uncertain.",
        "- If the matrix evidence clearly supports the conclusion, refute the original complex-matrix candidate.",
        "- Confirm only when visual matrix evidence clearly proves the conclusion is unsupported or inconsistent.",
        "- Do not invent unreadable values or unstated standard limits.",
    ])
```

Call it only when a target has `c07_complex_matrix_evidence`.

- [ ] **Step 3: Run prompt tests**

Run:

```bash
cd backend && python -m pytest tests/infrastructure/codex/test_prompt_builder.py -v
```

Expected: PASS.

## Task 7: Preserve Finalization Safety With Fake Reviews

**Files:**
- Modify: `backend/tests/application/test_report_check_usecase.py`
- Modify: `backend/tests/application/test_report_codex_evidence_builder.py`

- [ ] **Step 1: Add fake review behavior tests**

Add tests for three outcomes:

```python
def test_complex_matrix_uncertain_remains_manual_review_required() -> None:
    result = _run_report_check_with_fake_codex(
        finding_code="CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX",
        codex_verdict="uncertain",
    )

    finding = _single_c07_complex_matrix_finding(result)
    assert finding.metadata["final_status"] == "manual_review_required"
    assert result.summary["confirmed_errors_count"] == 0
```

```python
def test_complex_matrix_refute_clears_candidate_when_visual_mapping_is_clear() -> None:
    result = _run_report_check_with_fake_codex(
        finding_code="CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX",
        codex_verdict="refute",
    )

    finding = _single_c07_complex_matrix_finding(result)
    assert finding.metadata["final_status"] == "refuted"
    assert result.summary["confirmed_errors_count"] == 0
```

```python
def test_complex_matrix_confirm_requires_clear_business_error_reasoning() -> None:
    result = _run_report_check_with_fake_codex(
        finding_code="CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX",
        codex_verdict="confirm",
        metadata={"visual_matrix_evidence_quality": "clear_business_error"},
    )

    finding = _single_c07_complex_matrix_finding(result)
    assert finding.metadata["final_status"] in {"confirmed", "manual_review_required"}
```

The third test should assert the current implemented safety behavior. If current finalization defensively keeps complex matrix confirms as manual review, preserve that behavior and document it.

- [ ] **Step 2: Run usecase tests**

Run:

```bash
cd backend && python -m pytest tests/application/test_report_check_usecase.py tests/application/test_report_codex_evidence_builder.py -v
```

Expected: PASS. No real Codex CLI is called.

## Task 8: Documentation Updates

**Files:**
- Modify: `docs/current-status.md`
- Modify: `docs/tasks.md`
- Modify: `docs/codex-audit-local-e2e.md`
- Modify: `docs/quality-noise-reduction-plan.md`

- [ ] **Step 1: Update task status docs**

Record:

```markdown
T-CODEX-EVIDENCE-07 implements specialized matrix evidence for C07 item 59. It does not change finalization, does not hard-code item 59 as refuted, and treats unresolved matrix mapping as manual_review_required rather than a system failure.
```

- [ ] **Step 2: Add local validation instructions**

Add targeted item 59 validation command:

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C07 \
CODEX_AUDIT_INCLUDED_FINDING_CODES=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8023 \
BASE_URL=http://127.0.0.1:8023 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

- [ ] **Step 3: Run docs check**

Run:

```bash
git diff --check
```

Expected: PASS.

## Task 9: Automated Test Matrix

Run these after implementation:

```bash
cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py -v
cd backend && python -m pytest tests/infrastructure/audit/test_evidence_package_writer.py -v
cd backend && python -m pytest tests/application/test_codex_audit_service.py -v
cd backend && python -m pytest tests/infrastructure/codex/test_prompt_builder.py -v
cd backend && python -m pytest tests/application/test_report_check_usecase.py -v
cd backend && python -m pytest tests/rules/report/test_c07_item_conclusion.py -v
cd backend && python -m pytest tests/ -v
git diff --check
```

Expected:

- Synthetic complex matrix fixture produces specialized matrix visual evidence.
- Matrix image refs are workspace-local and materialize as PNG.
- CodexAuditService passes matrix PNGs to fake/spy runner.
- Prompt includes matrix-specific instructions and no `/Users/...` paths.
- Automated tests do not call real Codex CLI.
- Finalization remains unchanged.

## Task 10: Real Validation Plan

Real validation is manual and user-triggered only.

- [ ] **Step 1: Targeted item 59 validation**

Run only C07 complex matrix target first:

```bash
CODEX_AUDIT_INCLUDED_CHECK_IDS=C07
CODEX_AUDIT_INCLUDED_FINDING_CODES=CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1
```

Acceptance:

- If matrix visual evidence is sufficient and supports conclusion `符合`, Codex may `refute`; final result should have item 59 `final_status=refuted`.
- If matrix column mapping remains unstable, Codex should return `uncertain`; final result remains `manual_review_required`.
- `confirmed_errors_count` must remain 0 unless the visual matrix evidence clearly proves a business error.
- `codex_runtime_failure_count` must be 0.

- [ ] **Step 2: Full mandatory audit**

After targeted item 59 validation is acceptable, run full audit without `CODEX_AUDIT_INCLUDED_CHECK_IDS`.

Acceptance:

- C04/C05/C06/C09 remain refuted.
- Ordinary C07 visual candidates remain refuted.
- Item 59 is either safely refuted by specialized matrix evidence or remains `manual_review_required` with clear matrix-specific reasoning.
- No runtime failure.
- No confirmed final error unless visual matrix evidence clearly proves a real report error.

## Self-Review Checklist

- Spec coverage:
  - Matrix structure recognition is covered by Tasks 2, 4, and 6.
  - Visual evidence requirements are covered by Tasks 2 and 5.
  - Structured evidence requirements are covered by Task 4.
  - Prompt design is covered by Task 6.
  - Acceptance criteria are covered by Tasks 7, 9, and 10.
  - Real validation order is covered by Task 10.
- Safety:
  - No finalization change.
  - No hard-coded item 59 refute.
  - Complex matrix uncertainty stays `manual_review_required`, not system failure.
  - No real Codex in automated tests.
- Documentation:
  - The plan itself is saved under `docs/superpowers/plans/`.
  - Status docs should point to this plan before implementation begins.
