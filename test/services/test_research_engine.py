import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from app.services import research_engine


class TestNormalizeReport(unittest.TestCase):
    def test_wraps_single_topic_payload_using_research_topic_as_entity(self):
        payload = {"topic": "cats", "clusters": []}

        normalized = research_engine.normalize_report(payload, "cats")

        self.assertEqual(
            normalized, {"entities": [{"entity": "cats", "report": payload}]}
        )

    def test_normalizes_comparison_reports(self):
        payload = {
            "comparison": True,
            "entities": ["a", "b"],
            "reports": [
                {"entity": "a", "report": {"clusters": []}},
                {"entity": "b", "report": {"clusters": []}},
            ],
        }

        normalized = research_engine.normalize_report(payload, "a vs b")

        self.assertEqual(normalized, {"entities": payload["reports"]})


class TestRunDiagnose(unittest.TestCase):
    def test_parses_diagnose_json_from_stdout(self):
        fake = MagicMock(
            returncode=0,
            stdout=json.dumps({"available_sources": ["reddit", "hackernews"]}),
            stderr="",
        )
        with patch.object(research_engine.subprocess, "run", return_value=fake) as run_mock:
            result = research_engine.run_diagnose()

        self.assertEqual(result["available_sources"], ["reddit", "hackernews"])
        self.assertIn("--diagnose", run_mock.call_args.args[0])


class TestRunResearch(unittest.TestCase):
    def test_success_returns_normalized_payload(self):
        fake = MagicMock(
            returncode=0,
            stdout=json.dumps({"topic": "cats", "clusters": []}),
            stderr="",
        )
        with patch.object(research_engine.subprocess, "run", return_value=fake) as run_mock:
            result = research_engine.run_research("cats", "quick", ["reddit"])

        self.assertEqual(result["entities"][0]["entity"], "cats")
        args = run_mock.call_args.args[0]
        self.assertIn("--quick", args)
        self.assertIn("--json-profile", args)
        self.assertIn("raw", args)
        self.assertEqual(args[args.index("--search") + 1], "reddit")

    def test_deep_depth_passes_deep_flag(self):
        fake = MagicMock(
            returncode=0,
            stdout=json.dumps({"topic": "cats", "clusters": []}),
            stderr="",
        )
        with patch.object(research_engine.subprocess, "run", return_value=fake) as run_mock:
            research_engine.run_research("cats", "deep", ["reddit"])
        self.assertIn("--deep", run_mock.call_args.args[0])

    def test_nonzero_exit_raises_with_stderr_tail(self):
        fake = MagicMock(returncode=1, stdout="", stderr="boom")
        with patch.object(research_engine.subprocess, "run", return_value=fake):
            with self.assertRaises(research_engine.ResearchExecutionError) as ctx:
                research_engine.run_research("cats", "quick", ["reddit"])
        self.assertIn("boom", str(ctx.exception))

    def test_invalid_json_raises(self):
        fake = MagicMock(returncode=0, stdout="not json", stderr="")
        with patch.object(research_engine.subprocess, "run", return_value=fake):
            with self.assertRaises(research_engine.ResearchExecutionError):
                research_engine.run_research("cats", "quick", ["reddit"])

    def test_timeout_raises(self):
        with patch.object(
            research_engine.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd="last30days", timeout=900),
        ):
            with self.assertRaises(research_engine.ResearchExecutionError):
                research_engine.run_research("cats", "deep", ["reddit"])


if __name__ == "__main__":
    unittest.main()
