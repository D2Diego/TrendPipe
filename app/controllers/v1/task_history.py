import os

from fastapi import Path, Query, Request

from app.controllers import base
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.services import task_history
from app.utils import utils

router = new_router()


@router.get("/tasks/history", summary="List live and persisted task history")
def list_task_history(request: Request):
    return utils.get_response(200, {"tasks": task_history.collect_task_summaries(limit=20)})


@router.get("/tasks/{task_id}/restore-params", summary="Load validated parameters from a past task")
def get_task_restore_params(request: Request, task_id: str = Path(...)):
    payload = task_history.load_task_restore_payload(task_id)
    if payload is None:
        request_id = base.get_task_id(request)
        raise HttpException(task_id=task_id, status_code=404, message=f"{request_id}: task has no restorable parameters")
    return utils.get_response(200, payload)


@router.get("/tasks/{task_id}/file", summary="Read a file from a task folder")
def read_task_file(request: Request, task_id: str = Path(...), name: str = Query(..., description="File name inside the task folder")):
    # Build the path to the requested file inside the task directory and
    # return its text contents so the UI can preview logs and scripts.
    file_path = os.path.join(utils.task_dir(), task_id, name)
    if not os.path.isfile(file_path):
        request_id = base.get_task_id(request)
        raise HttpException(task_id=task_id, status_code=404, message=f"{request_id}: file not found")
    with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
        content = handle.read()
    return utils.get_response(200, {"name": name, "content": content})
