import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.services import research_store


class TestResearchStore(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._tmpdir.name, "research.db")
        self._patcher = patch.object(
            research_store, "_db_path", return_value=self._db_path
        )
        self._patcher.start()
        research_store.init_db()

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_create_and_get_research(self):
        created = research_store.create_research("cats", "quick", ["reddit"])

        fetched = research_store.get_research(created["id"])

        self.assertEqual(fetched["topic"], "cats")
        self.assertEqual(fetched["depth"], "quick")
        self.assertEqual(fetched["sources"], ["reddit"])
        self.assertEqual(fetched["status"], "pending")
        self.assertIsNone(fetched["report_json"])
        self.assertIsNone(fetched["error_message"])

    def test_get_research_returns_none_when_missing(self):
        self.assertIsNone(research_store.get_research("does-not-exist"))

    def test_list_researches_orders_newest_first(self):
        first = research_store.create_research("first", "quick", ["reddit"])
        second = research_store.create_research("second", "quick", ["reddit"])

        listed = research_store.list_researches()

        self.assertEqual([research["id"] for research in listed], [second["id"], first["id"]])

    def test_mark_running_updates_status(self):
        created = research_store.create_research("cats", "quick", ["reddit"])

        research_store.mark_running(created["id"])

        self.assertEqual(research_store.get_research(created["id"])["status"], "running")

    def test_mark_completed_stores_report_json(self):
        created = research_store.create_research("cats", "quick", ["reddit"])

        research_store.mark_completed(created["id"], json.dumps({"entities": []}))

        fetched = research_store.get_research(created["id"])
        self.assertEqual(fetched["status"], "completed")
        self.assertEqual(fetched["report_json"], {"entities": []})

    def test_mark_failed_stores_error_message(self):
        created = research_store.create_research("cats", "quick", ["reddit"])

        research_store.mark_failed(created["id"], "boom")

        fetched = research_store.get_research(created["id"])
        self.assertEqual(fetched["status"], "failed")
        self.assertEqual(fetched["error_message"], "boom")

    def test_delete_research_removes_row(self):
        created = research_store.create_research("cats", "quick", ["reddit"])

        self.assertTrue(research_store.delete_research(created["id"]))
        self.assertIsNone(research_store.get_research(created["id"]))

    def test_delete_research_returns_false_when_missing(self):
        self.assertFalse(research_store.delete_research("does-not-exist"))

    def test_upsert_artifact_overwrites_the_cluster_artifact(self):
        research = research_store.create_research("cats", "quick", ["reddit"])

        first = research_store.upsert_artifact(
            research["id"], "cats", "cluster-1",
            {"video_subject": "First", "video_script": "Script one"},
            ["video_script"],
        )
        second = research_store.upsert_artifact(
            research["id"], "cats", "cluster-1",
            {"video_subject": "Second", "video_terms": ["cat", "pet"]},
            ["video_terms"],
        )

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["video_subject"], "Second")
        self.assertEqual(second["video_terms"], ["cat", "pet"])
        self.assertIsNone(second["video_script"])
        self.assertEqual(second["generated_fields"], ["video_terms"])

    def test_delete_artifact_and_research_cascade(self):
        research = research_store.create_research("cats", "quick", ["reddit"])
        research_store.upsert_artifact(
            research["id"], "cats", "cluster-1",
            {"video_subject": "Cats"}, [],
        )

        self.assertTrue(research_store.delete_artifact(research["id"], "cats", "cluster-1"))
        self.assertIsNone(research_store.get_artifact(research["id"], "cats", "cluster-1"))

        research_store.upsert_artifact(
            research["id"], "cats", "cluster-1",
            {"video_subject": "Cats"}, [],
        )
        research_store.delete_research(research["id"])
        self.assertEqual(research_store.list_artifacts(research["id"]), [])


if __name__ == "__main__":
    unittest.main()
