import math
import os
from uuid import uuid4

from loguru import logger

from app.config import config
from app.services import voice
from app.utils import utils


def _detect_audio_mime(audio_file: str, audio_bytes: bytes) -> str:
    # Some OpenAI-compatible TTS Services, for example travisvn/chatterbox-tts-api,
    # even if you ask response_format=mp3, may still return WAV content. WebUI test if fixed
    # use audio/mp3, the browser may not be able to play, so here we detect the real format by header.
    header = audio_bytes[:12]
    if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        return "audio/wav"
    if header.startswith(b"ID3") or header[:2] in (
        b"\xff\xfb",
        b"\xff\xf3",
        b"\xff\xf2",
    ):
        return "audio/mp3"
    if header.startswith(b"OggS"):
        return "audio/ogg"
    ext = os.path.splitext(audio_file)[1].lower()
    return {
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
    }.get(ext, "audio/mp3")


def synthesize_voice_preview(
    *,
    content: str,
    voice_name: str,
    voice_rate: float,
    voice_volume: float,
) -> dict | None:
    """Generate a short TTS preview and return it as in-memory bytes.

    Ported from webui/Main.py:_synthesize_voice_preview, minus the
    st.session_state preview-reuse cache (no session concept over HTTP —
    every call re-synthesizes, which is acceptable for a short preview clip).
    """
    temp_dir = utils.storage_dir("temp", create=True)
    audio_file = os.path.join(temp_dir, f"tmp-voice-{str(uuid4())}.mp3")
    logger.info(
        f"generating voice preview: voice={voice_name}, rate={voice_rate}, "
        f"volume={voice_volume}, text_length={len(content)}"
    )
    try:
        with config.try_runtime_config_lock() as lock_acquired:
            if not lock_acquired:
                return {"busy": True}
            sub_maker = voice.tts(
                text=content,
                voice_name=voice_name,
                voice_rate=voice_rate,
                voice_file=audio_file,
                voice_volume=voice_volume,
            )
        if not sub_maker or not os.path.exists(audio_file):
            logger.error("voice preview did not produce an audio file")
            return None

        with open(audio_file, "rb") as file:
            audio_bytes = file.read()
        if not audio_bytes:
            logger.error(f"voice preview audio file is empty: {audio_file}")
            return None

        duration = voice.get_audio_duration(audio_file)
        if (
            not isinstance(duration, (int, float))
            or not math.isfinite(duration)
            or duration <= 0
        ):
            logger.warning(
                f"voice preview duration is unavailable: voice={voice_name}"
            )
            duration = None

        return {
            "audio_bytes": audio_bytes,
            "mime_type": _detect_audio_mime(audio_file, audio_bytes),
            "duration": duration,
        }
    finally:
        try:
            os.remove(audio_file)
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.warning(f"failed to delete voice preview file {audio_file}: {exc}")
