import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.models.schema import MaterialInfo, VideoAspect
from app.services import material, material_cache


class TestMaterialSearchCache(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir_patch = patch(
            "app.services.material_cache.utils.storage_dir",
            return_value=self.temp_dir.name,
        )
        self.cache_dir_patch.start()

    def tearDown(self):
        self.cache_dir_patch.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def _item(url: str = "https://example.com/video.mp4") -> MaterialInfo:
        return MaterialInfo(
            provider="pixabay",
            url=url,
            duration=12,
            source_info={
                "provider": "pixabay",
                "search_term": "nature",
                "asset_id": "123",
                "source_page": "https://pixabay.com/videos/example-123/",
                "creator": {
                    "id": "456",
                    "name": "Creator",
                    "profile_page": "https://pixabay.com/users/creator-456/",
                },
                "rendition": {
                    "id": "large",
                    "width": 1080,
                    "height": 1920,
                },
            },
        )

    def _cache_path(self) -> Path:
        return material_cache._cache_path(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
        )

    def test_cache_round_trip_preserves_material_fields(self):
        """
        The disk cache must be able to recover across process. MaterialInfo All fields needed, not just caches URL
        Lost after provider or duration, This has led to a change in the behaviour of subsequent downloads and time calculations.
        """
        saved = material_cache.save_material_search_cache(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
            items=[self._item()],
        )
        loaded = material_cache.load_material_search_cache(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
        )

        self.assertTrue(saved)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].provider, "pixabay")
        self.assertEqual(loaded[0].url, "https://example.com/video.mp4")
        self.assertEqual(loaded[0].duration, 12)
        self.assertEqual(loaded[0].source_info["search_term"], "nature")
        self.assertEqual(loaded[0].source_info["asset_id"], "123")
        self.assertEqual(
            loaded[0].source_info["source_page"],
            "https://pixabay.com/videos/example-123/",
        )
        self.assertEqual(
            loaded[0].source_info["creator"]["profile_page"],
            "https://pixabay.com/users/creator-456/",
        )

    def test_expired_cache_is_removed_and_treated_as_miss(self):
        """
        Pixabay Request maximum reuse of search results 24 Hours. The expired documents must immediately expire and be deleted.
        Prevention of old material URL Infinite re-use and avoid the continued accumulation of cache directories. JSON.
        """
        material_cache.save_material_search_cache(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
            items=[self._item()],
        )
        cache_path = self._cache_path()
        now = 2_000_000_000.0
        expired_mtime = now - material_cache.MATERIAL_SEARCH_CACHE_TTL_SECONDS - 1
        os.utime(cache_path, (expired_mtime, expired_mtime))

        loaded = material_cache.load_material_search_cache(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
            now=now,
        )

        self.assertIsNone(loaded)
        self.assertFalse(cache_path.exists())

    def test_future_dated_cache_is_removed_and_treated_as_miss(self):
        """The system cannot be bypassed by the future when time is abnormal. 24 Hours are valid."""
        material_cache.save_material_search_cache(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
            items=[self._item()],
        )
        cache_path = self._cache_path()
        now = 2_000_000_000.0
        future_mtime = now + 60
        os.utime(cache_path, (future_mtime, future_mtime))

        loaded = material_cache.load_material_search_cache(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
            now=now,
        )

        self.assertIsNone(loaded)
        self.assertFalse(cache_path.exists())

    def test_corrupted_cache_is_removed_without_breaking_search(self):
        """
        Unusual process exits, disk failures or manual changes may leave a corrupt file. Read failure should retreat
        Searching for and cleaning of bad files at a remote end does not allow a cache to permanently block material generation.
        """
        cache_path = self._cache_path()
        cache_path.write_text("{invalid-json", encoding="utf-8")

        with patch("app.services.material_cache.logger.warning") as warning:
            loaded = material_cache.load_material_search_cache(
                provider="pixabay",
                search_term="nature",
                minimum_duration=5,
                video_aspect=VideoAspect.portrait,
            )

        self.assertIsNone(loaded)
        self.assertFalse(cache_path.exists())
        self.assertTrue(warning.called)

    def test_empty_results_are_not_cached(self):
        """
        Current provider Interface [] It was also stated that there had been no results and that the request had failed. Cache empty list will put
        Cloudflare Interception or short-term network failure solidification 24 Hours, therefore, can only slow down successful results.
        """
        saved = material_cache.save_material_search_cache(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
            items=[],
        )

        self.assertFalse(saved)
        self.assertEqual(list(Path(self.temp_dir.name).iterdir()), [])

    def test_cache_file_does_not_contain_search_parameters_or_credentials(self):
        """
        The cache file name uses a summary and saves only material fields. Even if the user shares storage Contents
        There should be no keywords in the document.API Key or other request configuration.
        """
        item = self._item()
        item.source_info["source_page"] += "?token=drop"
        item.source_info["creator"]["profile_page"] += "?key=drop"
        material_cache.save_material_search_cache(
            provider="pixabay",
            search_term="private search term",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
            items=[item],
        )
        cache_files = list(Path(self.temp_dir.name).glob("*.json"))

        self.assertEqual(len(cache_files), 1)
        self.assertNotIn("private search term", cache_files[0].name)
        raw_payload = cache_files[0].read_text(encoding="utf-8")
        payload = json.loads(raw_payload)
        self.assertEqual(set(payload), {"version", "items"})
        self.assertNotIn("private search term", raw_payload)
        self.assertNotIn("token=drop", raw_payload)

    def test_coverr_signed_urls_are_never_cached(self):
        """Coverr Download Address Contains Signature JWT, Cannot enter disk caches that can be kept for long."""
        item = self._item(
            "https://storage.coverr.co/video/download?token=signed-jwt"
        )
        item.provider = "coverr"
        item.source_info["provider"] = "coverr"

        saved = material_cache.save_material_search_cache(
            provider="coverr",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
            items=[item],
        )

        self.assertFalse(saved)
        self.assertEqual(list(Path(self.temp_dir.name).glob("*.json")), [])

    def test_coverr_cache_load_removes_legacy_signed_url(self):
        """Visits Coverr This should clear the cache of possible downloads of signatures from the old version."""
        cache_path = material_cache._cache_path(
            provider="coverr",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
        )
        cache_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "items": [
                        {
                            "provider": "coverr",
                            "url": "https://storage.coverr.co/video?token=signed-jwt",
                            "duration": 12,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        loaded = material_cache.load_material_search_cache(
            provider="coverr",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
        )

        self.assertIsNone(loaded)
        self.assertFalse(cache_path.exists())

    def test_version_one_cache_is_invalidated(self):
        """Old caches lacked source information, and upgrades had to be re-examined rather than creating missing task records."""
        cache_path = self._cache_path()
        cache_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "items": [
                        {
                            "provider": "pixabay",
                            "url": "https://example.com/old.mp4",
                            "duration": 12,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        loaded = material_cache.load_material_search_cache(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
        )

        self.assertIsNone(loaded)
        self.assertFalse(cache_path.exists())

    def test_cache_key_separates_provider_duration_and_aspect(self):
        """
        The source of the material, the hour maximum and the painting will change the results of the remote search, and any change in the parameters will be required.
        Use an independent cache to avoid returning material that does not meet the requirements of the current task to the video generation process.
        """
        base_path = material_cache._cache_path(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
        )
        paths = {
            base_path,
            material_cache._cache_path(
                provider="pexels",
                search_term="nature",
                minimum_duration=5,
                video_aspect=VideoAspect.portrait,
            ),
            material_cache._cache_path(
                provider="pixabay",
                search_term="nature",
                minimum_duration=10,
                video_aspect=VideoAspect.portrait,
            ),
            material_cache._cache_path(
                provider="pixabay",
                search_term="nature",
                minimum_duration=5,
                video_aspect=VideoAspect.landscape,
            ),
        }

        self.assertEqual(len(paths), 4)

    def test_search_wrapper_reuses_cache_across_calls(self):
        """
        First call a remote search and write a cache, and second call the same parameter directly repeats the disk results.
        It's a reduction. Pixabay API Call Cloudflare Wind control triggers probability core behavior.
        """
        remote_search = Mock(return_value=[self._item()])

        first = material._search_videos_with_cache(
            provider="pixabay",
            search_videos=remote_search,
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
        )
        second = material._search_videos_with_cache(
            provider="pixabay",
            search_videos=remote_search,
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
        )

        self.assertEqual(remote_search.call_count, 1)
        self.assertEqual(first, second)

    def test_search_wrapper_refreshes_mixed_orientation_cache(self):
        """
        Pre-upgrading caches may be mixed into material in other directions. Only a small number of entries returned after filtering will reduce the ingenuity Box
        Diversity makes it possible to re-request and replace the entire pool when a mismatch of any direction is found.
        """
        portrait_item = self._item("https://example.com/old-portrait.mp4")
        landscape_item = self._item("https://example.com/old-landscape.mp4")
        landscape_item.source_info["rendition"] = {
            "id": "large",
            "width": 1920,
            "height": 1080,
        }
        material_cache.save_material_search_cache(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
            items=[portrait_item, landscape_item],
        )

        refreshed_item = self._item("https://example.com/refreshed-portrait.mp4")
        remote_search = Mock(return_value=[refreshed_item])
        results = material._search_videos_with_cache(
            provider="pixabay",
            search_videos=remote_search,
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
        )

        self.assertEqual(remote_search.call_count, 1)
        self.assertEqual(
            [item.url for item in results],
            ["https://example.com/refreshed-portrait.mp4"],
        )
        cached_items = material_cache.load_material_search_cache(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.portrait,
        )
        self.assertEqual(
            [item.url for item in cached_items],
            ["https://example.com/refreshed-portrait.mp4"],
        )

    def test_square_search_reuses_crop_compatible_cache(self):
        """Square tasks should continue to re-use cut-off material caches and should not repeat requests for remote ends depending on the original direction."""
        landscape_item = self._item("https://example.com/landscape.mp4")
        landscape_item.source_info["rendition"] = {
            "id": "large",
            "width": 1920,
            "height": 1080,
        }
        material_cache.save_material_search_cache(
            provider="pixabay",
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.square,
            items=[landscape_item],
        )
        remote_search = Mock(return_value=[])

        results = material._search_videos_with_cache(
            provider="pixabay",
            search_videos=remote_search,
            search_term="nature",
            minimum_duration=5,
            video_aspect=VideoAspect.square,
        )

        self.assertEqual(remote_search.call_count, 0)
        self.assertEqual(
            [item.url for item in results],
            ["https://example.com/landscape.mp4"],
        )

    def test_search_wrapper_retries_after_empty_result(self):
        """The empty results are not cached and the next call should still be made to the remote end in order to automatically retry once the temporary failure has resumed."""
        remote_search = Mock(return_value=[])

        for _ in range(2):
            results = material._search_videos_with_cache(
                provider="pixabay",
                search_videos=remote_search,
                search_term="nature",
                minimum_duration=5,
                video_aspect=VideoAspect.portrait,
            )
            self.assertEqual(results, [])

        self.assertEqual(remote_search.call_count, 2)

    def test_cache_read_failure_falls_back_to_remote_search(self):
        """Cache reading abnormalities can only be downgraded to non-failure and cannot interrupt remote material searches."""
        remote_items = [self._item()]
        remote_search = Mock(return_value=remote_items)

        with patch.object(
            material_cache,
            "load_material_search_cache",
            side_effect=RuntimeError("cache read failed"),
        ), patch.object(material_cache.logger, "warning") as warning:
            results = material._search_videos_with_cache(
                provider="pixabay",
                search_videos=remote_search,
                search_term="nature",
                minimum_duration=5,
                video_aspect=VideoAspect.portrait,
            )

        self.assertEqual(results, remote_items)
        self.assertEqual(remote_search.call_count, 1)
        self.assertTrue(warning.called)

    def test_cache_write_failure_keeps_remote_results(self):
        """Once the remote search is successful, even if the cache fails to write, the material must continue to be returned."""
        remote_items = [self._item()]
        remote_search = Mock(return_value=remote_items)

        with patch.object(
            material_cache,
            "load_material_search_cache",
            return_value=None,
        ), patch.object(
            material_cache,
            "save_material_search_cache",
            side_effect=RuntimeError("cache write failed"),
        ), patch.object(material_cache.logger, "warning") as warning:
            results = material._search_videos_with_cache(
                provider="pixabay",
                search_videos=remote_search,
                search_term="nature",
                minimum_duration=5,
                video_aspect=VideoAspect.portrait,
            )

        self.assertEqual(results, remote_items)
        self.assertEqual(remote_search.call_count, 1)
        self.assertTrue(warning.called)

    def test_invalid_cache_item_does_not_raise(self):
        """An abnormal material object cannot allow an optional cache to be written to destroy the caller main process."""
        with patch.object(material_cache.logger, "warning") as warning:
            saved = material_cache.save_material_search_cache(
                provider="pixabay",
                search_term="nature",
                minimum_duration=5,
                video_aspect=VideoAspect.portrait,
                items=[None],
            )

        self.assertFalse(saved)
        self.assertTrue(warning.called)

    def test_concurrent_identical_searches_share_remote_request(self):
        """
        API The service allows multiple assignments. When the same condition is first searched, the first line should wait for the next line
        Writes the cache instead of consuming the third-party interface again.
        """
        remote_started = threading.Event()
        allow_remote_finish = threading.Event()
        remote_call_lock = threading.Lock()
        remote_call_count = 0
        results = []

        def remote_search(**_kwargs):
            nonlocal remote_call_count
            with remote_call_lock:
                remote_call_count += 1
            remote_started.set()
            self.assertTrue(allow_remote_finish.wait(timeout=2))
            return [self._item()]

        def run_search():
            results.append(
                material._search_videos_with_cache(
                    provider="pixabay",
                    search_videos=remote_search,
                    search_term="shared nature",
                    minimum_duration=5,
                    video_aspect=VideoAspect.portrait,
                )
            )

        first_thread = threading.Thread(target=run_search)
        second_thread = threading.Thread(target=run_search)
        first_thread.start()
        self.assertTrue(remote_started.wait(timeout=2))
        second_thread.start()
        # Gives a second line time to access the cache lock waiting area to ensure that the test covers real and missed.
        time.sleep(0.05)
        allow_remote_finish.set()
        first_thread.join(timeout=2)
        second_thread.join(timeout=2)

        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())
        self.assertEqual(remote_call_count, 1)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])

    def test_cleanup_removes_expired_entries_only(self):
        """Low frequency clean-up only removes obsolete caches and should not affect valid caches or other user files."""
        stale_path = self._cache_path()
        stale_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "items": [
                        {
                            "provider": "pixabay",
                            "url": "https://example.com/stale.mp4",
                            "duration": 12,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        fresh_path = material_cache._cache_path(
            provider="pexels",
            search_term="fresh",
            minimum_duration=5,
            video_aspect=VideoAspect.landscape,
        )
        fresh_path.write_text("{}", encoding="utf-8")
        unrelated_path = Path(self.temp_dir.name) / "notes.json"
        unrelated_path.write_text("keep", encoding="utf-8")

        now = 2_000_000_000.0
        stale_mtime = now - material_cache.MATERIAL_SEARCH_CACHE_TTL_SECONDS - 1
        os.utime(stale_path, (stale_mtime, stale_mtime))
        os.utime(fresh_path, (now - 60, now - 60))

        deleted = material_cache.cleanup_expired_material_search_cache(
            now=now,
            force=True,
        )

        self.assertEqual(deleted, 1)
        self.assertFalse(stale_path.exists())
        self.assertTrue(fresh_path.exists())
        self.assertTrue(unrelated_path.exists())


if __name__ == "__main__":
    unittest.main()
