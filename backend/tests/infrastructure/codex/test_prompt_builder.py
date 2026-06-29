from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pytest

from app.domain.codex_review import (
    CodexEvidenceRef,
    CodexReviewRequest,
    CodexReviewTarget,
    CodexReviewTargetType,
)
from app.domain.evidence_package import (
    EvidenceItem,
    EvidencePackage,
    EvidencePackageKind,
    EvidenceSourceType,
    EvidenceTarget,
)
from app.infrastructure.codex.runner import CodexRunnerConfigurationError


CREATED_AT = datetime(2026, 6, 17, 9, 0, tzinfo=timezone.utc)
OLD_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"


def _review_target(
    *,
    target_id: str = "target-1",
    target_type: CodexReviewTargetType = CodexReviewTargetType.REPORT_RULE,
    evidence_refs: list[str] | None = None,
) -> CodexReviewTarget:
    refs = evidence_refs or ["ev-1"]
    return CodexReviewTarget(
        target_id=target_id,
        target_type=target_type,
        check_id="C02" if target_type is CodexReviewTargetType.REPORT_RULE else "PTR_TABLE",
        finding_id=f"finding-{target_id}",
        finding_code="C02_FIELD_MISMATCH" if target_type is CodexReviewTargetType.REPORT_RULE else "PTR_TABLE_VALUE_MISMATCH",
        title=f"Review {target_id}",
        summary=f"审核 {target_id} 的规则初判。",
        evidence_refs=[CodexEvidenceRef(ref_id=ref_id, source_type="pdf_text") for ref_id in refs],
    )


def _request(targets: list[CodexReviewTarget] | None = None) -> CodexReviewRequest:
    return CodexReviewRequest(
        request_id="request-1",
        task_id="task-1",
        task_type="report_check",
        targets=targets or [_review_target()],
        prompt_version="codex-review-prompt-v1",
        schema_version="codex-review-output-v1",
        created_at=CREATED_AT,
    )


def _package(
    *,
    kind: EvidencePackageKind = EvidencePackageKind.REPORT_RULE_REVIEW,
    target_type: str = "report_rule",
    target_refs: list[str] | None = None,
    items: list[EvidenceItem] | None = None,
) -> EvidencePackage:
    refs = target_refs or ["ev-1"]
    return EvidencePackage(
        package_id="pkg-1",
        task_id="task-1",
        task_type="report_check",
        kind=kind,
        schema_version="evidence-package-v1",
        created_at=CREATED_AT,
        targets=[
            EvidenceTarget(
                target_id="target-1",
                target_type=target_type,
                check_id="C02" if target_type == "report_rule" else "PTR_TABLE",
                finding_id="finding-target-1",
                finding_code="C02_FIELD_MISMATCH" if target_type == "report_rule" else "PTR_TABLE_VALUE_MISMATCH",
                summary="规则初判需要 Codex 复核。",
                evidence_refs=refs,
            )
        ],
        items=items
        or [
            EvidenceItem(
                ref_id="ev-1",
                source_type=EvidenceSourceType.PDF_TEXT,
                title="第三页字段片段",
                text="第三页型号规格: ABC-2",
                page_number=3,
                section="第三页",
                metadata={"field": "型号规格"},
            )
        ],
    )


def test_build_prompt_contains_package_target_and_evidence_refs() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "task-1" in prompt
    assert "pkg-1" in prompt
    assert "target-1" in prompt
    assert "ev-1" in prompt
    assert "第三页型号规格: ABC-2" in prompt


def test_prompt_contains_auditor_role_safety_and_json_only_requirements() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "受控审核员" in prompt
    assert "只能基于提供的 evidence refs" in prompt
    assert "不能读取项目源码" in prompt
    assert "不能修改文件" in prompt
    assert "只输出 JSON" in prompt
    assert "JSON schema" in prompt
    assert "uncertain" in prompt
    assert "不要臆测" in prompt


def test_prompt_declares_codex_as_mandatory_final_auditor_and_rules_as_candidates() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "最终审核员" in prompt
    assert "必须完成审核" in prompt
    assert "规则初判" in prompt
    assert "候选" in prompt
    assert "不是最终事实" in prompt
    assert "证据与 rule_context 冲突" in prompt
    assert "应 refute" in prompt
    assert "证据不足" in prompt
    assert "应 uncertain" in prompt
    assert "不要因为 rule_context" in prompt


