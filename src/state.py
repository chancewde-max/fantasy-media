"""Persistent state + de-duplication.

Stores which events have already fired in SQLite so the same event never
posts to the group chat twice. This is the difference between a useful tool
and a spam machine.
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
