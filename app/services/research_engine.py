"""Subprocess integration with the vendored trendpipe research engine."""

import json
import os
import subprocess
from typing import Any

from app.utils import utils

TRENDPIPE_DIR = os.path.join(utils.root_dir(), "vendor", "trendpipe")
TRENDPIPE_SCRIPT = os.path.join(TRENDPIPE_DIR, "trendpipe.py")
PYTHON_BIN = "python3.12"
RESEARCH_TIMEOUT_SECONDS = 900
DIAGNOSE_TIMEOUT_SECONDS = 30
_STDERR_TAIL_LENGTH = 2_000


class ResearchExecutionError(Exception):
    """The trendpipe process failed, timed out, or returned invalid output."""


def _trendpipe_env() -> dict[str, str]:
    # Imported here, not at module level, to avoid a circular import:
    # research_credentials imports TRENDPIPE_DIR from this module.
    from app.services import research_credentials

    return {
        **research_credentials.read_env_file(),
        **os.environ,
        "TRENDPIPE_CONFIG_DIR": "",
    }


def _parse_json_result(
    result: subprocess.CompletedProcess[str], action: str
) -> dict[str, Any]:
    if result.returncode != 0:
        stderr_tail = (result.stderr or "").strip()[-_STDERR_TAIL_LENGTH:]
        raise ResearchExecutionError(
            stderr_tail or f"trendpipe {action} exited with status {result.returncode}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ResearchExecutionError(
            f"trendpipe {action} returned invalid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ResearchExecutionError(
            f"trendpipe {action} returned a non-object JSON payload"
        )
    return payload


def run_diagnose() -> dict[str, Any]:
    """Discover which sources and credentials trendpipe can currently use."""
    try:
        result = subprocess.run(
            [PYTHON_BIN, TRENDPIPE_SCRIPT, "--diagnose", "--emit", "json"],
            capture_output=True,
            text=True,
            timeout=DIAGNOSE_TIMEOUT_SECONDS,
            env=_trendpipe_env(),
            cwd=TRENDPIPE_DIR,
        )
    except subprocess.TimeoutExpired as exc:
        raise ResearchExecutionError(
            f"credential diagnosis timed out after {DIAGNOSE_TIMEOUT_SECONDS}s"
        ) from exc
    return _parse_json_result(result, "diagnosis")


def normalize_report(payload: dict[str, Any], topic: str) -> dict[str, Any]:
    """Normalize single and comparison output to one entity/report collection."""
    if "reports" in payload:
        reports = payload["reports"]
        if not isinstance(reports, list):
            raise ResearchExecutionError("comparison report has an invalid reports field")
        return {"entities": reports}
    return {"entities": [{"entity": topic, "report": payload}]}


def run_research(topic: str, depth: str, sources: list[str]) -> dict[str, Any]:
    """Run trendpipe and return its normalized raw-profile report."""
    args = [
        PYTHON_BIN,
        TRENDPIPE_SCRIPT,
        topic,
        "--emit",
        "json",
        "--json-profile",
        "raw",
        "--deep" if depth == "deep" else "--quick",
        "--search",
        ",".join(sources),
    ]
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=RESEARCH_TIMEOUT_SECONDS,
            env=_trendpipe_env(),
            cwd=TRENDPIPE_DIR,
        )
    except subprocess.TimeoutExpired as exc:
        raise ResearchExecutionError(
            f"research timed out after {RESEARCH_TIMEOUT_SECONDS}s"
        ) from exc

    payload = _parse_json_result(result, "research")
    return normalize_report(payload, topic)
