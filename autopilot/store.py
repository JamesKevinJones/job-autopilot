"""SQLite persistence for seen jobs, the application queue and the tracker."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from .config import DB_PATH
from .models import ScoredJob

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    fingerprint   TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    title         TEXT NOT NULL,
    company       TEXT NOT NULL,
    location      TEXT,
    url           TEXT NOT NULL,
    salary        TEXT,
    posted_at     TEXT,
    score         INTEGER NOT NULL,
    rejected_by   TEXT,
    reasons_for   TEXT,
    reasons_against TEXT,
    first_seen    TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'new'
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs(first_seen);

CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at        TEXT NOT NULL,
    fetched       INTEGER NOT NULL,
    new_jobs      INTEGER NOT NULL,
    queued        INTEGER NOT NULL,
    rejected      INTEGER NOT NULL,
    errors        TEXT
);
"""

# Statuses a job moves through.
NEW = "new"
QUEUED = "queued"
APPLIED = "applied"
SKIPPED = "skipped"
REJECTED_BY_GATE = "gated"


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    target = path or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert(conn: sqlite3.Connection, scored: ScoredJob, threshold: int) -> bool:
    """Insert a job if unseen. Returns True if it was new."""
    job, verdict = scored.job, scored.verdict
    existing = conn.execute(
        "SELECT 1 FROM jobs WHERE fingerprint = ?", (job.fingerprint,)
    ).fetchone()
    if existing:
        return False

    if not verdict.passed_gates:
        status = REJECTED_BY_GATE
    elif verdict.score >= threshold:
        status = QUEUED
    else:
        status = NEW

    conn.execute(
        """
        INSERT INTO jobs (fingerprint, source, title, company, location, url,
                          salary, posted_at, score, rejected_by, reasons_for,
                          reasons_against, first_seen, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.fingerprint, job.source, job.title, job.company, job.location,
            job.url, job.salary, job.posted_at, verdict.score, verdict.rejected_by,
            " | ".join(verdict.reasons_for), " | ".join(verdict.reasons_against),
            scored.seen_at, status,
        ),
    )
    return True


def record_run(conn, fetched: int, new_jobs: int, queued: int, rejected: int, errors: str = "") -> None:
    conn.execute(
        "INSERT INTO runs (ran_at, fetched, new_jobs, queued, rejected, errors) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), fetched, new_jobs, queued, rejected, errors),
    )


def queue(conn, limit: int = 20) -> list[sqlite3.Row]:
    """Jobs waiting for your approval, best first."""
    return conn.execute(
        "SELECT * FROM jobs WHERE status = ? ORDER BY score DESC, first_seen DESC LIMIT ?",
        (QUEUED, limit),
    ).fetchall()


def today_rows(conn, day: str | None = None) -> dict[str, list[sqlite3.Row]]:
    """Everything that happened on a given day, grouped by status."""
    day = day or date.today().isoformat()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE substr(first_seen, 1, 10) = ? ORDER BY score DESC", (day,)
    ).fetchall()
    grouped: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["status"], []).append(row)
    return grouped


def runs_today(conn, day: str | None = None) -> list[sqlite3.Row]:
    day = day or date.today().isoformat()
    return conn.execute(
        "SELECT * FROM runs WHERE substr(ran_at, 1, 10) = ? ORDER BY ran_at", (day,)
    ).fetchall()


def set_status(conn, fingerprint: str, status: str) -> None:
    conn.execute("UPDATE jobs SET status = ? WHERE fingerprint = ?", (status, fingerprint))
