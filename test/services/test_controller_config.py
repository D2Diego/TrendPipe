import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.controllers.v1 import config as config_controller
from app.models.exception import HttpException


class TestConfigController(unittest.TestCase):
    def test_get_section_returns_snapshot(self):
        with patch.object(
            config_controller.config,
            "snapshot_config_with_pending",
            return_value={"tts_server": "azure-tts-v1"},
        ):
            response = config_controller.get_config_section(
                SimpleNamespace(headers={}), section="ui"
            )
        self.assertEqual(response["data"], {"tts_server": "azure-tts-v1"})

    def test_get_section_rejects_unknown_section(self):
        with self.assertRaises(HttpException) as ctx:
            config_controller.get_config_section(SimpleNamespace(headers={}), section="nope")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_set_key_delegates_to_update_config_nonblocking(self):
        with patch.object(
            config_controller.config, "update_config_nonblocking", return_value=True
        ) as mock_fn:
            response = config_controller.set_config_key(
                SimpleNamespace(headers={}),
                section="ui",
                key="tts_server",
                body=config_controller.SetConfigValueRequest(value="elevenlabs"),
            )
        mock_fn.assert_called_once()
        self.assertEqual(response["data"]["updated"], True)

    def test_delete_key_delegates_to_delete_config_nonblocking(self):
        with patch.object(
            config_controller.config, "delete_config_nonblocking", return_value=True
        ) as mock_fn:
            response = config_controller.delete_config_key(
                SimpleNamespace(headers={}), section="ui", key="some_key"
            )
        mock_fn.assert_called_once()
        self.assertEqual(response["data"]["deleted"], True)

    def test_save_delegates_to_try_save_config(self):
        with patch.object(config_controller.config, "try_save_config", return_value=True):
            response = config_controller.save_config(SimpleNamespace(headers={}))
        self.assertEqual(response["data"]["saved"], True)

    def test_get_section_rejects_credential_bearing_sections(self):
        for section in ("app", "azure", "elevenlabs", "siliconflow", "chatterbox"):
            with self.assertRaises(HttpException) as ctx:
                config_controller.get_config_section(SimpleNamespace(headers={}), section=section)
            self.assertEqual(ctx.exception.status_code, 400, f"section={section} should be rejected")

    def test_set_key_rejects_credential_bearing_sections(self):
        with self.assertRaises(HttpException) as ctx:
            config_controller.set_config_key(
                SimpleNamespace(headers={}),
                section="app",
                key="openai_api_key",
                body=config_controller.SetConfigValueRequest(value="attacker-key"),
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_delete_key_rejects_credential_bearing_sections(self):
        with self.assertRaises(HttpException) as ctx:
            config_controller.delete_config_key(
                SimpleNamespace(headers={}), section="azure", key="speech_key"
            )
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
