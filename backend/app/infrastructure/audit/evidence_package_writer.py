from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import fitz

from app.domain.evidence_package import EvidencePackage, EvidencePackageManifest, EvidenceSourceType


class EvidencePackageWriter:
    """Writes Codex audit evidence packages into a path-bound runtime workspace."""

    def __init__(self, audit_root: Path | str, *, long_text_threshold: int = 4000) -> None:
        self.audit_root = Path(audit_root).resolve()
        self.long_text_threshold = long_text_threshold

    def package_dir(self, task_id: str, package_id: str) -> Path:
        safe_task_id = self._safe_id(task_id, label="task id")
        safe_package_id = self._safe_id(package_id, label="package id")
        return self._resolve_under_audit_root(Path(safe_task_id) / safe_package_id / "input")

    def write_package(self, package: EvidencePackage) -> EvidencePackageManifest:
        input_dir = self.package_dir(package.task_id, package.package_id)
        input_dir.mkdir(parents=True, exist_ok=True)

        package_to_write = package.model_copy(deep=True)
        source_pdf_path = self._consume_source_pdf_path(package_to_write)
        image_diagnostics: list[dict[str, Any]] = []
        image_started = time.perf_counter()
        item_file_paths = self._materialize_image_items(package_to_write, input_dir, source_pdf_path, image_diagnostics)
        image_materialization_seconds = time.perf_counter() - image_started
        externalized_paths = self._externalize_long_text_items(package_to_write, input_dir)
        item_file_paths.extend(externalized_paths)
        if image_diagnostics:
            package_to_write.metadata["image_materialization_diagnostics"] = image_diagnostics

        package_json_path = input_dir / "evidence_package.json"
        package_json_path.write_text(
            json.dumps(package_to_write.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        manifest_metadata = {
            "schema_version": package.schema_version,
            "kind": package.kind.value,
            "image_materialization_seconds": round(max(0.0, image_materialization_seconds), 6),
            "image_items_count": self._image_items_count(package),
            "materialized_image_count": len(item_file_paths) - len(externalized_paths),
            "materialized_image_bytes": self._file_size_total(input_dir, item_file_paths[: len(item_file_paths) - len(externalized_paths)]),
            "externalized_text_count": len(externalized_paths),
            "externalized_text_bytes": self._file_size_total(input_dir, externalized_paths),
        }
        if image_diagnostics:
            manifest_metadata["image_materialization_diagnostics"] = image_diagnostics
        manifest = EvidencePackageManifest(
            package_id=package.package_id,
            task_id=package.task_id,
            root_dir=str(input_dir),
            package_json_path="evidence_package.json",
            item_file_paths=item_file_paths,
            metadata=manifest_metadata,
        )
        (input_dir / "manifest.json").write_text(
            json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest

    def _image_items_count(self, package: EvidencePackage) -> int:
        return sum(
            1
            for item in package.items
            if item.file_path
            and item.source_type == EvidenceSourceType.IMAGE
            and item.metadata.get("codex_image_input") is True
        )

    def _file_size_total(self, input_dir: Path, paths: list[str]) -> int:
        total = 0
        for file_path in paths:
            path = input_dir / file_path
            if path.is_file():
                total += path.stat().st_size
        return total

    def _consume_source_pdf_path(self, package: EvidencePackage) -> Path | None:
        value = package.metadata.pop("source_pdf_path", None)
        if not isinstance(value, str) or not value.strip():
            return None
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    def _materialize_image_items(
        self,
        package: EvidencePackage,
        input_dir: Path,
        source_pdf_path: Path | None,
        diagnostics: list[dict[str, Any]],
    ) -> list[str]:
        item_file_paths: list[str] = []
        image_items = [
            item
            for item in package.items
            if item.file_path
            and item.source_type == EvidenceSourceType.IMAGE
            and item.metadata.get("codex_image_input") is True
        ]
        if not image_items:
            return item_file_paths
        if source_pdf_path is None:
            for item in image_items:
                self._record_image_materialization_failure(
                    item,
                    diagnostics,
                    code="SOURCE_PDF_MISSING",
                    message="Image evidence item requires package.metadata.source_pdf_path.",
                )
            return item_file_paths

        document = fitz.open(str(source_pdf_path))
        try:
            for item in image_items:
                assert item.file_path is not None
                relative_path = Path(item.file_path)
                output_path = self._resolve_under_dir(input_dir, relative_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    page_number = self._image_render_page_number(item.metadata, item.page_number)
                except ValueError as exc:
                    self._record_image_materialization_failure(
                        item,
                        diagnostics,
                        code="INVALID_IMAGE_PAGE_NUMBER",
                        message=str(exc),
                    )
                    continue
                if page_number > len(document):
                    self._record_image_materialization_failure(
                        item,
                        diagnostics,
                        code="INVALID_IMAGE_PAGE_NUMBER",
                        message=f"render_page_number={page_number} exceeds source PDF page count.",
                    )
                    continue
                page = document[page_number - 1]
                try:
                    clip = self._image_render_clip(item.metadata)
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip)
                    pixmap.save(output_path)
                except ValueError as exc:
                    self._record_image_materialization_failure(
                        item,
                        diagnostics,
                        code="INVALID_IMAGE_BBOX",
                        message=str(exc),
                    )
                    continue
                item.metadata = {
                    **item.metadata,
                    "materialized_image": True,
                    "image_file_path": relative_path.as_posix(),
                }
                item_file_paths.append(relative_path.as_posix())
        finally:
            document.close()

        return item_file_paths

    def _image_render_page_number(self, metadata: dict[str, Any], fallback: int | None) -> int:
        value = metadata.get("render_page_number") or fallback
        if isinstance(value, int) and value > 0:
            return value
        if isinstance(value, str) and value.isdigit() and int(value) > 0:
            return int(value)
        raise ValueError("image evidence item requires a positive render_page_number")

    def _image_render_clip(self, metadata: dict[str, Any]) -> fitz.Rect | None:
        value = metadata.get("render_bbox")
        if value is None:
            value = metadata.get("crop_bbox")
        if value is None:
            return None
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            raise ValueError("image evidence bbox must contain four numbers")
        try:
            x0, y0, x1, y1 = (float(part) for part in value)
        except (TypeError, ValueError):
            raise ValueError("image evidence bbox must contain four numbers")
        if x1 <= x0 or y1 <= y0:
            raise ValueError("image evidence bbox must have positive width and height")
        return fitz.Rect(x0, y0, x1, y1)

    def _record_image_materialization_failure(
        self,
        item: Any,
        diagnostics: list[dict[str, Any]],
        *,
        code: str,
        message: str,
    ) -> None:
        diagnostic = {
            "ref_id": item.ref_id,
            "file_path": item.file_path,
            "code": code,
            "message": message,
        }
        item.metadata = {
            **item.metadata,
            "materialized_image": False,
            "image_materialization_error": diagnostic,
        }
        diagnostics.append(diagnostic)

    def read_package(self, manifest_or_path: EvidencePackageManifest | Path | str) -> EvidencePackage:
        if isinstance(manifest_or_path, EvidencePackageManifest):
            return self._read_package_from_manifest(manifest_or_path)

        path = self._resolve_existing_under_audit_root(Path(manifest_or_path))
        if path.is_dir():
            return self._read_package_from_manifest_path(path / "manifest.json")
        if path.name == "evidence_package.json":
            return self._read_package_json(path)
        return self._read_package_from_manifest_path(path)

    def _externalize_long_text_items(self, package: EvidencePackage, input_dir: Path) -> list[str]:
        item_file_paths: list[str] = []
        for item in package.items:
            if item.text is None or item.file_path is not None:
                continue
            if len(item.text) <= self.long_text_threshold:
                continue

            relative_path = Path("items") / f"{self._safe_file_stem(item.ref_id)}.txt"
            text_path = self._resolve_under_dir(input_dir, relative_path)
            text_path.parent.mkdir(parents=True, exist_ok=True)
            text_path.write_text(item.text, encoding="utf-8")

            item.text = None
            item.file_path = relative_path.as_posix()
            item.metadata = {
                **item.metadata,
                "externalized_text": True,
                "text_file_path": relative_path.as_posix(),
            }
            item_file_paths.append(relative_path.as_posix())
        return item_file_paths

    def _read_package_from_manifest_path(self, manifest_path: Path) -> EvidencePackage:
        path = self._resolve_existing_under_audit_root(manifest_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        manifest = EvidencePackageManifest.model_validate(data)
        return self._read_package_from_manifest(manifest)

    def _read_package_from_manifest(self, manifest: EvidencePackageManifest) -> EvidencePackage:
        root_dir = self._resolve_existing_under_audit_root(Path(manifest.root_dir))
        package_path = self._resolve_under_dir(root_dir, manifest.package_json_path)
        if not package_path.is_file():
            raise FileNotFoundError(package_path)
        return self._read_package_json(package_path)

    def _read_package_json(self, path: Path) -> EvidencePackage:
        package_path = self._resolve_existing_under_audit_root(path)
        if not package_path.is_file():
            raise FileNotFoundError(package_path)
        data = json.loads(package_path.read_text(encoding="utf-8"))
        return EvidencePackage.model_validate(data)

    def _resolve_under_audit_root(self, relative_path: Path | str) -> Path:
        path = Path(relative_path)
        target = path.resolve() if path.is_absolute() else (self.audit_root / path).resolve()
        if not target.is_relative_to(self.audit_root):
            raise ValueError("path must stay under evidence audit root")
        return target

    def _resolve_existing_under_audit_root(self, path: Path) -> Path:
        target = self._resolve_under_audit_root(path)
        if not target.exists():
            raise FileNotFoundError(target)
        return target

    def _resolve_under_dir(self, root_dir: Path, relative_path: Path | str) -> Path:
        path = Path(relative_path)
        target = path.resolve() if path.is_absolute() else (root_dir / path).resolve()
        if not target.is_relative_to(root_dir):
            raise ValueError("path must stay under evidence package input directory")
        if not target.is_relative_to(self.audit_root):
            raise ValueError("path must stay under evidence audit root")
        return target

    def _safe_id(self, value: str, *, label: str) -> str:
        if not value or value in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9_.:-]+", value):
            raise ValueError(f"invalid {label}")
        return value

    def _safe_file_stem(self, ref_id: str) -> str:
        stem = re.sub(r"[^A-Za-z0-9_.:-]+", "_", ref_id).strip("._")
        return stem or "evidence-item"


__all__ = ["EvidencePackageWriter"]
