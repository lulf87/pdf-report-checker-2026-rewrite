from pathlib import Path
import subprocess

import fitz
import pytest

from app.domain.evidence_package import (
    EvidenceItem,
    EvidencePackage,
    EvidencePackageKind,
    EvidenceSourceType,
    EvidenceTarget,
    evidence_item_from_text,
)
from app.infrastructure.audit.evidence_package_writer import EvidencePackageWriter


OLD_PROJECT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"


def _package(*, text: str = "第三页型号规格: ABC-2") -> EvidencePackage:
    return EvidencePackage(
        package_id="pkg-1",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        targets=[
            EvidenceTarget(
                target_id="target-c02-1",
                target_type="label_ocr",
                check_id="C02",
                finding_id="finding-c02-1",
                finding_code="C02_FIELD_MISMATCH",
                summary="复核第三页字段与标签 OCR 是否不一致。",
                evidence_refs=["ev-text-1"],
            )
        ],
        items=[
            evidence_item_from_text(
                ref_id="ev-text-1",
                source_type=EvidenceSourceType.PDF_TEXT,
                text=text,
                title="第三页字段片段",
                page_number=3,
                section="第三页",
            )
        ],
    )


def test_writer_creates_audit_workspace_under_tmp_path(tmp_path) -> None:
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    manifest = writer.write_package(_package())

    expected_input_dir = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    assert writer.package_dir("task-1", "pkg-1") == expected_input_dir
    assert Path(manifest.root_dir) == expected_input_dir
    assert expected_input_dir.is_dir()


def test_write_package_writes_package_json_and_manifest_json(tmp_path) -> None:
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    manifest = writer.write_package(_package())
    root_dir = Path(manifest.root_dir)

    assert manifest.package_json_path == "evidence_package.json"
    assert (root_dir / "evidence_package.json").is_file()
    assert (root_dir / "manifest.json").is_file()
    assert manifest.package_id == "pkg-1"
    assert manifest.task_id == "task-1"


def test_read_package_restores_evidence_package_from_manifest_or_package_json(tmp_path) -> None:
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")
    package = _package()

    manifest = writer.write_package(package)
    root_dir = Path(manifest.root_dir)

    assert writer.read_package(manifest) == package
    assert writer.read_package(root_dir / "manifest.json") == package
    assert writer.read_package(root_dir / "evidence_package.json") == package


def test_item_file_paths_are_relative_and_do_not_leak_project_source_paths(tmp_path) -> None:
    long_text = "第三页字段片段 " * 20
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit", long_text_threshold=20)

    manifest = writer.write_package(_package(text=long_text))

    assert manifest.item_file_paths == ["items/ev-text-1.txt"]
    for file_path in manifest.item_file_paths:
        assert not Path(file_path).is_absolute()
        assert OLD_PROJECT not in file_path
        assert NEW_PROJECT not in file_path
        assert (Path(manifest.root_dir) / file_path).is_file()


def test_writer_automatically_creates_missing_directories(tmp_path) -> None:
    audit_root = tmp_path / "missing" / "runtime" / "codex_audit"
    writer = EvidencePackageWriter(audit_root)

    manifest = writer.write_package(_package())

    assert audit_root.is_dir()
    assert Path(manifest.root_dir).is_dir()
    assert (Path(manifest.root_dir) / "manifest.json").is_file()


def test_writer_rejects_path_traversal_for_task_or_package_id(tmp_path) -> None:
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    with pytest.raises(ValueError, match="invalid task id"):
        writer.package_dir("../task", "pkg-1")

    bad_package = _package().model_copy(update={"package_id": "../pkg"})
    with pytest.raises(ValueError, match="invalid package id"):
        writer.write_package(bad_package)


def test_long_text_items_are_written_to_dedicated_text_files(tmp_path) -> None:
    long_text = "这是一段需要单独写入文本文件的长证据。" * 10
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit", long_text_threshold=20)

    manifest = writer.write_package(_package(text=long_text))
    root_dir = Path(manifest.root_dir)
    text_path = root_dir / "items" / "ev-text-1.txt"
    restored = writer.read_package(manifest)

    assert text_path.read_text(encoding="utf-8") == long_text
    assert restored.items[0].text is None
    assert restored.items[0].file_path == "items/ev-text-1.txt"
    assert restored.items[0].metadata["externalized_text"] is True
    assert manifest.metadata["externalized_text_count"] == 1
    assert manifest.metadata["externalized_text_bytes"] == text_path.stat().st_size


