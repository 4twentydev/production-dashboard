from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .config import APP_NAME, BACKUP_DIR, DATA_DIR, DB_PATH, DEFAULT_SETTINGS, LOG_DIR


def _schema_path() -> Path:
    return Path(__file__).with_name("schema.sql")


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_directories()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    ensure_directories()
    schema = _schema_path().read_text(encoding="utf-8")
    with connect() as conn:
        conn.executescript(schema)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                """
                INSERT INTO settings (key, value, protected, updated_at)
                VALUES (?, ?, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO NOTHING
                """,
                (key, value),
            )
        conn.execute(
            """
            INSERT OR IGNORE INTO security_state (id, updated_at)
            VALUES (1, CURRENT_TIMESTAMP)
            """
        )


def get_setting(key: str, default: str | None = None) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str, *, protected: bool = False) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, protected, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                protected = excluded.protected,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value, 1 if protected else 0),
        )


def list_settings(include_protected: bool = True) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT key, value, protected, updated_at
            FROM settings
            ORDER BY key
            """
        ).fetchall()
    settings = [dict(row) for row in rows]
    if include_protected:
        return settings
    return [row for row in settings if not row["protected"]]


def get_setting_int(key: str, default: int) -> int:
    value = get_setting(key)
    try:
        return int(value) if value is not None and str(value).strip() else default
    except ValueError:
        return default


def get_security_state() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM security_state WHERE id = 1").fetchone()
        return dict(row) if row else {"id": 1}


def update_security_state(**fields: Any) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values())
    values.append(1)
    with connect() as conn:
        conn.execute(
            f"""
            UPDATE security_state
            SET {assignments}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )


def log_action(
    action_key: str,
    *,
    allowed: bool,
    success: bool,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO action_log (
                action_key, allowed, success, message, details_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                action_key,
                1 if allowed else 0,
                1 if success else 0,
                message,
                json.dumps(details or {}, sort_keys=True),
            ),
        )


def list_action_logs(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT action_key, allowed, success, message, details_json, created_at
            FROM action_log
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_action(action: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO actions (
                key, label, kind, target, args_json, platform,
                requires_pin, destructive, enabled, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                label = excluded.label,
                kind = excluded.kind,
                target = excluded.target,
                args_json = excluded.args_json,
                platform = excluded.platform,
                requires_pin = excluded.requires_pin,
                destructive = excluded.destructive,
                enabled = excluded.enabled,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                action["key"],
                action["label"],
                action["kind"],
                action["target"],
                action.get("args_json", "[]"),
                action.get("platform", "any"),
                1 if action.get("requires_pin") else 0,
                1 if action.get("destructive") else 0,
                1 if action.get("enabled", True) else 0,
            ),
        )


def list_actions() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT key, label, kind, target, args_json, platform,
                   requires_pin, destructive, enabled, updated_at
            FROM actions
            WHERE enabled = 1
            ORDER BY label
            """
        ).fetchall()
    return [dict(row) for row in rows]


def set_mount_status(
    mount_key: str,
    mount_path: str,
    *,
    present: bool,
    is_mount: bool,
    message: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO mount_status (
                mount_key, mount_path, present, is_mount, message, checked_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(mount_key) DO UPDATE SET
                mount_path = excluded.mount_path,
                present = excluded.present,
                is_mount = excluded.is_mount,
                message = excluded.message,
                checked_at = CURRENT_TIMESTAMP
            """,
            (mount_key, mount_path, 1 if present else 0, 1 if is_mount else 0, message),
        )


