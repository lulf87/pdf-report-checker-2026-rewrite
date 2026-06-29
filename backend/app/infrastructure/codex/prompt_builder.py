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
            self._render_target_specific_instructions(request.targets),
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
                "你是 PDF 报告核对工具的受控审核员和最终审核员，本地产品任务必须完成审核后才算完成。",
                "你只能基于提供的 evidence refs 审核。",
                "你不能读取项目源码、旧项目目录、新项目目录、未列出的文件或任何外部路径。",
                "你不能修改文件，不能要求写入、删除、移动或重命名任何文件。",
                "你必须只输出 JSON，并且该 JSON 必须符合下方 JSON schema。",
                "deterministic rule output / rule_context 只是规则初判候选，不是最终事实。",
                "如果证据不足、证据互相冲突或无法稳定判断，应 uncertain。",
                "不要臆测缺失证据，不要补造标准条款、字段含义、检测结果或文件路径。",
            ]
        )

    def _render_task_instructions(self) -> str:
        return "\n".join(
            [
                "## Task Instructions",
                "",
                "- 对每个 target 进行 review，reviews 数组必须覆盖所有 targets。",
                "- 对规则初判候选只能选择 confirm、refute、uncertain 或 add_finding。",
                "- 规则初判候选不是最终事实；不要因为 rule_context 写了 mismatch 或 error 就直接 confirm。",
                "- 如果证据与 rule_context 冲突，应 refute。",
                "- 如果证据不足以确认或反驳规则初判，应 uncertain。",
                "- 跨页检验项目必须查看完整 InspectionItemGroup，包括续页 rows、effective_test_results、actual conclusion candidates、selected conclusion、diagnostics 和 source pages。",
                "- C04/C06 中 OCR 未识别字段不等于标签缺字段；请判断中文标签本体是否缺少字段，或字段是否与样品描述不一致。",
                "- caption 能证明存在中文标签样张，但不能证明标签字段内容完整或缺失；caption 存在不等于字段完整。",
                "- 中文标签样张 caption 能证明标签样张存在。",
                "- caption 存在但缺 matched OCR 时，不应确认标签样张缺失。",
                "- 未找到 OCR 字段不等于未找到标签样张。",
                "- 只有 matched label OCR 属于当前 component 时，才可判断标签字段是否缺失或不一致。",
                "- 只有 matched label OCR 属于当前 component 时，才可判断字段缺失或不一致。",
                "- 无 matched OCR/crop/structured fields 时应 uncertain。",
                "- matched_label_page_text 只是照片页或 caption 周边文本，不能当作标签本体 OCR。",
                "- matched_label_ocr_text 才是标签本体 OCR 文本；matched_label_fields 才是结构化标签字段。",
                "- 如果提供 label image/crop image，请把它作为当前 component 的中文标签视觉证据，不要把 caption 文本当作标签本体字段。",
                "- 请视觉读取标签图片中的部件名称、规格型号、序列号/批号、生产日期和其他可见字段。",
                "- C04 视觉审核输出应在 metadata 中填写 observed_label_fields、field_comparisons 和 visual_evidence_quality。",
                "- visual_evidence_quality 为 clear/partial 时，可结合图片字段 refute 或 confirm；图片不可读、crop 错误或字段看不清时，应 uncertain/manual_review_required。",
                "- 如果只有 caption，没有标签正文或结构化字段，应 uncertain；如果 finding 是 label-not-found，caption 存在时应 refute。",
                "- 如果 C04 候选称标签字段缺失，但 matched_label_fields 中对应字段存在且与样品描述一致，应 refute。",
                "- 如果 C04 候选字段有 matched label OCR/crop/structured fields 且字段确实缺失或与样品描述不一致，可以 confirm。",
                "- 没有标签图像、完整标签正文 OCR 或结构化标签字段时，应 uncertain，不能 confirm 标签本体缺字段。",
                "- C04/C05/C06 中备注为“本次检测未使用”的部件，不适用照片/标签覆盖错误，应 refute 或视为 not_applicable，不要 confirm 或 uncertain。",
                "- C05 中组合 caption 可能覆盖多个部件，应结合 normalized caption matching diagnostics 判断。",
                "- C07 中 “——” 和 “/” 的含义必须结合报告首页备注和完整 group 判断。",
                "- C07 必须查看 recovered_result_tokens、recovered_effective_test_results、compact_rows 和 inspection item 附近 page_text excerpt；不要要求 Codex 弥补缺失证据。",
                "- C07 complex_matrix_table=true 表示该 target 是复杂矩阵表列映射问题，不应按普通 C07 直接 confirm；证据不足时应 uncertain。",
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

    def _render_target_specific_instructions(self, targets: list[CodexReviewTarget]) -> str:
        sections: list[str] = []
        if self._has_c07_visual_target(targets):
            sections.append(self._render_c07_visual_instructions())
        if self._has_c07_complex_matrix_target(targets):
            sections.append(self._render_c07_complex_matrix_instructions())
        return "\n\n".join(sections)

    def _has_c07_visual_target(self, targets: list[CodexReviewTarget]) -> bool:
        for target in targets:
            if target.check_id != "C07":
                continue
            metadata = target.metadata if isinstance(target.metadata, dict) else {}
            if isinstance(metadata.get("c07_visual_evidence"), dict):
                return True
            if any(ref.ref_id.startswith("c07_visual_") for ref in target.evidence_refs):
                return True
        return False

    def _has_c07_complex_matrix_target(self, targets: list[CodexReviewTarget]) -> bool:
        for target in targets:
            if target.check_id != "C07":
                continue
            metadata = target.metadata if isinstance(target.metadata, dict) else {}
            matrix_evidence = metadata.get("c07_complex_matrix_evidence")
            if isinstance(matrix_evidence, dict):
                if matrix_evidence.get("review_mode") == "complex_matrix_specialized":
                    return True
                if matrix_evidence.get("has_complex_matrix_input") is True:
                    return True
            if metadata.get("complex_matrix_table") is True:
                return True
            visual_evidence = metadata.get("c07_visual_evidence")
            if isinstance(visual_evidence, dict) and visual_evidence.get("visual_review_mode") == "complex_matrix_table":
                return True
        return False

    def _render_c07_visual_instructions(self) -> str:
        return "\n".join(
            [
                "## C07 Visual Review Instructions",
                "",
                "- C07 deterministic finding 是 candidate，不是最终事实。",
                "- 请同时使用 textual evidence 和 C07 visual images。",
                "- page/table/item group/result column/conclusion column/remark column images 是当前检验项目的视觉证据。",
                "- result column images 用于核对当前 item_no 的所有检验结果。",
                "- conclusion column images 用于核对单项结论。",
                "- remark column images 用于核对备注。",
                "- 必须结合首页符号说明：“——”表示此项不适用；“/”表示此项空白。",
                "- 需要视觉核对当前 item_no 的所有检验结果、单项结论、备注、跨页续表行，以及 result token 是否被结构化抽取遗漏。",
                "- 如果图片能清楚反驳 all-placeholder 判断，应 refute。",
                "- 对 CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN，如果视觉证据足以判断结论合理时应 refute。",
                "- 不能仅因结构化抽取遗漏存在就 confirm/manual；应区分抽取遗漏本身与最终候选是否仍需复核。",
                "- 续行中的“符合要求”若属于同一 item group，应作为有效检验结果。",
                "- 如果同一 item group 内视觉可见“符合要求”或其他有效检验结果，且单项结论为“符合”，应 refute extraction-uncertain candidate。",
                "- 只有图像无法稳定读取对应行/列，或无法确认 result token 属于该 item group，才 uncertain。",
                "- 如果图片证据仍不清楚，或复杂矩阵表无法稳定判读，应 uncertain。",
                "- complex_matrix_table=true 时，不按普通 C07 直接 confirm；证据不足则 uncertain 或 specialized matrix review。",
                "- 不要求 Codex 弥补缺失证据，不臆测图片外的结果、结论或备注。",
            ]
        )

    def _render_c07_complex_matrix_instructions(self) -> str:
        return "\n".join(
            [
                "## C07 Complex Matrix Review Instructions",
                "",
                "- 当 complex_matrix_table=true 或 c07_complex_matrix_evidence.review_mode=complex_matrix_specialized 时，使用 complex matrix review 口径。",
                "- 先识别矩阵结构，再判断单项结论。",
                "- 必须查看 full page images、matrix table crops、row/column header crops、result matrix crops、conclusion column crops、cross-page continuation crops。",
                "- 需要识别漏电流 / 患者辅助电流项目，以及正常状态 / 单一故障状态。",
                "- 需要识别 B/BF/CF 或应用部分相关列、测量值、限值、占位符、单项结论列。",
                "- 需要判断续页行是否属于同一个 item 59 matrix。",
                "- 先根据矩阵视觉证据定位行标题、列标题、条件列、结果矩阵主体、结论列和跨页续表，再裁决原 candidate。",
                "- 如果视觉证据足以确认符合结论由矩阵结果支持，应 refute 原 complex-matrix candidate。",
                "- 如果视觉证据显示矩阵结果与“符合”冲突，可以 confirm。",
                "- 如果列映射、跨页续表或矩阵结果仍不清楚，应 uncertain。",
                "- 不要因为 rule_context 写了 complex_matrix_table=true 就自动 uncertain；需要先尝试使用 matrix visual evidence。",
                "- 不要按普通 C07 all-placeholder 逻辑直接 confirm/refute。",
                "- 不要把 item 59 硬编码为 refute 或 passed；必须基于提供的矩阵图像和 structured_matrix_hints 审核。",
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
