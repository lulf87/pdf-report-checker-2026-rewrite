from __future__ import annotations

import json
import re
from pathlib import Path

from app.domain.evidence_package import EvidencePackage, EvidencePackageManifest


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
        item_file_paths = self._externalize_long_text_items(package_to_write, input_dir)

        package_json_path = input_dir / "evidence_package.json"
        package_json_path.write_text(
            json.dumps(package_to_write.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        manifest = EvidencePackageManifest(
            package_id=package.package_id,
            task_id=package.task_id,
            root_dir=str(input_dir),
            package_json_path="evidence_package.json",
            item_file_paths=item_file_paths,
            metadata={
                "schema_version": package.schema_version,
                "kind": package.kind.value,
            },
        )
        (input_dir / "manifest.json").write_text(
            json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest

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
