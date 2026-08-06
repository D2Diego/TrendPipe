"""Check whether a newer stable MoneyPrinterTurbo release is available."""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import requests
from loguru import logger
from packaging.version import InvalidVersion, Version


LATEST_RELEASE_API_URL: Final = (
    "https://api.github.com/repos/harry0703/MoneyPrinterTurbo/releases/latest"
)
LATEST_RELEASE_PAGE_URL: Final = (
    "https://github.com/harry0703/MoneyPrinterTurbo/releases/latest"
)
# Update checks are optional and must not noticeably delay the local WebUI.
# Separate connection and read timeouts permit normal GitHub responses while
# failing quickly in offline environments.
RELEASE_CHECK_TIMEOUT: Final = (1.0, 2.0)
RELEASE_CHECK_HEADERS: Final = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "MoneyPrinterTurbo-Version-Checker",
}
UPDATE_CHECK_CACHE_TTL_SECONDS: Final = 12 * 60 * 60


def _parse_version(value: str) -> Version:
    """Parse common GitHub tags such as ``v1.2.3`` into comparable versions."""
    normalized = str(value or "").strip()
    if normalized.lower().startswith("v"):
        normalized = normalized[1:]
    return Version(normalized)


def get_available_update(current_version: str) -> str | None:
    """
    Return the latest stable version when it is newer, otherwise ``None``.

    GitHub's ``releases/latest`` endpoint excludes drafts and prereleases.
    Network, payload, and tag errors are logged and never affect core features.
    """
    try:
        installed_version = _parse_version(current_version)
    except InvalidVersion:
        logger.warning(
            f"skip update check because current version is invalid: {current_version!r}"
        )
        return None

    try:
        response = requests.get(
            LATEST_RELEASE_API_URL,
            headers=RELEASE_CHECK_HEADERS,
            timeout=RELEASE_CHECK_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        # Retain details for proxy, DNS, rate-limit, or payload failures without
        # disrupting ordinary WebUI users.
        logger.debug(
            "GitHub release check failed: "
            f"error_type={type(exc).__name__}, error={exc}"
        )
        return None

    if not isinstance(payload, dict):
        logger.debug(
            "GitHub release check returned an invalid payload: "
            f"payload_type={type(payload).__name__}"
        )
        return None

    tag_name = payload.get("tag_name", "")
    try:
        latest_version = _parse_version(tag_name)
    except InvalidVersion:
        logger.warning(
            f"skip update notification because release tag is invalid: {tag_name!r}"
        )
        return None

    if latest_version <= installed_version:
        return None

    normalized_latest_version = str(latest_version)
    logger.info(
        "MoneyPrinterTurbo update available: "
        f"current={installed_version}, latest={normalized_latest_version}"
    )
    return normalized_latest_version


@dataclass(frozen=True)
class UpdateCheckSnapshot:
    """Immediate, non-blocking snapshot of a background version check."""

    complete: bool
    available_version: str | None = None


class AsyncUpdateChecker:
    """
    Run version checks in a background thread and cache the latest result.

    Streamlit reruns the page after each interaction. A daemon performs network
    access so initial loads and expired caches never block the page.

    Positive and negative results are cached to avoid retrying on every rerun.
    The lock protects memory only and never wraps network I/O.
    """

    def __init__(
        self,
        check: Callable[[str], str | None] = get_available_update,
        ttl_seconds: float = UPDATE_CHECK_CACHE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._check = check
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._current_version: str | None = None
        self._available_version: str | None = None
        self._completed_at: float | None = None
        self._checking = False

    def poll(self, current_version: str) -> UpdateCheckSnapshot:
        """Return immediately, starting one check when the cache expires."""
        normalized_current_version = str(current_version or "").strip()
        now = self._clock()

        with self._lock:
            cache_is_fresh = (
                self._current_version == normalized_current_version
                and self._completed_at is not None
                and now - self._completed_at < self._ttl_seconds
            )
            if cache_is_fresh:
                return UpdateCheckSnapshot(
                    complete=True,
                    available_version=self._available_version,
                )

            if (
                self._checking
                and self._current_version == normalized_current_version
            ):
                return UpdateCheckSnapshot(complete=False)

            # Clear stale results first so callers see an explicit pending state.
            self._current_version = normalized_current_version
            self._available_version = None
            self._completed_at = None
            self._checking = True

            worker = threading.Thread(
                target=self._run_check,
                args=(normalized_current_version,),
                name="mpt-version-check",
                daemon=True,
            )
            worker.start()

        return UpdateCheckSnapshot(complete=False)

    def _run_check(self, current_version: str) -> None:
        try:
            available_version = self._check(current_version)
        except Exception:
            # Final worker boundary: log unexpected errors and leave pending state.
            logger.exception(
                "unexpected error while checking for a MoneyPrinterTurbo update"
            )
            available_version = None

        with self._lock:
            # A stale worker must not overwrite state for a newer version.
            if self._current_version != current_version:
                return
            self._available_version = available_version
            self._completed_at = self._clock()
            self._checking = False


_ASYNC_UPDATE_CHECKER = AsyncUpdateChecker()


def poll_available_update(current_version: str) -> UpdateCheckSnapshot:
    """Share one checker across Streamlit sessions to avoid duplicate requests."""
    return _ASYNC_UPDATE_CHECKER.poll(current_version)