def test_prompt_instructs_label_ocr_missing_is_not_label_content_missing() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "OCR 未识别字段不等于标签缺字段" in prompt
    assert "caption 能证明存在中文标签样张，但不能证明标签字段内容完整或缺失" in prompt
    assert "没有标签图像、完整标签正文 OCR 或结构化标签字段时，应 uncertain" in prompt
    assert "中文标签样张 caption 能证明标签样张存在" in prompt
    assert "caption 存在但缺 matched OCR 时，不应确认标签样张缺失" in prompt
    assert "未找到 OCR 字段不等于未找到标签样张" in prompt
    assert "只有 matched label OCR 属于当前 component 时" in prompt
    assert "只有 matched label OCR 属于当前 component 时，才可判断字段缺失或不一致" in prompt
    assert "无 matched OCR/crop/structured fields 时应 uncertain" in prompt
    assert "matched_label_page_text 只是照片页或 caption 周边文本" in prompt
    assert "matched_label_ocr_text 才是标签本体 OCR 文本" in prompt
    assert "如果 finding 是 label-not-found，caption 存在时应 refute" in prompt
    assert "matched_label_fields 中对应字段存在且与样品描述一致，应 refute" in prompt
    assert "字段确实缺失或与样品描述不一致，可以 confirm" in prompt
    assert "本次检测未使用" in prompt
    assert "应 refute 或视为 not_applicable" in prompt


def test_prompt_instructs_c04_visual_label_image_review_and_metadata_output() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "如果提供 label image/crop image" in prompt
    assert "视觉读取标签图片中的部件名称、规格型号、序列号/批号、生产日期" in prompt
    assert "observed_label_fields" in prompt
    assert "field_comparisons" in prompt
    assert "visual_evidence_quality" in prompt
    assert "图片不可读、crop 错误或字段看不清" in prompt


def test_prompt_instructs_complex_matrix_c07_to_stay_uncertain_not_confirmed() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "complex_matrix_table=true" in prompt
    assert "不应按普通 C07 直接 confirm" in prompt


def test_prompt_instructs_c07_to_use_recovered_tokens_and_compact_rows() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "recovered_result_tokens" in prompt
    assert "compact_rows" in prompt
    assert "不要要求 Codex 弥补缺失证据" in prompt


def test_c07_prompt_contains_visual_evidence_instructions() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    request, package = _c07_visual_request_and_package()

    prompt = PromptBuilder().build_review_prompt(request, package)

    assert "## C07 Visual Review Instructions" in prompt
    assert "C07 deterministic finding 是 candidate" in prompt
    assert "同时使用 textual evidence 和 C07 visual images" in prompt
    assert "page/table/item group/result column/conclusion column/remark column images" in prompt
    assert "result column images" in prompt
    assert "conclusion column images" in prompt
    assert "remark column images" in prompt
    assert "“——”表示此项不适用" in prompt
    assert "“/”表示此项空白" in prompt
    assert "当前 item_no 的所有检验结果" in prompt
    assert "跨页续表行" in prompt
    assert "result token 是否被结构化抽取遗漏" in prompt
    assert "图片能清楚反驳 all-placeholder 判断，应 refute" in prompt
    assert "复杂矩阵表无法稳定判读，应 uncertain" in prompt
    assert "complex_matrix_table=true" in prompt
    assert "/Users/" not in prompt


def test_c07_prompt_explains_extraction_uncertainty_refute_conditions() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    request, package = _c07_visual_request_and_package()

    prompt = PromptBuilder().build_review_prompt(request, package)

    assert "CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN" in prompt
    assert "视觉证据足以判断结论合理时应 refute" in prompt
    assert "不能仅因结构化抽取遗漏存在就 confirm/manual" in prompt
    assert "续行中的“符合要求”若属于同一 item group，应作为有效检验结果" in prompt
    assert "只有图像无法稳定读取对应行/列，或无法确认 result token 属于该 item group，才 uncertain" in prompt


def test_c07_complex_matrix_prompt_contains_specialized_matrix_instructions() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    request, package = _c07_complex_matrix_request_and_package()

    prompt = PromptBuilder().build_review_prompt(request, package)

    assert "## C07 Complex Matrix Review Instructions" in prompt
    assert "先识别矩阵结构，再判断单项结论" in prompt
    assert "正常状态 / 单一故障状态" in prompt
    assert "漏电流 / 患者辅助电流" in prompt
    assert "row/column header crops" in prompt
    assert "result matrix crops" in prompt
    assert "conclusion column crops" in prompt
    assert "cross-page continuation crops" in prompt
    assert "如果视觉证据足以确认符合结论由矩阵结果支持，应 refute" in prompt
    assert "不要因为 rule_context 写了 complex_matrix_table=true 就自动 uncertain" in prompt
    assert "不要按普通 C07 all-placeholder 逻辑直接 confirm/refute" in prompt
    assert "/Users/" not in prompt


