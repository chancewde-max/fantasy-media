"""Tests for storyline persistence: new/continue, heat, decay/archival, and
context formatting (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import storylines


def _db(tmp_path) -> str:
    return str(tmp_path / "state.db")


def test_no_context_when_nothing_active(tmp_path):
    assert storylines.active_context(_db(tmp_path)) == ""


def test_new_storyline_creates_and_appears_in_context(tmp_path):
    db = _db(tmp_path)
    storylines.apply_update(db, {
        "action": "new", "title": "The Josh Benching Scandal",
        "canon_note": "Josh benched his own RB1 in a playoff-implicated week.",
    })
    ctx = storylines.active_context(db)
    assert "The Josh Benching Scandal" in ctx
    assert "Josh benched his own RB1" in ctx
    assert "[key: the-josh-benching-scandal]" in ctx


def test_new_storyline_requires_title_and_note(tmp_path):
    db = _db(tmp_path)
    storylines.apply_update(db, {"action": "new", "title": "", "canon_note": "x"})
    storylines.apply_update(db, {"action": "new", "title": "x", "canon_note": ""})
    assert storylines.active_context(db) == ""


def test_none_action_is_a_no_op(tmp_path):
    db = _db(tmp_path)
    storylines.apply_update(db, {"action": "none"})
    storylines.apply_update(db, None)
    assert storylines.active_context(db) == ""


def test_continue_appends_note_and_raises_heat(tmp_path):
    db = _db(tmp_path)
    storylines.apply_update(db, {
        "action": "new", "title": "Waiver Wire Heist",
        "canon_note": "Miles snuck a league-winning waiver claim past everyone.",
    })
    storylines.apply_update(db, {
        "action": "continue", "key": "waiver-wire-heist",
        "canon_note": "Miles's stolen player has scored 20+ three weeks straight.",
    })
    ctx = storylines.active_context(db)
    assert "Miles snuck a league-winning" in ctx
    assert "scored 20+ three weeks straight" in ctx


def test_continue_against_unknown_key_is_ignored(tmp_path):
    db = _db(tmp_path)
    storylines.apply_update(db, {
        "action": "continue", "key": "does-not-exist", "canon_note": "x",
    })
    assert storylines.active_context(db) == ""


def test_notes_are_capped(tmp_path):
    db = _db(tmp_path)
    storylines.apply_update(db, {
        "action": "new", "title": "Ongoing Beef", "canon_note": "note-0",
    })
    for i in range(1, 10):
        storylines.apply_update(db, {
            "action": "continue", "key": "ongoing-beef", "canon_note": f"note-{i}",
        })
    ctx = storylines.active_context(db)
    assert "note-9" in ctx
    assert "note-0" not in ctx  # rolled off after MAX_NOTES


def test_decay_lowers_heat_and_eventually_archives(tmp_path):
    db = _db(tmp_path)
    storylines.apply_update(db, {
        "action": "new", "title": "Fading Bit", "canon_note": "it happened once",
    })
    assert "Fading Bit" in storylines.active_context(db)
    for _ in range(10):  # NEW_HEAT=55, DECAY_AMOUNT=12 -> archived well before 10 calls
        storylines.decay(db)
    assert storylines.active_context(db) == ""


def test_touch_by_teams_raises_heat_without_adding_a_note(tmp_path):
    db = _db(tmp_path)
    storylines.apply_update(db, {
        "action": "new", "title": "Rivalry Arc", "canon_note": "it started",
    })
    # Manually give it the real teams involved (apply_update doesn't set teams).
    import sqlite3
    conn = sqlite3.connect(db)
    conn.execute("UPDATE storylines SET teams = '[\"Team A\", \"Team B\"]' WHERE key = 'rivalry-arc'")
    conn.commit()
    conn.close()

    storylines.decay(db)  # heat: 55 -> 43
    storylines.touch_by_teams(db, ["Team A"])  # heat: 43 -> 49, survives longer
    for _ in range(3):
        storylines.decay(db)  # 49 -> 37 -> 25 -> 13, still alive
    assert "Rivalry Arc" in storylines.active_context(db)


def test_context_limits_to_top_n_by_heat(tmp_path):
    db = _db(tmp_path)
    for i in range(5):
        storylines.apply_update(db, {
            "action": "new", "title": f"Bit {i}", "canon_note": "x",
        })
        # continue a couple extra times so later bits run hotter than earlier ones
        for _ in range(i):
            storylines.apply_update(db, {
                "action": "continue", "key": f"bit-{i}", "canon_note": "escalated",
            })
    ctx = storylines.active_context(db, limit=2)
    assert "Bit 4" in ctx and "Bit 3" in ctx
    assert "Bit 0" not in ctx
