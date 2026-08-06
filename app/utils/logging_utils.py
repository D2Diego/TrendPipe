import os
import threading

from loguru import logger


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)
LOG_RECORD_FORMAT = (
    "<green>{time:%Y-%m-%d %H:%M:%S}</> | "
    "<level>{level}</> | "
    '"{file.path}:{line}":<blue> {function}</> '
    "- <level>{message}</>\n"
)
# Loguru's initial terminal handler has ID 0. WebUI reloads may replace it but
# must retain temporary sinks used by running tasks.
_terminal_handler_id: int | None = 0
_terminal_handler_lock = threading.RLock()


def format_log_record(record):
    """
    Apply one format to terminal and WebUI logs.

    Multiple sinks may process the same record, so accept both absolute paths
    and paths already shortened to ``./``. WebUI disables color but otherwise
    uses the same timestamp, level, location, and message.
    """
    file_path = record["file"].path
    if os.path.isabs(file_path):
        relative_path = os.path.relpath(file_path, PROJECT_ROOT)
        record["file"].path = f"./{relative_path}"

    # Shorten task paths consistently across terminal and WebUI entry points.
    record["message"] = record["message"].replace(PROJECT_ROOT, ".")
    return LOG_RECORD_FORMAT


def configure_terminal_logger(sink, level: str, colorize: bool = True) -> int:
    """
    Replace the process terminal handler while preserving task-specific sinks.

    Streamlit may initialize logging after reloads. Remove only the known
    terminal handler and guard its ID against concurrent browser sessions.
    """
    global _terminal_handler_id

    with _terminal_handler_lock:
        if _terminal_handler_id is not None:
            try:
                logger.remove(_terminal_handler_id)
            except ValueError:
                # Tests or external entry points may already have removed it;
                # continue without disturbing other valid sinks.
                pass

        _terminal_handler_id = logger.add(
            sink,
            level=level,
            format=format_log_record,
            colorize=colorize,
        )
        return _terminal_handler_id
