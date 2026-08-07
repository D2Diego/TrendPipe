import os
import subprocess
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from loguru import logger

from app.utils import utils

MAX_AUDIO_UPLOAD_BYTES = 30 * 1024 * 1024
SUPPORTED_AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")

# Mirrors app/services/bgm.py's sanitize_upload_filename validation rules
# (control characters, length, Windows-invalid characters, Windows-reserved
# device names) — duplicated rather than imported, per this file's own
# no-cross-module-private-coupling rule (see Step 1).
_WINDOWS_INVALID_FILENAME_CHARS = frozenset('<>:"|?*')
_WINDOWS_RESERVED_FILENAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)


class AudioUploadError(ValueError):
    """The uploaded file does not meet the format, size, or content requirements."""


class AudioUploadServiceError(RuntimeError):
    """Infrastructure failure (ffmpeg unavailable, timeout) — not a user input problem."""


def uploaded_audio_dir(create: bool = True) -> str:
    """Persistent directory for user-uploaded custom voiceover files."""
    return utils.storage_dir("uploaded_audio", create=create)


def sanitize_upload_filename(filename: str) -> str:
    safe_name = (filename or "").replace("\\", "/").split("/")[-1].strip()
    if (
        not safe_name
        or safe_name in {".", ".."}
        or len(safe_name) > 255
        or any(ord(character) < 32 for character in safe_name)
        or any(character in _WINDOWS_INVALID_FILENAME_CHARS for character in safe_name)
    ):
        raise AudioUploadError("invalid audio filename")

    windows_basename = safe_name.split(".", 1)[0].rstrip(" .").upper()
    if windows_basename in _WINDOWS_RESERVED_FILENAMES:
        raise AudioUploadError("invalid audio filename")

    if Path(safe_name).suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(ext.removeprefix(".").upper() for ext in SUPPORTED_AUDIO_EXTENSIONS)
        raise AudioUploadError(f"unsupported audio format; supported formats: {supported}")
    return safe_name


def _validate_audio(file_path: str, timeout_seconds: int = 30) -> None:
    """Confirm the file decodes as a real audio stream via ffmpeg (same technique as bgm.py)."""
    try:
        decoded = subprocess.run(
            [
                utils.get_ffmpeg_binary(),
                "-nostdin",
                "-v",
                "error",
                "-xerror",
                "-i",
                file_path,
                "-map",
                "0:a:0",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AudioUploadServiceError("audio validation is unavailable") from exc
    if decoded.returncode != 0:
        raise AudioUploadError("uploaded file is not a valid decodable audio stream")


def save_custom_audio_upload(filename: str, source: BinaryIO) -> str:
    """Stream-validate and persist an uploaded custom voiceover file.

    Mirrors app/services/bgm.py:save_bgm_upload's stage-then-atomic-rename
    pattern, but stores into storage/uploaded_audio/ with no task_id
    dependency (POST /api/v1/videos always server-generates its own task_id,
    so the upload can't be pre-scoped to a task the way Streamlit does it).
    """
    safe_name = sanitize_upload_filename(filename)
    target_dir = uploaded_audio_dir(create=True)
    temp_path = os.path.join(target_dir, f".upload-{uuid4().hex}.tmp")
    total_bytes = 0
    try:
        with open(temp_path, "wb") as temp_file:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_AUDIO_UPLOAD_BYTES:
                    raise AudioUploadError(
                        f"file exceeds the {MAX_AUDIO_UPLOAD_BYTES // (1024 * 1024)}MB limit"
                    )
                temp_file.write(chunk)

        _validate_audio(temp_path)

        stored_name = f"{uuid4().hex}{os.path.splitext(safe_name)[1]}"
        target_path = os.path.join(target_dir, stored_name)
        os.replace(temp_path, target_path)
        temp_path = ""
        logger.info(
            f"custom audio uploaded: original_name={safe_name}, "
            f"stored_name={stored_name}, size={total_bytes} bytes"
        )
        return os.path.join("storage", "uploaded_audio", stored_name)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as exc:
                logger.warning(f"failed to remove staged audio upload: {exc}")
