"""Application configuration - root APIRouter.

Defines all FastAPI application endpoints.

Resources:
    1. https://fastapi.tiangolo.com/tutorial/bigger-applications

"""

from fastapi import APIRouter

from app.controllers.v1 import (
    audio_upload,
    cache,
    config as config_v1,
    fonts,
    llm,
    providers,
    task_logs,
    task_history,
    video,
    version,
    voices,
)

root_api_router = APIRouter()
# v1
root_api_router.include_router(audio_upload.router)
root_api_router.include_router(cache.router)
root_api_router.include_router(task_history.router)
root_api_router.include_router(video.router)
root_api_router.include_router(version.router)
root_api_router.include_router(llm.router)
root_api_router.include_router(task_logs.router)
root_api_router.include_router(providers.router)
root_api_router.include_router(voices.router)
root_api_router.include_router(config_v1.router)
root_api_router.include_router(fonts.router)