def list_mount_status() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT mount_key, mount_path, present, is_mount, message, checked_at
            FROM mount_status
            ORDER BY mount_key
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_job(job_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, job_number, release_code, pallet_code, mark_number,
                   display_name, search_text, source_type, source_path,
                   source_url, last_seen_at, indexed_at
            FROM jobs
            WHERE id = ?
            """,
            (job_id,),
        ).fetchone()
    return dict(row) if row else None


def set_pinned_job(job_id: int | None, label: str | None = None) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, protected, updated_at)
            VALUES ('pinned_job_id', ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            ("" if job_id is None else str(job_id),),
        )
        if label is not None:
            conn.execute(
                """
                INSERT INTO settings (key, value, protected, updated_at)
                VALUES ('pinned_job_label', ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                (label,),
            )


def clear_pinned_job() -> None:
    set_pinned_job(None, "")


def get_pinned_job() -> dict[str, Any] | None:
    pinned_id = get_setting("pinned_job_id", "")
    if not pinned_id:
        return None
    try:
        job = get_job(int(pinned_id))
    except ValueError:
        job = None
    if job:
        return job
    label = get_setting("pinned_job_label", "") or "Pinned job"
    return {
        "id": None,
        "display_name": label,
        "job_number": None,
        "release_code": None,
        "pallet_code": None,
        "mark_number": None,
        "source_path": None,
        "source_url": None,
        "search_text": label,
    }


def upsert_job(job: dict[str, Any]) -> int:
    with connect() as conn:
        existing = conn.execute(
            """
            SELECT id FROM jobs
            WHERE job_number IS ? AND release_code IS ? AND pallet_code IS ? AND mark_number IS ? AND source_path = ?
            """,
            (
                job.get("job_number"),
                job.get("release_code"),
                job.get("pallet_code"),
                job.get("mark_number"),
                job.get("source_path"),
            ),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE jobs
                SET display_name = ?, search_text = ?, source_type = ?, source_url = ?,
                    last_seen_at = CURRENT_TIMESTAMP, indexed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    job["display_name"],
                    job["search_text"],
                    job["source_type"],
                    job.get("source_url"),
                    existing["id"],
                ),
            )
            return int(existing["id"])
        cursor = conn.execute(
            """
            INSERT INTO jobs (
                job_number, release_code, pallet_code, mark_number, display_name,
                search_text, source_type, source_path, source_url, last_seen_at,
                indexed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                job.get("job_number"),
                job.get("release_code"),
                job.get("pallet_code"),
                job.get("mark_number"),
                job["display_name"],
                job["search_text"],
                job["source_type"],
                job.get("source_path"),
                job.get("source_url"),
            ),
        )
        return int(cursor.lastrowid)


def upsert_job_document(document: dict[str, Any]) -> None:
    with connect() as conn:
        existing = conn.execute(
            """
            SELECT id FROM job_documents
            WHERE job_id IS ? AND path_or_url = ?
            """,
            (document["job_id"], document["path_or_url"]),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE job_documents
                SET doc_type = ?, label = ?, source_path = ?, search_text = ?,
                    sort_order = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    document["doc_type"],
                    document["label"],
                    document.get("source_path"),
                    document["search_text"],
                    document.get("sort_order", 0),
                    existing["id"],
                ),
            )
            return
        conn.execute(
            """
            INSERT INTO job_documents (
                job_id, doc_type, label, path_or_url, source_path, search_text,
                sort_order, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                document["job_id"],
                document["doc_type"],
                document["label"],
                document["path_or_url"],
                document.get("source_path"),
                document["search_text"],
                document.get("sort_order", 0),
            ),
        )


def search_jobs(query: str, *, limit: int = 25) -> list[dict[str, Any]]:
    normalized = query.strip().lower()
    tokens = [token for token in normalized.replace("/", " ").replace("-", " ").split() if token]
    with connect() as conn:
        base_query = """
            SELECT id, job_number, release_code, pallet_code, mark_number,
                   display_name, search_text, source_type, source_path,
                   source_url, last_seen_at, indexed_at
            FROM jobs
        """
        if tokens:
            where_clause = " WHERE " + " AND ".join("search_text LIKE ?" for _ in tokens)
            rows = conn.execute(
                base_query + where_clause + " ORDER BY indexed_at DESC, display_name ASC LIMIT ?",
                [f"%{token}%" for token in tokens] + [limit],
            ).fetchall()
        else:
            rows = conn.execute(
                base_query + " ORDER BY indexed_at DESC, display_name ASC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def recent_jobs(limit: int = 12) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, job_number, release_code, pallet_code, mark_number,
                   display_name, search_text, source_type, source_path,
                   source_url, last_seen_at, indexed_at
            FROM jobs
            ORDER BY indexed_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def job_documents_for(job_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, job_id, doc_type, label, path_or_url, source_path,
                   search_text, sort_order, updated_at
            FROM job_documents
            WHERE job_id = ?
            ORDER BY sort_order ASC, label ASC
            """,
            (job_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_note(
    *,
    note_type: str,
    title: str,
    body: str,
    job_ref: str | None = None,
    protected: bool = False,
) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO notes (
                note_type, job_ref, title, body, protected, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (note_type, job_ref, title, body, 1 if protected else 0),
        )
        return int(cursor.lastrowid)


def list_notes(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, note_type, job_ref, title, body, protected, created_at, updated_at
            FROM notes
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def log_search(query: str, results_count: int) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO search_history (query, results_count, created_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (query, results_count),
        )


def list_recent_searches(limit: int = 12) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, query, results_count, created_at
            FROM search_history
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def record_backup(path: str, *, size_bytes: int, status: str, message: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO backups (backup_path, size_bytes, status, message, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (path, size_bytes, status, message),
        )


def list_backups(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, backup_path, size_bytes, status, message, created_at
            FROM backups
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
