import io
import os
import unittest
from unittest.mock import patch

from app.services import audio_upload


class TestSaveCustomAudioUpload(unittest.TestCase):
    def setUp(self):
        self.patcher = patch.object(
            audio_upload.utils, "storage_dir", side_effect=self._fake_storage_dir
        )
        self.patcher.start()
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.patcher.stop()
        self._tmp.cleanup()

    def _fake_storage_dir(self, *parts, create=True):
        path = os.path.join(self._tmp.name, *parts)
        if create:
            os.makedirs(path, exist_ok=True)
        return path

    def test_rejects_unsupported_extension(self):
        with self.assertRaises(audio_upload.AudioUploadError):
            audio_upload.save_custom_audio_upload("voice.exe", io.BytesIO(b"not audio"))

    def test_rejects_oversized_upload(self):
        big = io.BytesIO(b"0" * (audio_upload.MAX_AUDIO_UPLOAD_BYTES + 1))
        with self.assertRaises(audio_upload.AudioUploadError):
            audio_upload.save_custom_audio_upload("voice.mp3", big)

    def test_rejects_invalid_audio_content(self):
        with patch.object(audio_upload, "_validate_audio", side_effect=audio_upload.AudioUploadError("bad audio")):
            with self.assertRaises(audio_upload.AudioUploadError):
                audio_upload.save_custom_audio_upload("voice.mp3", io.BytesIO(b"fake-mp3-bytes"))

    def test_saves_valid_upload_and_returns_uuid_filename(self):
        with patch.object(audio_upload, "_validate_audio", return_value=None):
            stored_path = audio_upload.save_custom_audio_upload("my voice.mp3", io.BytesIO(b"fake-mp3-bytes"))

        self.assertTrue(stored_path.endswith(".mp3"))
        self.assertNotIn("my voice", stored_path)  # original name not leaked into stored path
        self.assertTrue(stored_path.startswith(os.path.join("storage", "uploaded_audio")))
        target_dir = audio_upload.uploaded_audio_dir(create=False)
        stored_filename = os.path.basename(stored_path)
        self.assertTrue(os.path.exists(os.path.join(target_dir, stored_filename)))

    def test_returned_path_resolves_via_resolve_custom_audio_file(self):
        # This test exercises the *real* app.utils.utils.storage_dir/task_dir
        # (not the class-level bare-directory fake), because
        # resolve_custom_audio_file's fallback branch joins utils.root_dir()
        # directly with the returned relative path and only the real
        # storage_dir prepends "storage/" the way the returned path expects.
        from app.services import task as task_service

        self.patcher.stop()
        try:
            with patch.object(audio_upload.utils, "root_dir", return_value=self._tmp.name):
                with patch.object(audio_upload, "_validate_audio", return_value=None):
                    stored_path = audio_upload.save_custom_audio_upload(
                        "voice.mp3", io.BytesIO(b"fake-mp3-bytes")
                    )

                resolved = task_service.resolve_custom_audio_file("some-task-id", stored_path)
        finally:
            self.patcher.start()

        self.assertTrue(os.path.exists(resolved))

    def test_raises_service_error_when_ffmpeg_is_unavailable(self):
        with patch.object(
            audio_upload,
            "_validate_audio",
            side_effect=audio_upload.AudioUploadServiceError("ffmpeg missing"),
        ):
            with self.assertRaises(audio_upload.AudioUploadServiceError):
                audio_upload.save_custom_audio_upload("voice.mp3", io.BytesIO(b"fake-mp3-bytes"))


if __name__ == "__main__":
    unittest.main()
