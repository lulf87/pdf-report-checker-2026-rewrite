from __future__ import annotations

import json
import multiprocessing as mp
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.application.ptr_compare_usecase import PTRCompareUseCase
from app.application.task_service import TaskService
from app.domain.codex_review import CodexReviewVerdict
from app.domain.task import TaskState
from app.infrastructure.pdf.pymupdf_parser import PyMuPDFParser
from app.infrastructure.ptr.ptr_extractor import PTRExtractor
from app.infrastructure.report.field_extractor import FieldExtractor
from app.infrastructure.report.inspection_scope_extractor import ReportInspectionScopeExtractor
from app.infrastructure.report.inspection_table_extractor import InspectionTableExtractor
from app.infrastructure.report.parameter_table_extractor import ReportParameterTableExtractor
from app.infrastructure.storage.local_file_store import LocalFileStore
from tests.application.test_ptr_compare_usecase import FakePtrCodexAuditService


OLD_MATERIAL_DIR = Path("/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材")
REAL_SAMPLES = {
    "1539": (
        OLD_MATERIAL_DIR / "ptr/1539/射频脉冲电场消融系统产品技术要求-20260102-Clean.pdf",
        OLD_MATERIAL_DIR / "report/1539/QW2025-1539 Draft.pdf",
    ),
    "4788": (
        OLD_MATERIAL_DIR / "ptr/4788/CH3.4.1QuadraAllure3TMP技术要求_PM3562-1-0506最终.pdf",
        OLD_MATERIAL_DIR / "report/4788/4788draft.pdf",
    ),
    "2795": (
        OLD_MATERIAL_DIR / "ptr/2795/产品技术要求-心脏脉冲电场消融仪 - 1201.pdf",
        OLD_MATERIAL_DIR / "report/2795/QW2025-2795 Draft.pdf",
    ),
    "5780": (
        OLD_MATERIAL_DIR / "ptr/5780/消化道脉冲电场消融仪技术要求.pdf",
        OLD_MATERIAL_DIR / "report/5780/QW2025-5780 Draft.pdf",
    ),
    "0596": (
        OLD_MATERIAL_DIR / "ptr/0596/0596技术要求.pdf",
        OLD_MATERIAL_DIR / "report/0596/0596报告.pdf",
    ),
}


def test_real_1539_regression_content_driven_numeric_and_table_rows(tmp_path: Path) -> None:
    result = _run_real_sample_or_skip(tmp_path, "1539")
    details = result.metadata["ptr_comparison_details"]
    items = _items(details)

    output_rows = {row["atomic_id"]: row for row in items["2.2.1"]["atomic_comparison_rows"]}
    assert set(output_rows) == {"2.2.1:voltage", "2.2.1:current"}
    assert output_rows["2.2.1:voltage"]["actual"] == "3375"
    assert output_rows["2.2.1:voltage"]["status"] == "match"
    assert output_rows["2.2.1:current"]["actual"] == "59"
    assert output_rows["2.2.1:current"]["status"] == "match"

    rise_rows = {row["atomic_id"]: row for row in items["2.2.3"]["atomic_comparison_rows"]}
    assert rise_rows["2.2.3:rise_time:pulse3"]["actual"] == "430"
    assert rise_rows["2.2.3:rise_time:pf_reversible"]["actual"] == "455"
    assert all(row["status"] == "match" for row in rise_rows.values())

    fall_rows = {row["atomic_id"]: row for row in items["2.2.4"]["atomic_comparison_rows"]}
    assert fall_rows["2.2.4:fall_time:pulse3"]["actual"] == "260"
    assert fall_rows["2.2.4:fall_time:pf_reversible"]["actual"] == "205"
    assert all(row["status"] == "match" for row in fall_rows.values())

    energy_row = {row["atomic_id"]: row for row in items["2.2.6"]["atomic_comparison_rows"]}["2.2.6:max_energy"]
    assert energy_row["actual"] == "159"
    assert energy_row["status"] == "match"

    waveform_item = items["2.2.2"]
    assert waveform_item["effective_requirements"]
    assert {row.get("preset") for row in waveform_item["effective_requirements"]} == {
        "PULSE3",
        "PF Reversible",
    }
    assert all(row.get("table_title") == "波形参数" for row in waveform_item["effective_requirements"])
    assert waveform_item["requirement_alignment"]["status"] == "equivalent"
    assert waveform_item["result_compliance"]["status"] == "match"
    assert "软件功能" not in json.dumps(waveform_item["technical_evidence"]["ptr_tables"], ensure_ascii=False)

    software_item = items["2.6"]
    assert software_item["effective_requirements"]
    assert all(row.get("table_title") == "软件功能" for row in software_item["effective_requirements"])
    assert not any(row.get("preset") in {"PULSE3", "PF Reversible"} for row in software_item["effective_requirements"])
    assert software_item["requirement_alignment"]["status"] == "equivalent"
    assert software_item["result_compliance"]["status"] in {"match", "not_applicable"}
    assert "波形参数" not in json.dumps(software_item["technical_evidence"]["ptr_tables"], ensure_ascii=False)

    assert any(item.get("external_standard_coverages") for clause_id, item in items.items() if clause_id.startswith("2.5"))
    assert details["confirmed_errors_count"] == 0
    assert details["manual_review_required_count"] == 0
    assert details["overall_status"] == "passed"
    assert result.summary.manual_review_required_count == 0
    assert result.summary.final_audit_status == "passed"
    assert "/Users/" not in json.dumps(details, ensure_ascii=False)


