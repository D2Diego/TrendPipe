import os
import stat
import tempfile
import unittest
from unittest.mock import patch

from app.services import research_credentials


class TestCredentials(unittest.TestCase):
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

    def test_presence_reports_true_only_for_set_nonempty_keys(self):
        with open(self._env_path, "w", encoding="utf-8") as env_file:
            env_file.write(
                "# a comment\nOPENROUTER_API_KEY=abc\nGITHUB_TOKEN=\nOTHER=ignored\n"
            )

        presence = research_credentials.credential_presence()

        self.assertTrue(presence["OPENROUTER_API_KEY"])
        self.assertFalse(presence["GITHUB_TOKEN"])
        self.assertFalse(presence["SCRAPECREATORS_API_KEY"])
        self.assertEqual(set(presence), research_credentials.ALLOWED_CREDENTIAL_KEYS)

    def test_presence_with_no_env_file(self):
        presence = research_credentials.credential_presence()

        self.assertTrue(all(value is False for value in presence.values()))
        self.assertEqual(set(presence), research_credentials.ALLOWED_CREDENTIAL_KEYS)

    def test_delete_removes_matching_line_and_keeps_others(self):
        with open(self._env_path, "w", encoding="utf-8") as env_file:
            env_file.write(
                "# a comment\nOTHER_KEY=keep-me\nOPENROUTER_API_KEY=old\n"
            )

        research_credentials.delete_credential("OPENROUTER_API_KEY")

        with open(self._env_path, encoding="utf-8") as env_file:
            lines = env_file.readlines()
        self.assertIn("# a comment\n", lines)
        self.assertIn("OTHER_KEY=keep-me\n", lines)
        self.assertFalse(any(line.startswith("OPENROUTER_API_KEY=") for line in lines))

    def test_delete_is_a_noop_when_key_was_never_set(self):
        with open(self._env_path, "w", encoding="utf-8") as env_file:
            env_file.write("OTHER_KEY=keep-me\n")

        research_credentials.delete_credential("OPENROUTER_API_KEY")

        with open(self._env_path, encoding="utf-8") as env_file:
            content = env_file.read()
        self.assertEqual(content, "OTHER_KEY=keep-me\n")

    def test_delete_rejects_noncredential_key(self):
        with self.assertRaises(ValueError):
            research_credentials.delete_credential("UNRELATED_SETTING")

    def test_read_env_file_returns_every_key_including_noncredential_ones(self):
        with open(self._env_path, "w", encoding="utf-8") as env_file:
            env_file.write(
                "# a comment\n"
                "OPENROUTER_API_KEY=sk-or-abc\n"
                "LAST30DAYS_REASONING_PROVIDER=openrouter\n"
                "\n"
            )

        values = research_credentials.read_env_file()

        self.assertEqual(
            values,
            {
                "OPENROUTER_API_KEY": "sk-or-abc",
                "LAST30DAYS_REASONING_PROVIDER": "openrouter",
            },
        )

    def test_read_env_file_with_no_file(self):
        self.assertEqual(research_credentials.read_env_file(), {})


if __name__ == "__main__":
    unittest.main()