def test_regular_c07_prompt_does_not_include_complex_matrix_specialized_instructions() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    request, package = _c07_visual_request_and_package()

    prompt = PromptBuilder().build_review_prompt(request, package)

    assert "## C07 Visual Review Instructions" in prompt
    assert "## C07 Complex Matrix Review Instructions" not in prompt
    assert "先识别矩阵结构，再判断单项结论" not in prompt
    assert "row/column header crops" not in prompt
    assert "result matrix crops" not in prompt
    assert "cross-page continuation crops" not in prompt


def test_c04_prompt_does_not_include_c07_visual_evidence_instructions() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "## C07 Visual Review Instructions" not in prompt
    assert "page/table/item group/result column/conclusion column/remark column images" not in prompt
    assert "C07 visual images" not in prompt


def test_prompt_only_includes_target_referenced_evidence() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    package = _package(
        items=[
            EvidenceItem(
                ref_id="ev-1",
                source_type=EvidenceSourceType.PDF_TEXT,
                text="authorized evidence text",
            ),
            EvidenceItem(
                ref_id="ev-unused",
                source_type=EvidenceSourceType.PDF_TEXT,
                text="unused evidence text must stay out",
            ),
        ]
    )

    prompt = PromptBuilder().build_review_prompt(_request(), package)

    assert "authorized evidence text" in prompt
    assert "ev-unused" not in prompt
    assert "unused evidence text must stay out" not in prompt


def test_prompt_redacts_old_and_new_project_absolute_paths_from_evidence_text() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    package = _package(
        items=[
            EvidenceItem(
                ref_id="ev-1",
                source_type=EvidenceSourceType.PDF_TEXT,
                text=f"旧路径 {OLD_PROJECT_ROOT}/backend/app/services/report_self_check_service.py；"
                f"新路径 {NEW_PROJECT_ROOT}/backend/app/domain/result.py",
                structured={"source": f"file://{NEW_PROJECT_ROOT}/frontend/src/App.tsx"},
                metadata={"note": f"{OLD_PROJECT_ROOT}/README.md"},
            )
        ]
    )

    prompt = PromptBuilder().build_review_prompt(_request(), package)

    assert OLD_PROJECT_ROOT not in prompt
    assert NEW_PROJECT_ROOT not in prompt
    assert "/Users/" not in prompt
    assert "file://" not in prompt
    assert "backend/app" not in prompt
    assert "frontend/src" not in prompt
    assert "[redacted-path]" in prompt


def test_prompt_builder_rejects_absolute_evidence_item_file_path() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    unsafe_item = EvidenceItem.model_construct(
        ref_id="ev-1",
        source_type=EvidenceSourceType.PDF_TEXT,
        text=None,
        structured=None,
        file_path=f"{NEW_PROJECT_ROOT}/runtime/codex_audit/task-1/pkg-1/input/items/ev-1.txt",
        page_number=None,
        section=None,
        location=None,
        metadata={},
    )
    package = EvidencePackage.model_construct(
        package_id="pkg-1",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        created_at=CREATED_AT,
        targets=[
            EvidenceTarget(
                target_id="target-1",
                target_type="report_rule",
                evidence_refs=["ev-1"],
            )
        ],
        items=[unsafe_item],
        metadata={},
    )

    with pytest.raises(CodexRunnerConfigurationError, match="file_path"):
        PromptBuilder().build_review_prompt(_request(), package)


def test_prompt_truncates_long_item_text() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    long_text = "A" * 200
    package = _package(
        items=[
            EvidenceItem(
                ref_id="ev-1",
                source_type=EvidenceSourceType.PDF_TEXT,
                text=long_text,
            )
        ]
    )

    prompt = PromptBuilder().build_review_prompt(
        _request(),
        package,
        max_item_text_chars=40,
    )

    assert "A" * 120 not in prompt
    assert "[truncated]" in prompt


def test_prompt_total_size_can_be_truncated() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(
        _request(),
        _package(),
        max_total_chars=900,
    )

    assert len(prompt) <= 900
    assert prompt.endswith("[truncated]\n")


