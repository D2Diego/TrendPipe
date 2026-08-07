import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.asgi import app


class TestNewApiSmoke(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_llm_providers_route_is_registered(self):
        response = self.client.get("/api/v1/providers/llm")
        self.assertEqual(response.status_code, 200)
        self.assertIn("providers", response.json()["data"])

    def test_voices_route_rejects_unknown_provider_with_400(self):
        response = self.client.get("/api/v1/voices", params={"provider": "bogus"})
        self.assertEqual(response.status_code, 400)

    def test_task_logs_route_returns_404_for_unknown_task(self):
        response = self.client.get("/api/v1/tasks/does-not-exist/logs")
        self.assertEqual(response.status_code, 404)

    def test_cache_stats_route_is_registered(self):
        response = self.client.get("/api/v1/cache/video/stats")
        self.assertEqual(response.status_code, 200)
        self.assertIn("file_count", response.json()["data"])

    def test_config_route_rejects_unknown_section_with_400(self):
        response = self.client.get("/api/v1/config/not-a-real-section")
        self.assertEqual(response.status_code, 400)

    def test_config_route_allows_ui_section(self):
        response = self.client.get("/api/v1/config/ui")
        self.assertEqual(response.status_code, 200)

    def test_config_route_rejects_credential_bearing_section_with_400(self):
        # Task 8's security fix: only "ui" is exposed; app/azure/elevenlabs/
        # siliconflow/chatterbox hold plaintext credentials and must be
        # rejected even though they're valid keys in RUNTIME_CONFIG_SECTIONS.
        response = self.client.get("/api/v1/config/app")
        self.assertEqual(response.status_code, 400)

    def test_voice_preview_route_rejects_oversized_content_with_400(self):
        # Task 7's fix: content is capped at max_length=2000 via Pydantic.
        # This app normalizes all Pydantic/FastAPI validation errors to 400
        # via a global RequestValidationError handler in app/asgi.py, not
        # FastAPI's generic 422 default — so 400 is correct here too.
        response = self.client.post(
            "/api/v1/voices/preview",
            json={
                "content": "x" * 2001,
                "voice_name": "en-US-JennyNeural",
                "voice_rate": 1.0,
                "voice_volume": 1.0,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_groq_models_route_rejects_non_groq_base_url_with_400(self):
        # Task 4's SSRF fix: base_url must be a groq.com host.
        response = self.client.post(
            "/api/v1/providers/llm/groq/models",
            json={"api_key": "k", "base_url": "http://169.254.169.254/"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
