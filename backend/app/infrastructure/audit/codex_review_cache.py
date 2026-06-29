from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.domain.codex_review import CodexReviewRequest, CodexReviewResult, CodexReviewStatus, CodexReviewVerdict
from app.domain.evidence_package import EvidencePackage


UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


class CodexReviewCache:
    """Filesystem cache for schema-valid succeeded Codex reviews."""

    def __init__(self, cache_root: Path | str) -> None:
        self.cache_root = Path(cache_root).resolve()

    def key_for(
        self,
        *,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
        prompt: str,
        schema_text: str,
        image_paths: list[Path],
    ) -> str:
        payload = {
            "task_type": request.task_type,
            "mode": request.mode,
            "prompt_version": request.prompt_version,
            "schema_version": request.schema_version,
            "request": _normalize(request.model_dump(mode="json")),
            "evidence_package": _normalize(evidence_package.model_dump(mode="json")),
            "prompt_sha256": _sha256_text(_normalize_string(prompt)),
            "schema_sha256": _sha256_text(_normalize_string(schema_text)),
            "images": [
                {
                    "name": UUID_RE.sub("<uuid>", path.name),
                    "sha256": _sha256_file(path),
                }
                for path in image_paths
            ],
        }
        return _sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    def read(self, cache_key: str, request: CodexReviewRequest) -> list[CodexReviewResult] | None:
        path = self._path_for(cache_key)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            reviews = [CodexReviewResult.model_validate(item) for item in data.get("reviews", [])]
        except Exception:
            return None
        if len(reviews) != len(request.targets):
            return None
        restored: list[CodexReviewResult] = []
        for review, target in zip(reviews, request.targets, strict=True):
            if review.status is not CodexReviewStatus.SUCCEEDED:
                return None
            if review.verdict is CodexReviewVerdict.UNCERTAIN:
                return None
            metadata = dict(review.metadata)
            metadata["cache_hit"] = True
            metadata["cache_key"] = cache_key
            restored.append(
                review.model_copy(
                    update={
                        "review_id": f"{request.request_id}:{target.target_id}:cache",
                        "request_id": request.request_id,
                        "task_id": request.task_id,
                        "target": target,
                        "metadata": metadata,
                    }
                )
            )
        return restored

    def write(self, cache_key: str, reviews: list[CodexReviewResult]) -> None:
        if not reviews or any(review.status is not CodexReviewStatus.SUCCEEDED for review in reviews):
            return
        if any(review.verdict is CodexReviewVerdict.UNCERTAIN for review in reviews):
            return
        self.cache_root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(cache_key)
        payload = {
            "cache_key": cache_key,
            "reviews": [
                review.model_copy(update={"metadata": {**review.metadata, "cache_key": cache_key}}).model_dump(mode="json")
                for review in reviews
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _path_for(self, cache_key: str) -> Path:
        safe_key = re.sub(r"[^a-f0-9]", "", cache_key.lower())
        return self.cache_root / f"{safe_key}.json"


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in {"created_at", "completed_at", "task_id", "request_id", "package_id", "source_pdf_path"}:
                continue
            result[key] = _normalize(item)
        return result
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, str):
        return _normalize_string(value)
    return value


def _normalize_string(value: str) -> str:
    return UUID_RE.sub("<uuid>", value)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["CodexReviewCache"]
