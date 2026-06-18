from __future__ import annotations

import json
from pathlib import PurePosixPath
import re
from typing import Any

from app.domain.codex_review import CodexReviewRequest, CodexReviewTarget
from app.domain.evidence_package import EvidenceItem, EvidencePackage
from app.infrastructure.codex.runner import CodexRunnerConfigurationError
from app.infrastructure.codex.schemas import load_codex_review_output_schema


OLD_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"
REDACTED_PATH = "[redacted-path]"


class PromptBuilder:
    """Render a controlled Codex runtime-auditor prompt from an evidence package."""

    def build_review_prompt(
        self,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
        *,
        max_item_text_chars: int = 4000,
        max_total_chars: int = 24000,
    ) -> str:
        if max_item_text_chars <= 0:
            raise CodexRunnerConfigurationError("max_item_text_chars must be greater than zero")
        if max_total_chars <= 0:
            raise CodexRunnerConfigurationError("max_total_chars must be greater than zero")

        self._validate_request_package_match(request, evidence_package)
        allowed_refs = self._collect_allowed_refs(request, evidence_package)
        items_by_ref = {item.ref_id: item for item in evidence_package.items}
        allowed_items = [items_by_ref[ref_id] for ref_id in sorted(allowed_refs)]
        schema = load_codex_review_output_schema()

        parts = [
            self._render_role_and_safety(),
            self._render_task_instructions(),
            self._render_output_contract(schema),
            self._render_package_summary(evidence_package),
            self._render_targets(request.targets),
            self._render_evidence_items(allowed_items, max_item_text_chars=max_item_text_chars),
        ]
        return self._truncate_total("\n\n".join(parts).strip() + "\n", max_total_chars)

    def _validate_request_package_match(
        self,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
    ) -> None:
        if request.task_id != evidence_package.task_id:
            raise CodexRunnerConfigurationError("Codex review request task_id must match evidence package task_id")
        if request.task_type != evidence_package.task_type:
            raise CodexRunnerConfigurationError("Codex review request task_type must match evidence package task_type")
        if not request.targets:
            raise CodexRunnerConfigurationError("Codex review request must contain at least one target")

    def _collect_allowed_refs(
        self,
        request: CodexReviewRequest,
        evidence_package: EvidencePackage,
    ) -> set[str]:
        item_refs = {item.ref_id for item in evidence_package.items}
        allowed_refs: set[str] = set()
        for target in request.targets:
            for evidence_ref in target.evidence_refs:
                if evidence_ref.ref_id not in item_refs:
                    raise CodexRunnerConfigurationError(
                        f"target {target.target_id} references unknown evidence ref: {evidence_ref.ref_id}"
                    )
                allowed_refs.add(evidence_ref.ref_id)
        return allowed_refs

    def _render_role_and_safety(self) -> str:
        return "\n".join(
            [
                "# Codex Runtime Auditor Prompt",
                "",
                "你是 PDF 报告核对工具的受控审核员，只能基于提供的 evidence refs 审核。",
                "你不能读取项目源码、旧项目目录、新项目目录、未列出的文件或任何外部路径。",
                "你不能修改文件，不能要求写入、删除、移动或重命名任何文件。",
                "你必须只输出 JSON，并且该 JSON 必须符合下方 JSON schema。",
                "如果证据不足、证据互相冲突或无法稳定判断，使用 uncertain。",
                "不要臆测缺失证据，不要补造标准条款、字段含义、检测结果或文件路径。",
            ]
        )

    def _render_task_instructions(self) -> str:
        return "\n".join(
            [
                "## Task Instructions",
                "",
                "- 对每个 target 进行 review，reviews 数组必须覆盖所有 targets。",
                "- 对规则初判只能选择 confirm、refute、uncertain 或 add_finding。",
                "- 不删除原始 Finding，只输出审核意见；原始 Finding 不得删除或覆盖。",
                "- reasoning_summary 必须简短、可审计，并引用使用过的 evidence refs。",
                "- add_finding 必须包含 suggested_finding。",
                "- failed、timeout、非零退出或 schema 解析失败由 runner/parser 处理；正常输出不要主动写 failed。",
                "- 只输出 JSON；不输出 Markdown、解释性段落、前后缀或代码块。",
            ]
        )

    def _render_output_contract(self, schema: dict[str, Any]) -> str:
        schema_text = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)
        return "\n".join(
            [
                "## JSON Output Schema",
                "",
                "输出必须是一个 JSON object，包含 schema_version 和 reviews。",
                "每个 review 必须包含 target_id、status、verdict、confidence、reasoning_summary、evidence_refs、suggested_severity、suggested_finding、metadata。",
                "status 只能是 succeeded；verdict 只能是 confirm/refute/uncertain/add_finding；confidence 只能是 high/medium/low。",
                "Schema:",
                schema_text,
            ]
        )

    def _render_package_summary(self, evidence_package: EvidencePackage) -> str:
        lines = [
            "## Evidence Package Summary",
            "",
            f"- package_id: {self._safe_scalar(evidence_package.package_id)}",
            f"- task_id: {self._safe_scalar(evidence_package.task_id)}",
            f"- task_type: {self._safe_scalar(evidence_package.task_type)}",
            f"- kind: {self._safe_scalar(self._enum_value(evidence_package.kind))}",
            f"- schema_version: {self._safe_scalar(evidence_package.schema_version)}",
        ]
        return "\n".join(lines)

    def _render_targets(self, targets: list[CodexReviewTarget]) -> str:
        lines = ["## Targets", ""]
        for target in targets:
            allowed_refs = [ref.ref_id for ref in target.evidence_refs]
            target_payload = {
                "target_id": target.target_id,
                "target_type": self._enum_value(target.target_type),
                "check_id": target.check_id,
                "finding_id": target.finding_id,
                "finding_code": target.finding_code,
                "title": target.title,
                "summary": target.summary,
                "allowed_evidence_refs": allowed_refs,
                "metadata": target.metadata,
            }
            lines.extend(
                [
                    f"### Target {self._safe_scalar(target.target_id)}",
                    self._safe_json(target_payload),
                    "",
                ]
            )
        return "\n".join(lines).rstrip()

    def _render_evidence_items(
        self,
        items: list[EvidenceItem],
        *,
        max_item_text_chars: int,
    ) -> str:
        lines = ["## Evidence Items", ""]
        for item in items:
            file_path = self._safe_file_path(item)
            item_payload = {
                "ref_id": item.ref_id,
                "source_type": self._enum_value(item.source_type),
                "title": item.title,
                "page_number": item.page_number,
                "section": item.section,
                "file_path": file_path,
                "text": self._truncate_item_text(self._sanitize_text(item.text), max_item_text_chars)
                if item.text is not None
                else None,
                "structured": self._truncate_item_text(self._safe_json(item.structured), max_item_text_chars)
                if item.structured is not None
                else None,
                "location": self._truncate_item_text(self._safe_json(item.location), max_item_text_chars)
                if item.location is not None
                else None,
                "metadata": self._truncate_item_text(self._safe_json(item.metadata), max_item_text_chars)
                if item.metadata
                else {},
            }
            lines.extend(
                [
                    f"### Evidence {self._safe_scalar(item.ref_id)}",
                    self._safe_json(item_payload),
                    "",
                ]
            )
        return "\n".join(lines).rstrip()

    def _safe_file_path(self, item: EvidenceItem) -> str | None:
        if item.file_path is None:
            return None
        path = PurePosixPath(item.file_path)
        if path.is_absolute() or ".." in path.parts or item.file_path.startswith("~"):
            raise CodexRunnerConfigurationError(
                f"evidence item {item.ref_id} has unsafe file_path outside evidence workspace"
            )
        sanitized = self._sanitize_text(item.file_path)
        if sanitized != item.file_path:
            raise CodexRunnerConfigurationError(f"evidence item {item.ref_id} has unsafe file_path")
        return sanitized

    def _safe_scalar(self, value: Any) -> str:
        return self._sanitize_text("" if value is None else str(value))

    def _safe_json(self, value: Any) -> str:
        return self._sanitize_text(json.dumps(value, ensure_ascii=False, sort_keys=True))

    def _sanitize_text(self, value: str | None) -> str:
        if value is None:
            return ""
        sanitized = str(value)
        for exact in (OLD_PROJECT_ROOT, NEW_PROJECT_ROOT):
            sanitized = sanitized.replace(exact, REDACTED_PATH)
        sanitized = sanitized.replace("file://", REDACTED_PATH)
        sanitized = sanitized.replace("../", REDACTED_PATH)
        sanitized = sanitized.replace("..\\", REDACTED_PATH)
        sanitized = sanitized.replace("backend/app", REDACTED_PATH)
        sanitized = sanitized.replace("frontend/src", REDACTED_PATH)
        sanitized = re.sub(r"/Users/[^\s\"'，,；;\)\]\}]+", REDACTED_PATH, sanitized)
        return sanitized

    def _truncate_item_text(self, value: str, max_item_text_chars: int) -> str:
        if len(value) <= max_item_text_chars:
            return value
        marker = "\n[truncated]"
        keep = max(0, max_item_text_chars - len(marker))
        return value[:keep].rstrip() + marker

    def _truncate_total(self, prompt: str, max_total_chars: int) -> str:
        if len(prompt) <= max_total_chars:
            return prompt
        marker = "\n[truncated]\n"
        keep = max(0, max_total_chars - len(marker))
        return prompt[:keep].rstrip() + marker

    def _enum_value(self, value: Any) -> Any:
        return getattr(value, "value", value)


__all__ = ["PromptBuilder"]