def test_prompt_builder_fails_when_request_target_references_unknown_evidence() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    request = _request([_review_target(evidence_refs=["ev-missing"])])

    with pytest.raises(CodexRunnerConfigurationError, match="unknown evidence"):
        PromptBuilder().build_review_prompt(request, _package())


def test_prompt_instructs_add_finding_to_include_suggested_finding() -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "add_finding" in prompt
    assert "suggested_finding" in prompt
    assert "原始 Finding" in prompt
    assert "不得删除" in prompt


@pytest.mark.parametrize(
    ("target_type", "kind", "package_target_type"),
    [
        (CodexReviewTargetType.PTR_TABLE, EvidencePackageKind.PTR_TABLE_REVIEW, "ptr_table"),
        (CodexReviewTargetType.PTR_CLAUSE, EvidencePackageKind.PTR_CLAUSE_REVIEW, "ptr_clause"),
        (CodexReviewTargetType.REPORT_RULE, EvidencePackageKind.REPORT_RULE_REVIEW, "report_rule"),
    ],
)
def test_prompt_renders_ptr_table_ptr_clause_and_report_rule_targets(
    target_type: CodexReviewTargetType,
    kind: EvidencePackageKind,
    package_target_type: str,
) -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    request = _request([_review_target(target_type=target_type)])
    package = _package(kind=kind, target_type=package_target_type)

    prompt = PromptBuilder().build_review_prompt(request, package)

    assert target_type.value in prompt
    assert kind.value in prompt
    assert package_target_type in prompt


def test_prompt_builder_does_not_call_subprocess_or_codex_cli_runner(monkeypatch) -> None:
    from app.infrastructure.codex.prompt_builder import PromptBuilder

    def fail_if_called(*args, **kwargs):
        raise AssertionError("PromptBuilder must not call subprocess or real Codex")

    monkeypatch.setattr(subprocess, "run", fail_if_called)

    prompt = PromptBuilder().build_review_prompt(_request(), _package())

    assert "pkg-1" in prompt


def _c07_visual_request_and_package() -> tuple[CodexReviewRequest, EvidencePackage]:
    refs = [
        "finding:finding-c07-1",
        "rule_context:finding-c07-1",
        "symbol_note:finding-c07-1",
        "inspection_item:finding-c07-1",
        "c07_visual_page:finding-c07-1:p22",
        "c07_visual_table:finding-c07-1:p22",
        "c07_visual_item_group:finding-c07-1:p22",
        "c07_visual_result:finding-c07-1:p22",
        "c07_visual_conclusion:finding-c07-1:p22",
        "c07_visual_remark:finding-c07-1:p22",
    ]
    target = CodexReviewTarget(
        target_id="target-c07-1",
        target_type=CodexReviewTargetType.INSPECTION_ITEM,
        check_id="C07",
        finding_id="finding-c07-1",
        finding_code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
        title="C07 visual review target",
        summary="复核 C07 检验项目结论。",
        evidence_refs=[
            CodexEvidenceRef(
                ref_id=ref,
                source_type="image" if ref.startswith("c07_visual_") else "rule_context",
            )
            for ref in refs
        ],
        metadata={
            "c07_visual_evidence": {
                "has_visual_input": True,
                "visual_review_mode": "inspection_item_group",
                "page_image_refs": ["items/finding-c07-1-c07-page-p22.png"],
                "table_image_refs": ["items/finding-c07-1-c07-table-p22.png"],
                "item_group_crop_refs": ["items/finding-c07-1-c07-item-group-p22.png"],
                "result_column_crop_refs": ["items/finding-c07-1-c07-result-p22.png"],
                "conclusion_column_crop_refs": ["items/finding-c07-1-c07-conclusion-p22.png"],
                "remark_column_crop_refs": ["items/finding-c07-1-c07-remark-p22.png"],
                "missing_visual_evidence_reasons": [],
            },
            "complex_matrix_table": False,
        },
    )
    request = CodexReviewRequest(
        request_id="request-c07-1",
        task_id="task-1",
        task_type="report_check",
        targets=[target],
        prompt_version="codex-review-prompt-v1",
        schema_version="codex-review-output-v1",
        created_at=CREATED_AT,
    )
    items = [
        EvidenceItem(
            ref_id="finding:finding-c07-1",
            source_type=EvidenceSourceType.FINDING,
            text="C07 deterministic finding 是 candidate。",
        ),
        EvidenceItem(
            ref_id="rule_context:finding-c07-1",
            source_type=EvidenceSourceType.RULE_CONTEXT,
            text="rule_context: all-placeholder 判断需要复核。",
        ),
        EvidenceItem(
            ref_id="symbol_note:finding-c07-1",
            source_type=EvidenceSourceType.PAGE_TEXT,
            text="首页说明：“——”表示此项不适用；“/”表示此项空白。",
        ),
        EvidenceItem(
            ref_id="inspection_item:finding-c07-1",
            source_type=EvidenceSourceType.TABLE,
            structured={
                "inspection_item_group": {
                    "item_no": "94",
                    "effective_test_results": ["——"],
                    "recovered_result_tokens": ["符合要求"],
                    "compact_rows": [{"test_result": "——", "conclusion": "符合"}],
                }
            },
        ),
        *[
            EvidenceItem(
                ref_id=ref,
                source_type=EvidenceSourceType.IMAGE,
                file_path=file_path,
                page_number=22,
                metadata={"codex_image_input": True, "render_page_number": 22},
            )
            for ref, file_path in [
                ("c07_visual_page:finding-c07-1:p22", "items/finding-c07-1-c07-page-p22.png"),
                ("c07_visual_table:finding-c07-1:p22", "items/finding-c07-1-c07-table-p22.png"),
                ("c07_visual_item_group:finding-c07-1:p22", "items/finding-c07-1-c07-item-group-p22.png"),
                ("c07_visual_result:finding-c07-1:p22", "items/finding-c07-1-c07-result-p22.png"),
                ("c07_visual_conclusion:finding-c07-1:p22", "items/finding-c07-1-c07-conclusion-p22.png"),
                ("c07_visual_remark:finding-c07-1:p22", "items/finding-c07-1-c07-remark-p22.png"),
            ]
        ],
    ]
    package = EvidencePackage(
        package_id="pkg-c07-1",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        created_at=CREATED_AT,
        targets=[
            EvidenceTarget(
                target_id=target.target_id,
                target_type=target.target_type.value,
                check_id="C07",
                finding_id=target.finding_id,
                finding_code=target.finding_code,
                evidence_refs=refs,
            )
        ],
        items=items,
    )
    return request, package