def test_real_4788_regression_table_2_1_pvc_and_torque_wrench(tmp_path: Path) -> None:
    result = _run_real_sample_or_skip(tmp_path, "4788")
    details = result.metadata["ptr_comparison_details"]
    items = _items(details)

    for index in range(1, 13):
        assert items[f"2.1.{index}"]["atomic_comparison_rows"]

    item_211_rows = {row["atomic_id"]: row for row in items["2.1.1"]["atomic_comparison_rows"]}
    assert item_211_rows["2.1.1:basic_rate:nominal"]["expected"] == "60 min⁻¹"
    assert "60" in item_211_rows["2.1.1:basic_rate:nominal"]["actual"]
    assert "-8～+1" in item_211_rows["2.1.1:basic_rate:tolerance:240ohm"]["actual"]

    item_23 = items["2.3"]
    assert item_23["final_status"] == "passed"
    assert "PVC" not in item_23["ptr_clause_statement"]["local_text"]
    assert item_23["effective_requirements"]
    assert all("PVC" in row["label"] or "PVC" in str(row.get("expected") or "") for row in item_23["effective_requirements"])
    assert all("PVC" in row["standard_requirement_text"] for row in item_23["report_requirement_matches"])
    assert "PVC" in item_23["technical_evidence"]["ptr_full_text"]
    assert "PVC" in json.dumps(item_23["coverage_comparison_rows"], ensure_ascii=False)

    torque_rows = {row["atomic_id"]: row for row in items["2.8.2"]["atomic_comparison_rows"]}
    assert torque_rows["2.8.2:torque_wrench:A"]["actual"] == "0.884"
    assert torque_rows["2.8.2:torque_wrench:B"]["actual"] == "0.993"
    assert all(row["status"] == "match" for row in torque_rows.values())
    assert details["confirmed_errors_count"] == 0
    assert details["manual_review_required_count"] == 0
    assert details["overall_status"] == "passed"
    assert result.summary.manual_review_required_count == 0
    assert result.summary.final_audit_status == "passed"
    assert "/Users/" not in json.dumps(details, ensure_ascii=False)


