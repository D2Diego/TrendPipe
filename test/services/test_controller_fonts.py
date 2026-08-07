import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.controllers.v1 import fonts as fonts_controller
from app.services import fonts


class TestFontsEndpoint(unittest.TestCase):
    def test_lists_only_supported_font_files_in_stable_order(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ("z.ttf", "a.ttc", "ignore.txt"):
                open(os.path.join(directory, name), "wb").close()
            with patch.object(fonts.utils, "font_dir", return_value=directory):
                response = fonts_controller.list_fonts_endpoint(MagicMock())
        self.assertEqual(response["data"]["fonts"], ["a.ttc", "z.ttf"])

    def test_checks_font_support_without_exposing_a_path_parameter(self):
        body = fonts_controller.FontSupportRequest(font_name="safe.ttf", text="Olá")
        with patch.object(fonts_controller.fonts, "supports_text", return_value=False) as supports:
            response = fonts_controller.check_font_support(MagicMock(), body)
        self.assertEqual(response["data"], {"supported": False})
        supports.assert_called_once_with("safe.ttf", "Olá")


if __name__ == "__main__":
    unittest.main()
