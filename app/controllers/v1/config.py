from fastapi import Path, Request
from pydantic import BaseModel

from app.config import config
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.utils import utils

router = new_router()

# Only "ui" is exposed here — the other RUNTIME_CONFIG_SECTIONS entries
# (app, azure, elevenlabs, siliconflow, chatterbox) hold provider API keys
# and other credentials in plaintext, and this API currently has no auth.
# Do not widen this set without adding real authentication to this router.
_EXPOSED_CONFIG_SECTIONS = {"ui"}


class SetConfigValueRequest(BaseModel):
    value: object


def _resolve_section(section: str):
    if section not in _EXPOSED_CONFIG_SECTIONS:
        raise HttpException(task_id="", status_code=400, message=f"unknown config section: {section}")
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
