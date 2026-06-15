import pytest

from app.infrastructure.storage.local_file_store import LocalFileStore


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
    assert stored.input_file.file_id == "task-1:report.pdf"
    assert stored.input_file.file_name == "report.pdf"
    assert stored.input_file.content_type == "application/pdf"


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