def test_real_2795_regression_same_2_2_1_is_r_wave_sync_not_voltage_current(tmp_path: Path) -> None:
    result = _run_real_sample_or_skip(tmp_path, "2795")
    details = result.metadata["ptr_comparison_details"]
    items = _items(details)

    expected_waveform_actuals = {
        "2.1.1": {
            "2.1.1:voltage:nominal": "+71",
            "2.1.1:voltage:low_voltage": "+61",
        },
        "2.1.2": {"2.1.2:pulse_width": "+0.16"},
        "2.1.3": {"2.1.3:pulse_interval": "+0.099"},
        "2.1.4": {"2.1.4:pulse_group_interval": "3"},
        "2.1.5": {"2.1.5:rise_edge_time": "106"},
        "2.1.6": {"2.1.6:fall_edge_time": "434"},
        "2.1.7": {"2.1.7:pulse_group_cycles": "符合要求"},
        "2.1.8": {"2.1.8:treatment_wave_pulse_group_count": "符合要求"},
    }
    for clause_id, expected_rows in expected_waveform_actuals.items():
        item = items[clause_id]
        rows = {row["atomic_id"]: row for row in item["atomic_comparison_rows"]}
        for atomic_id, actual in expected_rows.items():
            assert rows[atomic_id]["actual"] == actual
            assert rows[atomic_id]["status"] == "match"
        assert item["user_facing_status"] == "covered_passed"

    item_221 = items["2.2.1"]
    atomic_ids = {row["atomic_id"] for row in item_221["atomic_comparison_rows"]}
    assert "2.2.1:voltage" not in atomic_ids
    assert "2.2.1:current" not in atomic_ids
    assert "2.2.1:r_wave_sync" in atomic_ids
    r_wave_row = next(row for row in item_221["atomic_comparison_rows"] if row["atomic_id"] == "2.2.1:r_wave_sync")
    assert r_wave_row["status"] == "match"
    assert item_221["report_matches"][0]["item_no"] == "158"

    item_222 = items["2.2.2"]
    assert "阻抗" in item_222["ptr_title"] or "阻抗" in item_222["ptr_requirement_text"]
    assert item_222["final_status"] == "passed"
    assert item_222["report_matches"][0]["single_conclusion"] == "符合"

    functional_clauses = ("2.3.1", "2.3.3", "2.4.1.1", "2.4.1.2", "2.4.2", "2.4.3")
    for clause_id in functional_clauses:
        rows = items[clause_id]["atomic_comparison_rows"]
        assert rows
        assert all(row["status"] == "match" for row in rows)
        assert items[clause_id]["final_status"] == "passed"

    assert "2.6.1" in items
    assert "2.6.2" in items
    assert items["2.6.1"]["final_status"] == "passed"
    assert items["2.6.2"]["final_status"] == "passed"
    assert any(
        coverage["standard"] == "GB 9706.1-2020"
        and coverage["start_item_no"] == "1"
        and coverage["end_item_no"] == "118"
        for coverage in items["2.6.1"]["external_standard_coverages"]
    )
    assert any(
        coverage["standard"] == "GB 9706.202-2021"
        and coverage["start_item_no"] == "119"
        and coverage["end_item_no"] == "156"
        for coverage in items["2.6.2"]["external_standard_coverages"]
    )

    assert not _has_finding(result, "PTR_SCOPE_EXCLUDED_TOPIC_PRESENT", clause_number="2.7")
    excluded_placeholders = details["scope_consistency"]["excluded_placeholders"]
    assert any(
        placeholder["item_no"] == "163"
        and placeholder["clause_number"] == "2.7"
        and placeholder["excluded_topic"] == "电磁兼容性"
        for placeholder in excluded_placeholders
    )
    assert details["confirmed_errors_count"] == 0
    assert details["manual_review_required_count"] == 0
    assert details["overall_status"] == "passed"
    assert result.summary.manual_review_required_count == 0
    assert result.summary.final_audit_status == "passed"
    assert "/Users/" not in json.dumps(details, ensure_ascii=False)


def test_real_5780_regression_textless_ptr_needs_ocr_and_emc_placeholder_is_not_error(tmp_path: Path) -> None:
    result = _run_real_sample_or_skip(tmp_path, "5780")
    details = result.metadata["ptr_comparison_details"]

    assert details["ptr_ocr_required"] is True
    assert details["requirements_count"] == 0
    assert details["overall_status"] != "passed"
    assert "OCR" in details["overall_summary"] or "无文本层" in details["overall_summary"]
    assert not _has_finding(result, "PTR_SCOPE_EXCLUDED_TOPIC_PRESENT", clause_number="2.6")
    assert details["confirmed_errors_count"] == 0
    assert result.summary.manual_review_required_count == details["manual_review_required_count"]
    assert result.summary.final_audit_status == "needs_manual_review"
    assert "/Users/" not in json.dumps(details, ensure_ascii=False)


