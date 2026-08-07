from dataclasses import asdict

from fastapi import Query, Request

from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.services import cache_manager
from app.utils import utils

router = new_router()


@router.get("/cache/video/stats", summary="Get video cache statistics")
def get_cache_stats(request: Request, max_age_days: int | None = Query(default=None)):
    try:
        stats = cache_manager.get_video_cache_stats(max_age_days=max_age_days)
    except ValueError as exc:
        raise HttpException(task_id="", status_code=400, message=str(exc))
    return utils.get_response(200, asdict(stats))


@router.delete("/cache/video", summary="Clean the video cache")
def clean_cache(request: Request, max_age_days: int | None = Query(default=None)):
    try:
        result = cache_manager.clean_video_cache(max_age_days=max_age_days)
    except ValueError as exc:
        raise HttpException(task_id="", status_code=400, message=str(exc))
    return utils.get_response(200, asdict(result))
