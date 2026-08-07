import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.controllers.v1 import task_logs as task_logs_controller
from app.models.exception import HttpException


class TestTaskLogsController(unittest.TestCase):
    def test_get_task_logs_returns_captured_lines_for_known_task(self):
        with patch.object(
            task_logs_controller.sm.state, "get_task", return_value={"task_id": "t1"}
        ), patch.object(
            task_logs_controller.api_task_logs,
            "get_task_logs",
            return_value=["line one", "line two"],
        ):
            response = task_logs_controller.get_task_logs_endpoint(
                SimpleNamespace(headers={}), task_id="t1"
            )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["data"]["logs"], ["line one", "line two"])

    def test_get_task_logs_raises_404_for_unknown_task(self):
        with patch.object(task_logs_controller.sm.state, "get_task", return_value=None):
            with self.assertRaises(HttpException) as ctx:
                task_logs_controller.get_task_logs_endpoint(
                    SimpleNamespace(headers={}), task_id="missing"
                )
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