def test_writer_does_not_call_codex_cli(tmp_path, monkeypatch) -> None:
    def fail_if_subprocess_is_called(*args, **kwargs):
        raise AssertionError("EvidencePackageWriter must not call Codex CLI or subprocesses")

    monkeypatch.setattr(subprocess, "run", fail_if_subprocess_is_called)
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    writer.write_package(_package())


def test_writer_renders_label_image_items_inside_evidence_workspace(tmp_path) -> None:
    source_pdf = tmp_path / "source.pdf"
    document = fitz.open()
    page = document.new_page(width=200, height=120)
    page.insert_text((20, 40), "图2 输注泵中文标签样张")
    document.save(source_pdf)
    document.close()
    package = _package().model_copy(
        update={
            "metadata": {"source_pdf_path": str(source_pdf)},
            "items": [
                EvidenceItem(
                    ref_id="label_image:finding-1",
                    source_type=EvidenceSourceType.IMAGE,
                    title="C04 label page image evidence",
                    file_path="items/label_image-finding-1.png",
                    page_number=1,
                    metadata={
                        "codex_image_input": True,
                        "render_page_number": 1,
                    },
                )
            ],
            "targets": [
                EvidenceTarget(
                    target_id="target-c04-1",
                    target_type="label_ocr",
                    check_id="C04",
                    finding_id="finding-1",
                    finding_code="SAMPLE_FIELD_MISSING_IN_LABEL",
                    evidence_refs=["label_image:finding-1"],
                )
            ],
        }
    )
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    manifest = writer.write_package(package)
    root_dir = Path(manifest.root_dir)
    image_path = root_dir / "items" / "label_image-finding-1.png"
    package_json = (root_dir / "evidence_package.json").read_text(encoding="utf-8")

    assert manifest.item_file_paths == ["items/label_image-finding-1.png"]
    assert image_path.is_file()
    assert image_path.read_bytes().startswith(b"\x89PNG")
    assert str(source_pdf) not in package_json
    assert OLD_PROJECT not in package_json
    assert NEW_PROJECT not in package_json
    assert manifest.metadata["image_items_count"] == 1
    assert manifest.metadata["materialized_image_count"] == 1
    assert manifest.metadata["materialized_image_bytes"] == image_path.stat().st_size
    assert manifest.metadata["image_materialization_seconds"] >= 0


def test_writer_materializes_c07_page_only_image_item_inside_workspace(tmp_path) -> None:
    source_pdf = _source_pdf(tmp_path)
    package = _c07_image_package(
        source_pdf=source_pdf,
        items=[
            EvidenceItem(
                ref_id="c07_visual_page:finding-1:p22",
                source_type=EvidenceSourceType.IMAGE,
                title="C07 page image evidence",
                file_path="items/finding-1-c07-page-p1.png",
                page_number=1,
                metadata={"codex_image_input": True, "render_page_number": 1, "crop_kind": "page"},
            )
        ],
    )
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    manifest = writer.write_package(package)
    root_dir = Path(manifest.root_dir)

    assert manifest.item_file_paths == ["items/finding-1-c07-page-p1.png"]
    assert (root_dir / "items" / "finding-1-c07-page-p1.png").read_bytes().startswith(b"\x89PNG")
    assert all(not Path(path).is_absolute() for path in manifest.item_file_paths)


