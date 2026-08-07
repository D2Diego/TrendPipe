import base64

from fastapi import Query, Request
from pydantic import BaseModel, Field

from app.config import config
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.services import voice, voice_preview
from app.utils import utils

router = new_router()

_VOICE_LIST_DISPATCH = {
    "azure-tts-v1": lambda: voice.get_all_azure_voices(),
    "azure-tts-v2": lambda: voice.get_all_azure_voices(),
    "siliconflow": lambda: voice.get_siliconflow_voices(),
    "gemini-tts": lambda: voice.get_gemini_voices(),
    "mimo-tts": lambda: voice.get_mimo_voices(),
    "elevenlabs": lambda: voice.get_elevenlabs_voices(config.elevenlabs.get("api_key", "")),
    "chatterbox": lambda: voice.get_chatterbox_voices(),
}


@router.get("/voices", summary="List available voices for a TTS provider")
def list_voices(request: Request, provider: str = Query(..., description="tts_server id")):
    dispatch = _VOICE_LIST_DISPATCH.get(provider)
    if dispatch is None:
        raise HttpException(
            task_id="",
            status_code=400,
            message=f"unknown provider: {provider}",
        )
    voices = dispatch()
    return utils.get_response(200, {"voices": voices})


class VoicePreviewRequest(BaseModel):
    content: str = Field(..., max_length=2000)
    voice_name: str
    voice_rate: float = 1.0
    voice_volume: float = 1.0


@router.post("/voices/preview", summary="Synthesize a short TTS preview clip")
def preview_voice(request: Request, body: VoicePreviewRequest):
    result = voice_preview.synthesize_voice_preview(
        content=body.content,
        voice_name=body.voice_name,
        voice_rate=body.voice_rate,
        voice_volume=body.voice_volume,
    )
    if not result:
        raise HttpException(task_id="", status_code=502, message="voice preview synthesis failed")
    if result.get("busy"):
        raise HttpException(
            task_id="",
            status_code=503,
            message="config is locked by a running task, try again shortly",
        )

    return utils.get_response(
        200,
        {
            "audio_base64": base64.b64encode(result["audio_bytes"]).decode("ascii"),
            "mime_type": result["mime_type"],
            "duration": result.get("duration"),
        },
    )
