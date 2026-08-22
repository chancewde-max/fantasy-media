"""Tests for the Insider fabrication scheduling helper (no network)."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import _any_games_played, _previous_checkpoint

HOURS = [7, 12, 18]


def test_no_games_played_when_everyone_is_scoreless():
    standings = [
        {"rank": i, "team": f"Team {i}", "wins": 0, "losses": 0, "points_for": 0.0}
        for i in range(1, 11)
    ]
    assert _any_games_played(standings) is False


def test_games_played_once_any_team_has_a_decision():
    standings = [
        {"rank": 1, "team": "A", "wins": 1, "losses": 0, "points_for": 120.0},
        {"rank": 2, "team": "B", "wins": 0, "losses": 1, "points_for": 90.0},
    ]
    assert _any_games_played(standings) is True


def test_empty_standings_is_not_games_played():
    assert _any_games_played([]) is False


def test_checkpoint_same_day_after_first_slot():
    now = datetime(2026, 8, 15, 9, 30, tzinfo=timezone.utc)
    assert _previous_checkpoint(HOURS, now) == datetime(2026, 8, 15, 7, 0, tzinfo=timezone.utc)


def test_checkpoint_same_day_after_last_slot():
    now = datetime(2026, 8, 15, 20, 0, tzinfo=timezone.utc)
    assert _previous_checkpoint(HOURS, now) == datetime(2026, 8, 15, 18, 0, tzinfo=timezone.utc)


def test_checkpoint_before_first_slot_falls_back_to_yesterday():
    now = datetime(2026, 8, 15, 3, 0, tzinfo=timezone.utc)
    assert _previous_checkpoint(HOURS, now) == datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc)


def test_checkpoint_exactly_on_a_slot_counts_as_that_slot():
    now = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
    assert _previous_checkpoint(HOURS, now) == datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
