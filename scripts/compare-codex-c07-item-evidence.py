#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare C07 item evidence between two Codex audit runs without exposing absolute paths."
    )
    parser.add_argument("--targeted-task-id", required=True)
    parser.add_argument("--full-task-id", required=True)
    parser.add_argument("--item-no", default="33")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    targeted = _extract_run(project_root, task_id=args.targeted_task_id, item_no=args.item_no)
    full = _extract_run(project_root, task_id=args.full_task_id, item_no=args.item_no)

    output = {
        "item_no": args.item_no,
        "targeted": targeted,
        "full": full,
        "comparison": {
            "same_finding_code": targeted.get("finding_code") == full.get("finding_code"),
            "same_visual_review_mode": targeted.get("visual_review_mode") == full.get("visual_review_mode"),
            "same_allowed_refs_normalized": targeted.get("allowed_evidence_refs_normalized")
            == full.get("allowed_evidence_refs_normalized"),
            "same_visual_metadata_normalized": targeted.get("c07_visual_evidence_normalized")
            == full.get("c07_visual_evidence_normalized"),
            "same_materialized_images_normalized": targeted.get("materialized_image_files_normalized")
            == full.get("materialized_image_files_normalized"),
            "verdicts": {
                "targeted": targeted.get("review", {}).get("verdict"),
                "full": full.get("review", {}).get("verdict"),
            },
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _extract_run(project_root: Path, *, task_id: str, item_no: str) -> dict[str, Any]:
    result_path = project_root / "runtime" / "codex_audit_local_e2e" / f"{task_id}.result.json"
    result = _read_json(result_path)
    c07 = next((item for item in result.get("check_results", []) if item.get("check_id") == "C07"), None)
    if not c07:
        raise SystemExit(f"C07 check_result not found for task {task_id}")

    finding = next(
        (
            item
            for item in c07.get("findings", [])
            if str(item.get("metadata", {}).get("normalized_item_no") or item.get("metadata", {}).get("item_no")) == item_no
        ),
        None,
    )
    if not finding:
        raise SystemExit(f"C07 item {item_no} finding not found for task {task_id}")

    finding_id = finding.get("id")
    review = next(
        (
            item
            for item in c07.get("codex_reviews", [])
            if item.get("target", {}).get("finding_id") == finding_id or finding_id in str(item.get("review_id", ""))
        ),
        None,
    )
    if not review:
        raise SystemExit(f"Codex review for C07 item {item_no} not found for task {task_id}")

    request_id = review.get("request_id") or ""
    batch_id = _batch_id_from_request(request_id)
    workspace_input = (
        project_root
        / "backend"
        / "runtime"
        / "codex_audit"
        / task_id
        / f"codex-report-{task_id}-C07-batch-{batch_id}"
        / "input"
    )
    evidence_package = _read_json(workspace_input / "evidence_package.json")
    manifest = _read_json(workspace_input / "manifest.json")
    codex_output = _read_json(workspace_input / "codex_review_output.json")
    prompt_text = (workspace_input / "prompt.md").read_text(encoding="utf-8")

    target = next(
        (
            item
            for item in evidence_package.get("targets", [])
            if item.get("finding_id") == finding_id or item.get("target_id") == review.get("target", {}).get("target_id")
        ),
        evidence_package.get("targets", [{}])[0],
    )
    visual = target.get("metadata", {}).get("c07_visual_evidence", {})
    allowed_refs = target.get("evidence_refs", [])
    image_items = [
        {
            "ref_id": item.get("ref_id"),
            "file_path": _safe_path(item.get("file_path"), project_root=project_root),
            "section": item.get("section"),
            "crop_kind": item.get("metadata", {}).get("crop_kind"),
            "render_bbox": item.get("metadata", {}).get("render_bbox"),
        }
        for item in evidence_package.get("items", [])
        if item.get("source_type") == "image"
    ]
    materialized = [_safe_path(value, project_root=project_root) for value in manifest.get("item_file_paths", [])]
    output_review = next(
        (
            item
            for item in codex_output.get("reviews", [])
            if item.get("target_id") == review.get("target", {}).get("target_id")
        ),
        {},
    )

    return {
        "task_id": task_id,
        "result_path": _safe_path(result_path, project_root=project_root),
        "workspace_input": _safe_path(workspace_input, project_root=project_root),
        "package_id": evidence_package.get("package_id"),
        "batch_id": batch_id,
        "target_id": target.get("target_id"),
        "finding_id": finding_id,
        "finding_code": finding.get("code"),
        "target_summary": target.get("summary"),
        "allowed_evidence_refs": allowed_refs,
        "allowed_evidence_refs_normalized": _normalize_task_ids(allowed_refs, task_id=task_id),
        "c07_visual_evidence": _normalize_paths(visual, project_root=project_root),
        "c07_visual_evidence_normalized": _normalize_task_ids(_normalize_paths(visual, project_root=project_root), task_id=task_id),
        "visual_review_mode": visual.get("visual_review_mode"),
        "image_refs": _image_refs(visual),
        "image_refs_normalized": _normalize_task_ids(_image_refs(visual), task_id=task_id),
        "image_items": image_items,
        "materialized_image_files": materialized,
        "materialized_image_files_normalized": _normalize_task_ids(materialized, task_id=task_id),
        "prompt_flags": {
            "has_c07_visual_instructions": "## C07 Visual Review Instructions" in prompt_text,
            "mentions_extraction_uncertain": "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN" in prompt_text,
            "mentions_refute_when_visual_sufficient": "视觉证据足以判断结论合理时应 refute" in prompt_text,
            "mentions_do_not_confirm_for_extraction_omission_only": "不能仅因结构化抽取遗漏存在就 confirm/manual" in prompt_text,
            "mentions_continuation_conforming_result": "续行中的“符合要求”若属于同一 item group" in prompt_text,
        },
        "review": {
            "verdict": output_review.get("verdict") or review.get("verdict"),
            "confidence": output_review.get("confidence") or review.get("confidence"),
            "reasoning_summary": output_review.get("reasoning_summary") or review.get("reasoning_summary"),
            "evidence_refs": output_review.get("evidence_refs") or review.get("evidence_refs"),
            "visual_evidence_quality": (output_review.get("metadata") or review.get("metadata") or {}).get(
                "visual_evidence_quality"
            ),
        },
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"required file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return value


def _batch_id_from_request(request_id: str) -> str:
    match = re.search(r"-batch-(\d+)$", request_id)
    if not match:
        raise SystemExit(f"cannot extract batch id from request_id: {request_id}")
    return match.group(1)


def _safe_path(value: Any, *, project_root: Path) -> Any:
    if not isinstance(value, (str, Path)):
        return value
    text = str(value)
    path = Path(text)
    if path.is_absolute():
        try:
            text = path.resolve().relative_to(project_root).as_posix()
        except ValueError:
            text = "[redacted-absolute-path]"
    return text.replace(str(project_root), "[project-root]").replace("/Users/", "[redacted-users]/")


def _normalize_paths(value: Any, *, project_root: Path) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_paths(item, project_root=project_root) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_paths(item, project_root=project_root) for item in value]
    return _safe_path(value, project_root=project_root)


def _normalize_task_ids(value: Any, *, task_id: str) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_task_ids(item, task_id=task_id) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_task_ids(item, task_id=task_id) for item in value]
    if isinstance(value, str):
        return value.replace(task_id, "{task_id}")
    return value


def _image_refs(visual: dict[str, Any]) -> dict[str, Any]:
    return {
        key: visual.get(key, [])
        for key in (
            "page_image_refs",
            "table_image_refs",
            "item_group_crop_refs",
            "result_column_crop_refs",
            "conclusion_column_crop_refs",
            "remark_column_crop_refs",
        )
    }


if __name__ == "__main__":
    raise SystemExit(main())
