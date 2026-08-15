"""Persistent state + de-duplication.

Stores which events have already fired in SQLite so the same event never
posts to the group chat twice. This is the difference between a useful tool
and a spam machine. Also holds small key/value markers (e.g. "when did a
real Insider tip last get reported") for scheduling decisions.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager

log = logging.getLogger(__name__)


class State:
    def __init__(self, db_path: str):
        self._db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fired_events (
                    event_key TEXT PRIMARY KEY,
                    fired_at  TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )

    def get_meta(self, key: str) -> str | None:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
            return row[0] if row else None

    def set_meta(self, key: str, value: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def is_new(self, event_key: str) -> bool:
        """True if this event_key has not fired before."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM fired_events WHERE event_key = ?", (event_key,)
            ).fetchone()
            return row is None

    def mark_fired(self, event_key: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO fired_events (event_key) VALUES (?)",
                (event_key,),
            )

    def filter_new(self, event_keys: list[str]) -> list[str]:
        """Return only the keys that haven't fired yet."""
        return [k for k in event_keys if self.is_new(k)]
