"""SQLite-backed persistence for trendpipe research runs."""

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from app.utils import utils

_DB_LOCK = threading.RLock()


def _db_path() -> str:
    return os.path.join(utils.storage_dir(create=True), "research.db")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    with _DB_LOCK:
        conn = sqlite3.connect(_db_path())
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS researches (
                id            TEXT PRIMARY KEY,
                topic         TEXT NOT NULL,
                depth         TEXT NOT NULL,
                sources       TEXT NOT NULL,
                status        TEXT NOT NULL,
                error_message TEXT,
                report_json   TEXT,
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_artifacts (
                id                    TEXT PRIMARY KEY,
                research_id           TEXT NOT NULL REFERENCES researches(id) ON DELETE CASCADE,
                entity                TEXT NOT NULL,
                cluster_id            TEXT NOT NULL,
                video_subject         TEXT NOT NULL,
                video_script          TEXT,
                video_script_prompt   TEXT,
                custom_system_prompt  TEXT,
                video_terms           TEXT,
                generated_fields      TEXT NOT NULL,
                created_at            TEXT NOT NULL,
                updated_at            TEXT NOT NULL,
                UNIQUE(research_id, entity, cluster_id)
            )
            """
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_research(topic: str, depth: str, sources: list[str]) -> dict[str, Any]:
    research_id = str(uuid.uuid4())
    now = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO researches
                (id, topic, depth, sources, status, error_message, report_json,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, 'pending', NULL, NULL, ?, ?)
            """,
            (research_id, topic, depth, json.dumps(sources), now, now),
        )
    created = get_research(research_id)
    if created is None:  # Defensive: the insert above either succeeds or raises.
        raise RuntimeError("research was not persisted")
    return created


def get_research(research_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM researches WHERE id = ?", (research_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def list_researches(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM researches ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def mark_running(research_id: str) -> None:
    _update(research_id, status="running", error_message=None)


def mark_completed(research_id: str, report_json: str) -> None:
    _update(
        research_id,
        status="completed",
        report_json=report_json,
        error_message=None,
    )


def mark_failed(research_id: str, error_message: str) -> None:
    _update(research_id, status="failed", error_message=error_message)


def _update(research_id: str, **fields: Any) -> None:
    fields["updated_at"] = _now()
    columns = ", ".join(f"{key} = ?" for key in fields)
    with _connect() as conn:
        conn.execute(
            f"UPDATE researches SET {columns} WHERE id = ?",
            (*fields.values(), research_id),
        )


def delete_research(research_id: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM researches WHERE id = ?", (research_id,)
        )
    return cursor.rowcount > 0


def upsert_artifact(
    research_id: str,
    entity: str,
    cluster_id: str,
    artifacts: dict[str, Any],
    generated_fields: list[str],
) -> dict[str, Any]:
    artifact_id = str(uuid.uuid4())
    now = _now()
    video_terms = artifacts.get("video_terms")
    encoded_terms = (
        json.dumps(video_terms, ensure_ascii=False)
        if video_terms is not None
        else None
    )
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO research_artifacts (
                id, research_id, entity, cluster_id, video_subject,
                video_script, video_script_prompt, custom_system_prompt,
                video_terms, generated_fields, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(research_id, entity, cluster_id) DO UPDATE SET
                video_subject = excluded.video_subject,
                video_script = excluded.video_script,
                video_script_prompt = excluded.video_script_prompt,
                custom_system_prompt = excluded.custom_system_prompt,
                video_terms = excluded.video_terms,
                generated_fields = excluded.generated_fields,
                updated_at = excluded.updated_at
            """,
            (
                artifact_id,
                research_id,
                entity,
                cluster_id,
                artifacts["video_subject"],
                artifacts.get("video_script"),
                artifacts.get("video_script_prompt"),
                artifacts.get("custom_system_prompt"),
                encoded_terms,
                json.dumps(generated_fields),
                now,
                now,
            ),
        )
    saved = get_artifact(research_id, entity, cluster_id)
    if saved is None:
        raise RuntimeError("artifact was not persisted")
    return saved


def get_artifact(
    research_id: str, entity: str, cluster_id: str
) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM research_artifacts
            WHERE research_id = ? AND entity = ? AND cluster_id = ?
            """,
            (research_id, entity, cluster_id),
        ).fetchone()
    return _artifact_row_to_dict(row) if row else None


def list_artifacts(research_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM research_artifacts
            WHERE research_id = ? ORDER BY created_at ASC
            """,
            (research_id,),
        ).fetchall()
    return [_artifact_row_to_dict(row) for row in rows]


def delete_artifact(research_id: str, entity: str, cluster_id: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute(
            """
            DELETE FROM research_artifacts
            WHERE research_id = ? AND entity = ? AND cluster_id = ?
            """,
            (research_id, entity, cluster_id),
        )
    return cursor.rowcount > 0


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["sources"] = json.loads(data["sources"])
    if data.get("report_json"):
        data["report_json"] = json.loads(data["report_json"])
    return data


def _artifact_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["generated_fields"] = json.loads(data["generated_fields"])
    if data.get("video_terms") is not None:
        data["video_terms"] = json.loads(data["video_terms"])
    return data
