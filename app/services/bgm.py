import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from loguru import logger

from app.utils import file_security, utils


# Background music is usually only a few MB. Enforce a service-side limit so
# oversized API uploads cannot consume disk and disrupt video tasks.
MAX_BGM_UPLOAD_BYTES = 30 * 1024 * 1024
_COPY_CHUNK_BYTES = 1024 * 1024
_INTERNAL_UPLOAD_PREFIX = ".bgm-upload-"
_WINDOWS_INVALID_FILENAME_CHARS = frozenset('<>:"|?*')
_WINDOWS_RESERVED_FILENAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)
# MoviePy Final pass. FFmpeg Decoding background music, so no artificial restriction is required MP3. It's only open here.
# Mainstream and semantic audio extension to avoid the use of MP4 When video containers are erroneously uploaded as background music.
# It's the same as the same. WebUI A single data source for upload controls does not appear inconsistent with subsequent additions or deletions.
SUPPORTED_BGM_EXTENSIONS = (
    ".mp3",
    ".m4a",
    ".aac",
    ".wav",
    ".flac",
    ".ogg",
    ".opus",
    ".wma",
)


class BgmUploadError(ValueError):
    """indicates that the upload file does not meet the security or format requirements of the background music."""


class BgmServiceError(RuntimeError):
    """Organisation FFmpeg Or the file system is not service-level to perform malfunctions."""


def should_use_bgm(bgm_type: str | None, bgm_volume: float | None) -> bool:
    """
    A uniform determination is made as to whether any background music is required for the current mission.

    The rule has nothing to do with specific sources: there is no chosen source, the volume is not valid or the volume is not greater 0 Time, random,
    Custom,Sonilo And future new providers must skip document resolution, external generation and final mix.
    General BGM The service avoids replicating one set for each additional provider 0 Volume judgement.
    """
    if not str(bgm_type or "").strip():
        return False
    try:
        normalized_volume = float(bgm_volume or 0)
    except (TypeError, ValueError):
        return False
    return math.isfinite(normalized_volume) and normalized_volume > 0


def uploaded_bgm_dir(create: bool = True) -> str:
    """
    Returns a persistent directory of user background music.

    The built-in song is a code resource. Keep it on. resource/songs; User uploads content to run-time data.
    It has to be. Docker Mounted storage Down, the container will be rebuilt before it's preserved. Git Workspace.
    """
    return utils.storage_dir("bgm", create=create)


def _remove_staged_file(file_path: str) -> None:
    """Every effort is made to clean up the uploading of temporary files and not to cover the original anomalies being processed by the caller."""
    if not file_path or not os.path.exists(file_path):
        return
    try:
        os.remove(file_path)
    except OSError as exc:
        # Temporary files are reserved prefixed, not entered BGM list;cleaning failure should not render "audio invalid"
        # When the original anomaly is covered with more precision, it must leave a path and a system error for deployment.
        logger.warning(
            f"failed to remove staged background music: path={file_path}, "
            f"error={str(exc)}"
        )


def sanitize_upload_filename(filename: str) -> str:
    """Extracts audio file names that can be displayed across the platform and rejects illegal names and unsupported extensions."""
    safe_name = (filename or "").replace("\\", "/").split("/")[-1].strip()
    if (
        not safe_name
        or safe_name in {".", ".."}
        or len(safe_name) > 255
        or any(ord(character) < 32 for character in safe_name)
        or any(character in _WINDOWS_INVALID_FILENAME_CHARS for character in safe_name)
        or safe_name.lower().startswith(_INTERNAL_UPLOAD_PREFIX)
    ):
        raise BgmUploadError("invalid background music filename")

    # Windows The first section before the extension is identified as a device, for example. CON.mp3, LPT1.wav Both
    # Could not close temporary folder: %s Even if the service end up using UUID, You could have rejected such names in advance.
    # Promise. API Inputs are consistent on different platforms.
    windows_basename = safe_name.split(".", 1)[0].rstrip(" .").upper()
    if windows_basename in _WINDOWS_RESERVED_FILENAMES:
        raise BgmUploadError("invalid background music filename")
    if Path(safe_name).suffix.lower() not in SUPPORTED_BGM_EXTENSIONS:
        supported_formats = ", ".join(
            extension.removeprefix(".").upper()
            for extension in SUPPORTED_BGM_EXTENSIONS
        )
        raise BgmUploadError(
            f"unsupported background music format; supported formats: {supported_formats}"
        )
    return safe_name


