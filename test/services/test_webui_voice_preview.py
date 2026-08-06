import ast
import hashlib
import re
import shutil
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.config import config
from app.models.schema import VideoParams
from app.services import task as tm
from app.services import voice
from app.services import webui_task
from app.utils import utils


ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"


def _load_duration_estimator():
    """Only load pure estimation functions to avoid unit testing importing and executing complete Streamlit page."""
    tree = ast.parse(WEBUI_MAIN.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_estimate_voiceover_duration_range"
    )
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {"re": re}
    exec(compile(module, str(WEBUI_MAIN), "exec"), namespace)
    return namespace["_estimate_voiceover_duration_range"]


def _load_provider_signature(test_config):
    """Loading extracts and Provider Fingerprint function, independent validation of cache failure rule."""
    tree = ast.parse(WEBUI_MAIN.read_text(encoding="utf-8"))
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name
        in {
            "_credential_signature",
            "_get_voice_preview_provider_signature",
        }
    ]
    module = ast.Module(body=functions, type_ignores=[])
    namespace = {"hashlib": hashlib, "config": test_config}
    exec(compile(module, str(WEBUI_MAIN), "exec"), namespace)
    return namespace["_get_voice_preview_provider_signature"]


def _button_by_key(app, key):
    return next(
        button
        for button in app.button
        if str(getattr(button, "key", "")).startswith(key)
    )


def test_duration_estimator_is_local_and_respects_voice_rate():
    """Local estimates should cover Chinese and English and reasonably reduce the speed of speech as the user chooses."""
    estimate = _load_duration_estimator()
    script = "Artificial intelligence is changing everyday life. It can help us to collate information and it can be more efficient."

    normal_range = estimate(script, 1.0)
    fast_range = estimate(script, 2.0)

    assert normal_range is not None
    assert fast_range is not None
    assert normal_range[0] < normal_range[1]
    assert fast_range[0] < normal_range[0]
    assert estimate("", 1.0) is None
    assert estimate("AI tools can simplify repetitive work.", 1.0) is not None


def test_provider_signature_changes_when_api_key_changes():
    """Modify Only API Key It is also important that the hearing cache be invalidated and not disguised as a new document to verify success."""
    test_config = SimpleNamespace(
        app={"gemini_api_key": "old-gemini", "mimo_api_key": "old-mimo"},
        azure={"speech_region": "eastasia", "speech_key": "old-azure"},
        siliconflow={"api_key": "old-siliconflow"},
        elevenlabs={"api_key": "old-elevenlabs", "model_id": "eleven_v3"},
        chatterbox={
            "api_key": "old-chatterbox",
            "base_url": "http://127.0.0.1:4123/v1",
            "model_id": "chatterbox",
        },
    )
    provider_signature = _load_provider_signature(test_config)

    old_signature = provider_signature("elevenlabs")
    test_config.elevenlabs["api_key"] = "new-elevenlabs"
    new_signature = provider_signature("elevenlabs")

    assert old_signature != new_signature
    assert "old-elevenlabs" not in str(old_signature)
    assert "new-elevenlabs" not in str(new_signature)