def test_writer_materializes_c07_crop_bbox_image_item_inside_workspace(tmp_path) -> None:
    source_pdf = _source_pdf(tmp_path)
    package = _c07_image_package(
        source_pdf=source_pdf,
        items=[
            EvidenceItem(
                ref_id="c07_visual_result:finding-1:p1",
                source_type=EvidenceSourceType.IMAGE,
                title="C07 result column crop evidence",
                file_path="items/finding-1-c07-result-p1.png",
                page_number=1,
                metadata={
                    "codex_image_input": True,
                    "render_page_number": 1,
                    "crop_bbox": [20, 20, 90, 80],
                    "crop_kind": "result",
                },
            )
        ],
    )
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    manifest = writer.write_package(package)
    root_dir = Path(manifest.root_dir)
    restored = writer.read_package(manifest)
    image_item = restored.items[0]

    assert manifest.item_file_paths == ["items/finding-1-c07-result-p1.png"]
    assert (root_dir / "items" / "finding-1-c07-result-p1.png").read_bytes().startswith(b"\x89PNG")
    assert image_item.metadata["materialized_image"] is True
    assert image_item.metadata["image_file_path"] == "items/finding-1-c07-result-p1.png"


def test_writer_materializes_c07_complex_matrix_image_items_inside_workspace(tmp_path) -> None:
    source_pdf = _source_pdf(tmp_path, page_count=2)
    items = [
        _c07_complex_matrix_image_item("page", page_number=1),
        _c07_complex_matrix_image_item("table", page_number=1, bbox=[10, 10, 220, 140]),
        _c07_complex_matrix_image_item("header", page_number=1, bbox=[10, 10, 220, 35]),
        _c07_complex_matrix_image_item("body", page_number=1, bbox=[10, 35, 220, 120]),
        _c07_complex_matrix_image_item("result", page_number=1, bbox=[100, 35, 170, 120]),
        _c07_complex_matrix_image_item("conclusion", page_number=1, bbox=[170, 35, 210, 120]),
        _c07_complex_matrix_image_item("continuation", page_number=2, bbox=[10, 10, 220, 140]),
    ]
    package = _c07_image_package(source_pdf=source_pdf, items=items)
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    manifest = writer.write_package(package)
    root_dir = Path(manifest.root_dir)
    restored = writer.read_package(manifest)

    assert [Path(path).name for path in manifest.item_file_paths] == [
        "finding-59-c07-matrix-page-p1.png",
        "finding-59-c07-matrix-table-p1.png",
        "finding-59-c07-matrix-header-p1.png",
        "finding-59-c07-matrix-body-p1.png",
        "finding-59-c07-matrix-result-p1.png",
        "finding-59-c07-matrix-conclusion-p1.png",
        "finding-59-c07-matrix-continuation-p2.png",
    ]
    assert all((root_dir / path).read_bytes().startswith(b"\x89PNG") for path in manifest.item_file_paths)
    assert all(not Path(path).is_absolute() for path in manifest.item_file_paths)
    assert all(OLD_PROJECT not in path and NEW_PROJECT not in path for path in manifest.item_file_paths)
    restored_matrix_items = [item for item in restored.items if item.section == "c07_complex_matrix_visual"]
    assert {item.metadata["matrix_evidence_role"] for item in restored_matrix_items} == {
        "page",
        "table",
        "header",
        "body",
        "result",
        "conclusion",
        "continuation",
    }
    assert all(item.metadata["materialized_image"] is True for item in restored_matrix_items)


def test_writer_records_c07_complex_matrix_materialization_diagnostics_without_source_pdf(tmp_path) -> None:
    package = _c07_image_package(
        source_pdf=None,
        items=[_c07_complex_matrix_image_item("page", page_number=1)],
    )
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    manifest = writer.write_package(package)
    restored = writer.read_package(manifest)

    assert manifest.item_file_paths == []
    assert manifest.metadata["image_materialization_diagnostics"][0]["code"] == "SOURCE_PDF_MISSING"
    assert restored.items[0].metadata["image_materialization_error"]["code"] == "SOURCE_PDF_MISSING"


def test_writer_records_c07_complex_matrix_materialization_diagnostics_for_invalid_bbox(tmp_path) -> None:
    source_pdf = _source_pdf(tmp_path)
    package = _c07_image_package(
        source_pdf=source_pdf,
        items=[_c07_complex_matrix_image_item("result", page_number=1, bbox=[90, 80, 20, 20])],
    )
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    manifest = writer.write_package(package)
    restored = writer.read_package(manifest)

    assert manifest.item_file_paths == []
    assert manifest.metadata["image_materialization_diagnostics"][0]["code"] == "INVALID_IMAGE_BBOX"
    assert restored.items[0].metadata["image_materialization_error"]["code"] == "INVALID_IMAGE_BBOX"


