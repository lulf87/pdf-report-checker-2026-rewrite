# T-CODEX-EVIDENCE-06 C07 Table Visual Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add C07 table/page/row/column visual evidence so Codex CLI can review remaining C07 manual-review targets from rendered PDF images, not only structured extraction and page text.

**Architecture:** Reuse the existing C04 visual evidence pipeline: `EvidenceItem(source_type=IMAGE, metadata.codex_image_input=true)` is rendered by `EvidencePackageWriter`, then `CodexAuditService` passes workspace-local PNG paths to `CodexCliRunner` as `codex exec --image items/...png`. T-CODEX-EVIDENCE-06 adds C07-specific visual geometry and evidence items, but does not change finalization semantics: Codex verdicts continue to flow through the existing finalization rules.

**Tech Stack:** FastAPI backend, Pydantic domain models, PyMuPDF/PyMuPDF table extraction, pytest, existing Codex CLI runner/prompt/schema infrastructure.

---

## Scope And Non-Goals

- Do not call GPT/OpenAI API.
- Do not call real Codex CLI in automated tests.
- Do not modify the old project directory `/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13`.
- Do not work on C04; C04 visual label audit is already validated.
- Do not change Codex finalization semantics in this task.
- Do not convert C07 business logic into pure image judgment. Deterministic C07 still creates candidate findings; Codex visual review only audits them.
- Do not treat visual uncertainty as confirmed error. Item 59 complex matrix should remain manual/specialized unless evidence clearly supports a different safe outcome.

## Current State

- C07 evidence already includes:
  - `inspection_item:{finding.id}` structured `InspectionItemGroup`
  - `symbol_note:{finding.id}` homepage symbol note text
  - `inspection_page_text:{finding.id}` focused page text excerpt
- Image input pipeline already exists:
  - `EvidencePackageWriter._materialize_image_items()` renders image items from current uploaded source PDF.
  - Image items use `metadata.codex_image_input=true`.
  - `CodexAuditService._image_paths_from_manifest()` forwards rendered PNGs to runner.
  - `CodexCliRunner` passes workspace-local paths via `--image`.
- Gap:
  - `InspectionItem` has no first-class bbox fields.
  - `InspectionTableExtractor` records `row_location` and per-field evidence metadata, but not stable row/table/column crop coordinates.
  - `ReportCodexEvidenceBuilder` does not create C07 image items.

## File Map

- Modify `backend/app/infrastructure/pdf/pymupdf_parser.py`
  - Capture optional PyMuPDF table cell geometry into `PdfTable.metadata["cell_bboxes"]` when available.
  - Keep fallback behavior unchanged when PyMuPDF does not expose cell bboxes.
- Modify `backend/app/infrastructure/report/inspection_table_extractor.py`
  - Convert table/cell bbox metadata into `InspectionItem.metadata["visual_geometry"]`.
  - Attach row bbox and field-level cell bboxes for sequence/result/conclusion/remark.
- Create `backend/app/application/c07_visual_evidence.py`
  - Isolate C07 visual evidence planning and image item creation from the already-large `ReportCodexEvidenceBuilder`.
- Modify `backend/app/application/report_codex_evidence_builder.py`
  - Wire C07 visual image items into `_evidence_refs_for_finding()` when `source_pdf_path` is present.
  - Add C07 visual metadata to target metadata.
- Modify `backend/app/infrastructure/codex/prompt_builder.py`
  - Add C07 visual review instructions for table/page/row/column images.
- Update tests:
  - `backend/tests/infrastructure/pdf/test_pymupdf_parser.py`
  - `backend/tests/infrastructure/report/test_inspection_table_extractor.py`
  - `backend/tests/application/test_report_codex_evidence_builder.py`
  - `backend/tests/application/test_codex_audit_service.py`
  - `backend/tests/infrastructure/audit/test_evidence_package_writer.py`
  - `backend/tests/infrastructure/codex/test_prompt_builder.py`
  - `backend/tests/application/test_report_check_usecase.py`
- Update docs:
  - `docs/current-status.md`
  - `docs/tasks.md`
  - `docs/codex-audit-local-e2e.md`
  - `docs/quality-noise-reduction-plan.md`

## Target Evidence Contract

For each C07 target, emit as many of the following refs as the source PDF and geometry support:

