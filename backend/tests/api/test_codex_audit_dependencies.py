from __future__ import annotations

from pytest import MonkeyPatch

from app.api.routes_ptr_compare import get_ptr_compare_usecase
from app.api.routes_report_check import get_report_check_usecase
from app.application.task_service import TaskService
from app.core.config import Settings


def test_api_usecase_dependencies_default_to_codex_audit_disabled(monkeypatch: MonkeyPatch) -> None:
    def fail_run(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("API default dependency must not call subprocess.run")

    monkeypatch.setattr("app.infrastructure.codex.codex_cli_runner.subprocess.run", fail_run)
    settings = Settings(_env_file=None)
    task_service = TaskService()

    report_usecase = get_report_check_usecase(task_service=task_service, settings=settings)
    ptr_usecase = get_ptr_compare_usecase(task_service=task_service, settings=settings)

    assert report_usecase.codex_audit_enabled is False
    assert report_usecase.codex_audit_service is None
    assert ptr_usecase.codex_audit_enabled is False
    assert ptr_usecase.codex_audit_service is None