def test_real_0596_numeric_limits_ignore_title_and_unit_formatting(tmp_path: Path) -> None:
    result = _run_real_sample_or_skip(tmp_path, "0596")
    details = result.metadata["ptr_comparison_details"]
    items = _items(details)

    pulse_width_item = items["2.1.3"]
    statement = pulse_width_item["ptr_clause_statement"]
    assert statement["clause_id"] == "2.1.3"
    assert statement["title"] == "脉冲宽度"
    assert "心房和心室脉冲宽度应符合表3的要求" in statement["local_text"].replace(" ", "")
    assert "起搏模式" not in statement["local_text"]
    assert "灵敏度" not in statement["local_text"]
    assert pulse_width_item["ptr_requirement_text"] == statement["local_text"]

    effective_requirements = pulse_width_item["effective_requirements"]
    assert effective_requirements
    assert all("脉冲" in row["label"] and "宽度" in row["label"] for row in effective_requirements)
    assert {row.get("model") for row in effective_requirements if row.get("model")} == {"6232"}
    assert any(row.get("table_number") == "3" and row.get("parent_clause") == "2.1" for row in effective_requirements)
    assert any("0.1" in str(row.get("expected") or "") and "0.35ms" in str(row.get("expected") or "") for row in effective_requirements)
    assert any("±35" in str(row.get("expected") or "") for row in effective_requirements)
    assert not any("起搏模式" in str(row) or "灵敏度" in str(row) for row in effective_requirements)

    report_requirements = pulse_width_item["report_requirement_matches"]
    assert report_requirements
    assert all("脉冲宽度" in str(row.get("standard_requirement_text") or "") for row in report_requirements)
    assert not any("起搏模式" in str(row) or "灵敏度" in str(row) for row in report_requirements)
    assert pulse_width_item["requirement_alignment"]["status"] == "equivalent"

    result_rows = pulse_width_item["result_comparisons"]
    assert len(result_rows) == 6
    assert {
        (row.get("condition"), row.get("load"), row.get("actual"))
        for row in result_rows
    } == {
        ("心房", "@500Ω", "-23～+23"),
        ("心房", "@240Ω", "-26～+23"),
        ("心房", "@2000Ω", "-22～+24"),
        ("心室", "@500Ω", "-22～+23"),
        ("心室", "@240Ω", "-24～+22"),
        ("心室", "@2000Ω", "-22～+23"),
    }
    assert all(row["unit"] == "μs" and row["status"] == "match" for row in result_rows)
    assert pulse_width_item["result_compliance"]["status"] == "match"
    assert pulse_width_item["coverage_status"] == "covered_passed"
    assert pulse_width_item["technical_evidence"]["ptr_full_text"]
    assert "起搏模式" in pulse_width_item["technical_evidence"]["ptr_full_text"]
    assert "灵敏度" in pulse_width_item["technical_evidence"]["ptr_full_text"]

    assert details["report_model_context"]["primary_model"] == "6232"
    registry = {entry["table_number"]: entry for entry in details["ptr_table_registry"]}
    assert {"2", "3"} <= set(registry)
    assert registry["3"]["parent_clause"] == "2.1"
    assert registry["3"]["table_title"] == "功能参数"
    assert registry["3"]["column_axes"][0] == {
        "axis_type": "model",
        "labels": ["6131", "6132", "6231", "6232"],
    }

    pacing_rows = [
        row
        for row in items["2.1.1"]["atomic_comparison_rows"]
        if row.get("model_column") == "6232" and row["label"] == "起搏模式"
    ]
    assert len(pacing_rows) == 1
    assert pacing_rows[0]["parent_clause"] == "2.1"
    assert pacing_rows[0]["table_key"] == "2.1:表3:功能参数"
    assert "DDD" in pacing_rows[0]["expected"]
    assert pacing_rows[0]["actual"] == "符合要求"
    assert pacing_rows[0]["status"] == "match"

    physical_item = next(item for item in details["items"] if "产品物理特性" in (item.get("ptr_title") or ""))
    physical_rows = [
        row
        for row in physical_item["atomic_comparison_rows"]
        if row.get("model_column") == "6232"
    ]
    assert {row["label"].split(" (")[0].replace("\n", "") for row in physical_rows} >= {"尺寸", "重量", "体积"}
    assert all(row["table_key"] == "2.1:表2:基本参数" for row in physical_rows)
    assert all(row["status"] == "match" for row in physical_rows)
    assert all(row["report_page"] == 32 for row in physical_rows)

    ethylene_oxide_row = items["2.6"]["atomic_comparison_rows"][0]
    assert ethylene_oxide_row["label"] == "环氧乙烷残留量"
    assert ethylene_oxide_row["expected"] == "≤10 μg/g"
    assert ethylene_oxide_row["actual"] == "<0.5"
    assert ethylene_oxide_row["status"] == "match"
    assert ethylene_oxide_row["report_item_no"] == "40"

    endotoxin_row = items["2.7"]["atomic_comparison_rows"][0]
    assert endotoxin_row["label"] == "细菌内毒素"
    assert endotoxin_row["expected"] == "≤20 EU/件"
    assert endotoxin_row["actual"] == "<20"
    assert endotoxin_row["status"] == "match"
    assert endotoxin_row["report_item_no"] == "41"

    assert not _has_finding(result, "PTR_CLAUSE_TEXT_MISMATCH", clause_number="2.6")
    assert not _has_finding(result, "PTR_CLAUSE_TEXT_MISMATCH", clause_number="2.7")
    remaining_text_mismatches = {
        finding["metadata"].get("clause_number")
        for finding in result.findings
        if finding["code"] == "PTR_CLAUSE_TEXT_MISMATCH"
    }
    assert remaining_text_mismatches == {"2.10", "2.11"}
    version_findings = [
        finding
        for finding in result.findings
        if finding["code"] == "PTR_CLAUSE_TEXT_MISMATCH"
        and finding["metadata"].get("clause_number") in {"2.10", "2.11"}
    ]
    assert all(finding["metadata"].get("requirement_type") == "standard_version_mismatch" for finding in version_findings)
    assert all(finding["metadata"].get("user_facing_status") == "needs_policy_review" for finding in version_findings)
    assert "2.1" not in items
    assert "ptr-2.1" in details["section_container_clause_ids"]
    for clause_id in ("2.1.7", "2.1.9", "2.1.12"):
        assert not any("40k" in str(row.get("expected") or "").lower() for row in items[clause_id]["atomic_comparison_rows"])

    basic_rate_actuals = {row.get("actual") for row in items["2.1.4.1"]["atomic_comparison_rows"]}
    magnetic_rate_actuals = {row.get("actual") for row in items["2.1.4.2"]["atomic_comparison_rows"]}
    assert "-0～+1" in basic_rate_actuals
    assert "38" not in basic_rate_actuals
    assert "+0" in magnetic_rate_actuals
    assert "38" not in magnetic_rate_actuals

    for clause_id in ("2.1.6.1", "2.1.6.2"):
        assert items[clause_id]["atomic_comparison_rows"]
        assert all(row["status"] == "match" for row in items[clause_id]["atomic_comparison_rows"])
        assert len(items[clause_id]["atomic_comparison_rows"]) == 2

    escape_rows = items["2.1.7"]["atomic_comparison_rows"]
    assert any(row.get("actual") == "-1～+1" and row["status"] == "match" for row in escape_rows)

    av_rows = items["2.1.9"]["atomic_comparison_rows"]
    assert {"-1～+0", "+2～+10"} <= {row.get("actual") for row in av_rows}
    assert any(
        diagnostic.get("code") == "clause_number_mismatch_but_title_match"
        for row in av_rows
        for diagnostic in row.get("diagnostics", [])
    )

    blanking_rows = items["2.1.11"]["atomic_comparison_rows"]
    assert blanking_rows
    assert all(row.get("table_key") == "2.1:表6:空白期/最短不应期" for row in blanking_rows)
    assert {"+0", "-2", "-4～+2", "-7～+1", "-4"} <= {row.get("actual") for row in blanking_rows}
    blanking_actuals = {
        (row["label"], row.get("condition")): row.get("actual")
        for row in blanking_rows
        if row["label"] in {"心房感知", "心房起搏", "心室感知", "心室起搏"}
    }
    assert blanking_actuals == {
        ("心房感知", "心房"): "+0",
        ("心房起搏", "心房"): "符合要求",
        ("心房起搏", "心室"): "-2",
        ("心室感知", "心房"): "-4～+2",
        ("心室感知", "心室"): "+0",
        ("心室起搏", "心房"): "-7～+1",
        ("心室起搏", "心室"): "-4",
    }

    max_tracking_rows = items["2.1.12"]["atomic_comparison_rows"]
    assert any(row.get("actual") == "-2～+1" and row["status"] == "match" for row in max_tracking_rows)

    physical_actuals = {
        value
        for row in physical_item["atomic_comparison_rows"]
        for value in str(row.get("actual") or "").split(" / ")
    }
    assert {"+0.2", "-0.1", "+0.4", "-0.3", "+0.7"} <= physical_actuals
    assert len(physical_rows) == 5
    input_impedance = items["2.1.8"]
    input_identity = input_impedance["clause_identity_alignment"]
    assert input_identity["status"] == "identity_mismatch"
    assert input_identity["selected_report_clause_number"] is None
    exact_number_candidate = next(
        candidate
        for candidate in input_identity["candidates"]
        if candidate["report_clause_number"] == "2.1.8"
    )
    assert exact_number_candidate["report_title"] == "房室间期"
    assert exact_number_candidate["rejected_reason"] == "exact_number_semantic_conflict"
    assert input_impedance["requirement_alignment"]["status"] == "needs_review"
    assert input_impedance["result_compliance"]["status"] == "needs_review"
    assert input_impedance["report_requirement_matches"] == []
    assert any("40k" in str(row.get("expected") or "").lower() for row in input_impedance["effective_requirements"])
    assert all(row.get("actual") is None for row in input_impedance["atomic_comparison_rows"])
    assert input_impedance["coverage_status"] == "confirmed_error"
    assert input_impedance["final_status"] == "confirmed_error"

    av_identity = items["2.1.9"]["clause_identity_alignment"]
    assert av_identity["status"] == "semantic_match_number_mismatch"
    assert av_identity["selected_report_clause_number"] == "2.1.8"
    assert av_identity["selected_report_title"] == "房室间期"
    assert av_identity["number_matches"] is False
    assert av_identity["title_matches"] is True
    for clause_id in ("2.1.9", "2.1.10", "2.1.11", "2.1.12", "2.1.13"):
        assert items[clause_id]["coverage_status"] == "confirmed_document_issue"
        assert items[clause_id]["final_status"] == "confirmed_document_issue"

    offset_groups = details["clause_sequence_offset_groups"]
    assert len(offset_groups) == 1
    assert offset_groups[0]["parent_clause"] == "2.1"
    assert offset_groups[0]["offset"] == -1
    assert offset_groups[0]["confidence"] == "high"
    assert [entry["ptr"] for entry in offset_groups[0]["affected_clauses"]] == [
        "2.1.9",
        "2.1.10",
        "2.1.11",
        "2.1.12",
        "2.1.13",
    ]

    identity_findings = {
        (finding["code"], finding["metadata"].get("clause_number"))
        for finding in result.findings
        if finding["code"]
        in {
            "PTR_CLAUSE_IDENTITY_MISMATCH",
            "PTR_REPORT_CLAUSE_NUMBER_MISMATCH",
        }
    }
    assert identity_findings == {
        ("PTR_CLAUSE_IDENTITY_MISMATCH", "2.1.8"),
        ("PTR_REPORT_CLAUSE_NUMBER_MISMATCH", "2.1.9"),
        ("PTR_REPORT_CLAUSE_NUMBER_MISMATCH", "2.1.10"),
        ("PTR_REPORT_CLAUSE_NUMBER_MISMATCH", "2.1.11"),
        ("PTR_REPORT_CLAUSE_NUMBER_MISMATCH", "2.1.12"),
        ("PTR_REPORT_CLAUSE_NUMBER_MISMATCH", "2.1.13"),
    }
    sensitivity = items["2.1.5"]
    assert sensitivity["requirement_alignment"]["status"] == "equivalent"
    assert sensitivity["result_compliance"]["status"] == "match"
    assert all(
        row["verification_basis"] == "pass_by_report_conclusion"
        for row in sensitivity["result_comparisons"]
    )
    torque = items["2.8.1.2"]
    assert torque["requirement_alignment"]["status"] == "equivalent"
    assert torque["result_compliance"]["status"] == "match"
    torque_rows = {row["atomic_id"]: row for row in torque["atomic_comparison_rows"]}
    assert torque_rows["2.8.1.2:torque_withstand"]["actual"] == "符合要求"
    assert torque_rows["2.8.1.2:torque_withstand"]["status"] == "match"
    assert torque_rows["2.8.1.2:preset_torque"]["expected"] == "8.5±1.41 N·cm"
    assert torque_rows["2.8.1.2:preset_torque"]["actual"] == "+0.58"
    assert torque_rows["2.8.1.2:preset_torque"]["status"] == "match"
    assert "ptr-2.1" in details["section_container_clause_ids"]
    for clause_id in ("2.10", "2.11"):
        assert items[clause_id]["requirement_alignment"]["status"] == "needs_policy_review"
        assert items[clause_id]["coverage_status"] == "needs_policy_review"
        assert items[clause_id]["final_status"] == "needs_policy_review"
    assert details["confirmed_errors_count"] == 1
    assert details["confirmed_findings_count"] == 2
    assert details["confirmed_document_issue_count"] == 1
    assert details["manual_review_required_count"] == 0
    assert details["policy_review_required_count"] == 2
    assert details["overall_status"] == "failed"
    assert result.summary.manual_review_required_count == details["manual_review_required_count"]
    assert result.summary.confirmed_findings_count == details["confirmed_findings_count"]
    assert result.summary.confirmed_errors_count == details["confirmed_errors_count"]
    assert result.summary.confirmed_document_issue_count == details["confirmed_document_issue_count"]
    assert result.summary.policy_review_required_count == details["policy_review_required_count"]
    assert result.summary.final_audit_status == "failed"
    assert "/Users/" not in json.dumps(details, ensure_ascii=False)