```json
{
  "c07_visual_evidence": {
    "has_visual_input": true,
    "visual_review_mode": "inspection_item_group",
    "page_image_refs": ["items/<finding-id>-c07-page-22.png"],
    "table_image_refs": ["items/<finding-id>-c07-table-p22.png"],
    "item_group_crop_refs": ["items/<finding-id>-c07-item-group-p22.png"],
    "result_column_crop_refs": ["items/<finding-id>-c07-result-p22.png"],
    "conclusion_column_crop_refs": ["items/<finding-id>-c07-conclusion-p22.png"],
    "remark_column_crop_refs": ["items/<finding-id>-c07-remark-p22.png"],
    "missing_visual_evidence_reasons": []
  }
}
```

Fallback when no bbox exists:

```json
{
  "c07_visual_evidence": {
    "has_visual_input": true,
    "visual_review_mode": "page_only",
    "page_image_refs": ["items/<finding-id>-c07-page-22.png"],
    "table_image_refs": [],
    "item_group_crop_refs": [],
    "result_column_crop_refs": [],
    "conclusion_column_crop_refs": [],
    "remark_column_crop_refs": [],
    "missing_visual_evidence_reasons": ["table_bbox_missing", "row_bbox_missing", "field_bbox_missing"]
  }
}
```

Complex matrix mode for item 59:

```json
{
  "c07_visual_evidence": {
    "has_visual_input": true,
    "visual_review_mode": "complex_matrix_table",
    "page_image_refs": ["items/<finding-id>-c07-page-42.png", "items/<finding-id>-c07-page-43.png"],
    "table_image_refs": ["items/<finding-id>-c07-matrix-table-p42.png", "items/<finding-id>-c07-matrix-table-p43.png"],
    "expected_codex_when_complex_matrix": "uncertain_or_specialized_matrix_review"
  }
}
```

## Task 1: Preserve Table And Cell Geometry

**Files:**
- Modify: `backend/app/infrastructure/pdf/pymupdf_parser.py`
- Modify: `backend/tests/infrastructure/pdf/test_pymupdf_parser.py`

- [ ] **Step 1: Add a failing unit test for PyMuPDF table cell bbox extraction**

Add a test that monkeypatches a fake PyMuPDF table object with `bbox`, `cells`, `extract()`, and `header.names`. The expected `PdfTable.metadata["cell_bboxes"]` shape is a list of rows, each row a list of `null` or `[x0, y0, x1, y1]`.

```python
def test_pymupdf_table_preserves_cell_bboxes() -> None:
    parser = PyMuPDFParser()
    table = FakePyMuPDFTable(
        bbox=(10, 20, 210, 120),
        rows=[
            ["序号", "检验结果", "单项结论", "备注"],
            ["33", "——", "符合", "/"],
        ],
        cells=[
            (10, 20, 40, 50), (40, 20, 120, 50), (120, 20, 170, 50), (170, 20, 210, 50),
            (10, 50, 40, 80), (40, 50, 120, 80), (120, 50, 170, 80), (170, 50, 210, 80),
        ],
        header_names=["序号", "检验结果", "单项结论", "备注"],
    )

    parsed = parser._table_from_pymupdf(table, page_number=22, table_index=0)

    assert parsed is not None
    assert parsed.metadata["cell_bboxes"][1][1] == [40.0, 50.0, 120.0, 80.0]
    assert parsed.metadata["cell_bboxes"][1][2] == [120.0, 50.0, 170.0, 80.0]
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
cd backend && python -m pytest tests/infrastructure/pdf/test_pymupdf_parser.py::test_pymupdf_table_preserves_cell_bboxes -v
```

Expected: FAIL because `cell_bboxes` is not yet populated.

- [ ] **Step 3: Implement `_table_cell_bboxes()`**

In `PyMuPDFParser`, add a helper:

```python
def _table_cell_bboxes(self, table: Any, row_count: int, col_count: int) -> list[list[list[float] | None]]:
    raw_cells = getattr(table, "cells", None)
    if not isinstance(raw_cells, list) or not raw_cells:
        return []
    result: list[list[list[float] | None]] = [[None for _ in range(col_count)] for _ in range(row_count)]
    for index, cell in enumerate(raw_cells[: row_count * col_count]):
        row_index = index // col_count
        col_index = index % col_count
        bbox = self._dump_bbox(self._bbox_from_rect(cell))
        if bbox is not None:
            result[row_index][col_index] = [bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]]
    return result
```

