import threading
from collections import deque

from loguru import logger

from app.services import task as tm

_task_logs: dict[str, deque[str]] = {}
_task_logs_lock = threading.RLock()
_MAX_LOG_TASKS = 20
_MAX_LOG_RECORDS_PER_TASK = 1000


def _append_task_log(task_id: str, message: str) -> None:
    """Keep a bounded per-task log ring buffer for the API task queue."""
    with _task_logs_lock:
        records = _task_logs.get(task_id)
        if records is None:
            if len(_task_logs) >= _MAX_LOG_TASKS:
                oldest_task_id = next(iter(_task_logs))
                _task_logs.pop(oldest_task_id, None)
            records = deque(maxlen=_MAX_LOG_RECORDS_PER_TASK)
            _task_logs[task_id] = records
        records.append(message.rstrip())


def get_task_logs(task_id: str) -> list[str]:
    """Return a snapshot of captured log lines for a task, newest last."""
    with _task_logs_lock:
        return list(_task_logs.get(task_id, ()))


def start_with_log_capture(task_id, params, stop_at="video", voice_preview=None):
    """Run app.services.task.start() with its logs captured per task_id.

    Must run ON the worker thread that app.controllers.manager.base_manager's
    TaskManager.execute_task() spawns for this task — it identifies "this
    task's" log lines by filtering on the calling thread's identity.
    """
    worker_thread_id = threading.get_ident()

    sink_id = logger.add(
        lambda message: _append_task_log(task_id, str(message)),
        filter=lambda record: record["thread"].id == worker_thread_id,
        format="{message}",
    )
    try:
        tm.start(task_id=task_id, params=params, stop_at=stop_at, voice_preview=voice_preview)
    finally:
        logger.remove(sink_id)
