import unittest
from unittest.mock import patch

from app.services import voice_preview


class TestSynthesizeVoicePreview(unittest.TestCase):
    def test_returns_none_when_tts_produces_no_file(self):
        with patch.object(voice_preview.voice, "tts", return_value=None):
            result = voice_preview.synthesize_voice_preview(
                content="hello world",
                voice_name="en-US-JennyNeural",
                voice_rate=1.0,
                voice_volume=1.0,
            )
        self.assertIsNone(result)

    def test_returns_audio_bytes_and_duration_on_success(self):
        def fake_tts(text, voice_name, voice_rate, voice_file, voice_volume=1.0):
            with open(voice_file, "wb") as f:
                f.write(b"\x00\x01fake-audio-bytes")
            return object()  # stand-in sub_maker

        with patch.object(voice_preview.voice, "tts", side_effect=fake_tts), patch.object(
            voice_preview.voice, "get_audio_duration", return_value=2.5
        ):
            result = voice_preview.synthesize_voice_preview(
                content="hello world",
                voice_name="en-US-JennyNeural",
                voice_rate=1.0,
                voice_volume=1.0,
            )

        self.assertIsNotNone(result)
        self.assertEqual(result["audio_bytes"], b"\x00\x01fake-audio-bytes")
        self.assertEqual(result["duration"], 2.5)
        self.assertIn("mime_type", result)

    def test_cleans_up_temp_file_even_on_failure(self):
        written_path = {}

        def fake_tts(text, voice_name, voice_rate, voice_file, voice_volume=1.0):
            written_path["path"] = voice_file
            with open(voice_file, "wb") as f:
                f.write(b"partial")
            raise RuntimeError("provider exploded")

        with patch.object(voice_preview.voice, "tts", side_effect=fake_tts):
            with self.assertRaises(RuntimeError):
                voice_preview.synthesize_voice_preview(
                    content="hello",
                    voice_name="en-US-JennyNeural",
                    voice_rate=1.0,
                    voice_volume=1.0,
                )

        import os

        self.assertFalse(os.path.exists(written_path["path"]))

    def test_returns_busy_when_config_lock_unavailable(self):
        from contextlib import contextmanager

        @contextmanager
        def fake_lock():
            yield False

        with patch.object(
            voice_preview.config, "try_runtime_config_lock", side_effect=fake_lock
        ), patch.object(voice_preview.voice, "tts") as mock_tts:
            result = voice_preview.synthesize_voice_preview(
                content="hello",
                voice_name="en-US-JennyNeural",
                voice_rate=1.0,
                voice_volume=1.0,
            )

        self.assertEqual(result, {"busy": True})
        mock_tts.assert_not_called()


if __name__ == "__main__":
    unittest.main()
