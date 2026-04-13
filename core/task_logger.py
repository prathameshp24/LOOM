import sqlite3
import os
import json
import logging
from datetime import datetime

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "loom_db", "jobs.db"))


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _init_db():
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS task_runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input  TEXT NOT NULL,
                agent       TEXT NOT NULL,
                plan        TEXT DEFAULT '',
                tool_calls  TEXT DEFAULT '[]',
                result      TEXT DEFAULT '',
                status      TEXT DEFAULT 'done',
                created_at  TEXT DEFAULT (datetime('now')),
                duration_ms INTEGER DEFAULT 0,
                job_id      INTEGER DEFAULT NULL REFERENCES jobs(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL UNIQUE,
                prompt          TEXT NOT NULL,
                cron            TEXT NOT NULL,
                schedule_human  TEXT NOT NULL,
                enabled         INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                last_run_at     TEXT DEFAULT NULL,
                next_run_at     TEXT DEFAULT NULL
            );
        """)


_init_db()


# ── Task runs ─────────────────────────────────────────────────────────────────

def log_task_run(
    user_input: str,
    agent: str,
    plan: str = "",
    tool_calls: list = None,
    result: str = "",
    status: str = "done",
    duration_ms: int = 0,
    job_id: int = None,
) -> int:
    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO task_runs
               (user_input, agent, plan, tool_calls, result, status, duration_ms, job_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_input[:500],
                agent,
                plan[:600] if plan else "",
                json.dumps(tool_calls or []),
                result[:1000] if result else "",
                status,
                duration_ms,
                job_id,
            ),
        )
        return cur.lastrowid


def get_task_runs(limit: int = 50) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM task_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["tool_calls"] = json.loads(d["tool_calls"] or "[]")
        except Exception:
            d["tool_calls"] = []
        result.append(d)
    return result


def delete_task_run(run_id: int):
    with _get_conn() as conn:
        conn.execute("DELETE FROM task_runs WHERE id=?", (run_id,))


# ── Jobs ──────────────────────────────────────────────────────────────────────

def create_job(name: str, prompt: str, cron: str, schedule_human: str) -> dict:
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO jobs (name, prompt, cron, schedule_human) VALUES (?,?,?,?)",
            (name.strip(), prompt.strip(), cron.strip(), schedule_human.strip()),
        )
    logging.info(f"Job created: {name} [{cron}]")
    return get_job_by_name(name)


def get_all_jobs() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def get_job_by_name(name: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE name=?", (name,)).fetchone()
    return dict(row) if row else None


def get_job_by_id(job_id: int) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return dict(row) if row else None


def toggle_job(job_id: int, enabled: bool):
    with _get_conn() as conn:
        conn.execute("UPDATE jobs SET enabled=? WHERE id=?", (1 if enabled else 0, job_id))


def delete_job(job_id: int):
    with _get_conn() as conn:
        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))


def update_job_run_times(job_id: int, last_run_at: str, next_run_at: str | None):
    with _get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET last_run_at=?, next_run_at=? WHERE id=?",
            (last_run_at, next_run_at, job_id),
        )
