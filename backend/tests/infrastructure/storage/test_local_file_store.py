import pytest

from app.domain.result import CheckResult, CheckStatus
from app.infrastructure.storage.local_file_store import LocalFileStore


def _check_result(task_id: str, check_id: str = "C01") -> CheckResult:
    return CheckResult(
        task_id=task_id,
        check_id=check_id,
        check_name=f"{check_id} check",
        status=CheckStatus.PASS,
        summary=f"{check_id} passed",
    )


def test_local_file_store_creates_runtime_directories(tmp_path) -> None:
    store = LocalFileStore(tmp_path / "runtime")

    store.ensure_root()

    assert (tmp_path / "runtime" / "uploads").is_dir()
    assert (tmp_path / "runtime" / "results").is_dir()
    assert (tmp_path / "runtime" / "exports").is_dir()


def test_local_file_store_saves_upload_under_runtime_root(tmp_path) -> None:
    store = LocalFileStore(tmp_path / "runtime")

    stored = store.save_upload(
        task_id="task-1",
        category="report",
        file_name="report.pdf",
        content=b"%PDF-1.4",
        content_type="application/pdf",
    )

    assert stored.path.is_relative_to(store.ensure_root())
    assert stored.path.read_bytes() == b"%PDF-1.4"
    assert stored.path.name == "report.pdf"
    assert stored.path.parent.name == "report"
    assert stored.path.parent.parent.name == "task-1"
    assert stored.path.parent.parent.parent.name == "uploads"
    assert stored.input_file.file_id == "task-1:report.pdf"
    assert stored.input_file.file_name == "report.pdf"
    assert stored.input_file.content_type == "application/pdf"
    assert store.get_upload_path(task_id="task-1", file_name="report.pdf", category="report") == stored.path


def test_local_file_store_saves_and_reads_check_result_json(tmp_path) -> None:
    store = LocalFileStore(tmp_path / "runtime")
    result = _check_result("task-1")

    stored = store.save_result_json(task_id="task-1", check_results=[result])
    loaded = store.read_result_json(task_id="task-1")

    assert stored.path == tmp_path / "runtime" / "results" / "task-1.json"
    assert stored.path.is_file()
    assert loaded == [result]


def test_local_file_store_saves_and_reads_export_file(tmp_path) -> None:
    store = LocalFileStore(tmp_path / "runtime")

    stored = store.save_export(
        task_id="task-1",
        file_name="task-1.json",
        content=b'{"ok": true}',
        content_type="application/json",
    )
    content = store.read_export(task_id="task-1", file_name="task-1.json")

    assert stored.path == tmp_path / "runtime" / "exports" / "task-1" / "task-1.json"
    assert stored.content_type == "application/json"
    assert content == b'{"ok": true}'


def test_local_file_store_raises_for_missing_result_upload_or_export(tmp_path) -> None:
    store = LocalFileStore(tmp_path / "runtime")

    with pytest.raises(FileNotFoundError):
        store.get_upload_path(task_id="task-1", file_name="missing.pdf")
    with pytest.raises(FileNotFoundError):
        store.read_result_json(task_id="task-1")
    with pytest.raises(FileNotFoundError):
        store.read_export(task_id="task-1", file_name="missing.json")


def test_local_file_store_rejects_paths_outside_root(tmp_path) -> None:
    store = LocalFileStore(tmp_path / "runtime")

    with pytest.raises(ValueError, match="path must stay"):
        store.resolve_under_root("../outside.pdf")

    with pytest.raises(ValueError, match="path separators"):
        store.save_upload(
            task_id="task-1",
            file_name="../report.pdf",
            content=b"pdf",
        )


@pytest.mark.parametrize("task_id", ["", "../task", "task/1", "task 1"])
def test_local_file_store_rejects_unsafe_task_ids(tmp_path, task_id: str) -> None:
    store = LocalFileStore(tmp_path / "runtime")

    with pytest.raises(ValueError, match="invalid task id"):
        store.save_upload(task_id=task_id, file_name="report.pdf", content=b"pdf")


@pytest.mark.parametrize("category", ["../report", "report/pdf", "report pdf"])
def test_local_file_store_rejects_unsafe_categories(tmp_path, category: str) -> None:
    store = LocalFileStore(tmp_path / "runtime")

    with pytest.raises(ValueError, match="invalid upload category"):
        store.save_upload(
            task_id="task-1",
            category=category,
            file_name="report.pdf",
            content=b"pdf",
        )


def test_local_file_store_uses_octet_stream_when_content_type_is_blank(tmp_path) -> None:
    store = LocalFileStore(tmp_path / "runtime")

    stored = store.save_upload(
        task_id="task-1",
        file_name="report.pdf",
        content=b"pdf",
        content_type="",
    )

    assert stored.input_file.content_type == "application/octet-stream"