Then include this in `_table_from_pymupdf()` metadata:

```python
cell_bboxes = self._table_cell_bboxes(table, row_count=len(rows), col_count=max((len(row) for row in rows), default=0))
metadata = {
    "row_count": len(rows),
    "column_count": max((len(row) for row in rows), default=0),
}
if cell_bboxes:
    metadata["cell_bboxes"] = cell_bboxes
```

- [ ] **Step 4: Run the test again**

Run:

```bash
cd backend && python -m pytest tests/infrastructure/pdf/test_pymupdf_parser.py::test_pymupdf_table_preserves_cell_bboxes -v
```

Expected: PASS.

## Task 2: Attach C07 Visual Geometry To Inspection Items

**Files:**
- Modify: `backend/app/infrastructure/report/inspection_table_extractor.py`
- Modify: `backend/tests/infrastructure/report/test_inspection_table_extractor.py`

- [ ] **Step 1: Add failing tests for row and field visual geometry**

Use a synthetic `PdfTable` with `bbox` and `metadata["cell_bboxes"]`.

```python
def test_inspection_items_include_visual_geometry_for_c07_crops() -> None:
    table = PdfTable(
        table_id="p22-t1",
        page_numbers=[22],
        bbox=(10, 20, 210, 120),
        columns=["序号", "检验项目", "检验结果", "单项结论", "备注"],
        rows=[
            ["33", "分类标记", "——", "符合", "/"],
            ["", "分类是 IPX0 或 IP0X 的 ME 设备不需要标记。", "", "", ""],
        ],
        metadata={
            "cell_bboxes": [
                [[10, 20, 35, 50], [35, 20, 110, 50], [110, 20, 150, 50], [150, 20, 185, 50], [185, 20, 210, 50]],
                [[10, 50, 35, 80], [35, 50, 110, 80], [110, 50, 150, 80], [150, 50, 185, 80], [185, 50, 210, 80]],
            ]
        },
    )

    extracted = InspectionTableExtractor().extract_items(_parsed_pdf_with_table(table))

    assert extracted[0].metadata["visual_geometry"]["table_bbox"] == [10.0, 20.0, 210.0, 120.0]
    assert extracted[0].metadata["visual_geometry"]["row_bbox"] == [10.0, 20.0, 210.0, 50.0]
    assert extracted[0].metadata["visual_geometry"]["field_bboxes"]["test_result"] == [110.0, 20.0, 150.0, 50.0]
    assert extracted[0].metadata["visual_geometry"]["field_bboxes"]["conclusion"] == [150.0, 20.0, 185.0, 50.0]
    assert extracted[0].metadata["visual_geometry"]["field_bboxes"]["remark"] == [185.0, 20.0, 210.0, 50.0]
```

Add a fallback test:

```python
def test_inspection_items_without_cell_bboxes_keep_existing_behavior() -> None:
    table = _table(22, [HEADERS, ["33", "分类标记", "7.2.9", "要求", "——", "符合", "/"]])

    extracted = InspectionTableExtractor().extract_items(_parsed_pdf_with_table(table))

    assert "visual_geometry" not in extracted[0].metadata
    assert extracted[0].test_result == "——"
    assert extracted[0].conclusion == "符合"
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
cd backend && python -m pytest tests/infrastructure/report/test_inspection_table_extractor.py::test_inspection_items_include_visual_geometry_for_c07_crops tests/infrastructure/report/test_inspection_table_extractor.py::test_inspection_items_without_cell_bboxes_keep_existing_behavior -v
```

Expected: first test FAILS, fallback test PASS or remains compatible.

- [ ] **Step 3: Implement geometry helpers in `InspectionTableExtractor`**

Add helpers:

```python
def _visual_geometry(self, table: PdfTable, row_index: int, header_map: dict[str, int]) -> dict[str, Any] | None:
    cell_bboxes = table.metadata.get("cell_bboxes")
    if not isinstance(cell_bboxes, list) or row_index >= len(cell_bboxes):
        return None
    row_cells = cell_bboxes[row_index]
    if not isinstance(row_cells, list):
        return None

    field_bboxes: dict[str, list[float]] = {}
    for field_name, col_index in header_map.items():
        bbox = self._bbox_list_from_cell(row_cells, col_index)
        if bbox is not None:
            field_bboxes[field_name] = bbox

    row_bbox = self._union_bboxes(list(field_bboxes.values()))
    table_bbox = self._bbox_list_from_model(table.bbox)
    if not row_bbox and not table_bbox and not field_bboxes:
        return None
    return {
        "table_id": table.table_id,
        "table_bbox": table_bbox,
        "row_bbox": row_bbox,
        "field_bboxes": field_bboxes,
    }
```

