import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.controllers.v1 import providers as providers_controller


class TestProvidersController(unittest.TestCase):
    def test_list_llm_providers_returns_registry_entries(self):
        response = providers_controller.list_llm_providers(SimpleNamespace(headers={}))
        self.assertEqual(response["status"], 200)
        provider_ids = {p["provider_id"] for p in response["data"]["providers"]}
        self.assertIn("moonshot", provider_ids)
        self.assertIn("openai", provider_ids)

    def test_groq_models_endpoint_delegates_to_service(self):
        with patch.object(
            providers_controller.llm, "get_groq_model_ids", return_value=["llama3-70b"]
        ) as mock_fn:
            response = providers_controller.list_groq_models(
                SimpleNamespace(headers={}),
                body=providers_controller.GroqModelsRequest(
                    api_key="k", base_url="https://api.groq.com/openai/v1"
                ),
            )

        mock_fn.assert_called_once_with("k", "https://api.groq.com/openai/v1")
        self.assertEqual(response["data"]["models"], ["llama3-70b"])

    def test_groq_models_rejects_non_groq_base_url(self):
        from app.models.exception import HttpException

        with self.assertRaises(HttpException) as ctx:
            providers_controller.list_groq_models(
                SimpleNamespace(headers={}),
                body=providers_controller.GroqModelsRequest(
                    api_key="k", base_url="http://169.254.169.254/latest/meta-data/"
                ),
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_groq_models_rejects_host_spoofing_via_path(self):
        from app.models.exception import HttpException

        with self.assertRaises(HttpException) as ctx:
            providers_controller.list_groq_models(
                SimpleNamespace(headers={}),
                body=providers_controller.GroqModelsRequest(
                    api_key="k", base_url="http://evil.com/api.groq.com"
                ),
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_groq_models_allows_empty_base_url(self):
        with patch.object(
            providers_controller.llm, "get_groq_model_ids", return_value=["llama3-70b"]
        ):
            response = providers_controller.list_groq_models(
                SimpleNamespace(headers={}),
                body=providers_controller.GroqModelsRequest(api_key="k", base_url=""),
            )
        self.assertEqual(response["data"]["models"], ["llama3-70b"])


if __name__ == "__main__":
    unittest.main()
