import unittest
from unittest.mock import MagicMock, patch

from app.controllers.v1 import config as config_controller


class TestConfigReadiness(unittest.TestCase):
    def test_exposes_configuration_presence_without_secret_values(self):
        with patch.object(config_controller.config, "app", {"pexels_api_keys": "secret", "pixabay_api_keys": "", "coverr_api_keys": ["key"]}), patch.object(config_controller.sonilo_service, "is_enabled", return_value=True), patch.object(config_controller.elevenlabs_music_service, "is_enabled", return_value=False):
            response = config_controller.get_generation_readiness(MagicMock())
        self.assertEqual(response["data"], {"pexels": True, "pixabay": False, "coverr": True, "sonilo": True, "elevenlabs": False})
        self.assertNotIn("secret", str(response))


if __name__ == "__main__":
    unittest.main()
