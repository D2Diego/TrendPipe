from dataclasses import asdict
from urllib.parse import urlparse

from fastapi import Request
from pydantic import BaseModel

from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.models.llm_provider import LLM_PROVIDER_REGISTRY
from app.services import elevenlabs_music, llm, sonilo
from app.utils import utils

router = new_router()


class GroqModelsRequest(BaseModel):
    api_key: str
    base_url: str = ""


def _is_allowed_groq_base_url(base_url: str) -> bool:
    """Validate that base_url is a groq.com host to prevent SSRF attacks."""
    if not base_url:
        return True
    host = (urlparse(base_url).hostname or "").lower()
    return host == "api.groq.com" or host.endswith(".groq.com")


@router.get("/providers/llm", summary="List available LLM providers")
def list_llm_providers(request: Request):
    providers = [asdict(provider) for provider in LLM_PROVIDER_REGISTRY]
    return utils.get_response(200, {"providers": providers})


@router.post(
    "/providers/llm/groq/models",
    summary="List available Groq models for the given credentials",
)
def list_groq_models(request: Request, body: GroqModelsRequest):
    if not _is_allowed_groq_base_url(body.base_url):
        raise HttpException(
            task_id="", status_code=400, message="base_url must be a groq.com host"
        )
    models = llm.get_groq_model_ids(body.api_key, body.base_url)
    return utils.get_response(200, {"models": models})


@router.post(
    "/providers/llm/test",
    summary="Test the connection using the currently configured LLM provider",
)
def test_llm_connection(request: Request):
    ok, error, elapsed = llm.test_connection()
    return utils.get_response(200, {"ok": ok, "error": error, "elapsed": elapsed})


@router.post("/providers/bgm/sonilo/test", summary="Test the configured Sonilo account")
def test_sonilo_connection(request: Request):
    try:
        sonilo.test_connection()
        result = {"ok": True, "error": ""}
    except sonilo.SoniloError as exc:
        result = {"ok": False, "error": str(exc)}
    return utils.get_response(200, result)


@router.post("/providers/bgm/elevenlabs/test", summary="Test the configured ElevenLabs Music account")
def test_elevenlabs_music_connection(request: Request):
    try:
        elevenlabs_music.test_connection()
        result = {"ok": True, "error": "", "paid_plan_required": False}
    except elevenlabs_music.ElevenLabsPaidPlanRequiredError as exc:
        result = {"ok": False, "error": str(exc), "paid_plan_required": True}
    except elevenlabs_music.ElevenLabsMusicError as exc:
        result = {"ok": False, "error": str(exc), "paid_plan_required": False}
    return utils.get_response(200, result)
