"""Application implementation - ASGI."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import config
from app.models.exception import HttpException
from app.router import root_api_router
from app.utils import utils


@asynccontextmanager
async def application_lifespan(_: FastAPI):
    """Focus API Process initiated recovery and closure logs."""
    logger.info("startup event")

    # Cross-platform release is executed by the current process thread pool and will not be restored after service restarts. On startup Redis
    # It recognizes that the state of activity that has lost the implementation process has failed to materialize, avoiding the permanent elimination of mandates.
    from app.services import research_store, task as task_service

    research_store.init_db()
    task_service.recover_interrupted_cross_posts()
    try:
        yield
    finally:
        logger.info("shutdown event")


def exception_handler(request: Request, e: HttpException):
    return JSONResponse(
        status_code=e.status_code,
        content=utils.get_response(e.status_code, e.data, e.message),
    )


def validation_exception_handler(request: Request, e: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content=utils.get_response(
            status=400, data=e.errors(), message="field required"
        ),
    )


def get_application() -> FastAPI:
    """Initialize FastAPI application.

    Returns:
       FastAPI: Application object instance.

    """
    instance = FastAPI(
        title=config.project_name,
        description=config.project_description,
        version=config.project_version,
        debug=False,
        lifespan=application_lifespan,
    )
    instance.include_router(root_api_router)
    instance.add_exception_handler(HttpException, exception_handler)
    instance.add_exception_handler(RequestValidationError, validation_exception_handler)
    return instance


app = get_application()

# Configures the CORS middleware for the FastAPI app
cors_allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
origins = cors_allowed_origins_str.split(",") if cors_allowed_origins_str else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

task_dir = utils.task_dir()
app.mount(
    "/tasks", StaticFiles(directory=task_dir, html=True, follow_symlink=True), name=""
)

# The React app (webui-react) is built into here and served same-origin,
# replacing the separate Nginx container that used to own this job.
public_dir = utils.public_dir()
app.mount(
    "/assets",
    StaticFiles(directory=os.path.join(public_dir, "assets")),
    name="assets",
)


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """Fall back to index.html for every non-API route.

    The frontend uses react-router's BrowserRouter (history-API routing), so
    a hard refresh on a client-side route like /researches/abc must still
    resolve to index.html and let the router take over - there is no real
    server-side route for it. This is registered last, after every API
    router and the /tasks and /assets mounts, so those keep taking priority.
    """
    return FileResponse(os.path.join(public_dir, "index.html"))
