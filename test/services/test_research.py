import os
import tempfile
import unittest
from unittest.mock import patch

from app.services import research, research_engine, research_store


class TestResearchService(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._tmpdir.name, "research.db")
        self._db_patcher = patch.object(
            research_store, "_db_path", return_value=self._db_path
        )
        self._db_patcher.start()
        research_store.init_db()
        self._diagnose_patcher = patch.object(
            research_engine,
            "run_diagnose",
            return_value={"available_sources": ["reddit", "hackernews"]},
        )
        self._diagnose_patcher.start()

    def tearDown(self):
        self._diagnose_patcher.stop()
        self._db_patcher.stop()
        self._tmpdir.cleanup()

    def test_create_research_validates_input_and_source_availability(self):
        invalid_requests = [
            ("   ", "quick", ["reddit"]),
            ("cats", "medium", ["reddit"]),
            ("cats", "quick", []),
            ("cats", "quick", ["tiktok"]),
        ]
        for topic, depth, sources in invalid_requests:
            with self.subTest(topic=topic, depth=depth, sources=sources):
                with self.assertRaises(research.ResearchValidationError):
                    research.create_research(topic, depth, sources)

    def test_create_research_persists_pending_row(self):
        created = research.create_research("  cats  ", "quick", ["reddit"])

        self.assertEqual(created["status"], "pending")
        self.assertEqual(created["topic"], "cats")

    def test_run_research_job_moves_from_running_to_completed(self):
        created = research.create_research("cats", "quick", ["reddit"])
        seen_status = {}

        def fake_run_research(topic, depth, sources):
            seen_status["status"] = research_store.get_research(created["id"])[
                "status"
            ]
            return {"entities": [{"entity": topic, "report": {}}]}

        with patch.object(
            research_engine, "run_research", side_effect=fake_run_research
        ):
            research.run_research_job(created["id"])

        fetched = research_store.get_research(created["id"])
        self.assertEqual(seen_status["status"], "running")
        self.assertEqual(fetched["status"], "completed")
        self.assertEqual(fetched["report_json"]["entities"][0]["entity"], "cats")

    def test_run_research_job_marks_failed_on_execution_error(self):
        created = research.create_research("cats", "quick", ["reddit"])
        with patch.object(
            research_engine,
            "run_research",
            side_effect=research_engine.ResearchExecutionError("boom"),
        ):
            research.run_research_job(created["id"])

        fetched = research_store.get_research(created["id"])
        self.assertEqual(fetched["status"], "failed")
        self.assertEqual(fetched["error_message"], "boom")

    def test_delete_research_blocks_running_rows(self):
        created = research.create_research("cats", "quick", ["reddit"])
        research_store.mark_running(created["id"])

        with self.assertRaises(research.ResearchConflictError):
            research.delete_research(created["id"])

    def test_delete_research_removes_existing_and_reports_missing(self):
        created = research.create_research("cats", "quick", ["reddit"])

        self.assertTrue(research.delete_research(created["id"]))
        self.assertFalse(research.delete_research("does-not-exist"))


if __name__ == "__main__":
    unittest.main()
