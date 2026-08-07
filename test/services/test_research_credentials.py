import os
import stat
import tempfile
import unittest
from unittest.mock import patch

from app.services import research_credentials


class TestWriteCredentials(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._env_path = os.path.join(self._tmpdir.name, ".env")
        self._patcher = patch.object(
            research_credentials, "ENV_PATH", self._env_path
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_creates_owner_only_file_with_given_keys(self):
        research_credentials.write_credentials({"OPENROUTER_API_KEY": "abc"})

        with open(self._env_path, encoding="utf-8") as env_file:
            content = env_file.read()

        self.assertIn("OPENROUTER_API_KEY=abc", content)
        self.assertEqual(stat.S_IMODE(os.stat(self._env_path).st_mode), 0o600)

    def test_preserves_unrelated_lines_and_overwrites_existing_key(self):
        with open(self._env_path, "w", encoding="utf-8") as env_file:
            env_file.write(
                "# a comment\nOTHER_KEY=keep-me\nOPENROUTER_API_KEY=old\n"
            )

        research_credentials.write_credentials({"OPENROUTER_API_KEY": "new"})

        with open(self._env_path, encoding="utf-8") as env_file:
            lines = env_file.readlines()
        self.assertIn("# a comment\n", lines)
        self.assertIn("OTHER_KEY=keep-me\n", lines)
        self.assertEqual(
            [line for line in lines if line.startswith("OPENROUTER_API_KEY=")],
            ["OPENROUTER_API_KEY=new\n"],
        )

    def test_rejects_values_with_newlines(self):
        with self.assertRaises(ValueError):
            research_credentials.write_credentials(
                {"OPENROUTER_API_KEY": "abc\nINJECTED=value"}
            )

    def test_rejects_noncredential_environment_keys(self):
        with self.assertRaises(ValueError):
            research_credentials.write_credentials({"UNRELATED_SETTING": "value"})


if __name__ == "__main__":
    unittest.main()
