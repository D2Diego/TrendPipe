from fastapi import Request, UploadFile
from fastapi.params import File
from loguru import logger

from app.controllers import base
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.services import audio_upload
from app.utils import utils

router = new_router()


@router.post(
    "/audio_upload",
    summary="Upload a custom voiceover audio file",
    description=(
        "Validate an MP3, WAV, M4A, AAC, FLAC, or OGG file up to 30 MB and "
        "store it under an immutable UUID filename in storage/uploaded_audio. "
        "The returned filename is a relative path suitable for "
        "VideoParams.custom_audio_file in a subsequent POST /api/v1/videos call."
    ),
)
def upload_audio_file(request: Request, file: UploadFile = File(...)):
    request_id = base.get_task_id(request)
    try:
        stored_path = audio_upload.save_custom_audio_upload(file.filename, file.file)
    except audio_upload.AudioUploadError as exc:
        logger.warning(f"custom audio upload rejected: request_id={request_id}, error={exc}")
        raise HttpException(task_id=request_id, status_code=400, message=f"{request_id}: {exc}")
    except audio_upload.AudioUploadServiceError as exc:
        logger.error(f"custom audio upload failed: request_id={request_id}, error={exc}")
        raise HttpException(
            task_id=request_id,
            status_code=500,
            message=f"{request_id}: audio validation is unavailable",
        )

    return utils.get_response(200, {"file": stored_path})