Call it while building `InspectionItem`:

```python
visual_geometry = self._visual_geometry(table, row_index, header_map)
metadata = {
    "item_no": sequence_raw,
    "item_name": values["item_name"],
    "single_conclusion": values["conclusion"],
    "source_table_id": table.table_id,
    "field_columns": dict(header_map),
    "row_text": " ".join(cell.strip() for cell in row if cell and cell.strip()),
}
if visual_geometry is not None:
    metadata["visual_geometry"] = visual_geometry
```

- [ ] **Step 4: Run extractor tests**

Run:

```bash
cd backend && python -m pytest tests/infrastructure/report/test_inspection_table_extractor.py -v
```

Expected: PASS.

## Task 3: Create C07 Visual Evidence Helper

**Files:**
- Create: `backend/app/application/c07_visual_evidence.py`
- Modify: `backend/tests/application/test_report_codex_evidence_builder.py`

- [ ] **Step 1: Add failing builder tests for C07 image refs**

Add a C07 fixture with `source_pdf_path` and `InspectionItem.metadata["visual_geometry"]`.

```python
def test_c07_visual_evidence_generates_page_table_group_and_column_images(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
        metadata={**_metadata_for_check("C07"), "item_no": "33", "normalized_item_no": "33"},
    )
    report = _report_with_inspection_items([
        InspectionItem(
            sequence_raw="33",
            sequence=33,
            item_name="分类标记",
            test_result="——",
            conclusion="符合",
            remark="/",
            source_page=22,
            row_index_in_page=10,
            metadata={
                "visual_geometry": {
                    "table_id": "p22-t1",
                    "table_bbox": [10, 20, 210, 120],
                    "row_bbox": [10, 50, 210, 80],
                    "field_bboxes": {
                        "test_result": [110, 50, 150, 80],
                        "conclusion": [150, 50, 185, 80],
                        "remark": [185, 50, 210, 80],
                    },
                }
            },
        )
    ])

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type="report_check",
        result=_check_result("C07", [finding]),
        report=report,
        source_pdf_path=source_pdf,
    )

    target = bundle.request.targets[0]
    visual = target.metadata["c07_visual_evidence"]
    assert visual["page_image_refs"] == ["items/task-1-C07-c07-page-p22.png"]
    assert visual["table_image_refs"] == ["items/task-1-C07-c07-table-p22.png"]
    assert visual["item_group_crop_refs"] == ["items/task-1-C07-c07-item-group-p22.png"]
    assert visual["result_column_crop_refs"] == ["items/task-1-C07-c07-result-p22.png"]
    assert visual["conclusion_column_crop_refs"] == ["items/task-1-C07-c07-conclusion-p22.png"]
    assert visual["remark_column_crop_refs"] == ["items/task-1-C07-c07-remark-p22.png"]
```

Add a no-bbox fallback test:

```python
def test_c07_visual_evidence_without_bbox_uses_page_image_only(tmp_path: Path) -> None:
    source_pdf = tmp_path / "report.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n%fake metadata only\n")
    finding = _finding(check_id="C07", metadata={**_metadata_for_check("C07"), "item_no": "94", "normalized_item_no": "94"})
    report = _report_with_inspection_items([
        InspectionItem(sequence_raw="94", sequence=94, test_result="——", conclusion="符合", remark="/", source_page=72, row_index_in_page=10)
    ])

    bundle = ReportCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type="report_check",
        result=_check_result("C07", [finding]),
        report=report,
        source_pdf_path=source_pdf,
    )

    visual = bundle.request.targets[0].metadata["c07_visual_evidence"]
    assert visual["visual_review_mode"] == "page_only"
    assert visual["page_image_refs"] == ["items/task-1-C07-c07-page-p72.png"]
    assert "row_bbox_missing" in visual["missing_visual_evidence_reasons"]
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py::test_c07_visual_evidence_generates_page_table_group_and_column_images tests/application/test_report_codex_evidence_builder.py::test_c07_visual_evidence_without_bbox_uses_page_image_only -v
```

