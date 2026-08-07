import json
import os
import re
from typing import Any

from loguru import logger

from app.models import const
from app.models.schema import VideoParams
from app.services import state as sm
from app.utils import file_security, utils

_FINAL_VIDEO_PATTERN = re.compile(r"^final-(?P<index>\d+)\.(?P<extension>mp4|mov|mkv|webm)$", re.IGNORECASE)


def find_final_task_video(task_path: str) -> str:
    try:
        files = os.listdir(task_path)
    except OSError:
        return ""
    candidates = []
    for file_name in files:
        match = _FINAL_VIDEO_PATTERN.fullmatch(file_name)
        if match:
            candidates.append((int(match.group("index")), file_name))
    return os.path.join(task_path, min(candidates)[1]) if candidates else ""


def safe_load_task_script(task_path: str) -> dict[str, Any]:
    script_file = os.path.join(task_path, "script.json")
    if not os.path.isfile(script_file):
        return {}
    try:
        with open(script_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning(f"failed to read task script data: {script_file}, {exc}")
        return {}


def scan_history_tasks(limit: int = 50) -> list[dict[str, Any]]:
    tasks_root = utils.task_dir()
    try:
        entries = [(entry.stat(follow_symlinks=False).st_mtime, entry.name, entry.path) for entry in os.scandir(tasks_root) if not entry.name.startswith(".") and entry.is_dir(follow_symlinks=False)]
    except OSError:
        return []
    entries.sort(reverse=True)
    results = []
    for mtime, task_id, task_path in entries[:limit]:
        script_data = safe_load_task_script(task_path)
        params = script_data.get("params") if isinstance(script_data.get("params"), dict) else {}
        video_file = find_final_task_video(task_path)
        results.append({
            "task_id": task_id,
            "subject": params.get("video_subject") or str(script_data.get("script") or "")[:40] or task_id,
            "state": const.TASK_STATE_COMPLETE if video_file else None,
            "progress": 100 if video_file else 0,
            "mtime": mtime,
            "task_path": task_path,
            "video_file": video_file,
            "source": "history",
        })
    return results


def _relative_task_path(path: str, tasks_root: str) -> str:
    if not path:
        return ""
    candidate = os.path.realpath(path if os.path.isabs(path) else os.path.join(tasks_root, path))
    try:
        if os.path.commonpath([tasks_root, candidate]) != tasks_root:
            return ""
    except ValueError:
        return ""
    return os.path.relpath(candidate, tasks_root).replace(os.sep, "/")


def collect_task_summaries(limit: int = 20) -> list[dict[str, Any]]:
    by_id = {task["task_id"]: task for task in scan_history_tasks(limit=50)}
    try:
        runtime_tasks, _ = sm.state.get_all_tasks(1, 50)
    except Exception as exc:
        logger.warning(f"failed to load runtime tasks: {exc}")
        runtime_tasks = []
    for task in runtime_tasks:
        task_id = str(task.get("task_id") or "")
        if not task_id:
            continue
        entry = by_id.setdefault(task_id, {"task_id": task_id, "source": "runtime"})
        entry["subject"] = task.get("video_subject") or entry.get("subject") or task_id
        entry["state"] = task.get("state")
        entry["progress"] = int(task.get("progress", entry.get("progress", 0)) or 0)
        videos = task.get("videos") or []
        if videos:
            entry["video_file"] = videos[0]
        task_path = entry.get("task_path") or os.path.join(utils.task_dir(), task_id)
        entry["task_path"] = task_path
        if os.path.isdir(task_path):
            entry["mtime"] = os.path.getmtime(task_path)
    tasks_root = os.path.realpath(utils.task_dir())
    merged = sorted(by_id.values(), key=lambda task: task.get("mtime", 0), reverse=True)[:limit]
    for task in merged:
        task["video_file"] = _relative_task_path(str(task.get("video_file") or ""), tasks_root)
        task["task_path"] = _relative_task_path(str(task.get("task_path") or ""), tasks_root)
    return merged


def load_task_restore_payload(task_id: str) -> dict[str, Any] | None:
    tasks_root = os.path.realpath(utils.task_dir())
    try:
        task_path = file_security.resolve_path_within_directory(tasks_root, str(task_id), require_file=False)
    except ValueError as exc:
        logger.warning(f"invalid task restore path: {task_id}, {exc}")
        return None
    script_data = safe_load_task_script(task_path)
    raw_params = script_data.get("params")
    if not isinstance(raw_params, dict):
        return None
    params_input = dict(raw_params)
    if script_data.get("script"):
        params_input["video_script"] = script_data["script"]
    if script_data.get("search_terms"):
        params_input["video_terms"] = script_data["search_terms"]
    try:
        params = VideoParams.model_validate(params_input).model_dump(mode="json")
    except Exception as exc:
        logger.warning(f"failed to validate task restore parameters: {task_id}, {exc}")
        return None
    return {"task_id": str(task_id), "subject": params.get("video_subject") or script_data.get("script") or task_id, "params": params}
