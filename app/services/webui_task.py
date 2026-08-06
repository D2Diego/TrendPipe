import threading
from collections import deque

from loguru import logger

from app.config import config
from app.controllers.manager.memory_manager import InMemoryTaskManager
from app.models import const
from app.models.schema import VideoParams
from app.services import state as sm
from app.services import task as tm
from app.utils.logging_utils import format_log_record


# WebUI . The configuration is saved in a process-level global dictionary. Original sync realization will be held during full generation
# runtime_config_lock，So different browser sessions are actually serially executed. Here's the number of simultaneous rounds.
# Yes 1，Continues the original configuration consistency and avoids multiple threads waiting in vain outside the configuration lock.
_task_manager = InMemoryTaskManager(
    max_concurrent_tasks=1,
    max_queued_tasks=max(1, int(config.app.get("max_queued_tasks", 100))),
)
_task_logs: dict[str, deque[str]] = {}
_task_logs_lock = threading.RLock()
_MAX_LOG_TASKS = 20
_MAX_LOG_RECORDS_PER_TASK = 1000
# Streamlit The component cannot be updated directly from the back-office thread, only by Fragment Rotation.0.5 sec
# That's enough. WebUI Logs are close to the real-time output of terminals and do not continuously occupy browser resources as is done for high-frequency repainting.
TASK_LOG_REFRESH_INTERVAL_SECONDS = 0.5


def _append_task_log(task_id: str, message: str) -> None:
    """Keep a limited number of logs by task for Streamlit Fragment Safety shifts."""
    with _task_logs_lock:
        records = _task_logs.get(task_id)
        if records is None:
            # Keep only recent task logs, avoid WebUI The service continues to occupy memory after long running.
            # dict Keep the order of insertion; task logs are used only for interface diagnostics and phase out the earliest records does not affect tasks.
            if len(_task_logs) >= _MAX_LOG_TASKS:
                oldest_task_id = next(iter(_task_logs))
                _task_logs.pop(oldest_task_id, None)
            records = deque(maxlen=_MAX_LOG_RECORDS_PER_TASK)
            _task_logs[task_id] = records
        records.append(message.rstrip())


def get_task_logs(task_id: str) -> list[str]:
    """Returns the log snapshot to avoid holding the lock used for the backstage thread during the page rendering."""
    with _task_logs_lock:
        return list(_task_logs.get(task_id, ()))


def _run_generation(
    task_id: str,
    params: VideoParams,
    capture_logs: bool,
    voice_preview: dict | None = None,
) -> dict:
    """
    Implementation of existing video streaming lines in back-office lines.

    Loguru Yes. sink It is a process-level resource and must therefore be filtered according to the current work schedule. Otherwise it runs simultaneously.
    API Other Organiser Pages read only normal list snapshots, not from backstage
    Thread access Streamlit session_state，Avoid refreshing the root causes. delta Paths are messy.
    """
    log_handler_id = None
    worker_thread_id = threading.get_ident()
    try:
        if capture_logs:
            log_handler_id = logger.add(
                lambda message: _append_task_log(task_id, str(message)),
                level="DEBUG",
                format=format_log_record,
                colorize=False,
                filter=lambda record: record["thread"].id == worker_thread_id,
            )

        # The complete task still uses the previous configuration lock to prevent another WebUI Sessions Generating Midway Changes
        # Provider、Keys, etc. process level configuration, resulting in different settings before and after the same video.
        with config.runtime_config_lock():
            return tm.start(
                task_id=task_id,
                params=params,
                voice_preview=voice_preview,
            )
    except Exception as exc:
        # tm.start Has been responsible for converting water flow lines to failure; extra protection log here sink、
        # Configure Locks etc. WebUI Packing layer. Any backstage wiring must remain final.
        # The manager displays " Generating " permanently after the workspace has been withdrawn.
        error = f"{type(exc).__name__}: {exc}"
        failure = {
            "task_id": task_id,
            "state": const.TASK_STATE_FAILED,
            "progress": 0,
            "failed_stage": "webui_worker",
            "error": error,
        }
        sm.state.update_task(
            task_id,
            state=failure["state"],
            progress=failure["progress"],
            failed_stage=failure["failed_stage"],
            error=failure["error"],
        )
        logger.exception(
            f"unexpected WebUI generation worker failure, "
            f"task_id={task_id}, error={exc}"
        )
        return failure
    finally:
        if log_handler_id is not None:
            try:
                logger.remove(log_handler_id)
            except ValueError:
                logger.debug(
                    f"WebUI task log handler already removed: task_id={task_id}"
                )


def submit_generation(
    task_id: str,
    params: VideoParams,
    capture_logs: bool = True,
    voice_preview: dict | None = None,
) -> None:
    """
    Registration and submission WebUI Video generation task, return immediately upon call.

    Task status must be written before the online process starts. This way, when this script is finished, you can find the task.
    Browser Refresh or WebSocket Reconnecting does not depend on the placeholder in the old page memory.
    """
    task_params = params.model_copy(deep=True)
    # The preview payload contains only non-variable audio paths, parameter snapshots and read-only subtitles time axis. Copying external dictionaries,
    # Avoid Page Following rerun Replaces the cache field with tasks that have been submitted to the background queue.
    voice_preview_snapshot = dict(voice_preview) if voice_preview else None
    sm.state.update_task(
        task_id,
        state=const.TASK_STATE_PROCESSING,
        progress=0,
        video_subject=task_params.video_subject or task_params.video_script or task_id,
    )
    try:
        _task_manager.add_task(
            _run_generation,
            task_id=task_id,
            params=task_params,
            capture_logs=capture_logs,
            voice_preview=voice_preview_snapshot,
        )
    except Exception as exc:
        # The dispatch failure must be as searchable as the flow line failure, avoiding permanent display of the task manager
        # “Generating”. Retain an anomaly type easily from Docker Or the fast-positioning queue of the log.
        error = f"{type(exc).__name__}: {exc}"
        sm.state.update_task(
            task_id,
            state=const.TASK_STATE_FAILED,
            progress=0,
            failed_stage="scheduling",
            error=error,
        )
        logger.exception(
            f"failed to submit WebUI generation task, task_id={task_id}, error={exc}"
        )
        raise