Expected: FAIL because C07 visual evidence does not exist yet.

- [ ] **Step 3: Implement `c07_visual_evidence.py`**

Create a helper with these responsibilities:

```python
@dataclass(frozen=True)
class C07VisualEvidenceResult:
    items: list[EvidenceItem]
    metadata: dict[str, Any]


class C07VisualEvidenceBuilder:
    def build(
        self,
        *,
        finding: Finding,
        group: InspectionItemGroup | None,
        source_pdf_path: str | None,
        safe_id: Callable[[str], str],
    ) -> C07VisualEvidenceResult | None:
        if not source_pdf_path or group is None or not group.pages:
            return None
        ...
```

Image item conventions:

```python
EvidenceItem(
    ref_id=f"c07_visual_page:{finding.id}:p{page_number}",
    source_type=EvidenceSourceType.IMAGE,
    title=f"C07 page image evidence p{page_number}",
    file_path=f"items/{safe_id(finding.id)}-c07-page-p{page_number}.png",
    page_number=page_number,
    section="c07_visual_page",
    metadata={
        "finding_id": finding.id,
        "check_id": "C07",
        "codex_image_input": True,
        "render_source": "source_pdf",
        "render_page_number": page_number,
    },
)
```

For crops, set `metadata["render_bbox"]`:

```python
metadata={
    "codex_image_input": True,
    "render_source": "source_pdf",
    "render_page_number": page_number,
    "render_bbox": [10.0, 50.0, 210.0, 80.0],
    "crop_kind": "item_group",
}
```

Use small bbox padding:

```python
def _pad_bbox(bbox: list[float], *, x_pad: float = 4.0, y_pad: float = 3.0) -> list[float]:
    x0, y0, x1, y1 = bbox
    return [max(0.0, x0 - x_pad), max(0.0, y0 - y_pad), x1 + x_pad, y1 + y_pad]
```

Use bbox union for group rows per page and for result/conclusion/remark columns.

- [ ] **Step 4: Run builder tests**

Run:

```bash
cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py -v
```

Expected: PASS.

## Task 4: Wire C07 Visual Items Into ReportCodexEvidenceBuilder

**Files:**
- Modify: `backend/app/application/report_codex_evidence_builder.py`
- Test: `backend/tests/application/test_report_codex_evidence_builder.py`

- [ ] **Step 1: Add C07 visual evidence refs to `_evidence_refs_for_finding()`**

For C07, after text/group evidence, add:

```python
for visual_item in self._c07_visual_items(finding, report, source_pdf_path=source_pdf_path):
    self._add_item(items_by_ref, visual_item, refs)
```

Add target metadata:

```python
if finding.check_id == "C07":
    c07_visual = self._c07_visual_metadata(finding, report, source_pdf_path=source_pdf_path)
    if c07_visual is not None:
        metadata["c07_visual_evidence"] = c07_visual
        metadata["evidence_has_c07_visual_input"] = c07_visual["has_visual_input"]
```

- [ ] **Step 2: Ensure no old-project path leaks**

Add assertions:

```python
dumped = json.dumps(bundle.evidence_package.model_dump(mode="json"), ensure_ascii=False)
assert "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13" not in dumped
assert str(source_pdf) in bundle.evidence_package.metadata["source_pdf_path"]
assert all(not item.file_path.startswith("/") for item in bundle.evidence_package.items if item.file_path)
```

- [ ] **Step 3: Run targeted tests**

Run:

```bash
cd backend && python -m pytest tests/application/test_report_codex_evidence_builder.py -v
```

Expected: PASS.

## Task 5: Verify Writer And Runner Image Materialization For C07

**Files:**
- Modify: `backend/tests/infrastructure/audit/test_evidence_package_writer.py`
- Modify: `backend/tests/application/test_codex_audit_service.py`

- [ ] **Step 1: Add writer test for multiple C07 image crops**

Use a one-page fixture PDF created by PyMuPDF in test, then build image items:

