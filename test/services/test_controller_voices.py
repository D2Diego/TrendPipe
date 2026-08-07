import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.controllers.v1 import voices as voices_controller
from app.models.exception import HttpException


class TestVoicesController(unittest.TestCase):
    def test_list_voices_dispatches_azure_by_default(self):
        with patch.object(
            voices_controller.voice, "get_all_azure_voices", return_value=["v1", "v2"]
        ) as mock_fn:
            response = voices_controller.list_voices(SimpleNamespace(headers={}), provider="azure-tts-v1")

        mock_fn.assert_called_once()
        self.assertEqual(response["data"]["voices"], ["v1", "v2"])

    def test_list_voices_dispatches_elevenlabs_with_configured_api_key(self):
        with patch.object(
            voices_controller.config.elevenlabs, "get", return_value="secret-key"
        ), patch.object(
            voices_controller.voice, "get_elevenlabs_voices", return_value=["ev1"]
        ) as mock_fn:
            response = voices_controller.list_voices(SimpleNamespace(headers={}), provider="elevenlabs")

        mock_fn.assert_called_once_with("secret-key")
        self.assertEqual(response["data"]["voices"], ["ev1"])

    def test_list_voices_rejects_unknown_provider(self):
        with self.assertRaises(HttpException) as ctx:
            voices_controller.list_voices(SimpleNamespace(headers={}), provider="not-a-provider")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_all_dispatch_entries_are_patchable_at_call_time(self):
        provider_to_service_fn = {
            "azure-tts-v1": "get_all_azure_voices",
            "azure-tts-v2": "get_all_azure_voices",
            "siliconflow": "get_siliconflow_voices",
            "gemini-tts": "get_gemini_voices",
            "mimo-tts": "get_mimo_voices",
            "chatterbox": "get_chatterbox_voices",
        }
        for provider, fn_name in provider_to_service_fn.items():
            with patch.object(voices_controller.voice, fn_name, return_value=["mocked"]):
                response = voices_controller.list_voices(SimpleNamespace(headers={}), provider=provider)
            self.assertEqual(
                response["data"]["voices"], ["mocked"], f"provider={provider} did not use the patched function"
            )


import base64


class TestVoicePreviewEndpoint(unittest.TestCase):
    def test_preview_returns_base64_audio_and_duration(self):
        fake_result = {
            "audio_bytes": b"abc123",
            "mime_type": "audio/mpeg",
            "duration": 1.5,
        }
        with patch.object(
            voices_controller.voice_preview, "synthesize_voice_preview", return_value=fake_result
        ):
            response = voices_controller.preview_voice(
                SimpleNamespace(headers={}),
                body=voices_controller.VoicePreviewRequest(
                    content="hello",
                    voice_name="en-US-JennyNeural",
                    voice_rate=1.0,
                    voice_volume=1.0,
                ),
            )

        self.assertEqual(response["status"], 200)
        self.assertEqual(
            base64.b64decode(response["data"]["audio_base64"]), b"abc123"
        )
        self.assertEqual(response["data"]["mime_type"], "audio/mpeg")
        self.assertEqual(response["data"]["duration"], 1.5)

    def test_preview_returns_502_when_synthesis_fails(self):
        with patch.object(
            voices_controller.voice_preview, "synthesize_voice_preview", return_value=None
        ):
            with self.assertRaises(voices_controller.HttpException) as ctx:
                voices_controller.preview_voice(
                    SimpleNamespace(headers={}),
                    body=voices_controller.VoicePreviewRequest(
                        content="hello",
                        voice_name="en-US-JennyNeural",
                        voice_rate=1.0,
                        voice_volume=1.0,
                    ),
                )
        self.assertEqual(ctx.exception.status_code, 502)

    def test_preview_returns_503_when_config_lock_is_busy(self):
        # synthesize_voice_preview returns {"busy": True} (no "audio_bytes" key)
        # when config.try_runtime_config_lock() couldn't acquire — e.g. a video
        # generation task currently holds it. This must be checked BEFORE
        # indexing into "audio_bytes", or it's an unhandled KeyError (bare 500)
        # instead of a clean response.
        with patch.object(
            voices_controller.voice_preview,
            "synthesize_voice_preview",
            return_value={"busy": True},
        ):
            with self.assertRaises(voices_controller.HttpException) as ctx:
                voices_controller.preview_voice(
                    SimpleNamespace(headers={}),
                    body=voices_controller.VoicePreviewRequest(
                        content="hello",
                        voice_name="en-US-JennyNeural",
                        voice_rate=1.0,
                        voice_volume=1.0,
                    ),
                )
        self.assertEqual(ctx.exception.status_code, 503)

    def test_preview_request_rejects_content_over_max_length(self):
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            voices_controller.VoicePreviewRequest(
                content="x" * 2001,
                voice_name="en-US-JennyNeural",
                voice_rate=1.0,
                voice_volume=1.0,
            )


if __name__ == "__main__":
    unittest.main()
