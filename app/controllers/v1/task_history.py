from fastapi import Path, Request

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