```python
def test_writer_materializes_c07_page_table_and_column_crops(tmp_path: Path) -> None:
    source_pdf = _write_one_page_pdf(tmp_path / "report.pdf")
    package = EvidencePackage(
        package_id="pkg",
        task_id="task",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        targets=[EvidenceTarget(target_id="target", target_type="inspection_item", check_id="C07", evidence_refs=["c07_visual_page:finding:p1"])],
        items=[
            EvidenceItem(
                ref_id="c07_visual_page:finding:p1",
                source_type=EvidenceSourceType.IMAGE,
                title="C07 page",
                file_path="items/finding-c07-page-p1.png",
                page_number=1,
                metadata={"codex_image_input": True, "render_page_number": 1},
            ),
            EvidenceItem(
                ref_id="c07_visual_result:finding:p1",
                source_type=EvidenceSourceType.IMAGE,
                title="C07 result crop",
                file_path="items/finding-c07-result-p1.png",
                page_number=1,
                metadata={"codex_image_input": True, "render_page_number": 1, "render_bbox": [10, 10, 100, 80]},
            ),
        ],
        metadata={"source_pdf_path": str(source_pdf)},
    )

    manifest = EvidencePackageWriter(tmp_path / "audit").write_package(package)

    assert "items/finding-c07-page-p1.png" in manifest.item_file_paths
    assert "items/finding-c07-result-p1.png" in manifest.item_file_paths
    assert (Path(manifest.root_dir) / "items" / "finding-c07-result-p1.png").is_file()
```

- [ ] **Step 2: Add audit service test that C07 images reach runner**

Extend existing `test_review_passes_workspace_image_paths_to_runner` or add:

```python
def test_review_passes_c07_visual_images_to_runner(tmp_path: Path, monkeypatch) -> None:
    package = _c07_package_with_image_items(tmp_path)
    request = _request_for_package(package)
    runner = RecordingRunner()

    results = CodexAuditService(
        evidence_writer=EvidencePackageWriter(tmp_path / "audit"),
        prompt_builder=PromptBuilder(),
        runner=runner,
    ).review(request, package)

    assert results[0].status == CodexReviewStatus.SUCCEEDED
    assert [path.name for path in runner.calls[0]["image_paths"]] == [
        "finding-c07-page-p1.png",
        "finding-c07-result-p1.png",
    ]
```

- [ ] **Step 3: Run writer/service tests**

Run:

```bash
cd backend && python -m pytest tests/infrastructure/audit/test_evidence_package_writer.py tests/application/test_codex_audit_service.py -v
```

Expected: PASS.

## Task 6: Update PromptBuilder For C07 Visual Review

**Files:**
- Modify: `backend/app/infrastructure/codex/prompt_builder.py`
- Modify: `backend/tests/infrastructure/codex/test_prompt_builder.py`

- [ ] **Step 1: Add failing prompt test**

```python
def test_prompt_instructs_c07_visual_table_review() -> None:
    prompt = PromptBuilder().build_review_prompt(_c07_visual_request(), _c07_visual_package())

    assert "C07" in prompt
    assert "table image" in prompt or "表格图片" in prompt
    assert "result column crop" in prompt or "检验结果列" in prompt
    assert "conclusion column crop" in prompt or "单项结论列" in prompt
    assert "remark column crop" in prompt or "备注列" in prompt
    assert "续页" in prompt
    assert "——" in prompt
    assert "/" in prompt
    assert "complex_matrix_table" in prompt
```

- [ ] **Step 2: Run failing prompt test**

Run:

```bash
cd backend && python -m pytest tests/infrastructure/codex/test_prompt_builder.py::test_prompt_instructs_c07_visual_table_review -v
```

Expected: FAIL until prompt instructions are added.

- [ ] **Step 3: Add concise instructions**

Append C07 visual instructions to task instructions:

```text
- 如果 C07 target 提供 table/page/row/column 图片，请优先结合图片核对当前 item_no 的所有检验结果、单项结论和备注。
- C07 图片 evidence 可能包括 page image、table image、item group crop、result column crop、conclusion column crop、remark column crop；请引用实际使用的 evidence refs。
- 跨页/续页 item 必须同时查看续页行图片和结构化 continuation rows。
- 首页符号说明中 “——” 表示此项不适用，“/” 表示此项空白；视觉判断必须结合该说明。
- complex_matrix_table=true 时不要按普通单行 C07 直接 confirm；应说明矩阵列映射是否可由图片稳定判断，证据不足时 uncertain。
```

