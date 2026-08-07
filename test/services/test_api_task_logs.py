import threading
import time
import unittest
from unittest.mock import patch

from loguru import logger

from app.services import api_task_logs


class TestApiTaskLogs(unittest.TestCase):
    def tearDown(self):
        # avoid cross-test pollution of the module-level log store
        api_task_logs._task_logs.clear()

    def test_get_task_logs_returns_empty_list_for_unknown_task(self):
        self.assertEqual(api_task_logs.get_task_logs("nope"), [])

    def test_append_and_get_task_logs_round_trip(self):
        api_task_logs._append_task_log("task-1", "hello")
        api_task_logs._append_task_log("task-1", "world")
        self.assertEqual(api_task_logs.get_task_logs("task-1"), ["hello", "world"])

    def test_log_store_evicts_oldest_task_beyond_max_log_tasks(self):
        for i in range(api_task_logs._MAX_LOG_TASKS + 1):
            api_task_logs._append_task_log(f"task-{i}", "x")
        self.assertEqual(len(api_task_logs._task_logs), api_task_logs._MAX_LOG_TASKS)
        self.assertNotIn("task-0", api_task_logs._task_logs)

    def test_start_with_log_capture_calls_underlying_start_and_captures_its_logs(self):
        def fake_start(task_id, params, stop_at="video", voice_preview=None):
            from loguru import logger

            logger.info(f"working on {task_id}")

        with patch.object(api_task_logs.tm, "start", side_effect=fake_start):
            api_task_logs.start_with_log_capture(
                task_id="task-2", params={"video_subject": "x"}, stop_at="video"
            )

        logs = api_task_logs.get_task_logs("task-2")
        self.assertTrue(any("working on task-2" in line for line in logs))

    def test_start_with_log_capture_only_captures_current_thread(self):
        # a log line emitted from an unrelated thread must not leak into this task's logs
        from loguru import logger

        def fake_start(task_id, params, stop_at="video", voice_preview=None):
            other = threading.Thread(target=lambda: logger.info("from another thread"))
            other.start()
            other.join()
            logger.info(f"working on {task_id}")

        with patch.object(api_task_logs.tm, "start", side_effect=fake_start):
            api_task_logs.start_with_log_capture(
                task_id="task-3", params={"video_subject": "x"}, stop_at="video"
            )

        logs = api_task_logs.get_task_logs("task-3")
        self.assertTrue(any("working on task-3" in line for line in logs))
        self.assertFalse(any("from another thread" in line for line in logs))

    def test_concurrent_start_with_log_capture_calls_do_not_cross_contaminate(self):
        def fake_start(task_id, params, stop_at="video", voice_preview=None):
            for i in range(10):
                logger.info(f"{task_id} line {i}")

        task_ids = [f"concurrent-task-{i}" for i in range(8)]
        threads = []
        with patch.object(api_task_logs.tm, "start", side_effect=fake_start):
            for tid in task_ids:
                t = threading.Thread(
                    target=api_task_logs.start_with_log_capture,
                    kwargs={"task_id": tid, "params": {}, "stop_at": "video"},
                )
                threads.append(t)
                t.start()
            for t in threads:
                t.join()

        for tid in task_ids:
            logs = api_task_logs.get_task_logs(tid)
            self.assertEqual(len(logs), 10)
            for line in logs:
                self.assertIn(tid, line)
                for other_tid in task_ids:
                    if other_tid != tid:
                        self.assertNotIn(other_tid, line)


if __name__ == "__main__":
    unittest.main()
