"""Validation and orchestration for last30days research runs."""

import json
from typing import Any

from app.services import research_engine, research_store

_VALID_DEPTHS = ("quick", "deep")


class ResearchValidationError(Exception):
    """A research request failed validation before it was persisted."""


class ResearchConflictError(Exception):
    """An operation conflicts with the research's current state."""


def create_research(topic: str, depth: str, sources: list[str]) -> dict[str, Any]:
    topic = (topic or "").strip()
    if not topic:
        raise ResearchValidationError("topic is required")
    if depth not in _VALID_DEPTHS:
        raise ResearchValidationError(f"depth must be one of {_VALID_DEPTHS}")
    if not sources:
        raise ResearchValidationError("at least one source is required")

    diagnose = research_engine.run_diagnose()
    available = set(diagnose.get("available_sources") or [])
    unavailable = [source for source in sources if source not in available]
    if unavailable:
        raise ResearchValidationError(
            f"sources not available: {', '.join(unavailable)}"
        )

    return research_store.create_research(topic, depth, list(dict.fromkeys(sources)))


def run_research_job(research_id: str) -> None:
    """Run synchronously; the HTTP controller schedules this in the background."""
    found = research_store.get_research(research_id)
    if found is None:
        return

    research_store.mark_running(research_id)
    try:
        normalized = research_engine.run_research(
            found["topic"], found["depth"], found["sources"]
        )
    except research_engine.ResearchExecutionError as exc:
        research_store.mark_failed(research_id, str(exc))
        return
    research_store.mark_completed(research_id, json.dumps(normalized))


def delete_research(research_id: str) -> bool:
    found = research_store.get_research(research_id)
    if found is None:
        return False
    if found["status"] == "running":
        raise ResearchConflictError(
            "cannot delete a research while it is running"
        )
    return research_store.delete_research(research_id)