- [ ] **Step 4: Run prompt tests**

Run:

```bash
cd backend && python -m pytest tests/infrastructure/codex/test_prompt_builder.py -v
```

Expected: PASS.

## Task 7: Preserve Output Schema And Finalization Boundaries

**Files:**
- Read only unless tests expose a contract failure:
  - `backend/app/infrastructure/codex/schemas/codex_review_output.schema.json`
  - `backend/app/infrastructure/codex/output_parser.py`
  - `backend/app/application/codex_audit_finalization.py`
- Modify tests only if necessary:
  - `backend/tests/infrastructure/codex/test_codex_review_output_schema.py`
  - `backend/tests/infrastructure/codex/test_output_parser.py`
  - `backend/tests/application/test_report_check_usecase.py`

- [ ] **Step 1: Confirm no C07-specific schema change is needed**

Run:

```bash
cd backend && python -m pytest tests/infrastructure/codex/test_codex_review_output_schema.py tests/infrastructure/codex/test_output_parser.py -v
```

Expected: PASS.

Rationale: C07 visual review can use existing `verdict`, `confidence`, `reasoning_summary`, `evidence_refs`, and existing `metadata.visual_evidence_quality`. Do not add C07-only schema fields unless a test proves the parser cannot carry required metadata.

- [ ] **Step 2: Add a usecase guard test that visual review does not change finalization**

```python
def test_c07_visual_uncertain_still_finalizes_to_manual_review_required() -> None:
    finding = _finding(
        check_id="C07",
        code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
        severity=FindingSeverity.WARN,
    )
    review = _codex_review(verdict=CodexReviewVerdict.UNCERTAIN, finding_id=finding.id)

    annotate_candidate_findings_with_codex_status([finding], [review], audit_scope="full")

    assert finding.metadata["final_status"] == "manual_review_required"
    assert finding.metadata["codex_verdict"] == "uncertain"
```

- [ ] **Step 3: Run report usecase/finalization tests**

Run:

```bash
cd backend && python -m pytest tests/application/test_report_check_usecase.py -v
```

Expected: PASS.

## Task 8: End-To-End Fake Review Fixtures

**Files:**
- Modify: `backend/tests/application/test_report_check_usecase.py`
- Modify: `backend/tests/api/` only if API serialization misses new metadata.

- [ ] **Step 1: Add fake-runner C07 visual refute fixture**

Create a fake Codex result for item 142/149-style extraction uncertainty:

```python
def test_report_check_c07_visual_refute_keeps_confirmed_errors_zero() -> None:
    fake_runner = FakeCodexRunner(
        review_overrides={
            "C07": {
                "verdict": "refute",
                "reasoning_summary": "视觉表格证据显示该 item 的检验结果列存在“符合要求”，单项结论为“符合”，规则候选的 all-placeholder 抽取不完整。",
                "evidence_refs": ["inspection_item:finding-c07", "c07_visual_result:finding-c07:p99", "c07_visual_conclusion:finding-c07:p99"],
            }
        }
    )

    result = _run_report_check_with_fake_codex(fake_runner)

    assert result.summary["confirmed_errors_count"] == 0
    assert result.summary["refuted_findings_count"] >= 1
```

- [ ] **Step 2: Add fake-runner complex matrix fixture**

```python
def test_report_check_c07_complex_matrix_visual_uncertain_remains_manual_review() -> None:
    fake_runner = FakeCodexRunner(
        review_overrides={
            "C07": {
                "verdict": "uncertain",
                "reasoning_summary": "矩阵表图片可见多列状态，但无法稳定确认普通 C07 行列映射。",
                "evidence_refs": ["inspection_item:finding-c07-59", "c07_visual_table:finding-c07-59:p42"],
            }
        }
    )

    result = _run_report_check_with_complex_matrix_fake_codex(fake_runner)

    assert result.summary["confirmed_errors_count"] == 0
    assert result.summary["manual_review_required_count"] >= 1
```

- [ ] **Step 3: Run API/report tests**

Run:

```bash
cd backend && python -m pytest tests/application/test_report_check_usecase.py tests/api -v
```

Expected: PASS.

## Task 9: Documentation

**Files:**
- Modify: `docs/current-status.md`
- Modify: `docs/tasks.md`
- Modify: `docs/codex-audit-local-e2e.md`
- Modify: `docs/quality-noise-reduction-plan.md`

