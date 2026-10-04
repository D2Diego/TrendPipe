import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.controllers.v1 import task_history as controller
from app.router import root_api_router
from app.models.exception import HttpException


class TestTaskHistoryController(unittest.TestCase):
    def test_static_history_route_is_registered_before_dynamic_task_route(self):
        paths = [route.path for route in root_api_router.routes]
        self.assertLess(paths.index("/api/v1/tasks/history"), paths.index("/api/v1/tasks/{task_id}"))

    def test_lists_merged_history(self):
        with patch.object(controller.task_history, "collect_task_summaries", return_value=[{"task_id": "t1"}]):
            response = controller.list_task_history(SimpleNamespace(headers={}))
        self.assertEqual(response["data"]["tasks"][0]["task_id"], "t1")

    def test_returns_restore_payload_or_404(self):
        with patch.object(controller.task_history, "load_task_restore_payload", return_value={"task_id": "t1", "params": {"video_subject": "cats"}}):
            response = controller.get_task_restore_params(SimpleNamespace(headers={}), task_id="t1")
        self.assertEqual(response["data"]["params"]["video_subject"], "cats")
        with patch.object(controller.task_history, "load_task_restore_payload", return_value=None):
            with self.assertRaises(HttpException) as context:
                controller.get_task_restore_params(SimpleNamespace(headers={}), task_id="missing")
        self.assertEqual(context.exception.status_code, 404)

    def test_reads_task_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_path = os.path.join(tmp, "t1")
            os.makedirs(task_path)
            with open(os.path.join(task_path, "script.json"), "w", encoding="utf-8") as handle:
                handle.write('{"script": "hello"}')
            with patch.object(controller.utils, "task_dir", return_value=tmp):
                response = controller.read_task_file(SimpleNamespace(headers={}), task_id="t1", name="script.json")
        self.assertIn("hello", response["data"]["content"])
