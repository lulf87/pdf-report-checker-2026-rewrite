from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.domain.result import CheckResult
from app.domain.task import InputFileRef


@dataclass(frozen=True)
class StoredUpload:
    path: Path
    input_file: InputFileRef


@dataclass(frozen=True)
class StoredResult:
    path: Path
    check_count: int


@dataclass(frozen=True)
class StoredExport:
    path: Path
    content_type: str


class LocalFileStore:
    """Local runtime storage adapter with path-bound writes."""

    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir).resolve()

    def ensure_root(self) -> Path:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        return self.root_dir

    @property
    def uploads_dir(self) -> Path:
        return self.root_dir / "uploads"

    @property
    def results_dir(self) -> Path:
        return self.root_dir / "results"

    @property
    def exports_dir(self) -> Path:
        return self.root_dir / "exports"

    def resolve_under_root(self, relative_path: Path | str) -> Path:
        target = (self.root_dir / relative_path).resolve()
        if not target.is_relative_to(self.root_dir):
            raise ValueError("path must stay under local file store root")
        return target

    def save_upload(
        self,
        *,
        task_id: str,
        file_name: str,
        content: bytes,
        content_type: str = "application/pdf",
        category: str | None = None,
    ) -> StoredUpload:
        safe_name = self._safe_file_name(file_name)
        parts = ["uploads", self._safe_task_id(task_id)]
        if category:
            parts.append(self._safe_category(category))
        relative_path = Path(*parts) / safe_name
        path = self.resolve_under_root(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        file_ref = InputFileRef(
            file_id=f"{task_id}:{safe_name}",
            file_name=safe_name,
            content_type=content_type or "application/octet-stream",
        )
        return StoredUpload(path=path, input_file=file_ref)

    def get_upload_path(self, *, task_id: str, file_name: str, category: str | None = None) -> Path:
        safe_name = self._safe_file_name(file_name)
        parts = ["uploads", self._safe_task_id(task_id)]
        if category:
            parts.append(self._safe_category(category))
        path = self.resolve_under_root(Path(*parts) / safe_name)
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    def save_result_json(self, *, task_id: str, check_results: list[CheckResult]) -> StoredResult:
        safe_task_id = self._safe_task_id(task_id)
        path = self.resolve_under_root(Path("results") / f"{safe_task_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [result.model_dump(mode="json") for result in check_results]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return StoredResult(path=path, check_count=len(check_results))

    def read_result_json(self, *, task_id: str) -> list[CheckResult]:
        safe_task_id = self._safe_task_id(task_id)
        path = self.resolve_under_root(Path("results") / f"{safe_task_id}.json")
        if not path.is_file():
            raise FileNotFoundError(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return [CheckResult.model_validate(item) for item in data]

    def save_export(
        self,
        *,
        task_id: str,
        file_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> StoredExport:
        safe_task_id = self._safe_task_id(task_id)
        safe_name = self._safe_file_name(file_name)
        path = self.resolve_under_root(Path("exports") / safe_task_id / safe_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredExport(path=path, content_type=content_type or "application/octet-stream")

    def read_export(self, *, task_id: str, file_name: str) -> bytes:
        safe_task_id = self._safe_task_id(task_id)
        safe_name = self._safe_file_name(file_name)
        path = self.resolve_under_root(Path("exports") / safe_task_id / safe_name)
        if not path.is_file():
            raise FileNotFoundError(path)
        return path.read_bytes()

    def _safe_file_name(self, file_name: str) -> str:
        name = Path(file_name or "").name
        if not name or name in {".", ".."}:
            raise ValueError("file name is required")
        if name != file_name:
            raise ValueError("file name must not contain path separators")
        if "\x00" in name:
            raise ValueError("file name must not contain NUL bytes")
        return name

    def _safe_task_id(self, task_id: str) -> str:
        if not task_id or not re.fullmatch(r"[A-Za-z0-9_.:-]+", task_id):
            raise ValueError("invalid task id for local file storage")
        return task_id

    def _safe_category(self, category: str) -> str:
        if not category or not re.fullmatch(r"[A-Za-z0-9_.:-]+", category):
            raise ValueError("invalid upload category")
        return category


__all__ = ["LocalFileStore", "StoredExport", "StoredResult", "StoredUpload"]