def test_full_voiceover_preview_is_disabled_until_script_exists():
    """The full preview must be activated by the user, and the file cannot be erroneously called by business when it is empty TTS。"""
    test_ui = dict(
        config.ui,
        voice_mode="tts",
        tts_server="azure-tts-v1",
        voice_name="zh-CN-XiaoxiaoNeural-Female",
    )
    with (
        patch.object(config, "ui", test_ui),
        patch.object(config, "save_config"),
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "zh"
        app.run()

    full_preview = _button_by_key(
        app,
        "generate_full_voiceover_preview_button",
    )
    assert full_preview.disabled
    assert any("After completing the video file" in item.value for item in app.caption)


def test_script_shows_estimate_and_enables_full_voiceover_preview():
    """Show free estimates after filling in the case and clearly complete preview may result API Cost."""
    test_ui = dict(
        config.ui,
        voice_mode="tts",
        tts_server="azure-tts-v1",
        voice_name="zh-CN-XiaoxiaoNeural-Female",
    )
    with (
        patch.object(config, "ui", test_ui),
        patch.object(config, "save_config"),
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "zh"
        app.session_state["video_script"] = (
            "Artificial intelligence is changing everyday life. Rational use of tools can help us to work more efficiently."
        )
        app.run()

    full_preview = _button_by_key(
        app,
        "generate_full_voiceover_preview_button",
    )
    assert not full_preview.disabled
    assert any("Local estimate, no call API" in item.value for item in app.caption)
    assert "Potential consumption API Amount" in full_preview.help
    assert [str(item.value) for item in app.exception] == []


def test_full_preview_uses_script_and_reuses_identical_cached_audio():
    """Use the current text for a complete audition, and no re-calls when the same arguments are clicked TTS。"""
    script = "This is a test file to verify the full audio preview cache."
    test_ui = dict(
        config.ui,
        voice_mode="tts",
        tts_server="azure-tts-v1",
        voice_name="zh-CN-XiaoxiaoNeural-Female",
    )

    def fake_tts(**kwargs):
        # File extension though mp3，But true. TTS Possible Return WAV；This smallest file header at the same time
        # Authentication WebUI The player will be identified by content MIME，Not blind letters extension.
        Path(kwargs["voice_file"]).write_bytes(
            b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32
        )
        return object()

    with (
        patch.object(config, "ui", test_ui),
        patch.object(config, "save_config"),
        patch.object(voice, "tts", side_effect=fake_tts) as synthesize,
        patch.object(voice, "get_audio_duration", return_value=12.3),
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "zh"
        app.session_state["video_script"] = script
        app.run()

        _button_by_key(
            app,
            "generate_full_voiceover_preview_button",
        ).click().run()
        _button_by_key(
            app,
            "generate_full_voiceover_preview_button",
        ).click().run()

    synthesize.assert_called_once()
    assert synthesize.call_args.kwargs["text"] == script
    assert len(app.get("audio")) == 1
    assert any("Actual voice length:12.3 sec" in item.value for item in app.caption)
    assert [str(item.value) for item in app.exception] == []


def test_full_preview_reports_when_tts_returns_no_audio():
    """TTS You must give an actionable hint when you return the empty result, so that the button does not click without any feedback."""
    test_ui = dict(
        config.ui,
        voice_mode="tts",
        tts_server="azure-tts-v1",
        voice_name="zh-CN-XiaoxiaoNeural-Female",
    )
    with (
        patch.object(config, "ui", test_ui),
        patch.object(config, "save_config"),
        patch.object(voice, "tts", return_value=None),
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "zh"
        app.session_state["video_script"] = "Validates an empty voice service response."
        app.run()
        _button_by_key(
            app,
            "generate_full_voiceover_preview_button",
        ).click().run()

    assert [item.value for item in app.error] == [
        "The audio placard service does not return the audio. Check the settings and application logs."
    ]
    assert [str(item.value) for item in app.exception] == []


def test_full_preview_returns_immediately_when_runtime_config_is_busy():
    """When a backstage job holds a configuration lock, the audition should be prompted to try again later rather than blocking the page."""
    test_ui = dict(
        config.ui,
        voice_mode="tts",
        tts_server="azure-tts-v1",
        voice_name="zh-CN-XiaoxiaoNeural-Female",
    )
    with (
        patch.object(config, "ui", test_ui),
        patch.object(config, "save_config"),
        patch.object(
            config,
            "try_runtime_config_lock",
            return_value=nullcontext(False),
        ),
        patch.object(voice, "tts") as synthesize,
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "zh"
        app.session_state["video_script"] = "Could not close temporary folder: %s"
        app.run()
        _button_by_key(
            app,
            "generate_full_voiceover_preview_button",
        ).click().run()

    synthesize.assert_not_called()
    warning_messages = [item.value for item in app.warning]
    assert "A video job is currently using a voice ration configuration, please try again later." in warning_messages


def test_full_preview_warns_when_audio_duration_is_unavailable():
    """The audio can play but cannot be decoded for a long time. 0.0 Seconds are shown as real results."""
    test_ui = dict(
        config.ui,
        voice_mode="tts",
        tts_server="azure-tts-v1",
        voice_name="zh-CN-XiaoxiaoNeural-Female",
    )

    def fake_tts(**kwargs):
        Path(kwargs["voice_file"]).write_bytes(
            b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32
        )
        return object()

    with (
        patch.object(config, "ui", test_ui),
        patch.object(config, "save_config"),
        patch.object(voice, "tts", side_effect=fake_tts),
        patch.object(voice, "get_audio_duration", return_value=0),
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "zh"
        app.session_state["video_script"] = "Could not close temporary folder: %s"
        app.run()
        _button_by_key(
            app,
            "generate_full_voiceover_preview_button",
        ).click().run()

    assert len(app.get("audio")) == 1
    warning_messages = [item.value for item in app.warning]
    assert "Check the application log if the test audio has been generated but cannot be read for an accurate period of time." in warning_messages


def test_task_reuses_matching_full_preview_without_calling_tts():
    """When the parameters are fully consistent, the official mission should repeat the audio and subtitle time axis."""
    task_id = "reuse-full-voice-preview"
    task_dir = Path(utils.task_dir(task_id))
    audio_file = task_dir / "audio.mp3"
    audio_file.write_bytes(b"preview audio")
    sub_maker = object()
    script = "The same text is used for the full interview and official assignment."
    params = VideoParams(
        video_subject="preview reuse",
        video_script=script,
        voice_name="zh-CN-XiaoxiaoNeural-Female",
        voice_rate=1.2,
        voice_volume=1.0,
    )
    preview = {
        "audio_file": str(audio_file),
        "duration": 8.2,
        "sub_maker": sub_maker,
        "script": script,
        "voice_name": params.voice_name,
        "voice_rate": params.voice_rate,
        "voice_volume": params.voice_volume,
    }

    try:
        with patch.object(tm.voice, "tts") as synthesize:
            result = tm.generate_audio(
                task_id,
                params,
                script,
                voice_preview=preview,
            )
    finally:
        shutil.rmtree(task_dir, ignore_errors=True)

    assert result == (str(audio_file.resolve()), 9, sub_maker)
    synthesize.assert_not_called()


def test_task_regenerates_audio_when_preview_parameters_changed():
    """You have to back up when the text or placard parameters change TTS，Could not close temporary folder: %s"""
    task_id = "stale-full-voice-preview"
    task_dir = Path(utils.task_dir(task_id))
    audio_file = task_dir / "audio.mp3"
    audio_file.write_bytes(b"stale preview audio")
    script = "Official tasks require new speech speeds to recreate sound."
    params = VideoParams(
        video_subject="stale preview",
        video_script=script,
        voice_name="zh-CN-XiaoxiaoNeural-Female",
        voice_rate=1.5,
        voice_volume=1.0,
    )
    preview = {
        "audio_file": str(audio_file),
        "duration": 8.2,
        "sub_maker": object(),
        "script": script,
        "voice_name": params.voice_name,
        "voice_rate": 1.0,
        "voice_volume": params.voice_volume,
    }
    regenerated_sub_maker = object()

    try:
        with (
            patch.object(
                tm.voice,
                "tts",
                return_value=regenerated_sub_maker,
            ) as synthesize,
            patch.object(tm.voice, "get_audio_duration", return_value=6),
        ):
            result = tm.generate_audio(
                task_id,
                params,
                script,
                voice_preview=preview,
            )
    finally:
        shutil.rmtree(task_dir, ignore_errors=True)

    assert result[1:] == (6, regenerated_sub_maker)
    synthesize.assert_called_once()
    assert synthesize.call_args.kwargs["voice_rate"] == 1.5


def test_non_default_volume_regenerates_audio_without_double_gain():
    """Non-default volume must exit process, avoid TTS Replication of gains with video synthesis phase."""
    task_id = "voice-volume-forwarding"
    task_dir = Path(utils.task_dir(task_id))
    audio_file = task_dir / "audio.mp3"
    audio_file.write_bytes(b"preview with provider-side volume")
    script = "The non-default volume needs to produce a voice by the original process."
    params = VideoParams(
        video_subject="voice volume",
        video_script=script,
        voice_name="zh-CN-XiaoxiaoNeural-Female",
        voice_rate=1.2,
        voice_volume=1.5,
    )
    sub_maker = object()
    preview = {
        "audio_file": str(audio_file),
        "duration": 5.0,
        "sub_maker": object(),
        "script": script,
        "voice_name": params.voice_name,
        "voice_rate": params.voice_rate,
        "voice_volume": params.voice_volume,
    }

    try:
        with (
            patch.object(tm.voice, "tts", return_value=sub_maker) as synthesize,
            patch.object(tm.voice, "get_audio_duration", return_value=5),
        ):
            result = tm.generate_audio(
                task_id,
                params,
                script,
                voice_preview=preview,
            )
    finally:
        shutil.rmtree(task_dir, ignore_errors=True)

    assert result[1:] == (5, sub_maker)
    synthesize.assert_called_once()
    assert "voice_volume" not in synthesize.call_args.kwargs


def test_webui_worker_forwards_voice_preview_to_pipeline():
    """Backstage task packagings cannot be lost with the test cache that was verified at the time of submission."""
    preview = {"audio_file": "audio.mp3", "duration": 5.0}
    with (
        patch.object(webui_task.tm, "start", return_value={"videos": []}) as start,
        patch.object(
            webui_task.config,
            "runtime_config_lock",
            return_value=nullcontext(),
        ),
    ):
        webui_task._run_generation(
            "preview-forwarding",
            VideoParams(video_subject="preview forwarding"),
            capture_logs=False,
            voice_preview=preview,
        )

    assert start.call_args.kwargs["voice_preview"] == preview