- [ ] **Step 1: Add T-CODEX-EVIDENCE-06 to `docs/tasks.md`**

Record:

```markdown
### T-CODEX-EVIDENCE-06：C07 table visual evidence / row-crop review
- 目标：为 C07 剩余 12 条 manual review target 提供 page/table/item-group/result/conclusion/remark visual evidence，让 Codex CLI 可视觉核对检验结果、单项结论、备注和续页行。
- 不允许做：不处理 C04；不改 finalization；不调用真实 Codex CLI 自动测试；不修改旧项目目录。
- 验收标准：Done when C07 target metadata 和 evidence package 包含 workspace-local image refs，runner 收到 image paths，prompt 指示 Codex 视觉核对 C07，fake tests 覆盖 refute/manual complex matrix 场景。
- 完成状态：[ ]
```

- [ ] **Step 2: Update local E2E docs with targeted command**

Add recommended validation command:

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C07 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

- [ ] **Step 3: Run markdown/diff check**

Run:

```bash
git diff --check
```

Expected: PASS.

## Task 10: Full Verification

Run targeted tests first:

```bash
cd backend && python -m pytest \
  tests/infrastructure/pdf/test_pymupdf_parser.py \
  tests/infrastructure/report/test_inspection_table_extractor.py \
  tests/application/test_report_codex_evidence_builder.py \
  tests/application/test_codex_audit_service.py \
  tests/infrastructure/audit/test_evidence_package_writer.py \
  tests/infrastructure/codex/test_prompt_builder.py \
  -v
```

Run broader backend checks:

```bash
cd backend && python -m pytest \
  tests/application/test_report_check_usecase.py \
  tests/rules/report/test_c07_item_conclusion.py \
  tests/api \
  -v
```

Run full backend suite:

```bash
cd backend && python -m pytest tests/ -v
```

Run frontend build:

```bash
cd frontend && npm run build
```

Run final whitespace check:

```bash
git diff --check
```

Expected: all commands PASS.

## Manual Validation After Merge

Do not run this during automated implementation. After tests pass and the user explicitly requests real validation, run C07 targeted visual validation:

```bash
cd /Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3

REPORT_FILE="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材/report/2795/QW2025-2795 Draft.pdf"

PYTHON_BIN=python \
ENABLE_CODEX_AUDIT_LOCAL_E2E=1 \
CODEX_AUDIT_INCLUDED_CHECK_IDS=C07 \
CODEX_AUDIT_MAX_TARGETS_PER_BATCH=1 \
CODEX_AUDIT_TIMEOUT_SECONDS=300 \
START_BACKEND=1 \
BACKEND_PORT=8011 \
BASE_URL=http://127.0.0.1:8011 \
TASK_TYPE=report-check \
REPORT_FILE="$REPORT_FILE" \
bash scripts/run-codex-audit-local-e2e.sh
```

Acceptance target:

- C07 `manual_review_required_count` should decrease from 12 if visual evidence is sufficient.
- `confirmed_errors_count` should remain 0 unless row/table images clearly prove a real report error.
- Item 59 should remain `manual_review_required` or enter a future specialized matrix-review task, not ordinary C07 confirmed.
- If C07 remains at 12, extract by `item_no`, `finding_code`, image evidence availability, and missing crop reasons. That result should drive T-CODEX-EVIDENCE-06B, not silent finalization changes.

## Self-Review

- Spec coverage:
  - Page/table/item group/result/conclusion/remark visual evidence is covered by Tasks 2-4.
  - Codex CLI image input wiring is covered by Task 5 and reuses existing C04 image path plumbing.
  - C07 prompt instructions are covered by Task 6.
  - Item 59 complex matrix safety is covered by Tasks 3, 6, and 8.
  - No C04/finalization changes are enforced by Scope and Task 7.
- Placeholder scan:
  - The plan uses concrete file paths, test names, commands, and expected outcomes.
  - No task says “handle edge cases” without specifying the concrete edge.
- Type consistency:
  - Image evidence uses existing `EvidenceItem.file_path`, `EvidenceSourceType.IMAGE`, and `metadata.codex_image_input`.
  - C07 metadata is namespaced under `c07_visual_evidence` to avoid conflicting with C04 label metadata.
