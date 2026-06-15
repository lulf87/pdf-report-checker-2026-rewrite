from app.application.task_service import TaskResult
from app.domain.task import InputFileRef, TaskState, TaskStatus, TaskType


TaskStatusResponse = TaskStatus
TaskResultResponse = TaskResult


__all__ = [
    "InputFileRef",
    "TaskResult",
    "TaskResultResponse",
    "TaskState",
    "TaskStatus",
    "TaskStatusResponse",
    "TaskType",
]
