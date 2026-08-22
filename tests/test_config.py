"""Tests for the zero-touch SEASON="auto" resolution (no network)."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import _current_nfl_season


def test_early_fall_is_that_years_season():
    d = datetime(2026, 9, 15, tzinfo=timezone.utc)
    assert _current_nfl_season(d) == 2026


def test_december_is_that_years_season():
    d = datetime(2026, 12, 20, tzinfo=timezone.utc)
    assert _current_nfl_season(d) == 2026


def test_january_still_belongs_to_previous_seasons_year():
    d = datetime(2027, 1, 10, tzinfo=timezone.utc)
    assert _current_nfl_season(d) == 2026


def test_february_still_belongs_to_previous_seasons_year():
    d = datetime(2027, 2, 25, tzinfo=timezone.utc)
    assert _current_nfl_season(d) == 2026


def test_march_rolls_into_the_new_season_year():
    d = datetime(2027, 3, 1, tzinfo=timezone.utc)
    assert _current_nfl_season(d) == 2027
