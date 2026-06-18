from pathlib import Path
import subprocess

import pytest

from app.domain.evidence_package import (
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


def test_writer_does_not_call_codex_cli(tmp_path, monkeypatch) -> None:
    def fail_if_subprocess_is_called(*args, **kwargs):
        raise AssertionError("EvidencePackageWriter must not call Codex CLI or subprocesses")

    monkeypatch.setattr(subprocess, "run", fail_if_subprocess_is_called)
    writer = EvidencePackageWriter(tmp_path / "runtime" / "codex_audit")

    writer.write_package(_package())
