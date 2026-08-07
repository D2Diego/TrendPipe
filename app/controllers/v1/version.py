from dataclasses import asdict

from fastapi import Request

from app.config import config
from app.controllers.v1.base import new_router
from app.services import version_checker
from app.utils import utils

router = new_router()


@router.get("/version", summary="Get application version and update status")
def get_version_status(request: Request):
    snapshot = version_checker.poll_available_update(config.project_version)
    return utils.get_response(
        200,
        {
            "current_version": str(config.project_version),
            "release_url": version_checker.LATEST_RELEASE_PAGE_URL,
            **asdict(snapshot),
        },
    )
