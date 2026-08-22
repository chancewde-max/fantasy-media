"""Persistent narrative memory: recurring beefs, bits, and storylines.

This is what makes the manufactured side of the feed (Insider reports,
fabricated rumors) feel like a living ecosystem instead of a slot machine
that spits out an unrelated rumor every few hours. Every Insider drop can
either start a new storyline, escalate an existing one, or let one wrap up
naturally — Claude decides which and we persist the outcome here, in the
same SQLite file as the rest of the engine's state.

A storyline has "heat": it rises when it's referenced or when the real teams
involved play a notable game, and decays on a daily cron. High-heat
storylines are always in context so the next drop can build on them; once
heat hits zero the storyline is archived and stops being fed back in,
so old bits fade out instead of getting dragged along forever.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

log = logging.getLogger(__name__)

MAX_NOTES = 6            # notes kept per storyline before the oldest drop off
NEW_HEAT = 55
CONTINUE_HEAT_BUMP = 18
TOUCH_HEAT_BUMP = 6
DECAY_AMOUNT = 12
MAX_HEAT = 100
CONTEXT_LIMIT = 3         # storylines fed into a single prompt


@contextmanager
def _conn(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS storylines (
            key        TEXT PRIMARY KEY,
            title      TEXT NOT NULL,
            teams      TEXT NOT NULL DEFAULT '[]',
            notes      TEXT NOT NULL DEFAULT '[]',
            heat       INTEGER NOT NULL DEFAULT 0,
            status     TEXT NOT NULL DEFAULT 'active',
            mentions   INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-")
    return slug[:40] or "storyline"


def _heat_label(heat: int) -> str:
    if heat >= 70:
        return "red hot"
    if heat >= 40:
        return "simmering"
    return "cooling off"


# --------------------------------------------------------------------- reads
def active_context(db_path: str, limit: int = CONTEXT_LIMIT) -> str:
    """Formatted block of the hottest active storylines, for a generator
    prompt. Empty string if there's nothing active — a storyline is never
    forced into a post."""
    with _conn(db_path) as conn:
        _init(conn)
        rows = conn.execute(
            "SELECT key, title, notes, heat FROM storylines "
            "WHERE status = 'active' ORDER BY heat DESC, updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    if not rows:
        return ""

    lines = []
    for key, title, notes_json, heat in rows:
        notes = json.loads(notes_json or "[]")
        note_text = "; ".join(notes[-3:]) if notes else "just kicked off, no details yet"
        lines.append(f"- [key: {key}] {title} ({_heat_label(heat)}): {note_text}")

    return (
        "ONGOING LEAGUE STORYLINES (real running bits this feed has been building — "
        "continue or escalate one if it naturally fits, or start something new; "
        "never force one into a post it doesn't belong in):\n" + "\n".join(lines)
    )


# ------------------------------------------------------------------- writes
def apply_update(db_path: str, storyline: dict | None) -> None:
    """Persist the outcome of one generation call.

    ``storyline`` is the ``{"action", "key", "title", "canon_note"}`` block a
    generator extracts from Claude's response. Silently a no-op for a missing
    or malformed dict, or action "none" — most drops don't touch a storyline.
    """
    if not storyline:
        return
    action = str(storyline.get("action") or "none").strip().lower()
    canon_note = str(storyline.get("canon_note") or "").strip()

    if action == "new":
        title = str(storyline.get("title") or "").strip()
        if not title or not canon_note:
            return
        key = str(storyline.get("key") or "").strip() or _slugify(title)
        _create(db_path, key, title, canon_note)
    elif action == "continue":
        key = str(storyline.get("key") or "").strip()
        if not key or not canon_note:
            return
        _continue(db_path, key, canon_note)
    # action == "none" (or unrecognized) -> nothing to persist


def _create(db_path: str, key: str, title: str, canon_note: str) -> None:
    now = _now()
    with _conn(db_path) as conn:
        _init(conn)
        conn.execute(
            "INSERT INTO storylines (key, title, teams, notes, heat, status, "
            "mentions, created_at, updated_at) VALUES (?, ?, '[]', ?, ?, 'active', 1, ?, ?) "
            "ON CONFLICT(key) DO NOTHING",
            (key, title, json.dumps([canon_note]), NEW_HEAT, now, now),
        )


def _continue(db_path: str, key: str, canon_note: str) -> None:
    with _conn(db_path) as conn:
        _init(conn)
        row = conn.execute(
            "SELECT notes, heat FROM storylines WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return  # Claude referenced a key that doesn't exist -> ignore
        notes = json.loads(row[0] or "[]")
        notes.append(canon_note)
        notes = notes[-MAX_NOTES:]
        heat = min(MAX_HEAT, row[1] + CONTINUE_HEAT_BUMP)
        conn.execute(
            "UPDATE storylines SET notes = ?, heat = ?, status = 'active', "
            "mentions = mentions + 1, updated_at = ? WHERE key = ?",
            (json.dumps(notes), heat, _now(), key),
        )


def touch_by_teams(db_path: str, teams: list[str]) -> None:
    """A real game result involved one of these teams -> nudge any active
    storyline that mentions them, so real events keep a beef alive without
    inventing new canon for it."""
    names = {t.strip().lower() for t in teams if t}
    if not names:
        return
    with _conn(db_path) as conn:
        _init(conn)
        rows = conn.execute(
            "SELECT key, teams, heat FROM storylines WHERE status = 'active'"
        ).fetchall()
        for key, teams_json, heat in rows:
            storyline_teams = {t.strip().lower() for t in json.loads(teams_json or "[]")}
            if storyline_teams & names:
                conn.execute(
                    "UPDATE storylines SET heat = ?, updated_at = ? WHERE key = ?",
                    (min(MAX_HEAT, heat + TOUCH_HEAT_BUMP), _now(), key),
                )


def decay(db_path: str, amount: int = DECAY_AMOUNT) -> None:
    """Cool every active storyline down; archive the ones that hit zero.
    Meant to run once a day so bits fade out instead of lingering forever."""
    with _conn(db_path) as conn:
        _init(conn)
        conn.execute(
            "UPDATE storylines SET heat = MAX(0, heat - ?), updated_at = ? "
            "WHERE status = 'active'",
            (amount, _now()),
        )
        conn.execute(
            "UPDATE storylines SET status = 'resolved' WHERE status = 'active' AND heat <= 0"
        )
