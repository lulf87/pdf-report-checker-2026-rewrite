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

    assert any(item.get("external_standard_coverages") for clause_id, item in items.items() if clause_id.startswith("2.5"))
    assert details["confirmed_errors_count"] == 0
    assert details["manual_review_required_count"] == 0
    assert details["overall_status"] == "passed"
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
    assert "PVC" in item_23["ptr_requirement_text"]
    assert "PVC" in json.dumps(item_23["coverage_comparison_rows"], ensure_ascii=False)

    torque_rows = {row["atomic_id"]: row for row in items["2.8.2"]["atomic_comparison_rows"]}
    assert torque_rows["2.8.2:torque_wrench:A"]["actual"] == "0.884"
    assert torque_rows["2.8.2:torque_wrench:B"]["actual"] == "0.993"
    assert all(row["status"] == "match" for row in torque_rows.values())
    assert details["confirmed_errors_count"] == 0
    assert details["manual_review_required_count"] == 0
    assert details["overall_status"] == "passed"
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
        codex_audit_service=FakePtrCodexAuditService(verdict=CodexReviewVerdict.UNCERTAIN),
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
