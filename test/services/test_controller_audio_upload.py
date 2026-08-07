import io
import unittest
from unittest.mock import MagicMock, patch

from app.controllers.v1 import audio_upload as audio_upload_controller
from app.models.exception import HttpException


class TestAudioUploadController(unittest.TestCase):
    def test_upload_returns_stored_filename(self):
        fake_file = MagicMock()
        fake_file.filename = "voice.mp3"
        fake_file.file = io.BytesIO(b"fake-bytes")

        with patch.object(
            audio_upload_controller.audio_upload,
            "save_custom_audio_upload",
            return_value="storage/uploaded_audio/abc123.mp3",
        ):
            response = audio_upload_controller.upload_audio_file(
                MagicMock(headers={}), file=fake_file
            )

        self.assertEqual(response["data"]["file"], "storage/uploaded_audio/abc123.mp3")

    def test_upload_rejects_invalid_audio_with_400(self):
        fake_file = MagicMock()
        fake_file.filename = "voice.exe"
        fake_file.file = io.BytesIO(b"not audio")

        with patch.object(
            audio_upload_controller.audio_upload,
            "save_custom_audio_upload",
            side_effect=audio_upload_controller.audio_upload.AudioUploadError("bad type"),
        ):
            with self.assertRaises(HttpException) as ctx:
                audio_upload_controller.upload_audio_file(MagicMock(headers={}), file=fake_file)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_upload_returns_500_when_service_is_unavailable(self):
        fake_file = MagicMock()
        fake_file.filename = "voice.mp3"
        fake_file.file = io.BytesIO(b"fake-bytes")

        with patch.object(
            audio_upload_controller.audio_upload,
            "save_custom_audio_upload",
            side_effect=audio_upload_controller.audio_upload.AudioUploadServiceError("ffmpeg missing"),
        ):
            with self.assertRaises(HttpException) as ctx:
                audio_upload_controller.upload_audio_file(MagicMock(headers={}), file=fake_file)
        self.assertEqual(ctx.exception.status_code, 500)


if __name__ == "__main__":
    unittest.main()
