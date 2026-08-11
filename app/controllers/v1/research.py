from fastapi import BackgroundTasks, Path, Request

from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.models.schema import (
    ArtifactChatRequest,
    CreateResearchRequest,
    UpdateResearchSettingsRequest,
)
from app.services import (
    research,
    research_artifacts,
    research_credentials,
    research_engine,
    research_store,
)
from app.utils import utils

router = new_router()


@router.post("/researches", summary="Start a new last30days research")
def create_research(
    request: Request,
    body: CreateResearchRequest,
    background_tasks: BackgroundTasks,
):
    try:
        created = research.create_research(body.topic, body.depth, body.sources)
    except research.ResearchValidationError as exc:
        raise HttpException(task_id="", status_code=400, message=str(exc)) from exc
    except research_engine.ResearchExecutionError as exc:
        raise HttpException(task_id="", status_code=502, message=str(exc)) from exc
    background_tasks.add_task(research.run_research_job, created["id"])
    return utils.get_response(200, created)


@router.get("/researches", summary="List past researches")
def list_researches(request: Request):
    return utils.get_response(
        200, {"researches": research_store.list_researches()}
    )


@router.get(
    "/researches/{research_id}",
    summary="Get a research and its completed report",
)
def get_research(request: Request, research_id: str = Path(...)):
    found = research_store.get_research(research_id)
    if found is None:
        raise HttpException(
            task_id=research_id, status_code=404, message="research not found"
        )
    payload = dict(found)
    payload["artifacts"] = research_store.list_artifacts(research_id)
    return utils.get_response(200, payload)


@router.post(
    "/researches/{research_id}/entities/{entity}/clusters/{cluster_id}/artifact-chat",
    summary="Continue a research artifact interview",
)
def artifact_chat(
    request: Request,
    body: ArtifactChatRequest,
    research_id: str = Path(...),
    entity: str = Path(...),
    cluster_id: str = Path(...),
):
    try:
        result = research_artifacts.chat(
            research_id,
            entity,
            cluster_id,
            list(body.selected_fields),
            [message.model_dump() for message in body.messages],
        )
    except research_artifacts.ArtifactValidationError as exc:
        raise HttpException(task_id=research_id, status_code=400, message=str(exc)) from exc
    except research_artifacts.ArtifactNotFoundError as exc:
        raise HttpException(task_id=research_id, status_code=404, message=str(exc)) from exc
    except research_artifacts.ArtifactConflictError as exc:
        raise HttpException(task_id=research_id, status_code=409, message=str(exc)) from exc
    except research_artifacts.ArtifactAgentError as exc:
        raise HttpException(task_id=research_id, status_code=502, message=str(exc)) from exc
    return utils.get_response(200, result)


@router.get(
    "/researches/{research_id}/entities/{entity}/clusters/{cluster_id}/restore-params",
    summary="Load complete video parameters from research artifacts",
)
def get_artifact_restore_params(
    request: Request,
    research_id: str = Path(...),
    entity: str = Path(...),
    cluster_id: str = Path(...),
):
    try:
        params = research_artifacts.restore_params(research_id, entity, cluster_id)
    except research_artifacts.ArtifactNotFoundError as exc:
        raise HttpException(task_id=research_id, status_code=404, message=str(exc)) from exc
    return utils.get_response(200, {"params": params})


@router.delete(
    "/researches/{research_id}/entities/{entity}/clusters/{cluster_id}/artifacts",
    summary="Delete the saved artifacts for a research cluster",
)
def delete_artifact(
    request: Request,
    research_id: str = Path(...),
    entity: str = Path(...),
    cluster_id: str = Path(...),
):
    deleted = research_store.delete_artifact(research_id, entity, cluster_id)
    if not deleted:
        raise HttpException(
            task_id=research_id, status_code=404, message="artifact not found"
        )
    return utils.get_response(200, {"deleted": True})


@router.delete("/researches/{research_id}", summary="Delete a research")
def delete_research(request: Request, research_id: str = Path(...)):
    try:
        deleted = research.delete_research(research_id)
    except research.ResearchConflictError as exc:
        raise HttpException(
            task_id=research_id, status_code=409, message=str(exc)
        ) from exc
    if not deleted:
        raise HttpException(
            task_id=research_id, status_code=404, message="research not found"
        )
    return utils.get_response(200, {"deleted": True})


@router.get(
    "/research-settings",
    summary="Check available last30days sources and credentials",
)
def get_research_settings(request: Request):
    try:
        diagnose = research_engine.run_diagnose()
    except research_engine.ResearchExecutionError as exc:
        raise HttpException(task_id="", status_code=502, message=str(exc)) from exc
    diagnose["credential_keys"] = research_credentials.credential_presence()
    return utils.get_response(200, diagnose)


@router.put("/research-settings", summary="Update last30days API keys")
def update_research_settings(
    request: Request, body: UpdateResearchSettingsRequest
):
    values = {key: value for key, value in body.values.items() if value}
    try:
        research_credentials.write_credentials(values)
    except ValueError as exc:
        raise HttpException(task_id="", status_code=400, message=str(exc)) from exc
    return utils.get_response(200, {"saved": True})


@router.delete("/research-settings/{key}", summary="Remove a last30days API key")
def delete_research_credential(request: Request, key: str = Path(...)):
    try:
        research_credentials.delete_credential(key)
    except ValueError as exc:
        raise HttpException(task_id="", status_code=400, message=str(exc)) from exc
    return utils.get_response(200, {"deleted": True})