def _run_real_sample_or_skip(tmp_path: Path, sample_id: str):
    ptr_path, report_path = REAL_SAMPLES[sample_id]
    if not ptr_path.exists() or not report_path.exists():
        pytest.skip(f"real sample {sample_id} PDFs are not available on this machine.")

    output_path = tmp_path / f"{sample_id}-result.json"
    context = mp.get_context("spawn")
    process = context.Process(target=_run_real_sample_worker, args=(sample_id, str(tmp_path / sample_id), str(output_path)))
    process.start()
    process.join(180)
    if process.is_alive():
        process.terminate()
        process.join(10)
        pytest.fail(f"real sample {sample_id} comparison timed out")
    if process.exitcode != 0:
        error_payload = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
        pytest.fail(f"real sample {sample_id} comparison failed: {error_payload.get('error', process.exitcode)}")
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    return SimpleNamespace(
        metadata=payload["metadata"],
        findings=payload["findings"],
        summary=SimpleNamespace(**payload["summary"]),
    )


def _run_real_sample_worker(sample_id: str, store_dir: str, output_path: str) -> None:
    try:
        payload = _run_real_sample_payload(Path(store_dir), sample_id)
        Path(output_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os._exit(0)
    except Exception as exc:  # pragma: no cover - surfaced to parent process.
        Path(output_path).write_text(json.dumps({"error": repr(exc)}, ensure_ascii=False), encoding="utf-8")
        os._exit(1)


def _run_real_sample_payload(store_dir: Path, sample_id: str) -> dict:
    ptr_path, report_path = REAL_SAMPLES[sample_id]
    task_service = TaskService()
    usecase = PTRCompareUseCase(
        task_service=task_service,
        file_store=LocalFileStore(store_dir),
        pdf_parser=PyMuPDFParser(),
        ptr_extractor=PTRExtractor(),
        report_extractor=FieldExtractor(),
        inspection_table_extractor=InspectionTableExtractor(),
        inspection_scope_extractor=ReportInspectionScopeExtractor(),
        parameter_table_extractor=ReportParameterTableExtractor(),
        codex_audit_service=FakePtrCodexAuditService(
            verdict=CodexReviewVerdict.CONFIRM if sample_id == "0596" else CodexReviewVerdict.UNCERTAIN
        ),
    )
    status = usecase.run(
        ptr_file_name=ptr_path.name,
        ptr_content=ptr_path.read_bytes(),
        report_file_name=report_path.name,
        report_content=report_path.read_bytes(),
        audit_options={"run_codex": True},
    )
    assert status.status == TaskState.COMPLETED, status.error_message
    result = task_service.get_result(status.task_id)
    return {
        "metadata": result.metadata,
        "findings": [finding.model_dump(mode="json") for finding in result.findings],
        "summary": result.summary.model_dump(mode="json"),
    }


def _items(details: dict) -> dict[str, dict]:
    return {item["ptr_clause_id"]: item for item in details["items"]}


def _has_finding(result, code: str, *, clause_number: str | None = None) -> bool:
    for finding in result.findings:
        finding_code = finding.get("code") if isinstance(finding, dict) else finding.code
        metadata = finding.get("metadata", {}) if isinstance(finding, dict) else finding.metadata
        if finding_code != code:
            continue
        if clause_number is not None and str(metadata.get("clause_number") or "") != clause_number:
            continue
        return True
    return False
