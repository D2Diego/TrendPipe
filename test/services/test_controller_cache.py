import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.controllers.v1 import cache as cache_controller
from app.models.exception import HttpException
from app.services.cache_manager import VideoCacheCleanupResult, VideoCacheStats


class TestCacheController(unittest.TestCase):
    def test_get_stats_returns_service_result_as_dict(self):
        stats = VideoCacheStats(file_count=3, total_size=1024, oldest_mtime=1.0, newest_mtime=2.0)
        with patch.object(cache_controller.cache_manager, "get_video_cache_stats", return_value=stats):
            response = cache_controller.get_cache_stats(SimpleNamespace(headers={}), max_age_days=None)
        self.assertEqual(response["data"]["file_count"], 3)
        self.assertEqual(response["data"]["total_size"], 1024)

    def test_clean_cache_returns_cleanup_result_as_dict(self):
        result = VideoCacheCleanupResult(deleted_count=2, deleted_size=512, failed_count=0)
        with patch.object(cache_controller.cache_manager, "clean_video_cache", return_value=result):
            response = cache_controller.clean_cache(SimpleNamespace(headers={}), max_age_days=7)
        self.assertEqual(response["data"]["deleted_count"], 2)
        self.assertEqual(response["data"]["failed_count"], 0)

    def test_get_stats_returns_400_for_invalid_max_age_days(self):
        with patch.object(
            cache_controller.cache_manager,
            "get_video_cache_stats",
            side_effect=ValueError("max_age_days must be a positive int"),
        ):
            with self.assertRaises(HttpException) as ctx:
                cache_controller.get_cache_stats(SimpleNamespace(headers={}), max_age_days=0)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_clean_cache_returns_400_for_invalid_max_age_days(self):
        with patch.object(
            cache_controller.cache_manager,
            "clean_video_cache",
            side_effect=ValueError("max_age_days must be a positive int"),
        ):
            with self.assertRaises(HttpException) as ctx:
                cache_controller.clean_cache(SimpleNamespace(headers={}), max_age_days=-1)
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