def _validate_audio(file_path: str, timeout_seconds: int = 30) -> None:
    """
    Use current project configuration only FFmpeg The authentication file contains a fully decoded audio stream.

    Project permission imageio-ffmpeg Offer port FFmpeg, This installation does not guarantee simultaneous presence
    FFprobe, Therefore, an independent binary dependency cannot be added.`-map 0:a:0` It'll fail without audio stream.
    `-xerror` It raises the decoding error to a failure; complete decoding can also intercept encrypted files or random data by accident
    The error of the audio frame. The file may contain additional streams such as the album cover, but only verify the first audio stream.
    """
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
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise BgmServiceError("FFmpeg background music validation timed out") from exc
    except OSError as exc:
        raise BgmServiceError("failed to run FFmpeg for background music validation") from exc
    if decoded.returncode != 0:
        raise BgmUploadError("uploaded file must contain a decodable audio stream")


def validate_audio_file(file_path: str, timeout_seconds: int = 120) -> None:
    """
    Verify audio files on disk from item FFmpeg Full decode.

    It's usually only for uploading. 30 sec;Sonilo The longest pair of codas ever produced. 6 Minutes, therefore, available externally
    Re-entry can be adjusted for overtime. Services depend only on FFmpeg, No additional system installation required FFprobe.
    """
    if not os.path.isfile(file_path) or os.path.getsize(file_path) <= 0:
        raise BgmUploadError("background music file is empty or missing")
    _validate_audio(file_path, timeout_seconds=timeout_seconds)


def _stage_bgm_upload(filename: str, source: BinaryIO) -> tuple[str, str, int]:
    """
    Uploads the upload to the same directory temporary file and returns the security file name, temporary path and bytes.

    WebUI The uploading pre-screening and eventual permanence must be read with identical segments, size limits and files First Name
    rule, otherwise there may be a split state in which the interface displays the availability, the click generation and the service rejects it.
    Temporary files are deleted or replaced by the caller after completion of audio detection.
    """
    safe_name = sanitize_upload_filename(filename)
    try:
        target_dir = uploaded_bgm_dir(create=True)
    except OSError as exc:
        raise BgmServiceError("failed to prepare background music storage") from exc
    temp_path = ""
    total_bytes = 0

    try:
        try:
            source.seek(0)
        except (AttributeError, OSError) as exc:
            raise BgmUploadError("background music upload is not seekable") from exc

        # Keep original extension convenient FFmpeg For uncontainable heads. AAC Waiting for the correct format
        # demuxer; Provisional documents remain in the target directory to ensure finality os.replace It's atom operation.
        descriptor, temp_path = tempfile.mkstemp(
            prefix=_INTERNAL_UPLOAD_PREFIX,
            suffix=Path(safe_name).suffix.lower(),
            dir=target_dir,
        )
        with os.fdopen(descriptor, "wb") as output:
            while True:
                chunk = source.read(_COPY_CHUNK_BYTES)
                if not chunk:
                    break
                if not isinstance(chunk, (bytes, bytearray, memoryview)):
                    raise BgmUploadError("background music upload must be binary")
                total_bytes += len(chunk)
                if total_bytes > MAX_BGM_UPLOAD_BYTES:
                    raise BgmUploadError("background music file exceeds the 30 MB limit")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())

        if total_bytes == 0:
            raise BgmUploadError("background music file is empty")
        return safe_name, temp_path, total_bytes
    except Exception as exc:
        _remove_staged_file(temp_path)
        if isinstance(exc, BgmUploadError):
            raise
        if isinstance(exc, OSError):
            raise BgmServiceError("failed to stage background music upload") from exc
        raise
    finally:
        # Restore reusable file-like inputs so validation does not leave later
        # reads at end-of-file.
        try:
            source.seek(0)
        except (AttributeError, OSError):
            pass


