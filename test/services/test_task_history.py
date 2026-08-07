import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.services import task_history


class TestTaskHistory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_lowest_final_video(self):
        for name in ("final-2.mp4", "final-0.mp4", "combined-0.mp4"):
            open(os.path.join(self.tmp.name, name), "w").close()
        self.assertEqual(os.path.basename(task_history.find_final_task_video(self.tmp.name)), "final-0.mp4")

    def test_safe_script_loader_handles_valid_and_corrupt_json(self):
        path = os.path.join(self.tmp.name, "script.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump({"script": "hello"}, file)
        self.assertEqual(task_history.safe_load_task_script(self.tmp.name)["script"], "hello")
        with open(path, "w", encoding="utf-8") as file:
            file.write("{bad")
        self.assertEqual(task_history.safe_load_task_script(self.tmp.name), {})

    def test_restore_validates_params_and_rejects_traversal(self):
        task_path = os.path.join(self.tmp.name, "t1")
        os.makedirs(task_path)
        with open(os.path.join(task_path, "script.json"), "w", encoding="utf-8") as file:
            json.dump({"params": {"video_subject": "cats"}, "script": "script", "search_terms": "cat"}, file)
        with patch.object(task_history.utils, "task_dir", return_value=self.tmp.name):
            result = task_history.load_task_restore_payload("t1")
            self.assertEqual(result["params"]["video_script"], "script")
            self.assertIsNone(task_history.load_task_restore_payload("../../etc"))

    def test_collect_merges_runtime_and_disk_history(self):
        task_path = os.path.join(self.tmp.name, "t1")
        os.makedirs(task_path)
        open(os.path.join(task_path, "final-0.mp4"), "w").close()
        with patch.object(task_history.utils, "task_dir", return_value=self.tmp.name), patch.object(task_history.sm.state, "get_all_tasks", return_value=([{"task_id": "t1", "state": 1, "progress": 100}], 1)):
            tasks = task_history.collect_task_summaries()
        self.assertEqual(tasks[0]["video_file"], "t1/final-0.mp4")


if __name__ == "__main__":
    unittest.main()