def _c07_complex_matrix_request_and_package() -> tuple[CodexReviewRequest, EvidencePackage]:
    text_refs = [
        "finding:finding-c07-59",
        "rule_context:finding-c07-59",
        "symbol_note:finding-c07-59",
        "inspection_item:finding-c07-59",
    ]
    image_refs = [
        "c07_complex_matrix_page:finding-c07-59:p42",
        "c07_complex_matrix_table:finding-c07-59:p42",
        "c07_complex_matrix_header:finding-c07-59:p42",
        "c07_complex_matrix_body:finding-c07-59:p42",
        "c07_complex_matrix_result:finding-c07-59:p42",
        "c07_complex_matrix_conclusion:finding-c07-59:p42",
        "c07_complex_matrix_continuation:finding-c07-59:p43",
    ]
    refs = [*text_refs, *image_refs]
    matrix_metadata = {
        "has_complex_matrix_input": True,
        "review_mode": "complex_matrix_specialized",
        "item_no": "59",
        "pages": [42, 43],
        "matrix_page_image_refs": ["items/finding-c07-59-c07-matrix-page-p42.png"],
        "matrix_table_image_refs": ["items/finding-c07-59-c07-matrix-table-p42.png"],
        "matrix_header_image_refs": ["items/finding-c07-59-c07-matrix-header-p42.png"],
        "matrix_body_image_refs": ["items/finding-c07-59-c07-matrix-body-p42.png"],
        "result_matrix_image_refs": ["items/finding-c07-59-c07-matrix-result-p42.png"],
        "conclusion_column_image_refs": ["items/finding-c07-59-c07-matrix-conclusion-p42.png"],
        "continuation_page_image_refs": ["items/finding-c07-59-c07-matrix-continuation-p43.png"],
        "structured_matrix_hints": {
            "item_no": "59",
            "pages": [42, 43],
            "group_row_count": 2,
            "continuation_markers": [{"raw_text": "续 59", "page_number": 43}],
            "effective_test_results": ["0.05 mA", "——"],
            "actual_conclusion_candidates": [{"value": "符合", "source": "row.conclusion"}],
            "complex_matrix_table": True,
            "complex_matrix_reason": "8.7 漏电流多页复杂矩阵需要专门矩阵审核",
            "known_columns": ["检验项目", "检验结果", "单项结论"],
            "placeholder_tokens": ["——", "/"],
            "non_placeholder_tokens": ["0.05 mA", "符合"],
            "candidate_conclusion": "符合",
        },
        "missing_complex_matrix_evidence_reasons": [],
    }
    target = CodexReviewTarget(
        target_id="target-c07-59",
        target_type=CodexReviewTargetType.INSPECTION_ITEM,
        check_id="C07",
        finding_id="finding-c07-59",
        finding_code="CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX",
        title="C07 complex matrix review target",
        summary="复核 C07 item 59 漏电流复杂矩阵。",
        evidence_refs=[
            CodexEvidenceRef(
                ref_id=ref,
                source_type="image" if ref.startswith("c07_complex_matrix_") else "rule_context",
            )
            for ref in refs
        ],
        metadata={
            "complex_matrix_table": True,
            "complex_matrix_reason": "8.7 漏电流多页复杂矩阵需要专门矩阵审核",
            "c07_visual_evidence": {
                "has_visual_input": True,
                "visual_review_mode": "complex_matrix_table",
            },
            "c07_complex_matrix_evidence": matrix_metadata,
        },
    )
    request = CodexReviewRequest(
        request_id="request-c07-59",
        task_id="task-1",
        task_type="report_check",
        targets=[target],
        prompt_version="codex-review-prompt-v1",
        schema_version="codex-review-output-v1",
        created_at=CREATED_AT,
    )
    text_items = [
        EvidenceItem(
            ref_id="finding:finding-c07-59",
            source_type=EvidenceSourceType.FINDING,
            text="C07 complex matrix deterministic finding 是 candidate。",
        ),
        EvidenceItem(
            ref_id="rule_context:finding-c07-59",
            source_type=EvidenceSourceType.RULE_CONTEXT,
            text="rule_context: complex_matrix_table=true, item 59 需要专门矩阵审核。",
        ),
        EvidenceItem(
            ref_id="symbol_note:finding-c07-59",
            source_type=EvidenceSourceType.PAGE_TEXT,
            text="首页说明：“——”表示此项不适用；“/”表示此项空白。",
        ),
        EvidenceItem(
            ref_id="inspection_item:finding-c07-59",
            source_type=EvidenceSourceType.TABLE,
            structured={"inspection_item_group": {"item_no": "59", "pages": [42, 43]}},
        ),
    ]
    image_items = [
        EvidenceItem(
            ref_id=ref,
            source_type=EvidenceSourceType.IMAGE,
            file_path=file_path,
            page_number=page,
            section="c07_complex_matrix_visual",
            metadata={"codex_image_input": True, "render_page_number": page, "matrix_evidence_role": role},
        )
        for ref, file_path, page, role in [
            ("c07_complex_matrix_page:finding-c07-59:p42", "items/finding-c07-59-c07-matrix-page-p42.png", 42, "page"),
            ("c07_complex_matrix_table:finding-c07-59:p42", "items/finding-c07-59-c07-matrix-table-p42.png", 42, "table"),
            ("c07_complex_matrix_header:finding-c07-59:p42", "items/finding-c07-59-c07-matrix-header-p42.png", 42, "header"),
            ("c07_complex_matrix_body:finding-c07-59:p42", "items/finding-c07-59-c07-matrix-body-p42.png", 42, "body"),
            ("c07_complex_matrix_result:finding-c07-59:p42", "items/finding-c07-59-c07-matrix-result-p42.png", 42, "result"),
            ("c07_complex_matrix_conclusion:finding-c07-59:p42", "items/finding-c07-59-c07-matrix-conclusion-p42.png", 42, "conclusion"),
            ("c07_complex_matrix_continuation:finding-c07-59:p43", "items/finding-c07-59-c07-matrix-continuation-p43.png", 43, "continuation"),
        ]
    ]
    package = EvidencePackage(
        package_id="pkg-c07-59",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        created_at=CREATED_AT,
        targets=[
            EvidenceTarget(
                target_id=target.target_id,
                target_type=target.target_type.value,
                check_id="C07",
                finding_id=target.finding_id,
                finding_code=target.finding_code,
                evidence_refs=refs,
            )
        ],
        items=[*text_items, *image_items],
    )
    return request, package
