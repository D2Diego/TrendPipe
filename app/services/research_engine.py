"""Subprocess integration with the trendpipe research engine.

The engine (app.services.research_cli + app.services.research_lib) is a
first-party part of this backend, not an external tool. It still runs as a
child process rather than a direct in-process call because its runs are
long (up to RESEARCH_TIMEOUT_SECONDS) and need a hard, killable timeout -
something a Python thread cannot safely get.
"""

import os
import json
import subprocess
import sys
from typing import Any

from app.utils import utils

RESEARCH_CLI_MODULE = "app.services.research_cli"
RESEARCH_TIMEOUT_SECONDS = 900
DIAGNOSE_TIMEOUT_SECONDS = 30
_STDERR_TAIL_LENGTH = 2_000


class ResearchExecutionError(Exception):
    """The trendpipe process failed, timed out, or returned invalid output."""


def _trendpipe_env() -> dict[str, str]:
    # Imported here, not at module level, to avoid a circular import:
    # research_credentials also depends on this module.
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
            [sys.executable, "-m", RESEARCH_CLI_MODULE, "--diagnose", "--emit", "json"],
            capture_output=True,
            text=True,
            timeout=DIAGNOSE_TIMEOUT_SECONDS,
            env=_trendpipe_env(),
            cwd=utils.root_dir(),
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
        sys.executable,
        "-m",
        RESEARCH_CLI_MODULE,
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
            cwd=utils.root_dir(),
        )
    except subprocess.TimeoutExpired as exc:
        raise ResearchExecutionError(
            f"research timed out after {RESEARCH_TIMEOUT_SECONDS}s"
        ) from exc

    payload = _parse_json_result(result, "research")
    return normalize_report(payload, topic)
