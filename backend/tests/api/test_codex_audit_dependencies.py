from __future__ import annotations

from pytest import MonkeyPatch

from app.api.routes_ptr_compare import get_ptr_compare_usecase
from app.api.routes_report_check import get_report_check_usecase
from app.application.task_service import TaskService
from app.core.config import Settings
from app.infrastructure.codex import CodexCliRunner


def test_api_usecase_dependencies_default_to_mandatory_codex_cli_without_executing(monkeypatch: MonkeyPatch) -> None:
    def fail_run(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("API dependency construction must not call subprocess.run")

    monkeypatch.setattr("app.infrastructure.codex.codex_cli_runner.subprocess.run", fail_run)
    settings = Settings(_env_file=None)
    task_service = TaskService()

    report_usecase = get_report_check_usecase(task_service=task_service, settings=settings)
    ptr_usecase = get_ptr_compare_usecase(task_service=task_service, settings=settings)

    assert report_usecase.codex_audit_service is not None
    assert ptr_usecase.codex_audit_service is not None
    assert isinstance(report_usecase.codex_audit_service.runner, CodexCliRunner)
    assert isinstance(ptr_usecase.codex_audit_service.runner, CodexCliRunner)
    assert report_usecase.codex_audit_service.runner.config.executable == "codex"
    assert ptr_usecase.codex_audit_service.runner.config.sandbox == "read-only"
