from dataclasses import asdict
from urllib.parse import urlparse

from fastapi import Request
from pydantic import BaseModel

from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.models.llm_provider import LLM_PROVIDER_REGISTRY
from app.services import llm
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