def test_writer_records_image_materialization_diagnostics_without_source_pdf(tmp_path) -> None:
    package = _c07_image_package(
        source_pdf=None,
        items=[
            EvidenceItem(
                ref_id="c07_visual_page:finding-1:p1",
                source_type=EvidenceSourceType.IMAGE,
                title="C07 page image evidence",
                file_path="items/finding-1-c07-page-p1.png",
                page_number=1,
                metadata={"codex_image_input": True, "render_page_number": 1},
            )
        ],
    )
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    manifest = writer.write_package(package)
    restored = writer.read_package(manifest)

    assert manifest.item_file_paths == []
    assert manifest.metadata["image_materialization_diagnostics"][0]["code"] == "SOURCE_PDF_MISSING"
    assert restored.items[0].metadata["materialized_image"] is False
    assert restored.items[0].metadata["image_materialization_error"]["code"] == "SOURCE_PDF_MISSING"


def test_writer_records_image_materialization_diagnostics_for_invalid_crop_bbox(tmp_path) -> None:
    source_pdf = _source_pdf(tmp_path)
    package = _c07_image_package(
        source_pdf=source_pdf,
        items=[
            EvidenceItem(
                ref_id="c07_visual_result:finding-1:p1",
                source_type=EvidenceSourceType.IMAGE,
                title="C07 invalid result crop evidence",
                file_path="items/finding-1-c07-result-p1.png",
                page_number=1,
                metadata={
                    "codex_image_input": True,
                    "render_page_number": 1,
                    "crop_bbox": [90, 80, 20, 20],
                },
            )
        ],
    )
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    manifest = writer.write_package(package)
    root_dir = Path(manifest.root_dir)
    restored = writer.read_package(manifest)

    assert manifest.item_file_paths == []
    assert not (root_dir / "items" / "finding-1-c07-result-p1.png").exists()
    assert manifest.metadata["image_materialization_diagnostics"][0]["code"] == "INVALID_IMAGE_BBOX"
    assert restored.items[0].metadata["image_materialization_error"]["code"] == "INVALID_IMAGE_BBOX"


def _source_pdf(tmp_path: Path, *, page_count: int = 1) -> Path:
    source_pdf = tmp_path / "source.pdf"
    document = fitz.open()
    for index in range(page_count):
        page = document.new_page(width=240, height=160)
        page.insert_text((20, 40), f"序号 59 漏电流矩阵 p{index + 1} 检验结果 符合要求 单项结论 符合")
    document.save(source_pdf)
    document.close()
    return source_pdf


def _c07_complex_matrix_image_item(
    role: str,
    *,
    page_number: int,
    bbox: list[float] | None = None,
) -> EvidenceItem:
    metadata = {
        "codex_image_input": True,
        "render_page_number": page_number,
        "crop_kind": f"complex_matrix_{role}",
        "matrix_evidence_role": role,
    }
    if bbox is not None:
        metadata["crop_bbox"] = bbox
    return EvidenceItem(
        ref_id=f"c07_complex_matrix_{role}:finding-59:p{page_number}",
        source_type=EvidenceSourceType.IMAGE,
        title=f"C07 complex matrix {role} image evidence",
        file_path=f"items/finding-59-c07-matrix-{role}-p{page_number}.png",
        page_number=page_number,
        section="c07_complex_matrix_visual",
        metadata=metadata,
    )


def _c07_image_package(*, source_pdf: Path | None, items: list[EvidenceItem]) -> EvidencePackage:
    return EvidencePackage(
        package_id="pkg-c07",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        metadata={"source_pdf_path": str(source_pdf)} if source_pdf is not None else {},
        targets=[
            EvidenceTarget(
                target_id="target-c07-1",
                target_type="inspection_item",
                check_id="C07",
                finding_id="finding-1",
                finding_code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
                evidence_refs=[item.ref_id for item in items],
            )
        ],
        items=items,
    )