def validate_bgm_upload(filename: str, source: BinaryIO) -> str:
    """Full verification of uploaded audio but not persistent for use WebUI Pre-check before displaying " ready " ."""
    safe_name, temp_path, total_bytes = _stage_bgm_upload(filename, source)
    try:
        _validate_audio(temp_path)
        logger.debug(
            f"background music upload validated: name={safe_name}, "
            f"size={total_bytes} bytes"
        )
        return safe_name
    finally:
        _remove_staged_file(temp_path)


def save_bgm_upload(filename: str, source: BinaryIO) -> str:
    """
    Saves the user background music in blocks, limits and atoms.

    Accept binary file-like inputs such as FastAPI UploadFile. Write a temporary
    file, verify it, and install it atomically with os.replace.
    Half the audio files left behind by uploading or process interruptions will also allow the same name to be uploaded differently. UUID Store key,
    Queued or running tasks therefore always refer to the original unchangeable document.
    """
    safe_name, temp_path, total_bytes = _stage_bgm_upload(filename, source)
    stored_name = f"{uuid4().hex}{Path(safe_name).suffix.lower()}"
    target_path = os.path.join(os.path.dirname(temp_path), stored_name)

    try:
        _validate_audio(temp_path)
        try:
            os.replace(temp_path, target_path)
        except OSError as exc:
            raise BgmServiceError("failed to persist background music upload") from exc
        temp_path = ""
        logger.info(
            f"background music uploaded: original_name={safe_name}, "
            f"stored_name={stored_name}, size={total_bytes} bytes"
        )
        return stored_name
    finally:
        _remove_staged_file(temp_path)


def list_bgm_files() -> list[str]:
    """Lists the available background music that users upload and include."""
    files_by_name: dict[str, str] = {}
    for directory in (utils.song_dir(), uploaded_bgm_dir(create=True)):
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory), key=str.lower):
            # The upload precheck and final save create the same directory file briefly. The temporary documents are legal.
            # Audio extension, but not verified, not random BGM list.
            if name.startswith(_INTERNAL_UPLOAD_PREFIX):
                continue
            if Path(name).suffix.lower() not in SUPPORTED_BGM_EXTENSIONS:
                continue
            file_path = os.path.join(directory, name)
            try:
                # The results of the count also require a true path check. Otherwise the assailant can be placed in the permitted directory.
                # Acoustic links to external files, borrowed randomly BGM Pass the path. MoviePy.
                resolved_path = file_security.resolve_path_within_directory(
                    directory, file_path
                )
            except ValueError as exc:
                logger.warning(
                    f"skip unsafe background music file: name={name}, error={str(exc)}"
                )
                continue
            files_by_name[name] = resolved_path
    return [files_by_name[name] for name in sorted(files_by_name, key=str.lower)]


def resolve_bgm_file(unsafe_path: str) -> str:
    """
    Parsing in user upload directory and built-in song directory BGM, And reject the path beyond the two white lists.

    File name should be given priority in the user directory while retaining `output000.mp3`, Absolute white list path and
    `./resource/songs/output000.mp3` Wait for old usage. Use of new upload files UUID, Normal
    There is no renaming with a built-in song or history.
    """
    if (
        not unsafe_path
        or Path(unsafe_path).suffix.lower() not in SUPPORTED_BGM_EXTENSIONS
    ):
        raise ValueError("unsupported background music path")

    candidates = [unsafe_path]
    if not os.path.isabs(unsafe_path):
        candidates.append(os.path.join(utils.root_dir(), unsafe_path))

    last_error = ValueError("background music file does not exist")
    for directory in (uploaded_bgm_dir(create=True), utils.song_dir()):
        for candidate in candidates:
            try:
                return file_security.resolve_path_within_directory(directory, candidate)
            except ValueError as exc:
                last_error = exc
    raise ValueError(str(last_error)) from last_error
