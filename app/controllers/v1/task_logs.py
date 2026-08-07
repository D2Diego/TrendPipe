from fastapi import Path, Request

from app.controllers import base
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.services import api_task_logs
from app.services import state as sm
from app.utils import utils

router = new_router()


@router.get(
    "/tasks/{task_id}/logs",
    summary="Get captured log lines for a task (API task queue only)",
)
def get_task_logs_endpoint(
    request: Request, task_id: str = Path(..., description="Task ID")
):
    request_id = base.get_task_id(request)
    task = sm.state.get_task(task_id)
    if not task:
        raise HttpException(
            task_id=task_id, status_code=404, message=f"{request_id}: task not found"
        )

    logs = api_task_logs.get_task_logs(task_id)
    return utils.get_response(200, {"logs": logs})
