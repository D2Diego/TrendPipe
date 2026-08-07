import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.controllers.v1 import version
from app.services.version_checker import UpdateCheckSnapshot


class TestVersionController(unittest.TestCase):
    def test_returns_current_version_and_nonblocking_update_snapshot(self):
        snapshot = UpdateCheckSnapshot(complete=True, available_version="9.9.9")
        with patch.object(version.version_checker, "poll_available_update", return_value=snapshot):
            response = version.get_version_status(SimpleNamespace(headers={}))

        self.assertEqual(response["data"]["current_version"], str(version.config.project_version))
        self.assertEqual(response["data"]["available_version"], "9.9.9")
        self.assertTrue(response["data"]["complete"])
        self.assertEqual(response["data"]["release_url"], version.version_checker.LATEST_RELEASE_PAGE_URL)
