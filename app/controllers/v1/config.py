from fastapi import Path, Request
from pydantic import BaseModel

from app.config import config
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.services import elevenlabs_music as elevenlabs_music_service
from app.services import sonilo as sonilo_service
from app.utils import utils

router = new_router()

# The settings UI needs every runtime section. This API intentionally has no
# authentication, matching the original local Streamlit UI. Keep the service
# bound to a trusted local/private network until authentication is added.
_EXPOSED_CONFIG_SECTIONS = set(config.RUNTIME_CONFIG_SECTIONS.keys())


class SetConfigValueRequest(BaseModel):
    value: object


@router.get(
    "/config/readiness",
    summary="Get non-sensitive generation provider readiness flags",
)
def get_generation_readiness(request: Request):
    return utils.get_response(
        200,
        {
            "pexels": bool(config.app.get("pexels_api_keys", "")),
            "pixabay": bool(config.app.get("pixabay_api_keys", "")),
            "coverr": bool(config.app.get("coverr_api_keys", "")),
            "sonilo": sonilo_service.is_enabled(),
            "elevenlabs": elevenlabs_music_service.is_enabled(),
        },
    )


def _resolve_section(section: str):
    if section not in _EXPOSED_CONFIG_SECTIONS:
        raise HttpException(
            task_id="",
            status_code=400,
            message=f"unknown config section: {section}",
        )
    return config.RUNTIME_CONFIG_SECTIONS[section]


@router.get("/config/{section}", summary="Get a runtime config section snapshot")
def get_config_section(request: Request, section: str = Path(...)):
    section_obj = _resolve_section(section)
    snapshot = config.snapshot_config_with_pending(section_obj)
    return utils.get_response(200, snapshot)


@router.put("/config/{section}/{key}", summary="Set a runtime config value")
def set_config_key(
    request: Request,
    body: SetConfigValueRequest,
    section: str = Path(...),
    key: str = Path(...),
):
    section_obj = _resolve_section(section)
    updated = config.update_config_nonblocking(section_obj, key, body.value)
    return utils.get_response(200, {"updated": updated})


@router.delete("/config/{section}/{key}", summary="Delete a runtime config value")
def delete_config_key(request: Request, section: str = Path(...), key: str = Path(...)):
    section_obj = _resolve_section(section)
    deleted = config.delete_config_nonblocking(section_obj, key)
    return utils.get_response(200, {"deleted": deleted})


@router.post("/config/save", summary="Persist current config to config.toml")
def save_config(request: Request):
    saved = config.try_save_config()
    return utils.get_response(200, {"saved": saved})
